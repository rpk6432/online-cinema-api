from helpers import create_movie
from httpx import AsyncClient


async def test_add_bookmark(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    resp = await client.post(f"/bookmarks/movies/{movie['id']}", headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["movie_id"] == movie["id"]


async def test_add_bookmark_duplicate(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(f"/bookmarks/movies/{movie['id']}", headers=auth_headers)
    resp = await client.post(f"/bookmarks/movies/{movie['id']}", headers=auth_headers)
    assert resp.status_code == 409


async def test_add_bookmark_movie_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post("/bookmarks/movies/999", headers=auth_headers)
    assert resp.status_code == 404


async def test_add_bookmark_unauthorized(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    movie = await create_movie(client, moderator_headers)
    resp = await client.post(f"/bookmarks/movies/{movie['id']}")
    assert resp.status_code == 401


async def test_list_bookmarks(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    m1 = await create_movie(client, moderator_headers, name="Movie 1")
    m2 = await create_movie(client, moderator_headers, name="Movie 2")
    await client.post(f"/bookmarks/movies/{m1['id']}", headers=auth_headers)
    await client.post(f"/bookmarks/movies/{m2['id']}", headers=auth_headers)

    resp = await client.get("/bookmarks", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert "movie" in data["items"][0]


async def test_list_bookmarks_search(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    m1 = await create_movie(client, moderator_headers, name="The Matrix")
    m2 = await create_movie(client, moderator_headers, name="Inception")
    await client.post(f"/bookmarks/movies/{m1['id']}", headers=auth_headers)
    await client.post(f"/bookmarks/movies/{m2['id']}", headers=auth_headers)

    resp = await client.get(
        "/bookmarks", params={"search": "matrix"}, headers=auth_headers
    )
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["movie"]["name"] == "The Matrix"


async def test_remove_bookmark(
    client: AsyncClient,
    moderator_headers: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    movie = await create_movie(client, moderator_headers)
    await client.post(f"/bookmarks/movies/{movie['id']}", headers=auth_headers)

    resp = await client.delete(f"/bookmarks/movies/{movie['id']}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get("/bookmarks", headers=auth_headers)
    assert resp.json()["total"] == 0


async def test_remove_bookmark_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.delete("/bookmarks/movies/999", headers=auth_headers)
    assert resp.status_code == 404
