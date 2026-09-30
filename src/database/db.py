"""Асинхронне підключення до бази даних PostgreSQL."""

import contextlib

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from src.conf.config import settings


class DatabaseSessionManager:
    """Створює рушій SQLAlchemy та видає асинхронні сесії бази даних."""

    def __init__(self, url: str):
        """
        Ініціалізує рушій і фабрику сесій.

        Args:
            url: Рядок підключення до бази даних.
        """
        self._engine: AsyncEngine | None = create_async_engine(url)
        self._session_maker: async_sessionmaker = async_sessionmaker(
            autoflush=False, autocommit=False, bind=self._engine
        )

    @contextlib.asynccontextmanager
    async def session(self):
        """
        Відкриває сесію бази даних і закриває її після використання.

        У разі помилки SQLAlchemy транзакція відкочується.

        Yields:
            Асинхронна сесія бази даних.

        Raises:
            Exception: Якщо фабрику сесій не ініціалізовано.
        """
        if self._session_maker is None:
            raise Exception("Database session is not initialized")
        session = self._session_maker()
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            await session.close()


sessionmanager = DatabaseSessionManager(settings.DB_URL)


async def get_db():
    """
    Залежність FastAPI, що надає сесію бази даних на час запиту.

    Yields:
        Асинхронна сесія бази даних.
    """
    async with sessionmanager.session() as session:
        yield session
