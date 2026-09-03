"""Tests for the read-only network connection monitor."""

from __future__ import annotations

import pytest

pytest.importorskip("psutil", reason="psutil not installed")

from cortex_unified.system_tools.network_monitor import (
    Connection,
    NetworkMonitor,
    _is_private,
)


class TestClassification:
    """TestClassification."""
    def test_loopback_is_private(self):
        """test_loopback_is_private."""
        assert _is_private("127.0.0.1") is True
        assert _is_private("::1") is True

    def test_lan_is_private(self):
        """test_lan_is_private."""
        assert _is_private("192.168.1.10") is True
        assert _is_private("10.0.0.5") is True
        assert _is_private("172.16.3.4") is True

    def test_public_is_not_private(self):
        """test_public_is_not_private."""
        assert _is_private("8.8.8.8") is False
        assert _is_private("140.82.112.3") is False

    def test_unparseable_defaults_private(self):
        # Can't classify -> must not falsely flag as external.
        """test_unparseable_defaults_private."""
        assert _is_private("not-an-ip") is True


class TestConnectionFlags:
    """TestConnectionFlags."""
    def test_public_listener_flagged(self):
        """test_public_listener_flagged."""
        c = Connection("TCP", "0.0.0.0", 445, "", 0, "LISTEN", 4, "System")
        assert c.listening_public is True
        assert c.remote_external is False

    def test_localhost_listener_not_public(self):
        """test_localhost_listener_not_public."""
        c = Connection("TCP", "127.0.0.1", 5432, "", 0, "LISTEN", 100, "postgres")
        assert c.listening_public is False

    def test_external_established_flagged(self):
        """test_external_established_flagged."""
        c = Connection("TCP", "192.168.1.5", 55000, "8.8.8.8", 443,
                       "ESTABLISHED", 200, "chrome.exe")
        assert c.remote_external is True

    def test_internal_established_not_external(self):
        """test_internal_established_not_external."""
        c = Connection("TCP", "192.168.1.5", 55000, "192.168.1.1", 443,
                       "ESTABLISHED", 200, "chrome.exe")
        assert c.remote_external is False

    def test_to_dict_shape(self):
        """test_to_dict_shape."""
        c = Connection("TCP", "0.0.0.0", 80, "", 0, "LISTEN", 4, "svc", "HTTP")
        d = c.to_dict()
        assert d["protocol"] == "TCP"
        assert d["local"] == "0.0.0.0:80"
        assert d["service"] == "HTTP"
        assert d["listening_public"] is True
        assert set(d) >= {"protocol", "local", "remote", "status", "pid",
                          "process", "service", "listening_public", "remote_external"}


class TestMonitor:
    """TestMonitor."""
    def test_connections_returns_list(self):
        """test_connections_returns_list."""
        conns = NetworkMonitor().connections()
        assert isinstance(conns, list)
        assert all(isinstance(c, Connection) for c in conns)

    def test_summarize_counts(self):
        """test_summarize_counts."""
        conns = [
            Connection("TCP", "0.0.0.0", 445, "", 0, "LISTEN", 4, "System"),
            Connection("TCP", "192.168.1.5", 5000, "8.8.8.8", 443,
                       "ESTABLISHED", 10, "app"),
            Connection("TCP", "127.0.0.1", 1234, "", 0, "LISTEN", 11, "loc"),
        ]
        s = NetworkMonitor.summarize(conns)
        assert s["total"] == 3
        assert s["listening"] == 2
        assert s["established"] == 1
        assert s["public_listeners"] == 1
        assert s["external"] == 1
