from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from core.config import Settings
from core.security import hash_password
from crud.user import user_crud
from models.user import ActivationToken
from tasks.cleanup import cleanup_expired_tokens
from tasks.email import send_activation_email, send_password_reset_email

test_settings = Settings(_env_file=".env.test")
sync_url = test_settings.database_url.replace("+asyncpg", "+psycopg2")
sync_engine = create_engine(sync_url, poolclass=NullPool)
sync_session = sessionmaker(sync_engine, expire_on_commit=False)


async def test_cleanup_deletes_only_expired_tokens(db: AsyncSession) -> None:
    expired_user = await user_crud.create_user(
        db, "expired@example.com", hash_password("Test1234")
    )
    valid_user = await user_crud.create_user(
        db, "valid@example.com", hash_password("Test1234")
    )

    now = datetime.now(UTC)

    db.add(
        ActivationToken(
            user_id=expired_user.id,
            token="expired-act",
            expires_at=now - timedelta(hours=1),
        )
    )
    db.add(
        ActivationToken(
            user_id=valid_user.id,
            token="valid-act",
            expires_at=now + timedelta(hours=24),
        )
    )
    await db.commit()

    with patch("tasks.cleanup.celery_session", sync_session):
        cleanup_expired_tokens()

    db.expire_all()
    result = await db.execute(select(ActivationToken))
    remaining = result.scalars().all()
    assert len(remaining) == 1
    assert remaining[0].token == "valid-act"


async def test_send_activation_email_calls_smtp() -> None:
    with patch("tasks.email.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        send_activation_email("user@example.com", "test-token-123")

        mock_server.send_message.assert_called_once()
        msg = mock_server.send_message.call_args[0][0]
        assert msg["To"] == "user@example.com"
        assert msg["Subject"] == "Activate your account"


async def test_send_password_reset_email_calls_smtp() -> None:
    with patch("tasks.email.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        send_password_reset_email("user@example.com", "reset-token-456")

        mock_server.send_message.assert_called_once()
        msg = mock_server.send_message.call_args[0][0]
        assert msg["To"] == "user@example.com"
        assert msg["Subject"] == "Reset your password"
