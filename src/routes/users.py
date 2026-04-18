from fastapi import APIRouter, Query

from core.dependencies import AdminUser, DBSession
from core.exceptions import AlreadyExistsError, NotFoundError
from crud.token import delete_activation_token_by_user
from crud.user import user_crud
from schemas.common import MessageResponse, PaginatedResponse
from schemas.users import ChangeGroupRequest, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    summary="List all users",
    responses={403: {"description": "Admin access required"}},
)
async def list_users(
    user: AdminUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[UserResponse]:
    """Return a paginated list of all users (admin only)."""
    total = await user_crud.count(db)
    skip = (page - 1) * per_page
    users = await user_crud.get_multi_with_group(db, skip=skip, limit=per_page)

    return PaginatedResponse[UserResponse](
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.patch(
    "/{user_id}/group",
    summary="Change user group",
    responses={
        403: {"description": "Admin access required"},
        404: {"description": "User not found"},
    },
)
async def change_group(
    user_id: int, body: ChangeGroupRequest, admin: AdminUser, db: DBSession
) -> UserResponse:
    """Change the group/role of a user (admin only)."""
    target = await user_crud.get_with_group(db, user_id)
    if target is None:
        raise NotFoundError("User not found")

    await user_crud.change_group(db, target, body.group_name)
    return UserResponse.model_validate(target)


@router.post(
    "/{user_id}/activate",
    summary="Manually activate a user",
    responses={
        403: {"description": "Admin access required"},
        404: {"description": "User not found"},
        409: {"description": "User already active"},
    },
)
async def activate_user(
    user_id: int, admin: AdminUser, db: DBSession
) -> MessageResponse:
    """Manually activate a user account (admin only)."""
    target = await user_crud.get(db, user_id)
    if target is None:
        raise NotFoundError("User not found")

    if target.is_active:
        raise AlreadyExistsError("User is already active")

    await user_crud.update(db, target, is_active=True)
    await delete_activation_token_by_user(db, user_id)

    return MessageResponse(detail="User activated successfully")
