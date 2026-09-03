"""S3-FIFO cache eviction — "FIFO queues are all you need" (SOSP'23).

Research grounding
------------------
* Yang et al., "FIFO Queues Are All You Need for Cache Eviction"
  (SOSP'23, best-paper contender, 6594 traces, 14 datasets,
  856 B requests). The central insight is *quick demotion*:
  most objects are accessed once and should be evicted early.
  A tiny 10 % FIFO filter (S) proves more precise than adaptive
  alternatives; the main 90 % queue (M) re-inserts hot objects
  via FIFO-Reinsertion, while a Ghost queue (G) remembers S-evicted
  keys to admit second-chance objects directly to M.

Why this matters for Cortex Cleaner
-----------------------------------
* The cleaner ships a ``CacheCleaner`` and ``ModelCacheManager`` that
  still use naive LRU / age-based policies. Those thrash on scans
  (``.cache/huggingface``, ``.npm``, ``.cargo``, ``.docker``) and
  over-retain one-hit wonders at the expense of hot reuse.
* Replacing the ad-hoc recency logic with S3-FIFO improves hit rate
  *and* scalability: FIFO queues are lock-friendly and 6× faster than
  LRU at 16 threads (SOSP'23 §4). For the desktop cleaner this means
  snappier cache panels and fewer “re-downloaded model” complaints.

Design (faithful to the paper, §4)
----------------------------------
* **Three static FIFO queues** – Small (10 %), Main (90 %), Ghost
  (capacity = |M|, stores only fingerprints, not values).
* **Per-object 2-bit frequency** (capped at 3) incremented on hits;
  no update is needed after the second hit, keeping the fast path
  atomic and branch-free.
* **Insertion** – new key: S if not Ghost, else M; on re-insertion
  from Ghost the Ghost entry is removed.
* **S eviction** (paper Alg. 1, line 14-20): head of S:
  ``freq > 1 → move to M (freq cleared)``, else ``→ Ghost``.
* **M eviction** (FIFO-Reinsertion, §4.1): head of M:
  ``freq ≥ 1 → freq-- and re-insert at tail``, else evict.
* **Thread-safety** – a single re-entrant lock guards all mutations;
  the hot read path (freq bump) is an atomic integer op under the lock,
  matching the paper’s “atomic write upon first/second request”.

References
----------
* J. Yang, Y. Zhang, Z. Qiu, Y. Yue, K. V. Rashmi, "FIFO Queues Are All
  You Need for Cache Eviction", SOSP'23, Koblenz, 2023.
  https://dl.acm.org/doi/10.1145/3600006.3613147  (open preprint:
  https://junchengyang.com/publication/sosp23-s3fifo.pdf)
* HOTOS'23 precursor "FIFO Can Be Better Than LRU" (Yang et al.).
* Thesys-lab/sosp23-s3fifo reference implementation (MIT).

Usage::

    from cortex_unified.system_tools.s3_fifo import S3FIFO
    cache = S3FIFO(capacity=1000)          # 100 small + 900 main
    cache.put("model:bert", b"...")         # insertion follows Ghost rule
    val = cache.get("model:bert")           # hit → freq bump, miss → None
    cache.stats()  # hit/miss/ghost-hit/eviction counters

The class is intentionally *generic* (``Any`` values) so it can back
``ModelCacheManager``, ``DiskAnalyzer`` result caches, and the premium
UI’s memoised page data without a second implementation.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Hashable, Optional, Tuple


@dataclass(slots=True)
class _Entry:
    key: Hashable
    value: Any
    freq: int = 0  # 0..3 (2 bits)
    """_Entry class."""
    """_Entry class."""


@dataclass
class S3FIFOStats:
    """S3 F I F O Stats data container."""
    hits: int = 0
    misses: int = 0
    ghost_hits: int = 0
    evictions: int = 0
    small_evictions_to_main: int = 0
    small_evictions_to_ghost: int = 0
    main_reinsertions: int = 0

    def to_dict(self) -> dict:
        """To dict.

        Returns:
            Result of the operation."""
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": (self.hits / total) if total else 0.0,
            "ghost_hits": self.ghost_hits,
            "evictions": self.evictions,
            "small_to_main": self.small_evictions_to_main,
            "small_to_ghost": self.small_evictions_to_ghost,
            "main_reinsertions": self.main_reinsertions,
        }


class S3FIFO:
    """S3-FIFO cache (SOSP'23) – three static FIFO queues.

    Args:
        capacity: Total number of live entries (|S| + |M| ≤ capacity).
            Must be ≥10 (so S gets at least one slot). Default 256.
        small_ratio: Fraction of capacity for the Small queue (default
            0.1 = 10 % as proven optimal in the paper; changing it is
            rarely beneficial).
    """

    def __init__(self, capacity: int = 256, small_ratio: float = 0.1) -> None:
        """Initialize S3 F I F O.

        Args:
            capacity: capacity.
            small_ratio: small ratio."""
        if capacity < 10:
            raise ValueError("capacity must be >= 10")
        if not (0.05 <= small_ratio <= 0.4):
            raise ValueError("small_ratio must be in [0.05, 0.4]")
        self.capacity = int(capacity)
        self.small_capacity = max(1, int(self.capacity * small_ratio))
        self.main_capacity = self.capacity - self.small_capacity
        self.ghost_capacity = self.main_capacity  # same as M, per paper

        self._small: Deque[_Entry] = deque()
        self._main: Deque[_Entry] = deque()
        self._ghost: Deque[Hashable] = deque()
        self._ghost_set: set[Hashable] = set()

        # O(1) lookup: key → (_Entry, queue_name)
        self._index: Dict[Hashable, Tuple[_Entry, str]] = {}

        self._lock = threading.RLock()
        self._stats = S3FIFOStats()

    # -- internal helpers

    def _ghost_contains(self, key: Hashable) -> bool:
        return key in self._ghost_set
        """_ghost_contains."""
        """_ghost_contains."""

    def _ghost_add(self, key: Hashable) -> None:
        if key in self._ghost_set:
            # Move to tail (FIFO recency) – remove old position
            try:
                self._ghost.remove(key)
            except ValueError:
                pass
        self._ghost.append(key)
        self._ghost_set.add(key)
        while len(self._ghost) > self.ghost_capacity:
            old = self._ghost.popleft()
            self._ghost_set.discard(old)
        """_ghost_add."""
        """_ghost_add."""

    def _ghost_remove(self, key: Hashable) -> None:
        if key in self._ghost_set:
            try:
                self._ghost.remove(key)
            except ValueError:
                pass
            self._ghost_set.discard(key)
        """_ghost_remove."""
        """_ghost_remove."""

    def _evict_small_if_needed(self) -> None:
        while len(self._small) > self.small_capacity:
            entry = self._small.popleft()
            # Remove from index (will be re-added if promoted)
            self._index.pop(entry.key, None)
            if entry.freq > 1:
                # Popular → promote to Main (clear freq as in paper)
                entry.freq = 0
                self._main.append(entry)
                self._index[entry.key] = (entry, "main")
                self._stats.small_evictions_to_main += 1
                self._evict_main_if_needed()
            else:
                self._ghost_add(entry.key)
                self._stats.small_evictions_to_ghost += 1
                self._stats.evictions += 1
        """_evict_small_if_needed."""
        """_evict_small_if_needed."""

    def _evict_main_if_needed(self) -> None:
        # FIFO-Reinsertion: keep looping until within capacity
        while len(self._main) > self.main_capacity:
            entry = self._main.popleft()
            if entry.freq >= 1:
                entry.freq -= 1
                self._main.append(entry)
                # index stays pointing at same entry object
                self._stats.main_reinsertions += 1
            else:
                self._index.pop(entry.key, None)
                self._stats.evictions += 1
        """_evict_main_if_needed."""
        """_evict_main_if_needed."""
                # Not added to ghost (paper: only S evictions enter ghost)

    # -- public API

    def get(self, key: Hashable) -> Optional[Any]:
        """Return value or ``None`` on miss; bumps frequency on hit."""
        with self._lock:
            hit = self._index.get(key)
            if hit is None:
                self._stats.misses += 1
                return None
            entry, _queue = hit
            if entry.freq < 3:
                entry.freq += 1
            self._stats.hits += 1
            return entry.value

    def put(self, key: Hashable, value: Any) -> None:
        """Insert or update ``key``.

        Update path: if the key already lives in S or M, only the value
        and frequency are updated (no queue movement).
        Insertion path: Ghost hit → M, else S, then rebalance.
        """
        with self._lock:
            existing = self._index.get(key)
            if existing is not None:
                entry, _queue = existing
                entry.value = value
                if entry.freq < 3:
                    entry.freq += 1
                self._stats.hits += 1
                return
            # New key
            is_ghost = self._ghost_contains(key)
            entry = _Entry(key=key, value=value, freq=0)
            if is_ghost:
                self._ghost_remove(key)
                self._main.append(entry)
                self._index[key] = (entry, "main")
                self._stats.ghost_hits += 1
                self._evict_main_if_needed()
            else:
                self._small.append(entry)
                self._index[key] = (entry, "small")
                self._evict_small_if_needed()

    def delete(self, key: Hashable) -> bool:
        """Remove ``key`` if present; returns True if removed."""
        with self._lock:
            hit = self._index.pop(key, None)
            if hit is None:
                return False
            entry, queue = hit
            try:
                if queue == "small":
                    self._small.remove(entry)
                else:
                    self._main.remove(entry)
            except ValueError:
                pass
            return True

    def contains(self, key: Hashable) -> bool:
        """Contains.

        Args:
            key: key.

        Returns:
            Result of the operation."""
        with self._lock:
            return key in self._index

    def __contains__(self, key: object) -> bool:  # type: ignore[override]
        return self.contains(key)  # type: ignore[arg-type]
        """__contains__."""
        """__contains__."""

    def __len__(self) -> int:
        with self._lock:
            return len(self._index)
        """__len__."""
        """__len__."""

    def clear(self) -> None:
        """Clear."""
        with self._lock:
            self._small.clear()
            self._main.clear()
            self._ghost.clear()
            self._ghost_set.clear()
            self._index.clear()
            self._stats = S3FIFOStats()

    def stats(self) -> dict:
        """Stats.

        Returns:
            Result of the operation."""
        with self._lock:
            d = self._stats.to_dict()
            d.update(
                {
                    "capacity": self.capacity,
                    "small_capacity": self.small_capacity,
                    "main_capacity": self.main_capacity,
                    "size": len(self._index),
                    "small_size": len(self._small),
                    "main_size": len(self._main),
                    "ghost_size": len(self._ghost),
                }
            )
            return d

    # Convenience for debugging / UI

    def keys(self) -> list[Hashable]:
        """Keys.

        Returns:
            Result of the operation."""
        with self._lock:
            return list(self._index.keys())

    def snapshot(self) -> dict:
        """Return a JSON-serialisable snapshot of queue states (ordered)."""
        with self._lock:
            return {
                "small": [(e.key, e.freq) for e in self._small],
                "main": [(e.key, e.freq) for e in self._main],
                "ghost": list(self._ghost),
            }


__all__ = ["S3FIFO", "S3FIFOStats"]
