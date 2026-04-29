from fastapi import APIRouter, status

from core.dependencies import DBSession, ModeratorUser
from core.exceptions import AlreadyExistsError, NotFoundError
from crud.star import star_crud
from schemas.catalogs import StarCreateRequest, StarResponse

router = APIRouter(prefix="/stars", tags=["Stars"])


@router.get("", summary="List stars")
async def list_stars(db: DBSession) -> list[StarResponse]:
    """Return all available stars."""
    stars = await star_crud.get_multi(db, limit=100)
    return [StarResponse.model_validate(s) for s in stars]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create star",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        409: {"description": "Star already exists"},
    },
)
async def create_star(
    body: StarCreateRequest, user: ModeratorUser, db: DBSession
) -> StarResponse:
    """Create a new star (moderator only)."""
    existing = await star_crud.get_by_name(db, body.name)
    if existing:
        raise AlreadyExistsError("Star already exists")

    star = await star_crud.create(db, name=body.name)
    return StarResponse.model_validate(star)


@router.patch(
    "/{star_id}",
    summary="Update star",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Star not found"},
    },
)
async def update_star(
    star_id: int,
    body: StarCreateRequest,
    user: ModeratorUser,
    db: DBSession,
) -> StarResponse:
    """Rename an existing star (moderator only)."""
    star = await star_crud.get(db, star_id)
    if star is None:
        raise NotFoundError("Star not found")

    await star_crud.update(db, star, name=body.name)
    return StarResponse.model_validate(star)


@router.delete(
    "/{star_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete star",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Star not found"},
    },
)
async def delete_star(star_id: int, user: ModeratorUser, db: DBSession) -> None:
    """Delete a star (moderator only)."""
    star = await star_crud.get(db, star_id)
    if star is None:
        raise NotFoundError("Star not found")

    await star_crud.delete(db, star)
