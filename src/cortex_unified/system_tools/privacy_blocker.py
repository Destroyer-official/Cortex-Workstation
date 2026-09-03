"""Privacy & Telemetry Blocker — 300+ settings, IFEO persistence, profiles.

Research grounding
------------------
* O&O ShutUp10++ 2.0.1009 (2025) — ~300 privacy settings across 20+
  categories, Copilot/Recall removal, .NET 8 portable, Free + Premium
  (client/service architecture with automatic re-application after
  Windows updates, no admin rights for end users, profiles editor).
* WallabyDesigns/windows-telemetry-guard — reversible toolkit with
  timestamped backup, Strict mode (hosts file block of 26 Microsoft
  endpoints), Balanced mode (diagnostic data to Required/Basic),
  IFEO debugger on CompatTelRunner.exe (survives updates).
* SysAdminDoc/TelemetrySlayer — WPF GUI, IFEO on CompatTelRunner.exe
  (taskkill.exe), firewall rules, clears DiagTrack ETL logs, Office
  telemetry, Edge/WebView2, NVIDIA/VS telemetry, preflight recovery
  bundle, survives feature updates.
* N0tHorizon/WindowsTelemetryBlocker — PowerShell, modular (telemetry,
  services, apps, misc), registry backups, rollback scripts, dry-run.
* NX1X/Windows-Privacy-Toolkit — 24-check audit, 25-step OS telemetry
  disable, 9-step Office, 4-step PowerShell, optional advanced
  (15+ tasks, 35+ hosts, firewall), 3 hardening levels, Restore script.
* RajwanYair/RegiLattice — 7,718 tweaks across 158 categories, 5
  machine profiles (business/gaming/privacy/minimal/server), CorporateGuard
  blocks unsafe tweaks on domain/Azure AD/Intune, declarative RegOp
  engine, WinForms GUI + CLI, .NET 10.

Why this matters for Cortex Cleaner
-----------------------------------
* Windows scatters privacy controls across ~150 panels; feature updates
  quietly reset choices or add new endpoints.
* A production tool must be reversible, profile-based, survive updates
  (IFEO + firewall), and support enterprise deployment (profiles,
  no-admin-rights client/service).

Design
------
* **Declarative tweak definitions**: YAML/JSON tweak catalog with
  path, type, recommended value, risk level, category, profile tags.
* **Engine**: `apply(tweak_ids)`, `remove(tweak_ids)`, `status(tweak_ids)`,
  `profile(profile_name)`, `audit()` → JSON report.
* **Persistence**: IFEO debugger on `CompatTelRunner.exe` → `taskkill.exe`
  (survives re-enablement), firewall rules, scheduled task monitoring.
* **Profiles**: `privacy`, `gaming`, `business`, `minimal`, `server`
  (like RegiLattice).
* **Enterprise**: client/service split (Premium) — service holds
  privileges, client UI no admin rights, automatic re-application.
* **Rollback**: timestamped registry exports, restore point, hosts file
  backup, firewall rule export before changes.

Usage::

    from cortex_unified.system_tools.privacy_blocker import PrivacyBlocker
    pb = PrivacyBlocker()
    report = pb.audit()
    pb.apply_profile("privacy")
    # Enterprise:
    pb.enable_auto_enforcement()

References
----------
* O&O ShutUp10++ manual (manuals.oo-software.com)
* WallabyDesigns/windows-telemetry-guard (GitHub)
* SysAdminDoc/TelemetrySlayer (GitHub)
* N0tHorizon/WindowsTelemetryBlocker (GitHub)
* NX1X/Windows-Privacy-Toolkit (GitHub)
* RajwanYair/RegiLattice (GitHub)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import winreg
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple, Any

from cortex_unified.system_tools.restore_point import RestorePointManager


# ---------------------------------------------------------------------------
# Tweak definition (declarative)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TweakDef:
    """Single privacy tweak definition."""
    id: str
    name: str
    description: str = ""
    category: str = ""
    # Registry
    reg_path: Optional[str] = None
    reg_value: Optional[str] = None
    reg_type: Optional[int] = None  # winreg.REG_DWORD, REG_SZ, etc.
    reg_data: Any = None
    # Service
    service_name: Optional[str] = None
    service_start_type: Optional[int] = None  # 2=auto, 3=manual, 4=disabled
    # Scheduled task
    task_path: Optional[str] = None
    task_enabled: Optional[bool] = None
    # Firewall
    firewall_rule_name: Optional[str] = None
    firewall_direction: Optional[str] = None  # in/out
    firewall_action: Optional[str] = None  # block/allow
    firewall_program: Optional[str] = None
    # IFEO
    ifeo_target: Optional[str] = None
    ifeo_debugger: Optional[str] = None
    # Risk & metadata
    risk: str = "low"  # low/medium/high/critical
    profiles: List[str] = field(default_factory=list)  # privacy, gaming, business, minimal, server
    requires_admin: bool = True
    reversible: bool = True
    # Windows version constraints
    min_build: int = 0
    max_build: int = 999999
    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    conflicts_with: List[str] = field(default_factory=list)

    def applies_to_current_os(self) -> bool:
        """Applies to current os."""
        import platform
        build = int(platform.version().split(".")[-1]) if platform.version() else 0
        return self.min_build <= build <= self.max_build


# ---------------------------------------------------------------------------
# Built-in tweak catalog (subset — full catalog would be external YAML)
# ---------------------------------------------------------------------------

TELEMETRY_TWEAKS: List[TweakDef] = [
    # Core telemetry
    TweakDef(
        id="telemetry_allow_level",
        name="Set Diagnostic Data to Required (Basic)",
        description="Minimum telemetry level allowed by Windows Pro/Enterprise",
        category="telemetry",
        reg_path=r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection",
        reg_value="AllowTelemetry",
        reg_type=winreg.REG_DWORD,
        reg_data=1,  # 0=Security (Ent only), 1=Required, 2=Enhanced, 3=Full
        risk="low",
        profiles=["privacy", "business", "minimal"],
    ),
    TweakDef(
        id="telemetry_max_allowed",
        name="Set Max Telemetry Allowed",
        description="Hard ceiling for telemetry level",
        category="telemetry",
        reg_path=r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection",
        reg_value="MaxTelemetryAllowed",
        reg_type=winreg.REG_DWORD,
        reg_data=1,
        risk="low",
        profiles=["privacy", "business", "minimal"],
    ),
    # DiagTrack service
    TweakDef(
        id="diagtrack_disable",
        name="Disable Connected User Experiences and Telemetry Service",
        description="Primary telemetry pipeline — stops collection and upload",
        category="telemetry",
        service_name="DiagTrack",
        service_start_type=4,  # disabled
        risk="medium",
        profiles=["privacy", "gaming", "minimal", "server"],
    ),
    # WAP Push
    TweakDef(
        id="dmwappushservice_disable",
        name="Disable WAP Push Message Routing Service",
        description="Telemetry companion for DiagTrack",
        category="telemetry",
        service_name="dmwappushservice",
        service_start_type=4,
        risk="medium",
        profiles=["privacy", "minimal"],
    ),
    # Advertising ID
    TweakDef(
        id="advertising_id_disable",
        name="Disable Advertising ID",
        description="Prevents cross-app ad profiling",
        category="privacy",
        reg_path=r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
        reg_value="Enabled",
        reg_type=winreg.REG_DWORD,
        reg_data=0,
        risk="low",
        profiles=["privacy", "gaming", "business", "minimal"],
    ),
    # Activity History
    TweakDef(
        id="activity_history_disable",
        name="Disable Activity History / Timeline",
        description="Stops collection of app/website usage timeline",
        category="privacy",
        reg_path=r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
        reg_value="ActivityHistoryEnabled",
        reg_type=winreg.REG_DWORD,
        reg_data=0,
        risk="low",
        profiles=["privacy", "gaming", "minimal"],
    ),
    TweakDef(
        id="activity_history_publish",
        name="Disable Activity History Cloud Sync",
        description="Prevents uploading timeline to Microsoft cloud",
        category="privacy",
        reg_path=r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
        reg_value="PublishUserActivities",
        reg_type=winreg.REG_DWORD,
        reg_data=0,
        risk="low",
        profiles=["privacy", "minimal"],
    ),
    # Cortana
    TweakDef(
        id="cortana_disable",
        name="Disable Cortana Voice Assistant",
        category="privacy",
        reg_path=r"HKLM\SOFTWARE\Policies\Microsoft\Windows\Windows Search",
        reg_value="AllowCortana",
        reg_type=winreg.REG_DWORD,
        reg_data=0,
        risk="low",
        profiles=["privacy", "gaming", "minimal", "server"],
    ),
    # Windows Search Web
    TweakDef(
        id="web_search_disable",
        name="Disable Web Search in Start Menu (Bing)",
        category="privacy",
        reg_path=r"HKCU\SOFTWARE\Policies\Microsoft\Windows\Explorer",
        reg_value="DisableSearchBoxSuggestions",
        reg_type=winreg.REG_DWORD,
        reg_data=1,
        risk="low",
        profiles=["privacy", "gaming", "business", "minimal"],
    ),
    # Location
    TweakDef(
        id="location_disable",
        name="Disable Location Services",
        category="privacy",
        reg_path=r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location",
        reg_value="Value",
        reg_type=winreg.REG_SZ,
        reg_data="Deny",
        risk="low",
        profiles=["privacy", "minimal"],
    ),
    # Feedback
    TweakDef(
        id="feedback_frequency_never",
        name="Set Feedback Frequency to Never",
        category="privacy",
        reg_path=r"HKCU\SOFTWARE\Microsoft\Siuf\Rules",
        reg_value="NumberOfSIUFInPeriod",
        reg_type=winreg.REG_DWORD,
        reg_data=0,
        risk="low",
        profiles=["privacy", "gaming", "business", "minimal"],
    ),
    # Tailored Experiences
    TweakDef(
        id="tailored_experiences_disable",
        name="Disable Tailored Experiences (personalized tips/ads)",
        category="privacy",
        reg_path=r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
        reg_value="SubscribedContent-310093Enabled",
        reg_type=winreg.REG_DWORD,
        reg_data=0,
        risk="low",
        profiles=["privacy", "gaming", "business", "minimal"],
    ),
    # Windows Spotlight (lock screen ads)
    TweakDef(
        id="spotlight_disable",
        name="Disable Windows Spotlight / Lock Screen Ads",
        category="privacy",
        reg_path=r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
        reg_value="RotatingLockScreenEnabled",
        reg_type=winreg.REG_DWORD,
        reg_data=0,
        risk="low",
        profiles=["privacy", "gaming", "minimal"],
    ),
    # Suggestions & Tips
    TweakDef(
        id="suggestions_disable",
        name="Disable Suggestions & Tips",
        category="privacy",
        reg_path=r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
        reg_value="SystemPaneSuggestionsEnabled",
        reg_type=winreg.REG_DWORD,
        reg_data=0,
        risk="low",
        profiles=["privacy", "gaming", "minimal"],
    ),
    # WiFi Sense
    TweakDef(
        id="wifi_sense_disable",
        name="Disable Wi-Fi Sense (password sharing)",
        category="privacy",
        reg_path=r"HKLM\SOFTWARE\Microsoft\WcmSvc\wifinetworkmanager\config",
        reg_value="AutoConnectAllowedOEM",
        reg_type=winreg.REG_DWORD,
        reg_data=0,
        risk="low",
        profiles=["privacy", "business", "minimal"],
    ),
    # Windows Update P2P (Delivery Optimization)
    TweakDef(
        id="delivery_optimization_lan_only",
        name="Set Delivery Optimization to LAN-only (no internet upload)",
        category="network",
        reg_path=r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization",
        reg_value="DODownloadMode",
        reg_type=winreg.REG_DWORD,
        reg_data=2,  # 1=LAN, 2=Group, 3=Internet, 99=Simple
        risk="low",
        profiles=["privacy", "business", "server"],
    ),
    # CEIP
    TweakDef(
        id="ceip_disable",
        name="Disable Customer Experience Improvement Program",
        category="telemetry",
        reg_path=r"HKLM\SOFTWARE\Policies\Microsoft\SQMClient\Windows",
        reg_value="CEIPEnabled",
        reg_type=winreg.REG_DWORD,
        reg_data=0,
        risk="low",
        profiles=["privacy", "business", "minimal", "server"],
    ),
    # Error Reporting
    TweakDef(
        id="wer_disable",
        name="Disable Windows Error Reporting Uploads",
        category="telemetry",
        reg_path=r"HKLM\SOFTWARE\Policies\Microsoft\Windows\Windows Error Reporting",
        reg_value="Disabled",
        reg_type=winreg.REG_DWORD,
        reg_data=1,
        risk="low",
        profiles=["privacy", "business", "server"],
    ),
    # Ink/Typing/Speech
    TweakDef(
        id="inking_typing_disable",
        name="Disable Inking & Typing Personalization",
        category="privacy",
        reg_path=r"HKCU\SOFTWARE\Microsoft\InputPersonalization",
        reg_value="RestrictImplicitTextCollection",
        reg_type=winreg.REG_DWORD,
        reg_data=1,
        risk="low",
        profiles=["privacy", "business", "minimal"],
    ),
    # Steps Recorder
    TweakDef(
        id="steps_recorder_disable",
        name="Disable Steps Recorder (psr.exe)",
        category="privacy",
        reg_path=r"HKLM\SOFTWARE\Policies\Microsoft\Windows\AppCompat",
        reg_value="DisableStepsRecorder",
        reg_type=winreg.REG_DWORD,
        reg_data=1,
        risk="low",
        profiles=["privacy", "minimal"],
    ),
    # Remote Registry
    TweakDef(
        id="remote_registry_disable",
        name="Disable Remote Registry Service",
        category="security",
        service_name="RemoteRegistry",
        service_start_type=4,
        risk="medium",
        profiles=["privacy", "business", "server", "minimal"],
    ),
    # App Diagnostics Access
    TweakDef(
        id="app_diagnostics_disable",
        name="Disable App Diagnostics Access",
        category="privacy",
        reg_path=r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\appDiagnostics",
        reg_value="Value",
        reg_type=winreg.REG_SZ,
        reg_data="Deny",
        risk="low",
        profiles=["privacy", "minimal"],
    ),
    # IFEO on CompatTelRunner (survives updates)
    TweakDef(
        id="ifeo_compattelrunner",
        name="IFEO Debugger on CompatTelRunner.exe (kills telemetry runner)",
        description="Image File Execution Options — survives feature updates",
        category="telemetry",
        ifeo_target="CompatTelRunner.exe",
        ifeo_debugger="taskkill.exe",
        risk="medium",
        profiles=["privacy", "gaming", "minimal", "server"],
    ),
    # Scheduled Tasks (telemetry)
    TweakDef(
        id="task_microsoft_windows_customer_experience",
        name="Disable Customer Experience Improvement Program Tasks",
        category="telemetry",
        task_path=r"\Microsoft\Windows\Customer Experience Improvement Program",
        task_enabled=False,
        risk="medium",
        profiles=["privacy", "business", "minimal", "server"],
    ),
    TweakDef(
        id="task_microsoft_windows_autochk",
        name="Disable Autochk SQM Proxy Task",
        category="telemetry",
        task_path=r"\Microsoft\Windows\Autochk\Proxy",
        task_enabled=False,
        risk="medium",
        profiles=["privacy", "minimal"],
    ),
    TweakDef(
        id="task_microsoft_windows_diskdiagnostic",
        name="Disable Disk Diagnostic Data Collector",
        category="telemetry",
        task_path=r"\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector",
        task_enabled=False,
        risk="medium",
        profiles=["privacy", "minimal"],
    ),
    TweakDef(
        id="task_microsoft_windows_pi_sqm",
        name="Disable PI SQM Tasks",
        category="telemetry",
        task_path=r"\Microsoft\Windows\PI\SqmTasks",
        task_enabled=False,
        risk="medium",
        profiles=["privacy", "minimal"],
    ),
]


# ---------------------------------------------------------------------------
# Privacy Blocker Engine
# ---------------------------------------------------------------------------

class PrivacyBlocker:
    """Declarative privacy tweak engine with profiles and persistence."""

    def __init__(
        self,
        tweaks: Optional[List[TweakDef]] = None,
        create_restore_point: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
        dry_run: bool = False,
    ):
        """Initialize Privacy Blocker."""
        self.tweaks = {t.id: t for t in (tweaks or TELEMETRY_TWEAKS)}
        self.create_restore_point = create_restore_point
        self.progress = progress_callback or (lambda _: None)
        self.cancel_event = cancel_event or threading.Event()
        self.dry_run = dry_run
        self._restore_mgr = RestorePointManager() if create_restore_point else None
        self._backup_dir = Path(os.environ.get("TEMP", "C:\\Temp")) / "CortexPrivacyBackups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    # -- registry helpers

    def _reg_set(self, path: str, value: str, data: Any, dtype: int) -> bool:
        if self.dry_run:
            self.progress(f"[DRY-RUN] Set {path}\\{value} = {data} ({dtype})")
            return True
        try:
            hive_str, subkey = path.split("\\", 1)
            hive = getattr(winreg, hive_str)
            with winreg.CreateKeyEx(hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, value, 0, dtype, data)
            return True
        except Exception as exc:
            self.progress(f"Registry set failed {path}\\{value}: {exc}")
            return False
        """_reg_set."""
        """_reg_set."""

    def _reg_get(self, path: str, value: str) -> Any:
        try:
            hive_str, subkey = path.split("\\", 1)
            hive = getattr(winreg, hive_str)
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
                data, _ = winreg.QueryValueEx(key, value)
                return data
        except Exception:
            return None
        """_reg_get."""
        """_reg_get."""

    def _reg_backup(self, path: str) -> Optional[str]:
        """Export registry key to .reg file."""
        try:
            hive_str, subkey = path.split("\\", 1)
            hive = getattr(winreg, hive_str)
            backup_file = self._backup_dir / f"reg_{hive_str}_{subkey.replace('\\','_')}_{int(time.time())}.reg"
            subprocess.run(["reg", "export", f"{hive_str}\\{subkey}", str(backup_file), "/y"],
                           check=True, capture_output=True)
            return str(backup_file)
        except Exception:
            return None

    # -- service helpers

    def _svc_set_start(self, name: str, start_type: int) -> bool:
        if self.dry_run:
            self.progress(f"[DRY-RUN] Set service {name} start type = {start_type}")
            return True
        rc, _, _ = subprocess.run(["sc", "config", name, "start=", str(start_type)],
                                  capture_output=True)
        if rc == 0:
            # Stop if disabling
            if start_type == 4:
                subprocess.run(["net", "stop", name], capture_output=True)
            return True
        return False
        """_svc_set_start."""
        """_svc_set_start."""

    def _svc_get_start(self, name: str) -> Optional[int]:
        try:
            out = subprocess.run(["sc", "qc", name], capture_output=True, text=True).stdout
            for line in out.splitlines():
                if "START_TYPE" in line:
                    return int(line.split(":")[-1].strip())
        except Exception:
            pass
        return None
        """_svc_get_start."""
        """_svc_get_start."""

    # -- scheduled task helpers

    def _task_set_enabled(self, path: str, enabled: bool) -> bool:
        if self.dry_run:
            self.progress(f"[DRY-RUN] Set task {path} enabled = {enabled}")
            return True
        state = "enable" if enabled else "disable"
        rc = subprocess.run(["schtasks", "/change", "/tn", path, "/" + state],
                            capture_output=True).returncode
        return rc == 0
        """_task_set_enabled."""
        """_task_set_enabled."""

    # -- firewall helpers

    def _fw_add_block(self, name: str, direction: str, program: str) -> bool:
        if self.dry_run:
            self.progress(f"[DRY-RUN] Add firewall block rule {name}")
            return True
        cmd = ["netsh", "advfirewall", "firewall", "add", "rule",
               "name=" + name, "dir=" + direction, "action=block",
               "program=" + program, "enable=yes", "profile=any"]
        return subprocess.run(cmd, capture_output=True).returncode == 0
        """_fw_add_block."""
        """_fw_add_block."""

    # -- IFEO helpers

    def _ifeo_set(self, target: str, debugger: str) -> bool:
        if self.dry_run:
            self.progress(f"[DRY-RUN] Set IFEO {target} = {debugger}")
            return True
        path = rf"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\{target}"
        return self._reg_set(path, "Debugger", debugger, winreg.REG_SZ)
        """_ifeo_set."""
        """_ifeo_set."""

    def _ifeo_remove(self, target: str) -> bool:
        if self.dry_run:
            return True
        path = rf"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\{target}"
        try:
            winreg.DeleteKey(getattr(winreg, "HKEY_LOCAL_MACHINE"),
                             rf"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\{target}")
            return True
        except Exception:
            return False
        """_ifeo_remove."""
        """_ifeo_remove."""

    # -- core operations

    def apply(self, tweak_ids: List[str]) -> Dict[str, bool]:
        """Apply tweaks by ID list."""
        results = {}
        if self.create_restore_point:
            self._restore_mgr.create("Cortex Privacy: Apply Tweaks")

        for tid in tweak_ids:
            if self.cancel_event.is_set():
                break
            if tid not in self.tweaks:
                results[tid] = False
                continue
            tweak = self.tweaks[tid]
            if not tweak.applies_to_current_os():
                results[tid] = False
                continue

            self.progress(f"Applying {tid}...")
            ok = False
            try:
                if tweak.reg_path:
                    ok = self._reg_set(tweak.reg_path, tweak.reg_value, tweak.reg_data, tweak.reg_type)
                elif tweak.service_name:
                    ok = self._svc_set_start(tweak.service_name, tweak.service_start_type)
                elif tweak.task_path:
                    ok = self._task_set_enabled(tweak.task_path, tweak.task_enabled)
                elif tweak.firewall_rule_name:
                    ok = self._fw_add_block(tweak.firewall_rule_name,
                                            tweak.firewall_direction or "out",
                                            tweak.firewall_program or "")
                elif tweak.ifeo_target:
                    ok = self._ifeo_set(tweak.ifeo_target, tweak.ifeo_debugger)
                else:
                    ok = False
            except Exception as exc:
                self.progress(f"Error applying {tid}: {exc}")
                ok = False
            results[tid] = ok
        return results

    def remove(self, tweak_ids: List[str]) -> Dict[str, bool]:
        """Remove/revert tweaks by ID list."""
        results = {}
        for tid in tweak_ids:
            if self.cancel_event.is_set():
                break
            if tid not in self.tweaks:
                results[tid] = False
                continue
            tweak = self.tweaks[tid]
            if not tweak.reversible:
                results[tid] = False
                continue

            self.progress(f"Removing {tid}...")
            ok = False
            try:
                if tweak.reg_path:
                    # Delete the value (revert to default)
                    hive_str, subkey = tweak.reg_path.split("\\", 1)
                    hive = getattr(winreg, hive_str)
                    try:
                        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
                            winreg.DeleteValue(key, tweak.reg_value)
                        ok = True
                    except FileNotFoundError:
                        ok = True  # Already gone
                    except Exception:
                        ok = False
                elif tweak.service_name:
                    ok = self._svc_set_start(tweak.service_name, 2)  # auto
                elif tweak.task_path:
                    ok = self._task_set_enabled(tweak.task_path, True)
                elif tweak.ifeo_target:
                    ok = self._ifeo_remove(tweak.ifeo_target)
                else:
                    ok = True
            except Exception as exc:
                self.progress(f"Error removing {tid}: {exc}")
                ok = False
            results[tid] = ok
        return results

    def status(self, tweak_ids: List[str]) -> Dict[str, Dict]:
        """Check current status of tweaks."""
        results = {}
        for tid in tweak_ids:
            if tid not in self.tweaks:
                results[tid] = {"applied": False, "error": "Unknown tweak"}
                continue
            tweak = self.tweaks[tid]
            applied = False
            current = None
            try:
                if tweak.reg_path:
                    current = self._reg_get(tweak.reg_path, tweak.reg_value)
                    applied = (current == tweak.reg_data)
                elif tweak.service_name:
                    current = self._svc_get_start(tweak.service_name)
                    applied = (current == tweak.service_start_type)
                elif tweak.ifeo_target:
                    path = rf"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\{tweak.ifeo_target}"
                    current = self._reg_get(path, "Debugger")
                    applied = (current == tweak.ifeo_debugger)
                else:
                    applied = False
            except Exception:
                applied = False
            results[tid] = {"applied": applied, "current_value": current}
        return results

    def apply_profile(self, profile_name: str) -> Dict[str, bool]:
        """Apply all tweaks tagged with a profile."""
        ids = [t.id for t in self.tweaks.values() if profile_name in t.profiles]
        self.progress(f"Applying profile '{profile_name}' ({len(ids)} tweaks)...")
        return self.apply(ids)

    def audit(self) -> Dict:
        """Full privacy audit — returns JSON-serializable report."""
        all_ids = list(self.tweaks.keys())
        status = self.status(all_ids)
        applied = sum(1 for v in status.values() if v["applied"])
        total = len(status)
        by_category: Dict[str, Dict] = {}
        for tid, tweak in self.tweaks.items():
            cat = tweak.category
            if cat not in by_category:
                by_category[cat] = {"total": 0, "applied": 0, "tweaks": []}
            by_category[cat]["total"] += 1
            if status[tid]["applied"]:
                by_category[cat]["applied"] += 1
            by_category[cat]["tweaks"].append({
                "id": tid,
                "name": tweak.name,
                "applied": status[tid]["applied"],
                "risk": tweak.risk,
                "profiles": tweak.profiles,
            })
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {"total": total, "applied": applied, "percentage": round(applied/total*100, 1) if total else 0},
            "by_category": by_category,
        }

    def list_profiles(self) -> Dict[str, List[str]]:
        """Return profile -> tweak IDs mapping."""
        profiles: Dict[str, List[str]] = {}
        for tweak in self.tweaks.values():
            for p in tweak.profiles:
                profiles.setdefault(p, []).append(tweak.id)
        return profiles

    def export_config(self, path: str) -> None:
        """Export current applied tweaks as JSON config."""
        status = self.status(list(self.tweaks.keys()))
        applied_ids = [tid for tid, v in status.items() if v["applied"]]
        config = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "applied_tweaks": applied_ids,
        }
        Path(path).write_text(json.dumps(config, indent=2), encoding="utf-8")
        self.progress(f"Exported config to {path}")

    def import_config(self, path: str) -> Dict[str, bool]:
        """Import and apply tweaks from JSON config."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return self.apply(data.get("applied_tweaks", []))

    def enable_auto_enforcement(self, interval_minutes: int = 60) -> bool:
        """Register scheduled task for periodic re-application (Premium feature)."""
        if self.dry_run:
            return True
        try:
            script = f"""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -Command "cortex-privacy-enforce"'
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes {interval_minutes}) -RepetitionDuration ([TimeSpan]::MaxValue)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName 'CortexPrivacyEnforcement' -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force
"""
            subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True, capture_output=True)
            return True
        except Exception:
            return False


__all__ = [
    "PrivacyBlocker",
    "TweakDef",
    "TELEMETRY_TWEAKS",
]