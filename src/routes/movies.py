from fastapi import APIRouter, Query, status

from core.dependencies import DBSession, ModeratorUser
from core.exceptions import BadRequestError, NotFoundError
from crud.comment import comment_crud
from crud.movie import movie_crud
from crud.order import order_crud
from crud.rating import rating_crud
from schemas.common import PaginatedResponse
from schemas.movies import (
    MovieCreateRequest,
    MovieListItemResponse,
    MovieResponse,
    MovieUpdateRequest,
)

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get("", summary="List movies")
async def list_movies(
    db: DBSession,
    search: str | None = None,
    year: int | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    imdb_min: float | None = None,
    imdb_max: float | None = None,
    genre_id: int | None = None,
    certification_id: int | None = None,
    sort_by: str = Query(default="id", pattern="^(id|price|year|imdb|votes)$"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[MovieListItemResponse]:
    """Return a paginated list of movies with optional filters and sorting."""
    skip = (page - 1) * per_page

    movies = await movie_crud.get_list(
        db,
        skip=skip,
        limit=per_page,
        search=search,
        year=year,
        year_min=year_min,
        year_max=year_max,
        imdb_min=imdb_min,
        imdb_max=imdb_max,
        genre_id=genre_id,
        certification_id=certification_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    total = await movie_crud.count_filtered(
        db,
        search=search,
        year=year,
        year_min=year_min,
        year_max=year_max,
        imdb_min=imdb_min,
        imdb_max=imdb_max,
        genre_id=genre_id,
        certification_id=certification_id,
    )

    return PaginatedResponse.create(
        items=[MovieListItemResponse.model_validate(m) for m in movies],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/{movie_id}",
    summary="Get movie",
    responses={404: {"description": "Movie not found"}},
)
async def get_movie(movie_id: int, db: DBSession) -> MovieResponse:
    """Return full details of a movie by ID."""
    movie = await movie_crud.get_detail(db, movie_id)
    if movie is None:
        raise NotFoundError("Movie not found")

    avg, total_ratings = await rating_crud.get_movie_stats(db, movie_id)
    total_comments = await comment_crud.count_by_movie(db, movie_id)

    data = MovieResponse.model_validate(movie)
    data.average_rating = avg
    data.total_ratings = total_ratings
    data.total_comments = total_comments
    return data


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create movie",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
    },
)
async def create_movie(
    body: MovieCreateRequest, user: ModeratorUser, db: DBSession
) -> MovieResponse:
    """Create a new movie with relationships (moderator only)."""
    movie = await movie_crud.create_movie(db, **body.model_dump())
    return MovieResponse.model_validate(movie)


@router.patch(
    "/{movie_id}",
    summary="Update movie",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Movie not found"},
    },
)
async def update_movie(
    movie_id: int,
    body: MovieUpdateRequest,
    user: ModeratorUser,
    db: DBSession,
) -> MovieResponse:
    """Update a movie's fields and relationships (moderator only)."""
    movie = await movie_crud.get_detail(db, movie_id)
    if movie is None:
        raise NotFoundError("Movie not found")

    data = body.model_dump(exclude_unset=True)
    movie = await movie_crud.update_movie(db, movie, **data)
    return MovieResponse.model_validate(movie)


@router.delete(
    "/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete movie",
    responses={
        400: {"description": "Cannot delete a movie that has been purchased"},
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Movie not found"},
    },
)
async def delete_movie(movie_id: int, user: ModeratorUser, db: DBSession) -> None:
    """Delete a movie (moderator only)."""
    movie = await movie_crud.get(db, movie_id)
    if movie is None:
        raise NotFoundError("Movie not found")

    if await order_crud.is_movie_purchased(db, movie_id):
        raise BadRequestError("Cannot delete a movie that has been purchased")

    await movie_crud.delete(db, movie)
