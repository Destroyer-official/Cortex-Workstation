"""Immutable-ish data models shared across the engine.

These are plain ``dataclasses`` (not Pydantic) because they sit on hot paths
(millions of files) where per-object validation overhead would matter. Values
are produced internally by trusted code, so validation lives at the boundaries
instead.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class StorageKind(str, enum.Enum):
    """Physical medium backing a path.

    The distinction drives whether multi-pass overwriting is meaningful:
    it only is on ``HDD``. On ``SSD``/``NVME`` the controller relocates writes
    (wear-leveling / copy-on-write), so overwriting cannot guarantee the old
    blocks are gone.
    """

    HDD = "hdd"          # rotational; overwrite passes are effective
    SSD = "ssd"          # solid state; overwrite passes are NOT reliable
    NVME = "nvme"        # NVMe SSD; same caveat as SSD
    REMOVABLE = "removable"  # USB / SD; treat like SSD for wiping purposes
    NETWORK = "network"  # network share; no local wiping guarantees
    UNKNOWN = "unknown"

    @property
    def overwrite_effective(self) -> bool:
        """True only when physically overwriting bytes reliably destroys data."""
        return self is StorageKind.HDD


class DeletionMethod(str, enum.Enum):
    """How an item should be removed."""

    DRY_RUN = "dry_run"      # report only, touch nothing
    RECYCLE = "recycle"      # move to OS trash/recycle bin (reversible)
    DELETE = "delete"        # unlink/rmtree, no overwrite
    OVERWRITE = "overwrite"  # overwrite then delete (HDD-effective only)


class DeletionOutcome(str, enum.Enum):
    """Result of a single item deletion."""

    WOULD_DELETE = "would_delete"     # dry-run success
    RECYCLED = "recycled"
    DELETED = "deleted"
    OVERWRITTEN = "overwritten"
    SKIPPED_UNSAFE = "skipped_unsafe"  # blocked by PathGuard
    FAILED = "failed"


@dataclass(slots=True)
class FileEntry:
    """A single filesystem entry discovered during a scan.

    ``size`` and ``mtime`` are captured from the ``DirEntry`` stat cache to avoid
    a second ``stat`` syscall on the hot path.
    """

    path: Path
    size: int
    mtime: float
    is_dir: bool = False
    is_symlink: bool = False

    @property
    def age_days(self) -> float:
        import time
        return max(0.0, (time.time() - self.mtime) / 86400.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "size": self.size,
            "mtime": self.mtime,
            "is_dir": self.is_dir,
            "is_symlink": self.is_symlink,
        }


@dataclass(slots=True)
class ScanResult:
    """Aggregate result of a traversal."""

    files: list[FileEntry] = field(default_factory=list)
    dirs: list[FileEntry] = field(default_factory=list)
    total_bytes: int = 0
    files_scanned: int = 0
    dirs_scanned: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "files": [f.to_dict() for f in self.files],
            "dirs": [d.to_dict() for d in self.dirs],
            "total_bytes": self.total_bytes,
            "files_scanned": self.files_scanned,
            "dirs_scanned": self.dirs_scanned,
            "error_count": self.error_count,
            "duration_seconds": round(self.duration_seconds, 4),
        }


@dataclass(slots=True)
class DeletionResult:
    """Per-item deletion record plus batch aggregation helpers."""

    path: Path
    outcome: DeletionOutcome
    method: DeletionMethod
    size: int = 0
    reason: str = ""
    backup_path: Path | None = None

    @property
    def succeeded(self) -> bool:
        return self.outcome not in (DeletionOutcome.FAILED, DeletionOutcome.SKIPPED_UNSAFE)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "outcome": self.outcome.value,
            "method": self.method.value,
            "size": self.size,
            "reason": self.reason,
            "backup_path": str(self.backup_path) if self.backup_path else None,
        }
