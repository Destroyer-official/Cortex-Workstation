"""Windows Native Restart Manager File Unlocker & Process Lock Auditor.

Research Grounding
------------------
* Microsoft Windows Restart Manager Architecture (`rstrtmgr.dll`, Windows Vista - Windows 11):
  Traditional file unlockers rely on brute-force scanning of every kernel handle across
  the entire operating system (`NtQuerySystemInformation` with `SystemHandleInformation`),
  which can cause hard driver deadlocks, AV heuristic flags, and system instability.
  The native Windows Restart Manager is Microsoft's official, zero-impact API designed
  to identify exactly which applications or NT services hold open locks on specific files.
* Restart Manager Sequence:
  1. `RmStartSession`: Allocates a unique caller session GUID.
  2. `RmRegisterResources`: Registers target file paths with the session.
  3. `RmGetList`: Queries `RM_PROCESS_INFO` records for PIDs, executable names, and service identities.
  4. `RmShutdown`: (Optional) Gracefully requests locked processes to save state and terminate.
  5. `RmEndSession`: Releases session memory and kernel structures.

This module binds `rstrtmgr.dll` via `ctypes` for native lock detection, with an
integrated fallback to `psutil` open-file inspection when non-elevated or on test platforms.
"""

from __future__ import annotations

import ctypes
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOG = logging.getLogger("cortex.system_tools.restart_manager")
_IS_WINDOWS = sys.platform == "win32"

# Win32 Constants & Structures for Restart Manager
CCH_RM_MAX_APP_NAME = 255
CCH_RM_MAX_SVC_NAME = 63


class RM_UNIQUE_PROCESS(ctypes.Structure):
    """R M_ U N I Q U E_ P R O C E S S."""
    _fields_ = [
        ("dwProcessId", ctypes.c_ulong),
        ("ProcessStartTime", ctypes.c_uint64),
    ]


class RM_PROCESS_INFO(ctypes.Structure):
    """R M_ P R O C E S S_ I N F O."""
    _fields_ = [
        ("Process", RM_UNIQUE_PROCESS),
        ("strAppName", ctypes.c_wchar * (CCH_RM_MAX_APP_NAME + 1)),
        ("strServiceShortName", ctypes.c_wchar * (CCH_RM_MAX_SVC_NAME + 1)),
        ("ApplicationType", ctypes.c_int),
        ("AppStatus", ctypes.c_ulong),
        ("TSSessionId", ctypes.c_ulong),
        ("bRestartable", ctypes.c_bool),
    ]


@dataclass
class LockingProcessInfo:
    """Identity and telemetry of a process holding an exclusive file lock."""
    pid: int
    name: str
    service_name: str = ""
    app_type: str = "Application"

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "pid": self.pid,
            "name": self.name,
            "service_name": self.service_name,
            "app_type": self.app_type,
        }


@dataclass
class FileLockReport:
    """Forensic report detailing whether a file is locked and which processes lock it."""
    file_path: str
    exists: bool
    is_locked: bool
    locking_processes: List[LockingProcessInfo] = field(default_factory=list)
    scan_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "file_path": self.file_path,
            "exists": self.exists,
            "is_locked": self.is_locked,
            "locking_processes": [p.to_dict() for p in self.locking_processes],
            "scan_duration_ms": self.scan_duration_ms,
        }


@dataclass
class UnlockResult:
    """Outcome of an unlock or process termination attempt."""
    file_path: str
    success: bool
    terminated_pids: List[int] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "file_path": self.file_path,
            "success": self.success,
            "terminated_pids": self.terminated_pids,
            "message": self.message,
        }


class RestartManagerUnlocker:
    """Native Windows Restart Manager file lock analyzer and process unlocker."""

    def __init__(self) -> None:
        """Initialize Restart Manager Unlocker."""
        self.logger = _LOG
        self._rstrtmgr = None
        if _IS_WINDOWS:
            try:
                self._rstrtmgr = ctypes.WinDLL("rstrtmgr.dll", use_last_error=True)
            except Exception as exc:
                self.logger.debug("rstrtmgr.dll load fallback: %s", exc)

    def inspect_locks(self, file_path: str) -> FileLockReport:
        """Query which processes currently lock the given file using Windows Restart Manager."""
        t0 = time.perf_counter()
        target = Path(file_path).resolve()
        exists = target.exists()

        if not exists:
            return FileLockReport(str(target), False, False, scan_duration_ms=0.0)

        procs = self._get_locking_processes_native(str(target))
        if not procs:
            procs = self._get_locking_processes_psutil(str(target))

        is_locked = len(procs) > 0
        dur = (time.perf_counter() - t0) * 1000.0

        return FileLockReport(
            file_path=str(target),
            exists=True,
            is_locked=is_locked,
            locking_processes=procs,
            scan_duration_ms=dur,
        )

    def _get_locking_processes_native(self, abs_path: str) -> List[LockingProcessInfo]:
        """Query rstrtmgr.dll for processes locking abs_path."""
        if not self._rstrtmgr:
            return []

        results: List[LockingProcessInfo] = []
        session_handle = ctypes.c_ulong(0)
        session_key = (ctypes.c_wchar * 64)()

        try:
            # 1. RmStartSession
            res = self._rstrtmgr.RmStartSession(
                ctypes.byref(session_handle),
                ctypes.c_ulong(0),
                session_key,
            )
            if res != 0:
                return []

            # 2. RmRegisterResources
            paths_array = (ctypes.c_wchar_p * 1)(abs_path)
            res = self._rstrtmgr.RmRegisterResources(
                session_handle,
                ctypes.c_uint(1),
                paths_array,
                ctypes.c_uint(0),
                None,
                ctypes.c_uint(0),
                None,
            )
            if res != 0:
                self._rstrtmgr.RmEndSession(session_handle)
                return []

            # 3. RmGetList
            n_proc_info_needed = ctypes.c_uint(0)
            n_proc_info = ctypes.c_uint(0)
            reboot_reasons = ctypes.c_ulong(0)

            # First probe for buffer size
            self._rstrtmgr.RmGetList(
                session_handle,
                ctypes.byref(n_proc_info_needed),
                ctypes.byref(n_proc_info),
                None,
                ctypes.byref(reboot_reasons),
            )

            if n_proc_info_needed.value > 0:
                arr_type = RM_PROCESS_INFO * n_proc_info_needed.value
                process_info_arr = arr_type()
                n_proc_info.value = n_proc_info_needed.value

                res = self._rstrtmgr.RmGetList(
                    session_handle,
                    ctypes.byref(n_proc_info_needed),
                    ctypes.byref(n_proc_info),
                    process_info_arr,
                    ctypes.byref(reboot_reasons),
                )

                if res == 0:
                    for i in range(n_proc_info.value):
                        pinfo = process_info_arr[i]
                        pid = pinfo.Process.dwProcessId
                        app_name = pinfo.strAppName or f"PID {pid}"
                        svc_name = pinfo.strServiceShortName or ""
                        results.append(
                            LockingProcessInfo(
                                pid=pid,
                                name=app_name,
                                service_name=svc_name,
                                app_type="Service" if svc_name else "Application",
                            )
                        )

            # 4. RmEndSession
            self._rstrtmgr.RmEndSession(session_handle)
        except Exception as exc:
            self.logger.debug("RestartManager native query exception: %s", exc)

        return results

    def _get_locking_processes_psutil(self, abs_path: str) -> List[LockingProcessInfo]:
        """Fallback process inspection via psutil open file handle auditing."""
        results: List[LockingProcessInfo] = []
        try:
            import psutil
            target_norm = os.path.normcase(os.path.abspath(abs_path))
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    for f in proc.open_files():
                        if os.path.normcase(os.path.abspath(f.path)) == target_norm:
                            results.append(
                                LockingProcessInfo(
                                    pid=proc.info["pid"],
                                    name=proc.info["name"] or f"PID {proc.info['pid']}",
                                )
                            )
                except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                    continue
        except Exception:
            pass

        return results

    def unlock_file(self, file_path: str, force_terminate: bool = False) -> UnlockResult:
        """Release locks on a file by gracefully or forcefully terminating the locking processes."""
        report = self.inspect_locks(file_path)
        if not report.is_locked:
            return UnlockResult(file_path, True, message="File is not currently locked by any active process.")

        terminated: List[int] = []
        try:
            import psutil
            for pinfo in report.locking_processes:
                try:
                    p = psutil.Process(pinfo.pid)
                    if force_terminate:
                        p.kill()
                    else:
                        p.terminate()
                    terminated.append(pinfo.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                    self.logger.debug("Cannot terminate PID %d: %s", pinfo.pid, exc)
        except Exception as exc:
            return UnlockResult(
                file_path,
                False,
                terminated_pids=terminated,
                message=f"Termination error: {exc}",
            )

        success = len(terminated) == len(report.locking_processes)
        msg = (
            f"Successfully unlocked file by terminating {len(terminated)} locking process(es)."
            if success
            else f"Partially unlocked: terminated {len(terminated)}/{len(report.locking_processes)} processes."
        )
        return UnlockResult(file_path, success, terminated_pids=terminated, message=msg)
