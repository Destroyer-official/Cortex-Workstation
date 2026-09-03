"""Telemetry Blocker — comprehensive Windows privacy hardening via Registry.

Covers 15+ telemetry vectors including:
  - Data Collection / Diagnostics
  - Advertising ID
  - Cortana / Search
  - Location Tracking
  - App Launch Tracking
  - Feedback & Tips
  - Wi-Fi Sense
  - Cloud Content / Suggested Apps
  - Activity History
  - Handwriting data sharing
  - Clipboard sync
"""

import json
import logging
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


_BACKUP_DIR = Path.home() / ".cortex_cleaner" / "telemetry_backups"


def _get_windows_build() -> Optional[int]:
    """_get_windows_build."""
    try:
        v = platform.version()
        parts = v.split(".")
        if len(parts) >= 3:
            return int(parts[2])
    except (ValueError, IndexError):
        pass
    return None
    """_get_windows_build."""
    """_get_windows_build."""


def _is_win11_24h2_plus() -> bool:
    """_is_win11_24h2_plus."""
    build = _get_windows_build()
    return build is not None and build >= 26100
    """_is_win11_24h2_plus."""
    """_is_win11_24h2_plus."""


class TelemetryBlocker:
    """Disables OS telemetry and diagnostic tracking via Windows Registry."""

    def __init__(self):
        """Initialize Telemetry Blocker."""
        self.logger = logging.getLogger("telemetry_blocker")
        self._rules = self._build_rules()

    @property
    def rules(self) -> List[dict]:
        """Rules."""
        return self._rules

    @staticmethod
    def _build_rules() -> List[dict]:
        """Define all telemetry registry rules."""
        try:
            import winreg
        except ImportError:
            return []

        HKLM = winreg.HKEY_LOCAL_MACHINE
        HKCU = winreg.HKEY_CURRENT_USER
        DWORD = winreg.REG_DWORD

        rules = [
            # ── Data Collection ──────────────────────────────
            {
                "label": "Diagnostic Data",
                "hkey": HKLM,
                "path": r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                "name": "AllowTelemetry",
                "value": 0,
                "type": DWORD,
            },
            # ── Application Compatibility Telemetry ──────────
            {
                "label": "App Compatibility Telemetry",
                "hkey": HKLM,
                "path": r"SOFTWARE\Policies\Microsoft\Windows\AppCompat",
                "name": "AITEnable",
                "value": 0,
                "type": DWORD,
            },
            # ── Advertising ID ───────────────────────────────
            {
                "label": "Advertising ID",
                "hkey": HKCU,
                "path": r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
                "name": "Enabled",
                "value": 0,
                "type": DWORD,
            },
            # ── Suggested Content / Cloud Content ────────────
            {
                "label": "Suggested Apps & Content",
                "hkey": HKLM,
                "path": r"SOFTWARE\Policies\Microsoft\Windows\CloudContent",
                "name": "DisableWindowsConsumerFeatures",
                "value": 1,
                "type": DWORD,
            },
            {
                "label": "Soft Landing (Tips)",
                "hkey": HKCU,
                "path": r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
                "name": "SoftLandingEnabled",
                "value": 0,
                "type": DWORD,
            },
            {
                "label": "Subscribed Content",
                "hkey": HKCU,
                "path": r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
                "name": "SubscribedContent-338389Enabled",
                "value": 0,
                "type": DWORD,
            },
            # ── Cortana / Search ─────────────────────────────
            {
                "label": "Cortana Web Search",
                "hkey": HKLM,
                "path": r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                "name": "AllowCortana",
                "value": 0,
                "type": DWORD,
            },
            {
                "label": "Cloud Search",
                "hkey": HKLM,
                "path": r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                "name": "AllowCloudSearch",
                "value": 0,
                "type": DWORD,
            },
            # ── Location Tracking ────────────────────────────
            {
                "label": "Location Tracking",
                "hkey": HKLM,
                "path": r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors",
                "name": "DisableLocation",
                "value": 1,
                "type": DWORD,
            },
            # ── Input / Handwriting Data ─────────────────────
            {
                "label": "Handwriting Data Sharing",
                "hkey": HKLM,
                "path": r"SOFTWARE\Policies\Microsoft\InputPersonalization",
                "name": "AllowInputPersonalization",
                "value": 0,
                "type": DWORD,
            },
            # ── Feedback Frequency ───────────────────────────
            {
                "label": "Feedback Notifications",
                "hkey": HKCU,
                "path": r"SOFTWARE\Microsoft\Siuf\Rules",
                "name": "NumberOfSIUFInPeriod",
                "value": 0,
                "type": DWORD,
            },
            # ── App Launch Tracking ──────────────────────────
            {
                "label": "App Launch Tracking",
                "hkey": HKCU,
                "path": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "name": "Start_TrackProgs",
                "value": 0,
                "type": DWORD,
            },
            # ── Activity History ─────────────────────────────
            {
                "label": "Activity History Upload",
                "hkey": HKLM,
                "path": r"SOFTWARE\Policies\Microsoft\Windows\System",
                "name": "UploadUserActivities",
                "value": 0,
                "type": DWORD,
            },
            {
                "label": "Activity History Collection",
                "hkey": HKLM,
                "path": r"SOFTWARE\Policies\Microsoft\Windows\System",
                "name": "PublishUserActivities",
                "value": 0,
                "type": DWORD,
            },
            # ── Clipboard Cloud Sync ─────────────────────────
            {
                "label": "Clipboard Cloud Sync",
                "hkey": HKLM,
                "path": r"SOFTWARE\Policies\Microsoft\Windows\System",
                "name": "AllowCrossDeviceClipboard",
                "value": 0,
                "type": DWORD,
            },
            # ── Wi-Fi Sense ──────────────────────────────────
            {
                "label": "Wi-Fi Sense Auto-Connect",
                "hkey": HKLM,
                "path": r"SOFTWARE\Microsoft\WcmSvc\wifinetworkmanager\config",
                "name": "AutoConnectAllowedOEM",
                "value": 0,
                "type": DWORD,
            },
        ]

        if _is_win11_24h2_plus():
            for rule in rules:
                if rule["name"] == "AllowTelemetry":
                    rule["value"] = 1
                    break

        return rules

    # ──────────────────────────────────────────────────────────────────

    def _backup_key(self, rule: dict) -> Optional[dict]:
        """_backup_key."""
        try:
            import winreg
        except ImportError:
            return None
        try:
            key = winreg.OpenKey(rule["hkey"], rule["path"])
            val, type_id = winreg.QueryValueEx(key, rule["name"])
            winreg.CloseKey(key)
            return {"value": val, "type": type_id}
        except FileNotFoundError:
            return {"value": None, "type": None, "missing": True}
        except Exception as exc:
            self.logger.debug("Backup read failed for %s: %s", rule["label"], exc)
            return None
        """_backup_key."""
        """_backup_key."""

    def _save_backup(self, entries: List[dict]) -> Path:
        """_save_backup."""
        _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = _BACKUP_DIR / f"backup_{ts}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(entries, fh, indent=2)
        return path
        """_save_backup."""
        """_save_backup."""

    def backup_telemetry(self) -> Optional[Path]:
        """Backup telemetry."""
        try:
            import winreg
        except ImportError:
            self.logger.error("winreg unavailable")
            return None

        entries = []
        for rule in self._rules:
            entry = {
                "label": rule["label"],
                "hkey": "HKLM" if rule["hkey"] == winreg.HKEY_LOCAL_MACHINE else "HKCU",
                "path": rule["path"],
                "name": rule["name"],
            }
            backup = self._backup_key(rule)
            if backup:
                entry.update(backup)
            entries.append(entry)

        path = self._save_backup(entries)
        self.logger.info("Backup saved to %s", path)
        return path

    def restore_from_backup(self, backup_path: Optional[Path] = None) -> bool:
        """Restore from backup."""
        try:
            import winreg
        except ImportError:
            self.logger.error("winreg unavailable")
            return False

        if backup_path is None:
            backups = sorted(_BACKUP_DIR.glob("backup_*.json"), reverse=True)
            if not backups:
                self.logger.error("No backup files found in %s", _BACKUP_DIR)
                return False
            backup_path = backups[0]

        try:
            with open(backup_path, "r", encoding="utf-8") as fh:
                entries = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            self.logger.error("Failed to read backup %s: %s", backup_path, exc)
            return False

        hkey_map = {
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
            "HKCU": winreg.HKEY_CURRENT_USER,
        }
        all_ok = True
        for entry in entries:
            hkey = hkey_map.get(entry.get("hkey"))
            if hkey is None:
                continue
            try:
                if entry.get("missing"):
                    try:
                        key = winreg.OpenKey(hkey, entry["path"], 0, winreg.KEY_SET_VALUE)
                        winreg.DeleteValue(key, entry["name"])
                        winreg.CloseKey(key)
                    except FileNotFoundError:
                        pass
                else:
                    key = winreg.CreateKey(hkey, entry["path"])
                    winreg.SetValueEx(key, entry["name"], 0, entry["type"], entry["value"])
                    winreg.CloseKey(key)
                self.logger.info("Restored: %s", entry.get("label", entry["name"]))
            except PermissionError:
                self.logger.error("Permission denied restoring %s", entry.get("label"))
                all_ok = False
            except Exception as exc:
                self.logger.error("Failed to restore %s: %s", entry.get("label"), exc)
                all_ok = False
        return all_ok

    def check_status(self) -> Dict[str, bool]:
        """Return {label: is_blocked} for every rule."""
        try:
            import winreg
        except ImportError:
            return {}

        status: Dict[str, bool] = {}
        for rule in self._rules:
            blocked = False
            try:
                key = winreg.OpenKey(rule["hkey"], rule["path"])
                val, _ = winreg.QueryValueEx(key, rule["name"])
                blocked = (val == rule["value"])
                winreg.CloseKey(key)
            except FileNotFoundError:
                pass  # key doesn't exist → not blocked (OS default)
            except Exception as exc:
                self.logger.debug("Error reading %s: %s", rule["label"], exc)

            status[rule["label"]] = blocked

        return status

    def block_telemetry(self) -> bool:
        """Apply all rules. Returns True if ALL succeeded."""
        try:
            import winreg
        except ImportError:
            self.logger.error("winreg unavailable")
            return False

        backup_entries = []
        for rule in self._rules:
            backup = self._backup_key(rule)
            entry = {
                "label": rule["label"],
                "hkey": "HKLM" if rule["hkey"] == winreg.HKEY_LOCAL_MACHINE else "HKCU",
                "path": rule["path"],
                "name": rule["name"],
            }
            if backup:
                entry.update(backup)
            backup_entries.append(entry)

        if backup_entries:
            bp = self._save_backup(backup_entries)
            self.logger.info("Pre-apply backup saved to %s", bp)

        all_ok = True
        for rule in self._rules:
            try:
                key = winreg.CreateKey(rule["hkey"], rule["path"])
                winreg.SetValueEx(key, rule["name"], 0, rule["type"], rule["value"])
                winreg.CloseKey(key)
                self.logger.info("Blocked: %s", rule["label"])
            except PermissionError:
                self.logger.error("Permission denied: %s (admin required)", rule["label"])
                all_ok = False
            except Exception as exc:
                self.logger.error("Failed to set %s: %s", rule["label"], exc)
                all_ok = False
        return all_ok

    def restore_defaults(self) -> bool:
        """Remove all custom telemetry registry values (restore OS defaults)."""
        try:
            import winreg
        except ImportError:
            return False

        all_ok = True
        for rule in self._rules:
            try:
                key = winreg.OpenKey(rule["hkey"], rule["path"], 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, rule["name"])
                winreg.CloseKey(key)
            except FileNotFoundError:
                pass  # already gone
            except PermissionError:
                all_ok = False
            except Exception:
                all_ok = False
        return all_ok
