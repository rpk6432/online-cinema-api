from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.base import CRUDBase
from models.movie import Star


class CRUDStar(CRUDBase[Star]):
    async def get_by_name(self, db: AsyncSession, name: str) -> Star | None:
        result = await db.execute(select(Star).where(Star.name == name))
        return result.scalar_one_or_none()


star_crud = CRUDStar(Star)
