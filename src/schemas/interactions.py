from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from schemas.movies import MovieListItemResponse


class CommentCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    parent_id: int | None = None


class CommentAuthor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie_id: int
    parent_id: int | None = None
    content: str
    created_at: datetime
    user: CommentAuthor


class CommentLikeRequest(BaseModel):
    is_like: bool


class CommentLikeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    comment_id: int
    is_like: bool
    created_at: datetime


class CommentLikesStats(BaseModel):
    likes: int
    dislikes: int


class RatingRequest(BaseModel):
    score: int = Field(ge=1, le=10)


class RatingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    movie_id: int
    score: int
    created_at: datetime


class MovieRatingResponse(BaseModel):
    average_rating: float | None = None
    total_ratings: int


class BookmarkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie_id: int
    added_at: datetime


class BookmarkWithMovieResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    added_at: datetime
    movie: MovieListItemResponse
