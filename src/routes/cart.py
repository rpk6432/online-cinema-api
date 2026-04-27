from decimal import Decimal

from fastapi import APIRouter, status

from core.dependencies import ActiveUser, DBSession
from core.exceptions import AlreadyExistsError, NotFoundError
from crud.cart import cart_crud
from crud.movie import movie_crud
from crud.order import order_crud
from models.order import OrderStatusEnum
from schemas.cart import AddToCartRequest, CartItemResponse, CartResponse

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("")
async def get_cart(user: ActiveUser, db: DBSession) -> CartResponse:
    """Return the current user's cart."""
    cart = await cart_crud.get_cart(db, user.id)
    if cart is None or not cart.items:
        return CartResponse(items=[], total_items=0, total_amount=Decimal("0.00"))

    items = [CartItemResponse.model_validate(item) for item in cart.items]
    total = sum((item.movie.price for item in cart.items), Decimal("0.00"))
    return CartResponse(
        items=items,
        total_items=len(items),
        total_amount=total,
    )


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def add_item(
    body: AddToCartRequest, user: ActiveUser, db: DBSession
) -> CartItemResponse:
    """Add a movie to the cart."""
    movie = await movie_crud.get(db, body.movie_id)
    if movie is None:
        raise NotFoundError("Movie not found")

    order_status = await order_crud.get_movie_order_status(db, user.id, body.movie_id)
    if order_status == OrderStatusEnum.PAID:
        raise AlreadyExistsError("Movie already purchased")
    if order_status == OrderStatusEnum.PENDING:
        raise AlreadyExistsError("Movie is in a pending order. Cancel the order first.")

    cart = await cart_crud.get_or_create_cart(db, user.id)

    existing = await cart_crud.get_item(db, cart.id, body.movie_id)
    if existing is not None:
        raise AlreadyExistsError("Movie already in cart")

    item = await cart_crud.add_item(db, cart, body.movie_id)
    return CartItemResponse.model_validate(item)


@router.delete("/items/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(movie_id: int, user: ActiveUser, db: DBSession) -> None:
    """Remove a movie from the cart."""
    removed = await cart_crud.remove_item(db, user.id, movie_id)
    if not removed:
        raise NotFoundError("Movie not in cart")


@router.delete("/clear", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(user: ActiveUser, db: DBSession) -> None:
    """Remove all items from the cart."""
    await cart_crud.clear_cart(db, user.id)
