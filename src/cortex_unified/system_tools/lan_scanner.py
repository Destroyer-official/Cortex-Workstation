"""LAN device discovery - see what else is on your local network.

Reads the operating system's ARP cache (``arp -a``) to list the devices your
machine has recently talked to on the local network: their IP, MAC (hardware)
address, and a best-effort vendor guess from the MAC's OUI prefix for a handful
of common vendors. This is read-only and offline - it inspects a cache the OS
already maintains, it does not send probes or scan ports.

Why it's useful: spotting an unfamiliar device on your network (the kind of
"new device joined" alert premium tools charge for) is a simple, honest
security win. We clearly mark entries we can't identify rather than guessing.
"""

from __future__ import annotations

import logging
import platform
import re
import subprocess
from dataclasses import dataclass
from typing import Any

_LOG = logging.getLogger("cortex.system_tools.lan_scanner")
_IS_WINDOWS = platform.system() == "Windows"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

# A small, honest set of common OUI prefixes -> vendor. Not exhaustive; unknown
# prefixes are reported as "" rather than guessed.
_OUI = {
    "00:50:56": "VMware", "00:0c:29": "VMware", "00:05:69": "VMware",
    "08:00:27": "VirtualBox", "00:15:5d": "Microsoft Hyper-V",
    "b8:27:eb": "Raspberry Pi", "dc:a6:32": "Raspberry Pi", "e4:5f:01": "Raspberry Pi",
    "fc:fb:fb": "Cisco", "00:1a:11": "Google", "3c:5a:b4": "Google",
    "d8:eb:97": "TP-Link", "50:c7:bf": "TP-Link", "ac:84:c6": "TP-Link",
    "00:1d:0f": "TP-Link", "f4:f2:6d": "TP-Link",
    "00:1e:c2": "Apple", "a4:83:e7": "Apple", "f0:18:98": "Apple",
    "3c:07:54": "Apple", "ac:bc:32": "Apple",
    "00:12:fb": "Samsung", "5c:0a:5b": "Samsung", "e8:50:8b": "Samsung",
    "00:24:e4": "Withings", "18:b4:30": "Nest",
}

_ARP_RE = re.compile(
    r"(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-fA-F]{2}(?:[-:][0-9a-fA-F]{2}){5})\s+(\w+)"
)


@dataclass(slots=True)
class LanDevice:
    ip: str
    mac: str
    kind: str          # dynamic / static
    vendor: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"ip": self.ip, "mac": self.mac, "kind": self.kind, "vendor": self.vendor}


class LanScanner:
    """Enumerate LAN devices from the OS ARP cache (read-only)."""

    def scan(self) -> list[LanDevice]:
        out = self._run()
        return self._parse(out)

    @staticmethod
    def _vendor_for(mac: str) -> str:
        norm = mac.replace("-", ":").lower()
        return _OUI.get(norm[:8], "")

    @classmethod
    def _parse(cls, out: str | None) -> list[LanDevice]:
        if not out:
            return []
        devices: list[LanDevice] = []
        seen: set[str] = set()
        for line in out.splitlines():
            m = _ARP_RE.search(line)
            if not m:
                continue
            ip, mac, kind = m.group(1), m.group(2), m.group(3)
            mac = mac.replace("-", ":").lower()
            # Skip broadcast / multicast noise.
            if ip.endswith(".255") or ip.startswith("224.") or mac == "ff:ff:ff:ff:ff:ff":
                continue
            if ip in seen:
                continue
            seen.add(ip)
            devices.append(LanDevice(
                ip=ip, mac=mac, kind=kind.lower(),
                vendor=cls._vendor_for(mac),
            ))
        devices.sort(key=lambda d: tuple(int(x) for x in d.ip.split(".")))
        return devices

    def _run(self) -> str | None:
        try:
            proc = subprocess.run(
                ["arp", "-a"], capture_output=True, text=True,
                timeout=15, creationflags=_NO_WINDOW,
            )
            return proc.stdout if proc.returncode == 0 else None
        except (OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("arp failed: %s", exc)
            return None
