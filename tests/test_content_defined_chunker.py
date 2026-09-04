"""Tests for FastCDC / VectorCDC content-defined chunking."""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex_unified.analyzers.content_defined_chunker import (
    ContentDefinedChunker,
    chunk_similarity,
    file_chunks,
    gear_chunk,
    jaccard,
)


# --- chunker primitives ---

def test_gear_chunk_deterministic():
    """test_gear_chunk_deterministic.

    Manages test gear chunk deterministic operations and coordinates related state changes for the component.
    """
    data = b"hello world " * 2000
    a = gear_chunk(data)
    b = gear_chunk(data)
    assert a == b
    assert all(c.length >= 2048 for c in a)  # min_size
    assert all(c.length <= 65536 for c in a)


def test_gear_chunk_shift_resistant():
    """test_gear_chunk_shift_resistant.

    Manages test gear chunk shift resistant operations and coordinates related state changes for the component.
    """
    import random
    rnd = random.Random(0xC0FFEE)
    base = bytes(rnd.getrandbits(8) for _ in range(50000))
    # Insert one byte near the start – CDC should keep most chunks stable
    inserted = base[:100] + b"X" + base[100:]
    ca = gear_chunk(base)
    cb = gear_chunk(inserted)
    # Random content → ~6 chunks; insertion perturbs 1, rest should survive
    assert len(ca) >= 3 and len(cb) >= 3
    assert jaccard((c.fingerprint for c in ca), (c.fingerprint for c in cb)) >= 0.4


def test_gear_chunk_empty():
    """test_gear_chunk_empty.

    Manages test gear chunk empty operations and coordinates related state changes for the component.
    """
    assert gear_chunk(b"") == []


def test_gear_chunk_invalid_params():
    """test_gear_chunk_invalid_params.

    Manages test gear chunk invalid params operations and coordinates related state changes for the component.
    """
    with pytest.raises(ValueError):
        gear_chunk(b"data", avg_size=100, min_size=200, max_size=300)


def test_jaccard_basic():
    """test_jaccard_basic.

    Manages test jaccard basic operations and coordinates related state changes for the component.
    """
    assert jaccard([], []) == 1.0
    assert jaccard([1, 2], []) == 0.0
    assert jaccard([1, 2, 3], [1, 2, 3]) == 1.0
    assert jaccard([1, 2], [2, 3]) == pytest.approx(1/3)


def test_chunk_similarity_identical_is_one():
    """test_chunk_similarity_identical_is_one.

    Manages test chunk similarity identical is one operations and coordinates related state changes for the component.
    """
    data = b"identical content " * 1000
    assert chunk_similarity(data, data) == 1.0


def test_chunk_similarity_different_is_low():
    """test_chunk_similarity_different_is_low.

    Manages test chunk similarity different is low operations and coordinates related state changes for the component.
    """
    a = b"A" * 10000
    b = b"Z" * 10000
    assert chunk_similarity(a, b) < 0.2


def test_file_chunks_reads_file(tmp_path: Path):
    """test_file_chunks_reads_file.

    Manages test file chunks reads file operations and coordinates related state changes for the component.

    Args:
        tmp_path (Path): Filesystem path to the target file or directory.
    """
    p = tmp_path / "data.bin"
    p.write_bytes(b"file content " * 2000)
    cs = file_chunks(p)
    assert len(cs) > 0
    assert sum(c.length for c in cs) == p.stat().st_size


def test_file_chunks_missing_raises(tmp_path: Path):
    """test_file_chunks_missing_raises.

    Manages test file chunks missing raises operations and coordinates related state changes for the component.

    Args:
        tmp_path (Path): Filesystem path to the target file or directory.
    """
    with pytest.raises(OSError):
        file_chunks(tmp_path / "nope.bin")


# --- finder ---

def test_finder_groups_shifted_duplicates(tmp_path: Path):
    """test_finder_groups_shifted_duplicates.

    Manages test finder groups shifted duplicates operations and coordinates related state changes for the component.

    Args:
        tmp_path (Path): Filesystem path to the target file or directory.
    """
    import random
    rnd = random.Random(1)
    base = bytes(rnd.getrandbits(8) for _ in range(60000))
    # File A: base, File B: base with 1-byte insertion (shift-resistant)
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    c = tmp_path / "c.bin"
    a.write_bytes(base)
    b.write_bytes(base[:100] + b"X" + base[100:])
    c.write_bytes(bytes(rnd.getrandbits(8) for _ in range(60000)))
    finder = ContentDefinedChunker(str(tmp_path), threshold=0.4)
    groups = finder.find_cdc_duplicates()
    names = sorted(p.name for members in groups.values() for p in members)
    assert "a.bin" in names and "b.bin" in names
    for members in groups.values():
        mn = {p.name for p in members}
        if "a.bin" in mn:
            assert "c.bin" not in mn


def test_finder_excludes_non_eligible_or_empty(tmp_path: Path):
    """test_finder_excludes_non_eligible_or_empty.

    Manages test finder excludes non eligible or empty operations and coordinates related state changes for the component.

    Args:
        tmp_path (Path): Filesystem path to the target file or directory.
    """
    (tmp_path / "empty.bin").write_bytes(b"")
    (tmp_path / "image.jpg").write_bytes(b"jpg-like-but-skipped" * 1000)
    finder = ContentDefinedChunker(str(tmp_path))
    assert finder.find_cdc_duplicates() == {}


def test_finder_respects_exclude_dirs(tmp_path: Path):
    """test_finder_respects_exclude_dirs.

    Manages test finder respects exclude dirs operations and coordinates related state changes for the component.

    Args:
        tmp_path (Path): Filesystem path to the target file or directory.
    """
    sub = tmp_path / "skip"
    sub.mkdir()
    base = b"dup for skip test " * 500
    (sub / "a.bin").write_bytes(base)
    (sub / "b.bin").write_bytes(base)
    (tmp_path / "ta.bin").write_bytes(base)
    (tmp_path / "tb.bin").write_bytes(base)
    from cortex_unified.core.config import Config
    cfg = Config()
    cfg.config_data["exclude_dirs"] = ["skip"]
    finder = ContentDefinedChunker(str(tmp_path), config=cfg)
    groups = finder.find_cdc_duplicates()
    names = {p.name for members in groups.values() for p in members}
    assert not names.intersection({"a.bin", "b.bin"})
    assert "ta.bin" in names and "tb.bin" in names


def test_finder_stats(tmp_path: Path):
    """test_finder_stats.

    Manages test finder stats operations and coordinates related state changes for the component.

    Args:
        tmp_path (Path): Filesystem path to the target file or directory.
    """
    base = b"stats test " * 800
    (tmp_path / "a.bin").write_bytes(base)
    (tmp_path / "b.bin").write_bytes(base + b"X")  # still similar enough at 0.5
    finder = ContentDefinedChunker(str(tmp_path), threshold=0.4)
    finder.find_cdc_duplicates()
    stats = finder.get_stats()
    assert stats["total_files_scanned"] == 2
    assert stats["cdc_duplicate_groups"] >= 0


def test_vector_cdc_chunk_produces_valid_chunks():
    """test_vector_cdc_chunk_produces_valid_chunks.

    Manages test vector cdc chunk produces valid chunks operations and coordinates related state changes for the component.
    """
    from cortex_unified.analyzers.content_defined_chunker import vector_cdc_chunk
    data = b"VectorCDC fast test data stream " * 1000
    chunks = vector_cdc_chunk(data, avg_size=4096, min_size=1024, max_size=16384)
    assert len(chunks) > 0
    assert sum(c.length for c in chunks) == len(data)
    assert all(c.length >= 1024 or c == chunks[-1] for c in chunks)


def test_idea_inverted_index():
    """test_idea_inverted_index.

    Manages test idea inverted index operations and coordinates related state changes for the component.
    """
    import random
    from cortex_unified.analyzers.content_defined_chunker import IdeaInvertedIndex, vector_cdc_chunk
    rnd = random.Random(42)
    base = bytes(rnd.getrandbits(8) for _ in range(80000))
    data1 = base + b" unique tail 1"
    data2 = base + b" unique tail 2"
    data3 = bytes(rnd.getrandbits(8) for _ in range(80000))

    p1 = Path("/mock/file1.bin")
    p2 = Path("/mock/file2.bin")
    p3 = Path("/mock/file3.bin")

    index = IdeaInvertedIndex()
    index.insert(p1, vector_cdc_chunk(data1, avg_size=4096, min_size=1024))
    index.insert(p2, vector_cdc_chunk(data2, avg_size=4096, min_size=1024))
    index.insert(p3, vector_cdc_chunk(data3, avg_size=4096, min_size=1024))

    similar_to_1 = index.find_similar(p1, threshold=0.4)
    matched_paths = [path for path, score in similar_to_1]

    assert p2 in matched_paths
    assert p3 not in matched_paths
