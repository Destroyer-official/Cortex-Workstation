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

import logging
from typing import Dict, List


class TelemetryBlocker:
    """Disables OS telemetry and diagnostic tracking via Windows Registry."""

    def __init__(self):
        self.logger = logging.getLogger("telemetry_blocker")
        self._rules = self._build_rules()

    @property
    def rules(self) -> List[dict]:
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

        return [
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

    # ──────────────────────────────────────────────────────────────────

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
