from alembic import command
from alembic.config import Config
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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
