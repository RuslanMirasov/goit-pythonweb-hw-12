"""Спільні фікстури для інтеграційних тестів маршрутів."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from main import app
from src.api.users import limiter
from src.database.db import get_db
from src.database.models import Base, User, UserRole
from src.database.redis import get_redis
from src.services.auth import Hash, create_access_token

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(
    autoflush=False, expire_on_commit=False, bind=engine
)

admin_user = {
    "username": "admin",
    "email": "admin@example.com",
    "password": "12345678",
}
regular_user = {
    "username": "regular",
    "email": "regular@example.com",
    "password": "12345678",
}


@event.listens_for(engine.sync_engine, "connect")
def register_sqlite_functions(dbapi_connection, connection_record):
    """Додає в SQLite функцію ``to_char``, яка є в PostgreSQL."""
    dbapi_connection.create_function(
        "to_char", 2, lambda value, fmt: value[5:10] if value else None
    )


class FakeRedis:
    """Імітація Redis у пам'яті для тестів."""

    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)


@pytest.fixture(scope="module", autouse=True)
def init_models_wrap():
    """Створює чисту базу з адміністратором і звичайним користувачем для кожного модуля."""

    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        async with TestingSessionLocal() as session:
            hash_handler = Hash()
            for data, role in ((admin_user, UserRole.ADMIN), (regular_user, UserRole.USER)):
                session.add(
                    User(
                        username=data["username"],
                        email=data["email"],
                        hashed_password=hash_handler.get_password_hash(data["password"]),
                        confirmed=True,
                        role=role,
                    )
                )
            await session.commit()

    asyncio.run(init_models())


@pytest.fixture(scope="module")
def fake_redis():
    return FakeRedis()


@pytest.fixture(scope="module")
def client(fake_redis):
    """Тестовий клієнт з тестовою базою, FakeRedis і вимкненим лімітером."""

    async def override_get_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    async def override_get_redis():
        return fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    limiter.enabled = False

    yield TestClient(app)

    app.dependency_overrides.clear()
    limiter.enabled = True


@pytest.fixture(autouse=True)
def mock_emails(monkeypatch):
    """Підміняє надсилання листів, щоб тести не відправляли справжню пошту."""
    mocks = {"verify": AsyncMock(), "reset": AsyncMock()}
    monkeypatch.setattr("src.api.auth.send_email", mocks["verify"])
    monkeypatch.setattr("src.api.auth.send_reset_password_email", mocks["reset"])
    return mocks


@pytest.fixture(scope="module")
def admin_token():
    return asyncio.run(create_access_token(data={"sub": admin_user["username"]}))


@pytest.fixture(scope="module")
def user_token():
    return asyncio.run(create_access_token(data={"sub": regular_user["username"]}))


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
