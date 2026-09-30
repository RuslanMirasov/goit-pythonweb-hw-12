# Фінальне домашнє завдання

## Запуск

Створіть файл `.env`, заповнивши його за прикладом `.env.example` своїми значеннями.

```bash
POSTGRES_DB=hw12
POSTGRES_USER=postgres
POSTGRES_PASSWORD=123qweQ
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

MAIL_USERNAME=example@gmail.com
MAIL_PASSWORD=app_password
MAIL_FROM=example@gmail.com
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com

CLD_NAME=cloud_name
CLD_API_KEY=api_key
CLD_API_SECRET=api_secret

JWT_SECRET=your_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_SECONDS=3600

REDIS_HOST=localhost
REDIS_PORT=6379
```

- `JWT_SECRET` — випадковий рядок, наприклад: `python -c "import secrets; print(secrets.token_hex(32))"`
- `MAIL_*` — SMTP-скринька для листів підтвердження та скидання пароля. Для Gmail потрібен
  [пароль застосунку](https://myaccount.google.com/apppasswords) (двоетапна автентифікація має бути увімкнена).
- `CLD_*` — ключі з консолі [Cloudinary](https://console.cloudinary.com/) → Settings → API Keys.

Команди:

```bash
docker compose up -d --build                  # піднімає Postgres, Redis і контейнер застосунку
docker compose exec app alembic upgrade head  # застосувати міграції, створити таблиці users і contacts
```

Swagger документація: http://localhost:8000/docs

### Роль адміністратора

Після реєстрації користувач отримує роль `user`. Змінювати аватар може лише `admin`. Призначити роль:

```bash
docker compose exec db sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB -c "UPDATE users SET role = '"'"'ADMIN'"'"' WHERE username = '"'"'your_username'"'"'"'
docker compose exec redis redis-cli del user:your_username   # скинути кеш користувача
```

## Структура проєкту

```
├── main.py                        # Точка входу: FastAPI, CORS, обробник 429, підключення роутерів
├── src/
│   ├── api/                       # Маршрути (presentation layer)
│   │   ├── auth.py                #   реєстрація, вхід, підтвердження email, скидання пароля
│   │   ├── contacts.py            #   CRUD контактів, пошук, дні народження
│   │   ├── users.py               #   /me з лімітом запитів, аватар (лише admin)
│   │   └── utils.py               #   healthchecker
│   ├── services/                  # Бізнес-логіка
│   │   ├── auth.py                #   паролі, JWT, кеш користувача в Redis, ролі
│   │   ├── contacts.py            #   сервіс контактів
│   │   ├── users.py               #   сервіс користувачів, аватар Gravatar
│   │   ├── email.py               #   листи підтвердження та скидання пароля
│   │   ├── upload_file.py         #   завантаження аватара в Cloudinary
│   │   └── templates/             #   HTML-шаблони листів
│   ├── repository/                # Доступ до даних (запити до бази)
│   │   ├── contacts.py
│   │   └── users.py
│   ├── database/
│   │   ├── models.py              #   ORM-моделі User, Contact, ролі UserRole
│   │   ├── db.py                  #   асинхронне підключення до PostgreSQL
│   │   └── redis.py               #   підключення до Redis
│   ├── conf/
│   │   └── config.py              #   налаштування з .env (pydantic-settings)
│   └── schemas.py                 # Pydantic-схеми запитів і відповідей
├── tests/
│   ├── unit/                      # Модульні тести: репозиторії, сервіси, підключення
│   └── integration/               # Інтеграційні тести маршрутів, conftest.py з фікстурами
├── migrations/                    # Міграції Alembic
├── docs/                          # Документація Sphinx: conf.py, index.rst
├── docker-compose.yaml            # Сервіси db (PostgreSQL), redis, app
├── docker-compose.override.yaml   # Режим розробки: --reload і монтування коду
├── Dockerfile
├── alembic.ini
├── pyproject.toml                 # Налаштування pytest і coverage
├── requirements.txt
└── .env.example                   # Приклад змінних середовища
```

## Тести

Модульні тести (`tests/unit`) перевіряють репозиторії та сервіси з моками сесії бази даних. Інтеграційні тести
(`tests/integration`) перевіряють маршрути через `TestClient` на SQLite в пам'яті. Пошта, Cloudinary та Redis у
тестах підмінені, тому PostgreSQL і запущені контейнери не потрібні.

```bash
pytest -v                                     # запустити всі тести
pytest --cov=src --cov-report=term-missing    # покриття в консолі
pytest --cov=src --cov-report=html            # покриття в HTML: htmlcov/index.html
```

## Документація Sphinx

Документація генерується з docstrings модулів застосунку.

```bash
sphinx-build -M html docs docs/_build
```

Результат: `docs/_build/html/index.html`.

## Ендпоінти

| Метод  | URL                                 | Опис                                                         | Авторизація |
| ------ | ----------------------------------- | ------------------------------------------------------------ | ----------- |
| GET    | `/api/healthchecker`                | Перевірка підключення до бази даних                          |             |
| POST   | `/api/auth/register`                | Реєстрація, `201`; `409`, якщо email або ім'я зайняті        |             |
| POST   | `/api/auth/login`                   | Вхід (form: `username`, `password`), повертає `access_token` |             |
| GET    | `/api/auth/confirmed_email/{token}` | Підтвердження email за посиланням з листа                    |             |
| POST   | `/api/auth/request_email`           | Повторно надіслати лист підтвердження                        |             |
| POST   | `/api/auth/request_password_reset`  | Надіслати на email токен для скидання пароля                 |             |
| POST   | `/api/auth/reset_password`          | Встановити новий пароль за одноразовим токеном               |             |
| GET    | `/api/users/me`                     | Поточний користувач, не більше 10 запитів на хвилину         | ✅          |
| PATCH  | `/api/users/avatar`                 | Оновити аватар (Cloudinary), лише для `admin`                | ✅ admin    |
| GET    | `/api/contacts/`                    | Список контактів, пошук: `first_name`, `last_name`, `email`  | ✅          |
| GET    | `/api/contacts/birthdays`           | Дні народження на найближчі 7 днів (`days`)                  | ✅          |
| GET    | `/api/contacts/{contact_id}`        | Контакт за ідентифікатором                                   | ✅          |
| POST   | `/api/contacts/`                    | Створити контакт, `201`                                      | ✅          |
| PUT    | `/api/contacts/{contact_id}`        | Оновити контакт                                              | ✅          |
| DELETE | `/api/contacts/{contact_id}`        | Видалити контакт                                             | ✅          |
