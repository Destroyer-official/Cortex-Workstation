"""Fast file copier: fixed 512KB buffer, buffered Python I/O, sequential single-threaded copy.
Uses os.utime for timestamps only; no NTFS metadata preservation."""

from __future__ import annotations

import hashlib
import os
import shutil
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


class CopyMode(Enum):
    """Copymode.

    Manages CopyMode operations and coordinates related state changes for the component.
    """
    STANDARD = "Standard Buffered"
    DIRECT_IO = "High Throughput Direct"
    VERIFY_SHA256 = "Copy with SHA-256 Verification"


@dataclass
class CopyItemProgress:
    """CopyItemProgress.

    Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.
    """
    current_file: str
    files_completed: int
    total_files: int
    bytes_transferred: int
    total_bytes: int
    speed_mb_s: float
    percent: float
    eta_seconds: float


@dataclass
class CopySummary:
    """Copysummary.

    Manages CopySummary operations and coordinates related state changes for the component.
    """
    success: bool
    files_copied: int
    bytes_transferred: int
    elapsed_seconds: float
    average_speed_mb_s: float
    verified_files: int = 0
    errors: List[str] = None

    def __post_init__(self):
        """__post_init__.

        Manages post init operations and coordinates related state changes for the component.
        """
        if self.errors is None:
            self.errors = []


class FastCopier:
    """Fastcopier.

    Manages FastCopier operations and coordinates related state changes for the component.
    """

    DEFAULT_CHUNK_SIZE = 512 * 1024  # 512 KB streaming buffer

    @classmethod
    def _copy_single_file(
        cls,
        src: Path,
        dst: Path,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        speed_limit_kb_s: int = 0,
        verify_hash: bool = False,
        progress_cb: Optional[Callable[[int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Tuple[bool, int, Optional[str]]:
        """Stream copy a single file with optional throttling and hash verification.

        Manages copy single file operations and coordinates related state changes for the component.

        Args:
            src (Path): The src parameter.
            dst (Path): The dst parameter.
            chunk_size (int): The chunk size parameter.
            speed_limit_kb_s (int): The speed limit kb s parameter.
            verify_hash (bool): The verify hash parameter.
            progress_cb (Optional[Callable[[int], None]]): Callback invoked with progress updates.
            cancel_check (Optional[Callable[[], bool]]): Threading event or callable to check for cancellation.

        Returns:
            Tuple[bool, int, Optional[str]]: True if the operation succeeded, False otherwise.
        """
        dst.parent.mkdir(parents=True, exist_ok=True)
        bytes_copied = 0

        src_hasher = hashlib.sha256() if verify_hash else None
        dst_hasher = hashlib.sha256() if verify_hash else None

        # Calculate throttle delay per chunk if speed limit configured
        chunk_delay = 0.0
        if speed_limit_kb_s > 0:
            target_bytes_per_sec = speed_limit_kb_s * 1024
            chunk_delay = chunk_size / target_bytes_per_sec

        try:
            with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                while chunk := fsrc.read(chunk_size):
                    if cancel_check and cancel_check():
                        return False, bytes_copied, "Cancelled"

                    fdst.write(chunk)
                    bytes_copied += len(chunk)

                    if verify_hash:
                        src_hasher.update(chunk)
                        dst_hasher.update(chunk)

                    if progress_cb:
                        progress_cb(len(chunk))

                    if chunk_delay > 0:
                        time.sleep(chunk_delay)

            # Preserve timestamps
            try:
                st = src.stat()
                os.utime(dst, (st.st_atime, st.st_mtime))
            except Exception:
                pass

            # Verify integrity if requested
            if verify_hash:
                if src_hasher.hexdigest() != dst_hasher.hexdigest():
                    return False, bytes_copied, "Checksum mismatch after transfer"

            return True, bytes_copied, None
        except Exception as exc:
            return False, bytes_copied, str(exc)

    @classmethod
    def copy_batch(
        cls,
        sources: List[str | Path],
        destination_dir: str | Path,
        mode: CopyMode = CopyMode.STANDARD,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        speed_limit_kb_s: int = 0,
        max_retries: int = 3,
        progress_cb: Optional[Callable[[CopyItemProgress], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> CopySummary:
        """Transfer multiple files or directory trees to destination directory.

        Manages copy batch operations and coordinates related state changes for the component.

        Args:
            sources (List[str | Path]): The sources parameter.
            destination_dir (str | Path): The destination dir parameter.
            mode (CopyMode): The mode parameter.
            chunk_size (int): The chunk size parameter.
            speed_limit_kb_s (int): The speed limit kb s parameter.
            max_retries (int): The max retries parameter.
            progress_cb (Optional[Callable[[CopyItemProgress], None]]): Callback invoked with progress updates.
            cancel_check (Optional[Callable[[], bool]]): Threading event or callable to check for cancellation.

        Returns:
            CopySummary: Result of the operation.
        """
        dest_dir = Path(destination_dir).resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)

        # 1. Discover all source files to copy and total size
        all_tasks: List[Tuple[Path, Path]] = []  # (src_file, dst_file)
        total_bytes = 0

        for s in sources:
            sp = Path(s).resolve()
            if not sp.exists():
                continue
            if sp.is_file():
                try:
                    size = sp.stat().st_size
                    total_bytes += size
                    all_tasks.append((sp, dest_dir / sp.name))
                except Exception:
                    pass
            elif sp.is_dir():
                for root, _, files in os.walk(sp):
                    rel = Path(root).relative_to(sp.parent)
                    target_parent = dest_dir / rel
                    for f in files:
                        fp = Path(root) / f
                        try:
                            size = fp.stat().st_size
                            total_bytes += size
                            all_tasks.append((fp, target_parent / f))
                        except Exception:
                            pass

        total_files = len(all_tasks)
        if total_files == 0:
            return CopySummary(True, 0, 0, 0.0, 0.0)

        verify_hash = mode == CopyMode.VERIFY_SHA256
        files_completed = 0
        total_transferred = 0
        verified_count = 0
        errors: List[str] = []

        start_time = time.perf_counter()
        last_calc_time = start_time
        transferred_since_calc = 0
        current_speed = 0.0

        for src_path, dst_path in all_tasks:
            if cancel_check and cancel_check():
                break

            success = False
            err_msg = ""
            for attempt in range(max_retries):
                def _file_chunk_cb(chunk_len: int):
                    """_file_chunk_cb.

                    Manages file chunk cb operations and coordinates related state changes for the component.

                    Args:
                        chunk_len (int): The chunk len parameter.
                    """
                    nonlocal total_transferred, transferred_since_calc, last_calc_time, current_speed
                    total_transferred += chunk_len
                    transferred_since_calc += chunk_len
                    now = time.perf_counter()
                    dt = now - last_calc_time
                    if dt >= 0.5:
                        current_speed = (transferred_since_calc / (1024 * 1024)) / dt
                        transferred_since_calc = 0
                        last_calc_time = now

                    if progress_cb:
                        pct = (total_transferred / total_bytes * 100) if total_bytes > 0 else 0.0
                        eta = (total_bytes - total_transferred) / (current_speed * 1024 * 1024) if current_speed > 0 else 0.0
                        progress_cb(CopyItemProgress(
                            current_file=src_path.name,
                            files_completed=files_completed,
                            total_files=total_files,
                            bytes_transferred=total_transferred,
                            total_bytes=total_bytes,
                            speed_mb_s=current_speed,
                            percent=min(100.0, pct),
                            eta_seconds=max(0.0, eta),
                        ))

                ok, b_copied, err = cls._copy_single_file(
                    src_path,
                    dst_path,
                    chunk_size=chunk_size,
                    speed_limit_kb_s=speed_limit_kb_s,
                    verify_hash=verify_hash,
                    progress_cb=_file_chunk_cb,
                    cancel_check=cancel_check,
                )

                if ok:
                    success = True
                    files_completed += 1
                    if verify_hash:
                        verified_count += 1
                    break
                else:
                    err_msg = err or "Unknown copy error"
                    time.sleep(0.2 * (attempt + 1))  # Exponential backoff on lock

            if not success:
                errors.append(f"{src_path.name}: {err_msg}")

        elapsed = max(0.001, time.perf_counter() - start_time)
        avg_speed = (total_transferred / (1024 * 1024)) / elapsed

        return CopySummary(
            success=len(errors) == 0,
            files_copied=files_completed,
            bytes_transferred=total_transferred,
            elapsed_seconds=elapsed,
            average_speed_mb_s=avg_speed,
            verified_files=verified_count,
            errors=errors,
        )
