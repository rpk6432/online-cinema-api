from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from schemas.movies import MovieListItemResponse


class AddToCartRequest(BaseModel):
    movie_id: int


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie: MovieListItemResponse
    added_at: datetime


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    total_items: int
    total_amount: Decimal
