from typing import Any

from httpx import AsyncClient


async def create_movie(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    name: str = "Test Movie",
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
        "price": "9.99",
    }
    if genre_ids is not None:
        payload["genre_ids"] = genre_ids
    if certification_id is not None:
        payload["certification_id"] = certification_id

    resp = await client.post("/movies", json=payload, headers=headers)
    data: dict[str, Any] = resp.json()
    return data
