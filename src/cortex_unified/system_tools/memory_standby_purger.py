"""Windows NT Kernel RAM Standby List & Working Set Purger.

Utilizes undocumented native NTDLL SystemMemoryListInformation (Class 80) calls
to flush the system standby memory cache, empty process working sets, and eliminate
micro-stutter in competitive gaming, video rendering, and heavy local LLM inference.
Requires SeProfileSingleProcessPrivilege (automatically acquired via TokenPrivileges).
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

_LOG = logging.getLogger("cortex.system_tools.memory_standby")

# NTSTATUS Constants
STATUS_SUCCESS = 0x00000000
STATUS_PRIVILEGE_NOT_HELD = 0xC0000061

# SystemMemoryListInformation commands
SYSTEM_MEMORY_LIST_INFORMATION = 80
MEMORY_EMPTY_WORKING_SETS = 2
MEMORY_PURGE_MODIFIED_PAGE_LIST = 3
MEMORY_PURGE_STANDBY_LIST = 4
MEMORY_PURGE_LOW_PRIORITY_STANDBY_LIST = 5

# Win32 Token Privilege Constants
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
SE_PROFILE_SINGLE_PROCESS_NAME = "SeProfileSingleProcessPrivilege"
SE_INCREASE_QUOTA_NAME = "SeIncreaseQuotaPrivilege"


class LUID(ctypes.Structure):
    """L U I D."""
    _fields_ = [
        ("LowPart", wintypes.DWORD),
        ("HighPart", wintypes.LONG),
    ]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    """L U I D_ A N D_ A T T R I B U T E S."""
    _fields_ = [
        ("Luid", LUID),
        ("Attributes", wintypes.DWORD),
    ]


class TOKEN_PRIVILEGES(ctypes.Structure):
    """T O K E N_ P R I V I L E G E S."""
    _fields_ = [
        ("PrivilegeCount", wintypes.DWORD),
        ("Privileges", LUID_AND_ATTRIBUTES * 1),
    ]


class MEMORYSTATUSEX(ctypes.Structure):
    """M E M O R Y S T A T U S E X."""
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


@dataclass
class MemorySnapshot:
    """Current system memory status."""

    total_phys_bytes: int
    avail_phys_bytes: int
    used_phys_bytes: int
    memory_load_percent: int
    total_pagefile_bytes: int
    avail_pagefile_bytes: int

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "total_phys": self.total_phys_bytes,
            "avail_phys": self.avail_phys_bytes,
            "used_phys": self.used_phys_bytes,
            "load_percent": self.memory_load_percent,
            "total_pagefile": self.total_pagefile_bytes,
            "avail_pagefile": self.avail_pagefile_bytes,
        }


@dataclass
class PurgeResult:
    """Outcome of kernel memory purge operations."""

    action: str
    success: bool
    reclaimed_bytes_approx: int = 0
    message: str = ""
    error_code: Optional[int] = None


class MemoryStandbyPurger:
    """Manages kernel memory standby list purging and working set trimming."""

    def __init__(self) -> None:
        """Initialize Memory Standby Purger."""
        self.is_windows = sys.platform == "win32"
        self._ntdll = None
        self._kernel32 = None
        self._advapi32 = None
        if self.is_windows:
            try:
                self._ntdll = ctypes.WinDLL("ntdll")
                self._kernel32 = ctypes.WinDLL("kernel32")
                self._advapi32 = ctypes.WinDLL("advapi32")
            except Exception as e:
                _LOG.warning("Failed to initialize Windows NT DLLs: %s", e)

    def get_memory_snapshot(self) -> MemorySnapshot:
        """Query real-time physical and virtual memory allocation."""
        if not self.is_windows or not self._kernel32:
            return MemorySnapshot(0, 0, 0, 0, 0, 0)

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if not self._kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return MemorySnapshot(0, 0, 0, 0, 0, 0)

        used = stat.ullTotalPhys - stat.ullAvailPhys
        return MemorySnapshot(
            total_phys_bytes=stat.ullTotalPhys,
            avail_phys_bytes=stat.ullAvailPhys,
            used_phys_bytes=used,
            memory_load_percent=stat.dwMemoryLoad,
            total_pagefile_bytes=stat.ullTotalPageFile,
            avail_pagefile_bytes=stat.ullAvailPageFile,
        )

    def enable_privilege(self, priv_name: str) -> bool:
        """Enable specified security privilege in current process token."""
        if not self.is_windows or not self._advapi32 or not self._kernel32:
            return False

        h_token = wintypes.HANDLE()
        h_process = self._kernel32.GetCurrentProcess()

        if not self._advapi32.OpenProcessToken(h_process, TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(h_token)):
            return False

        try:
            luid = LUID()
            if not self._advapi32.LookupPrivilegeValueW(None, priv_name, ctypes.byref(luid)):
                return False

            tp = TOKEN_PRIVILEGES()
            tp.PrivilegeCount = 1
            tp.Privileges[0].Luid = luid
            tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED

            if not self._advapi32.AdjustTokenPrivileges(h_token, False, ctypes.byref(tp), 0, None, None):
                return False

            return ctypes.GetLastError() == 0
        finally:
            self._kernel32.CloseHandle(h_token)

    def purge_standby_list(self) -> PurgeResult:
        """Purge system standby list cache (MemoryPurgeStandbyList = 4)."""
        return self._send_memory_command(MEMORY_PURGE_STANDBY_LIST, "Purge Standby List")

    def purge_working_sets(self) -> PurgeResult:
        """Flush working sets across processes (MemoryEmptyWorkingSets = 2)."""
        return self._send_memory_command(MEMORY_EMPTY_WORKING_SETS, "Empty Working Sets")

    def purge_modified_page_list(self) -> PurgeResult:
        """Flush modified page list to storage (MemoryPurgeModifiedPageList = 3)."""
        return self._send_memory_command(MEMORY_PURGE_MODIFIED_PAGE_LIST, "Flush Modified Page List")

    def _send_memory_command(self, cmd_val: int, label: str) -> PurgeResult:
        """Issue command to NtSetSystemInformation."""
        if not self.is_windows or not self._ntdll:
            return PurgeResult(action=label, success=False, message="Only supported on Windows NT.")

        # Ensure SeProfileSingleProcessPrivilege is enabled
        self.enable_privilege(SE_PROFILE_SINGLE_PROCESS_NAME)
        self.enable_privilege(SE_INCREASE_QUOTA_NAME)

        before = self.get_memory_snapshot()
        command = ctypes.c_ulong(cmd_val)

        status = self._ntdll.NtSetSystemInformation(
            SYSTEM_MEMORY_LIST_INFORMATION,
            ctypes.byref(command),
            ctypes.sizeof(command),
        )

        after = self.get_memory_snapshot()
        reclaimed = max(0, after.avail_phys_bytes - before.avail_phys_bytes)

        if status == STATUS_SUCCESS:
            return PurgeResult(
                action=label,
                success=True,
                reclaimed_bytes_approx=reclaimed,
                message=f"Successfully executed {label}.",
            )
        elif (status & 0xFFFFFFFF) == STATUS_PRIVILEGE_NOT_HELD:
            return PurgeResult(
                action=label,
                success=False,
                message="Privilege not held. Please run Cortex Cleaner as Administrator.",
                error_code=status,
            )
        else:
            return PurgeResult(
                action=label,
                success=False,
                message=f"NtSetSystemInformation failed with NTSTATUS: {hex(status & 0xFFFFFFFF)}",
                error_code=status,
            )
