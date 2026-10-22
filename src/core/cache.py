"""Small in-process cache for identical planning requests.

The cache is content-addressed: the key is a SHA-256 of the canonical JSON
body. Repeating a brief returns the stored plan without calling a model.
Entries expire by TTL and the map evicts the least-recently used key once it
passes ``max_entries``.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from typing import Any


def plan_cache_key(payload: dict[str, Any]) -> str:
    """Hash a JSON-ready payload into a stable cache key.

    Args:
        payload: A ``model_dump(mode="json")`` dictionary.

    Returns:
        A hex SHA-256 digest.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ResponseCache:
    """Thread-safe LRU cache with a time-to-live on each entry."""

    def __init__(self, max_entries: int, ttl_seconds: int) -> None:
        """Create an empty cache.

        Args:
            max_entries: Maximum stored plans. Must be at least 1.
            ttl_seconds: Seconds before an unread entry is stale.
        """
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._items: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> dict[str, Any] | None:
        """Return a stored payload, or ``None`` on a miss or expiry.

        A hit refreshes the least-recently-used position. Expired entries are
        removed as they are touched.
        """
        now = time.monotonic()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                self.misses += 1
                return None
            stored_at, payload = item
            if now - stored_at > self.ttl_seconds:
                del self._items[key]
                self.misses += 1
                return None
            self._items.move_to_end(key)
            self.hits += 1
            return payload

    def set(self, key: str, payload: dict[str, Any]) -> None:
        """Store a JSON-ready payload and evict the oldest key if needed."""
        now = time.monotonic()
        with self._lock:
            self._items[key] = (now, payload)
            self._items.move_to_end(key)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)

    def stats(self) -> dict[str, int]:
        """Return counters safe to expose on the health endpoint."""
        with self._lock:
            return {
                "entries": len(self._items),
                "hits": self.hits,
                "misses": self.misses,
            }
