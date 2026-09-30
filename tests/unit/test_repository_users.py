"""Модульні тести репозиторію користувачів."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.repository.users import UserRepository
from src.schemas import UserCreate


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def user_repository(mock_session):
    return UserRepository(mock_session)


@pytest.fixture
def user():
    return User(
        id=1,
        username="testuser",
        email="testuser@example.com",
        hashed_password="hashed",
        confirmed=False,
    )


def mock_scalar_result(mock_session, value):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = value
    mock_session.execute = AsyncMock(return_value=mock_result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method, argument",
    [
        ("get_user_by_id", 1),
        ("get_user_by_username", "testuser"),
        ("get_user_by_email", "testuser@example.com"),
    ],
)
async def test_get_user(user_repository, mock_session, user, method, argument):
    # Setup
    mock_scalar_result(mock_session, user)

    # Call method
    result = await getattr(user_repository, method)(argument)

    # Assertions
    assert result == user
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_not_found(user_repository, mock_session):
    # Setup
    mock_scalar_result(mock_session, None)

    # Call method
    result = await user_repository.get_user_by_email("nobody@example.com")

    # Assertions
    assert result is None


@pytest.mark.asyncio
async def test_create_user(user_repository, mock_session):
    # Setup
    body = UserCreate(
        username="newuser", email="newuser@example.com", password="hashed_password"
    )

    # Call method
    result = await user_repository.create_user(body, avatar="http://avatar.url")

    # Assertions
    assert isinstance(result, User)
    assert result.username == "newuser"
    assert result.hashed_password == "hashed_password"
    assert result.avatar == "http://avatar.url"
    mock_session.add.assert_called_once_with(result)
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(result)


@pytest.mark.asyncio
async def test_confirmed_email(user_repository, mock_session, user):
    # Setup
    mock_scalar_result(mock_session, user)

    # Call method
    await user_repository.confirmed_email(user.email)

    # Assertions
    assert user.confirmed is True
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_avatar_url(user_repository, mock_session, user):
    # Setup
    mock_scalar_result(mock_session, user)

    # Call method
    result = await user_repository.update_avatar_url(user.email, "http://new.url")

    # Assertions
    assert result.avatar == "http://new.url"
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_update_password(user_repository, mock_session, user):
    # Setup
    mock_scalar_result(mock_session, user)

    # Call method
    result = await user_repository.update_password(user.email, "new_hash")

    # Assertions
    assert result.hashed_password == "new_hash"
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(user)
