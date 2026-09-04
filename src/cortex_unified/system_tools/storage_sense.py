"""Storage Sense - surface and configure Windows' built-in auto-cleanup.

Windows already ships an automatic cleaner ("Storage Sense") that removes temp
files, empties the Recycle Bin on a schedule, and can clean the Downloads
folder. Most users never discover it. Cortex reads its current policy and lets
you turn it on and set the schedule - working *with* Windows instead of
duplicating it.

Everything here lives under the per-user registry key
``HKCU\\...\\StorageSense\\Parameters\\StoragePolicy`` (DWORD values), so changes
are per-user and fully reversible. No admin required.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

_LOG = logging.getLogger("cortex.system_tools.storage_sense")
_IS_WINDOWS = sys.platform == "win32"

_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy"

# Cadence value (registry '2048') -> human label.
_CADENCE = {0: "When disk space is low", 1: "Every day", 7: "Every week", 30: "Every month"}
# Retention day options used by recycle-bin / downloads thresholds.
_DAYS = {0: "Never", 1: "1 day", 14: "14 days", 30: "30 days", 60: "60 days"}


class StorageSense:
    """Storagesense.

    Manages StorageSense operations and coordinates related state changes for the component.
    """

    @staticmethod
    def is_supported() -> bool:
        """Is supported.

        Manages is supported operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return _IS_WINDOWS

    # -- read ---------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Get status.

        Manages get status operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        if not _IS_WINDOWS:
            return {"supported": False}
        return self._interpret(self._read_values())

    def _read_values(self) -> dict[str, int]:
        """_read_values.

        Manages read values operations and coordinates related state changes for the component.

        Returns:
            dict[str, int]: Dictionary mapping identifiers to status or values.
        """
        values: dict[str, int] = {}
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY_PATH) as key:
                i = 0
                while True:
                    try:
                        name, data, _ = winreg.EnumValue(key, i)
                        i += 1
                        if isinstance(data, int):
                            values[name] = data
                    except OSError:
                        break
        except FileNotFoundError:
            pass  # key absent -> Storage Sense never configured
        except Exception as exc:  # noqa: BLE001
            _LOG.debug("read StoragePolicy failed: %s", exc)
        return values

    @staticmethod
    def _interpret(v: dict[str, int]) -> dict[str, Any]:
        """Interpret.

        Manages interpret operations and coordinates related state changes for the component.

        Args:
            v (dict[str, int]): The v parameter.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        enabled = bool(v.get("01", 0))
        cadence = int(v.get("2048", 0))
        return {
            "supported": _IS_WINDOWS,
            "configured": bool(v),
            "enabled": enabled,
            "cadence": cadence,
            "cadence_label": _CADENCE.get(cadence, "Custom"),
            "clean_temp_files": bool(v.get("04", 0)),
            "recycle_bin_cleanup": bool(v.get("08", 0)),
            "recycle_bin_days": int(v.get("256", 0)),
            "recycle_bin_days_label": _DAYS.get(int(v.get("256", 0)), "Custom"),
            "downloads_cleanup": bool(v.get("32", 0)),
            "downloads_days": int(v.get("512", 0)),
            "downloads_days_label": _DAYS.get(int(v.get("512", 0)), "Custom"),
        }

    # -- write --------------------------------------------------------------

    def _write(self, name: str, value: int) -> bool:
        """Write.

        Manages write operations and coordinates related state changes for the component.

        Args:
            name (str): The name parameter.
            value (int): The value parameter.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        if not _IS_WINDOWS:
            return False
        try:
            import winreg
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _KEY_PATH) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, int(value))
            return True
        except Exception as exc:  # noqa: BLE001
            _LOG.debug("write StoragePolicy %s failed: %s", name, exc)
            return False

    def set_enabled(self, enabled: bool) -> tuple[bool, str]:
        """Set enabled.

        Manages set enabled operations and coordinates related state changes for the component.

        Args:
            enabled (bool): The enabled parameter.

        Returns:
            tuple[bool, str]: True if the operation succeeded, False otherwise.
        """
        ok = self._write("01", 1 if enabled else 0)
        if not ok:
            return False, "Could not update Storage Sense (registry write failed)."
        if enabled and not self._read_values().get("2048"):
            self._write("2048", 7)  # sensible default: weekly
        return True, "Storage Sense turned on." if enabled else "Storage Sense turned off."

    def set_cadence(self, days: int) -> tuple[bool, str]:
        """Set cadence.

        Manages set cadence operations and coordinates related state changes for the component.

        Args:
            days (int): The days parameter.

        Returns:
            tuple[bool, str]: True if the operation succeeded, False otherwise.
        """
        if days not in _CADENCE:
            return False, "Invalid schedule."
        ok = self._write("2048", days)
        return ok, (f"Schedule set to '{_CADENCE[days]}'." if ok
                    else "Could not update the schedule.")

    def set_recycle_bin_days(self, days: int) -> tuple[bool, str]:
        """Set recycle bin days.

        Manages set recycle bin days operations and coordinates related state changes for the component.

        Args:
            days (int): The days parameter.

        Returns:
            tuple[bool, str]: True if the operation succeeded, False otherwise.
        """
        if days not in _DAYS:
            return False, "Invalid retention period."
        ok1 = self._write("08", 1 if days else 0)
        ok2 = self._write("256", days)
        return (ok1 and ok2), ("Recycle Bin cleanup updated." if (ok1 and ok2)
                               else "Could not update Recycle Bin cleanup.")
