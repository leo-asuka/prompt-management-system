from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import OperationalError

from src.app import database
from src.app import models

@pytest.mark.anyio("asyncio")
async def test_lifespan_initializes_engine_and_session(monkeypatch):
    fake_engine = MagicMock()
    fake_connect_ctx = MagicMock()
    fake_connect_ctx.__enter__.return_value = MagicMock()
    fake_engine.connect.return_value = fake_connect_ctx
    fake_engine.dispose = MagicMock()

    fake_session_factory = object()

    monkeypatch.setattr(database, "create_engine", lambda url: fake_engine)
    monkeypatch.setattr(
        database, "sessionmaker", lambda *args, **kwargs: fake_session_factory
    )
    monkeypatch.setattr(models.Base.metadata, "create_all", MagicMock())

    app = SimpleNamespace(state=SimpleNamespace())

    async with database.lifespan(app):
        assert app.state.engine is fake_engine
        assert app.state.SessionLocal is fake_session_factory

    fake_engine.dispose.assert_called_once()
    models.Base.metadata.create_all.assert_called_once_with(bind=fake_engine)


@pytest.mark.anyio("asyncio")
async def test_lifespan_retries_and_raises_when_db_unavailable(monkeypatch):
    error = OperationalError(None, None, Exception("db down"))

    class _FlakyEngine:
        def __init__(self):
            self.attempts = 0

        def connect(self):
            self.attempts += 1
            raise error

        def dispose(self):
            pass

    flaky_engine = _FlakyEngine()

    monkeypatch.setattr(database, "create_engine", lambda url: flaky_engine)
    monkeypatch.setattr(database, "sessionmaker", lambda *args, **kwargs: None)
    monkeypatch.setattr(models.Base.metadata, "create_all", MagicMock())
    monkeypatch.setattr(database.time, "sleep", lambda *_: None)

    app = SimpleNamespace(state=SimpleNamespace())

    with pytest.raises(RuntimeError):
        async with database.lifespan(app):
            pass

    assert flaky_engine.attempts == 5


def test_get_db_yields_session_and_closes():
    class _Session:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    session = _Session()
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(SessionLocal=lambda: session))
    )

    generator = database.get_db(request)
    yielded_session = next(generator)
    assert yielded_session is session

    generator.close()
    assert session.closed
