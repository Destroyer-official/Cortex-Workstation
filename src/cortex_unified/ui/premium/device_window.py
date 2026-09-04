"""Per-device deep scan worker and the premium device detail window.

Selecting a discovered device and pressing *Deep Scan Device* opens one focused
window that shows everything Cortex actually observed about that single host:
identity, reachable services with protocol evidence, evidence-backed security
findings, fingerprint reasoning, discovery methods, local history and the raw
JSON behind every claim.

Safety notes that also hold here:

* The target is revalidated against the private scopes of the completed scan
  immediately before any probe, so a device that has left the scope cannot be
  scanned from this window.
* Nothing is exploited, brute-forced or logged into. A finding is produced only
  from an observation the device itself returned.
* Absence of a finding is never presented as proof that a device is safe.
"""

from __future__ import annotations

import html
import json
import threading

from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtGui import (
    QDesktopServices,
    QGuiApplication,
    QPdfWriter,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .widgets import Badge, Card, StatCard

_SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}
_BADGE_KIND = {
    "critical": "high", "high": "high", "medium": "medium",
    "low": "low", "info": "info",
}
_DASH = "\u2014"


def _severity_badge_kind(severity: str) -> str:
    """Map a finding severity string to its badge kind.

    Manages severity badge kind operations and coordinates related state changes for the component.

    Args:
        severity (str): The severity parameter.

    Returns:
        str: Formatted string or path.
    """
    return _BADGE_KIND.get(str(severity).lower(), "info")


class DeviceDeepScanWorker(QObject):
    """Devicedeepscanworker.

    Manages DeviceDeepScanWorker operations and coordinates related state changes for the component.
    """

    finished = Signal(object)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        device,
        networks,
        profile="advanced",
        custom_ports=(),
        nmap_modes=None,
        catalog_path=None,
    ):
        """Store the device snapshot, authorized networks, and scan options for the worker.

        Initializes the instance and configures internal state.

        Args:
            device: The device parameter.
            networks: The networks parameter.
            profile: The profile parameter.
            custom_ports: The custom ports parameter.
            nmap_modes: The nmap modes parameter.
            catalog_path: Filesystem path to the target file or directory.
        """
        super().__init__()
        self._ip = str(getattr(device, "ip", ""))
        self._mac = str(getattr(device, "mac", ""))
        self._hostname = str(getattr(device, "hostname", ""))
        self._vendor = str(getattr(device, "vendor", ""))
        self._advertised = dict(getattr(device, "services", {}) or {})
        self._sources = set(getattr(device, "sources", set()) or set())
        self._known_ports = list(getattr(device, "open_ports", ()) or ())
        self._is_gateway = bool(getattr(device, "is_gateway", False))
        self._is_self = bool(getattr(device, "is_self", False))
        self._networks = tuple(networks)
        self._profile = str(profile)
        self._custom_ports = tuple(custom_ports or ())
        self._nmap_modes = nmap_modes
        self._catalog_path = catalog_path
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """Request cancellation of the running scan.

        Sets the internal cancellation event to cooperatively stop worker execution at the next safe boundary.
        """
        self._cancel.set()

    def _say(self, message: str) -> None:
        """Say.

        Manages say operations and coordinates related state changes for the component.

        Args:
            message (str): Informational or progress status message.
        """
        self.progress.emit(message)

    def run(self):  # noqa: C901 - one linear evidence-gathering sequence
        """Re-check authorization, scan services, fingerprint, audit, and emit the evidence payload.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.device_fingerprint import (
                fingerprint_device,
            )
            from cortex_unified.system_tools.network_discovery import Device
            from cortex_unified.system_tools.network_security_audit import (
                audit_devices,
            )
            from cortex_unified.system_tools.network_service_scanner import (
                NetworkServiceScanner,
                ScanProfile,
                is_authorized_target,
            )

            # Re-verify authorization here: the scope list comes from the
            # completed discovery, and a device may have left it since.
            if not is_authorized_target(self._ip, self._networks):
                raise ValueError(
                    f"{self._ip} is not inside the authorized private "
                    "scope of the last scan; run a new network scan first.")

            notes: list[str] = []
            profile = ScanProfile(self._profile)
            scanner = NetworkServiceScanner(
                timeout=0.7 if profile is not ScanProfile.DEEP else 0.9,
                workers=48,
                rate_limit=200.0,
            )
            self._say(f"Auditing services on {self._ip}\u2026")
            observations = scanner.scan(
                hosts=[self._ip],
                allowed_networks=self._networks,
                profile=profile,
                progress=self._say,
                cancel_event=self._cancel,
                custom_ports=self._custom_ports,
            )

            nmap_status = {"used": False, "reason": "not requested"}
            if self._nmap_modes and not self._cancel.is_set():
                nmap_status = self._run_nmap(observations, notes)

            observed_sources = set(self._sources)
            if observations:
                observed_sources.add("ports")
            device = Device(
                ip=self._ip,
                mac=self._mac,
                hostname=self._hostname,
                vendor=self._vendor,
                sources=observed_sources,
                services=dict(self._advertised),
                open_ports=[
                    item.port for item in observations
                    if item.transport == "tcp" and item.state == "open"
                ] or list(self._known_ports),
                service_observations=list(observations),
                is_gateway=self._is_gateway,
                is_self=self._is_self,
            )
            device.fingerprint = fingerprint_device(device)

            catalog = None
            if self._catalog_path:
                from cortex_unified.system_tools.vulnerability_catalog import (
                    VulnerabilityCatalog,
                )
                catalog = VulnerabilityCatalog.load(self._catalog_path)
            findings = audit_devices([device], vulnerability_catalog=catalog)
            findings.sort(key=lambda item: (
                _SEVERITY_RANK.get(item.severity, 5),
                item.port or 0,
                item.code,
            ))

            ping = self._ping()
            reverse_dns = self._reverse_dns()
            history = self._history(device)

            payload = {
                "device": device.to_dict(),
                "services": [item.to_dict() for item in observations],
                "findings": [item.to_dict() for item in findings],
                "fingerprint": (
                    device.fingerprint.to_dict()
                    if device.fingerprint is not None else None),
                "ping": ping,
                "reverse_dns": reverse_dns,
                "profile": self._profile,
                "scanned_networks": list(self._networks),
                "custom_ports": list(self._custom_ports),
                "nmap": nmap_status,
                "cancelled": self._cancel.is_set(),
                "notes": notes,
                "advertised_services": dict(self._advertised),
                "discovery_sources": sorted(self._sources),
                **history,
            }
            self.finished.emit(payload)
        except Exception as exc:  # noqa: BLE001 - report verbatim to UI
            self.failed.emit(str(exc))

    def _run_nmap(self, observations, notes) -> dict:
        """Optionally verify observed TCP ports with local Nmap; merge new observations.

        Manages run nmap operations and coordinates related state changes for the component.

        Args:
            observations: The observations parameter.
            notes: The notes parameter.

        Returns:
            dict: Dictionary mapping identifiers to status or values.
        """
        from cortex_unified.core import proc
        from cortex_unified.system_tools.nmap_adapter import (
            NmapAdapter,
            NmapError,
        )

        adapter = NmapAdapter()
        status = adapter.status()
        if not status.available:
            notes.append(
                "Optional Nmap was requested, but its executable was not "
                "found, so only Cortex's own bounded scanner ran.")
            return {"used": False, "reason": status.reason}
        ports = self._custom_ports or tuple(
            item.port for item in observations
            if item.transport == "tcp" and item.state == "open")
        if not ports:
            notes.append(
                "Optional Nmap was skipped: no open TCP port was observed to "
                "verify, and Cortex never asks Nmap to scan every port here.")
            return {"used": False, "reason": "no observed TCP port to verify"}
        self._say(f"Running explicit optional Nmap on {self._ip}\u2026")
        try:
            extra = adapter.scan(
                targets=[self._ip],
                allowed_networks=self._networks,
                ports=ports,
                modes=self._nmap_modes,
                cancel_event=self._cancel,
            )
        except proc.ProcessCancelled:
            notes.append("The optional Nmap step was cancelled.")
            return {"used": False, "reason": "cancelled"}
        except (NmapError, OSError, ValueError) as exc:
            notes.append(f"Optional Nmap did not complete: {exc}")
            return {"used": False, "reason": str(exc)}
        known = {
            (item.ip, item.port, item.transport, item.name, item.source)
            for item in observations
        }
        for item in extra:
            key = (item.ip, item.port, item.transport, item.name, item.source)
            if key not in known:
                observations.append(item)
                known.add(key)
        return {
            "used": True,
            "reason": "completed",
            "modes": list(self._nmap_modes or ()),
            "observations": len(extra),
        }

    def _ping(self) -> dict:
        """Ping.

        Manages ping operations and coordinates related state changes for the component.

        Returns:
            dict: Dictionary mapping identifiers to status or values.
        """
        if self._cancel.is_set():
            return {"reachable": False, "error": "cancelled"}
        from cortex_unified.system_tools.network_tools import NetworkTools

        self._say(f"Checking reachability of {self._ip}\u2026")
        return NetworkTools().ping(
            self._ip,
            count=2,
            timeout_s=2,
            cancel_event=self._cancel,
        ).to_dict()

    def _reverse_dns(self) -> str:
        """Resolve the device IP to a hostname.

        Manages reverse dns operations and coordinates related state changes for the component.

        Returns:
            str: Formatted string or path.
        """
        if self._cancel.is_set():
            return ""
        from cortex_unified.system_tools.network_tools import NetworkTools

        return NetworkTools.reverse_dns(self._ip)

    def _history(self, device) -> dict:
        """History.

        Manages history operations and coordinates related state changes for the component.

        Args:
            device: The device parameter.

        Returns:
            dict: Dictionary mapping identifiers to status or values.
        """
        try:
            from cortex_unified.system_tools.network_inventory import (
                NetworkInventory,
                identity_key_for,
            )
            identity_key = identity_key_for(device)
            with NetworkInventory() as inventory:
                metadata = inventory.get_metadata(identity_key)
                lifetimes = {
                    row["identity_key"]: row
                    for row in inventory.device_lifetimes()
                }
                trends = inventory.exposure_trends(30)
        except (OSError, ValueError, RuntimeError) as exc:
            return {
                "identity_key": "",
                "metadata": None,
                "lifetime": None,
                "trends": [],
                "history_error": str(exc),
            }
        return {
            "identity_key": identity_key,
            "metadata": metadata.to_dict() if metadata is not None else None,
            "lifetime": lifetimes.get(identity_key),
            "trends": trends,
            "history_error": "",
        }


class DevicePingWorker(QObject):
    """Devicepingworker.

    Manages DevicePingWorker operations and coordinates related state changes for the component.
    """

    finished = Signal(object)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, ip: str, networks):
        """Store the target IP, authorized networks, and cancel event.

        Initializes the instance and configures internal state.

        Args:
            ip (str): The ip parameter.
            networks: The networks parameter.
        """
        super().__init__()
        self._ip = str(ip)
        self._networks = tuple(networks)
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """Request cancellation of the ping check.

        Sets the internal cancellation event to cooperatively stop worker execution at the next safe boundary.
        """
        self._cancel.set()

    def run(self) -> None:
        """Re-check authorization and emit an ICMP reachability result.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.network_service_scanner import (
                is_authorized_target,
            )
            from cortex_unified.system_tools.network_tools import NetworkTools

            if not is_authorized_target(self._ip, self._networks):
                raise ValueError(
                    f"{self._ip} is not inside the authorized private scope "
                    "of the last scan; run a new network scan first."
                )
            if self._cancel.is_set():
                self.finished.emit({
                    "host": self._ip,
                    "reachable": False,
                    "error": "cancelled",
                    "cancelled": True,
                })
                return
            self.progress.emit(f"Pinging {self._ip}\u2026")
            result = NetworkTools().ping(
                self._ip,
                count=2,
                timeout_s=2,
                cancel_event=self._cancel,
            ).to_dict()
            result["cancelled"] = self._cancel.is_set()
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001 - reported to the UI
            self.failed.emit(str(exc))


class DeviceDetailWindow(QDialog):
    """Devicedetailwindow.

    Manages DeviceDetailWindow operations and coordinates related state changes for the component.
    """

    closed = Signal(object)

    def __init__(
        self,
        win,
        device,
        networks,
        catalog_path=None,
        parent=None,
    ):
        """Build the non-modal device window with header, actions, stat cards, and evidence tabs.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
            device: The device parameter.
            networks: The networks parameter.
            catalog_path: Filesystem path to the target file or directory.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent or win)
        self.win = win
        self.p = win.palette_tokens
        self._device = device
        self._networks = tuple(networks)
        self._catalog_path = catalog_path
        self._payload: dict | None = None
        self._worker: DeviceDeepScanWorker | DevicePingWorker | None = None
        self._is_busy = False
        self._has_completed_scan = False
        self._close_pending = False

        self.setWindowTitle(f"Device \u2014 {device.label} ({device.ip})")
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.resize(1080, 760)
        self.setSizeGripEnabled(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)
        root.addWidget(self._build_header())
        root.addWidget(self._build_actions())
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        root.addWidget(self.progress)
        self.status = QLabel("Press Deep Scan Device to audit this host now.")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        root.addWidget(self._build_cards())
        root.addWidget(self._build_tabs(), 1)

        self._render_known()

    # -- construction ------------------------------------------------------

    def _build_header(self) -> QWidget:
        """Create the device header card with name, identity line, and badges.

        Manages build header operations and coordinates related state changes for the component.

        Returns:
            QWidget: Result of the operation.
        """
        device = self._device
        card = Card(self.p)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        top = QHBoxLayout()
        name = QLabel(device.label)
        name.setStyleSheet("font-size: 20px; font-weight: 800;")
        name.setWordWrap(True)
        top.addWidget(name)
        top.addStretch(1)
        for kind, text in self._header_badges():
            top.addWidget(Badge(self.p, kind, text))
        lay.addLayout(top)

        subtitle = QLabel(
            f"{device.ip}   \u2022   "
            f"{device.mac or 'MAC not observed'}   \u2022   "
            f"{device.vendor or 'vendor unknown'}")
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        lay.addWidget(subtitle)
        return card

    def _header_badges(self) -> list[tuple[str, str]]:
        """Derive header badges for router/self/randomized-MAC/kind flags.

        Manages header badges operations and coordinates related state changes for the component.

        Returns:
            list[tuple[str, str]]: List of processed items or identifiers.
        """
        device = self._device
        badges: list[tuple[str, str]] = []
        if device.is_gateway:
            badges.append(("info", "ROUTER"))
        if device.is_self:
            badges.append(("info", "THIS PC"))
        if device.randomized_mac:
            badges.append(("medium", "PRIVATE MAC"))
        kind = device.kind.upper()[:28]
        if kind and kind not in {text for _badge_kind, text in badges}:
            badges.append(("info", kind))
        return badges

    def _build_actions(self) -> QWidget:
        """Create the primary action row and the collapsible More Actions panel.

        Manages build actions operations and coordinates related state changes for the component.

        Returns:
            QWidget: Result of the operation.
        """
        holder = QWidget()
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        primary = QHBoxLayout()

        self.scan_btn = QPushButton("Deep Scan Device")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.setToolTip(
            "Audit common TCP/UDP services on this one device, with banners, "
            "TLS metadata and evidence-based findings.")
        self.scan_btn.clicked.connect(lambda: self.start_scan("advanced"))

        self.allports_btn = QPushButton("All TCP Ports")
        self.allports_btn.setToolTip(
            "Check TCP ports 1-65535 on this device only. Read-only and "
            "cancellable, but it takes longer and creates more traffic.")
        self.allports_btn.clicked.connect(self._confirm_all_ports)

        self.nmap_check = QComboBox()
        self.nmap_check.addItems([
            "Nmap: off",
            "Nmap: connect + version",
            "Nmap: SYN + version (admin)",
            "Nmap: ACK firewall map (admin)",
            "Nmap: SYN + version + OS (admin)",
        ])
        self.nmap_check.setMinimumWidth(190)
        self.nmap_check.setToolTip(
            "Optional verification with local Nmap. Only observed open ports "
            "are re-checked; scripts and exploits are never used.")

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel)
        self.ping_btn = QPushButton("Ping")
        self.ping_btn.clicked.connect(self._ping_only)
        self.wake_btn = QPushButton("Wake")
        self.wake_btn.clicked.connect(self._wake)
        self.open_btn = QPushButton("Open Service")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._open_service)
        self.copy_btn = QPushButton("Copy IP / MAC")
        self.copy_btn.clicked.connect(self._copy_identity)
        self.export_btn = QPushButton("Export Device Report")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export)

        self.more_actions_btn = QPushButton("More Actions  \u203A")
        self.more_actions_btn.setObjectName("CommandDisclosure")
        self.more_actions_btn.setCheckable(True)
        self.more_actions_btn.toggled.connect(self._toggle_more_actions)

        primary.addWidget(self.scan_btn)
        primary.addWidget(self.ping_btn)
        primary.addWidget(self.open_btn)
        primary.addWidget(self.more_actions_btn)
        primary.addStretch(1)
        primary.addWidget(self.cancel_btn)
        layout.addLayout(primary)

        self.action_panel = QWidget()
        self.action_panel.setObjectName("CommandPanel")
        secondary = QHBoxLayout(self.action_panel)
        secondary.setContentsMargins(10, 8, 10, 8)
        secondary.setSpacing(8)
        scan_label = QLabel("SCAN")
        scan_label.setObjectName("CommandGroupLabel")
        secondary.addWidget(scan_label)
        secondary.addWidget(self.allports_btn)
        secondary.addWidget(self.nmap_check)
        device_label = QLabel("DEVICE")
        device_label.setObjectName("CommandGroupLabel")
        secondary.addWidget(device_label)
        secondary.addWidget(self.wake_btn)
        secondary.addWidget(self.copy_btn)
        report_label = QLabel("REPORT")
        report_label.setObjectName("CommandGroupLabel")
        secondary.addWidget(report_label)
        secondary.addWidget(self.export_btn)
        secondary.addStretch(1)
        self.action_panel.setVisible(False)
        layout.addWidget(self.action_panel)
        return holder

    def _toggle_more_actions(self, visible: bool) -> None:
        """Show or hide the secondary action panel and restyle the disclosure button.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.

        Args:
            visible (bool): The visible parameter.
        """
        self.action_panel.setVisible(visible)
        marker = "\u2304" if visible else "\u203A"
        self.more_actions_btn.setText(f"More Actions  {marker}")
        self.more_actions_btn.setProperty("expanded", visible)
        style = self.more_actions_btn.style()
        style.unpolish(self.more_actions_btn)
        style.polish(self.more_actions_btn)

    def _build_cards(self) -> QWidget:
        """Create the five stat cards (services, findings, risk, latency, identity).

        Manages build cards operations and coordinates related state changes for the component.

        Returns:
            QWidget: Result of the operation.
        """
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        self.card_ports = StatCard(self.p, "Open services", _DASH)
        self.card_findings = StatCard(self.p, "Findings", _DASH)
        self.card_risk = StatCard(self.p, "Highest severity", _DASH)
        self.card_latency = StatCard(self.p, "Reachability", _DASH)
        self.card_identity = StatCard(self.p, "Identity confidence", _DASH)
        for card in (
            self.card_ports,
            self.card_findings,
            self.card_risk,
            self.card_latency,
            self.card_identity,
        ):
            lay.addWidget(card)
        return holder

    def _build_tabs(self) -> QWidget:
        """Create the tab widget with overview, services, findings, identity, discovery, history, labels, and raw evidence.

        Manages build tabs operations and coordinates related state changes for the component.

        Returns:
            QWidget: Result of the operation.
        """
        self.tabs = QTabWidget()

        self.overview = QWidget()
        self.overview_grid = QGridLayout(self.overview)
        self.overview_grid.setContentsMargins(12, 12, 12, 12)
        self.overview_grid.setHorizontalSpacing(18)
        self.overview_grid.setVerticalSpacing(8)
        self.tabs.addTab(self.overview, "Overview")

        self.services_tbl = self._table([
            "Port", "Proto", "Service", "State", "Product", "Version",
            "Latency", "Confidence", "Source", "Evidence",
        ], stretch=(9,))
        self.tabs.addTab(self.services_tbl, "Ports & Services")

        self.findings_tbl = self._table([
            "Severity", "Finding", "Port", "Detail", "Remediation",
            "CVE / advisory", "Confidence", "Evidence",
        ], stretch=(3, 4, 7))
        self.tabs.addTab(self.findings_tbl, "Security")

        self.identity_tbl = self._table([
            "Source", "Observation", "Strength", "Weight", "Why it matters",
        ], stretch=(1, 4))
        self.tabs.addTab(self.identity_tbl, "Identity Evidence")

        self.discovery_view = QTextEdit()
        self.discovery_view.setReadOnly(True)
        self.tabs.addTab(self.discovery_view, "Discovery")

        self.history_view = QTextEdit()
        self.history_view.setReadOnly(True)
        self.tabs.addTab(self.history_view, "History")

        self.notes_tab = QWidget()
        notes_layout = QVBoxLayout(self.notes_tab)
        notes_layout.setContentsMargins(12, 12, 12, 12)
        notes_hint = QLabel(
            "Your own labels for this device. They are stored locally in the "
            "Cortex inventory and are keyed to the device identity, so they "
            "survive DHCP address changes.")
        notes_hint.setObjectName("Muted")
        notes_hint.setWordWrap(True)
        notes_layout.addWidget(notes_hint)
        form = QGridLayout()
        form.addWidget(QLabel("Custom name:"), 0, 0)
        self.name_input = QLineEdit()
        form.addWidget(self.name_input, 0, 1)
        form.addWidget(QLabel("Trust:"), 1, 0)
        self.trust_combo = QComboBox()
        self.trust_combo.addItems(["unknown", "trusted", "guest", "blocked"])
        form.addWidget(self.trust_combo, 1, 1)
        form.addWidget(QLabel("Tags:"), 2, 0)
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("camera, iot, kids-room")
        form.addWidget(self.tags_input, 2, 1)
        form.addWidget(QLabel("Notes:"), 3, 0)
        self.notes_input = QLineEdit()
        form.addWidget(self.notes_input, 3, 1)
        notes_layout.addLayout(form)
        save_row = QHBoxLayout()
        save_row.addStretch(1)
        self.save_btn = QPushButton("Save Device Details")
        self.save_btn.setObjectName("Primary")
        self.save_btn.clicked.connect(self._save_metadata)
        save_row.addWidget(self.save_btn)
        notes_layout.addLayout(save_row)
        notes_layout.addStretch(1)
        self.tabs.addTab(self.notes_tab, "Labels & Notes")

        self.raw_view = QTextEdit()
        self.raw_view.setReadOnly(True)
        self.tabs.addTab(self.raw_view, "Raw Evidence")
        return self.tabs

    def _table(
        self,
        headers: list[str],
        stretch: tuple[int, ...] = (),
    ) -> QTableWidget:
        """Table.

        Manages table operations and coordinates related state changes for the component.

        Args:
            headers (list[str]): The headers parameter.
            stretch (tuple[int, ...]): The stretch parameter.

        Returns:
            QTableWidget: Result of the operation.
        """
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setWordWrap(False)
        header = table.horizontalHeader()
        for column in stretch:
            if column < len(headers):
                header.setSectionResizeMode(
                    column, QHeaderView.ResizeMode.Stretch)
        return table

    # -- scanning ----------------------------------------------------------

    def start_scan(self, profile: str = "advanced") -> None:
        """Launch a DeviceDeepScanWorker with the chosen Nmap mode and profile.

        Manages start scan operations and coordinates related state changes for the component.

        Args:
            profile (str): The profile parameter.
        """
        if self._worker is not None:
            return
        modes = (
            None, ("connect", "version"), ("syn", "version"), ("ack",),
            ("syn", "version", "os"),
        )[self.nmap_check.currentIndex()]
        self._worker = DeviceDeepScanWorker(
            self._device,
            self._networks,
            profile=profile,
            nmap_modes=modes,
            catalog_path=self._catalog_path,
        )
        self._busy(True)
        self.status.setText(
            f"Starting {profile} audit of {self._device.ip}\u2026")
        self.win.run_worker(
            self._worker,
            self._on_scanned,
            self._on_failed,
            on_progress=self.status.setText,
        )

    def _confirm_all_ports(self) -> None:
        """Confirm a deep 1-65535 TCP scan before starting it.

        Manages confirm all ports operations and coordinates related state changes for the component.
        """
        answer = QMessageBox.question(
            self, "Scan all TCP ports on this device?",
            f"This checks TCP ports 1-65535 on {self._device.ip} only.\n\n"
            "It is read-only and cancellable, but it creates noticeably "
            "more traffic and can take several minutes. Run it only on a "
            "device you own or are authorized to assess.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.start_scan("deep")

    def _cancel(self) -> None:
        """Cancel.

        Manages cancel operations and coordinates related state changes for the component.
        """
        if self._worker is not None:
            self._worker.cancel()
            self.status.setText("Cancelling\u2026")

    def _busy(self, busy: bool) -> None:
        """Update the busy state indicators across the interface.

        Shows or hides loading indicators, adjusts cursor feedback, and toggles action button availability.

        Args:
            busy (bool): The busy parameter.
        """
        self._is_busy = busy
        self._refresh_action_states()

    def _refresh_action_states(self) -> None:
        """Derive every action from worker, evidence, and device capability.

        Manages refresh action states operations and coordinates related state changes for the component.
        """
        busy = self._is_busy
        for button in (
            self.scan_btn,
            self.allports_btn,
            self.ping_btn,
            self.copy_btn,
            self.save_btn,
        ):
            button.setEnabled(not busy)
        self.nmap_check.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        self.cancel_btn.setVisible(busy)
        self.progress.setVisible(busy)

        services = (self._payload or {}).get("services") or []
        actionable = {"http", "https", "ssh", "rdp"}
        self.open_btn.setEnabled(
            not busy
            and any(
                item.get("name") in actionable
                and item.get("state", "open") == "open"
                for item in services
            )
        )
        self.export_btn.setEnabled(
            not busy
            and self._has_completed_scan
            and self._payload is not None
        )

        try:
            from cortex_unified.system_tools.wake_on_lan import validate_mac

            validate_mac(self._device.mac)
            can_wake = True
            wake_tip = (
                "Send a Wake-on-LAN magic packet to this device's subnet "
                "broadcast. The device must have Wake-on-LAN enabled."
            )
        except ValueError as exc:
            can_wake = False
            wake_tip = f"Wake-on-LAN unavailable: {exc}"
        self.wake_btn.setEnabled(not busy and can_wake)
        self.wake_btn.setToolTip(wake_tip)

    def _on_failed(self, message: str) -> None:
        """Clear the worker, handle a pending close, and show the failure.

        Captures worker error messages, presents diagnostic feedback to the user, and resets interactive controls for retry.

        Args:
            message (str): Informational or progress status message.
        """
        self._worker = None
        self._busy(False)
        if self._close_pending:
            self._finish_pending_close()
            return
        self.status.setText(message)
        QMessageBox.warning(self, "Device scan failed", message)

    def _ping_only(self) -> None:
        """Launch a DevicePingWorker for a quick reachability check.

        Manages ping only operations and coordinates related state changes for the component.
        """
        if self._worker is not None:
            return
        self._worker = DevicePingWorker(self._device.ip, self._networks)
        self._busy(True)
        self.status.setText(f"Pinging {self._device.ip}\u2026")
        self.win.run_worker(
            self._worker,
            self._on_pinged,
            self._on_failed,
            on_progress=self.status.setText,
        )

    def _on_pinged(self, ping: dict) -> None:
        """Fold the ping result into the payload and describe the outcome.

        Manages on pinged operations and coordinates related state changes for the component.

        Args:
            ping (dict): The ping parameter.
        """
        self._worker = None
        self._busy(False)
        if self._close_pending:
            self._finish_pending_close()
            return
        if self._payload is not None:
            self._payload["ping"] = ping
            self._render(self._payload, scanned=self._has_completed_scan)
        if ping.get("cancelled"):
            message = "Ping cancelled."
        elif ping.get("reachable"):
            average = ping.get("avg_ms")
            message = (
                f"Device replied in {float(average):.0f} ms."
                if isinstance(average, (int, float))
                else "Device replied to ping."
            )
        else:
            message = "Device did not reply; a firewall may block ICMP."
        self.status.setText(message)

    def _finish_pending_close(self) -> None:
        """Close the window now that the worker has finished.

        Manages finish pending close operations and coordinates related state changes for the component.
        """
        self._close_pending = False
        self.close()

    # -- rendering ---------------------------------------------------------

    def _render_known(self) -> None:
        """Show what discovery already observed, before any focused scan.

        Manages render known operations and coordinates related state changes for the component.
        """
        device = self._device
        fingerprint = getattr(device, "fingerprint", None)
        payload = {
            "device": device.to_dict(),
            "services": [
                item.to_dict() if hasattr(item, "to_dict") else {}
                for item in getattr(device, "service_observations", ())
            ],
            "findings": [],
            "fingerprint": (
                fingerprint.to_dict() if fingerprint is not None
                and hasattr(fingerprint, "to_dict") else None),
            "ping": {},
            "reverse_dns": "",
            "profile": "discovery",
            "scanned_networks": list(self._networks),
            "nmap": {"used": False, "reason": "not requested"},
            "cancelled": False,
            "notes": [],
            "advertised_services": dict(getattr(device, "services", {}) or {}),
            "discovery_sources": sorted(getattr(device, "sources", ()) or ()),
            "identity_key": "",
            "metadata": None,
            "lifetime": None,
            "trends": [],
            "history_error": "",
        }
        self._payload = payload
        self._render(payload, scanned=False)
        self._load_metadata()

    def _on_scanned(self, payload) -> None:
        """Store the scan payload, render it, and summarize the results.

        Manages on scanned operations and coordinates related state changes for the component.

        Args:
            payload: The payload parameter.
        """
        self._worker = None
        self._has_completed_scan = True
        self._busy(False)
        if self._close_pending:
            self._finish_pending_close()
            return
        self._payload = payload
        self._render(payload, scanned=True)
        summary = (
            f"{len(payload['services'])} service(s) and "
            f"{len(payload['findings'])} evidence-backed finding(s) on "
            f"{self._device.ip}")
        if payload.get("cancelled"):
            summary += " (cancelled early - results may be incomplete)"
        self.status.setText(summary)

    def _render(self, payload: dict, scanned: bool) -> None:
        """Render.

        Manages render operations and coordinates related state changes for the component.

        Args:
            payload (dict): The payload parameter.
            scanned (bool): The scanned parameter.
        """
        services = payload.get("services") or []
        findings = payload.get("findings") or []
        self._render_cards(payload, services, findings, scanned)
        self._render_overview(payload, services, findings, scanned)
        self._render_services(services)
        self._render_findings(findings, scanned)
        self._render_identity(payload.get("fingerprint"))
        self._render_discovery(payload)
        self._render_history(payload)
        self.raw_view.setPlainText(
            json.dumps(payload, indent=2, ensure_ascii=False))
        self._refresh_action_states()

    def _render_cards(self, payload, services, findings, scanned) -> None:
        """Update the stat cards for services, findings, severity, latency, and identity.

        Manages render cards operations and coordinates related state changes for the component.

        Args:
            payload: The payload parameter.
            services: The services parameter.
            findings: The findings parameter.
            scanned: The scanned parameter.
        """
        open_services = [
            item for item in services if item.get("state", "open") == "open"]
        self.card_ports.set_value(str(len(open_services)))
        self.card_findings.set_value(str(len(findings)) if scanned else _DASH)
        if findings:
            self.card_risk.set_value(findings[0]["severity"].upper())
        else:
            self.card_risk.set_value("NONE" if scanned else _DASH)
        ping = payload.get("ping") or {}
        if ping:
            average = ping.get("avg_ms")
            self.card_latency.set_value(
                f"{average:.0f} ms" if ping.get("reachable") and average
                else ("Replied" if ping.get("reachable") else "No ICMP reply"))
        else:
            self.card_latency.set_value(_DASH)
        fingerprint = payload.get("fingerprint") or {}
        confidence = fingerprint.get("confidence")
        self.card_identity.set_value(
            f"{float(confidence) * 100:.0f}%" if confidence else _DASH)

    def _render_overview(self, payload, services, findings, scanned) -> None:
        """Rebuild the overview grid rows and the evidence caveat.

        Manages render overview operations and coordinates related state changes for the component.

        Args:
            payload: The payload parameter.
            services: The services parameter.
            findings: The findings parameter.
            scanned: The scanned parameter.
        """
        while self.overview_grid.count():
            item = self.overview_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        device = payload.get("device") or {}
        fingerprint = payload.get("fingerprint") or {}
        ping = payload.get("ping") or {}
        metadata = payload.get("metadata") or {}
        nmap = payload.get("nmap") or {}
        open_ports = ", ".join(
            str(port) for port in device.get("open_ports", ())
        )
        rows = [
            ("Name", device.get("label", "")),
            ("Custom name", metadata.get("custom_name") or _DASH),
            ("Trust", (metadata.get("trust_state") or "unknown").title()),
            ("IP address", device.get("ip", "")),
            ("MAC address", device.get("mac") or "not observed"),
            ("Vendor (IEEE)", device.get("vendor") or "unknown"),
            ("Hostname", device.get("hostname") or _DASH),
            ("Reverse DNS", payload.get("reverse_dns") or _DASH),
            ("Device type", device.get("kind", "")),
            ("OS family", fingerprint.get("os_family", "unknown")),
            ("Product / version", " ".join(filter(None, (
                fingerprint.get("product", ""),
                fingerprint.get("version", "")))) or _DASH),
            ("Open TCP ports", open_ports or "none observed"),
            ("Discovered by", device.get("evidence", "")),
            ("Reachability", (
                "replied to ping" if ping.get("reachable")
                else "no ICMP reply (a firewall can block ping)"
                if ping else _DASH)),
            ("Audit profile", payload.get("profile", "")),
            ("Authorized scope", ", ".join(
                payload.get("scanned_networks", ()))),
            ("Optional Nmap", (
                f"used ({', '.join(nmap.get('modes', ()))})"
                if nmap.get("used")
                else f"not used - {nmap.get('reason', '')}"
            )),
        ]
        for row, (label, value) in enumerate(rows):
            key = QLabel(label)
            key.setObjectName("Muted")
            val = QLabel(str(value) or _DASH)
            val.setWordWrap(True)
            val.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse)
            self.overview_grid.addWidget(
                key,
                row,
                0,
                Qt.AlignmentFlag.AlignTop,
            )
            self.overview_grid.addWidget(val, row, 1)
        self.overview_grid.setColumnStretch(1, 1)
        caveat = QLabel(
            "Findings come only from what this device actually answered. "
            "No finding does not prove the device is free of vulnerabilities, "
            "and a version match is a potential advisory match, not a "
            "confirmed exploitable flaw."
            if scanned else
            "This is what discovery already saw. Press Deep Scan Device for "
            "a full per-device service and security audit.")
        caveat.setObjectName("Muted")
        caveat.setWordWrap(True)
        self.overview_grid.addWidget(caveat, len(rows), 0, 1, 2)

    def _render_services(self, services) -> None:
        """Fill the ports/services table sorted by port and transport.

        Manages render services operations and coordinates related state changes for the component.

        Args:
            services: The services parameter.
        """
        self.services_tbl.setRowCount(len(services))
        for row, item in enumerate(sorted(
                services, key=lambda entry: (
                    entry.get("port", 0), entry.get("transport", "")))):
            evidence = ", ".join(
                str(text)
                for text in (item.get("metadata") or {}).get(
                    "evidence",
                    (),
                )
            )
            latency = item.get("latency_ms")
            values = (
                str(item.get("port", "")),
                str(item.get("transport", "")).upper(),
                item.get("name", ""),
                item.get("state", ""),
                item.get("product") or _DASH,
                item.get("version") or _DASH,
                (
                    f"{latency:.1f} ms"
                    if isinstance(latency, (int, float))
                    else _DASH
                ),
                f"{float(item.get('confidence', 0)) * 100:.0f}%",
                item.get("source", ""),
                evidence or item.get("banner", "")[:160] or _DASH,
            )
            for column, value in enumerate(values):
                self.services_tbl.setItem(
                    row, column, QTableWidgetItem(str(value)))
        self.services_tbl.resizeColumnsToContents()

    def _render_findings(self, findings, scanned) -> None:
        """Fill the security findings table with severity badges and remediation.

        Manages render findings operations and coordinates related state changes for the component.

        Args:
            findings: The findings parameter.
            scanned: The scanned parameter.
        """
        self.findings_tbl.setRowCount(len(findings))
        for row, item in enumerate(findings):
            severity = str(item.get("severity", "info"))
            badge = Badge(
                self.p,
                _severity_badge_kind(severity),
                severity.upper(),
            )
            self.findings_tbl.setCellWidget(row, 0, badge)
            values = (
                item.get("title", ""),
                str(item.get("port") or _DASH),
                item.get("detail", ""),
                item.get("remediation", ""),
                ", ".join(item.get("cve_ids", ())) or _DASH,
                f"{float(item.get('confidence', 0)) * 100:.0f}%",
                "; ".join(str(text) for text in item.get("evidence", ())),
            )
            for offset, value in enumerate(values, start=1):
                self.findings_tbl.setItem(
                    row, offset, QTableWidgetItem(str(value)))
        if not findings:
            self.findings_tbl.setRowCount(1)
            message = (
                "No evidence-backed finding was produced for this device."
                if scanned else
                "Run Deep Scan Device to audit this host's services.")
            self.findings_tbl.setItem(0, 1, QTableWidgetItem(message))
        self.findings_tbl.resizeColumnsToContents()

    def _render_identity(self, fingerprint) -> None:
        """Fill the identity evidence table from the fingerprint.

        Manages render identity operations and coordinates related state changes for the component.

        Args:
            fingerprint: The fingerprint parameter.
        """
        evidence = (fingerprint or {}).get("evidence", [])
        self.identity_tbl.setRowCount(len(evidence))
        for row, item in enumerate(evidence):
            values = (
                item.get("source", ""),
                item.get("value", ""),
                item.get("strength", ""),
                str(item.get("weight", "")),
                item.get("detail", ""),
            )
            for column, value in enumerate(values):
                self.identity_tbl.setItem(
                    row, column, QTableWidgetItem(str(value)))
        self.identity_tbl.resizeColumnsToContents()

    def _render_discovery(self, payload) -> None:
        """Write discovery methods and self-advertised services to the Discovery tab.

        Manages render discovery operations and coordinates related state changes for the component.

        Args:
            payload: The payload parameter.
        """
        lines = [
            "HOW THIS DEVICE WAS FOUND",
            "  " + (payload.get("device") or {}).get("evidence", ""),
            "",
            "DISCOVERY METHODS THAT SAW IT",
        ]
        lines.extend(
            f"  \u2022 {source}"
            for source in payload.get("discovery_sources", ())
        )
        advertised = payload.get("advertised_services") or {}
        lines.extend(["", "WHAT THE DEVICE ADVERTISED ABOUT ITSELF"])
        if advertised:
            lines.extend(
                f"  \u2022 {key}: {value}"
                for key, value in sorted(advertised.items())
            )
        else:
            lines.append(
                "  (nothing self-advertised over "
                "mDNS/SSDP/WS-Discovery)"
            )
        notes = payload.get("notes") or []
        if notes:
            lines.extend(["", "NOTES"])
            lines.extend(f"  \u2022 {note}" for note in notes)
        self.discovery_view.setPlainText("\n".join(lines))

    def _render_history(self, payload) -> None:
        """Write lifetime, history, and exposure-trend lines to the History tab.

        Manages render history operations and coordinates related state changes for the component.

        Args:
            payload: The payload parameter.
        """
        lifetime = payload.get("lifetime") or {}
        lines = ["LOCAL HISTORY FOR THIS DEVICE"]
        if payload.get("identity_key"):
            lines.append(f"  Identity key: {payload['identity_key']}")
        if lifetime:
            lines.extend([
                f"  First seen: {lifetime.get('first_seen', '')}",
                f"  Last seen:  {lifetime.get('last_seen', '')}",
                (
                    "  Identity confidence: "
                    f"{lifetime.get('identity_confidence', '')}"
                ),
            ])
        else:
            lines.append(
                "  No retained history yet. History is written when a full "
                "network scan runs.")
        if payload.get("history_error"):
            lines.append(f"  History unavailable: {payload['history_error']}")
        trends = payload.get("trends") or []
        if trends:
            lines.extend([
                "",
                "NETWORK-WIDE EXPOSURE TREND (most recent last)",
                "  observed_at | devices | services | findings | risk",
            ])
            lines.extend(
                f"  {row['observed_at']} | {row['device_count']} | "
                f"{row['service_count']} | {row['finding_count']} | "
                f"{row['risk_score']}"
                for row in trends)
        lines.extend([
            "",
            "Identity is best-effort: DHCP can move addresses and privacy "
            "features randomize MAC addresses.",
        ])
        self.history_view.setPlainText("\n".join(lines))

    # -- per-device actions ------------------------------------------------

    def _load_metadata(self) -> None:
        """Load saved labels and notes for the device into the form and overview.

        Manages load metadata operations and coordinates related state changes for the component.
        """
        try:
            from cortex_unified.system_tools.network_inventory import (
                NetworkInventory,
            )
            with NetworkInventory() as inventory:
                metadata = inventory.get_metadata(self._device)
        except (OSError, ValueError, RuntimeError):
            return
        if metadata is None:
            return
        self.name_input.setText(metadata.custom_name)
        self.trust_combo.setCurrentText(metadata.trust_state)
        self.tags_input.setText(", ".join(metadata.tags))
        self.notes_input.setText(metadata.notes)
        if self._payload is not None:
            self._payload["metadata"] = metadata.to_dict()
            self._render_overview(
                self._payload, self._payload.get("services") or [],
                self._payload.get("findings") or [], False)

    def _save_metadata(self) -> None:
        """Save the edited name, trust, tags, and notes to the inventory.

        Manages save metadata operations and coordinates related state changes for the component.
        """
        try:
            from cortex_unified.system_tools.network_inventory import (
                NetworkInventory,
            )
            with NetworkInventory() as inventory:
                metadata = inventory.set_metadata(
                    self._device,
                    custom_name=self.name_input.text(),
                    trust_state=self.trust_combo.currentText(),
                    tags=self.tags_input.text(),
                    notes=self.notes_input.text())
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Details not saved", str(exc))
            return
        self.status.setText(
            f"Saved device details for {metadata.identity_key}")
        if self._payload is not None:
            self._payload["metadata"] = metadata.to_dict()
            self._render_overview(
                self._payload, self._payload.get("services") or [],
                self._payload.get("findings") or [], False)

    def _wake(self) -> None:
        """Wake.

        Manages wake operations and coordinates related state changes for the component.
        """
        import ipaddress

        try:
            from cortex_unified.system_tools.wake_on_lan import (
                send_magic_packet,
            )

            address = ipaddress.IPv4Address(self._device.ip)
            network = next(
                ipaddress.IPv4Network(value, strict=False)
                for value in self._networks
                if address in ipaddress.IPv4Network(value, strict=False))
            send_magic_packet(
                self._device.mac,
                str(network.broadcast_address),
                self._networks,
            )
        except (StopIteration, OSError, ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Wake-on-LAN failed", str(exc))
            return
        self.status.setText(
            "Wake-on-LAN magic packet sent. The device only wakes if it has "
            "Wake-on-LAN enabled in firmware and the OS.")

    def _open_service(self) -> None:
        """Open the best http/https/ssh/rdp service in the system handler.

        Manages open service operations and coordinates related state changes for the component.
        """
        services = (self._payload or {}).get("services") or []
        priority = {"https": 0, "http": 1, "ssh": 2, "rdp": 3}
        candidates = [
            item for item in services
            if item.get("name") in priority
            and item.get("state", "open") == "open"
        ]
        if not candidates:
            return
        service = min(candidates, key=lambda item: priority[item["name"]])
        name, port = service["name"], service.get("port")
        if name in {"http", "https"}:
            url = f"{name}://{self._device.ip}:{port}/"
        elif name == "ssh":
            url = f"ssh://{self._device.ip}:{port}"
        else:
            url = f"rdp://{self._device.ip}:{port}"
        QDesktopServices.openUrl(QUrl(url))
        self.status.setText(f"Asked the system to open {url}")

    def _copy_identity(self) -> None:
        """Copy the device IP and MAC to the clipboard.

        Manages copy identity operations and coordinates related state changes for the component.
        """
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            return
        clipboard.setText(
            f"{self._device.ip}\t{self._device.mac or 'no MAC observed'}")
        self.status.setText("Copied the IP and MAC address to the clipboard.")

    def _export(self) -> None:
        """Export.

        Manages export operations and coordinates related state changes for the component.
        """
        payload = self._payload
        if payload is None:
            return
        safe_ip = self._device.ip.replace(".", "-")
        path, selected = QFileDialog.getSaveFileName(
            self, "Export device report", f"device-{safe_ip}.json",
            "JSON report (*.json);;Printable HTML report (*.html);;"
            "PDF report (*.pdf)")
        if not path:
            return
        from pathlib import Path

        target = Path(path)
        suffix = target.suffix.lower()
        if suffix not in {".json", ".html", ".pdf"}:
            suffix = (
                ".pdf" if "PDF" in selected
                else ".html" if "HTML" in selected else ".json")
            target = target.with_suffix(suffix)
        try:
            if suffix == ".json":
                target.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False),
                    encoding="utf-8")
            else:
                document = self._html_report(payload)
                if suffix == ".pdf":
                    writer = QPdfWriter(str(target))
                    writer.setTitle(f"Cortex device report {self._device.ip}")
                    view = QTextDocument()
                    view.setHtml(document)
                    view.print_(writer)
                else:
                    target.write_text(document, encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
            return
        self.status.setText(f"Device report exported to {target}")

    def _html_report(self, payload: dict) -> str:
        """Build the printable HTML report for the payload.

        Manages html report operations and coordinates related state changes for the component.

        Args:
            payload (dict): The payload parameter.

        Returns:
            str: Formatted string or path.
        """
        device = payload.get("device") or {}
        rows = "".join(
            "<tr>"
            + "".join(
                f"<td>{html.escape(str(value))}</td>"
                for value in (
                    item.get("port", ""),
                    item.get("transport", ""),
                    item.get("name", ""),
                    item.get("state", ""),
                    item.get("product", ""),
                    item.get("version", ""),
                )
            )
            + "</tr>"
            for item in payload.get("services", ())
        )
        findings = "".join(
            f"<li><strong>{html.escape(str(item.get('severity', '')).upper())}"
            f"</strong> {html.escape(item.get('title', ''))} \u2014 "
            f"{html.escape(item.get('remediation', ''))}</li>"
            for item in payload.get("findings", ())
        )
        profile = html.escape(str(payload.get("profile", "")))
        service_rows = rows or "<tr><td colspan=6>None observed</td></tr>"
        finding_rows = findings or "<li>None observed</li>"
        return (
            "<!doctype html><meta charset='utf-8'><title>Cortex Device Report"
            "</title><style>body{font:14px Segoe UI,sans-serif;"
            "max-width:1000px;margin:28px auto;color:#1f2937}"
            "table{border-collapse:collapse;width:100%}"
            "th,td{border:1px solid #d1d5db;padding:6px;text-align:left}"
            "th{background:#eef2ff}</style>"
            f"<h1>{html.escape(device.get('label', ''))}</h1>"
            f"<p>{html.escape(device.get('ip', ''))} &middot; "
            f"{html.escape(device.get('mac') or 'no MAC observed')} "
            "&middot; "
            f"{html.escape(device.get('vendor') or 'vendor unknown')} "
            "&middot; "
            f"{html.escape(device.get('kind', ''))}</p>"
            f"<p>Audit profile: {profile}. Evidence-only report; absence of "
            "a finding does not prove absence of a vulnerability.</p>"
            "<h2>Services</h2><table><tr><th>Port</th><th>Proto</th>"
            "<th>Service</th><th>State</th><th>Product</th><th>Version</th>"
            f"</tr>{service_rows}</table>"
            f"<h2>Findings</h2><ul>{finding_rows}</ul>"
        )

    # -- lifecycle ---------------------------------------------------------

    def closeEvent(self, event):  # noqa: N802 - Qt signature
        """Handle the window or widget close event.

        Performs graceful shutdown, releases active workers and system hooks, persists window geometry, and accepts the close event.

        Args:
            event: The Qt event object.
        """
        if self._worker is not None:
            self._close_pending = True
            self._worker.cancel()
            self.status.setText("Cancelling before closing\u2026")
            self.hide()
            event.ignore()
            return
        self.closed.emit(self)
        super().closeEvent(event)


__all__ = ["DeviceDeepScanWorker", "DeviceDetailWindow"]
