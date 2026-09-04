"""Nexus Explorer — Forensic File Timestamp & Attribute Modifier (MACB Touch).

Inspects and updates:
1. Created Time (Birth Time / CTime)
2. Last Modified Time (MTime)
3. Last Accessed Time (ATime)
4. Win32 File Attributes (Read-only, Hidden, System, Archive, Compressed, Temporary)
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import datetime
import os
import platform
import time
from dataclasses import dataclass
from enum import Flag, auto
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class FileAttributeFlags(Flag):
    """Fileattributeflags.

    Manages FileAttributeFlags operations and coordinates related state changes for the component.
    """
    READONLY = 0x00000001
    HIDDEN = 0x00000002
    SYSTEM = 0x00000004
    ARCHIVE = 0x00000020
    NORMAL = 0x00000080
    TEMPORARY = 0x00000100
    COMPRESSED = 0x00000800


@dataclass
class TimestampInfo:
    """Timestampinfo.

    Manages TimestampInfo operations and coordinates related state changes for the component.
    """
    path: str
    filename: str
    created_time: float
    modified_time: float
    accessed_time: float
    attributes: int
    is_readonly: bool
    is_hidden: bool
    is_system: bool
    is_archive: bool


@dataclass
class TimestampUpdateResult:
    """Timestampupdateresult.

    Manages TimestampUpdateResult operations and coordinates related state changes for the component.
    """
    path: str
    success: bool
    error: Optional[str] = None


class TimestampTouchEngine:
    """Timestamptouchengine.

    Manages TimestampTouchEngine operations and coordinates related state changes for the component.
    """

    @classmethod
    def get_file_metadata(cls, file_path: str | Path) -> Optional[TimestampInfo]:
        """Query full MACB timestamps and attribute flags.

        Manages get file metadata operations and coordinates related state changes for the component.

        Args:
            file_path (str | Path): Filesystem path to the target file or directory.

        Returns:
            Optional[TimestampInfo]: Result of the operation.
        """
        p = Path(file_path).resolve()
        if not p.exists():
            return None

        try:
            st = p.stat()
            c_time = getattr(st, "st_birthtime", getattr(st, "st_ctime", st.st_mtime))
            m_time = st.st_mtime
            a_time = st.st_atime
            attrs = getattr(st, "st_file_attributes", 0)

            return TimestampInfo(
                path=str(p),
                filename=p.name,
                created_time=c_time,
                modified_time=m_time,
                accessed_time=a_time,
                attributes=attrs,
                is_readonly=bool(attrs & FileAttributeFlags.READONLY.value),
                is_hidden=bool(attrs & FileAttributeFlags.HIDDEN.value),
                is_system=bool(attrs & FileAttributeFlags.SYSTEM.value),
                is_archive=bool(attrs & FileAttributeFlags.ARCHIVE.value),
            )
        except Exception:
            return None

    @classmethod
    def set_timestamps(
        cls,
        file_path: str | Path,
        created_time: Optional[float | datetime.datetime] = None,
        modified_time: Optional[float | datetime.datetime] = None,
        accessed_time: Optional[float | datetime.datetime] = None,
    ) -> TimestampUpdateResult:
        """Set Created, Modified, and Accessed timestamps on a file or directory.

        Manages set timestamps operations and coordinates related state changes for the component.

        Args:
            file_path (str | Path): Filesystem path to the target file or directory.
            created_time (Optional[float | datetime.datetime]): The created time parameter.
            modified_time (Optional[float | datetime.datetime]): The modified time parameter.
            accessed_time (Optional[float | datetime.datetime]): The accessed time parameter.

        Returns:
            TimestampUpdateResult: Result of the operation.
        """
        p = Path(file_path).resolve()
        if not p.exists():
            return TimestampUpdateResult(str(p), False, "File does not exist")

        def _to_timestamp(val: Optional[float | datetime.datetime]) -> Optional[float]:
            """_to_timestamp.

            Manages to timestamp operations and coordinates related state changes for the component.

            Args:
                val (Optional[float | datetime.datetime]): The val parameter.

            Returns:
                Optional[float]: Result of the operation.
            """
            if val is None:
                return None
            if isinstance(val, datetime.datetime):
                return val.timestamp()
            return float(val)

        c_ts = _to_timestamp(created_time)
        m_ts = _to_timestamp(modified_time)
        a_ts = _to_timestamp(accessed_time)

        # On Windows, use SetFileTime Win32 API to accurately update Creation Time as well as M/A times
        if platform.system() == "Windows":
            return cls._set_windows_timestamps(p, c_ts, m_ts, a_ts)

        # Standard POSIX fallback for Modified / Accessed
        try:
            curr = p.stat()
            new_a = a_ts if a_ts is not None else curr.st_atime
            new_m = m_ts if m_ts is not None else curr.st_mtime
            os.utime(p, (new_a, new_m))
            return TimestampUpdateResult(str(p), True)
        except Exception as exc:
            return TimestampUpdateResult(str(p), False, str(exc))

    @classmethod
    def _set_windows_timestamps(
        cls,
        path: Path,
        created_ts: Optional[float],
        modified_ts: Optional[float],
        accessed_ts: Optional[float],
    ) -> TimestampUpdateResult:
        """Win32 SetFileTime implementation via ctypes.

        Manages set windows timestamps operations and coordinates related state changes for the component.

        Args:
            path (Path): Filesystem path to the target file or directory.
            created_ts (Optional[float]): The created ts parameter.
            modified_ts (Optional[float]): The modified ts parameter.
            accessed_ts (Optional[float]): The accessed ts parameter.

        Returns:
            TimestampUpdateResult: Result of the operation.
        """
        GENERIC_READ = 0x80000000
        GENERIC_WRITE = 0x40000000
        FILE_SHARE_READ = 0x00000001
        FILE_SHARE_WRITE = 0x00000002
        OPEN_EXISTING = 3
        FILE_FLAG_BACKUP_SEMANTICS = 0x02000000  # Required to open directory handles

        kernel32 = ctypes.windll.kernel32

        handle = kernel32.CreateFileW(
            str(path),
            GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS,
            None,
        )

        if handle == wintypes.HANDLE(-1).value or handle == 0:
            err = ctypes.GetLastError()
            return TimestampUpdateResult(str(path), False, f"Failed to open handle (Win32 Error: {err})")

        try:
            def _to_filetime(ts: Optional[float]) -> Optional[ctypes.c_uint64]:
                """_to_filetime.

                Manages to filetime operations and coordinates related state changes for the component.

                Args:
                    ts (Optional[float]): The ts parameter.

                Returns:
                    Optional[ctypes.c_uint64]: Result of the operation.
                """
                if ts is None:
                    return None
                # Windows FILETIME is 100-nanosecond intervals since Jan 1, 1601 UTC
                # Unix epoch is Jan 1, 1970 (11644473600 seconds after 1601)
                ft_val = int((ts + 11644473600) * 10000000)
                return ctypes.c_uint64(ft_val)

            c_ft = _to_filetime(created_ts)
            a_ft = _to_filetime(accessed_ts)
            m_ft = _to_filetime(modified_ts)

            lp_creation = ctypes.byref(c_ft) if c_ft is not None else None
            lp_access = ctypes.byref(a_ft) if a_ft is not None else None
            lp_write = ctypes.byref(m_ft) if m_ft is not None else None

            ok = kernel32.SetFileTime(handle, lp_creation, lp_access, lp_write)
            if ok:
                return TimestampUpdateResult(str(path), True)
            err = ctypes.GetLastError()
            return TimestampUpdateResult(str(path), False, f"SetFileTime failed (Win32 Error: {err})")
        finally:
            kernel32.CloseHandle(handle)

    @classmethod
    def set_attributes(
        cls,
        file_path: str | Path,
        readonly: Optional[bool] = None,
        hidden: Optional[bool] = None,
        system: Optional[bool] = None,
        archive: Optional[bool] = None,
    ) -> bool:
        """Update file attribute flags (Readonly, Hidden, System, Archive).

        Manages set attributes operations and coordinates related state changes for the component.

        Args:
            file_path (str | Path): Filesystem path to the target file or directory.
            readonly (Optional[bool]): The readonly parameter.
            hidden (Optional[bool]): The hidden parameter.
            system (Optional[bool]): The system parameter.
            archive (Optional[bool]): The archive parameter.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        p = Path(file_path).resolve()
        if not p.exists() or platform.system() != "Windows":
            return False

        try:
            curr_attrs = ctypes.windll.kernel32.GetFileAttributesW(str(p))
            if curr_attrs == 0xFFFFFFFF:
                return False

            new_attrs = curr_attrs
            if readonly is not None:
                new_attrs = (new_attrs | 0x1) if readonly else (new_attrs & ~0x1)
            if hidden is not None:
                new_attrs = (new_attrs | 0x2) if hidden else (new_attrs & ~0x2)
            if system is not None:
                new_attrs = (new_attrs | 0x4) if system else (new_attrs & ~0x4)
            if archive is not None:
                new_attrs = (new_attrs | 0x20) if archive else (new_attrs & ~0x20)

            return bool(ctypes.windll.kernel32.SetFileAttributesW(str(p), new_attrs))
        except Exception:
            return False

    @classmethod
    def touch_batch(
        cls,
        file_paths: List[str | Path],
        created_time: Optional[float | datetime.datetime] = None,
        modified_time: Optional[float | datetime.datetime] = None,
        accessed_time: Optional[float | datetime.datetime] = None,
    ) -> List[TimestampUpdateResult]:
        """Apply timestamp touch updates across a batch of files.

        Manages touch batch operations and coordinates related state changes for the component.

        Args:
            file_paths (List[str | Path]): Filesystem path to the target file or directory.
            created_time (Optional[float | datetime.datetime]): The created time parameter.
            modified_time (Optional[float | datetime.datetime]): The modified time parameter.
            accessed_time (Optional[float | datetime.datetime]): The accessed time parameter.

        Returns:
            List[TimestampUpdateResult]: List of processed items or identifiers.
        """
        results = []
        for fp in file_paths:
            results.append(cls.set_timestamps(fp, created_time, modified_time, accessed_time))
        return results
