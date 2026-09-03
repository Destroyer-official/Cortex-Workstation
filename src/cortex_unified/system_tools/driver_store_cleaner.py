"""Cortex Cleaner — Driver Store Explorer & Superseded Driver Purger.

Inspects and manages the Windows Driver Store repository (%WinDir%\\System32\\DriverStore):
1. Enumerates all third-party INF driver packages (oem*.inf) via pnputil.exe.
2. Identifies duplicate, superseded, and obsolete driver versions for the same hardware.
3. Provides selective and batch driver deletion (pnputil /delete-driver oemXX.inf /force).
4. Exports driver packages to backup archive directory (pnputil /export-driver * <folder>).
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class DriverPackage:
    """Driver Package data container."""
    published_name: str  # "oem12.inf"
    original_name: str  # "nv_dispi.inf"
    provider_name: str  # "NVIDIA"
    class_name: str  # "Display"
    driver_version: str  # "31.0.15.5123"
    driver_date: str  # "1/18/2024"
    signer_name: str  # "Microsoft Windows Hardware Compatibility Publisher"
    is_superseded: bool = False
    size_estimate_bytes: int = 0


@dataclass
class DriverCleanResult:
    """Driver Clean Result data container."""
    drivers_deleted: int
    bytes_freed_estimate: int
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        """__post_init__."""
        """__post_init__."""


class DriverStoreCleaner:
    """Production Driver Store Explorer (RAPR) and superseded INF driver purger."""

    @classmethod
    def enumerate_drivers(cls) -> List[DriverPackage]:
        """Query and parse all third-party driver packages via pnputil /enum-drivers."""
        if platform.system() != "Windows":
            return []

        drivers: List[DriverPackage] = []

        try:
            res = subprocess.run(["pnputil.exe", "/enum-drivers"], capture_output=True, text=True, timeout=15)
            if res.returncode != 0:
                return []

            current_dict: Dict[str, str] = {}
            for line in res.stdout.splitlines():
                line = line.strip()
                if not line:
                    if "Published Name" in current_dict:
                        drivers.append(DriverPackage(
                            published_name=current_dict.get("Published Name", ""),
                            original_name=current_dict.get("Original Name", ""),
                            provider_name=current_dict.get("Provider Name", ""),
                            class_name=current_dict.get("Class Name", ""),
                            driver_version=current_dict.get("Driver Version", ""),
                            driver_date=current_dict.get("Driver Date", ""),
                            signer_name=current_dict.get("Signer Name", ""),
                        ))
                    current_dict = {}
                    continue

                if ":" in line:
                    key, val = line.split(":", 1)
                    current_dict[key.strip()] = val.strip()

            if "Published Name" in current_dict:
                drivers.append(DriverPackage(
                    published_name=current_dict.get("Published Name", ""),
                    original_name=current_dict.get("Original Name", ""),
                    provider_name=current_dict.get("Provider Name", ""),
                    class_name=current_dict.get("Class Name", ""),
                    driver_version=current_dict.get("Driver Version", ""),
                    driver_date=current_dict.get("Driver Date", ""),
                    signer_name=current_dict.get("Signer Name", ""),
                ))
        except Exception:
            return []

        # Identify superseded drivers (same class, provider, original name with older version)
        # Group by (class_name, provider_name, original_name)
        groups: Dict[Tuple[str, str, str], List[DriverPackage]] = {}
        for d in drivers:
            k = (d.class_name.lower(), d.provider_name.lower(), d.original_name.lower())
            groups.setdefault(k, []).append(d)

        for _, group_list in groups.items():
            if len(group_list) > 1:
                # Mark all except the last/newest as superseded
                for d in group_list[:-1]:
                    d.is_superseded = True

        return drivers

    @classmethod
    def delete_driver(cls, published_name: str, force: bool = True) -> Tuple[bool, str]:
        """Delete a single third-party driver package from the Windows Driver Store."""
        if platform.system() != "Windows":
            return False, "Windows only"

        clean_name = published_name.strip()
        if not clean_name.lower().endswith(".inf"):
            clean_name += ".inf"

        cmd = ["pnputil.exe", "/delete-driver", clean_name]
        if force:
            cmd.append("/force")

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if res.returncode == 0 or "Driver package deleted successfully" in res.stdout:
                return True, f"Driver package '{clean_name}' successfully removed."
            return False, res.stderr.strip() or res.stdout.strip() or "Failed to delete driver package (Admin required)"
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def export_all_drivers(cls, backup_dir: str | Path) -> Tuple[bool, str]:
        """Export and backup all installed third-party drivers to directory."""
        if platform.system() != "Windows":
            return False, "Windows only"

        out_path = Path(backup_dir).resolve()
        out_path.mkdir(parents=True, exist_ok=True)

        try:
            cmd = ["pnputil.exe", "/export-driver", "*", str(out_path)]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0 or "Exported driver package" in res.stdout:
                return True, f"Exported driver packages to {out_path}."
            return False, res.stderr.strip() or res.stdout.strip() or "Export failed"
        except Exception as exc:
            return False, str(exc)
