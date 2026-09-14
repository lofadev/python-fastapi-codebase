import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.item_repository import item_repository
from app.repositories.user_repository import user_repository

USER_PAYLOAD = {"email": "test@example.com", "password": "testpass123", "name": "Test User"}
OTHER_PAYLOAD = {"email": "other@example.com", "password": "otherpass123", "name": "Other"}
VIETNAMESE_CHAR = chr(0x1EC7)  # "ệ": 3 bytes in UTF-8


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


async def test_delete_user(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    me = (await client.get("/api/v1/users/me", headers=auth_headers)).json()
    response = await client.delete(f"/api/v1/users/{me['id']}", headers=auth_headers)
    assert response.status_code == 204


async def test_read_other_user_forbidden(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    other = await client.post("/api/v1/users/", json=OTHER_PAYLOAD)

    response = await client.get(f"/api/v1/users/{other.json()['id']}", headers=auth_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized"


async def test_read_own_user(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    me = (await client.get("/api/v1/users/me", headers=auth_headers)).json()

    response = await client.get(f"/api/v1/users/{me['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == me


async def test_delete_own_user_removes_their_items(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
) -> None:
    me = (await client.get("/api/v1/users/me", headers=auth_headers)).json()
    await client.post("/api/v1/items/", json={"title": "Owned"}, headers=auth_headers)

    response = await client.delete(f"/api/v1/users/{me['id']}", headers=auth_headers)
    assert response.status_code == 204

    remaining = await item_repository.get_multi_by_owner(db_session, me["id"])
    assert list(remaining) == []


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


@pytest.mark.parametrize("field", ["name", "email", "password"])
async def test_update_user_null_field_rejected(
    client: AsyncClient, auth_headers: dict[str, str], field: str
) -> None:
    me = (await client.get("/api/v1/users/me", headers=auth_headers)).json()

    response = await client.patch(
        f"/api/v1/users/{me['id']}", json={field: None}, headers=auth_headers
    )
    assert response.status_code == 422


async def test_create_user_name_too_long(client: AsyncClient) -> None:
    response = await client.post("/api/v1/users/", json={**USER_PAYLOAD, "name": "n" * 256})
    assert response.status_code == 422


async def test_password_over_72_bytes_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    password = VIETNAMESE_CHAR * 30  # 30 characters, 90 bytes

    create = await client.post(
        "/api/v1/users/",
        json={"email": "vn@example.com", "password": password, "name": "VN"},
    )
    assert create.status_code == 422

    me = (await client.get("/api/v1/users/me", headers=auth_headers)).json()
    update = await client.patch(
        f"/api/v1/users/{me['id']}", json={"password": password}, headers=auth_headers
    )
    assert update.status_code == 422


async def test_password_of_exactly_72_bytes_accepted(client: AsyncClient) -> None:
    password = VIETNAMESE_CHAR * 24  # 24 characters, 72 bytes
    payload = {"email": "vn72@example.com", "password": password, "name": "VN"}

    create = await client.post("/api/v1/users/", json=payload)
    assert create.status_code == 201

    login = await client.post(
        "/api/v1/auth/login", data={"username": payload["email"], "password": password}
    )
    assert login.status_code == 200


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


async def test_create_read_update_delete(client: AsyncClient) -> None:
    # 1. Create a user
    payload = {"email": "e2e@example.com", "password": "e2epassword", "name": "E2E"}
    create_response = await client.post("/api/v1/users/", json=payload)
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    # 2. Login
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Read profile
    read_response = await client.get("/api/v1/users/me", headers=headers)
    assert read_response.status_code == 200
    assert read_response.json()["name"] == "E2E"

    # 4. Update profile
    update_response = await client.patch(
        f"/api/v1/users/{user_id}", json={"name": "E2E Updated"}, headers=headers
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "E2E Updated"

    # 5. Delete profile
    delete_response = await client.delete(f"/api/v1/users/{user_id}", headers=headers)
    assert delete_response.status_code == 204

    # 6. Verify deletion (login fails)
    login_again = await client.post(
        "/api/v1/auth/login",
        data={"username": payload["email"], "password": payload["password"]},
    )
    assert login_again.status_code == 401
