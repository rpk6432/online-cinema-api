from pydantic import BaseModel


class MessageResponse(BaseModel):
    detail: str


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int
