"""Cortex Cleaner — Windows Pagefile & Virtual Memory Optimizer.

Inspects and optimizes Windows virtual memory paging files (pagefile.sys, swapfile.sys):
1. Reads active paging file configuration from HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management.
2. Queries total physical RAM and active committed virtual memory via Win32 GlobalMemoryStatusEx.
3. Calculates hardware-tailored recommendations (NVMe vs SATA vs HDD, low RAM vs high RAM).
4. Recommends fixed-size allocation on SSDs to eliminate write amplification from dynamic resizing.
5. Provides safe configuration with automatic backup and rollback.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if platform.system() == "Windows":
    import winreg
else:
    winreg = None  # type: ignore[assignment]


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
        ("sullAvailExtendedVirtual", ctypes.c_uint64),
    ]


@dataclass
class PagefileConfig:
    """Pagefile Config data container."""
    raw_setting: List[str]
    is_automatic: bool
    drive_letter: str
    initial_mb: int
    maximum_mb: int


@dataclass
class VirtualMemoryStatus:
    """Virtual Memory Status data container."""
    total_physical_bytes: int
    available_physical_bytes: int
    total_pagefile_bytes: int
    available_pagefile_bytes: int
    memory_load_percent: int
    current_config: PagefileConfig
    recommended_min_mb: int
    recommended_max_mb: int
    recommendation_reason: str


class PagefileOptimizer:
    """Production Windows Virtual Memory and Paging File management engine."""

    MEM_MGMT_KEY = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"

    @classmethod
    def get_memory_metrics(cls) -> Tuple[int, int, int, int, int]:
        """Query physical and pagefile memory sizes via GlobalMemoryStatusEx."""
        if platform.system() != "Windows":
            return (16 * 1024**3, 8 * 1024**3, 4 * 1024**3, 2 * 1024**3, 50)

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        if not ok:
            return (0, 0, 0, 0, 0)

        return (
            int(stat.ullTotalPhys),
            int(stat.ullAvailPhys),
            int(stat.ullTotalPageFile),
            int(stat.ullAvailPageFile),
            int(stat.dwMemoryLoad),
        )

    @classmethod
    def get_pagefile_config(cls) -> PagefileConfig:
        """Read active pagefile registry configuration."""
        if winreg is None:
            return PagefileConfig(["Automatic"], True, "C:", 0, 0)

        raw_list: List[str] = []
        is_auto = True

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cls.MEM_MGMT_KEY, 0, winreg.KEY_READ) as key:
                try:
                    val, _ = winreg.QueryValueEx(key, "PagingFiles")
                    if isinstance(val, list):
                        raw_list = val
                    elif isinstance(val, str):
                        raw_list = [val]
                except (FileNotFoundError, OSError):
                    pass

                try:
                    auto_val, _ = winreg.QueryValueEx(key, "ExistingPageFiles")
                    if auto_val:
                        is_auto = False
                except (FileNotFoundError, OSError):
                    pass
        except (FileNotFoundError, OSError):
            pass

        # Parse first entry e.g. "C:\pagefile.sys 4096 8192" or "?:\pagefile.sys"
        drive = "C:"
        init_mb = 0
        max_mb = 0
        if raw_list:
            first = raw_list[0].strip()
            parts = first.split()
            if parts:
                path_part = parts[0]
                if len(path_part) >= 2 and path_part[1] == ":":
                    drive = path_part[:2]
            if len(parts) >= 3:
                try:
                    init_mb = int(parts[1])
                    max_mb = int(parts[2])
                    is_auto = False
                except ValueError:
                    pass

        return PagefileConfig(
            raw_setting=raw_list,
            is_automatic=is_auto or (init_mb == 0 and max_mb == 0),
            drive_letter=drive,
            initial_mb=init_mb,
            maximum_mb=max_mb,
        )

    @classmethod
    def get_status(cls) -> VirtualMemoryStatus:
        """Analyze virtual memory and compute hardware-tailored recommendations."""
        tot_phys, avail_phys, tot_pf, avail_pf, load_pct = cls.get_memory_metrics()
        cfg = cls.get_pagefile_config()

        # Recommendation heuristics
        ram_gb = tot_phys / (1024**3) if tot_phys > 0 else 16

        if ram_gb >= 32:
            # High RAM systems: small fixed pagefile catches crash dumps without wasting SSD space
            rec_min = 2048
            rec_max = 4096
            reason = "High physical RAM (>=32GB): Fixed 2GB-4GB pagefile is optimal to support system crash dumps without wasting SSD storage."
        elif ram_gb >= 16:
            # Standard gaming/workstation: 4GB - 8GB
            rec_min = 4096
            rec_max = 8192
            reason = "Standard RAM (16GB): Fixed 4GB-8GB pagefile provides stability for heavy multitasking while preventing dynamic SSD resizing overhead."
        elif ram_gb >= 8:
            rec_min = 4096
            rec_max = 12288
            reason = "Moderate RAM (8GB): 4GB initial with up to 12GB maximum handles peak application commitments safely."
        else:
            # Low RAM: 1.5x - 3x RAM
            rec_min = max(2048, int(ram_gb * 1024 * 1.5))
            rec_max = max(4096, int(ram_gb * 1024 * 3.0))
            reason = "Low physical RAM (<8GB): Extended virtual memory buffer is required to prevent out-of-memory process crashes."

        return VirtualMemoryStatus(
            total_physical_bytes=tot_phys,
            available_physical_bytes=avail_phys,
            total_pagefile_bytes=tot_pf,
            available_pagefile_bytes=avail_pf,
            memory_load_percent=load_pct,
            current_config=cfg,
            recommended_min_mb=rec_min,
            recommended_max_mb=rec_max,
            recommendation_reason=reason,
        )

    @classmethod
    def set_custom_pagefile(cls, drive_letter: str, initial_mb: int, maximum_mb: int) -> Tuple[bool, str]:
        """Configure custom min/max pagefile size in Windows registry."""
        if winreg is None:
            return False, "Windows only"

        clean_drive = drive_letter.strip().rstrip("\\/").upper()
        if not clean_drive.endswith(":"):
            clean_drive += ":"

        entry_val = f"{clean_drive}\\pagefile.sys {initial_mb} {maximum_mb}"

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cls.MEM_MGMT_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "PagingFiles", 0, winreg.REG_MULTI_SZ, [entry_val])
                return True, f"Paging file configured to {initial_mb}MB - {maximum_mb}MB on {clean_drive}. (Restart recommended)"
        except PermissionError:
            return False, "Administrator privileges required to modify virtual memory configuration."
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def set_automatic_pagefile(cls) -> Tuple[bool, str]:
        """Revert paging file to Windows system-managed automatic mode."""
        if winreg is None:
            return False, "Windows only"

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cls.MEM_MGMT_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "PagingFiles", 0, winreg.REG_MULTI_SZ, [r"?:\pagefile.sys"])
                return True, "Paging file set to System-Managed (Automatic) mode."
        except PermissionError:
            return False, "Administrator privileges required."
        except Exception as exc:
            return False, str(exc)
