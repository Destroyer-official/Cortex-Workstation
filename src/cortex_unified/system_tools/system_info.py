"""System information & diagnostics - lightweight, offline, read-only.

Gathers CPU / RAM / disk / OS / battery facts using ``psutil`` + stdlib
``platform``. Everything is a cheap read; nothing is modified and no network is
touched. Values degrade gracefully to ``None`` when a source is unavailable.
"""

from __future__ import annotations

import logging
import platform
from typing import Any

_LOG = logging.getLogger("cortex.system_tools.system_info")

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:  # pragma: no cover
    _HAS_PSUTIL = False


def _fmt_bytes(n: int | float | None) -> str:
    """_fmt_bytes.

    Converts raw numeric values into formatted, localized, and human-readable string representations.

    Args:
        n (int | float | None): The n parameter.

    Returns:
        str: Formatted string or path.
    """
    if not n:
        return "0 B"
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if size < 1024 or unit == "PB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


class SystemInfo:
    """Systeminfo.

    Manages SystemInfo operations and coordinates related state changes for the component.
    """

    def platform_info(self) -> dict[str, Any]:
        """Platform info.

        Manages platform info operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        uname = platform.uname()
        return {
            "system": uname.system,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "processor": uname.processor or platform.processor(),
            "hostname": uname.node,
            "python": platform.python_version(),
        }

    def cpu_info(self) -> dict[str, Any]:
        """Cpu info.

        Manages cpu info operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        if not _HAS_PSUTIL:
            return {}
        try:
            freq = psutil.cpu_freq()
        except Exception:  # noqa: BLE001
            freq = None
        return {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "current_freq_mhz": round(freq.current, 0) if freq else None,
            "max_freq_mhz": round(freq.max, 0) if freq and freq.max else None,
            "usage_percent": psutil.cpu_percent(interval=0.2),
        }

    def memory_info(self) -> dict[str, Any]:
        """Memory info.

        Manages memory info operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        if not _HAS_PSUTIL:
            return {}
        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()
        return {
            "total": vm.total,
            "total_human": _fmt_bytes(vm.total),
            "available": vm.available,
            "available_human": _fmt_bytes(vm.available),
            "used_percent": vm.percent,
            "swap_total_human": _fmt_bytes(sw.total),
            "swap_used_percent": sw.percent,
        }

    def disk_info(self) -> list[dict[str, Any]]:
        """Disk info.

        Manages disk info operations and coordinates related state changes for the component.

        Returns:
            list[dict[str, Any]]: List of processed items or identifiers.
        """
        if not _HAS_PSUTIL:
            return []
        out: list[dict[str, Any]] = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                continue
            out.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total": usage.total,
                "total_human": _fmt_bytes(usage.total),
                "used_human": _fmt_bytes(usage.used),
                "free_human": _fmt_bytes(usage.free),
                "used_percent": usage.percent,
            })
        return out

    def battery_info(self) -> dict[str, Any] | None:
        """Battery info.

        Manages battery info operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any] | None: Dictionary mapping identifiers to status or values.
        """
        if not _HAS_PSUTIL or not hasattr(psutil, "sensors_battery"):
            return None
        try:
            bat = psutil.sensors_battery()
        except Exception:  # noqa: BLE001
            return None
        if bat is None:
            return None
        return {
            "percent": round(bat.percent, 0),
            "plugged_in": bat.power_plugged,
            "secs_left": bat.secsleft if bat.secsleft not in (-1, -2) else None,
        }

    def boot_time(self) -> float | None:
        """Boot time.

        Manages boot time operations and coordinates related state changes for the component.

        Returns:
            float | None: Result of the operation.
        """
        if not _HAS_PSUTIL:
            return None
        try:
            return psutil.boot_time()
        except Exception:  # noqa: BLE001
            return None

    def snapshot(self) -> dict[str, Any]:
        """Snapshot.

        Manages snapshot operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "platform": self.platform_info(),
            "cpu": self.cpu_info(),
            "memory": self.memory_info(),
            "disks": self.disk_info(),
            "battery": self.battery_info(),
            "boot_time": self.boot_time(),
            "psutil_available": _HAS_PSUTIL,
        }
