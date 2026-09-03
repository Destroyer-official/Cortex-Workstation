"""Nexus Explorer — Directory Comparison & Folder Synchronization Engine.

Compares two directory trees by size, timestamp, or cryptographic content hash.
Classifies entries into diff matrices (Left Only, Right Only, Newer, Diff, Identical)
and provides automated synchronization (Mirror Left/Right, Two-Way Merge, Update Newer).
"""

from __future__ import annotations

import hashlib
import os
import shutil
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple


class DiffStatus(Enum):
    """DiffStatus."""
    IDENTICAL = "Identical"
    LEFT_ONLY = "Left Only"
    RIGHT_ONLY = "Right Only"
    NEWER_LEFT = "Newer on Left"
    NEWER_RIGHT = "Newer on Right"
    CONTENT_DIFF = "Content Mismatch"
    """DiffStatus class."""


class SyncMode(Enum):
    """SyncMode."""
    MIRROR_LEFT_TO_RIGHT = "Mirror Left -> Right"
    MIRROR_RIGHT_TO_LEFT = "Mirror Right -> Left"
    TWO_WAY_MERGE = "Two-Way Bidirectional Merge"
    UPDATE_NEWER = "Update Newer Files Only"
    """SyncMode class."""


@dataclass
class DiffEntry:
    """DiffEntry."""
    relative_path: str
    left_path: Optional[str]
    right_path: Optional[str]
    status: DiffStatus
    left_size: int = 0
    right_size: int = 0
    left_mtime: float = 0.0
    right_mtime: float = 0.0
    is_dir: bool = False
    """DiffEntry class."""


@dataclass
class SyncStats:
    """SyncStats."""
    copied: int = 0
    updated: int = 0
    deleted: int = 0
    skipped: int = 0
    bytes_transferred: int = 0
    errors: List[str] = None

    def __post_init__(self):
        """__post_init__."""
        if self.errors is None:
            self.errors = []
        """__post_init__."""
    """SyncStats class."""


class DirectoryDiffEngine:
    """Production directory comparison and folder synchronization engine."""

    @staticmethod
    def _quick_hash(path_str: str) -> str:
        """Compute SHA256 of first/last 64KB + total size for fast accurate verification."""
        try:
            h = hashlib.sha256()
            size = os.path.getsize(path_str)
            h.update(str(size).encode("utf-8"))
            with open(path_str, "rb") as f:
                h.update(f.read(65536))
                if size > 65536:
                    f.seek(max(0, size - 65536))
                    h.update(f.read(65536))
            return h.hexdigest()
        except Exception:
            return ""

    @classmethod
    def compare_directories(
        cls,
        left_dir: str | Path,
        right_dir: str | Path,
        compare_content_hash: bool = False,
        progress_cb: Optional[Callable[[int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> List[DiffEntry]:
        """Compare two folders recursively and return a list of DiffEntry items."""
        left_base = Path(left_dir).resolve()
        right_base = Path(right_dir).resolve()

        if not left_base.is_dir() or not right_base.is_dir():
            return []

        # 1. Collect all relative paths
        left_files: Dict[str, Tuple[int, float, bool]] = {}
        for root, dirs, files in os.walk(left_base):
            if cancel_check and cancel_check():
                return []
            rel_dir = os.path.relpath(root, left_base)
            for d in dirs:
                rel = (Path(rel_dir) / d).as_posix() if rel_dir != "." else d
                left_files[rel] = (0, 0.0, True)
            for f in files:
                rel = (Path(rel_dir) / f).as_posix() if rel_dir != "." else f
                full = Path(root) / f
                try:
                    stat = full.stat()
                    left_files[rel] = (stat.st_size, stat.st_mtime, False)
                except Exception:
                    pass

        right_files: Dict[str, Tuple[int, float, bool]] = {}
        for root, dirs, files in os.walk(right_base):
            if cancel_check and cancel_check():
                return []
            rel_dir = os.path.relpath(root, right_base)
            for d in dirs:
                rel = (Path(rel_dir) / d).as_posix() if rel_dir != "." else d
                right_files[rel] = (0, 0.0, True)
            for f in files:
                rel = (Path(rel_dir) / f).as_posix() if rel_dir != "." else f
                full = Path(root) / f
                try:
                    stat = full.stat()
                    right_files[rel] = (stat.st_size, stat.st_mtime, False)
                except Exception:
                    pass

        all_rel_paths = sorted(set(left_files.keys()).union(right_files.keys()))
        diff_entries: List[DiffEntry] = []
        total = len(all_rel_paths)

        for i, rel in enumerate(all_rel_paths):
            if cancel_check and cancel_check():
                break
            if progress_cb and i % 50 == 0:
                progress_cb(i, rel)

            in_left = rel in left_files
            in_right = rel in right_files

            if in_left and not in_right:
                size, mtime, is_d = left_files[rel]
                diff_entries.append(DiffEntry(
                    relative_path=rel,
                    left_path=str(left_base / rel),
                    right_path=None,
                    status=DiffStatus.LEFT_ONLY,
                    left_size=size,
                    left_mtime=mtime,
                    is_dir=is_d,
                ))
            elif in_right and not in_left:
                size, mtime, is_d = right_files[rel]
                diff_entries.append(DiffEntry(
                    relative_path=rel,
                    left_path=None,
                    right_path=str(right_base / rel),
                    status=DiffStatus.RIGHT_ONLY,
                    right_size=size,
                    right_mtime=mtime,
                    is_dir=is_d,
                ))
            else:
                # Exists on both sides
                l_size, l_mtime, l_is_d = left_files[rel]
                r_size, r_mtime, r_is_d = right_files[rel]

                if l_is_d and r_is_d:
                    diff_entries.append(DiffEntry(
                        relative_path=rel,
                        left_path=str(left_base / rel),
                        right_path=str(right_base / rel),
                        status=DiffStatus.IDENTICAL,
                        is_dir=True,
                    ))
                    continue

                status = DiffStatus.IDENTICAL
                time_diff = l_mtime - r_mtime

                if compare_content_hash:
                    l_hash = cls._quick_hash(str(left_base / rel))
                    r_hash = cls._quick_hash(str(right_base / rel))
                    if l_hash != r_hash:
                        if abs(time_diff) > 2.0:
                            status = DiffStatus.NEWER_LEFT if time_diff > 0 else DiffStatus.NEWER_RIGHT
                        else:
                            status = DiffStatus.CONTENT_DIFF
                else:
                    if l_size != r_size:
                        status = DiffStatus.NEWER_LEFT if time_diff > 0 else DiffStatus.NEWER_RIGHT
                    elif abs(time_diff) > 2.0:  # Allow 2-second timestamp tolerance for FAT32
                        status = DiffStatus.NEWER_LEFT if time_diff > 0 else DiffStatus.NEWER_RIGHT

                diff_entries.append(DiffEntry(
                    relative_path=rel,
                    left_path=str(left_base / rel),
                    right_path=str(right_base / rel),
                    status=status,
                    left_size=l_size,
                    right_size=r_size,
                    left_mtime=l_mtime,
                    right_mtime=r_mtime,
                    is_dir=False,
                ))

        return diff_entries

    @classmethod
    def execute_sync(
        cls,
        diff_list: List[DiffEntry],
        left_dir: str | Path,
        right_dir: str | Path,
        mode: SyncMode,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> SyncStats:
        """Execute folder synchronization according to selected SyncMode strategy."""
        left_base = Path(left_dir).resolve()
        right_base = Path(right_dir).resolve()
        stats = SyncStats()

        total = len(diff_list)

        for i, entry in enumerate(diff_list):
            if cancel_check and cancel_check():
                break
            if progress_cb:
                progress_cb(i + 1, total, entry.relative_path)

            l_path = left_base / entry.relative_path
            r_path = right_base / entry.relative_path

            try:
                if mode == SyncMode.MIRROR_LEFT_TO_RIGHT:
                    if entry.status in (DiffStatus.LEFT_ONLY, DiffStatus.NEWER_LEFT, DiffStatus.CONTENT_DIFF):
                        if entry.is_dir:
                            r_path.mkdir(parents=True, exist_ok=True)
                        else:
                            r_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(l_path, r_path)
                            stats.copied += 1
                            stats.bytes_transferred += entry.left_size
                    elif entry.status in (DiffStatus.RIGHT_ONLY,):
                        if r_path.is_dir():
                            shutil.rmtree(r_path, ignore_errors=True)
                        elif r_path.exists():
                            r_path.unlink()
                        stats.deleted += 1

                elif mode == SyncMode.MIRROR_RIGHT_TO_LEFT:
                    if entry.status in (DiffStatus.RIGHT_ONLY, DiffStatus.NEWER_RIGHT, DiffStatus.CONTENT_DIFF):
                        if entry.is_dir:
                            l_path.mkdir(parents=True, exist_ok=True)
                        else:
                            l_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(r_path, l_path)
                            stats.copied += 1
                            stats.bytes_transferred += entry.right_size
                    elif entry.status in (DiffStatus.LEFT_ONLY,):
                        if l_path.is_dir():
                            shutil.rmtree(l_path, ignore_errors=True)
                        elif l_path.exists():
                            l_path.unlink()
                        stats.deleted += 1

                elif mode == SyncMode.TWO_WAY_MERGE:
                    if entry.status == DiffStatus.LEFT_ONLY:
                        if entry.is_dir:
                            r_path.mkdir(parents=True, exist_ok=True)
                        else:
                            r_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(l_path, r_path)
                            stats.copied += 1
                            stats.bytes_transferred += entry.left_size
                    elif entry.status == DiffStatus.RIGHT_ONLY:
                        if entry.is_dir:
                            l_path.mkdir(parents=True, exist_ok=True)
                        else:
                            l_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(r_path, l_path)
                            stats.copied += 1
                            stats.bytes_transferred += entry.right_size
                    elif entry.status == DiffStatus.NEWER_LEFT:
                        if not entry.is_dir:
                            shutil.copy2(l_path, r_path)
                            stats.updated += 1
                            stats.bytes_transferred += entry.left_size
                    elif entry.status == DiffStatus.NEWER_RIGHT:
                        if not entry.is_dir:
                            shutil.copy2(r_path, l_path)
                            stats.updated += 1
                            stats.bytes_transferred += entry.right_size

                elif mode == SyncMode.UPDATE_NEWER:
                    if entry.status == DiffStatus.NEWER_LEFT:
                        if not entry.is_dir:
                            shutil.copy2(l_path, r_path)
                            stats.updated += 1
                            stats.bytes_transferred += entry.left_size
                    elif entry.status == DiffStatus.NEWER_RIGHT:
                        if not entry.is_dir:
                            shutil.copy2(r_path, l_path)
                            stats.updated += 1
                            stats.bytes_transferred += entry.right_size
            except Exception as exc:
                stats.errors.append(f"Sync failed for {entry.relative_path}: {exc}")

        return stats
