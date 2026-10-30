from unittest.mock import Mock

from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.features.todos.models import TodoRecord
from app.features.todos.repository import TodoRepository


def test_list_maps_models_and_orders_tasks_newest_first(model_factory, todo_values, todo):
    session = Mock(spec=Session)
    session.scalars.return_value = [model_factory(todo_values)]
    assert TodoRepository(session).list() == [todo]
    statement = session.scalars.call_args.args[0]
    expected = select(TodoRecord).order_by(TodoRecord.created_at.desc(), TodoRecord.id.desc())
    assert statement.compare(expected)
    compiled = str(statement.compile(dialect=postgresql.dialect()))
    assert "ORDER BY todos.created_at DESC, todos.id DESC" in compiled


def test_get_returns_none_for_missing_task():
    session = Mock(spec=Session)
    session.get.return_value = None
    assert TodoRepository(session).get(404) is None
    session.get.assert_called_once_with(TodoRecord, 404)


def test_get_returns_existing_task(model_factory, todo_values, todo):
    session = Mock(spec=Session)
    session.get.return_value = model_factory(todo_values)
    assert TodoRepository(session).get(todo.id) == todo


def test_create_commits_refreshes_and_returns_task():
    from app.features.todos.schemas import TodoCreate

    session = Mock(spec=Session)
    session.refresh.side_effect = lambda record: setattr(record, "id", 9)
    payload = TodoCreate(title="New task")
    result = TodoRepository(session).create(payload)
    record = session.add.call_args.args[0]
    assert result.id == 9
    assert result.title == "New task"
    assert result.completed is False
    assert result.created_at == result.updated_at
    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(record)


def test_update_changes_only_supplied_fields(model_factory, todo_values):
    from app.features.todos.schemas import TodoUpdate

    session = Mock(spec=Session)
    record = model_factory(todo_values)
    session.get.return_value = record
    result = TodoRepository(session).update(7, TodoUpdate(completed=True, due_date=None))
    assert result.completed is True
    assert result.due_date is None
    assert result.title == todo_values["title"]
    assert result.created_at == todo_values["created_at"]
    assert result.updated_at > todo_values["updated_at"]
    session.commit.assert_called_once_with()
    session.refresh.assert_called_once_with(record)


def test_update_missing_task_does_not_commit():
    from app.features.todos.schemas import TodoUpdate

    session = Mock(spec=Session)
    session.get.return_value = None
    assert TodoRepository(session).update(404, TodoUpdate(completed=True)) is None
    session.commit.assert_not_called()


def test_delete_existing_task_commits(model_factory, todo_values):
    session = Mock(spec=Session)
    record = model_factory(todo_values)
    session.get.return_value = record
    assert TodoRepository(session).delete(7) is True
    session.delete.assert_called_once_with(record)
    session.commit.assert_called_once_with()


def test_delete_missing_task_does_not_commit():
    session = Mock(spec=Session)
    session.get.return_value = None
    assert TodoRepository(session).delete(404) is False
    session.delete.assert_not_called()
    session.commit.assert_not_called()
