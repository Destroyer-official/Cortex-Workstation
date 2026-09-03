"""Deep LAN device discovery - find everything actually on your network.

Why the old ARP-only scan missed devices
----------------------------------------
``arp -a`` prints the OS **neighbour cache**, which only holds entries for
hosts this PC has exchanged unicast traffic with recently (entries also age
out in minutes). Nothing proactively fills it in for the rest of the subnet.
So a sleeping phone, a Google TV you have never opened a socket to, or an
ESP32 quietly running its own firmware are all simply absent - not because
they are hidden, but because the cache was never the right place to look.

How this module finds them instead
----------------------------------
No single technique finds every device, so all of these run and their results
are merged, with each device recording *which* methods saw it:

* **Forced ARP resolution** (the workhorse). Sending any packet to a LAN IP
  makes the OS ARP for it first, and a device must answer ARP at the link
  layer to use the network at all - even when it silently drops ICMP and every
  TCP/UDP port, which phones, printers and IoT gear routinely do. We poke
  every address in the subnet with a cheap UDP datagram, then re-read the
  neighbour cache. This is the same reason ``nmap`` prefers ARP for local
  targets.
* **Neighbour cache read**, including IPv6 via ``Get-NetNeighbor`` on Windows.
* **mDNS / DNS-SD** (224.0.0.251:5353) - the richest source of *names*.
  Chromecast/Google TV, AirPlay, ESPHome/Arduino boards, printers and NAS
  boxes all advertise here, so this is what turns "192.168.1.47" into
  "living-room-tv".
* **SSDP / UPnP** (239.255.255.250:1900) - smart TVs, streamers, routers,
  consoles.
* **WS-Discovery** (239.255.255.250:3702) - Windows PCs and network printers.
* **NetBIOS name service** (UDP 137) - names for Windows and Samba hosts.
* **Reverse DNS** - names handed out by the router's resolver.

Honesty and safety
------------------
* Unlike the old passive scan, this **actively sends probes**. They go only to
  the private subnets of this PC's own interfaces - the module refuses to probe
  anything else, and never touches the internet.
* Every device says which methods observed it, so "we think this exists"
  is always backed by evidence rather than asserted.
* Two things genuinely cannot be worked around, and are reported rather than
  papered over: Wi-Fi **client isolation** (the access point refuses to forward
  traffic between clients, making peers unreachable from your PC by design),
  and **MAC randomization** (a phone deliberately hiding its identity). Both
  are surfaced as findings so the user knows the limit is the network, not the
  tool.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import sys
import socket
import struct
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from cortex_unified.core import proc as _proc
from cortex_unified.system_tools import oui

_LOG = logging.getLogger("cortex.system_tools.network_discovery")
_IS_WINDOWS = sys.platform == "win32"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

ProgressFn = Callable[[str], None]

#: Largest subnet we will sweep host-by-host. A /22 is 1022 hosts, which is
#: already generous for a home or small office; anything bigger is almost
#: certainly a misconfiguration and sweeping it would take minutes.
MAX_SWEEP_HOSTS = 1024

#: UDP port used to force ARP resolution. Port 9 is "discard"; we do not care
#: whether anything is listening - the ARP exchange that *precedes* the
#: datagram is the actual probe, so a closed port works just as well.
_ARP_POKE_PORT = 9

# -- multicast discovery endpoints ----------------------------------------
_MDNS_ADDR, _MDNS_PORT = "224.0.0.251", 5353
_SSDP_ADDR, _SSDP_PORT = "239.255.255.250", 1900
_WSD_ADDR, _WSD_PORT = "239.255.255.250", 3702
_NBNS_PORT = 137

#: Service types worth asking mDNS about by name. The meta-query
#: ``_services._dns-sd._udp.local`` enumerates types generically, but many
#: devices answer a direct question far more reliably, and these cover the
#: hardware people actually want identified.
_MDNS_SERVICES = (
    "_services._dns-sd._udp.local",
    "_googlecast._tcp.local",      # Chromecast / Google TV / Nest Hub
    "_androidtvremote2._tcp.local",  # Android TV / Google TV
    "_adb-tls-connect._tcp.local",   # Android wireless debugging endpoint
    "_adb-tls-pairing._tcp.local",   # Android wireless-debug pairing
    "_airplay._tcp.local",         # Apple TV, AirPlay speakers, some TVs
    "_raop._tcp.local",            # AirPlay audio
    "_spotify-connect._tcp.local",
    "_esphomelib._tcp.local",      # ESPHome (very common on ESP32)
    "_arduino._tcp.local",         # Arduino/ESP OTA
    "_http._tcp.local",            # generic web UI (most IoT boards)
    "_printer._tcp.local",
    "_ipp._tcp.local",
    "_ipps._tcp.local",
    "_smb._tcp.local",
    "_workstation._tcp.local",     # Linux/avahi hosts
    "_device-info._tcp.local",
    "_homekit._tcp.local",
    "_hap._tcp.local",             # HomeKit accessories
    "_miio._udp.local",            # Xiaomi devices
    "_amzn-wplay._tcp.local",      # Fire TV
    "_sonos._tcp.local",
)

#: Small, targeted TCP probe set used only to classify a device we already
#: know exists. Not a port scan of the network: it runs against discovered
#: hosts to answer "what kind of thing is this?".
_FINGERPRINT_PORTS: dict[int, str] = {
    80: "web UI",
    443: "HTTPS",
    22: "SSH",
    445: "Windows file sharing",
    139: "NetBIOS",
    631: "IPP printing",
    9100: "raw printing",
    8009: "Chromecast",
    8008: "Chromecast web",
    5555: "Android debug bridge",
    1883: "MQTT",
    8123: "Home Assistant",
    62078: "iOS sync",
    32400: "Plex",
    548: "AFP (Apple)",
    3389: "Remote Desktop",
}


#: Keyword hints applied to the *authoritative* vendor/model text (from the
#: IEEE registry or the device's own UPnP/mDNS/HTTP self-report) to suggest a
#: category. These are substring tests against a real reported name - not a MAC
#: prefix table - so a new product from a known maker is still categorised, and
#: an unknown maker simply falls through to "Unknown" instead of being guessed.
_VENDOR_KIND_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("espressif", "esp32", "esp8266"), "IoT board (ESP/Arduino)"),
    (("raspberry",), "Raspberry Pi"),
    (("hikvision", "dahua", "reolink", "wyze", "axis communications"), "Camera"),
    (("tuya", "shelly", "sonoff", "itead", "tp-link smart", "broadlink"),
     "Smart home device"),
    (("sonos", "bose", "denon", "yamaha", "harman", "marshall"), "Speaker / audio"),
    (("hewlett", "canon", "epson", "brother", "lexmark", "kyocera", "xerox"),
     "Printer"),
    (("apple",), "Apple device"),
    (("chromecast", "google"), "TV / streaming device"),
    (("roku", "amazon", "nvidia shield", "skyworth", "tcl", "hisense",
      "vestel", "philips tv"), "TV / streaming device"),
    (("samsung", "xiaomi", "redmi", "oneplus", "vivo mobile", "oppo",
      "realme", "huawei", "honor", "motorola", "nothing technology"),
     "Phone / tablet"),
    (("intel corporate", "micro-star", "asustek", "gigabyte", "dell",
      "lenovo", "hewlett packard", "wistron", "compal", "quanta", "clevo",
      "lcfc", "pegatron"), "Computer"),
    (("routerboard", "mikrotik", "ubiquiti", "netgear", "d-link", "zyxel",
      "trendnet", "aruba", "cisco", "juniper", "actiontec", "servercom",
      "arris", "technicolor", "sagemcom", "zte", "fiberhome"),
     "Network equipment"),
    (("vmware", "virtualbox", "pcs systemtechnik", "qemu", "parallels",
      "docker", "microsoft corporation"), "Virtual machine / host"),
    (("sony", "nintendo", "valve"), "Console / media device"),
)


@dataclass
class Device:
    """One discovered device, with the evidence that found it."""

    ip: str
    mac: str = ""
    hostname: str = ""
    vendor: str = ""
    #: Which discovery methods observed this device (arp, mdns, ssdp, ...).
    sources: set[str] = field(default_factory=set)
    #: Self-advertised protocol hints, e.g. {"_googlecast._tcp": "Living Room TV"}.
    services: dict[str, str] = field(default_factory=dict)
    open_ports: list[int] = field(default_factory=list)
    #: Structured results from the authorized private-LAN service scanner.
    service_observations: list[Any] = field(default_factory=list)
    #: Evidence-weighted OS/type identity; populated after active scanning.
    fingerprint: Any | None = None
    #: Neighbour-cache state (reachable/stale/permanent) when known.
    state: str = ""
    is_gateway: bool = False
    is_self: bool = False
    rtt_ms: float | None = None

    @property
    def randomized_mac(self) -> bool:
        """True when the device is using a privacy/randomized MAC."""
        return oui.is_randomized(self.mac)

    @property
    def label(self) -> str:
        """Best available human name for the device, never empty.

        Preference order is deliberately "what a person would recognise":
        the device's own friendly name, then its model, then a service
        instance name, then the hostname - because many devices (Chromecast
        in particular) use a raw UUID as their hostname, which is useless to
        read and worse than showing the model.
        """
        for key in ("friendly", "model"):
            value = self.services.get(key)
            if value:
                return value
        if self.hostname and not self._looks_like_uuid(self.hostname):
            return self.hostname
        for key, value in sorted(self.services.items()):
            if value and key not in ("upnp", "upnp-type", "wsd"):
                return value
        if self.hostname:
            return self.hostname
        if self.vendor and not self.vendor.startswith("private address"):
            return self.vendor
        if self.is_gateway:
            return "Router"
        return self.ip

    @staticmethod
    def _looks_like_uuid(text: str) -> bool:
        """True for machine-generated identifiers not worth showing as a name."""
        stripped = text.replace("-", "")
        return len(stripped) >= 24 and all(
            c in "0123456789abcdefABCDEF" for c in stripped)

    @property
    def kind(self) -> str:
        """Best-effort device category, derived only from observed evidence.

        Every rule below reads either a protocol the device actually answered,
        a port it actually accepted, or a name the device (or the IEEE registry)
        actually reported. Nothing is inferred from a hand-maintained list of
        MAC prefixes, so this cannot go stale or mislabel new hardware - it can
        only say less than it might, which is the safer failure.
        """
        if self.is_gateway:
            return "Router / gateway"
        if self.is_self:
            return "This PC"

        svc = " ".join(self.services)
        # Vendor + self-reported model text, searched together as one haystack.
        text = " ".join(filter(None, (
            self.vendor, self.hostname,
            self.services.get("model", ""), self.services.get("friendly", ""),
            self.services.get("upnp", ""),
        ))).lower()

        if "_googlecast" in svc or "_androidtvremote2" in svc or 8009 in self.open_ports:
            return "TV / streaming device"
        if "_amzn-wplay" in svc:
            return "Fire TV"
        if "_esphomelib" in svc or "_arduino" in svc:
            return "IoT board (ESP/Arduino)"
        if "_printer" in svc or "_ipp" in svc or 9100 in self.open_ports or 631 in self.open_ports:
            return "Printer"
        if "_raop" in svc or "_sonos" in svc or "_spotify-connect" in svc:
            return "Speaker / audio"
        if "_hap" in svc or "_homekit" in svc or "_miio" in svc:
            return "Smart home device"
        if 62078 in self.open_ports or "_airplay" in svc:
            return "Apple device"
        if 5555 in self.open_ports or "_adb" in svc:
            return "Android device"

        # Keyword match against the authoritative vendor/model string. These
        # are substring tests on real reported text, not MAC guesses.
        for needles, label in _VENDOR_KIND_HINTS:
            if any(needle in text for needle in needles):
                return label

        if 3389 in self.open_ports or 445 in self.open_ports:
            return "Computer"
        if self.randomized_mac:
            # Randomization is overwhelmingly a phone/laptop privacy feature.
            return "Phone / laptop (private address)"
        return "Unknown"

    @property
    def evidence(self) -> str:
        """Plain description of how we know this device is there."""
        names = {
            "neighbor": "answered ARP",
            "arp-sweep": "answered ARP when probed",
            "mdns": "advertises itself over mDNS",
            "ssdp": "advertises itself over UPnP",
            "wsd": "responds to WS-Discovery",
            "nbns": "answered a NetBIOS name query",
            "ping": "replied to ping",
            "ports": "accepted a TCP connection",
        }
        seen = [names[s] for s in sorted(self.sources) if s in names]
        return ", ".join(seen) if seen else "seen on the network"

    def merge(self, other: "Device") -> None:
        """Fold another observation of the same device into this one."""
        self.mac = self.mac or other.mac
        self.hostname = self.hostname or other.hostname
        self.vendor = self.vendor or other.vendor
        self.state = self.state or other.state
        self.sources |= other.sources
        for key, value in other.services.items():
            self.services.setdefault(key, value)
        for port in other.open_ports:
            if port not in self.open_ports:
                self.open_ports.append(port)
        observed = {
            (getattr(item, "ip", ""), getattr(item, "port", 0),
             getattr(item, "transport", ""), getattr(item, "name", ""))
            for item in self.service_observations
        }
        for item in other.service_observations:
            key = (getattr(item, "ip", ""), getattr(item, "port", 0),
                   getattr(item, "transport", ""), getattr(item, "name", ""))
            if key not in observed:
                self.service_observations.append(item)
                observed.add(key)
        self.fingerprint = self.fingerprint or other.fingerprint
        self.is_gateway = self.is_gateway or other.is_gateway
        self.is_self = self.is_self or other.is_self
        if self.rtt_ms is None:
            self.rtt_ms = other.rtt_ms

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "ip": self.ip,
            "mac": self.mac,
            "hostname": self.hostname,
            "label": self.label,
            "vendor": self.vendor,
            "kind": self.kind,
            "sources": sorted(self.sources),
            "evidence": self.evidence,
            "services": dict(self.services),
            "open_ports": sorted(self.open_ports),
            "service_observations": [
                item.to_dict() if hasattr(item, "to_dict") else str(item)
                for item in sorted(
                    self.service_observations,
                    key=lambda item: (getattr(item, "port", 0),
                                      getattr(item, "transport", ""),
                                      getattr(item, "name", "")),
                )
            ],
            "fingerprint": (
                self.fingerprint.to_dict()
                if self.fingerprint is not None and hasattr(self.fingerprint, "to_dict")
                else None
            ),
            "state": self.state,
            "is_gateway": self.is_gateway,
            "is_self": self.is_self,
            "randomized_mac": self.randomized_mac,
            "rtt_ms": self.rtt_ms,
        }


@dataclass(slots=True)
class Interface:
    """A local IPv4 interface worth scanning."""

    name: str
    ip: str
    netmask: str

    @property
    def network(self) -> ipaddress.IPv4Network | None:
        """Network."""
        try:
            return ipaddress.IPv4Network(f"{self.ip}/{self.netmask}", strict=False)
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError, ValueError):
            return None


@dataclass
class DiscoveryResult:
    """Everything a scan found, plus evidence-backed audit results."""

    devices: list[Device] = field(default_factory=list)
    networks: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    #: Caveats worth showing the user (isolation, randomized MACs, skipped nets).
    notes: list[str] = field(default_factory=list)
    cancelled: bool = False
    findings: list[Any] = field(default_factory=list)
    wan_status: Any | None = None
    inventory_changes: Any | None = None
    audit_profile: str = "targeted"

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "devices": [d.to_dict() for d in self.devices],
            "networks": self.networks,
            "duration_seconds": round(self.duration_seconds, 2),
            "notes": self.notes,
            "cancelled": self.cancelled,
            "device_count": len(self.devices),
            "audit_profile": self.audit_profile,
            "findings": [
                item.to_dict() if hasattr(item, "to_dict") else str(item)
                for item in self.findings
            ],
            "wan_status": (
                self.wan_status.to_dict()
                if self.wan_status is not None and hasattr(self.wan_status, "to_dict")
                else None
            ),
            "inventory_changes": (
                self.inventory_changes.to_dict()
                if self.inventory_changes is not None
                and hasattr(self.inventory_changes, "to_dict")
                else None
            ),
        }


class NetworkDiscovery:
    """Multi-protocol LAN discovery. Probes only this PC's own subnets."""

    def __init__(self, timeout_s: float = 4.0, workers: int = 128) -> None:
        """Initialize Network Discovery."""
        self.timeout_s = timeout_s
        self.workers = max(8, workers)
        self.logger = _LOG

    # -- public API ---------------------------------------------------------

    def scan(
        self,
        progress: ProgressFn | None = None,
        cancel_event: threading.Event | None = None,
        deep: bool = True,
        rounds: int = 2,
        audit_profile: str = "targeted",
        include_upnp_wan: bool = False,
        record_history: bool = False,
        requested_networks: Iterable[str] | None = None,
        custom_ports: Iterable[int] | None = None,
        nmap_modes: Iterable[str] | str | None = None,
        advisory_catalog_path: str | None = None,
    ) -> DiscoveryResult:
        """Discover devices, then run the selected defensive audit tier.

        ``deep`` controls host discovery (ARP sweep and name resolution).
        ``audit_profile`` controls service coverage: ``targeted`` checks a
        compact classifier set, ``advanced`` checks common services plus safe
        UDP probes, and ``deep`` checks every TCP port. ``requested_networks``
        can narrow scanning to subnets attached to this PC, never broaden it.
        ``custom_ports`` augments the selected profile. Optional Nmap modes are
        explicit and operate only on discovered in-scope hosts. UPnP WAN reads
        and local history are explicit caller choices.
        """
        started = time.perf_counter()
        result = DiscoveryResult(audit_profile=audit_profile)
        devices: dict[str, Device] = {}
        vulnerability_catalog = None
        if advisory_catalog_path:
            from cortex_unified.system_tools.vulnerability_catalog import (
                VulnerabilityCatalog,
            )
            vulnerability_catalog = VulnerabilityCatalog.load(
                advisory_catalog_path)

        # Use the cached IEEE registry if it has ever been downloaded, so
        # vendor names are authoritative without the user doing anything.
        oui.ensure_registry_loaded()

        def _say(msg: str) -> None:
            if progress is not None:
                progress(msg)
            """_say."""
            """_say."""

        def _cancelled() -> bool:
            return cancel_event is not None and cancel_event.is_set()
            """_cancelled."""
            """_cancelled."""

        interfaces = self.local_interfaces()
        if not interfaces:
            result.notes.append(
                "No active private network interface was found, so there is "
                "nothing to scan.")
            result.duration_seconds = time.perf_counter() - started
            return result

        from cortex_unified.system_tools.network_service_scanner import (
            normalize_custom_ports,
            parse_allowed_networks,
        )

        interface_networks = tuple(
            net for net in (iface.network for iface in interfaces)
            if net is not None)
        requested = parse_allowed_networks(requested_networks or ())
        extra_ports = normalize_custom_ports(custom_ports)
        if requested:
            outside = [
                net for net in requested
                if not any(net.subnet_of(local) for local in interface_networks)
            ]
            if outside:
                raise ValueError(
                    "custom scope must be contained by an active local "
                    f"interface: {', '.join(map(str, outside))}")
            selected_networks = requested
        else:
            selected_networks = interface_networks

        targets: list[ipaddress.IPv4Network] = []
        selected_host_count = 0
        for net in selected_networks:
            host_count = (
                net.num_addresses if net.prefixlen >= 31
                else net.num_addresses - 2)
            if (host_count > MAX_SWEEP_HOSTS
                    or selected_host_count + host_count > MAX_SWEEP_HOSTS):
                result.notes.append(
                    f"{net} covers {net.num_addresses:,} addresses - too "
                    "large for the bounded host sweep, so only passive and "
                    "multicast discovery ran for it.")
                continue
            targets.append(net)
            selected_host_count += host_count
            result.networks.append(str(net))

        self_ips = {i.ip for i in interfaces}
        gateways = self.default_gateways()

        # 0. This PC. It is never in its own ARP table (the OS has no reason to
        #    resolve its own address), so without this the machine running the
        #    scan is the one device conspicuously missing from the list.
        self._merge(devices, self._local_devices(interfaces))

        # 1. Whatever the OS already knows (free, instant).
        _say("Reading the network neighbour cache\u2026")
        self._merge(devices, self._read_neighbors())

        # 2. Force ARP resolution across the subnet - the step that actually
        #    finds silent devices. Two passes, because devices in Wi-Fi
        #    power-save (phones, battery sensors, ESP boards with modem sleep)
        #    routinely miss the first request and answer the second.
        if deep and targets and not _cancelled():
            hosts = [str(h) for net in targets for h in net.hosts()]
            total_rounds = max(1, rounds)
            # A broadcast ping first: some devices answer it and land in the
            # ARP table before we even start the unicast sweep.
            self._broadcast_ping(targets)
            for round_no in range(1, total_rounds + 1):
                if _cancelled():
                    break
                _say(f"Probing {len(hosts):,} addresses to force ARP replies "
                     f"(pass {round_no} of {total_rounds})\u2026")
                self._arp_sweep(hosts, cancel_event)
                if not _cancelled():
                    self._merge(devices, self._read_neighbors())

        # 3. Ask devices to introduce themselves (names + types).
        if not _cancelled():
            _say("Listening for mDNS / Bonjour announcements\u2026")
            self._merge(devices, self._discover_mdns(cancel_event))
        if not _cancelled():
            _say("Asking for UPnP / SSDP devices\u2026")
            self._merge(devices, self._discover_ssdp(cancel_event))
        if not _cancelled():
            _say("Asking for WS-Discovery devices\u2026")
            self._merge(devices, self._discover_wsd(cancel_event))

        # 3b. Re-read the neighbour cache once more. The multicast rounds above
        #     put real traffic on the wire, which often prompts a device that
        #     ignored the unicast sweep to speak up and land in the ARP table.
        if deep and not _cancelled():
            self._merge(devices, self._read_neighbors())

        # A manual scope narrows the inventory as well as the active probes;
        # multicast announcements from adjacent local subnets must not leak in.
        if requested:
            devices = {
                ip: device for ip, device in devices.items()
                if any(ipaddress.IPv4Address(ip) in net for net in targets)
            }

        # 4. Fill in names and classification for what we found.
        if not _cancelled():
            _say("Resolving names\u2026")
            self._resolve_names(devices, cancel_event)
        if deep and not _cancelled():
            _say("Auditing authorized private-LAN services\u2026")
            # Keep the legacy two-argument _fingerprint hook for compatibility;
            # the per-scan scope/profile is carried only for this synchronous call.
            self._audit_targets = tuple(targets)
            self._audit_profile = audit_profile
            self._audit_progress = progress
            self._audit_custom_ports = extra_ports
            self._audit_nmap_modes = nmap_modes
            self._fingerprint(devices, cancel_event)

        # 5. Annotate, fingerprint, audit and finish.
        from cortex_unified.system_tools.device_fingerprint import fingerprint_device
        from cortex_unified.system_tools.network_security_audit import audit_devices, audit_wan
        from cortex_unified.system_tools.wan_audit import WanAuditor

        for ip, device in devices.items():
            device.vendor = device.vendor or oui.describe_vendor(device.mac)
            device.is_gateway = ip in gateways
            device.is_self = ip in self_ips
            device.fingerprint = fingerprint_device(device)

        result.devices = sorted(
            devices.values(), key=lambda d: self._ip_sort_key(d.ip))
        result.cancelled = _cancelled()

        if not result.cancelled:
            _say("Reading local route and WAN gateway status\u2026")
            result.wan_status = WanAuditor(timeout=min(self.timeout_s, 4.0)).audit(
                gateway_ips=sorted(gateways),
                include_upnp=include_upnp_wan,
                progress=progress,
                cancel_event=cancel_event,
            )
            result.findings = audit_devices(
                result.devices, vulnerability_catalog=vulnerability_catalog)
            result.findings.extend(audit_wan(result.wan_status))
            result.findings.sort(
                key=lambda item: (
                    {"critical": 0, "high": 1, "medium": 2,
                     "low": 3, "info": 4}.get(item.severity, 5),
                    item.device_ip, item.code,
                )
            )

        if record_history and not result.cancelled:
            try:
                from cortex_unified.system_tools.network_inventory import NetworkInventory
                result.inventory_changes = NetworkInventory().update(
                    result.devices, result.findings)
            except (OSError, ValueError, RuntimeError) as exc:
                result.notes.append(f"Network history could not be updated: {exc}")

        result.duration_seconds = time.perf_counter() - started
        result.notes.extend(self._build_notes(result.devices, targets, gateways))
        return result

    # -- interface / route discovery ---------------------------------------

    @staticmethod
    def local_interfaces() -> list[Interface]:
        """Return this PC's up, private IPv4 interfaces."""
        out: list[Interface] = []
        try:
            import psutil
        except ImportError:
            return out
        try:
            stats = psutil.net_if_stats()
            for name, addrs in psutil.net_if_addrs().items():
                info = stats.get(name)
                if info is not None and not info.isup:
                    continue
                for addr in addrs:
                    if addr.family != socket.AF_INET or not addr.address:
                        continue
                    try:
                        ip = ipaddress.IPv4Address(addr.address)
                    except ipaddress.AddressValueError:
                        continue
                    # Only private LANs: never probe public address space.
                    if ip.is_loopback or ip.is_link_local or not ip.is_private:
                        continue
                    out.append(Interface(name, addr.address,
                                         addr.netmask or "255.255.255.0"))
        except Exception as exc:  # noqa: BLE001 - enumeration must never crash a scan
            _LOG.debug("interface enumeration failed: %s", exc)
        return out

    @staticmethod
    def _local_devices(interfaces: list[Interface]) -> list[Device]:
        """Represent this PC itself, one entry per active interface."""
        hostname = ""
        try:
            hostname = socket.gethostname().split(".")[0]
        except OSError:
            pass

        macs: dict[str, str] = {}
        try:
            import psutil
            for name, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    # AF_LINK is the MAC family; its value differs per platform.
                    if getattr(addr, "family", None) == getattr(psutil, "AF_LINK", None):
                        normalized = oui.normalize(addr.address or "")
                        if normalized:
                            macs[name] = normalized
        except Exception as exc:  # noqa: BLE001
            _LOG.debug("local MAC lookup failed: %s", exc)

        return [
            Device(
                ip=iface.ip,
                mac=macs.get(iface.name, ""),
                hostname=hostname,
                sources={"neighbor"},
                state="local",
                is_self=True,
            )
            for iface in interfaces
        ]

    def default_gateways(self) -> set[str]:
        """Return default-gateway IPs (used to label the router)."""
        gateways: set[str] = set()
        if _IS_WINDOWS:
            out = self._run_ps(
                "Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction "
                "SilentlyContinue | Select-Object -ExpandProperty NextHop")
            for line in (out or "").splitlines():
                candidate = line.strip()
                if self._is_ipv4(candidate) and candidate != "0.0.0.0":
                    gateways.add(candidate)
        else:
            try:
                res = _proc.run(["ip", "route", "show", "default"],
                                text=True, timeout=10)
                for line in (res.stdout or "").splitlines():
                    parts = line.split()
                    if "via" in parts:
                        candidate = parts[parts.index("via") + 1]
                        if self._is_ipv4(candidate):
                            gateways.add(candidate)
            except Exception as exc:  # noqa: BLE001
                _LOG.debug("gateway lookup failed: %s", exc)
        return gateways

    # -- layer 2: neighbour cache + ARP sweep ------------------------------

    def _read_neighbors(self) -> list[Device]:
        """Read the OS neighbour cache (ARP for IPv4, NDP for IPv6)."""
        if _IS_WINDOWS:
            devices = self._read_neighbors_windows()
            if devices:
                return devices
        return self._read_arp_command()

    def _read_neighbors_windows(self) -> list[Device]:
        """Use ``Get-NetNeighbor``, which exposes reachability state too."""
        # Only states that imply a real answered ARP exchange. Incomplete and
        # Unreachable entries exist for every address we probed without reply,
        # and carry a 00-00-00-00-00-00 address - including them would invent a
        # device for every unused IP in the subnet.
        out = self._run_ps(
            "Get-NetNeighbor -AddressFamily IPv4 -ErrorAction SilentlyContinue "
            "| Where-Object { $_.LinkLayerAddress -and "
            "$_.LinkLayerAddress -ne '00-00-00-00-00-00' -and "
            "$_.State -in 'Reachable','Stale','Permanent','Delay','Probe' } "
            "| ForEach-Object { $_.IPAddress + '|' + $_.LinkLayerAddress + "
            "'|' + $_.State }")
        devices: list[Device] = []
        for line in (out or "").splitlines():
            parts = line.strip().split("|")
            if len(parts) != 3:
                continue
            ip, mac, state = parts[0].strip(), oui.normalize(parts[1]), parts[2].strip()
            if not self._usable_host(ip, mac):
                continue
            devices.append(Device(ip=ip, mac=mac, state=state.lower(),
                                  sources={"neighbor"}))
        return devices

    def _read_arp_command(self) -> list[Device]:
        """Fallback: parse ``arp -a`` (works on every platform)."""
        try:
            res = _proc.run(["arp", "-a"], text=True, timeout=20,
                            creationflags=_NO_WINDOW)
            text = res.stdout or ""
        except Exception as exc:  # noqa: BLE001
            _LOG.debug("arp -a failed: %s", exc)
            return []

        devices: list[Device] = []
        pattern = re.compile(
            r"(\d{1,3}(?:\.\d{1,3}){3}).*?"
            r"([0-9a-fA-F]{2}(?:[-:][0-9a-fA-F]{2}){5})")
        for line in text.splitlines():
            match = pattern.search(line)
            if not match:
                continue
            ip, mac = match.group(1), oui.normalize(match.group(2))
            if not self._usable_host(ip, mac):
                continue
            state = "static" if "static" in line.lower() else "dynamic"
            devices.append(Device(ip=ip, mac=mac, state=state,
                                  sources={"neighbor"}))
        return devices

    @staticmethod
    def _broadcast_ping(targets: list[ipaddress.IPv4Network]) -> None:
        """Send a UDP datagram to each subnet's broadcast address.

        Cheap and occasionally productive: some stacks answer broadcast traffic
        and end up in the ARP table before the unicast sweep begins. Failure is
        completely uninteresting, so it is ignored.
        """
        for net in targets:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.settimeout(0.5)
                    sock.sendto(b"\x00", (str(net.broadcast_address), _ARP_POKE_PORT))
            except OSError:
                continue

    def _arp_sweep(self, hosts: Iterable[str],
                   cancel_event: threading.Event | None,
                   settle_s: float = 2.0) -> None:
        """Send one cheap UDP datagram per host to force ARP resolution.

        We deliberately ignore whether anything answers on the port: the point
        is that the OS must resolve the MAC *before* it can send the datagram,
        and a device has to answer ARP to function on the network at all. This
        is why it finds hosts that drop every ping and every port probe.

        Concurrency is capped well below the thread pool's usual width because
        blasting a whole subnet's worth of simultaneous ARP requests makes the
        OS drop queued resolutions - which shows up as a device "missing" even
        though it is right there. Slower and complete beats fast and wrong.
        """
        payload = b"\x00"

        def _poke(ip: str) -> None:
            if cancel_event is not None and cancel_event.is_set():
                return
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)
                    sock.sendto(payload, (ip, _ARP_POKE_PORT))
            except OSError:
                pass  # unreachable/blocked is fine - the ARP attempt happened
            """_poke."""
            """_poke."""

        with ThreadPoolExecutor(max_workers=min(self.workers, 48)) as pool:
            list(pool.map(_poke, hosts))

        # Give the stack time to record the replies before we read the cache.
        deadline = time.monotonic() + settle_s
        while time.monotonic() < deadline:
            if cancel_event is not None and cancel_event.is_set():
                return
            time.sleep(0.1)

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _is_ipv4(value: str) -> bool:
        try:
            ipaddress.IPv4Address(value)
            return True
        except (ipaddress.AddressValueError, ValueError):
            return False
        """_is_ipv4."""
        """_is_ipv4."""

    @classmethod
    def _usable_host(cls, ip: str, mac: str) -> bool:
        """Filter out entries that are not a real, present device.

        The critical case is the all-zero MAC. After an ARP sweep, Windows
        keeps a neighbour entry for *every* address we probed; the ones that
        never answered sit in ``Incomplete``/``Unreachable`` with a
        ``00-00-00-00-00-00`` link-layer address. Treating those as devices
        would report an entire subnet of phantom hosts, so a zero MAC is proof
        of absence, not presence.
        """
        if not cls._is_ipv4(ip) or not mac:
            return False
        if mac in ("00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"):
            return False
        if oui.is_multicast(mac):
            return False
        try:
            addr = ipaddress.IPv4Address(ip)
        except (ipaddress.AddressValueError, ValueError):
            return False
        return not (addr.is_multicast or addr.is_unspecified or ip.endswith(".255"))

    @staticmethod
    def _ip_sort_key(ip: str) -> tuple:
        try:
            return (0,) + tuple(int(p) for p in ip.split("."))
        except (ValueError, AttributeError):
            return (1, ip)
        """_ip_sort_key."""
        """_ip_sort_key."""

    @staticmethod
    def _merge(into: dict[str, Device], found: Iterable[Device]) -> None:
        for device in found:
            existing = into.get(device.ip)
            if existing is None:
                into[device.ip] = device
            else:
                existing.merge(device)
        """_merge."""
        """_merge."""

    def _run_ps(self, script: str, timeout: int = 45) -> str | None:
        try:
            res = _proc.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                text=True, timeout=timeout, creationflags=_NO_WINDOW,
            )
            return res.stdout
        except (_proc.ProcessCancelled, OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("powershell failed: %s", exc)
            return None
        """_run_ps."""
        """_run_ps."""

    # -- mDNS / DNS-SD -----------------------------------------------------

    def _discover_mdns(self, cancel_event: threading.Event | None) -> list[Device]:
        """Query mDNS for common service types and collect names + addresses.

        Implemented directly on a UDP socket (no extra dependency): we build
        standard DNS queries, send them to the mDNS multicast group from every
        local interface, then parse every answer that arrives during the
        listen window. Devices answer with A records (address), PTR/SRV
        (service instance names) and TXT (model details), which together give
        us the friendly name that makes a device recognisable.
        """
        found: dict[str, Device] = {}
        queries = [self._build_dns_query(name) for name in _MDNS_SERVICES]

        for iface in self.local_interfaces():
            if cancel_event is not None and cancel_event.is_set():
                break
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # Bind to this interface so the query really leaves via it -
                # essential on a PC with Wi-Fi + Ethernet + virtual adapters.
                sock.bind((iface.ip, 0))
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                                socket.inet_aton(iface.ip))
                sock.settimeout(0.4)

                for query in queries:
                    try:
                        sock.sendto(query, (_MDNS_ADDR, _MDNS_PORT))
                    except OSError:
                        continue

                deadline = time.monotonic() + self.timeout_s
                while time.monotonic() < deadline:
                    if cancel_event is not None and cancel_event.is_set():
                        break
                    try:
                        data, addr = sock.recvfrom(9000)
                    except socket.timeout:
                        continue
                    except OSError:
                        break
                    self._absorb_mdns(found, data, addr[0])
            except OSError as exc:
                _LOG.debug("mDNS on %s failed: %s", iface.ip, exc)
            finally:
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass
        return list(found.values())

    def _absorb_mdns(self, found: dict[str, Device], data: bytes, src_ip: str) -> None:
        """Parse an mDNS response and record names/services for the sender."""
        try:
            records = self._parse_dns_records(data)
        except Exception as exc:  # noqa: BLE001 - malformed packets are expected
            _LOG.debug("mDNS parse failed from %s: %s", src_ip, exc)
            return

        device = found.get(src_ip) or Device(ip=src_ip, sources={"mdns"})
        device.sources.add("mdns")

        for name, rtype, value in records:
            if rtype == 1 and isinstance(value, str) and self._is_ipv4(value):
                # An A record tells us the advertised address, which can differ
                # from the packet source on multi-homed devices.
                target = found.get(value) or Device(ip=value, sources={"mdns"})
                target.sources.add("mdns")
                if name.endswith(".local") and not target.hostname:
                    target.hostname = name[: -len(".local")]
                found[value] = target
            elif rtype in (12, 33):  # PTR / SRV -> service instance names
                service, instance = self._split_service_instance(
                    value if isinstance(value, str) else name)
                if service:
                    device.services.setdefault(service, instance)
            elif rtype == 16 and isinstance(value, str) and value:
                # TXT records carry the good stuff: "fn=Living Room TV" is the
                # name the user themselves gave the device, and "md=" its model.
                for token in value.split(";"):
                    lowered = token.lower()
                    label = token.split("=", 1)[1].strip() if "=" in token else ""
                    if not label:
                        continue
                    if lowered.startswith("fn="):
                        device.services["friendly"] = label
                    elif lowered.startswith(("md=", "model=", "am=", "ty=")):
                        device.services.setdefault("model", label)

        # A hostname from the packet's own question/answer names is a good
        # fallback when no A record named it.
        if not device.hostname:
            for name, rtype, _ in records:
                if rtype == 1 and name.endswith(".local"):
                    device.hostname = name[: -len(".local")]
                    break
        found[src_ip] = device

    @staticmethod
    def _split_service_instance(value: str) -> tuple[str, str]:
        """Split ``Living Room._googlecast._tcp.local`` into (type, instance)."""
        if not value:
            return "", ""
        text = value[: -len(".local")] if value.endswith(".local") else value
        match = re.search(r"(_[^.]+\._(?:tcp|udp))$", text)
        if match:
            service = match.group(1)
            instance = text[: match.start()].rstrip(".")
            return service, instance
        return "", ""

    @staticmethod
    def _build_dns_query(name: str, qtype: int = 12) -> bytes:
        """Build a minimal DNS query packet (PTR by default) for *name*."""
        header = struct.pack(">HHHHHH", 0, 0, 1, 0, 0, 0)
        parts = b"".join(
            bytes([len(label)]) + label.encode("ascii", "ignore")
            for label in name.split(".") if label
        )
        return header + parts + b"\x00" + struct.pack(">HH", qtype, 1)

    @classmethod
    def _parse_dns_records(cls, data: bytes) -> list[tuple[str, int, Any]]:
        """Parse answer/authority/additional records out of a DNS message.

        Handles DNS name compression (the 0xC0 pointer form), which mDNS
        responders use heavily; without it most real packets are unreadable.
        """
        if len(data) < 12:
            return []
        qdcount, ancount, nscount, arcount = struct.unpack(">HHHH", data[4:12])
        offset = 12
        for _ in range(qdcount):
            _, offset = cls._read_name(data, offset)
            offset += 4  # qtype + qclass

        records: list[tuple[str, int, Any]] = []
        for _ in range(ancount + nscount + arcount):
            if offset >= len(data):
                break
            name, offset = cls._read_name(data, offset)
            if offset + 10 > len(data):
                break
            rtype, _rclass, _ttl, rdlength = struct.unpack(
                ">HHIH", data[offset:offset + 10])
            offset += 10
            rdata = data[offset:offset + rdlength]
            value: Any = None
            if rtype == 1 and rdlength == 4:                     # A
                value = socket.inet_ntoa(rdata)
            elif rtype in (12, 5):                               # PTR / CNAME
                value, _ = cls._read_name(data, offset)
            elif rtype == 33 and rdlength > 6:                   # SRV
                value, _ = cls._read_name(data, offset + 6)
            elif rtype == 16:                                    # TXT
                chunks, pos = [], 0
                while pos < len(rdata):
                    length = rdata[pos]
                    chunks.append(rdata[pos + 1:pos + 1 + length]
                                  .decode("utf-8", "replace"))
                    pos += 1 + length
                value = ";".join(chunks)
            records.append((name, rtype, value))
            offset += rdlength
        return records

    @staticmethod
    def _read_name(data: bytes, offset: int) -> tuple[str, int]:
        """Read a (possibly compressed) DNS name; returns (name, next_offset)."""
        labels: list[str] = []
        jumped = False
        original = offset
        hops = 0
        while offset < len(data):
            length = data[offset]
            if length == 0:
                offset += 1
                break
            if length & 0xC0 == 0xC0:                 # compression pointer
                if offset + 1 >= len(data):
                    break
                pointer = ((length & 0x3F) << 8) | data[offset + 1]
                if not jumped:
                    original = offset + 2
                    jumped = True
                offset = pointer
                hops += 1
                if hops > 20:                          # malformed/looping packet
                    break
                continue
            offset += 1
            labels.append(data[offset:offset + length].decode("utf-8", "replace"))
            offset += length
        return ".".join(labels), (original if jumped else offset)

    # -- SSDP / UPnP -------------------------------------------------------

    def _discover_ssdp(self, cancel_event: threading.Event | None) -> list[Device]:
        """Send an SSDP M-SEARCH and record every responder.

        Smart TVs, streaming sticks, consoles and routers answer this even when
        they ignore ping, and the ``SERVER``/``ST`` headers usually name the
        product directly.
        """
        found: dict[str, Device] = {}
        request = (
            "M-SEARCH * HTTP/1.1\r\n"
            f"HOST: {_SSDP_ADDR}:{_SSDP_PORT}\r\n"
            'MAN: "ssdp:discover"\r\n'
            "MX: 2\r\n"
            "ST: ssdp:all\r\n"
            "\r\n"
        ).encode("ascii")

        for iface in self.local_interfaces():
            if cancel_event is not None and cancel_event.is_set():
                break
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((iface.ip, 0))
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                sock.settimeout(0.4)
                sock.sendto(request, (_SSDP_ADDR, _SSDP_PORT))

                deadline = time.monotonic() + self.timeout_s
                while time.monotonic() < deadline:
                    if cancel_event is not None and cancel_event.is_set():
                        break
                    try:
                        data, addr = sock.recvfrom(4096)
                    except socket.timeout:
                        continue
                    except OSError:
                        break
                    ip = addr[0]
                    device = found.get(ip) or Device(ip=ip, sources={"ssdp"})
                    device.sources.add("ssdp")
                    headers = self._parse_http_headers(data)
                    server = headers.get("server", "")
                    if server:
                        device.services.setdefault("upnp", server[:120])
                    st = headers.get("st", "")
                    if st and "rootdevice" not in st:
                        device.services.setdefault("upnp-type", st[:80])
                    found[ip] = device
            except OSError as exc:
                _LOG.debug("SSDP on %s failed: %s", iface.ip, exc)
            finally:
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass
        return list(found.values())

    # -- WS-Discovery ------------------------------------------------------

    def _discover_wsd(self, cancel_event: threading.Event | None) -> list[Device]:
        """Send a WS-Discovery Probe - the way Windows itself finds PCs/printers."""
        found: dict[str, Device] = {}
        probe = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<soap:Envelope '
            'xmlns:soap="http://www.w3.org/2003/05/soap-envelope" '
            'xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing" '
            'xmlns:wsd="http://schemas.xmlsoap.org/ws/2005/04/discovery">'
            "<soap:Header>"
            "<wsa:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>"
            "<wsa:Action>"
            "http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe"
            "</wsa:Action>"
            f"<wsa:MessageID>urn:uuid:{self._pseudo_uuid()}</wsa:MessageID>"
            "</soap:Header>"
            "<soap:Body><wsd:Probe/></soap:Body>"
            "</soap:Envelope>"
        ).encode("utf-8")

        for iface in self.local_interfaces():
            if cancel_event is not None and cancel_event.is_set():
                break
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((iface.ip, 0))
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                sock.settimeout(0.4)
                sock.sendto(probe, (_WSD_ADDR, _WSD_PORT))

                deadline = time.monotonic() + min(self.timeout_s, 4.0)
                while time.monotonic() < deadline:
                    if cancel_event is not None and cancel_event.is_set():
                        break
                    try:
                        data, addr = sock.recvfrom(8192)
                    except socket.timeout:
                        continue
                    except OSError:
                        break
                    ip = addr[0]
                    device = found.get(ip) or Device(ip=ip, sources={"wsd"})
                    device.sources.add("wsd")
                    text = data.decode("utf-8", "replace")
                    if "PrintDeviceType" in text or "Print" in text:
                        device.services.setdefault("wsd", "printer")
                    elif "Computer" in text:
                        device.services.setdefault("wsd", "computer")
                    else:
                        device.services.setdefault("wsd", "device")
                    found[ip] = device
            except OSError as exc:
                _LOG.debug("WS-Discovery on %s failed: %s", iface.ip, exc)
            finally:
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass
        return list(found.values())

    @staticmethod
    def _pseudo_uuid() -> str:
        import uuid
        return str(uuid.uuid4())
        """_pseudo_uuid."""
        """_pseudo_uuid."""

    @staticmethod
    def _parse_http_headers(data: bytes) -> dict[str, str]:
        """Parse SSDP's HTTP-style headers into a lower-cased dict."""
        headers: dict[str, str] = {}
        for line in data.decode("utf-8", "replace").splitlines()[1:]:
            if ":" in line:
                key, _, value = line.partition(":")
                headers[key.strip().lower()] = value.strip()
        return headers

    # -- naming ------------------------------------------------------------

    def _resolve_names(self, devices: dict[str, Device],
                       cancel_event: threading.Event | None) -> None:
        """Fill in hostnames via reverse DNS and NetBIOS, in parallel."""
        pending = [d for d in devices.values() if not d.hostname]
        if not pending:
            return

        def _resolve(device: Device) -> None:
            if cancel_event is not None and cancel_event.is_set():
                return
            # Reverse DNS: names the router's resolver knows about.
            try:
                host = socket.gethostbyaddr(device.ip)[0]
                if host and not host.startswith(device.ip):
                    device.hostname = host.split(".")[0]
                    return
            except (OSError, socket.herror, socket.gaierror):
                pass
            # NetBIOS: still the best name source for Windows/Samba hosts.
            name = self._netbios_name(device.ip)
            if name:
                device.hostname = name
                device.sources.add("nbns")
            """_resolve."""
            """_resolve."""

        with ThreadPoolExecutor(max_workers=min(self.workers, 64)) as pool:
            list(pool.map(_resolve, pending))

    def _netbios_name(self, ip: str, timeout: float = 0.6) -> str:
        """Send a NetBIOS node-status query (UDP 137) and read the name."""
        # Node status request for the wildcard name "*".
        query = (
            struct.pack(">HHHHHH", 0x4E42, 0x0000, 1, 0, 0, 0)
            + b"\x20CKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x00"
            + struct.pack(">HH", 0x0021, 0x0001)
        )
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(timeout)
                sock.sendto(query, (ip, _NBNS_PORT))
                data, _ = sock.recvfrom(2048)
        except (OSError, socket.timeout):
            return ""
        # Names start after the header + question echo; each entry is 16 bytes
        # of padded name followed by 2 flag bytes.
        try:
            count_offset = 56
            if len(data) <= count_offset:
                return ""
            count = data[count_offset]
            pos = count_offset + 1
            for _ in range(count):
                if pos + 18 > len(data):
                    break
                raw = data[pos:pos + 15].decode("ascii", "ignore").strip()
                flags = data[pos + 16]
                pos += 18
                # Bit 0x80 marks a group (workgroup) name; we want unique names.
                if raw and not flags & 0x80:
                    return raw
        except (IndexError, UnicodeDecodeError):
            return ""
        return ""

    # -- classification ----------------------------------------------------

    def _fingerprint(self, devices: dict[str, Device],
                     cancel_event: threading.Event | None) -> None:
        """Enumerate services only on discovered, in-scope private hosts.

        The scanner revalidates every host against ``_audit_targets`` before a
        socket is opened. The attributes are set immediately before this
        synchronous call so the established two-argument test/mocking API stays
        compatible with older callers.
        """
        targets = tuple(getattr(self, "_audit_targets", ()))
        if not devices or not targets:
            return
        from cortex_unified.system_tools.network_service_scanner import (
            NetworkServiceScanner,
            ScanProfile,
        )

        try:
            profile = ScanProfile(str(getattr(
                self, "_audit_profile", "targeted")).lower())
        except ValueError:
            profile = ScanProfile.TARGETED
        scanner = NetworkServiceScanner(
            timeout=0.45 if profile is not ScanProfile.DEEP else 0.65,
            workers=min(self.workers, 64),
            rate_limit=180.0 if profile is not ScanProfile.DEEP else 240.0,
        )
        extra_ports = tuple(getattr(self, "_audit_custom_ports", ()))
        observations = scanner.scan(
            hosts=devices,
            allowed_networks=targets,
            profile=profile,
            progress=getattr(self, "_audit_progress", None),
            cancel_event=cancel_event,
            custom_ports=extra_ports,
        )
        nmap_modes = getattr(self, "_audit_nmap_modes", None)
        if nmap_modes and extra_ports and not (
                cancel_event is not None and cancel_event.is_set()):
            from cortex_unified.system_tools.nmap_adapter import NmapAdapter

            progress = getattr(self, "_audit_progress", None)
            if progress:
                progress("Running explicit optional Nmap expert audit...")
            nmap_observations = NmapAdapter().scan(
                targets=devices,
                allowed_networks=targets,
                ports=extra_ports,
                modes=nmap_modes,
                cancel_event=cancel_event,
            )
            observations.extend(nmap_observations)

        unique = {
            (item.ip, item.port, item.transport, item.name, item.source): item
            for item in observations
        }
        for observation in unique.values():
            device = devices.get(observation.ip)
            if device is None:
                continue
            device.service_observations.append(observation)
            if (observation.transport == "tcp"
                    and observation.state == "open"
                    and observation.port not in device.open_ports):
                device.open_ports.append(observation.port)
            device.sources.add("ports")

    # -- reporting ---------------------------------------------------------

    @staticmethod
    def _build_notes(devices: list[Device],
                     targets: list[ipaddress.IPv4Network],
                     gateways: set[str]) -> list[str]:
        """Explain the scan's limits, so gaps read as facts not failures."""
        notes: list[str] = []

        # A missing vendor database is deliberately NOT noted here: until the
        # "Update Vendor Database" action ships, every fresh install would
        # carry the note on every scan, which is noise rather than signal.
        # (Vendor names still populate from oui.py's built-in table.)
        if oui.has_full_registry() and oui.registry_status().get("stale"):
            notes.append(
                "The vendor database is over 90 days old. Refreshing it helps "
                "identify recently released devices.")

        randomized = [d for d in devices if d.randomized_mac]
        if randomized:
            notes.append(
                f"{len(randomized)} device(s) use a randomized private MAC "
                "address, so their manufacturer cannot be identified and the "
                "address will change again later. That is the device "
                "protecting its privacy - phones do this by default.")

        real = [d for d in devices if not d.is_self]
        if targets and gateways and len(real) <= 1:
            notes.append(
                "Only the router answered. If you know other devices are "
                "connected, the access point is very likely using client "
                "isolation (also called AP isolation or guest mode), which "
                "blocks devices from seeing each other by design - no scanner "
                "can work around that from this side.")

        no_mac = [d for d in devices if not d.mac and not d.is_self]
        if no_mac:
            notes.append(
                f"{len(no_mac)} device(s) announced themselves over mDNS/UPnP "
                "but are not in the ARP table - they are usually on another "
                "subnet or reached through a router.")
        return notes
