from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.cart import CartItem
from models.movie import Movie
from models.order import Order, OrderItem, OrderStatusEnum


class CRUDOrder:
    _order_options = (
        selectinload(Order.items)
        .selectinload(OrderItem.movie)
        .selectinload(Movie.genres),
        selectinload(Order.items)
        .selectinload(OrderItem.movie)
        .selectinload(Movie.certification),
    )

    async def create_order(
        self, db: AsyncSession, user_id: int, cart_items: list[CartItem]
    ) -> Order:
        """Create an order from cart items with price snapshots."""
        order_items = [
            OrderItem(movie_id=item.movie_id, price_at_order=item.movie.price)
            for item in cart_items
        ]
        total = sum((item.price_at_order for item in order_items), Decimal("0.00"))

        order = Order(
            user_id=user_id,
            total_amount=total,
            items=order_items,
        )
        db.add(order)
        await db.commit()

        result = await db.execute(
            select(Order).where(Order.id == order.id).options(*self._order_options)
        )
        return result.scalar_one()

    async def get_order(
        self, db: AsyncSession, order_id: int, user_id: int
    ) -> Order | None:
        """Return a user's order with items."""
        result = await db.execute(
            select(Order)
            .where(Order.id == order_id, Order.user_id == user_id)
            .options(*self._order_options)
        )
        return result.scalar_one_or_none()

    async def get_order_by_id(self, db: AsyncSession, order_id: int) -> Order | None:
        """Return an order by ID without ownership check."""
        result = await db.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()

    async def get_user_orders(
        self,
        db: AsyncSession,
        user_id: int,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Order]:
        """Return paginated list of user's orders."""
        query = select(Order).where(Order.user_id == user_id)
        if status is not None:
            query = query.where(Order.status == status)
        query = (
            query.options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_user_orders(
        self, db: AsyncSession, user_id: int, status: str | None = None
    ) -> int:
        """Count user's orders, optionally filtered by status."""
        query = select(func.count()).select_from(Order).where(Order.user_id == user_id)
        if status is not None:
            query = query.where(Order.status == status)
        result = await db.execute(query)
        return result.scalar_one()

    async def cancel_order(self, db: AsyncSession, order: Order) -> None:
        """Cancel a pending order."""
        order.status = OrderStatusEnum.CANCELED
        await db.commit()

    async def mark_order_paid(self, db: AsyncSession, order: Order) -> None:
        """Mark an order as paid."""
        order.status = OrderStatusEnum.PAID
        await db.commit()

    async def get_movie_order_status(
        self, db: AsyncSession, user_id: int, movie_id: int
    ) -> str | None:
        """Return the status of an active order containing this movie."""
        result = await db.execute(
            select(Order.status)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(
                Order.user_id == user_id,
                OrderItem.movie_id == movie_id,
                Order.status != OrderStatusEnum.CANCELED,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()


order_crud = CRUDOrder()
