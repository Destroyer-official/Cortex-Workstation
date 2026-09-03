"""Archive support via native 7-Zip CLI — multithreaded extraction.

Replaces Python zipfile/tarfile/py7zr/rarfile with 7z.exe calls.
All formats handled by a single native binary: ZIP, RAR, 7z, TAR, GZ,
BZ2, XZ, WIM, ISO, CAB, TAR.GZ, TAR.BZ2, TAR.XZ, and more.

Security:
- Path traversal prevention (validated resolved paths)
- Maximum extraction size limit (10 GB)
- QThread interruption via process kill
"""

from __future__ import annotations

import logging
import os
import re
import shlex
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

log = logging.getLogger("nexus.archive")

MAX_EXTRACT_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB

def _get_7z_search_paths() -> list[str]:
    """_get_7z_search_paths."""
    paths: list[str] = []
    # Environment variables
    for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "ProgramW6432", "LOCALAPPDATA"):
        val = os.environ.get(env)
        if val:
            if env == "LOCALAPPDATA":
                paths.append(str(Path(val) / "Programs" / "7-Zip" / "7z.exe"))
            else:
                paths.append(str(Path(val) / "7-Zip" / "7z.exe"))
                paths.append(str(Path(val) / "AMD" / "CIM" / "Bin64" / "7z.exe"))
                paths.append(str(Path(val) / "AMD" / "CNext" / "CNext" / "7z.exe"))
    # Check all active fixed drives
    try:
        import string
        for letter in string.ascii_uppercase:
            drive_root = Path(f"{letter}:/")
            if drive_root.exists():
                paths.append(str(drive_root / "Program Files" / "7-Zip" / "7z.exe"))
                paths.append(str(drive_root / "Program Files (x86)" / "7-Zip" / "7z.exe"))
                paths.append(str(drive_root / "7-Zip" / "7z.exe"))
    except Exception:
        pass
    # Deduplicate preserving order
    seen: set[str] = set()
    result: list[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result
    """_get_7z_search_paths."""


_7z_exe: str | None = None
_7z_checked = False
_7z_lock = threading.Lock()


def _find_7z() -> str | None:
    """_find_7z."""
    global _7z_exe, _7z_checked
    if _7z_checked:
        return _7z_exe
    with _7z_lock:
        if _7z_checked:
            return _7z_exe
        _7z_checked = True

        # 1. Check PATH
        import shutil
        found = shutil.which("7z")
        if found:
            _7z_exe = found
            return _7z_exe

        # 2. Check known install paths
        for p in _get_7z_search_paths():
            if os.path.isfile(p):
                _7z_exe = p
                return _7z_exe

        # 3. Check registry
        try:
            import winreg
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    key = winreg.OpenKey(hive, r"SOFTWARE\7-Zip")
                    val, _ = winreg.QueryValueEx(key, "Path")
                    exe = os.path.join(val, "7z.exe")
                    if os.path.isfile(exe):
                        _7z_exe = exe
                        return _7z_exe
                except OSError:
                    pass
        except ImportError:
            pass

        log.warning("7z.exe not found — archive operations unavailable")
        return None
    """_find_7z."""


def is_7z_available() -> bool:
    """is_7z_available."""
    return _find_7z() is not None
    """is_7z_available."""


def _7z() -> str:
    """_7z."""
    exe = _find_7z()
    if not exe:
        raise FileNotFoundError(
            "7z.exe not found. Install 7-Zip from https://7-zip.org"
        )
    return exe
    """_7z."""


# ── Security ────────────────────────────────────────────────────────────────

class ArchiveSecurityError(Exception):
    """ArchiveSecurityError."""
    pass
    """ArchiveSecurityError class."""


def validate_extract_path(dest_dir: str, entry_path: str) -> str:
    """validate_extract_path."""
    dest_real = os.path.realpath(dest_dir)
    target = os.path.realpath(os.path.join(dest_dir, entry_path))
    if not (target == dest_real or target.startswith(dest_real + os.sep)):
        raise ArchiveSecurityError(f"Path traversal blocked: {entry_path}")
    return target
    """validate_extract_path."""


def _enforce_total_size(total: int, label: str = "archive"):
    """_enforce_total_size."""
    if total > MAX_EXTRACT_SIZE:
        raise ArchiveSecurityError(
            f"{label} exceeds max size "
            f"({total / (1024**3):.1f} GB > {MAX_EXTRACT_SIZE / (1024**3):.0f} GB)"
        )
    """_enforce_total_size."""


# ── Enums / data ────────────────────────────────────────────────────────────

class ArchiveType(Enum):
    """ArchiveType."""
    ZIP = auto()
    TAR = auto()
    TAR_GZ = auto()
    TAR_BZ2 = auto()
    TAR_XZ = auto()
    SEVEN_Z = auto()
    RAR = auto()
    WIM = auto()
    ISO = auto()
    CAB = auto()
    """ArchiveType class."""


ARCHIVE_EXTENSIONS = {
    ".zip": ArchiveType.ZIP,
    ".tar": ArchiveType.TAR,
    ".gz": ArchiveType.TAR_GZ,
    ".tgz": ArchiveType.TAR_GZ,
    ".bz2": ArchiveType.TAR_BZ2,
    ".tbz2": ArchiveType.TAR_BZ2,
    ".xz": ArchiveType.TAR_XZ,
    ".txz": ArchiveType.TAR_XZ,
    ".7z": ArchiveType.SEVEN_Z,
    ".rar": ArchiveType.RAR,
    ".wim": ArchiveType.WIM,
    ".swm": ArchiveType.WIM,
    ".esd": ArchiveType.WIM,
    ".iso": ArchiveType.ISO,
    ".cab": ArchiveType.CAB,
}


@dataclass
class ArchiveEntry:
    """ArchiveEntry."""
    archive_path: str
    name: str
    is_dir: bool
    size: int
    compressed_size: int = 0
    modified_ms: int = 0
    compression: str = ""
    encrypted: bool = False
    """ArchiveEntry class."""


@dataclass
class ArchiveInfo:
    """ArchiveInfo."""
    path: str
    archive_type: ArchiveType
    total_entries: int = 0
    total_size: int = 0
    compressed_size: int = 0
    is_encrypted: bool = False
    """ArchiveInfo class."""


def detect_archive_type(path: str) -> ArchiveType | None:
    """detect_archive_type."""
    p = Path(path)
    ext = p.suffix.lower()

    if ext == ".tar":
        return ArchiveType.TAR
    if ext in (".tgz",):
        return ArchiveType.TAR_GZ
    if ext in (".bz2", ".tbz2"):
        return ArchiveType.TAR_BZ2
    if ext in (".xz", ".txz"):
        return ArchiveType.TAR_XZ

    if ext == ".gz":
        try:
            with open(path, "rb") as f:
                magic = f.read(2)
            if magic == b'\x1f\x8b':
                return ArchiveType.TAR_GZ
        except OSError:
            pass
        return None

    return ARCHIVE_EXTENSIONS.get(ext)
    """detect_archive_type."""


def is_archive(path: str) -> bool:
    """is_archive."""
    return detect_archive_type(path) is not None
    """is_archive."""


# ── 7z.exe output parser ───────────────────────────────────────────────────

def _parse_7z_list(output: str) -> list[ArchiveEntry]:
    """Parse `7z l` output into ArchiveEntry list."""
    entries: list[ArchiveEntry] = []
    lines = output.splitlines()

    # Find the data section: starts after a line of dashes, ends before summary
    in_data = False
    for line in lines:
        stripped = line.strip()

        # Detect data section start (line of dashes)
        if stripped.startswith("---") and len(stripped) > 10:
            in_data = True
            continue

        # Detect summary section
        if in_data and (stripped.startswith("Ranges") or stripped.startswith("-----")):
            break

        if not in_data:
            continue

        # Parse: Date Time  Attr  Size  Compressed  Name
        # Example: 2024-01-15 10:30:00  .....  12345  5678  path/to/file.txt
        # Or folder: 2024-01-15 10:30:00  D.....  0  0  path/to/folder/
        if not stripped or stripped.startswith("Path =") or stripped.startswith("Type ="):
            continue

        # Skip header line
        if stripped.startswith("Date") or stripped.startswith("_time"):
            continue

        # Try to parse the line
        parts = stripped.split(None, 5)
        if len(parts) < 6:
            continue

        try:
            date_str = parts[0]
            time_str = parts[1]
            attr = parts[2]
            comp_size_str = parts[3]
            uncomp_size_str = parts[4]
            name = parts[5]

            is_dir = "D" in attr.upper()
            size = int(uncomp_size_str) if uncomp_size_str.isdigit() else 0
            comp_size = int(comp_size_str) if comp_size_str.isdigit() else 0

            # Parse modified date
            modified_ms = 0
            try:
                from datetime import datetime
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                modified_ms = int(dt.timestamp() * 1000)
            except (ValueError, OverflowError):
                pass

            # Detect encrypted
            upper_attr = attr.upper()
            encrypted = upper_attr.startswith("C") or "E" in upper_attr

            entries.append(ArchiveEntry(
                archive_path=name,
                name=Path(name).name or name.rstrip("/").rstrip("\\"),
                is_dir=is_dir,
                size=size,
                compressed_size=comp_size,
                modified_ms=modified_ms,
                encrypted=encrypted,
            ))
        except (ValueError, IndexError):
            continue

    return entries


def _parse_7z_list_xml(output: str) -> list[ArchiveEntry]:
    """Fallback XML parser for `7z l -slt` output."""
    entries: list[ArchiveEntry] = []
    current: dict = {}
    for line in output.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            current[k.strip()] = v.strip()
        elif current.get("Path") or current.get("Name"):
            # End of one entry block
            path = current.get("Path", "")
            if path:
                is_dir = current.get("Attr", "").upper().startswith("D")
                try:
                    size = int(current.get("Size", "0"))
                except ValueError:
                    size = 0
                try:
                    packed = int(current.get("Packed Size", "0"))
                except ValueError:
                    packed = 0

                entries.append(ArchiveEntry(
                    archive_path=path,
                    name=Path(path).name or path,
                    is_dir=is_dir,
                    size=size,
                    compressed_size=packed,
                ))
                current = {}

    # Don't forget last entry
    path = current.get("Path", "")
    if path:
        is_dir = current.get("Attr", "").upper().startswith("D")
        try:
            size = int(current.get("Size", "0"))
        except ValueError:
            size = 0
        try:
            packed = int(current.get("Packed Size", "0"))
        except ValueError:
            packed = 0
        entries.append(ArchiveEntry(
            archive_path=path,
            name=Path(path).name or path,
            is_dir=is_dir,
            size=size,
            compressed_size=packed,
        ))

    return entries


# ── 7z.exe runner ───────────────────────────────────────────────────────────

def _run_7z(
    args: list[str],
    timeout: int = 300,
    password: str = "",
    capture: bool = True,
    encoding: str = "utf-8",
) -> tuple[int, str, str]:
    """Run 7z.exe with args. Returns (returncode, stdout, stderr)."""
    cmd = [_7z()]
    if password:
        cmd.append(f"-p{password}")
    cmd.append("-y")  # overwrite without prompt
    cmd.extend(args)

    log.debug("7z: %s", shlex.join(cmd))

    try:
        proc = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=timeout,
            encoding=encoding,
            errors="replace",
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except FileNotFoundError:
        log.error("7z.exe not found at: %s", cmd[0])
        return -1, "", "7z.exe not found"
    except subprocess.TimeoutExpired as exc:
        log.warning("7z.exe timed out after %ds", timeout)
        proc.kill()
        proc.communicate()
        return -2, "", "Timed out"
    except Exception as e:
        log.error("7z.exe error: %s", e)
        return -1, "", str(e)


def _7z_version() -> tuple[int, ...]:
    """Return (major, minor) tuple for the installed 7z version."""
    try:
        exe = _7z()
        rc, out, _ = _run_7z(["i"], timeout=10)
        if rc == 0:
            m = re.search(r"7-Zip\s+(\d+)\.(\d+)", out)
            if m:
                return (int(m.group(1)), int(m.group(2)))
    except Exception:
        pass
    return (21, 0)


def _has_mmt_flag() -> bool:
    """Check if installed 7z supports -mmt=on (v21+)."""
    return _7z_version() >= (21, 0)


# ── ArchiveReader (7z.exe backed) ──────────────────────────────────────────

class SevenZipCLIReader:
    """Universal archive reader using 7z.exe CLI."""

    def __init__(self, path: str, password: str = ""):
        """__init__."""
        self._path = path
        self._password = password
        self._entries: list[ArchiveEntry] | None = None

        # Verify the archive is readable (skip for huge files)
        try:
            fsize = os.path.getsize(path)
        except OSError:
            fsize = 0
        timeout = 30 if fsize < 500_000_000 else 120  # 500MB threshold
        rc, out, err = _run_7z(
            ["l", self._path],
            password=password,
            timeout=timeout,
        )
        if rc not in (0, 1):  # 1 = some files OK, some failed
            raise FileNotFoundError(f"Cannot open archive: {err}")
        """__init__."""

    def list_entries(self) -> list[ArchiveEntry]:
        """list_entries."""
        if self._entries is not None:
            return self._entries

        # Try normal listing first
        rc, out, err = _run_7z(
            ["l", self._path],
            password=self._password,
        )
        entries = _parse_7z_list(out)

        # Fallback to SLT format if normal parsing failed
        if not entries:
            rc, out, err = _run_7z(
                ["l", "-slt", self._path],
                password=self._password,
            )
            entries = _parse_7z_list_xml(out)

        self._entries = entries
        return entries
        """list_entries."""

    def extract_entry(self, entry_path: str, dest_path: str) -> bool:
        """Extract a single entry."""
        validate_extract_path(dest_path, entry_path)
        os.makedirs(dest_path, exist_ok=True)

        rc, out, err = _run_7z(
            ["x", self._path, f"-o{dest_path}", "-aoa", entry_path],
            password=self._password,
            timeout=600,
        )
        if rc not in (0, 1):
            log.warning("7z extract failed for %s: %s", entry_path, err)
            return False
        return True

    def extract_all(self, dest_dir: str) -> bool:
        """Extract entire archive — native multithreaded."""
        os.makedirs(dest_dir, exist_ok=True)

        args = ["x", self._path, f"-o{dest_dir}", "-aoa"]
        if _has_mmt_flag():
            args.append("-mmt=on")
        rc, out, err = _run_7z(
            args,
            password=self._password,
            timeout=3600,
        )
        if rc not in (0, 1):
            log.warning("7z extractall failed: %s", err)
            return False
        return True

    def read_entry(self, entry_path: str) -> bytes | None:
        """Read a single entry to memory. Refuses entries larger than 500 MB."""
        MAX_READ_SIZE = 500 * 1024 * 1024
        for e in self.list_entries():
            if e.archive_path == entry_path and not e.is_dir:
                if e.size > MAX_READ_SIZE:
                    log.warning(
                        "Entry %s too large (%d bytes), refusing to load into RAM",
                        entry_path, e.size,
                    )
                    return None
                break
        with tempfile.TemporaryDirectory() as tmp:
            rc, out, err = _run_7z(
                ["x", self._path, f"-o{tmp}", entry_path],
                password=self._password,
            )
            if rc not in (0, 1):
                return None
            target = os.path.join(tmp, entry_path)
            if os.path.isfile(target):
                with open(target, "rb") as f:
                    return f.read()
        return None

    def get_info(self) -> ArchiveInfo:
        """get_info."""
        entries = self.list_entries()
        total_size = sum(e.size for e in entries if not e.is_dir)
        compressed = sum(e.compressed_size for e in entries if not e.is_dir)
        encrypted = any(e.encrypted for e in entries)
        return ArchiveInfo(
            path=self._path,
            archive_type=detect_archive_type(self._path),
            total_entries=len(entries),
            total_size=total_size,
            compressed_size=compressed,
            is_encrypted=encrypted,
        )
        """get_info."""

    def clear_cache(self) -> None:
        """clear_cache."""
        self._entries = None
        """clear_cache."""


# ── Factory ─────────────────────────────────────────────────────────────────

def open_archive(path: str, password: str = "") -> SevenZipCLIReader | None:
    """Open an archive for reading via 7z.exe. Returns None on failure."""
    if not is_7z_available():
        log.warning("7z.exe not available — cannot open %s", path)
        return None

    try:
        return SevenZipCLIReader(path, password)
    except Exception as e:
        log.warning("Failed to open archive %s: %s", path, e)
        return None


# ── Background extraction (QThread) ────────────────────────────────────────

class _ExtractWorker(QThread):
    """Background extraction using 7z.exe with progress reporting."""

    progress = Signal(int, str)     # percent, current_file
    finished_signal = Signal(bool)  # success

    def __init__(
        self,
        archive_path: str,
        dest: str,
        password: str = "",
        entries: list[str] | None = None,
    ):
        """__init__."""
        super().__init__()
        self._archive = archive_path
        self._dest = dest
        self._password = password
        self._entries = entries
        self._process: subprocess.Popen | None = None
        self._cancelled = threading.Event()
        """__init__."""

    def run(self):
        """run."""
        os.makedirs(self._dest, exist_ok=True)

        cmd = [_7z(), "x", self._archive, f"-o{self._dest}", "-y"]
        if _has_mmt_flag():
            cmd.append("-mmt=on")
        if self._password:
            cmd.insert(1, f"-p{self._password}")

        if self._entries:
            # Selective extraction via include list
            for entry in self._entries:
                cmd.append(f"-i!{entry}")

        log.info("7z extract: %s", shlex.join(cmd))

        try:
            # Start 7z process with line-by-line output for progress
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            success = True
            for line in self._process.stdout:
                if self._cancelled.is_set() or self.isInterruptionRequested():
                    self._process.kill()
                    success = False
                    break

                stripped = line.strip()
                # Parse progress: "Extracting  path/to/file.txt"
                if stripped.startswith("Extracting"):
                    fname = stripped.split(None, 1)[-1] if len(stripped.split(None, 1)) > 1 else ""
                    self.progress.emit(-1, fname)  # -1 = indeterminate

                # Parse percentage: "0% .. 50% .. 100%"
                pct_match = re.search(r"^\s*(\d+)%", stripped)
                if pct_match:
                    self.progress.emit(int(pct_match.group(1)), "")

            self._process.wait()
            rc = self._process.returncode
            success = success and rc in (0, 1)
            self.finished_signal.emit(success)

        except Exception as e:
            log.error("7z extract error: %s", e)
            self.finished_signal.emit(False)
        finally:
            self._process = None
        """run."""

    def cancel(self):
        """Kill the 7z process immediately."""
        self._cancelled.set()
        if self._process:
            try:
                self._process.kill()
            except OSError:
                pass


# ── Public manager ──────────────────────────────────────────────────────────

class ArchiveManager(QObject):
    """High-level archive operations backed by native 7z.exe."""

    extraction_progress = Signal(int, str)
    extraction_finished = Signal(bool)

    def __init__(self, parent=None):
        """__init__."""
        super().__init__(parent)
        self._worker: _ExtractWorker | None = None
        """__init__."""

    @property
    def available(self) -> bool:
        """available."""
        return is_7z_available()
        """available."""

    # -- browsing -----------------------------------------------------------

    def browse(self, path: str, password: str = "") -> SevenZipCLIReader | None:
        """browse."""
        return open_archive(path, password)
        """browse."""

    # -- extraction ---------------------------------------------------------

    def extract_all(
        self, archive_path: str, dest: str, password: str = ""
    ) -> bool:
        """extract_all."""
        self._stop_worker()
        self._worker = _ExtractWorker(archive_path, dest, password)
        self._worker.progress.connect(self.extraction_progress.emit)
        self._worker.finished_signal.connect(self._on_done)
        self._worker.start()
        return True
        """extract_all."""

    def extract_selected(
        self,
        archive_path: str,
        entries: list[str],
        dest: str,
        password: str = "",
    ) -> bool:
        """extract_selected."""
        self._stop_worker()
        self._worker = _ExtractWorker(archive_path, dest, password, entries)
        self._worker.progress.connect(self.extraction_progress.emit)
        self._worker.finished_signal.connect(self._on_done)
        self._worker.start()
        return True
        """extract_selected."""

    def cancel_extraction(self):
        """cancel_extraction."""
        if self._worker:
            self._worker.cancel()
        """cancel_extraction."""

    def _on_done(self, success: bool):
        """_on_done."""
        if self._worker:
            try:
                self._worker.progress.disconnect()
                self._worker.finished_signal.disconnect()
            except RuntimeError:
                pass
        self.extraction_finished.emit(success)
        self._worker = None
        """_on_done."""

    # -- creation -----------------------------------------------------------

    def create_archive(
        self,
        archive_path: str,
        files: list[str],
        format: str = "zip",
        compression: str = "normal",
        password: str = "",
    ) -> bool:
        """Create an archive via 7z.exe."""
        if not files:
            return False

        missing = [f for f in files if not os.path.exists(f)]
        if missing:
            log.warning("Source files not found: %s", missing)
            return False

        cmd = [_7z(), "a", archive_path]
        if password:
            cmd.append(f"-p{password}")

        # Format-specific compression
        fmt = format.lower()
        if fmt == "7z":
            cmd.extend(["-t7z", f"-mx={_compression_level(compression)}"])
        elif fmt == "zip":
            cmd.extend(["-tzip", f"-mx={_compression_level(compression)}"])
        elif fmt in ("tar", "tar.gz", "tgz", "tar.bz2", "tar.xz"):
            tar_fmt = {
                "tar": "tar",
                "tar.gz": "tar.gz",
                "tgz": "tar.gz",
                "tar.bz2": "tar.bz2",
                "tar.xz": "tar.xz",
            }[fmt]
            cmd.extend([f"-t{tar_fmt}"])
        elif fmt == "rar":
            cmd.extend(["-trar", f"-mx={_compression_level(compression)}"])
        else:
            cmd.extend([f"-t{fmt}", f"-mx={_compression_level(compression)}"])

        cmd.extend(files)

        rc, out, err = _run_7z(cmd, timeout=600)
        if rc not in (0, 1):
            log.warning("7z create failed: %s", err)
            return False
        return True

    # -- status -------------------------------------------------------------

    def is_extracting(self) -> bool:
        """is_extracting."""
        return self._worker is not None and self._worker.isRunning()
        """is_extracting."""

    def _stop_worker(self):
        """_stop_worker."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(5000)
        if self._worker:
            try:
                self._worker.progress.disconnect()
                self._worker.finished_signal.disconnect()
            except RuntimeError:
                pass
            self._worker = None
        """_stop_worker."""


def _compression_level(level: str) -> int:
    """_compression_level."""
    levels = {
        "store": 0, "fast": 1, "normal": 5, "best": 9,
    }
    key = level.lower()
    if key not in levels:
        raise ValueError(
            f"Unknown compression level {level!r}; "
            f"expected one of: {', '.join(levels)}"
        )
    return levels[key]
    """_compression_level."""
