"""Cortex Cleaner — Storage Performance & IOPS Disk Benchmark.

Performs non-destructive storage benchmarks measuring:
1. Sequential Read (1MB block size)
2. Sequential Write (1MB block size)
3. Random 4KB Read (IOPS & Access Latency)
4. Random 4KB Write (IOPS & Access Latency)
"""

from __future__ import annotations

import os
import random
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class DiskBenchmarkMetric:
    """Disk Benchmark Metric data container."""
    test_name: str
    speed_mb_s: float
    iops: float
    avg_latency_ms: float


@dataclass
class DiskBenchmarkReport:
    """Disk Benchmark Report data container."""
    target_drive: str
    target_path: str
    test_file_size_mb: int
    sequential_read: DiskBenchmarkMetric
    sequential_write: DiskBenchmarkMetric
    random_read_4k: DiskBenchmarkMetric
    random_write_4k: DiskBenchmarkMetric
    elapsed_seconds: float
    error: Optional[str] = None


class DiskBenchmarkEngine:
    """Production non-destructive disk throughput and IOPS storage benchmark."""

    @classmethod
    def run_benchmark(
        cls,
        target_directory: str | Path,
        file_size_mb: int = 64,  # 64MB default for fast, accurate measurement
        progress_cb: Optional[Callable[[str, float], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> DiskBenchmarkReport:
        """Execute full benchmark suite on the specified storage location."""
        target_dir = Path(target_directory).resolve()
        if not target_dir.is_dir():
            target_dir = Path(tempfile.gettempdir())

        temp_test_file = target_dir / f"__cortex_bench_{uuid.uuid4().hex[:8]}.tmp"
        total_bytes = file_size_mb * 1024 * 1024
        block_1mb = 1024 * 1024
        block_4kb = 4096

        start_time = time.perf_counter()

        seq_write = DiskBenchmarkMetric("Sequential Write (1MB)", 0.0, 0.0, 0.0)
        seq_read = DiskBenchmarkMetric("Sequential Read (1MB)", 0.0, 0.0, 0.0)
        rnd_write = DiskBenchmarkMetric("Random Write (4KB)", 0.0, 0.0, 0.0)
        rnd_read = DiskBenchmarkMetric("Random Read (4KB)", 0.0, 0.0, 0.0)

        # Pre-generate 1MB random buffer to defeat file system compression spoofing
        payload_1mb = os.urandom(block_1mb)
        payload_4kb = os.urandom(block_4kb)

        try:
            # 1. Sequential Write
            if progress_cb:
                progress_cb("Sequential Write (1MB)", 10.0)
            if cancel_check and cancel_check():
                raise KeyboardInterrupt("Cancelled")

            t0 = time.perf_counter()
            with open(temp_test_file, "wb", buffering=0) as f:
                for _ in range(file_size_mb):
                    f.write(payload_1mb)
                f.flush()
                os.fsync(f.fileno())
            t_write = max(0.0001, time.perf_counter() - t0)
            seq_write = DiskBenchmarkMetric(
                test_name="Sequential Write (1MB)",
                speed_mb_s=round(file_size_mb / t_write, 2),
                iops=round(file_size_mb / t_write, 1),
                avg_latency_ms=round((t_write / file_size_mb) * 1000.0, 3),
            )

            # 2. Sequential Read
            if progress_cb:
                progress_cb("Sequential Read (1MB)", 35.0)
            if cancel_check and cancel_check():
                raise KeyboardInterrupt("Cancelled")

            t0 = time.perf_counter()
            with open(temp_test_file, "rb", buffering=0) as f:
                while chunk := f.read(block_1mb):
                    pass
            t_read = max(0.0001, time.perf_counter() - t0)
            seq_read = DiskBenchmarkMetric(
                test_name="Sequential Read (1MB)",
                speed_mb_s=round(file_size_mb / t_read, 2),
                iops=round(file_size_mb / t_read, 1),
                avg_latency_ms=round((t_read / file_size_mb) * 1000.0, 3),
            )

            # 3. Random Write 4KB
            if progress_cb:
                progress_cb("Random Write (4KB)", 60.0)
            if cancel_check and cancel_check():
                raise KeyboardInterrupt("Cancelled")

            num_4k_ops = min(2000, total_bytes // block_4kb)
            max_offset = total_bytes - block_4kb

            t0 = time.perf_counter()
            with open(temp_test_file, "r+b", buffering=0) as f:
                for _ in range(num_4k_ops):
                    offset = random.randint(0, max_offset // block_4kb) * block_4kb
                    f.seek(offset)
                    f.write(payload_4kb)
                f.flush()
                os.fsync(f.fileno())
            t_rnd_write = max(0.0001, time.perf_counter() - t0)
            mb_rnd_write = (num_4k_ops * block_4kb) / (1024 * 1024)
            rnd_write = DiskBenchmarkMetric(
                test_name="Random Write (4KB)",
                speed_mb_s=round(mb_rnd_write / t_rnd_write, 2),
                iops=round(num_4k_ops / t_rnd_write, 1),
                avg_latency_ms=round((t_rnd_write / num_4k_ops) * 1000.0, 3),
            )

            # 4. Random Read 4KB
            if progress_cb:
                progress_cb("Random Read (4KB)", 85.0)
            if cancel_check and cancel_check():
                raise KeyboardInterrupt("Cancelled")

            t0 = time.perf_counter()
            with open(temp_test_file, "rb", buffering=0) as f:
                for _ in range(num_4k_ops):
                    offset = random.randint(0, max_offset // block_4kb) * block_4kb
                    f.seek(offset)
                    _ = f.read(block_4kb)
            t_rnd_read = max(0.0001, time.perf_counter() - t0)
            mb_rnd_read = (num_4k_ops * block_4kb) / (1024 * 1024)
            rnd_read = DiskBenchmarkMetric(
                test_name="Random Read (4KB)",
                speed_mb_s=round(mb_rnd_read / t_rnd_read, 2),
                iops=round(num_4k_ops / t_rnd_read, 1),
                avg_latency_ms=round((t_rnd_read / num_4k_ops) * 1000.0, 3),
            )

            if progress_cb:
                progress_cb("Complete", 100.0)

            elapsed = time.perf_counter() - start_time
            drive_letter = str(target_dir.drive) if target_dir.drive else str(target_dir)

            return DiskBenchmarkReport(
                target_drive=drive_letter,
                target_path=str(target_dir),
                test_file_size_mb=file_size_mb,
                sequential_read=seq_read,
                sequential_write=seq_write,
                random_read_4k=rnd_read,
                random_write_4k=rnd_write,
                elapsed_seconds=round(elapsed, 2),
            )
        except Exception as exc:
            return DiskBenchmarkReport(
                target_drive=str(target_dir.drive) or str(target_dir),
                target_path=str(target_dir),
                test_file_size_mb=file_size_mb,
                sequential_read=seq_read,
                sequential_write=seq_write,
                random_read_4k=rnd_read,
                random_write_4k=rnd_write,
                elapsed_seconds=time.perf_counter() - start_time,
                error=str(exc),
            )
        finally:
            if temp_test_file.exists():
                try:
                    temp_test_file.unlink()
                except Exception:
                    pass
