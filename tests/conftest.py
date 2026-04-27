from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import models  # noqa: F401
from core.config import Settings
from crud.user import user_crud
from database.base import Base
from database.seed import seed_user_groups
from database.session import get_db_session
from main import app
from models.user import UserGroupEnum

test_settings = Settings(_env_file=".env.test")
test_engine = create_async_engine(test_settings.database_url)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def _override_get_db_session() -> AsyncGenerator[AsyncSession]:
    async with test_session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
async def setup_tables() -> AsyncGenerator[None]:
    async with test_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
    async with test_session_factory() as session:
        await seed_user_groups(session)
    yield
    await test_engine.dispose()


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    async with test_session_factory() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db_session] = _override_get_db_session
    transport = ASGITransport(app=app)
    with (
        patch("routes.auth.send_activation_email"),
        patch("routes.auth.send_password_reset_email"),
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    app.dependency_overrides.clear()


async def _register_user(
    client: AsyncClient,
    email: str = "test@example.com",
    password: str = "Secret1234",
) -> dict[str, str]:
    await client.post("/auth/register", json={"email": email, "password": password})
    return {"email": email, "password": password}


async def _activate_user(db: AsyncSession, email: str) -> None:
    user = await user_crud.get_by_email(db, email)
    assert user is not None
    await user_crud.update(db, user, is_active=True)


async def _login_user(
    client: AsyncClient,
    email: str = "test@example.com",
    password: str = "Secret1234",
) -> dict[str, str]:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    data: dict[str, str] = resp.json()
    return data


@pytest.fixture
async def registered_user(client: AsyncClient) -> dict[str, str]:
    return await _register_user(client)


@pytest.fixture
async def active_user(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    creds = await _register_user(client)
    await _activate_user(db, creds["email"])
    return creds


@pytest.fixture
async def auth_headers(
    client: AsyncClient, active_user: dict[str, str]
) -> dict[str, str]:
    tokens = await _login_user(client)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _make_admin(db: AsyncSession, email: str) -> None:
    user = await user_crud.get_by_email(db, email)
    assert user is not None
    await user_crud.change_group(db, user, UserGroupEnum.ADMIN)


@pytest.fixture
async def admin_user(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    creds = await _register_user(client, email="admin@example.com")
    await _activate_user(db, creds["email"])
    await _make_admin(db, creds["email"])
    return creds


@pytest.fixture
async def admin_headers(
    client: AsyncClient, admin_user: dict[str, str]
) -> dict[str, str]:
    tokens = await _login_user(
        client, email=admin_user["email"], password=admin_user["password"]
    )
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _make_moderator(db: AsyncSession, email: str) -> None:
    user = await user_crud.get_by_email(db, email)
    assert user is not None
    await user_crud.change_group(db, user, UserGroupEnum.MODERATOR)


@pytest.fixture
async def moderator_user(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    creds = await _register_user(client, email="moderator@example.com")
    await _activate_user(db, creds["email"])
    await _make_moderator(db, creds["email"])
    return creds


@pytest.fixture
async def moderator_headers(
    client: AsyncClient, moderator_user: dict[str, str]
) -> dict[str, str]:
    tokens = await _login_user(
        client,
        email=moderator_user["email"],
        password=moderator_user["password"],
    )
    return {"Authorization": f"Bearer {tokens['access_token']}"}
