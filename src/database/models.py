"""ORM-моделі бази даних."""

from datetime import date, datetime
from enum import Enum

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовий клас для всіх ORM-моделей."""

    pass


class UserRole(str, Enum):
    """Ролі користувачів застосунку."""

    USER = "user"
    ADMIN = "admin"


class User(Base):
    """
    Користувач застосунку.

    Пароль зберігається лише у вигляді хешу. Користувач може увійти в систему
    тільки після підтвердження email (``confirmed``).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(255))
    confirmed: Mapped[bool] = mapped_column(default=False)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole), default=UserRole.USER, server_default="USER", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    contacts: Mapped[list["Contact"]] = relationship(back_populates="user")


class Contact(Base):
    """
    Контакт, що належить користувачу.

    Email контакту унікальний у межах одного користувача.
    """

    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("email", "user_id", name="unique_contact_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    birthday: Mapped[date] = mapped_column(nullable=False)
    additional_data: Mapped[str | None] = mapped_column(String(250))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="contacts")
