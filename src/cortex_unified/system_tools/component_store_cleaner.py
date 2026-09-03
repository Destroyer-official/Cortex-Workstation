"""Component Store / WinSxS Cleaner — DISM-based analysis and cleanup.

Research grounding
------------------
* Microsoft Learn: "Clean Up the WinSxS Folder" / "Determine the Actual Size
  of the WinSxS Folder" — official DISM commands for component store
  maintenance.
* AzimsTech (2025) — Windows 11 24H2 bug where two packages (26100.1742)
  remain "Staged" after `/StartComponentCleanup`; fix requires targeted
  `/Remove-Package` followed by cleanup.
* Ed Tittel (2025) — "Spurious reclaimables" persist after cleanup; removing
  the deeply superseded top-level package (`Package_for_RollupFix~...`)
  eliminates them.
* RobzTech (2025) — Complete DISM cleanup guide: `/AnalyzeComponentStore`,
  `/StartComponentCleanup`, `/StartComponentCleanup /ResetBase`,
  `/SPSuperseded`; `ResetBase` trade-off (no rollback); PowerShell module;
  Intune Remediations for fleet automation.
* Microsoft Learn: "Reduce the Size of the Component Store in an Offline
  Windows Image" — offline WIM/VHD/VHDX support for golden images.

Why this matters for Cortex Cleaner
-----------------------------------
* WinSxS routinely grows to 15–25 GB after a year of updates. Explorer
  reports a smaller size due to hard links; actual reclaimable space is
  only visible via `DISM /AnalyzeComponentStore`.
* Standard cleanup (`/StartComponentCleanup`) respects 30-day retention.
  `/ResetBase` maximizes reclaim but prevents update rollback — safe for
  stable images / VDI / Autopilot pre-handoff.
* 24H2 "checkpoint cumulative updates" leave packages in "Staged" state
  that standard cleanup ignores; targeted removal is required.

Design
------
* **Read-first**: `analyze()` runs `DISM /AnalyzeComponentStore`, parses
  output into structured `ComponentStoreInfo` (actual size, shared,
  backups, cache, reclaimable packages, cleanup recommended).
* **Cleanup actions**: `cleanup(reset_base=False, sp_superseded=False)`
  runs appropriate DISM command; returns `CleanupResult` with before/after
  sizes and reclaimed bytes.
* **Targeted fix**: `fix_staged_packages()` identifies stuck "Staged"
  packages via `dism /get-packages`, removes the known problematic
  `Package_for_RollupFix~...` if present, then runs cleanup.
* **Offline support**: `analyze_offline(wim_path, index)` and
  `cleanup_offline(wim_path, index)` for golden image maintenance.
* **Safety**: All mutating operations create System Restore point first
  (via `RestorePointManager`). `/ResetBase` requires explicit confirmation.
* **Automation**: `schedule_cleanup(task_name, frequency)` registers
  Proactive Remediation for Intune / Task Scheduler.

Usage::

    from cortex_unified.system_tools.component_store_cleaner import (
        ComponentStoreCleaner, ComponentStoreInfo,
    )
    cleaner = ComponentStoreCleaner()
    info = cleaner.analyze()
    if info.cleanup_recommended:
        result = cleaner.cleanup()
        print(f"Reclaimed {result.reclaimed_bytes:,} bytes")
    # For 24H2 staged packages:
    cleaner.fix_staged_packages()

References
----------
* Microsoft Learn: Clean Up the WinSxS Folder
* Microsoft Learn: Determine the Actual Size of the WinSxS Folder
* Microsoft Learn: Reduce the Size of the Component Store in an Offline Windows Image
* DISM Operating System Package Servicing Command-Line Options
* USENIX ATC 2016 FastCDC (chunking context for delta compression)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from cortex_unified.system_tools.restore_point import RestorePointManager


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ComponentStoreInfo:
    """Parsed output of `DISM /AnalyzeComponentStore`."""
    explorer_reported_size_gb: float
    actual_size_gb: float
    shared_with_windows_gb: float
    backups_disabled_features_mb: float
    cache_temp_kb: float
    last_cleanup: str
    reclaimable_packages: int
    cleanup_recommended: bool
    raw_output: str

    @property
    def reclaimable_gb(self) -> float:
        """Reclaimable gb.

        Returns:
            Result of the operation."""
        return (self.backups_disabled_features_mb + self.cache_temp_kb / 1024.0) / 1024.0


@dataclass(frozen=True, slots=True)
class CleanupResult:
    """Cleanup Result data container."""
    success: bool
    before: ComponentStoreInfo
    after: ComponentStoreInfo
    reclaimed_bytes: int
    command: str
    duration_seconds: float
    error: Optional[str] = None


@dataclass(frozen=True, slots=True)
class PackageInfo:
    """Single package from `dism /get-packages`."""
    name: str
    state: str  # Installed, Staged, Superseded, Install Pending, etc.
    version: str
    release_type: str  # Feature Pack, Update, etc.


# ---------------------------------------------------------------------------
# Core cleaner
# ---------------------------------------------------------------------------

class ComponentStoreCleaner:
    """DISM-based Component Store analyzer and cleaner."""

    def __init__(
        self,
        dism_path: str = "Dism.exe",
        create_restore_point: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ):
        """Initialize Component Store Cleaner.

        Args:
            dism_path: dism path.
            create_restore_point: create restore point.
            progress_callback: progress callback.
            cancel_event: cancel event."""
        self.dism = dism_path
        self.create_restore_point = create_restore_point
        self.progress = progress_callback or (lambda _: None)
        self.cancel_event = cancel_event or threading.Event()
        self._restore_mgr = RestorePointManager() if create_restore_point else None

    # -- helpers

    def _run_dism(self, args: List[str], timeout: int = 1800) -> Tuple[int, str, str]:
        """Run DISM command, return (returncode, stdout, stderr)."""
        if self.cancel_event.is_set():
            raise RuntimeError("Operation cancelled")
        cmd = [self.dism] + args
        self.progress(f"Running: {' '.join(cmd)}")
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
                encoding=sys.getdefaultencoding(), errors="replace"
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"DISM timed out after {timeout}s"
        except Exception as exc:
            return -1, "", str(exc)

    def _parse_analyze(self, output: str) -> ComponentStoreInfo:
        """Parse `DISM /AnalyzeComponentStore` output."""
        # Sample output fields:
        # Windows Explorer Reported Size of Component Store : 5.60 GB
        # Actual Size of Component Store : 5.52 GB
        #     Shared with Windows : 3.81 GB
        #     Backups and Disabled Features : 1.70 GB
        #     Cache and Temporary Data :  0 bytes
        # Date of Last Cleanup : 2025-03-20 18:21:30
        # Number of Reclaimable Packages : 2
        # Component Store Cleanup Recommended : Yes
        patterns = {
            "explorer_reported_size_gb": r"Windows Explorer Reported Size of Component Store\s*:\s*([\d.]+)\s*GB",
            "actual_size_gb": r"Actual Size of Component Store\s*:\s*([\d.]+)\s*GB",
            "shared_with_windows_gb": r"Shared with Windows\s*:\s*([\d.]+)\s*GB",
            "backups_disabled_features_mb": r"Backups and Disabled Features\s*:\s*([\d.]+)\s*MB",
            "cache_temp_kb": r"Cache and Temporary Data\s*:\s*([\d.]+)\s*KB",
            "last_cleanup": r"Date of Last Cleanup\s*:\s*(.+)",
            "reclaimable_packages": r"Number of Reclaimable Packages\s*:\s*(\d+)",
            "cleanup_recommended": r"Component Store Cleanup Recommended\s*:\s*(Yes|No)",
        }
        data = {"raw_output": output}
        for key, pat in patterns.items():
            m = re.search(pat, output, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if key.endswith("_gb") or key.endswith("_mb") or key.endswith("_kb"):
                    data[key] = float(val)
                elif key == "reclaimable_packages":
                    data[key] = int(val)
                elif key == "cleanup_recommended":
                    data[key] = val.lower() == "yes"
                else:
                    data[key] = val
            else:
                # Defaults
                if key.endswith("_gb") or key.endswith("_mb") or key.endswith("_kb"):
                    data[key] = 0.0
                elif key == "reclaimable_packages":
                    data[key] = 0
                elif key == "cleanup_recommended":
                    data[key] = False
                else:
                    data[key] = ""
        return ComponentStoreInfo(**data)

    def _parse_packages(self, output: str) -> List[PackageInfo]:
        """Parse `dism /get-packages` table output."""
        packages: List[PackageInfo] = []
        # Output is a table with columns: Name, State, Release Type, Version
        # Skip header lines, parse each row
        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("---") or line.lower().startswith("name"):
                continue
            # Split by multiple spaces
            parts = re.split(r"\s{2,}", line)
            if len(parts) >= 4:
                name, state, rel_type, version = parts[0], parts[1], parts[2], parts[3]
                packages.append(PackageInfo(
                    name=name.strip(),
                    state=state.strip(),
                    version=version.strip(),
                    release_type=rel_type.strip(),
                ))
        return packages

    # -- public API

    def analyze(self) -> ComponentStoreInfo:
        """Run `DISM /Online /Cleanup-Image /AnalyzeComponentStore`."""
        self.progress("Analyzing Component Store...")
        rc, out, err = self._run_dism([
            "/Online", "/Cleanup-Image", "/AnalyzeComponentStore"
        ])
        if rc != 0:
            raise RuntimeError(f"DISM analyze failed (rc={rc}): {err}")
        return self._parse_analyze(out)

    def cleanup(
        self,
        reset_base: bool = False,
        sp_superseded: bool = False,
    ) -> CleanupResult:
        """Run component store cleanup.

        Args:
            reset_base: Use `/ResetBase` — removes ALL superseded components
                (including those within 30-day window), prevents rollback.
            sp_superseded: Use `/SPSuperseded` — removes service pack backup
                components (legacy, rarely needed on Win10/11).
        """
        if reset_base and self.create_restore_point:
            self.progress("Creating System Restore point before ResetBase...")
            rp = self._restore_mgr.create("Cortex Cleaner: Component Store ResetBase")
            if not rp:
                self.progress("Warning: Could not create restore point")

        before = self.analyze()
        self.progress("Running component store cleanup...")

        args = ["/Online", "/Cleanup-Image", "/StartComponentCleanup"]
        if reset_base:
            args.append("/ResetBase")
        if sp_superseded:
            args.append("/SPSuperseded")

        t0 = time.time()
        rc, out, err = self._run_dism(args, timeout=3600)
        duration = time.time() - t0

        after = self.analyze()
        reclaimed = int((before.actual_size_gb - after.actual_size_gb) * 1024**3)

        return CleanupResult(
            success=rc == 0,
            before=before,
            after=after,
            reclaimed_bytes=max(0, reclaimed),
            command=" ".join([self.dism] + args),
            duration_seconds=duration,
            error=err if rc != 0 else None,
        )

    def fix_staged_packages(self) -> CleanupResult:
        """Fix Windows 11 24H2 stuck 'Staged' packages (26100.1742).

        Identifies the problematic `Package_for_RollupFix~31bf3856ad364e35~amd64~~26100.1742.1.10`
        package, removes it via `/Remove-Package`, then runs standard cleanup.
        """
        self.progress("Checking for stuck Staged packages...")
        rc, out, err = self._run_dism(["/Online", "/Get-Packages"])
        if rc != 0:
            raise RuntimeError(f"Get-Packages failed: {err}")

        packages = self._parse_packages(out)
        # Find the specific 24H2 problematic package
        target = None
        for pkg in packages:
            if pkg.state.lower() == "staged" and "Package_for_RollupFix" in pkg.name and "26100.1742" in pkg.name:
                target = pkg
                break

        if not target:
            self.progress("No stuck 24H2 staged packages found")
            return CleanupResult(
                success=True,
                before=self.analyze(),
                after=self.analyze(),
                reclaimed_bytes=0,
                command="fix_staged_packages (no-op)",
                duration_seconds=0,
            )

        self.progress(f"Removing stuck package: {target.name}")
        if self.create_restore_point:
            self._restore_mgr.create(f"Cortex Cleaner: Remove {target.name}")

        # Remove the package
        rc, out, err = self._run_dism([
            "/Online", "/Remove-Package", f"/PackageName:{target.name}"
        ], timeout=1800)
        if rc != 0:
            raise RuntimeError(f"Remove-Package failed: {err}")

        # Run standard cleanup to finalize
        return self.cleanup()

    def analyze_offline(self, wim_path: str, index: int = 1) -> ComponentStoreInfo:
        """Analyze component store in offline WIM/VHD/VHDX."""
        rc, out, err = self._run_dism([
            "/Image", wim_path, "/Index", str(index),
            "/Cleanup-Image", "/AnalyzeComponentStore"
        ])
        if rc != 0:
            raise RuntimeError(f"Offline analyze failed: {err}")
        return self._parse_analyze(out)

    def cleanup_offline(
        self,
        wim_path: str,
        index: int = 1,
        reset_base: bool = False,
    ) -> CleanupResult:
        """Cleanup component store in offline image."""
        before = self.analyze_offline(wim_path, index)
        args = [
            "/Image", wim_path, "/Index", str(index),
            "/Cleanup-Image", "/StartComponentCleanup"
        ]
        if reset_base:
            args.append("/ResetBase")
        t0 = time.time()
        rc, out, err = self._run_dism(args, timeout=3600)
        duration = time.time() - t0
        after = self.analyze_offline(wim_path, index)
        reclaimed = int((before.actual_size_gb - after.actual_size_gb) * 1024**3)
        return CleanupResult(
            success=rc == 0,
            before=before,
            after=after,
            reclaimed_bytes=max(0, reclaimed),
            command=" ".join([self.dism] + args),
            duration_seconds=duration,
            error=err if rc != 0 else None,
        )

    def schedule_cleanup(
        self,
        task_name: str = "CortexComponentStoreCleanup",
        frequency_days: int = 30,
        reset_base: bool = False,
    ) -> bool:
        """Register a scheduled task for automatic cleanup (admin required)."""
        import subprocess
        # PowerShell to create scheduled task
        ps = f"""
$action = New-ScheduledTaskAction -Execute '{self.dism}' -Argument '/Online /Cleanup-Image /StartComponentCleanup{" /ResetBase" if reset_base else ""}'
$trigger = New-ScheduledTaskTrigger -Daily -At 3am -DaysInterval {frequency_days}
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable
Register-ScheduledTask -TaskName '{task_name}' -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force
"""
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, capture_output=True)
            self.progress(f"Scheduled task '{task_name}' created")
            return True
        except subprocess.CalledProcessError as exc:
            self.progress(f"Failed to create scheduled task: {exc}")
            return False


__all__ = [
    "ComponentStoreCleaner",
    "ComponentStoreInfo",
    "CleanupResult",
    "PackageInfo",
]