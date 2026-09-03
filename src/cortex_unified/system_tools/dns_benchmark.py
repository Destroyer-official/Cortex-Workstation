"""Cortex Cleaner — Multi-Threaded DNS Latency Benchmark & Optimizer.

Benchmarks query round-trip latency across top global, privacy, and secure DNS providers
using raw DNS socket queries (A-record resolution) and enables 1-click optimal adapter configuration.
"""

from __future__ import annotations

import concurrent.futures
import platform
import random
import socket
import struct
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class DnsServerSpec:
    """Dns Server Spec data container."""
    provider: str
    name: str
    primary_ip: str
    secondary_ip: str
    category: str  # "Fast & Standard", "Security & Malware", "Ad Blocking", "Family Safe"
    features: str


KNOWN_DNS_PROVIDERS: List[DnsServerSpec] = [
    DnsServerSpec("Cloudflare", "Cloudflare Standard", "1.1.1.1", "1.0.0.1", "Fast & Standard", "Lowest latency, privacy-first, zero logs"),
    DnsServerSpec("Cloudflare", "Cloudflare Security", "1.1.1.2", "1.0.0.2", "Security & Malware", "Automated malware and phishing blocking"),
    DnsServerSpec("Google", "Google Public DNS", "8.8.8.8", "8.8.4.4", "Fast & Standard", "Global geo-distributed anycast infrastructure"),
    DnsServerSpec("Quad9", "Quad9 Secure", "9.9.9.9", "149.112.112.112", "Security & Malware", "Threat intelligence blocklist, Swiss privacy"),
    DnsServerSpec("OpenDNS", "OpenDNS Home", "208.67.222.222", "208.67.220.220", "Fast & Standard", "Cisco Umbrella threat intelligence"),
    DnsServerSpec("AdGuard", "AdGuard Default", "94.140.14.14", "94.140.15.15", "Ad Blocking", "Blocks ads, trackers, and malicious domains"),
    DnsServerSpec("Control D", "Control D Uncensored", "76.76.2.0", "76.76.10.0", "Fast & Standard", "High-speed modern DNS with zero logging"),
    DnsServerSpec("CleanBrowsing", "CleanBrowsing Security", "185.228.168.9", "185.228.169.9", "Security & Malware", "Blocks phishing, malicious sites, and exploits"),
]


@dataclass
class DnsBenchmarkResult:
    """Dns Benchmark Result data container."""
    server: DnsServerSpec
    min_ms: float
    avg_ms: float
    max_ms: float
    jitter_ms: float
    success_rate_pct: float
    is_fastest: bool = False
    is_reachable: bool = True
    error: Optional[str] = None


class DnsBenchmarkEngine:
    """Production DNS query benchmarking and network configuration engine."""

    BENCHMARK_DOMAINS = ["google.com", "cloudflare.com", "microsoft.com", "wikipedia.org", "amazon.com"]

    @staticmethod
    def _build_dns_query(domain: str) -> bytes:
        """Construct raw DNS wire format query for an A record."""
        # Transaction ID (random 16-bit)
        tid = random.randint(0, 65535)
        # Flags: Standard query, recursion desired (0x0100)
        flags = 0x0100
        # Questions = 1, Answer RRs = 0, Authority RRs = 0, Additional RRs = 0
        header = struct.pack(">HHHHHH", tid, flags, 1, 0, 0, 0)

        # Question name: length-prefixed labels e.g. \x06google\x03com\x00
        qname = b""
        for part in domain.split("."):
            qname += bytes([len(part)]) + part.encode("ascii")
        qname += b"\x00"

        # Type A (1), Class IN (1)
        qtype_qclass = struct.pack(">HH", 1, 1)
        return header + qname + qtype_qclass

    @classmethod
    def _query_dns(cls, server_ip: str, domain: str, timeout_seconds: float = 1.5) -> Optional[float]:
        """Send a direct UDP DNS query and measure round-trip latency in milliseconds."""
        query = cls._build_dns_query(domain)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout_seconds)

        start = time.perf_counter()
        try:
            sock.sendto(query, (server_ip, 53))
            data, _ = sock.recvfrom(512)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return elapsed_ms
        except Exception:
            return None
        finally:
            sock.close()

    @classmethod
    def benchmark_server(
        cls,
        server: DnsServerSpec,
        domains: Optional[List[str]] = None,
        timeout_seconds: float = 1.5,
    ) -> DnsBenchmarkResult:
        """Benchmark a DNS provider across multiple test domains."""
        test_domains = domains or cls.BENCHMARK_DOMAINS
        latencies: List[float] = []

        for d in test_domains:
            lat = cls._query_dns(server.primary_ip, d, timeout_seconds=timeout_seconds)
            if lat is not None:
                latencies.append(lat)

        if not latencies:
            return DnsBenchmarkResult(
                server=server,
                min_ms=0.0,
                avg_ms=0.0,
                max_ms=0.0,
                jitter_ms=0.0,
                success_rate_pct=0.0,
                is_reachable=False,
                error="No response (timeout)",
            )

        min_lat = min(latencies)
        max_lat = max(latencies)
        avg_lat = sum(latencies) / len(latencies)
        jitter = max_lat - min_lat
        success_rate = (len(latencies) / len(test_domains)) * 100.0

        return DnsBenchmarkResult(
            server=server,
            min_ms=round(min_lat, 2),
            avg_ms=round(avg_lat, 2),
            max_ms=round(max_lat, 2),
            jitter_ms=round(jitter, 2),
            success_rate_pct=round(success_rate, 1),
            is_reachable=True,
        )

    @classmethod
    def run_full_benchmark(
        cls,
        servers: Optional[List[DnsServerSpec]] = None,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> List[DnsBenchmarkResult]:
        """Concurrently benchmark all known DNS providers."""
        target_servers = servers or KNOWN_DNS_PROVIDERS
        results: List[DnsBenchmarkResult] = []
        total = len(target_servers)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_server = {
                executor.submit(cls.benchmark_server, s): s for s in target_servers
            }

            for idx, future in enumerate(concurrent.futures.as_completed(future_to_server)):
                if cancel_check and cancel_check():
                    break
                res = future.result()
                results.append(res)
                if progress_cb:
                    progress_cb(idx + 1, total, res.server.name)

        # Sort reachable by lowest average latency
        reachable = [r for r in results if r.is_reachable]
        unreachable = [r for r in results if not r.is_reachable]

        reachable.sort(key=lambda r: r.avg_ms)
        if reachable:
            reachable[0].is_fastest = True

        return reachable + unreachable

    @classmethod
    def apply_dns_servers(cls, interface_name: str, primary_ip: str, secondary_ip: Optional[str] = None) -> Tuple[bool, str]:
        """Configure DNS servers on the specified network adapter via netsh."""
        if platform.system() != "Windows":
            return False, "Windows only"

        try:
            # Set primary DNS
            cmd1 = ["netsh", "interface", "ip", "set", "dns", f"name={interface_name}", "static", primary_ip]
            res1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=10)
            if res1.returncode != 0:
                return False, res1.stderr.strip() or res1.stdout.strip() or "Failed to set primary DNS (Admin rights required)"

            # Set secondary DNS if provided
            if secondary_ip:
                cmd2 = ["netsh", "interface", "ip", "add", "dns", f"name={interface_name}", secondary_ip, "index=2"]
                subprocess.run(cmd2, capture_output=True, text=True, timeout=10)

            # Flush DNS cache to take immediate effect
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True, timeout=5)
            return True, f"Configured DNS for '{interface_name}' to {primary_ip}" + (f", {secondary_ip}" if secondary_ip else "")
        except Exception as exc:
            return False, str(exc)
