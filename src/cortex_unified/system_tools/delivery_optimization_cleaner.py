"""Cortex Cleaner — Windows Delivery Optimization (WUDO) Cache Cleaner.

Scans and purges Windows Delivery Optimization peer cache and staging files
in %WinDir%\\SoftwareDistribution\\DeliveryOptimization and ProgramData cache locations.
"""

from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass
class DeliveryOptimizationStatus:
    """Deliveryoptimizationstatus.

    Manages DeliveryOptimizationStatus operations and coordinates related state changes for the component.
    """
    cache_path: str
    file_count: int
    size_bytes: int
    is_service_active: bool = True


@dataclass
class DeliveryOptimizationCleanReport:
    """Deliveryoptimizationcleanreport.

    Manages DeliveryOptimizationCleanReport operations and coordinates related state changes for the component.
    """
    files_deleted: int = 0
    bytes_freed: int = 0
    errors: List[str] = None

    def __post_init__(self):
        """__post_init__.

        Manages post init operations and coordinates related state changes for the component.
        """
        if self.errors is None:
            self.errors = []


class DeliveryOptimizationCleaner:
    """Deliveryoptimizationcleaner.

    Manages DeliveryOptimizationCleaner operations and coordinates related state changes for the component.
    """

    @classmethod
    def get_status(cls) -> DeliveryOptimizationStatus:
        """Query total cache size and file count in Delivery Optimization stores.

        Manages get status operations and coordinates related state changes for the component.

        Returns:
            DeliveryOptimizationStatus: Result of the operation.
        """
        if platform.system() != "Windows":
            return DeliveryOptimizationStatus("", 0, 0, False)

        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        program_data = Path(os.environ.get("ProgramData", r"C:\ProgramData"))

        cache_dirs = [
            windir / "SoftwareDistribution" / "DeliveryOptimization",
            program_data / "Microsoft" / "Windows" / "DeliveryOptimization",
        ]

        total_files = 0
        total_size = 0
        primary_path = str(cache_dirs[0])

        for c_dir in cache_dirs:
            if c_dir.is_dir():
                for root, _, files in os.walk(c_dir):
                    for f in files:
                        fp = Path(root) / f
                        try:
                            total_size += fp.stat().st_size
                            total_files += 1
                        except Exception:
                            pass

        return DeliveryOptimizationStatus(
            cache_path=primary_path,
            file_count=total_files,
            size_bytes=total_size,
            is_service_active=True,
        )

    @classmethod
    def clean_cache(cls) -> DeliveryOptimizationCleanReport:
        """Purge all Delivery Optimization cache files.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

        Returns:
            DeliveryOptimizationCleanReport: Result of the operation.
        """
        report = DeliveryOptimizationCleanReport()
        if platform.system() != "Windows":
            return report

        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        program_data = Path(os.environ.get("ProgramData", r"C:\ProgramData"))

        cache_dirs = [
            windir / "SoftwareDistribution" / "DeliveryOptimization",
            program_data / "Microsoft" / "Windows" / "DeliveryOptimization" / "Cache",
        ]

        for c_dir in cache_dirs:
            if not c_dir.is_dir():
                continue

            for root, dirs, files in os.walk(c_dir):
                for f in files:
                    fp = Path(root) / f
                    try:
                        sz = fp.stat().st_size
                        fp.unlink()
                        report.files_deleted += 1
                        report.bytes_freed += sz
                    except Exception as exc:
                        report.errors.append(f"Failed to delete {fp.name}: {exc}")

        return report
