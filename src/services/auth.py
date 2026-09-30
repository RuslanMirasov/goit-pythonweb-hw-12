"""Автентифікація: хешування паролів, JWT-токени, кеш і перевірка ролей."""

import json
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.conf.config import settings
from src.database.db import get_db
from src.database.models import User, UserRole
from src.database.redis import get_redis
from src.services.users import UserService


class Hash:
    """Хешування та перевірка паролів за алгоритмом bcrypt."""

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password, hashed_password):
        """
        Перевіряє, чи відповідає пароль хешу.

        Args:
            plain_password: Пароль у відкритому вигляді.
            hashed_password: Збережений хеш пароля.

        Returns:
            True, якщо пароль правильний.
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str):
        """
        Хешує пароль.

        Args:
            password: Пароль у відкритому вигляді.

        Returns:
            bcrypt-хеш пароля.
        """
        return self.pwd_context.hash(password)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

RESET_TOKEN_EXPIRE_SECONDS = 3600


async def create_access_token(data: dict, expires_delta: int | None = None):
    """
    Створює JWT-токен доступу.

    Args:
        data: Дані для токена, зазвичай ``{"sub": username}``.
        expires_delta: Час життя токена в секундах. Якщо не задано,
            використовується ``JWT_EXPIRATION_SECONDS`` з налаштувань.

    Returns:
        Закодований JWT-токен.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + timedelta(seconds=expires_delta)
    else:
        expire = datetime.now(UTC) + timedelta(
            seconds=settings.JWT_EXPIRATION_SECONDS
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def user_cache_key(username: str) -> str:
    """
    Повертає ключ Redis для кешу користувача.

    Args:
        username: Ім'я користувача.

    Returns:
        Ключ у форматі ``user:<username>``.
    """
    return f"user:{username}"


def user_to_cache(user: User) -> str:
    """
    Серіалізує користувача в JSON для збереження в кеші.

    Хеш пароля до кешу не потрапляє.

    Args:
        user: Користувач із бази даних.

    Returns:
        JSON-рядок з даними користувача.
    """
    return json.dumps(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "confirmed": user.confirmed,
            "role": user.role.value,
        }
    )


def user_from_cache(data: str) -> User:
    """
    Відновлює користувача з JSON, збереженого в кеші.

    Args:
        data: JSON-рядок з кешу.

    Returns:
        Об'єкт користувача, не прив'язаний до сесії бази даних.
    """
    user_data = json.loads(data)
    user_data["role"] = UserRole(user_data["role"])
    return User(**user_data)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    cache: Redis = Depends(get_redis),
):
    """
    Повертає поточного користувача за JWT-токеном.

    Спочатку шукає користувача в кеші Redis. Якщо його там немає, бере з бази
    даних і зберігає в кеш на ``REDIS_TTL_SECONDS`` секунд.

    Args:
        token: JWT-токен із заголовка Authorization.
        db: Сесія бази даних.
        cache: Клієнт Redis.

    Returns:
        Поточний користувач.

    Raises:
        HTTPException: 401, якщо токен недійсний або користувача не знайдено.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        username = payload["sub"]
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    cached_user = await cache.get(user_cache_key(username))
    if cached_user:
        return user_from_cache(cached_user)

    user_service = UserService(db)
    user = await user_service.get_user_by_username(username)
    if user is None:
        raise credentials_exception
    await cache.set(
        user_cache_key(username),
        user_to_cache(user),
        ex=settings.REDIS_TTL_SECONDS,
    )
    return user


def get_current_admin_user(current_user: User = Depends(get_current_user)):
    """
    Повертає поточного користувача, якщо він має роль адміністратора.

    Args:
        current_user: Поточний користувач.

    Returns:
        Поточний користувач з роллю admin.

    Raises:
        HTTPException: 403, якщо користувач не адміністратор.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user


def create_email_token(data: dict):
    """
    Створює токен для підтвердження email, дійсний 7 днів.

    Args:
        data: Дані для токена, зазвичай ``{"sub": email}``.

    Returns:
        Закодований JWT-токен.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=7)
    to_encode.update({"iat": datetime.now(UTC), "exp": expire})
    token = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    return token


async def get_email_from_token(token: str):
    """
    Дістає email із токена підтвердження.

    Args:
        token: Токен із посилання в листі.

    Returns:
        Email користувача.

    Raises:
        HTTPException: 422, якщо токен недійсний.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        email = payload["sub"]
        return email
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid email verification token",
        )


def create_reset_password_token(data: dict):
    """
    Створює токен для скидання пароля.

    Токен дійсний ``RESET_TOKEN_EXPIRE_SECONDS`` секунд і містить
    ``scope: reset_password``, тому інші токени для скидання не підходять.

    Args:
        data: Дані для токена, зазвичай ``{"sub": email}``.

    Returns:
        Закодований JWT-токен.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(seconds=RESET_TOKEN_EXPIRE_SECONDS)
    to_encode.update(
        {"iat": datetime.now(UTC), "exp": expire, "scope": "reset_password"}
    )
    token = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    return token


async def get_email_from_reset_token(token: str):
    """
    Дістає email із токена скидання пароля.

    Args:
        token: Токен із листа.

    Returns:
        Email користувача.

    Raises:
        HTTPException: 422, якщо токен недійсний, прострочений або має інший scope.
    """
    invalid_token_exception = HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Invalid or expired password reset token",
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        raise invalid_token_exception
    if payload.get("scope") != "reset_password":
        raise invalid_token_exception
    return payload["sub"]


def reset_token_key(token: str) -> str:
    """
    Повертає ключ Redis для використаного токена скидання пароля.

    Args:
        token: Токен скидання пароля.

    Returns:
        Ключ у форматі ``reset_token_used:<token>``.
    """
    return f"reset_token_used:{token}"
