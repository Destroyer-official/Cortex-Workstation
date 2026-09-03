"""Free-space wipe - overwrite the unused space on a volume.

After you delete a file normally, its bytes usually remain on disk until they
happen to be overwritten. Wiping free space overwrites all currently-unused
clusters so previously-deleted files can no longer be recovered by undelete
tools. On Windows this uses the built-in ``cipher /w`` command.

Honesty note: like single-file shredding, this is only a hard guarantee on
spinning HDDs. On SSDs/NVMe, wear-levelling and over-provisioning mean some
old data may physically remain even after a free-space wipe. We surface that
caveat rather than promising more than the medium can deliver.
"""

from __future__ import annotations

import logging
import sys
import re
import subprocess
import threading
from dataclasses import dataclass

from cortex_unified.core import proc as _proc
from cortex_unified.engine.storage import detect_storage

_LOG = logging.getLogger("cortex.system_tools.free_space_wipe")
_IS_WINDOWS = sys.platform == "win32"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0


@dataclass(slots=True)
class WipeResult:
    """Wipe Result data container."""
    success: bool
    message: str
    medium: str = ""
    effective: bool = True


class FreeSpaceWiper:
    """Overwrite a volume's free space (Windows ``cipher /w``)."""

    @staticmethod
    def is_supported() -> bool:
        """Is supported."""
        return _IS_WINDOWS

    def medium_for(self, drive_letter: str) -> tuple[str, bool]:
        """Return (medium_kind, overwrite_effective) for the drive."""
        try:
            info = detect_storage(f"{drive_letter}:\\")
            return info.kind.value, info.kind.overwrite_effective
        except Exception:  # noqa: BLE001
            return "unknown", False

    def wipe(self, drive_letter: str,
            cancel_event: "threading.Event | None" = None) -> WipeResult:
        """Wipe free space on *drive_letter* (e.g. 'C'). Blocking; can be slow."""
        if not _IS_WINDOWS:
            return WipeResult(False, "Free-space wipe is only available on Windows.")
        letter = (drive_letter or "").rstrip(":\\").strip()
        if not re.fullmatch(r"[A-Za-z]", letter):
            return WipeResult(False, "Invalid drive letter.")
        medium, effective = self.medium_for(letter)
        try:
            # cipher /w can run for up to an hour; poll the timeout and
            # cancel_event instead of blocking uninterruptibly, and kill the
            # whole process tree on either - never the calling thread.
            proc = _proc.run(
                ["cipher", f"/w:{letter}:\\"],
                text=True, timeout=60 * 60, cancel_event=cancel_event,
                creationflags=_NO_WINDOW,
            )
        except _proc.ProcessCancelled:
            return WipeResult(False, "Free-space wipe cancelled.", medium, effective)
        except subprocess.TimeoutExpired:
            return WipeResult(False, "Free-space wipe timed out.", medium, effective)
        except (OSError, subprocess.SubprocessError) as exc:
            return WipeResult(False, f"Free-space wipe failed: {exc}", medium, effective)

        if proc.returncode == 0:
            msg = f"Free space on {letter}: wiped."
            if not effective:
                msg += (f" Note: this drive is {medium}; some previously-deleted data may "
                        "physically remain due to wear-levelling.")
            return WipeResult(True, msg, medium, effective)
        return WipeResult(False,
                          "cipher reported an error (Administrator may be required).",
                          medium, effective)
