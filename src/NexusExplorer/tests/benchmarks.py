"""Performance benchmarks for NexusExplorer core operations.

Run with: pytest tests/benchmarks.py -v --benchmark-only
Or standalone: python tests/benchmarks.py
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable

import pytest


def _create_test_tree(root: Path, depth: int = 3, files_per_dir: int = 50, file_size: int = 1024):
    """Create a test directory tree for benchmarking."""
    for d in range(depth):
        dir_path = root / f"dir_{d}"
        dir_path.mkdir(exist_ok=True)
        for f in range(files_per_dir):
            file_path = dir_path / f"file_{f:04d}.txt"
            if not file_path.exists():
                file_path.write_bytes(os.urandom(file_size))


def _cleanup_tree(root: Path):
    """Remove test directory tree."""
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)


class BenchmarkTimer:
    """Context manager for timing operations."""

    def __init__(self, name: str):
        self.name = name
        self.elapsed_ms: float = 0
        self._start: float = 0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000

    def __repr__(self):
        return f"{self.name}: {self.elapsed_ms:.1f}ms"


# ---------------------------------------------------------------------------
# Directory listing benchmarks
# ---------------------------------------------------------------------------

class TestDirectoryListing:
    """Benchmark directory listing operations."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path / "bench_tree"
        self.root.mkdir(exist_ok=True)
        _create_test_tree(self.root, depth=3, files_per_dir=100)
        yield
        _cleanup_tree(self.root)

    def test_list_small_dir(self):
        """Benchmark listing a directory with ~100 files."""
        target = self.root / "dir_0"
        with BenchmarkTimer("list_100_files") as t:
            entries = list(target.iterdir())
        assert len(entries) >= 100
        print(f"\n  {t}")

    def test_list_medium_dir(self):
        """Benchmark listing a directory with ~500 files."""
        # Create a dir with more files
        big_dir = self.root / "big_dir"
        big_dir.mkdir(exist_ok=True)
        for i in range(500):
            (big_dir / f"file_{i:04d}.txt").write_bytes(b"x" * 512)
        with BenchmarkTimer("list_500_files") as t:
            entries = list(big_dir.iterdir())
        assert len(entries) >= 500
        print(f"\n  {t}")

    def test_scandir_small(self):
        """Benchmark os.scandir on a small directory."""
        target = self.root / "dir_0"
        with BenchmarkTimer("scandir_100_files") as t:
            with os.scandir(target) as it:
                entries = list(it)
        assert len(entries) >= 100
        print(f"\n  {t}")


# ---------------------------------------------------------------------------
# Copy/move/delete benchmarks
# ---------------------------------------------------------------------------

class TestFileOperations:
    """Benchmark file copy, move, and delete operations."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path / "bench_ops"
        self.root.mkdir(exist_ok=True)
        self.src_dir = self.root / "src"
        self.src_dir.mkdir(exist_ok=True)
        # Create source files
        for i in range(50):
            (self.src_dir / f"file_{i:04d}.txt").write_bytes(os.urandom(4096))
        yield
        _cleanup_tree(self.root)

    def test_copy_files(self):
        """Benchmark copying 50 small files."""
        dst_dir = self.root / "dst_copy"
        dst_dir.mkdir(exist_ok=True)
        with BenchmarkTimer("copy_50_files") as t:
            for f in self.src_dir.iterdir():
                shutil.copy2(f, dst_dir / f.name)
        assert len(list(dst_dir.iterdir())) == 50
        print(f"\n  {t}")

    def test_move_files(self):
        """Benchmark moving 50 small files."""
        dst_dir = self.root / "dst_move"
        dst_dir.mkdir(exist_ok=True)
        # Copy first, then move
        for f in self.src_dir.iterdir():
            shutil.copy2(f, dst_dir / f.name)
        dst2 = self.root / "dst_move2"
        dst2.mkdir(exist_ok=True)
        with BenchmarkTimer("move_50_files") as t:
            for f in dst_dir.iterdir():
                shutil.move(str(f), dst2 / f.name)
        assert len(list(dst2.iterdir())) == 50
        print(f"\n  {t}")

    def test_delete_files(self):
        """Benchmark deleting 50 small files."""
        del_dir = self.root / "to_delete"
        del_dir.mkdir(exist_ok=True)
        for i in range(50):
            (del_dir / f"file_{i:04d}.txt").write_bytes(b"x" * 4096)
        with BenchmarkTimer("delete_50_files") as t:
            for f in del_dir.iterdir():
                f.unlink()
        print(f"\n  {t}")


# ---------------------------------------------------------------------------
# Search benchmarks
# ---------------------------------------------------------------------------

class TestSearch:
    """Benchmark search operations."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path / "bench_search"
        self.root.mkdir(exist_ok=True)
        _create_test_tree(self.root, depth=4, files_per_dir=50)
        yield
        _cleanup_tree(self.root)

    def test_glob_search(self):
        """Benchmark glob pattern matching across tree."""
        with BenchmarkTimer("glob_*.txt") as t:
            results = list(self.root.rglob("*.txt"))
        assert len(results) > 0
        print(f"\n  {t} ({len(results)} results)")

    def test_name_contains_search(self):
        """Benchmark substring search across tree."""
        with BenchmarkTimer("name_contains_file_") as t:
            results = [p for p in self.root.rglob("*") if "file_" in p.name.lower()]
        assert len(results) > 0
        print(f"\n  {t} ({len(results)} results)")


# ---------------------------------------------------------------------------
# Hashing benchmarks
# ---------------------------------------------------------------------------

class TestHashing:
    """Benchmark file hashing operations."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.test_file = tmp_path / "hash_test.bin"
        self.test_file.write_bytes(os.urandom(1024 * 1024))  # 1MB
        yield
        _cleanup_tree(tmp_path)

    def test_xxh3_hash(self):
        """Benchmark xxh3 hashing of 1MB file."""
        try:
            from xxhash import xxh3_64
            with BenchmarkTimer("xxh3_1MB") as t:
                h = xxh3_64()
                with open(self.test_file, "rb") as f:
                    while chunk := f.read(1024 * 1024):
                        h.update(chunk)
                digest = h.hexdigest()
            assert digest
            print(f"\n  {t}")
        except ImportError:
            pytest.skip("xxhash not installed")

    def test_sha256_hash(self):
        """Benchmark SHA-256 hashing of 1MB file."""
        import hashlib
        with BenchmarkTimer("sha256_1MB") as t:
            h = hashlib.sha256()
            with open(self.test_file, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    h.update(chunk)
            digest = h.hexdigest()
        assert digest
        print(f"\n  {t}")


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("NexusExplorer Performance Benchmarks")
    print("=" * 60)

    # Create temp dir for all benchmarks
    bench_root = Path(tempfile.mkdtemp(prefix="nexus_bench_"))

    try:
        # Directory listing
        print("\n--- Directory Listing ---")
        tree = bench_root / "tree"
        tree.mkdir()
        _create_test_tree(tree, depth=3, files_per_dir=100)

        for count, label in [(100, "100 files"), (500, "500 files")]:
            if count == 500:
                big = tree / "big"
                big.mkdir(exist_ok=True)
                for i in range(500):
                    (big / f"f{i:04d}.txt").write_bytes(b"x" * 512)
                target = big
            else:
                target = tree / "dir_0"
            t0 = time.perf_counter()
            entries = list(target.iterdir())
            ms = (time.perf_counter() - t0) * 1000
            print(f"  List {label}: {ms:.1f}ms ({len(entries)} entries)")

        # Copy
        print("\n--- File Copy ---")
        src = bench_root / "copy_src"
        src.mkdir()
        for i in range(50):
            (src / f"f{i:04d}.txt").write_bytes(os.urandom(4096))
        dst = bench_root / "copy_dst"
        dst.mkdir()
        t0 = time.perf_counter()
        for f in src.iterdir():
            shutil.copy2(f, dst / f.name)
        ms = (time.perf_counter() - t0) * 1000
        print(f"  Copy 50 files (4KB each): {ms:.1f}ms")

        # Search
        print("\n--- Search ---")
        t0 = time.perf_counter()
        results = list(tree.rglob("*.txt"))
        ms = (time.perf_counter() - t0) * 1000
        print(f"  Glob *.txt: {ms:.1f}ms ({len(results)} results)")

        # Hashing
        print("\n--- Hashing ---")
        test_file = bench_root / "hash.bin"
        test_file.write_bytes(os.urandom(1024 * 1024))

        try:
            from xxhash import xxh3_64
            t0 = time.perf_counter()
            h = xxh3_64()
            with open(test_file, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    h.update(chunk)
            ms = (time.perf_counter() - t0) * 1000
            print(f"  xxh3 1MB: {ms:.1f}ms")
        except ImportError:
            print("  xxhash not installed, skipping")

        import hashlib
        t0 = time.perf_counter()
        h = hashlib.sha256()
        with open(test_file, "rb") as f:
            while chunk := f.read(1024 * 1024):
                h.update(chunk)
        ms = (time.perf_counter() - t0) * 1000
        print(f"  SHA-256 1MB: {ms:.1f}ms")

    finally:
        shutil.rmtree(bench_root, ignore_errors=True)

    print("\n" + "=" * 60)
    print("Benchmarks complete.")
