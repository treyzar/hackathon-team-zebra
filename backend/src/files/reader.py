"""Reads uploaded text files (e.g. large programming tests) for the worker."""

import asyncio
from collections import OrderedDict

from files import storage
from files.models import File, FileStatus


class CachedFileReader:
    """Returns file contents as text, keeping the most recently used files in
    memory up to ``max_bytes``. Uploaded files do not change, so entries never
    go stale."""

    def __init__(self, session_factory, max_bytes: int):
        self._session_factory = session_factory
        self._max_bytes = max_bytes
        self._cache: OrderedDict[int, str] = OrderedDict()
        self._sizes: dict[int, int] = {}
        self._used = 0
        # One download per file even if several runs need it at once.
        self._locks: dict[int, asyncio.Lock] = {}

    async def text(self, file_id: int) -> str:
        if file_id in self._cache:
            self._cache.move_to_end(file_id)
            return self._cache[file_id]
        lock = self._locks.setdefault(file_id, asyncio.Lock())
        async with lock:
            if file_id in self._cache:
                return self._cache[file_id]
            data = await self._load(file_id)
        self._locks.pop(file_id, None)
        text = data.decode("utf-8")  # tests are text; a bad file is an error
        self._put(file_id, text, len(data))
        return text

    async def _load(self, file_id: int) -> bytes:
        async with self._session_factory() as db:
            file = await db.get(File, file_id)
        if not file or file.status != FileStatus.READY:
            raise FileNotFoundError(f"File {file_id} is not available")
        return await storage.read_object(file.storage_key)

    def _put(self, file_id: int, text: str, size: int) -> None:
        if size > self._max_bytes:
            return  # too big to cache, still returned to the caller
        self._cache[file_id] = text
        self._sizes[file_id] = size
        self._used += size
        while self._used > self._max_bytes:
            old_id, _ = self._cache.popitem(last=False)
            self._used -= self._sizes.pop(old_id)
