"""Cortex Cleaner — Volume Shadow Copy (VSS) & Snapshot Manager.

Provides programmatic inspection and maintenance of Windows Volume Shadow Copies:
- Discovers existing VSS snapshots, creation timestamps, and space consumption.
- Audits VSS shadow storage allocations (Used, Allocated, Maximum).
- Prunes stale or excessive shadow copies to reclaim gigabytes of disk space.
- Creates on-demand recovery snapshots before performing destructive cleanup operations.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("cortex.system_tools.vss_manager")


@dataclass
class ShadowCopyInfo:
    """Shadowcopyinfo.

    Manages ShadowCopyInfo operations and coordinates related state changes for the component.
    """
    shadow_id: str
    original_volume: str
    creation_time: str
    shadow_volume: str
    provider: str = "Microsoft Software Shadow Copy provider 1.0"
    attributes: str = "Persistent, Differential"


@dataclass
class ShadowStorageInfo:
    """Shadowstorageinfo.

    Manages ShadowStorageInfo operations and coordinates related state changes for the component.
    """
    for_volume: str
    on_volume: str
    used_bytes: int
    allocated_bytes: int
    max_bytes: int

    @property
    def used_gb(self) -> float:
        """Used gb.

        Manages used gb operations and coordinates related state changes for the component.

        Returns:
            float: Result of the operation.
        """
        return self.used_bytes / (1024**3)

    @property
    def allocated_gb(self) -> float:
        """Allocated gb.

        Manages allocated gb operations and coordinates related state changes for the component.

        Returns:
            float: Result of the operation.
        """
        return self.allocated_bytes / (1024**3)

    @property
    def max_gb(self) -> float:
        """Max gb.

        Manages max gb operations and coordinates related state changes for the component.

        Returns:
            float: Result of the operation.
        """
        return self.max_bytes / (1024**3)


@dataclass
class VssAuditReport:
    """Vssauditreport.

    Manages VssAuditReport operations and coordinates related state changes for the component.
    """
    shadows: list[ShadowCopyInfo] = field(default_factory=list)
    storages: list[ShadowStorageInfo] = field(default_factory=list)
    total_used_bytes: int = 0
    total_allocated_bytes: int = 0
    error: Optional[str] = None


class VssManager:
    """Vssmanager.

    Manages VssManager operations and coordinates related state changes for the component.
    """

    def __init__(self):
        """Initialize Vss Manager.

        Initializes the instance and configures internal state.
        """
        self._is_windows = os.name == "nt"

    def audit(self) -> VssAuditReport:
        """Audit.

        Manages audit operations and coordinates related state changes for the component.

        Returns:
            VssAuditReport: Result of the operation.
        """
        if not self._is_windows:
            return VssAuditReport(error="VSS management requires Windows NT.")

        shadows = self.list_shadows()
        storages = self.list_shadow_storage()

        tot_used = sum(s.used_bytes for s in storages)
        tot_alloc = sum(s.allocated_bytes for s in storages)

        return VssAuditReport(
            shadows=shadows,
            storages=storages,
            total_used_bytes=tot_used,
            total_allocated_bytes=tot_alloc,
        )

    def list_shadows(self) -> list[ShadowCopyInfo]:
        """List all active shadow copies via vssadmin.

        Manages list shadows operations and coordinates related state changes for the component.

        Returns:
            list[ShadowCopyInfo]: List of processed items or identifiers.
        """
        if not self._is_windows:
            return []

        cmd = ["vssadmin", "list", "shadows"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as exc:
            logger.warning("Failed to query vssadmin shadows: %s", exc)
            return []

        out = res.stdout or ""
        shadows: list[ShadowCopyInfo] = []

        curr_id = ""
        curr_orig = ""
        curr_time = ""
        curr_vol = ""
        curr_prov = ""

        for line in out.splitlines():
            line_str = line.strip()
            if "Shadow Copy ID:" in line_str:
                if curr_id:
                    shadows.append(
                        ShadowCopyInfo(
                            shadow_id=curr_id,
                            original_volume=curr_orig,
                            creation_time=curr_time,
                            shadow_volume=curr_vol,
                            provider=curr_prov or "Microsoft Software Shadow Copy provider",
                        )
                    )
                curr_id = line_str.split(":", 1)[1].strip()
                curr_orig = ""
                curr_time = ""
                curr_vol = ""
                curr_prov = ""
            elif "Original Volume:" in line_str:
                curr_orig = line_str.split(":", 1)[1].strip()
            elif "Creation Time:" in line_str:
                curr_time = line_str.split(":", 1)[1].strip()
            elif "Shadow Copy Volume:" in line_str:
                curr_vol = line_str.split(":", 1)[1].strip()
            elif "Provider:" in line_str:
                curr_prov = line_str.split(":", 1)[1].strip()

        if curr_id:
            shadows.append(
                ShadowCopyInfo(
                    shadow_id=curr_id,
                    original_volume=curr_orig,
                    creation_time=curr_time,
                    shadow_volume=curr_vol,
                    provider=curr_prov or "Microsoft Software Shadow Copy provider",
                )
            )

        return shadows

    def list_shadow_storage(self) -> list[ShadowStorageInfo]:
        """List shadow copy storage space allocations.

        Manages list shadow storage operations and coordinates related state changes for the component.

        Returns:
            list[ShadowStorageInfo]: List of processed items or identifiers.
        """
        if not self._is_windows:
            return []

        cmd = ["vssadmin", "list", "shadowstorage"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as exc:
            logger.warning("Failed to query vssadmin shadowstorage: %s", exc)
            return []

        out = res.stdout or ""
        storages: list[ShadowStorageInfo] = []

        for_vol = ""
        on_vol = ""
        used_b = 0
        alloc_b = 0
        max_b = 0

        def _parse_bytes(text: str) -> int:
            # Matches formats like '1.50 GB (1,610,612,736 B)' or '100 MB'
            """_parse_bytes.

            Manages parse bytes operations and coordinates related state changes for the component.

            Args:
                text (str): Display text string.

            Returns:
                int: Result of the operation.
            """
            m = re.search(r"\(([\d,]+)\s*B\)", text)
            if m:
                return int(m.group(1).replace(",", ""))
            m_num = re.search(r"([\d.]+)\s*(GB|MB|KB|TB)", text, re.I)
            if m_num:
                val = float(m_num.group(1))
                unit = m_num.group(2).upper()
                multipliers = {"KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
                return int(val * multipliers.get(unit, 1))
            return 0

        for line in out.splitlines():
            line_str = line.strip()
            if "For volume:" in line_str:
                if for_vol:
                    storages.append(
                        ShadowStorageInfo(
                            for_volume=for_vol,
                            on_volume=on_vol,
                            used_bytes=used_b,
                            allocated_bytes=alloc_b,
                            max_bytes=max_b,
                        )
                    )
                for_vol = line_str.split(":", 1)[1].strip()
                on_vol = ""
                used_b = alloc_b = max_b = 0
            elif "Shadow Copy Storage volume:" in line_str:
                on_vol = line_str.split(":", 1)[1].strip()
            elif "Used Shadow Copy Storage space:" in line_str:
                used_b = _parse_bytes(line_str)
            elif "Allocated Shadow Copy Storage space:" in line_str:
                alloc_b = _parse_bytes(line_str)
            elif "Maximum Shadow Copy Storage space:" in line_str:
                max_b = _parse_bytes(line_str)

        if for_vol:
            storages.append(
                ShadowStorageInfo(
                    for_volume=for_vol,
                    on_volume=on_vol,
                    used_bytes=used_b,
                    allocated_bytes=alloc_b,
                    max_bytes=max_b,
                )
            )

        return storages

    def create_shadow_copy(self, volume: str = "C:") -> tuple[bool, str]:
        """Create an on-demand volume shadow copy.

        Manages create shadow copy operations and coordinates related state changes for the component.

        Args:
            volume (str): The volume parameter.

        Returns:
            tuple[bool, str]: True if the operation succeeded, False otherwise.
        """
        if not self._is_windows:
            return False, "Windows required"

        clean_vol = volume.rstrip("\\")
        if not clean_vol.endswith(":"):
            clean_vol += ":"
        vol_path = clean_vol + "\\"

        # Use WMI / PowerShell to create a shadow copy
        ps_cmd = f'(Get-WmiObject -List Win32_ShadowCopy).Create("{vol_path}", "ClientAccessible")'
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if res.returncode == 0 and "ReturnValue = 0" in res.stdout:
                return True, f"Successfully created shadow copy for {clean_vol}"
            return False, res.stderr.strip() or res.stdout.strip() or "Failed to create snapshot"
        except Exception as exc:
            return False, str(exc)

    def delete_oldest_shadow(self, volume: str = "C:") -> tuple[bool, str]:
        """Delete the oldest shadow copy on a given volume to reclaim space.

        Manages delete oldest shadow operations and coordinates related state changes for the component.

        Args:
            volume (str): The volume parameter.

        Returns:
            tuple[bool, str]: True if the operation succeeded, False otherwise.
        """
        if not self._is_windows:
            return False, "Windows required"

        clean_vol = volume.rstrip("\\")
        if not clean_vol.endswith(":"):
            clean_vol += ":"

        cmd = ["vssadmin", "delete", "shadows", f"/for={clean_vol}", "/oldest", "/quiet"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if res.returncode == 0:
                return True, f"Deleted oldest shadow copy on {clean_vol}"
            return False, res.stderr.strip() or res.stdout.strip()
        except Exception as exc:
            return False, str(exc)
