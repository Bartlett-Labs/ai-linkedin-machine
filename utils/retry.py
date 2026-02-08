"""
Retry with exponential backoff for Playwright actions.

Wraps async functions so transient failures (slow page loads, network
hiccups) get retried instead of silently skipped.
"""

import asyncio
import functools
import logging
import random
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_async(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    **kwargs,
) -> T:
    """Call an async function with exponential backoff on failure.

    Args:
        func: The async function to call.
        max_retries: Number of retry attempts.
        base_delay: Initial delay in seconds (doubles each retry).
        max_delay: Cap on delay.
        jitter: Add randomness to delay.

    Returns:
        The return value of func.

    Raises:
        The last exception if all retries fail.
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt == max_retries:
                logger.error(
                    "All %d retries exhausted for %s: %s",
                    max_retries, func.__name__, e,
                )
                raise

            delay = min(base_delay * (2 ** attempt), max_delay)
            if jitter:
                delay = delay * (0.5 + random.random())

            logger.warning(
                "Attempt %d/%d failed for %s: %s. Retrying in %.1fs",
                attempt + 1, max_retries, func.__name__, e, delay,
            )
            await asyncio.sleep(delay)


def with_retry(max_retries: int = 3, base_delay: float = 2.0):
    """Decorator to add retry logic to async functions."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_async(
                func, *args,
                max_retries=max_retries,
                base_delay=base_delay,
                **kwargs,
            )
        return wrapper
    return decorator
