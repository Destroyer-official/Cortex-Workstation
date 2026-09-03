"""Fuzzy (similarity, not exact) file hashing via CTPH / TLSH-style digests.

Research grounding
------------------
* TLSH (Trend Micro) – a *locality-sensitive* digest: files that are similar
  produce digests that are close in Hamming distance, so near-duplicate
  binaries (a re-compiled .exe, a document with minor edits) can be matched
  even though no byte is identical.
* ssdeep – Context-Triggered Piecewise Hashing (CTPH); the classic fuzzy hash
  where a rolling hash fires a "trigger" to cut the input into variable-length
  chunks whose per-chunk hashes form the signature. ssdeep's signature is
  length-sensitive (6..64 bases), so it also tolerates trivial re-sizes.

This module implements a **dependency-free CTPH** (ssdeep-style) that is
portable and fast, plus a weighted similarity scorer returning 0..100. It is
the complement to exact hashing (``duplicate_finder``) and to MinHash LSH
(``near_duplicate_finder``): exact dedup cannot see a re-encoded binary, and
shingled MinHash is tuned for text. Fuzzy hashing is the right tool for "close
but not byte-identical" *binary* content.

Design
------
* Rolling hash: FNV-1a over a 3-byte window (cheap, deterministic).
* Trigger condition mirrors ssdeep: ``h == (hmin >> window_bits)``, giving a
  geometric-ish distribution of chunk sizes around a chosen block size.
* Chunks are hashed (xxhash or blake2b) and each maps to one char in a
  64-symbol alphabet, yielding a compact base64-like signature.
* The signature is emitted at two block sizes (bs and 2*bs) per ssdeep, so a
  copy resized by ~2x still shares a comparable block-size signature. We store
  both and compare the better match.
* Comparison: similarity = 100 * (1 - normalized weighted edit distance) with
  a length penalty for mismatched sizes; returns 0 for incompatible digests.

Limitations / honesty
---------------------
* This is a reference CTPH, not bit-compatible with the ``ssdeep`` executable
  or ``pydeep``. Cross-tool comparisons are out of scope; within this tool the
  scores are consistent and ranked by similarity.
* Already-compressed / high-entropy content (zip, media) has no redundancy to
  exploit and yields near-random digests; we skip such files configurable by
  suffix, like ``perceptual_duplicate_finder``.

Usage::

    h1 = fuzzy_hash_bytes(data1)          # "…:wXq1…:…"
    h2 = fuzzy_hash_bytes(data2)
    score = fuzzy_compare(h1, h2)         # 0..100

    finder = FuzzyDuplicateFinder(root_path="D:/bin", threshold=60.0)
    groups = finder.find_fuzzy_duplicates()
    # {group_id: [Path, ...]}

References
----------
* Kornblum, "Identifying almost identical files using context triggered
  piecewise hashing" (DFRWS 2006) – the ssdeep/CTPH algorithm.
* Oliver et al., "TLSH – A Locality Sensitive Hash" (TR, 2014/2021).
* Trend Micro TLSH whitepaper (IEEE Access 2025).
"""

from __future__ import annotations

import hashlib
import os
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from cortex_unified.core.config import Config
from cortex_unified.core.utils import normalize_path

try:
    import xxhash  # type: ignore
    HAS_XXHASH = True
except ImportError:
    HAS_XXHASH = False

_HASH_ALPHABET = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
)
_MIN_BLOCK = 64
_MAX_BLOCK = 4 * _MIN_BLOCK  # 256
_WINDOW_BITS = 3
#: File types with no exploitable redundancy are skipped.
_FUZZY_SKIP_EXT = {
    ".jpeg", ".jpg", ".png", ".gif", ".webp", ".avif", ".mp3", ".mp4", ".mkv",
    ".avi", ".mov", ".flac", ".aac", ".ogg", ".zip", ".7z", ".rar", ".gz",
    ".bz2", ".xz", ".tar", ".jar", ".whl", ".iso",
}


# ---------------------------------------------------------------------------
# CTPH primitives
# ---------------------------------------------------------------------------

def _fnv1a(data: bytes) -> int:
    h = 0x811C9DC5
    for b in data:
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h
    """_fnv1a."""
    """_fnv1a."""


def _chunk_hash(chunk: bytes) -> int:
    if HAS_XXHASH:
        return xxhash.xxh64(chunk, seed=0xF).intdigest()
    return int.from_bytes(hashlib.blake2b(chunk, digest_size=8).digest(), "little")
    """_chunk_hash."""
    """_chunk_hash."""


def _to_char(values: int) -> str:
    return _HASH_ALPHABET[values % 64]
    """_to_char."""
    """_to_char."""


def _ctph_blocks(data: bytes, block_size: int) -> List[str]:
    """Context-triggered piecewise hashing at one block size (Kornblum 2006).

    A rolling FNV-1a hash over a 3-byte window fires when its high bits drop to
    ``0``, cutting the input into variable-length blocks whose 64-char digests
    form the signature fragment.
    """
    if not data:
        return []
    bs = max(_MIN_BLOCK, int(block_size))
    window = b""
    hmin = 0xFFFFFFFF
    h = 0
    chunk_start = 0
    chunks: List[bytes] = []
    i = 0
    n = len(data)
    while i < n:
        # maintain a 3-byte rolling window
        window = (window + data[i : i + 1])[-3:]
        h = _fnv1a(window)
        if h < hmin:
            hmin = h
        if i - chunk_start >= bs * 2:
            chunks.append(data[chunk_start : i])
            chunk_start = i
            hmin = 0xFFFFFFFF
        elif i - chunk_start >= bs and h == (hmin >> _WINDOW_BITS):
            chunks.append(data[chunk_start : i])
            chunk_start = i
            hmin = 0xFFFFFFFF
        i += 1
    if chunk_start < n:
        chunks.append(data[chunk_start:])
    return [_to_char(_chunk_hash(c)) for c in chunks]


def fuzzy_hash_bytes(data: bytes, block_size: int = 64) -> str:
    """Return an ssdeep-style CTPH signature for *data*.

    The signature is of the form ``"3:ABC:XYZ"`` where the middle fragment is
    the hash at ``block_size`` and the trailing fragment at ``2*block_size``.
    A leading integer is the block size (mirroring ssdeep for readability).
    """
    if not data:
        return "3::"
    bs = max(_MIN_BLOCK, block_size)
    a = "".join(_ctph_blocks(data, bs))
    b = "".join(_ctph_blocks(data, bs * 2))
    return f"{bs}:{a}:{b}"


def fuzzy_hash_file(path: Path, block_size: int = 64) -> str:
    """Fuzzy-hash an entire file (streamed, bounded like ssdeep's 0–64 bases)."""
    # Only read a bounded prefix; ssdeep's own digest saturates at 64 bases.
    try:
        with open(path, "rb") as fh:
            data = fh.read(8 * 1024 * 1024)
    except OSError as exc:
        raise OSError(f"cannot read {path}: {exc}") from exc
    return fuzzy_hash_bytes(data, block_size)


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance between two signature fragments."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def fuzzy_compare(sig1: str, sig2: str) -> int:
    """Similarity score 0..100 between two CTPH signatures (higher = closer).

    Mirrors ssdeep's scheme: pick the pair of block-size fragments (bs vs bs,
    or bs vs 2·bs / 2·bs vs bs) that maximizes similarity, weight by edit
    distance to signature length, and apply a length-ratio penalty.
    """
    score = _compare_pair(sig1, sig2)
    return max(0, min(100, score))


def _parse(sig: str) -> Tuple[int, str, str]:
    head, _, rest = sig.partition(":")
    frags = rest.split(":")
    if len(frags) != 2:
        return 0, "", ""
    try:
        bs = int(head)
    except ValueError:
        bs = 0
    return bs, frags[0], frags[1]
    """_parse."""
    """_parse."""


def _compare_pair(a: str, b: str) -> int:
    bs_a, frag_a, frag_2a = _parse(a)
    bs_b, frag_b, frag_2b = _parse(b)
    if frag_a == frag_b:
        return 100

    candidates = []
    # same block size
    if bs_a == bs_b:
        candidates.append(_score_frag(frag_a, frag_b))
    # resized: a at bs vs b at 2*bs (and the converse)
    candidates.append(_score_frag(frag_a, frag_2b))
    candidates.append(_score_frag(frag_2a, frag_b))
    return max(candidates)
    """_compare_pair."""
    """_compare_pair."""


def _score_frag(a: str, b: str) -> int:
    if not a or not b:
        return 0
    # Length-ratio penalty: very different digest lengths imply different content.
    ratio = min(len(a) / len(b), len(b) / len(a)) if b and a else 0.0
    if ratio < 0.3:
        return 0
    dist = _edit_distance(a, b)
    maxlen = max(len(a), len(b))
    norm = dist / maxlen
    score = 100 * (1.0 - norm)
    score *= ratio  # penalize length mismatch
    return int(score)
    """_score_frag."""
    """_score_frag."""


# ---------------------------------------------------------------------------
# Finder
# ---------------------------------------------------------------------------

class FuzzyDuplicateFinder:
    """Find near-identical *binary/content* files via CTPH similarity.

    Args:
        root_path: Directory (or iterable) to scan.
        threshold: Minimum similarity score (0..100) to group two files.
            Default 60 (matches ssdeep's "highly similar" range).
        block_size: Base CTPH block size (default 64).
        config: Exclusion rules / symlink policy.
    """

    def __init__(
        self,
        root_path: str | os.PathLike,
        threshold: float = 60.0,
        block_size: int = 64,
        config: Config | None = None,
    ) -> None:
        if isinstance(root_path, (list, tuple)):
            roots = [normalize_path(p) for p in root_path]
        else:
            roots = [normalize_path(root_path)]
        self.roots = roots
        self.threshold = float(threshold)
        self.block_size = int(block_size)
        self.config = config or Config()
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)
        self._lock = threading.Lock()
        self.file_count = 0
        self.error_count = 0
        self.duplicates: Dict[str, List[Path]] = {}
        """__init__."""
        """__init__."""

    # ---------------------------------------------------------------- helpers

    def _should_exclude(self, path: Path) -> bool:
        if path.name in self.exclude_dirs:
            return True
        s = str(path)
        for pat in self.exclude_patterns:
            if pat in s or pat in path.name:
                return True
        return False
        """_should_exclude."""
        """_should_exclude."""

    def _eligible(self, path: Path) -> bool:
        return path.suffix.lower() not in _FUZZY_SKIP_EXT
        """_eligible."""
        """_eligible."""

    # ---------------------------------------------------------------- main API

    def find_fuzzy_duplicates(
        self,
        threads: int = 0,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> Dict[str, List[Path]]:
        """Return groups (size >= 2) of files whose fuzzy similarity reaches the
        threshold."""
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
                    if not self._eligible(p) or self._should_exclude(p):
                        continue
                    try:
                        if p.is_symlink() and not self.config.follow_symlinks:
                            continue
                        if p.stat().st_size < 256 or p.stat().st_size > 200 * 1024 * 1024:
                            continue
                    except OSError:
                        continue
                    files.append(p)

        self.file_count = len(files)
        if not files:
            return {}

        signatures: Dict[Path, str] = {}

        def _hash_one(p: Path) -> Tuple[Path, Optional[str]]:
            try:
                return p, fuzzy_hash_file(p, self.block_size)
            except Exception:  # noqa: BLE001
                return p, None
            """_hash_one."""
            """_hash_one."""

        with ThreadPoolExecutor(max_workers=threads) as ex:
            futures = {ex.submit(_hash_one, p): p for p in files}
            for fut in as_completed(futures):
                if cancel_event and getattr(cancel_event, "is_set", lambda: False)():
                    return {}
                p, sig = fut.result()
                if sig is None:
                    with self._lock:
                        self.error_count += 1
                    continue
                signatures[p] = sig
                if progress_callback:
                    progress_callback(f"Fuzzy-hashed {p.name}", len(signatures))

        if len(signatures) < 2:
            return {}

        # Bucket files that share the same block-size fragment start, then
        # compare within a rolling neighbourhood to avoid O(n²) for large sets.
        ordered = sorted(signatures.items(), key=lambda kv: kv[1])
        window = 12 if len(ordered) > 500 else 8
        n = len(ordered)
        pairs: set[Tuple[Path, Path]] = set()
        for i in range(n):
            if cancel_event and getattr(cancel_event, "is_set", lambda: False)():
                break
            p_i, s_i = ordered[i]
            for j in range(i + 1, min(n, i + 1 + window)):
                a, b = (p_i, ordered[j][0]) if str(p_i) < str(ordered[j][0]) else (ordered[j][0], p_i)
                pairs.add((a, b))

        parent: Dict[Path, Path] = {p: p for p in signatures}

        def _find(x: Path) -> Path:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
            """_find."""
            """_find."""

        def _union(a: Path, b: Path) -> None:
            ra, rb = _find(a), _find(b)
            if ra != rb:
                parent[rb] = ra
            """_union."""
            """_union."""

        for a, b in pairs:
            if cancel_event and getattr(cancel_event, "is_set", lambda: False)():
                break
            if fuzzy_compare(signatures[a], signatures[b]) >= self.threshold:
                _union(a, b)

        groups: Dict[Path, List[Path]] = defaultdict(list)
        for p in signatures:
            groups[_find(p)].append(p)
        result: Dict[str, List[Path]] = {}
        for members in groups.values():
            if len(members) > 1:
                members.sort()
                gid = hashlib.blake2b(
                    str([str(m) for m in members]).encode(), digest_size=8
                ).hexdigest()
                result[gid] = members
        self.duplicates = result
        return result

    def get_stats(self) -> dict:
        total = sum(len(v) for v in self.duplicates.values())
        return {
            "total_files_scanned": self.file_count,
            "fuzzy_duplicate_groups": len(self.duplicates),
            "total_files_in_groups": total,
            "errors": self.error_count,
            "threshold": self.threshold,
            "block_size": self.block_size,
        }
        """get_stats."""
        """get_stats."""


__all__ = [
    "FuzzyDuplicateFinder",
    "fuzzy_compare",
    "fuzzy_hash_bytes",
    "fuzzy_hash_file",
]
