from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.interaction import Rating


class CRUDRating:
    async def set_rating(
        self, db: AsyncSession, user_id: int, movie_id: int, score: int
    ) -> Rating:
        """Create or update a rating."""
        result = await db.execute(
            select(Rating).where(Rating.user_id == user_id, Rating.movie_id == movie_id)
        )
        existing: Rating | None = result.scalar_one_or_none()

        if existing is None:
            rating = Rating(user_id=user_id, movie_id=movie_id, score=score)
            db.add(rating)
            await db.commit()
            await db.refresh(rating)
            return rating

        existing.score = score
        await db.commit()
        await db.refresh(existing)
        return existing

    async def get_movie_stats(
        self, db: AsyncSession, movie_id: int
    ) -> tuple[float | None, int]:
        """Return (average_rating, total_ratings) for a movie."""
        result = await db.execute(
            select(
                func.avg(Rating.score),
                func.count(),
            ).where(Rating.movie_id == movie_id)
        )
        row = result.one()
        avg = round(float(row[0]), 1) if row[0] is not None else None
        return avg, row[1]


rating_crud = CRUDRating()
