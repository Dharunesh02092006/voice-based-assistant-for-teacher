"""Exponential-backoff retry decorator shared by every API client wrapper."""

from __future__ import annotations

import functools
import random
import time
from typing import Callable, TypeVar

from utils.logger import get_logger

T = TypeVar("T")
logger = get_logger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 0.75,
    max_delay: float = 8.0,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retries the wrapped function with jittered exponential backoff.

    Args:
        max_retries: total attempts (including the first) before giving up.
        base_delay: seconds to wait before the first retry.
        max_delay: cap on the backoff delay.
        retry_on: exception types that should trigger a retry; anything
            else propagates immediately.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempt = 0
            while True:
                attempt += 1
                try:
                    return func(*args, **kwargs)
                except retry_on as exc:  # type: ignore[misc]
                    if attempt >= max_retries:
                        logger.error(
                            "%s failed after %d attempt(s): %s", func.__qualname__, attempt, exc
                        )
                        raise
                    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    delay += random.uniform(0, delay * 0.25)  # jitter
                    logger.warning(
                        "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                        func.__qualname__,
                        attempt,
                        max_retries,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

        return wrapper

    return decorator
