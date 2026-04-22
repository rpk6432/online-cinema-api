from decimal import Decimal

from helpers import create_movie
from httpx import AsyncClient


async def _create_genre(
    client: AsyncClient, headers: dict[str, str], name: str = "Action"
) -> int:
    resp = await client.post("/genres", json={"name": name}, headers=headers)
    return int(resp.json()["id"])


async def _create_certification(
    client: AsyncClient, headers: dict[str, str], name: str = "PG-13"
) -> int:
    resp = await client.post("/certifications", json={"name": name}, headers=headers)
    return int(resp.json()["id"])


async def testcreate_movie(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    data = await create_movie(client, moderator_headers)
    assert data["name"] == "Test Movie"
    assert data["year"] == 2024
    assert Decimal(data["price"]) == Decimal("9.99")


async def testcreate_movie_with_relationships(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    genre_id = await _create_genre(client, moderator_headers)
    cert_id = await _create_certification(client, moderator_headers)

    data = await create_movie(
        client,
        moderator_headers,
        genre_ids=[genre_id],
        certification_id=cert_id,
    )
    assert len(data["genres"]) == 1
    assert data["genres"][0]["name"] == "Action"
    assert data["certification"]["name"] == "PG-13"


async def testcreate_movie_forbidden(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/movies",
        json={
            "name": "Movie",
            "year": 2024,
            "time": 120,
            "imdb": 7.0,
            "votes": 100,
            "description": "Desc",
            "price": "9.99",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 403


async def test_get_movie(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    created = await create_movie(client, moderator_headers)
    movie_id = created["id"]

    resp = await client.get(f"/movies/{movie_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Movie"
    assert "description" in resp.json()


async def test_get_movie_not_found(client: AsyncClient) -> None:
    resp = await client.get("/movies/999")
    assert resp.status_code == 404


async def test_list_movies(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    await create_movie(client, moderator_headers, name="Movie 1")
    await create_movie(client, moderator_headers, name="Movie 2")

    resp = await client.get("/movies")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["page"] == 1


async def test_list_movies_search(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    await create_movie(client, moderator_headers, name="The Matrix")
    await create_movie(client, moderator_headers, name="Inception")

    resp = await client.get("/movies", params={"search": "matrix"})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "The Matrix"


async def test_list_movies_filter_genre(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    genre_id = await _create_genre(client, moderator_headers, name="Sci-Fi")
    await create_movie(client, moderator_headers, name="Matrix", genre_ids=[genre_id])
    await create_movie(client, moderator_headers, name="Drama Movie")

    resp = await client.get("/movies", params={"genre_id": genre_id})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Matrix"


async def test_update_movie(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    created = await create_movie(client, moderator_headers)
    movie_id = created["id"]

    resp = await client.patch(
        f"/movies/{movie_id}",
        json={"name": "Updated Movie"},
        headers=moderator_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Movie"


async def test_delete_movie(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    created = await create_movie(client, moderator_headers)
    movie_id = created["id"]

    resp = await client.delete(f"/movies/{movie_id}", headers=moderator_headers)
    assert resp.status_code == 204

    resp = await client.get(f"/movies/{movie_id}")
    assert resp.status_code == 404


async def test_update_movie_not_found(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    resp = await client.patch(
        "/movies/999", json={"name": "X"}, headers=moderator_headers
    )
    assert resp.status_code == 404


async def test_delete_movie_not_found(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    resp = await client.delete("/movies/999", headers=moderator_headers)
    assert resp.status_code == 404


async def test_list_movies_pagination(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    for i in range(3):
        await create_movie(client, moderator_headers, name=f"Movie {i}")

    resp = await client.get("/movies", params={"page": 1, "per_page": 2})
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["pages"] == 2

    resp = await client.get("/movies", params={"page": 2, "per_page": 2})
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["page"] == 2


async def test_list_movies_sort(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    await create_movie(client, moderator_headers, name="Alpha")
    await create_movie(client, moderator_headers, name="Zeta")

    resp = await client.get("/movies", params={"sort_by": "id", "sort_order": "desc"})
    items = resp.json()["items"]
    assert items[0]["name"] == "Zeta"
    assert items[1]["name"] == "Alpha"
