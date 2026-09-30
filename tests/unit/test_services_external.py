"""Модульні тести сервісів, що працюють із зовнішніми системами: пошта, Cloudinary, Gravatar."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi_mail.errors import ConnectionErrors

from src.schemas import UserCreate
from src.services.email import send_email, send_reset_password_email
from src.services.upload_file import UploadFileService
from src.services.users import UserService


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "send_function, template",
    [
        (send_email, "verify_email.html"),
        (send_reset_password_email, "reset_password.html"),
    ],
)
async def test_send_email(send_function, template):
    with patch("src.services.email.FastMail.send_message", new_callable=AsyncMock) as mock_send:
        await send_function("user@example.com", "user", "http://localhost:8000/")

    mock_send.assert_awaited_once()
    message = mock_send.call_args.args[0]
    assert message.recipients[0].email == "user@example.com"
    assert mock_send.call_args.kwargs["template_name"] == template
    assert "token" in message.template_body


@pytest.mark.asyncio
@pytest.mark.parametrize("send_function", [send_email, send_reset_password_email])
async def test_send_email_connection_error(send_function, capsys):
    with patch(
        "src.services.email.FastMail.send_message",
        new_callable=AsyncMock,
        side_effect=ConnectionErrors("SMTP is down"),
    ):
        await send_function("user@example.com", "user", "http://localhost:8000/")

    assert "SMTP is down" in capsys.readouterr().out


def test_upload_file():
    file = MagicMock()
    with patch(
        "src.services.upload_file.cloudinary.uploader.upload",
        return_value={"version": 123},
    ) as mock_upload:
        service = UploadFileService("cloud", "key", "secret")
        url = service.upload_file(file, "testuser")

    mock_upload.assert_called_once_with(
        file.file, public_id="RestApp/testuser", overwrite=True
    )
    assert "RestApp/testuser" in url
    assert "v123" in url


@pytest.mark.asyncio
async def test_create_user_without_gravatar():
    body = UserCreate(username="newuser", email="newuser@example.com", password="hashed")
    service = UserService(AsyncMock())
    service.repository.create_user = AsyncMock(return_value="created")

    with patch("src.services.users.Gravatar", side_effect=Exception("no network")):
        result = await service.create_user(body)

    assert result == "created"
    service.repository.create_user.assert_awaited_once_with(body, None)


@pytest.mark.asyncio
async def test_get_user_by_id():
    service = UserService(AsyncMock())
    service.repository.get_user_by_id = AsyncMock(return_value="user")

    result = await service.get_user_by_id(1)

    assert result == "user"
    service.repository.get_user_by_id.assert_awaited_once_with(1)
