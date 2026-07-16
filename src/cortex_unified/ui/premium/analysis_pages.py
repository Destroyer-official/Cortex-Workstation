"""Analysis & system pages: Disk Analyzer, Disk Health (S.M.A.R.T.), Scheduled Tasks.

Each page wraps a read-only or clearly-confirmed backend behind a background
worker so the UI stays responsive. Nothing here modifies the system without an
explicit confirmation dialog.
"""

from __future__ import annotations

import platform

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

from .states import StatePanel
from .widgets import Card, CircularGauge, StatCard, title_block
from .window import _Page, fmt_bytes

IS_WINDOWS = platform.system() == "Windows"


# =====================================================================
#  Workers
# =====================================================================

class DiskAnalyzeWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, root: str):
        super().__init__()
        self._root = root

    def run(self):
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
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.disk_health import DiskHealthMonitor
            self.finished.emit([d.to_dict() for d in DiskHealthMonitor().get_health()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ScheduledTasksWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.scheduler.scheduler import TaskScheduler
            self.finished.emit(TaskScheduler().list_scheduled_tasks())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class BootPerfWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.boot_performance import BootPerformanceMonitor
            self.finished.emit(BootPerformanceMonitor().analyze())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class SystemRepairWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, action: str, drive: str = "C"):
        super().__init__()
        self._action = action
        self._drive = drive

    def run(self):
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
    finished = Signal(bool, str)   # (success, task_name)
    failed = Signal(str)

    def __init__(self, name: str):
        super().__init__()
        self._name = name

    def run(self):
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
    """Break down where space goes: file types + largest directories."""

    def __init__(self, win):
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
        folder = QFileDialog.getExistingDirectory(self, "Select a folder", self._folder)
        if folder:
            self._folder = folder
            self.path_label.setText(folder)

    def _run(self):
        self.run_btn.setEnabled(False)
        self.state.show_loading("Analyzing disk usage\u2026")
        self.win.statusBar().showMessage("Analyzing disk usage\u2026")
        self.win.run_worker(DiskAnalyzeWorker(self._folder), self._on_done, self._fail)

    def _on_done(self, stats: dict):
        self.run_btn.setEnabled(True)
        usage = stats.get("disk_usage", {})
        self.card_total.set_value(usage.get("total_human", "\u2014"))
        self.card_used.set_value(
            f"{usage.get('used_human', '\u2014')} ({usage.get('used_percent', 0):.0f}%)")
        self.card_free.set_value(usage.get("free_human", "\u2014"))

        types = stats.get("file_types", {})
        rows = list(types.items())[:20]
        self.types_tbl.setRowCount(len(rows))
        for r, (ext, info) in enumerate(rows):
            self.types_tbl.setItem(r, 0, QTableWidgetItem(ext))
            self.types_tbl.setItem(r, 1, QTableWidgetItem(str(info.get("count", 0))))
            self.types_tbl.setItem(r, 2, QTableWidgetItem(info.get("size_human", "0 B")))

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
        self.run_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._run)


# =====================================================================
#  Disk Health  (feature D - read-only S.M.A.R.T.)
# =====================================================================

class DiskHealthPage(_Page):
    """Read-only physical-disk health (S.M.A.R.T.) overview."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Disk Health",
            "Read-only S.M.A.R.T. overview: health status, wear, temperature and "
            "power-on hours where your drive reports them. Nothing is modified.",
        ))
        if not IS_WINDOWS:
            note = QLabel("\u2139  Disk health reporting is only available on Windows.")
            note.setObjectName("Muted")
            note.setWordWrap(True)
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
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Reading disk health\u2026")
        self.win.statusBar().showMessage("Reading disk health\u2026")
        self.win.run_worker(DiskHealthWorker(), self._on_done, self._fail)

    @staticmethod
    def _dash(v):
        return "\u2014" if v is None else str(v)

    def _on_done(self, disks: list):
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
            self.hint.setText(f"\u26A0  {unhealthy} drive(s) not reporting 'Healthy'. "
                              "Back up important data and investigate.")
        else:
            self.hint.setText("All drives report healthy. Values shown are read directly "
                              "from the drive; blank means the drive doesn't expose that metric.")
        self.win.statusBar().showMessage(f"{len(disks)} physical disk(s)", 5000)

    def _fail(self, msg: str):
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Scheduled Tasks  (feature C / H)
# =====================================================================

class ScheduledTasksPage(_Page):
    """View OS scheduled tasks; delete Cortex-created cleanup tasks."""

    def __init__(self, win):
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
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Listing scheduled tasks\u2026")
        self.win.statusBar().showMessage("Listing scheduled tasks\u2026")
        self.win.run_worker(ScheduledTasksWorker(), self._on_done, self._fail)

    def _on_done(self, tasks: list):
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
        self.progress.setVisible(False)
        if ok:
            QMessageBox.information(self, "Task deleted", f"Removed '{name}'.")
        else:
            QMessageBox.warning(self, "Delete failed",
                                f"Could not delete '{name}'. It may require Administrator "
                                "or be protected by the system.")
        self._load()

    def _fail(self, msg: str):
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Boot Performance
# =====================================================================

class BootPerformancePage(_Page):
    """Why your PC is slow to start - using Windows' own boot measurements."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Boot Performance",
            "How long your PC takes to start, and exactly what slows it down - "
            "read straight from Windows' own boot diagnostics, not estimated.",
        ))
        if not IS_WINDOWS:
            note = QLabel("\u2139  Boot diagnostics are only available on Windows.")
            note.setObjectName("Muted")
            note.setWordWrap(True)
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
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Reading boot diagnostics\u2026")
        self.win.statusBar().showMessage("Reading boot diagnostics\u2026")
        self.win.run_worker(BootPerfWorker(), self._on_done, self._fail)

    def _on_done(self, data: dict):
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
                impact_text = f"+{it['impact_seconds']}s  \u26A0 high"
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
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  System File Health & Repair
# =====================================================================

class SystemRepairPage(_Page):
    """Run Windows' built-in SFC / DISM / CHKDSK repair tools, explained."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "System File Health",
            "Check and repair Windows using its own built-in tools (SFC, DISM, "
            "CHKDSK) - the Microsoft-recommended fix for corruption, crashes, "
            "failed updates and unexplained slowness.",
        ))
        if not IS_WINDOWS:
            note = QLabel("\u2139  System repair tools are only available on Windows.")
            note.setObjectName("Muted")
            note.setWordWrap(True)
            self.v.addWidget(note)
            self.v.addStretch(1)
            return

        from cortex_unified.system_tools.system_repair import SystemRepair
        if not SystemRepair.is_elevated():
            warn = QLabel("\u26A0  These tools need Administrator. Restart Cortex as "
                          "Administrator to run repairs.")
            warn.setObjectName("Muted")
            warn.setWordWrap(True)
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
        self.progress.setVisible(False)
        self.status.setText("")
        for b in self._buttons:
            b.setEnabled(True)
        icon = {"clean": "\u2705", "repaired": "\u2705", "repairable": "\u26A0",
                "errors": "\u26A0", "partial": "\u26D4", "error": "\u26D4",
                "busy": "\u26A0"}.get(r["status"], "\u2139")
        reboot = ("<br><b>A restart is recommended</b> to complete the changes."
                  if r.get("needs_reboot") else "")
        tail = ("<br><br><span style='font-size:11px'>Tool output (tail):<br>"
                f"{r['raw_tail'].replace(chr(10), '<br>')}</span>" if r.get("raw_tail") else "")
        self.result.setText(f"{icon} <b>{r['tool']}:</b> {r['message']}{reboot}{tail}")
        self.win.statusBar().showMessage(f"{r['tool']}: {r['status']}", 6000)

    def _fail(self, msg: str):
        self.progress.setVisible(False)
        self.status.setText("")
        for b in self._buttons:
            b.setEnabled(True)
        self.result.setText(f"\u26D4 Repair failed: {msg}")


# =====================================================================
#  Storage Sense
# =====================================================================

class StorageSenseWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, action: str = "status", value: int = 0):
        super().__init__()
        self._action = action
        self._value = value

    def run(self):
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
    """Turn on and schedule Windows' built-in automatic cleanup."""

    _CADENCE = [(0, "When disk space is low"), (1, "Every day"),
                (7, "Every week"), (30, "Every month")]
    _DAYS = [(0, "Never"), (1, "1 day"), (14, "14 days"), (30, "30 days"), (60, "60 days")]

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Storage Sense",
            "Let Windows clean up automatically on a schedule - temp files, the "
            "Recycle Bin and old downloads. This configures the built-in Windows "
            "feature, so it keeps working even when Cortex isn't open.",
        ))
        if not IS_WINDOWS:
            note = QLabel("\u2139  Storage Sense is only available on Windows.")
            note.setObjectName("Muted")
            note.setWordWrap(True)
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
        self.win.run_worker(StorageSenseWorker("status"), self._on_status, self._fail)

    def _on_status(self, s: dict):
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
        if self._loading:
            return
        self.win.run_worker(StorageSenseWorker("enable", 1 if on else 0),
                            self._on_status, self._fail)

    def _set_cadence(self, idx: int):
        if self._loading:
            return
        self.win.run_worker(StorageSenseWorker("cadence", self._CADENCE[idx][0]),
                            self._on_status, self._fail)

    def _set_recycle(self, idx: int):
        if self._loading:
            return
        self.win.run_worker(StorageSenseWorker("recycle", self._DAYS[idx][0]),
                            self._on_status, self._fail)

    def _fail(self, msg: str):
        self.win._default_fail(msg)


# =====================================================================
#  Security (Windows Defender)
# =====================================================================

class DefenderStatusWorker(QObject):
    finished = Signal(dict, list)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.defender import WindowsDefender
            d = WindowsDefender()
            self.finished.emit(d.status().to_dict(), d.recent_threats())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DefenderScanWorker(QObject):
    finished = Signal(bool, str)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.defender import WindowsDefender
            ok, msg = WindowsDefender().start_quick_scan()
            self.finished.emit(ok, msg)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class SecurityPage(_Page):
    """Windows Security (Defender) status + quick scan."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Security",
            "Your Windows Defender protection at a glance - real-time protection, "
            "signature freshness, last scan - and a one-click quick scan.",
        ))
        if not IS_WINDOWS:
            note = QLabel("\u2139  Windows Security status is only available on Windows.")
            note.setObjectName("Muted")
            note.setWordWrap(True)
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
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Checking Windows Security\u2026")
        self.win.run_worker(DefenderStatusWorker(), self._on_status, self._fail)

    def _on_status(self, s: dict, threats: list):
        self.state.clear()
        self.refresh_btn.setEnabled(True)
        if not s.get("available"):
            self.info.setText("Windows Defender is not available or is managed by "
                              "another security product.")
            return
        badge = "\u2705 Protected" if s["healthy"] else "\u26A0 Needs attention"
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
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        if ok:
            QMessageBox.information(self, "Scan complete", msg)
        else:
            QMessageBox.warning(self, "Scan", msg)
        self._load()

    def _fail(self, msg: str):
        self.refresh_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  One-click Health Check
# =====================================================================

class HealthCheckWorker(QObject):
    progress = Signal(str)
    finished = Signal(dict)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.health_check import HealthChecker
            report = HealthChecker().run(progress=self.progress.emit)
            self.finished.emit(report.to_dict())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class HealthCheckPage(_Page):
    """One click to assess overall PC health across the fast diagnostics."""

    _SEV = {
        "good": ("\u2705", "#34D399", "Healthy"),
        "warning": ("\u26A0", "#FBBF24", "Review"),
        "critical": ("\u26D4", "#FB7185", "Action needed"),
        "info": ("\u2139", "#38BDF8", "Unknown"),
    }

    def __init__(self, win):
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
        gc.addWidget(self.gauge, alignment=Qt.AlignmentFlag.AlignCenter)
        self.grade_label = QLabel("")
        self.grade_label.setObjectName("PageTitle")
        self.grade_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gc.addWidget(self.grade_label)
        self.run_btn = QPushButton("Run Health Check")
        self.run_btn.setObjectName("Primary")
        self.run_btn.clicked.connect(self._run)
        gc.addWidget(self.run_btn)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        gc.addWidget(self.progress)
        self.scan_status = QLabel("")
        self.scan_status.setObjectName("Muted")
        self.scan_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gc.addWidget(self.scan_status)
        hero.addWidget(gauge_card, 0)

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
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl.setColumnWidth(0, 40)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        checks_col.addWidget(self.tbl, 1)
        hero.addLayout(checks_col, 1)
        self.v.addLayout(hero, 1)

        self._autoload = self._run
        self._loaded = False

    def _run(self):
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.scan_status.setText("Starting\u2026")
        self.gauge.set_center_text("\u2026")
        self.grade_label.setText("")
        self.win.run_worker(HealthCheckWorker(), self._on_done, self._fail,
                            on_progress=self._on_progress)

    def _on_progress(self, msg: str):
        self.scan_status.setText(msg)

    def _on_done(self, report: dict):
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
        if criticals:
            self.summary.setText(f"\u26D4 {criticals} issue(s) need attention"
                                 + (f" and {warnings} to review." if warnings else "."))
        elif warnings:
            self.summary.setText(f"\u26A0 {warnings} item(s) worth reviewing - otherwise healthy.")
        else:
            self.summary.setText("\u2705 Everything looks healthy.")

        self.tbl.setRowCount(len(checks))
        for r, c in enumerate(checks):
            icon, color, sev_label = self._SEV.get(
                c["severity"], ("\u2139", "#888", "Unknown"))
            sev_item = QTableWidgetItem(icon)
            sev_item.setForeground(Qt.GlobalColor.white)
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
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.run_btn.setEnabled(True)
        self.win._default_fail(msg)


# =====================================================================
#  Windows Update
# =====================================================================

class WUActivityWorker(QObject):
    finished = Signal(dict, list)   # (last_activity, history)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.windows_update import WindowsUpdate
            wu = WindowsUpdate()
            self.finished.emit(wu.last_activity(), wu.recent_history())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class WUPendingWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.windows_update import WindowsUpdate
            self.finished.emit([u.to_dict() for u in WindowsUpdate().check_pending()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class WindowsUpdatePage(_Page):
    """See when Windows last updated, what's pending, and recent update history."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Windows Update",
            "When Windows last updated (offline, instant) and what's pending "
            "(checking reaches Microsoft, so it needs internet). Cortex reports "
            "updates - Windows installs them, handling reboots safely.",
        ))
        if not IS_WINDOWS:
            note = QLabel("\u2139  Windows Update status is only available on Windows.")
            note.setObjectName("Muted")
            note.setWordWrap(True)
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
        self.check_btn = QPushButton("Check for Updates  \U0001F310")
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
        self.state.show_loading("Reading update status\u2026")
        self.win.run_worker(WUActivityWorker(), self._on_activity, self._fail)

    def _on_activity(self, activity: dict, history: list):
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
        self.check_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.statusBar().showMessage("Checking Windows Update (online)\u2026")
        self.win.run_worker(WUPendingWorker(), self._on_pending, self._fail)

    def _on_pending(self, updates: list):
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
        try:
            import os
            os.startfile("ms-settings:windowsupdate")  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Open failed", str(exc))

    def _fail(self, msg: str):
        self.check_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)
