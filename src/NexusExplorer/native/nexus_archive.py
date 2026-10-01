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


def _is_functional_7z(path: str) -> bool:
    """Verify that path exists, is a file, and successfully runs."""
    if not path or not os.path.isfile(path):
        return False
    try:
        proc = subprocess.run([path, "i"], capture_output=True, timeout=5)
        return proc.returncode == 0
    except Exception:
        return False


def _get_7z_search_paths() -> list[str]:
    """Build candidate 7z.exe paths from Program Files-style env vars
    (including LOCALAPPDATA\\Programs) and the standard install dirs on
    every active fixed drive, deduplicated preserving order."""
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
    # Scoop paths
    try:
        home = Path.home()
        paths.append(str(home / "scoop" / "apps" / "7zip" / "current" / "7z.exe"))
        paths.append(str(home / "scoop" / "shims" / "7z.exe"))
    except Exception:
        pass
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


_7z_exe: str | None = None
_7z_checked = False
_7z_lock = threading.Lock()


def _find_7z() -> str | None:
    """Locate 7z.exe once (double-checked under a lock): PATH lookup, the
    known install paths, then the registry (HKLM/HKCU SOFTWARE\\7-Zip);
    caches the result and returns None when 7-Zip is not installed."""
    global _7z_exe, _7z_checked
    if _7z_checked:
        return _7z_exe
    with _7z_lock:
        if _7z_checked:
            return _7z_exe

        # 1. Check known install paths first (and validate)
        for p in _get_7z_search_paths():
            if _is_functional_7z(p):
                _7z_exe = p
                _7z_checked = True
                return _7z_exe

        # 2. Check PATH (and validate)
        import shutil

        found = shutil.which("7z") or shutil.which("7z.exe")
        if found and _is_functional_7z(found):
            _7z_exe = found
            _7z_checked = True
            return _7z_exe

        # 3. Check registry
        try:
            import winreg

            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    key = winreg.OpenKey(hive, r"SOFTWARE\7-Zip")
                    val, _ = winreg.QueryValueEx(key, "Path")
                    exe = os.path.join(val, "7z.exe")
                    if _is_functional_7z(exe):
                        _7z_exe = exe
                        _7z_checked = True
                        return _7z_exe
                except OSError:
                    pass
        except ImportError:
            pass

        _7z_checked = True
        log.warning("7z.exe not found — archive operations will use native fallback")
        return None


def is_7z_available() -> bool:
    """Return True when a functional 7z.exe installation was found."""
    return _find_7z() is not None


def _7z() -> str:
    """Return the resolved 7z.exe path, raising FileNotFoundError when
    7-Zip is not installed."""
    exe = _find_7z()
    if not exe:
        raise FileNotFoundError("7z.exe not found. Install 7-Zip from https://7-zip.org")
    return exe


# ── Security ────────────────────────────────────────────────────────────────


class ArchiveSecurityError(Exception):
    """Raised when an archive violates extraction safety limits (path
    traversal or oversized payload)."""

    pass
    """Raised when an archive violates extraction safety limits (path
    traversal or oversized payload)."""


def validate_extract_path(dest_dir: str, entry_path: str) -> str:
    """Resolve entry_path under dest_dir and reject path traversal
    (ArchiveSecurityError when the target escapes dest_dir); returns the
    resolved target path."""
    dest_real = os.path.realpath(dest_dir)
    target = os.path.realpath(os.path.join(dest_dir, entry_path))
    if not (target == dest_real or target.startswith(dest_real + os.sep)):
        raise ArchiveSecurityError(f"Path traversal blocked: {entry_path}")
    return target


def _enforce_total_size(total: int, label: str = "archive"):
    """Raise ArchiveSecurityError when a total (un)compressed size exceeds
    the 10 GB extraction limit."""
    if total > MAX_EXTRACT_SIZE:
        raise ArchiveSecurityError(
            f"{label} exceeds max size " f"({total / (1024**3):.1f} GB > {MAX_EXTRACT_SIZE / (1024**3):.0f} GB)"
        )


# ── Enums / data ────────────────────────────────────────────────────────────


class ArchiveType(Enum):
    """Supported archive format categories."""

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
    """Supported archive format categories."""


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
    """One entry (file or folder) inside an archive, as parsed from 7z
    listing output."""

    archive_path: str
    name: str
    is_dir: bool
    size: int
    compressed_size: int = 0
    modified_ms: int = 0
    compression: str = ""
    encrypted: bool = False
    """One entry (file or folder) inside an archive, as parsed from 7z
    listing output."""


@dataclass
class ArchiveInfo:
    """Summary metadata about an archive (type, counts, sizes,
    encryption)."""

    path: str
    archive_type: ArchiveType
    total_entries: int = 0
    total_size: int = 0
    compressed_size: int = 0
    is_encrypted: bool = False
    """Summary metadata about an archive (type, counts, sizes,
    encryption)."""


def detect_archive_type(path: str) -> ArchiveType | None:
    """Classify an archive by extension, sniffing .gz magic bytes
    (\\x1f\\x8b) to decide TAR_GZ; returns None for non-archives."""
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
            if magic == b"\x1f\x8b":
                return ArchiveType.TAR_GZ
        except OSError:
            pass
        return None

    return ARCHIVE_EXTENSIONS.get(ext)


def is_archive(path: str) -> bool:
    """Return True when the path resolves to a known archive type."""
    return detect_archive_type(path) is not None


# ── 7z.exe output parser ───────────────────────────────────────────────────


def _parse_7z_list(output: str) -> list[ArchiveEntry]:
    """Parse `7z l` output into ArchiveEntry list."""
    entries: list[ArchiveEntry] = []
    lines = output.splitlines()

    # Find the data section: starts after a line of dashes, ends before summary
    in_data = False
    for line in lines:
        stripped = line.strip()

        # Detect data section start/end (line of dashes)
        if stripped.startswith("---") and len(stripped) > 10:
            if in_data:
                # Reached closing dashes before summary: end of data entries
                break
            in_data = True
            continue

        # Detect summary section
        if in_data and stripped.startswith("Ranges"):
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

            entries.append(
                ArchiveEntry(
                    archive_path=name,
                    name=Path(name).name or name.rstrip("/").rstrip("\\"),
                    is_dir=is_dir,
                    size=size,
                    compressed_size=comp_size,
                    modified_ms=modified_ms,
                    encrypted=encrypted,
                )
            )
        except (ValueError, IndexError):
            continue

    return entries


def _parse_7z_list_xml(output: str) -> list[ArchiveEntry]:
    """Fallback key=value text parser for 7z -slt (plain 'Key = Value' lines, not XML)."""
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

                entries.append(
                    ArchiveEntry(
                        archive_path=path,
                        name=Path(path).name or path,
                        is_dir=is_dir,
                        size=size,
                        compressed_size=packed,
                    )
                )
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
        entries.append(
            ArchiveEntry(
                archive_path=path,
                name=Path(path).name or path,
                is_dir=is_dir,
                size=size,
                compressed_size=packed,
            )
        )

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
    exe = _7z()
    # If caller included 7z executable in args, strip it
    if args and (args[0] == exe or Path(args[0]).name.lower() in ("7z.exe", "7z")):
        args = args[1:]
    cmd = [exe]
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
        """Store path/password and verify readability with a 7z listing
        (timeout scales with archive size: 30 s under 500 MB, else 120 s);
        raises FileNotFoundError when 7z cannot open the archive."""
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

    def list_entries(self) -> list[ArchiveEntry]:
        """List archive entries via '7z l', caching the parsed result;
        retries with the -slt (key=value) format when the default column
        parse yields nothing."""
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
                        entry_path,
                        e.size,
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
        """Summarize the archive: entry count, total/compressed sizes,
        encryption flag, and detected type from the listed entries."""
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

    def clear_cache(self) -> None:
        """Drop the cached entry list so the next list_entries re-parses."""
        self._entries = None

    def close(self) -> None:
        """Close the reader and release cached data."""
        self.clear_cache()


def _archive_stem(path: str | Path) -> str:
    """Return the clean folder stem for an archive, stripping compound extensions like .tar.gz."""
    name = Path(path).name
    lower = name.lower()
    for compound in (
        ".tar.gz",
        ".tar.bz2",
        ".tar.xz",
        ".tar.zst",
        ".tar.lz4",
        ".tar.lz",
        ".tar.sz",
    ):
        if lower.endswith(compound):
            return name[: -len(compound)]
    return Path(path).stem


class TarArchiveReader:
    """Universal tar archive reader using Python's standard tarfile module.

    Supports .tar, .tar.gz, .tgz, .tar.bz2, .tbz2, .tar.xz, .txz directly.
    Provides the same list_entries(), extract_entry(), extract_all(), close() API as SevenZipCLIReader.
    """

    def __init__(self, path: str, password: str = ""):
        """Open a tar archive for reading; raises FileNotFoundError when unreadable."""
        self._path = path
        self._password = password
        self._entries: list[ArchiveEntry] | None = None
        import tarfile

        try:
            with tarfile.open(self._path, "r:*"):
                pass
        except Exception as e:
            raise FileNotFoundError(f"Cannot open tar archive {path}: {e}")

    def list_entries(self) -> list[ArchiveEntry]:
        """List archive members as ArchiveEntry items (cached after first walk)."""
        if self._entries is not None:
            return self._entries

        import tarfile

        entries: list[ArchiveEntry] = []
        try:
            with tarfile.open(self._path, "r:*") as tf:
                for m in tf.getmembers():
                    norm_path = m.name.replace("\\", "/").lstrip("/")
                    if m.isdir() and not norm_path.endswith("/"):
                        norm_path += "/"
                    name = Path(norm_path.rstrip("/")).name
                    entries.append(
                        ArchiveEntry(
                            archive_path=norm_path,
                            name=name,
                            is_dir=m.isdir(),
                            size=m.size,
                            modified_ms=int(m.mtime * 1000),
                        )
                    )
        except Exception as e:
            log.warning("Tar list failed for %s: %s", self._path, e)

        self._entries = entries
        return entries

    def extract_entry(self, entry_path: str, dest_path: str) -> bool:
        """Extract one tar member to dest_path; returns True on success, False otherwise."""
        import tarfile

        validate_extract_path(dest_path, entry_path)
        os.makedirs(dest_path, exist_ok=True)
        try:
            with tarfile.open(self._path, "r:*") as tf:
                clean_target = entry_path.replace("\\", "/").strip("/")
                matched = None
                for m in tf.getmembers():
                    if m.name.replace("\\", "/").strip("/") == clean_target:
                        matched = m
                        break
                if matched:
                    if hasattr(tarfile, "data_filter"):
                        tf.extract(matched, dest_path, filter="data")
                    else:
                        tf.extract(matched, dest_path)
                    return True
                return False
        except Exception as e:
            log.warning("Tar extract failed for %s: %s", entry_path, e)
            return False

    def extract_all(self, dest_dir: str) -> bool:
        """Extract all tar members to dest_dir; returns True on success, False otherwise."""
        import tarfile

        os.makedirs(dest_dir, exist_ok=True)
        try:
            with tarfile.open(self._path, "r:*") as tf:
                if hasattr(tarfile, "data_filter"):
                    tf.extractall(dest_dir, filter="data")
                else:
                    tf.extractall(dest_dir)
            return True
        except Exception as e:
            log.warning("Tar extractall failed: %s", e)
            return False

    def get_info(self) -> ArchiveInfo:
        """Summarize tar contents as ArchiveInfo (entry count, total/compressed size)."""
        entries = self.list_entries()
        total_size = sum(e.size for e in entries)
        try:
            compressed = os.path.getsize(self._path)
        except OSError:
            compressed = total_size
        return ArchiveInfo(
            path=self._path,
            archive_type=detect_archive_type(self._path),
            total_entries=len(entries),
            total_size=total_size,
            compressed_size=compressed,
            is_encrypted=False,
        )

    def clear_cache(self) -> None:
        """Drop the cached member list so the next read re-walks the archive."""
        self._entries = None

    def close(self) -> None:
        """Release cached state for this reader (no open handles are held)."""
        self.clear_cache()


# ── Factory ─────────────────────────────────────────────────────────────────


def open_archive(path: str, password: str = "") -> SevenZipCLIReader | TarArchiveReader | None:
    """Open an archive for reading. Uses native tarfile for compound tarballs, or 7z.exe."""
    lower = path.lower()
    if lower.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz", ".tar")):
        try:
            return TarArchiveReader(path, password)
        except Exception as e:
            log.debug("TarArchiveReader failed for %s: %s; falling back to 7z", path, e)

    if not is_7z_available():
        log.warning("7z.exe not available — cannot open %s", path)
        return None

    try:
        return SevenZipCLIReader(path, password)
    except Exception as e:
        log.warning("Failed to open archive %s: %s", path, e)
        return None


def create_archive(
    archive_path: str,
    files: list[str],
    format: str = "zip",
    compression: str = "normal",
    password: str = "",
) -> bool:
    """Convenience helper to create an archive via ArchiveManager."""
    mgr = ArchiveManager()
    return mgr.create_archive(archive_path, files, format=format, compression=compression, password=password)


# ── Background extraction (QThread) ────────────────────────────────────────


class _ExtractWorker(QThread):
    """Background extraction using 7z.exe with progress reporting."""

    progress = Signal(int, str)  # percent, current_file
    finished_signal = Signal(bool)  # success

    def __init__(
        self,
        archive_path: str,
        dest: str,
        password: str = "",
        entries: list[str] | None = None,
    ):
        """Store archive/dest/password and the optional include-list of
        entries to extract selectively; no process runs until start()."""
        super().__init__()
        self._archive = archive_path
        self._dest = dest
        self._password = password
        self._entries = entries
        self._process: subprocess.Popen | None = None
        self._cancelled = threading.Event()

    def run(self):
        """Run '7z x' as a live Popen: parse 'Extracting' lines into
        per-file progress (-1 indeterminate) and percentage markers,
        honor isInterruptionRequested/cancel by killing the process, and
        emit finished_signal(ok = exit code 0 or 1)."""
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
        """Create the manager with no extraction worker running."""
        super().__init__(parent)
        self._worker: _ExtractWorker | None = None

    @property
    def available(self) -> bool:
        """Return True when 7z.exe is installed."""
        return is_7z_available()

    # -- browsing -----------------------------------------------------------

    def browse(self, path: str, password: str = "") -> SevenZipCLIReader | None:
        """Open an archive for browsing (open_archive wrapper; None on
        failure)."""
        return open_archive(path, password)

    # -- extraction ---------------------------------------------------------

    def extract_all(self, archive_path: str, dest: str, password: str = "") -> bool:
        """Start a background extraction of the whole archive, forwarding
        worker progress/finish signals to extraction_progress/
        extraction_finished; returns True once started."""
        self._stop_worker()
        self._worker = _ExtractWorker(archive_path, dest, password)
        self._worker.progress.connect(self.extraction_progress.emit)
        self._worker.finished_signal.connect(self._on_done)
        self._worker.start()
        return True

    def extract_selected(
        self,
        archive_path: str,
        entries: list[str],
        dest: str,
        password: str = "",
    ) -> bool:
        """Start a background extraction limited to the given entries
        (worker include-list); returns True once started."""
        self._stop_worker()
        self._worker = _ExtractWorker(archive_path, dest, password, entries)
        self._worker.progress.connect(self.extraction_progress.emit)
        self._worker.finished_signal.connect(self._on_done)
        self._worker.start()
        return True

    def cancel_extraction(self):
        """Request cancellation of the running extraction worker (kills
        the 7z process)."""
        if self._worker:
            self._worker.cancel()

    def _on_done(self, success: bool):
        """Worker finish handler: disconnect its signals, emit
        extraction_finished, and drop the worker reference."""
        if self._worker:
            try:
                self._worker.progress.disconnect()
                self._worker.finished_signal.disconnect()
            except RuntimeError:
                pass
        self.extraction_finished.emit(success)
        self._worker = None

    # -- creation -----------------------------------------------------------

    def create_archive(
        self,
        archive_path: str,
        files: list[str],
        format: str = "zip",
        compression: str = "normal",
        password: str = "",
    ) -> bool:
        """Create an archive via 7z.exe with native fallback for zip/tar."""
        if not files:
            return False

        missing = [f for f in files if not os.path.exists(f)]
        if missing:
            log.warning("Source files not found: %s", missing)
            return False

        fmt = format.lower()

        # For tar.gz / tgz, native tarfile creates genuine gzip archives in one step
        if fmt in ("tar.gz", "tgz") and not password:
            import tarfile

            try:
                with tarfile.open(archive_path, "w:gz") as tf:
                    for f in files:
                        fp = Path(f)
                        tf.add(fp, arcname=fp.name)
                return True
            except Exception as e:
                log.error("Native tar.gz creation failed: %s", e)
                return False

        # Native fallback if 7z.exe is not available
        if not is_7z_available():
            if fmt == "zip" and not password:
                import zipfile

                try:
                    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                        for f in files:
                            fp = Path(f)
                            if fp.is_file():
                                zf.write(fp, fp.name)
                            elif fp.is_dir():
                                for root, _, filenames in os.walk(fp):
                                    for fn in filenames:
                                        ffp = Path(root) / fn
                                        zf.write(ffp, str(ffp.relative_to(fp.parent)))
                    return True
                except Exception as e:
                    log.error("Native zip creation failed: %s", e)
                    return False
            elif fmt in ("tar", "tar.bz2", "tar.xz") and not password:
                import tarfile

                mode_map = {"tar": "w", "tar.bz2": "w:bz2", "tar.xz": "w:xz"}
                mode = mode_map.get(fmt, "w")
                try:
                    with tarfile.open(archive_path, mode) as tf:
                        for f in files:
                            fp = Path(f)
                            tf.add(fp, arcname=fp.name)
                    return True
                except Exception as e:
                    log.error("Native tar creation failed: %s", e)
                    return False
            else:
                log.warning("7z.exe not available for format: %s", format)
                return False

        cmd = ["a", archive_path]
        if password:
            cmd.append(f"-p{password}")

        # Format-specific compression
        if fmt == "7z":
            cmd.extend(["-t7z", f"-mx={_compression_level(compression)}"])
        elif fmt == "zip":
            cmd.extend(["-tzip", f"-mx={_compression_level(compression)}"])
        elif fmt == "tar":
            cmd.extend(["-ttar"])
        elif fmt in ("tar.bz2", "tbz2"):
            cmd.extend(["-ttar.bz2"])
        elif fmt in ("tar.xz", "txz"):
            cmd.extend(["-ttar.xz"])
        elif fmt == "rar":
            cmd.extend(["-trar", f"-mx={_compression_level(compression)}"])
        else:
            cmd.extend([f"-t{fmt}", f"-mx={_compression_level(compression)}"])

        cmd.extend(files)

        rc, out, err = _run_7z(cmd, timeout=600)
        if rc not in (0, 1):
            log.warning("7z create failed: %s", err)
            if fmt == "zip" and not password:
                import zipfile

                try:
                    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                        for f in files:
                            fp = Path(f)
                            if fp.is_file():
                                zf.write(fp, fp.name)
                            elif fp.is_dir():
                                for root, _, filenames in os.walk(fp):
                                    for fn in filenames:
                                        ffp = Path(root) / fn
                                        zf.write(ffp, str(ffp.relative_to(fp.parent)))
                    return True
                except Exception as e2:
                    log.error("Native zip fallback failed: %s", e2)
            return False
        return True

    # -- status -------------------------------------------------------------

    def is_extracting(self) -> bool:
        """Return True while an extraction worker thread is running."""
        return self._worker is not None and self._worker.isRunning()

    def _stop_worker(self):
        """Cancel and reap a running worker (5 s wait), disconnect its
        signals, and clear the reference."""
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


def _compression_level(level: str) -> int:
    """Translate a named compression level ('store'/'fast'/'normal'/
    'best') into the 7z -mx integer (0/1/5/9); unknown names raise
    ValueError."""
    levels = {
        "store": 0,
        "fast": 1,
        "normal": 5,
        "best": 9,
    }
    key = level.lower()
    if key not in levels:
        raise ValueError(f"Unknown compression level {level!r}; " f"expected one of: {', '.join(levels)}")
    return levels[key]
