import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.repositories.user_repository import user_repository


async def test_api_writes_are_committed(client: AsyncClient, db_session: AsyncSession) -> None:
    response = await client.post(
        "/api/v1/users/",
        json={"email": "persist@example.com", "password": "persist123", "name": "Persist"},
    )
    assert response.status_code == 201

    user = await user_repository.get_by_email(db_session, "persist@example.com")
    assert user is not None


def test_migrations_match_models(alembic_config: Config) -> None:
    command.check(alembic_config)


async def test_failed_commit_returns_500(monkeypatch: pytest.MonkeyPatch) -> None:
    async def failing_commit(self: AsyncSession) -> None:
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(AsyncSession, "commit", failing_commit)

    # The app must report the failure instead of a 201 that was sent before committing.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.post(
            "/api/v1/users/",
            json={"email": "commit@example.com", "password": "commit123", "name": "Commit"},
        )

    assert response.status_code == 500
