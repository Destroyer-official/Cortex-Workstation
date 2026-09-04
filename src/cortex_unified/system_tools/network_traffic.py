"""Live network throughput monitor - system-wide and per-interface.

Uses psutil's I/O counters and computes up/download *rates* from the delta
between successive samples. This is accurate, needs no admin, and is very
cheap (two counter reads per tick), which keeps it in line with Cortex's
lightweight goal.

Honesty note: this reports throughput per network interface, not per process.
Attributing bytes-on-the-wire to individual processes on Windows requires
kernel ETW tracing (the ``Microsoft-Windows-Kernel-Network`` provider) running
as Administrator, which is heavy and fragile; we deliberately don't fake a
per-process byte figure. For per-process insight we use active-connection
counts (see NetworkMonitor), which are real.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class NicSample:
    """Nicsample.

    Manages NicSample operations and coordinates related state changes for the component.
    """

    name: str
    bytes_sent: int
    bytes_recv: int
    send_rate: float = 0.0   # bytes/sec
    recv_rate: float = 0.0   # bytes/sec

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "name": self.name,
            "bytes_sent": self.bytes_sent,
            "bytes_recv": self.bytes_recv,
            "send_rate": self.send_rate,
            "recv_rate": self.recv_rate,
        }


@dataclass(slots=True)
class TrafficSample:
    """Trafficsample.

    Manages TrafficSample operations and coordinates related state changes for the component.
    """

    send_rate: float = 0.0
    recv_rate: float = 0.0
    total_sent: int = 0
    total_recv: int = 0
    sent_since_start: int = 0
    recv_since_start: int = 0
    per_nic: list[NicSample] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "send_rate": self.send_rate,
            "recv_rate": self.recv_rate,
            "total_sent": self.total_sent,
            "total_recv": self.total_recv,
            "sent_since_start": self.sent_since_start,
            "recv_since_start": self.recv_since_start,
            "per_nic": [n.to_dict() for n in self.per_nic],
        }


class TrafficMonitor:
    """Stateful throughput sampler. Reuse ONE instance for correct rates.

    Rates come from the delta between successive samples, so a fresh monitor
    reports zeros until its second :meth:`sample` call.
    """

    _instance: "TrafficMonitor | None" = None
    _instance_lock: threading.Lock = threading.Lock()

    @classmethod
    def instance(cls) -> "TrafficMonitor":
        """Instance.

        Manages instance operations and coordinates related state changes for the component.

        Returns:
            'TrafficMonitor': Result of the operation.
        """
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        """Initialize Traffic Monitor.

        Initializes the instance and configures internal state.
        """
        self._last_total: tuple[int, int] | None = None      # (sent, recv)
        self._last_nic: dict[str, tuple[int, int]] = {}
        self._last_t: float | None = None
        self._start_total: tuple[int, int] | None = None      # baseline at first sample
        self._sample_lock = threading.Lock()

    def sample(self) -> TrafficSample:
        """Read psutil I/O counters once and derive rates from the previous sample.

        The first call only establishes the baseline. Negative deltas (counter
        reset, e.g. after a NIC restart) are clamped to 0 rather than reported
        as negative throughput.
        """
        with self._sample_lock:
            try:
                import psutil
            except ImportError:
                return TrafficSample()

            now = time.monotonic()
            total = psutil.net_io_counters()
            pernic = psutil.net_io_counters(pernic=True)
            cur_total = (total.bytes_sent, total.bytes_recv)

            if self._start_total is None:
                self._start_total = cur_total

            dt = (now - self._last_t) if self._last_t else 0.0
            send_rate = recv_rate = 0.0
            if self._last_total is not None and dt > 0:
                send_rate = max(0.0, (cur_total[0] - self._last_total[0]) / dt)
                recv_rate = max(0.0, (cur_total[1] - self._last_total[1]) / dt)

            nic_samples: list[NicSample] = []
            for name, counters in pernic.items():
                cur = (counters.bytes_sent, counters.bytes_recv)
                s_rate = r_rate = 0.0
                prev = self._last_nic.get(name)
                if prev is not None and dt > 0:
                    s_rate = max(0.0, (cur[0] - prev[0]) / dt)
                    r_rate = max(0.0, (cur[1] - prev[1]) / dt)
                nic_samples.append(NicSample(
                    name=name, bytes_sent=cur[0], bytes_recv=cur[1],
                    send_rate=s_rate, recv_rate=r_rate,
                ))
                self._last_nic[name] = cur

            self._last_total = cur_total
            self._last_t = now

            return TrafficSample(
                send_rate=send_rate,
                recv_rate=recv_rate,
                total_sent=cur_total[0],
                total_recv=cur_total[1],
                sent_since_start=cur_total[0] - self._start_total[0],
                recv_since_start=cur_total[1] - self._start_total[1],
                per_nic=sorted(nic_samples,
                               key=lambda n: n.recv_rate + n.send_rate, reverse=True),
            )
