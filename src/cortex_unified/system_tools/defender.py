"""Windows Security (Defender) status + quick scan trigger.

Surfaces the protection state most users never check - is real-time protection
on, when did it last scan, are signatures current - and lets them kick off a
quick scan. It reads ``Get-MpComputerStatus`` / ``Get-MpThreatDetection`` and
starts scans with ``Start-MpScan`` (the official Defender PowerShell module).
Read-only status; scanning is an explicit, harmless action the user triggers.
"""

from __future__ import annotations

import json
import logging
import sys
import subprocess
from dataclasses import dataclass
from typing import Any

from cortex_unified.core import proc as _proc

_LOG = logging.getLogger("cortex.system_tools.defender")
_IS_WINDOWS = sys.platform == "win32"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0


@dataclass(slots=True)
class DefenderStatus:
    """Defenderstatus.

    Manages DefenderStatus operations and coordinates related state changes for the component.
    """
    available: bool
    realtime_protection: bool = False
    antivirus_enabled: bool = False
    tamper_protection: bool = False
    signature_version: str = ""
    signature_age_days: int | None = None
    last_quick_scan: str = ""
    last_full_scan: str = ""
    engine_version: str = ""

    @property
    def healthy(self) -> bool:
        """Healthy.

        Manages healthy operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return (self.available and self.realtime_protection and self.antivirus_enabled
                and (self.signature_age_days is None or self.signature_age_days <= 7))

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "available": self.available,
            "realtime_protection": self.realtime_protection,
            "antivirus_enabled": self.antivirus_enabled,
            "tamper_protection": self.tamper_protection,
            "signature_version": self.signature_version,
            "signature_age_days": self.signature_age_days,
            "last_quick_scan": self.last_quick_scan,
            "last_full_scan": self.last_full_scan,
            "engine_version": self.engine_version,
            "healthy": self.healthy,
        }


class WindowsDefender:
    """Windowsdefender.

    Manages WindowsDefender operations and coordinates related state changes for the component.
    """

    @staticmethod
    def is_supported() -> bool:
        """Is supported.

        Manages is supported operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return _IS_WINDOWS

    def status(self) -> DefenderStatus:
        """Status.

        Manages status operations and coordinates related state changes for the component.

        Returns:
            DefenderStatus: Result of the operation.
        """
        if not _IS_WINDOWS:
            return DefenderStatus(available=False)
        script = (
            "$s = Get-MpComputerStatus | Select-Object AMRunningMode,"
            "RealTimeProtectionEnabled,AntivirusEnabled,IsTamperProtected,"
            "AntivirusSignatureVersion,AntivirusSignatureAge,QuickScanEndTime,"
            "FullScanEndTime,AMEngineVersion;"
            "$s | ConvertTo-Json -Compress"
        )
        return self._parse_status(self._run(script, timeout=30))

    @staticmethod
    def _parse_status(out: str | None) -> DefenderStatus:
        """_parse_status.

        Manages parse status operations and coordinates related state changes for the component.

        Args:
            out (str | None): The out parameter.

        Returns:
            DefenderStatus: Result of the operation.
        """
        if not out:
            return DefenderStatus(available=False)
        try:
            d = json.loads(out)
        except (ValueError, TypeError):
            return DefenderStatus(available=False)
        if isinstance(d, list):
            d = d[0] if d else {}

        def _int(v):
            """Int.

            Manages int operations and coordinates related state changes for the component.

            Args:
                v: The v parameter.
            """
            try:
                return int(v) if v is not None else None
            except (ValueError, TypeError):
                return None

        return DefenderStatus(
            available=True,
            realtime_protection=bool(d.get("RealTimeProtectionEnabled")),
            antivirus_enabled=bool(d.get("AntivirusEnabled")),
            tamper_protection=bool(d.get("IsTamperProtected")),
            signature_version=str(d.get("AntivirusSignatureVersion") or ""),
            signature_age_days=_int(d.get("AntivirusSignatureAge")),
            last_quick_scan=WindowsDefender._clean_date(d.get("QuickScanEndTime")),
            last_full_scan=WindowsDefender._clean_date(d.get("FullScanEndTime")),
            engine_version=str(d.get("AMEngineVersion") or ""),
        )

    def recent_threats(self, limit: int = 20) -> list[dict[str, Any]]:
        """Recent threats.

        Manages recent threats operations and coordinates related state changes for the component.

        Args:
            limit (int): The limit parameter.

        Returns:
            list[dict[str, Any]]: List of processed items or identifiers.
        """
        if not _IS_WINDOWS:
            return []
        script = (
            f"Get-MpThreatDetection -ErrorAction SilentlyContinue | "
            f"Sort-Object InitialDetectionTime -Descending | Select-Object -First {limit} "
            "ThreatID,@{n='Time';e={$_.InitialDetectionTime.ToString('s')}},"
            "@{n='Threat';e={(Get-MpThreat -ThreatID $_.ThreatID -ErrorAction SilentlyContinue).ThreatName}} "
            "| ConvertTo-Json -Compress"
        )
        out = self._run(script, timeout=30)
        return self._parse_threats(out)

    @staticmethod
    def _parse_threats(out: str | None) -> list[dict[str, Any]]:
        """_parse_threats.

        Manages parse threats operations and coordinates related state changes for the component.

        Args:
            out (str | None): The out parameter.

        Returns:
            list[dict[str, Any]]: List of processed items or identifiers.
        """
        if not out:
            return []
        try:
            data = json.loads(out)
        except (ValueError, TypeError):
            return []
        if isinstance(data, dict):
            data = [data]
        threats = []
        for t in data:
            if isinstance(t, dict):
                threats.append({
                    "time": str(t.get("Time") or ""),
                    "threat": str(t.get("Threat") or "Unknown"),
                    "id": t.get("ThreatID"),
                })
        return threats

    def start_quick_scan(self) -> tuple[bool, str]:
        """Kick off a Defender quick scan (harmless; scans, doesn't delete data).

        Manages start quick scan operations and coordinates related state changes for the component.

        Returns:
            tuple[bool, str]: True if the operation succeeded, False otherwise.
        """
        if not _IS_WINDOWS:
            return False, "Windows only."
        out = self._run("Start-MpScan -ScanType QuickScan", timeout=60 * 20,
                        want_returncode=True)
        if out is True:
            return True, "Quick scan completed."
        return False, "Could not run the quick scan (Defender may be managed or disabled)."

    @staticmethod
    def _clean_date(raw: Any) -> str:
        """_clean_date.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

        Args:
            raw (Any): The raw parameter.

        Returns:
            str: Formatted string or path.
        """
        if not raw:
            return ""
        s = str(raw)
        if s.startswith("/Date(") and s.endswith(")/"):
            try:
                import datetime
                ms = int(s[6:-2].split("+")[0].split("-")[0])
                return datetime.datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M")
            except (ValueError, OverflowError, OSError):
                return ""
        return s.replace("T", " ")[:16]

    def _run(self, script: str, timeout: int, want_returncode: bool = False):
        """Run.

        Manages run operations and coordinates related state changes for the component.

        Args:
            script (str): The script parameter.
            timeout (int): The timeout parameter.
            want_returncode (bool): The want returncode parameter.
        """
        try:
            # A quick scan can run for many minutes; poll the timeout instead of
            # blocking uninterruptibly, and kill the whole tree if it fires
            # (never the calling thread - see core/proc.py).
            proc = _proc.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                text=True, timeout=timeout, creationflags=_NO_WINDOW,
            )
            if want_returncode:
                return proc.returncode == 0
            return proc.stdout if proc.returncode == 0 else None
        except (_proc.ProcessCancelled, OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("defender query failed: %s", exc)
            return False if want_returncode else None
