"""Cortex Cleaner — Windows Shellbags & JumpLists Activity Forensics Purger.

Scans and purges Windows Explorer historical activity artifacts:
1. Shellbags Registry Keys (BagMRU, Bags) which record folder view history and directory accesses.
2. Windows JumpLists (AutomaticDestinations, CustomDestinations).
3. Windows Recent Items (%AppData%\\Microsoft\\Windows\\Recent).
4. Explorer Run dialog MRU and TypedPaths.
"""

from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if platform.system() == "Windows":
    import winreg
else:
    winreg = None


@dataclass
class ShellbagsTarget:
    """Shellbagstarget.

    Manages ShellbagsTarget operations and coordinates related state changes for the component.
    """
    category: str
    target_type: str  # "Registry", "File Directory"
    path: str
    items_count: int
    size_bytes: int


@dataclass
class ShellbagsCleanResult:
    """Shellbagscleanresult.

    Manages ShellbagsCleanResult operations and coordinates related state changes for the component.
    """
    registry_keys_cleared: int
    files_deleted: int
    bytes_freed: int
    errors: List[str] = None

    def __post_init__(self):
        """__post_init__.

        Manages post init operations and coordinates related state changes for the component.
        """
        if self.errors is None:
            self.errors = []


class ShellbagsPrivacyCleaner:
    """Shellbagsprivacycleaner.

    Manages ShellbagsPrivacyCleaner operations and coordinates related state changes for the component.
    """

    SHELL_REG_PATHS = [
        r"Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\BagMRU",
        r"Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\Bags",
        r"Software\Microsoft\Windows\Shell\BagMRU",
        r"Software\Microsoft\Windows\Shell\Bags",
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU",
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths",
    ]

    @classmethod
    def _count_reg_keys(cls, subkey: str) -> int:
        """Count subkeys and values in a registry key.

        Manages count reg keys operations and coordinates related state changes for the component.

        Args:
            subkey (str): The subkey parameter.

        Returns:
            int: Result of the operation.
        """
        if winreg is None:
            return 0
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_READ) as key:
                info = winreg.QueryInfoKey(key)
                return info[0] + info[1]  # subkeys + values
        except Exception:
            return 0

    @classmethod
    def _delete_reg_tree(cls, subkey: str) -> int:
        """Recursively delete a registry key tree.

        Manages delete reg tree operations and coordinates related state changes for the component.

        Args:
            subkey (str): The subkey parameter.

        Returns:
            int: Result of the operation.
        """
        if winreg is None:
            return 0
        deleted_count = 0
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
                while True:
                    try:
                        child = winreg.EnumKey(key, 0)
                        deleted_count += cls._delete_reg_tree(f"{subkey}\\{child}")
                    except OSError:
                        break
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, subkey)
            deleted_count += 1
        except Exception:
            pass
        return deleted_count

    @classmethod
    def scan_shell_activity(cls) -> List[ShellbagsTarget]:
        """Scan system for all Shellbag and Explorer activity artifacts.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Returns:
            List[ShellbagsTarget]: List of processed items or identifiers.
        """
        targets: List[ShellbagsTarget] = []

        # 1. Registry Shellbags & MRU
        if winreg is not None:
            for r_path in cls.SHELL_REG_PATHS:
                cnt = cls._count_reg_keys(r_path)
                if cnt > 0:
                    cat_name = "Shellbags Folder History" if "Bag" in r_path else "Explorer Typed MRU"
                    targets.append(ShellbagsTarget(
                        category=cat_name,
                        target_type="Registry",
                        path=f"HKCU\\{r_path}",
                        items_count=cnt,
                        size_bytes=cnt * 256,  # ~256 bytes per MRU entry estimate
                    ))

        # 2. File paths: Recent, JumpLists
        app_data = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        recent_dir = app_data / "Microsoft" / "Windows" / "Recent"
        auto_dest = recent_dir / "AutomaticDestinations"
        cust_dest = recent_dir / "CustomDestinations"

        file_locations = [
            ("Recent Items Shortcuts", recent_dir, False),
            ("JumpLists (Automatic)", auto_dest, True),
            ("JumpLists (Custom)", cust_dest, True),
        ]

        for name, p_dir, is_rec in file_locations:
            if not p_dir.is_dir():
                continue
            sz = 0
            cnt = 0
            try:
                for entry in os.scandir(p_dir):
                    if entry.is_file():
                        try:
                            sz += entry.stat().st_size
                            cnt += 1
                        except Exception:
                            pass
            except Exception:
                pass

            if cnt > 0:
                targets.append(ShellbagsTarget(
                    category=name,
                    target_type="File Directory",
                    path=str(p_dir),
                    items_count=cnt,
                    size_bytes=sz,
                ))

        return targets

    @classmethod
    def clean_shell_activity(cls, targets: Optional[List[ShellbagsTarget]] = None) -> ShellbagsCleanResult:
        """Purge selected or all Explorer activity and Shellbag targets.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

        Args:
            targets (Optional[List[ShellbagsTarget]]): The targets parameter.

        Returns:
            ShellbagsCleanResult: Result of the operation.
        """
        result = ShellbagsCleanResult(0, 0, 0)
        scan_items = targets or cls.scan_shell_activity()

        for t in scan_items:
            if t.target_type == "Registry":
                if t.path.startswith("HKCU\\"):
                    sub = t.path[5:]
                    cnt = cls._delete_reg_tree(sub)
                    result.registry_keys_cleared += cnt
                    result.bytes_freed += t.size_bytes
            elif t.target_type == "File Directory":
                p = Path(t.path)
                if p.is_dir():
                    try:
                        for entry in os.scandir(p):
                            if entry.is_file():
                                try:
                                    sz = entry.stat().st_size
                                    os.unlink(entry.path)
                                    result.files_deleted += 1
                                    result.bytes_freed += sz
                                except Exception:
                                    pass
                    except Exception as exc:
                        result.errors.append(f"{t.category}: {exc}")

        return result
