"""Windows Application Uninstaller for Cortex Cleaner.

Reads installed software from the Windows Registry Uninstall keys
and provides safe uninstallation + silent uninstall support.
"""

import subprocess
import logging
from typing import List, Dict, Any, Optional


class AppUninstaller:
    """Appuninstaller.

    Manages AppUninstaller operations and coordinates related state changes for the component.
    """

    # The three standard registry locations where Windows stores uninstall info.
    _UNINSTALL_PATHS = [
        (0x80000002, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),           # HKLM
        (0x80000002, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"), # HKLM 32-bit
        (0x80000001, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),           # HKCU
    ]

    def __init__(self):
        """Initialize App Uninstaller.

        Initializes the instance and configures internal state.
        """
        self.logger = logging.getLogger("app_uninstaller")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_installed_apps(self) -> List[Dict[str, Any]]:
        """Return a deduplicated, sorted list of installed applications.

        Manages get installed apps operations and coordinates related state changes for the component.

        Returns:
            List[Dict[str, Any]]: List of processed items or identifiers.
        """
        try:
            import winreg
        except ImportError:
            self.logger.error("winreg is not available on this platform")
            return []

        apps: List[Dict[str, Any]] = []

        hive_map = {
            0x80000002: winreg.HKEY_LOCAL_MACHINE,
            0x80000001: winreg.HKEY_CURRENT_USER,
        }

        for hive_int, sub_path in self._UNINSTALL_PATHS:
            hive = hive_map[hive_int]
            try:
                root_key = winreg.OpenKey(hive, sub_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            except FileNotFoundError:
                continue
            except OSError as exc:
                self.logger.debug("Cannot open %s: %s", sub_path, exc)
                continue

            try:
                num_subkeys = winreg.QueryInfoKey(root_key)[0]
                for idx in range(num_subkeys):
                    try:
                        subkey_name = winreg.EnumKey(root_key, idx)
                        app = self._read_app_entry(winreg, hive, sub_path, subkey_name)
                        if app:
                            apps.append(app)
                    except OSError:
                        continue
            finally:
                winreg.CloseKey(root_key)

        # De-duplicate by display name (keep first occurrence)
        seen: Dict[str, bool] = {}
        unique: List[Dict[str, Any]] = []
        for app in apps:
            key = app["name"].lower()
            if key not in seen:
                seen[key] = True
                unique.append(app)

        return sorted(unique, key=lambda a: a["name"].lower())

    def uninstall_app(self, app_info: Dict[str, Any], silent: bool = False) -> bool:
        """Execute the uninstall string for an application.

        Args:
            app_info: dict returned by get_installed_apps()
            silent: if True, attempt to add quiet-mode flags for MSI-based installers
        Returns:
            True if the uninstaller process was launched successfully.
        """
        uninstall_string = app_info.get("quiet_uninstall_string") or app_info.get("uninstall_string")
        if not uninstall_string:
            self.logger.error("No uninstall string for %s", app_info.get("name"))
            return False

        try:
            cmd = uninstall_string

            # For MSI packages, inject /QB (basic UI, no user input) if not already quiet
            if silent and "msiexec" in cmd.lower():
                if "/q" not in cmd.lower() and "/passive" not in cmd.lower():
                    cmd = cmd.rstrip() + " /QB"

            self.logger.info("Launching uninstaller for '%s': %s", app_info["name"], cmd)

            # SECURITY: do NOT use shell=True. The uninstall string comes from
            # the registry (which malware can populate), and shell=True would
            # let embedded metacharacters (&, |, &&, ...) chain arbitrary extra
            # commands via cmd.exe. Without a shell, Windows' CreateProcess runs
            # the program directly and does not interpret those metacharacters.
            import shlex
            try:
                argv = shlex.split(cmd, posix=False)
            except ValueError:
                argv = [cmd]
            subprocess.Popen(argv, shell=False)
            return True
        except Exception as exc:
            self.logger.error("Failed to launch uninstaller for '%s': %s", app_info["name"], exc)
            return False

    def get_app_size_mb(self, app_info: Dict[str, Any]) -> float:
        """Return estimated size in MB from the registry's EstimatedSize (KB) value.

        Manages get app size mb operations and coordinates related state changes for the component.

        Args:
            app_info (Dict[str, Any]): The app info parameter.

        Returns:
            float: Result of the operation.
        """
        est_kb = app_info.get("estimated_size_kb", 0)
        if isinstance(est_kb, (int, float)):
            return est_kb / 1024.0
        return 0.0

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_app_entry(winreg, hive, parent_path: str, subkey_name: str) -> Optional[Dict[str, Any]]:
        """Read a single Uninstall subkey and return an app dict, or None.

        Manages read app entry operations and coordinates related state changes for the component.

        Args:
            winreg: The winreg parameter.
            hive: The hive parameter.
            parent_path (str): Filesystem path to the target file or directory.
            subkey_name (str): The subkey name parameter.

        Returns:
            Optional[Dict[str, Any]]: Dictionary mapping identifiers to status or values.
        """
        full_path = f"{parent_path}\\{subkey_name}"
        try:
            sk = winreg.OpenKey(hive, full_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        except (FileNotFoundError, OSError):
            return None

        def _val(name: str, default=""):
            """Val.

            Manages val operations and coordinates related state changes for the component.

            Args:
                name (str): The name parameter.
                default: The default parameter.
            """
            try:
                return winreg.QueryValueEx(sk, name)[0]
            except (FileNotFoundError, OSError):
                return default

        try:
            display_name = _val("DisplayName")
            if not display_name:
                return None  # Skip entries without a visible name

            # SystemComponent=1 means hidden from Programs & Features — skip
            sys_comp = _val("SystemComponent", 0)
            if sys_comp == 1:
                return None

            uninstall_str = _val("UninstallString")
            quiet_uninstall = _val("QuietUninstallString")
            if not uninstall_str and not quiet_uninstall:
                return None  # No way to uninstall

            return {
                "name": display_name,
                "publisher": _val("Publisher"),
                "display_version": _val("DisplayVersion"),
                "install_date": _val("InstallDate"),
                "install_location": _val("InstallLocation"),
                "uninstall_string": uninstall_str,
                "quiet_uninstall_string": quiet_uninstall,
                "estimated_size_kb": _val("EstimatedSize", 0),
                "registry_key": full_path,
            }
        finally:
            winreg.CloseKey(sk)
