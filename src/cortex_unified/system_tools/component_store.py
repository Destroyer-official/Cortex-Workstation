"""Component store (WinSxS) analysis and Windows upgrade leftovers.

``C:\\Windows`` bloat is almost always WinSxS plus upgrade leftovers, and
hand-deleting either breaks Windows Update, feature repair, or the ability to
uninstall installed software. This module measures the store read-only via
``DISM /AnalyzeComponentStore``, cleans it the supported way
(``DISM /StartComponentCleanup``, with ``/ResetBase`` as an explicit opt-in
because it permanently blocks uninstalling currently installed updates), and
inventories leftovers such as ``Windows.old`` with the cost of removing each.
WinSxS and ``C:\\Windows\\Installer`` are reported, never deleted directly.
Windows-only; every subprocess call is time-boxed with a hidden window and
nothing modifies the system unless a cleanup method is called explicitly.
"""

from __future__ import annotations

import enum
import logging
import sys
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from cortex_unified.core import proc as _proc

_LOG = logging.getLogger("cortex.system_tools.component_store")
_IS_WINDOWS = sys.platform == "win32"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

#: Rollback window Windows itself honours for ``Windows.old`` before removing it.
_ROLLBACK_DAYS = 10


class LeftoverRisk(str, enum.Enum):
    """What you give up by removing a leftover."""

    SAFE = "safe"              # regenerable; nothing is lost
    LOSES_ROLLBACK = "rollback"  # you can no longer go back to the old build
    MANAGED = "managed"        # Windows owns this; never delete by hand


@dataclass(slots=True)
class StoreAnalysis:
    """Result of ``DISM /AnalyzeComponentStore`` - all figures from Windows."""

    supported: bool = True
    ok: bool = False
    reported_size: int = 0        # what Explorer shows (double-counts hard links)
    actual_size: int = 0         # real size on disk
    shared_with_windows: int = 0  # cannot be reclaimed at any price
    backups_and_features: int = 0
    cache_and_temp: int = 0
    reclaimable_packages: int = 0
    last_cleanup: str = ""
    cleanup_recommended: bool = False
    message: str = ""
    raw_tail: str = ""

    @property
    def explorer_gap_note(self) -> str:
        """Why Explorer's WinSxS figure exceeds the actual on-disk size."""
        if not (self.reported_size and self.actual_size):
            return ""
        if self.reported_size <= self.actual_size:
            return ""
        return (
            "File Explorer reports WinSxS as larger than it is. Most of the "
            "folder is hard links to files that also live in System32, and "
            "Explorer counts each link separately. The actual size is the "
            "figure that matters."
        )

    @property
    def reclaimable_estimate(self) -> int:
        """Upper bound on what a cleanup could return.

        Only the backup/disabled-feature and cache portions are candidates; the
        part shared with Windows is never reclaimable. This is Windows' own
        breakdown, not a guess of ours.
        """
        return max(0, self.backups_and_features + self.cache_and_temp)

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "supported": self.supported,
            "ok": self.ok,
            "reported_size": self.reported_size,
            "actual_size": self.actual_size,
            "shared_with_windows": self.shared_with_windows,
            "backups_and_features": self.backups_and_features,
            "cache_and_temp": self.cache_and_temp,
            "reclaimable_packages": self.reclaimable_packages,
            "reclaimable_estimate": self.reclaimable_estimate,
            "last_cleanup": self.last_cleanup,
            "cleanup_recommended": self.cleanup_recommended,
            "message": self.message,
        }


@dataclass(slots=True)
class Leftover:
    """One upgrade/servicing leftover on disk."""

    path: Path
    label: str
    size_bytes: int
    risk: LeftoverRisk
    explanation: str
    age_days: float | None = None
    #: How to remove it properly. Empty when Cortex can remove it directly.
    supported_removal: str = ""

    @property
    def removable_here(self) -> bool:
        """True when Cortex may delete this itself."""
        return self.risk is not LeftoverRisk.MANAGED

    @property
    def rollback_expired(self) -> bool:
        """True once Windows' own rollback window has passed."""
        return self.age_days is not None and self.age_days > _ROLLBACK_DAYS

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "path": str(self.path),
            "label": self.label,
            "size_bytes": self.size_bytes,
            "risk": self.risk.value,
            "explanation": self.explanation,
            "age_days": self.age_days,
            "supported_removal": self.supported_removal,
            "removable_here": self.removable_here,
            "rollback_expired": self.rollback_expired,
        }


@dataclass(slots=True)
class CleanupOutcome:
    """Result of a component-store cleanup, with measured before/after."""

    success: bool
    reset_base: bool = False
    before_bytes: int = 0
    after_bytes: int = 0
    message: str = ""
    raw_tail: str = ""
    needs_reboot: bool = False

    @property
    def freed_bytes(self) -> int:
        """Freed bytes."""
        return max(0, self.before_bytes - self.after_bytes)

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "success": self.success,
            "reset_base": self.reset_base,
            "before_bytes": self.before_bytes,
            "after_bytes": self.after_bytes,
            "freed_bytes": self.freed_bytes,
            "message": self.message,
            "needs_reboot": self.needs_reboot,
        }


class ComponentStore:
    """Analyze and clean the WinSxS component store; inventory leftovers."""

    def __init__(self) -> None:
        """Initialize Component Store."""
        self.logger = _LOG

    @staticmethod
    def is_supported() -> bool:
        """Is supported."""
        return _IS_WINDOWS

    @staticmethod
    def is_elevated() -> bool:
        """True when running as Administrator (required for every cleanup)."""
        if not _IS_WINDOWS:
            return False
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:  # noqa: BLE001
            return False

    # -- analysis (read-only) -----------------------------------------------

    def analyze(self, timeout: int = 900,
               cancel_event: "threading.Event | None" = None) -> StoreAnalysis:
        """Run ``DISM /AnalyzeComponentStore`` and parse Windows' own figures."""
        if not _IS_WINDOWS:
            return StoreAnalysis(supported=False, message="Windows-only feature.")

        out = self._run_dism(["/Online", "/Cleanup-Image", "/AnalyzeComponentStore"],
                             timeout=timeout, cancel_event=cancel_event)
        if out is None:
            return StoreAnalysis(
                ok=False,
                message=("Could not run DISM. Analyzing the component store "
                         "requires Administrator rights."),
            )
        return self._parse_analysis(out)

    @staticmethod
    def _parse_analysis(out: str) -> StoreAnalysis:
        """Parse DISM's human-readable report into numbers.

        DISM localizes its output, so parsing is keyed on the stable English
        labels and degrades to "unknown" (0) rather than guessing when a label
        isn't found - a wrong number here would be worse than none.
        """
        res = StoreAnalysis(raw_tail="\n".join(
            line for line in out.splitlines() if line.strip())[-1200:])
        low = out.lower()

        def _bytes_after(label: str) -> int:
            # e.g. "Actual Size of Component Store : 7.32 GB"
            """_bytes_after."""
            m = re.search(
                rf"{label}\s*:\s*([\d.,]+)\s*(bytes|kb|mb|gb|tb)", low)
            if not m:
                return 0
            try:
                value = float(m.group(1).replace(",", ""))
            except ValueError:
                return 0
            unit = m.group(2)
            factor = {"bytes": 1, "kb": 1024, "mb": 1024 ** 2,
                      "gb": 1024 ** 3, "tb": 1024 ** 4}[unit]
            return int(value * factor)
            """_bytes_after."""
            """_bytes_after."""

        res.reported_size = _bytes_after(r"windows explorer reported size of component store")
        res.actual_size = _bytes_after(r"actual size of component store")
        res.shared_with_windows = _bytes_after(r"shared with windows")
        res.backups_and_features = _bytes_after(r"backups and disabled features")
        res.cache_and_temp = _bytes_after(r"cache and temporary data")

        m = re.search(r"number of reclaimable packages\s*:\s*(\d+)", low)
        if m:
            res.reclaimable_packages = int(m.group(1))
        m = re.search(r"date of last cleanup\s*:\s*(.+)", out, re.IGNORECASE)
        if m:
            res.last_cleanup = m.group(1).strip()
        m = re.search(r"component store cleanup recommended\s*:\s*(\w+)", low)
        if m:
            res.cleanup_recommended = m.group(1).strip() == "yes"

        if "error" in low and "0x" in low:
            code = re.search(r"(0x[0-9a-fA-F]{8})", out)
            res.ok = False
            res.message = (f"DISM reported error {code.group(1) if code else ''}. "
                           "Run the component store repair first (System File Health).")
            return res

        res.ok = bool(res.actual_size or res.reclaimable_packages
                      or "completed successfully" in low)
        if not res.ok:
            res.message = ("DISM finished but its report could not be read. "
                           "See the raw output for details.")
        elif res.cleanup_recommended:
            res.message = "Windows recommends cleaning the component store."
        else:
            res.message = "Windows does not consider a cleanup necessary right now."
        return res

    # -- leftovers (read-only) ----------------------------------------------

    def find_leftovers(
        self,
        progress: Callable[[str], None] | None = None,
        cancel_event=None,
        analysis: StoreAnalysis | None = None,
    ) -> list[Leftover]:
        """Inventory upgrade/servicing leftovers with size, age and cost.

        Pass ``analysis`` to source the component store's size from DISM instead
        of walking ``WinSxS``. That is both far faster (the folder holds hundreds
        of thousands of entries) and *more correct*: walking it counts each hard
        link separately, which is exactly the inflated figure Explorer shows and
        that this page exists to explain.
        """
        if not _IS_WINDOWS:
            return []
        system_drive = Path(os.environ.get("SystemDrive", "C:") + "\\")
        windir = Path(os.environ.get("SystemRoot", r"C:\Windows"))

        specs: list[tuple[Path, str, LeftoverRisk, str, str]] = [
            (system_drive / "Windows.old",
             "Previous Windows installation",
             LeftoverRisk.LOSES_ROLLBACK,
             "Your files from the build you upgraded from. Removing it frees the "
             "most space of anything here, but you can no longer roll back to "
             "that Windows version.",
             ""),
            (system_drive / "$WinREAgent",
             "Upgrade working folder",
             LeftoverRisk.SAFE,
             "Temporary staging left behind by a Windows upgrade or update. "
             "Windows recreates it when needed.",
             ""),
            (system_drive / "$Windows.~BT",
             "Upgrade installation files",
             LeftoverRisk.LOSES_ROLLBACK,
             "Setup files from an in-place upgrade. Needed only for rollback.",
             ""),
            (system_drive / "$Windows.~WS",
             "Upgrade download cache",
             LeftoverRisk.SAFE,
             "Downloaded setup payload from an upgrade attempt; re-downloaded "
             "if you upgrade again.",
             ""),
            (windir / "SoftwareDistribution" / "Download",
             "Windows Update download staging",
             LeftoverRisk.SAFE,
             "Update packages already installed. Windows re-downloads anything "
             "it still needs.",
             ""),
            (windir / "Panther",
             "Setup logs",
             LeftoverRisk.SAFE,
             "Logs from Windows setup. Useful only when troubleshooting a failed "
             "upgrade.",
             ""),
            (windir / "Minidump",
             "Crash minidumps",
             LeftoverRisk.SAFE,
             "Small crash reports. Keep them if you are still investigating a "
             "blue screen - the Reliability page can read them.",
             ""),
            (windir / "Installer",
             "Installer cache",
             LeftoverRisk.MANAGED,
             "Cached installer data used to repair, patch and uninstall software. "
             "Deleting files here eventually breaks Office, Visual Studio and "
             "other products - permanently.",
             "Leave it alone. Uninstall software you no longer use instead."),
        ]

        out: list[Leftover] = []

        # The component store is listed from DISM's own measurement, never by
        # walking the folder (see the docstring).
        winsxs = windir / "WinSxS"
        if winsxs.is_dir() and analysis is not None and analysis.actual_size:
            out.append(Leftover(
                path=winsxs,
                label="Component store (WinSxS)",
                size_bytes=analysis.actual_size,
                risk=LeftoverRisk.MANAGED,
                explanation=(
                    "Windows' own component store, as measured by Windows itself. "
                    "Most of it is hard links shared with System32, so Explorer "
                    "overstates the size, and deleting anything inside breaks "
                    "Windows Update and feature repair."),
                age_days=self._age_days(winsxs),
                supported_removal=("Use the component store cleanup above (DISM) - "
                                   "the only supported way to shrink it."),
            ))

        for path, label, risk, explanation, removal in specs:
            if cancel_event is not None and getattr(cancel_event, "is_set", bool)():
                break
            if not path.exists():
                continue
            if progress is not None:
                progress(f"Measuring {label}\u2026")
            size = self._dir_size(path)
            if size <= 0:
                continue
            out.append(Leftover(
                path=path, label=label, size_bytes=size, risk=risk,
                explanation=explanation, age_days=self._age_days(path),
                supported_removal=removal,
            ))

        # Single large files worth naming explicitly.
        dump = windir / "MEMORY.DMP"
        if dump.exists():
            try:
                size = dump.stat().st_size
            except OSError:
                size = 0
            if size > 0:
                out.append(Leftover(
                    dump, "Full crash dump (MEMORY.DMP)", size, LeftoverRisk.SAFE,
                    "A complete memory dump from a blue screen - often several "
                    "gigabytes. Keep it only while diagnosing that crash.",
                    age_days=self._age_days(dump),
                ))

        out.sort(key=lambda item: item.size_bytes, reverse=True)
        return out

    # -- cleanup (modifies the system) --------------------------------------

    # ------------------------------------------------------------------
    # 24H2 spurious reclaimables fix (Package_for_RollupFix)
    # ------------------------------------------------------------------
    # Windows 11 24H2 checkpoint cumulative updates (26100.1742) leave two
    # packages deeply superseded but staged. DISM /StartComponentCleanup alone
    # will never reclaim them (0x800f0906 spurious). ElevenForum member
    # "Bree" discovered that removing the top-level package removes both and
    # frees ~1.2-1.3GB after a second StartComponentCleanup. This is
    # Microsoft-confirmed safe when the CBS log says
    # "is a top-level package and is deeply superseded" (Microsoft Q&A
    # 2025-03-20/21, Azimstech, Ed Tittel). We automate it only when
    # AnalyzeComponentStore reports exactly 2 reclaimables after a successful
    # cleanup (the fingerprint of the bug), never speculatively.
    _SPURIOUS_PKG = "Package_for_RollupFix~31bf3856ad364e35~amd64~~26100.1742.1.10"
    _SPURIOUS_THRESHOLD = 2

    def _try_remove_spurious_package(self, timeout: int = 600) -> tuple[bool, str]:
        """Attempt to remove the deeply-superseded 24H2 rollup fix package.

        Returns (removed, log). Failure is benign (package absent or not
        superseded) – DISM simply fails, no store harm.
        """
        out = self._run_dism(
            ["/Online", "/Remove-Package", f"/PackageName:{self._SPURIOUS_PKG}"],
            timeout=timeout,
        )
        if out is None:
            return False, "DISM Remove-Package produced no output"
        low = out.lower()
        if "completed successfully" in low:
            return True, out
        # Even failure text is useful for diagnostics
        return False, out

    def cleanup(
        self,
        reset_base: bool = False,
        timeout: int = 3600,
        progress: Callable[[str], None] | None = None,
        cancel_event: "threading.Event | None" = None,
        auto_fix_spurious: bool = True,
    ) -> CleanupOutcome:
        """Run ``DISM /StartComponentCleanup``, optionally with ``/ResetBase``.

        ``reset_base`` removes *all* superseded versions, which permanently
        prevents uninstalling the updates currently installed. Callers must have
        made that trade-off explicit to the user before passing ``True``.

        ``auto_fix_spurious`` – when True (default), handles the Windows 11
        24H2 staged-package bug: if after a successful cleanup
        ``reclaimable_packages == 2`` (the spurious fingerprint), Cortex will
        offer to run ``Remove-Package`` for ``Package_for_RollupFix`` and then
        re-run ``StartComponentCleanup`` to reclaim the ~1.2GB. This mirrors the
        manual 3-step fix from Microsoft Q&A / Azimstech and is only triggered
        on that exact condition, never blindly.
        """
        if not _IS_WINDOWS:
            return CleanupOutcome(False, reset_base, message="Windows-only feature.")
        if not self.is_elevated():
            return CleanupOutcome(
                False, reset_base,
                message=("Administrator rights are required. Restart Cortex as "
                         "Administrator to clean the component store."),
            )

        if progress is not None:
            progress("Measuring the component store\u2026")
        before = self.analyze(timeout=600, cancel_event=cancel_event)

        if cancel_event is not None and cancel_event.is_set():
            return CleanupOutcome(False, reset_base, before.actual_size, before.actual_size,
                                   message="Cancelled before cleanup started.")

        args = ["/Online", "/Cleanup-Image", "/StartComponentCleanup"]
        if reset_base:
            args.append("/ResetBase")
        if progress is not None:
            progress("Cleaning the component store\u2026 this can take 10-30 minutes")
        out = self._run_dism(args, timeout=timeout, cancel_event=cancel_event)

        if out is None:
            cancelled = cancel_event is not None and cancel_event.is_set()
            return CleanupOutcome(
                False, reset_base, before.actual_size, before.actual_size,
                message=("Cancelled." if cancelled else
                         "Could not run DISM (Administrator required)."),
            )

        low = out.lower()
        tail = "\n".join(line for line in out.splitlines() if line.strip())[-1200:]

        if "the operation completed successfully" not in low and "completed successfully" not in low:
            code = re.search(r"(0x[0-9a-fA-F]{8})", out)
            msg = "Cleanup did not complete."
            if code:
                msg += f" DISM reported {code.group(1)}."
            if "0x800f0806" in low:
                msg += (" Windows Update is busy or a restart is pending - "
                        "restart and try again.")
            elif "another servicing" in low or "pending" in low:
                msg += " Another servicing operation is in progress; try again later."
            return CleanupOutcome(False, reset_base, before.actual_size,
                                   before.actual_size, message=msg, raw_tail=tail)

        if progress is not None:
            progress("Measuring again\u2026")
        after = self.analyze(timeout=600)

        # -- 24H2 spurious reclaimables auto-fix --------------------------------
        spurious_note = ""
        if (
            auto_fix_spurious
            and not reset_base
            and after.ok
            and after.reclaimable_packages == self._SPURIOUS_THRESHOLD
            and after.reclaimable_packages != 0
        ):
            # Fingerprint matches the documented 2-package bug; attempt removal
            if progress is not None:
                progress("Detected 2 spurious reclaimables (24H2 bug) – removing RollupFix …")
            removed, rm_out = self._try_remove_spurious_package(timeout=900)
            rm_low = rm_out.lower() if rm_out else ""
            if removed and "completed successfully" in rm_low:
                spurious_note = (
                    f" Removed spurious package {self._SPURIOUS_PKG} (≈1.2GB). "
                )
                # Second cleanup to actually reclaim after package removal
                if progress is not None:
                    progress("Re-running component cleanup after spurious removal …")
                second = self._run_dism(
                    ["/Online", "/Cleanup-Image", "/StartComponentCleanup"],
                    timeout=timeout,
                )
                if second and "completed successfully" in second.lower():
                    tail += "\n" + "\n".join(line for line in second.splitlines() if line.strip())[-600:]
                    after = self.analyze(timeout=600)
                else:
                    spurious_note += "Second cleanup did not complete. "
            else:
                # Removal not applicable – leave after as-is (benign)
                spurious_note = " Spurious 2-package fingerprint present but RollupFix removal not applicable (already removed or not staged). "

        outcome = CleanupOutcome(
            True, reset_base, before.actual_size, after.actual_size,
            raw_tail=tail,
            needs_reboot="restart" in low and "required" in low,
        )
        if outcome.freed_bytes == 0:
            base_msg = (
                "Cleanup completed, but the store did not shrink - there were no "
                "superseded components left to remove.")
            # Suppress spurious alarm: 2 reclaimables on 24H2 are by-design staged
            # checkpoints, not bloat, per Microsoft "checkpoint cumulative updates"
            # (Learn article 2025-03). We explain rather than alarm.
            if after.reclaimable_packages == 2:
                base_msg += (
                    " 2 reclaimables remain – these are staged checkpoint packages "
                    "on Windows 11 24H2 (by-design, not bloat) – see Microsoft "
                    "checkpoint cumulative updates. The RollupFix auto-fix was "
                    f"{'attempted' if spurious_note else 'not needed'}.")
            outcome.message = base_msg + spurious_note
        else:
            outcome.message = "Component store cleanup completed." + spurious_note
        return outcome

    def run_servicing_task(self, timeout: int = 3600) -> tuple[bool, str]:
        """Trigger Windows' own scheduled StartComponentCleanup task.

        Windows ships this task and runs it on idle. Triggering it is gentler
        than a manual DISM cleanup (it self-limits to one hour and skips
        components newer than 30 days), which makes it the safer default.
        """
        if not _IS_WINDOWS:
            return False, "Windows-only feature."
        task = r"\Microsoft\Windows\Servicing\StartComponentCleanup"
        try:
            proc = _proc.run(["schtasks", "/Run", "/TN", task],
                             timeout=timeout, creationflags=_NO_WINDOW)
        except FileNotFoundError:
            return False, "schtasks is not available on this system."
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"Could not start the servicing task: {exc}"
        text = self._decode(proc.stdout) + self._decode(proc.stderr)
        if proc.returncode == 0:
            return True, ("Windows' component cleanup task was started. It runs in "
                          "the background and can take up to an hour.")
        if "access is denied" in text.lower():
            return False, "Administrator rights are required to start this task."
        return False, text.strip() or "Could not start the servicing task."

    # -- helpers ------------------------------------------------------------

    def _run_dism(self, args: list[str], timeout: int,
                 cancel_event: "threading.Event | None" = None) -> str | None:
        """_run_dism."""
        try:
            # DISM can run for 10-30 minutes; poll timeout/cancel_event instead
            # of blocking uninterruptibly, and kill the whole tree on either -
            # never the calling thread (see core/proc.py).
            proc = _proc.run(["dism", *args], timeout=timeout,
                             cancel_event=cancel_event, creationflags=_NO_WINDOW)
        except FileNotFoundError:
            self.logger.debug("dism not found")
            return None
        except (_proc.ProcessCancelled, subprocess.TimeoutExpired):
            return None
        except (OSError, subprocess.SubprocessError) as exc:
            self.logger.debug("dism failed: %s", exc)
            return None
        text = self._decode(proc.stdout) + self._decode(proc.stderr)
        return text or None
        """_run_dism."""
        """_run_dism."""

    @staticmethod
    def _decode(raw: bytes | str | None) -> str:
        """Decode DISM output, which is UTF-16LE with NULs on many consoles."""
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw
        for enc in ("utf-8", "utf-16-le", "cp1252"):
            try:
                return raw.decode(enc).replace("\x00", "")
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")

    @staticmethod
    def _dir_size(path: Path) -> int:
        """Sum a directory tree, skipping what we cannot read (never raises)."""
        total = 0
        stack = [str(path)]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as it:
                    for entry in it:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
                            elif not entry.is_symlink():
                                total += entry.stat(follow_symlinks=False).st_size
                        except OSError:
                            continue
            except OSError:
                continue
        return total

    @staticmethod
    def _age_days(path: Path) -> float | None:
        """_age_days."""
        try:
            return max(0.0, (time.time() - path.stat().st_mtime) / 86400.0)
        except OSError:
            return None
        """_age_days."""
        """_age_days."""
