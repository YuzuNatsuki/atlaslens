"""In-memory TTL cache for AI responses.

We don't need a real cache backend for the hackathon demo — a process-local
dict with a TTL is enough to make repeated demo clicks instant after the first
warm-up. Keyed by an arbitrary string the caller produces.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any


class TTLCache:
    def __init__(self, default_ttl_seconds: float = 600.0) -> None:
        self._default_ttl = default_ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, key: str) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    async def get_or_compute(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        *,
        ttl: float | None = None,
    ) -> Any:
        now = time.monotonic()
        existing = self._store.get(key)
        if existing is not None and existing[0] > now:
            return existing[1]

        async with self._lock_for(key):
            existing = self._store.get(key)
            if existing is not None and existing[0] > time.monotonic():
                return existing[1]
            value = await factory()
            expires_at = time.monotonic() + (ttl if ttl is not None else self._default_ttl)
            self._store[key] = (expires_at, value)
            return value

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)


cache = TTLCache(default_ttl_seconds=600.0)
