import math
from collections.abc import Sequence
from typing import Self

from pydantic import BaseModel


class MessageResponse(BaseModel):
    detail: str


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int

    @classmethod
    def create(
        cls, *, items: Sequence[T], total: int, page: int, per_page: int
    ) -> Self:
        pages = math.ceil(total / per_page) if total else 0
        return cls(
            items=list(items),
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )
