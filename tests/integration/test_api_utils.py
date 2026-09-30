"""Інтеграційні тести службових маршрутів."""

from unittest.mock import AsyncMock, MagicMock

from main import app
from src.database.db import get_db


def test_healthchecker(client):
    response = client.get("/api/healthchecker")

    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to FastAPI!"}


def test_healthchecker_database_error(client):
    original_get_db = app.dependency_overrides[get_db]
    broken_session = AsyncMock()
    broken_session.execute.side_effect = Exception("connection refused")

    async def broken_get_db():
        yield broken_session

    app.dependency_overrides[get_db] = broken_get_db
    try:
        response = client.get("/api/healthchecker")
    finally:
        app.dependency_overrides[get_db] = original_get_db

    assert response.status_code == 500
    assert response.json()["detail"] == "Error connecting to the database"


def test_healthchecker_empty_result(client):
    original_get_db = app.dependency_overrides[get_db]
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = AsyncMock()
    session.execute.return_value = result

    async def empty_get_db():
        yield session

    app.dependency_overrides[get_db] = empty_get_db
    try:
        response = client.get("/api/healthchecker")
    finally:
        app.dependency_overrides[get_db] = original_get_db

    assert response.status_code == 500
