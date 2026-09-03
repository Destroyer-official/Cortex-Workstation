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
import sys
import re
import subprocess
from dataclasses import dataclass
from typing import Any

from cortex_unified.core import proc as _proc

_LOG = logging.getLogger("cortex.system_tools.lan_scanner")
_IS_WINDOWS = sys.platform == "win32"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

from cortex_unified.system_tools import oui as _oui

_ARP_RE = re.compile(
    r"(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-fA-F]{2}(?:[-:][0-9a-fA-F]{2}){5})\s+(\w+)"
)


@dataclass(slots=True)
class LanDevice:
    """Lan Device data container."""
    ip: str
    mac: str
    kind: str          # dynamic / static
    vendor: str = ""

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {"ip": self.ip, "mac": self.mac, "kind": self.kind, "vendor": self.vendor}


class LanScanner:
    """Enumerate LAN devices from the OS ARP cache (read-only)."""

    def scan(self) -> list[LanDevice]:
        """Scan."""
        out = self._run()
        return self._parse(out)

    @staticmethod
    def _vendor_for(mac: str) -> str:
        """Vendor from the authoritative IEEE registry (empty when unknown).

        Previously this used a small hand-written table, which turned out to be
        wrong for 13% of its entries - it reported ``d8:eb:97`` as TP-Link when
        IEEE assigns it to TRENDnet. Vendor data now comes only from the IEEE
        registry via :mod:`cortex_unified.system_tools.oui`.
        """
        return _oui.shorten(_oui.lookup(mac))

    @classmethod
    def _parse(cls, out: str | None) -> list[LanDevice]:
        """_parse."""
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
        """_parse."""
        """_parse."""

    def _run(self) -> str | None:
        """_run."""
        try:
            proc = _proc.run(
                ["arp", "-a"], text=True, timeout=15, creationflags=_NO_WINDOW,
            )
            return proc.stdout if proc.returncode == 0 else None
        except (_proc.ProcessCancelled, OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("arp failed: %s", exc)
            return None
        """_run."""
        """_run."""
