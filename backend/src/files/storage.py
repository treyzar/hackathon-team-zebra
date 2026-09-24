"""S3-compatible object storage (SeaweedFS in docker compose)."""

import asyncio
from functools import cache
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from config import settings


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


async def object_size(key: str) -> int | None:
    """Size of the uploaded object, or None if it does not exist."""

    def head() -> int | None:
        try:
            resp = _internal().head_object(Bucket=settings.s3_bucket, Key=key)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                return None
            raise
        return resp["ContentLength"]

    return await asyncio.to_thread(head)
