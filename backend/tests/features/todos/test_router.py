import pytest

from app.features.todos.schemas import TodoCreate


def test_list_returns_tasks_from_repository(client, repository_mock, todo):
    repository_mock.list.return_value = [todo]
    response = client.get("/api/todos")
    assert response.status_code == 200
    assert response.json() == [todo.model_dump(mode="json")]
    repository_mock.list.assert_called_once_with()


def test_create_trims_input_and_returns_created_task(client, repository_mock, todo):
    repository_mock.create.return_value = todo
    response = client.post("/api/todos", json={"title": "  Plan the sprint  ", "priority": "high"})
    assert response.status_code == 201
    assert response.json() == todo.model_dump(mode="json")
    repository_mock.create.assert_called_once_with(
        TodoCreate(title="Plan the sprint", priority="high")
    )


@pytest.mark.parametrize("payload", [
    {"title": "   "},
    {"title": "x" * 121},
    {"title": "Task", "priority": "urgent"},
    {"title": "Task", "due_date": "2026-02-30"},
])
def test_invalid_create_never_calls_repository(client, repository_mock, payload):
    assert client.post("/api/todos", json=payload).status_code == 422
    repository_mock.create.assert_not_called()


def test_get_returns_task(client, repository_mock, todo):
    repository_mock.get.return_value = todo
    response = client.get("/api/todos/7")
    assert response.status_code == 200
    assert response.json() == todo.model_dump(mode="json")
    repository_mock.get.assert_called_once_with(7)


def test_update_returns_saved_task(client, repository_mock, todo):
    from app.features.todos.schemas import TodoUpdate

    repository_mock.update.return_value = todo
    response = client.patch("/api/todos/7", json={"completed": True})
    assert response.status_code == 200
    assert response.json() == todo.model_dump(mode="json")
    repository_mock.update.assert_called_once_with(7, TodoUpdate(completed=True))


def test_delete_returns_empty_response(client, repository_mock):
    repository_mock.delete.return_value = True
    response = client.delete("/api/todos/7")
    assert response.status_code == 204
    assert response.content == b""
    repository_mock.delete.assert_called_once_with(7)


@pytest.mark.parametrize("method,operation,payload", [
    ("get", "get", None), ("patch", "update", {"completed": True}),
    ("delete", "delete", None),
])
def test_missing_task_returns_404(client, repository_mock, method, operation, payload):
    getattr(repository_mock, operation).return_value = None
    response = client.request(method, "/api/todos/404", json=payload)
    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found."}


@pytest.mark.parametrize("todo_id", [0, -1, "invalid"])
@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_invalid_id_never_calls_repository(client, repository_mock, todo_id, method):
    payload = {"completed": True} if method == "patch" else None
    assert client.request(method, f"/api/todos/{todo_id}", json=payload).status_code == 422
    repository_mock.get.assert_not_called()
    repository_mock.update.assert_not_called()
    repository_mock.delete.assert_not_called()
