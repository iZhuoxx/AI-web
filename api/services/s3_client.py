"""AWS S3 helper utilities."""

from __future__ import annotations

from typing import Any, Dict, Optional

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from api.settings import settings


def get_s3_client() -> BaseClient:
    """Return a configured boto3 S3 client."""

    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        raise RuntimeError("AWS credentials are not configured. Set them in .env or the CSV file.")

    session = boto3.session.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION,
    )

    return session.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        config=Config(signature_version="s3v4"),
    )


def create_presigned_upload(key: str, expires_in: int = 900, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate a presigned POST for uploading objects from the frontend."""

    client = get_s3_client()
    if not settings.AWS_S3_BUCKET:
        raise RuntimeError("AWS_S3_BUCKET must be configured to use uploads")
    fields = extra or {}
    conditions = []
    if extra:
        for field, value in extra.items():
            conditions.append({field: value})

    return client.generate_presigned_post(
        Bucket=settings.AWS_S3_BUCKET,
        Key=key,
        Fields=fields,
        Conditions=conditions,
        ExpiresIn=expires_in,
    )


def create_presigned_download(key: str, expires_in: int = 900) -> str:
    """Generate a presigned download URL for an existing object."""

    client = get_s3_client()
    if not settings.AWS_S3_BUCKET:
        raise RuntimeError("AWS_S3_BUCKET must be configured to use downloads")
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )
