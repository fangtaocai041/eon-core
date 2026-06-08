"""TendrilCache — simple TTL-based cache for tendril probe results."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional


class TendrilCache:
    """TTL-based cache for external source results.

    Reduces redundant API calls for identical queries.
    """

    def __init__(self, ttl_seconds: float = 3600.0, maxsize: int = 1000) -> None:
        self.ttl = ttl_seconds
        self.maxsize = maxsize
        self._store: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached entry if not expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() - entry["ts"] > self.ttl:
            del self._store[key]
            return None
        return entry["data"]

    def set(self, key: str, data: Dict[str, Any]) -> None:
        """Store entry with current timestamp.

        IF store exceeds maxsize THEN evict oldest entry.
        """
        if len(self._store) >= self.maxsize:
            oldest = min(self._store, key=lambda k: self._store[k]["ts"])
            del self._store[oldest]
        self._store[key] = {"data": data, "ts": time.monotonic()}

    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)
