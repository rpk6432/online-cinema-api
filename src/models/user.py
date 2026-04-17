import enum
from datetime import date, datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class UserGroupEnum(enum.StrEnum):
    USER = "USER"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"


class GenderEnum(enum.StrEnum):
    MAN = "MAN"
    WOMAN = "WOMAN"


class UserGroup(Base):
    __tablename__ = "user_groups"

    name: Mapped[str] = mapped_column(String(50), unique=True)

    users: Mapped[list[User]] = relationship(back_populates="group")


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    group_id: Mapped[int] = mapped_column(ForeignKey("user_groups.id"))

    group: Mapped[UserGroup] = relationship(back_populates="users")
    profile: Mapped[UserProfile] = relationship(
        back_populates="user", uselist=False
    )
    activation_token: Mapped[ActivationToken] = relationship(
        back_populates="user", uselist=False
    )
    password_reset_token: Mapped[PasswordResetToken] = relationship(
        back_populates="user", uselist=False
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user"
    )

    @property
    def group_name(self) -> str:
        """Shortcut for serialization — returns the group's display name."""
        return self.group.name


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    first_name: Mapped[str | None] = mapped_column(String(150))
    last_name: Mapped[str | None] = mapped_column(String(150))
    avatar: Mapped[str | None] = mapped_column(String(500))
    gender: Mapped[GenderEnum | None] = mapped_column()
    date_of_birth: Mapped[date | None] = mapped_column()
    info: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="profile")


class ActivationToken(Base):
    __tablename__ = "activation_tokens"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    token: Mapped[str] = mapped_column(String(255), unique=True)
    expires_at: Mapped[datetime] = mapped_column()

    user: Mapped[User] = relationship(back_populates="activation_token")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    token: Mapped[str] = mapped_column(String(255), unique=True)
    expires_at: Mapped[datetime] = mapped_column()

    user: Mapped[User] = relationship(back_populates="password_reset_token")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    token: Mapped[str] = mapped_column(String(500), unique=True)
    expires_at: Mapped[datetime] = mapped_column()

    user: Mapped[User] = relationship(back_populates="refresh_tokens")
