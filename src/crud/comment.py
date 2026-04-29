from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crud.base import CRUDBase
from models.interaction import Comment, CommentLike, Notification, NotificationType


class CRUDComment(CRUDBase[Comment]):
    async def create_comment(
        self,
        db: AsyncSession,
        user_id: int,
        movie_id: int,
        content: str,
        parent_id: int | None = None,
    ) -> Comment:
        """Create a comment or reply. Replies to replies are auto-flattened to root."""
        parent: Comment | None = None
        if parent_id is not None:
            parent = await self.get(db, parent_id)
            if parent is None:
                msg = "Parent comment not found"
                raise ValueError(msg)
            if parent.movie_id != movie_id:
                msg = "Parent comment belongs to a different movie"
                raise ValueError(msg)
            if parent.parent_id is not None:
                root = await self.get(db, parent.parent_id)
                if root is None:
                    msg = "Parent comment not found"
                    raise ValueError(msg)
                parent = root
                parent_id = parent.id

        comment = Comment(
            user_id=user_id,
            movie_id=movie_id,
            content=content,
            parent_id=parent_id,
        )
        db.add(comment)
        await db.commit()

        result = await db.execute(
            select(Comment)
            .where(Comment.id == comment.id)
            .options(selectinload(Comment.user))
        )
        comment = result.scalar_one()

        if parent is not None and parent.user_id != user_id:
            notification = Notification(
                user_id=parent.user_id,
                type=NotificationType.COMMENT_REPLY,
                message=f"User replied to your comment on movie #{movie_id}",
                related_movie_id=movie_id,
                related_comment_id=comment.id,
            )
            db.add(notification)
            await db.commit()
            logger.info(
                "Notification: reply to comment {} by user {}",
                parent_id,
                parent.user_id,
            )

        return comment

    async def get_by_movie(
        self,
        db: AsyncSession,
        movie_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> list[Comment]:
        """Get top-level comments for a movie with author info."""
        query = (
            select(Comment)
            .where(Comment.movie_id == movie_id, Comment.parent_id.is_(None))
            .options(selectinload(Comment.user))
            .order_by(Comment.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_replies(self, db: AsyncSession, parent_id: int) -> list[Comment]:
        """Get replies to a comment."""
        query = (
            select(Comment)
            .where(Comment.parent_id == parent_id)
            .options(selectinload(Comment.user))
            .order_by(Comment.created_at.asc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_by_movie(self, db: AsyncSession, movie_id: int) -> int:
        """Count top-level comments for a movie."""
        result = await db.execute(
            select(func.count())
            .select_from(Comment)
            .where(Comment.movie_id == movie_id, Comment.parent_id.is_(None))
        )
        return result.scalar_one()

    # Comment likes

    async def toggle_like(
        self, db: AsyncSession, user_id: int, comment_id: int, is_like: bool
    ) -> CommentLike | None:
        """Toggle like/dislike. Returns CommentLike or None if removed."""
        comment = await self.get(db, comment_id)
        if comment is None:
            msg = "Comment not found"
            raise ValueError(msg)

        result = await db.execute(
            select(CommentLike).where(
                CommentLike.user_id == user_id,
                CommentLike.comment_id == comment_id,
            )
        )
        existing: CommentLike | None = result.scalar_one_or_none()

        if existing is None:
            comment_like = CommentLike(
                user_id=user_id, comment_id=comment_id, is_like=is_like
            )
            db.add(comment_like)
            await db.commit()
            await db.refresh(comment_like)

            if is_like and comment.user_id != user_id:
                notification = Notification(
                    user_id=comment.user_id,
                    type=NotificationType.COMMENT_LIKE,
                    message=f"Someone liked your comment #{comment_id}",
                    related_movie_id=comment.movie_id,
                    related_comment_id=comment_id,
                )
                db.add(notification)
                await db.commit()
                logger.info(
                    "Notification: like on comment {} for user {}",
                    comment_id,
                    comment.user_id,
                )

            return comment_like

        if existing.is_like == is_like:
            await db.delete(existing)
            await db.commit()
            return None

        existing.is_like = is_like
        await db.commit()
        await db.refresh(existing)
        return existing

    async def get_likes_stats(
        self, db: AsyncSession, comment_id: int
    ) -> tuple[int, int]:
        """Return (likes_count, dislikes_count) for a comment."""
        result = await db.execute(
            select(
                func.count().filter(CommentLike.is_like.is_(True)),
                func.count().filter(CommentLike.is_like.is_(False)),
            ).where(CommentLike.comment_id == comment_id)
        )
        row = result.one()
        return row[0], row[1]


comment_crud = CRUDComment(Comment)
