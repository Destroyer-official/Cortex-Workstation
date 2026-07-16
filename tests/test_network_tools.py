"""Tests for the network diagnostic utilities (parsers + offline logic)."""

from __future__ import annotations

from cortex_unified.system_tools.network_tools import Hop, NetworkTools, PingResult

WIN_PING = """
Pinging google.com [142.250.190.78] with 32 bytes of data:
Reply from 142.250.190.78: bytes=32 time=12ms TTL=115
Reply from 142.250.190.78: bytes=32 time=11ms TTL=115
Reply from 142.250.190.78: bytes=32 time=14ms TTL=115
Reply from 142.250.190.78: bytes=32 time=13ms TTL=115

Ping statistics for 142.250.190.78:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 11ms, Maximum = 14ms, Average = 12ms
"""

NIX_PING = """
PING google.com (142.250.190.78) 56(84) bytes of data.
64 bytes from x: icmp_seq=1 ttl=115 time=12.0 ms
--- google.com ping statistics ---
4 packets transmitted, 4 received, 0% packet loss, time 3005ms
rtt min/avg/max/mdev = 11.100/12.200/14.000/1.000 ms
"""

WIN_PING_LOSS = """
Ping statistics for 10.0.0.9:
    Packets: Sent = 4, Received = 1, Lost = 3 (75% loss),
Approximate round trip times in milli-seconds:
    Minimum = 20ms, Maximum = 30ms, Average = 25ms
"""

WIN_TRACERT = """
Tracing route to google.com [142.250.190.78]
over a maximum of 30 hops:

  1     1 ms     1 ms     1 ms  192.168.1.1
  2     *        *        *     Request timed out.
  3    12 ms    11 ms    13 ms  142.250.190.78

Trace complete.
"""


class TestPingParse:
    def test_windows_success(self):
        r = NetworkTools._parse_ping("google.com", WIN_PING)
        assert isinstance(r, PingResult)
        assert r.reachable is True
        assert r.sent == 4 and r.received == 4
        assert r.loss_percent == 0.0
        assert r.min_ms == 11.0 and r.max_ms == 14.0 and r.avg_ms == 12.0

    def test_nix_success(self):
        r = NetworkTools._parse_ping("google.com", NIX_PING)
        assert r.reachable is True
        assert r.received == 4
        assert r.avg_ms == 12.2

    def test_loss(self):
        r = NetworkTools._parse_ping("10.0.0.9", WIN_PING_LOSS)
        assert r.loss_percent == 75.0
        assert r.received == 1 and r.reachable is True

    def test_unreachable(self):
        r = NetworkTools._parse_ping("x", "Ping request could not find host x.")
        assert r.reachable is False


class TestTracerouteParse:
    def test_parses_hops(self):
        hops = NetworkTools._parse_traceroute(WIN_TRACERT)
        assert len(hops) == 3
        assert hops[0].number == 1 and hops[0].host == "192.168.1.1"
        assert hops[0].times_ms == [1.0, 1.0, 1.0]

    def test_timeout_hop(self):
        hops = NetworkTools._parse_traceroute(WIN_TRACERT)
        assert hops[1].host == "*"
        assert hops[1].times_ms == []

    def test_hop_to_dict_avg(self):
        hops = NetworkTools._parse_traceroute(WIN_TRACERT)
        d = hops[2].to_dict()
        assert d["avg_ms"] == 12.0


class TestDNS:
    def test_localhost_resolves(self):
        ips = NetworkTools.dns_lookup("localhost")
        assert any(ip.startswith("127.") or ip == "::1" for ip in ips)

    def test_bad_host_empty(self):
        assert NetworkTools.dns_lookup("no_such_host_zzz.invalid") == []

    def test_reverse_loopback(self):
        # Reverse of 127.0.0.1 may or may not resolve; must not raise.
        assert isinstance(NetworkTools.reverse_dns("127.0.0.1"), str)


class TestPorts:
    def test_closed_high_port_false(self):
        # A very high port on localhost is almost certainly closed.
        assert NetworkTools.check_port("127.0.0.1", 59999, timeout=0.3) is False

    def test_invalid_port(self):
        assert NetworkTools.check_port("127.0.0.1", 999999, timeout=0.3) is False

    def test_scan_returns_all_common_ports(self):
        from cortex_unified.system_tools.network_tools import COMMON_PORTS
        res = NetworkTools().scan_common_ports("127.0.0.1", timeout=0.1)
        assert set(res.keys()) == set(COMMON_PORTS.keys())
        assert all(isinstance(v, bool) for v in res.values())


class TestIpInfo:
    def test_public(self):
        info = NetworkTools.ip_info("8.8.8.8")
        assert info["valid"] and info["global"]
        assert info["category"] == "Public (internet)"

    def test_private(self):
        info = NetworkTools.ip_info("192.168.1.1")
        assert info["private"] and info["category"] == "Private / LAN"

    def test_loopback(self):
        assert NetworkTools.ip_info("127.0.0.1")["category"] == "Loopback (this machine)"

    def test_ipv6(self):
        info = NetworkTools.ip_info("2001:4860:4860::8888")
        assert info["valid"] and info["version"] == 6

    def test_invalid(self):
        assert NetworkTools.ip_info("not-an-ip")["valid"] is False
