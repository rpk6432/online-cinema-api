from helpers import create_movie
from httpx import AsyncClient

# Ratings


async def test_set_rating(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    resp = await client.post(
        f"/movies/{movie['id']}/rating",
        json={"score": 8},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["score"] == 8


async def test_update_rating(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(
        f"/movies/{movie['id']}/rating",
        json={"score": 5},
        headers=auth_headers,
    )
    resp = await client.post(
        f"/movies/{movie['id']}/rating",
        json={"score": 9},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["score"] == 9


async def test_set_rating_invalid_score(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    resp = await client.post(
        f"/movies/{movie['id']}/rating",
        json={"score": 11},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_set_rating_unauthorized(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    movie = await create_movie(client, moderator_headers)
    resp = await client.post(f"/movies/{movie['id']}/rating", json={"score": 8})
    assert resp.status_code == 401


async def test_set_rating_movie_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/movies/999/rating", json={"score": 8}, headers=auth_headers
    )
    assert resp.status_code == 404


async def test_get_movie_rating(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(
        f"/movies/{movie['id']}/rating",
        json={"score": 8},
        headers=auth_headers,
    )

    resp = await client.get(f"/movies/{movie['id']}/rating")
    assert resp.status_code == 200
    data = resp.json()
    assert data["average_rating"] == 8.0
    assert data["total_ratings"] == 1


async def test_get_movie_rating_empty(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    movie = await create_movie(client, moderator_headers)
    resp = await client.get(f"/movies/{movie['id']}/rating")
    assert resp.status_code == 200
    assert resp.json()["average_rating"] is None
    assert resp.json()["total_ratings"] == 0


async def test_movie_detail_includes_stats(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(
        f"/movies/{movie['id']}/rating",
        json={"score": 7},
        headers=auth_headers,
    )
    await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Great movie!"},
        headers=auth_headers,
    )

    resp = await client.get(f"/movies/{movie['id']}")
    data = resp.json()
    assert data["average_rating"] == 7.0
    assert data["total_ratings"] == 1
    assert data["total_comments"] == 1


# Comments


async def test_create_comment(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    resp = await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Nice movie!"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Nice movie!"
    assert data["parent_id"] is None
    assert "user" in data


async def test_create_reply(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    comment_resp = await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Original"},
        headers=auth_headers,
    )
    comment_id = comment_resp.json()["id"]

    resp = await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Reply", "parent_id": comment_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["parent_id"] == comment_id


async def test_reply_to_reply_flattened(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    root = await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Root"},
        headers=auth_headers,
    )
    root_id = root.json()["id"]

    reply = await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Reply", "parent_id": root_id},
        headers=auth_headers,
    )
    reply_id = reply.json()["id"]

    nested = await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Nested reply", "parent_id": reply_id},
        headers=auth_headers,
    )
    assert nested.status_code == 201
    assert nested.json()["parent_id"] == root_id


async def test_create_comment_unauthorized(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    movie = await create_movie(client, moderator_headers)
    resp = await client.post(
        f"/movies/{movie['id']}/comments", json={"content": "Hello"}
    )
    assert resp.status_code == 401


async def test_list_comments(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Comment 1"},
        headers=auth_headers,
    )
    await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Comment 2"},
        headers=auth_headers,
    )

    resp = await client.get(f"/movies/{movie['id']}/comments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_get_replies(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    root = await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Root"},
        headers=auth_headers,
    )
    root_id = root.json()["id"]
    await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Reply 1", "parent_id": root_id},
        headers=auth_headers,
    )

    resp = await client.get(f"/comments/{root_id}/replies")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["content"] == "Reply 1"


async def test_delete_comment(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    comment = await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "To delete"},
        headers=auth_headers,
    )
    comment_id = comment.json()["id"]

    resp = await client.delete(f"/comments/{comment_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_delete_comment_not_owner(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    comment = await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Not yours"},
        headers=moderator_headers,
    )
    comment_id = comment.json()["id"]

    resp = await client.delete(f"/comments/{comment_id}", headers=auth_headers)
    assert resp.status_code == 403


# Comment Likes


async def test_toggle_like(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    comment = await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Likeable"},
        headers=moderator_headers,
    )
    comment_id = comment.json()["id"]

    resp = await client.post(
        f"/comments/{comment_id}/like",
        json={"is_like": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_like"] is True


async def test_toggle_like_removes(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    comment = await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Toggle test"},
        headers=moderator_headers,
    )
    comment_id = comment.json()["id"]

    await client.post(
        f"/comments/{comment_id}/like",
        json={"is_like": True},
        headers=auth_headers,
    )
    resp = await client.post(
        f"/comments/{comment_id}/like",
        json={"is_like": True},
        headers=auth_headers,
    )
    assert resp.json()["detail"] == "Reaction removed"


async def test_get_comment_likes(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    comment = await client.post(
        f"/movies/{movie['id']}/comments",
        json={"content": "Stats test"},
        headers=moderator_headers,
    )
    comment_id = comment.json()["id"]

    await client.post(
        f"/comments/{comment_id}/like",
        json={"is_like": True},
        headers=auth_headers,
    )

    resp = await client.get(f"/comments/{comment_id}/likes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["likes"] == 1
    assert data["dislikes"] == 0
