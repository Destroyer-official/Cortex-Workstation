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
    """Cacherebuildreport.

    Manages CacheRebuildReport operations and coordinates related state changes for the component.
    """
    icon_cache_rebuilt: bool = False
    thumb_cache_rebuilt: bool = False
    font_cache_rebuilt: bool = False
    shell_notified: bool = False
    files_deleted: int = 0
    bytes_freed: int = 0
    errors: List[str] = None

    def __post_init__(self):
        """__post_init__.

        Manages post init operations and coordinates related state changes for the component.
        """
        if self.errors is None:
            self.errors = []


class SystemCacheRebuilder:
    """Systemcacherebuilder.

    Manages SystemCacheRebuilder operations and coordinates related state changes for the component.
    """

    @classmethod
    def rebuild_font_cache(cls) -> Tuple[bool, int, int, List[str]]:
        """Stop FontCache service, delete cached .dat files, and restart service.

        Manages rebuild font cache operations and coordinates related state changes for the component.

        Returns:
            Tuple[bool, int, int, List[str]]: List of processed items or identifiers.
        """
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
        """Purge IconCache.db, iconcache_*.db, and thumbcache_*.db files.

        Manages rebuild icon thumbnail cache operations and coordinates related state changes for the component.

        Returns:
            Tuple[bool, int, int, List[str]]: List of processed items or identifiers.
        """
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
        """Issue Windows Shell change notification to reload icons without killing explorer.

        Manages notify shell refresh operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
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
        """Restart Windows Explorer safely without leaving a black screen.

        Terminates the existing Explorer instance gracefully and restarts it
        using the native Windows ShellExecute API to ensure the taskbar and desktop
        shell are fully restored.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        if platform.system() != "Windows":
            return False

        windir = os.environ.get("WINDIR", r"C:\Windows")
        explorer_path = os.path.join(windir, "explorer.exe")

        try:
            # 1. First broadcast shell change notification so caches reload
            cls.notify_shell_refresh()

            # 2. Attempt graceful close (without /f) so Explorer saves its state
            try:
                subprocess.run(["taskkill", "/im", "explorer.exe"], capture_output=True, timeout=3)
            except Exception:
                pass
            time.sleep(0.8)

            # Check if explorer is still running; only force kill if stuck
            try:
                import psutil
                explorer_alive = any((p.name() or "").lower() == "explorer.exe" for p in psutil.process_iter(["name"]))
            except Exception:
                explorer_alive = False

            if explorer_alive:
                subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], capture_output=True, timeout=4)
                time.sleep(1.0)

            # 3. Restart Explorer via native ShellExecute to guarantee desktop initialization
            restarted = False
            try:
                ret = ctypes.windll.shell32.ShellExecuteW(None, "open", explorer_path, None, windir, 1)
                if ret > 32:  # ShellExecute returns > 32 on success
                    restarted = True
            except Exception:
                pass

            # Fallback to detached cmd /c start if ShellExecute didn't launch
            if not restarted:
                try:
                    subprocess.Popen(
                        ["cmd.exe", "/c", "start", "", explorer_path],
                        cwd=windir,
                        creationflags=getattr(subprocess, "DETACHED_PROCESS", 0x00000008),
                    )
                except Exception:
                    subprocess.Popen([explorer_path], cwd=windir)

            time.sleep(0.5)
            return True
        except Exception:
            # Emergency fallback: ensure explorer is launched
            try:
                ctypes.windll.shell32.ShellExecuteW(None, "open", explorer_path, None, windir, 1)
            except Exception:
                pass
            return False

    @classmethod
    def execute_full_cache_rebuild(cls, restart_shell: bool = False) -> CacheRebuildReport:
        """Run a full system cache rebuild across fonts, icons, thumbnails, and shell.

        Manages execute full cache rebuild operations and coordinates related state changes for the component.

        Args:
            restart_shell (bool): The restart shell parameter.

        Returns:
            CacheRebuildReport: Result of the operation.
        """
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
        # Always issue non-destructive shell change notification
        report.shell_notified = cls.notify_shell_refresh()
        if restart_shell:
            cls.restart_explorer()

        return report

