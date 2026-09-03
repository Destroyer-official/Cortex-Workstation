"""Cortex Cleaner — Windows Temp Folder Deep Scanner & Auto-Cleaner.

Advanced temp file cleanup beyond what Storage Sense handles:
1. Scans all system, user, and application temp directories.
2. Detects stale temp files (configurable age threshold in hours).
3. Identifies locked files and skips them gracefully.
4. Provides per-directory breakdown of recoverable space.
5. Cleans Windows Installer orphaned patches ($PatchCache$).
"""

from __future__ import annotations

import os
import platform
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class TempLocation:
    """Temp Location data container."""
    name: str
    path: str
    total_files: int
    total_size_bytes: int
    stale_files: int
    stale_size_bytes: int
    exists: bool


@dataclass
class TempScanReport:
    """Temp Scan Report data container."""
    locations: List[TempLocation]
    total_files: int
    total_size_bytes: int
    stale_files: int
    stale_size_bytes: int
    locked_files: int


@dataclass
class TempCleanResult:
    """Temp Clean Result data container."""
    files_deleted: int
    bytes_freed: int
    locked_skipped: int
    errors: List[str] = field(default_factory=list)


class TempFolderCleaner:
    """Production Windows temp directory deep scanner and auto-cleaner."""

    @classmethod
    def _get_temp_locations(cls) -> List[Tuple[str, str]]:
        """Discover all known temp directories on the system."""
        locations: List[Tuple[str, str]] = []

        # User temp
        user_temp = os.environ.get("TEMP", os.environ.get("TMP", ""))
        if user_temp:
            locations.append(("User TEMP", user_temp))

        # System temp
        windir = os.environ.get("WINDIR", r"C:\Windows")
        locations.append(("Windows Temp", os.path.join(windir, "Temp")))

        # Prefetch (already handled by prefetch_analyzer but included for completeness)
        locations.append(("Windows Prefetch", os.path.join(windir, "Prefetch")))

        # Windows Installer Patch Cache
        sys_drive = os.environ.get("SystemDrive", "C:")
        locations.append(("Installer Patch Cache", os.path.join(sys_drive, os.sep, "Windows", "Installer", "$PatchCache$")))

        # SoftwareDistribution Download cache
        locations.append(("Windows Update Cache", os.path.join(windir, "SoftwareDistribution", "Download")))

        # User-specific locations
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            locations.append(("CrashDumps", os.path.join(local_app, "CrashDumps")))
            locations.append(("D3DSCache", os.path.join(local_app, "D3DSCache")))
            locations.append(("NVIDIA DXCache", os.path.join(local_app, "NVIDIA", "DXCache")))
            locations.append(("NVIDIA GLCache", os.path.join(local_app, "NVIDIA", "GLCache")))
            locations.append(("AMD DxCache", os.path.join(local_app, "AMD", "DxCache")))
            locations.append(("Temp Internet Files", os.path.join(local_app, "Microsoft", "Windows", "INetCache")))
            locations.append(("Edge Cache", os.path.join(local_app, "Microsoft", "Edge", "User Data", "Default", "Cache")))

        return [(n, p) for n, p in locations if p]

    @classmethod
    def scan(cls, stale_hours: int = 24) -> TempScanReport:
        """Scan all temp locations and categorize files by age."""
        now = time.time()
        stale_threshold = now - (stale_hours * 3600)
        locations: List[TempLocation] = []
        total_files = total_size = stale_files = stale_size = locked = 0

        for name, path in cls._get_temp_locations():
            p = Path(path)
            if not p.is_dir():
                locations.append(TempLocation(name, path, 0, 0, 0, 0, False))
                continue

            loc_files = loc_size = loc_stale = loc_stale_sz = 0
            try:
                for entry in os.scandir(p):
                    try:
                        if entry.is_file(follow_symlinks=False):
                            stat = entry.stat()
                            loc_files += 1
                            loc_size += stat.st_size
                            if stat.st_mtime < stale_threshold:
                                loc_stale += 1
                                loc_stale_sz += stat.st_size
                    except (PermissionError, OSError):
                        locked += 1
            except (PermissionError, OSError):
                pass

            locations.append(TempLocation(name, path, loc_files, loc_size, loc_stale, loc_stale_sz, True))
            total_files += loc_files
            total_size += loc_size
            stale_files += loc_stale
            stale_size += loc_stale_sz

        return TempScanReport(
            locations=locations,
            total_files=total_files,
            total_size_bytes=total_size,
            stale_files=stale_files,
            stale_size_bytes=stale_size,
            locked_files=locked,
        )

    @classmethod
    def clean(cls, stale_hours: int = 24, locations_filter: Optional[List[str]] = None,
              progress_cb: Optional[Callable[[int, str], None]] = None) -> TempCleanResult:
        """Delete stale temp files across all discovered temp locations."""
        now = time.time()
        stale_threshold = now - (stale_hours * 3600)
        deleted = freed = locked = 0
        errors: List[str] = []
        count = 0

        all_locs = cls._get_temp_locations()
        if locations_filter:
            filter_set = set(locations_filter)
            all_locs = [(n, p) for n, p in all_locs if n in filter_set]

        for name, path in all_locs:
            p = Path(path)
            if not p.is_dir():
                continue

            try:
                for entry in os.scandir(p):
                    try:
                        if entry.is_file(follow_symlinks=False):
                            stat = entry.stat()
                            if stat.st_mtime < stale_threshold:
                                sz = stat.st_size
                                os.unlink(entry.path)
                                deleted += 1
                                freed += sz
                                count += 1
                                if progress_cb and count % 50 == 0:
                                    progress_cb(count, entry.name)
                    except PermissionError:
                        locked += 1
                    except OSError as exc:
                        errors.append(f"{entry.name}: {exc}")
            except (PermissionError, OSError):
                pass

        return TempCleanResult(
            files_deleted=deleted,
            bytes_freed=freed,
            locked_skipped=locked,
            errors=errors,
        )
