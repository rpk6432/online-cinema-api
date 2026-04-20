from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.base import CRUDBase
from models.movie import Director


class CRUDDirector(CRUDBase[Director]):
    async def get_by_name(self, db: AsyncSession, name: str) -> Director | None:
        result = await db.execute(select(Director).where(Director.name == name))
        return result.scalar_one_or_none()


director_crud = CRUDDirector(Director)
