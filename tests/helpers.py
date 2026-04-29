from typing import Any
from unittest.mock import MagicMock

from httpx import AsyncClient


async def create_movie(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    name: str = "Test Movie",
    price: str = "9.99",
    genre_ids: list[int] | None = None,
    certification_id: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "year": 2024,
        "time": 120,
        "imdb": 7.5,
        "votes": 10000,
        "description": "A test movie.",
        "price": price,
    }
    if genre_ids is not None:
        payload["genre_ids"] = genre_ids
    if certification_id is not None:
        payload["certification_id"] = certification_id

    resp = await client.post("/movies", json=payload, headers=headers)
    data: dict[str, Any] = resp.json()
    return data


async def create_pending_order(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> dict[str, Any]:
    """Create a movie, add to cart, and create a pending order."""
    movie = await create_movie(client, moderator_headers)
    await client.post(
        "/cart/items", json={"movie_id": movie["id"]}, headers=auth_headers
    )
    resp = await client.post("/orders", headers=auth_headers)
    data: dict[str, Any] = resp.json()
    return data


def mock_stripe_session(session_id: str = "sess_test_123") -> MagicMock:
    """Return a mock Stripe Checkout Session."""
    session = MagicMock()
    session.id = session_id
    session.url = "https://checkout.stripe.com/test"
    return session


def mock_webhook_event(session_id: str) -> MagicMock:
    """Return a mock Stripe webhook event."""
    event = MagicMock()
    event.type = "checkout.session.completed"
    event.data.object = {"id": session_id}
    return event
