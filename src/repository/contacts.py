"""Шар доступу до даних для контактів."""

from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.schemas import ContactModel


class ContactRepository:
    """Репозиторій з операціями над контактами користувача в базі даних."""

    def __init__(self, session: AsyncSession):
        """
        Ініціалізує репозиторій.

        Args:
            session: Активна асинхронна сесія бази даних.
        """
        self.db = session

    async def get_contacts(
        self,
        skip: int,
        limit: int,
        user: User,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
    ) -> list[Contact]:
        """
        Повертає контакти користувача з пошуком і пагінацією.

        Пошук за іменем, прізвищем та email нечутливий до регістру і знаходить
        часткові збіги. Кілька фільтрів поєднуються через «І».

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
        stmt = select(Contact).filter_by(user_id=user.id)
        if first_name:
            stmt = stmt.where(Contact.first_name.ilike(f"%{first_name}%"))
        if last_name:
            stmt = stmt.where(Contact.last_name.ilike(f"%{last_name}%"))
        if email:
            stmt = stmt.where(Contact.email.ilike(f"%{email}%"))
        stmt = stmt.offset(skip).limit(limit)
        contacts = await self.db.execute(stmt)
        return contacts.scalars().all()

    async def get_upcoming_birthdays(self, days: int, user: User) -> list[Contact]:
        """
        Повертає контакти з днями народження на найближчі дні.

        Порівнюються лише місяць і день народження, тому рік не має значення.
        Враховується перехід через Новий рік: спочатку йдуть дати до кінця
        поточного року, потім — з початку наступного.

        Args:
            days: Кількість днів уперед, починаючи з сьогодні.
            user: Власник контактів.

        Returns:
            Список контактів, відсортований за найближчою датою.
        """
        today = date.today()
        end_date = today + timedelta(days=days)
        birthday_md = func.to_char(Contact.birthday, "MM-DD")
        start_md = today.strftime("%m-%d")
        end_md = end_date.strftime("%m-%d")

        if start_md <= end_md:
            condition = birthday_md.between(start_md, end_md)
        else:
            condition = or_(birthday_md >= start_md, birthday_md <= end_md)

        stmt = (
            select(Contact)
            .filter_by(user_id=user.id)
            .where(condition)
            .order_by(birthday_md < start_md, birthday_md)
        )
        contacts = await self.db.execute(stmt)
        return contacts.scalars().all()

    async def get_contact_by_id(self, contact_id: int, user: User) -> Contact | None:
        """
        Знаходить контакт користувача за ідентифікатором.

        Args:
            contact_id: Ідентифікатор контакту.
            user: Власник контакту.

        Returns:
            Контакт або None, якщо його не знайдено чи він належить іншому користувачу.
        """
        stmt = select(Contact).filter_by(id=contact_id, user_id=user.id)
        contact = await self.db.execute(stmt)
        return contact.scalar_one_or_none()

    async def get_contact_by_email(self, email: str, user: User) -> Contact | None:
        """
        Знаходить контакт користувача за email.

        Args:
            email: Email контакту.
            user: Власник контакту.

        Returns:
            Контакт або None, якщо його не знайдено.
        """
        stmt = select(Contact).filter_by(email=email, user_id=user.id)
        contact = await self.db.execute(stmt)
        return contact.scalar_one_or_none()

    async def create_contact(self, body: ContactModel, user: User) -> Contact:
        """
        Створює новий контакт для користувача.

        Args:
            body: Дані контакту.
            user: Власник контакту.

        Returns:
            Створений контакт.
        """
        contact = Contact(**body.model_dump(exclude_unset=True), user_id=user.id)
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def update_contact(
        self, contact_id: int, body: ContactModel, user: User
    ) -> Contact | None:
        """
        Повністю оновлює контакт користувача.

        Args:
            contact_id: Ідентифікатор контакту.
            body: Нові дані контакту.
            user: Власник контакту.

        Returns:
            Оновлений контакт або None, якщо його не знайдено.
        """
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            for key, value in body.model_dump().items():
                setattr(contact, key, value)
            await self.db.commit()
            await self.db.refresh(contact)
        return contact

    async def remove_contact(self, contact_id: int, user: User) -> Contact | None:
        """
        Видаляє контакт користувача.

        Args:
            contact_id: Ідентифікатор контакту.
            user: Власник контакту.

        Returns:
            Видалений контакт або None, якщо його не знайдено.
        """
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            await self.db.delete(contact)
            await self.db.commit()
        return contact
