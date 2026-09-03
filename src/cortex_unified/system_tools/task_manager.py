"""Task manager backend - live process + resource monitor with honest totals.

This deliberately reconciles the numbers people find confusing:

* Summing every process's memory never equals "in use", because per-process
  figures are *working sets* only and exclude the kernel, drivers, paged /
  non-paged pool, compressed memory, cached/standby memory and GPU-shared RAM.
* Installed RAM can exceed the RAM the OS can use, because integrated GPUs and
  firmware reserve some ("Hardware reserved").

So alongside the process list we return a breakdown that adds up, and we label
the leftover honestly rather than pretending it doesn't exist.

Everything is read-only except :meth:`end_process`, which asks psutil to
terminate a PID (guarded in the UI by a confirmation dialog).
"""

from __future__ import annotations

import logging
import sys
from typing import Any

_LOG = logging.getLogger("cortex.system_tools.task_manager")
_IS_WINDOWS = sys.platform == "win32"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0


def _describe(name: str, exe: str) -> str:
    """Friendly description via process_meta; never raises."""
    try:
        from cortex_unified.system_tools.process_meta import describe
        return describe(name, exe)
    except Exception:  # noqa: BLE001
        return ""


class TaskManager:
    """Stateful monitor. Reuse ONE instance so CPU deltas are meaningful.

    psutil reports a process's CPU as usage *since the previous call* on the
    same object, so we cache Process handles by PID between snapshots.
    """

    _instance: "TaskManager | None" = None

    @classmethod
    def instance(cls) -> "TaskManager":
        """Instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        """Initialize Task Manager."""
        self._cache: dict[int, Any] = {}   # pid -> psutil.Process
        self._installed_bytes: int | None = None  # physical RAM incl. reserved

    # -- public API ---------------------------------------------------------

    # Windows' idle process (and its aliases) represent UNUSED CPU, not load.
    # Task Manager hides them; so do we, otherwise they dominate the CPU sort.
    _IDLE_NAMES = {"system idle process", "idle"}

    def snapshot(self, sample_interval: float = 0.3) -> dict[str, Any]:
        """Return {'cpu':..., 'memory':..., 'processes':[...]} or {'error':...}.

        CPU is measured over a short *blocking* window (``sample_interval``
        seconds). Because this runs on a worker thread, blocking is fine, and it
        makes every reading reliable instead of depending on how long ago the
        previous snapshot happened.
        """
        try:
            import psutil
        except ImportError:
            return {"error": "psutil is not installed."}

        cores = psutil.cpu_count(logical=True) or 1

        # Prime per-process CPU counters (first read returns 0 and sets the
        # baseline), then take one blocking system sample which doubles as the
        # measurement window for the per-process deltas we read afterwards.
        handles = self._refresh_handles(psutil)
        for h in handles.values():
            try:
                h.cpu_percent(None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        per_core = psutil.cpu_percent(interval=sample_interval, percpu=True)
        total_cpu = sum(per_core) / len(per_core) if per_core else 0.0

        processes = self._collect_processes(psutil, cores, handles)
        memory = self._collect_memory(psutil, processes)

        return {
            "cpu": {
                "total_percent": round(total_cpu, 1),
                "per_core": [round(c, 1) for c in per_core],
                "cores": cores,
            },
            "memory": memory,
            "processes": processes,
        }

    def _refresh_handles(self, psutil) -> dict[int, Any]:
        """Return {pid: Process} reusing cached handles; drop dead ones."""
        live: dict[int, Any] = {}
        for p in psutil.process_iter(["pid"]):
            pid = p.info.get("pid")
            if pid is None or pid == 0:
                continue  # skip the idle process
            handle = self._cache.get(pid) or p
            live[pid] = handle
        self._cache = live
        return live

    def end_process(self, pid: int, force: bool = False) -> tuple[bool, str]:
        """Terminate (or kill) a process by PID. Returns (ok, message)."""
        try:
            import psutil
        except ImportError:
            return False, "psutil is not installed."
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            if force:
                proc.kill()
            else:
                proc.terminate()
            return True, f"Ended {name} (PID {pid})."
        except psutil.NoSuchProcess:
            return False, "Process already exited."
        except psutil.AccessDenied:
            return False, "Access denied - this process needs Administrator to end."
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    # -- internals ----------------------------------------------------------

    def _collect_processes(self, psutil, cores: int,
                           handles: dict[int, Any]) -> list[dict[str, Any]]:
        """_collect_processes."""
        procs: list[dict[str, Any]] = []
        for pid, handle in handles.items():
            try:
                with handle.oneshot():
                    name = handle.name()
                    if name.lower() in self._IDLE_NAMES:
                        continue
                    raw_cpu = handle.cpu_percent(None)  # delta over sample window
                    mem = handle.memory_info()
                    try:
                        user = handle.username().split("\\")[-1]
                    except (psutil.AccessDenied, Exception):  # noqa: BLE001
                        user = ""
                    try:
                        exe = handle.exe()
                    except (psutil.AccessDenied, Exception):  # noqa: BLE001
                        exe = ""
                    procs.append({
                        "pid": pid,
                        "name": name or "?",
                        # Normalize to a 0-100 scale across all cores, like Task Manager.
                        "cpu": round(raw_cpu / cores, 1),
                        "rss": mem.rss if mem else 0,
                        "threads": handle.num_threads(),
                        "user": user,
                        "status": handle.status(),
                        "exe": exe,
                        "desc": _describe(name, exe),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception:  # noqa: BLE001 - never let one bad process break the list
                continue
        procs.sort(key=lambda d: d["rss"], reverse=True)
        return procs
        """_collect_processes."""
        """_collect_processes."""

    def _collect_memory(self, psutil, processes: list[dict]) -> dict[str, Any]:
        """_collect_memory."""
        vm = psutil.virtual_memory()
        sum_ws = sum(p["rss"] for p in processes)
        used = vm.total - vm.available
        # NOTE: we do NOT claim "processes + system = in use". Per-process
        # working sets can't be summed to the OS total for two opposing
        # reasons, and we report both honestly:
        #   * overcount: shared memory (DLLs, mapped files) is included in the
        #     working set of every process that maps it.
        #   * undercount: the kernel, drivers, paged/non-paged pool, compressed
        #     and cached memory aren't attributed to any process.
        try:
            swap = psutil.swap_memory()
            committed = swap.used  # rough; real "commit charge" needs OS APIs
        except Exception:  # noqa: BLE001
            committed = 0
        out = {
            "total": vm.total,
            "available": vm.available,
            "used": used,
            "percent": vm.percent,
            "sum_process_ws": sum_ws,
            "ws_overlaps": sum_ws > used,  # True when shared-memory overcount dominates
            "swap_used": committed,
        }
        installed = self._installed_ram(psutil)
        if installed and installed > vm.total:
            out["installed"] = installed
            out["hardware_reserved"] = installed - vm.total
        return out
        """_collect_memory."""
        """_collect_memory."""

    def _installed_ram(self, psutil) -> int | None:
        """Physically-installed RAM (may exceed OS-usable due to reservations).

        Cached after the first successful read so we don't shell out on every
        refresh. Returns None if it can't be determined.
        """
        if self._installed_bytes is not None:
            return self._installed_bytes or None
        if not _IS_WINDOWS:
            self._installed_bytes = 0
            return None
        try:
            from cortex_unified.core import proc as _proc
            out = _proc.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 "(Get-CimInstance Win32_PhysicalMemory | "
                 "Measure-Object -Property Capacity -Sum).Sum"],
                text=True, timeout=15, creationflags=_NO_WINDOW,
            )
            val = int((out.stdout or "0").strip() or 0)
            self._installed_bytes = val
            return val or None
        except Exception:  # noqa: BLE001 - includes ProcessCancelled/SubprocessError
            self._installed_bytes = 0
            return None
