"""Nexus Explorer — NTFS Alternate Data Streams (ADS) & Zone.Identifier Manager.

Enumerates, inspects, extracts, and strips NTFS Alternate Data Streams
(including Zone.Identifier Mark-of-the-Web security blocks and hidden streams)
using native Windows kernel32.dll FindFirstStreamW / FindNextStreamW APIs.
"""

from __future__ import annotations

import ctypes
import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

if platform.system() == "Windows":
    from ctypes import wintypes

    class WIN32_FIND_STREAM_DATA(ctypes.Structure):
        """WIN32_FIND_STREAM_DATA."""
        _fields_ = [
            ("StreamSize", ctypes.c_longlong),
            ("cStreamName", wintypes.WCHAR * 296),
        ]
        """WIN32_FIND_STREAM_DATA class."""


@dataclass
class AlternateDataStream:
    """AlternateDataStream."""
    file_path: str
    stream_full_name: str  # e.g. ":Zone.Identifier:$DATA"
    stream_name: str       # e.g. "Zone.Identifier"
    stream_type: str       # e.g. "$DATA"
    size_bytes: int
    is_zone_identifier: bool = False
    content_preview: str = ""
    """AlternateDataStream class."""


class AlternateDataStreamsManager:
    """Production NTFS Alternate Data Stream inspector and unblocker."""

    @classmethod
    def list_streams(cls, file_path: str | Path) -> List[AlternateDataStream]:
        """Enumerate all alternate data streams for the target file."""
        target = str(Path(file_path).resolve())
        kernel32 = ctypes.windll.kernel32
        find_data = WIN32_FIND_STREAM_DATA()

        # Configure 64-bit safe ctypes prototypes
        kernel32.FindFirstStreamW.restype = wintypes.HANDLE
        kernel32.FindFirstStreamW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        kernel32.FindNextStreamW.restype = wintypes.BOOL
        kernel32.FindNextStreamW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        kernel32.FindClose.restype = wintypes.BOOL
        kernel32.FindClose.argtypes = [wintypes.HANDLE]

        # FindFirstStreamW
        INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
        handle = kernel32.FindFirstStreamW(
            target,
            0,  # FindStreamInfoStandard
            ctypes.byref(find_data),
            0,
        )

        if handle == INVALID_HANDLE_VALUE or not handle or handle == -1:
            return []

        streams: List[AlternateDataStream] = []

        try:
            while True:
                raw_name = find_data.cStreamName
                size = find_data.StreamSize

                # Default main stream is "::$DATA"
                if raw_name and raw_name != "::$DATA":
                    # Format is :StreamName:$StreamType
                    parts = raw_name.strip(":").split(":")
                    stream_id = parts[0] if parts else raw_name
                    stream_type = parts[1] if len(parts) > 1 else "$DATA"
                    is_zone_id = (stream_id.lower() == "zone.identifier")

                    # Preview stream content if small
                    preview = ""
                    try:
                        stream_path = f"{target}:{stream_id}"
                        with open(stream_path, "r", encoding="utf-8", errors="replace") as sf:
                            preview = sf.read(512).strip()
                    except Exception:
                        pass

                    streams.append(AlternateDataStream(
                        file_path=target,
                        stream_full_name=raw_name,
                        stream_name=stream_id,
                        stream_type=stream_type,
                        size_bytes=size,
                        is_zone_identifier=is_zone_id,
                        content_preview=preview,
                    ))

                # FindNextStreamW
                has_next = kernel32.FindNextStreamW(handle, ctypes.byref(find_data))
                if not has_next:
                    break
        finally:
            kernel32.FindClose(handle)

        return streams

    @classmethod
    def read_stream_text(cls, file_path: str | Path, stream_name: str) -> str:
        """Read text contents of a specific alternate data stream."""
        target = str(Path(file_path).resolve())
        stream_id = stream_name.strip(":").split(":")[0]
        stream_path = f"{target}:{stream_id}"

        try:
            with open(stream_path, "r", encoding="utf-8", errors="replace") as sf:
                return sf.read()
        except Exception as exc:
            return f"Error reading stream: {exc}"

    @classmethod
    def delete_stream(cls, file_path: str | Path, stream_name: str) -> Tuple[bool, str]:
        """Delete an alternate data stream using kernel32.DeleteFileW."""
        target = str(Path(file_path).resolve())
        stream_id = stream_name.strip(":").split(":")[0]
        stream_path = f"{target}:{stream_id}"

        if platform.system() == "Windows":
            kernel32 = ctypes.windll.kernel32
            ok = kernel32.DeleteFileW(ctypes.c_wchar_p(stream_path))
            if ok:
                return True, f"Stream '{stream_id}' removed successfully."
            err = ctypes.GetLastError()
            return False, f"Failed to delete stream (Win32 Error: {err})"

        try:
            os.remove(stream_path)
            return True, f"Stream '{stream_id}' removed."
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def unblock_file(cls, file_path: str | Path) -> Tuple[bool, str]:
        """Unblock downloaded file by removing its Zone.Identifier alternate data stream."""
        return cls.delete_stream(file_path, "Zone.Identifier")

    @classmethod
    def strip_all_streams(cls, file_path: str | Path) -> Tuple[int, int]:
        """Remove all alternate data streams from a file."""
        streams = cls.list_streams(file_path)
        success = 0
        failed = 0
        for s in streams:
            ok, _ = cls.delete_stream(file_path, s.stream_name)
            if ok:
                success += 1
            else:
                failed += 1
        return success, failed
