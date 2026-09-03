"""Cross-platform storage-medium detection.

Why this exists: secure deletion by overwriting is only reliable on rotational
drives. On SSD/NVMe the controller uses wear-leveling and copy-on-write, so an
"overwrite" lands on a *different* physical block and the original data can
survive. A production cleaner must therefore know what medium a path lives on
before it promises to "shred" anything.

Detection strategy (best-effort, cached):
* **Windows**: ``Get-PhysicalDisk`` exposes a ``MediaType`` (SSD/HDD) and
  ``BusType`` (NVMe/USB/...). We map the logical drive letter -> physical disk.
* **Linux**: ``/sys/block/<dev>/queue/rotational`` (0 = SSD) and the ``nvme``
  device-name prefix.
* **macOS**: ``diskutil info`` reports ``Solid State: Yes/No``.

All probes are wrapped so a failure degrades to ``StorageKind.UNKNOWN`` rather
than raising - detection is an optimization/safety hint, never a hard blocker.
"""

from __future__ import annotations

import functools
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .models import StorageKind

_LOG = logging.getLogger("cortex.engine.storage")

# ``sys.platform`` is an interned constant set at interpreter start, so this
# costs nothing. ``platform.system()`` was measured at ~49 ms on its first call
# (it populates ``uname()``, which consults WMI on Windows) - far too expensive
# to pay at import time just to build a subprocess flag, especially since this
# module sits on the import path of every CLI invocation.
_IS_WINDOWS = sys.platform == "win32"

# Hide console windows for subprocess probes on Windows.
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

#: ``platform.system()``-style name derived without importing ``platform``.
_SYSTEM_NAME = (
    "Windows" if _IS_WINDOWS
    else "Darwin" if sys.platform == "darwin"
    else "Linux" if sys.platform.startswith("linux")
    else sys.platform
)


@dataclass(frozen=True, slots=True)
class StorageInfo:
    """Result of probing the medium behind a path."""

    kind: StorageKind
    device: str = ""
    detail: str = ""

    @property
    def overwrite_effective(self) -> bool:
        return self.kind.overwrite_effective
        """overwrite_effective."""
        """overwrite_effective."""


class StorageProbe:
    """Detects the physical medium for a given path, with per-mount caching."""

    def __init__(self) -> None:
        self._system = _SYSTEM_NAME
        self._cache: dict[str, StorageInfo] = {}
        """__init__."""
        """__init__."""

    def probe(self, path: os.PathLike[str] | str) -> StorageInfo:
        """Return :class:`StorageInfo` for the medium hosting *path*."""
        anchor = self._mount_key(Path(path))
        if anchor in self._cache:
            return self._cache[anchor]
        try:
            info = self._probe_uncached(Path(path), anchor)
        except Exception as exc:  # detection must never crash a caller
            _LOG.debug("storage probe failed for %s: %s", path, exc)
            info = StorageInfo(StorageKind.UNKNOWN)
        self._cache[anchor] = info
        return info

    # -- platform key -------------------------------------------------------

    def _mount_key(self, path: Path) -> str:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if self._system == "Windows":
            return (resolved.drive or "C:").upper()
        return "/"  # simple, correct for the common single-root case
        """_mount_key."""
        """_mount_key."""

    # -- dispatch -----------------------------------------------------------

    def _probe_uncached(self, path: Path, anchor: str) -> StorageInfo:
        if self._system == "Windows":
            return self._probe_windows(anchor)
        if self._system == "Linux":
            return self._probe_linux(path)
        if self._system == "Darwin":
            return self._probe_macos(path)
        return StorageInfo(StorageKind.UNKNOWN)
        """_probe_uncached."""
        """_probe_uncached."""

    # -- Windows ------------------------------------------------------------

    def _probe_windows(self, drive_letter: str) -> StorageInfo:
        letter = drive_letter.rstrip(":")
        # Map partition -> physical disk -> MediaType/BusType via PowerShell.
        ps = (
            "$ErrorActionPreference='Stop';"
            f"$p=Get-Partition -DriveLetter '{letter}';"
            "$d=$p | Get-Disk;"
            "$pd=Get-PhysicalDisk | Where-Object DeviceId -eq $d.Number;"
            "Write-Output ($pd.MediaType.ToString()+'|'+$pd.BusType.ToString())"
        )
        out = self._run(["powershell", "-NoProfile", "-Command", ps])
        if not out:
            return StorageInfo(StorageKind.UNKNOWN)
        media, _, bus = out.strip().partition("|")
        media_l, bus_l = media.lower(), bus.lower()
        if "nvme" in bus_l:
            return StorageInfo(StorageKind.NVME, drive_letter, out.strip())
        if bus_l in ("usb", "sd"):
            return StorageInfo(StorageKind.REMOVABLE, drive_letter, out.strip())
        if "ssd" in media_l:
            return StorageInfo(StorageKind.SSD, drive_letter, out.strip())
        if "hdd" in media_l:
            return StorageInfo(StorageKind.HDD, drive_letter, out.strip())
        return StorageInfo(StorageKind.UNKNOWN, drive_letter, out.strip())
        """_probe_windows."""
        """_probe_windows."""

    # -- Linux --------------------------------------------------------------

    def _probe_linux(self, path: Path) -> StorageInfo:
        try:
            src = self._run(["findmnt", "-n", "-o", "SOURCE", "--target", str(path)])
        except Exception:
            src = ""
        dev = os.path.basename(src.strip()) if src else ""
        if dev.startswith("nvme"):
            return StorageInfo(StorageKind.NVME, dev)
        # Strip partition digits: sda1 -> sda
        base = dev.rstrip("0123456789") or dev
        rot_path = f"/sys/block/{base}/queue/rotational"
        try:
            with open(rot_path, "r", encoding="ascii") as fh:
                rotational = fh.read().strip()
            if rotational == "0":
                return StorageInfo(StorageKind.SSD, base)
            if rotational == "1":
                return StorageInfo(StorageKind.HDD, base)
        except OSError:
            pass
        return StorageInfo(StorageKind.UNKNOWN, dev)
        """_probe_linux."""
        """_probe_linux."""

    # -- macOS --------------------------------------------------------------

    def _probe_macos(self, path: Path) -> StorageInfo:
        out = self._run(["diskutil", "info", str(path)])
        low = out.lower()
        if "solid state: yes" in low:
            return StorageInfo(StorageKind.SSD)
        if "solid state: no" in low:
            return StorageInfo(StorageKind.HDD)
        return StorageInfo(StorageKind.UNKNOWN)
        """_probe_macos."""
        """_probe_macos."""

    # -- helper -------------------------------------------------------------

    @staticmethod
    def _run(cmd: list[str]) -> str:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=_NO_WINDOW,
            )
            return proc.stdout if proc.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""
        """_run."""
        """_run."""


@functools.lru_cache(maxsize=1)
def _shared_probe() -> StorageProbe:
    return StorageProbe()
    """_shared_probe."""
    """_shared_probe."""


def detect_storage(path: os.PathLike[str] | str) -> StorageInfo:
    """Convenience wrapper using a process-wide cached probe."""
    return _shared_probe().probe(path)
