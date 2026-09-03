"""GPU & DirectX Shader Cache Forensics & Cleanup Engine.

Research Grounding
------------------
* Microsoft DirectX Graphics Infrastructure (DXGI) & Direct3D 12 Pipeline:
  DirectX pre-compiles High-Level Shader Language (HLSL) code into hardware-specific
  binary shader blobs stored in `%LOCALAPPDATA%\\D3DSCache`.
* NVIDIA Graphics Architecture:
  Proprietary driver-level shader caches reside in `%LOCALAPPDATA%\\NVIDIA\\DXCache`
  (DirectX) and `GLCache` (OpenGL/Vulkan), plus legacy `%APPDATA%\\NVIDIA\\ComputeCache`.
* AMD Radeon Adrenalin Driver Architecture:
  Compiled shader bytecode accumulates in `%LOCALAPPDATA%\\AMD\\DxCache` and `DxcCache`.
* Intel Graphics Software:
  Intel Arc and Iris Xe shader caches reside in `%LOCALAPPDATA%\\Intel\\ShaderCache`.

Over time, driver updates, game patches, and uninstalled applications leave gigabytes
of orphaned, unreferenced shader binaries that are never purged by Windows. This module
safely scans, analyzes by access age, and reclaims stale shader cache storage.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOG = logging.getLogger("cortex.system_tools.shader_cache")


@dataclass
class ShaderLocationInfo:
    """Metadata and size analysis for a specific shader cache target location."""
    name: str
    vendor: str
    path: str
    exists: bool
    file_count: int = 0
    total_bytes: int = 0
    stale_file_count: int = 0
    stale_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "name": self.name,
            "vendor": self.vendor,
            "path": self.path,
            "exists": self.exists,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "stale_file_count": self.stale_file_count,
            "stale_bytes": self.stale_bytes,
        }


@dataclass
class ShaderCacheReport:
    """Consolidated inventory of GPU shader caches across all hardware vendors."""
    locations: List[ShaderLocationInfo] = field(default_factory=list)
    total_files: int = 0
    total_bytes: int = 0
    stale_files: int = 0
    stale_bytes: int = 0
    scan_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "locations": [loc.to_dict() for loc in self.locations],
            "total_files": self.total_files,
            "total_bytes": self.total_bytes,
            "stale_files": self.stale_files,
            "stale_bytes": self.stale_bytes,
            "scan_duration_ms": self.scan_duration_ms,
        }


@dataclass
class ShaderCleanResult:
    """Outcome of a shader cache purge operation."""
    cleaned_files: int = 0
    freed_bytes: int = 0
    skipped_locked_files: int = 0
    errors: List[str] = field(default_factory=list)
    dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "cleaned_files": self.cleaned_files,
            "freed_bytes": self.freed_bytes,
            "skipped_locked_files": self.skipped_locked_files,
            "errors": self.errors,
            "dry_run": self.dry_run,
        }


class ShaderCacheCleaner:
    """Production GPU shader cache detection, forensics, and cleanup engine."""

    def __init__(self) -> None:
        """Initialize Shader Cache Cleaner."""
        self.logger = _LOG

    def get_known_locations(self) -> List[tuple[str, str, Path]]:
        """Resolve standard shader cache paths dynamically from current user profile."""
        local_app_data = os.environ.get("LOCALAPPDATA")
        app_data = os.environ.get("APPDATA")

        targets: List[tuple[str, str, Path]] = []

        if local_app_data:
            lad = Path(local_app_data)
            # Microsoft DirectX D3D Shader Cache
            targets.append(("DirectX D3D Shader Cache", "Microsoft", lad / "D3DSCache"))
            # NVIDIA Driver Shader Caches
            targets.append(("NVIDIA DirectX Shader Cache", "NVIDIA", lad / "NVIDIA" / "DXCache"))
            targets.append(("NVIDIA OpenGL/Vulkan Cache", "NVIDIA", lad / "NVIDIA" / "GLCache"))
            # AMD Radeon Adrenalin Caches
            targets.append(("AMD Radeon DX Cache", "AMD", lad / "AMD" / "DxCache"))
            targets.append(("AMD Radeon DXC Cache", "AMD", lad / "AMD" / "DxcCache"))
            # Intel Graphics Cache
            targets.append(("Intel Arc / Xe Shader Cache", "Intel", lad / "Intel" / "ShaderCache"))

        if app_data:
            ad = Path(app_data)
            targets.append(("NVIDIA Legacy Compute Cache", "NVIDIA", ad / "NVIDIA" / "ComputeCache"))

        return targets

    def scan(self, min_age_days: int = 0) -> ShaderCacheReport:
        """Scan all GPU shader cache locations and analyze disk consumption."""
        t0 = time.perf_counter()
        report = ShaderCacheReport()
        now = time.time()
        age_threshold_sec = min_age_days * 86400

        for name, vendor, path in self.get_known_locations():
            loc_info = ShaderLocationInfo(
                name=name,
                vendor=vendor,
                path=str(path),
                exists=path.is_dir(),
            )

            if loc_info.exists:
                try:
                    for root, _, files in os.walk(path):
                        for f in files:
                            fp = Path(root) / f
                            try:
                                stat = fp.stat()
                                sz = stat.st_size
                                loc_info.file_count += 1
                                loc_info.total_bytes += sz

                                is_stale = (now - stat.st_mtime) >= age_threshold_sec
                                if is_stale:
                                    loc_info.stale_file_count += 1
                                    loc_info.stale_bytes += sz
                            except (OSError, PermissionError):
                                continue
                except (OSError, PermissionError) as exc:
                    self.logger.debug("Failed to traverse %s: %s", path, exc)

            report.locations.append(loc_info)
            report.total_files += loc_info.file_count
            report.total_bytes += loc_info.total_bytes
            report.stale_files += loc_info.stale_file_count
            report.stale_bytes += loc_info.stale_bytes

        report.scan_duration_ms = (time.perf_counter() - t0) * 1000.0
        return report

    def clean(self, min_age_days: int = 0, dry_run: bool = False) -> ShaderCleanResult:
        """Purge stale or orphaned shader cache files across all detected locations."""
        result = ShaderCleanResult(dry_run=dry_run)
        now = time.time()
        age_threshold_sec = min_age_days * 86400

        for _, _, path in self.get_known_locations():
            if not path.is_dir():
                continue

            try:
                for root, _, files in os.walk(path, topdown=False):
                    for f in files:
                        fp = Path(root) / f
                        try:
                            stat = fp.stat()
                            if (now - stat.st_mtime) >= age_threshold_sec:
                                sz = stat.st_size
                                if not dry_run:
                                    fp.unlink()
                                result.cleaned_files += 1
                                result.freed_bytes += sz
                        except (PermissionError, OSError) as exc:
                            result.skipped_locked_files += 1
                            self.logger.debug("Cannot remove active shader file %s: %s", fp, exc)

                    # Clean empty parent directories inside shader folder
                    if not dry_run and root != str(path):
                        try:
                            if not os.listdir(root):
                                os.rmdir(root)
                        except OSError:
                            pass
            except (OSError, PermissionError) as exc:
                result.errors.append(f"Error accessing {path}: {exc}")

        return result
