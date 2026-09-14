from httpx import AsyncClient


async def _create_item(client: AsyncClient, headers: dict[str, str]) -> dict:
    response = await client.post(
        "/api/v1/items/",
        json={"title": "First item", "description": "A test item"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


async def test_create_item(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    item = await _create_item(client, auth_headers)
    assert item["title"] == "First item"
    assert item["description"] == "A test item"
    assert "id" in item
    assert "owner_id" in item


async def test_create_item_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/api/v1/items/", json={"title": "No auth"})
    assert response.status_code == 401


async def test_list_own_items(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    await _create_item(client, auth_headers)
    response = await client.get("/api/v1/items/", headers=auth_headers)
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["title"] == "First item"


async def test_update_item(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    item = await _create_item(client, auth_headers)
    response = await client.patch(
        f"/api/v1/items/{item['id']}",
        json={"title": "Updated title"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated title"
    assert response.json()["description"] == "A test item"


async def test_delete_item(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    item = await _create_item(client, auth_headers)
    response = await client.delete(f"/api/v1/items/{item['id']}", headers=auth_headers)
    assert response.status_code == 204

    response = await client.get(f"/api/v1/items/{item['id']}", headers=auth_headers)
    assert response.status_code == 404


async def test_update_item_null_title_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    item = await _create_item(client, auth_headers)

    response = await client.patch(
        f"/api/v1/items/{item['id']}", json={"title": None}, headers=auth_headers
    )
    assert response.status_code == 422


async def test_update_item_null_description_clears_it(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    item = await _create_item(client, auth_headers)

    response = await client.patch(
        f"/api/v1/items/{item['id']}", json={"description": None}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["description"] is None


async def test_create_item_title_too_long(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/items/", json={"title": "t" * 256}, headers=auth_headers
    )
    assert response.status_code == 422


async def test_other_users_item_forbidden(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    item = await _create_item(client, auth_headers)

    await client.post(
        "/api/v1/users/",
        json={"email": "other@example.com", "password": "otherpass123", "name": "Other"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "other@example.com", "password": "otherpass123"},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.get(f"/api/v1/items/{item['id']}", headers=other_headers)
    assert response.status_code == 403
