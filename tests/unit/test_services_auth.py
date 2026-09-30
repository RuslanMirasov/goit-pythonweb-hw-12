"""Модульні тести сервісу автентифікації."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from jose import jwt

from src.conf.config import settings
from src.database.models import User, UserRole
from src.services.auth import (
    Hash,
    create_access_token,
    create_email_token,
    create_reset_password_token,
    get_current_admin_user,
    get_current_user,
    get_email_from_reset_token,
    get_email_from_token,
    reset_token_key,
    user_cache_key,
    user_from_cache,
    user_to_cache,
)


@pytest.fixture
def user():
    return User(
        id=1,
        username="testuser",
        email="testuser@example.com",
        avatar=None,
        confirmed=True,
        role=UserRole.USER,
    )


def decode(token):
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def test_hash_password():
    hash_handler = Hash()
    hashed = hash_handler.get_password_hash("secret123")

    assert hashed != "secret123"
    assert hash_handler.verify_password("secret123", hashed)
    assert not hash_handler.verify_password("wrong", hashed)


@pytest.mark.asyncio
async def test_create_access_token_default_expiration():
    token = await create_access_token({"sub": "testuser"})
    payload = decode(token)

    assert payload["sub"] == "testuser"
    assert "exp" in payload


@pytest.mark.asyncio
async def test_create_access_token_custom_expiration():
    token = await create_access_token({"sub": "testuser"}, expires_delta=60)
    default_token = await create_access_token({"sub": "testuser"})

    assert decode(token)["exp"] < decode(default_token)["exp"]


def test_cache_keys():
    assert user_cache_key("testuser") == "user:testuser"
    assert reset_token_key("abc") == "reset_token_used:abc"


def test_user_cache_roundtrip(user):
    data = user_to_cache(user)
    restored = user_from_cache(data)

    assert "hashed_password" not in data
    assert restored.id == user.id
    assert restored.username == user.username
    assert restored.role == UserRole.USER


@pytest.mark.asyncio
async def test_get_current_user_from_cache(user):
    token = await create_access_token({"sub": user.username})
    cache = AsyncMock()
    cache.get.return_value = user_to_cache(user)
    db = AsyncMock()

    result = await get_current_user(token=token, db=db, cache=cache)

    assert result.username == user.username
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token="invalid", db=AsyncMock(), cache=AsyncMock())

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_without_sub():
    token = await create_access_token({"sub": None})

    with pytest.raises(HTTPException) as exc:
        await get_current_user(token=token, db=AsyncMock(), cache=AsyncMock())

    assert exc.value.status_code == 401


def test_get_current_admin_user(user):
    user.role = UserRole.ADMIN

    assert get_current_admin_user(user) == user


def test_get_current_admin_user_forbidden(user):
    with pytest.raises(HTTPException) as exc:
        get_current_admin_user(user)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_email_token():
    token = create_email_token({"sub": "testuser@example.com"})

    assert await get_email_from_token(token) == "testuser@example.com"


@pytest.mark.asyncio
async def test_email_token_invalid():
    with pytest.raises(HTTPException) as exc:
        await get_email_from_token("invalid")

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_reset_password_token():
    token = create_reset_password_token({"sub": "testuser@example.com"})

    assert decode(token)["scope"] == "reset_password"
    assert await get_email_from_reset_token(token) == "testuser@example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "token",
    ["invalid", create_email_token({"sub": "testuser@example.com"})],
)
async def test_reset_password_token_invalid(token):
    with pytest.raises(HTTPException) as exc:
        await get_email_from_reset_token(token)

    assert exc.value.status_code == 422
