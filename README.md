# FastAPI Template (Python 3.13)

Production-ready FastAPI project template with async SQLAlchemy 2.0, JWT authentication, and a layered architecture (API → services → repositories → models).

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Quick Start

```bash
# Install dependencies (creates .venv automatically)
uv sync

# Configure environment
cp .env.example .env
# Edit .env — at minimum set a real SECRET_KEY

# Run the development server
uv run uvicorn app.main:app --reload
```

The API is now available at http://127.0.0.1:8000 — interactive docs at http://127.0.0.1:8000/docs.

## Project Structure

```
app/
├── api/                    # API layer
│   ├── dependencies.py     # Shared dependencies (DB session, current user)
│   └── v1/
│       ├── endpoints/      # Route handlers (auth, users, items)
│       └── router.py       # v1 router aggregation
├── core/                   # Core configuration
│   ├── config.py           # Settings (pydantic-settings, reads .env)
│   ├── database.py         # Async engine, session, Base
│   └── security.py         # JWT creation, password hashing (bcrypt)
├── models/                 # SQLAlchemy 2.0 ORM models (Mapped / mapped_column)
├── schemas/                # Pydantic v2 schemas (request/response)
├── services/               # Business logic
├── repositories/           # Data access (generic BaseRepository, PEP 695 generics)
└── main.py                 # Application entry point (lifespan, CORS, routers)
tests/                      # Async test suite (pytest-asyncio + httpx)
```

## API Overview

| Method | Path                    | Auth | Description                    |
|--------|-------------------------|------|--------------------------------|
| POST   | `/api/v1/users/`        | No   | Register a new user            |
| POST   | `/api/v1/auth/login`    | No   | Login (OAuth2 form), get JWT   |
| GET    | `/api/v1/users/me`      | Yes  | Current user profile           |
| GET    | `/api/v1/users/{id}`    | Yes  | Get user by ID                 |
| PATCH  | `/api/v1/users/{id}`    | Yes  | Update own profile             |
| DELETE | `/api/v1/users/{id}`    | Yes  | Delete own account             |
| POST   | `/api/v1/items/`        | Yes  | Create an item                 |
| GET    | `/api/v1/items/`        | Yes  | List own items                 |
| GET    | `/api/v1/items/{id}`    | Yes  | Get own item                   |
| PATCH  | `/api/v1/items/{id}`    | Yes  | Update own item                |
| DELETE | `/api/v1/items/{id}`    | Yes  | Delete own item                |
| GET    | `/health`               | No   | Health check                   |

## Testing

Tests run against the `app_test` PostgreSQL database from `docker-compose.yml`, through the real `get_db` dependency (real commits):

```bash
docker compose up -d --wait
uv run pytest
```

- The schema is rebuilt with Alembic (`downgrade base` → `upgrade head`) once per test session, and every table is truncated after each test.
- Point the suite at another database with `TEST_DATABASE_URL`. It refuses to run unless the database name ends with `_test`, because it truncates every table.

## Configuration

All settings live in `app/core/config.py` and are loaded from environment variables or `.env`:

| Variable                      | Default                                           | Description                          |
|-------------------------------|---------------------------------------------------|--------------------------------------|
| `DATABASE_URL`                | `postgresql+asyncpg://app:app@localhost:5433/app` | Async SQLAlchemy connection string   |
| `SECRET_KEY`                  | _(required)_                                      | JWT signing key (min. 32 characters) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30`                                              | Access token lifetime                |
| `CORS_ORIGINS`                | `[]`                                              | Allowed CORS origins (JSON array)    |

## Python 3.13 Notes

- Uses **PEP 695 generics** (`class BaseRepository[ModelT, CreateT, UpdateT]`) — no `TypeVar` boilerplate.
- Uses **PyJWT + bcrypt** instead of `python-jose`/`passlib` (passlib depends on the stdlib `crypt` module, removed in Python 3.13).
- SQLAlchemy 2.0 typed ORM (`Mapped` / `mapped_column`) and Pydantic v2 throughout.

## Production Checklist

- Set a strong `SECRET_KEY` (e.g. `python -c "import secrets; print(secrets.token_hex(32))"`).
- Restrict `CORS_ORIGINS` to your frontend origins.
- Replace the startup `create_all` in `app/main.py` with [Alembic](https://alembic.sqlalchemy.org/) migrations.
