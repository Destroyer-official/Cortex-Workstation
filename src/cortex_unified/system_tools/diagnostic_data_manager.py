"""Cortex Cleaner — Windows Telemetry & Diagnostic Data Manager.

Audits and configures Windows diagnostic telemetry levels:
1. Controls AllowTelemetry level (0=Security, 1=Required/Basic, 2=Enhanced, 3=Optional/Full).
2. Manages Customer Experience Improvement Program (CEIP) tracking.
3. Manages Application Impact Telemetry (AIT) and Windows Error Reporting auto-submission.
4. Manages Windows Advertising ID and Timeline Activity Feed publication.
5. Computes a privacy telemetry exposure score and provides 1-click maximum privacy enforcement.
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

if platform.system() == "Windows":
    import winreg
else:
    winreg = None  # type: ignore[assignment]


@dataclass
class TelemetrySetting:
    """Telemetry Setting data container."""
    id: str
    name: str
    hive_name: str  # "HKLM" or "HKCU"
    subkey: str
    value_name: str
    current_value: Optional[int]
    recommended_value: int
    is_hardened: bool
    description: str


@dataclass
class TelemetryAuditReport:
    """Telemetry Audit Report data container."""
    total_settings: int
    hardened_count: int
    exposed_count: int
    privacy_score_percent: float
    settings: List[TelemetrySetting]


class DiagnosticDataManager:
    """Production Windows Telemetry & Diagnostic Data level management engine."""

    DATA_COLLECTION_POLICIES = [
        TelemetrySetting(
            id="allow_telemetry",
            name="Diagnostic Telemetry Level",
            hive_name="HKLM",
            subkey=r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
            value_name="AllowTelemetry",
            current_value=None,
            recommended_value=0,  # 0 = Security / Minimum
            is_hardened=False,
            description="Controls OS diagnostic data sent to Microsoft (0=Security/Minimal, 1=Basic, 3=Full)",
        ),
        TelemetrySetting(
            id="ceip",
            name="Customer Experience Improvement (CEIP)",
            hive_name="HKLM",
            subkey=r"SOFTWARE\Policies\Microsoft\SQMClient\Windows",
            value_name="CEIPEnable",
            current_value=None,
            recommended_value=0,
            is_hardened=False,
            description="Prevents participation in Windows Software Quality Metrics data collection",
        ),
        TelemetrySetting(
            id="app_impact_telemetry",
            name="Application Impact Telemetry (AIT)",
            hive_name="HKLM",
            subkey=r"SOFTWARE\Policies\Microsoft\Windows\AppCompat",
            value_name="AITEnable",
            current_value=None,
            recommended_value=0,
            is_hardened=False,
            description="Disables collection of application performance and crash telemetry",
        ),
        TelemetrySetting(
            id="advertising_id",
            name="Windows Advertising ID",
            hive_name="HKCU",
            subkey=r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
            value_name="Enabled",
            current_value=None,
            recommended_value=0,
            is_hardened=False,
            description="Blocks targeted advertising tracking across Windows Store applications",
        ),
        TelemetrySetting(
            id="activity_history",
            name="Timeline Activity Feed",
            hive_name="HKLM",
            subkey=r"SOFTWARE\Policies\Microsoft\Windows\System",
            value_name="EnableActivityFeed",
            current_value=None,
            recommended_value=0,
            is_hardened=False,
            description="Prevents Windows from publishing user file and web activities to Microsoft cloud",
        ),
        TelemetrySetting(
            id="publish_activities",
            name="Publish User Activities",
            hive_name="HKLM",
            subkey=r"SOFTWARE\Policies\Microsoft\Windows\System",
            value_name="PublishUserActivities",
            current_value=None,
            recommended_value=0,
            is_hardened=False,
            description="Disables syncing of local application activity sessions",
        ),
        TelemetrySetting(
            id="wer_data",
            name="WER Additional Data Upload",
            hive_name="HKLM",
            subkey=r"SOFTWARE\Policies\Microsoft\Windows\Windows Error Reporting",
            value_name="DontSendAdditionalData",
            current_value=None,
            recommended_value=1,
            is_hardened=False,
            description="Prevents Windows Error Reporting from transmitting memory dumps or document contents",
        ),
    ]

    @classmethod
    def _read_dword(cls, hive, subkey: str, name: str) -> Optional[int]:
        if winreg is None:
            return None
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, name)
                return int(val)
        except (FileNotFoundError, OSError):
            return None
        """_read_dword."""
        """_read_dword."""

    @classmethod
    def _write_dword(cls, hive, subkey: str, name: str, value: int) -> bool:
        if winreg is None:
            return False
        try:
            with winreg.CreateKeyEx(hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
                return True
        except PermissionError:
            return False
        except Exception:
            return False
        """_write_dword."""
        """_write_dword."""

    @classmethod
    def audit_telemetry(cls) -> TelemetryAuditReport:
        """Inspect all diagnostic telemetry settings and calculate score."""
        settings: List[TelemetrySetting] = []
        hardened_cnt = 0

        for s in cls.DATA_COLLECTION_POLICIES:
            hive = winreg.HKEY_LOCAL_MACHINE if s.hive_name == "HKLM" and winreg else (winreg.HKEY_CURRENT_USER if winreg else None)
            val = cls._read_dword(hive, s.subkey, s.value_name) if hive else None

            is_hard = (val == s.recommended_value)
            if is_hard:
                hardened_cnt += 1

            settings.append(TelemetrySetting(
                id=s.id,
                name=s.name,
                hive_name=s.hive_name,
                subkey=s.subkey,
                value_name=s.value_name,
                current_value=val,
                recommended_value=s.recommended_value,
                is_hardened=is_hard,
                description=s.description,
            ))

        total = len(settings)
        score = (hardened_cnt / total * 100.0) if total > 0 else 0.0

        return TelemetryAuditReport(
            total_settings=total,
            hardened_count=hardened_cnt,
            exposed_count=total - hardened_cnt,
            privacy_score_percent=round(score, 1),
            settings=settings,
        )

    @classmethod
    def apply_maximum_privacy(cls) -> Tuple[int, List[str]]:
        """Harden all telemetry settings to maximum privacy values."""
        if winreg is None:
            return 0, ["Windows only"]

        applied = 0
        errors: List[str] = []

        for s in cls.DATA_COLLECTION_POLICIES:
            hive = winreg.HKEY_LOCAL_MACHINE if s.hive_name == "HKLM" else winreg.HKEY_CURRENT_USER
            ok = cls._write_dword(hive, s.subkey, s.value_name, s.recommended_value)
            if ok:
                applied += 1
            else:
                errors.append(f"Failed to set {s.name} (Administrator privileges required)")

        return applied, errors
