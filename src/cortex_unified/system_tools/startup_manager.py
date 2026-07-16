"""System startup manager for Cortex Cleaner."""

import os
import sys
import platform
from pathlib import Path
from typing import List, Dict, Tuple
import subprocess

from ..core.utils import normalize_path
from ..core.config import Config


class StartupManager:
    """Manager for system startup programs and services."""
    
    def __init__(self, config: Config = None):
        """Initialize startup manager."""
        self.config = config or Config()
        self.system = platform.system().lower()
        
        # Results
        self.startup_items = []
        self.error_count = 0
    
    def list_startup_items(self) -> List[Dict]:
        """List all startup items based on the operating system."""
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
        """List Windows startup items."""
        try:
            # Method 1: Registry-based startup items
            try:
                import winreg
                
                # HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
                self._read_registry_startup_items(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run"
                )
                
                # HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Run
                self._read_registry_startup_items(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"Software\Microsoft\Windows\CurrentVersion\Run"
                )
                
                # HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\RunOnce
                self._read_registry_startup_items(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\RunOnce"
                )
                
                # HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\RunOnce
                self._read_registry_startup_items(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"Software\Microsoft\Windows\CurrentVersion\RunOnce"
                )
            except Exception:
                self.error_count += 1
            
            # Method 2: Startup folder items
            try:
                # Current user startup folder
                startup_folder = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
                self._read_startup_folder_items(startup_folder)
                
                # All users startup folder
                all_users_startup = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
                self._read_startup_folder_items(all_users_startup)
            except Exception:
                self.error_count += 1
                
        except Exception:
            self.error_count += 1
    
    def _read_registry_startup_items(self, hive, key_path):
        """Read startup items from Windows registry."""
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
        """Read startup items from Windows startup folder."""
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
        """List macOS startup items."""
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
    
    def _read_plist_items(self, folder_path: Path):
        """Read startup items from macOS plist files."""
        try:
            if folder_path.exists():
                for plist_file in folder_path.glob("*.plist"):
                    try:
                        # Try to read basic info from plist
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
        """List Linux startup items."""
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
    
    def enable_startup_item(self, item_name: str) -> bool:
        """Enable a startup item."""
        # This is a placeholder implementation
        # Actual implementation would need to modify system settings
        try:
            # Find the item
            for item in self.startup_items:
                if item["name"] == item_name:
                    # In a real implementation, we would enable the item
                    item["enabled"] = True
                    return True
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
        """Disable a registry-based startup item."""
        try:
            import winreg
            
            # For registry items, we can delete the value to disable
            def delete_value(hive, key_path, value_name):
                try:
                    with winreg.OpenKey(hive, key_path, 0, winreg.KEY_SET_VALUE) as key:
                        winreg.DeleteValue(key, value_name)
                except Exception:
                    pass
            
            # Check both current user and local machine
            delete_value(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", name)
            delete_value(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", name)
            delete_value(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", name)
            delete_value(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", name)
            
            return True
        except Exception:
            return False
    
    def _disable_startup_folder_item(self, name: str) -> bool:
        """Disable a file-based startup item."""
        try:
            # For file items, we can move them to a backup location
            def move_to_backup(item_path):
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