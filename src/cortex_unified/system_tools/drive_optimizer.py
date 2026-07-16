"""Media-aware drive optimization - the honest way.

The #1 correctness rule (well-established): **never defragment an SSD.** On SSD/
NVMe the right maintenance is TRIM (``Optimize-Volume -ReTrim``); on rotational
HDDs it's defragmentation (``Optimize-Volume -Defrag``). Windows' own Optimize
Drives does the right thing per medium; many third-party "defraggers" get this
dangerously wrong. We detect the medium first (reusing the engine's StorageProbe)
and pick the correct operation - or refuse and explain.

All operations are read-first (analyze) and only act when explicitly asked.
Windows-only; time-boxed, window-hidden subprocess calls.
"""

from __future__ import annotations

import enum
import logging
import platform
import subprocess
from dataclasses import dataclass, field
from typing import Any

from cortex_unified.engine.storage import detect_storage
from cortex_unified.engine.models import StorageKind

_LOG = logging.getLogger("cortex.system_tools.drive_optimizer")
_IS_WINDOWS = platform.system() == "Windows"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0


class OptimizeOp(str, enum.Enum):
    TRIM = "retrim"          # correct for SSD/NVMe
    DEFRAG = "defrag"        # correct for HDD
    NONE = "none"            # nothing appropriate / unsupported


@dataclass(slots=True)
class DriveInfo:
    letter: str
    kind: StorageKind
    recommended_op: OptimizeOp
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "letter": self.letter,
            "kind": self.kind.value,
            "recommended_op": self.recommended_op.value,
            "note": self.note,
        }


@dataclass(slots=True)
class OptimizeResult:
    letter: str
    op: OptimizeOp
    success: bool
    message: str = ""


class DriveOptimizer:
    """List fixed drives, recommend the correct op per medium, and run it safely."""

    def __init__(self) -> None:
        self.logger = _LOG

    @staticmethod
    def is_supported() -> bool:
        return _IS_WINDOWS

    def list_drives(self) -> list[DriveInfo]:
        """Return fixed drives with the medium-correct recommended operation."""
        if not _IS_WINDOWS:
            return []
        drives: list[DriveInfo] = []
        for letter in self._fixed_drive_letters():
            info = detect_storage(f"{letter}:\\")
            op, note = self._recommend(info.kind)
            drives.append(DriveInfo(letter, info.kind, op, note))
        return drives

    @staticmethod
    def _recommend(kind: StorageKind) -> tuple[OptimizeOp, str]:
        if kind is StorageKind.HDD:
            return OptimizeOp.DEFRAG, "Rotational drive: defragmentation is appropriate."
        if kind in (StorageKind.SSD, StorageKind.NVME):
            return OptimizeOp.TRIM, "Solid-state drive: TRIM only - never defragment an SSD."
        if kind is StorageKind.REMOVABLE:
            return OptimizeOp.TRIM, "Removable/flash media: TRIM if supported."
        return OptimizeOp.NONE, "Unknown medium: no optimization recommended."

    def optimize(self, letter: str, op: OptimizeOp | None = None) -> OptimizeResult:
        """Run the correct optimization for *letter*. If *op* is None, auto-pick.

        Refuses to defrag SSD/NVMe even if explicitly asked (safety).
        """
        letter = letter.rstrip(":\\").upper()
        if not _IS_WINDOWS:
            return OptimizeResult(letter, OptimizeOp.NONE, False, "Windows-only feature.")

        kind = detect_storage(f"{letter}:\\").kind
        auto_op, _ = self._recommend(kind)
        chosen = op or auto_op

        # Hard safety: never defragment solid-state media.
        if chosen is OptimizeOp.DEFRAG and kind in (StorageKind.SSD, StorageKind.NVME):
            return OptimizeResult(
                letter, OptimizeOp.NONE, False,
                f"Refused: {letter}: is {kind.value}; defragmenting an SSD is harmful. "
                f"Use TRIM instead.",
            )
        if chosen is OptimizeOp.NONE:
            return OptimizeResult(letter, OptimizeOp.NONE, False,
                                  "No appropriate optimization for this medium.")

        flag = "-ReTrim" if chosen is OptimizeOp.TRIM else "-Defrag"
        script = (
            f"$ErrorActionPreference='Stop';"
            f"try {{ Optimize-Volume -DriveLetter {letter} {flag} -Verbose; "
            f"Write-Output 'OPTIMIZE_OK' }} "
            f"catch {{ Write-Output ('OPTIMIZE_FAIL;'+$_.Exception.Message) }}"
        )
        out = self._run_ps(script, timeout=1800)  # defrag can be slow
        if out and "OPTIMIZE_OK" in out:
            return OptimizeResult(letter, chosen, True,
                                  f"{chosen.value.upper()} completed on {letter}:.")
        msg = ""
        if out and "OPTIMIZE_FAIL;" in out:
            msg = out.split("OPTIMIZE_FAIL;", 1)[1].strip()
        return OptimizeResult(letter, chosen, False, msg or "Optimization failed (Administrator may be required).")

    # -- helpers ------------------------------------------------------------

    def _fixed_drive_letters(self) -> list[str]:
        """Return fixed (non-removable, non-network) drive letters."""
        script = (
            "Get-CimInstance -ClassName Win32_LogicalDisk -Filter 'DriveType=3' "
            "| Select-Object -ExpandProperty DeviceID"
        )
        out = self._run_ps(script, timeout=20)
        letters: list[str] = []
        if out:
            for line in out.splitlines():
                line = line.strip().rstrip(":")
                if len(line) == 1 and line.isalpha():
                    letters.append(line.upper())
        return letters or ["C"]

    def _run_ps(self, script: str, timeout: int) -> str | None:
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, timeout=timeout, creationflags=_NO_WINDOW,
            )
            return proc.stdout if proc.stdout else (proc.stderr or None)
        except (OSError, subprocess.SubprocessError) as exc:
            self.logger.debug("powershell failed: %s", exc)
            return None
