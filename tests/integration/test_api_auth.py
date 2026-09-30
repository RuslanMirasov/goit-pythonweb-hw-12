"""Інтеграційні тести маршрутів автентифікації."""

import asyncio

from sqlalchemy import select

from src.database.models import User
from src.services.auth import create_email_token, create_reset_password_token
from tests.integration.conftest import TestingSessionLocal

user_data = {
    "username": "agent007",
    "email": "agent007@example.com",
    "password": "12345678",
}


def login(client, username, password):
    return client.post(
        "/api/auth/login", data={"username": username, "password": password}
    )


def test_signup(client, mock_emails):
    response = client.post("/api/auth/register", json=user_data)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert data["role"] == "user"
    assert data["avatar"].startswith("https://www.gravatar.com/")
    assert "password" not in data
    assert "hashed_password" not in data
    mock_emails["verify"].assert_called_once()


def test_repeat_signup_email(client):
    response = client.post(
        "/api/auth/register", json={**user_data, "username": "other_name"}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "User with this email already exists"


def test_repeat_signup_username(client):
    response = client.post(
        "/api/auth/register", json={**user_data, "email": "other@example.com"}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "User with this username already exists"


def test_signup_invalid_data(client):
    response = client.post(
        "/api/auth/register",
        json={"username": "ab", "email": "not-email", "password": "123"},
    )

    assert response.status_code == 422


def test_not_confirmed_login(client):
    response = login(client, user_data["username"], user_data["password"])

    assert response.status_code == 401
    assert response.json()["detail"] == "Email is not confirmed"


def test_request_email_not_confirmed(client, mock_emails):
    response = client.post("/api/auth/request_email", json={"email": user_data["email"]})

    assert response.status_code == 200
    assert response.json()["message"] == "Check your email for confirmation"
    mock_emails["verify"].assert_called_once()


def test_request_email_unknown(client, mock_emails):
    response = client.post(
        "/api/auth/request_email", json={"email": "nobody@example.com"}
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Check your email for confirmation"
    mock_emails["verify"].assert_not_called()


def test_confirmed_email(client):
    token = create_email_token({"sub": user_data["email"]})

    response = client.get(f"/api/auth/confirmed_email/{token}")

    assert response.status_code == 200
    assert response.json()["message"] == "Email confirmed"


def test_confirmed_email_again(client):
    token = create_email_token({"sub": user_data["email"]})

    response = client.get(f"/api/auth/confirmed_email/{token}")

    assert response.status_code == 200
    assert response.json()["message"] == "Your email is already confirmed"


def test_confirmed_email_unknown_user(client):
    token = create_email_token({"sub": "nobody@example.com"})

    response = client.get(f"/api/auth/confirmed_email/{token}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Verification error"


def test_confirmed_email_invalid_token(client):
    response = client.get("/api/auth/confirmed_email/invalid-token")

    assert response.status_code == 422


def test_request_email_already_confirmed(client, mock_emails):
    response = client.post("/api/auth/request_email", json={"email": user_data["email"]})

    assert response.status_code == 200
    assert response.json()["message"] == "Your email is already confirmed"
    mock_emails["verify"].assert_not_called()


def test_login(client):
    response = login(client, user_data["username"], user_data["password"])

    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_wrong_password_login(client):
    response = login(client, user_data["username"], "wrong-password")

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_wrong_username_login(client):
    response = login(client, "unknown", user_data["password"])

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_request_password_reset(client, mock_emails):
    response = client.post(
        "/api/auth/request_password_reset", json={"email": user_data["email"]}
    )

    assert response.status_code == 200
    mock_emails["reset"].assert_called_once()


def test_request_password_reset_unknown(client, mock_emails):
    response = client.post(
        "/api/auth/request_password_reset", json={"email": "nobody@example.com"}
    )

    assert response.status_code == 200
    mock_emails["reset"].assert_not_called()


def test_reset_password(client, fake_redis):
    token = create_reset_password_token({"sub": user_data["email"]})

    response = client.post(
        "/api/auth/reset_password", json={"token": token, "password": "newpassword"}
    )

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "Password has been reset"
    assert login(client, user_data["username"], user_data["password"]).status_code == 401
    assert login(client, user_data["username"], "newpassword").status_code == 200

    repeat = client.post(
        "/api/auth/reset_password", json={"token": token, "password": "another123"}
    )
    assert repeat.status_code == 422


def test_reset_password_hash_saved(client):
    async def get_user():
        async with TestingSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.email == user_data["email"])
            )
            return result.scalar_one()

    user = asyncio.run(get_user())

    assert user.hashed_password != "newpassword"
    assert user.hashed_password.startswith("$2b$")


def test_reset_password_with_email_token(client):
    token = create_email_token({"sub": user_data["email"]})

    response = client.post(
        "/api/auth/reset_password", json={"token": token, "password": "another123"}
    )

    assert response.status_code == 422


def test_reset_password_unknown_user(client):
    token = create_reset_password_token({"sub": "nobody@example.com"})

    response = client.post(
        "/api/auth/reset_password", json={"token": token, "password": "another123"}
    )

    assert response.status_code == 400
