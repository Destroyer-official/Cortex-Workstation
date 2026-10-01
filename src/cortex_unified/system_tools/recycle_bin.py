"""Cortex Cleaner — Recycle Bin measurer & emptier.

Every cleaner in this app moves files *to* the Recycle Bin (reversible), but
nothing could show the bin's size or empty it in one place — so cleaned space
was never actually freed. This module closes that loop:

- ``measure()`` walks ``$RECYCLE.BIN`` on every fixed drive (Windows) or
  ``~/.local/share/Trash`` (POSIX) and reports bytes + item counts.
- ``empty()`` permanently empties the bin via ``SHEmptyRecycleBinW`` (Windows,
  no confirmation UI of its own — callers confirm first) or by removing the
  contents of the freedesktop Trash dirs (POSIX). ``dry_run=True`` reports
  what *would* be freed without touching anything.

Emptying is irreversible by nature: it is always opt-in behind its own
confirmation dialog and is never part of any "clean everything" sweep.
"""

from __future__ import annotations

import logging
import os
import shutil
import string
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("cortex.system_tools.recycle_bin")

#: Flags for SHEmptyRecycleBinW (shell32).
_SHERB_NOCONFIRMATION = 0x00000001
_SHERB_NOPROGRESSUI = 0x00000002
_SHERB_NOSOUND = 0x00000004


@dataclass
class RecycleBinDrive:
    """Per-drive Recycle Bin usage."""

    drive: str
    size_bytes: int = 0
    item_count: int = 0


@dataclass
class RecycleBinReport:
    """Result of measuring the Recycle Bin across all drives."""

    drives: list[RecycleBinDrive] = field(default_factory=list)
    error: str | None = None

    @property
    def total_bytes(self) -> int:
        """Total bytes held in the bin across all drives."""
        return sum(d.size_bytes for d in self.drives)

    @property
    def total_items(self) -> int:
        """Total items held in the bin across all drives."""
        return sum(d.item_count for d in self.drives)


@dataclass
class RecycleBinEmptyResult:
    """Outcome of emptying the Recycle Bin."""

    emptied: bool = False
    freed_bytes: int = 0
    message: str = ""


def _fixed_drive_roots() -> list[Path]:
    """Return existing ``X:\\`` drive roots (Windows) or ``[/]`` (POSIX)."""
    if os.name != "nt":
        return [Path("/")]
    roots: list[Path] = []
    for letter in string.ascii_uppercase:
        drive = Path(f"{letter}:\\")
        try:
            if drive.is_dir():
                roots.append(drive)
        except OSError:
            continue
    return roots


def _bin_dirs_for(root: Path, extra_roots: list[Path] | None = None) -> list[Path]:
    """Candidate bin directories for one drive root (plus test overrides)."""
    candidates = [root / "$RECYCLE.BIN"]
    if extra_roots:
        candidates.extend(extra_roots)
    if os.name != "nt":
        candidates.append(Path.home() / ".local" / "share" / "Trash" / "files")
    return [c for c in candidates if c.is_dir()]


def _dir_size(path: Path) -> tuple[int, int]:
    """Return ``(bytes, file_count)`` under *path* without following links."""
    total = 0
    count = 0
    stack: list[Path] = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                            count += 1
                    except OSError:
                        continue
        except OSError:
            continue
    return total, count


class RecycleBinManager:
    """Measure and empty the OS Recycle Bin / Trash."""

    def measure(self, roots: list[Path] | None = None) -> RecycleBinReport:
        """Measure bin usage per drive; read-only, never raises on IO issues.

        Args:
            roots: Optional drive roots to measure (defaults to all fixed
                drives). Exposed so tests can point at scratch directories.
        """
        report = RecycleBinReport()
        try:
            drive_roots = list(roots) if roots is not None else _fixed_drive_roots()
        except OSError as exc:
            report.error = str(exc)
            return report
        for drive_root in drive_roots:
            size, count = 0, 0
            for bin_dir in _bin_dirs_for(drive_root):
                try:
                    sub_size, sub_count = _dir_size(bin_dir)
                except OSError:
                    continue
                size += sub_size
                count += sub_count
            if size or count:
                report.drives.append(RecycleBinDrive(drive=str(drive_root), size_bytes=size, item_count=count))
        return report

    def empty(self, dry_run: bool = True) -> RecycleBinEmptyResult:
        """Empty the bin on all drives (or preview with ``dry_run=True``).

        Always measures first so the result reports the bytes that were (or
        would be) freed. Real emptying on Windows goes through
        ``SHEmptyRecycleBinW`` with no-confirmation/no-UI flags; on POSIX it
        removes ``Trash/files`` and ``Trash/info`` contents.
        """
        before = self.measure()
        if dry_run:
            return RecycleBinEmptyResult(
                emptied=False,
                freed_bytes=before.total_bytes,
                message=f"Dry run: {before.total_items:,} item(s) would be permanently removed.",
            )
        if os.name == "nt":
            return self._empty_windows(before)
        return self._empty_posix(before)

    def _empty_windows(self, before: RecycleBinReport) -> RecycleBinEmptyResult:
        """Empty all Windows recycle bins via the Shell API."""
        try:
            import ctypes

            flags = _SHERB_NOCONFIRMATION | _SHERB_NOPROGRESSUI | _SHERB_NOSOUND
            shell32 = ctypes.windll.shell32  # type: ignore[attr-defined]
            hresult = shell32.SHEmptyRecycleBinW(None, None, flags)
            if hresult != 0:
                return RecycleBinEmptyResult(
                    emptied=False,
                    freed_bytes=0,
                    message=f"Windows refused to empty the Recycle Bin (HRESULT {hresult}).",
                )
        except Exception as exc:  # noqa: BLE001 - report, don't crash the batch
            logger.error("emptying Recycle Bin failed: %s", exc)
            return RecycleBinEmptyResult(emptied=False, freed_bytes=0, message=f"Empty failed: {exc}")
        after = self.measure()
        freed = max(0, before.total_bytes - after.total_bytes)
        return RecycleBinEmptyResult(
            emptied=True,
            freed_bytes=freed,
            message=f"Recycle Bin emptied ({after.total_items:,} item(s) remain).",
        )

    def _empty_posix(self, before: RecycleBinReport) -> RecycleBinEmptyResult:
        """Empty freedesktop Trash contents on POSIX hosts."""
        trash = Path.home() / ".local" / "share" / "Trash"
        for sub in ("files", "info"):
            target = trash / sub
            if not target.is_dir():
                continue
            try:
                for child in target.iterdir():
                    try:
                        if child.is_dir() and not child.is_symlink():
                            shutil.rmtree(child, ignore_errors=True)
                        else:
                            child.unlink(missing_ok=True)
                    except OSError:
                        continue
            except OSError as exc:
                return RecycleBinEmptyResult(emptied=False, freed_bytes=0, message=f"Empty failed: {exc}")
        after = self.measure()
        freed = max(0, before.total_bytes - after.total_bytes)
        return RecycleBinEmptyResult(emptied=True, freed_bytes=freed, message="Trash emptied.")
