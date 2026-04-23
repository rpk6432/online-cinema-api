from helpers import create_movie
from httpx import AsyncClient


async def test_create_order(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )

    resp = await client.post("/orders", headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "PENDING"
    assert len(data["items"]) == 1
    assert data["items"][0]["price_at_order"] == str(movie["price"])
    assert data["total_amount"] == str(movie["price"])


async def test_create_order_empty_cart(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post("/orders", headers=auth_headers)
    assert resp.status_code == 400


async def test_create_order_clears_cart(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )
    await client.post("/orders", headers=auth_headers)

    cart = await client.get("/cart", headers=auth_headers)
    assert cart.json()["total_items"] == 0


async def test_create_order_unauthorized(client: AsyncClient) -> None:
    resp = await client.post("/orders")
    assert resp.status_code == 401


async def test_list_orders(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )
    await client.post("/orders", headers=auth_headers)

    resp = await client.get("/orders", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["total_items"] == 1


async def test_list_orders_filter_by_status(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )
    await client.post("/orders", headers=auth_headers)

    resp = await client.get(
        "/orders", params={"status": "CANCELED"}, headers=auth_headers
    )
    assert resp.json()["total"] == 0

    resp = await client.get(
        "/orders", params={"status": "PENDING"}, headers=auth_headers
    )
    assert resp.json()["total"] == 1


async def test_get_order(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )
    create_resp = await client.post("/orders", headers=auth_headers)
    order_id = create_resp.json()["id"]

    resp = await client.get(f"/orders/{order_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id
    assert len(resp.json()["items"]) == 1


async def test_get_order_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get("/orders/999", headers=auth_headers)
    assert resp.status_code == 404


async def test_cancel_order(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )
    create_resp = await client.post("/orders", headers=auth_headers)
    order_id = create_resp.json()["id"]

    resp = await client.post(f"/orders/{order_id}/cancel", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELED"


async def test_cancel_already_canceled(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )
    create_resp = await client.post("/orders", headers=auth_headers)
    order_id = create_resp.json()["id"]

    await client.post(f"/orders/{order_id}/cancel", headers=auth_headers)
    resp = await client.post(f"/orders/{order_id}/cancel", headers=auth_headers)
    assert resp.status_code == 400


async def test_price_snapshot(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers, price="9.99")
    await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )
    create_resp = await client.post("/orders", headers=auth_headers)
    assert create_resp.json()["items"][0]["price_at_order"] == "9.99"


async def test_add_to_cart_movie_in_pending_order(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )
    await client.post("/orders", headers=auth_headers)

    resp = await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )
    assert resp.status_code == 409
    assert "pending" in resp.json()["detail"].lower()
