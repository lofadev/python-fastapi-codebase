import pytest
from httpx import AsyncClient

from app.repositories.user_repository import user_repository

USER_PAYLOAD = {"email": "test@example.com", "password": "testpass123", "name": "Test User"}
OTHER_PAYLOAD = {"email": "other@example.com", "password": "otherpass123", "name": "Other"}


async def test_create_user(client: AsyncClient) -> None:
    response = await client.post("/api/v1/users/", json=USER_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert data["is_active"] is True
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data


async def test_create_user_duplicate_email(client: AsyncClient) -> None:
    await client.post("/api/v1/users/", json=USER_PAYLOAD)
    response = await client.post("/api/v1/users/", json=USER_PAYLOAD)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


async def test_create_user_short_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/users/",
        json={"email": "short@example.com", "password": "short", "name": "Short"},
    )
    assert response.status_code == 422
async def test_update_email_to_another_users_email_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await client.post("/api/v1/users/", json=OTHER_PAYLOAD)
    me = (await client.get("/api/v1/users/me", headers=auth_headers)).json()

    response = await client.patch(
        f"/api/v1/users/{me['id']}",
        json={"email": OTHER_PAYLOAD["email"]},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


async def test_update_email_to_own_email_allowed(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    me = (await client.get("/api/v1/users/me", headers=auth_headers)).json()

    response = await client.patch(
        f"/api/v1/users/{me['id']}",
        json={"email": me["email"]},
        headers=auth_headers,
    )
    assert response.status_code == 200


async def test_create_user_duplicate_email_race(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await client.post("/api/v1/users/", json=USER_PAYLOAD)

    async def no_existing_user(*args: object, **kwargs: object) -> None:
        return None

    # Simulate a concurrent request that passed the pre-check before the first insert committed.
    monkeypatch.setattr(user_repository, "get_by_email", no_existing_user)

    response = await client.post("/api/v1/users/", json=USER_PAYLOAD)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

async def test_read_user_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/1")
    assert response.status_code == 401


async def test_update_own_user(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    me = await client.get("/api/v1/users/me", headers=auth_headers)
    user_id = me.json()["id"]

    response = await client.patch(
        f"/api/v1/users/{user_id}",
        json={"name": "Renamed"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


async def test_update_other_user_forbidden(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.patch(
        "/api/v1/users/9999",
        json={"name": "Hacker"},
        headers=auth_headers,
    )
    assert response.status_code == 403
