"""System file health & repair - orchestrating Windows' own repair tools.

Corrupted system files are a leading cause of crashes, update failures and
mysterious slowness. Microsoft's supported fixes are three built-in tools, and
Cortex simply runs them in the right order with plain-language results and
explicit confirmation - it does not invent its own "repair":

* ``sfc /scannow`` - System File Checker: verifies and repairs protected
  Windows files against a known-good cache.
* ``DISM /Online /Cleanup-Image /CheckHealth|ScanHealth|RestoreHealth`` -
  checks and repairs the component store that SFC relies on.
* ``chkdsk`` - checks the filesystem for errors (read-only scan here; a full
  ``/F`` fix must be scheduled for reboot, which we surface honestly).

These are long-running and (for the repair actions) system-modifying, so the UI
confirms first and runs them on a worker thread. All require Administrator.
"""

from __future__ import annotations

import logging
import platform
import re
import subprocess
from dataclasses import dataclass
from typing import Any

_LOG = logging.getLogger("cortex.system_tools.system_repair")
_IS_WINDOWS = platform.system() == "Windows"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0


@dataclass(slots=True)
class RepairResult:
    tool: str
    success: bool
    status: str          # short outcome label
    message: str         # human explanation
    needs_reboot: bool = False
    raw_tail: str = ""   # last lines of output for transparency

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool, "success": self.success, "status": self.status,
            "message": self.message, "needs_reboot": self.needs_reboot,
            "raw_tail": self.raw_tail,
        }


class SystemRepair:
    """Runs SFC / DISM / CHKDSK and interprets their results honestly."""

    @staticmethod
    def is_supported() -> bool:
        return _IS_WINDOWS

    @staticmethod
    def is_elevated() -> bool:
        if not _IS_WINDOWS:
            return False
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:  # noqa: BLE001
            return False

    # -- SFC ----------------------------------------------------------------

    def run_sfc(self) -> RepairResult:
        if not _IS_WINDOWS:
            return RepairResult("SFC", False, "unsupported", "Windows only.")
        out = self._run(["sfc", "/scannow"], timeout=60 * 30)
        return self._parse_sfc(out)

    @staticmethod
    def _parse_sfc(out: str | None) -> RepairResult:
        if out is None:
            return RepairResult("SFC", False, "error",
                                "Could not run SFC (Administrator required).")
        low = out.lower()
        tail = "\n".join(l for l in out.splitlines() if l.strip())[-600:]
        if "did not find any integrity violations" in low:
            return RepairResult("SFC", True, "clean",
                                "No corrupted system files found.", raw_tail=tail)
        if "successfully repaired" in low:
            return RepairResult("SFC", True, "repaired",
                                "Found corrupted files and successfully repaired them.",
                                needs_reboot=True, raw_tail=tail)
        if "unable to fix" in low or "could not perform" in low:
            return RepairResult("SFC", False, "partial",
                                "Found corruption but could not repair everything. "
                                "Run DISM RestoreHealth, then SFC again.", raw_tail=tail)
        if "another servicing" in low or "pending" in low:
            return RepairResult("SFC", False, "busy",
                                "A system servicing operation is in progress; try again "
                                "after it finishes.", raw_tail=tail)
        return RepairResult("SFC", True, "done", "SFC finished.", raw_tail=tail)

    # -- DISM ---------------------------------------------------------------

    def run_dism(self, action: str = "CheckHealth") -> RepairResult:
        if not _IS_WINDOWS:
            return RepairResult("DISM", False, "unsupported", "Windows only.")
        action = action if action in ("CheckHealth", "ScanHealth", "RestoreHealth") \
            else "CheckHealth"
        timeout = 60 * 30 if action == "RestoreHealth" else 60 * 15
        out = self._run(["dism", "/Online", "/Cleanup-Image", f"/{action}"], timeout=timeout)
        return self._parse_dism(out, action)

    @staticmethod
    def _parse_dism(out: str | None, action: str) -> RepairResult:
        if out is None:
            return RepairResult("DISM", False, "error",
                                "Could not run DISM (Administrator required).")
        low = out.lower()
        tail = "\n".join(l for l in out.splitlines() if l.strip())[-600:]
        if "no component store corruption detected" in low:
            return RepairResult("DISM", True, "clean",
                                "The Windows component store is healthy.", raw_tail=tail)
        if "the restore operation completed successfully" in low or \
           ("restorehealth" in action.lower() and "completed successfully" in low):
            return RepairResult("DISM", True, "repaired",
                                "Component store corruption was repaired successfully.",
                                needs_reboot=True, raw_tail=tail)
        if "the component store is repairable" in low:
            return RepairResult("DISM", True, "repairable",
                                "Corruption detected but it IS repairable. Run DISM "
                                "RestoreHealth to fix it.", raw_tail=tail)
        if "error" in low and "0x" in low:
            m = re.search(r"(0x[0-9a-fA-F]{8})", out)
            code = m.group(1) if m else ""
            return RepairResult("DISM", False, "error",
                                f"DISM reported an error {code}. Check your internet "
                                "connection (RestoreHealth may fetch files from Windows "
                                "Update).", raw_tail=tail)
        return RepairResult("DISM", True, "done", f"DISM {action} finished.", raw_tail=tail)

    # -- CHKDSK (read-only scan) -------------------------------------------

    def run_chkdsk_scan(self, drive: str = "C") -> RepairResult:
        if not _IS_WINDOWS:
            return RepairResult("CHKDSK", False, "unsupported", "Windows only.")
        letter = (drive or "C").rstrip(":\\").strip()
        if not re.fullmatch(r"[A-Za-z]", letter):
            return RepairResult("CHKDSK", False, "error", "Invalid drive letter.")
        out = self._run(["chkdsk", f"{letter}:"], timeout=60 * 20)
        return self._parse_chkdsk(out, letter)

    @staticmethod
    def _parse_chkdsk(out: str | None, letter: str) -> RepairResult:
        if out is None:
            return RepairResult("CHKDSK", False, "error",
                                "Could not run CHKDSK (Administrator required).")
        low = out.lower()
        tail = "\n".join(l for l in out.splitlines() if l.strip())[-600:]
        if "found no problems" in low or "no further action is required" in low:
            return RepairResult("CHKDSK", True, "clean",
                                f"Drive {letter}: has no filesystem errors.", raw_tail=tail)
        if "errors" in low and ("found" in low or "detected" in low):
            return RepairResult("CHKDSK", True, "errors",
                                f"Drive {letter}: has filesystem errors. Schedule a full "
                                "check with repair (chkdsk /F) which runs at next reboot.",
                                needs_reboot=True, raw_tail=tail)
        return RepairResult("CHKDSK", True, "done",
                            f"CHKDSK finished scanning {letter}:.", raw_tail=tail)

    # -- helper -------------------------------------------------------------

    def _run(self, args: list[str], timeout: int) -> str | None:
        try:
            proc = subprocess.run(
                args, capture_output=True, timeout=timeout, creationflags=_NO_WINDOW,
            )
            # SFC/DISM emit UTF-16LE with embedded NULs on the Windows console;
            # decode robustly and strip NULs so parsing works.
            raw = proc.stdout or b""
            text = self._decode(raw)
            if proc.stderr:
                text += "\n" + self._decode(proc.stderr)
            return text
        except subprocess.TimeoutExpired:
            _LOG.debug("%s timed out", args[0] if args else "?")
            return None
        except (OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("%s failed: %s", args[0] if args else "?", exc)
            return None

    @staticmethod
    def _decode(raw: bytes) -> str:
        if not raw:
            return ""
        if b"\x00" in raw:
            try:
                return raw.decode("utf-16-le", "replace")
            except Exception:  # noqa: BLE001
                pass
        for enc in ("utf-8", "mbcs", "latin-1"):
            try:
                return raw.decode(enc, "replace")
            except Exception:  # noqa: BLE001
                continue
        return raw.decode("utf-8", "replace")
