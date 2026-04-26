from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import delete

from celery_app import app
from database.celery_session import celery_session
from models.user import ActivationToken, PasswordResetToken, RefreshToken

TOKEN_MODELS = (ActivationToken, PasswordResetToken, RefreshToken)


@app.task
def cleanup_expired_tokens() -> None:
    now = datetime.now(UTC)

    with celery_session() as session:
        for model in TOKEN_MODELS:
            deleted = session.execute(
                delete(model).where(model.expires_at < now).returning(model.id)
            ).all()
            if deleted:
                logger.info(
                    "Deleted {} expired {}",
                    len(deleted),
                    model.__tablename__,
                )
        session.commit()
