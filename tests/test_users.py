import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from crud.user import user_crud


async def test_list_users_admin(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.get("/users", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["page"] == 1
    assert len(data["items"]) >= 1


async def test_list_users_forbidden(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get("/users", headers=auth_headers)
    assert resp.status_code == 403


async def test_list_users_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/users")
    assert resp.status_code == 401


async def test_change_group(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_user: dict[str, str],
    db: AsyncSession,
) -> None:
    user = await user_crud.get_by_email(db, active_user["email"])
    assert user is not None

    resp = await client.patch(
        f"/users/{user.id}/group",
        headers=admin_headers,
        json={"group_name": "MODERATOR"},
    )
    assert resp.status_code == 200
    assert resp.json()["group_name"] == "MODERATOR"


async def test_change_group_invalid(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.patch(
        "/users/1/group",
        headers=admin_headers,
        json={"group_name": "SUPERADMIN"},
    )
    assert resp.status_code == 422


async def test_change_group_not_found(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.patch(
        "/users/9999/group",
        headers=admin_headers,
        json={"group_name": "MODERATOR"},
    )
    assert resp.status_code == 404


@pytest.mark.usefixtures("admin_user")
async def test_activate_user_admin(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db: AsyncSession,
) -> None:
    # Register a new inactive user
    await client.post(
        "/auth/register",
        json={"email": "inactive@example.com", "password": "Secret1234"},
    )
    user = await user_crud.get_by_email(db, "inactive@example.com")
    assert user is not None
    assert not user.is_active

    resp = await client.post(f"/users/{user.id}/activate", headers=admin_headers)
    assert resp.status_code == 200

    await db.refresh(user)
    assert user.is_active


async def test_activate_already_active(
    client: AsyncClient,
    admin_headers: dict[str, str],
    active_user: dict[str, str],
    db: AsyncSession,
) -> None:
    user = await user_crud.get_by_email(db, active_user["email"])
    assert user is not None

    resp = await client.post(f"/users/{user.id}/activate", headers=admin_headers)
    assert resp.status_code == 409
