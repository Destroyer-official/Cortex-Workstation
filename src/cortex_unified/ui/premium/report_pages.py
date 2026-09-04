"""Reporting & recovery pages: exportable PC Health Report, Backups/Restore.

- HealthReportPage gathers read-only system facts (system info, disk usage,
  disk health) and exports a shareable HTML/JSON/text report via
  ReportsGenerator.
- BackupsPage lists backup manifests produced by the engine and restores files
  from them - always dry-run first, then a confirmed real restore.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .states import StatePanel
from .widgets import Card, title_block
from .window import _Page


# =====================================================================
#  Workers
# =====================================================================

class HealthReportWorker(QObject):
    """Healthreportworker.

    Manages HealthReportWorker operations and coordinates related state changes for the component.
    """

    finished = Signal(str, dict)   # (report_path, data)
    failed = Signal(str)

    def __init__(self, fmt: str):
        """Store the report output format ("html", "json", or "text").

        Initializes the instance and configures internal state.

        Args:
            fmt (str): The fmt parameter.
        """
        super().__init__()
        self._fmt = fmt

    def _collect(self) -> dict:
        """Aggregate discovered files or telemetry metrics into collections.

        Iterates over raw subsystem records, filters excluded paths, and collates findings into a structured report list.

        Returns:
            dict: Dictionary mapping identifiers to status or values.
        """
        data: dict = {}
        try:
            from cortex_unified.system_tools.system_info import SystemInfo
            data["System"] = SystemInfo().snapshot()
        except Exception as exc:  # noqa: BLE001
            data["System"] = {"error": str(exc)}
        try:
            from cortex_unified.system_tools.disk_health import DiskHealthMonitor
            disks = [d.to_dict() for d in DiskHealthMonitor().get_health()]
            data["Disk Health"] = disks or "Not reported (may require Administrator)"
        except Exception as exc:  # noqa: BLE001
            data["Disk Health"] = {"error": str(exc)}
        return data

    def run(self):
        """Collect diagnostics, generate the report file, and emit its path and data.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.reports.reports import ReportsGenerator
            data = self._collect()
            gen = ReportsGenerator()
            if self._fmt == "html":
                path = gen.generate_html_report(data)
            elif self._fmt == "json":
                path = gen.generate_json_report(data)
            else:
                path = gen.generate_text_report(data)
            self.finished.emit(path, data)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ManifestListWorker(QObject):
    """List cleanup backups: operation manifests + leftover-clean journals.

    Leftover sessions appear as read-only history rows: files went to the
    Recycle Bin and registry keys have .reg exports inside the session
    folder, so there is deliberately no in-app restore button for them -
    the row's detail says exactly where each undo artifact lives.
    """

    finished = Signal(list)
    failed = Signal(str)

    @staticmethod
    def _leftover_sessions() -> list[dict]:
        """Build read-only history rows from leftover-cleanup journals (newest first).

        Manages leftover sessions operations and coordinates related state changes for the component.

        Returns:
            list[dict]: List of processed items or identifiers.
        """
        rows: list[dict] = []
        root = Path.home() / "CortexCleanerBackups" / "leftovers"
        try:
            sessions = sorted(p for p in root.iterdir() if p.is_dir())
        except OSError:
            return rows
        for session in reversed(sessions):          # newest first
            journal_file = session / "journal.json"
            if not journal_file.is_file():
                continue
            try:
                payload = json.loads(
                    journal_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            ok = int(payload.get("ok_count", 0))
            failed = int(payload.get("fail_count", 0))
            rows.append({
                "backup_name": f"Leftover cleanup \u2014 {session.name}",
                "timestamp": payload.get("timestamp", session.name),
                "files_backed_up": ok,
                "_kind": "leftovers",
                "_detail": (f"{ok} cleaned, {failed} failed. Files are in "
                            f"the Recycle Bin; .reg/.xml backups and the "
                            f"journal are in {session}"),
            })
        return rows

    def run(self):
        """List restore manifests plus leftover sessions and emit the combined rows.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.reports.restore_manager import RestoreManager
            manifests = list(RestoreManager().list_manifests())
            for m in manifests:
                m.setdefault("_kind", "manifest")
            manifests.extend(self._leftover_sessions())
            self.finished.emit(manifests)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class RestoreWorker(QObject):
    """Restores files from a backup manifest (dry-run or real, optional overwrite).

    Emits ``finished`` with the restore result dict or ``failed`` with an error.
    """
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, manifest_file: str, dry_run: bool, overwrite: bool):
        """Store the manifest path plus dry-run and overwrite flags.

        Initializes the instance and configures internal state.

        Args:
            manifest_file (str): The manifest file parameter.
            dry_run (bool): The dry run parameter.
            overwrite (bool): The overwrite parameter.
        """
        super().__init__()
        self._file = manifest_file
        self._dry = dry_run
        self._overwrite = overwrite

    def run(self):
        """Run the manifest restore via RestoreManager and emit the result.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.reports.restore_manager import RestoreManager
            res = RestoreManager().restore_from_manifest(
                self._file, dry_run=self._dry, overwrite_existing=self._overwrite)
            self.finished.emit(res)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# =====================================================================
#  PC Health Report  (feature I)
# =====================================================================

class HealthReportPage(_Page):
    """Healthreportpage.

    Manages HealthReportPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Build the PC Health Report page: export buttons, progress, and preview card.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "PC Health Report",
            "Generate a shareable snapshot of your system: hardware, OS, memory, "
            "disks and drive health. Fully offline; written to your reports folder.",
        ))

        row = QHBoxLayout()
        self.html_btn = QPushButton("Export HTML")
        self.html_btn.setObjectName("Primary")
        self.html_btn.clicked.connect(lambda: self._generate("html"))
        self.json_btn = QPushButton("Export JSON")
        self.json_btn.clicked.connect(lambda: self._generate("json"))
        self.txt_btn = QPushButton("Export Text")
        self.txt_btn.clicked.connect(lambda: self._generate("text"))
        row.addWidget(self.html_btn)
        row.addWidget(self.json_btn)
        row.addWidget(self.txt_btn)
        row.addStretch(1)
        self.open_btn = QPushButton("Open Last Report")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._open_last)
        row.addWidget(self.open_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.card = Card(self.p)
        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(20, 18, 20, 18)
        self.preview = QLabel("Choose a format above to generate a report.")
        self.preview.setWordWrap(True)
        self.preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        cl.addWidget(self.preview)
        self.v.addWidget(self.card, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.card)
        self.v.addWidget(self.state, 1)

        self._last_path: str | None = None

    def _generate(self, fmt: str):
        """Generate.

        Manages generate operations and coordinates related state changes for the component.

        Args:
            fmt (str): The fmt parameter.
        """
        for b in (self.html_btn, self.json_btn, self.txt_btn):
            b.setEnabled(False)
        self.state.show_loading("Collecting diagnostics\u2026")
        self.win.statusBar().showMessage("Collecting diagnostics\u2026")
        self.win.run_worker(HealthReportWorker(fmt), self._on_done, self._fail)

    def _on_done(self, path: str, data: dict):
        """Show a summary preview of the saved report and enable opening it.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            path (str): Filesystem path to the target file or directory.
            data (dict): The data parameter.
        """
        self.state.clear()
        for b in (self.html_btn, self.json_btn, self.txt_btn):
            b.setEnabled(True)
        self._last_path = path
        self.open_btn.setEnabled(True)
        sysd = data.get("System", {})
        p = sysd.get("platform", {}) if isinstance(sysd, dict) else {}
        mem = sysd.get("memory", {}) if isinstance(sysd, dict) else {}
        lines = [
            f"<b>Report saved:</b> {path}",
            "",
            f"<b>OS:</b> {p.get('system', '?')} {p.get('release', '')}",
            f"<b>Host:</b> {p.get('hostname', '')}",
            f"<b>Memory:</b> {mem.get('total_human', '?')} total, "
            f"{mem.get('used_percent', '?')}% used",
        ]
        dh = data.get("Disk Health")
        if isinstance(dh, list) and dh:
            lines.append(f"<b>Drives:</b> " + ", ".join(
                f"{d.get('name', '?')} ({d.get('health_status', '?')})" for d in dh))
        self.preview.setText("<br>".join(lines))
        self.win.statusBar().showMessage(f"Report written to {path}", 6000)

    def _open_last(self):
        """Open the most recently generated report with the OS default viewer.

        Manages open last operations and coordinates related state changes for the component.
        """
        if not self._last_path:
            return
        try:
            import os
            os.startfile(self._last_path)  # type: ignore[attr-defined]  # Windows
        except AttributeError:
            import subprocess
            import sys
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.Popen([opener, self._last_path])
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Open failed", str(exc))

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        for b in (self.html_btn, self.json_btn, self.txt_btn):
            b.setEnabled(True)
        self.state.show_error(msg, on_retry=None)


# =====================================================================
#  Backups / Restore  (feature G)
# =====================================================================

class BackupsPage(_Page):
    """List backup manifests and restore files from them.

    Creates a backup archive or export of target resources, reporting the final output location upon success.
    """

    def __init__(self, win):
        """Build the Backups & Restore page: refresh/preview/restore buttons and a manifests table.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Backups & Restore",
            "Restore files from backups Cortex made before cleaning. A dry-run "
            "preview always runs first so you know exactly what will be restored.",
        ))

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.preview_btn = QPushButton("Preview Restore")
        self.preview_btn.setEnabled(False)
        self.preview_btn.clicked.connect(self._preview)
        self.restore_btn = QPushButton("Restore Selected")
        self.restore_btn.setObjectName("Primary")
        self.restore_btn.setEnabled(False)
        self.restore_btn.clicked.connect(self._restore)
        row.addWidget(self.preview_btn)
        row.addWidget(self.restore_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["Backup", "Created", "Files"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.itemSelectionChanged.connect(self._on_sel)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        self.v.addWidget(self.status)

        self._autoload = self._load
        self._loaded = False

    def _on_sel(self):
        """Enable Preview/Restore buttons based on table selection.

        Manages on sel operations and coordinates related state changes for the component.
        """
        has = bool(self.tbl.selectedIndexes())
        self.preview_btn.setEnabled(has)
        self.restore_btn.setEnabled(has)

    def _load(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Loading backups\u2026")
        self.win.run_worker(ManifestListWorker(), self._on_listed, self._fail)

    def _on_listed(self, manifests: list):
        """Populate the backups table and show an empty state when none exist.

        Manages on listed operations and coordinates related state changes for the component.

        Args:
            manifests (list): The manifests parameter.
        """
        if not manifests:
            self.state.show_empty("No backups found yet. Cortex creates these before "
                                   "cleaning when backups are enabled in Settings.")
        else:
            self.state.clear()
        self.refresh_btn.setEnabled(True)
        self._manifests = manifests
        self.tbl.setRowCount(len(manifests))
        for r, m in enumerate(manifests):
            name_item = QTableWidgetItem(m.get("backup_name", "?"))
            name_item.setData(Qt.ItemDataRole.UserRole, m.get("file_path", ""))
            self.tbl.setItem(r, 0, name_item)
            self.tbl.setItem(r, 1, QTableWidgetItem(str(m.get("timestamp", ""))))
            self.tbl.setItem(r, 2, QTableWidgetItem(str(m.get("files_backed_up", 0))))
        if not manifests:
            self.status.setText("No backups found yet. Cortex creates these before "
                                 "cleaning when backups are enabled in Settings.")
        else:
            self.status.setText(f"{len(manifests)} backup(s) available.")

    def _selected_manifest(self) -> str | None:
        """Return the file path of the currently selected backup row.

        Manages selected manifest operations and coordinates related state changes for the component.

        Returns:
            str | None: Formatted string or path.
        """
        sel = self.tbl.selectedIndexes()
        if not sel:
            return None
        item = self.tbl.item(sel[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _preview(self):
        """Preview.

        Manages preview operations and coordinates related state changes for the component.
        """
        mf = self._selected_manifest()
        if not mf:
            return
        self._busy(True)
        self.win.run_worker(RestoreWorker(mf, True, False), self._on_preview, self._fail)

    def _on_preview(self, res: dict):
        """Show dry-run counts (would-restore / skipped / errors) in the status line.

        Manages on preview operations and coordinates related state changes for the component.

        Args:
            res (dict): The res parameter.
        """
        self._busy(False)
        self.status.setText(
            f"Dry-run: {res['restored']} file(s) would be restored, "
            f"{res['skipped']} skipped, {res['errors']} error(s). "
            + (f"First issues: {res['error_details'][0]}" if res.get("error_details") else ""))

    def _restore(self):
        """Restore.

        Manages restore operations and coordinates related state changes for the component.
        """
        mf = self._selected_manifest()
        if not mf:
            return
        overwrite = QMessageBox.question(
            self, "Overwrite existing?",
            "If a file already exists at its original location, overwrite it?\n\n"
            "Yes = overwrite existing files.  No = skip files that already exist.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes
        confirm = QMessageBox.question(
            self, "Confirm restore",
            "Restore files from this backup to their original locations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._busy(True)
        self.win.run_worker(RestoreWorker(mf, False, overwrite), self._on_restored, self._fail)

    def _on_restored(self, res: dict):
        """Report restore results (restored / skipped / errors) in a dialog and status line.

        Manages on restored operations and coordinates related state changes for the component.

        Args:
            res (dict): The res parameter.
        """
        self._busy(False)
        msg = (f"Restored {res['restored']} file(s). "
               f"Skipped {res['skipped']}, {res['errors']} error(s).")
        QMessageBox.information(self, "Restore complete", msg)
        self.status.setText(msg)
        self.win.statusBar().showMessage(msg, 6000)

    def _busy(self, on: bool):
        """Update the busy state indicators across the interface.

        Shows or hides loading indicators, adjusts cursor feedback, and toggles action button availability.

        Args:
            on (bool): The on parameter.
        """
        self.progress.setVisible(on)
        self.refresh_btn.setEnabled(not on)
        self.preview_btn.setEnabled(not on and bool(self.tbl.selectedIndexes()))
        self.restore_btn.setEnabled(not on and bool(self.tbl.selectedIndexes()))

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self._busy(False)
        self.state.show_error(msg, on_retry=self._load)
