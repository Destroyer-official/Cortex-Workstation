"""Safe Windows scheduling for unattended private-LAN inventory scans."""

from __future__ import annotations

import platform
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from cortex_unified.core import proc
from cortex_unified.system_tools.network_service_scanner import (
    parse_allowed_networks,
    parse_custom_port_spec,
)

_TASK_NAME = r"\Cortex Cleaner\Network Security Audit"
_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
_WEEKDAYS = {
    "MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN",
}


@dataclass(frozen=True, slots=True)
class NetworkSchedule:
    """Network Schedule data container."""
    frequency: str = "daily"
    time: str = "09:00"
    weekday: str = "MON"
    interval_hours: int = 1
    profile: str = "targeted"
    scopes: tuple[str, ...] = ()
    ports: str = ""
    output: str = ""


class NetworkScheduleError(RuntimeError):
    """Raised when schedule validation or OS task creation fails."""


def _validated(spec: NetworkSchedule) -> NetworkSchedule:
    """_validated."""
    frequency = spec.frequency.strip().lower()
    if frequency not in {"hourly", "daily", "weekly"}:
        raise ValueError("frequency must be hourly, daily, or weekly")
    if spec.profile not in {"targeted", "advanced"}:
        raise ValueError("scheduled profile must be targeted or advanced")
    if not _TIME_RE.fullmatch(spec.time):
        raise ValueError("schedule time must use 24-hour HH:MM format")
    weekday = spec.weekday.strip().upper()
    if weekday not in _WEEKDAYS:
        raise ValueError("invalid weekly schedule day")
    interval = int(spec.interval_hours)
    if not 1 <= interval <= 24:
        raise ValueError("hourly interval must be from 1 through 24")
    scopes = tuple(map(str, parse_allowed_networks(spec.scopes)))
    ports = ",".join(map(str, parse_custom_port_spec(spec.ports)))
    output = (
        str(Path(spec.output).expanduser()) if spec.output else
        str(Path.home() / ".cortex_cleaner" / "netdata" /
            "last-scheduled-network-scan.json")
    )
    return NetworkSchedule(
        frequency, spec.time, weekday, interval, spec.profile,
        scopes, ports, output,
    )
    """_validated."""
    """_validated."""


def build_scan_command(spec: NetworkSchedule) -> list[str]:
    """Build the fixed CLI command; no user-provided executable is accepted."""
    selected = _validated(spec)
    command = [
        sys.executable, "-m",
        "cortex_unified.system_tools.network_scan_cli",
        "--profile", selected.profile,
    ]
    for scope in selected.scopes:
        command.extend(["--scope", scope])
    if selected.ports:
        command.extend(["--ports", selected.ports])
    if selected.output:
        command.extend(["--output", selected.output])
    return command


def build_windows_arguments(spec: NetworkSchedule) -> list[str]:
    """Build windows arguments."""
    selected = _validated(spec)
    trigger = ["/sc", selected.frequency]
    if selected.frequency == "hourly":
        trigger.extend(["/mo", str(selected.interval_hours)])
    elif selected.frequency == "daily":
        trigger.extend(["/st", selected.time])
    else:
        trigger.extend(["/d", selected.weekday, "/st", selected.time])
    return [
        "schtasks", "/create", "/f", "/tn", _TASK_NAME,
        "/tr", subprocess.list2cmdline(build_scan_command(selected)),
        *trigger,
    ]


class NetworkScanScheduler:
    """Purpose-built adapter that can only schedule Cortex LAN scans."""

    @staticmethod
    def supported() -> bool:
        """Supported."""
        return platform.system() == "Windows"

    def create(self, spec: NetworkSchedule) -> None:
        """Create."""
        if not self.supported():
            raise NetworkScheduleError(
                "recurring network scans currently require Windows Task "
                "Scheduler")
        result = proc.run(build_windows_arguments(spec), text=True, timeout=30)
        if result.returncode != 0:
            detail = (
                result.stderr or result.stdout or "unknown error").strip()
            raise NetworkScheduleError(
                f"Task Scheduler rejected the network scan: {detail[:512]}")

    def delete(self) -> bool:
        """Delete."""
        if not self.supported():
            return False
        result = proc.run(
            ["schtasks", "/delete", "/tn", _TASK_NAME, "/f"],
            text=True, timeout=30)
        return result.returncode == 0

    def status(self) -> dict[str, str | bool]:
        """Status."""
        if not self.supported():
            return {"installed": False, "detail": "unsupported platform"}
        result = proc.run(
            ["schtasks", "/query", "/tn", _TASK_NAME, "/fo", "LIST"],
            text=True, timeout=30)
        return {
            "installed": result.returncode == 0,
            "detail": (result.stdout or result.stderr or "").strip()[:2048],
        }


__all__ = [
    "NetworkScanScheduler", "NetworkSchedule", "NetworkScheduleError",
    "build_scan_command", "build_windows_arguments",
]
