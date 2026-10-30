from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.lifespan import lifespan


@pytest.mark.anyio
async def test_initializes_database_and_disposes_after_shutdown():
    app = SimpleNamespace(state=SimpleNamespace(database_url="postgresql://test/db"))
    engine = Mock()
    with patch("app.core.lifespan.create_database_engine", return_value=engine) as create, \
         patch("app.core.lifespan.initialize") as initialize, \
         patch("app.core.lifespan.create_session_factory", return_value="factory"):
        async with lifespan(app):
            assert app.state.session_factory == "factory"
            engine.dispose.assert_not_called()
        create.assert_called_once_with(app.state.database_url)
        initialize.assert_called_once_with(engine)
        engine.dispose.assert_called_once_with()


@pytest.mark.anyio
async def test_disposes_engine_when_initialization_fails():
    app = SimpleNamespace(state=SimpleNamespace(database_url="postgresql://test/db"))
    engine = Mock()
    with patch("app.core.lifespan.create_database_engine", return_value=engine), \
         patch("app.core.lifespan.initialize", side_effect=RuntimeError("Database unavailable")):
        with pytest.raises(RuntimeError, match="Database unavailable"):
            async with lifespan(app):
                pytest.fail("Startup must fail")
    engine.dispose.assert_called_once_with()


@pytest.fixture
def anyio_backend():
    return "asyncio"
