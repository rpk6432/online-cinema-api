from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.base import CRUDBase
from models.user import UserProfile


class CRUDProfile(CRUDBase[UserProfile]):
    async def get_by_user_id(
        self, db: AsyncSession, user_id: int
    ) -> UserProfile | None:
        """Get profile by user ID."""
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()


profile_crud = CRUDProfile(UserProfile)
