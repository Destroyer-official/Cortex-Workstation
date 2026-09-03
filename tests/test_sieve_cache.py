"""Unit tests for the NSDI 2024 SIEVE Cache Algorithm."""

import threading
import pytest
from cortex_unified.system_tools.sieve_cache import SieveCache


def test_sieve_basic_put_get():
    cache = SieveCache[str, int](capacity=3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)

    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.get("nonexistent") is None
    assert cache.size == 3


def test_sieve_eviction_order():
    """Verify SIEVE eviction semantics:
    Insert A, B, C (cap=3). Access A.
    Insert D -> B has visited=0, so B should be evicted before A.
    """
    cache = SieveCache[str, str](capacity=3)
    cache.put("A", "valA")
    cache.put("B", "valB")
    cache.put("C", "valC")

    # Access A so A.visited = True
    assert cache.get("A") == "valA"

    # Put D: trigger eviction. B is older than C, visited=False.
    # Eviction candidate at tail is A (visited=True -> flipped to False), moves to B (visited=False -> evicted).
    cache.put("D", "valD")

    assert cache.size == 3
    assert cache.contains("A")
    assert cache.contains("C")
    assert cache.contains("D")
    assert not cache.contains("B")


def test_sieve_stats_and_hit_ratio():
    cache = SieveCache[str, int](capacity=2)
    cache.put("x", 10)
    cache.put("y", 20)

    # 2 hits
    cache.get("x")
    cache.get("y")
    # 2 misses
    cache.get("z")
    cache.get("w")

    st = cache.stats()
    assert st["algorithm"] == "SIEVE"
    assert st["hits"] == 2
    assert st["misses"] == 2
    assert st["hit_ratio"] == 50.0


def test_sieve_delete_and_clear():
    cache = SieveCache[int, str](capacity=5)
    cache.put(1, "one")
    cache.put(2, "two")
    assert cache.delete(1) is True
    assert cache.delete(999) is False
    assert cache.size == 1

    cache.clear()
    assert cache.size == 0
    assert cache.get(2) is None


def test_sieve_concurrency_safety():
    cache = SieveCache[int, int](capacity=50)

    def worker(offset: int):
        for i in range(100):
            k = (offset + i) % 70
            cache.put(k, k * 2)
            _ = cache.get(k)

    threads = [threading.Thread(target=worker, args=(t * 20,)) for t in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert cache.size <= 50
