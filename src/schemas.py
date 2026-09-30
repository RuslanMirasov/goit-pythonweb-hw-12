"""Pydantic-схеми для валідації вхідних даних і формування відповідей API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PastDate

from src.database.models import UserRole


class ContactModel(BaseModel):
    """Дані контакту для створення та оновлення."""

    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=100)
    phone: str = Field(
        min_length=7,
        max_length=20,
        pattern=r"^\+?[\d\s\-()]+$",
        examples=["+38 (000) 000-00-00"],
    )
    birthday: PastDate
    additional_data: str | None = Field(default=None, max_length=250)


class ContactResponse(ContactModel):
    """Контакт у відповіді API."""

    id: int
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class User(BaseModel):
    """Користувач у відповіді API, без хешу пароля."""

    id: int
    username: str
    email: str
    avatar: str | None
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """Дані для реєстрації користувача."""

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr = Field(max_length=100)
    password: str = Field(min_length=6, max_length=72)


class Token(BaseModel):
    """Токен доступу, що видається після входу."""

    access_token: str
    token_type: str


class RequestEmail(BaseModel):
    """Email для повторного надсилання листа або скидання пароля."""

    email: EmailStr


class ResetPassword(BaseModel):
    """Токен із листа та новий пароль для скидання пароля."""

    token: str
    password: str = Field(min_length=6, max_length=72)
