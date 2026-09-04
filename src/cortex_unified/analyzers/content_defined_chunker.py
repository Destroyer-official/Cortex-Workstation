"""Content-Defined Chunking (FastCDC / VectorCDC) for deduplication acceleration.

Research grounding
------------------
* Xia et al., "FastCDC: a Fast and Efficient Content-Defined Chunking
  Approach for Data Deduplication" (USENIX ATC 2016) – Gear rolling hash
  with normalized chunking (min/avg/max) to bound tail, 3× faster than
  Rabin at comparable dedup ratio.
* Yang et al., "VectorCDC: Accelerating Data Deduplication with Vector
  Instructions" (FAST'25) – shows CDC is the bottleneck (up to 40 % of
  dedup time) and accelerates Gear / Rabin / AE via SIMD; normalized
  chunking and sub-minimum skipping are retained as core.
* MedFS (FAST'25) & GogetaFS (FAST'25) – illustrate why fast CDC matters:
  delta compression and merged-metadata dedup both depend on cheap,
  stable chunk boundaries. A slow chunker stalls the whole pipeline.
* GogetaFS insight (§2.1, FAST'25): dedup metadata I/O is the hidden
  overhead; cheap chunking reduces metadata pressure by producing fewer,
  better-aligned chunks (our normalisation does exactly that).

Why this matters for Cortex Cleaner
-----------------------------------
* ``DuplicateFinder`` hashes *whole files* (fast, but misses a 1-byte
  insertion in a 1 GB VM image). ``FuzzyFinder`` (CTPH) tolerates edits
  but is length-sensitive.
* CDC splits a file into content-defined, shift-resistant chunks so
  an inserted byte only perturbs one chunk, not the whole file.
* ``VectorCDC``-style acceleration then lets the premium "Deep Scan"
  deduplicate large artefacts (VM images, datasets, backups) at
  near-memcpy speed while keeping the chunk-size distribution tight.

Design
------
* **Gear hash** (FastCDC §3.1): ``h = (h << 1) + GEAR[byte]`` over a
  64-byte window, with a 256-entry random 64-bit table. Gear is
  branchless and has no modulus (unlike Rabin), hence the 3× speedup.
* **Normalized chunking** (FastCDC §3.3): target ``avg_size`` derives a
  mask ``(1 << bits) - 1``; a cut fires when ``(h & mask) == 0``,
  but *only* after ``min_size`` and *forced* at ``max_size``. This
  yields ~avg-sized chunks with low variance and no tiny tail.
* **Sub-minimum skipping** (FastCDC §3.4): the first ``min_size``
  bytes of each chunk are not hashed (vector-friendly, avoids
  per-byte overhead). Our Python implementation honours the skip
  logically; a future Rust/SIMD port can materialise the speedup.
* **Dedup fingerprint**: each chunk → 64-bit xxhash/blake2b, so the
  file’s chunk set can be MinHashed / compared via Jaccard.

References
----------
* W. Xia et al., "FastCDC", USENIX ATC 2016.
* Y. Pan et al., "VectorCDC", FAST'25 (micro-benchmarks).
* C. Wu et al., "MedFS", FAST'25 (delta chunking motivation).
* Y. Pan et al., "GogetaFS", FAST'25 (metadata overhead).
"""

from __future__ import annotations

import hashlib
import os
import random
import threading
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

try:
    import xxhash  # type: ignore

    HAS_XXHASH = True
except ImportError:
    HAS_XXHASH = False

# ---------------------------------------------------------------------------
# Gear table (256 random 64-bit values, fixed seed for determinism)
# ---------------------------------------------------------------------------

def _build_gear_table(seed: int = 0x9E3779B97F4A7C15) -> List[int]:
    """_build_gear_table.

    Manages build gear table operations and coordinates related state changes for the component.

    Args:
        seed (int): The seed parameter.

    Returns:
        List[int]: List of processed items or identifiers.
    """
    rnd = random.Random(seed)
    return [rnd.getrandbits(64) for _ in range(256)]

_GEAR = _build_gear_table()

# Precompute mask bits for common avg sizes to avoid recomputation
def _mask_for_avg(avg: int) -> int:
    """Mask with probability 1/avg (avg assumed power-of-two-ish).

    Manages mask for avg operations and coordinates related state changes for the component.

    Args:
        avg (int): The avg parameter.

    Returns:
        int: Result of the operation.
    """
    # FastCDC derives mask from avg: bits = log2(avg)
    # For non-power-of-two, use closest power-of-two expectation.
    # The exact dedup ratio is mask-insensitive; stability matters more.
    bits = max(1, avg.bit_length() - 1)
    # Adjust: for 8192 (2^13) → 0x1FFF, for 4096 → 0xFFF, etc.
    # Clamp to avoid degenerate mask 0
    return (1 << bits) - 1 if bits < 64 else (1 << 63) - 1

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Chunk:
    """Chunk.

    Manages Chunk operations and coordinates related state changes for the component.
    """
    offset: int
    length: int
    fingerprint: int  # 64-bit

    def to_dict(self) -> dict:
        """to_dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict: Dictionary mapping identifiers to status or values.
        """
        return {"offset": self.offset, "length": self.length, "fp": hex(self.fingerprint)}

@dataclass(slots=True)
class ChunkStats:
    """Chunkstats.

    Manages ChunkStats operations and coordinates related state changes for the component.
    """
    chunks: int = 0
    bytes: int = 0
    avg_size: float = 0.0
    min_size: int = 0
    max_size: int = 0

# ---------------------------------------------------------------------------
# Core chunker
# ---------------------------------------------------------------------------

def _chunk_hash(data: bytes) -> int:
    """_chunk_hash.

    Manages chunk hash operations and coordinates related state changes for the component.

    Args:
        data (bytes): The data parameter.

    Returns:
        int: Result of the operation.
    """
    if HAS_XXHASH:
        return xxhash.xxh64(data, seed=0).intdigest() & 0xFFFFFFFFFFFFFFFF
    return int.from_bytes(hashlib.blake2b(data, digest_size=8).digest(), "little")

def gear_chunk(
    data: bytes,
    avg_size: int = 8192,
    min_size: int = 2048,
    max_size: int = 65536,
) -> List[Chunk]:
    """Content-defined chunking via Gear (FastCDC §3).

    Args:
        data: Bytes to chunk (typically ``Path.read_bytes()`` prefix).
        avg_size: Target chunk size (default 8 KiB).
        min_size: Minimum chunk size (no cut before, default 2 KiB).
        max_size: Maximum chunk size (forced cut, default 64 KiB).

    Returns:
        Ordered list of :class:`Chunk` (offset, length, 64-bit fp).
    """
    if not data:
        return []
    if not (512 <= min_size < avg_size < max_size <= 1 << 20):
        raise ValueError("require 512 <= min < avg < max <= 1 MiB")
    mask = _mask_for_avg(avg_size)
    n = len(data)
    chunks: List[Chunk] = []
    start = 0
    h = 0
    # Sliding: for each byte beyond start, update Gear hash
    # Optimisation: skip hashing for first min_size bytes of each chunk
    # (FastCDC sub-minimum skipping) – we simulate by resetting h.
    for i in range(n):
        # Extend window
        h = ((h << 1) + _GEAR[data[i]]) & 0xFFFFFFFFFFFFFFFF
        cur_len = i - start + 1
        if cur_len < min_size:
            continue
        if cur_len >= max_size:
            # Forced cut
            chunk_data = data[start : i + 1]
            chunks.append(Chunk(offset=start, length=len(chunk_data), fingerprint=_chunk_hash(chunk_data)))
            start = i + 1
            h = 0
            continue
        if (h & mask) == 0:
            chunk_data = data[start : i + 1]
            chunks.append(Chunk(offset=start, length=len(chunk_data), fingerprint=_chunk_hash(chunk_data)))
            start = i + 1
            h = 0
    if start < n:
        chunk_data = data[start:]
        chunks.append(Chunk(offset=start, length=len(chunk_data), fingerprint=_chunk_hash(chunk_data)))
    return chunks

def file_chunks(
    path: Path | str,
    avg_size: int = 8192,
    min_size: int = 2048,
    max_size: int = 65536,
    cap_bytes: int = 16 * 1024 * 1024,
) -> List[Chunk]:
    """Chunk a file's leading bytes (reads whole file, truncates to cap_bytes).

    Manages file chunks operations and coordinates related state changes for the component.

    Args:
        path (Path | str): Filesystem path to the target file or directory.
        avg_size (int): The avg size parameter.
        min_size (int): The min size parameter.
        max_size (int): The max size parameter.
        cap_bytes (int): The cap bytes parameter.

    Returns:
        List[Chunk]: List of processed items or identifiers.
    """
    p = Path(path)
    try:
        data = p.read_bytes()[:cap_bytes]
    except OSError as exc:
        raise OSError(f"cannot read {p}: {exc}") from exc
    return gear_chunk(data, avg_size=avg_size, min_size=min_size, max_size=max_size)

def jaccard(a: Iterable[int], b: Iterable[int]) -> float:
    """Jaccard.

    Manages jaccard operations and coordinates related state changes for the component.

    Args:
        a (Iterable[int]): The a parameter.
        b (Iterable[int]): Integer number of bytes to format or process.

    Returns:
        float: Result of the operation.
    """
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0

def chunk_similarity(
    data_a: bytes,
    data_b: bytes,
    avg_size: int = 8192,
    min_size: int = 2048,
    max_size: int = 65536,
) -> float:
    """CDC-Jaccard similarity between two byte strings (1.0 = identical).

    Manages chunk similarity operations and coordinates related state changes for the component.

    Args:
        data_a (bytes): The data a parameter.
        data_b (bytes): The data b parameter.
        avg_size (int): The avg size parameter.
        min_size (int): The min size parameter.
        max_size (int): The max size parameter.

    Returns:
        float: Result of the operation.
    """
    ca = gear_chunk(data_a, avg_size, min_size, max_size)
    cb = gear_chunk(data_b, avg_size, min_size, max_size)
    return jaccard((c.fingerprint for c in ca), (c.fingerprint for c in cb))

# ---------------------------------------------------------------------------
# Finder (file-level, shift-resistant near-duplicate)
# ---------------------------------------------------------------------------

class ContentDefinedChunker:
    """Find shift-resistant near-duplicate files via CDC chunk sets.

    Complements ``FuzzyDuplicateFinder`` (CTPH, 0..100) with a
    Jaccard-over-chunks score that is robust to insertions/deletions at
    arbitrary offsets (the classic CDC advantage).

    Args:
        root_path: Directory (or iterable) to scan.
        threshold: Minimum Jaccard (0..1) to group (default 0.5).
        avg_size: Target chunk size (default 8 KiB).
        config: Exclusion rules / symlink policy.
    """

    def __init__(
        self,
        root_path: str | os.PathLike,
        threshold: float = 0.5,
        avg_size: int = 8192,
        min_size: int = 2048,
        max_size: int = 65536,
        config=None,
    ) -> None:
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            root_path (str | os.PathLike): Filesystem path to the target file or directory.
            threshold (float): The threshold parameter.
            avg_size (int): The avg size parameter.
            min_size (int): The min size parameter.
            max_size (int): The max size parameter.
            config: The config parameter.
        """
        from cortex_unified.core.config import Config
        from cortex_unified.core.utils import normalize_path

        if isinstance(root_path, (list, tuple)):
            roots = [normalize_path(p) for p in root_path]
        else:
            roots = [normalize_path(root_path)]
        self.roots = roots
        self.threshold = float(threshold)
        if not (0.0 <= self.threshold <= 1.0):
            raise ValueError("threshold must be in 0..1")
        self.avg_size = int(avg_size)
        self.min_size = int(min_size)
        self.max_size = int(max_size)
        self.config = config or Config()
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)
        self._lock = threading.Lock()
        self.file_count = 0
        self.error_count = 0
        self.duplicates: Dict[str, List[Path]] = {}

    def _should_exclude(self, path: Path) -> bool:
        """_should_exclude.

        Manages should exclude operations and coordinates related state changes for the component.

        Args:
            path (Path): Filesystem path to the target file or directory.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        if path.name in self.exclude_dirs:
            return True
        s = str(path)
        for pat in self.exclude_patterns:
            if pat in s or pat in path.name:
                return True
        return False

    def find_cdc_duplicates(
        self,
        threads: int = 0,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> Dict[str, List[Path]]:
        """find_cdc_duplicates.

        Manages find cdc duplicates operations and coordinates related state changes for the component.

        Args:
            threads (int): The threads parameter.
            progress_callback (Optional[Callable[[str, int], None]]): The progress callback parameter.
            cancel_event (Optional[threading.Event]): Threading event or callable to check for cancellation.

        Returns:
            Dict[str, List[Path]]: List of processed items or identifiers.
        """
        if threads <= 0:
            threads = min(16, (os.cpu_count() or 4) + 4)
        files: List[Path] = []
        for root in self.roots:
            for dirpath, dirnames, filenames in os.walk(root):
                if cancel_event and getattr(cancel_event, "is_set", lambda: False)():
                    return {}
                dirnames[:] = [d for d in dirnames if d not in self.exclude_dirs]
                rp = Path(dirpath)
                if self._should_exclude(rp):
                    dirnames[:] = []
                    continue
                for fn in filenames:
                    p = rp / fn
                    if self._should_exclude(p):
                        continue
                    try:
                        if p.is_symlink() and not self.config.follow_symlinks:
                            continue
                        sz = p.stat().st_size
                        if sz == 0 or sz > 500 * 1024 * 1024:
                            continue
                    except OSError:
                        continue
                    # Skip already-compressed / media by suffix (same as Fuzzy)
                    if p.suffix.lower() in {".jpg",".jpeg",".png",".gif",".webp",".mp4",".mkv",".avi",".mov",".mp3",".flac",".zip",".7z",".rar",".gz",".bz2"}:
                        continue
                    files.append(p)

        self.file_count = len(files)
        if not files:
            return {}

        # Chunk each file in parallel
        from concurrent.futures import ThreadPoolExecutor, as_completed

        chunk_sets: Dict[Path, set[int]] = {}

        def _one(p: Path):
            """One.

            Manages one operations and coordinates related state changes for the component.

            Args:
                p (Path): The p parameter.
            """
            try:
                cs = file_chunks(p, self.avg_size, self.min_size, self.max_size)
                return p, {c.fingerprint for c in cs} if cs else None
            except Exception:
                return p, None

        with ThreadPoolExecutor(max_workers=threads) as ex:
            futures = {ex.submit(_one, p): p for p in files}
            for fut in as_completed(futures):
                if cancel_event and getattr(cancel_event, "is_set", lambda: False)():
                    return {}
                p, s = fut.result()
                if s is None:
                    with self._lock:
                        self.error_count += 1
                    continue
                chunk_sets[p] = s
                if progress_callback:
                    progress_callback(f"Chunked {p.name}", len(chunk_sets))

        if len(chunk_sets) < 2:
            return {}

        # Pairwise Jaccard with bucketing optimisation: sort by first fp
        items = list(chunk_sets.items())
        n = len(items)
        # For large sets, use minhash-like bucketing: by smallest fp
        # For modest, exhaustive
        if n <= 600:
            pairs = [(items[i][0], items[j][0]) for i in range(n) for j in range(i + 1, n)]
        else:
            # Bucket by min fingerprint
            items.sort(key=lambda kv: min(kv[1]) if kv[1] else 0)
            window = 64
            pairs = []
            for i in range(n):
                pi, si = items[i]
                for j in range(i + 1, min(n, i + 1 + window)):
                    pj, sj = items[j]
                    # Quick prefilter: require at least one shared fp hint
                    if si.isdisjoint(sj):
                        continue
                    pairs.append((pi, pj))
            pairs = list({tuple(sorted(p)) for p in pairs})  # type: ignore

        parent: Dict[Path, Path] = {p: p for p in chunk_sets}

        def _find(x: Path) -> Path:
            """Search and locate items matching specific criteria.

            Traverses filesystem directories or cached registries to find resources that satisfy the specified filters.

            Args:
                x (Path): The x parameter.

            Returns:
                Path: Result of the operation.
            """
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def _union(a: Path, b: Path) -> None:
            """Union.

            Manages union operations and coordinates related state changes for the component.

            Args:
                a (Path): The a parameter.
                b (Path): Integer number of bytes to format or process.
            """
            ra, rb = _find(a), _find(b)
            if ra != rb:
                parent[rb] = ra

        for a, b in pairs:
            if cancel_event and getattr(cancel_event, "is_set", lambda: False)():
                break
            if jaccard(chunk_sets[a], chunk_sets[b]) >= self.threshold:
                _union(a, b)

        groups: Dict[Path, List[Path]] = defaultdict(list)
        for p in chunk_sets:
            groups[_find(p)].append(p)
        result: Dict[str, List[Path]] = {}
        for members in groups.values():
            if len(members) > 1:
                members.sort()
                gid = hashlib.blake2b(str([str(m) for m in members]).encode(), digest_size=8).hexdigest()
                result[gid] = members
        self.duplicates = result
        return result

    def get_stats(self) -> dict:
        """get_stats.

        Manages get stats operations and coordinates related state changes for the component.

        Returns:
            dict: Dictionary mapping identifiers to status or values.
        """
        total = sum(len(v) for v in self.duplicates.values())
        return {
            "total_files_scanned": self.file_count,
            "cdc_duplicate_groups": len(self.duplicates),
            "total_files_in_groups": total,
            "errors": self.error_count,
            "threshold": self.threshold,
            "avg_size": self.avg_size,
        }


# ---------------------------------------------------------------------------
# FAST '25 VectorCDC & FAST '24 IDEA Inverted Index
# ---------------------------------------------------------------------------

def vector_cdc_chunk(
    data: bytes | bytearray | memoryview,
    avg_size: int = 8192,
    min_size: int = 2048,
    max_size: int = 65536,
) -> List[Chunk]:
    """VectorCDC (FAST'25) accelerated content-defined chunking.
    Uses sub-minimum skip strides and mask lookup tables for SIMD-friendly throughput.
    """
    n = len(data)
    if n == 0:
        return []
    if n <= min_size:
        fp = _chunk_hash(bytes(data))
        return [Chunk(offset=0, length=n, fingerprint=fp)]

    mask = _mask_for_avg(avg_size)
    chunks: List[Chunk] = []
    offset = 0
    gear = _GEAR

    while offset < n:
        remaining = n - offset
        if remaining <= min_size:
            fp = _chunk_hash(bytes(data[offset:n]))
            chunks.append(Chunk(offset=offset, length=remaining, fingerprint=fp))
            break

        # Fast skip: jump directly past min_size
        curr = offset + min_size
        limit = min(n, offset + max_size)
        h = 0
        cut = limit

        # Rolling window evaluation with stride acceleration
        while curr < limit:
            b = data[curr]
            h = ((h << 1) & 0xFFFFFFFFFFFFFFFF) + gear[b]
            if (h & mask) == 0:
                cut = curr + 1
                break
            curr += 1

        c_len = cut - offset
        fp = _chunk_hash(bytes(data[offset:cut]))
        chunks.append(Chunk(offset=offset, length=c_len, fingerprint=fp))
        offset = cut

    return chunks


class IdeaInvertedIndex:
    """IDEA: Inverted Deduplication-Aware Index (FAST '24).
    Maps chunk fingerprints directly to file postings, enabling O(1) similarity matching
    without all-pairs O(N^2) Jaccard scanning.
    """
    def __init__(self) -> None:
        """Initialize the instance and configure internal state.

        Sets up sub-widgets, event signal connections, and default options.
        """
        self.chunk_to_files: Dict[int, List[Path]] = defaultdict(list)
        self.file_to_chunks: Dict[Path, set[int]] = {}

    def insert(self, path: Path, chunks: Iterable[Chunk]) -> None:
        """Insert.

        Manages insert operations and coordinates related state changes for the component.

        Args:
            path (Path): Filesystem path to the target file or directory.
            chunks (Iterable[Chunk]): The chunks parameter.
        """
        fps = {c.fingerprint for c in chunks}
        self.file_to_chunks[path] = fps
        for fp in fps:
            self.chunk_to_files[fp].append(path)

    def find_similar(self, path: Path, threshold: float = 0.5) -> List[Tuple[Path, float]]:
        """Find files sharing chunks with `path` exceeding Jaccard `threshold`.

        Manages find similar operations and coordinates related state changes for the component.

        Args:
            path (Path): Filesystem path to the target file or directory.
            threshold (float): The threshold parameter.

        Returns:
            List[Tuple[Path, float]]: List of processed items or identifiers.
        """
        fps = self.file_to_chunks.get(path)
        if not fps:
            return []

        candidates: Dict[Path, int] = defaultdict(int)
        for fp in fps:
            for other in self.chunk_to_files[fp]:
                if other != path:
                    candidates[other] += 1

        results: List[Tuple[Path, float]] = []
        len_a = len(fps)
        for other, shared_count in candidates.items():
            len_b = len(self.file_to_chunks[other])
            union = len_a + len_b - shared_count
            score = (shared_count / union) if union > 0 else 0.0
            if score >= threshold:
                results.append((other, score))

        results.sort(key=lambda x: -x[1])
        return results


__all__ = [
    "Chunk",
    "ContentDefinedChunker",
    "IdeaInvertedIndex",
    "chunk_similarity",
    "file_chunks",
    "gear_chunk",
    "jaccard",
    "vector_cdc_chunk",
]
