from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.user import user_crud
from models.user import ActivationToken, PasswordResetToken, User

# Registration


async def test_register_success(client: AsyncClient) -> None:
    resp = await client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": "Secret1234"},
    )
    assert resp.status_code == 201
    assert resp.json()["detail"] == "Check your email to activate your account"


async def test_register_duplicate_email(client: AsyncClient) -> None:
    payload = {"email": "dup@example.com", "password": "Secret1234"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 409


async def test_register_weak_password(client: AsyncClient) -> None:
    resp = await client.post(
        "/auth/register",
        json={"email": "weak@example.com", "password": "short"},
    )
    assert resp.status_code == 422


# Activation


async def test_activate_success(
    client: AsyncClient, registered_user: dict[str, str], db: AsyncSession
) -> None:
    user = await user_crud.get_by_email(db, registered_user["email"])
    assert user is not None

    result = await db.execute(
        select(ActivationToken).where(ActivationToken.user_id == user.id)
    )
    token = result.scalar_one()

    resp = await client.post("/auth/activate", json={"token": token.token})
    assert resp.status_code == 200
    assert "activated" in resp.json()["detail"].lower()


async def test_activate_invalid_token(client: AsyncClient) -> None:
    resp = await client.post("/auth/activate", json={"token": "invalid-token"})
    assert resp.status_code == 404


# Login


async def test_login_success(client: AsyncClient, active_user: dict[str, str]) -> None:
    resp = await client.post(
        "/auth/login",
        json={
            "email": active_user["email"],
            "password": active_user["password"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(
    client: AsyncClient, active_user: dict[str, str]
) -> None:
    resp = await client.post(
        "/auth/login",
        json={"email": active_user["email"], "password": "Wrong1234"},
    )
    assert resp.status_code == 401


async def test_login_inactive_account(
    client: AsyncClient, registered_user: dict[str, str]
) -> None:
    resp = await client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert resp.status_code == 403


# Logout


async def test_logout_success(client: AsyncClient, active_user: dict[str, str]) -> None:
    tokens = await client.post(
        "/auth/login",
        json={
            "email": active_user["email"],
            "password": active_user["password"],
        },
    )
    data = tokens.json()
    headers = {"Authorization": f"Bearer {data['access_token']}"}

    resp = await client.post(
        "/auth/logout",
        json={"refresh_token": data["refresh_token"]},
        headers=headers,
    )
    assert resp.status_code == 200


# Refresh


async def test_refresh_success(
    client: AsyncClient, active_user: dict[str, str]
) -> None:
    tokens = await client.post(
        "/auth/login",
        json={
            "email": active_user["email"],
            "password": active_user["password"],
        },
    )
    refresh = tokens.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

    # Old refresh token should be invalidated (rotation)
    resp2 = await client.post("/auth/refresh", json={"refresh_token": refresh})
    assert resp2.status_code == 401


async def test_refresh_invalid_token(client: AsyncClient) -> None:
    resp = await client.post("/auth/refresh", json={"refresh_token": "invalid"})
    assert resp.status_code == 401


# Password Change


async def test_password_change_success(
    client: AsyncClient,
    active_user: dict[str, str],
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post(
        "/auth/password-change",
        json={
            "old_password": active_user["password"],
            "new_password": "NewSecret1234",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200

    login_resp = await client.post(
        "/auth/login",
        json={
            "email": active_user["email"],
            "password": "NewSecret1234",
        },
    )
    assert login_resp.status_code == 200


async def test_password_change_wrong_old(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/auth/password-change",
        json={"old_password": "Wrong1234", "new_password": "NewSecret1234"},
        headers=auth_headers,
    )
    assert resp.status_code == 401


# Password Reset


async def test_password_reset_request(
    client: AsyncClient, active_user: dict[str, str]
) -> None:
    resp = await client.post(
        "/auth/password-reset", json={"email": active_user["email"]}
    )
    assert resp.status_code == 200


async def test_password_reset_nonexistent_email(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/auth/password-reset", json={"email": "nobody@example.com"}
    )
    assert resp.status_code == 200


async def test_password_reset_confirm_success(
    client: AsyncClient, active_user: dict[str, str], db: AsyncSession
) -> None:
    await client.post("/auth/password-reset", json={"email": active_user["email"]})

    user_result = await db.execute(
        select(User).where(User.email == active_user["email"])
    )
    user = user_result.scalar_one()

    token_result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )
    token = token_result.scalar_one()

    resp = await client.post(
        "/auth/password-reset/confirm",
        json={"token": token.token, "new_password": "Reset1234"},
    )
    assert resp.status_code == 200

    login_resp = await client.post(
        "/auth/login",
        json={"email": active_user["email"], "password": "Reset1234"},
    )
    assert login_resp.status_code == 200


# Me


async def test_me_success(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["is_active"] is True
    assert data["group_name"] == "USER"


async def test_me_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
