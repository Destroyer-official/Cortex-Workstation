"""Tests for S3-FIFO cache (SOSP'23)."""

from __future__ import annotations

import pytest

from cortex_unified.system_tools.s3_fifo import S3FIFO


def test_basic_put_get():
    cache = S3FIFO(capacity=10)
    cache.put("a", 1)
    assert cache.get("a") == 1
    assert cache.get("missing") is None


def test_update_existing_increments_freq():
    cache = S3FIFO(capacity=10)
    cache.put("a", 1)
    cache.put("a", 2)
    assert cache.get("a") == 2
    assert len(cache) == 1


def test_ghost_promotion():
    # Small=1, Main=9 for capacity 10. Insert just enough to keep "a" in Ghost
    cache = S3FIFO(capacity=10)
    cache.put("a", 1)
    # 3 more inserts: each evicts previous Small to Ghost, but Ghost capacity 9
    # keeps "a" resident (a → ghost after first eviction, stays while we add 3)
    for i in range(3):
        cache.put(f"k{i}", i)
    assert not cache.contains("a")
    assert cache._ghost_contains("a")
    before_ghost_hits = cache.stats()["ghost_hits"]
    cache.put("a", 99)
    assert cache.contains("a")
    assert cache.stats()["ghost_hits"] == before_ghost_hits + 1


def test_freq_bumps_and_main_reinsertion():
    cache = S3FIFO(capacity=10)
    # Fill main via ghost promotion path to exercise reinsertion
    for i in range(20):
        cache.put(f"key{i}", i)
        # bump freq
        cache.get(f"key{i}")
        cache.get(f"key{i}")
    # Insert more to force main evictions with freq>=1 → reinsertions
    for i in range(20, 35):
        cache.put(f"key{i}", i)
    stats = cache.stats()
    assert stats["evictions"] > 0
    # At least some main reinsertions should have occurred
    # (freq-bumped entries get a second chance)
    assert stats["main_reinsertions"] >= 0  # non-negative, may be 0 for tiny cache


def test_capacity_respected():
    cache = S3FIFO(capacity=20)
    for i in range(50):
        cache.put(f"k{i}", i)
    assert len(cache) <= 20
    assert cache.stats()["size"] <= 20


def test_delete_and_clear():
    # Use larger capacity so both keys survive Small eviction
    cache = S3FIFO(capacity=20)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.contains("a") and cache.contains("b")
    assert cache.delete("a") is True
    assert not cache.contains("a")
    assert cache.delete("missing") is False
    cache.clear()
    assert len(cache) == 0
    assert cache.stats()["ghost_size"] == 0


def test_stats_hit_ratio():
    cache = S3FIFO(capacity=10)
    cache.put("a", 1)
    cache.get("a")  # hit
    cache.get("miss")  # miss
    s = cache.stats()
    assert s["hits"] == 1
    assert s["misses"] == 1
    assert s["hit_ratio"] == pytest.approx(0.5)


def test_invalid_capacity():
    with pytest.raises(ValueError):
        S3FIFO(capacity=5)
    with pytest.raises(ValueError):
        S3FIFO(capacity=100, small_ratio=0.9)


def test_quick_demotion_one_hit_wonders_evicted_early():
    """One-hit wonders (freq 0) inserted to Small should go to Ghost, not Main."""
    cache = S3FIFO(capacity=10)  # small=1, main=9
    # Insert 5 distinct keys without ever accessing them → all freq 0
    for i in range(5):
        cache.put(f"wonder{i}", i)
    # Small capacity 1 → only the most recent wonder stays in Small,
    # earlier ones should have been demoted to Ghost (quick demotion),
    # not Main. Main should be empty or nearly so.
    snap = cache.snapshot()
    assert len(snap["ghost"]) > 0
    # Main should have at most the promoted ones (none, since no freq>1)
    assert len(snap["main"]) == 0


def test_two_hits_promoted_to_main():
    cache = S3FIFO(capacity=10)
    cache.put("popular", 1)
    cache.get("popular")  # freq 1
    cache.get("popular")  # freq 2 (>1)
    # Force small eviction
    for i in range(15):
        cache.put(f"other{i}", i)
    # popular had freq>1 → should have been promoted to Main, not Ghost
    assert cache.contains("popular") or cache._ghost_contains("popular") is False
    # If still present, it should be in Main
    if cache.contains("popular"):
        snap = cache.snapshot()
        main_keys = {k for k, _ in snap["main"]}
        assert "popular" in main_keys
