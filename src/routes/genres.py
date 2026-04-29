from fastapi import APIRouter, status

from core.dependencies import DBSession, ModeratorUser
from core.exceptions import AlreadyExistsError, NotFoundError
from crud.genre import genre_crud
from crud.movie import movie_crud
from schemas.catalogs import GenreCreateRequest, GenreResponse, GenreWithCountResponse
from schemas.movies import MovieListItemResponse

router = APIRouter(prefix="/genres", tags=["Genres"])


@router.get("", summary="List genres")
async def list_genres(db: DBSession) -> list[GenreWithCountResponse]:
    """Return all available genres with movie counts."""
    rows = await genre_crud.get_all_with_movie_count(db)
    return [
        GenreWithCountResponse(id=genre.id, name=genre.name, movie_count=count)
        for genre, count in rows
    ]


@router.get(
    "/{genre_id}/movies",
    summary="List movies by genre",
    responses={404: {"description": "Genre not found"}},
)
async def get_genre_movies(genre_id: int, db: DBSession) -> list[MovieListItemResponse]:
    """Return movies belonging to a genre."""
    genre = await genre_crud.get(db, genre_id)
    if genre is None:
        raise NotFoundError("Genre not found")

    movies = await movie_crud.get_list(db, genre_id=genre_id, limit=100)
    return [MovieListItemResponse.model_validate(m) for m in movies]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create genre",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        409: {"description": "Genre already exists"},
    },
)
async def create_genre(
    body: GenreCreateRequest, user: ModeratorUser, db: DBSession
) -> GenreResponse:
    """Create a new genre (moderator only)."""
    existing = await genre_crud.get_by_name(db, body.name)
    if existing:
        raise AlreadyExistsError("Genre already exists")

    genre = await genre_crud.create(db, name=body.name)
    return GenreResponse.model_validate(genre)


@router.patch(
    "/{genre_id}",
    summary="Update genre",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Genre not found"},
    },
)
async def update_genre(
    genre_id: int,
    body: GenreCreateRequest,
    user: ModeratorUser,
    db: DBSession,
) -> GenreResponse:
    """Rename an existing genre (moderator only)."""
    genre = await genre_crud.get(db, genre_id)
    if genre is None:
        raise NotFoundError("Genre not found")

    await genre_crud.update(db, genre, name=body.name)
    return GenreResponse.model_validate(genre)


@router.delete(
    "/{genre_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete genre",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Genre not found"},
    },
)
async def delete_genre(genre_id: int, user: ModeratorUser, db: DBSession) -> None:
    """Delete a genre (moderator only)."""
    genre = await genre_crud.get(db, genre_id)
    if genre is None:
        raise NotFoundError("Genre not found")

    await genre_crud.delete(db, genre)
