"""Cortex Cleaner — Windows Font, Icon & Thumbnail Cache Rebuilder.

Purges corrupted Windows icon databases (IconCache.db, iconcache_*.db, thumbcache_*.db),
rebuilds the system Font Cache (FontCache service stop + DAT purge + restart),
and issues shell refresh notifications / explorer restart to repair UI corruption.
"""

from __future__ import annotations

import ctypes
import glob
import os
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass
class CacheRebuildReport:
    """Cache Rebuild Report data container."""
    icon_cache_rebuilt: bool = False
    thumb_cache_rebuilt: bool = False
    font_cache_rebuilt: bool = False
    shell_notified: bool = False
    files_deleted: int = 0
    bytes_freed: int = 0
    errors: List[str] = None

    def __post_init__(self):
        """__post_init__."""
        if self.errors is None:
            self.errors = []
        """__post_init__."""
        """__post_init__."""


class SystemCacheRebuilder:
    """Production Windows system cache recovery and rebuilding toolkit."""

    @classmethod
    def rebuild_font_cache(cls) -> Tuple[bool, int, int, List[str]]:
        """Stop FontCache service, delete cached .dat files, and restart service."""
        if platform.system() != "Windows":
            return False, 0, 0, ["Windows only"]

        errors: List[str] = []
        files_deleted = 0
        bytes_freed = 0

        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        font_cache_dirs = [
            windir / "ServiceProfiles" / "LocalService" / "AppData" / "Local",
            windir / "System32",
        ]

        # 1. Stop FontCache service
        try:
            subprocess.run(["net", "stop", "FontCache", "/y"], capture_output=True, timeout=10)
        except Exception:
            pass

        # 2. Delete font cache dat files
        patterns = [
            str(windir / "ServiceProfiles" / "LocalService" / "AppData" / "Local" / "FontCache*.dat"),
            str(windir / "ServiceProfiles" / "LocalService" / "AppData" / "Local" / "~FontCache*.dat"),
            str(windir / "System32" / "FNTCACHE.DAT"),
        ]

        for pat in patterns:
            for f in glob.glob(pat):
                try:
                    f_size = os.path.getsize(f)
                    os.remove(f)
                    files_deleted += 1
                    bytes_freed += f_size
                except Exception as exc:
                    errors.append(f"Failed to delete {f}: {exc}")

        # 3. Start FontCache service
        try:
            subprocess.run(["net", "start", "FontCache"], capture_output=True, timeout=10)
        except Exception as exc:
            errors.append(f"Failed to restart FontCache service: {exc}")

        return (len(errors) == 0 or files_deleted > 0), files_deleted, bytes_freed, errors

    @classmethod
    def rebuild_icon_thumbnail_cache(cls) -> Tuple[bool, int, int, List[str]]:
        """Purge IconCache.db, iconcache_*.db, and thumbcache_*.db files."""
        if platform.system() != "Windows":
            return False, 0, 0, ["Windows only"]

        errors: List[str] = []
        files_deleted = 0
        bytes_freed = 0

        local_app_data = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        explorer_cache_dir = local_app_data / "Microsoft" / "Windows" / "Explorer"

        patterns = [
            str(local_app_data / "IconCache.db"),
            str(explorer_cache_dir / "iconcache_*.db"),
            str(explorer_cache_dir / "thumbcache_*.db"),
        ]

        for pat in patterns:
            for f in glob.glob(pat):
                try:
                    f_size = os.path.getsize(f)
                    os.remove(f)
                    files_deleted += 1
                    bytes_freed += f_size
                except Exception as exc:
                    errors.append(f"Could not delete locked cache file {Path(f).name}: {exc}")

        return True, files_deleted, bytes_freed, errors

    @classmethod
    def notify_shell_refresh(cls) -> bool:
        """Issue Windows Shell change notification to reload icons without killing explorer."""
        if platform.system() != "Windows":
            return False

        try:
            shell32 = ctypes.windll.shell32
            # SHCNE_ASSOCCHANGED = 0x08000000, SHCNF_IDLIST = 0x0000
            shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
            return True
        except Exception:
            return False

    @classmethod
    def restart_explorer(cls) -> bool:
        """Gracefully terminate and restart Windows Explorer."""
        if platform.system() != "Windows":
            return False

        try:
            subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], capture_output=True, timeout=5)
            time.sleep(1)
            subprocess.Popen(["explorer.exe"])
            return True
        except Exception:
            return False

    @classmethod
    def execute_full_cache_rebuild(cls, restart_shell: bool = False) -> CacheRebuildReport:
        """Run a full system cache rebuild across fonts, icons, thumbnails, and shell."""
        report = CacheRebuildReport()

        # Font Cache
        ok_font, f_del, f_bytes, f_errs = cls.rebuild_font_cache()
        report.font_cache_rebuilt = ok_font
        report.files_deleted += f_del
        report.bytes_freed += f_bytes
        report.errors.extend(f_errs)

        # Icon & Thumbnail Cache
        ok_icon, i_del, i_bytes, i_errs = cls.rebuild_icon_thumbnail_cache()
        report.icon_cache_rebuilt = ok_icon
        report.thumb_cache_rebuilt = ok_icon
        report.files_deleted += i_del
        report.bytes_freed += i_bytes
        report.errors.extend(i_errs)

        # Shell Notification / Restart
        if restart_shell:
            cls.restart_explorer()
            report.shell_notified = True
        else:
            report.shell_notified = cls.notify_shell_refresh()

        return report
