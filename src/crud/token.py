import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import ActivationToken, PasswordResetToken, RefreshToken


async def create_activation_token(
    db: AsyncSession, user_id: int, hours: int = 24
) -> ActivationToken:
    """Create activation token, replacing any existing one for this user."""
    await db.execute(delete(ActivationToken).where(ActivationToken.user_id == user_id))
    token = ActivationToken(
        user_id=user_id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(UTC) + timedelta(hours=hours),
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def get_activation_token(db: AsyncSession, token: str) -> ActivationToken | None:
    """Return valid (non-expired) activation token or None."""
    result = await db.execute(
        select(ActivationToken).where(
            ActivationToken.token == token,
            ActivationToken.expires_at > datetime.now(UTC),
        )
    )
    return result.scalar_one_or_none()


async def delete_activation_token(db: AsyncSession, token_obj: ActivationToken) -> None:
    await db.delete(token_obj)
    await db.commit()


async def create_password_reset_token(
    db: AsyncSession, user_id: int, hours: int = 1
) -> PasswordResetToken:
    """Create reset token, replacing any existing one for this user."""
    await db.execute(
        delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
    )
    token = PasswordResetToken(
        user_id=user_id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(UTC) + timedelta(hours=hours),
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def get_password_reset_token(
    db: AsyncSession, token: str
) -> PasswordResetToken | None:
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == token,
            PasswordResetToken.expires_at > datetime.now(UTC),
        )
    )
    return result.scalar_one_or_none()


async def delete_password_reset_token(
    db: AsyncSession, token_obj: PasswordResetToken
) -> None:
    await db.delete(token_obj)
    await db.commit()


async def create_refresh_token_record(
    db: AsyncSession, user_id: int, token: str, days: int = 7
) -> RefreshToken:
    record = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=datetime.now(UTC) + timedelta(days=days),
    )
    db.add(record)
    await db.commit()
    return record


async def get_refresh_token(db: AsyncSession, token: str) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == token,
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )
    return result.scalar_one_or_none()


async def delete_refresh_token(db: AsyncSession, token: str) -> None:
    await db.execute(delete(RefreshToken).where(RefreshToken.token == token))
    await db.commit()
