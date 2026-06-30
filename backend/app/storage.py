"""S3-compatible object storage client.

Targets MinIO locally and DigitalOcean Spaces in production — identical API
because both are S3-compatible. Switch by changing SPACES_* env vars.
"""
from __future__ import annotations

import io
from functools import lru_cache

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


@lru_cache(maxsize=1)
def _presign_client():
    """Client used exclusively for presigned URL generation.

    Uses spaces_presign_endpoint_url if set (e.g. http://localhost:9000 in dev)
    so the signed URL is reachable from a browser, not the internal Docker hostname.
    Falls back to spaces_endpoint_url when not set (production, where they match).
    """
    endpoint = settings.spaces_presign_endpoint_url or settings.spaces_endpoint_url
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
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


def presigned_url(key: str, expires_in: int = 3600, *, filename: str | None = None) -> str:
    client = _presign_client()
    params: dict = {"Bucket": settings.spaces_bucket, "Key": key}
    if filename:
        params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
    return client.generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=expires_in,
    )


def public_url(key: str) -> str:
    return f"{settings.spaces_public_url.rstrip('/')}/{key}"


def delete_object(key: str) -> None:
    client = _client()
    client.delete_object(Bucket=settings.spaces_bucket, Key=key)
