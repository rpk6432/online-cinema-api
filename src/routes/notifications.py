from fastapi import APIRouter, Query

from core.dependencies import ActiveUser, DBSession
from core.exceptions import NotFoundError
from crud.notification import notification_crud
from schemas.common import PaginatedResponse
from schemas.notifications import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(
    user: ActiveUser,
    db: DBSession,
    unread_only: bool = False,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[NotificationResponse]:
    """List current user's notifications."""
    notifications = await notification_crud.get_user_notifications(
        db,
        user.id,
        unread_only=unread_only,
        page=page,
        per_page=per_page,
    )
    total = await notification_crud.count_user_notifications(
        db, user.id, unread_only=unread_only
    )

    return PaginatedResponse.create(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int, user: ActiveUser, db: DBSession
) -> NotificationResponse:
    """Mark a notification as read."""
    notification = await notification_crud.mark_as_read(db, notification_id, user.id)
    if notification is None:
        raise NotFoundError("Notification not found")
    return NotificationResponse.model_validate(notification)
