from fastapi import APIRouter, Query, status
from sqlalchemy.exc import IntegrityError

from core.dependencies import ActiveUser, DBSession
from core.exceptions import AlreadyExistsError, NotFoundError
from crud.bookmark import bookmark_crud
from schemas.common import PaginatedResponse
from schemas.interactions import BookmarkResponse, BookmarkWithMovieResponse

router = APIRouter(prefix="/bookmarks", tags=["Bookmarks"])


@router.get("")
async def list_bookmarks(
    user: ActiveUser,
    db: DBSession,
    search: str | None = None,
    sort_by: str = Query(default="added_at", pattern="^(added_at)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[BookmarkWithMovieResponse]:
    """List current user's bookmarked movies."""
    bookmarks = await bookmark_crud.get_user_bookmarks(
        db,
        user.id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
    )
    total = await bookmark_crud.count_user_bookmarks(db, user.id, search=search)

    return PaginatedResponse.create(
        items=[BookmarkWithMovieResponse.model_validate(b) for b in bookmarks],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/movies/{movie_id}", status_code=status.HTTP_201_CREATED)
async def add_bookmark(
    movie_id: int, user: ActiveUser, db: DBSession
) -> BookmarkResponse:
    """Add a movie to bookmarks."""
    if await bookmark_crud.exists(db, user.id, movie_id):
        raise AlreadyExistsError("Movie already bookmarked")
    try:
        bookmark = await bookmark_crud.add(db, user.id, movie_id)
    except IntegrityError:
        raise NotFoundError("Movie not found") from None
    return BookmarkResponse.model_validate(bookmark)


@router.delete("/movies/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_bookmark(movie_id: int, user: ActiveUser, db: DBSession) -> None:
    """Remove a movie from bookmarks."""
    if not await bookmark_crud.remove(db, user.id, movie_id):
        raise NotFoundError("Bookmark not found")
