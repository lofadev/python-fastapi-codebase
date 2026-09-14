import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

# Point the app at the test database before any app module reads settings.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5433/app_test"
)
os.environ["SECRET_KEY"] = "test-only-secret-key-with-at-least-32-characters"

_test_database_url = make_url(os.environ["DATABASE_URL"])
if not (_test_database_url.database or "").endswith("_test"):
    shown_url = _test_database_url.render_as_string(hide_password=True)
    pytest.exit(
        f"Refusing to run tests against {shown_url}: the database name must end with '_test' "
        "because tests truncate every table."
    )

from app.core.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.main import app  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    return Config(
        file_=PROJECT_ROOT / "alembic.ini",
        toml_file=PROJECT_ROOT / "pyproject.toml",
    )


@pytest.fixture(scope="session", autouse=True)
def _migrated_schema(alembic_config: Config) -> None:
    """Rebuild the schema from migrations once per test session."""
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")


@pytest_asyncio.fixture(autouse=True)
async def _clean_database() -> AsyncGenerator[None]:
    """Truncate every table after each test and drop connections bound to its event loop."""
    yield
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """A session independent of request sessions; commit anything you arrange with it."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a user and return Bearer auth headers for them."""
    await client.post(
        "/api/v1/users/",
        json={"email": "owner@example.com", "password": "secret123", "name": "Owner"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "owner@example.com", "password": "secret123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
