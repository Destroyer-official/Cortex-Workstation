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
    """Groups related helpers: init, repr."""
    __slots__ = ("key", "value", "visited", "prev", "next")

    def __init__(self, key: K, value: V) -> None:
        """Initialize Sieve Node.

        Initializes the instance and configures internal state.

        Args:
            key (K): The key parameter.
            value (V): The value parameter.
        """
        self.key: K = key
        self.value: V = value
        self.visited: bool = False
        self.prev: Optional[SieveNode[K, V]] = None
        self.next: Optional[SieveNode[K, V]] = None

    def __repr__(self) -> str:
        """Return an informative string representation of the instance.

        Formats key attributes and state flags into a concise string suitable for debugging and diagnostics.

        Returns:
            str: Formatted string or path.
        """
        return f"SieveNode(key={self.key!r}, visited={self.visited})"


class SieveCache(Generic[K, V]):
    """Groups related helpers: init, get, contains, put, insert head, remove node, evict, delete."""

    def __init__(self, capacity: int) -> None:
        """Initialize Sieve Cache.

        Initializes the instance and configures internal state.

        Args:
            capacity (int): The capacity parameter.
        """
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
        """Get helper. Returns node.value.

        Args:
        key (K): The key parameter.
        default (Optional[V]): The default parameter.

        Returns:
        Optional[V]: Result of the operation.
        """
        with self._lock:
            node = self._table.get(key)
            if node is not None:
                node.visited = True
                self._hits += 1
                return node.value
            self._misses += 1
            return default

    def contains(self, key: K) -> bool:
        """Contains helper. Returns key in self._table.

        Args:
        key (K): The key parameter.

        Returns:
        bool: True if the operation succeeded, False otherwise.
        """
        with self._lock:
            return key in self._table

    def put(self, key: K, value: V) -> None:
        """Put helper. Returns if len(...).

        Args:
        key (K): The key parameter.
        value (V): The value parameter.
        """
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
        """Insert node at head (most recent insertion point).

        Args:
        node (SieveNode[K, V]): The node parameter.
        """
        node.next = self._head
        node.prev = None
        if self._head is not None:
            self._head.prev = node
        self._head = node
        if self._tail is None:
            self._tail = node

    def _remove_node(self, node: SieveNode[K, V]) -> None:
        """Remove node from doubly linked list and advance hand if pointing to it.

        Args:
        node (SieveNode[K, V]): The node parameter.
        """
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
        """Evict helper. Returns (o.key, o.value).

        Returns:
        Optional[Tuple[K, V]]: Result of the operation.
        """
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
        """Delete helper. Returns True.

        Args:
        key (K): The key parameter.

        Returns:
        bool: True if the operation succeeded, False otherwise.
        """
        with self._lock:
            node = self._table.pop(key, None)
            if node is not None:
                self._remove_node(node)
                return True
            return False

    def clear(self) -> None:
        """Clear helper."""
        with self._lock:
            self._table.clear()
            self._head = None
            self._tail = None
            self._hand = None

    @property
    def size(self) -> int:
        """Size helper. Returns len(self._table).

        Returns:
        int: Result of the operation.
        """
        with self._lock:
            return len(self._table)

    @property
    def hit_ratio(self) -> float:
        """Hit ratio helper. Returns (...).

        Returns:
        float: Result of the operation.
        """
        with self._lock:
            total = self._hits + self._misses
            return (self._hits / total) if total > 0 else 0.0

    def stats(self) -> Dict[str, Any]:
        """Stats helper.

        Returns:
        Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
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
        """Keys helper. Returns list(self._table.keys()).

        Returns:
        List[K]: List of processed items or identifiers.
        """
        with self._lock:
            return list(self._table.keys())
