"""Fast content hashing and duplicate detection.

Algorithm choice (fastest available, all non-cryptographic-strength but ideal
for dedup where we only need collision resistance for *content identity*):
    xxhash.xxh3_64  (if installed, ~10x faster than MD5)
      -> fallback to hashlib.blake2b (built-in, faster & safer than MD5)

Duplicate-finding pipeline (minimizes expensive hashing):
    1. Group candidate files by exact size (a cheap ``DirEntry`` field). Files
       with a unique size cannot have a duplicate, so they're dropped for free.
    2. Within each size-group, cheaply hash a small head chunk to split
       obvious non-matches without reading whole files.
    3. Only for surviving head-collisions do we compute a full content hash.
    4. Hashing is parallelised with a thread pool (I/O-bound; the GIL is
       released during file reads).
"""

from __future__ import annotations

import hashlib
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

# Hash backend selection, fastest-suitable first. For *content identity*
# (dedup) a non-cryptographic hash is ideal and XXH3 is the throughput king
# (~30 GB/s). BLAKE3 is the best fast *cryptographic* option (parallel Merkle
# tree, faster than SHA-256); blake2b is the always-available stdlib fallback.
try:  # optional, fastest for dedup identity
    import xxhash  # type: ignore

    _HAS_XXHASH = True
except ImportError:  # pragma: no cover - depends on environment
    _HAS_XXHASH = False

try:  # optional, fast + cryptographically strong
    import blake3  # type: ignore

    _HAS_BLAKE3 = True
except ImportError:  # pragma: no cover - depends on environment
    _HAS_BLAKE3 = False

if _HAS_XXHASH:
    HASH_ALGORITHM = "xxh3_64"
elif _HAS_BLAKE3:
    HASH_ALGORITHM = "blake3"
else:
    HASH_ALGORITHM = "blake2b"

_HEAD_BYTES = 65536       # 64 KiB probe for the pre-hash stage
_CHUNK = 1024 * 1024      # 1 MiB streaming chunk for full hashes


def _new_hasher():
    """Construct the fastest available hasher (see HASH_ALGORITHM)."""
    if _HAS_XXHASH:
        return xxhash.xxh3_64()
    if _HAS_BLAKE3:
        return blake3.blake3()
    return hashlib.blake2b(digest_size=16)


def hash_file(path: os.PathLike[str] | str, limit: int | None = None) -> str | None:
    """Return the hex digest of *path* (or its first ``limit`` bytes).

    Returns ``None`` if the file cannot be read. Never raises for I/O errors.
    """
    hasher = _new_hasher()
    remaining = limit if limit is not None else -1
    try:
        with open(path, "rb", buffering=0) as fh:
            while True:
                want = _CHUNK if remaining < 0 else min(_CHUNK, remaining)
                if want == 0:
                    break
                chunk = fh.read(want)
                if not chunk:
                    break
                hasher.update(chunk)
                if remaining > 0:
                    remaining -= len(chunk)
        return hasher.hexdigest()
    except (OSError, ValueError):
        return None


class DuplicateFinderEngine:
    """Find duplicate files among an arbitrary set of paths."""

    def __init__(self, workers: int = 0) -> None:
        # I/O-bound: a few more threads than cores keeps disks busy without
        # oversubscribing. Capped to avoid thrashing on spinning media.
        self.workers = workers if workers > 0 else min(32, (os.cpu_count() or 4) + 4)
        self.hash_algorithm = HASH_ALGORITHM
        """__init__."""
        """__init__."""

    def find(
        self,
        entries: list[tuple[Path, int]],
        progress: Callable[[int, int], None] | None = None,
    ) -> dict[str, list[Path]]:
        """Return ``{content_hash: [paths...]}`` for groups with >1 member.

        *entries* is a list of ``(path, size)`` pairs (sizes come free from the
        walker's ``DirEntry`` cache, so callers avoid extra ``stat`` calls).
        """
        # Stage 1: size prefilter.
        by_size: dict[int, list[Path]] = defaultdict(list)
        for path, size in entries:
            if size > 0:
                by_size[size].append(path)
        candidates = [p for group in by_size.values() if len(group) > 1 for p in group]
        if not candidates:
            return {}

        # Stage 2: cheap head-hash to prune within size groups.
        head_groups = self._group_by_hash(candidates, limit=_HEAD_BYTES, progress=progress)
        survivors = [p for group in head_groups.values() if len(group) > 1 for p in group]
        if not survivors:
            return {}

        # Stage 3: full content hash only on survivors.
        full_groups = self._group_by_hash(survivors, limit=None, progress=progress)
        return {h: paths for h, paths in full_groups.items() if len(paths) > 1}

    def _group_by_hash(
        self,
        paths: list[Path],
        limit: int | None,
        progress: Callable[[int, int], None] | None,
    ) -> dict[str, list[Path]]:
        groups: dict[str, list[Path]] = defaultdict(list)
        total = len(paths)
        done = 0
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            for path, digest in zip(paths, pool.map(lambda p: hash_file(p, limit), paths)):
                done += 1
                if digest is not None:
                    # Include size implicitly (same size-group) + limit marker so
                    # head-hashes and full-hashes never collide across stages.
                    key = f"{limit}:{digest}"
                    groups[key].append(path)
                if progress is not None:
                    progress(done, total)
        return groups
        """_group_by_hash."""
        """_group_by_hash."""

    @staticmethod
    def wasted_bytes(groups: dict[str, list[Path]]) -> int:
        """Bytes reclaimable by keeping one copy per duplicate group."""
        total = 0
        for paths in groups.values():
            if len(paths) <= 1:
                continue
            try:
                unit = paths[0].stat().st_size
            except OSError:
                continue
            total += unit * (len(paths) - 1)
        return total
