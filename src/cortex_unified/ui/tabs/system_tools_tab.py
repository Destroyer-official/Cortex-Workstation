"""Tab for system tools tab in Cortex Cleaner GUI."""

import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QMessageBox,
    QFileDialog, QTextEdit, QSplitter
)
from PySide6.QtCore import QThread, Signal, Qt

from .base_tab import BaseTab

from cortex_unified.ui.tabs.process_analyzer_tab import ProcessAnalyzerTab
from cortex_unified.ui.tabs.startup_manager_tab import StartupManagerTab
try:
    from cortex_unified.ui.tabs.registry_cleaner_tab import RegistryCleanerTab
    HAS_REGISTRY_CLEANER = True
except ImportError:
    HAS_REGISTRY_CLEANER = False


class LanScanWorker(QThread):
    """Background worker for LAN ARP/OUI subnet scanning."""
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        """Scan ARP cache and resolve OUI vendors off the main thread."""
        try:
            from cortex_unified.system_tools.lan_scanner import LanScanner
            scanner = LanScanner()
            devices = scanner.scan()
            self.finished.emit(devices)
        except Exception as exc:
            self.error.emit(str(exc))


class WanAuditWorker(QThread):
    """Background worker for WAN connectivity, gateway, and IGD auditing."""
    finished = Signal(object)
    error = Signal(str)

    def run(self):
        """Execute WAN audit off the main thread."""
        try:
            from cortex_unified.system_tools.wan_audit import WanAuditor
            auditor = WanAuditor()
            report = auditor.audit()
            self.finished.emit(report)
        except Exception as exc:
            self.error.emit(str(exc))


class SystemToolsTab(BaseTab):
    """Container Tab mapping System Tools sub-tabs dynamically."""

    def __init__(self, config, logger, safety_manager):
        """Initialize the container tab via the base class."""
        self._last_lan_devices = []
        super().__init__(config, logger, safety_manager)

    def setup_ui(self):
        """Create the system tools tab natively injecting components.

        Fills an inner QTabWidget with StartupManagerTab, ProcessAnalyzerTab,
        (if importable) RegistryCleanerTab, and Network Tools as sub-tabs.
        """
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        tools_tab_widget = QTabWidget()
        layout.addWidget(tools_tab_widget)
        
        # Instantiate natively directly into view rather than faking creation
        startup_tab = StartupManagerTab(self.config, self.logger, self.safety_manager)
        tools_tab_widget.addTab(startup_tab, 'Startup Manager')
        
        process_tab = ProcessAnalyzerTab(self.config, self.logger, self.safety_manager)
        tools_tab_widget.addTab(process_tab, 'Process Analyzer')
        
        if HAS_REGISTRY_CLEANER:
            registry_tab = RegistryCleanerTab(self.config, self.logger, self.safety_manager)
            tools_tab_widget.addTab(registry_tab, 'Registry Cleaner')

        network_tab = self.create_network_tools_subtab()
        tools_tab_widget.addTab(network_tab, 'Network Tools')

    def create_network_tools_subtab(self) -> QWidget:
        """Create the integrated Network Tools sub-tab.

        Houses LAN ARP scanning with IEEE OUI resolution, WAN gateway auditing,
        persistent SQLite Network Inventory with CSV export, and remote share access.
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        # Header controls
        controls = QHBoxLayout()
        self.btn_lan_scan = QPushButton("🔍 Scan Local LAN")
        self.btn_lan_scan.setToolTip("Discover active LAN devices via OS ARP cache and resolve hardware OUI vendors.")
        self.btn_lan_scan.clicked.connect(self._run_lan_scan)
        controls.addWidget(self.btn_lan_scan)

        self.btn_wan_audit = QPushButton("🌐 Audit WAN / Gateway")
        self.btn_wan_audit.setToolTip("Inspect public IP classification, default gateway, DNS servers, and UPnP/IGD state.")
        self.btn_wan_audit.clicked.connect(self._run_wan_audit)
        controls.addWidget(self.btn_wan_audit)

        self.btn_export_inventory = QPushButton("💾 Export Inventory (CSV)")
        self.btn_export_inventory.setToolTip("Export snapshot of discovered devices into NetworkInventory SQLite and CSV.")
        self.btn_export_inventory.clicked.connect(self._export_network_inventory)
        controls.addWidget(self.btn_export_inventory)

        self.btn_remote_server = QPushButton("🔗 Connect Remote Share")
        self.btn_remote_server.setToolTip("Open Remote Server Browser for SMB, FTP, SFTP, and WebDAV endpoints.")
        self.btn_remote_server.clicked.connect(self._open_remote_server)
        controls.addWidget(self.btn_remote_server)

        controls.addStretch()
        layout.addLayout(controls)

        # Progress bar
        self.net_progress = QProgressBar()
        self.net_progress.setRange(0, 0)
        self.net_progress.setVisible(False)
        layout.addWidget(self.net_progress)

        # Status summary label
        self.net_summary_lbl = QLabel("Click 'Scan Local LAN' or 'Audit WAN / Gateway' to examine network status.")
        self.net_summary_lbl.setStyleSheet("font-size: 12px; color: #aaa; padding: 4px;")
        layout.addWidget(self.net_summary_lbl)

        # Splitter with LAN Devices Table and WAN Audit / Diagnostics Pane
        splitter = QSplitter(Qt.Orientation.Vertical)

        # LAN Table
        self.lan_table = QTableWidget(0, 4)
        self.lan_table.setHorizontalHeaderLabels(["IP Address", "MAC Address", "Type", "Vendor (IEEE OUI)"])
        self.lan_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.lan_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.lan_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.lan_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.lan_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.lan_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.lan_table.setAlternatingRowColors(True)
        splitter.addWidget(self.lan_table)

        # WAN / Diagnostics detail text
        self.net_diag_text = QTextEdit()
        self.net_diag_text.setReadOnly(True)
        self.net_diag_text.setPlaceholderText("Network diagnostics and WAN audit details will appear here...")
        self.net_diag_text.setMaximumHeight(180)
        splitter.addWidget(self.net_diag_text)

        layout.addWidget(splitter, 1)
        return tab

    def _run_lan_scan(self):
        """Execute background LAN scan using LanScanner."""
        self.net_progress.setVisible(True)
        self.btn_lan_scan.setEnabled(False)
        self.net_summary_lbl.setText("Scanning local network ARP table and resolving OUI vendors...")

        worker = LanScanWorker()
        self.add_worker_thread(worker)

        def on_done(devices):
            """Handle LAN discovery completion."""
            self.net_progress.setVisible(False)
            self.btn_lan_scan.setEnabled(True)
            self.remove_worker_thread(worker)
            worker.deleteLater()
            self._last_lan_devices = devices
            self.lan_table.setRowCount(len(devices))
            for i, dev in enumerate(devices):
                self.lan_table.setItem(i, 0, QTableWidgetItem(dev.ip))
                self.lan_table.setItem(i, 1, QTableWidgetItem(dev.mac))
                self.lan_table.setItem(i, 2, QTableWidgetItem(dev.kind))
                self.lan_table.setItem(i, 3, QTableWidgetItem(dev.vendor or "Unidentified / Private"))
            self.net_summary_lbl.setText(f"Discovered {len(devices)} active devices on local subnet.")

            # Record in NetworkInventory
            try:
                from cortex_unified.system_tools.network_inventory import NetworkInventory, InventoryDevice
                inv = NetworkInventory()
                inv_devices = [
                    InventoryDevice(ip=dev.ip, mac=dev.mac, hostname="", vendor=dev.vendor)
                    for dev in devices
                ]
                inv.record_snapshot(inv_devices)
            except Exception as e:
                self.logger.debug(f"Could not persist LAN snapshot in NetworkInventory: {e}")

        def on_err(msg):
            """Handle LAN scan error."""
            self.net_progress.setVisible(False)
            self.btn_lan_scan.setEnabled(True)
            self.remove_worker_thread(worker)
            worker.deleteLater()
            self.net_summary_lbl.setText(f"LAN scan error: {msg}")
            QMessageBox.critical(self, "Scan Error", f"LAN scan failed:\n{msg}")

        worker.finished.connect(on_done)
        worker.error.connect(on_err)
        worker.start()

    def _run_wan_audit(self):
        """Execute background WAN audit using WanAuditor."""
        self.net_progress.setVisible(True)
        self.btn_wan_audit.setEnabled(False)
        self.net_summary_lbl.setText("Auditing WAN gateway, external IP classification, and UPnP...")

        worker = WanAuditWorker()
        self.add_worker_thread(worker)

        def on_done(report):
            """Handle WAN audit completion."""
            self.net_progress.setVisible(False)
            self.btn_wan_audit.setEnabled(True)
            self.remove_worker_thread(worker)
            worker.deleteLater()
            
            ext_ip = getattr(report, "external_ip", "") or "Not detected"
            gateway = getattr(report, "gateway", "") or "Default"
            dns_list = ", ".join(getattr(report, "dns_servers", [])) or "System default"
            igd_status = "Found (Active UPnP)" if getattr(report, "igd_found", False) else "None / Filtered"
            duration = getattr(report, "duration_seconds", 0.0)

            diag_lines = [
                f"=== WAN & Gateway Audit Report ===",
                f"External IP:       {ext_ip}",
                f"Default Gateway:   {gateway}",
                f"DNS Servers:       {dns_list}",
                f"UPnP / IGD State:  {igd_status}",
                f"Audit Duration:    {duration:.2f}s",
            ]
            warnings = getattr(report, "warnings", [])
            if warnings:
                diag_lines.append("\nWarnings / Notes:")
                for w in warnings:
                    diag_lines.append(f"  • {w}")

            self.net_diag_text.setPlainText("\n".join(diag_lines))
            self.net_summary_lbl.setText(f"WAN audit complete: Gateway {gateway} | Ext IP {ext_ip}")

        def on_err(msg):
            """Handle WAN audit error."""
            self.net_progress.setVisible(False)
            self.btn_wan_audit.setEnabled(True)
            self.remove_worker_thread(worker)
            worker.deleteLater()
            self.net_summary_lbl.setText(f"WAN audit error: {msg}")
            QMessageBox.critical(self, "Audit Error", f"WAN audit failed:\n{msg}")

        worker.finished.connect(on_done)
        worker.error.connect(on_err)
        worker.start()

    def _export_network_inventory(self):
        """Export NetworkInventory records to a CSV spreadsheet."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Network Inventory", "network_inventory.csv", "CSV Files (*.csv)"
        )
        if not file_path:
            return
        try:
            from cortex_unified.system_tools.network_inventory import NetworkInventory, InventoryDevice
            inv = NetworkInventory()
            # If we have recent scan devices, ensure snapshot is saved
            if self._last_lan_devices:
                inv_devices = [
                    InventoryDevice(ip=dev.ip, mac=dev.mac, hostname="", vendor=dev.vendor)
                    for dev in self._last_lan_devices
                ]
                inv.record_snapshot(inv_devices)
            count = inv.export_inventory_csv(file_path)
            QMessageBox.information(
                self, "Export Complete",
                f"Network inventory exported to:\n{file_path}\nTotal devices exported: {count}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", f"Failed to export inventory CSV:\n{exc}")

    def _open_remote_server(self):
        """Open the interactive Remote Server Browser dialog."""
        try:
            from cortex_unified.ui.premium.network_pages import RemoteServerDialog
            dlg = RemoteServerDialog(self)
            dlg.exec()
        except Exception as exc:
            QMessageBox.critical(self, "Remote Server Error", f"Could not launch Remote Server dialog:\n{exc}")

