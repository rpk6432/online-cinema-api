from unittest.mock import AsyncMock, MagicMock, patch

import stripe
from helpers import create_movie, create_pending_order
from httpx import AsyncClient


def _mock_stripe_session(session_id: str = "sess_test_123") -> MagicMock:
    """Return a mock Stripe Checkout Session."""
    session = MagicMock()
    session.id = session_id
    session.url = "https://checkout.stripe.com/test"
    return session


async def test_checkout(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    order = await create_pending_order(client, moderator_headers, auth_headers)

    with patch(
        "services.stripe.stripe.checkout.Session.create_async",
        new_callable=AsyncMock,
        return_value=_mock_stripe_session(),
    ):
        resp = await client.post(
            f"/payments/{order['id']}/checkout", headers=auth_headers
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["checkout_url"] == "https://checkout.stripe.com/test"
    assert "payment_id" in data


async def test_checkout_non_pending_order(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    order = await create_pending_order(client, moderator_headers, auth_headers)
    await client.post(f"/orders/{order['id']}/cancel", headers=auth_headers)

    resp = await client.post(f"/payments/{order['id']}/checkout", headers=auth_headers)
    assert resp.status_code == 400


async def test_checkout_order_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post("/payments/999/checkout", headers=auth_headers)
    assert resp.status_code == 404


async def test_checkout_unauthorized(client: AsyncClient) -> None:
    resp = await client.post("/payments/1/checkout")
    assert resp.status_code == 401


async def test_webhook_success(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    order = await create_pending_order(client, moderator_headers, auth_headers)
    session_id = "sess_webhook_test"

    with patch(
        "services.stripe.stripe.checkout.Session.create_async",
        new_callable=AsyncMock,
        return_value=_mock_stripe_session(session_id),
    ):
        await client.post(f"/payments/{order['id']}/checkout", headers=auth_headers)

    mock_event = MagicMock()
    mock_event.type = "checkout.session.completed"
    mock_event.data.object = {"id": session_id}

    with patch(
        "services.stripe.stripe.Webhook.construct_event",
        return_value=mock_event,
    ):
        resp = await client.post(
            "/payments/webhook",
            content=b"{}",
            headers={"stripe-signature": "test_sig"},
        )

    assert resp.status_code == 200

    order_resp = await client.get(f"/orders/{order['id']}", headers=auth_headers)
    assert order_resp.json()["status"] == "PAID"

    payments_resp = await client.get("/payments", headers=auth_headers)
    payment = payments_resp.json()["items"][0]
    assert payment["status"] == "SUCCESSFUL"


async def test_webhook_invalid_signature(client: AsyncClient) -> None:

    with patch(
        "services.stripe.stripe.Webhook.construct_event",
        side_effect=stripe.SignatureVerificationError("bad", "sig"),  # type: ignore[no-untyped-call]
    ):
        resp = await client.post(
            "/payments/webhook",
            content=b"{}",
            headers={"stripe-signature": "bad_sig"},
        )

    assert resp.status_code == 400


async def test_list_payments(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    order = await create_pending_order(client, moderator_headers, auth_headers)

    with patch(
        "services.stripe.stripe.checkout.Session.create_async",
        new_callable=AsyncMock,
        return_value=_mock_stripe_session(),
    ):
        await client.post(f"/payments/{order['id']}/checkout", headers=auth_headers)

    resp = await client.get("/payments", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["items"][0]["order_id"] == order["id"]


async def test_retry_checkout_cancels_previous(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    order = await create_pending_order(client, moderator_headers, auth_headers)

    with patch(
        "services.stripe.stripe.checkout.Session.create_async",
        new_callable=AsyncMock,
        return_value=_mock_stripe_session("sess_first"),
    ):
        first = await client.post(
            f"/payments/{order['id']}/checkout", headers=auth_headers
        )

    with patch(
        "services.stripe.stripe.checkout.Session.create_async",
        new_callable=AsyncMock,
        return_value=_mock_stripe_session("sess_second"),
    ):
        second = await client.post(
            f"/payments/{order['id']}/checkout", headers=auth_headers
        )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["payment_id"] != second.json()["payment_id"]


async def test_cart_blocks_paid_movie(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )
    order_resp = await client.post("/orders", headers=auth_headers)
    order = order_resp.json()
    session_id = "sess_paid_test"

    with patch(
        "services.stripe.stripe.checkout.Session.create_async",
        new_callable=AsyncMock,
        return_value=_mock_stripe_session(session_id),
    ):
        await client.post(f"/payments/{order['id']}/checkout", headers=auth_headers)

    mock_event = MagicMock()
    mock_event.type = "checkout.session.completed"
    mock_event.data.object = {"id": session_id}

    with patch(
        "services.stripe.stripe.Webhook.construct_event",
        return_value=mock_event,
    ):
        await client.post(
            "/payments/webhook",
            content=b"{}",
            headers={"stripe-signature": "test_sig"},
        )

    resp = await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )
    assert resp.status_code == 409
    assert "purchased" in resp.json()["detail"].lower()
