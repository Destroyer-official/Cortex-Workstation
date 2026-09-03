"""Cortex Cleaner — Storage Growth Tracker & Timeline Differ.

Records persistent disk snapshots and visualizes folder tree expansion over time:
- Creates persistent snapshots of folder trees, file sizes, and directory hierarchies.
- Compares any two historical snapshots to calculate net growth deltas (+GB / -GB).
- Pinpoints exactly which directories and applications are consuming new storage.
- Identifies newly added high-footprint files and purged directories.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("cortex.system_tools.storage_growth_tracker")


@dataclass
class SnapshotSummary:
    """Snapshot Summary data container."""
    snapshot_id: int
    label: str
    root_path: str
    timestamp: float
    total_bytes: int
    total_files: int
    total_folders: int

    @property
    def formatted_time(self) -> str:
        """Formatted time."""
        return datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")

    @property
    def total_gb(self) -> float:
        """Total gb."""
        return self.total_bytes / (1024**3)


@dataclass
class DirectoryDelta:
    """Directory Delta data container."""
    path: str
    old_bytes: int
    new_bytes: int
    growth_bytes: int
    growth_percent: float

    @property
    def growth_mb(self) -> float:
        """Growth mb."""
        return self.growth_bytes / (1024**2)

    @property
    def growth_gb(self) -> float:
        """Growth gb."""
        return self.growth_bytes / (1024**3)


@dataclass
class StorageGrowthDiffReport:
    """Storage Growth Diff Report data container."""
    base_snapshot: SnapshotSummary
    target_snapshot: SnapshotSummary
    net_growth_bytes: int
    top_growing_dirs: list[DirectoryDelta] = field(default_factory=list)
    top_shrinking_dirs: list[DirectoryDelta] = field(default_factory=list)
    new_files_count: int = 0
    deleted_files_count: int = 0
    error: Optional[str] = None

    @property
    def net_growth_gb(self) -> float:
        """Net growth gb."""
        return self.net_growth_bytes / (1024**3)


class StorageGrowthTracker:
    """Enterprise Storage Growth Tracker & Snapshot Differ."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize Storage Growth Tracker."""
        if not db_path:
            cortex_home = Path.home() / ".cortex"
            cortex_home.mkdir(parents=True, exist_ok=True)
            self._db_path = cortex_home / "storage_growth.db"
        else:
            self._db_path = Path(db_path)

        self._init_db()

    def _init_db(self):
        """Create sqlite schema for snapshot metadata and items."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    root_path TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    total_bytes INTEGER NOT NULL,
                    total_files INTEGER NOT NULL,
                    total_folders INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshot_entries (
                    snapshot_id INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    is_dir INTEGER NOT NULL,
                    size INTEGER NOT NULL,
                    FOREIGN KEY(snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_snap_entries ON snapshot_entries(snapshot_id, path)"
            )
            conn.commit()

    def take_snapshot(
        self, root_path: str, label: str = "Manual Scan", max_depth: int = 5
    ) -> SnapshotSummary:
        """Scan directory and capture persistent snapshot."""
        root = Path(root_path).resolve()
        now = time.time()
        tot_bytes = 0
        tot_files = 0
        tot_folders = 0

        entries_to_insert: list[tuple[int, str, int, int]] = []
        dir_sizes: dict[str, int] = {}

        # Walk tree
        for dirpath, dirnames, filenames in os.walk(root):
            p_dir = Path(dirpath)
            # check depth
            try:
                depth = len(p_dir.relative_to(root).parts)
            except ValueError:
                depth = 0
            if depth > max_depth:
                dirnames.clear()
                continue

            tot_folders += 1
            curr_dir_size = 0

            for fname in filenames:
                fpath = p_dir / fname
                try:
                    sz = fpath.stat().st_size
                    tot_bytes += sz
                    tot_files += 1
                    curr_dir_size += sz
                    entries_to_insert.append((0, str(fpath), 0, sz))
                except (PermissionError, OSError):
                    pass

            dir_sizes[str(p_dir)] = curr_dir_size

        with sqlite3.connect(self._db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO snapshots (label, root_path, timestamp, total_bytes, total_files, total_folders) VALUES (?, ?, ?, ?, ?, ?)",
                (label, str(root), now, tot_bytes, tot_files, tot_folders),
            )
            snap_id = cur.lastrowid or 1

            # Insert folder rollups and files
            rows = [
                (snap_id, path_str, is_dir, sz)
                for (_, path_str, is_dir, sz) in entries_to_insert
            ]
            for dpath, dsz in dir_sizes.items():
                rows.append((snap_id, dpath, 1, dsz))

            cur.executemany(
                "INSERT INTO snapshot_entries VALUES (?, ?, ?, ?)", rows
            )
            conn.commit()

        return SnapshotSummary(
            snapshot_id=snap_id,
            label=label,
            root_path=str(root),
            timestamp=now,
            total_bytes=tot_bytes,
            total_files=tot_files,
            total_folders=tot_folders,
        )

    def list_snapshots(self) -> list[SnapshotSummary]:
        """List all captured snapshots."""
        with sqlite3.connect(self._db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, label, root_path, timestamp, total_bytes, total_files, total_folders FROM snapshots ORDER BY timestamp DESC")
            rows = cur.fetchall()
            return [
                SnapshotSummary(
                    snapshot_id=r[0],
                    label=r[1],
                    root_path=r[2],
                    timestamp=r[3],
                    total_bytes=r[4],
                    total_files=r[5],
                    total_folders=r[6],
                )
                for r in rows
            ]

    def compare_snapshots(self, base_id: int, target_id: int) -> StorageGrowthDiffReport:
        """Calculate differential storage growth between two snapshots."""
        with sqlite3.connect(self._db_path) as conn:
            cur = conn.cursor()

            # Load snapshots metadata
            cur.execute("SELECT id, label, root_path, timestamp, total_bytes, total_files, total_folders FROM snapshots WHERE id = ?", (base_id,))
            b_row = cur.fetchone()
            cur.execute("SELECT id, label, root_path, timestamp, total_bytes, total_files, total_folders FROM snapshots WHERE id = ?", (target_id,))
            t_row = cur.fetchone()

            if not b_row or not t_row:
                empty_summary = SnapshotSummary(0, "", "", 0.0, 0, 0, 0)
                return StorageGrowthDiffReport(empty_summary, empty_summary, 0, error="Invalid snapshot IDs")

            base_snap = SnapshotSummary(*b_row)
            target_snap = SnapshotSummary(*t_row)

            # Query folder sizes for both
            cur.execute("SELECT path, size FROM snapshot_entries WHERE snapshot_id = ? AND is_dir = 1", (base_id,))
            base_dirs = dict(cur.fetchall())
            cur.execute("SELECT path, size FROM snapshot_entries WHERE snapshot_id = ? AND is_dir = 1", (target_id,))
            target_dirs = dict(cur.fetchall())

            all_dirs = set(base_dirs.keys()) | set(target_dirs.keys())
            deltas: list[DirectoryDelta] = []

            for d in all_dirs:
                old_sz = base_dirs.get(d, 0)
                new_sz = target_dirs.get(d, 0)
                diff = new_sz - old_sz
                if diff != 0:
                    pct = ((diff / old_sz) * 100.0) if old_sz > 0 else 100.0
                    deltas.append(
                        DirectoryDelta(
                            path=d,
                            old_bytes=old_sz,
                            new_bytes=new_sz,
                            growth_bytes=diff,
                            growth_percent=pct,
                        )
                    )

            growing = sorted([d for d in deltas if d.growth_bytes > 0], key=lambda x: x.growth_bytes, reverse=True)[:15]
            shrinking = sorted([d for d in deltas if d.growth_bytes < 0], key=lambda x: x.growth_bytes)[:15]

            net_growth = target_snap.total_bytes - base_snap.total_bytes

            return StorageGrowthDiffReport(
                base_snapshot=base_snap,
                target_snapshot=target_snap,
                net_growth_bytes=net_growth,
                top_growing_dirs=growing,
                top_shrinking_dirs=shrinking,
            )
