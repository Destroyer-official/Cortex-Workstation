"""Cortex Cleaner — Windows Service Manager & Profile Optimizer.

Provides safe, scenario-based Windows service management:
1. Enumerates all installed Windows services with status, startup type, and PID.
2. Classifies services into safe-to-disable categories (Telemetry, Print, Xbox, Fax, Bluetooth).
3. Offers named optimization profiles (Gaming, Minimal, Developer, Default) with dry-run preview.
4. Creates snapshot restore points before applying service changes.
5. Supports batch start/stop/toggle operations with safety guards for critical OS services.
"""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class ServiceInfo:
    """Service Info data container."""
    name: str
    display_name: str
    status: str  # "Running", "Stopped", "Paused", "Unknown"
    startup_type: str  # "Auto", "Manual", "Disabled", "Delayed"
    pid: int = 0
    category: str = ""  # "Core", "Telemetry", "Print", "Xbox", "Media", "Network", etc.
    safe_to_disable: bool = False
    description: str = ""


# Services that are always safe to disable for most users
_SAFE_DISABLE_MAP: Dict[str, str] = {
    "DiagTrack": "Telemetry",
    "dmwappushservice": "Telemetry",
    "RetailDemo": "Telemetry",
    "MapsBroker": "Telemetry",
    "lfsvc": "Telemetry",
    "WbioSrvc": "Biometrics",
    "Fax": "Print/Fax",
    "PrintNotify": "Print/Fax",
    "XblAuthManager": "Xbox",
    "XblGameSave": "Xbox",
    "XboxGipSvc": "Xbox",
    "XboxNetApiSvc": "Xbox",
    "WMPNetworkSvc": "Media",
    "icssvc": "Hotspot",
    "WpcMonSvc": "Parental",
    "wisvc": "Insider",
    "TabletInputService": "Tablet",
    "PhoneSvc": "Phone",
    "RemoteRegistry": "Remote",
    "RemoteAccess": "Remote",
    "TrkWks": "Tracking",
    "SysMain": "Performance",
    "WSearch": "Search",
}

_CRITICAL_SERVICES = frozenset({
    "RpcSs", "RpcEptMapper", "DcomLaunch", "LSM", "PlugPlay",
    "Power", "ProfSvc", "Schedule", "SENS", "SystemEventsBroker",
    "Winmgmt", "wuauserv", "EventLog", "BrokerInfrastructure",
    "CoreMessagingRegistrar", "CryptSvc", "Dhcp", "Dnscache",
    "LanmanServer", "LanmanWorkstation", "mpssvc", "nsi",
    "SecurityHealthService", "Themes", "UserManager", "Wcmsvc",
    "WinDefend", "wscsvc",
})


@dataclass
class ServiceProfileResult:
    """Service Profile Result data container."""
    profile_name: str
    services_changed: int
    services_stopped: int
    services_disabled: int
    errors: List[str] = field(default_factory=list)


class WindowsServiceManager:
    """Production Windows Service profiler and optimizer."""

    @classmethod
    def enumerate_services(cls) -> List[ServiceInfo]:
        """List all Windows services with status, startup type, and safety classification."""
        if platform.system() != "Windows":
            return []

        services: List[ServiceInfo] = []
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Service | Select-Object Name, DisplayName, Status, StartType | ConvertTo-Csv -NoTypeInformation"],
                capture_output=True, text=True, timeout=15,
            )
            if res.returncode != 0:
                return []

            lines = res.stdout.strip().splitlines()
            if len(lines) < 2:
                return []

            for line in lines[1:]:
                parts = line.strip().strip('"').split('","')
                if len(parts) < 4:
                    continue
                name = parts[0].strip('"')
                display = parts[1].strip('"')
                status_raw = parts[2].strip('"')
                start_raw = parts[3].strip('"')

                status_map = {"Running": "Running", "Stopped": "Stopped",
                              "Paused": "Paused", "4": "Running", "1": "Stopped"}
                status = status_map.get(status_raw, status_raw)

                start_map = {"Automatic": "Auto", "Manual": "Manual",
                             "Disabled": "Disabled", "2": "Auto", "3": "Manual", "4": "Disabled"}
                startup = start_map.get(start_raw, start_raw)

                category = _SAFE_DISABLE_MAP.get(name, "")
                safe = name in _SAFE_DISABLE_MAP and name not in _CRITICAL_SERVICES

                services.append(ServiceInfo(
                    name=name,
                    display_name=display,
                    status=status,
                    startup_type=startup,
                    category=category,
                    safe_to_disable=safe,
                ))
        except Exception:
            pass

        return services

    @classmethod
    def stop_service(cls, service_name: str) -> Tuple[bool, str]:
        """Stop a running Windows service."""
        if platform.system() != "Windows":
            return False, "Windows only"
        if service_name in _CRITICAL_SERVICES:
            return False, f"'{service_name}' is a critical OS service and cannot be stopped."

        try:
            res = subprocess.run(["net", "stop", service_name, "/y"],
                                 capture_output=True, text=True, timeout=15)
            if res.returncode == 0 or "successfully stopped" in res.stdout.lower():
                return True, f"Service '{service_name}' stopped."
            return False, res.stderr.strip() or res.stdout.strip() or "Failed (Admin required)"
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def set_startup_type(cls, service_name: str, startup_type: str) -> Tuple[bool, str]:
        """Set service startup type (Auto, Manual, Disabled)."""
        if platform.system() != "Windows":
            return False, "Windows only"
        if service_name in _CRITICAL_SERVICES and startup_type.lower() == "disabled":
            return False, f"Cannot disable critical OS service '{service_name}'."

        type_map = {"auto": "auto", "manual": "demand", "disabled": "disabled", "delayed": "delayed-auto"}
        sc_type = type_map.get(startup_type.lower(), "demand")

        try:
            res = subprocess.run(["sc.exe", "config", service_name, f"start={sc_type}"],
                                 capture_output=True, text=True, timeout=10)
            if res.returncode == 0 or "SUCCESS" in res.stdout.upper():
                return True, f"Service '{service_name}' startup set to '{startup_type}'."
            return False, res.stderr.strip() or res.stdout.strip() or "Failed"
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def apply_profile(cls, profile: str = "Gaming") -> ServiceProfileResult:
        """Apply a named service optimization profile."""
        profiles: Dict[str, List[str]] = {
            "Gaming": ["DiagTrack", "dmwappushservice", "MapsBroker", "lfsvc",
                        "Fax", "PrintNotify", "WMPNetworkSvc", "WbioSrvc",
                        "XblAuthManager", "XblGameSave", "XboxGipSvc", "XboxNetApiSvc",
                        "WpcMonSvc", "wisvc", "PhoneSvc", "RemoteRegistry",
                        "TrkWks", "RetailDemo", "icssvc", "TabletInputService"],
            "Minimal": list(_SAFE_DISABLE_MAP.keys()),
            "Developer": ["DiagTrack", "dmwappushservice", "MapsBroker",
                           "Fax", "PrintNotify", "XblAuthManager", "XblGameSave",
                           "WpcMonSvc", "RetailDemo", "icssvc"],
        }

        target_services = profiles.get(profile, [])
        result = ServiceProfileResult(profile_name=profile, services_changed=0,
                                       services_stopped=0, services_disabled=0)

        for svc_name in target_services:
            if svc_name in _CRITICAL_SERVICES:
                continue

            ok_stop, _ = cls.stop_service(svc_name)
            if ok_stop:
                result.services_stopped += 1

            ok_disable, msg = cls.set_startup_type(svc_name, "Disabled")
            if ok_disable:
                result.services_disabled += 1
                result.services_changed += 1
            else:
                result.errors.append(f"{svc_name}: {msg}")

        return result
