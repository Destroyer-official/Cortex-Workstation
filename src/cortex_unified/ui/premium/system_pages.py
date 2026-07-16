"""Premium GUI pages for the real system-tool backends.

Each page wires a genuinely-functional backend module (privacy cleaner, startup
manager, process analyzer, app uninstaller, telemetry blocker, registry cleaner)
to the premium shell with background workers, confirmation dialogs, and
Windows-only guarding where relevant. Kept in its own module so ``window.py``
stays focused on the shell + core pages.
"""

from __future__ import annotations

import platform

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .states import StatePanel
from .widgets import (
    Card,
    CoreBars,
    StatCard,
    hline,
    icon_for_exe,
    placeholder_icon,
    title_block,
)
from .window import _Page, fmt_bytes

IS_WINDOWS = platform.system() == "Windows"


def _windows_only(page: _Page, feature: str) -> bool:
    """If not on Windows, show a notice on *page* and return True."""
    if IS_WINDOWS:
        return False
    note = QLabel(f"\u2139  {feature} is only available on Windows.")
    note.setObjectName("Muted")
    note.setWordWrap(True)
    page.v.addWidget(note)
    page.v.addStretch(1)
    return True


# =====================================================================
#  Workers
# =====================================================================

class PrivacyScanWorker(QObject):
    finished = Signal(dict, dict)   # browsers, traces
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.analyzers.privacy_cleaner import PrivacyCleaner
            pc = PrivacyCleaner()
            self.finished.emit(pc.scan_browsers(), pc.scan_system_traces())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class PrivacyCleanWorker(QObject):
    finished = Signal(bool)
    failed = Signal(str)

    def __init__(self, to_clean: dict, clean_system: bool):
        super().__init__()
        self._to_clean = to_clean
        self._clean_system = clean_system

    def run(self):
        try:
            from cortex_unified.analyzers.privacy_cleaner import PrivacyCleaner
            pc = PrivacyCleaner()
            ok = True
            for browser, items in self._to_clean.items():
                if not pc.clean_browser(browser, items):
                    ok = False
            if self._clean_system:
                pc.clean_system_traces()
            self.finished.emit(ok)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class StartupListWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.startup_manager import StartupManager
            self.finished.emit(StartupManager().list_startup_items())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class TaskSnapshotWorker(QObject):
    """Full task-manager snapshot: CPU, memory reconciliation + process list."""

    finished = Signal(dict)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.task_manager import TaskManager
            snap = TaskManager.instance().snapshot()
            if "error" in snap:
                self.failed.emit(snap["error"])
            else:
                self.finished.emit(snap)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class NetworkWorker(QObject):
    """Read-only snapshot of active network connections + a summary."""

    finished = Signal(list, dict)   # (connections, summary)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.network_monitor import NetworkMonitor
            mon = NetworkMonitor()
            conns = mon.connections()
            self.finished.emit([c.to_dict() for c in conns], mon.summarize(conns))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# =====================================================================
#  Cross-platform pages
# =====================================================================

class PrivacyPage(_Page):
    """Scan and sweep browser data + system privacy traces."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Privacy Shield",
            "Find and clear browser cache/cookies/history and system traces.",
        ))
        self._results: dict = {}

        row = QHBoxLayout()
        self.scan_btn = QPushButton("Scan Browsers & Traces")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.clicked.connect(self._scan)
        row.addWidget(self.scan_btn)
        row.addStretch(1)
        self.sweep_btn = QPushButton("Sweep Selected")
        self.sweep_btn.setObjectName("Danger")
        self.sweep_btn.setEnabled(False)
        self.sweep_btn.clicked.connect(self._sweep)
        row.addWidget(self.sweep_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Browser / Data", "Size"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner tree scrolls; route the wheel to one container.
        self.tree.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tree)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.v.addWidget(self.tree, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tree)
        self.v.addWidget(self.state, 1)

    def _scan(self):
        self.scan_btn.setEnabled(False)
        self.sweep_btn.setEnabled(False)
        self.state.show_loading("Scanning browsers & traces…")
        self.tree.clear()
        self.win.run_worker(PrivacyScanWorker(), self._on_scan, self._fail)

    def _on_scan(self, browsers: dict, traces: dict):
        self.scan_btn.setEnabled(True)
        self._results = {"browsers": browsers, "traces": traces}
        total = 0
        for browser, stats in browsers.items():
            node = QTreeWidgetItem(self.tree, [f"\U0001F310 {browser}", ""])
            node.setFlags(node.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            node.setCheckState(0, Qt.CheckState.Checked)
            bt = 0
            for cat, size in stats.items():
                if size <= 0:
                    continue
                child = QTreeWidgetItem(node, [cat, fmt_bytes(size)])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked)
                bt += size
            node.setText(1, fmt_bytes(bt))
            total += bt
        if traces:
            sysnode = QTreeWidgetItem(self.tree, ["\U0001F5A5 System Traces", ""])
            sysnode.setFlags(sysnode.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            sysnode.setCheckState(0, Qt.CheckState.Checked)
            st = 0
            for name, size in traces.items():
                child = QTreeWidgetItem(sysnode, [name, fmt_bytes(size)])
                st += size
            sysnode.setText(1, fmt_bytes(st))
            total += st
        self.tree.expandAll()
        if total == 0:
            self.state.show_empty("No privacy traces found.")
        else:
            self.state.clear()
        self.sweep_btn.setEnabled(total > 0)
        self.sweep_btn.setText(f"Sweep Selected ({fmt_bytes(total)})" if total else "Sweep Selected")
        self.win.statusBar().showMessage(
            "No privacy traces found." if total == 0 else f"Found {fmt_bytes(total)} of traces", 5000)

    def _sweep(self):
        to_clean: dict[str, list[str]] = {}
        clean_system = False
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            label = top.text(0)
            items = [top.child(j).text(0) for j in range(top.childCount())
                     if top.child(j).checkState(0) == Qt.CheckState.Checked]
            if not items:
                continue
            if "System Traces" in label:
                clean_system = True
            else:
                to_clean[label.replace("\U0001F310 ", "").strip()] = items
        if not to_clean and not clean_system:
            return
        confirm = QMessageBox.question(
            self, "Confirm privacy sweep",
            "Close your browsers first.\n\nPermanently delete the selected cookies, "
            "cache, history and session data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.sweep_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.run_worker(PrivacyCleanWorker(to_clean, clean_system), self._on_swept, self._fail)

    def _on_swept(self, ok: bool):
        self.progress.setVisible(False)
        msg = "Privacy traces cleared." if ok else "Some items could not be deleted (browser open?)."
        self.win.statusBar().showMessage(msg, 6000)
        QMessageBox.information(self, "Done", msg)
        self._scan()

    def _fail(self, msg: str):
        self.scan_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._scan)


class StartupPage(_Page):
    """List startup items and disable selected ones."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Startup Manager",
            "See what launches at boot and disable items to speed up startup.",
        ))
        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.disable_btn = QPushButton("Disable Selected")
        self.disable_btn.setObjectName("Danger")
        self.disable_btn.setEnabled(False)
        self.disable_btn.clicked.connect(self._disable)
        row.addWidget(self.disable_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Name", "Location", "Type", "Path"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)
        self._items: list[dict] = []
        self._autoload = self._load   # lazy-loaded on first visit
        self._loaded = False

    def _load(self):
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Reading startup items…")
        self.win.run_worker(StartupListWorker(), self._on_loaded, self._fail)

    def _on_loaded(self, items: list):
        self.refresh_btn.setEnabled(True)
        if not items:
            self.state.show_empty("No startup items found.")
        else:
            self.state.clear()
        self._items = items
        self.tbl.setRowCount(len(items))
        for r, it in enumerate(items):
            self.tbl.setItem(r, 0, QTableWidgetItem(str(it.get("name", ""))))
            self.tbl.setItem(r, 1, QTableWidgetItem(str(it.get("location", ""))))
            self.tbl.setItem(r, 2, QTableWidgetItem(str(it.get("type", ""))))
            self.tbl.setItem(r, 3, QTableWidgetItem(str(it.get("path", ""))))
        self.disable_btn.setEnabled(bool(items))
        self.win.statusBar().showMessage(f"{len(items)} startup items", 5000)

    def _disable(self):
        rows = sorted({idx.row() for idx in self.tbl.selectedIndexes()})
        if not rows:
            QMessageBox.information(self, "No selection", "Select startup items to disable.")
            return
        names = [self.tbl.item(r, 0).text() for r in rows]
        confirm = QMessageBox.question(
            self, "Disable startup items",
            f"Disable {len(names)} startup item(s)?\n\n" + "\n".join(names[:8]),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        from cortex_unified.system_tools.startup_manager import StartupManager
        sm = StartupManager()
        done = 0
        for r in rows:
            name = self.tbl.item(r, 0).text()
            itype = self.tbl.item(r, 2).text()
            try:
                if sm.disable_startup_item(name, itype):
                    done += 1
            except Exception:  # noqa: BLE001
                pass
        QMessageBox.information(self, "Done", f"Disabled {done} of {len(rows)} item(s).")
        self._load()

    def _fail(self, msg: str):
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


class _NumItem(QTableWidgetItem):
    """Table cell that sorts by a stored numeric value, not display text."""

    def __init__(self, display: str, value: float):
        super().__init__(display)
        self._value = value
        self.setData(Qt.ItemDataRole.UserRole, value)

    def __lt__(self, other):  # noqa: D401
        try:
            return self._value < other._value
        except AttributeError:
            return super().__lt__(other)


class ProcessesPage(_Page):
    """A proper task manager: live CPU/memory monitor + sortable, searchable
    process list with an honest breakdown of where memory actually goes."""

    _COLS = ["PID", "Name", "Description", "CPU %", "Memory", "Threads", "User", "Status"]

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Task Manager",
            "Live processes with CPU and memory. The summary reconciles the "
            "numbers Windows Task Manager leaves unexplained.",
        ))

        # -- summary cards --
        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.cpu_card = StatCard(self.p, "CPU", "\u2014")
        self.mem_card = StatCard(self.p, "Memory in use", "\u2014")
        self.proc_card = StatCard(self.p, "Processes", "\u2014")
        for c in (self.cpu_card, self.mem_card, self.proc_card):
            cards.addWidget(c)
        self.v.addLayout(cards)

        # -- per-core CPU bars --
        cores_card = Card(self.p)
        cc = QVBoxLayout(cores_card)
        cc.setContentsMargins(16, 10, 16, 10)
        cc_label = QLabel("Per-core CPU usage")
        cc_label.setObjectName("Muted")
        cc.addWidget(cc_label)
        self.core_bars = CoreBars(self.p)
        cc.addWidget(self.core_bars)
        self.v.addWidget(cores_card)

        # -- honest reconciliation line --
        self.breakdown = QLabel("")
        self.breakdown.setObjectName("Muted")
        self.breakdown.setWordWrap(True)
        self.breakdown.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.v.addWidget(self.breakdown)

        # -- controls --
        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter by name or PID\u2026")
        self.search.textChanged.connect(self._apply_filter)
        row.addWidget(self.search, 1)
        self.auto_chk = QCheckBox("Live")
        self.auto_chk.setChecked(True)
        self.auto_chk.toggled.connect(self._toggle_live)
        row.addWidget(self.auto_chk)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        self.kill_btn = QPushButton("End Task")
        self.kill_btn.setObjectName("Danger")
        self.kill_btn.setEnabled(False)
        self.kill_btn.clicked.connect(self._kill)
        row.addWidget(self.kill_btn)
        self.v.addLayout(row)

        self.tbl = QTableWidget(0, len(self._COLS))
        self.tbl.setHorizontalHeaderLabels(self._COLS)
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl.setSortingEnabled(True)
        self.tbl.sortByColumn(4, Qt.SortOrder.DescendingOrder)  # Memory desc
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.itemSelectionChanged.connect(self._on_select)
        self.tbl.itemDoubleClicked.connect(lambda *_: self._kill())
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._procs: list[dict] = []
        self._loading = False
        self._has_data = False
        self._selected_pid: int | None = None

        # Live timer: lightweight, and only ticks while the page is visible.
        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self._tick)

        self._autoload = self._start_live
        self._loaded = False

    # -- live lifecycle --
    def _start_live(self):
        self._load()
        if self.auto_chk.isChecked():
            self._timer.start()

    def _toggle_live(self, on: bool):
        if on:
            self._timer.start()
            self._tick()
        else:
            self._timer.stop()

    def _tick(self):
        if self.isVisible() and not self._loading:
            self._load()

    def _load(self):
        if self._loading:
            return
        self._loading = True
        if not self._has_data:
            self.state.show_loading("Loading processes…")
        self.refresh_btn.setEnabled(False)
        self.win.run_worker(TaskSnapshotWorker(), self._on_snapshot, self._fail)

    # -- render --
    def _on_snapshot(self, snap: dict):
        self._loading = False
        self.refresh_btn.setEnabled(True)
        cpu = snap["cpu"]
        mem = snap["memory"]
        self._procs = snap["processes"]
        if self._procs:
            self.state.clear()
        elif not self._has_data:
            self.state.show_empty("No processes to show.")
        self._has_data = True

        self.cpu_card.set_value(f"{cpu['total_percent']:.0f}%  ({cpu['cores']} cores)")
        self.mem_card.set_value(
            f"{fmt_bytes(mem['used'])} / {fmt_bytes(mem['total'])} ({mem['percent']:.0f}%)")
        self.proc_card.set_value(str(len(self._procs)))
        self.core_bars.set_values(cpu.get("per_core", []))
        self._render_breakdown(mem)
        self._apply_filter()

    def _render_breakdown(self, mem: dict):
        parts = [
            f"<b>Memory:</b> {fmt_bytes(mem['used'])} in use, "
            f"{fmt_bytes(mem['available'])} available of {fmt_bytes(mem['total'])} usable.",
        ]
        if "hardware_reserved" in mem:
            parts.append(
                f" You have {fmt_bytes(mem['installed'])} installed, but "
                f"{fmt_bytes(mem['hardware_reserved'])} is hardware-reserved, so "
                f"Windows can only use {fmt_bytes(mem['total'])}."
                "<br><span>That reserved block is your integrated GPU's memory. An "
                "integrated GPU has no VRAM of its own, so the BIOS sets aside a "
                "fixed slice of system RAM as its frame buffer (the 'UMA Frame "
                "Buffer Size' setting). You can lower it in BIOS to reclaim RAM, or "
                "raise it for more graphics headroom - it's reversible. Games can "
                "also borrow more 'shared GPU memory' on demand, which is returned "
                "afterwards.</span>")
        # Honest note about why the process list doesn't sum to "in use".
        parts.append(
            f"<br><span>Adding up the Memory column ("
            f"{fmt_bytes(mem['sum_process_ws'])} across all processes) won't equal "
            f"'in use'. Working sets <b>double-count shared memory</b> (one DLL "
            "loaded by many apps is counted in each), while the kernel, drivers "
            "and cached memory aren't shown per-process at all. So the column is "
            "great for ranking hogs, not for totalling.</span>")
        self.breakdown.setText("".join(parts))

    def _apply_filter(self):
        term = self.search.text().strip().lower()
        rows = [p for p in self._procs
                if not term or term in p["name"].lower() or term in str(p["pid"])
                or term in p.get("desc", "").lower()]
        self._fill(rows)

    def _fill(self, rows: list[dict]):
        self.tbl.setSortingEnabled(False)
        self.tbl.setRowCount(len(rows))
        for r, p in enumerate(rows):
            self.tbl.setItem(r, 0, _NumItem(str(p["pid"]), p["pid"]))
            name_item = QTableWidgetItem(p["name"] or "Unknown")
            # Real native icon where available; a token placeholder glyph when
            # the icon is unavailable so the row is never left blank (Req 8.3).
            icon = icon_for_exe(p.get("exe", ""))
            name_item.setIcon(icon if icon is not None else placeholder_icon(self.p))
            self.tbl.setItem(r, 1, name_item)
            self.tbl.setItem(r, 2, QTableWidgetItem(p.get("desc", "")))
            self.tbl.setItem(r, 3, _NumItem(f"{p['cpu']:.1f}", p["cpu"]))
            self.tbl.setItem(r, 4, _NumItem(fmt_bytes(p["rss"]), p["rss"]))
            self.tbl.setItem(r, 5, _NumItem(str(p["threads"]), p["threads"]))
            self.tbl.setItem(r, 6, QTableWidgetItem(p["user"]))
            self.tbl.setItem(r, 7, QTableWidgetItem(p["status"]))
        self.tbl.setSortingEnabled(True)
        self._restore_selection()

    def _on_select(self):
        sel = self.tbl.selectedIndexes()
        self.kill_btn.setEnabled(bool(sel))
        if sel:
            item = self.tbl.item(sel[0].row(), 0)
            if item:
                self._selected_pid = int(item.data(Qt.ItemDataRole.UserRole))

    def _restore_selection(self):
        if self._selected_pid is None:
            return
        for r in range(self.tbl.rowCount()):
            item = self.tbl.item(r, 0)
            if item and int(item.data(Qt.ItemDataRole.UserRole)) == self._selected_pid:
                self.tbl.selectRow(r)
                return

    def _kill(self):
        sel = self.tbl.selectedIndexes()
        if not sel:
            return
        r = sel[0].row()
        pid = int(self.tbl.item(r, 0).data(Qt.ItemDataRole.UserRole))
        name = self.tbl.item(r, 1).text()
        confirm = QMessageBox.warning(
            self, "End task",
            f"End task '{name}' (PID {pid})?\n\nUnsaved work in that program will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        from cortex_unified.system_tools.task_manager import TaskManager
        ok, msg = TaskManager.instance().end_process(pid)
        if not ok:
            QMessageBox.warning(self, "Could not end task", msg)
        self.win.statusBar().showMessage(msg, 5000)
        self._selected_pid = None
        self._load()

    def _fail(self, msg: str):
        self._loading = False
        self.refresh_btn.setEnabled(True)
        if not self._has_data:
            self.state.show_error(msg, on_retry=self._load)
        else:
            self.win.statusBar().showMessage(f"Refresh failed: {msg}", 4000)


class NetworkPage(_Page):
    """Security-minded view of active network connections and their owners."""

    _COLS = ["Process", "PID", "Proto", "Local address", "Remote address",
             "State", "Service"]

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Network Monitor",
            "See which programs are talking to the network, where to, over which "
            "protocol and port. Read-only - it helps you spot suspicious "
            "connections or exposed services; it doesn't block traffic.",
        ))

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.card_est = StatCard(self.p, "Established", "\u2014")
        self.card_listen = StatCard(self.p, "Listening", "\u2014")
        self.card_ext = StatCard(self.p, "External (internet)", "\u2014")
        self.card_pub = StatCard(self.p, "Public listeners", "\u2014")
        for c in (self.card_est, self.card_listen, self.card_ext, self.card_pub):
            cards.addWidget(c)
        self.v.addLayout(cards)

        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter by process, address, port or service\u2026")
        self.search.textChanged.connect(self._apply_filter)
        row.addWidget(self.search, 1)
        self.only_risky = QCheckBox("Only external / public")
        self.only_risky.toggled.connect(self._apply_filter)
        row.addWidget(self.only_risky)
        self.auto_chk = QCheckBox("Live")
        self.auto_chk.setChecked(True)
        self.auto_chk.toggled.connect(self._toggle_live)
        row.addWidget(self.auto_chk)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        self.kill_btn = QPushButton("End Owning Task")
        self.kill_btn.setObjectName("Danger")
        self.kill_btn.setEnabled(False)
        self.kill_btn.clicked.connect(self._kill)
        row.addWidget(self.kill_btn)
        self.v.addLayout(row)

        self.tbl = QTableWidget(0, len(self._COLS))
        self.tbl.setHorizontalHeaderLabels(self._COLS)
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl.setSortingEnabled(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.itemSelectionChanged.connect(
            lambda: self.kill_btn.setEnabled(bool(self.tbl.selectedIndexes())))
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self.hint = QLabel("")
        self.hint.setObjectName("Muted")
        self.hint.setWordWrap(True)
        self.v.addWidget(self.hint)

        self._conns: list[dict] = []
        self._loading = False
        self._has_data = False

        self._timer = QTimer(self)
        self._timer.setInterval(3000)
        self._timer.timeout.connect(self._tick)

        self._autoload = self._start_live
        self._loaded = False

    def _start_live(self):
        self._load()
        if self.auto_chk.isChecked():
            self._timer.start()

    def _toggle_live(self, on: bool):
        if on:
            self._timer.start()
            self._tick()
        else:
            self._timer.stop()

    def _tick(self):
        if self.isVisible() and not self._loading:
            self._load()

    def _load(self):
        if self._loading:
            return
        self._loading = True
        if not self._has_data:
            self.state.show_loading("Loading connections…")
        self.refresh_btn.setEnabled(False)
        self.win.run_worker(NetworkWorker(), self._on_loaded, self._fail)

    def _on_loaded(self, conns: list, summary: dict):
        self._loading = False
        self.refresh_btn.setEnabled(True)
        self._conns = conns
        if self._conns:
            self.state.clear()
        elif not self._has_data:
            self.state.show_empty("No active network connections.")
        self._has_data = True
        self.card_est.set_value(str(summary.get("established", 0)))
        self.card_listen.set_value(str(summary.get("listening", 0)))
        self.card_ext.set_value(str(summary.get("external", 0)))
        self.card_pub.set_value(str(summary.get("public_listeners", 0)))
        if not conns:
            self.hint.setText("No connections listed. Full visibility of every "
                              "process's sockets needs Administrator.")
        else:
            self.hint.setText("Rows in orange listen on all interfaces (network-"
                              "reachable); rows in red are live connections out to "
                              "the internet. Neither is automatically bad - just "
                              "confirm you recognize the program.")
        self._apply_filter()

    def _apply_filter(self):
        term = self.search.text().strip().lower()
        risky_only = self.only_risky.isChecked()
        rows = []
        for c in self._conns:
            if risky_only and not (c["remote_external"] or c["listening_public"]):
                continue
            hay = f"{c['process']} {c['local']} {c['remote']} {c['service']} {c['pid']}".lower()
            if term and term not in hay:
                continue
            rows.append(c)
        self._fill(rows)

    def _fill(self, rows: list[dict]):
        self.tbl.setSortingEnabled(False)
        self.tbl.setRowCount(len(rows))
        for r, c in enumerate(rows):
            proc_item = QTableWidgetItem(c["process"] or "?")
            proc_item.setData(Qt.ItemDataRole.UserRole, c["pid"])
            # Real native icon where available, else a token placeholder glyph
            # so the connection's process is never shown iconless (Req 8.3).
            icon = icon_for_exe(c.get("process_exe", ""))
            proc_item.setIcon(icon if icon is not None else placeholder_icon(self.p))
            if c.get("process_desc"):
                proc_item.setToolTip(c["process_desc"])
            pid_item = _NumItem(str(c["pid"]) if c["pid"] else "-", c["pid"] or 0)
            # Non-color signalling (Req 10.5): the risk colour must be paired
            # with a text label so the "external"/"public" state is not conveyed
            # by colour alone. Append a marker to the address the risk relates to.
            local_text = c["local"]
            remote_text = c["remote"]
            colour = None
            risk_tip = ""
            if c["remote_external"]:
                colour = Qt.GlobalColor.red
                remote_text = f"{c['remote']}  \u26A0 external"
                risk_tip = "Connected to an external (non-private) address"
            elif c["listening_public"]:
                colour = Qt.GlobalColor.darkYellow
                local_text = f"{c['local']}  \u26A0 public"
                risk_tip = "Listening on a publicly-reachable address"
            items = [
                proc_item, pid_item,
                QTableWidgetItem(c["protocol"]),
                QTableWidgetItem(local_text),
                QTableWidgetItem(remote_text),
                QTableWidgetItem(c["status"]),
                QTableWidgetItem(c["service"]),
            ]
            for col, it in enumerate(items):
                if colour is not None:
                    it.setForeground(colour)
                    if risk_tip:
                        it.setToolTip(risk_tip)
                self.tbl.setItem(r, col, it)
        self.tbl.setSortingEnabled(True)

    def _kill(self):
        sel = self.tbl.selectedIndexes()
        if not sel:
            return
        r = sel[0].row()
        pid = self.tbl.item(r, 0).data(Qt.ItemDataRole.UserRole)
        name = self.tbl.item(r, 0).text()
        if not pid:
            QMessageBox.information(self, "No owner",
                                    "This connection has no ownable process (kernel/system).")
            return
        confirm = QMessageBox.warning(
            self, "End owning task",
            f"End '{name}' (PID {pid}) to close its connection(s)?\n\n"
            "Unsaved work in that program will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        from cortex_unified.system_tools.task_manager import TaskManager
        ok, msg = TaskManager.instance().end_process(int(pid))
        if not ok:
            QMessageBox.warning(self, "Could not end task", msg)
        self.win.statusBar().showMessage(msg, 5000)
        self._load()

    def _fail(self, msg: str):
        self._loading = False
        self.refresh_btn.setEnabled(True)
        if not self._has_data:
            self.state.show_error(msg, on_retry=self._load)
        else:
            self.win.statusBar().showMessage(f"Refresh failed: {msg}", 4000)


# =====================================================================
#  Windows-only workers
# =====================================================================

class UninstallerListWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.app_uninstaller import AppUninstaller
            self.finished.emit(AppUninstaller().get_installed_apps())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class TelemetryStatusWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.telemetry_blocker import TelemetryBlocker
            self.finished.emit(TelemetryBlocker().check_status())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class TelemetryApplyWorker(QObject):
    finished = Signal(bool)
    failed = Signal(str)

    def __init__(self, restore: bool):
        super().__init__()
        self._restore = restore

    def run(self):
        try:
            from cortex_unified.system_tools.telemetry_blocker import TelemetryBlocker
            tb = TelemetryBlocker()
            ok = tb.restore_defaults() if self._restore else tb.block_telemetry()
            self.finished.emit(ok)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class RegistryScanWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.registry_cleaner import RegistryCleaner
            self.finished.emit(RegistryCleaner().scan_orphaned_entries())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class RegistryCleanWorker(QObject):
    finished = Signal(int, str)   # (removed_count, backup_path)
    failed = Signal(str)

    def __init__(self, entries: list):
        super().__init__()
        self._entries = entries

    def run(self):
        try:
            from cortex_unified.system_tools.registry_cleaner import RegistryCleaner
            rc = RegistryCleaner()
            backup = rc.backup_registry() or ""
            removed = 0
            for entry in self._entries:
                if rc.remove_orphaned_entry(entry):
                    removed += 1
            self.finished.emit(removed, backup)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# =====================================================================
#  Windows-only pages
# =====================================================================

class UninstallerPage(_Page):
    """List installed apps and launch their official uninstaller (Windows)."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Deep Uninstaller",
            "Registry-based app discovery. Launches each app's official "
            "uninstaller. Select multiple apps (Ctrl/Shift-click) to uninstall "
            "them one after another.",
        ))
        if _windows_only(self, "The Deep Uninstaller"):
            return
        self._apps: list[dict] = []

        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search installed applications\u2026")
        self.search.textChanged.connect(self._filter)
        row.addWidget(self.search, 1)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        self.uninstall_btn = QPushButton("Uninstall Selected")
        self.uninstall_btn.setObjectName("Danger")
        self.uninstall_btn.setEnabled(False)
        self.uninstall_btn.clicked.connect(self._uninstall)
        row.addWidget(self.uninstall_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["Name", "Publisher", "Version"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.itemSelectionChanged.connect(
            lambda: self.uninstall_btn.setEnabled(bool(self.tbl.selectedIndexes())))
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)
        self._autoload = self._load   # lazy-loaded on first visit
        self._loaded = False

    def _load(self):
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Listing installed apps…")
        self.win.run_worker(UninstallerListWorker(), self._on_loaded, self._fail)

    def _on_loaded(self, apps: list):
        self.refresh_btn.setEnabled(True)
        if not apps:
            self.state.show_empty("No installed applications found.")
        else:
            self.state.clear()
        self._apps = apps
        self._render(apps)
        self.win.statusBar().showMessage(f"{len(apps)} installed applications", 5000)

    def _render(self, apps: list):
        self.tbl.setRowCount(len(apps))
        for r, a in enumerate(apps):
            name_item = QTableWidgetItem(a.get("name", "?"))
            name_item.setData(Qt.ItemDataRole.UserRole, a)
            self.tbl.setItem(r, 0, name_item)
            self.tbl.setItem(r, 1, QTableWidgetItem(a.get("publisher", "")))
            self.tbl.setItem(r, 2, QTableWidgetItem(a.get("display_version", "")))

    def _filter(self, text: str):
        t = text.lower()
        self._render([a for a in self._apps
                      if t in a.get("name", "").lower() or t in a.get("publisher", "").lower()])

    def _uninstall(self):
        rows = sorted({idx.row() for idx in self.tbl.selectedIndexes()})
        apps = [self.tbl.item(r, 0).data(Qt.ItemDataRole.UserRole)
                for r in rows if self.tbl.item(r, 0)]
        apps = [a for a in apps if a]
        if not apps:
            return
        names = "\n".join(f"  \u2022 {a.get('name')}" for a in apps)
        confirm = QMessageBox.question(
            self, "Confirm uninstall",
            f"Launch the official uninstaller for {len(apps)} app(s)?\n\n{names}\n\n"
            "Each uninstaller opens in turn - complete one before the next appears.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        from cortex_unified.system_tools.app_uninstaller import AppUninstaller
        uninstaller = AppUninstaller()
        launched = sum(1 for a in apps if uninstaller.uninstall_app(a))
        if launched:
            QMessageBox.information(
                self, "Uninstaller launched",
                f"Launched {launched} of {len(apps)} uninstaller(s). "
                "Complete each one, then click Refresh.")
        else:
            QMessageBox.warning(self, "Error",
                                "Could not launch the uninstaller(s) (may need elevation).")

    def _fail(self, msg: str):
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


class TelemetryPage(_Page):
    """Block / restore Windows telemetry (Windows, admin required to apply)."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Telemetry Blocker",
            "Disable Windows diagnostic/tracking features via the registry.",
        ))
        if _windows_only(self, "The Telemetry Blocker"):
            return

        self.status_lbl = QLabel("Checking\u2026")
        self.status_lbl.setWordWrap(True)
        self.v.addWidget(self.status_lbl)

        row = QHBoxLayout()
        self.block_btn = QPushButton("Block All Telemetry")
        self.block_btn.setObjectName("Primary")
        self.block_btn.clicked.connect(lambda: self._apply(False))
        row.addWidget(self.block_btn)
        self.restore_btn = QPushButton("Restore Defaults")
        self.restore_btn.clicked.connect(lambda: self._apply(True))
        row.addWidget(self.restore_btn)
        row.addStretch(1)
        self.v.addLayout(row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Telemetry feature", "Status"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner tree scrolls; route the wheel to one container.
        self.tree.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tree)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.v.addWidget(self.tree, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tree)
        self.v.addWidget(self.state, 1)
        self._autoload = self._refresh   # lazy-loaded on first visit
        self._loaded = False

    def _refresh(self):
        self.state.show_loading("Reading telemetry status…")
        self.win.run_worker(TelemetryStatusWorker(), self._on_status, self._fail)

    def _on_status(self, status: dict):
        self.state.clear()
        self.tree.clear()
        blocked = sum(1 for v in status.values() if v)
        total = len(status)
        for label, is_blocked in status.items():
            QTreeWidgetItem(self.tree, [label, "\u2705 Blocked" if is_blocked else "\u26A0 Active"])
        self.status_lbl.setText(f"{blocked} of {total} telemetry features blocked.")

    def _apply(self, restore: bool):
        action = "restore Windows defaults" if restore else "block all telemetry"
        confirm = QMessageBox.question(
            self, "Confirm",
            f"This will modify the Windows registry to {action}.\n"
            "Administrator privileges are required. Proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.block_btn.setEnabled(False)
        self.restore_btn.setEnabled(False)
        self.win.run_worker(TelemetryApplyWorker(restore), self._on_applied, self._fail)

    def _on_applied(self, ok: bool):
        self.block_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        if not ok:
            QMessageBox.warning(self, "Partial", "Some changes failed. Run as Administrator.")
        self._refresh()

    def _fail(self, msg: str):
        self.block_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._refresh)


class RegistryPage(_Page):
    """Scan for orphaned registry entries and remove them with a backup first."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Registry Cleaner",
            "Find orphaned entries (missing targets). A .reg backup is exported before removal.",
        ))
        if _windows_only(self, "The Registry Cleaner"):
            return
        self._entries: list[dict] = []

        warn = QLabel("\u26A0  Registry edits can affect system behavior. A backup is exported first.")
        warn.setStyleSheet(f"color: {self.p.warning}; font-weight: 600;")
        warn.setWordWrap(True)
        self.v.addWidget(warn)

        row = QHBoxLayout()
        self.scan_btn = QPushButton("Scan Registry")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.clicked.connect(self._scan)
        row.addWidget(self.scan_btn)
        row.addStretch(1)
        self.clean_btn = QPushButton("Clean All Found")
        self.clean_btn.setObjectName("Danger")
        self.clean_btn.setEnabled(False)
        self.clean_btn.clicked.connect(self._clean)
        row.addWidget(self.clean_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["Subkey", "Hive", "Reason"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

    def _scan(self):
        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.state.show_loading("Scanning registry…")
        self.tbl.setRowCount(0)
        self.win.run_worker(RegistryScanWorker(), self._on_scan, self._fail)

    def _on_scan(self, entries: list):
        self.scan_btn.setEnabled(True)
        if not entries:
            self.state.show_empty("No orphaned registry entries found.")
        else:
            self.state.clear()
        self._entries = entries
        self.tbl.setRowCount(len(entries))
        for r, e in enumerate(entries):
            self.tbl.setItem(r, 0, QTableWidgetItem(str(e.get("path", ""))))
            self.tbl.setItem(r, 1, QTableWidgetItem(str(e.get("hive", ""))))
            self.tbl.setItem(r, 2, QTableWidgetItem(str(e.get("reason", ""))))
        self.clean_btn.setEnabled(bool(entries))
        self.win.statusBar().showMessage(f"{len(entries)} orphaned entries found", 5000)

    def _clean(self):
        if not self._entries:
            return
        confirm = QMessageBox.warning(
            self, "Confirm registry cleanup",
            f"Remove {len(self._entries)} orphaned entries?\n\n"
            "A .reg backup is exported first. Administrator privileges may be required.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.clean_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.run_worker(RegistryCleanWorker(list(self._entries)), self._on_clean, self._fail)

    def _on_clean(self, removed: int, backup: str):
        self.progress.setVisible(False)
        note = f"Removed {removed} entries." + (f"\nBackup: {backup}" if backup else "")
        QMessageBox.information(self, "Done", note)
        self.win.statusBar().showMessage(f"Removed {removed} registry entries", 6000)
        self._scan()

    def _fail(self, msg: str):
        self.scan_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._scan)
