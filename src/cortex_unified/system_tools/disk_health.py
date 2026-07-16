"""Disk health (S.M.A.R.T.) reporting - read-only, honest.

Reads each physical disk's health/operational status (and, where the driver
exposes it, wear %, temperature and reallocated sectors) via Windows'
``Get-PhysicalDisk`` / ``Get-StorageReliabilityCounter``. Purely informational;
it never modifies anything. Values that a drive doesn't report are left as
``None`` rather than guessed.
"""

from __future__ import annotations

import json
import logging
import platform
import subprocess
from dataclasses import dataclass
from typing import Any

_LOG = logging.getLogger("cortex.system_tools.disk_health")
_IS_WINDOWS = platform.system() == "Windows"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0


@dataclass(slots=True)
class DiskHealth:
    name: str
    media_type: str
    health_status: str          # Healthy / Warning / Unhealthy / Unknown
    operational_status: str
    size_bytes: int = 0
    wear_percent: int | None = None
    temperature_c: int | None = None
    reallocated_sectors: int | None = None
    power_on_hours: int | None = None

    @property
    def is_healthy(self) -> bool:
        return self.health_status.lower() == "healthy"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "media_type": self.media_type,
            "health_status": self.health_status,
            "operational_status": self.operational_status,
            "size_bytes": self.size_bytes,
            "wear_percent": self.wear_percent,
            "temperature_c": self.temperature_c,
            "reallocated_sectors": self.reallocated_sectors,
            "power_on_hours": self.power_on_hours,
        }


class DiskHealthMonitor:
    """Reads S.M.A.R.T. / physical-disk health information."""

    @staticmethod
    def is_supported() -> bool:
        return _IS_WINDOWS

    def get_health(self) -> list[DiskHealth]:
        if not _IS_WINDOWS:
            return []
        script = (
            "$out=@();"
            "foreach($d in Get-PhysicalDisk){"
            "  $rc = $null;"
            "  try { $rc = $d | Get-StorageReliabilityCounter -ErrorAction SilentlyContinue } catch {}"
            "  $out += [pscustomobject]@{"
            "    Name=$d.FriendlyName; MediaType=$d.MediaType.ToString();"
            "    Health=$d.HealthStatus.ToString(); Op=($d.OperationalStatus -join ',');"
            "    Size=$d.Size;"
            "    Wear=(if($rc){$rc.Wear}else{$null});"
            "    Temp=(if($rc){$rc.Temperature}else{$null});"
            "    Realloc=(if($rc){$rc.ReadErrorsTotal}else{$null});"
            "    Hours=(if($rc){$rc.PowerOnHours}else{$null})"
            "  }"
            "}"
            "$out | ConvertTo-Json -Compress"
        )
        out = self._run(script)
        return self._parse(out)

    @staticmethod
    def _parse(out: str | None) -> list[DiskHealth]:
        if not out:
            return []
        try:
            data = json.loads(out)
        except (ValueError, TypeError):
            return []
        if isinstance(data, dict):
            data = [data]

        def _int(v):
            try:
                return int(v) if v is not None else None
            except (ValueError, TypeError):
                return None

        disks: list[DiskHealth] = []
        for d in data:
            disks.append(DiskHealth(
                name=str(d.get("Name") or "Unknown"),
                media_type=str(d.get("MediaType") or "Unspecified"),
                health_status=str(d.get("Health") or "Unknown"),
                operational_status=str(d.get("Op") or ""),
                size_bytes=_int(d.get("Size")) or 0,
                wear_percent=_int(d.get("Wear")),
                temperature_c=_int(d.get("Temp")),
                reallocated_sectors=_int(d.get("Realloc")),
                power_on_hours=_int(d.get("Hours")),
            ))
        return disks

    def _run(self, script: str) -> str | None:
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, timeout=45, creationflags=_NO_WINDOW,
            )
            return proc.stdout if proc.returncode == 0 else (proc.stdout or None)
        except (OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("disk health query failed: %s", exc)
            return None
