"""Nexus Explorer — NTFS USN (Update Sequence Number) Change Journal Scanner.

Interacts with the NTFS Change Journal:
1. Queries USN Journal status via Win32 FSCTL_QUERY_USN_JOURNAL.
2. Extracts Journal ID, First Usn, Next Usn, and allocated journal sizes.
3. Provides sub-millisecond volume change tracking metrics.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class UsnJournalStatus:
    drive_letter: str
    is_supported: bool
    is_active: bool
    journal_id: int = 0
    first_usn: int = 0
    next_usn: int = 0
    lowest_valid_usn: int = 0
    max_usn: int = 0
    max_size_bytes: int = 0
    allocation_delta_bytes: int = 0
    estimated_records: int = 0
    error: Optional[str] = None
    """UsnJournalStatus class."""


class USN_JOURNAL_DATA_V0(ctypes.Structure):
    _fields_ = [
        ("UsnJournalID", ctypes.c_uint64),
        ("FirstUsn", ctypes.c_int64),
        ("NextUsn", ctypes.c_int64),
        ("LowestValidUsn", ctypes.c_int64),
        ("MaxUsn", ctypes.c_int64),
        ("MaximumSize", ctypes.c_uint64),
        ("AllocationDelta", ctypes.c_uint64),
    ]
    """USN_JOURNAL_DATA_V0 class."""


class UsnJournalScanner:
    """Production NTFS USN Change Journal query and diagnostic engine."""

    FSCTL_QUERY_USN_JOURNAL = 0x000900f4
    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000

    @classmethod
    def query_volume_journal(cls, drive_letter: str = "C:") -> UsnJournalStatus:
        """Query NTFS USN Journal status on the specified drive."""
        clean_drive = drive_letter.strip().rstrip("\\/").upper()
        if not clean_drive.endswith(":"):
            clean_drive += ":"

        if platform.system() != "Windows":
            return UsnJournalStatus(clean_drive, False, False, error="Windows NTFS only")

        volume_path = f"\\\\.\\{clean_drive}"
        kernel32 = ctypes.windll.kernel32

        handle = kernel32.CreateFileW(
            volume_path,
            cls.GENERIC_READ | cls.GENERIC_WRITE,
            cls.FILE_SHARE_READ | cls.FILE_SHARE_WRITE,
            None,
            cls.OPEN_EXISTING,
            cls.FILE_FLAG_BACKUP_SEMANTICS,
            None,
        )

        if handle == wintypes.HANDLE(-1).value or handle == 0:
            err = ctypes.GetLastError()
            # If standard user, open with read-only share
            handle = kernel32.CreateFileW(
                volume_path,
                cls.GENERIC_READ,
                cls.FILE_SHARE_READ | cls.FILE_SHARE_WRITE,
                None,
                cls.OPEN_EXISTING,
                0,
                None,
            )
            if handle == wintypes.HANDLE(-1).value or handle == 0:
                return UsnJournalStatus(clean_drive, True, False, error=f"Access denied (Admin rights required to inspect physical volume, Win32 Error: {err})")

        try:
            journal_data = USN_JOURNAL_DATA_V0()
            bytes_returned = wintypes.DWORD(0)

            ok = kernel32.DeviceIoControl(
                handle,
                cls.FSCTL_QUERY_USN_JOURNAL,
                None,
                0,
                ctypes.byref(journal_data),
                ctypes.sizeof(journal_data),
                ctypes.byref(bytes_returned),
                None,
            )

            if not ok:
                err = ctypes.GetLastError()
                return UsnJournalStatus(clean_drive, True, False, error=f"USN Journal not active on volume (Win32 Error {err})")

            est_records = max(0, int((journal_data.NextUsn - journal_data.FirstUsn) // 128))

            return UsnJournalStatus(
                drive_letter=clean_drive,
                is_supported=True,
                is_active=True,
                journal_id=int(journal_data.UsnJournalID),
                first_usn=int(journal_data.FirstUsn),
                next_usn=int(journal_data.NextUsn),
                lowest_valid_usn=int(journal_data.LowestValidUsn),
                max_usn=int(journal_data.MaxUsn),
                max_size_bytes=int(journal_data.MaximumSize),
                allocation_delta_bytes=int(journal_data.AllocationDelta),
                estimated_records=est_records,
            )
        finally:
            kernel32.CloseHandle(handle)
