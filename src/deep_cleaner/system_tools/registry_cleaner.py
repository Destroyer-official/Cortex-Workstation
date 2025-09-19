"""Windows registry cleaner for Deep Cleaner."""

import os
import sys
import platform
from pathlib import Path
from typing import List, Dict, Tuple
import subprocess

from ..utils import normalize_path
from ..config import Config


class RegistryCleaner:
    """Cleaner for Windows registry entries."""
    
    def __init__(self, config: Config = None):
        """Initialize registry cleaner."""
        self.config = config or Config()
        self.system = platform.system().lower()
        
        # Check if we're on Windows
        if self.system != "windows":
            raise RuntimeError("Registry cleaner is only available on Windows")
        
        # Results
        self.orphaned_entries = []
        self.backup_entries = []
        self.error_count = 0
    
    def scan_orphaned_entries(self) -> List[Dict]:
        """Scan for orphaned/uninstalled software registry entries."""
        self.orphaned_entries = []
        self.error_count = 0
        
        try:
            import winreg
            
            # Scan common registry locations for orphaned entries
            self._scan_uninstall_entries(winreg.HKEY_LOCAL_MACHINE)
            self._scan_uninstall_entries(winreg.HKEY_CURRENT_USER)
            
            # Scan startup entries
            self._scan_startup_entries()
            
            # Scan file associations
            self._scan_file_associations()
            
        except Exception as e:
            self.error_count += 1
        
        return self.orphaned_entries
    
    def _scan_uninstall_entries(self, hive):
        """Scan uninstall entries for orphaned software."""
        try:
            import winreg
            
            uninstall_paths = [
                r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
                r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
            ]
            
            for uninstall_path in uninstall_paths:
                try:
                    with winreg.OpenKey(hive, uninstall_path) as key:
                        i = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                subkey_path = f"{uninstall_path}\\{subkey_name}"
                                
                                # Check if this entry is orphaned
                                if self._is_orphaned_uninstall_entry(hive, subkey_path):
                                    # Get entry details
                                    details = self._get_uninstall_entry_details(hive, subkey_path)
                                    self.orphaned_entries.append({
                                        "name": details.get("DisplayName", subkey_name),
                                        "path": subkey_path,
                                        "type": "uninstall_entry",
                                        "hive": "HKEY_LOCAL_MACHINE" if hive == winreg.HKEY_LOCAL_MACHINE else "HKEY_CURRENT_USER",
                                        "details": details
                                    })
                                
                                i += 1
                            except WindowsError:
                                break
                except Exception:
                    self.error_count += 1
        except Exception:
            self.error_count += 1
    
    def _is_orphaned_uninstall_entry(self, hive, subkey_path: str) -> bool:
        """Check if an uninstall entry is orphaned."""
        try:
            import winreg
            
            with winreg.OpenKey(hive, subkey_path) as key:
                # Check for common orphaned indicators
                try:
                    # Get install location
                    install_location, _ = winreg.QueryValueEx(key, "InstallLocation")
                    if install_location:
                        install_path = Path(install_location)
                        # If install location doesn't exist, likely orphaned
                        if not install_path.exists():
                            return True
                except WindowsError:
                    pass
                
                # Check for uninstall string
                try:
                    uninstall_string, _ = winreg.QueryValueEx(key, "UninstallString")
                    if not uninstall_string:
                        # No uninstall string, likely orphaned
                        return True
                except WindowsError:
                    # No uninstall string, likely orphaned
                    return True
                
                return False
        except Exception:
            # If we can't read the entry, consider it potentially orphaned
            return True
    
    def _get_uninstall_entry_details(self, hive, subkey_path: str) -> Dict:
        """Get details for an uninstall entry."""
        details = {}
        try:
            import winreg
            
            with winreg.OpenKey(hive, subkey_path) as key:
                # Common uninstall entry values
                value_names = [
                    "DisplayName", "DisplayVersion", "Publisher", 
                    "InstallLocation", "UninstallString", "InstallDate",
                    "Size", "EstimatedSize"
                ]
                
                for value_name in value_names:
                    try:
                        value, _ = winreg.QueryValueEx(key, value_name)
                        details[value_name] = value
                    except WindowsError:
                        pass
        except Exception:
            pass
        
        return details
    
    def _scan_startup_entries(self):
        """Scan startup entries for orphaned entries."""
        # This would check if the programs referenced in startup entries still exist
        pass  # Placeholder for future implementation
    
    def _scan_file_associations(self):
        """Scan file associations for orphaned entries."""
        # This would check if the programs associated with file types still exist
        pass  # Placeholder for future implementation
    
    def backup_registry(self) -> bool:
        """Create a backup of registry entries before making changes."""
        try:
            # Create timestamp for backup
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"registry_backup_{timestamp}.reg"
            
            # Use reg export command to backup registry
            cmd = ["reg", "export", "HKEY_CURRENT_USER", backup_file, "/y"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.backup_entries.append(backup_file)
                return True
            else:
                self.error_count += 1
                return False
        except Exception:
            self.error_count += 1
            return False
    
    def remove_orphaned_entry(self, entry_path: str) -> bool:
        """Remove an orphaned registry entry."""
        # This is a placeholder implementation for safety
        # Actual implementation would need to carefully remove entries
        try:
            # In a real implementation, we would remove the registry entry
            # For safety, we'll just simulate the operation
            print(f"Would remove registry entry: {entry_path}")
            return True
        except Exception:
            return False
    
    def get_stats(self) -> dict:
        """Get statistics about registry cleaning."""
        return {
            "orphaned_entries_found": len(self.orphaned_entries),
            "backups_created": len(self.backup_entries),
            "errors": self.error_count
        }
    
    def filter_by_type(self, entry_type: str) -> List[Dict]:
        """Filter orphaned entries by type."""
        return [entry for entry in self.orphaned_entries if entry.get("type") == entry_type]