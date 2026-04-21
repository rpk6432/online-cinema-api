from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.interaction import Bookmark
from models.movie import Movie


class CRUDBookmark:
    async def add(self, db: AsyncSession, user_id: int, movie_id: int) -> Bookmark:
        """Add movie to bookmarks."""
        bookmark = Bookmark(user_id=user_id, movie_id=movie_id)
        db.add(bookmark)
        await db.commit()
        await db.refresh(bookmark)
        return bookmark

    async def remove(self, db: AsyncSession, user_id: int, movie_id: int) -> bool:
        """Remove from bookmarks. Returns True if deleted, False if not found."""
        result = await db.execute(
            select(Bookmark).where(
                Bookmark.user_id == user_id, Bookmark.movie_id == movie_id
            )
        )
        bookmark = result.scalar_one_or_none()
        if bookmark is None:
            return False
        await db.delete(bookmark)
        await db.commit()
        return True

    async def exists(self, db: AsyncSession, user_id: int, movie_id: int) -> bool:
        """Check if movie is in user's bookmarks."""
        result = await db.execute(
            select(Bookmark.id).where(
                Bookmark.user_id == user_id, Bookmark.movie_id == movie_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_user_bookmarks(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        search: str | None = None,
        sort_by: str = "added_at",
        sort_order: str = "desc",
        page: int = 1,
        per_page: int = 20,
    ) -> list[Bookmark]:
        """Get user's bookmarks with movie data, search, and sorting."""
        query = (
            select(Bookmark)
            .where(Bookmark.user_id == user_id)
            .options(selectinload(Bookmark.movie).selectinload(Movie.genres))
            .options(selectinload(Bookmark.movie).selectinload(Movie.certification))
        )

        if search:
            query = query.join(Bookmark.movie).where(Movie.name.ilike(f"%{search}%"))

        sort_column = getattr(Bookmark, sort_by, Bookmark.added_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_user_bookmarks(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        search: str | None = None,
    ) -> int:
        """Count user's bookmarks with optional search filter."""
        query = (
            select(func.count())
            .select_from(Bookmark)
            .where(Bookmark.user_id == user_id)
        )

        if search:
            query = query.join(Bookmark.movie).where(Movie.name.ilike(f"%{search}%"))

        result = await db.execute(query)
        return result.scalar_one()


bookmark_crud = CRUDBookmark()
