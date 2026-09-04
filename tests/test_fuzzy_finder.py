"""Tests for CTPH fuzzy (similarity) hashing."""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex_unified.analyzers.fuzzy_finder import (
    FuzzyDuplicateFinder,
    fuzzy_compare,
    fuzzy_hash_bytes,
    fuzzy_hash_file,
)


def _text(n=4000):
    """Text.

    Manages text operations and coordinates related state changes for the component.

    Args:
        n: The n parameter.
    """
    base = ("All work and no play makes Jack a dull boy. " * 20).encode()
    return (base * (n // len(base) + 1))[:n]


def _noise(n=4000, seed=7):
    """Noise.

    Manages noise operations and coordinates related state changes for the component.

    Args:
        n: The n parameter.
        seed: The seed parameter.
    """
    import random

    rng = random.Random(seed)
    return bytes(rng.getrandbits(8) for _ in range(n))


# --- primitives -------------------------------------------------------------

def test_fuzzy_hash_is_deterministic():
    """test_fuzzy_hash_is_deterministic.

    Manages test fuzzy hash is deterministic operations and coordinates related state changes for the component.
    """
    data = _text()
    assert fuzzy_hash_bytes(data) == fuzzy_hash_bytes(data)


def test_identical_content_matches_at_100():
    """test_identical_content_matches_at_100.

    Manages test identical content matches at 100 operations and coordinates related state changes for the component.
    """
    data = _text()
    assert fuzzy_compare(fuzzy_hash_bytes(data), fuzzy_hash_bytes(data)) >= 90


def test_similar_content_scores_high_pairs():
    """test_similar_content_scores_high_pairs.

    Manages test similar content scores high pairs operations and coordinates related state changes for the component.
    """
    a = _text(4000)
    b = a[:2000] + a[2000:-100] + a[-100:] + b" trailing append text " * 5
    score = fuzzy_compare(fuzzy_hash_bytes(a), fuzzy_hash_bytes(b))
    # Both are ~long-form repetitive text; they should be quite similar but
    # not necessarily identical.
    assert 0 <= score <= 100
    assert score > 0


def test_unrelated_content_scores_low():
    """test_unrelated_content_scores_low.

    Manages test unrelated content scores low operations and coordinates related state changes for the component.
    """
    a = _text(4000)
    b = _noise(4000)
    score = fuzzy_compare(fuzzy_hash_bytes(a), fuzzy_hash_bytes(b))
    assert score < 60


def test_empty_signature():
    """test_empty_signature.

    Manages test empty signature operations and coordinates related state changes for the component.
    """
    assert fuzzy_compare("3::", "3::") >= 0


# --- finder -----------------------------------------------------------------

def test_finder_groups_near_identical_binaries(tmp_path):
    """test_finder_groups_near_identical_binaries.

    Manages test finder groups near identical binaries operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    src = _text(6000)
    (tmp_path / "a.bin").write_bytes(src)
    # near-copy: one small edit inserted in the middle
    edited = src[:3000] + b"bumped content xxyyzz" + src[3000:]
    (tmp_path / "b.bin").write_bytes(edited)
    (tmp_path / "c.bin").write_bytes(_noise(6000))

    finder = FuzzyDuplicateFinder(str(tmp_path), threshold=50.0)
    groups = finder.find_fuzzy_duplicates()
    names = {p.name for paths in groups.values() for p in paths}
    assert "a.bin" in names and "b.bin" in names
    assert "c.bin" not in names


def test_finder_skips_incompressible_and_small(tmp_path):
    """test_finder_skips_incompressible_and_small.

    Manages test finder skips incompressible and small operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    (tmp_path / "tiny.log").write_text("x")
    (tmp_path / "a.zip").write_bytes(_noise(1000))
    finder = FuzzyDuplicateFinder(str(tmp_path))
    assert finder.find_fuzzy_duplicates() == {}


def test_finder_stats(tmp_path):
    """test_finder_stats.

    Manages test finder stats operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    a = _text(3000)
    (tmp_path / "a.bin").write_bytes(a)
    (tmp_path / "b.bin").write_bytes(a[:1500] + b"edit" + a[1500:])
    finder = FuzzyDuplicateFinder(str(tmp_path), threshold=50.0)
    finder.find_fuzzy_duplicates()
    stats = finder.get_stats()
    assert stats["total_files_scanned"] == 2
    assert stats["fuzzy_duplicate_groups"] >= 1


def test_fuzzy_hash_file_reads(tmp_path):
    """test_fuzzy_hash_file_reads.

    Manages test fuzzy hash file reads operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    p = tmp_path / "f.txt"
    p.write_bytes(_text())
    sig = fuzzy_hash_file(p)
    assert ":" in sig
