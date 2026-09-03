"""Cortex Cleaner — Windows Crash Dump & Error Reporting (WER) Cleaner.

Discovers and safely sanitizes Windows Kernel Memory Dumps (MEMORY.DMP), Minidumps,
LiveKernelReports, User-Mode Crash Dumps (%LocalAppData%\\CrashDumps), and WER report queues.
"""

from __future__ import annotations

import glob
import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class CrashDumpItem:
    """Crash Dump Item data container."""
    path: str
    filename: str
    category: str  # "Kernel Dump", "Minidump", "LiveKernel", "User CrashDump", "WER Report"
    size_bytes: int
    modified_time: float


@dataclass
class CrashDumpCleanReport:
    """Crash Dump Clean Report data container."""
    total_found: int = 0
    total_bytes_found: int = 0
    files_deleted: int = 0
    bytes_freed: int = 0
    errors: List[str] = None

    def __post_init__(self):
        """__post_init__."""
        if self.errors is None:
            self.errors = []
        """__post_init__."""
        """__post_init__."""


class CrashDumpCleaner:
    """Production Windows crash dump and WER queue sanitizer."""

    @classmethod
    def scan_dumps(cls) -> List[CrashDumpItem]:
        """Scan all known Windows crash dump and error reporting locations."""
        if platform.system() != "Windows":
            return []

        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        program_data = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
        local_app_data = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))

        items: List[CrashDumpItem] = []

        # 1. Kernel Dump (MEMORY.DMP)
        mem_dmp = windir / "MEMORY.DMP"
        if mem_dmp.is_file():
            try:
                st = mem_dmp.stat()
                items.append(CrashDumpItem(str(mem_dmp), mem_dmp.name, "Kernel Memory Dump", st.st_size, st.st_mtime))
            except Exception:
                pass

        # 2. Minidump folder
        minidump_dir = windir / "Minidump"
        if minidump_dir.is_dir():
            for f in minidump_dir.glob("*.dmp"):
                try:
                    st = f.stat()
                    items.append(CrashDumpItem(str(f), f.name, "Kernel Minidump", st.st_size, st.st_mtime))
                except Exception:
                    pass

        # 3. LiveKernelReports
        live_dir = windir / "LiveKernelReports"
        if live_dir.is_dir():
            for f in live_dir.rglob("*.dmp"):
                try:
                    st = f.stat()
                    items.append(CrashDumpItem(str(f), f.name, "LiveKernel Report", st.st_size, st.st_mtime))
                except Exception:
                    pass

        # 4. User-mode Crash Dumps (%LocalAppData%\CrashDumps)
        user_dumps = local_app_data / "CrashDumps"
        if user_dumps.is_dir():
            for f in user_dumps.glob("*.dmp"):
                try:
                    st = f.stat()
                    items.append(CrashDumpItem(str(f), f.name, "User Application CrashDump", st.st_size, st.st_mtime))
                except Exception:
                    pass

        # 5. WER Report Queues & Archives
        wer_dirs = [
            program_data / "Microsoft" / "Windows" / "WER" / "ReportArchive",
            program_data / "Microsoft" / "Windows" / "WER" / "ReportQueue",
            program_data / "Microsoft" / "Windows" / "WER" / "Temp",
            local_app_data / "Microsoft" / "Windows" / "WER" / "ReportArchive",
            local_app_data / "Microsoft" / "Windows" / "WER" / "ReportQueue",
        ]

        for w_dir in wer_dirs:
            if w_dir.is_dir():
                for f in w_dir.rglob("*"):
                    if f.is_file():
                        try:
                            st = f.stat()
                            items.append(CrashDumpItem(str(f), f.name, "WER Error Report", st.st_size, st.st_mtime))
                        except Exception:
                            pass

        return sorted(items, key=lambda x: x.size_bytes, reverse=True)

    @classmethod
    def clean_dumps(cls, items_to_delete: Optional[List[CrashDumpItem]] = None) -> CrashDumpCleanReport:
        """Purge selected or all discovered crash dumps and WER files."""
        if items_to_delete is None:
            items_to_delete = cls.scan_dumps()

        report = CrashDumpCleanReport(
            total_found=len(items_to_delete),
            total_bytes_found=sum(item.size_bytes for item in items_to_delete),
        )

        for item in items_to_delete:
            p = Path(item.path)
            if p.is_file():
                try:
                    size = p.stat().st_size
                    p.unlink()
                    report.files_deleted += 1
                    report.bytes_freed += size
                except Exception as exc:
                    report.errors.append(f"Failed to delete {p.name}: {exc}")

        return report
