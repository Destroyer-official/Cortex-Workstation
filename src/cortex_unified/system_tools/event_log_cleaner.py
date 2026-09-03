"""Cortex Cleaner — Enterprise Windows Event Log Sweeper.

Enumerates Windows Event Log channels (Application, System, Security, PowerShell, Diagnostics),
inspects record counts and on-disk sizes (%WinDir%\\System32\\Winevt\\Logs),
and provides selective/batch clearing with automated EVTX backup archiving.
"""

from __future__ import annotations

import os
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class EventLogChannel:
    """Event Log Channel data container."""
    name: str
    file_path: str
    record_count: int
    size_bytes: int
    is_enabled: bool = True
    last_modified: float = 0.0


@dataclass
class EventLogCleanResult:
    """Event Log Clean Result data container."""
    channel: str
    records_cleared: int
    bytes_freed: int
    backup_path: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


class EventLogCleaner:
    """Production Windows Event Log manager and sweeper."""

    STANDARD_CHANNELS = [
        "Application",
        "System",
        "Security",
        "Setup",
        "Microsoft-Windows-PowerShell/Operational",
        "Windows PowerShell",
        "Microsoft-Windows-Diagnostics-Performance/Operational",
        "Microsoft-Windows-TaskScheduler/Operational",
        "Microsoft-Windows-WindowsUpdateClient/Operational",
        "Microsoft-Windows-CodeIntegrity/Operational",
        "Microsoft-Windows-NTLM/Operational",
        "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational",
        "Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational",
        "Microsoft-Windows-User Profile Service/Operational",
        "Microsoft-Windows-WMI-Activity/Operational",
    ]

    @classmethod
    def list_all_logs(
        cls,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[EventLogChannel]:
        """Enumerate all available Windows event log channels and their metrics."""
        if platform.system() != "Windows":
            return []

        logs_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "Winevt" / "Logs"
        channels: List[EventLogChannel] = []

        # High-speed disk scan of all .evtx files in Logs directory
        if logs_dir.is_dir():
            try:
                for entry in os.scandir(logs_dir):
                    if entry.is_file() and entry.name.lower().endswith(".evtx"):
                        try:
                            stat = entry.stat()
                            raw_name = entry.name[:-5]  # strip .evtx
                            ch_name = raw_name.replace("%4", "/")
                            # Estimate record count from evtx size (header ~4KB, avg record ~500B)
                            approx_records = max(0, (stat.st_size - 4096) // 512) if stat.st_size > 4096 else 0
                            channels.append(EventLogChannel(
                                name=ch_name,
                                file_path=entry.path,
                                record_count=approx_records,
                                size_bytes=stat.st_size,
                                is_enabled=True,
                                last_modified=stat.st_mtime,
                            ))
                        except Exception:
                            pass
            except Exception:
                pass

        if not channels:
            for ch in cls.STANDARD_CHANNELS:
                channels.append(EventLogChannel(name=ch, file_path="", record_count=0, size_bytes=0, is_enabled=True))

        return sorted(channels, key=lambda c: (c.size_bytes, c.record_count), reverse=True)

    @classmethod
    def clear_log(
        cls,
        channel_name: str,
        backup_directory: Optional[str | Path] = None,
    ) -> EventLogCleanResult:
        """Clear a specific Windows event log with optional backup export."""
        if platform.system() != "Windows":
            return EventLogCleanResult(channel_name, 0, 0, None, False, "Windows only")

        backup_file = None
        if backup_directory:
            b_dir = Path(backup_directory)
            b_dir.mkdir(parents=True, exist_ok=True)
            safe_name = channel_name.replace("/", "_").replace(" ", "_")
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_file = str(b_dir / f"{safe_name}_{timestamp}.evtx")

            # wevtutil epl
            try:
                subprocess.run(
                    ["wevtutil", "epl", channel_name, backup_file],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
            except Exception:
                backup_file = None

        # wevtutil cl
        try:
            res = subprocess.run(
                ["wevtutil", "cl", channel_name],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if res.returncode == 0:
                return EventLogCleanResult(channel_name, 0, 0, backup_file, True)
            return EventLogCleanResult(channel_name, 0, 0, backup_file, False, res.stderr.strip() or "Access Denied")
        except Exception as exc:
            return EventLogCleanResult(channel_name, 0, 0, backup_file, False, str(exc))

    @classmethod
    def clear_all_logs(
        cls,
        backup_directory: Optional[str | Path] = None,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
    ) -> Tuple[int, int, List[EventLogCleanResult]]:
        """Clean all active Windows event log channels."""
        channels = cls.list_all_logs()
        results: List[EventLogCleanResult] = []
        success_count = 0
        total_freed = 0

        for idx, ch in enumerate(channels):
            if progress_cb:
                progress_cb(idx + 1, len(channels), ch.name)

            res = cls.clear_log(ch.name, backup_directory)
            if res.success:
                res.bytes_freed = ch.size_bytes
                res.records_cleared = ch.record_count
                success_count += 1
                total_freed += ch.size_bytes
            results.append(res)

        return success_count, total_freed, results
