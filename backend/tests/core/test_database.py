from app.core.database import create_database_engine


def test_engine_uses_the_postgresql_psycopg_driver():
    url = "postgresql+psycopg://taskly:taskly@localhost:5432/taskly"
    engine = create_database_engine(url)
    try:
        assert engine.url.drivername == "postgresql+psycopg"
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
        assert engine.url.database == "taskly"
    finally:
        engine.dispose()


def test_session_factory_keeps_loaded_values_after_commit():
    from unittest.mock import Mock
    from app.core.database import create_session_factory

    engine = Mock()
    factory = create_session_factory(engine)
    assert factory.kw["bind"] is engine
    assert factory.kw["expire_on_commit"] is False


def test_initialize_creates_tables():
    from unittest.mock import Mock, patch
    from app.core.database import initialize

    engine = Mock()
    with patch("app.core.database.Base.metadata.create_all") as create_all:
        initialize(engine)
    create_all.assert_called_once_with(engine)
