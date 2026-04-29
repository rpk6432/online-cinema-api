from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.base import CRUDBase
from models.movie import Genre, movie_genres


class CRUDGenre(CRUDBase[Genre]):
    async def get_by_name(self, db: AsyncSession, name: str) -> Genre | None:
        result = await db.execute(select(Genre).where(Genre.name == name))
        return result.scalar_one_or_none()

    async def get_all_with_movie_count(
        self, db: AsyncSession
    ) -> list[tuple[Genre, int]]:
        """Return all genres with their movie counts, ordered by name."""
        query = (
            select(Genre, func.count(movie_genres.c.movie_id))
            .outerjoin(movie_genres, Genre.id == movie_genres.c.genre_id)
            .group_by(Genre.id)
            .order_by(Genre.name)
        )
        result = await db.execute(query)
        return [(row[0], row[1]) for row in result.all()]


genre_crud = CRUDGenre(Genre)
