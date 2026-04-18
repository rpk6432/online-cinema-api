from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crud.base import CRUDBase
from models.user import User, UserGroup, UserGroupEnum


class CRUDUser(CRUDBase[User]):
    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        """Find user by email address, returns None if not found."""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_with_group(self, db: AsyncSession, user_id: int) -> User | None:
        """Load user with eagerly loaded group relationship."""
        result = await db.execute(
            select(User)
            .options(selectinload(User.group))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        db: AsyncSession,
        email: str,
        hashed_password: str,
        group_name: UserGroupEnum = UserGroupEnum.USER,
    ) -> User:
        """Create user and assign to group. Group must exist in DB."""
        result = await db.execute(
            select(UserGroup).where(UserGroup.name == group_name.value)
        )
        group = result.scalar_one()

        user = User(
            email=email,
            hashed_password=hashed_password,
            group_id=group.id,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user, attribute_names=["group"])
        return user


user_crud = CRUDUser(User)
