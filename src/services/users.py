"""Бізнес-логіка для роботи з користувачами."""

from libgravatar import Gravatar
from sqlalchemy.ext.asyncio import AsyncSession

from src.repository.users import UserRepository
from src.schemas import UserCreate


class UserService:
    """Сервіс користувачів, що працює поверх репозиторію користувачів."""

    def __init__(self, db: AsyncSession):
        """
        Ініціалізує сервіс.

        Args:
            db: Активна асинхронна сесія бази даних.
        """
        self.repository = UserRepository(db)

    async def create_user(self, body: UserCreate):
        """
        Створює користувача з аватаром із Gravatar.

        Якщо отримати аватар не вдалося, користувач створюється без нього.

        Args:
            body: Дані реєстрації з уже захешованим паролем.

        Returns:
            Створений користувач.
        """
        avatar = None
        try:
            g = Gravatar(body.email)
            avatar = g.get_image()
        except Exception as e:
            print(e)

        return await self.repository.create_user(body, avatar)

    async def get_user_by_id(self, user_id: int):
        """
        Повертає користувача за ідентифікатором.

        Args:
            user_id: Ідентифікатор користувача.

        Returns:
            Користувач або None, якщо його не знайдено.
        """
        return await self.repository.get_user_by_id(user_id)

    async def get_user_by_username(self, username: str):
        """
        Повертає користувача за іменем.

        Args:
            username: Ім'я користувача.

        Returns:
            Користувач або None, якщо його не знайдено.
        """
        return await self.repository.get_user_by_username(username)

    async def get_user_by_email(self, email: str):
        """
        Повертає користувача за email.

        Args:
            email: Email користувача.

        Returns:
            Користувач або None, якщо його не знайдено.
        """
        return await self.repository.get_user_by_email(email)

    async def confirmed_email(self, email: str):
        """
        Підтверджує email користувача.

        Args:
            email: Email користувача.
        """
        return await self.repository.confirmed_email(email)

    async def update_avatar_url(self, email: str, url: str):
        """
        Оновлює аватар користувача.

        Args:
            email: Email користувача.
            url: Новий URL аватара.

        Returns:
            Оновлений користувач.
        """
        return await self.repository.update_avatar_url(email, url)

    async def update_password(self, email: str, hashed_password: str):
        """
        Оновлює пароль користувача.

        Args:
            email: Email користувача.
            hashed_password: Новий bcrypt-хеш пароля.

        Returns:
            Оновлений користувач.
        """
        return await self.repository.update_password(email, hashed_password)
