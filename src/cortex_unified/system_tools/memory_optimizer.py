"""Cortex Cleaner — Working Set & System RAM Memory Optimizer.

Inspects:
1. Physical RAM composition (Total, Used, Free, Cached, Available).
2. Per-process Working Set and Private Bytes.
3. Safe process working set trimming via Win32 psapi.EmptyWorkingSet.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import platform
import psutil
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SystemRamMetrics:
    """System Ram Metrics data container."""
    total_bytes: int
    available_bytes: int
    used_bytes: int
    percent_used: float
    cached_bytes: int = 0
    commit_total_bytes: int = 0
    commit_limit_bytes: int = 0


@dataclass
class ProcessMemoryItem:
    """Process Memory Item data container."""
    pid: int
    name: str
    working_set_bytes: int
    private_bytes: int
    is_optimizable: bool = True


@dataclass
class MemoryOptimizeResult:
    """Memory Optimize Result data container."""
    processes_trimmed: int
    bytes_freed_estimate: int
    errors: List[str] = None
    dry_run: bool = False

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        """__post_init__."""
        """__post_init__."""

    @property
    def ok(self) -> bool:
        """Ok."""
        return len(self.errors) == 0

    @property
    def message(self) -> str:
        """Message."""
        mb = self.bytes_freed_estimate / (1024 * 1024)
        action = "Would trim" if self.dry_run else "Trimmed"
        return f"{action} working sets of {self.processes_trimmed} processes, freeing ~{mb:.1f} MB."

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "ok": self.ok,
            "processes_trimmed": self.processes_trimmed,
            "bytes_freed_estimate": self.bytes_freed_estimate,
            "dry_run": self.dry_run,
            "message": self.message,
            "errors": self.errors,
        }


class MemoryOptimizer:
    """Production Windows RAM composition inspector and process working set optimizer."""

    PROTECTED_SYSTEM_PROCESSES = {
        "system", "system idle process", "smss.exe", "csrss.exe",
        "wininit.exe", "services.exe", "lsass.exe", "svchost.exe",
        "winlogon.exe", "dwm.exe",
    }

    @classmethod
    def get_system_ram_metrics(cls) -> SystemRamMetrics:
        """Query physical RAM metrics using psutil and Win32 GlobalMemoryStatusEx."""
        vm = psutil.virtual_memory()
        cached = getattr(vm, "cached", 0)

        swap = psutil.swap_memory()
        commit_total = swap.used
        commit_limit = swap.total

        return SystemRamMetrics(
            total_bytes=vm.total,
            available_bytes=vm.available,
            used_bytes=vm.used,
            percent_used=vm.percent,
            cached_bytes=cached,
            commit_total_bytes=commit_total,
            commit_limit_bytes=commit_limit,
        )

    @classmethod
    def scan_process_memory(cls, limit: int = 30) -> List[ProcessMemoryItem]:
        """Scan active processes and sort by Working Set (physical RAM consumption)."""
        items: List[ProcessMemoryItem] = []

        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                info = proc.info
                pid = info["pid"]
                name = info["name"] or f"PID {pid}"
                mem = info["memory_info"]
                if not mem:
                    continue

                ws = mem.rss
                pv = getattr(mem, "vms", 0)

                is_opt = name.lower() not in cls.PROTECTED_SYSTEM_PROCESSES and pid > 4

                items.append(ProcessMemoryItem(
                    pid=pid,
                    name=name,
                    working_set_bytes=ws,
                    private_bytes=pv,
                    is_optimizable=is_opt,
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return sorted(items, key=lambda x: x.working_set_bytes, reverse=True)[:limit]

    @classmethod
    def trim_process_working_set(cls, pid: int) -> Tuple[bool, int]:
        """Trim the working set of a specific process via Win32 EmptyWorkingSet."""
        if platform.system() != "Windows":
            return False, 0

        PROCESS_SET_QUOTA = 0x0100
        PROCESS_QUERY_INFORMATION = 0x0400
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi

        try:
            # Measure before
            proc = psutil.Process(pid)
            before_rss = proc.memory_info().rss
        except Exception:
            return False, 0

        h_proc = kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION, False, pid)
        if not h_proc:
            return False, 0

        try:
            ok = psapi.EmptyWorkingSet(h_proc)
            if ok:
                time.sleep(0.05)
                try:
                    after_rss = proc.memory_info().rss
                    freed = max(0, before_rss - after_rss)
                    return True, freed
                except Exception:
                    return True, 0
            return False, 0
        finally:
            kernel32.CloseHandle(h_proc)

    @classmethod
    def optimize_all_background_working_sets(cls, pids: Optional[List[int]] = None) -> MemoryOptimizeResult:
        """Trim working sets of non-critical processes."""
        if platform.system() != "Windows":
            return MemoryOptimizeResult(0, 0, ["Windows only"])

        result = MemoryOptimizeResult(0, 0)
        target_pids = pids

        if target_pids is None:
            # Discover top non-critical processes
            procs = cls.scan_process_memory(limit=50)
            target_pids = [p.pid for p in procs if p.is_optimizable and p.working_set_bytes > (20 * 1024 * 1024)]  # > 20MB

        for pid in target_pids:
            try:
                ok, freed = cls.trim_process_working_set(pid)
                if ok:
                    result.processes_trimmed += 1
                    result.bytes_freed_estimate += freed
            except Exception as exc:
                result.errors.append(f"PID {pid}: {exc}")

        return result


def memory_stats() -> Dict[str, Any]:
    """Query current system RAM statistics and top consumer processes."""
    if not hasattr(psutil, "virtual_memory"):
        return {"supported": False}
    try:
        metrics = MemoryOptimizer.get_system_ram_metrics()
        swap = psutil.swap_memory()
        procs = MemoryOptimizer.scan_process_memory(limit=10)
        top = [
            {"pid": p.pid, "name": p.name, "rss_bytes": p.working_set_bytes}
            for p in procs
        ]
        return {
            "supported": True,
            "total_bytes": metrics.total_bytes,
            "used_bytes": metrics.used_bytes,
            "percent_used": metrics.percent_used,
            "available_bytes": metrics.available_bytes,
            "swap_percent_used": swap.percent,
            "top_consumers": top,
        }
    except Exception as exc:
        return {"supported": False, "error": str(exc)}


def optimize(min_rss_mb: int = 50, dry_run: bool = True) -> MemoryOptimizeResult:
    """Optimize working sets of non-critical background processes."""
    if platform.system() != "Windows":
        return MemoryOptimizeResult(0, 0, errors=["Windows only"], dry_run=dry_run)
    procs = MemoryOptimizer.scan_process_memory(limit=50)
    min_bytes = min_rss_mb * 1024 * 1024
    eligible = [p for p in procs if p.is_optimizable and p.working_set_bytes >= min_bytes]
    if dry_run:
        est_freed = sum(int(p.working_set_bytes * 0.25) for p in eligible)
        return MemoryOptimizeResult(
            processes_trimmed=len(eligible),
            bytes_freed_estimate=est_freed,
            dry_run=True,
        )
    result = MemoryOptimizer.optimize_all_background_working_sets(pids=[p.pid for p in eligible])
    result.dry_run = False
    return result
