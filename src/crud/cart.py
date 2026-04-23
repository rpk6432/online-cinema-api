from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.cart import Cart, CartItem
from models.movie import Movie


class CRUDCart:
    async def get_cart(self, db: AsyncSession, user_id: int) -> Cart | None:
        """Return user's cart with items and movies loaded."""
        result = await db.execute(
            select(Cart)
            .where(Cart.user_id == user_id)
            .options(
                selectinload(Cart.items)
                .selectinload(CartItem.movie)
                .selectinload(Movie.genres),
                selectinload(Cart.items)
                .selectinload(CartItem.movie)
                .selectinload(Movie.certification),
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_cart(self, db: AsyncSession, user_id: int) -> Cart:
        """Return existing cart or create a new one."""
        cart = await self.get_cart(db, user_id)
        if cart is not None:
            return cart

        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart, attribute_names=["items"])
        return cart

    async def add_item(self, db: AsyncSession, cart: Cart, movie_id: int) -> CartItem:
        """Add a movie to the cart."""
        item = CartItem(cart_id=cart.id, movie_id=movie_id)
        db.add(item)
        await db.commit()

        result = await db.execute(
            select(CartItem)
            .where(CartItem.id == item.id)
            .options(
                selectinload(CartItem.movie).selectinload(Movie.genres),
                selectinload(CartItem.movie).selectinload(Movie.certification),
            )
        )
        return result.scalar_one()

    async def get_item(
        self, db: AsyncSession, cart_id: int, movie_id: int
    ) -> CartItem | None:
        """Return a specific cart item."""
        result = await db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart_id,
                CartItem.movie_id == movie_id,
            )
        )
        return result.scalar_one_or_none()

    async def remove_item(self, db: AsyncSession, user_id: int, movie_id: int) -> bool:
        """Remove a movie from the user's cart. Return True if removed."""
        cart = await self.get_cart(db, user_id)
        if cart is None:
            return False

        item = await self.get_item(db, cart.id, movie_id)
        if item is None:
            return False

        await db.delete(item)
        await db.commit()
        return True

    async def clear_cart(self, db: AsyncSession, user_id: int) -> None:
        """Remove all items from the user's cart."""
        cart = await self.get_cart(db, user_id)
        if cart is None:
            return

        await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        await db.commit()

    async def is_movie_purchased(
        self, db: AsyncSession, user_id: int, movie_id: int
    ) -> bool:
        """Check if the user has already purchased this movie.

        TODO: implement when order tracking is available.
        """
        return False


cart_crud = CRUDCart()
