from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import UserGroup, UserGroupEnum


async def seed_user_groups(db: AsyncSession) -> None:
    """Insert default user groups if they don't exist."""
    for group in UserGroupEnum:
        exists = await db.execute(
            select(UserGroup).where(UserGroup.name == group.value)
        )
        if exists.scalar_one_or_none() is None:
            db.add(UserGroup(name=group.value))
            logger.info("Created user group: {}", group.value)
    await db.commit()
