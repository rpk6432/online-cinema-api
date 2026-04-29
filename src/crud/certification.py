from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.base import CRUDBase
from models.movie import Certification


class CRUDCertification(CRUDBase[Certification]):
    async def get_by_name(self, db: AsyncSession, name: str) -> Certification | None:
        result = await db.execute(
            select(Certification).where(Certification.name == name)
        )
        return result.scalar_one_or_none()


certification_crud = CRUDCertification(Certification)
