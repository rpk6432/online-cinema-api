from unittest.mock import AsyncMock, patch

from httpx import AsyncClient


async def test_get_profile(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await client.get("/profiles/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["first_name"] is None
    assert data["last_name"] is None
    assert data["avatar"] is None
    assert data["gender"] is None


async def test_update_profile(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.patch(
        "/profiles/me",
        headers=auth_headers,
        json={"first_name": "John", "last_name": "Doe"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"


async def test_update_profile_partial(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Updating one field should not clear others."""
    await client.patch(
        "/profiles/me",
        headers=auth_headers,
        json={"first_name": "John", "last_name": "Doe"},
    )
    resp = await client.patch(
        "/profiles/me",
        headers=auth_headers,
        json={"first_name": "Jane"},
    )
    data = resp.json()
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Doe"


async def test_update_profile_invalid_gender(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.patch(
        "/profiles/me",
        headers=auth_headers,
        json={"gender": "INVALID"},
    )
    assert resp.status_code == 422


@patch("routes.profiles.upload_avatar", new_callable=AsyncMock)
@patch("routes.profiles.delete_avatar", new_callable=AsyncMock)
async def test_upload_avatar(
    mock_delete: AsyncMock,
    mock_upload: AsyncMock,
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    mock_upload.return_value = "avatars/1/abc123.jpg"

    resp = await client.post(
        "/profiles/me/avatar",
        headers=auth_headers,
        files={"file": ("avatar.jpg", b"fake-image-data", "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["avatar"] is not None
    assert "avatars/1/abc123.jpg" in data["avatar"]
    mock_upload.assert_called_once()
    mock_delete.assert_not_called()


@patch("routes.profiles.upload_avatar", new_callable=AsyncMock)
@patch("routes.profiles.delete_avatar", new_callable=AsyncMock)
@patch("routes.profiles.get_avatar_url")
async def test_delete_avatar(
    mock_url: AsyncMock,
    mock_delete: AsyncMock,
    mock_upload: AsyncMock,
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    mock_upload.return_value = "avatars/1/abc123.jpg"
    mock_url.return_value = "http://minio/bucket/avatars/1/abc123.jpg"

    # Upload first
    await client.post(
        "/profiles/me/avatar",
        headers=auth_headers,
        files={"file": ("avatar.jpg", b"fake-image-data", "image/jpeg")},
    )

    # Then delete
    resp = await client.delete("/profiles/me/avatar", headers=auth_headers)
    assert resp.status_code == 204

    # Verify profile avatar is cleared
    resp = await client.get("/profiles/me", headers=auth_headers)
    assert resp.json()["avatar"] is None


async def test_profile_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/profiles/me")
    assert resp.status_code == 401
