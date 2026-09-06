"""Orphaned Windows registry entry detection with export-before-delete safety.

Finds uninstall entries whose install path or uninstaller is gone, Run/RunOnce
values pointing at missing executables, file associations whose handler no
longer exists, and SharedDLLs values with a zero reference count and no file
on disk. All mutations enforce pre-deletion rollback backup verification
(fail-closed), protected subsystem key exclusions, and full rollback via
:meth:`RegistryCleaner.restore_backup`.
"""

import os
import platform
import subprocess
import datetime
import logging
from typing import List, Dict, Optional

from ..core.config import Config

PROTECTED_REGISTRY_KEYS = [
    r"Winlogon",
    r"CurrentControlSet\Services",
    r"CurrentControlSet\Control\Lsa",
    r"CurrentControlSet\Control\Session Manager",
    r"KnownDLLs",
    r"BCD00000000",
    r"SAM",
    r"SECURITY",
    r"Software\Microsoft\Windows\CurrentVersion\Policies",
    r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon",
]


class RegistryCleaner:
    """Groups related helpers: init, scan, scan orphaned entries, scan uninstall entries, check uninstall entry, scan startup entries, scan file associations, scan shared dlls."""

    def __init__(self, config: Config = None):
        """Initialize Registry Cleaner.

        Initializes the instance and configures internal state.

        Args:
            config (Config): The config parameter.
        """
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
        """Alias used by SmartScanner.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Returns:
            List[Dict]: List of processed items or identifiers.
        """
        return self.scan_orphaned_entries()

    def scan_orphaned_entries(self) -> List[Dict]:
        """Run all category scans and return the accumulated orphans.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Returns:
            List[Dict]: List of processed items or identifiers.
        """
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
        """_scan_uninstall_entries.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            hive: The hive parameter.
        """
        import winreg

        # Both views must be enumerated: the plain path holds 64-bit installers,
        # WOW6432Node the 32-bit ones.
        paths = [
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
            r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ]
        hive_name = "HKLM" if hive == winreg.HKEY_LOCAL_MACHINE else "HKCU"

        for sub_path in paths:
            try:
                # KEY_WOW64_64KEY: read the 64-bit view even from 32-bit Python,
                # so entries are neither missed nor shadowed by redirection.
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
        """Check uninstall entry helper (reads Windows registry).

        Args:
        hive: The hive parameter.
        hive_name: The hive name parameter.
        full_path: Filesystem path to the target file or directory.
        subkey_name: The subkey name parameter.
        """
        import winreg
        try:
            with winreg.OpenKey(hive, full_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as sk:
                display_name = self._reg_val(winreg, sk, "DisplayName", subkey_name)

                # InstallLocation is frequently empty; only trust it when set.
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

                # Many installers register only UninstallString, so fall back
                # to it when InstallLocation gave no verdict.
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
        """Check Run/RunOnce keys for entries that reference missing executables.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
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
        r"""Check HKCR (via HKLM\Software\Classes) for associations pointing to missing executables.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
        import winreg

        classes_path = r"Software\Classes"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, classes_path, 0, winreg.KEY_READ) as root:
                i = 0
                while True:
                    try:
                        ext_name = winreg.EnumKey(root, i)
                        i += 1
                        if not ext_name.startswith("."):
                            continue
                        cmd_path = f"{classes_path}\\{ext_name}\\shell\\open\\command"
                        try:
                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cmd_path) as cmd_key:
                                val, _ = winreg.QueryValueEx(cmd_key, "")
                                if isinstance(val, str):
                                    exe = self._extract_exe_path(val)
                                    # System32 handlers are OS-inbox components,
                                    # not orphans worth deleting.
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
        """Check SharedDLLs registry for entries with reference count = 0.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
        import winreg
        shared_path = r"Software\Microsoft\Windows\CurrentVersion\SharedDLLs"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, shared_path, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        dll_path, ref_count, _ = winreg.EnumValue(key, i)
                        i += 1
                        # Refcounts are installer bookkeeping and often wrong,
                        # so a zero alone is not verdict enough: the file must
                        # also be gone before the entry counts as debris.
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
        """Export registry uninstall branches (both HKCU and HKLM) to .reg files for safety and rollback.
        """
        if not backup_dir:
            backup_dir = os.path.join(os.environ.get("USERPROFILE", "."), "CortexCleanerBackups")
        os.makedirs(backup_dir, exist_ok=True)

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"registry_backup_hkcu_{ts}.reg")
        hklm_backup_file = os.path.join(backup_dir, f"registry_backup_hklm_{ts}.reg")

        exported_any = False
        try:
            result = subprocess.run(
                ["reg", "export",
                 r"HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall",
                 backup_file, "/y"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and os.path.exists(backup_file) and os.path.getsize(backup_file) > 0:
                self.backup_files.append(backup_file)
                self.logger.info("HKCU Registry backup saved: %s", backup_file)
                exported_any = True
            else:
                self.logger.warning("reg export HKCU failed: %s", result.stderr)
        except Exception as exc:
            self.logger.warning("HKCU backup failed: %s", exc)

        try:
            result_hklm = subprocess.run(
                ["reg", "export",
                 r"HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall",
                 hklm_backup_file, "/y"],
                capture_output=True, text=True, timeout=30,
            )
            if result_hklm.returncode == 0 and os.path.exists(hklm_backup_file) and os.path.getsize(hklm_backup_file) > 0:
                self.backup_files.append(hklm_backup_file)
                self.logger.info("HKLM Registry backup saved: %s", hklm_backup_file)
                exported_any = True
        except Exception:
            pass

        if exported_any:
            return backup_file if os.path.exists(backup_file) else hklm_backup_file
        return None

    def backup_entry(self, entry: Dict, backup_dir: Optional[str] = None) -> Optional[str]:
        """Export a specific registry entry to a .reg file before deletion for instant rollback.

        Creates a verified backup export of target key/values, returning the path on success.

        Args:
            entry (Dict): The entry parameter.
            backup_dir (Optional[str]): The backup dir parameter.

        Returns:
            Optional[str]: Formatted path on success, None on failure.
        """
        hive = entry.get("hive", "")
        path = entry.get("path", "")
        if not hive or not path:
            return None

        if not backup_dir:
            backup_dir = os.path.join(
                os.path.expanduser("~"), ".cortex_cleaner", "backups", "registry"
            )
        os.makedirs(backup_dir, exist_ok=True)

        safe_name = "".join(c if c.isalnum() else "_" for c in f"{hive}_{path}")[:60]
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"rollback_{safe_name}_{ts}.reg")

        target_key = f"{hive}\\{path}"
        if entry.get("type") == "startup_entry":
            parent, _, _ = path.rpartition("\\")
            target_key = f"{hive}\\{parent}"

        try:
            res = subprocess.run(
                ["reg", "export", target_key, backup_file, "/y"],
                capture_output=True, text=True, timeout=15,
            )
            if res.returncode == 0 and os.path.exists(backup_file) and os.path.getsize(backup_file) > 0:
                self.backup_files.append(backup_file)
                self.logger.info("Created rollback backup for %s at %s", target_key, backup_file)
                return backup_file
            else:
                self.logger.warning("Failed to export valid non-empty rollback key %s (code %s)", target_key, res.returncode)
        except Exception as exc:
            self.logger.debug("Failed to export rollback key %s: %s", target_key, exc)
        return None

    def restore_backup(self, backup_file: str) -> bool:
        """Restore a registry backup (.reg file) using reg import.

        Args:
            backup_file (str): Path to the .reg file to restore.

        Returns:
            bool: True if import succeeded, False otherwise.
        """
        if not os.path.exists(backup_file):
            self.logger.error("Backup file not found for restore: %s", backup_file)
            return False

        try:
            res = subprocess.run(
                ["reg", "import", backup_file],
                capture_output=True, text=True, timeout=30,
            )
            if res.returncode == 0:
                self.logger.info("Successfully restored registry backup from %s", backup_file)
                return True
            else:
                self.logger.error("reg import failed (%s): %s", res.returncode, res.stderr)
                return False
        except Exception as exc:
            self.logger.error("Exception while restoring registry backup %s: %s", backup_file, exc)
            return False

    def remove_orphaned_entry(self, entry: Dict, auto_backup: bool = True) -> bool:
        """Delete an orphaned registry entry with auto-backup for rollback.

        Enforces protected subsystem exclusions and fail-closed backup verification.
        Requires appropriate permissions.
        """
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

        # 1. Enforce protected Windows subsystem key exclusions
        for protected in PROTECTED_REGISTRY_KEYS:
            if protected.lower() in path.lower():
                self.logger.critical("Refusing to delete protected system registry key: %s\\%s", entry.get("hive", ""), path)
                return False

        # 2. Enforce pre-mutation rollback backup (fail-closed)
        if auto_backup:
            backup_path = self.backup_entry(entry)
            if not backup_path or not os.path.exists(backup_path) or os.path.getsize(backup_path) == 0:
                self.logger.error(
                    "Deletion aborted: failed to create and verify pre-deletion rollback backup for %s\\%s (fail-closed)",
                    entry.get("hive", ""), path
                )
                return False

        try:
            if entry_type in ("uninstall_entry", "file_association"):
                # Whole subkey: these entries are one key per product.
                winreg.DeleteKey(hive, path)
                self.logger.info("Deleted registry key: %s\\%s", entry["hive"], path)
                return True
            elif entry_type == "startup_entry":
                # Value only - the Run key itself must survive.
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
        """Get stats helper.

        Returns:
        dict: Dictionary mapping identifiers to status or values.
        """
        return {
            "orphaned_entries_found": len(self.orphaned_entries),
            "backups_created": len(self.backup_files),
            "errors": self.error_count,
        }

    def filter_by_type(self, entry_type: str) -> List[Dict]:
        """Filter by type helper.

        Args:
        entry_type (str): The entry type parameter.

        Returns:
        List[Dict]: List of processed items or identifiers.
        """
        return [e for e in self.orphaned_entries if e.get("type") == entry_type]

    # ──────────────────────────────────────────────────────────────────
    # Utility
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _reg_val(winreg, key, name, default=""):
        """Reg val helper (reads Windows registry). Returns winreg.QueryValueEx(...).

        Args:
        winreg: The winreg parameter.
        key: The key parameter.
        name: The name parameter.
        default: The default parameter.
        """
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
        # Unquoted path: spaces are ambiguous, so take the first token.
        parts = raw.split()
        if parts:
            candidate = parts[0]
            # Launchers that always live in System32 - never orphans.
            if candidate.lower() in ("msiexec.exe", "msiexec", "rundll32.exe", "rundll32"):
                return None
            return candidate
        return None