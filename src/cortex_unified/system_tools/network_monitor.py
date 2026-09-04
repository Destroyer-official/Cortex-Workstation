"""Network connection monitor - see what's talking to your machine and out.

Lists active TCP/UDP connections with the owning process, protocol, local and
remote address:port, and connection state. This is a defensive, read-only tool:
it helps a user notice things like an unexpected process making an outbound
connection, or a service listening on all network interfaces (a remote-attack
surface). It never blocks or kills connections - that's the OS firewall's job -
but it points you at what to investigate.

Interpreting the flags we add:
* ``listening_public`` - the socket listens on 0.0.0.0 / :: (every interface),
  so it's reachable from other machines, not just localhost. Worth checking the
  owning program is one you trust to be network-exposed.
* ``remote_external`` - an ESTABLISHED connection to an address that isn't
  loopback or a private LAN range, i.e. out to the internet.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from dataclasses import dataclass
from typing import Any

_LOG = logging.getLogger("cortex.system_tools.network_monitor")

# psutil socket kinds -> friendly protocol label.
_PROTO = {
    (socket.AF_INET, socket.SOCK_STREAM): "TCP",
    (socket.AF_INET6, socket.SOCK_STREAM): "TCP6",
    (socket.AF_INET, socket.SOCK_DGRAM): "UDP",
    (socket.AF_INET6, socket.SOCK_DGRAM): "UDP6",
}

# Well-known ports -> service name, so users recognize what a port is for.
_SERVICES = {
    20: "FTP-data", 21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
    53: "DNS", 67: "DHCP", 68: "DHCP", 80: "HTTP", 110: "POP3",
    123: "NTP", 135: "RPC", 137: "NetBIOS", 138: "NetBIOS", 139: "NetBIOS",
    143: "IMAP", 161: "SNMP", 389: "LDAP", 443: "HTTPS", 445: "SMB",
    465: "SMTPS", 587: "SMTP", 993: "IMAPS", 995: "POP3S",
    1433: "MSSQL", 1521: "Oracle", 3306: "MySQL", 3389: "RDP",
    5432: "PostgreSQL", 5900: "VNC", 6379: "Redis", 8080: "HTTP-alt",
    8443: "HTTPS-alt", 27017: "MongoDB",
}


@dataclass(slots=True)
class Connection:
    """Connection.

    Manages Connection operations and coordinates related state changes for the component.
    """
    protocol: str
    local_addr: str
    local_port: int
    remote_addr: str
    remote_port: int
    status: str
    pid: int | None
    process: str
    service: str = ""
    process_exe: str = ""
    process_desc: str = ""

    @property
    def listening_public(self) -> bool:
        """Listening public.

        Manages listening public operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return (self.status == "LISTEN"
                and self.local_addr in ("0.0.0.0", "::"))

    @property
    def remote_external(self) -> bool:
        """Remote external.

        Manages remote external operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        if self.status != "ESTABLISHED" or not self.remote_addr:
            return False
        return not _is_private(self.remote_addr)

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "protocol": self.protocol,
            "local": f"{self.local_addr}:{self.local_port}" if self.local_port else self.local_addr,
            "remote": (f"{self.remote_addr}:{self.remote_port}"
                       if self.remote_addr else ""),
            "status": self.status,
            "pid": self.pid,
            "process": self.process,
            "service": self.service,
            "process_exe": self.process_exe,
            "process_desc": self.process_desc,
            "listening_public": self.listening_public,
            "remote_external": self.remote_external,
        }


def _is_private(addr: str) -> bool:
    """_is_private.

    Manages is private operations and coordinates related state changes for the component.

    Args:
        addr (str): The addr parameter.

    Returns:
        bool: True if the operation succeeded, False otherwise.
    """
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return True  # can't classify -> don't flag as external
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast


class NetworkMonitor:
    """Networkmonitor.

    Manages NetworkMonitor operations and coordinates related state changes for the component.
    """

    def connections(self) -> list[Connection]:
        """Connections.

        Manages connections operations and coordinates related state changes for the component.

        Returns:
            list[Connection]: List of processed items or identifiers.
        """
        try:
            import psutil
        except ImportError:
            return []

        meta: dict[int, tuple[str, str, str]] = {}   # pid -> (name, exe, desc)
        conns: list[Connection] = []
        try:
            raw = psutil.net_connections(kind="inet")
        except (psutil.AccessDenied, PermissionError):
            _LOG.debug("net_connections denied; run as Administrator for full view")
            return []
        except Exception as exc:  # noqa: BLE001
            _LOG.debug("net_connections failed: %s", exc)
            return []

        for c in raw:
            proto = _PROTO.get((c.family, c.type), "?")
            laddr = getattr(c.laddr, "ip", "") if c.laddr else ""
            lport = getattr(c.laddr, "port", 0) if c.laddr else 0
            raddr = getattr(c.raddr, "ip", "") if c.raddr else ""
            rport = getattr(c.raddr, "port", 0) if c.raddr else 0
            pid = c.pid
            if pid is not None and pid not in meta:
                meta[pid] = self._meta_for(psutil, pid)
            name, exe, desc = meta.get(pid, ("System", "", "")) if pid is not None \
                else ("System", "", "")
            service = _SERVICES.get(lport) or _SERVICES.get(rport) or ""
            conns.append(Connection(
                protocol=proto,
                local_addr=laddr, local_port=lport,
                remote_addr=raddr, remote_port=rport,
                status=c.status or "",
                pid=pid,
                process=name,
                service=service,
                process_exe=exe,
                process_desc=desc,
            ))
        # Most interesting first: external established, then public listeners.
        conns.sort(key=lambda x: (not x.remote_external, not x.listening_public,
                                  x.process.lower()))
        return conns

    @staticmethod
    def _meta_for(psutil, pid: int) -> tuple[str, str, str]:
        """Return (name, exe_path, friendly_description) for a PID.

        Manages meta for operations and coordinates related state changes for the component.

        Args:
            psutil: The psutil parameter.
            pid (int): The pid parameter.

        Returns:
            tuple[str, str, str]: Formatted string or path.
        """
        try:
            proc = psutil.Process(pid)
            with proc.oneshot():
                name = proc.name()
                try:
                    exe = proc.exe()
                except (psutil.AccessDenied, Exception):  # noqa: BLE001
                    exe = ""
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "?", "", ""
        try:
            from cortex_unified.system_tools.process_meta import describe
            desc = describe(name, exe)
        except Exception:  # noqa: BLE001
            desc = ""
        return name, exe, desc

    @staticmethod
    def summarize(conns: list[Connection]) -> dict[str, int]:
        """Summarize.

        Manages summarize operations and coordinates related state changes for the component.

        Args:
            conns (list[Connection]): The conns parameter.

        Returns:
            dict[str, int]: Dictionary mapping identifiers to status or values.
        """
        return {
            "total": len(conns),
            "established": sum(1 for c in conns if c.status == "ESTABLISHED"),
            "listening": sum(1 for c in conns if c.status == "LISTEN"),
            "public_listeners": sum(1 for c in conns if c.listening_public),
            "external": sum(1 for c in conns if c.remote_external),
        }
