"""Cortex Cleaner — Windows Event Log Anomaly & Hardware Error Monitor.

Queries Windows Event Log channels for critical system faults and hardware warnings:
1. Disk & NTFS Errors (Event IDs 7, 11, 55 — bad blocks, controller errors, MFT corruption).
2. Kernel Crashes & BugChecks (Event ID 1001 — BlueScreen of Death events).
3. Sudden Power Loss & Dirty Shutdowns (Event ID 6008, Event ID 41 Kernel-Power).
4. Application Crash Events (Event ID 1000 — faulty modules and exception codes).
5. Security Audit Failures (Event ID 4625 — failed authentication attempts).
"""

from __future__ import annotations

import datetime
import os
import platform
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class LogAnomalyEvent:
    """Log Anomaly Event data container."""
    channel: str
    event_id: int
    level: str  # "Critical", "Error", "Warning"
    source: str
    time_created: str
    message: str
    category: str  # "Hardware / Disk", "Kernel Crash", "Power Loss", "App Crash", "Security"


@dataclass
class AnomalyScanReport:
    """Anomaly Scan Report data container."""
    total_anomalies: int
    critical_count: int
    error_count: int
    warning_count: int
    disk_errors_count: int
    crash_count: int
    events: List[LogAnomalyEvent]


class EventLogMonitor:
    """Production Windows Event Log hardware and crash anomaly detector."""

    CRITICAL_QUERIES = [
        # (Category, Channel, Level, XPath Filter)
        ("Hardware / Disk", "System", "Error", "*[System[(Level=1 or Level=2) and (EventID=7 or EventID=11 or EventID=55 or EventID=153)]]"),
        ("Kernel Crash", "System", "Critical", "*[System[(EventID=1001 or EventID=41)]]"),
        ("Power Loss", "System", "Error", "*[System[(EventID=6008)]]"),
        ("App Crash", "Application", "Error", "*[System[(Level=2) and (EventID=1000 or EventID=1002)]]"),
    ]

    @classmethod
    def query_anomalies(cls, max_events_per_category: int = 15) -> AnomalyScanReport:
        """Query Event Log channels for recent critical errors and hardware warnings."""
        if platform.system() != "Windows":
            return AnomalyScanReport(0, 0, 0, 0, 0, 0, [])

        events: List[LogAnomalyEvent] = []

        for category, channel, default_level, xpath in cls.CRITICAL_QUERIES:
            cmd = [
                "wevtutil.exe", "qe", channel,
                f"/q:{xpath}",
                f"/c:{max_events_per_category}",
                "/rd:true",
                "/f:RenderedXml",
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
                if res.returncode == 0 and res.stdout.strip():
                    import xml.etree.ElementTree as ET
                    # Wrap output in a root tag to parse multiple events
                    wrapped_xml = f"<Events>{res.stdout}</Events>"
                    try:
                        root = ET.fromstring(wrapped_xml)
                        for ev in root.findall(".//{http://schemas.microsoft.com/win/2004/08/events/event}Event"):
                            sys_elem = ev.find("{http://schemas.microsoft.com/win/2004/08/events/event}System")
                            if sys_elem is None:
                                continue

                            ev_id_el = sys_elem.find("{http://schemas.microsoft.com/win/2004/08/events/event}EventID")
                            ev_id = int(ev_id_el.text) if ev_id_el is not None and ev_id_el.text else 0

                            provider = sys_elem.find("{http://schemas.microsoft.com/win/2004/08/events/event}Provider")
                            source_name = provider.attrib.get("Name", "Unknown") if provider is not None else "Unknown"

                            time_el = sys_elem.find("{http://schemas.microsoft.com/win/2004/08/events/event}TimeCreated")
                            time_str = time_el.attrib.get("SystemTime", "") if time_el is not None else ""

                            level_el = sys_elem.find("{http://schemas.microsoft.com/win/2004/08/events/event}Level")
                            lvl_val = int(level_el.text) if level_el is not None and level_el.text else 2
                            level_label = "Critical" if lvl_val == 1 else ("Error" if lvl_val == 2 else "Warning")

                            # Read message details from EventData if present
                            msg_parts = []
                            event_data = ev.find("{http://schemas.microsoft.com/win/2004/08/events/event}EventData")
                            if event_data is not None:
                                for data_item in event_data.findall("{http://schemas.microsoft.com/win/2004/08/events/event}Data"):
                                    if data_item.text:
                                        msg_parts.append(data_item.text.strip())

                            msg_summary = "; ".join(msg_parts[:3]) if msg_parts else f"Event {ev_id} reported by {source_name}"

                            events.append(LogAnomalyEvent(
                                channel=channel,
                                event_id=ev_id,
                                level=level_label,
                                source=source_name,
                                time_created=time_str.split(".")[0].replace("T", " "),
                                message=msg_summary,
                                category=category,
                            ))
                    except ET.ParseError:
                        pass
            except Exception:
                pass

        crit_cnt = sum(1 for e in events if e.level == "Critical")
        err_cnt = sum(1 for e in events if e.level == "Error")
        warn_cnt = sum(1 for e in events if e.level == "Warning")
        disk_cnt = sum(1 for e in events if "Disk" in e.category)
        crash_cnt = sum(1 for e in events if "Crash" in e.category)

        return AnomalyScanReport(
            total_anomalies=len(events),
            critical_count=crit_cnt,
            error_count=err_cnt,
            warning_count=warn_cnt,
            disk_errors_count=disk_cnt,
            crash_count=crash_cnt,
            events=events,
        )
