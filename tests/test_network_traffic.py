"""Tests for the live throughput monitor (rate math + shape)."""

from __future__ import annotations

import pytest

pytest.importorskip("psutil", reason="psutil not installed")

from cortex_unified.system_tools.network_traffic import (
    NicSample,
    TrafficMonitor,
    TrafficSample,
)


class TestSample:
    """Testsample.

    Manages TestSample operations and coordinates related state changes for the component.
    """
    def test_first_sample_zero_rate(self):
        """test_first_sample_zero_rate.

        Manages test first sample zero rate operations and coordinates related state changes for the component.
        """
        tm = TrafficMonitor()
        s = tm.sample()
        assert isinstance(s, TrafficSample)
        # No previous reading -> rates are zero, totals are real.
        assert s.send_rate == 0.0 and s.recv_rate == 0.0
        assert s.total_sent >= 0 and s.total_recv >= 0

    def test_since_start_starts_zero(self):
        """test_since_start_starts_zero.

        Manages test since start starts zero operations and coordinates related state changes for the component.
        """
        tm = TrafficMonitor()
        s = tm.sample()
        assert s.sent_since_start == 0 and s.recv_since_start == 0

    def test_second_sample_has_nonnegative_rates(self):
        """test_second_sample_has_nonnegative_rates.

        Manages test second sample has nonnegative rates operations and coordinates related state changes for the component.
        """
        import time
        tm = TrafficMonitor()
        tm.sample()
        time.sleep(0.2)
        s = tm.sample()
        assert s.send_rate >= 0.0 and s.recv_rate >= 0.0
        # since-start deltas can only grow.
        assert s.sent_since_start >= 0 and s.recv_since_start >= 0

    def test_per_nic_present_and_sorted(self):
        """test_per_nic_present_and_sorted.

        Manages test per nic present and sorted operations and coordinates related state changes for the component.
        """
        tm = TrafficMonitor()
        tm.sample()
        s = tm.sample()
        assert isinstance(s.per_nic, list)
        assert all(isinstance(n, NicSample) for n in s.per_nic)
        rates = [n.send_rate + n.recv_rate for n in s.per_nic]
        assert rates == sorted(rates, reverse=True)

    def test_to_dict_shape(self):
        """test_to_dict_shape.

        Manages test to dict shape operations and coordinates related state changes for the component.
        """
        tm = TrafficMonitor()
        d = tm.sample().to_dict()
        assert set(d) >= {"send_rate", "recv_rate", "total_sent", "total_recv",
                          "sent_since_start", "recv_since_start", "per_nic"}


def test_singleton():
    """test_singleton.

    Manages test singleton operations and coordinates related state changes for the component.
    """
    assert TrafficMonitor.instance() is TrafficMonitor.instance()
