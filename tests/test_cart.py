from unittest.mock import AsyncMock, patch

from helpers import create_movie
from httpx import AsyncClient


async def test_get_empty_cart(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get("/cart", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total_items"] == 0
    assert data["total_amount"] == "0.00"


async def test_add_item(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    resp = await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )
    assert resp.status_code == 201
    assert resp.json()["movie"]["id"] == movie["id"]


async def test_add_item_duplicate(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )
    resp = await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )
    assert resp.status_code == 409


async def test_add_item_movie_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/cart/items", json={"movie_id": 999}, headers=auth_headers
    )
    assert resp.status_code == 404


async def test_add_item_unauthorized(client: AsyncClient) -> None:
    resp = await client.post("/cart/items", json={"movie_id": 1})
    assert resp.status_code == 401


async def test_add_item_already_purchased(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    with patch(
        "routes.cart.cart_crud.is_movie_purchased",
        new_callable=AsyncMock,
        return_value=True,
    ):
        resp = await client.post(
            "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
        )
    assert resp.status_code == 409
    assert "purchased" in resp.json()["detail"].lower()


async def test_get_cart_with_items(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    m1 = await create_movie(client, moderator_headers, name="Movie A")
    m2 = await create_movie(client, moderator_headers, name="Movie B")
    await client.post("/cart/items", json={"movie_id": m1["id"]}, headers=auth_headers)
    await client.post("/cart/items", json={"movie_id": m2["id"]}, headers=auth_headers)

    resp = await client.get("/cart", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_items"] == 2
    assert len(data["items"]) == 2
    assert float(data["total_amount"]) == 19.98


async def test_remove_item(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )

    resp = await client.delete(f"/cart/items/{movie['id']}", headers=auth_headers)
    assert resp.status_code == 204

    cart = await client.get("/cart", headers=auth_headers)
    assert cart.json()["total_items"] == 0


async def test_remove_item_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.delete("/cart/items/999", headers=auth_headers)
    assert resp.status_code == 404


async def test_clear_cart(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    m1 = await create_movie(client, moderator_headers, name="Clear A")
    m2 = await create_movie(client, moderator_headers, name="Clear B")
    await client.post("/cart/items", json={"movie_id": m1["id"]}, headers=auth_headers)
    await client.post("/cart/items", json={"movie_id": m2["id"]}, headers=auth_headers)

    resp = await client.delete("/cart/clear", headers=auth_headers)
    assert resp.status_code == 204

    cart = await client.get("/cart", headers=auth_headers)
    assert cart.json()["total_items"] == 0
