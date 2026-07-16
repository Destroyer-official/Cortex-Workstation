"""Windows Registry Cleaner — finds and removes orphaned registry entries.

Scans:
  - Uninstall entries pointing to non-existent paths
  - Startup entries referencing deleted executables
  - File associations pointing to missing programs
  - SharedDLLs with zero reference counts

Provides real backup and deletion via `reg export` and `winreg.DeleteKey`.
"""

import os
import sys
import platform
import subprocess
import datetime
import logging
from pathlib import Path
from typing import List, Dict, Optional

from ..core.config import Config


class RegistryCleaner:
    """Cleaner for orphaned Windows registry entries."""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.logger = logging.getLogger("registry_cleaner")

        if platform.system().lower() != "windows":
            raise RuntimeError("Registry cleaner is only available on Windows")

        self.orphaned_entries: List[Dict] = []
        self.backup_files: List[str] = []
        self.error_count = 0

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def scan(self) -> List[Dict]:
        """Alias used by SmartScanner."""
        return self.scan_orphaned_entries()

    def scan_orphaned_entries(self) -> List[Dict]:
        """Full scan across all categories."""
        self.orphaned_entries.clear()
        self.error_count = 0

        try:
            import winreg
            self._scan_uninstall_entries(winreg.HKEY_LOCAL_MACHINE)
            self._scan_uninstall_entries(winreg.HKEY_CURRENT_USER)
            self._scan_startup_entries()
            self._scan_file_associations()
            self._scan_shared_dlls()
        except Exception as exc:
            self.logger.error("Registry scan failed: %s", exc)
            self.error_count += 1

        return self.orphaned_entries

    # ──────────────────────────────────────────────────────────────────
    # Uninstall entries
    # ──────────────────────────────────────────────────────────────────

    def _scan_uninstall_entries(self, hive):
        import winreg

        paths = [
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
            r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ]
        hive_name = "HKLM" if hive == winreg.HKEY_LOCAL_MACHINE else "HKCU"

        for sub_path in paths:
            try:
                with winreg.OpenKey(hive, sub_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            full = f"{sub_path}\\{subkey_name}"
                            self._check_uninstall_entry(hive, hive_name, full, subkey_name)
                            i += 1
                        except OSError:
                            break
            except FileNotFoundError:
                pass
            except Exception:
                self.error_count += 1

    def _check_uninstall_entry(self, hive, hive_name, full_path, subkey_name):
        import winreg
        try:
            with winreg.OpenKey(hive, full_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as sk:
                display_name = self._reg_val(winreg, sk, "DisplayName", subkey_name)

                # Check InstallLocation — if it's set but doesn't exist, orphaned
                install_loc = self._reg_val(winreg, sk, "InstallLocation", "")
                if install_loc and not os.path.exists(install_loc):
                    self.orphaned_entries.append({
                        "name": display_name,
                        "path": full_path,
                        "type": "uninstall_entry",
                        "hive": hive_name,
                        "reason": f"InstallLocation missing: {install_loc}",
                    })
                    return

                # Check UninstallString — if it references a missing exe
                uninstall_str = self._reg_val(winreg, sk, "UninstallString", "")
                if uninstall_str:
                    exe = self._extract_exe_path(uninstall_str)
                    if exe and not os.path.exists(exe):
                        self.orphaned_entries.append({
                            "name": display_name,
                            "path": full_path,
                            "type": "uninstall_entry",
                            "hive": hive_name,
                            "reason": f"Uninstaller missing: {exe}",
                        })
        except Exception:
            self.error_count += 1

    # ──────────────────────────────────────────────────────────────────
    # Startup entries
    # ──────────────────────────────────────────────────────────────────

    def _scan_startup_entries(self):
        """Check Run/RunOnce keys for entries that reference missing executables."""
        import winreg

        startup_keys = [
            (winreg.HKEY_CURRENT_USER, "HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_CURRENT_USER, "HKCU", r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
            (winreg.HKEY_LOCAL_MACHINE, "HKLM", r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, "HKLM", r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
        ]

        for hive, hive_name, key_path in startup_keys:
            try:
                with winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ) as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            if isinstance(value, str):
                                exe = self._extract_exe_path(value)
                                if exe and not os.path.exists(exe):
                                    self.orphaned_entries.append({
                                        "name": name,
                                        "path": f"{key_path}\\{name}",
                                        "type": "startup_entry",
                                        "hive": hive_name,
                                        "reason": f"Startup executable missing: {exe}",
                                    })
                            i += 1
                        except OSError:
                            break
            except FileNotFoundError:
                pass
            except Exception:
                self.error_count += 1

    # ──────────────────────────────────────────────────────────────────
    # File associations
    # ──────────────────────────────────────────────────────────────────

    def _scan_file_associations(self):
        """Check HKCR (via HKLM\\Software\\Classes) for associations pointing to missing executables."""
        import winreg

        classes_path = r"Software\Classes"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, classes_path, 0, winreg.KEY_READ) as root:
                i = 0
                while True:
                    try:
                        ext_name = winreg.EnumKey(root, i)
                        i += 1
                        # Only check file extensions (start with '.')
                        if not ext_name.startswith("."):
                            continue
                        # Check shell\open\command
                        cmd_path = f"{classes_path}\\{ext_name}\\shell\\open\\command"
                        try:
                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cmd_path) as cmd_key:
                                val, _ = winreg.QueryValueEx(cmd_key, "")
                                if isinstance(val, str):
                                    exe = self._extract_exe_path(val)
                                    if exe and not os.path.exists(exe) and "system32" not in exe.lower():
                                        self.orphaned_entries.append({
                                            "name": f"{ext_name} handler",
                                            "path": cmd_path,
                                            "type": "file_association",
                                            "hive": "HKLM",
                                            "reason": f"Handler missing: {exe}",
                                        })
                        except (FileNotFoundError, OSError):
                            pass
                    except OSError:
                        break
        except Exception:
            self.error_count += 1

    # ──────────────────────────────────────────────────────────────────
    # SharedDLLs
    # ──────────────────────────────────────────────────────────────────

    def _scan_shared_dlls(self):
        """Check SharedDLLs registry for entries with reference count = 0."""
        import winreg
        shared_path = r"Software\Microsoft\Windows\CurrentVersion\SharedDLLs"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, shared_path, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        dll_path, ref_count, _ = winreg.EnumValue(key, i)
                        i += 1
                        if isinstance(ref_count, int) and ref_count == 0:
                            if not os.path.exists(dll_path):
                                self.orphaned_entries.append({
                                    "name": os.path.basename(dll_path),
                                    "path": f"{shared_path}\\{dll_path}",
                                    "type": "shared_dll",
                                    "hive": "HKLM",
                                    "reason": f"DLL missing with ref_count=0: {dll_path}",
                                })
                    except OSError:
                        break
        except FileNotFoundError:
            pass
        except Exception:
            self.error_count += 1

    # ──────────────────────────────────────────────────────────────────
    # Backup & Remove
    # ──────────────────────────────────────────────────────────────────

    def backup_registry(self, backup_dir: str = None) -> Optional[str]:
        """Export HKCU uninstall keys to a .reg file for safety."""
        if not backup_dir:
            backup_dir = os.path.join(os.environ.get("USERPROFILE", "."), "CortexCleanerBackups")
        os.makedirs(backup_dir, exist_ok=True)

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"registry_backup_{ts}.reg")

        try:
            result = subprocess.run(
                ["reg", "export",
                 r"HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall",
                 backup_file, "/y"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                self.backup_files.append(backup_file)
                self.logger.info("Registry backup saved: %s", backup_file)
                return backup_file
            else:
                self.logger.error("reg export failed: %s", result.stderr)
                return None
        except Exception as exc:
            self.logger.error("Backup failed: %s", exc)
            return None

    def remove_orphaned_entry(self, entry: Dict) -> bool:
        """Delete an orphaned registry entry.  Requires appropriate permissions."""
        import winreg

        hive_map = {
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
            "HKCU": winreg.HKEY_CURRENT_USER,
        }
        hive = hive_map.get(entry.get("hive"))
        path = entry.get("path", "")
        entry_type = entry.get("type", "")

        if not hive or not path:
            return False

        try:
            if entry_type in ("uninstall_entry", "file_association"):
                # Delete the entire subkey
                winreg.DeleteKey(hive, path)
                self.logger.info("Deleted registry key: %s\\%s", entry["hive"], path)
                return True
            elif entry_type == "startup_entry":
                # Delete just the value from the parent key
                parent, _, value_name = path.rpartition("\\")
                with winreg.OpenKey(hive, parent, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, value_name)
                self.logger.info("Deleted startup value: %s", path)
                return True
        except PermissionError:
            self.logger.error("Permission denied deleting %s (admin required)", path)
        except FileNotFoundError:
            pass  # Already gone
        except Exception as exc:
            self.logger.error("Failed to delete %s: %s", path, exc)

        return False

    # ──────────────────────────────────────────────────────────────────
    # Stats
    # ──────────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "orphaned_entries_found": len(self.orphaned_entries),
            "backups_created": len(self.backup_files),
            "errors": self.error_count,
        }

    def filter_by_type(self, entry_type: str) -> List[Dict]:
        return [e for e in self.orphaned_entries if e.get("type") == entry_type]

    # ──────────────────────────────────────────────────────────────────
    # Utility
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _reg_val(winreg, key, name, default=""):
        try:
            return winreg.QueryValueEx(key, name)[0]
        except (FileNotFoundError, OSError):
            return default

    @staticmethod
    def _extract_exe_path(raw: str) -> Optional[str]:
        """Extract a file path from a registry value string like:
        '"C:\\Program Files\\App\\app.exe" --args'  or  'C:\\path\\app.exe'
        """
        if not raw:
            return None
        raw = raw.strip()
        if raw.startswith('"'):
            end = raw.find('"', 1)
            if end > 1:
                return raw[1:end]
        # No quotes — take everything before the first space that looks like an arg
        parts = raw.split()
        if parts:
            candidate = parts[0]
            # Handle MsiExec paths
            if candidate.lower() in ("msiexec.exe", "msiexec", "rundll32.exe", "rundll32"):
                return None  # These always exist in System32
            return candidate
        return None