"""Cortex Cleaner — Enterprise Network Stack & DNS Optimizer.

Flushes DNS Resolver cache, purges ARP tables, resets Winsock catalog and TCP/IP stack,
and inspects/tunes TCP Window Auto-Tuning, RSS, and ECN capabilities via netsh.
"""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class TcpGlobalSettings:
    """Tcp Global Settings data container."""
    autotuning_level: str = "normal"
    receive_side_scaling: str = "enabled"
    ecn_capability: str = "disabled"
    timestamps: str = "disabled"
    rsc: str = "enabled"
    raw_output: str = ""


@dataclass
class NetworkResetReport:
    """Network Reset Report data container."""
    dns_flushed: bool = False
    arp_cleared: bool = False
    winsock_reset: bool = False
    tcp_ip_reset: bool = False
    output_messages: List[str] = None

    def __post_init__(self):
        if self.output_messages is None:
            self.output_messages = []
        """__post_init__."""
        """__post_init__."""


class NetworkStackOptimizer:
    """Production Windows network stack diagnostic and optimization engine."""

    @classmethod
    def flush_dns(cls) -> Tuple[bool, str]:
        """Flush the Windows DNS Resolver cache (ipconfig /flushdns)."""
        if platform.system() != "Windows":
            return False, "Windows only"

        try:
            res = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return True, "Successfully flushed the DNS Resolver Cache."
            return False, res.stderr.strip() or "Failed to flush DNS cache"
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def clear_arp_cache(cls) -> Tuple[bool, str]:
        """Purge ARP cache tables (netsh interface ip delete arpcache)."""
        if platform.system() != "Windows":
            return False, "Windows only"

        try:
            res = subprocess.run(["netsh", "interface", "ip", "delete", "arpcache"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return True, "ARP Cache purged successfully."
            return False, res.stderr.strip() or "Failed to delete ARP cache (Admin rights required)"
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def reset_winsock(cls) -> Tuple[bool, str]:
        """Reset the Winsock catalog back to default configuration."""
        if platform.system() != "Windows":
            return False, "Windows only"

        try:
            res = subprocess.run(["netsh", "winsock", "reset"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return True, "Winsock catalog reset successfully. A reboot may be recommended."
            return False, res.stderr.strip() or "Failed to reset Winsock"
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def reset_tcp_ip_stack(cls) -> Tuple[bool, str]:
        """Reset the TCP/IP stack configuration."""
        if platform.system() != "Windows":
            return False, "Windows only"

        try:
            res = subprocess.run(["netsh", "int", "ip", "reset"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return True, "TCP/IP Stack reset successfully."
            return False, res.stderr.strip() or "Failed to reset TCP/IP"
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def get_tcp_settings(cls) -> TcpGlobalSettings:
        """Query active Windows TCP global parameters."""
        if platform.system() != "Windows":
            return TcpGlobalSettings()

        settings = TcpGlobalSettings()
        try:
            res = subprocess.run(["netsh", "int", "tcp", "show", "global"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                settings.raw_output = res.stdout
                for line in res.stdout.splitlines():
                    lower = line.lower()
                    if "receive window auto-tuning level" in lower or "auto-tuning level" in lower:
                        settings.autotuning_level = line.split(":", 1)[1].strip()
                    elif "receive-side scaling state" in lower or "rss" in lower:
                        settings.receive_side_scaling = line.split(":", 1)[1].strip()
                    elif "ecn capability" in lower:
                        settings.ecn_capability = line.split(":", 1)[1].strip()
                    elif "rfc 1323 timestamps" in lower or "timestamps" in lower:
                        settings.timestamps = line.split(":", 1)[1].strip()
                    elif "receive segment coalescing state" in lower or "rsc" in lower:
                        settings.rsc = line.split(":", 1)[1].strip()
        except Exception:
            pass

        return settings

    @classmethod
    def set_tcp_autotuning(cls, level: str = "normal") -> Tuple[bool, str]:
        """Configure TCP Window Auto-Tuning (disabled, highlyrestricted, restricted, normal, experimental)."""
        if platform.system() != "Windows":
            return False, "Windows only"

        valid = ("disabled", "highlyrestricted", "restricted", "normal", "experimental")
        if level.lower() not in valid:
            return False, f"Invalid autotuning level. Choose from: {', '.join(valid)}"

        try:
            res = subprocess.run(["netsh", "int", "tcp", "set", "global", f"autotuninglevel={level.lower()}"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return True, f"TCP Auto-Tuning level set to '{level}'."
            return False, res.stderr.strip() or res.stdout.strip()
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def set_ecn_capability(cls, state: str = "enabled") -> Tuple[bool, str]:
        """Configure Explicit Congestion Notification (enabled / disabled)."""
        if platform.system() != "Windows":
            return False, "Windows only"

        try:
            res = subprocess.run(["netsh", "int", "tcp", "set", "global", f"ecncapability={state.lower()}"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return True, f"ECN capability set to '{state}'."
            return False, res.stderr.strip() or res.stdout.strip()
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def execute_complete_network_repair(cls) -> NetworkResetReport:
        """Perform a complete flush and reset of DNS, ARP, Winsock, and TCP/IP."""
        report = NetworkResetReport()

        ok, msg = cls.flush_dns()
        report.dns_flushed = ok
        report.output_messages.append(f"DNS: {msg}")

        ok, msg = cls.clear_arp_cache()
        report.arp_cleared = ok
        report.output_messages.append(f"ARP: {msg}")

        ok, msg = cls.reset_winsock()
        report.winsock_reset = ok
        report.output_messages.append(f"Winsock: {msg}")

        ok, msg = cls.reset_tcp_ip_stack()
        report.tcp_ip_reset = ok
        report.output_messages.append(f"TCP/IP: {msg}")

        return report
