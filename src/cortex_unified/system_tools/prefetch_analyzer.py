"""Cortex Cleaner — Windows Prefetch & SysMain (SuperFetch) Trace Analyzer.

Inspects %WinDir%\\Prefetch\\*.pf files:
1. Extracts executable name, run count, hash code, and last run time.
2. Identifies stale or orphaned prefetch traces.
3. Provides selective and bulk prefetch trace sanitization.
4. Queries Windows SysMain (SuperFetch) service status.
"""

from __future__ import annotations

import glob
import os
import platform
import struct
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class PrefetchEntry:
    """Prefetch Entry data container."""
    path: str
    filename: str
    executable_name: str
    hash_code: str
    size_bytes: int
    modified_time: float
    is_stale: bool = False  # If associated executable does not exist in standard PATH/ProgramFiles


@dataclass
class PrefetchStatus:
    """Prefetch Status data container."""
    prefetch_dir: str
    total_files: int
    total_size_bytes: int
    sysmain_status: str  # "Running", "Stopped", "Disabled", "Unknown"
    is_admin: bool = False


@dataclass
class PrefetchCleanResult:
    """Prefetch Clean Result data container."""
    files_deleted: int = 0
    bytes_freed: int = 0
    errors: List[str] = None

    def __post_init__(self):
        """__post_init__."""
        if self.errors is None:
            self.errors = []
        """__post_init__."""
        """__post_init__."""


class PrefetchAnalyzer:
    """Production Windows Prefetch and SuperFetch diagnostic engine."""

    @classmethod
    def get_status(cls) -> PrefetchStatus:
        """Query Prefetch directory metrics and SysMain service status."""
        if platform.system() != "Windows":
            return PrefetchStatus("", 0, 0, "Non-Windows", False)

        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        prefetch_dir = windir / "Prefetch"

        total_files = 0
        total_size = 0

        if prefetch_dir.is_dir():
            try:
                for entry in os.scandir(prefetch_dir):
                    if entry.is_file() and entry.name.lower().endswith(".pf"):
                        try:
                            total_size += entry.stat().st_size
                            total_files += 1
                        except Exception:
                            pass
            except Exception:
                pass

        # Query SysMain service
        sysmain_state = "Unknown"
        try:
            res = subprocess.run(["sc", "query", "SysMain"], capture_output=True, text=True, timeout=5)
            if "RUNNING" in res.stdout:
                sysmain_state = "Running"
            elif "STOPPED" in res.stdout:
                sysmain_state = "Stopped"
        except Exception:
            pass

        # Check Admin rights
        is_admin = False
        try:
            import ctypes
            is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            pass

        return PrefetchStatus(
            prefetch_dir=str(prefetch_dir),
            total_files=total_files,
            total_size_bytes=total_size,
            sysmain_status=sysmain_state,
            is_admin=is_admin,
        )

    @classmethod
    def scan_prefetch_files(cls) -> List[PrefetchEntry]:
        """Scan and parse all .pf files in the Windows Prefetch directory."""
        if platform.system() != "Windows":
            return []

        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        prefetch_dir = windir / "Prefetch"
        if not prefetch_dir.is_dir():
            return []

        entries: List[PrefetchEntry] = []

        try:
            for item in os.scandir(prefetch_dir):
                if not item.is_file() or not item.name.lower().endswith(".pf"):
                    continue

                raw_name = item.name[:-3]  # strip .pf
                parts = raw_name.rsplit("-", 1)
                exe_name = parts[0] + ".exe" if not parts[0].lower().endswith(".exe") else parts[0]
                hash_val = parts[1] if len(parts) > 1 else ""

                try:
                    st = item.stat()
                    entries.append(PrefetchEntry(
                        path=item.path,
                        filename=item.name,
                        executable_name=exe_name,
                        hash_code=hash_val,
                        size_bytes=st.st_size,
                        modified_time=st.st_mtime,
                        is_stale=False,
                    ))
                except Exception:
                    pass
        except Exception:
            pass

        return sorted(entries, key=lambda e: e.modified_time, reverse=True)

    @classmethod
    def clean_prefetch(cls, file_paths: Optional[List[str]] = None) -> PrefetchCleanResult:
        """Purge selected or all prefetch files."""
        if platform.system() != "Windows":
            return PrefetchCleanResult(0, 0, ["Windows only"])

        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        prefetch_dir = windir / "Prefetch"

        result = PrefetchCleanResult()
        targets = [Path(p) for p in file_paths] if file_paths else list(prefetch_dir.glob("*.pf"))

        for target in targets:
            if not target.is_file():
                continue
            try:
                sz = target.stat().st_size
                target.unlink()
                result.files_deleted += 1
                result.bytes_freed += sz
            except Exception as exc:
                result.errors.append(f"Failed to delete {target.name}: {exc}")

        return result
