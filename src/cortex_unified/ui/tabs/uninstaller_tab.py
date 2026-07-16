"""Deep Uninstaller tab — safe app removal + residual cleanup.

Features:
  - Threaded app list loading with search/filter
  - Estimated size display from registry
  - Safe uninstallation via native UninstallString
  - Threaded residual scanning with strict matching
  - Bulk residual cleanup with confirmation
"""

import os
import shutil
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QMessageBox, QLineEdit, QSplitter, QProgressBar,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont

from .base_tab import BaseTab
from cortex_unified.system_tools.app_uninstaller import AppUninstaller
from cortex_unified.analyzers.residual_hunter import ResidualHunter


# ──────────────────────────────────────────────────────────────────────
# Workers
# ──────────────────────────────────────────────────────────────────────

class AppListWorker(QObject):
    finished = Signal(list)
    def run(self):
        self.finished.emit(AppUninstaller().get_installed_apps())


class ResidualScanWorker(QObject):
    finished = Signal(list)
    def __init__(self, app_name: str, publisher: str):
        super().__init__()
        self._app_name = app_name
        self._publisher = publisher
    def run(self):
        self.finished.emit(ResidualHunter().scan_for_app(self._app_name, self._publisher))


# ──────────────────────────────────────────────────────────────────────
# Uninstaller Tab
# ──────────────────────────────────────────────────────────────────────

class UninstallerTab(BaseTab):
    """Deep Uninstaller with residual hunting."""

    def __init__(self, config, logger, safety_manager, parent=None):
        self.uninstaller = AppUninstaller()
        self.all_apps = []
        self._app_thread = None
        self._app_worker = None
        self._res_thread = None
        self._res_worker = None
        super().__init__(config, logger, safety_manager)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # Header
        header = QLabel("Deep Uninstaller & Residual Hunter")
        hf = QFont(); hf.setPointSize(18); hf.setBold(True)
        header.setFont(hf)
        main_layout.addWidget(header)

        desc = QLabel("Safely uninstall applications and remove leftover files from AppData, ProgramData, and Program Files.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray;")
        main_layout.addWidget(desc)

        # Controls bar
        ctrl = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search installed applications…")
        self.search_input.textChanged.connect(self._filter_apps)
        ctrl.addWidget(self.search_input)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load_apps)
        ctrl.addWidget(self.refresh_btn)

        self.lbl_count = QLabel("")
        ctrl.addWidget(self.lbl_count)
        main_layout.addLayout(ctrl)

        # Loading indicator
        self.load_progress = QProgressBar()
        self.load_progress.setRange(0, 0)
        self.load_progress.setVisible(False)
        main_layout.addWidget(self.load_progress)

        # Splitter: table on left, details on right
        splitter = QSplitter(Qt.Horizontal)

        # App table
        self.app_table = QTableWidget(0, 4)
        self.app_table.setHorizontalHeaderLabels(["Name", "Publisher", "Version", "Size"])
        self.app_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.app_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.app_table.setSelectionMode(QTableWidget.SingleSelection)
        self.app_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.app_table.itemSelectionChanged.connect(self._on_app_selected)
        splitter.addWidget(self.app_table)

        # Details panel
        details = QGroupBox("Application Details")
        dl = QVBoxLayout(details)

        self.lbl_name = QLabel("Name: —")
        self.lbl_pub = QLabel("Publisher: —")
        self.lbl_ver = QLabel("Version: —")
        self.lbl_loc = QLabel("Install path: —")
        self.lbl_loc.setWordWrap(True)
        self.lbl_reg = QLabel("Registry: —")
        self.lbl_reg.setWordWrap(True)
        for w in (self.lbl_name, self.lbl_pub, self.lbl_ver, self.lbl_loc, self.lbl_reg):
            dl.addWidget(w)

        self.btn_uninstall = QPushButton("Run Official Uninstaller")
        self.btn_uninstall.setStyleSheet(
            "background-color: #F44336; color: white; padding: 10px; font-weight: bold;"
        )
        self.btn_uninstall.setEnabled(False)
        self.btn_uninstall.clicked.connect(self._run_uninstall)
        dl.addWidget(self.btn_uninstall)

        dl.addWidget(QLabel(""))  # spacer

        self.btn_residuals = QPushButton("Scan for Leftover Files")
        self.btn_residuals.setEnabled(False)
        self.btn_residuals.clicked.connect(self._scan_residuals)
        dl.addWidget(self.btn_residuals)

        self.residual_progress = QProgressBar()
        self.residual_progress.setRange(0, 0)
        self.residual_progress.setVisible(False)
        dl.addWidget(self.residual_progress)

        self.res_table = QTableWidget(0, 2)
        self.res_table.setHorizontalHeaderLabels(["Leftover Path", "Size"])
        self.res_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.res_table.setSelectionMode(QTableWidget.MultiSelection)
        self.res_table.setSelectionBehavior(QTableWidget.SelectRows)
        dl.addWidget(QLabel("Residual files/folders:"))
        dl.addWidget(self.res_table)

        self.btn_clean = QPushButton("Delete Selected Residuals")
        self.btn_clean.setStyleSheet(
            "background-color: #FF9800; color: white; padding: 8px; font-weight: bold;"
        )
        self.btn_clean.setEnabled(False)
        self.btn_clean.clicked.connect(self._clean_residuals)
        dl.addWidget(self.btn_clean)

        splitter.addWidget(details)
        splitter.setSizes([550, 450])
        main_layout.addWidget(splitter)

        # Kick off initial load
        self._load_apps()

    def setup_tooltips(self):
        self.btn_uninstall.setToolTip("Launch the application's official uninstaller")
        self.btn_residuals.setToolTip("Search for orphaned folders left behind by this application")

    # ── App Loading ───────────────────────────────────────────────────

    def _load_apps(self):
        self.refresh_btn.setEnabled(False)
        self.app_table.setRowCount(0)
        self.search_input.clear()
        self.load_progress.setVisible(True)

        self._app_thread = QThread(self)
        self._app_worker = AppListWorker()
        self._app_worker.moveToThread(self._app_thread)

        self._app_thread.started.connect(self._app_worker.run)
        self._app_worker.finished.connect(self._on_apps_loaded)
        self._app_worker.finished.connect(self._app_thread.quit)
        self._app_worker.finished.connect(self._app_worker.deleteLater)
        self._app_thread.finished.connect(self._app_thread.deleteLater)

        self._app_thread.start()

    def _on_apps_loaded(self, apps):
        self.all_apps = apps
        self._populate_table(apps)
        self.refresh_btn.setEnabled(True)
        self.load_progress.setVisible(False)
        self.lbl_count.setText(f"{len(apps)} apps found")

    def _populate_table(self, apps):
        self.app_table.setRowCount(len(apps))
        for row, app in enumerate(apps):
            name_item = QTableWidgetItem(app.get("name", "Unknown"))
            name_item.setData(Qt.UserRole, app)  # store full dict

            pub_item = QTableWidgetItem(app.get("publisher", ""))
            ver_item = QTableWidgetItem(app.get("display_version", ""))

            est_kb = app.get("estimated_size_kb", 0)
            if isinstance(est_kb, (int, float)) and est_kb > 0:
                size_mb = est_kb / 1024.0
                if size_mb > 1024:
                    size_text = f"{size_mb / 1024:.1f} GB"
                else:
                    size_text = f"{size_mb:.1f} MB"
            else:
                size_text = ""
            size_item = QTableWidgetItem(size_text)

            self.app_table.setItem(row, 0, name_item)
            self.app_table.setItem(row, 1, pub_item)
            self.app_table.setItem(row, 2, ver_item)
            self.app_table.setItem(row, 3, size_item)

    def _filter_apps(self, text):
        text = text.lower()
        filtered = [
            a for a in self.all_apps
            if text in a.get("name", "").lower()
            or text in a.get("publisher", "").lower()
        ]
        self._populate_table(filtered)

    # ── App Selection ─────────────────────────────────────────────────

    def _on_app_selected(self):
        sel = self.app_table.selectedItems()
        if not sel:
            self.btn_uninstall.setEnabled(False)
            self.btn_residuals.setEnabled(False)
            return

        app = self.app_table.item(sel[0].row(), 0).data(Qt.UserRole)
        self.lbl_name.setText(f"Name: {app.get('name', '—')}")
        self.lbl_pub.setText(f"Publisher: {app.get('publisher', '—')}")
        self.lbl_ver.setText(f"Version: {app.get('display_version', '—')}")
        self.lbl_loc.setText(f"Install path: {app.get('install_location', '—')}")
        self.lbl_reg.setText(f"Registry: {app.get('registry_key', '—')}")

        self.btn_uninstall.setEnabled(True)
        self.btn_residuals.setEnabled(True)
        self.res_table.setRowCount(0)
        self.btn_clean.setEnabled(False)

    # ── Uninstall ─────────────────────────────────────────────────────

    def _run_uninstall(self):
        sel = self.app_table.selectedItems()
        if not sel:
            return
        app = self.app_table.item(sel[0].row(), 0).data(Qt.UserRole)

        reply = QMessageBox.question(
            self, "Confirm Uninstall",
            f"Launch the official uninstaller for:\n\n{app.get('name')}?\n\n"
            f"After it finishes, click 'Scan for Leftover Files' to find residuals.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            ok = self.uninstaller.uninstall_app(app)
            if ok:
                QMessageBox.information(
                    self, "Uninstaller Launched",
                    "The uninstaller has been started.\n"
                    "Once it finishes, click 'Scan for Leftover Files'.",
                )
            else:
                QMessageBox.warning(
                    self, "Error",
                    "Failed to launch the uninstaller.\n"
                    "It may require elevated privileges.",
                )

    # ── Residual Scan (threaded) ──────────────────────────────────────

    def _scan_residuals(self):
        sel = self.app_table.selectedItems()
        if not sel:
            return
        app = self.app_table.item(sel[0].row(), 0).data(Qt.UserRole)

        self.btn_residuals.setEnabled(False)
        self.residual_progress.setVisible(True)
        self.res_table.setRowCount(0)
        self.btn_clean.setEnabled(False)

        self._res_thread = QThread(self)
        self._res_worker = ResidualScanWorker(app.get("name", ""), app.get("publisher", ""))
        self._res_worker.moveToThread(self._res_thread)

        self._res_thread.started.connect(self._res_worker.run)
        self._res_worker.finished.connect(self._on_residuals_done)
        self._res_worker.finished.connect(self._res_thread.quit)
        self._res_worker.finished.connect(self._res_worker.deleteLater)
        self._res_thread.finished.connect(self._res_thread.deleteLater)

        self._res_thread.start()

    def _on_residuals_done(self, leftovers):
        self.btn_residuals.setEnabled(True)
        self.residual_progress.setVisible(False)

        self.res_table.setRowCount(len(leftovers))
        for row, item in enumerate(leftovers):
            path_item = QTableWidgetItem(item["path"])
            path_item.setData(Qt.UserRole, item["path"])

            sz = item.get("size", 0)
            mb = sz / (1024 * 1024)
            size_item = QTableWidgetItem(f"{mb:.2f} MB" if mb > 0.01 else "<0.01 MB")

            self.res_table.setItem(row, 0, path_item)
            self.res_table.setItem(row, 1, size_item)

        if leftovers:
            self.btn_clean.setEnabled(True)
            self.res_table.selectAll()
        else:
            QMessageBox.information(self, "Clean", "No leftover files found for this application.")

    # ── Residual Cleanup ──────────────────────────────────────────────

    def _clean_residuals(self):
        ranges = self.res_table.selectedRanges()
        if not ranges:
            return

        paths = []
        for r in ranges:
            for row in range(r.topRow(), r.bottomRow() + 1):
                item = self.res_table.item(row, 0)
                if item:
                    paths.append(item.data(Qt.UserRole))

        if not paths:
            return

        reply = QMessageBox.warning(
            self, "Confirm Deletion",
            f"You are about to permanently delete {len(paths)} leftover folders/files.\n\n"
            f"This cannot be undone. Proceed?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        deleted = 0
        for path in paths:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                    deleted += 1
                elif os.path.isfile(path):
                    os.remove(path)
                    deleted += 1
            except OSError:
                pass

        QMessageBox.information(self, "Done", f"Removed {deleted} of {len(paths)} residual items.")
        self.res_table.setRowCount(0)
        self.btn_clean.setEnabled(False)
