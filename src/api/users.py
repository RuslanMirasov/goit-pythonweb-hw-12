"""Маршрути профілю користувача."""

from fastapi import APIRouter, Depends, File, Request, UploadFile
from redis.asyncio import Redis
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from src.conf.config import settings
from src.database.db import get_db
from src.database.redis import get_redis
from src.schemas import User
from src.services.auth import (
    get_current_admin_user,
    get_current_user,
    user_cache_key,
)
from src.services.upload_file import UploadFileService
from src.services.users import UserService

router = APIRouter(prefix="/users", tags=["users"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/me", response_model=User)
@limiter.limit("10/minute")
async def me(request: Request, user: User = Depends(get_current_user)):
    """
    Повертає профіль поточного користувача.

    Не більше 10 запитів на хвилину з однієї IP-адреси.
    \f
    Args:
        request: Вхідний запит, потрібен для обмеження кількості запитів.
        user: Поточний користувач.

    Returns:
        Поточний користувач.
    """
    return user


@router.patch("/avatar", response_model=User)
async def update_avatar_user(
    file: UploadFile = File(),
    user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
    cache: Redis = Depends(get_redis),
):
    """
    Завантажує новий аватар поточного користувача. Лише для адміністраторів.

    Зображення зберігається в Cloudinary, кеш користувача скидається.
    \f
    Args:
        file: Файл зображення.
        user: Поточний користувач з роллю admin.
        db: Сесія бази даних.
        cache: Клієнт Redis.

    Returns:
        Користувач з новим URL аватара.

    Raises:
        HTTPException: 403, якщо користувач не адміністратор.
    """
    avatar_url = UploadFileService(
        settings.CLD_NAME, settings.CLD_API_KEY, settings.CLD_API_SECRET
    ).upload_file(file, user.username)

    user_service = UserService(db)
    user = await user_service.update_avatar_url(user.email, avatar_url)
    await cache.delete(user_cache_key(user.username))
    return user
