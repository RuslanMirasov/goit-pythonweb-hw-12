"""Маршрути для роботи з контактами поточного користувача."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.schemas import ContactModel, ContactResponse, User
from src.services.auth import get_current_user
from src.services.contacts import ContactService

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/", response_model=list[ContactResponse])
async def read_contacts(
    first_name: str | None = Query(default=None),
    last_name: str | None = Query(default=None),
    email: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Повертає список контактів з пошуком і пагінацією.

    Пошук за іменем, прізвищем та email знаходить часткові збіги без урахування регістру.
    \f
    Args:
        first_name: Частина імені для пошуку.
        last_name: Частина прізвища для пошуку.
        email: Частина email для пошуку.
        skip: Скільки контактів пропустити.
        limit: Максимальна кількість контактів у відповіді.
        db: Сесія бази даних.
        user: Поточний користувач.

    Returns:
        Список контактів поточного користувача.
    """
    return await ContactService(db).get_contacts(
        skip, limit, user, first_name, last_name, email
    )


@router.get("/birthdays", response_model=list[ContactResponse])
async def read_upcoming_birthdays(
    days: int = Query(default=7, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Повертає контакти з днями народження на найближчі дні (за замовчуванням 7).
    \f
    Args:
        days: Кількість днів уперед.
        db: Сесія бази даних.
        user: Поточний користувач.

    Returns:
        Список контактів, відсортований за найближчою датою.
    """
    return await ContactService(db).get_upcoming_birthdays(days, user)


@router.get("/{contact_id}", response_model=ContactResponse)
async def read_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Повертає контакт за ідентифікатором.
    \f
    Args:
        contact_id: Ідентифікатор контакту.
        db: Сесія бази даних.
        user: Поточний користувач.

    Returns:
        Контакт.

    Raises:
        HTTPException: 404, якщо контакт не знайдено або він належить іншому користувачу.
    """
    contact = await ContactService(db).get_contact(contact_id, user)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return contact


@router.post(
    "/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED
)
async def create_contact(
    body: ContactModel,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Створює новий контакт.
    \f
    Args:
        body: Дані контакту.
        db: Сесія бази даних.
        user: Поточний користувач.

    Returns:
        Створений контакт.

    Raises:
        HTTPException: 409, якщо контакт з таким email уже існує.
    """
    contact_service = ContactService(db)
    if await contact_service.get_contact_by_email(body.email, user):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contact with this email already exists",
        )
    return await contact_service.create_contact(body, user)


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    body: ContactModel,
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Повністю оновлює контакт.
    \f
    Args:
        body: Нові дані контакту.
        contact_id: Ідентифікатор контакту.
        db: Сесія бази даних.
        user: Поточний користувач.

    Returns:
        Оновлений контакт.

    Raises:
        HTTPException: 409, якщо email зайнятий іншим контактом; 404, якщо контакт не знайдено.
    """
    contact_service = ContactService(db)
    existing = await contact_service.get_contact_by_email(body.email, user)
    if existing and existing.id != contact_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contact with this email already exists",
        )
    contact = await contact_service.update_contact(contact_id, body, user)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return contact


@router.delete("/{contact_id}", response_model=ContactResponse)
async def remove_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Видаляє контакт.
    \f
    Args:
        contact_id: Ідентифікатор контакту.
        db: Сесія бази даних.
        user: Поточний користувач.

    Returns:
        Видалений контакт.

    Raises:
        HTTPException: 404, якщо контакт не знайдено.
    """
    contact = await ContactService(db).remove_contact(contact_id, user)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return contact
