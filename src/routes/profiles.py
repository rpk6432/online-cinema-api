from fastapi import APIRouter, UploadFile, status

from core.dependencies import ActiveUser, DBSession
from core.exceptions import NotFoundError
from crud.profile import profile_crud
from schemas.profiles import ProfileResponse, ProfileUpdateRequest
from storages.s3 import delete_avatar, get_avatar_url, upload_avatar

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.get(
    "/me",
    summary="Get own profile",
    responses={401: {"description": "Not authenticated"}},
)
async def get_profile(user: ActiveUser, db: DBSession) -> ProfileResponse:
    """Return the authenticated user's profile."""
    profile = await profile_crud.get_by_user_id(db, user.id)
    if profile is None:
        raise NotFoundError("Profile not found")

    data = ProfileResponse.model_validate(profile)
    if profile.avatar:
        data.avatar = get_avatar_url(profile.avatar)
    return data


@router.patch(
    "/me",
    summary="Update own profile",
    responses={401: {"description": "Not authenticated"}},
)
async def update_profile(
    body: ProfileUpdateRequest, user: ActiveUser, db: DBSession
) -> ProfileResponse:
    """Update the authenticated user's profile fields."""
    profile = await profile_crud.get_by_user_id(db, user.id)
    if profile is None:
        raise NotFoundError("Profile not found")

    updates = body.model_dump(exclude_unset=True)
    if updates:
        await profile_crud.update(db, profile, **updates)

    data = ProfileResponse.model_validate(profile)
    if profile.avatar:
        data.avatar = get_avatar_url(profile.avatar)
    return data


@router.post(
    "/me/avatar",
    summary="Upload avatar",
    responses={401: {"description": "Not authenticated"}},
)
async def upload_profile_avatar(
    file: UploadFile, user: ActiveUser, db: DBSession
) -> ProfileResponse:
    """Upload or replace the user's avatar image."""
    profile = await profile_crud.get_by_user_id(db, user.id)
    if profile is None:
        raise NotFoundError("Profile not found")

    if profile.avatar:
        await delete_avatar(profile.avatar)

    key = await upload_avatar(file, user.id)
    await profile_crud.update(db, profile, avatar=key)

    data = ProfileResponse.model_validate(profile)
    data.avatar = get_avatar_url(key)
    return data


@router.delete(
    "/me/avatar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete avatar",
    responses={401: {"description": "Not authenticated"}},
)
async def delete_profile_avatar(user: ActiveUser, db: DBSession) -> None:
    """Remove the user's avatar from storage and profile."""
    profile = await profile_crud.get_by_user_id(db, user.id)
    if profile is None:
        raise NotFoundError("Profile not found")

    if profile.avatar:
        await delete_avatar(profile.avatar)
        await profile_crud.update(db, profile, avatar=None)
