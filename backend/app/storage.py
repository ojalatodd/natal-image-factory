"""S3-compatible object storage client.

Targets MinIO locally and DigitalOcean Spaces in production — identical API
because both are S3-compatible. Switch by changing SPACES_* env vars.
"""
from __future__ import annotations

import io

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import settings


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.spaces_endpoint_url,
        region_name=settings.spaces_region,
        aws_access_key_id=settings.spaces_key,
        aws_secret_access_key=settings.spaces_secret,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket() -> None:
    client = _client()
    try:
        client.head_bucket(Bucket=settings.spaces_bucket)
    except ClientError:
        client.create_bucket(Bucket=settings.spaces_bucket)


def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    client = _client()
    client.put_object(
        Bucket=settings.spaces_bucket,
        Key=key,
        Body=io.BytesIO(data),
        ContentType=content_type,
    )
    return key


def download_bytes(key: str) -> bytes:
    client = _client()
    obj = client.get_object(Bucket=settings.spaces_bucket, Key=key)
    return obj["Body"].read()


def presigned_url(key: str, expires_in: int = 3600) -> str:
    client = _client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.spaces_bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def public_url(key: str) -> str:
    return f"{settings.spaces_public_url.rstrip('/')}/{key}"
