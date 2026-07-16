"""Driver inventory - READ-ONLY listing of installed device drivers.

Research is clear that automatic "driver updater" tools are a common vector for
scareware and bundled junk, and that pushing generic drivers can destabilize a
system. So Cortex intentionally does NOT download or install drivers. Instead
it gives you an honest, read-only inventory (device name, provider, version,
date) via ``Get-CimInstance Win32_PnPSignedDriver`` so you can check versions
yourself against the manufacturer's site. Nothing here modifies the system.
"""

from __future__ import annotations

import json
import logging
import platform
import subprocess
from dataclasses import dataclass
from typing import Any

_LOG = logging.getLogger("cortex.system_tools.driver_inventory")
_IS_WINDOWS = platform.system() == "Windows"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0


@dataclass(slots=True)
class DriverInfo:
    device_name: str
    provider: str
    version: str
    date: str
    device_class: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_name": self.device_name,
            "provider": self.provider,
            "version": self.version,
            "date": self.date,
            "device_class": self.device_class,
        }


class DriverInventory:
    """Read-only inventory of signed device drivers (Windows)."""

    @staticmethod
    def is_supported() -> bool:
        return _IS_WINDOWS

    def list_drivers(self) -> list[DriverInfo]:
        if not _IS_WINDOWS:
            return []
        script = (
            "Get-CimInstance Win32_PnPSignedDriver | "
            "Where-Object { $_.DeviceName -ne $null } | "
            "Select-Object DeviceName,DriverProviderName,DriverVersion,DriverDate,DeviceClass | "
            "ConvertTo-Json -Compress"
        )
        return self._parse(self._run(script))

    @staticmethod
    def _parse(out: str | None) -> list[DriverInfo]:
        if not out:
            return []
        try:
            data = json.loads(out)
        except (ValueError, TypeError):
            return []
        if isinstance(data, dict):
            data = [data]

        drivers: list[DriverInfo] = []
        seen: set[tuple[str, str]] = set()
        for d in data:
            if not isinstance(d, dict):
                continue
            name = str(d.get("DeviceName") or "").strip()
            if not name:
                continue
            version = str(d.get("DriverVersion") or "")
            key = (name, version)
            if key in seen:
                continue
            seen.add(key)
            drivers.append(DriverInfo(
                device_name=name,
                provider=str(d.get("DriverProviderName") or ""),
                version=version,
                date=DriverInventory._clean_date(d.get("DriverDate")),
                device_class=str(d.get("DeviceClass") or ""),
            ))
        drivers.sort(key=lambda x: (x.device_class, x.device_name))
        return drivers

    @staticmethod
    def _clean_date(raw: Any) -> str:
        if not raw:
            return ""
        s = str(raw)
        # WMI dates arrive as '/Date(1690000000000)/' or 'YYYYMMDD...'.
        if s.startswith("/Date(") and s.endswith(")/"):
            try:
                import datetime
                ms = int(s[6:-2].split("+")[0].split("-")[0])
                return datetime.datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d")
            except (ValueError, OverflowError, OSError):
                return ""
        if len(s) >= 8 and s[:8].isdigit():
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        return s

    def _run(self, script: str) -> str | None:
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, timeout=60, creationflags=_NO_WINDOW,
            )
            return proc.stdout if proc.returncode == 0 else None
        except (OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("driver inventory query failed: %s", exc)
            return None
