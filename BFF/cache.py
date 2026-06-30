import time
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class TtlCache:
    def __init__(self, name: str):
        self.name = name
        self._store: dict[str, CacheEntry] = {}
        self._lock = Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self.misses += 1
                return None
            if time.monotonic() >= entry.expires_at:
                del self._store[key]
                self.misses += 1
                return None
            self.hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        with self._lock:
            self._store[key] = CacheEntry(
                value=value,
                expires_at=time.monotonic() + ttl_seconds,
            )

    def invalidate(self, prefix: str | None = None) -> int:
        with self._lock:
            if prefix is None:
                count = len(self._store)
                self._store.clear()
                return count
            keys = [key for key in self._store if key.startswith(prefix)]
            for key in keys:
                del self._store[key]
            return len(keys)

    def stats(self) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "entries": len(self._store),
                "hits": self.hits,
                "misses": self.misses,
            }


evaluation_cache = TtlCache("evaluation")
flag_list_cache = TtlCache("flag_list")
