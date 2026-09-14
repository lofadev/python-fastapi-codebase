from httpx import AsyncClient

USER_PAYLOAD = {"email": "login@example.com", "password": "loginpass123", "name": "Login User"}


async def test_login_and_read_me(client: AsyncClient) -> None:
    await client.post("/api/v1/users/", json=USER_PAYLOAD)

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": USER_PAYLOAD["email"], "password": USER_PAYLOAD["password"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"

    me = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == USER_PAYLOAD["email"]


async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post("/api/v1/users/", json=USER_PAYLOAD)

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": USER_PAYLOAD["email"], "password": "wrongpassword"},
    )
    assert response.status_code == 401


async def test_login_unknown_user(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@example.com", "password": "whatever123"},
    )
    assert response.status_code == 401


async def test_invalid_token_rejected(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert response.status_code == 401
