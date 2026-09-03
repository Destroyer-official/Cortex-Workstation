"""Developer Package Caches (Winget, Cargo, Vcpkg, NuGet, Pip) Deep Cleaner.

Research Grounding
------------------
* Modern Developer Workstation Storage Overhead:
  Developers working across multiple toolchains accumulate dozens of gigabytes
  of immutable compiled tarballs, crate archives, wheel caches, and installer payloads.
* Targeted Ecosystem Stores:
  1. Windows Package Manager (`winget`): Installer downloads cached in
     `%LOCALAPPDATA%\\Packages\\Microsoft.DesktopAppInstaller_*\\LocalState` and Temp directories.
  2. Rust Cargo: Compressed crate archives in `%USERPROFILE%\\.cargo\\registry\\cache`
     and git repository checkouts in `%USERPROFILE%\\.cargo\\git\\checkouts`.
  3. Microsoft C++ `vcpkg`: Pre-built binary archives in `%LOCALAPPDATA%\\vcpkg\\archives`.
  4. .NET NuGet: HTTP package download caches in `%LOCALAPPDATA%\\NuGet\\v3-cache`.
  5. Python Pip: Wheel and source download caches in `%LOCALAPPDATA%\\pip\\cache`.
  6. Node Yarn/Pnpm: Global content-addressable package tarballs.

This module dynamically inspects and cleans these developer package stores without
damaging installed toolchains, build environments, or active source trees.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOG = logging.getLogger("cortex.system_tools.dev_package_cache")


@dataclass
class DevPackageStoreInfo:
    """Status and storage consumption of a specific developer package cache."""
    name: str
    ecosystem: str
    path: str
    exists: bool
    package_count: int = 0
    total_bytes: int = 0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "name": self.name,
            "ecosystem": self.ecosystem,
            "path": self.path,
            "exists": self.exists,
            "package_count": self.package_count,
            "total_bytes": self.total_bytes,
            "description": self.description,
        }


@dataclass
class DevPackageReport:
    """Consolidated storage consumption across all developer package ecosystems."""
    stores: List[DevPackageStoreInfo] = field(default_factory=list)
    total_packages: int = 0
    total_bytes: int = 0
    scan_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "stores": [s.to_dict() for s in self.stores],
            "total_packages": self.total_packages,
            "total_bytes": self.total_bytes,
            "scan_duration_ms": self.scan_duration_ms,
        }


@dataclass
class DevPackageCleanResult:
    """Outcome of a developer package cache purge."""
    cleaned_stores: int = 0
    deleted_packages: int = 0
    freed_bytes: int = 0
    errors: List[str] = field(default_factory=list)
    dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "cleaned_stores": self.cleaned_stores,
            "deleted_packages": self.deleted_packages,
            "freed_bytes": self.freed_bytes,
            "errors": self.errors,
            "dry_run": self.dry_run,
        }


class DevPackageCacheCleaner:
    """Production developer environment cache detection and cleanup engine."""

    def __init__(self) -> None:
        """Initialize Dev Package Cache Cleaner."""
        self.logger = _LOG

    def get_candidate_stores(self) -> List[tuple[str, str, Path, str]]:
        """Resolve candidate developer cache roots dynamically from active user profiles."""
        lad = os.environ.get("LOCALAPPDATA")
        up = os.environ.get("USERPROFILE") or os.environ.get("HOME")

        stores: List[tuple[str, str, Path, str]] = []

        if lad:
            lad_p = Path(lad)
            # Windows Package Manager (Winget)
            stores.append((
                "Windows Package Manager (Winget) Cache",
                "Winget",
                lad_p / "Packages" / "Microsoft.DesktopAppInstaller_8wekyb3d8bbwe" / "LocalState",
                "Downloaded MSIX, MSI, and EXE installers cached by winget.",
            ))
            # Microsoft C++ vcpkg binary archives
            stores.append((
                "Microsoft vcpkg Binary Archive",
                "vcpkg",
                lad_p / "vcpkg" / "archives",
                "Precompiled static and dynamic C/C++ libraries cached by vcpkg.",
            ))
            # .NET NuGet v3 Cache
            stores.append((
                ".NET NuGet v3 Download Cache",
                "NuGet",
                lad_p / "NuGet" / "v3-cache",
                "Downloaded .nupkg archives and metadata.",
            ))
            # Python Pip Cache
            stores.append((
                "Python Pip Wheel Cache",
                "pip",
                lad_p / "pip" / "cache",
                "Locally cached Python .whl wheels and source tarballs.",
            ))
            # Yarn Cache
            stores.append((
                "Yarn Package Cache",
                "Yarn",
                lad_p / "Yarn" / "Cache",
                "Global Node.js package archives downloaded by Yarn.",
            ))

        if up:
            up_p = Path(up)
            # Rust Cargo Registry Cache
            stores.append((
                "Rust Cargo Registry Crate Cache",
                "Cargo",
                up_p / ".cargo" / "registry" / "cache",
                "Compressed .crate packages downloaded from crates.io.",
            ))
            # Rust Cargo Git Checkouts
            stores.append((
                "Rust Cargo Git Clones Cache",
                "Cargo",
                up_p / ".cargo" / "git" / "checkouts",
                "Cloned Git dependency repositories cached by Cargo.",
            ))

        return stores

    def scan(self) -> DevPackageReport:
        """Analyze developer package stores and measure disk space consumption."""
        t0 = time.perf_counter()
        report = DevPackageReport()

        for name, eco, path, desc in self.get_candidate_stores():
            exists = path.is_dir()
            sinfo = DevPackageStoreInfo(
                name=name,
                ecosystem=eco,
                path=str(path),
                exists=exists,
                description=desc,
            )

            if exists:
                try:
                    for root, _, files in os.walk(path):
                        for f in files:
                            fp = Path(root) / f
                            try:
                                sz = fp.stat().st_size
                                sinfo.package_count += 1
                                sinfo.total_bytes += sz
                            except (OSError, PermissionError):
                                continue
                except (OSError, PermissionError) as exc:
                    self.logger.debug("Cannot scan store %s: %s", path, exc)

            report.stores.append(sinfo)
            report.total_packages += sinfo.package_count
            report.total_bytes += sinfo.total_bytes

        report.scan_duration_ms = (time.perf_counter() - t0) * 1000.0
        return report

    def clean(
        self,
        selected_ecosystems: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> DevPackageCleanResult:
        """Purge developer package cache archives."""
        result = DevPackageCleanResult(dry_run=dry_run)
        eco_filter = {e.lower() for e in selected_ecosystems} if selected_ecosystems else None

        for _, eco, path, _ in self.get_candidate_stores():
            if eco_filter and eco.lower() not in eco_filter:
                continue

            if not path.is_dir():
                continue

            store_cleaned = False
            try:
                for root, _, files in os.walk(path, topdown=False):
                    for f in files:
                        fp = Path(root) / f
                        try:
                            sz = fp.stat().st_size
                            if not dry_run:
                                fp.unlink()
                            result.deleted_packages += 1
                            result.freed_bytes += sz
                            store_cleaned = True
                        except (PermissionError, OSError) as exc:
                            self.logger.debug("Cannot remove cached package %s: %s", fp, exc)

                    if not dry_run and root != str(path):
                        try:
                            if not os.listdir(root):
                                os.rmdir(root)
                        except OSError:
                            pass

                if store_cleaned:
                    result.cleaned_stores += 1
            except Exception as exc:
                result.errors.append(f"Error cleaning {eco} at {path}: {exc}")

        return result
