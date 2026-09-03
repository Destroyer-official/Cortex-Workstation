"""SIEVE Cache Eviction Algorithm.

Reference:
    "SIEVE is Simpler than LRU: an Efficient Turn-Key Eviction Algorithm for Web Caches"
    Juncheng Yang, Yazhuo Zhang, Yao Yue, Ymir Vigfusson, K.V. Rashmi
    USENIX NSDI 2024 (Community Award Winner).

Characteristics:
    - Superior miss ratio compared to LRU, FIFO, ARC, and 2Q across wide trace distributions.
    - Zero lock contention on cache hits: hits simply flip a single `visited` bit without moving nodes.
    - O(1) amortized insertion, eviction, and lookup.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class SieveNode(Generic[K, V]):
    """Internal doubly-linked list node for SIEVE cache."""
    __slots__ = ("key", "value", "visited", "prev", "next")

    def __init__(self, key: K, value: V) -> None:
        """Initialize Sieve Node."""
        self.key: K = key
        self.value: V = value
        self.visited: bool = False
        self.prev: Optional[SieveNode[K, V]] = None
        self.next: Optional[SieveNode[K, V]] = None

    def __repr__(self) -> str:
        return f"SieveNode(key={self.key!r}, visited={self.visited})"
        """__repr__."""
        """__repr__."""


class SieveCache(Generic[K, V]):
    """Production thread-safe implementation of the NSDI 2024 SIEVE Cache Algorithm."""

    def __init__(self, capacity: int) -> None:
        """Initialize Sieve Cache."""
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self.capacity: int = capacity
        self._table: Dict[K, SieveNode[K, V]] = {}
        self._head: Optional[SieveNode[K, V]] = None  # Most recently inserted
        self._tail: Optional[SieveNode[K, V]] = None  # Oldest inserted
        self._hand: Optional[SieveNode[K, V]] = None  # Eviction hand pointer
        self._lock = threading.RLock()

        # Operational Metrics
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """Lookup key in cache. On hit, flips `visited = True` without linked-list mutation."""
        with self._lock:
            node = self._table.get(key)
            if node is not None:
                node.visited = True
                self._hits += 1
                return node.value
            self._misses += 1
            return default

    def contains(self, key: K) -> bool:
        """Check if key exists in cache without mutating hit counters or visited bit."""
        with self._lock:
            return key in self._table

    def put(self, key: K, value: V) -> None:
        """Insert or update a key-value pair. Evicts using SIEVE algorithm if full."""
        with self._lock:
            if key in self._table:
                node = self._table[key]
                node.value = value
                node.visited = True
                return

            if len(self._table) >= self.capacity:
                self._evict()

            node = SieveNode(key, value)
            self._insert_head(node)
            self._table[key] = node

    def _insert_head(self, node: SieveNode[K, V]) -> None:
        """Insert node at head (most recent insertion point)."""
        node.next = self._head
        node.prev = None
        if self._head is not None:
            self._head.prev = node
        self._head = node
        if self._tail is None:
            self._tail = node

    def _remove_node(self, node: SieveNode[K, V]) -> None:
        """Remove node from doubly linked list and advance hand if pointing to it."""
        if self._hand is node:
            self._hand = node.prev

        if node.prev is not None:
            node.prev.next = node.next
        else:
            self._head = node.next

        if node.next is not None:
            node.next.prev = node.prev
        else:
            self._tail = node.prev

        node.prev = None
        node.next = None

    def _evict(self) -> Optional[Tuple[K, V]]:
        """Run SIEVE eviction loop. Returns (evicted_key, evicted_value) or None."""
        o = self._hand if self._hand is not None else self._tail
        while o is not None and o.visited:
            o.visited = False
            o = o.prev if o.prev is not None else self._tail

        if o is not None:
            self._hand = o.prev
            self._remove_node(o)
            self._table.pop(o.key, None)
            self._evictions += 1
            return (o.key, o.value)
        return None

    def delete(self, key: K) -> bool:
        """Explicitly remove a key from cache."""
        with self._lock:
            node = self._table.pop(key, None)
            if node is not None:
                self._remove_node(node)
                return True
            return False

    def clear(self) -> None:
        """Purge all entries and reset hand."""
        with self._lock:
            self._table.clear()
            self._head = None
            self._tail = None
            self._hand = None

    @property
    def size(self) -> int:
        """Size."""
        with self._lock:
            return len(self._table)

    @property
    def hit_ratio(self) -> float:
        """Hit ratio."""
        with self._lock:
            total = self._hits + self._misses
            return (self._hits / total) if total > 0 else 0.0

    def stats(self) -> Dict[str, Any]:
        """Return operational cache statistics."""
        with self._lock:
            return {
                "algorithm": "SIEVE",
                "capacity": self.capacity,
                "size": len(self._table),
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_ratio": round(self.hit_ratio * 100, 2),
            }

    def keys(self) -> List[K]:
        """Return snapshot of currently cached keys."""
        with self._lock:
            return list(self._table.keys())
