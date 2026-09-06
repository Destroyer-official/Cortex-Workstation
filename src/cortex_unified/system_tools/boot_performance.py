"""Boot performance analysis - using Windows' OWN boot measurements.

Windows records detailed boot diagnostics in the event log
``Microsoft-Windows-Diagnostics-Performance/Operational``:

* Event ID 100 - a summary of each boot, including total boot time and the
  "main path" boot time (until the desktop is usable), in milliseconds.
* Event IDs 101/102/103/109 - specific apps, drivers, services or devices that
  Windows measured as taking *longer than usual* and thereby degrading your
  boot, each with the offending name and time impact.

Because these numbers come straight from Windows' own instrumentation, this is
an honest answer to "why is my PC slow to start?" - no guessing, no fabricated
"boot score". Read-only.
"""

from __future__ import annotations

import json
import logging
import sys
import subprocess
from dataclasses import dataclass
from typing import Any

from cortex_unified.core import proc as _proc

_LOG = logging.getLogger("cortex.system_tools.boot_performance")
_IS_WINDOWS = sys.platform == "win32"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

_LOG_NAME = "Microsoft-Windows-Diagnostics-Performance/Operational"

# Degradation event id -> the kind of thing that was slow.
_KIND = {
    "101": "Application",
    "102": "Driver",
    "103": "Service",
    "106": "Background optimization",
    "109": "Device",
}


@dataclass(slots=True)
class BootRecord:
    """One Windows boot timing summary from Event ID 100.

    Holds wall-clock boot and main-path times in milliseconds.
    """
    when: str
    boot_ms: int
    main_path_ms: int

    @property
    def boot_seconds(self) -> float:
        """Boot time in seconds derived from boot_ms.

        Returns:
            float: Result of the operation.
        """
        return round(self.boot_ms / 1000.0, 1)

    def to_dict(self) -> dict[str, Any]:
        """Serialize this boot record to a plain dict.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {"when": self.when, "boot_ms": self.boot_ms,
                "main_path_ms": self.main_path_ms, "boot_seconds": self.boot_seconds}


@dataclass(slots=True)
class BootIssue:
    """One boot-degrading item from Events 101/102/103/109.

    Records kind (app/driver/service/device), name, and time impact.
    """
    kind: str
    name: str
    impact_ms: int
    when: str

    @property
    def impact_seconds(self) -> float:
        """Degradation impact in seconds derived from impact_ms.

        Returns:
            float: Result of the operation.
        """
        return round(self.impact_ms / 1000.0, 1)

    def to_dict(self) -> dict[str, Any]:
        """Serialize this boot issue to a plain dict.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {"kind": self.kind, "name": self.name, "impact_ms": self.impact_ms,
                "impact_seconds": self.impact_seconds, "when": self.when}


class BootPerformanceMonitor:
    """Read-only analyzer of Windows boot performance event log.

    Queries Diagnostics-Performance log via PowerShell; Windows-only, no
    admin required for reads, no side effects.
    """

    @staticmethod
    def is_supported() -> bool:
        """True on Windows where the Diagnostics-Performance log exists.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return _IS_WINDOWS

    def analyze(self, max_boots: int = 10, max_issues: int = 40) -> dict[str, Any]:
        """Analyze recent boots and worst degraders from the event log.

        Read-only PowerShell query; returns boots/issues plus averages.

        Args:
            max_boots (int): The max boots parameter.
            max_issues (int): The max issues parameter.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        if not _IS_WINDOWS:
            return {"supported": False, "boots": [], "issues": []}
        out = self._run(self._script(max_boots, max_issues))
        boots, issues = self._parse(out)
        avg = round(sum(b.boot_ms for b in boots) / len(boots) / 1000.0, 1) if boots else 0.0
        return {
            "supported": True,
            "boots": [b.to_dict() for b in boots],
            "issues": [i.to_dict() for i in issues],
            "latest_seconds": boots[0].boot_seconds if boots else 0.0,
            "average_seconds": avg,
        }

    @staticmethod
    def _script(max_boots: int, max_issues: int) -> str:
        """Build the PowerShell script querying boot Events 100/101/102/103/109.

        Args:
            max_boots (int): The max boots parameter.
            max_issues (int): The max issues parameter.

        Returns:
            str: Formatted string or path.
        """
        return (
            f"$log='{_LOG_NAME}';"
            "function Fields($e){ $x=[xml]$e.ToXml(); $d=@{}; "
            "foreach($n in $x.Event.EventData.Data){ $d[$n.Name]=$n.'#text' }; return $d }"
            f"$boots=@(); Get-WinEvent -LogName $log -FilterXPath '*[System[EventID=100]]' "
            f"-MaxEvents {max_boots} -ErrorAction SilentlyContinue | ForEach-Object {{"
            " $d=Fields $_; $boots+=[pscustomobject]@{ Time=$_.TimeCreated.ToString('s');"
            " BootTime=$d['BootTime']; MainPath=$d['MainPathBootTime'] } };"
            f"$issues=@(); Get-WinEvent -LogName $log -FilterXPath "
            "'*[System[(EventID=101 or EventID=102 or EventID=103 or EventID=109)]]' "
            f"-MaxEvents {max_issues} -ErrorAction SilentlyContinue | ForEach-Object {{"
            " $d=Fields $_; $issues+=[pscustomobject]@{ Id=$_.Id.ToString();"
            " Name=$d['Name']; TotalTime=$d['TotalTime']; Time=$_.TimeCreated.ToString('s') } };"
            "[pscustomobject]@{ boots=$boots; issues=$issues } | ConvertTo-Json -Depth 4 -Compress"
        )

    @staticmethod
    def _parse(out: str | None) -> tuple[list[BootRecord], list[BootIssue]]:
        """Parse and decode structured data from strings or byte streams.

        Extracts fields, validates expected formats, and instantiates corresponding strongly-typed model objects.

        Args:
            out (str | None): The out parameter.

        Returns:
            tuple[list[BootRecord], list[BootIssue]]: List of processed items or identifiers.
        """
        if not out:
            return [], []
        try:
            data = json.loads(out)
        except (ValueError, TypeError):
            return [], []

        def _int(v):
            """Coerce an event-log value to int, returning 0 when missing.

            Args:
                v: The v parameter.
            """
            try:
                return int(float(v)) if v not in (None, "") else 0
            except (ValueError, TypeError):
                return 0

        def _as_list(v):
            """Normalize a JSON value to a list for uniform iteration.

            Args:
                v: The v parameter.
            """
            if v is None:
                return []
            return v if isinstance(v, list) else [v]

        boots: list[BootRecord] = []
        for b in _as_list(data.get("boots")):
            if not isinstance(b, dict):
                continue
            boots.append(BootRecord(
                when=str(b.get("Time") or ""),
                boot_ms=_int(b.get("BootTime")),
                main_path_ms=_int(b.get("MainPath")),
            ))

        issues: list[BootIssue] = []
        for it in _as_list(data.get("issues")):
            if not isinstance(it, dict):
                continue
            name = str(it.get("Name") or "").strip()
            if not name:
                continue
            issues.append(BootIssue(
                kind=_KIND.get(str(it.get("Id")), "Other"),
                name=name,
                impact_ms=_int(it.get("TotalTime")),
                when=str(it.get("Time") or ""),
            ))
        issues.sort(key=lambda i: i.impact_ms, reverse=True)
        return boots, issues

    def _run(self, script: str) -> str | None:
        """Run the boot-query PowerShell script with timeout, returning stdout.

        Returns None on failure; read-only, no side effects.

        Args:
            script (str): The script parameter.

        Returns:
            str | None: Formatted string or path.
        """
        try:
            proc = _proc.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                text=True, timeout=60, creationflags=_NO_WINDOW,
            )
            return proc.stdout if proc.returncode == 0 else None
        except (_proc.ProcessCancelled, OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("boot performance query failed: %s", exc)
            return None
