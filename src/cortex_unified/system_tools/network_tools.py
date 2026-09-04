"""Network diagnostic utilities: ping, traceroute, DNS, port & IP checks.

A focused toolbox of the classic utilities every power user reaches for, wired
to the OS's own ``ping``/``tracert`` and Python's ``socket`` so there are no
extra dependencies. These tools inherently reach the target you name (that's
their purpose) - the UI states that clearly - but nothing is sent anywhere you
don't ask for.

Scope choices for safety and honesty:
* The port check is a *connectivity diagnostic* (is host:port reachable) and a
  self-audit of THIS PC's own open ports, not a mass scanner of arbitrary
  hosts.
* IP classification is computed offline from the address itself; we do not call
  external reputation/geolocation services (that needs internet + licensed
  data), so we never claim a location or "reputation" we can't verify.
"""

from __future__ import annotations

import ipaddress
import logging
import sys
import re
import socket
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Any

from cortex_unified.core import proc as _proc

_LOG = logging.getLogger("cortex.system_tools.network_tools")
_IS_WINDOWS = sys.platform == "win32"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

# Common service ports for the self-audit / connectivity checks.
COMMON_PORTS = {
    20: "FTP-data", 21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
    53: "DNS", 80: "HTTP", 110: "POP3", 135: "RPC", 139: "NetBIOS",
    143: "IMAP", 443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
    1433: "MSSQL", 3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL",
    5900: "VNC", 6379: "Redis", 8080: "HTTP-alt", 8443: "HTTPS-alt",
}


@dataclass(slots=True)
class PingResult:
    """Pingresult.

    Manages PingResult operations and coordinates related state changes for the component.
    """
    host: str
    reachable: bool
    sent: int = 0
    received: int = 0
    loss_percent: float = 0.0
    min_ms: float | None = None
    avg_ms: float | None = None
    max_ms: float | None = None
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "host": self.host, "reachable": self.reachable, "sent": self.sent,
            "received": self.received, "loss_percent": self.loss_percent,
            "min_ms": self.min_ms, "avg_ms": self.avg_ms, "max_ms": self.max_ms,
            "error": self.error,
        }


@dataclass(slots=True)
class Hop:
    """Hop.

    Manages Hop operations and coordinates related state changes for the component.
    """
    number: int
    host: str
    times_ms: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        avg = round(sum(self.times_ms) / len(self.times_ms), 1) if self.times_ms else None
        return {"number": self.number, "host": self.host,
                "times_ms": self.times_ms, "avg_ms": avg}


class NetworkTools:
    """Networktools.

    Manages NetworkTools operations and coordinates related state changes for the component.
    """

    # -- ping ---------------------------------------------------------------

    def ping(
        self,
        host: str,
        count: int = 4,
        timeout_s: int = 4,
        cancel_event: threading.Event | None = None,
    ) -> PingResult:
        """Ping.

        Manages ping operations and coordinates related state changes for the component.

        Args:
            host (str): The host parameter.
            count (int): The count parameter.
            timeout_s (int): The timeout s parameter.
            cancel_event (threading.Event | None): Threading event or callable to check for cancellation.

        Returns:
            PingResult: Result of the operation.
        """
        host = (host or "").strip()
        if not host:
            return PingResult(host, False, error="No host given.")
        count = max(1, min(count, 10))
        if _IS_WINDOWS:
            args = ["ping", "-n", str(count), "-w", str(timeout_s * 1000), host]
        else:
            args = ["ping", "-c", str(count), "-W", str(timeout_s), host]
        out = self._run(
            args,
            timeout=count * timeout_s + 10,
            cancel_event=cancel_event,
        )
        if out is None:
            return PingResult(host, False, error="Could not run ping.")
        return self._parse_ping(host, out)

    @staticmethod
    def _parse_ping(host: str, out: str) -> PingResult:
        """_parse_ping.

        Manages parse ping operations and coordinates related state changes for the component.

        Args:
            host (str): The host parameter.
            out (str): The out parameter.

        Returns:
            PingResult: Result of the operation.
        """
        res = PingResult(host, False)
        # Packet stats (Windows: "Sent = 4, Received = 4, Lost = 0 (0% loss)";
        # *nix: "4 packets transmitted, 4 received, 0% packet loss").
        m = re.search(r"Sent\s*=\s*(\d+),\s*Received\s*=\s*(\d+),\s*Lost\s*=\s*(\d+)", out)
        if m:
            res.sent, res.received = int(m.group(1)), int(m.group(2))
        else:
            m = re.search(r"(\d+) packets transmitted,\s*(\d+)\s*(?:packets\s*)?received", out)
            if m:
                res.sent, res.received = int(m.group(1)), int(m.group(2))
        lm = re.search(r"\(([\d.]+)%\s*(?:packet\s*)?loss\)?", out)
        if lm:
            res.loss_percent = float(lm.group(1))
        elif res.sent:
            res.loss_percent = round(100.0 * (res.sent - res.received) / res.sent, 1)
        # Timings (Windows: "Minimum = 11ms, Maximum = 14ms, Average = 12ms";
        # *nix: "rtt min/avg/max/mdev = 11.1/12.2/14.0/1.0 ms").
        wm = re.search(r"Minimum\s*=\s*(\d+)ms,\s*Maximum\s*=\s*(\d+)ms,\s*Average\s*=\s*(\d+)ms", out)
        if wm:
            res.min_ms, res.max_ms, res.avg_ms = float(wm.group(1)), float(wm.group(2)), float(wm.group(3))
        else:
            nm = re.search(r"=\s*([\d.]+)/([\d.]+)/([\d.]+)/[\d.]+\s*ms", out)
            if nm:
                res.min_ms, res.avg_ms, res.max_ms = float(nm.group(1)), float(nm.group(2)), float(nm.group(3))
        res.reachable = res.received > 0
        return res

    # -- traceroute ---------------------------------------------------------

    def traceroute(self, host: str, max_hops: int = 30) -> list[Hop]:
        """Traceroute.

        Manages traceroute operations and coordinates related state changes for the component.

        Args:
            host (str): The host parameter.
            max_hops (int): The max hops parameter.

        Returns:
            list[Hop]: List of processed items or identifiers.
        """
        host = (host or "").strip()
        if not host:
            return []
        max_hops = max(1, min(max_hops, 40))
        if _IS_WINDOWS:
            args = ["tracert", "-d", "-h", str(max_hops), "-w", "1500", host]
        else:
            args = ["traceroute", "-n", "-m", str(max_hops), host]
        out = self._run(args, timeout=max_hops * 3 + 20)
        return self._parse_traceroute(out) if out else []

    @staticmethod
    def _parse_traceroute(out: str) -> list[Hop]:
        """_parse_traceroute.

        Manages parse traceroute operations and coordinates related state changes for the component.

        Args:
            out (str): The out parameter.

        Returns:
            list[Hop]: List of processed items or identifiers.
        """
        hops: list[Hop] = []
        for line in out.splitlines():
            line = line.strip()
            m = re.match(r"^(\d+)\s+(.*)$", line)
            if not m:
                continue
            num = int(m.group(1))
            rest = m.group(2)
            times = [float(t) for t in re.findall(r"([\d.]+)\s*ms", rest)]
            # Last token that looks like an IP/host.
            hosts = re.findall(r"(\d{1,3}(?:\.\d{1,3}){3}|[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})", rest)
            hostname = hosts[-1] if hosts else ("*" if "*" in rest else "")
            hops.append(Hop(number=num, host=hostname, times_ms=times))
        return hops

    # -- DNS ----------------------------------------------------------------

    @staticmethod
    def dns_lookup(host: str) -> list[str]:
        """Dns lookup.

        Manages dns lookup operations and coordinates related state changes for the component.

        Args:
            host (str): The host parameter.

        Returns:
            list[str]: List of processed items or identifiers.
        """
        host = (host or "").strip()
        if not host:
            return []
        try:
            infos = socket.getaddrinfo(host, None)
            return sorted({info[4][0] for info in infos})
        except (socket.gaierror, OSError):
            return []

    @staticmethod
    def reverse_dns(ip: str) -> str:
        """Reverse dns.

        Manages reverse dns operations and coordinates related state changes for the component.

        Args:
            ip (str): The ip parameter.

        Returns:
            str: Formatted string or path.
        """
        ip = (ip or "").strip()
        try:
            return socket.gethostbyaddr(ip)[0]
        except (socket.herror, socket.gaierror, OSError):
            return ""

    # -- ports --------------------------------------------------------------

    @staticmethod
    def check_port(host: str, port: int, timeout: float = 1.0) -> bool:
        """True if a TCP connection to host:port succeeds (reachability).

        Manages check port operations and coordinates related state changes for the component.

        Args:
            host (str): The host parameter.
            port (int): The port parameter.
            timeout (float): The timeout parameter.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        try:
            with socket.create_connection((host, int(port)), timeout=timeout):
                return True
        except (OSError, ValueError, OverflowError):
            return False

    def scan_common_ports(self, host: str, timeout: float = 0.6) -> dict[int, bool]:
        """Check the COMMON_PORTS on *host* (self-audit when host is this PC).

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            host (str): The host parameter.
            timeout (float): The timeout parameter.

        Returns:
            dict[int, bool]: Dictionary mapping identifiers to status or values.
        """
        host = (host or "").strip()
        results: dict[int, bool] = {}
        if not host:
            return results
        for port in COMMON_PORTS:
            results[port] = self.check_port(host, port, timeout)
        return results

    # -- IP classification (offline) ---------------------------------------

    @staticmethod
    def ip_info(address: str) -> dict[str, Any]:
        """Classify an IP entirely offline - no external lookups, no guesses.

        Manages ip info operations and coordinates related state changes for the component.

        Args:
            address (str): The address parameter.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        address = (address or "").strip()
        info: dict[str, Any] = {"address": address, "valid": False}
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return info
        info.update({
            "valid": True,
            "version": ip.version,
            "private": ip.is_private,
            "loopback": ip.is_loopback,
            "link_local": ip.is_link_local,
            "multicast": ip.is_multicast,
            "reserved": ip.is_reserved,
            "global": ip.is_global,
            "category": NetworkTools._category(ip),
        })
        return info

    @staticmethod
    def _category(ip) -> str:
        """Category.

        Manages category operations and coordinates related state changes for the component.

        Args:
            ip: The ip parameter.

        Returns:
            str: Formatted string or path.
        """
        if ip.is_loopback:
            return "Loopback (this machine)"
        if ip.is_private:
            return "Private / LAN"
        if ip.is_link_local:
            return "Link-local"
        if ip.is_multicast:
            return "Multicast"
        if ip.is_reserved:
            return "Reserved"
        if ip.is_global:
            return "Public (internet)"
        return "Unspecified"

    # -- helper -------------------------------------------------------------

    def _run(
        self,
        args: list[str],
        timeout: int = 30,
        cancel_event: threading.Event | None = None,
    ) -> str | None:
        """Run.

        Manages run operations and coordinates related state changes for the component.

        Args:
            args (list[str]): The args parameter.
            timeout (int): The timeout parameter.
            cancel_event (threading.Event | None): Threading event or callable to check for cancellation.

        Returns:
            str | None: Formatted string or path.
        """
        try:
            result = _proc.run(
                args,
                text=True,
                timeout=timeout,
                creationflags=_NO_WINDOW,
                cancel_event=cancel_event,
            )
            return result.stdout or result.stderr or ""
        except (
            _proc.ProcessCancelled,
            OSError,
            subprocess.SubprocessError,
        ) as exc:
            _LOG.debug(
                "network tool failed (%s): %s",
                args[0] if args else "?",
                exc,
            )
            return None
