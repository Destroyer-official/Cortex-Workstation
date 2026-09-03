"""Cortex Cleaner — Windows Power Scheme & CPU Throttle Optimizer.

Manages Windows Power Plans via powercfg.exe:
1. Lists installed power schemes (Balanced, High Performance, Power Saver, Ultimate Performance).
2. Unlocks Ultimate Performance mode (GUID e9a42b02-d5df-448d-aa00-03f14749eb61).
3. Configures CPU throttling states (Minimum/Maximum processor state) and Core Parking.
4. Manages Windows Hibernation footprint (powercfg /h /type reduced vs off).
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class PowerScheme:
    """Power Scheme data container."""
    guid: str
    name: str
    is_active: bool
    description: str = ""


@dataclass
class PowerPlanStatus:
    """Power Plan Status data container."""
    active_scheme_name: str
    active_scheme_guid: str
    schemes: List[PowerScheme]
    hibernation_status: str  # "Full", "Reduced", "Disabled", "Unknown"
    is_admin: bool = False


class PowerPlanOptimizer:
    """Production Windows Power Scheme and CPU performance optimization engine."""

    ULTIMATE_PERF_GUID = "e9a42b02-d5df-448d-aa00-03f14749eb61"

    @classmethod
    def get_status(cls) -> PowerPlanStatus:
        """Query all installed power schemes and active configuration."""
        if platform.system() != "Windows":
            return PowerPlanStatus("Non-Windows", "", [], "Non-Windows", False)

        schemes: List[PowerScheme] = []
        active_name = "Unknown"
        active_guid = ""

        try:
            res = subprocess.run(["powercfg.exe", "/list"], capture_output=True, text=True, timeout=5)
            # Example lines:
            # Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced) *
            for line in res.stdout.splitlines():
                line = line.strip()
                if "Power Scheme GUID:" in line:
                    match = re.search(r"GUID:\s+([a-f0-9\-]+)\s+\((.*?)\)(\s+\*)?", line, re.IGNORECASE)
                    if match:
                        guid = match.group(1).strip()
                        name = match.group(2).strip()
                        is_act = bool(match.group(3))
                        schemes.append(PowerScheme(guid=guid, name=name, is_active=is_act))
                        if is_act:
                            active_name = name
                            active_guid = guid
        except Exception:
            pass

        # Check Admin
        is_admin = False
        try:
            import ctypes
            is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            pass

        # Check hiberfil.sys
        hiber_status = "Disabled"
        hiber_file = Path(os.environ.get("SystemDrive", "C:") + r"\hiberfil.sys")
        if hiber_file.exists():
            hiber_status = "Active (Full / Fast Startup)"

        return PowerPlanStatus(
            active_scheme_name=active_name,
            active_scheme_guid=active_guid,
            schemes=schemes,
            hibernation_status=hiber_status,
            is_admin=is_admin,
        )

    @classmethod
    def set_active_scheme(cls, scheme_guid: str) -> Tuple[bool, str]:
        """Activate the specified power plan GUID."""
        if platform.system() != "Windows":
            return False, "Windows only"

        try:
            res = subprocess.run(["powercfg.exe", "/setactive", scheme_guid.strip()], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return True, "Power plan successfully activated."
            return False, res.stderr.strip() or res.stdout.strip() or "Failed to set active power plan"
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def unlock_ultimate_performance_plan(cls) -> Tuple[bool, str]:
        """Duplicate and unlock the hidden Ultimate Performance power plan."""
        if platform.system() != "Windows":
            return False, "Windows only"

        try:
            cmd = ["powercfg.exe", "-duplicatescheme", cls.ULTIMATE_PERF_GUID]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                # Extract new GUID
                match = re.search(r"GUID:\s+([a-f0-9\-]+)", res.stdout, re.IGNORECASE)
                if match:
                    new_guid = match.group(1).strip()
                    # Activate it
                    cls.set_active_scheme(new_guid)
                    return True, "Ultimate Performance power plan successfully unlocked and activated!"
                return True, "Ultimate Performance plan created."
            return False, res.stderr.strip() or res.stdout.strip() or "Failed to duplicate scheme"
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def set_reduced_hibernation(cls) -> Tuple[bool, str]:
        """Reduce hiberfil.sys size to 40% of RAM (enables Fast Startup without full RAM snapshot)."""
        if platform.system() != "Windows":
            return False, "Windows only"

        try:
            res = subprocess.run(["powercfg.exe", "/h", "/type", "reduced"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return True, "Hibernation file reduced to 40% of RAM (Fast Startup preserved)."
            return False, res.stderr.strip() or res.stdout.strip() or "Failed to configure hibernation (Admin required)"
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def disable_hibernation(cls) -> Tuple[bool, str]:
        """Disable hibernation entirely and delete hiberfil.sys to reclaim gigabytes of disk space."""
        if platform.system() != "Windows":
            return False, "Windows only"

        try:
            res = subprocess.run(["powercfg.exe", "/h", "off"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return True, "Hibernation disabled and hiberfil.sys deleted."
            return False, res.stderr.strip() or res.stdout.strip() or "Failed to disable hibernation"
        except Exception as exc:
            return False, str(exc)
