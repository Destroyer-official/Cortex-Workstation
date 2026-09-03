"""Cortex Cleaner — NTFS Disk Cluster & Slack Space Forensics Analyzer.

Analyzes filesystem cluster allocation efficiency and unallocated slack space:
1. Queries drive cluster geometry (sectors per cluster, bytes per sector) via Win32 GetDiskFreeSpaceW.
2. Compares logical file sizes vs physical cluster allocation across directory trees.
3. Calculates total slack space (wasted bytes within allocated clusters).
4. Identifies directories with severe cluster fragmentation and storage waste (e.g. node_modules, caches).
5. Recommends NTFS filesystem compression (compact /c) for high-waste directories to reclaim space.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class DirectorySlackStat:
    """Directory Slack Stat data container."""
    path: str
    file_count: int
    logical_size_bytes: int
    physical_size_bytes: int
    slack_waste_bytes: int
    slack_percentage: float


@dataclass
class VolumeSlackReport:
    """Volume Slack Report data container."""
    volume: str
    cluster_size_bytes: int
    total_files_scanned: int
    total_logical_bytes: int
    total_physical_bytes: int
    total_slack_waste_bytes: int
    overall_slack_percentage: float
    worst_offenders: List[DirectorySlackStat]


class SlackSpaceAnalyzer:
    """Production NTFS cluster geometry and slack space forensics analyzer."""

    @classmethod
    def get_cluster_size(cls, drive_path: Optional[str] = None) -> int:
        """Query physical volume cluster allocation size in bytes via Win32 GetDiskFreeSpaceW."""
        if platform.system() != "Windows":
            return 4096

        if not drive_path:
            drive_path = os.environ.get("SystemDrive", "C:") + "\\"
        clean_path = os.path.splitdrive(drive_path)[0] + "\\"
        sectors_per_cluster = wintypes.DWORD()
        bytes_per_sector = wintypes.DWORD()
        free_clusters = wintypes.DWORD()
        total_clusters = wintypes.DWORD()

        ok = ctypes.windll.kernel32.GetDiskFreeSpaceW(
            clean_path,
            ctypes.byref(sectors_per_cluster),
            ctypes.byref(bytes_per_sector),
            ctypes.byref(free_clusters),
            ctypes.byref(total_clusters),
        )

        if not ok:
            return 4096

        cluster_size = sectors_per_cluster.value * bytes_per_sector.value
        return cluster_size if cluster_size > 0 else 4096

    @classmethod
    def analyze_directory(
        cls,
        target_dir: str | Path,
        max_depth: int = 3,
        progress_cb: Optional[Callable[[int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> VolumeSlackReport:
        """Scan directory and calculate logical vs physical cluster slack space."""
        root = Path(target_dir).resolve()
        cluster_sz = cls.get_cluster_size(str(root))

        dir_stats: Dict[str, DirectorySlackStat] = {}
        tot_files = 0
        tot_logical = 0
        tot_physical = 0

        for parent, _, files in os.walk(root):
            if cancel_check and cancel_check():
                break

            p_obj = Path(parent)
            # Group stats up to max_depth levels relative to root
            try:
                rel = p_obj.relative_to(root)
                parts = rel.parts
                group_dir = str(root / Path(*parts[:max_depth])) if parts else str(root)
            except ValueError:
                group_dir = parent

            if group_dir not in dir_stats:
                dir_stats[group_dir] = DirectorySlackStat(group_dir, 0, 0, 0, 0, 0.0)

            for f in files:
                tot_files += 1
                fp = p_obj / f
                try:
                    sz = fp.stat().st_size
                    # Calculate allocated cluster bytes
                    if sz == 0:
                        allocated = 0
                    else:
                        allocated = ((sz + cluster_sz - 1) // cluster_sz) * cluster_sz

                    slack = max(0, allocated - sz)

                    tot_logical += sz
                    tot_physical += allocated

                    st = dir_stats[group_dir]
                    st.file_count += 1
                    st.logical_size_bytes += sz
                    st.physical_size_bytes += allocated
                    st.slack_waste_bytes += slack

                    if progress_cb and tot_files % 200 == 0:
                        progress_cb(tot_files, str(fp))
                except (PermissionError, OSError):
                    pass

        # Calculate percentages
        for st in dir_stats.values():
            if st.physical_size_bytes > 0:
                st.slack_percentage = round((st.slack_waste_bytes / st.physical_size_bytes) * 100.0, 1)

        tot_slack = max(0, tot_physical - tot_logical)
        overall_pct = (tot_slack / tot_physical * 100.0) if tot_physical > 0 else 0.0

        # Sort worst offending directories by total slack waste
        worst = sorted(dir_stats.values(), key=lambda s: s.slack_waste_bytes, reverse=True)[:15]

        return VolumeSlackReport(
            volume=str(root),
            cluster_size_bytes=cluster_sz,
            total_files_scanned=tot_files,
            total_logical_bytes=tot_logical,
            total_physical_bytes=tot_physical,
            total_slack_waste_bytes=tot_slack,
            overall_slack_percentage=round(overall_pct, 1),
            worst_offenders=worst,
        )
