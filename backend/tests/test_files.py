"""Storage wrapper and the worker's file cache, without S3 or a database."""

import asyncio
import io

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from files import storage
from files.reader import CachedFileReader
from files.storage import StorageError


def client_error(code):
    return ClientError({"Error": {"Code": code, "Message": code}}, "GetObject")


class FakeS3:
    def __init__(self, objects=None, error=None):
        self.objects = objects or {}
        self.error = error

    def get_object(self, Bucket, Key):
        if self.error:
            raise self.error
        if Key not in self.objects:
            raise client_error("NoSuchKey")
        return {"Body": io.BytesIO(self.objects[Key])}

    def head_object(self, Bucket, Key):
        if self.error:
            raise self.error
        if Key not in self.objects:
            raise client_error("404")
        return {"ContentLength": len(self.objects[Key])}


@pytest.fixture
def s3(monkeypatch):
    fake = FakeS3({"a": b"hello"})
    monkeypatch.setattr(storage, "_internal", lambda: fake)
    return fake


async def test_read_object(s3):
    assert await storage.read_object("a") == b"hello"
    with pytest.raises(FileNotFoundError):
        await storage.read_object("missing")


@pytest.mark.parametrize(
    "error",
    [client_error("AccessDenied"), EndpointConnectionError(endpoint_url="http://s3")],
)
async def test_read_object_failures_are_retryable(s3, error):
    s3.error = error
    with pytest.raises(StorageError):
        await storage.read_object("a")


async def test_object_size(s3):
    assert await storage.object_size("a") == 5
    assert await storage.object_size("missing") is None
    s3.error = client_error("AccessDenied")
    with pytest.raises(ClientError):
        await storage.object_size("a")


def test_presigned_urls_point_at_public_endpoint():
    from config import settings

    up = storage.presign_upload("submission/x", "text/plain")
    down = storage.presign_download("submission/x", "отчёт.pdf")
    assert up.startswith(
        f"{settings.s3_public_endpoint}/{settings.s3_bucket}/submission/x?"
    )
    # Non-ASCII file names are encoded (RFC 5987).
    assert "filename%2A%3DUTF-8%27%27" in down


class CountingReader(CachedFileReader):
    def __init__(self, files, max_bytes):
        super().__init__(session_factory=None, max_bytes=max_bytes)
        self.files, self.loads = files, []

    async def _load(self, file_id):
        self.loads.append(file_id)
        await asyncio.sleep(0.01)
        return self.files[file_id]


async def test_reader_caches():
    r = CountingReader({1: b"one", 2: b"two"}, max_bytes=100)
    assert [await r.text(1), await r.text(2), await r.text(1)] == ["one", "two", "one"]
    assert r.loads == [1, 2]


async def test_reader_evicts_least_recently_used():
    r = CountingReader({1: b"a" * 40, 2: b"b" * 40, 3: b"c" * 40}, max_bytes=100)
    await r.text(1)
    await r.text(2)
    await r.text(1)  # 1 is now more recent than 2
    await r.text(3)  # over the limit: 2 is evicted
    await r.text(1)
    await r.text(2)
    assert r.loads == [1, 2, 3, 2]


async def test_reader_does_not_cache_huge_files():
    r = CountingReader({1: b"x" * 200}, max_bytes=100)
    await r.text(1)
    await r.text(1)
    assert r.loads == [1, 1]


async def test_reader_downloads_once_for_concurrent_requests():
    r = CountingReader({1: b"one"}, max_bytes=100)
    assert await asyncio.gather(*(r.text(1) for _ in range(5))) == ["one"] * 5
    assert r.loads == [1]


async def test_reader_rejects_binary_files():
    r = CountingReader({1: b"\xff\xfe"}, max_bytes=100)
    with pytest.raises(UnicodeDecodeError):
        await r.text(1)
