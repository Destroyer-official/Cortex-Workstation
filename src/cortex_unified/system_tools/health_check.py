"""One-click PC health check - aggregates the fast, read-only diagnostics.

Runs a handful of cheap, honest checks (free space, memory pressure, drive
S.M.A.R.T. health, boot time, and Windows Security state), each producing a
clear status and, where relevant, a pointer to the page that fixes it. It then
rolls them into an overall score/grade.

Design principles:
* Every check is read-only and quick - no long scans, no system changes.
* A check that can't gather data reports "unknown" (info), never a fake pass.
* The score is a transparent weighted deduction, not a mysterious number.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

_LOG = logging.getLogger("cortex.system_tools.health_check")
_IS_WINDOWS = sys.platform == "win32"

# severity -> points deducted from 100
_DEDUCT = {"good": 0, "info": 0, "warning": 12, "critical": 30}


@dataclass(slots=True)
class HealthCheck:
    """Healthcheck.

    Manages HealthCheck operations and coordinates related state changes for the component.
    """
    id: str
    title: str
    severity: str          # good / warning / critical / info
    detail: str
    action_page: str = ""  # page id to jump to, if any

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {"id": self.id, "title": self.title, "severity": self.severity,
                "detail": self.detail, "action_page": self.action_page}


@dataclass(slots=True)
class HealthReport:
    """Healthreport.

    Manages HealthReport operations and coordinates related state changes for the component.
    """
    checks: list[HealthCheck] = field(default_factory=list)
    score: int = 100
    grade: str = "A"

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {"checks": [c.to_dict() for c in self.checks],
                "score": self.score, "grade": self.grade}


ProgressCB = Callable[[str], None]


class HealthChecker:
    """Healthchecker.

    Manages HealthChecker operations and coordinates related state changes for the component.
    """

    def run(self, progress: ProgressCB | None = None) -> HealthReport:
        """Run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.

        Args:
            progress (ProgressCB | None): The progress parameter.

        Returns:
            HealthReport: Result of the operation.
        """
        checks: list[HealthCheck] = []
        steps = [
            ("Checking free disk space\u2026", self._check_disk_space),
            ("Checking memory\u2026", self._check_memory),
            ("Checking drive health\u2026", self._check_disk_health),
            ("Checking boot performance\u2026", self._check_boot),
            ("Checking security\u2026", self._check_security),
            ("Checking Windows Update\u2026", self._check_updates),
        ]
        for msg, fn in steps:
            if progress:
                progress(msg)
            try:
                c = fn()
                if c is not None:
                    checks.append(c)
            except Exception as exc:  # noqa: BLE001 - a broken check must not fail the report
                _LOG.debug("health check %s failed: %s", fn.__name__, exc)
        score, grade = self._score(checks)
        return HealthReport(checks=checks, score=score, grade=grade)

    # -- scoring (pure, testable) ------------------------------------------

    @staticmethod
    def _score(checks: list[HealthCheck]) -> tuple[int, str]:
        """Score.

        Manages score operations and coordinates related state changes for the component.

        Args:
            checks (list[HealthCheck]): The checks parameter.

        Returns:
            tuple[int, str]: Formatted string or path.
        """
        score = 100
        for c in checks:
            score -= _DEDUCT.get(c.severity, 0)
        score = max(0, min(100, score))
        if score >= 90:
            grade = "A"
        elif score >= 75:
            grade = "B"
        elif score >= 60:
            grade = "C"
        elif score >= 40:
            grade = "D"
        else:
            grade = "F"
        return score, grade

    # -- individual checks --------------------------------------------------

    @staticmethod
    def _check_disk_space() -> HealthCheck:
        """_check_disk_space.

        Manages check disk space operations and coordinates related state changes for the component.

        Returns:
            HealthCheck: Result of the operation.
        """
        import shutil
        root = str(Path.home().anchor or (os.environ.get("SystemDrive", "C:") + "\\")) if _IS_WINDOWS else "/"
        total, used, free = shutil.disk_usage(root)
        pct_free = (free / total * 100) if total else 0
        free_gb = free / 1024 ** 3
        if pct_free < 10:
            sev, detail = "critical", (f"Only {pct_free:.0f}% free ({free_gb:.0f} GB). "
                                       "Low space slows Windows and blocks updates.")
        elif pct_free < 20:
            sev, detail = "warning", (f"{pct_free:.0f}% free ({free_gb:.0f} GB). "
                                      "Consider freeing some space.")
        else:
            sev, detail = "good", f"{pct_free:.0f}% free ({free_gb:.0f} GB). Plenty of room."
        return HealthCheck("disk_space", "Free disk space", sev, detail, "dashboard")

    @staticmethod
    def _check_memory() -> HealthCheck:
        """_check_memory.

        Manages check memory operations and coordinates related state changes for the component.

        Returns:
            HealthCheck: Result of the operation.
        """
        try:
            import psutil
        except ImportError:
            return HealthCheck("memory", "Memory", "info", "psutil unavailable.")
        vm = psutil.virtual_memory()
        if vm.percent >= 90:
            sev, detail = "warning", (f"Memory is {vm.percent:.0f}% used right now. "
                                      "Close heavy apps or check the Task Manager.")
        else:
            sev, detail = "good", f"Memory is {vm.percent:.0f}% used - comfortable."
        return HealthCheck("memory", "Memory usage", sev, detail, "processes")

    @staticmethod
    def _check_disk_health() -> HealthCheck | None:
        """_check_disk_health.

        Manages check disk health operations and coordinates related state changes for the component.

        Returns:
            HealthCheck | None: Result of the operation.
        """
        if not _IS_WINDOWS:
            return None
        from cortex_unified.system_tools.disk_health import DiskHealthMonitor
        disks = DiskHealthMonitor().get_health()
        if not disks:
            return HealthCheck("disk_health", "Drive health", "info",
                               "Could not read S.M.A.R.T. status (may need Administrator).",
                               "diskhealth")
        unhealthy = [d for d in disks if not d.is_healthy]
        if unhealthy:
            names = ", ".join(d.name for d in unhealthy)
            return HealthCheck("disk_health", "Drive health", "critical",
                               f"{len(unhealthy)} drive(s) not healthy: {names}. Back up now.",
                               "diskhealth")
        return HealthCheck("disk_health", "Drive health", "good",
                           f"All {len(disks)} drive(s) report healthy.", "diskhealth")

    @staticmethod
    def _check_boot() -> HealthCheck | None:
        """_check_boot.

        Manages check boot operations and coordinates related state changes for the component.

        Returns:
            HealthCheck | None: Result of the operation.
        """
        if not _IS_WINDOWS:
            return None
        from cortex_unified.system_tools.boot_performance import BootPerformanceMonitor
        data = BootPerformanceMonitor().analyze(max_boots=5, max_issues=10)
        latest = data.get("latest_seconds", 0.0)
        if not latest:
            return HealthCheck("boot", "Boot performance", "info",
                               "No boot diagnostics available yet.", "bootperf")
        issues = data.get("issues", [])
        top = issues[0]["name"] if issues else ""
        if latest > 150:
            sev, detail = "critical", (f"Boot takes {latest:.0f}s"
                                       + (f"; worst offender: {top}." if top else "."))
        elif latest > 75:
            sev, detail = "warning", (f"Boot takes {latest:.0f}s"
                                      + (f"; consider disabling {top} at startup." if top else "."))
        else:
            sev, detail = "good", f"Boot takes {latest:.0f}s - fast."
        return HealthCheck("boot", "Boot performance", sev, detail, "bootperf")

    @staticmethod
    def _check_security() -> HealthCheck | None:
        """_check_security.

        Manages check security operations and coordinates related state changes for the component.

        Returns:
            HealthCheck | None: Result of the operation.
        """
        if not _IS_WINDOWS:
            return None
        from cortex_unified.system_tools.defender import WindowsDefender
        s = WindowsDefender().status()
        if not s.available:
            return HealthCheck("security", "Security", "info",
                               "Windows Defender status unavailable (may be managed by "
                               "another product).", "security")
        if not s.realtime_protection:
            return HealthCheck("security", "Security", "warning",
                               "Real-time protection is OFF.", "security")
        if s.signature_age_days is not None and s.signature_age_days > 7:
            return HealthCheck("security", "Security", "warning",
                               f"Antivirus signatures are {s.signature_age_days} days old.",
                               "security")
        return HealthCheck("security", "Security", "good",
                           "Defender is on with current signatures.", "security")

    @staticmethod
    def _check_updates() -> HealthCheck | None:
        """_check_updates.

        Manages check updates operations and coordinates related state changes for the component.

        Returns:
            HealthCheck | None: Result of the operation.
        """
        if not _IS_WINDOWS:
            return None
        from cortex_unified.system_tools.windows_update import WindowsUpdate
        last_install = WindowsUpdate().last_activity().get("last_install", "")
        if not last_install:
            return HealthCheck("updates", "Windows Update", "info",
                               "Could not read last update date.", "winupdate")
        # Parse the registry timestamp ("YYYY-MM-DD HH:MM:SS") and age it.
        try:
            import datetime
            dt = datetime.datetime.strptime(last_install[:19], "%Y-%m-%d %H:%M:%S")
            age_days = (datetime.datetime.now() - dt).days
        except (ValueError, TypeError):
            return HealthCheck("updates", "Windows Update", "info",
                               f"Last install: {last_install}.", "winupdate")
        if age_days > 45:
            sev = "warning"
            detail = f"Last update installed {age_days} days ago - check for updates."
        else:
            sev = "good"
            detail = f"Last update installed {age_days} day(s) ago."
        return HealthCheck("updates", "Windows Update", sev, detail, "winupdate")
