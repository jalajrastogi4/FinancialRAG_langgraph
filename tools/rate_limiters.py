import time
from collections import defaultdict
from threading import Lock
from typing import Callable

from core.logging import get_logger

logger = get_logger()


class RateLimiter:
    def __init__(self, rate_per_sec: float):
        self.rate = rate_per_sec
        self.allowance = rate_per_sec
        self.last_check = time.monotonic()
        self.lock = Lock()

    def acquire(self):
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_check
            self.last_check = now

            self.allowance += elapsed * self.rate
            if self.allowance > self.rate:
                self.allowance = self.rate

            if self.allowance < 1.0:
                sleep_time = (1.0 - self.allowance) / self.rate
                logger.debug(f"Rate limit hit, sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
                self.allowance = 0
            else:
                self.allowance -= 1.0



_RATE_LIMITERS = {}


_RATE_LIMITER_LOCK = Lock()


def get_rate_limiter(tool_name: str, rate_per_sec: float) -> RateLimiter:
    """
    Get or create a rate limiter for a specific tool
    """
    if tool_name in _RATE_LIMITERS:
        return _RATE_LIMITERS[tool_name]

    with _RATE_LIMITER_LOCK:
        if tool_name not in _RATE_LIMITERS:
            logger.debug(f"Creating rate limiter for {tool_name} at {rate_per_sec} QPS")
            _RATE_LIMITERS[tool_name] = RateLimiter(rate_per_sec)

        return _RATE_LIMITERS[tool_name]