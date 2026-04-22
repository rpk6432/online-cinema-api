from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from schemas.catalogs import (
    CertificationResponse,
    DirectorResponse,
    GenreResponse,
    StarResponse,
)


class MovieListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: UUID
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    price: Decimal
    certification: CertificationResponse | None = None
    genres: list[GenreResponse] = []


class MovieResponse(MovieListItemResponse):
    meta_score: float | None = None
    gross: float | None = None
    description: str
    stars: list[StarResponse] = []
    directors: list[DirectorResponse] = []
    average_rating: float | None = None
    total_ratings: int = 0
    total_comments: int = 0


class MovieCreateRequest(BaseModel):
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: float | None = None
    gross: float | None = None
    description: str
    price: Decimal
    certification_id: int | None = None
    genre_ids: list[int] = []
    star_ids: list[int] = []
    director_ids: list[int] = []


class MovieUpdateRequest(BaseModel):
    name: str | None = None
    year: int | None = None
    time: int | None = None
    imdb: float | None = None
    votes: int | None = None
    meta_score: float | None = None
    gross: float | None = None
    description: str | None = None
    price: Decimal | None = None
    certification_id: int | None = None
    genre_ids: list[int] | None = None
    star_ids: list[int] | None = None
    director_ids: list[int] | None = None
