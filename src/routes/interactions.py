from fastapi import APIRouter, Query, status
from sqlalchemy.exc import IntegrityError

from core.dependencies import ActiveUser, DBSession
from core.exceptions import NotFoundError, ValidationError
from crud.comment import comment_crud
from crud.rating import rating_crud
from schemas.common import MessageResponse, PaginatedResponse
from schemas.interactions import (
    CommentCreateRequest,
    CommentLikeRequest,
    CommentLikeResponse,
    CommentLikesStats,
    CommentResponse,
    MovieRatingResponse,
    RatingRequest,
    RatingResponse,
)

router = APIRouter(tags=["Interactions"])


# Ratings


@router.post("/movies/{movie_id}/rating", status_code=status.HTTP_201_CREATED)
async def set_rating(
    movie_id: int, body: RatingRequest, user: ActiveUser, db: DBSession
) -> RatingResponse:
    """Set or update the current user's rating for a movie."""
    try:
        rating = await rating_crud.set_rating(db, user.id, movie_id, body.score)
    except IntegrityError:
        raise NotFoundError("Movie not found") from None
    return RatingResponse.model_validate(rating)


@router.get("/movies/{movie_id}/rating")
async def get_movie_rating(movie_id: int, db: DBSession) -> MovieRatingResponse:
    """Get average rating and total count for a movie."""
    avg, total = await rating_crud.get_movie_stats(db, movie_id)
    return MovieRatingResponse(average_rating=avg, total_ratings=total)


# Comments


@router.post("/movies/{movie_id}/comments", status_code=status.HTTP_201_CREATED)
async def create_comment(
    movie_id: int,
    body: CommentCreateRequest,
    user: ActiveUser,
    db: DBSession,
) -> CommentResponse:
    """Create a comment or reply. Nested replies are flattened to the root."""
    try:
        comment = await comment_crud.create_comment(
            db,
            user_id=user.id,
            movie_id=movie_id,
            content=body.content,
            parent_id=body.parent_id,
        )
    except ValueError as e:
        raise ValidationError(str(e)) from None
    except IntegrityError:
        raise NotFoundError("Movie not found") from None
    return CommentResponse.model_validate(comment)


@router.get("/movies/{movie_id}/comments")
async def list_comments(
    movie_id: int,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[CommentResponse]:
    """List top-level comments for a movie."""
    comments = await comment_crud.get_by_movie(
        db, movie_id, page=page, per_page=per_page
    )
    total = await comment_crud.count_by_movie(db, movie_id)

    return PaginatedResponse.create(
        items=[CommentResponse.model_validate(c) for c in comments],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/comments/{comment_id}/replies")
async def get_replies(comment_id: int, db: DBSession) -> list[CommentResponse]:
    """Get all replies to a comment."""
    comment = await comment_crud.get(db, comment_id)
    if comment is None:
        raise NotFoundError("Comment not found")
    replies = await comment_crud.get_replies(db, comment_id)
    return [CommentResponse.model_validate(r) for r in replies]


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: int, user: ActiveUser, db: DBSession) -> None:
    """Delete own comment."""
    comment = await comment_crud.get(db, comment_id)
    if comment is None:
        raise NotFoundError("Comment not found")
    if comment.user_id != user.id:
        raise ValidationError("Cannot delete another user's comment")
    await comment_crud.delete(db, comment)


# Comment Likes


@router.post("/comments/{comment_id}/like")
async def toggle_comment_like(
    comment_id: int,
    body: CommentLikeRequest,
    user: ActiveUser,
    db: DBSession,
) -> CommentLikeResponse | MessageResponse:
    """Toggle like/dislike on a comment."""
    try:
        result = await comment_crud.toggle_like(db, user.id, comment_id, body.is_like)
    except ValueError as e:
        raise NotFoundError(str(e)) from None
    if result is None:
        return MessageResponse(detail="Reaction removed")
    return CommentLikeResponse.model_validate(result)


@router.get("/comments/{comment_id}/likes")
async def get_comment_likes(comment_id: int, db: DBSession) -> CommentLikesStats:
    """Get like/dislike counts for a comment."""
    comment = await comment_crud.get(db, comment_id)
    if comment is None:
        raise NotFoundError("Comment not found")
    likes, dislikes = await comment_crud.get_likes_stats(db, comment_id)
    return CommentLikesStats(likes=likes, dislikes=dislikes)
