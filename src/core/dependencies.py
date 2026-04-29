from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ForbiddenError, UnauthorizedError
from core.security import decode_token, verify_password
from crud.user import user_crud
from database import get_db_session
from database.session import async_session as _session_factory
from models.user import User, UserGroupEnum

DBSession = Annotated[AsyncSession, Depends(get_db_session)]

_bearer = HTTPBearer(auto_error=False)

_basic = HTTPBasic()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: DBSession,
) -> User:
    """Extract and validate JWT from Authorization header, return user."""
    if credentials is None:
        raise UnauthorizedError
    payload = decode_token(credentials.credentials)
    user_id = int(payload["sub"])
    user = await user_crud.get_with_group(db, user_id)
    if user is None:
        raise UnauthorizedError("User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_active_user(user: CurrentUser) -> User:
    """Ensure the current user has activated their account."""
    if not user.is_active:
        raise ForbiddenError("Account is not activated")
    return user


ActiveUser = Annotated[User, Depends(get_current_active_user)]


def require_group(
    *allowed: UserGroupEnum,
) -> Callable[..., Awaitable[User]]:
    """Factory for role-based access control dependency."""

    async def check_group(user: ActiveUser) -> User:
        if user.group_name not in {g.value for g in allowed}:
            raise ForbiddenError("Insufficient permissions")
        return user

    return check_group


AdminUser = Annotated[User, Depends(require_group(UserGroupEnum.ADMIN))]
ModeratorUser = Annotated[
    User, Depends(require_group(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
]


async def verify_admin_basic(
    credentials: HTTPBasicCredentials = Depends(_basic),
) -> None:
    """Verify admin credentials via HTTP Basic auth."""
    unauthorized = HTTPException(
        status_code=401,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )
    async with _session_factory() as db:
        user = await user_crud.get_by_email(db, credentials.username)
        if user is None or not verify_password(
            credentials.password, user.hashed_password
        ):
            raise unauthorized
        if not user.is_active:
            raise unauthorized
        await db.refresh(user, attribute_names=["group"])
        if user.group.name != UserGroupEnum.ADMIN.value:
            raise unauthorized
