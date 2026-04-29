import uuid

import aioboto3
from fastapi import UploadFile

from core.config import settings

_session = aioboto3.Session()


def _get_client_kwargs() -> dict[str, str]:
    return {
        "endpoint_url": settings.s3_endpoint_url,
        "aws_access_key_id": settings.s3_access_key,
        "aws_secret_access_key": settings.s3_secret_key,
    }


async def upload_avatar(file: UploadFile, user_id: int) -> str:
    """Upload avatar to S3/MinIO, return the object key."""
    parts = file.filename.rsplit(".", 1) if file.filename else []
    ext = parts[-1] if len(parts) == 2 else "jpg"
    key = f"avatars/{user_id}/{uuid.uuid4().hex}.{ext}"

    async with _session.client("s3", **_get_client_kwargs()) as s3:
        await s3.upload_fileobj(
            file.file,
            settings.s3_bucket_name,
            key,
            ExtraArgs={"ContentType": file.content_type or "image/jpeg"},
        )

    return key


async def delete_avatar(key: str) -> None:
    """Delete avatar from S3/MinIO."""
    async with _session.client("s3", **_get_client_kwargs()) as s3:
        await s3.delete_object(Bucket=settings.s3_bucket_name, Key=key)


def get_avatar_url(key: str) -> str:
    """Build public URL for an avatar stored in MinIO."""
    return f"{settings.s3_public_url}/{settings.s3_bucket_name}/{key}"
