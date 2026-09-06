"""Volume Shadow Copy (VSS) Writer Health, Shadow Storage & State Recovery Engine.

Research Grounding
------------------
* Microsoft Volume Shadow Copy Service (VSS) Architecture (Windows Server & Windows 10/11):
  VSS coordinates volume block snapshots between Requestors (backup software), Writers
  (applications like Registry, Hyper-V, MSSearch, and System Writer), and Providers.
* Interrupted Snapshot Deadlocks:
  When an update, crash, or backup fails midway, VSS writers often freeze in
  `[5] Waiting for completion` or `[8] Failed` states. In this state, Windows cannot
  create new restore points, system backups fail, and orphaned differential area
  storage accumulates in `System Volume Information`.
* Storage Allocations (`vssadmin list shadowstorage`):
  NTFS shadow copies use a dynamic Copy-on-Write diff area. Auditing allocated vs
  maximum shadow storage bounds ensures unconstrained growth is detected before disk starvation.

This module parses `vssadmin list writers` and `vssadmin list shadowstorage`,
flags stalled or failed writers, and provides automated 1-click state reset.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from cortex_unified.core import proc as _proc

_LOG = logging.getLogger("cortex.system_tools.vss_health")
_IS_WINDOWS = sys.platform == "win32"


@dataclass
class VssWriterStatus:
    """Record holding name, writer_id, state_code, state_desc, last_error, is_healthy."""
    name: str
    writer_id: str
    state_code: int
    state_desc: str
    last_error: str
    is_healthy: bool

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict with keys name, writer_id, state_code, state_desc, last_error, is_healthy.

        Returns:
        Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "name": self.name,
            "writer_id": self.writer_id,
            "state_code": self.state_code,
            "state_desc": self.state_desc,
            "last_error": self.last_error,
            "is_healthy": self.is_healthy,
        }


@dataclass
class VssStorageAllocation:
    """Record holding for_volume, shadow_volume, used_bytes, allocated_bytes, max_bytes."""
    for_volume: str
    shadow_volume: str
    used_bytes: int = 0
    allocated_bytes: int = 0
    max_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict with keys for_volume, shadow_volume, used_bytes, allocated_bytes, max_bytes.

        Returns:
        Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "for_volume": self.for_volume,
            "shadow_volume": self.shadow_volume,
            "used_bytes": self.used_bytes,
            "allocated_bytes": self.allocated_bytes,
            "max_bytes": self.max_bytes,
        }


@dataclass
class VssHealthReport:
    """Record holding writers, storage_allocations, healthy_writer_count, failed_writer_count, total_shadow_used_bytes, scan_duration_ms."""
    writers: List[VssWriterStatus] = field(default_factory=list)
    storage_allocations: List[VssStorageAllocation] = field(default_factory=list)
    healthy_writer_count: int = 0
    failed_writer_count: int = 0
    total_shadow_used_bytes: int = 0
    scan_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict with keys writers, storage_allocations, healthy_writer_count, failed_writer_count, total_shadow_used_bytes, scan_duration_ms.

        Returns:
        Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "writers": [w.to_dict() for w in self.writers],
            "storage_allocations": [s.to_dict() for s in self.storage_allocations],
            "healthy_writer_count": self.healthy_writer_count,
            "failed_writer_count": self.failed_writer_count,
            "total_shadow_used_bytes": self.total_shadow_used_bytes,
            "scan_duration_ms": self.scan_duration_ms,
        }


@dataclass
class VssResetResult:
    """Record holding success, restarted_services, message."""
    success: bool
    restarted_services: List[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict with keys success, restarted_services, message.

        Returns:
        Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "success": self.success,
            "restarted_services": self.restarted_services,
            "message": self.message,
        }


class VssHealthAnalyzer:
    """Groups related helpers: init, inspect health, parse writers, build writer status, parse shadowstorage, build storage allocation, reset vss writers. Windows-only; returns a safe default elsewhere."""

    def __init__(self) -> None:
        """Initialize Vss Health Analyzer.

        Initializes the instance and configures internal state.
        """
        self.logger = _LOG

    def inspect_health(self) -> VssHealthReport:
        """Query vssadmin for active writers and volume shadow storage bounds.

        Returns:
        VssHealthReport: Result of the operation.
        """
        t0 = time.perf_counter()
        report = VssHealthReport()

        if not _IS_WINDOWS:
            report.healthy_writer_count = 1
            report.writers.append(
                VssWriterStatus(
                    name="System Writer (Emulated)",
                    writer_id="{e81062d3-180e-4366-b94f-95cb2778ac9f}",
                    state_code=1,
                    state_desc="[1] Stable",
                    last_error="No error",
                    is_healthy=True,
                )
            )
            report.scan_duration_ms = (time.perf_counter() - t0) * 1000.0
            return report

        # 1. Parse vssadmin list writers
        try:
            res = _proc.run(["vssadmin", "list", "writers"])
            if res.stdout:
                report.writers = self._parse_writers(res.stdout)
                for w in report.writers:
                    if w.is_healthy:
                        report.healthy_writer_count += 1
                    else:
                        report.failed_writer_count += 1
        except Exception as exc:
            self.logger.debug("Failed querying vssadmin list writers: %s", exc)

        # 2. Parse vssadmin list shadowstorage
        try:
            res = _proc.run(["vssadmin", "list", "shadowstorage"])
            if res.stdout:
                report.storage_allocations = self._parse_shadowstorage(res.stdout)
                report.total_shadow_used_bytes = sum(s.used_bytes for s in report.storage_allocations)
        except Exception as exc:
            self.logger.debug("Failed querying vssadmin list shadowstorage: %s", exc)

        report.scan_duration_ms = (time.perf_counter() - t0) * 1000.0
        return report

    def _parse_writers(self, text: str) -> List[VssWriterStatus]:
        """Parse writers helper. Returns writers.

        Args:
        text (str): Display text string.

        Returns:
        List[VssWriterStatus]: List of processed items or identifiers.
        """
        writers: List[VssWriterStatus] = []
        current: Dict[str, str] = {}

        for line in text.splitlines():
            line_str = line.strip()
            if not line_str:
                if "name" in current:
                    writers.append(self._build_writer_status(current))
                    current = {}
                continue

            if line_str.startswith("Writer name:"):
                if "name" in current:
                    writers.append(self._build_writer_status(current))
                    current = {}
                current["name"] = line_str.split(":", 1)[1].strip().strip("'\"")
            elif line_str.startswith("Writer Id:"):
                current["id"] = line_str.split(":", 1)[1].strip()
            elif line_str.startswith("State:"):
                current["state"] = line_str.split(":", 1)[1].strip()
            elif line_str.startswith("Last error:"):
                current["error"] = line_str.split(":", 1)[1].strip()

        if "name" in current:
            writers.append(self._build_writer_status(current))

        return writers

    def _build_writer_status(self, d: Dict[str, str]) -> VssWriterStatus:
        """Build writer status helper. Returns VssWriterStatus.

        Args:
        d (Dict[str, str]): The d parameter.

        Returns:
        VssWriterStatus: Result of the operation.
        """
        name = d.get("name", "Unknown Writer")
        wid = d.get("id", "")
        state_str = d.get("state", "[1] Stable")
        err_str = d.get("error", "No error")

        code = 1
        m = re.search(r"\[(\d+)\]", state_str)
        if m:
            code = int(m.group(1))

        is_healthy = code == 1 and err_str.lower() in ("no error", "")

        return VssWriterStatus(
            name=name,
            writer_id=wid,
            state_code=code,
            state_desc=state_str,
            last_error=err_str,
            is_healthy=is_healthy,
        )

    def _parse_shadowstorage(self, text: str) -> List[VssStorageAllocation]:
        """Parse shadowstorage helper. Returns allocs.

        Args:
        text (str): Display text string.

        Returns:
        List[VssStorageAllocation]: List of processed items or identifiers.
        """
        allocs: List[VssStorageAllocation] = []
        current: Dict[str, str] = {}

        for line in text.splitlines():
            line_str = line.strip()
            if not line_str:
                if "for_volume" in current:
                    allocs.append(self._build_storage_allocation(current))
                    current = {}
                continue

            if "For volume:" in line_str:
                current["for_volume"] = line_str.split(":", 1)[1].strip()
            elif "Shadow Copy Storage volume:" in line_str:
                current["shadow_volume"] = line_str.split(":", 1)[1].strip()
            elif "Used Shadow Copy Storage space:" in line_str:
                current["used"] = line_str.split(":", 1)[1].strip()
            elif "Allocated Shadow Copy Storage space:" in line_str:
                current["allocated"] = line_str.split(":", 1)[1].strip()
            elif "Maximum Shadow Copy Storage space:" in line_str:
                current["max"] = line_str.split(":", 1)[1].strip()

        if "for_volume" in current:
            allocs.append(self._build_storage_allocation(current))

        return allocs

    def _build_storage_allocation(self, d: Dict[str, str]) -> VssStorageAllocation:
        """Build storage allocation helper. Returns int(m.group(1)).

        Args:
        d (Dict[str, str]): The d parameter.

        Returns:
        VssStorageAllocation: Result of the operation.
        """
        def _parse_bytes(s: str) -> int:
            # Format: '1.234 GB (1234567890 B)'
            """Parse bytes helper. Returns int(m.group(1)).

            Args:
            s (str): The s parameter.

            Returns:
            int: Result of the operation.
            """
            m = re.search(r"\((\d+)\s*B\)", s)
            if m:
                return int(m.group(1))
            return 0

        return VssStorageAllocation(
            for_volume=d.get("for_volume", ""),
            shadow_volume=d.get("shadow_volume", ""),
            used_bytes=_parse_bytes(d.get("used", "")),
            allocated_bytes=_parse_bytes(d.get("allocated", "")),
            max_bytes=_parse_bytes(d.get("max", "")),
        )

    def reset_vss_writers(self) -> VssResetResult:
        """Reset stalled VSS writers by cycling dependent Windows services.

        Returns:
        VssResetResult: Result of the operation.
        """
        if not _IS_WINDOWS:
            return VssResetResult(True, ["vss", "swprv"], "[Emulated] VSS services cycled on non-Windows host.")

        services = ["vss", "swprv", "cryptsvc"]
        restarted: List[str] = []

        for svc in services:
            try:
                _proc.run(["net", "stop", svc, "/y"])
                res = _proc.run(["net", "start", svc])
                if res.returncode == 0:
                    restarted.append(svc)
            except Exception as exc:
                self.logger.debug("Failed cycling service %s: %s", svc, exc)

        success = len(restarted) > 0
        msg = (
            f"Successfully cycled {len(restarted)} VSS subsystem services ({', '.join(restarted)})."
            if success
            else "Failed to cycle VSS services (Administrative privileges required)."
        )
        return VssResetResult(success, restarted, msg)
