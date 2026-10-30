from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.api.dependencies import get_repository
from app.factory import create_app


def test_factory_registers_routes_database_url_and_lifespan():
    app = create_app("postgresql://test/db")
    assert app.state.database_url == "postgresql://test/db"
    paths = app.openapi()["paths"]
    assert "/api/health" in paths
    assert "/api/todos" in paths
    assert "/api/todos/{todo_id}" in paths


def test_health_checks_database_before_returning_ok():
    app = create_app("postgresql://test/db")
    repository = Mock()
    app.dependency_overrides[get_repository] = lambda: repository
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    repository.session.execute.assert_called_once()


def test_health_does_not_hide_database_failure():
    app = create_app("postgresql://test/db")
    repository = Mock()
    repository.session.execute.side_effect = RuntimeError("Database unavailable")
    app.dependency_overrides[get_repository] = lambda: repository
    response = TestClient(app, raise_server_exceptions=False).get("/api/health")
    assert response.status_code == 500


def test_factory_runs_database_lifespan():
    engine = Mock()
    with patch("app.core.lifespan.create_database_engine", return_value=engine), \
         patch("app.core.lifespan.initialize") as initialize, \
         patch("app.core.lifespan.create_session_factory", return_value="factory"):
        with TestClient(create_app("postgresql://test/db")) as client:
            assert client.app.state.session_factory == "factory"
            initialize.assert_called_once_with(engine)
        engine.dispose.assert_called_once_with()
