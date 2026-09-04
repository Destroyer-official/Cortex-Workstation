"""Analysis & system pages: Disk Analyzer, Disk Health (S.M.A.R.T.), Scheduled Tasks.

Each page wraps a read-only or clearly-confirmed backend behind a background
worker so the UI stays responsive. Nothing here modifies the system without an
explicit confirmation dialog.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
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

from pathlib import Path

from . import icons
from .states import StatePanel
from .widgets import Card, CircularGauge, StatCard, status_note, title_block
from .window import _Page, fmt_bytes

# ``sys.platform`` is an interned constant; ``platform.system()`` costs ~50 ms
# on its first call because it populates ``uname()`` via WMI on Windows.
IS_WINDOWS = sys.platform == "win32"


# =====================================================================
#  Workers
# =====================================================================

class DiskAnalyzeWorker(QObject):
    """Diskanalyzeworker.

    Manages DiskAnalyzeWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, root: str):
        """Store constructor arguments (root) and initialize worker signals.

        Initializes the instance and configures internal state.

        Args:
            root (str): Filesystem path to the target file or directory.
        """
        super().__init__()
        self._root = root

    def run(self):
        """Run the DiskAnalyzer (disk analyzer) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.analyzers.disk_analyzer import DiskAnalyzer
            an = DiskAnalyzer(root_path=self._root)
            an.analyze_disk_usage()
            an.analyze_file_types()
            an.find_largest_directories(limit=15)
            self.finished.emit(an.get_stats())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DiskHealthWorker(QObject):
    """Diskhealthworker.

    Manages DiskHealthWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        """Run the DiskHealthMonitor (disk health) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.disk_health import DiskHealthMonitor
            self.finished.emit([d.to_dict() for d in DiskHealthMonitor().get_health()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ScheduledTasksWorker(QObject):
    """Scheduledtasksworker.

    Manages ScheduledTasksWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        """Run the TaskScheduler (scheduler) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.scheduler.scheduler import TaskScheduler
            self.finished.emit(TaskScheduler().list_scheduled_tasks())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class BootPerfWorker(QObject):
    """Bootperfworker.

    Manages BootPerfWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(dict)
    failed = Signal(str)

    def run(self):
        """Run the BootPerformanceMonitor (boot performance) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.boot_performance import BootPerformanceMonitor
            self.finished.emit(BootPerformanceMonitor().analyze())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class SystemRepairWorker(QObject):
    """Systemrepairworker.

    Manages SystemRepairWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, action: str, drive: str = "C"):
        """Store constructor arguments (action, drive) and initialize worker signals.

        Initializes the instance and configures internal state.

        Args:
            action (str): The action parameter.
            drive (str): The drive parameter.
        """
        super().__init__()
        self._action = action
        self._drive = drive

    def run(self):
        """Run the SystemRepair (system repair) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.system_repair import SystemRepair
            sr = SystemRepair()
            a = self._action
            if a == "sfc":
                res = sr.run_sfc()
            elif a in ("CheckHealth", "ScanHealth", "RestoreHealth"):
                res = sr.run_dism(a)
            elif a == "chkdsk":
                res = sr.run_chkdsk_scan(self._drive)
            else:
                self.failed.emit("Unknown repair action.")
                return
            self.finished.emit(res.to_dict())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DeleteTaskWorker(QObject):
    """Deletetaskworker.

    Manages DeleteTaskWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(bool, str)   # (success, task_name)
    failed = Signal(str)

    def __init__(self, name: str):
        """Store constructor arguments (name) and initialize worker signals.

        Initializes the instance and configures internal state.

        Args:
            name (str): The name parameter.
        """
        super().__init__()
        self._name = name

    def run(self):
        """Run the TaskScheduler (scheduler) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.scheduler.scheduler import TaskScheduler
            ok = TaskScheduler().delete_scheduled_task(self._name)
            self.finished.emit(bool(ok), self._name)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# =====================================================================
#  Disk Analyzer  (feature A)
# =====================================================================

class DiskAnalyzerPage(_Page):
    """Diskanalyzerpage.

    Manages DiskAnalyzerPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Disk Analyzer",
            "See exactly where your space goes: usage summary, biggest file "
            "types, and the heaviest directories under a chosen folder.",
        ))

        picker = QHBoxLayout()
        pick_btn = QPushButton("Choose Folder\u2026")
        pick_btn.clicked.connect(self._pick)
        self.path_label = QLabel(str(Path.home()))
        self.path_label.setObjectName("Muted")
        self.run_btn = QPushButton("Analyze")
        self.run_btn.setObjectName("Primary")
        self.run_btn.clicked.connect(self._run)
        picker.addWidget(pick_btn)
        picker.addWidget(self.path_label, 1)
        picker.addWidget(self.run_btn)
        self.v.addLayout(picker)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        stat_row = QHBoxLayout()
        stat_row.setSpacing(14)
        self.card_total = StatCard(self.p, "Volume total", "\u2014")
        self.card_used = StatCard(self.p, "Used", "\u2014")
        self.card_free = StatCard(self.p, "Free", "\u2014")
        for c in (self.card_total, self.card_used, self.card_free):
            stat_row.addWidget(c)
        self.v.addLayout(stat_row)

        body = QHBoxLayout()
        body.setSpacing(18)

        types_col = QVBoxLayout()
        types_col.addWidget(QLabel("Largest file types"))
        self.types_tbl = QTableWidget(0, 3)
        self.types_tbl.setHorizontalHeaderLabels(["Type", "Files", "Size"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.types_tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.types_tbl)
        self.types_tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.types_tbl.verticalHeader().setVisible(False)
        self.types_tbl.setAlternatingRowColors(True)
        self.types_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        types_col.addWidget(self.types_tbl)
        body.addLayout(types_col, 1)

        dirs_col = QVBoxLayout()
        dirs_col.addWidget(QLabel("Largest directories"))
        self.dirs_tbl = QTableWidget(0, 2)
        self.dirs_tbl.setHorizontalHeaderLabels(["Directory", "Size"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.dirs_tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.dirs_tbl)
        self.dirs_tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.dirs_tbl.verticalHeader().setVisible(False)
        self.dirs_tbl.setAlternatingRowColors(True)
        self.dirs_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        dirs_col.addWidget(self.dirs_tbl)
        body.addLayout(dirs_col, 1)

        self.v.addLayout(body, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.types_tbl, self.dirs_tbl)
        self.v.addWidget(self.state, 1)

        self._folder = str(Path.home())

    def _pick(self):
        """Prompt the user to select a filesystem directory or file.

        Launches a native file dialog and populates the selected path into the corresponding target input widget.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select a folder", self._folder)
        if folder:
            self._folder = folder
            self.path_label.setText(folder)

    def _run(self):
        """Run.

        Manages run operations and coordinates related state changes for the component.
        """
        self.run_btn.setEnabled(False)
        self.state.show_loading("Analyzing disk usage\u2026")
        self.win.statusBar().showMessage("Analyzing disk usage\u2026")
        self.win.run_worker(DiskAnalyzeWorker(self._folder), self._on_done, self._fail)

    def _on_done(self, stats: dict):
        """Handle worker results: refresh tables/trees, update cards/labels, update the state panel and clear the busy state.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            stats (dict): The stats parameter.
        """
        self.run_btn.setEnabled(True)
        usage = stats.get("disk_usage", {})
        self.card_total.set_value(usage.get("total_human", "\u2014"))
        self.card_used.set_value(
            f"{usage.get('used_human', '\u2014')} ({usage.get('used_percent', 0):.0f}%)")
        self.card_free.set_value(usage.get("free_human", "\u2014"))

        types = stats.get("file_types", {})
        rows = list(types.items())[:20]
        self.types_tbl.setRowCount(len(rows))
        # AI model extensions surfaced as HIGH-risk, disabled/high-risk note
        try:
            from cortex_unified.analyzers.large_file_finder import AI_MODEL_EXTENSIONS
        except Exception:
            AI_MODEL_EXTENSIONS = {".gguf", ".safetensors", ".onnx", ".bin"}
        for r, (ext, info) in enumerate(rows):
            item0 = QTableWidgetItem(ext)
            item1 = QTableWidgetItem(str(info.get("count", 0)))
            item2 = QTableWidgetItem(info.get("size_human", "0 B"))
            if ext.lower() in AI_MODEL_EXTENSIONS:
                # Flag AI models — HIGH risk, 1-2GB each, re-downloadable but not auto-deleted
                from PySide6.QtGui import QColor
                for it in (item0, item1, item2):
                    it.setForeground(QColor("#FB7185"))
                    it.setToolTip("AI model file — 1-2GB each, re-downloadable but HIGH risk (disabled by default).")
                item0.setText(f"{ext}  (AI model)")
            self.types_tbl.setItem(r, 0, item0)
            self.types_tbl.setItem(r, 1, item1)
            self.types_tbl.setItem(r, 2, item2)

        dirs = stats.get("largest_directories", [])
        self.dirs_tbl.setRowCount(len(dirs))
        for r, d in enumerate(dirs):
            self.dirs_tbl.setItem(r, 0, QTableWidgetItem(d.get("path", "")))
            self.dirs_tbl.setItem(r, 1, QTableWidgetItem(d.get("size_human", "0 B")))

        if not types and not dirs:
            self.state.show_empty("No files found under this folder.")
        else:
            self.state.clear()

        self.win.statusBar().showMessage(
            f"Analyzed {len(types)} file types, {len(dirs)} directories", 5000)

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.run_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._run)


# =====================================================================
#  Disk Health  (feature D - read-only S.M.A.R.T.)
# =====================================================================

class DiskHealthPage(_Page):
    """Diskhealthpage.

    Manages DiskHealthPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Build the page layout (buttons, tables, title header, state panel) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Disk Health",
            "Read-only S.M.A.R.T. overview: health status, wear, temperature and "
            "power-on hours where your drive reports them. Nothing is modified.",
        ))
        if not IS_WINDOWS:
            note = status_note(self.p, "info", "Disk health reporting is only available on Windows.")
            self.v.addWidget(note)
            self.v.addStretch(1)
            return

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Check Disk Health")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tbl = QTableWidget(0, 7)
        self.tbl.setHorizontalHeaderLabels(
            ["Drive", "Media", "Health", "Size", "Wear %", "Temp \u00b0C", "Power-on h"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self.hint = QLabel("")
        self.hint.setObjectName("Muted")
        self.hint.setWordWrap(True)
        self.v.addWidget(self.hint)

        self._autoload = self._load
        self._loaded = False

    def _load(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Reading disk health\u2026")
        self.win.statusBar().showMessage("Reading disk health\u2026")
        self.win.run_worker(DiskHealthWorker(), self._on_done, self._fail)

    @staticmethod
    def _dash(v):
        """Dash.

        Manages dash operations and coordinates related state changes for the component.

        Args:
            v: The v parameter.
        """
        return "\u2014" if v is None else str(v)

    def _on_done(self, disks: list):
        """Handle worker results: refresh tables/trees, update the state panel, note status and clear the busy state.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            disks (list): The disks parameter.
        """
        self.refresh_btn.setEnabled(True)
        if not disks:
            self.state.show_empty("No physical disks reported. This may require Administrator.")
        else:
            self.state.clear()
        self.tbl.setRowCount(len(disks))
        unhealthy = 0
        for r, d in enumerate(disks):
            # Name/type placeholders (Req 8.1, 8.3): never leave the cell blank.
            self.tbl.setItem(r, 0, QTableWidgetItem(d.get("name") or "Unknown drive"))
            self.tbl.setItem(r, 1, QTableWidgetItem(d.get("media_type") or "\u2014"))
            health = d.get("health_status", "Unknown")
            health_item = QTableWidgetItem(health)
            if health.lower() != "healthy":
                unhealthy += 1
                health_item.setForeground(Qt.GlobalColor.red)
            self.tbl.setItem(r, 2, health_item)
            self.tbl.setItem(r, 3, QTableWidgetItem(
                fmt_bytes(d.get("size_bytes", 0)) if d.get("size_bytes") else "\u2014"))
            self.tbl.setItem(r, 4, QTableWidgetItem(self._dash(d.get("wear_percent"))))
            self.tbl.setItem(r, 5, QTableWidgetItem(self._dash(d.get("temperature_c"))))
            self.tbl.setItem(r, 6, QTableWidgetItem(self._dash(d.get("power_on_hours"))))
        if not disks:
            self.hint.setText("No physical disks reported. This may require Administrator.")
        elif unhealthy:
            self.hint.setText(
                f"{unhealthy} drive(s) not reporting 'Healthy'. "
                "Back up important data and investigate.")
        else:
            self.hint.setText("All drives report healthy. Values shown are read directly "
                              "from the drive; blank means the drive doesn't expose that metric.")
        self.win.statusBar().showMessage(f"{len(disks)} physical disk(s)", 5000)

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Scheduled Tasks  (feature C / H)
# =====================================================================

class ScheduledTasksPage(_Page):
    """Scheduledtaskspage.

    Manages ScheduledTasksPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Build the page layout (buttons, tables, title header, state panel) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Scheduled Tasks",
            "Review the tasks your OS runs on a schedule. You can remove tasks "
            "created by Cortex for automatic cleanup here.",
        ))

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.del_btn = QPushButton("Delete Selected Task")
        self.del_btn.setObjectName("Danger")
        self.del_btn.setEnabled(False)
        self.del_btn.clicked.connect(self._delete)
        row.addWidget(self.del_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["Task", "Next run", "Status"])
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
        self.tbl.itemSelectionChanged.connect(
            lambda: self.del_btn.setEnabled(bool(self.tbl.selectedIndexes())))
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        note = QLabel("Deleting an unfamiliar system task can break Windows features. "
                      "Only remove tasks you recognize.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        self.v.addWidget(note)

        self._autoload = self._load
        self._loaded = False

    def _load(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Listing scheduled tasks\u2026")
        self.win.statusBar().showMessage("Listing scheduled tasks\u2026")
        self.win.run_worker(ScheduledTasksWorker(), self._on_done, self._fail)

    def _on_done(self, tasks: list):
        """Handle worker results: refresh tables/trees, update the state panel, note status and clear the busy state.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            tasks (list): The tasks parameter.
        """
        self.refresh_btn.setEnabled(True)
        if not tasks:
            self.state.show_empty("No scheduled tasks found.")
        else:
            self.state.clear()
        self.tbl.setRowCount(len(tasks))
        for r, t in enumerate(tasks):
            name = t.get("name") or (t.get("command", "")[:60])
            self.tbl.setItem(r, 0, QTableWidgetItem(str(name)))
            self.tbl.setItem(r, 1, QTableWidgetItem(str(t.get("next_run_time", ""))))
            self.tbl.setItem(r, 2, QTableWidgetItem(str(t.get("status", ""))))
        self.win.statusBar().showMessage(f"{len(tasks)} scheduled task(s)", 5000)

    def _delete(self):
        """Delete.

        Manages delete operations and coordinates related state changes for the component.
        """
        sel = self.tbl.selectedIndexes()
        if not sel:
            return
        name = self.tbl.item(sel[0].row(), 0).text()
        confirm = QMessageBox.question(
            self, "Delete scheduled task",
            f"Delete the scheduled task:\n\n{name}\n\n"
            "This cannot be undone. Only proceed if you recognize this task.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.del_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.run_worker(DeleteTaskWorker(name), self._on_deleted, self._fail)

    def _on_deleted(self, ok: bool, name: str):
        """Handle worker results: update widgets and clear the busy state.

        Manages on deleted operations and coordinates related state changes for the component.

        Args:
            ok (bool): The ok parameter.
            name (str): The name parameter.
        """
        self.progress.setVisible(False)
        if ok:
            QMessageBox.information(self, "Task deleted", f"Removed '{name}'.")
        else:
            QMessageBox.warning(self, "Delete failed",
                                f"Could not delete '{name}'. It may require Administrator "
                                "or be protected by the system.")
        self._load()

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Boot Performance
# =====================================================================

class BootPerformancePage(_Page):
    """Bootperformancepage.

    Manages BootPerformancePage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Boot Performance",
            "How long your PC takes to start, and exactly what slows it down - "
            "read straight from Windows' own boot diagnostics, not estimated.",
        ))
        if not IS_WINDOWS:
            note = status_note(self.p, "info", "Boot diagnostics are only available on Windows.")
            self.v.addWidget(note)
            self.v.addStretch(1)
            return

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.card_latest = StatCard(self.p, "Last boot", "\u2014")
        self.card_avg = StatCard(self.p, "Average boot", "\u2014")
        self.card_count = StatCard(self.p, "Boots analyzed", "\u2014")
        for c in (self.card_latest, self.card_avg, self.card_count):
            cards.addWidget(c)
        self.v.addLayout(cards)

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Analyze Boot")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.startup_btn = QPushButton("Manage Startup Apps \u2192")
        self.startup_btn.clicked.connect(lambda: self.win._select("startup"))
        row.addWidget(self.startup_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Type", "What slowed boot", "Added delay", "When"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self.hint = QLabel("")
        self.hint.setObjectName("Muted")
        self.hint.setWordWrap(True)
        self.v.addWidget(self.hint)

        self._autoload = self._load
        self._loaded = False

    def _load(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Reading boot diagnostics\u2026")
        self.win.statusBar().showMessage("Reading boot diagnostics\u2026")
        self.win.run_worker(BootPerfWorker(), self._on_done, self._fail)

    def _on_done(self, data: dict):
        """Handle worker results: refresh tables/trees, update cards/labels, update the state panel and clear the busy state.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            data (dict): The data parameter.
        """
        self.refresh_btn.setEnabled(True)
        latest = data.get("latest_seconds", 0.0)
        avg = data.get("average_seconds", 0.0)
        boots = data.get("boots", [])
        issues = data.get("issues", [])
        if not boots:
            self.state.show_empty("No boot diagnostics available yet (may need "
                                  "Administrator or a few reboots).")
        else:
            self.state.clear()
        self.card_latest.set_value(f"{latest:.0f} s" if latest else "\u2014")
        self.card_avg.set_value(f"{avg:.0f} s" if avg else "\u2014")
        self.card_count.set_value(str(len(boots)))

        self.tbl.setRowCount(len(issues))
        for r, it in enumerate(issues):
            self.tbl.setItem(r, 0, QTableWidgetItem(it["kind"]))
            name_item = QTableWidgetItem(it["name"] or "Unknown")
            impact_text = f"+{it['impact_seconds']}s"
            if it["impact_seconds"] >= 10:
                # Non-color signalling (Req 10.5): pair the red highlight with a
                # text marker so the "high impact" state is not colour-only.
                name_item.setForeground(Qt.GlobalColor.red)
                name_item.setToolTip("High boot impact")
                impact_text = f"+{it['impact_seconds']}s  (high)"
            self.tbl.setItem(r, 1, name_item)
            self.tbl.setItem(r, 2, QTableWidgetItem(impact_text))
            self.tbl.setItem(r, 3, QTableWidgetItem(it["when"].replace("T", " ")))

        if not boots:
            self.hint.setText("No boot diagnostics available yet (this may need "
                              "Administrator, or a few reboots to accumulate data).")
        elif issues:
            worst = issues[0]
            self.hint.setText(
                f"Windows measured your last boot at {latest:.0f}s. The biggest "
                f"contributor was <b>{worst['name']}</b> (+{worst['impact_seconds']}s). "
                "Apps in red add 10s or more - consider disabling the ones you don't "
                "need at startup via 'Manage Startup Apps'. These are Windows' own "
                "measurements, not estimates.")
        else:
            self.hint.setText(f"Your last boot was {latest:.0f}s and Windows flagged "
                              "no significant slowdowns. Nice and clean.")
        self.win.statusBar().showMessage(
            f"Boot: last {latest:.0f}s, {len(issues)} slowdown(s) flagged", 5000)

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  System File Health & Repair
# =====================================================================

class SystemRepairPage(_Page):
    """Systemrepairpage.

    Manages SystemRepairPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Build the page layout (cards, title header, progress bar) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "System File Health",
            "Check and repair Windows using its own built-in tools (SFC, DISM, "
            "CHKDSK) - the Microsoft-recommended fix for corruption, crashes, "
            "failed updates and unexplained slowness.",
        ))
        if not IS_WINDOWS:
            note = status_note(self.p, "info", "System repair tools are only available on Windows.")
            self.v.addWidget(note)
            self.v.addStretch(1)
            return

        from cortex_unified.system_tools.system_repair import SystemRepair
        if not SystemRepair.is_elevated():
            warn = status_note(
                self.p, "warning",
                "These tools need Administrator. Restart Cortex as "
                "Administrator to run repairs.")
            self.v.addWidget(warn)

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(10)

        # Recommended order: quick check -> repair store -> repair files.
        self.check_btn = self._tool_row(
            cl, "1. Quick Health Check", "Fast check of the component store (seconds).",
            lambda: self._run("CheckHealth", "Quick health check",
                              "This is a fast, read-only check. Proceed?"))
        self.dism_btn = self._tool_row(
            cl, "2. Repair Component Store", "DISM RestoreHealth - repairs the store SFC "
            "relies on. Can take 10-30 min and may download from Windows Update.",
            lambda: self._run("RestoreHealth", "Repair component store (DISM)",
                              "DISM RestoreHealth can take 10-30 minutes and may use the "
                              "internet to fetch repair files. Proceed?"))
        self.sfc_btn = self._tool_row(
            cl, "3. Repair System Files", "SFC /scannow - verifies and repairs protected "
            "Windows files. Takes 10-20 min.",
            lambda: self._run("sfc", "Repair system files (SFC)",
                              "SFC /scannow can take 10-20 minutes and may repair system "
                              "files. Proceed?"))
        self.chkdsk_btn = self._tool_row(
            cl, "4. Check Disk (read-only)", "CHKDSK scan of C: for filesystem errors. A "
            "full fix (/F) must be scheduled for reboot.",
            lambda: self._run("chkdsk", "Check disk (read-only)",
                              "This runs a read-only CHKDSK scan of C:. It does not change "
                              "anything. Proceed?"))
        self.v.addWidget(card)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.v.addWidget(self.status)

        res_card = Card(self.p)
        rl = QVBoxLayout(res_card)
        rl.setContentsMargins(18, 16, 18, 16)
        self.result = QLabel("Run a check above. Recommended order: 1 \u2192 2 \u2192 3.")
        self.result.setWordWrap(True)
        self.result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        rl.addWidget(self.result)
        self.v.addWidget(res_card, 1)

        self._buttons = [self.check_btn, self.dism_btn, self.sfc_btn, self.chkdsk_btn]

    def _tool_row(self, layout, title, desc, handler) -> QPushButton:
        """Tool row via the worker/widgets; results return through worker signals.

        Manages tool row operations and coordinates related state changes for the component.

        Args:
            layout: The layout parameter.
            title: Display text string.
            desc: The desc parameter.
            handler: The handler parameter.

        Returns:
            QPushButton: Result of the operation.
        """
        row = QHBoxLayout()
        col = QVBoxLayout()
        t = QLabel(f"<b>{title}</b>")
        d = QLabel(desc)
        d.setObjectName("Muted")
        d.setWordWrap(True)
        col.addWidget(t)
        col.addWidget(d)
        row.addLayout(col, 1)
        btn = QPushButton("Run")
        btn.clicked.connect(handler)
        row.addWidget(btn)
        layout.addLayout(row)
        return btn

    def _run(self, action: str, title: str, prompt: str):
        """Run.

        Manages run operations and coordinates related state changes for the component.

        Args:
            action (str): The action parameter.
            title (str): Display text string.
            prompt (str): The prompt parameter.
        """
        confirm = QMessageBox.question(
            self, title, prompt + "\n\nRequires Administrator. Cortex stays responsive "
            "while it runs, but don't shut down until it finishes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        for b in self._buttons:
            b.setEnabled(False)
        self.progress.setVisible(True)
        self.status.setText(f"Running {title}\u2026 this can take several minutes.")
        self.result.setText("Working\u2026")
        self.win.statusBar().showMessage(f"{title} running\u2026")
        self.win.run_worker(SystemRepairWorker(action), self._on_done, self._fail)

    def _on_done(self, r: dict):
        """Handle worker results: note status, re-enable buttons and clear the busy state.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            r (dict): The r parameter.
        """
        self.progress.setVisible(False)
        self.status.setText("")
        for b in self._buttons:
            b.setEnabled(True)
        # A word, not a pictograph: U+2705 / U+26D4 render as colour emoji on
        # Windows, and this is rich text where an SVG cannot be dropped in
        # cheaply. The outcome word is also clearer for screen readers.
        outcome = {
            "clean": "No issues found", "repaired": "Repaired",
            "repairable": "Repairable", "errors": "Errors found",
            "partial": "Partly completed", "error": "Failed",
            "busy": "Already running",
        }.get(r["status"], "Result")
        color = {
            "clean": self.p.success, "repaired": self.p.success,
            "repairable": self.p.warning, "errors": self.p.warning,
            "busy": self.p.warning, "partial": self.p.danger,
            "error": self.p.danger,
        }.get(r["status"], self.p.text_muted)
        reboot = ("<br><b>A restart is recommended</b> to complete the changes."
                  if r.get("needs_reboot") else "")
        tail = ("<br><br><span style='font-size:11px'>Tool output (tail):<br>"
                f"{r['raw_tail'].replace(chr(10), '<br>')}</span>" if r.get("raw_tail") else "")
        self.result.setText(
            f"<span style='color:{color}'><b>{outcome}</b></span> &middot; "
            f"<b>{r['tool']}:</b> {r['message']}{reboot}{tail}")
        self.win.statusBar().showMessage(f"{r['tool']}: {r['status']}", 6000)

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.progress.setVisible(False)
        self.status.setText("")
        for b in self._buttons:
            b.setEnabled(True)
        self.result.setText(
            f"<span style='color:{self.p.danger}'><b>Failed</b></span> "
            f"&middot; Repair failed: {msg}")


# =====================================================================
#  Storage Sense
# =====================================================================

class StorageSenseWorker(QObject):
    """Storagesenseworker.

    Manages StorageSenseWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, action: str = "status", value: int = 0):
        """Store constructor arguments (action, value) and initialize worker signals.

        Initializes the instance and configures internal state.

        Args:
            action (str): The action parameter.
            value (int): The value parameter.
        """
        super().__init__()
        self._action = action
        self._value = value

    def run(self):
        """Run the StorageSense (storage sense) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.storage_sense import StorageSense
            ss = StorageSense()
            if self._action == "enable":
                ss.set_enabled(bool(self._value))
            elif self._action == "cadence":
                ss.set_cadence(self._value)
            elif self._action == "recycle":
                ss.set_recycle_bin_days(self._value)
            self.finished.emit(ss.get_status())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class StorageSensePage(_Page):
    """Storagesensepage.

    Manages StorageSensePage operations and coordinates related state changes for the component.
    """

    _CADENCE = [(0, "When disk space is low"), (1, "Every day"),
                (7, "Every week"), (30, "Every month")]
    _DAYS = [(0, "Never"), (1, "1 day"), (14, "14 days"), (30, "30 days"), (60, "60 days")]

    def __init__(self, win):
        """Build the page layout (cards, title header, controls) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Storage Sense",
            "Let Windows clean up automatically on a schedule - temp files, the "
            "Recycle Bin and old downloads. This configures the built-in Windows "
            "feature, so it keeps working even when Cortex isn't open.",
        ))
        if not IS_WINDOWS:
            note = status_note(self.p, "info", "Storage Sense is only available on Windows.")
            self.v.addWidget(note)
            self.v.addStretch(1)
            return

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(12)

        self.enable_chk = QCheckBox("Storage Sense is ON")
        self.enable_chk.toggled.connect(self._toggle_enable)
        cl.addWidget(self.enable_chk)

        crow = QHBoxLayout()
        crow.addWidget(QLabel("Run cleanup:"))
        self.cadence = QComboBox()
        for _, label in self._CADENCE:
            self.cadence.addItem(label)
        self.cadence.activated.connect(self._set_cadence)
        crow.addWidget(self.cadence)
        crow.addStretch(1)
        cl.addLayout(crow)

        rrow = QHBoxLayout()
        rrow.addWidget(QLabel("Empty Recycle Bin items older than:"))
        self.rb_days = QComboBox()
        for _, label in self._DAYS:
            self.rb_days.addItem(label)
        self.rb_days.activated.connect(self._set_recycle)
        rrow.addWidget(self.rb_days)
        rrow.addStretch(1)
        cl.addLayout(rrow)
        self.v.addWidget(card)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        self.v.addWidget(self.status)
        self.v.addStretch(1)

        self._loading = True   # guard so programmatic updates don't re-trigger writes
        self._autoload = self._load
        self._loaded = False

    def _load(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        self.win.run_worker(StorageSenseWorker("status"), self._on_status, self._fail)

    def _on_status(self, s: dict):
        """Handle worker results: update cards/labels and clear the busy state.

        Manages on status operations and coordinates related state changes for the component.

        Args:
            s (dict): The s parameter.
        """
        self._loading = True
        self.enable_chk.setChecked(s.get("enabled", False))
        self.enable_chk.setText("Storage Sense is ON" if s.get("enabled")
                                else "Storage Sense is OFF")
        cad = s.get("cadence", 0)
        for i, (val, _) in enumerate(self._CADENCE):
            if val == cad:
                self.cadence.setCurrentIndex(i)
        rbd = s.get("recycle_bin_days", 0)
        for i, (val, _) in enumerate(self._DAYS):
            if val == rbd:
                self.rb_days.setCurrentIndex(i)
        extras = []
        if s.get("clean_temp_files"):
            extras.append("temp files")
        if s.get("downloads_cleanup"):
            extras.append(f"downloads older than {s.get('downloads_days_label')}")
        self.status.setText(
            ("Configured. " if s.get("configured") else "Not yet configured. ")
            + (f"Also cleaning: {', '.join(extras)}." if extras else
               "Tip: enabling weekly cleanup keeps free space healthy automatically."))
        self._loading = False

    def _toggle_enable(self, on: bool):
        """Compute and return the value for toggle enable used by the page.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.

        Args:
            on (bool): The on parameter.
        """
        if self._loading:
            return
        self.win.run_worker(StorageSenseWorker("enable", 1 if on else 0),
                            self._on_status, self._fail)

    def _set_cadence(self, idx: int):
        """Compute and return the value for set cadence used by the page.

        Manages set cadence operations and coordinates related state changes for the component.

        Args:
            idx (int): The idx parameter.
        """
        if self._loading:
            return
        self.win.run_worker(StorageSenseWorker("cadence", self._CADENCE[idx][0]),
                            self._on_status, self._fail)

    def _set_recycle(self, idx: int):
        """Compute and return the value for set recycle used by the page.

        Manages set recycle operations and coordinates related state changes for the component.

        Args:
            idx (int): The idx parameter.
        """
        if self._loading:
            return
        self.win.run_worker(StorageSenseWorker("recycle", self._DAYS[idx][0]),
                            self._on_status, self._fail)

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.win._default_fail(msg)


# =====================================================================
#  Security (Windows Defender)
# =====================================================================

class DefenderStatusWorker(QObject):
    """Defenderstatusworker.

    Manages DefenderStatusWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(dict, list)
    failed = Signal(str)

    def run(self):
        """Run the WindowsDefender (defender) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.defender import WindowsDefender
            d = WindowsDefender()
            self.finished.emit(d.status().to_dict(), d.recent_threats())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DefenderScanWorker(QObject):
    """Defenderscanworker.

    Manages DefenderScanWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(bool, str)
    failed = Signal(str)

    def run(self):
        """Run the WindowsDefender (defender) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.defender import WindowsDefender
            ok, msg = WindowsDefender().start_quick_scan()
            self.finished.emit(ok, msg)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class SecurityPage(_Page):
    """Securitypage.

    Manages SecurityPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Security",
            "Your Windows Defender protection at a glance - real-time protection, "
            "signature freshness, last scan - and a one-click quick scan.",
        ))
        if not IS_WINDOWS:
            note = status_note(self.p, "info", "Windows Security status is only available on Windows.")
            self.v.addWidget(note)
            self.v.addStretch(1)
            return

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.scan_btn = QPushButton("Run Quick Scan")
        self.scan_btn.clicked.connect(self._scan)
        row.addWidget(self.scan_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.card = Card(self.p)
        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(20, 18, 20, 18)
        self.info = QLabel("Loading Defender status\u2026")
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        cl.addWidget(self.info)
        self.v.addWidget(self.card)

        thr_label = QLabel("Recent detections")
        thr_label.setObjectName("SectionTitle")
        self.v.addWidget(thr_label)
        self.tbl = QTableWidget(0, 2)
        self.tbl.setHorizontalHeaderLabels(["When", "Threat"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.card, self.tbl)
        self.v.addWidget(self.state, 1)

        self._autoload = self._load
        self._loaded = False

    def _load(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Checking Windows Security\u2026")
        self.win.run_worker(DefenderStatusWorker(), self._on_status, self._fail)

    def _on_status(self, s: dict, threats: list):
        """Handle worker results: refresh tables/trees, re-enable buttons and clear the busy state.

        Manages on status operations and coordinates related state changes for the component.

        Args:
            s (dict): The s parameter.
            threats (list): The threats parameter.
        """
        self.state.clear()
        self.refresh_btn.setEnabled(True)
        if not s.get("available"):
            self.info.setText("Windows Defender is not available or is managed by "
                              "another security product.")
            return
        # Colour + word rather than a pictograph: the old marks rendered as
        # colour emoji on Windows, and the word keeps it readable without them.
        badge = (
            f"<span style='color:{self.p.success}'>Protected</span>"
            if s["healthy"] else
            f"<span style='color:{self.p.warning}'>Needs attention</span>"
        )
        age = s.get("signature_age_days")
        age_txt = f"{age} day(s) old" if age is not None else "unknown"
        lines = [
            f"<b>{badge}</b>",
            f"Real-time protection: {'on' if s['realtime_protection'] else '<b>OFF</b>'}",
            f"Antivirus: {'enabled' if s['antivirus_enabled'] else 'disabled'}  \u2022  "
            f"Tamper protection: {'on' if s['tamper_protection'] else 'off'}",
            f"Signatures: {s['signature_version'] or 'n/a'} ({age_txt})",
            f"Last quick scan: {s['last_quick_scan'] or 'never'}  \u2022  "
            f"Last full scan: {s['last_full_scan'] or 'never'}",
            f"Engine: {s['engine_version'] or 'n/a'}",
        ]
        if not s["realtime_protection"]:
            lines.append("<span style='color:#e0a000'>Real-time protection is off - turn "
                         "it on in Windows Security unless another antivirus manages it.</span>")
        if age is not None and age > 7:
            lines.append("<span style='color:#e0a000'>Signatures are stale - run a quick "
                         "scan or check for updates.</span>")
        self.info.setText("<br>".join(lines))

        self.tbl.setRowCount(len(threats))
        for r, t in enumerate(threats):
            self.tbl.setItem(r, 0, QTableWidgetItem(t["time"].replace("T", " ")))
            self.tbl.setItem(r, 1, QTableWidgetItem(t["threat"]))
        if not threats:
            self.tbl.setRowCount(1)
            self.tbl.setItem(0, 0, QTableWidgetItem(""))
            self.tbl.setItem(0, 1, QTableWidgetItem("No threats detected \u2014 clean."))

    def _scan(self):
        """Scan via the background worker, confirmation dialog, progress state; results return through worker signals.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
        confirm = QMessageBox.question(
            self, "Run quick scan",
            "Run a Windows Defender quick scan now? This checks the most common "
            "locations and may take a few minutes. It only scans - it won't delete "
            "your files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.statusBar().showMessage("Running Defender quick scan\u2026")
        self.win.run_worker(DefenderScanWorker(), self._on_scanned, self._fail)

    def _on_scanned(self, ok: bool, msg: str):
        """Handle worker results: re-enable buttons and clear the busy state.

        Manages on scanned operations and coordinates related state changes for the component.

        Args:
            ok (bool): The ok parameter.
            msg (str): Informational or progress status message.
        """
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        if ok:
            QMessageBox.information(self, "Scan complete", msg)
        else:
            QMessageBox.warning(self, "Scan", msg)
        self._load()

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.refresh_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  One-click Health Check
# =====================================================================

class HealthCheckWorker(QObject):
    """Healthcheckworker.

    Manages HealthCheckWorker operations and coordinates related state changes for the component.
    """
    progress = Signal(str)
    finished = Signal(dict)
    failed = Signal(str)

    def run(self):
        """Run the HealthChecker (health check) backend call off the UI thread; emit finished/failed/progress with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.health_check import HealthChecker
            report = HealthChecker().run(progress=self.progress.emit)
            self.finished.emit(report.to_dict())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class HealthCheckPage(_Page):
    """Healthcheckpage.

    Manages HealthCheckPage operations and coordinates related state changes for the component.
    """

    #: severity -> (icon asset, colour, human label). The marks used to be
    #: codepoints; U+2705 and U+26D4 have *emoji* presentation on Windows, so
    #: they rendered as full-colour pictographs inside an otherwise monochrome
    #: table. These are now tinted SVGs from the shared icon set.
    _SEV = {
        "good": ("success", "#34D399", "Healthy"),
        "warning": ("warning", "#FBBF24", "Review"),
        "critical": ("error", "#FB7185", "Action needed"),
        "info": ("info", "#38BDF8", "Unknown"),
    }

    def __init__(self, win):
        """Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Health Check",
            "One click to assess your PC across disk space, drive health, memory, "
            "boot speed and security - honest checks, with a jump to fix each issue.",
        ))

        hero = QHBoxLayout()
        hero.setSpacing(18)
        gauge_card = Card(self.p, "HeroCard")
        gc = QVBoxLayout(gauge_card)
        gc.setContentsMargins(24, 24, 24, 24)
        self.gauge = CircularGauge(self.p, caption="health score")
        # Glow matches the Dashboard gauge so both hero cards read the same way.
        from .widgets import attach_glow
        attach_glow(self.gauge, self.p.accent, 34, 55)
        gc.addWidget(self.gauge, alignment=Qt.AlignmentFlag.AlignCenter)
        self.grade_label = QLabel("")
        self.grade_label.setObjectName("PageTitle")
        self.grade_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gc.addWidget(self.grade_label)
        self.run_btn = QPushButton("Run Health Check")
        self.run_btn.setObjectName("Primary")
        self.run_btn.clicked.connect(self._run)
        from . import motion
        motion.press_feedback(self.run_btn)   # pressed-state feedback on the primary action
        gc.addWidget(self.run_btn)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        gc.addWidget(self.progress)
        self.scan_status = QLabel("")
        self.scan_status.setObjectName("Muted")
        self.scan_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gc.addWidget(self.scan_status)
        # Top-align the hero card so it hugs its content instead of stretching
        # into a tall card with an empty lower half beside the results table.
        hero.addWidget(gauge_card, 0, Qt.AlignmentFlag.AlignTop)

        checks_col = QVBoxLayout()
        self.summary = QLabel("Run a health check to see how your PC is doing.")
        self.summary.setObjectName("Muted")
        self.summary.setWordWrap(True)
        checks_col.addWidget(self.summary)
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["", "Check", "Detail", ""])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        # Column sizing that adapts to the window and never clips: the icon is a
        # fixed narrow column, "Check" and the "Fix" action size to their content
        # (so "Fix \u2192" is always fully visible), and "Detail" takes the rest.
        header = self.tbl.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.setColumnWidth(0, 44)
        self.tbl.setWordWrap(False)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        checks_col.addWidget(self.tbl, 1)
        # Loading state: a shimmer skeleton stands in for the results
        # table while the checks run, then is swapped out when they arrive.
        from .skeleton import ShimmerSkeleton
        self.skeleton = ShimmerSkeleton(self.p, rows=6)
        self.skeleton.setVisible(False)
        checks_col.addWidget(self.skeleton, 1)
        hero.addLayout(checks_col, 1)
        self.v.addLayout(hero, 1)

        self._autoload = self._run
        self._loaded = False

    def _run(self):
        """Run.

        Manages run operations and coordinates related state changes for the component.
        """
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.scan_status.setText("Starting\u2026")
        self.gauge.set_center_text("\u2026")
        self.grade_label.setText("")
        # Swap the results table for the shimmer skeleton while we scan.
        self.tbl.setVisible(False)
        self.skeleton.setVisible(True)
        self.skeleton.start()
        self.win.run_worker(HealthCheckWorker(), self._on_done, self._fail,
                            on_progress=self._on_progress)

    def _on_progress(self, msg: str):
        """Handle worker results: update widgets and clear the busy state.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            msg (str): Informational or progress status message.
        """
        self.scan_status.setText(msg)

    def _on_done(self, report: dict):
        """Handle worker results: refresh tables/trees, update cards/labels, note status and clear the busy state.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            report (dict): The generated report data object from the backend.
        """
        self.skeleton.stop()
        self.skeleton.setVisible(False)
        self.tbl.setVisible(True)
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.run_btn.setEnabled(True)
        score = report.get("score", 0)
        grade = report.get("grade", "")
        self.gauge.animate_to(float(score), display=str(score))
        self.grade_label.setText(f"Grade {grade}")
        checks = report.get("checks", [])
        criticals = sum(1 for c in checks if c["severity"] == "critical")
        warnings = sum(1 for c in checks if c["severity"] == "warning")
        # Plain text: severity is carried by the per-row icons and labels in the
        # table below, so the summary line does not need a pictograph - and the
        # ones used here rendered as colour emoji on Windows.
        if criticals:
            self.summary.setText(
                f"{criticals} issue(s) need attention"
                + (f" and {warnings} to review." if warnings else "."))
        elif warnings:
            self.summary.setText(
                f"{warnings} item(s) worth reviewing - otherwise healthy.")
        else:
            self.summary.setText("Everything looks healthy.")

        self.tbl.setRowCount(len(checks))
        for r, c in enumerate(checks):
            icon_name, color, sev_label = self._SEV.get(
                c["severity"], ("info", "#888888", "Unknown"))
            sev_item = QTableWidgetItem()
            sev_item.setIcon(icons.icon(icon_name, 15, color))
            # Non-color signalling (Req 10.5): the severity glyph/colour is
            # backed by a text label (tooltip + accessible text) so severity is
            # not conveyed by colour alone.
            sev_item.setToolTip(sev_label)
            sev_item.setData(Qt.ItemDataRole.AccessibleTextRole, sev_label)
            self.tbl.setItem(r, 0, sev_item)
            title_item = QTableWidgetItem(c["title"])
            self.tbl.setItem(r, 1, title_item)
            detail_item = QTableWidgetItem(c["detail"])
            self.tbl.setItem(r, 2, detail_item)
            if c.get("action_page"):
                btn = QPushButton("Fix \u2192")
                btn.clicked.connect(lambda _=False, p=c["action_page"]: self.win._select(p))
                self.tbl.setCellWidget(r, 3, btn)
        self.tbl.resizeRowsToContents()
        self.win.statusBar().showMessage(f"Health score {score}/100 (grade {grade})", 6000)

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.skeleton.stop()
        self.skeleton.setVisible(False)
        self.tbl.setVisible(True)
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.run_btn.setEnabled(True)
        self.win._default_fail(msg)


# =====================================================================
#  Windows Update
# =====================================================================

class WUActivityWorker(QObject):
    """Wuactivityworker.

    Manages WUActivityWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(dict, list)   # (last_activity, history)
    failed = Signal(str)

    def run(self):
        """Run the WindowsUpdate (windows update) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.windows_update import WindowsUpdate
            wu = WindowsUpdate()
            self.finished.emit(wu.last_activity(), wu.recent_history())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class WUPendingWorker(QObject):
    """Wupendingworker.

    Manages WUPendingWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        """Run the WindowsUpdate (windows update) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.windows_update import WindowsUpdate
            self.finished.emit([u.to_dict() for u in WindowsUpdate().check_pending()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class WindowsUpdatePage(_Page):
    """Windowsupdatepage.

    Manages WindowsUpdatePage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Windows Update",
            "When Windows last updated (offline, instant) and what's pending "
            "(checking reaches Microsoft, so it needs internet). Cortex reports "
            "updates - Windows installs them, handling reboots safely.",
        ))
        if not IS_WINDOWS:
            note = status_note(self.p, "info", "Windows Update status is only available on Windows.")
            self.v.addWidget(note)
            self.v.addStretch(1)
            return

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.card_check = StatCard(self.p, "Last checked", "\u2014")
        self.card_install = StatCard(self.p, "Last installed", "\u2014")
        for c in (self.card_check, self.card_install):
            cards.addWidget(c)
        self.v.addLayout(cards)

        row = QHBoxLayout()
        self.check_btn = QPushButton("Check for Updates Online")
        self.check_btn.setObjectName("Primary")
        self.check_btn.clicked.connect(self._check_pending)
        row.addWidget(self.check_btn)
        self.open_btn = QPushButton("Open Windows Update")
        self.open_btn.clicked.connect(self._open_settings)
        row.addWidget(self.open_btn)
        row.addStretch(1)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        pend_label = QLabel("Pending updates")
        pend_label.setObjectName("SectionTitle")
        self.v.addWidget(pend_label)
        self.pending_tbl = QTableWidget(0, 3)
        self.pending_tbl.setHorizontalHeaderLabels(["Update", "KB", "Severity"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.pending_tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.pending_tbl)
        self.pending_tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.pending_tbl.verticalHeader().setVisible(False)
        self.pending_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.pending_tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.pending_tbl)

        hist_label = QLabel("Recent update history")
        hist_label.setObjectName("SectionTitle")
        self.v.addWidget(hist_label)
        self.hist_tbl = QTableWidget(0, 3)
        self.hist_tbl.setHorizontalHeaderLabels(["Update", "Date", "Result"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.hist_tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.hist_tbl)
        self.hist_tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.hist_tbl.verticalHeader().setVisible(False)
        self.hist_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.hist_tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.hist_tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.hist_tbl, self.pending_tbl)
        self.v.addWidget(self.state, 1)

        self._autoload = self._load
        self._loaded = False

    def _load(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        self.state.show_loading("Reading update status\u2026")
        self.win.run_worker(WUActivityWorker(), self._on_activity, self._fail)

    def _on_activity(self, activity: dict, history: list):
        """Handle worker results: refresh tables/trees, update cards/labels and clear the busy state.

        Manages on activity operations and coordinates related state changes for the component.

        Args:
            activity (dict): The activity parameter.
            history (list): The history parameter.
        """
        self.state.clear()
        self.card_check.set_value(activity.get("last_check") or "unknown")
        self.card_install.set_value(activity.get("last_install") or "unknown")
        self.hist_tbl.setRowCount(len(history))
        for r, h in enumerate(history):
            self.hist_tbl.setItem(r, 0, QTableWidgetItem(h["title"]))
            self.hist_tbl.setItem(r, 1, QTableWidgetItem(h["date"]))
            res_item = QTableWidgetItem(h["result"])
            if not h["succeeded"]:
                res_item.setForeground(Qt.GlobalColor.red)
            self.hist_tbl.setItem(r, 2, res_item)

    def _check_pending(self):
        """Handle check pending for the page widgets and worker state.

        Manages check pending operations and coordinates related state changes for the component.
        """
        self.check_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.statusBar().showMessage("Checking Windows Update (online)\u2026")
        self.win.run_worker(WUPendingWorker(), self._on_pending, self._fail)

    def _on_pending(self, updates: list):
        """Handle worker results: refresh tables/trees, note status, re-enable buttons and clear the busy state.

        Manages on pending operations and coordinates related state changes for the component.

        Args:
            updates (list): The updates parameter.
        """
        self.progress.setVisible(False)
        self.check_btn.setEnabled(True)
        self.pending_tbl.setRowCount(len(updates))
        for r, u in enumerate(updates):
            self.pending_tbl.setItem(r, 0, QTableWidgetItem(u["title"]))
            self.pending_tbl.setItem(r, 1, QTableWidgetItem(u["kb"]))
            self.pending_tbl.setItem(r, 2, QTableWidgetItem(u["severity"] or "\u2014"))
        if not updates:
            self.win.statusBar().showMessage("Windows is up to date.", 5000)
        else:
            self.win.statusBar().showMessage(f"{len(updates)} update(s) available", 5000)

    def _open_settings(self):
        """Handle open settings for the page widgets and worker state.

        Manages open settings operations and coordinates related state changes for the component.
        """
        try:
            import os
            os.startfile("ms-settings:windowsupdate")  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Open failed", str(exc))

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.check_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Component Store (WinSxS) + Windows upgrade leftovers
# =====================================================================

class ComponentStorePage(_Page):
    """Shrink WinSxS the supported way, and clear upgrade leftovers.

    ``C:\\Windows`` filling up is nearly always the component store plus upgrade
    leftovers, and the internet is full of advice that breaks Windows Update or
    permanently prevents uninstalling Office. This page measures first using
    Windows' own analysis, then offers only supported actions - and reports what
    each one costs.
    """

    def __init__(self, win):
        """Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Windows Component Store",
            "The usual reason C:\\Windows is huge. Cortex asks Windows to measure "
            "it, then cleans it the supported way - and refuses to hand-delete "
            "anything Windows manages itself.",
        ))
        if not IS_WINDOWS:
            note = status_note(self.p, "info", "The component store is a Windows-only concept.")
            self.v.addWidget(note)
            self.v.addStretch(1)
            return

        self._leftovers: list = []
        self._analysis = None

        # -- summary cards ---------------------------------------------------
        cards = QHBoxLayout()
        self.card_actual = StatCard(self.p, "Actual size", "\u2014")
        self.card_shared = StatCard(self.p, "Shared with Windows", "\u2014")
        self.card_reclaim = StatCard(self.p, "Could be reclaimed", "\u2014")
        for c in (self.card_actual, self.card_shared, self.card_reclaim):
            cards.addWidget(c)
        self.v.addLayout(cards)

        self.verdict = QLabel("")
        self.verdict.setObjectName("Muted")
        self.verdict.setWordWrap(True)
        self.v.addWidget(self.verdict)

        # -- controls --------------------------------------------------------
        row = QHBoxLayout()
        self.analyze_btn = QPushButton("Analyze Component Store")
        self.analyze_btn.setObjectName("Primary")
        self.analyze_btn.clicked.connect(self._analyze)
        row.addWidget(self.analyze_btn)
        self.task_btn = QPushButton("Let Windows Clean It")
        self.task_btn.clicked.connect(self._run_task)
        row.addWidget(self.task_btn)
        self.fix_24h2_btn = QPushButton("Fix 24H2 Staged Packages")
        self.fix_24h2_btn.setToolTip("Removes stuck Windows 11 24H2 checkpoint cumulative update packages (Package_for_RollupFix)")
        self.fix_24h2_btn.clicked.connect(self._fix_24h2)
        row.addWidget(self.fix_24h2_btn)
        row.addStretch(1)
        self.clean_btn = QPushButton("Clean Now")
        self.clean_btn.setObjectName("Primary")
        self.clean_btn.setEnabled(False)
        self.clean_btn.clicked.connect(self._clean)
        row.addWidget(self.clean_btn)
        self.v.addLayout(row)

        self.reset_chk = QCheckBox(
            "Also remove all superseded versions (/ResetBase) - frees more, but "
            "permanently blocks uninstalling the updates you have now")
        self.reset_chk.setToolTip(
            "ResetBase cannot be undone. Only use it when you are confident the "
            "current updates are stable.")
        self.v.addWidget(self.reset_chk)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        self.v.addWidget(self.status)

        # -- leftovers table -------------------------------------------------
        hdr = QLabel("Windows upgrade & servicing leftovers")
        hdr.setObjectName("Muted")
        self.v.addWidget(hdr)

        self._COLS = ["Item", "Size", "Removing it costs you", "Location"]
        self.tbl = QTableWidget(0, len(self._COLS))
        self.tbl.setHorizontalHeaderLabels(self._COLS)
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.itemSelectionChanged.connect(self._on_select)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        del_row = QHBoxLayout()
        del_row.addStretch(1)
        self.del_btn = QPushButton("Remove Selected Leftovers")
        self.del_btn.setObjectName("Danger")
        self.del_btn.setEnabled(False)
        self.del_btn.clicked.connect(self._delete_leftovers)
        del_row.addWidget(self.del_btn)
        self.v.addLayout(del_row)

        note = QLabel(
            "Cleaning the component store needs Administrator and can take 10-30 "
            "minutes. Items marked as managed by Windows are shown for context "
            "only - Cortex will not delete them, because doing so breaks Windows "
            "Update and software repair."
        )
        note.setObjectName("Muted")
        note.setWordWrap(True)
        self.v.addWidget(note)

        # No autoload: DISM /AnalyzeComponentStore can take minutes on a
        # machine with a long update history, so - like System File Health's
        # SFC/DISM tools - this page waits for an explicit click rather than
        # spawning it every time the page is opened (Req 1.5).
        self.state.show_empty("Click \u201cAnalyze Component Store\u201d to measure it.")

    # -- selection -----------------------------------------------------------

    def _selected_leftovers(self) -> list:
        """Compute and return the value for selected leftovers used by the page.

        Manages selected leftovers operations and coordinates related state changes for the component.

        Returns:
            list: List of processed items or identifiers.
        """
        rows = sorted({i.row() for i in self.tbl.selectedIndexes()})
        return [self._leftovers[r] for r in rows if 0 <= r < len(self._leftovers)]

    def _on_select(self):
        """Handle worker results: re-enable buttons and clear the busy state.

        Manages on select operations and coordinates related state changes for the component.
        """
        chosen = self._selected_leftovers()
        # Managed items can never be removed here, so don't offer it.
        self.del_btn.setEnabled(bool(chosen) and all(item.removable_here for item in chosen))

    # -- analyze -------------------------------------------------------------

    def _analyze(self):
        """Analyze.

        Manages analyze operations and coordinates related state changes for the component.
        """
        from .workers import ComponentStoreAnalyzeWorker
        self.analyze_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.state.show_loading("Measuring the component store\u2026")
        self.win.run_worker(ComponentStoreAnalyzeWorker(), self._on_analyzed,
                            self._fail, on_progress=self.status.setText)

    def _on_analyzed(self, analysis, leftovers: list):
        """Handle worker results: refresh tables/trees, update cards/labels, update the state panel and clear the busy state.

        Manages on analyzed operations and coordinates related state changes for the component.

        Args:
            analysis: The analysis parameter.
            leftovers (list): The leftovers parameter.
        """
        self.analyze_btn.setEnabled(True)
        self._analysis = analysis
        self._leftovers = leftovers

        if analysis.actual_size:
            self.card_actual.set_value(fmt_bytes(analysis.actual_size))
            self.card_shared.set_value(fmt_bytes(analysis.shared_with_windows))
            self.card_reclaim.set_value(fmt_bytes(analysis.reclaimable_estimate))
            self.clean_btn.setEnabled(True)
        else:
            for c in (self.card_actual, self.card_shared, self.card_reclaim):
                c.set_value("\u2014")

        parts = [analysis.message]
        if analysis.reclaimable_packages:
            parts.append(f"{analysis.reclaimable_packages} superseded package(s) "
                         f"can be removed.")
        if analysis.last_cleanup:
            parts.append(f"Last cleanup: {analysis.last_cleanup}.")
        if analysis.explorer_gap_note:
            parts.append(analysis.explorer_gap_note)
        self.verdict.setText("  ".join(p for p in parts if p))
        self.status.setText("")

        self.tbl.setRowCount(len(leftovers))
        for r, item in enumerate(leftovers):
            self.tbl.setItem(r, 0, QTableWidgetItem(item.label))
            size_item = QTableWidgetItem(fmt_bytes(item.size_bytes))
            size_item.setData(Qt.ItemDataRole.UserRole, item.size_bytes)
            self.tbl.setItem(r, 1, size_item)
            cost = item.explanation
            if item.risk.value == "managed":
                cost = f"[managed by Windows] {cost}  {item.supported_removal}"
            elif item.risk.value == "rollback" and item.rollback_expired:
                cost = (f"{cost} (Windows' 10-day rollback window has already "
                        f"passed for this item.)")
            self.tbl.setItem(r, 2, QTableWidgetItem(cost))
            self.tbl.setItem(r, 3, QTableWidgetItem(str(item.path)))

        self.tbl.clearSelection()
        self._on_select()

        if not leftovers:
            self.state.show_empty("No Windows upgrade leftovers found.")
        else:
            self.state.clear()
            removable = sum(item.size_bytes for item in leftovers if item.removable_here)
            if removable:
                self.win.statusBar().showMessage(
                    f"{fmt_bytes(removable)} of removable leftovers found", 6000)

    # -- actions -------------------------------------------------------------

    def _clean(self):
        """Clean via the background worker, confirmation dialog, progress state; results return through worker signals.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.
        """
        from .workers import ComponentStoreCleanWorker
        reset = self.reset_chk.isChecked()
        estimate = (fmt_bytes(self._analysis.reclaimable_estimate)
                    if self._analysis else "an unknown amount")
        extra = ("\n\nResetBase is selected: after this, the updates currently "
                 "installed can no longer be uninstalled. This cannot be undone."
                 if reset else "")
        confirm = QMessageBox.question(
            self, "Clean component store",
            f"Clean the Windows component store?\n\n"
            f"Windows estimates up to {estimate} can be reclaimed. The operation "
            f"needs Administrator and typically takes 10-30 minutes. Nothing you "
            f"installed is removed.{extra}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.clean_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.run_worker(ComponentStoreCleanWorker(reset), self._on_cleaned,
                            self._fail, on_progress=self.status.setText)

    def _on_cleaned(self, outcome):
        """Handle worker results: note status, re-enable buttons and clear the busy state.

        Manages on cleaned operations and coordinates related state changes for the component.

        Args:
            outcome: The outcome parameter.
        """
        self.progress.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.clean_btn.setEnabled(True)
        msg = outcome.message
        if outcome.success and outcome.freed_bytes:
            msg = f"Reclaimed {fmt_bytes(outcome.freed_bytes)}. {msg}"
        if outcome.needs_reboot:
            msg += " A restart is needed to finish."
        self.status.setText(msg)
        self.win.statusBar().showMessage(msg, 8000)

        box = QMessageBox(self)
        box.setWindowTitle("Component store cleanup")
        box.setText(msg)
        box.setIcon(QMessageBox.Icon.Information if outcome.success
                    else QMessageBox.Icon.Warning)
        if outcome.raw_tail:
            box.setDetailedText(outcome.raw_tail)
        box.exec()
        if outcome.success:
            self._analyze()

    def _run_task(self):
        """Handle run task for the page widgets and worker state.

        Manages run task operations and coordinates related state changes for the component.
        """
        from .workers import ServicingTaskWorker
        confirm = QMessageBox.question(
            self, "Let Windows clean it",
            "Start Windows' own component cleanup task?\n\n"
            "This is the gentler option: Windows limits itself to an hour and "
            "keeps components newer than 30 days. It runs in the background.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.task_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.run_worker(ServicingTaskWorker(), self._on_task, self._fail)

    def _on_task(self, ok: bool, message: str):
        """Handle worker results: note status, re-enable buttons and clear the busy state.

        Manages on task operations and coordinates related state changes for the component.

        Args:
            ok (bool): The ok parameter.
            message (str): Informational or progress status message.
        """
        self.progress.setVisible(False)
        self.task_btn.setEnabled(True)
        self.status.setText(message)
        self.win.statusBar().showMessage(message, 8000)
        if ok:
            QMessageBox.information(self, "Windows cleanup task", message)
        else:
            QMessageBox.warning(self, "Windows cleanup task", message)

    def _fix_24h2(self):
        """Fix Windows 11 24H2 stuck staged packages using ComponentStoreCleaner.

        Manages fix 24h2 operations and coordinates related state changes for the component.
        """
        confirm = QMessageBox.question(
            self, "Fix 24H2 Staged Packages",
            "This targets stuck 'Staged' checkpoint cumulative update packages in Windows 11 24H2 "
            "(known Microsoft bug) and unblocks DISM component store reclamation.\n\n"
            "Proceed with fix?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.status.setText("Fixing stuck 24H2 packages via DISM...")
        self.progress.setVisible(True)
        try:
            from cortex_unified.system_tools.component_store_cleaner import ComponentStoreCleaner
            cleaner = ComponentStoreCleaner()
            result = cleaner.fix_staged_packages()
            self.progress.setVisible(False)
            self.status.setText(f"24H2 package fix complete: {result.command}")
            QMessageBox.information(self, "24H2 Staged Packages", f"Operation completed: {result.command}")
            self._analyze()
        except Exception as exc:
            self.progress.setVisible(False)
            self._fail(f"Fix failed: {exc}")

    def _delete_leftovers(self):
        """Handle delete leftovers for the page widgets and worker state.

        Manages delete leftovers operations and coordinates related state changes for the component.
        """
        from .workers import LeftoverDeleteWorker
        chosen = [item for item in self._selected_leftovers() if item.removable_here]
        if not chosen:
            return
        total = sum(item.size_bytes for item in chosen)
        rollback = [item for item in chosen if item.risk.value == "rollback"]
        lines = "\n".join(f"  \u2022 {item.label}  ({fmt_bytes(item.size_bytes)})"
                          for item in chosen)
        warn = ""
        if rollback:
            warn = ("\n\nThis includes rollback data: you will no longer be able "
                    "to go back to your previous Windows version.")
        confirm = QMessageBox.question(
            self, "Remove leftovers",
            f"Permanently remove {len(chosen)} item(s), freeing about "
            f"{fmt_bytes(total)}?\n\n{lines}\n\n"
            f"These are system folders, so they cannot go to the Recycle Bin - "
            f"removal is permanent. Administrator may be required.{warn}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.del_btn.setEnabled(False)
        self.progress.setVisible(True)
        sizes = {str(item.path): item.size_bytes for item in chosen}
        self.win.run_worker(
            LeftoverDeleteWorker([str(item.path) for item in chosen], sizes),
            self._on_deleted, self._fail, on_progress=self.status.setText)

    def _on_deleted(self, freed: int, removed: int, blocked: int):
        """Handle worker results: note status and clear the busy state.

        Manages on deleted operations and coordinates related state changes for the component.

        Args:
            freed (int): The freed parameter.
            removed (int): The removed parameter.
            blocked (int): The blocked parameter.
        """
        self.progress.setVisible(False)
        msg = f"Removed {removed} item(s), freeing {fmt_bytes(freed)}."
        if blocked:
            msg += (f" {blocked} could not be removed - they are in use or the "
                    f"safety guard blocked them.")
        self.status.setText(msg)
        self.win.statusBar().showMessage(msg, 8000)
        QMessageBox.information(self, "Leftovers removed", msg)
        self._analyze()

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.progress.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.task_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._analyze)
