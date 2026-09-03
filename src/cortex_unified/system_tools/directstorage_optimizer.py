"""Windows 11 DirectStorage & BypassIO Hardware Acceleration Auditor.

Audits per-volume BypassIO capability (FSCTL_MANAGE_BYPASS_IO) introduced in Windows 11
for DirectStorage v1.2+ GPU decompression pipelines. Identifies incompatible storage stacks,
legacy file system minifilters, or third-party filter drivers blocking direct NVMe transfers.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOG = logging.getLogger("cortex.system_tools.directstorage")


@dataclass
class BypassIoVolumeReport:
    """BypassIO and DirectStorage status for a single storage volume."""

    volume_letter: str
    is_supported: bool
    status_reason: str
    storage_type: str
    driver_name: str
    blocking_minifilters: List[str] = field(default_factory=list)
    raw_output: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "volume": self.volume_letter,
            "supported": self.is_supported,
            "status_reason": self.status_reason,
            "storage_type": self.storage_type,
            "driver": self.driver_name,
            "blocking_minifilters": self.blocking_minifilters,
        }


@dataclass
class DirectStorageAuditReport:
    """Comprehensive system-wide DirectStorage readiness report."""

    volumes: List[BypassIoVolumeReport] = field(default_factory=list)
    total_volumes: int = 0
    directstorage_ready_volumes: int = 0
    os_supported: bool = True
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "total_volumes": self.total_volumes,
            "ready_volumes": self.directstorage_ready_volumes,
            "os_supported": self.os_supported,
            "recommendations": self.recommendations,
            "volumes": [v.to_dict() for v in self.volumes],
        }


class DirectStorageOptimizer:
    """Audits and provides diagnostics for Windows DirectStorage and BypassIO."""

    def __init__(self) -> None:
        """Initialize Direct Storage Optimizer."""
        self.fsutil_path = shutil.which("fsutil")

    @classmethod
    def parse_bypassio_output(cls, volume: str, text: str) -> BypassIoVolumeReport:
        """Parse the standard stdout of 'fsutil bypassio state <volume> /v'."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        is_supported = False
        status_reason = "Unknown"
        storage_type = "Unknown"
        driver_name = "Unknown"
        blocking_filters: List[str] = []

        for line in lines:
            lower = line.lower()
            if "bypassio is supported" in lower or "bypassio state: supported" in lower:
                is_supported = True
                status_reason = "Supported"
            elif "not supported" in lower or "disabled" in lower:
                is_supported = False
                status_reason = line.split(":", 1)[-1].strip() if ":" in line else line
            elif "storage type:" in lower:
                storage_type = line.split(":", 1)[-1].strip()
            elif "volume driver:" in lower or "driver name:" in lower:
                driver_name = line.split(":", 1)[-1].strip()
            elif "incompatible driver:" in lower or "blocking driver:" in lower or "filter:" in lower:
                flt = line.split(":", 1)[-1].strip()
                if flt and flt.lower() not in [f.lower() for f in blocking_filters]:
                    blocking_filters.append(flt)

        if not is_supported and status_reason == "Unknown" and lines:
            status_reason = lines[0]

        return BypassIoVolumeReport(
            volume_letter=volume,
            is_supported=is_supported,
            status_reason=status_reason,
            storage_type=storage_type,
            driver_name=driver_name,
            blocking_minifilters=blocking_filters,
            raw_output=text,
        )

    def _get_active_drives(self) -> List[str]:
        """Detect all mounted active drive letters on Windows."""
        drives = []
        if sys.platform != "win32":
            return ["C:"]
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if bitmask & 1:
                    drives.append(f"{letter}:")
                bitmask >>= 1
        except Exception:
            drives = ["C:"]
        return drives

    def audit(self) -> DirectStorageAuditReport:
        """Audit all mounted volumes for DirectStorage BypassIO readiness."""
        report = DirectStorageAuditReport()

        if sys.platform != "win32" or not self.fsutil_path:
            report.os_supported = False
            report.recommendations.append("BypassIO is only available on Windows 11 (build 22000+) with NVMe storage.")
            return report

        drives = self._get_active_drives()
        for drive in drives:
            try:
                # Run fsutil bypassio state C: /v
                proc = subprocess.run(
                    [self.fsutil_path, "bypassIo", "state", drive, "/v"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
                output = proc.stdout or proc.stderr or ""
                vol_rep = self.parse_bypassio_output(drive, output)
            except Exception as e:
                _LOG.warning("Failed to query BypassIO on %s: %s", drive, e)
                vol_rep = BypassIoVolumeReport(
                    volume_letter=drive,
                    is_supported=False,
                    status_reason=str(e),
                    storage_type="Unknown",
                    driver_name="Unknown",
                )

            report.volumes.append(vol_rep)
            report.total_volumes += 1
            if vol_rep.is_supported:
                report.directstorage_ready_volumes += 1

        # Recommendations logic
        if report.directstorage_ready_volumes == 0:
            report.recommendations.append(
                "No volume currently has BypassIO enabled. Ensure games and assets reside on an NVMe SSD."
            )
        else:
            report.recommendations.append(
                f"DirectStorage BypassIO is operational on {report.directstorage_ready_volumes} volume(s)."
            )

        for v in report.volumes:
            if v.blocking_minifilters:
                report.recommendations.append(
                    f"Volume {v.volume_letter} is blocked by minifilters: {', '.join(v.blocking_minifilters)}. "
                    "Consider updating or whitelisting DirectStorage in your antivirus/filter driver stack."
                )

        return report
