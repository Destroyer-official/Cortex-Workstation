"""Nexus Explorer — Process Unlocker & File Handle Inspector.

Queries active Windows handles and processes locking any file or directory
using the Windows Restart Manager API (rstrtmgr.dll) and psutil handle discovery.
Provides safe process termination and file unlock capabilities.
"""

from __future__ import annotations

import ctypes
import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

if platform.system() == "Windows":
    from ctypes import wintypes

    # Windows Restart Manager Structures & Constants
    CCH_RM_MAX_APP_NAME = 255
    CCH_RM_MAX_SVC_NAME = 63

    class RM_UNIQUE_PROCESS(ctypes.Structure):
        """RM_UNIQUE_PROCESS."""
        _fields_ = [
            ("dwProcessId", wintypes.DWORD),
            ("ProcessStartTime", wintypes.FILETIME),
        ]
        """RM_UNIQUE_PROCESS class."""

    class RM_APP_TYPE(ctypes.c_int):
        """RM_APP_TYPE."""
        pass
        """RM_APP_TYPE class."""

    class RM_PROCESS_INFO(ctypes.Structure):
        """RM_PROCESS_INFO."""
        _fields_ = [
            ("Process", RM_UNIQUE_PROCESS),
            ("strAppName", wintypes.WCHAR * (CCH_RM_MAX_APP_NAME + 1)),
            ("strServiceShortName", wintypes.WCHAR * (CCH_RM_MAX_SVC_NAME + 1)),
            ("ApplicationType", RM_APP_TYPE),
            ("AppStatus", wintypes.ULONG),
            ("TSSessionId", wintypes.DWORD),
            ("bRestartable", wintypes.BOOL),
        ]
        """RM_PROCESS_INFO class."""


@dataclass
class LockingProcessInfo:
    """LockingProcessInfo."""
    pid: int
    name: str
    executable_path: str
    is_system: bool = False
    service_name: str = ""
    user: str = ""
    memory_mb: float = 0.0
    """LockingProcessInfo class."""


class FileUnlocker:
    """Production Windows file unlocker and process handle inspector."""

    @classmethod
    def get_locking_processes(cls, file_path: str | Path) -> List[LockingProcessInfo]:
        """Query which processes currently hold an open lock on the target file."""
        target = str(Path(file_path).resolve())
        if not os.path.exists(target):
            return []

        results: List[LockingProcessInfo] = []

        if platform.system() == "Windows":
            # 1. Primary: Windows Restart Manager API (authoritative & instant)
            return cls._query_restart_manager([target])
        else:
            return cls._query_psutil_handles(target)

    @classmethod
    def _query_restart_manager(cls, file_paths: List[str]) -> List[LockingProcessInfo]:
        """Invoke Windows Restart Manager to enumerate locking processes."""
        if platform.system() != "Windows":
            return []

        try:
            rstrtmgr = ctypes.windll.rstrtmgr
        except Exception:
            return []

        session_handle = wintypes.DWORD()
        session_key = (wintypes.WCHAR * 33)()

        # RmStartSession
        res = rstrtmgr.RmStartSession(ctypes.byref(session_handle), 0, session_key)
        if res != 0:
            return []

        locking_procs: List[LockingProcessInfo] = []

        try:
            # RmRegisterResources
            c_files = (ctypes.c_wchar_p * len(file_paths))(*file_paths)
            res = rstrtmgr.RmRegisterResources(
                session_handle,
                len(file_paths),
                c_files,
                0,
                None,
                0,
                None,
            )
            if res != 0:
                return []

            # RmGetList (Step 1: get buffer size)
            n_proc_info_needed = wintypes.UINT(0)
            n_proc_info = wintypes.UINT(0)
            reboot_reasons = wintypes.DWORD(0)

            res = rstrtmgr.RmGetList(
                session_handle,
                ctypes.byref(n_proc_info_needed),
                ctypes.byref(n_proc_info),
                None,
                ctypes.byref(reboot_reasons),
            )

            # ERROR_MORE_DATA is 234
            if res != 0 and res != 234:
                return []

            if n_proc_info_needed.value == 0:
                return []

            # Step 2: retrieve process info array
            n_proc_info.value = n_proc_info_needed.value
            process_info_array = (RM_PROCESS_INFO * n_proc_info.value)()

            res = rstrtmgr.RmGetList(
                session_handle,
                ctypes.byref(n_proc_info_needed),
                ctypes.byref(n_proc_info),
                process_info_array,
                ctypes.byref(reboot_reasons),
            )

            if res == 0:
                for i in range(n_proc_info.value):
                    proc_entry = process_info_array[i]
                    pid = proc_entry.Process.dwProcessId
                    app_name = proc_entry.strAppName
                    svc_name = proc_entry.strServiceShortName

                    exe_path = ""
                    mem_mb = 0.0
                    user_str = ""

                    try:
                        import psutil
                        p = psutil.Process(pid)
                        exe_path = p.exe()
                        mem_mb = p.memory_info().rss / (1024 * 1024)
                        user_str = p.username()
                    except Exception:
                        pass

                    is_sys = pid in (0, 4) or "system" in (app_name.lower() or exe_path.lower())

                    locking_procs.append(LockingProcessInfo(
                        pid=pid,
                        name=app_name or Path(exe_path).name or f"PID {pid}",
                        executable_path=exe_path,
                        is_system=is_sys,
                        service_name=svc_name,
                        user=user_str,
                        memory_mb=round(mem_mb, 1),
                    ))

        finally:
            rstrtmgr.RmEndSession(session_handle)

        return locking_procs

    @classmethod
    def _query_psutil_handles(cls, target_path: str) -> List[LockingProcessInfo]:
        """Fallback process inspection via psutil open_files."""
        target_lower = target_path.lower()
        locking_procs: List[LockingProcessInfo] = []

        try:
            import psutil
            for proc in psutil.process_iter(["pid", "name", "exe"]):
                try:
                    open_files = proc.open_files()
                    for of in open_files:
                        if of.path and of.path.lower() == target_lower:
                            mem_mb = proc.memory_info().rss / (1024 * 1024)
                            locking_procs.append(LockingProcessInfo(
                                pid=proc.pid,
                                name=proc.name(),
                                executable_path=proc.exe() or "",
                                is_system=(proc.pid in (0, 4)),
                                user=proc.username() if hasattr(proc, "username") else "",
                                memory_mb=round(mem_mb, 1),
                            ))
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

        return locking_procs

    @classmethod
    def unlock_and_terminate(cls, pid: int, force: bool = False) -> Tuple[bool, str]:
        """Terminate a locking process by PID to release locked files."""
        if pid in (0, 4):
            return False, "Cannot terminate critical Windows System Process (PID 0/4)"

        try:
            import psutil
            proc = psutil.Process(pid)
            if force:
                proc.kill()
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except psutil.TimeoutExpired:
                    proc.kill()
            return True, f"Process {proc.name()} (PID {pid}) terminated successfully."
        except Exception as exc:
            return False, f"Failed to terminate PID {pid}: {exc}"
