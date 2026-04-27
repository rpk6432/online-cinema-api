import time

from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from core.config import settings
from core.security import verify_password
from crud.user import user_crud
from database.session import async_session, engine
from models.cart import Cart, CartItem
from models.interaction import Bookmark, Comment, CommentLike, Notification, Rating
from models.movie import Certification, Director, Genre, Movie, Star
from models.order import Order, OrderItem
from models.payment import Payment
from models.user import User, UserGroup, UserGroupEnum, UserProfile


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        email, password = str(form.get("username", "")), str(form.get("password", ""))

        async with async_session() as db:
            user = await user_crud.get_by_email(db, email)
            if user is None or not verify_password(password, user.hashed_password):
                return False
            if not user.is_active:
                return False
            await db.refresh(user, attribute_names=["group"])
            if user.group.name != UserGroupEnum.ADMIN.value:
                return False

            request.session.update({"user_id": user.id})
            return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        user_id = request.session.get("user_id")
        if user_id is None:
            return False

        verified_at = request.session.get("verified_at", 0)
        if time.time() - verified_at < 300:  # 5 min cache
            return True

        async with async_session() as db:
            user = await user_crud.get_with_group(db, user_id)
            if user is None or not user.is_active:
                return False
            if user.group.name != UserGroupEnum.ADMIN.value:
                return False

        request.session["verified_at"] = time.time()
        return True


# Model views


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.email, User.is_active, User.created_at]
    column_searchable_list = [User.email]
    column_sortable_list = [User.id, User.email, User.created_at]
    can_create = False
    can_delete = False


class UserGroupAdmin(ModelView, model=UserGroup):
    column_list = [UserGroup.id, UserGroup.name]
    can_create = False
    can_delete = False


class UserProfileAdmin(ModelView, model=UserProfile):
    column_list = [
        UserProfile.id,
        UserProfile.user_id,
        UserProfile.first_name,
        UserProfile.last_name,
    ]
    can_create = False
    can_delete = False


class MovieAdmin(ModelView, model=Movie):
    column_list = [Movie.id, Movie.name, Movie.year, Movie.imdb, Movie.price]
    column_searchable_list = [Movie.name]
    column_sortable_list = [Movie.id, Movie.name, Movie.year, Movie.imdb]


class GenreAdmin(ModelView, model=Genre):
    column_list = [Genre.id, Genre.name]
    column_searchable_list = [Genre.name]


class StarAdmin(ModelView, model=Star):
    column_list = [Star.id, Star.name]
    column_searchable_list = [Star.name]


class DirectorAdmin(ModelView, model=Director):
    column_list = [Director.id, Director.name]
    column_searchable_list = [Director.name]


class CertificationAdmin(ModelView, model=Certification):
    column_list = [Certification.id, Certification.name]


class OrderAdmin(ModelView, model=Order):
    column_list = [
        Order.id,
        Order.user_id,
        Order.status,
        Order.total_amount,
        Order.created_at,
    ]
    column_sortable_list = [Order.id, Order.created_at]
    can_create = False


class OrderItemAdmin(ModelView, model=OrderItem):
    column_list = [
        OrderItem.id,
        OrderItem.order_id,
        OrderItem.movie_id,
        OrderItem.price_at_order,
    ]
    can_create = False
    can_delete = False


class PaymentAdmin(ModelView, model=Payment):
    column_list = [
        Payment.id,
        Payment.order_id,
        Payment.status,
        Payment.amount,
        Payment.created_at,
    ]
    column_sortable_list = [Payment.id, Payment.created_at]
    can_create = False


class CartAdmin(ModelView, model=Cart):
    column_list = [Cart.id, Cart.user_id, Cart.created_at]
    can_create = False


class CartItemAdmin(ModelView, model=CartItem):
    column_list = [CartItem.id, CartItem.cart_id, CartItem.movie_id, CartItem.added_at]
    can_create = False


class CommentAdmin(ModelView, model=Comment):
    column_list = [
        Comment.id,
        Comment.user_id,
        Comment.movie_id,
        Comment.content,
        Comment.created_at,
    ]
    column_sortable_list = [Comment.id, Comment.created_at]


class CommentLikeAdmin(ModelView, model=CommentLike):
    column_list = [
        CommentLike.id,
        CommentLike.user_id,
        CommentLike.comment_id,
        CommentLike.is_like,
    ]
    can_create = False


class RatingAdmin(ModelView, model=Rating):
    column_list = [Rating.id, Rating.user_id, Rating.movie_id, Rating.score]
    can_create = False


class BookmarkAdmin(ModelView, model=Bookmark):
    column_list = [Bookmark.id, Bookmark.user_id, Bookmark.movie_id, Bookmark.added_at]
    can_create = False


class NotificationAdmin(ModelView, model=Notification):
    column_list = [
        Notification.id,
        Notification.user_id,
        Notification.type,
        Notification.is_read,
    ]
    column_sortable_list = [Notification.id, Notification.created_at]
    can_create = False


def setup_admin(app: FastAPI) -> None:
    """Mount SQLAdmin on the FastAPI application."""
    auth_backend = AdminAuth(secret_key=settings.admin_secret_key)
    admin = Admin(app, engine, authentication_backend=auth_backend)

    admin.add_view(UserAdmin)
    admin.add_view(UserGroupAdmin)
    admin.add_view(UserProfileAdmin)
    admin.add_view(MovieAdmin)
    admin.add_view(GenreAdmin)
    admin.add_view(StarAdmin)
    admin.add_view(DirectorAdmin)
    admin.add_view(CertificationAdmin)
    admin.add_view(OrderAdmin)
    admin.add_view(OrderItemAdmin)
    admin.add_view(PaymentAdmin)
    admin.add_view(CartAdmin)
    admin.add_view(CartItemAdmin)
    admin.add_view(CommentAdmin)
    admin.add_view(CommentLikeAdmin)
    admin.add_view(RatingAdmin)
    admin.add_view(BookmarkAdmin)
    admin.add_view(NotificationAdmin)
