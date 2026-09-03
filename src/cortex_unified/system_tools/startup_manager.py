"""Startup item enumeration and disabling across platforms.

Reads autostart locations read-only: registry Run/RunOnce keys, Startup
folders, launchd plists, XDG .desktop files. Disabling is implemented for
Windows only. Every failed location increments ``error_count`` instead of
aborting, so one broken source never hides the others.
"""

import os
import platform
from pathlib import Path
from typing import List, Dict

from ..core.config import Config

class StartupManager:
    """Enumerate autostart entries; disable them on Windows."""

    def __init__(self, config: Config = None):
        """Use *config* or a default Config; the OS decides which backends run."""
        self.config = config or Config()
        self.system = platform.system().lower()

        self.startup_items = []
        self.error_count = 0
    
    def list_startup_items(self) -> List[Dict]:
        """Populate ``startup_items`` from every autostart location for this OS."""
        self.startup_items = []
        self.error_count = 0
        
        try:
            if self.system == "windows":
                self._list_windows_startup_items()
            elif self.system == "darwin":  # macOS
                self._list_macos_startup_items()
            elif self.system == "linux":
                self._list_linux_startup_items()
        except Exception:
            self.error_count += 1
        
        return self.startup_items
    
    def _list_windows_startup_items(self):
        """Collect registry Run/RunOnce values plus Startup-folder files."""
        try:
            # Registry-based items: HKCU/HKLM x Run/RunOnce.
            try:
                import winreg
                
                self._read_registry_startup_items(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run"
                )
                
                self._read_registry_startup_items(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"Software\Microsoft\Windows\CurrentVersion\Run"
                )
                
                self._read_registry_startup_items(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\RunOnce"
                )
                
                self._read_registry_startup_items(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"Software\Microsoft\Windows\CurrentVersion\RunOnce"
                )
            except Exception:
                self.error_count += 1
            
            # File-based items: per-user and all-users Startup folders.
            try:
                startup_folder = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
                self._read_startup_folder_items(startup_folder)
                
                all_users_startup = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
                self._read_startup_folder_items(all_users_startup)
            except Exception:
                self.error_count += 1
                
        except Exception:
            self.error_count += 1
    
    def _read_registry_startup_items(self, hive, key_path):
        """Append every value under one Run/RunOnce key."""
        try:
            import winreg
            
            with winreg.OpenKey(hive, key_path) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        self.startup_items.append({
                            "name": name,
                            "path": value,
                            "location": f"Registry: {key_path}",
                            "enabled": True,
                            "type": "registry"
                        })
                        i += 1
                    except WindowsError:
                        break
        except Exception:
            self.error_count += 1
    
    def _read_startup_folder_items(self, folder_path: Path):
        """Append each file in one Startup folder."""
        try:
            if folder_path.exists():
                for item in folder_path.iterdir():
                    if item.is_file():
                        self.startup_items.append({
                            "name": item.name,
                            "path": str(item),
                            "location": f"Startup Folder: {folder_path}",
                            "enabled": True,
                            "type": "file"
                        })
        except Exception:
            self.error_count += 1
    
    def _list_macos_startup_items(self):
        try:
            # Launch agents in ~/Library/LaunchAgents
            user_agents = Path.home() / "Library" / "LaunchAgents"
            self._read_plist_items(user_agents)
            
            # Launch agents in /Library/LaunchAgents
            system_agents = Path("/Library/LaunchAgents")
            self._read_plist_items(system_agents)
            
            # Launch daemons in /Library/LaunchDaemons
            system_daemons = Path("/Library/LaunchDaemons")
            self._read_plist_items(system_daemons)
        except Exception:
            self.error_count += 1
        """_list_macos_startup_items."""
        """_list_macos_startup_items."""
    
    def _read_plist_items(self, folder_path: Path):
        """Append each launchd plist in one folder (name only, no parsing)."""
        try:
            if folder_path.exists():
                for plist_file in folder_path.glob("*.plist"):
                    try:
                        plist_name = plist_file.stem
                        self.startup_items.append({
                            "name": plist_name,
                            "path": str(plist_file),
                            "location": f"Plist: {folder_path}",
                            "enabled": True,  # Assume enabled
                            "type": "plist"
                        })
                    except Exception:
                        continue
        except Exception:
            self.error_count += 1
    
    def _list_linux_startup_items(self):
        try:
            # Autostart directory items
            autostart_dirs = [
                Path.home() / ".config" / "autostart",
                Path("/etc/xdg/autostart")
            ]
            
            for autostart_dir in autostart_dirs:
                self._read_desktop_items(autostart_dir)
        except Exception:
            self.error_count += 1
        """_list_linux_startup_items."""
        """_list_linux_startup_items."""
    
    def _read_desktop_items(self, folder_path: Path):
        """Read startup items from Linux .desktop files."""
        try:
            if folder_path.exists():
                for desktop_file in folder_path.glob("*.desktop"):
                    try:
                        # Try to read basic info from desktop file
                        self.startup_items.append({
                            "name": desktop_file.name,
                            "path": str(desktop_file),
                            "location": f"Desktop: {folder_path}",
                            "enabled": True,  # Assume enabled
                            "type": "desktop"
                        })
                    except Exception:
                        continue
        except Exception:
            self.error_count += 1
    
    def _registry_backup_path(self) -> Path:
        """JSON sidecar where disabled Run/RunOnce values are preserved."""
        return Path.home() / "StartupBackup" / "disabled_registry_backup.json"

    def _load_registry_backup(self) -> Dict[str, dict]:
        try:
            import json
            with open(self._registry_backup_path(), encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
        """_load_registry_backup."""
        """_load_registry_backup."""

    def _save_registry_backup(self, backup: Dict[str, dict]) -> None:
        try:
            import json
            self._registry_backup_path().parent.mkdir(exist_ok=True)
            with open(self._registry_backup_path(), "w", encoding="utf-8") as handle:
                json.dump(backup, handle, indent=2)
        except Exception:
            pass
        """_save_registry_backup."""
        """_save_registry_backup."""

    def enable_startup_item(self, item_name: str) -> bool:
        """
        Re-enable a previously disabled startup item.

        File-based items are restored from ``~/StartupBackup`` (where
        :meth:`_disable_startup_folder_item` moves them). Registry items are
        restored from the JSON sidecar written at disable time; without that
        record the original value cannot be reconstructed, so this returns
        False rather than guessing.

        Args:
            item_name: The ``name`` of the startup item.

        Returns:
            bool: True if the item was restored successfully.
        """
        try:
            if platform.system() != "Windows":
                return False
            target = None
            for item in self.startup_items:
                if item.get("name") == item_name:
                    target = item
                    break
            if target is None and not item_name:
                return False

            wanted = (target or {}).get("name", item_name)

            # File items: move the newest matching backup back into place.
            backup_folder = Path.home() / "StartupBackup"
            if backup_folder.exists():
                candidates = sorted(
                    backup_folder.glob(wanted + "*"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                startup_folders = [
                    Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows"
                    / "Start Menu" / "Programs" / "Startup",
                    Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
                    / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
                ]
                for candidate in candidates:
                    if candidate.suffix.lower() == ".json":
                        continue
                    for folder in startup_folders:
                        destination = folder / candidate.name
                        if destination.exists():
                            continue
                        try:
                            folder.mkdir(parents=True, exist_ok=True)
                            candidate.rename(destination)
                            if target is not None:
                                target["enabled"] = True
                            return True
                        except Exception:
                            continue

            # Registry items: restore from the JSON sidecar.
            backup = self._load_registry_backup()
            record = backup.get(wanted)
            if not record:
                return False
            try:
                import winreg

                hive = getattr(winreg, record.get("hive", "HKEY_CURRENT_USER"))
                with winreg.OpenKey(
                    hive, record["key_path"], 0, winreg.KEY_SET_VALUE
                ) as key:
                    winreg.SetValueEx(
                        key, wanted, 0, record.get("value_type", winreg.REG_SZ),
                        record["value_data"],
                    )
                backup.pop(wanted, None)
                self._save_registry_backup(backup)
                if target is not None:
                    target["enabled"] = True
                return True
            except Exception:
                return False
        except Exception:
            return False
    
    def disable_startup_item(self, name: str, item_type: str) -> bool:
        """
        Disable a specific startup item.

        Args:
            name (str): The name of the startup item.
            item_type (str): The type of the item ('registry' or 'file').

        Returns:
            bool: True if successful, False otherwise.
        """
        if platform.system() == "Windows":
            if item_type == 'registry':
                return self._disable_registry_item(name)
            elif item_type == 'file':
                return self._disable_startup_folder_item(name)
        return False

    def _disable_registry_item(self, name: str) -> bool:
        """Disable a registry-based startup item (values backed up first)."""
        try:
            import winreg

            # Snapshot every location holding this value BEFORE deleting, so
            # enable_startup_item() can restore the exact original data.
            snapshot = {}

            def capture(hive_name, hive, key_path):
                """Capture.

                Args:
                    hive_name: hive name.
                    hive: hive.
                    key_path: key path."""
                try:
                    with winreg.OpenKey(
                        hive, key_path, 0,
                        winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE
                    ) as key:
                        value_data, value_type = winreg.QueryValueEx(key, name)
                        snapshot[name] = {
                            "hive": hive_name,
                            "key_path": key_path,
                            "value_type": int(value_type),
                            "value_data": value_data,
                        }
                except Exception:
                    pass

            capture("HKEY_CURRENT_USER", winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run")
            capture("HKEY_LOCAL_MACHINE", winreg.HKEY_LOCAL_MACHINE,
                    r"Software\Microsoft\Windows\CurrentVersion\Run")
            capture("HKEY_CURRENT_USER", winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\RunOnce")
            capture("HKEY_LOCAL_MACHINE", winreg.HKEY_LOCAL_MACHINE,
                    r"Software\Microsoft\Windows\CurrentVersion\RunOnce")

            if not snapshot:
                return False

            def delete_value(hive, key_path, value_name):
                """Delete value.

                Args:
                    hive: hive.
                    key_path: key path.
                    value_name: value name."""
                try:
                    with winreg.OpenKey(hive, key_path, 0, winreg.KEY_SET_VALUE) as key:
                        winreg.DeleteValue(key, value_name)
                except Exception:
                    pass

            delete_value(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", name)
            delete_value(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", name)
            delete_value(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", name)
            delete_value(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", name)

            self._save_registry_backup({**self._load_registry_backup(), **snapshot})
            return True
        except Exception:
            return False
    
    def _disable_startup_folder_item(self, name: str) -> bool:
        """Disable a file-based startup item."""
        try:
            # For file items, we can move them to a backup location
            def move_to_backup(item_path):
                """Move to backup.

                Args:
                    item_path: item path."""
                try:
                    backup_folder = Path.home() / "StartupBackup"
                    backup_folder.mkdir(exist_ok=True)
                    new_location = backup_folder / item_path.name
                    i = 1
                    while new_location.exists():
                        new_location = backup_folder / f"{item_path.stem}_backup{i}{item_path.suffix}"
                        i += 1
                    item_path.rename(new_location)
                except Exception:
                    pass
            
            # Check current user and all users startup folders
            startup_folders = [
                Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
                Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            ]
            
            for folder in startup_folders:
                item_path = folder / name
                if item_path.exists():
                    move_to_backup(item_path)
            
            return True
        except Exception:
            return False
    
    def get_stats(self) -> dict:
        """Get statistics about startup items."""
        enabled_count = sum(1 for item in self.startup_items if item.get("enabled", True))
        disabled_count = len(self.startup_items) - enabled_count
        
        return {
            "total_startup_items": len(self.startup_items),
            "enabled_items": enabled_count,
            "disabled_items": disabled_count,
            "system_type": self.system,
            "errors": self.error_count
        }
    
    def filter_by_type(self, item_type: str) -> List[Dict]:
        """Filter startup items by type."""
        return [item for item in self.startup_items if item.get("type") == item_type]