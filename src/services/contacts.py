"""Бізнес-логіка для роботи з контактами."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.repository.contacts import ContactRepository
from src.schemas import ContactModel


class ContactService:
    """Сервіс контактів, що передає виклики до репозиторію контактів."""

    def __init__(self, db: AsyncSession):
        """
        Ініціалізує сервіс.

        Args:
            db: Активна асинхронна сесія бази даних.
        """
        self.repository = ContactRepository(db)

    async def get_contacts(
        self,
        skip: int,
        limit: int,
        user: User,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
    ):
        """
        Повертає контакти користувача з пошуком і пагінацією.

        Args:
            skip: Скільки контактів пропустити.
            limit: Максимальна кількість контактів у відповіді.
            user: Власник контактів.
            first_name: Частина імені для пошуку.
            last_name: Частина прізвища для пошуку.
            email: Частина email для пошуку.

        Returns:
            Список контактів.
        """
        return await self.repository.get_contacts(
            skip, limit, user, first_name, last_name, email
        )

    async def get_upcoming_birthdays(self, days: int, user: User):
        """
        Повертає контакти з днями народження на найближчі дні.

        Args:
            days: Кількість днів уперед.
            user: Власник контактів.

        Returns:
            Список контактів.
        """
        return await self.repository.get_upcoming_birthdays(days, user)

    async def get_contact(self, contact_id: int, user: User):
        """
        Повертає контакт користувача за ідентифікатором.

        Args:
            contact_id: Ідентифікатор контакту.
            user: Власник контакту.

        Returns:
            Контакт або None, якщо його не знайдено.
        """
        return await self.repository.get_contact_by_id(contact_id, user)

    async def get_contact_by_email(self, email: str, user: User):
        """
        Повертає контакт користувача за email.

        Args:
            email: Email контакту.
            user: Власник контакту.

        Returns:
            Контакт або None, якщо його не знайдено.
        """
        return await self.repository.get_contact_by_email(email, user)

    async def create_contact(self, body: ContactModel, user: User):
        """
        Створює контакт для користувача.

        Args:
            body: Дані контакту.
            user: Власник контакту.

        Returns:
            Створений контакт.
        """
        return await self.repository.create_contact(body, user)

    async def update_contact(self, contact_id: int, body: ContactModel, user: User):
        """
        Оновлює контакт користувача.

        Args:
            contact_id: Ідентифікатор контакту.
            body: Нові дані контакту.
            user: Власник контакту.

        Returns:
            Оновлений контакт або None, якщо його не знайдено.
        """
        return await self.repository.update_contact(contact_id, body, user)

    async def remove_contact(self, contact_id: int, user: User):
        """
        Видаляє контакт користувача.

        Args:
            contact_id: Ідентифікатор контакту.
            user: Власник контакту.

        Returns:
            Видалений контакт або None, якщо його не знайдено.
        """
        return await self.repository.remove_contact(contact_id, user)
