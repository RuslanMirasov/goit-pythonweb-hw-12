"""Модульні тести репозиторію контактів."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.repository.contacts import ContactRepository
from src.schemas import ContactModel


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def contact_repository(mock_session):
    return ContactRepository(mock_session)


@pytest.fixture
def user():
    return User(id=1, username="testuser")


@pytest.fixture
def contact(user):
    return Contact(
        id=1,
        first_name="Olena",
        last_name="Shevchenko",
        email="olena@example.com",
        phone="+380501112233",
        birthday=date(1995, 10, 2),
        user_id=user.id,
    )


@pytest.fixture
def contact_body():
    return ContactModel(
        first_name="Taras",
        last_name="Shevchuk",
        email="taras@example.com",
        phone="+380677654321",
        birthday=date(1990, 3, 9),
    )


def mock_scalar_result(mock_session, value):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = value
    mock_session.execute = AsyncMock(return_value=mock_result)


def mock_scalars_result(mock_session, values):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = values
    mock_session.execute = AsyncMock(return_value=mock_result)


@pytest.mark.asyncio
async def test_get_contacts(contact_repository, mock_session, user, contact):
    # Setup
    mock_scalars_result(mock_session, [contact])

    # Call method
    contacts = await contact_repository.get_contacts(skip=0, limit=10, user=user)

    # Assertions
    assert len(contacts) == 1
    assert contacts[0].first_name == "Olena"
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_contacts_with_filters(contact_repository, mock_session, user, contact):
    # Setup
    mock_scalars_result(mock_session, [contact])

    # Call method
    contacts = await contact_repository.get_contacts(
        skip=0,
        limit=10,
        user=user,
        first_name="ole",
        last_name="shev",
        email="example",
    )

    # Assertions
    assert contacts == [contact]
    query = str(mock_session.execute.call_args.args[0]).lower()
    assert query.count("like") == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "today, expected_operator",
    [(date(2026, 9, 29), "between"), (date(2026, 12, 28), " or ")],
)
async def test_get_upcoming_birthdays(
    contact_repository, mock_session, user, contact, monkeypatch, today, expected_operator
):
    # Setup
    class FakeDate(date):
        @classmethod
        def today(cls):
            return today

    monkeypatch.setattr("src.repository.contacts.date", FakeDate)
    mock_scalars_result(mock_session, [contact])

    # Call method
    contacts = await contact_repository.get_upcoming_birthdays(days=7, user=user)

    # Assertions
    assert contacts == [contact]
    query = str(mock_session.execute.call_args.args[0]).lower()
    assert expected_operator in query


@pytest.mark.asyncio
async def test_get_contact_by_id(contact_repository, mock_session, user, contact):
    # Setup
    mock_scalar_result(mock_session, contact)

    # Call method
    result = await contact_repository.get_contact_by_id(contact_id=1, user=user)

    # Assertions
    assert result is not None
    assert result.id == 1
    assert result.email == "olena@example.com"


@pytest.mark.asyncio
async def test_get_contact_by_email(contact_repository, mock_session, user, contact):
    # Setup
    mock_scalar_result(mock_session, contact)

    # Call method
    result = await contact_repository.get_contact_by_email("olena@example.com", user)

    # Assertions
    assert result == contact


@pytest.mark.asyncio
async def test_create_contact(contact_repository, mock_session, user, contact_body):
    # Call method
    result = await contact_repository.create_contact(body=contact_body, user=user)

    # Assertions
    assert isinstance(result, Contact)
    assert result.first_name == "Taras"
    assert result.user_id == user.id
    mock_session.add.assert_called_once_with(result)
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(result)


@pytest.mark.asyncio
async def test_update_contact(contact_repository, mock_session, user, contact, contact_body):
    # Setup
    mock_scalar_result(mock_session, contact)

    # Call method
    result = await contact_repository.update_contact(1, contact_body, user)

    # Assertions
    assert result.first_name == "Taras"
    assert result.email == "taras@example.com"
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(contact)


@pytest.mark.asyncio
async def test_update_contact_not_found(contact_repository, mock_session, user, contact_body):
    # Setup
    mock_scalar_result(mock_session, None)

    # Call method
    result = await contact_repository.update_contact(999, contact_body, user)

    # Assertions
    assert result is None
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_contact(contact_repository, mock_session, user, contact):
    # Setup
    mock_scalar_result(mock_session, contact)

    # Call method
    result = await contact_repository.remove_contact(1, user)

    # Assertions
    assert result == contact
    mock_session.delete.assert_awaited_once_with(contact)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_contact_not_found(contact_repository, mock_session, user):
    # Setup
    mock_scalar_result(mock_session, None)

    # Call method
    result = await contact_repository.remove_contact(999, user)

    # Assertions
    assert result is None
    mock_session.delete.assert_not_awaited()
