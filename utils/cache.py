"""
Lightweight in-memory TTL cache.

Used to avoid re-spending API calls (and money/latency) when the teacher
re-asks the same question, or when Streamlit reruns the script and would
otherwise re-trigger an identical classification/generation call.

Deliberately dependency-free (no redis/memcached) since this is a
single-process classroom MVP. Swap this module out for a real cache backend
if the app needs to scale across multiple workers.
"""

from __future__ import annotations

import functools
import hashlib
import json
import threading
import time
from typing import Any, Callable, TypeVar

from config.settings import settings

T = TypeVar("T")


class TTLCache:
    """A minimal, thread-safe time-to-live cache."""

    def __init__(self, ttl_seconds: int | None = None) -> None:
        self._ttl = ttl_seconds if ttl_seconds is not None else settings.cache_ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.time() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


def _make_cache_key(prefix: str, args: tuple, kwargs: dict) -> str:
    try:
        payload = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    except TypeError:
        payload = str(args) + str(kwargs)
    digest = hashlib.md5(payload.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def cached(cache: TTLCache, prefix: str | None = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that caches a function's return value for `cache`'s TTL,
    keyed on a hash of its arguments. Skips caching `self` by convention
    (assumes first positional arg of bound methods is the instance, which
    is intentionally excluded from the key so two instances with identical
    config share a cache entry)."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        key_prefix = prefix or func.__qualname__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            cache_args = args[1:] if args else args  # drop `self`
            key = _make_cache_key(key_prefix, cache_args, kwargs)
            hit = cache.get(key)
            if hit is not None:
                return hit  # type: ignore[return-value]
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result

        return wrapper

    return decorator
