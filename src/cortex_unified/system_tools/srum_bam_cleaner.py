"""Windows BAM/DAM & SRUM Forensic Privacy Cleaner.

Inspects and sanitizes deep Windows execution tracking artifacts:
1. BAM (Background Activity Moderator) & DAM (Desktop Activity Moderator):
   Registry persistence tracking exact execution timestamps of every executable run.
   Located under: HKLM\\SYSTEM\\CurrentControlSet\\Services\\bam\\State\\UserSettings\\<SID>
2. SRUM (System Resource Usage Monitor):
   ESE database tracking historical per-process network bandwidth, CPU seconds, and energy.
   Located under: C:\\Windows\\System32\\sru\\SRUDB.dat
"""

from __future__ import annotations

import datetime
import logging
import os
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

_LOG = logging.getLogger("cortex.system_tools.srum_bam")

try:
    import winreg
except ImportError:
    winreg = None  # type: ignore[assignment]


@dataclass
class BamExecutionEntry:
    """Represents an execution record captured by BAM/DAM."""

    path: str
    last_run_timestamp: str
    epoch_time: float
    user_sid: str
    source: str  # "bam" or "dam"

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "path": self.path,
            "last_run": self.last_run_timestamp,
            "epoch": self.epoch_time,
            "user_sid": self.user_sid,
            "source": self.source,
        }


@dataclass
class SrumDatabaseInfo:
    """Status of the Windows SRUM forensic database."""

    db_path: str
    exists: bool
    size_bytes: int
    modified_time: str
    is_locked_by_system: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "path": self.db_path,
            "exists": self.exists,
            "size_bytes": self.size_bytes,
            "modified": self.modified_time,
            "is_locked": self.is_locked_by_system,
        }


@dataclass
class SrumBamReport:
    """Forensic report containing BAM/DAM execution traces and SRUM metrics."""

    bam_entries: List[BamExecutionEntry] = field(default_factory=list)
    srum_info: Optional[SrumDatabaseInfo] = None
    cleaned_entries_count: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "bam_entries_count": len(self.bam_entries),
            "srum_info": self.srum_info.to_dict() if self.srum_info else None,
            "cleaned_count": self.cleaned_entries_count,
            "errors": self.errors,
            "sample_entries": [e.to_dict() for e in self.bam_entries[:50]],
        }


class SrumBamCleaner:
    """Forensic scanner and cleaner for Windows BAM/DAM and SRUM stores."""

    SRUM_PATH = Path("C:\\Windows\\System32\\sru\\SRUDB.dat")

    @classmethod
    def _filetime_to_datetime(cls, ft_bytes: bytes) -> Tuple[str, float]:
        """Convert an 8-byte Windows FILETIME structure to ISO timestamp and UNIX epoch."""
        if len(ft_bytes) < 8:
            return "Unknown", 0.0
        try:
            ft = struct.unpack("<Q", ft_bytes[:8])[0]
            if ft == 0:
                return "Never", 0.0
            # FILETIME epoch is Jan 1, 1601; Unix epoch is Jan 1, 1970 (11644473600 seconds)
            epoch = (ft / 10_000_000.0) - 11644473600.0
            if epoch < 0:
                return "Corrupt/Invalid", 0.0
            dt = datetime.datetime.fromtimestamp(epoch, tz=datetime.timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC"), epoch
        except Exception:
            return "Invalid Timestamp", 0.0

    def query_srum(self) -> SrumDatabaseInfo:
        """Inspect the presence, size, and status of Windows SRUM database."""
        p = self.SRUM_PATH
        if not p.exists():
            return SrumDatabaseInfo(
                db_path=str(p),
                exists=False,
                size_bytes=0,
                modified_time="N/A",
                is_locked_by_system=False,
            )

        try:
            st = p.stat()
            sz = st.st_size
            mtime = datetime.datetime.fromtimestamp(st.st_mtime, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        except (OSError, PermissionError):
            sz = 0
            mtime = "Locked"

        # Check if exclusively locked by Windows Diagnostic Policy Service (DPS)
        is_locked = True
        try:
            with open(p, "rb") as f:
                f.read(16)
            is_locked = False
        except (OSError, PermissionError):
            is_locked = True

        return SrumDatabaseInfo(
            db_path=str(p),
            exists=True,
            size_bytes=sz,
            modified_time=mtime,
            is_locked_by_system=is_locked,
        )

    def scan(self) -> SrumBamReport:
        """Scan BAM, DAM, and SRUM execution traces."""
        report = SrumBamReport()
        report.srum_info = self.query_srum()

        if winreg is None or sys.platform != "win32":
            return report

        services_to_probe = [
            ("bam", r"SYSTEM\CurrentControlSet\Services\bam\State\UserSettings"),
            ("dam", r"SYSTEM\CurrentControlSet\Services\dam\State\UserSettings"),
        ]

        for source_tag, base_reg in services_to_probe:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_reg, 0, winreg.KEY_READ) as user_settings_key:
                    # Enumerate User SIDs
                    num_subkeys, _, _ = winreg.QueryInfoKey(user_settings_key)
                    for sid_idx in range(num_subkeys):
                        try:
                            sid_str = winreg.EnumKey(user_settings_key, sid_idx)
                            with winreg.OpenKey(user_settings_key, sid_str, 0, winreg.KEY_READ) as sid_key:
                                num_values = winreg.QueryInfoKey(sid_key)[1]
                                for val_idx in range(num_values):
                                    val_name, val_data, val_type = winreg.EnumValue(sid_key, val_idx)
                                    if not val_name or val_name.startswith("SequenceNumber") or val_name.startswith("Version"):
                                        continue

                                    # Binary payload contains FILETIME
                                    if isinstance(val_data, bytes):
                                        ts_str, epoch = self._filetime_to_datetime(val_data)
                                    else:
                                        ts_str, epoch = "Unknown", 0.0

                                    entry = BamExecutionEntry(
                                        path=val_name,
                                        last_run_timestamp=ts_str,
                                        epoch_time=epoch,
                                        user_sid=sid_str,
                                        source=source_tag,
                                    )
                                    report.bam_entries.append(entry)
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                continue

        # Sort by most recent execution first
        report.bam_entries.sort(key=lambda x: x.epoch_time, reverse=True)
        return report

    def clean_bam_entries(self, entries: Optional[List[BamExecutionEntry]] = None) -> int:
        """Sanitize specified or all BAM/DAM registry execution records."""
        if winreg is None or sys.platform != "win32":
            return 0

        to_clean = entries if entries is not None else self.scan().bam_entries
        cleaned_count = 0

        # Group by (source, sid) -> list of paths
        grouped: Dict[Tuple[str, str], List[str]] = {}
        for e in to_clean:
            key = (e.source, e.user_sid)
            grouped.setdefault(key, []).append(e.path)

        for (source_tag, sid_str), paths in grouped.items():
            reg_path = f"SYSTEM\\CurrentControlSet\\Services\\{source_tag}\\State\\UserSettings\\{sid_str}"
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_SET_VALUE) as key:
                    for p in paths:
                        try:
                            winreg.DeleteValue(key, p)
                            cleaned_count += 1
                        except (OSError, PermissionError):
                            pass
            except (OSError, PermissionError):
                continue

        return cleaned_count
