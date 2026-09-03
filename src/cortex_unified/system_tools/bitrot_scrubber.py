"""Cortex Cleaner — Silent BitRot & File Integrity Scrubber.

Detects silent archival corruption, bit flips, and storage degradation:
- Maintains a lightweight SQLite cryptographic integrity database.
- Calculates streaming SHA-256 hashes of critical files, photos, and system libraries.
- During scrub passes, detects files whose modified timestamp is unchanged but cryptographic hash has mutated (silent bitrot).
- Alerts on corrupted files, bit flip anomalies, and unauthorized tampering.
"""

from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("cortex.system_tools.bitrot_scrubber")


@dataclass
class ScrubberRecord:
    """Scrubber Record data container."""
    path: str
    size: int
    mtime: float
    sha256: str
    last_verified: float


@dataclass
class BitRotIssue:
    """Bit Rot Issue data container."""
    path: str
    expected_hash: str
    actual_hash: str
    size: int
    severity: str = "CRITICAL"  # Bitrot is high severity


@dataclass
class BitRotScrubReport:
    """Bit Rot Scrub Report data container."""
    total_files_scanned: int = 0
    clean_files_count: int = 0
    corrupted_count: int = 0
    new_files_indexed: int = 0
    updated_files_count: int = 0
    duration_seconds: float = 0.0
    corrupted_items: list[BitRotIssue] = field(default_factory=list)
    error: Optional[str] = None


class BitRotScrubber:
    """Enterprise BitRot Scrubber & Integrity Baseline Manager."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize Bit Rot Scrubber."""
        if not db_path:
            cortex_home = Path.home() / ".cortex"
            cortex_home.mkdir(parents=True, exist_ok=True)
            self._db_path = cortex_home / "integrity_baseline.db"
        else:
            self._db_path = Path(db_path)

        self._init_db()

    def _init_db(self):
        """Initialize integrity database schema."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS file_integrity (
                    path TEXT PRIMARY KEY,
                    size INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    sha256 TEXT NOT NULL,
                    last_verified REAL NOT NULL
                )
                """
            )
            conn.commit()

    @staticmethod
    def _compute_sha256(path: Path) -> str:
        """Stream SHA-256 calculation for arbitrary file sizes."""
        h = hashlib.sha256()
        buf = bytearray(256 * 1024)  # 256KB buffer
        with open(path, "rb") as f:
            while True:
                n = f.readinto(buf)
                if not n:
                    break
                h.update(memoryview(buf)[:n])
        return h.hexdigest()

    def scrub(self, target_dir: str, max_files: int = 5000) -> BitRotScrubReport:
        """Perform a cryptographic integrity scrub on target directory."""
        root = Path(target_dir)
        if not root.is_dir():
            return BitRotScrubReport(error=f"Directory does not exist: {target_dir}")

        t0 = time.perf_counter()
        scanned = 0
        clean = 0
        corrupted: list[BitRotIssue] = []
        new_indexed = 0
        updated = 0

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            for p in root.rglob("*"):
                if scanned >= max_files:
                    break
                if not p.is_file() or p.is_symlink():
                    continue

                scanned += 1
                try:
                    st = p.stat()
                    curr_size = st.st_size
                    curr_mtime = st.st_mtime
                    p_str = str(p.resolve())

                    cursor.execute(
                        "SELECT size, mtime, sha256 FROM file_integrity WHERE path = ?",
                        (p_str,),
                    )
                    row = cursor.fetchone()

                    curr_hash = self._compute_sha256(p)
                    now = time.time()

                    if row is None:
                        # New file -> index into baseline
                        cursor.execute(
                            "INSERT INTO file_integrity VALUES (?, ?, ?, ?, ?)",
                            (p_str, curr_size, curr_mtime, curr_hash, now),
                        )
                        new_indexed += 1
                    else:
                        base_size, base_mtime, base_hash = row
                        # If size and mtime are virtually unchanged (within filesystem 1s resolution), but hash mutated -> BITROT!
                        if abs(curr_mtime - base_mtime) <= 1.0 and curr_size == base_size:
                            if curr_hash != base_hash:
                                corrupted.append(
                                    BitRotIssue(
                                        path=p_str,
                                        expected_hash=base_hash,
                                        actual_hash=curr_hash,
                                        size=curr_size,
                                    )
                                )
                            else:
                                clean += 1
                                cursor.execute(
                                    "UPDATE file_integrity SET last_verified = ? WHERE path = ?",
                                    (now, p_str),
                                )
                        else:
                            # File legitimately edited -> update baseline
                            cursor.execute(
                                "UPDATE file_integrity SET size = ?, mtime = ?, sha256 = ?, last_verified = ? WHERE path = ?",
                                (curr_size, curr_mtime, curr_hash, now, p_str),
                            )
                            updated += 1

                except (PermissionError, OSError):
                    continue

            conn.commit()

        duration = time.perf_counter() - t0
        return BitRotScrubReport(
            total_files_scanned=scanned,
            clean_files_count=clean,
            corrupted_count=len(corrupted),
            new_files_indexed=new_indexed,
            updated_files_count=updated,
            duration_seconds=duration,
            corrupted_items=corrupted,
        )

    def reset_baseline(self, target_dir: Optional[str] = None):
        """Reset records in integrity database."""
        with sqlite3.connect(self._db_path) as conn:
            if target_dir:
                pattern = f"{target_dir}%"
                conn.execute("DELETE FROM file_integrity WHERE path LIKE ?", (pattern,))
            else:
                conn.execute("DELETE FROM file_integrity")
            conn.commit()
