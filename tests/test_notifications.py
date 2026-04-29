from helpers import create_movie
from httpx import AsyncClient


async def _trigger_notification(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    """Create a comment and reply to trigger a COMMENT_REPLY notification."""
    movie = await create_movie(client, moderator_headers)
    comment = await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Original comment"},
        headers=moderator_headers,
    )
    comment_id = comment.json()["id"]
    await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Reply", "parent_id": comment_id},
        headers=auth_headers,
    )


async def test_list_notifications_empty(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get("/notifications", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_notification_on_reply(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    await _trigger_notification(client, moderator_headers, auth_headers)

    resp = await client.get("/notifications", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["type"] == "COMMENT_REPLY"
    assert data["items"][0]["is_read"] is False


async def test_mark_notification_read(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    await _trigger_notification(client, moderator_headers, auth_headers)

    notifications = await client.get("/notifications", headers=moderator_headers)
    notif_id = notifications.json()["items"][0]["id"]

    resp = await client.patch(
        f"/notifications/{notif_id}/read", headers=moderator_headers
    )
    assert resp.status_code == 200
    assert resp.json()["is_read"] is True


async def test_mark_notification_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.patch("/notifications/999/read", headers=auth_headers)
    assert resp.status_code == 404


async def test_list_notifications_unread_only(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    await _trigger_notification(client, moderator_headers, auth_headers)

    notifications = await client.get("/notifications", headers=moderator_headers)
    notif_id = notifications.json()["items"][0]["id"]
    await client.patch(f"/notifications/{notif_id}/read", headers=moderator_headers)

    resp = await client.get(
        "/notifications",
        params={"unread_only": True},
        headers=moderator_headers,
    )
    assert resp.json()["total"] == 0


async def test_notification_unauthorized(client: AsyncClient) -> None:
    resp = await client.get("/notifications")
    assert resp.status_code == 401


async def test_notification_on_like(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    comment = await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Like me"},
        headers=moderator_headers,
    )
    comment_id = comment.json()["id"]

    await client.post(
        f"/comments/{comment_id}/like",
        json={"is_like": True},
        headers=auth_headers,
    )

    resp = await client.get("/notifications", headers=moderator_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["type"] == "COMMENT_LIKE"
