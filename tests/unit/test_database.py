"""Модульні тести підключень до бази даних і Redis."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.database import db
from src.database.db import DatabaseSessionManager, get_db
from src.database.redis import get_redis, redis_client


@pytest.fixture
def session_manager():
    return DatabaseSessionManager("sqlite+aiosqlite:///:memory:")


@pytest.mark.asyncio
async def test_session_executes_query(session_manager):
    async with session_manager.session() as session:
        result = await session.execute(text("SELECT 1"))

    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_session_rollback_on_error(session_manager):
    with pytest.raises(SQLAlchemyError):
        async with session_manager.session() as session:
            await session.execute(text("SELECT * FROM missing_table"))


@pytest.mark.asyncio
async def test_session_not_initialized(session_manager):
    session_manager._session_maker = None

    with pytest.raises(Exception, match="not initialized"):
        async with session_manager.session():
            pass


@pytest.mark.asyncio
async def test_get_db(monkeypatch, session_manager):
    monkeypatch.setattr(db, "sessionmanager", session_manager)

    generator = get_db()
    session = await anext(generator)
    result = await session.execute(text("SELECT 1"))
    await generator.aclose()

    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_get_redis():
    assert await get_redis() is redis_client
