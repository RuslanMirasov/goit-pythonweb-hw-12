"""Інтеграційні тести маршрутів користувача."""

import asyncio
from unittest.mock import AsyncMock, patch

from main import app
from src.api.users import limiter
from src.database.db import get_db
from src.services.auth import create_access_token
from tests.integration.conftest import admin_user, auth_headers


def test_get_me(client, admin_token, fake_redis):
    response = client.get("/api/users/me", headers=auth_headers(admin_token))

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == admin_user["username"]
    assert data["role"] == "admin"
    assert "avatar" in data
    assert f"user:{admin_user['username']}" in fake_redis.store


def test_get_me_from_cache(client, admin_token):
    original_get_db = app.dependency_overrides[get_db]
    session = AsyncMock()

    async def tracked_get_db():
        yield session

    app.dependency_overrides[get_db] = tracked_get_db
    try:
        response = client.get("/api/users/me", headers=auth_headers(admin_token))
    finally:
        app.dependency_overrides[get_db] = original_get_db

    assert response.status_code == 200
    assert response.json()["username"] == admin_user["username"]
    session.execute.assert_not_awaited()


def test_get_me_unauthorized(client):
    response = client.get("/api/users/me")

    assert response.status_code == 401


def test_get_me_invalid_token(client):
    response = client.get("/api/users/me", headers=auth_headers("invalid-token"))

    assert response.status_code == 401


def test_get_me_unknown_user(client):
    token = asyncio.run(create_access_token(data={"sub": "ghost"}))

    response = client.get("/api/users/me", headers=auth_headers(token))

    assert response.status_code == 401


@patch("src.services.upload_file.UploadFileService.upload_file")
def test_update_avatar_admin(mock_upload_file, client, admin_token, fake_redis):
    fake_url = "http://example.com/avatar.jpg"
    mock_upload_file.return_value = fake_url
    file_data = {"file": ("avatar.jpg", b"fake image content", "image/jpeg")}

    response = client.patch(
        "/api/users/avatar", headers=auth_headers(admin_token), files=file_data
    )

    assert response.status_code == 200, response.text
    assert response.json()["avatar"] == fake_url
    mock_upload_file.assert_called_once()
    assert f"user:{admin_user['username']}" not in fake_redis.store


@patch("src.services.upload_file.UploadFileService.upload_file")
def test_update_avatar_forbidden_for_user(mock_upload_file, client, user_token):
    file_data = {"file": ("avatar.jpg", b"fake image content", "image/jpeg")}

    response = client.patch(
        "/api/users/avatar", headers=auth_headers(user_token), files=file_data
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"
    mock_upload_file.assert_not_called()


def test_rate_limit_me(client, user_token):
    limiter.enabled = True
    limiter.reset()
    try:
        codes = [
            client.get("/api/users/me", headers=auth_headers(user_token)).status_code
            for _ in range(11)
        ]
        last = client.get("/api/users/me", headers=auth_headers(user_token))
    finally:
        limiter.reset()
        limiter.enabled = False

    assert codes[:10] == [200] * 10
    assert codes[10] == 429
    assert last.json()["detail"] == "Rate limit exceeded. Please try again later."
