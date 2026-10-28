"""In-memory fixed-window rate limiter.

Good enough for a single API instance. When running several instances, replace
this with a Redis-backed implementation exposing the same `hit` method.
"""

import threading
import time
from collections import defaultdict


class RateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[float, int]] = defaultdict(lambda: (0.0, 0))

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Record a hit. Returns False when the caller is over the limit."""
        now = time.monotonic()
        with self._lock:
            started, count = self._windows[key]
            if now - started >= window_seconds:
                started, count = now, 0
            count += 1
            self._windows[key] = (started, count)
            return count <= limit
