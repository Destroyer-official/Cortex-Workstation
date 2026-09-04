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
        """True only when physically overwriting bytes reliably destroys data.

        Manages overwrite effective operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return self is StorageKind.HDD


class DeletionMethod(str, enum.Enum):
    """Deletionmethod.

    Manages DeletionMethod operations and coordinates related state changes for the component.
    """

    DRY_RUN = "dry_run"      # report only, touch nothing
    RECYCLE = "recycle"      # move to OS trash/recycle bin (reversible)
    DELETE = "delete"        # unlink/rmtree, no overwrite
    OVERWRITE = "overwrite"  # overwrite then delete (HDD-effective only)


class DeletionOutcome(str, enum.Enum):
    """Deletionoutcome.

    Manages DeletionOutcome operations and coordinates related state changes for the component.
    """

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

    ``size`` is always the *logical* size reported by the filesystem. For sparse,
    NTFS-compressed and cloud-placeholder files that overstates the space a
    deletion would actually reclaim, so ``on_disk`` carries the allocated size
    when it was measured. ``attrs``/``reparse_tag`` are the raw Windows values
    captured during the walk, which lets consumers ask "is this a cloud
    placeholder?" without a second syscall.
    """

    path: Path
    size: int
    mtime: float
    is_dir: bool = False
    is_symlink: bool = False
    attrs: int = 0
    reparse_tag: int = 0
    on_disk: int | None = None

    @property
    def age_days(self) -> float:
        """age_days.

        Manages age days operations and coordinates related state changes for the component.

        Returns:
            float: Result of the operation.
        """
        import time
        return max(0.0, (time.time() - self.mtime) / 86400.0)

    @property
    def reclaimable_size(self) -> int:
        """Bytes that deleting this entry would actually free.

        Falls back to the logical size when the allocated size wasn't measured,
        and is 0 for cloud placeholders because their bytes are not here.
        """
        from . import winattrs
        if winattrs.is_dehydrated(self.attrs):
            return 0
        return self.size if self.on_disk is None else self.on_disk

    @property
    def is_cloud_placeholder(self) -> bool:
        """True when the content lives in the cloud, not on this disk.

        Manages is cloud placeholder operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        from . import winattrs
        return winattrs.is_dehydrated(self.attrs)

    @property
    def is_junction(self) -> bool:
        """True for a junction / volume mount point (not a symlink to Python).

        Manages is junction operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        from . import winattrs
        return winattrs.is_junction(self.reparse_tag)

    @property
    def special_note(self) -> str:
        """Short human explanation of any special storage behaviour, or ``""``.

        Manages special note operations and coordinates related state changes for the component.

        Returns:
            str: Formatted string or path.
        """
        from . import winattrs
        return winattrs.describe(self.attrs, self.reparse_tag)

    def to_dict(self) -> dict[str, Any]:
        """to_dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "path": str(self.path),
            "size": self.size,
            "mtime": self.mtime,
            "is_dir": self.is_dir,
            "is_symlink": self.is_symlink,
            "on_disk": self.on_disk,
            "cloud_placeholder": self.is_cloud_placeholder,
            "note": self.special_note,
        }


@dataclass(slots=True)
class ScanResult:
    """Aggregate result of a traversal.

    Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
    """

    files: list[FileEntry] = field(default_factory=list)
    dirs: list[FileEntry] = field(default_factory=list)
    total_bytes: int = 0
    files_scanned: int = 0
    dirs_scanned: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    #: Files left out because their bytes live in the cloud, not on this disk.
    #: Reported rather than silently dropped so the UI can say so out loud.
    cloud_skipped: int = 0
    cloud_skipped_bytes: int = 0
    #: Junctions / mount points not descended into, to avoid double counting.
    junctions_skipped: int = 0

    @property
    def error_count(self) -> int:
        """error_count.

        Manages error count operations and coordinates related state changes for the component.

        Returns:
            int: Result of the operation.
        """
        return len(self.errors)

    def to_dict(self) -> dict[str, Any]:
        """to_dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "files": [f.to_dict() for f in self.files],
            "dirs": [d.to_dict() for d in self.dirs],
            "total_bytes": self.total_bytes,
            "files_scanned": self.files_scanned,
            "dirs_scanned": self.dirs_scanned,
            "error_count": self.error_count,
            "duration_seconds": round(self.duration_seconds, 4),
            "cloud_skipped": self.cloud_skipped,
            "cloud_skipped_bytes": self.cloud_skipped_bytes,
            "junctions_skipped": self.junctions_skipped,
        }


@dataclass(slots=True)
class DeletionResult:
    """Deletionresult.

    Manages DeletionResult operations and coordinates related state changes for the component.
    """

    path: Path
    outcome: DeletionOutcome
    method: DeletionMethod
    size: int = 0
    reason: str = ""
    backup_path: Path | None = None

    @property
    def succeeded(self) -> bool:
        """Succeeded.

        Manages succeeded operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return self.outcome not in (DeletionOutcome.FAILED, DeletionOutcome.SKIPPED_UNSAFE)

    def to_dict(self) -> dict[str, Any]:
        """to_dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "path": str(self.path),
            "outcome": self.outcome.value,
            "method": self.method.value,
            "size": self.size,
            "reason": self.reason,
            "backup_path": str(self.backup_path) if self.backup_path else None,
        }
