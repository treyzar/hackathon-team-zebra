"""S3-compatible object storage (SeaweedFS in docker compose)."""

import asyncio
from functools import cache
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from config import settings


class StorageError(Exception):
    """Storage is unavailable or failed; the operation may be retried."""


def _client(endpoint: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


@cache
def _internal():
    return _client(settings.s3_endpoint)


@cache
def _public():
    # Signing is local, no request is made; the URL must be browser-reachable.
    return _client(settings.s3_public_endpoint)


def presign_upload(key: str, mime: str) -> str:
    return _public().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": key, "ContentType": mime},
        ExpiresIn=settings.presigned_url_ttl_seconds,
    )


def presign_download(key: str, filename: str) -> str:
    disposition = f"attachment; filename*=UTF-8''{quote(filename)}"
    return _public().generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
            "ResponseContentDisposition": disposition,
        },
        ExpiresIn=settings.presigned_url_ttl_seconds,
    )


def _missing(e: ClientError) -> bool:
    return e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey")


async def read_object(key: str) -> bytes:
    """Whole object; FileNotFoundError if it does not exist."""

    def get() -> bytes:
        try:
            resp = _internal().get_object(Bucket=settings.s3_bucket, Key=key)
            return resp["Body"].read()
        except ClientError as e:
            if _missing(e):
                raise FileNotFoundError(key) from e
            raise StorageError(str(e)) from e
        except BotoCoreError as e:
            raise StorageError(str(e)) from e

    return await asyncio.to_thread(get)


async def object_size(key: str) -> int | None:
    """Size of the uploaded object, or None if it does not exist."""

    def head() -> int | None:
        try:
            resp = _internal().head_object(Bucket=settings.s3_bucket, Key=key)
        except ClientError as e:
            if _missing(e):
                return None
            raise
        return resp["ContentLength"]

    return await asyncio.to_thread(head)
