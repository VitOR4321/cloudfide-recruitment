from unittest.mock import patch

import pytest
from sqlalchemy.engine import make_url

from app.core.config import resolve_database_url


def test_explicit_database_url_takes_precedence(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://environment/db")
    assert resolve_database_url("postgresql://explicit/db") == "postgresql://explicit/db"


def test_uses_database_url_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://environment/db")
    assert resolve_database_url() == "postgresql://environment/db"


def test_builds_url_with_escaped_credentials(monkeypatch):
    values = {
        "POSTGRES_USER": "user@example.com", "POSTGRES_PASSWORD": "p@ss:/word",
        "POSTGRES_HOST": "localhost", "DB_PORT": "5433", "POSTGRES_DB": "taskly",
    }
    with patch("app.core.config.load_dotenv"), patch.dict("os.environ", values, clear=True):
        url = make_url(resolve_database_url())
    assert url.username == values["POSTGRES_USER"]
    assert url.password == values["POSTGRES_PASSWORD"]
    assert url.host == "localhost"
    assert url.port == 5433
    assert url.database == "taskly"


def test_missing_configuration_fails_clearly():
    with patch("app.core.config.load_dotenv"), patch.dict("os.environ", {}, clear=True):
        with pytest.raises(KeyError, match="POSTGRES_USER"):
            resolve_database_url()
