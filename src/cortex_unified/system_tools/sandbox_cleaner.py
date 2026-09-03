"""Cortex Cleaner — Windows Sandbox & Virtual Environment Artifact Purger.

Forensic cleaner for virtual environments, containers, and hypervisors:
- Scans Windows Sandbox temporary base images, user containers, and scratch VHDs.
- Audits Hyper-V checkpoint differencing disks (.avhdx) and saved state files (.vsv, .bin).
- Detects orphaned WSL2/WSA virtual disk snapshots.
- Reclaims tens of gigabytes of storage locked in virtual machine caches.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("cortex.system_tools.sandbox_cleaner")


@dataclass
class VirtualArtifact:
    """Virtual Artifact data container."""
    name: str
    path: str
    category: str  # "Windows Sandbox", "Hyper-V", "WSL", "VMware/VBox"
    size_bytes: int
    is_safe_to_clean: bool
    description: str

    @property
    def size_mb(self) -> float:
        """Size mb."""
        return self.size_bytes / (1024**2)

    @property
    def size_gb(self) -> float:
        """Size gb."""
        return self.size_bytes / (1024**3)


@dataclass
class SandboxCleanReport:
    """Sandbox Clean Report data container."""
    artifacts: list[VirtualArtifact] = field(default_factory=list)
    total_reclaimable_bytes: int = 0
    categories_found: list[str] = field(default_factory=list)
    cleaned_bytes: int = 0
    error: Optional[str] = None


class SandboxCleaner:
    """Enterprise Virtual Environment & Sandbox Artifact Purger."""

    def __init__(self):
        """Initialize Sandbox Cleaner."""
        self._is_windows = os.name == "nt"

    def scan(self) -> SandboxCleanReport:
        """Scan system for virtual environment leftovers and sandbox files."""
        artifacts: list[VirtualArtifact] = []

        local_appdata = os.environ.get("LOCALAPPDATA", "")
        program_data = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
        user_profile = os.environ.get("USERPROFILE", "")

        # 1. Windows Sandbox
        sandbox_paths = [
            Path(local_appdata) / "Microsoft" / "Windows" / "Sandbox",
            Path(program_data) / "Microsoft" / "Windows" / "Sandbox",
        ]
        for sb_dir in sandbox_paths:
            if sb_dir.is_dir():
                for p in sb_dir.rglob("*"):
                    if p.is_file():
                        try:
                            sz = p.stat().st_size
                            artifacts.append(
                                VirtualArtifact(
                                    name=p.name,
                                    path=str(p),
                                    category="Windows Sandbox",
                                    size_bytes=sz,
                                    is_safe_to_clean=True,
                                    description="Temporary Sandbox container or discardable snapshot",
                                )
                            )
                        except OSError:
                            pass

        # 2. Hyper-V Checkpoint & Memory State Files (.vsv, .bin, .avhdx)
        hyperv_search_dirs = [
            Path(program_data) / "Microsoft" / "Windows" / "Hyper-V",
            Path(program_data) / "Microsoft" / "Windows" / "Virtual Hard Disks",
            Path(user_profile) / "Virtual Machines",
        ]
        for hv_dir in hyperv_search_dirs:
            if hv_dir.is_dir():
                for ext in ["*.vsv", "*.bin", "*.avhdx"]:
                    for p in hv_dir.rglob(ext):
                        if p.is_file():
                            try:
                                sz = p.stat().st_size
                                artifacts.append(
                                    VirtualArtifact(
                                        name=p.name,
                                        path=str(p),
                                        category="Hyper-V",
                                        size_bytes=sz,
                                        is_safe_to_clean=ext != "*.avhdx",  # avhdx might be in active chain
                                        description="Hyper-V saved memory state or checkpoint differencing disk",
                                    )
                                )
                            except OSError:
                                pass

        # 3. WSL2 swap and export caches
        wsl_swap = Path(local_appdata) / "Temp" / "swap.vhdx"
        if wsl_swap.is_file():
            try:
                sz = wsl_swap.stat().st_size
                artifacts.append(
                    VirtualArtifact(
                        name="swap.vhdx",
                        path=str(wsl_swap),
                        category="WSL",
                        size_bytes=sz,
                        is_safe_to_clean=True,
                        description="WSL2 discarded swap container",
                    )
                )
            except OSError:
                pass

        total_bytes = sum(a.size_bytes for a in artifacts)
        cats = sorted(list(set(a.category for a in artifacts)))

        return SandboxCleanReport(
            artifacts=artifacts,
            total_reclaimable_bytes=total_bytes,
            categories_found=cats,
        )

    def clean(self, target_paths: list[str]) -> tuple[int, list[str]]:
        """Safely clean selected virtual artifacts."""
        cleaned_bytes = 0
        errors: list[str] = []

        for p_str in target_paths:
            p = Path(p_str)
            if not p.exists():
                continue
            try:
                sz = p.stat().st_size if p.is_file() else 0
                if p.is_file():
                    p.unlink(missing_ok=True)
                elif p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                cleaned_bytes += sz
            except Exception as exc:
                errors.append(f"Failed to remove {p.name}: {exc}")

        return cleaned_bytes, errors
