from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.base import CRUDBase
from models.movie import Genre


class CRUDGenre(CRUDBase[Genre]):
    async def get_by_name(self, db: AsyncSession, name: str) -> Genre | None:
        result = await db.execute(select(Genre).where(Genre.name == name))
        return result.scalar_one_or_none()


genre_crud = CRUDGenre(Genre)
