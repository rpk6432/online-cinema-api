from unittest.mock import AsyncMock, patch

from helpers import create_movie, mock_stripe_session, mock_webhook_event
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from crud.user import user_crud


async def test_purchase_flow(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    """Cart -> order -> checkout -> webhook -> verify PAID."""
    movie1 = await create_movie(client, moderator_headers, name="Movie A", price="5.00")
    movie2 = await create_movie(client, moderator_headers, name="Movie B", price="3.00")

    resp = await client.post(
        "/cart/items", json={"movie_id": movie1["id"]}, headers=auth_headers
    )
    assert resp.status_code == 201

    resp = await client.post(
        "/cart/items", json={"movie_id": movie2["id"]}, headers=auth_headers
    )
    assert resp.status_code == 201

    cart_resp = await client.get("/cart", headers=auth_headers)
    assert cart_resp.json()["total_items"] == 2
    assert cart_resp.json()["total_amount"] == "8.00"

    order_resp = await client.post("/orders", headers=auth_headers)
    assert order_resp.status_code == 201
    order = order_resp.json()
    assert order["status"] == "PENDING"
    assert len(order["items"]) == 2

    cart_resp = await client.get("/cart", headers=auth_headers)
    assert cart_resp.json()["total_items"] == 0

    session_id = "sess_purchase_flow"
    with patch(
        "services.stripe.stripe.checkout.Session.create_async",
        new_callable=AsyncMock,
        return_value=mock_stripe_session(session_id),
    ):
        checkout_resp = await client.post(
            f"/payments/{order['id']}/checkout", headers=auth_headers
        )
    assert checkout_resp.status_code == 201
    assert "checkout_url" in checkout_resp.json()

    with patch(
        "services.stripe.stripe.Webhook.construct_event",
        return_value=mock_webhook_event(session_id),
    ):
        webhook_resp = await client.post(
            "/payments/webhook",
            content=b"{}",
            headers={"stripe-signature": "test_sig"},
        )
    assert webhook_resp.status_code == 200

    order_resp = await client.get(f"/orders/{order['id']}", headers=auth_headers)
    assert order_resp.json()["status"] == "PAID"

    payments_resp = await client.get("/payments", headers=auth_headers)
    assert payments_resp.json()["items"][0]["status"] == "SUCCESSFUL"

    resp = await client.post(
        "/cart/items", json={"movie_id": movie1["id"]}, headers=auth_headers
    )
    assert resp.status_code == 409

    resp = await client.delete(f"/movies/{movie1['id']}", headers=moderator_headers)
    assert resp.status_code == 400


async def test_auth_lifecycle(client: AsyncClient, db: AsyncSession) -> None:
    """Register -> activate -> login -> change password -> logout."""
    email = "lifecycle@example.com"
    password = "OldPass1234"

    resp = await client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert resp.status_code == 201

    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 403

    user = await user_crud.get_by_email(db, email)
    assert user is not None
    await user_crud.update(db, user, is_active=True)

    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    tokens = resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    resp = await client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == email

    new_password = "NewPass5678"
    resp = await client.post(
        "/auth/password-change",
        json={"old_password": password, "new_password": new_password},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 401

    resp = await client.post(
        "/auth/login", json={"email": email, "password": new_password}
    )
    assert resp.status_code == 200

    new_tokens = resp.json()
    resp = await client.post(
        "/auth/logout",
        json={"refresh_token": new_tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
    )
    assert resp.status_code == 200


async def test_admin_user_management(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Admin activates a user -> promotes to moderator -> moderator creates a movie."""
    email = "newbie@example.com"
    password = "Newbie1234"

    resp = await client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert resp.status_code == 201

    resp = await client.get("/users", headers=admin_headers)
    assert resp.status_code == 200
    users = resp.json()["items"]
    target = next(u for u in users if u["email"] == email)
    assert target["is_active"] is False

    resp = await client.post(f"/users/{target['id']}/activate", headers=admin_headers)
    assert resp.status_code == 200

    resp = await client.patch(
        f"/users/{target['id']}/group",
        json={"group_name": "MODERATOR"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["group_name"] == "MODERATOR"

    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    mod_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    movie = await create_movie(client, mod_headers, name="Mod Movie")
    assert movie["name"] == "Mod Movie"


async def test_bookmark_and_interaction_flow(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    """Bookmark movie -> rate -> comment -> delete comment -> remove bookmark."""
    movie = await create_movie(client, moderator_headers, name="Interactive Movie")
    movie_id = movie["id"]

    resp = await client.post(f"/bookmarks/movies/{movie_id}", headers=auth_headers)
    assert resp.status_code == 201

    resp = await client.get("/bookmarks", headers=auth_headers)
    assert resp.json()["total"] >= 1

    resp = await client.post(
        f"/movies/{movie_id}/rating",
        json={"score": 8},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    resp = await client.get(f"/movies/{movie_id}/rating")
    assert resp.json()["average_rating"] == 8.0
    assert resp.json()["total_ratings"] == 1

    resp = await client.post(
        f"/movies/{movie_id}/comments",
        json={"content": "Great movie!"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    comment_id = resp.json()["id"]

    resp = await client.get(f"/movies/{movie_id}/comments")
    assert resp.json()["total"] == 1

    resp = await client.delete(f"/comments/{comment_id}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get(f"/movies/{movie_id}/comments")
    assert resp.json()["total"] == 0

    resp = await client.delete(f"/bookmarks/movies/{movie_id}", headers=auth_headers)
    assert resp.status_code == 204
