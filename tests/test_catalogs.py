from httpx import AsyncClient


async def test_list_genres_empty(client: AsyncClient) -> None:
    resp = await client.get("/genres")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_genre(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/genres", json={"name": "Action"}, headers=moderator_headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Action"
    assert "id" in data


async def test_create_genre_duplicate(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    await client.post("/genres", json={"name": "Action"}, headers=moderator_headers)
    resp = await client.post(
        "/genres", json={"name": "Action"}, headers=moderator_headers
    )
    assert resp.status_code == 409


async def test_create_genre_forbidden(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post("/genres", json={"name": "Action"}, headers=auth_headers)
    assert resp.status_code == 403


async def test_update_genre(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    create = await client.post(
        "/genres", json={"name": "Action"}, headers=moderator_headers
    )
    genre_id = create.json()["id"]

    resp = await client.patch(
        f"/genres/{genre_id}", json={"name": "Drama"}, headers=moderator_headers
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Drama"


async def test_delete_genre(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    create = await client.post(
        "/genres", json={"name": "Action"}, headers=moderator_headers
    )
    genre_id = create.json()["id"]

    resp = await client.delete(f"/genres/{genre_id}", headers=moderator_headers)
    assert resp.status_code == 204


async def test_create_star(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/stars", json={"name": "Tom Hanks"}, headers=moderator_headers
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Tom Hanks"


async def test_create_director(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/directors", json={"name": "Steven Spielberg"}, headers=moderator_headers
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Steven Spielberg"


async def test_create_certification(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/certifications", json={"name": "PG-13"}, headers=moderator_headers
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "PG-13"


async def test_list_certifications(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    await client.post(
        "/certifications", json={"name": "PG-13"}, headers=moderator_headers
    )
    await client.post("/certifications", json={"name": "R"}, headers=moderator_headers)

    resp = await client.get("/certifications")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_update_genre_not_found(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    resp = await client.patch(
        "/genres/999", json={"name": "Drama"}, headers=moderator_headers
    )
    assert resp.status_code == 404


async def test_delete_genre_not_found(
    client: AsyncClient, moderator_headers: dict[str, str]
) -> None:
    resp = await client.delete("/genres/999", headers=moderator_headers)
    assert resp.status_code == 404


async def test_create_genre_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post("/genres", json={"name": "Action"})
    assert resp.status_code == 401


async def test_admin_can_create_genre(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.post("/genres", json={"name": "Comedy"}, headers=admin_headers)
    assert resp.status_code == 201
