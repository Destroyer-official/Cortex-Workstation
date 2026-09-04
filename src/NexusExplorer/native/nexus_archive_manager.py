"""Archive creation: STORED and DEFLATED only; no BZIP2/LZMA, no password support."""

from __future__ import annotations

import os
import shutil
import tarfile
import time
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


class ArchiveFormat(Enum):
    """ArchiveFormat.

    Converts raw numeric values into formatted, localized, and human-readable string representations.
    """
    ZIP = "ZIP Archive (.zip)"
    TAR = "Tarball (.tar)"
    TAR_GZ = "Gzipped Tarball (.tar.gz)"
    TAR_BZ2 = "Bzip2 Tarball (.tar.bz2)"
    TAR_XZ = "XZ Compressed Tarball (.tar.xz)"


class CompressionLevel(Enum):
    """Compressionlevel.

    Manages CompressionLevel operations and coordinates related state changes for the component.
    """
    STORE = 0
    FAST = 1
    NORMAL = 6
    MAXIMUM = 9


@dataclass
class ArchiveEntryInfo:
    """Archiveentryinfo.

    Manages ArchiveEntryInfo operations and coordinates related state changes for the component.
    """
    filename: str
    uncompressed_size: int
    compressed_size: int
    is_directory: bool
    modified_time: float
    crc: Optional[str] = None


@dataclass
class ArchiveOperationResult:
    """Archiveoperationresult.

    Manages ArchiveOperationResult operations and coordinates related state changes for the component.
    """
    success: bool
    archive_path: str
    total_files: int
    total_uncompressed_bytes: int
    total_compressed_bytes: int
    elapsed_seconds: float
    error: Optional[str] = None


class ArchiveManager:
    """Archivemanager.

    Manages ArchiveManager operations and coordinates related state changes for the component.
    """

    @staticmethod
    def detect_format(archive_path: str | Path) -> Optional[ArchiveFormat]:
        """Detect archive format based on file extension.

        Converts raw numeric values into formatted, localized, and human-readable string representations.

        Args:
            archive_path (str | Path): Filesystem path to the target file or directory.

        Returns:
            Optional[ArchiveFormat]: Result of the operation.
        """
        name = Path(archive_path).name.lower()
        if name.endswith(".zip"):
            return ArchiveFormat.ZIP
        if name.endswith((".tar.gz", ".tgz")):
            return ArchiveFormat.TAR_GZ
        if name.endswith((".tar.bz2", ".tbz2")):
            return ArchiveFormat.TAR_BZ2
        if name.endswith(".tar.xz"):
            return ArchiveFormat.TAR_XZ
        if name.endswith(".tar"):
            return ArchiveFormat.TAR
        return None

    @classmethod
    def list_entries(cls, archive_path: str | Path) -> List[ArchiveEntryInfo]:
        """List all entries contained in an archive without extracting to disk.

        Manages list entries operations and coordinates related state changes for the component.

        Args:
            archive_path (str | Path): Filesystem path to the target file or directory.

        Returns:
            List[ArchiveEntryInfo]: List of processed items or identifiers.
        """
        path = Path(archive_path).resolve()
        if not path.is_file():
            return []

        fmt = cls.detect_format(path)
        entries: List[ArchiveEntryInfo] = []

        try:
            if fmt == ArchiveFormat.ZIP:
                with zipfile.ZipFile(path, "r") as zf:
                    for info in zf.infolist():
                        dt = time.mktime((*info.date_time, 0, 0, -1)) if info.date_time else 0.0
                        entries.append(ArchiveEntryInfo(
                            filename=info.filename,
                            uncompressed_size=info.file_size,
                            compressed_size=info.compress_size,
                            is_directory=info.is_dir(),
                            modified_time=dt,
                            crc=f"{info.CRC & 0xFFFFFFFF:08X}" if info.CRC else "",
                        ))
            elif fmt in (ArchiveFormat.TAR, ArchiveFormat.TAR_GZ, ArchiveFormat.TAR_BZ2, ArchiveFormat.TAR_XZ):
                mode = "r:*"
                with tarfile.open(path, mode) as tf:
                    for member in tf.getmembers():
                        entries.append(ArchiveEntryInfo(
                            filename=member.name,
                            uncompressed_size=member.size,
                            compressed_size=member.size,
                            is_directory=member.isdir(),
                            modified_time=member.mtime,
                            crc="",
                        ))
        except Exception:
            pass

        return entries

    @classmethod
    def test_archive(cls, archive_path: str | Path) -> Tuple[bool, Optional[str]]:
        """Verify archive integrity and check for CRC/decompress corruption.

        Manages test archive operations and coordinates related state changes for the component.

        Args:
            archive_path (str | Path): Filesystem path to the target file or directory.

        Returns:
            Tuple[bool, Optional[str]]: True if the operation succeeded, False otherwise.
        """
        path = Path(archive_path).resolve()
        if not path.is_file():
            return False, "Archive file does not exist"

        fmt = cls.detect_format(path)
        try:
            if fmt == ArchiveFormat.ZIP:
                with zipfile.ZipFile(path, "r") as zf:
                    bad_file = zf.testzip()
                    if bad_file:
                        return False, f"Corrupted file detected in archive: {bad_file}"
                    return True, "All archive CRC checksums verified successfully."
            elif fmt in (ArchiveFormat.TAR, ArchiveFormat.TAR_GZ, ArchiveFormat.TAR_BZ2, ArchiveFormat.TAR_XZ):
                with tarfile.open(path, "r:*") as tf:
                    for member in tf.getmembers():
                        if member.isfile():
                            f = tf.extractfile(member)
                            if f:
                                while f.read(65536):
                                    pass
                    return True, "Tarball structure and decompression stream verified."
            return False, "Unsupported archive format"
        except Exception as exc:
            return False, f"Archive verification failed: {exc}"

    @classmethod
    def extract_archive(
        cls,
        archive_path: str | Path,
        destination_dir: str | Path,
        password: Optional[str] = None,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> ArchiveOperationResult:
        """Extract an archive to a destination directory.

        Manages extract archive operations and coordinates related state changes for the component.

        Args:
            archive_path (str | Path): Filesystem path to the target file or directory.
            destination_dir (str | Path): The destination dir parameter.
            password (Optional[str]): The password parameter.
            progress_cb (Optional[Callable[[int, int, str], None]]): Callback invoked with progress updates.
            cancel_check (Optional[Callable[[], bool]]): Threading event or callable to check for cancellation.

        Returns:
            ArchiveOperationResult: Result of the operation.
        """
        arc_p = Path(archive_path).resolve()
        dest_p = Path(destination_dir).resolve()
        dest_p.mkdir(parents=True, exist_ok=True)

        if not arc_p.is_file():
            return ArchiveOperationResult(False, str(arc_p), 0, 0, 0, 0.0, "Archive not found")

        start = time.perf_counter()
        fmt = cls.detect_format(arc_p)
        total_extracted = 0
        total_bytes = 0

        try:
            if fmt == ArchiveFormat.ZIP:
                with zipfile.ZipFile(arc_p, "r") as zf:
                    pwd = password.encode("utf-8") if password else None
                    infolist = zf.infolist()
                    total = len(infolist)
                    for idx, info in enumerate(infolist):
                        if cancel_check and cancel_check():
                            return ArchiveOperationResult(False, str(arc_p), total_extracted, total_bytes, 0, time.perf_counter() - start, "Cancelled")
                        zf.extract(info, dest_p, pwd=pwd)
                        total_extracted += 1
                        total_bytes += info.file_size
                        if progress_cb:
                            progress_cb(idx + 1, total, info.filename)
            elif fmt in (ArchiveFormat.TAR, ArchiveFormat.TAR_GZ, ArchiveFormat.TAR_BZ2, ArchiveFormat.TAR_XZ):
                with tarfile.open(arc_p, "r:*") as tf:
                    members = tf.getmembers()
                    total = len(members)
                    for idx, member in enumerate(members):
                        if cancel_check and cancel_check():
                            return ArchiveOperationResult(False, str(arc_p), total_extracted, total_bytes, 0, time.perf_counter() - start, "Cancelled")
                        tf.extract(member, dest_p, filter="data" if hasattr(tarfile, "data_filter") else None)
                        total_extracted += 1
                        total_bytes += member.size
                        if progress_cb:
                            progress_cb(idx + 1, total, member.name)

            elapsed = max(0.001, time.perf_counter() - start)
            return ArchiveOperationResult(True, str(arc_p), total_extracted, total_bytes, arc_p.stat().st_size, elapsed)
        except Exception as exc:
            return ArchiveOperationResult(False, str(arc_p), total_extracted, total_bytes, 0, time.perf_counter() - start, str(exc))

    @classmethod
    def create_archive(
        cls,
        sources: List[str | Path],
        output_file: str | Path,
        fmt: ArchiveFormat = ArchiveFormat.ZIP,
        compression_level: CompressionLevel = CompressionLevel.NORMAL,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> ArchiveOperationResult:
        """Create archive (STORED or DEFLATED only; no BZIP2/LZMA, no password)."""
        out_p = Path(output_file).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)

        start = time.perf_counter()
        files_to_add: List[Tuple[Path, str]] = []  # (source_abs_path, arcname)
        total_uncompressed = 0

        for s in sources:
            sp = Path(s).resolve()
            if not sp.exists():
                continue
            if sp.is_file():
                files_to_add.append((sp, sp.name))
                total_uncompressed += sp.stat().st_size
            elif sp.is_dir():
                for root, _, files in os.walk(sp):
                    for f in files:
                        fp = Path(root) / f
                        rel_arc = fp.relative_to(sp.parent)
                        files_to_add.append((fp, str(rel_arc)))
                        try:
                            total_uncompressed += fp.stat().st_size
                        except Exception:
                            pass

        total_files = len(files_to_add)
        if total_files == 0:
            return ArchiveOperationResult(False, str(out_p), 0, 0, 0, 0.0, "No files found to archive")

        try:
            if fmt == ArchiveFormat.ZIP:
                comp_type = zipfile.ZIP_STORED if compression_level == CompressionLevel.STORE else zipfile.ZIP_DEFLATED
                with zipfile.ZipFile(out_p, "w", compression=comp_type, compresslevel=compression_level.value) as zf:
                    for idx, (src_file, arcname) in enumerate(files_to_add):
                        if cancel_check and cancel_check():
                            return ArchiveOperationResult(False, str(out_p), idx, 0, 0, time.perf_counter() - start, "Cancelled")
                        zf.write(src_file, arcname)
                        if progress_cb:
                            progress_cb(idx + 1, total_files, arcname)
            elif fmt in (ArchiveFormat.TAR, ArchiveFormat.TAR_GZ, ArchiveFormat.TAR_BZ2, ArchiveFormat.TAR_XZ):
                mode_map = {
                    ArchiveFormat.TAR: "w",
                    ArchiveFormat.TAR_GZ: "w:gz",
                    ArchiveFormat.TAR_BZ2: "w:bz2",
                    ArchiveFormat.TAR_XZ: "w:xz",
                }
                mode = mode_map.get(fmt, "w:gz")
                with tarfile.open(out_p, mode) as tf:
                    for idx, (src_file, arcname) in enumerate(files_to_add):
                        if cancel_check and cancel_check():
                            return ArchiveOperationResult(False, str(out_p), idx, 0, 0, time.perf_counter() - start, "Cancelled")
                        tf.add(src_file, arcname=arcname)
                        if progress_cb:
                            progress_cb(idx + 1, total_files, arcname)

            elapsed = max(0.001, time.perf_counter() - start)
            compressed_size = out_p.stat().st_size if out_p.exists() else 0
            return ArchiveOperationResult(True, str(out_p), total_files, total_uncompressed, compressed_size, elapsed)
        except Exception as exc:
            return ArchiveOperationResult(False, str(out_p), 0, total_uncompressed, 0, time.perf_counter() - start, str(exc))
