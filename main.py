"""Точка входу REST API застосунку для керування контактами."""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse

from src.api import auth, contacts, users, utils

app = FastAPI(
    title="Contacts API",
    description=(
        "Сервіс для зберігання та керування особистими контактами.\n\n"
        "Реєстрація з підтвердженням email, вхід за JWT-токеном і скидання пароля "
        "через лист. Пошук контактів та нагадування про найближчі дні народження. "
        "Ролі user / admin, кешування користувача в Redis, аватари в Cloudinary."
    ),
    version="1.0.0",
)

origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Повертає відповідь 429, коли перевищено ліміт запитів.

    Args:
        request: Вхідний запит.
        exc: Виняток slowapi про перевищення ліміту.

    Returns:
        JSON-відповідь зі статусом 429.
    """
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


app.include_router(utils.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(contacts.router, prefix="/api")
