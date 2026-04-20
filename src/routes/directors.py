from fastapi import APIRouter, status

from core.dependencies import DBSession, ModeratorUser
from core.exceptions import AlreadyExistsError, NotFoundError
from crud.director import director_crud
from schemas.catalogs import DirectorCreateRequest, DirectorResponse

router = APIRouter(prefix="/directors", tags=["Directors"])


@router.get("")
async def list_directors(db: DBSession) -> list[DirectorResponse]:
    """Return all available directors."""
    directors = await director_crud.get_multi(db, limit=100)
    return [DirectorResponse.model_validate(d) for d in directors]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_director(
    body: DirectorCreateRequest, user: ModeratorUser, db: DBSession
) -> DirectorResponse:
    """Create a new director (moderator only)."""
    existing = await director_crud.get_by_name(db, body.name)
    if existing:
        raise AlreadyExistsError("Director already exists")

    director = await director_crud.create(db, name=body.name)
    return DirectorResponse.model_validate(director)


@router.patch("/{director_id}")
async def update_director(
    director_id: int,
    body: DirectorCreateRequest,
    user: ModeratorUser,
    db: DBSession,
) -> DirectorResponse:
    """Rename an existing director (moderator only)."""
    director = await director_crud.get(db, director_id)
    if director is None:
        raise NotFoundError("Director not found")

    await director_crud.update(db, director, name=body.name)
    return DirectorResponse.model_validate(director)


@router.delete("/{director_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_director(director_id: int, user: ModeratorUser, db: DBSession) -> None:
    """Delete a director (moderator only)."""
    director = await director_crud.get(db, director_id)
    if director is None:
        raise NotFoundError("Director not found")

    await director_crud.delete(db, director)
