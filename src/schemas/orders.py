from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from schemas.movies import MovieListItemResponse


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie: MovieListItemResponse
    price_at_order: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    total_amount: Decimal
    created_at: datetime
    items: list[OrderItemResponse]


class OrderListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    total_amount: Decimal
    total_items: int
    created_at: datetime
