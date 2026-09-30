"""Маршрути автентифікації: реєстрація, вхід, підтвердження email, скидання пароля."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.database.redis import get_redis
from src.schemas import RequestEmail, ResetPassword, Token, User, UserCreate
from src.services.auth import (
    RESET_TOKEN_EXPIRE_SECONDS,
    Hash,
    create_access_token,
    get_email_from_reset_token,
    get_email_from_token,
    reset_token_key,
    user_cache_key,
)
from src.services.email import send_email, send_reset_password_email
from src.services.users import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Реєструє нового користувача.

    Пароль зберігається у вигляді хешу. На email надсилається лист
    із посиланням для підтвердження.
    \f
    Args:
        user_data: Дані реєстрації.
        background_tasks: Фонові задачі FastAPI для надсилання листа.
        request: Вхідний запит, з нього береться адреса застосунку.
        db: Сесія бази даних.

    Returns:
        Створений користувач.

    Raises:
        HTTPException: 409, якщо email або ім'я користувача вже зайняті.
    """
    user_service = UserService(db)

    if await user_service.get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    if await user_service.get_user_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this username already exists",
        )

    user_data.password = Hash().get_password_hash(user_data.password)
    new_user = await user_service.create_user(user_data)
    background_tasks.add_task(
        send_email, new_user.email, new_user.username, request.base_url
    )
    return new_user


@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Виконує вхід і повертає токен доступу.

    Увійти може лише користувач з підтвердженим email.
    \f
    Args:
        form_data: Форма з полями ``username`` і ``password``.
        db: Сесія бази даних.

    Returns:
        Токен доступу та його тип.

    Raises:
        HTTPException: 401, якщо логін чи пароль неправильні або email не підтверджено.
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_username(form_data.username)
    if not user or not Hash().verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email is not confirmed",
        )
    access_token = await create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db: AsyncSession = Depends(get_db)):
    """
    Підтверджує email за посиланням із листа.
    \f
    Args:
        token: Токен підтвердження з посилання.
        db: Сесія бази даних.

    Returns:
        Повідомлення про результат підтвердження.

    Raises:
        HTTPException: 400, якщо користувача не знайдено; 422, якщо токен недійсний.
    """
    email = await get_email_from_token(token)
    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    await user_service.confirmed_email(email)
    return {"message": "Email confirmed"}


@router.post("/request_email")
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Повторно надсилає лист для підтвердження email.

    Відповідь однакова незалежно від того, чи зареєстровано email.
    \f
    Args:
        body: Email користувача.
        background_tasks: Фонові задачі FastAPI для надсилання листа.
        request: Вхідний запит, з нього береться адреса застосунку.
        db: Сесія бази даних.

    Returns:
        Повідомлення для користувача.
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_email(body.email)

    if user and user.confirmed:
        return {"message": "Your email is already confirmed"}
    if user:
        background_tasks.add_task(
            send_email, user.email, user.username, request.base_url
        )
    return {"message": "Check your email for confirmation"}


@router.post("/request_password_reset")
async def request_password_reset(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Надсилає на email токен для скидання пароля.

    Відповідь однакова незалежно від того, чи зареєстровано email.
    \f
    Args:
        body: Email користувача.
        background_tasks: Фонові задачі FastAPI для надсилання листа.
        request: Вхідний запит, з нього береться адреса застосунку.
        db: Сесія бази даних.

    Returns:
        Повідомлення для користувача.
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_email(body.email)
    if user:
        background_tasks.add_task(
            send_reset_password_email, user.email, user.username, request.base_url
        )
    return {"message": "If this email is registered, a reset token has been sent"}


@router.post("/reset_password")
async def reset_password(
    body: ResetPassword,
    db: AsyncSession = Depends(get_db),
    cache: Redis = Depends(get_redis),
):
    """
    Встановлює новий пароль за токеном із листа.

    Токен одноразовий: після використання він зберігається в Redis
    і вдруге не приймається. Кеш користувача скидається.
    \f
    Args:
        body: Токен скидання та новий пароль.
        db: Сесія бази даних.
        cache: Клієнт Redis.

    Returns:
        Повідомлення про успішну зміну пароля.

    Raises:
        HTTPException: 422, якщо токен недійсний, прострочений або вже використаний;
            400, якщо користувача не знайдено.
    """
    if await cache.get(reset_token_key(body.token)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid or expired password reset token",
        )
    email = await get_email_from_reset_token(body.token)
    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    hashed_password = Hash().get_password_hash(body.password)
    await user_service.update_password(email, hashed_password)
    await cache.set(
        reset_token_key(body.token), "1", ex=RESET_TOKEN_EXPIRE_SECONDS
    )
    await cache.delete(user_cache_key(user.username))
    return {"message": "Password has been reset"}
