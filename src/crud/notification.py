from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.base import CRUDBase
from models.interaction import Notification


class CRUDNotification(CRUDBase[Notification]):
    async def get_user_notifications(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        unread_only: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> list[Notification]:
        """Get notifications for a user."""
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            query = query.where(Notification.is_read.is_(False))

        query = (
            query.order_by(Notification.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_user_notifications(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        unread_only: bool = False,
    ) -> int:
        """Count notifications for a user."""
        query = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id)
        )

        if unread_only:
            query = query.where(Notification.is_read.is_(False))

        result = await db.execute(query)
        return result.scalar_one()

    async def mark_as_read(
        self, db: AsyncSession, notification_id: int, user_id: int
    ) -> Notification | None:
        """Mark notification as read. Returns None if not found or not owned."""
        notification = await self.get(db, notification_id)
        if notification is None or notification.user_id != user_id:
            return None
        notification.is_read = True
        await db.commit()
        await db.refresh(notification)
        return notification


notification_crud = CRUDNotification(Notification)
