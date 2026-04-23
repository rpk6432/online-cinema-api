from fastapi import APIRouter, Query, status

from core.dependencies import ActiveUser, DBSession
from core.exceptions import BadRequestError, NotFoundError
from crud.cart import cart_crud
from crud.order import order_crud
from models.order import OrderStatusEnum
from schemas.common import PaginatedResponse
from schemas.orders import OrderListItemResponse, OrderResponse

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_order(user: ActiveUser, db: DBSession) -> OrderResponse:
    """Create an order from the current cart."""
    cart = await cart_crud.get_cart(db, user.id)
    if cart is None or not cart.items:
        raise BadRequestError("Cart is empty")

    order = await order_crud.create_order(db, user.id, cart.items)
    await cart_crud.clear_cart(db, user.id)
    return OrderResponse.model_validate(order)


@router.get("")
async def list_orders(
    user: ActiveUser,
    db: DBSession,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[OrderListItemResponse]:
    """List the current user's orders."""
    offset = (page - 1) * per_page
    orders = await order_crud.get_user_orders(
        db, user.id, status_filter, offset, per_page
    )
    total = await order_crud.count_user_orders(db, user.id, status_filter)

    items = [
        OrderListItemResponse(
            id=o.id,
            status=o.status,
            total_amount=o.total_amount,
            total_items=len(o.items),
            created_at=o.created_at,
        )
        for o in orders
    ]
    return PaginatedResponse.create(
        items=items, total=total, page=page, per_page=per_page
    )


@router.get("/{order_id}")
async def get_order(order_id: int, user: ActiveUser, db: DBSession) -> OrderResponse:
    """Get order details."""
    order = await order_crud.get_order(db, order_id, user.id)
    if order is None:
        raise NotFoundError("Order not found")
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/cancel")
async def cancel_order(order_id: int, user: ActiveUser, db: DBSession) -> OrderResponse:
    """Cancel a pending order."""
    order = await order_crud.get_order(db, order_id, user.id)
    if order is None:
        raise NotFoundError("Order not found")

    if order.status == OrderStatusEnum.CANCELED:
        raise BadRequestError("Order is already canceled")
    if order.status == OrderStatusEnum.PAID:
        raise BadRequestError("Paid orders cannot be canceled")

    await order_crud.cancel_order(db, order)
    canceled = await order_crud.get_order(db, order_id, user.id)
    return OrderResponse.model_validate(canceled)
