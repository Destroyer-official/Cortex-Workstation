"""Premium GUI pages for the real system-tool backends.

Each page wires a functional backend module (privacy cleaner, startup
manager, process analyzer, app uninstaller, telemetry blocker, registry cleaner)
to the premium shell with background workers, confirmation dialogs, and
Windows-only guarding where relevant. Kept in its own module so ``window.py``
stays focused on the shell + core pages.
"""

from __future__ import annotations

import sys

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
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from cortex_unified.licensing import Feature

from . import icons
from .states import StatePanel
from .tablemodel import Column, bind_table
from .widgets import (
    Card,
    CoreBars,
    StatCard,
    icon_for_exe,
    placeholder_icon,
    require_feature,
    status_note,
    title_block,
)
from .window import _Page, fmt_bytes

# ``sys.platform`` is an interned constant; ``platform.system()`` costs ~50 ms
# on its first call because it populates ``uname()`` via WMI on Windows.
IS_WINDOWS = sys.platform == "win32"


def _windows_only(page: _Page, feature: str) -> bool:
    """Return True (after showing a notice on *page*) unless on Windows."""
    if IS_WINDOWS:
        return False
    note = status_note(
        page.p, "info", f"{feature} is only available on Windows.")
    page.v.addWidget(note)
    page.v.addStretch(1)
    return True


# =====================================================================
#  Workers
# =====================================================================

class PrivacyScanWorker(QObject):
    """PrivacyScanWorker class."""
    finished = Signal(dict, dict)   # browsers, traces
    failed = Signal(str)

    def run(self):
        """run."""
        try:
            from cortex_unified.analyzers.privacy_cleaner import PrivacyCleaner
            pc = PrivacyCleaner()
            self.finished.emit(pc.scan_browsers(), pc.scan_system_traces())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class PrivacyCleanWorker(QObject):
    """PrivacyCleanWorker class."""
    finished = Signal(bool)
    failed = Signal(str)

    def __init__(self, to_clean: dict, clean_system: bool):
        """__init__."""
        super().__init__()
        self._to_clean = to_clean
        self._clean_system = clean_system

    def run(self):
        """run."""
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
    """StartupListWorker class."""
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        """run."""
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
        """run."""
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
        """run."""
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
        """__init__."""
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
        """_scan."""
        self.scan_btn.setEnabled(False)
        self.sweep_btn.setEnabled(False)
        self.state.show_loading("Scanning browsers & traces…")
        self.tree.clear()
        self.win.run_worker(PrivacyScanWorker(), self._on_scan, self._fail)

    def _on_scan(self, browsers: dict, traces: dict):
        """_on_scan."""
        self.scan_btn.setEnabled(True)
        self._results = {"browsers": browsers, "traces": traces}
        total = 0
        for browser, stats in browsers.items():
            node = QTreeWidgetItem(self.tree, [browser, ""])
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
            sysnode = QTreeWidgetItem(self.tree, ["System Traces", ""])
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
        """_sweep."""
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
        """_on_swept."""
        self.progress.setVisible(False)
        msg = "Privacy traces cleared." if ok else "Some items could not be deleted (browser open?)."
        self.win.statusBar().showMessage(msg, 6000)
        QMessageBox.information(self, "Done", msg)
        self._scan()

    def _fail(self, msg: str):
        """_fail."""
        self.scan_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._scan)


class StartupPage(_Page):
    """List startup items and disable selected ones."""

    def __init__(self, win):
        """__init__."""
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
        """_load."""
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Reading startup items…")
        self.win.run_worker(StartupListWorker(), self._on_loaded, self._fail)

    def _on_loaded(self, items: list):
        """_on_loaded."""
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
        """_disable."""
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
        """_fail."""
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


class ProcessesPage(_Page):
    """Live task-manager page: CPU/memory monitor plus a sortable, searchable
    process list, with a breakdown reconciling where memory actually goes."""

    def __init__(self, win):
        """__init__."""
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

        # -- memory reconciliation --
        # A one-line summary is always shown; the detailed explanation lives
        # behind a progressive-disclosure toggle (collapsed by default) so the
        # big paragraph never squeezes the process table or forces the page to
        # scroll, and its expensive rich-text relayout doesn't run every tick.
        self.mem_summary = QLabel("")
        self.mem_summary.setObjectName("Muted")
        self.mem_summary.setWordWrap(True)
        self.v.addWidget(self.mem_summary)

        self.why_btn = QPushButton("Why don't these numbers add up?")
        self.why_btn.setObjectName("Ghost")
        self.why_btn.setCheckable(True)
        self.why_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Disclosure state shown by a real chevron icon rather than a codepoint
        # appended to the label.
        self.why_btn.setIcon(icons.icon("chevron-down", 12, self.p.text_muted))
        self.why_btn.setIconSize(icons.icon_size(12))
        self.why_btn.toggled.connect(self._toggle_why)
        self.v.addWidget(self.why_btn, 0, Qt.AlignmentFlag.AlignLeft)

        self.breakdown = QLabel("")
        self.breakdown.setObjectName("Muted")
        self.breakdown.setWordWrap(True)
        self.breakdown.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.breakdown.setVisible(False)
        self.v.addWidget(self.breakdown)
        self._breakdown_html = ""

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

        # Model/view instead of an item-based table. This is the hottest list in
        # the app: a QTableWidget allocated one QTableWidgetItem per cell -
        # ~150-500 rows x 8 columns, torn down and rebuilt every 2 seconds while
        # "Live" is checked, i.e. up to ~4,000 throwaway objects per tick, all
        # for the ~20 rows a user can actually see. A QAbstractTableModel hands
        # the view only the cells it paints, so the cost tracks the viewport
        # rather than the process count. The typed sort role is the other half of
        # the win: item tables sort on the display string, which is why "9 MB"
        # used to land above "10 MB" unless a cell subclass intervened.
        self.tbl = QTableView()
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        # Row selection, single selection, read-only, alternating rows, hidden
        # vertical header and the per-column stretch all come from bind_table.
        self.table = bind_table(
            self.tbl, self._columns(),
            sort_column=4, sort_order=Qt.SortOrder.DescendingOrder,  # Memory desc
        )
        # A QTableView has no itemSelectionChanged - the selection model is the
        # equivalent, and it also fires for keyboard navigation.
        self.tbl.selectionModel().selectionChanged.connect(self._on_select)
        self.tbl.doubleClicked.connect(lambda *_: self._kill())
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._procs: list[dict] = []
        self._loading = False
        self._has_data = False
        self._selected_pid: int | None = None

        # Live refresh timer; _tick skips work while the page is hidden or a
        # load is in flight.
        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self._tick)

        self._autoload = self._start_live
        self._loaded = False

    # -- columns --
    def _columns(self) -> list[Column]:
        """Declare the eight process columns once, instead of filling cells.

        Numeric columns carry a ``sort_key`` returning the raw number, so the
        cell can show a human string ("1.4 GB", "3.5") while the proxy still
        orders on the value behind it. Those same columns opt out of the search
        so typing "8" filters on names, PIDs and descriptions - the fields the
        old python-side filter looked at - rather than matching stray digits in
        a byte count.
        """
        def name_icon(p: dict):
            """name_icon."""
            # Real native icon where available; a token placeholder glyph when
            # the icon is unavailable so the row is never left blank (Req 8.3).
            icon = icon_for_exe(p.get("exe", ""))
            return icon if icon is not None else placeholder_icon(self.p)

        return [
            Column("PID", "pid", sort_key=lambda p: p["pid"]),
            Column("Name", lambda p: p["name"] or "Unknown",
                   icon=name_icon, stretch=True),
            Column("Description", lambda p: p.get("desc", ""), stretch=True),
            Column("CPU %", lambda p: f"{p['cpu']:.1f}",
                   sort_key=lambda p: p["cpu"], searchable=False),
            Column("Memory", lambda p: fmt_bytes(p["rss"]),
                   sort_key=lambda p: p["rss"], searchable=False),
            Column("Threads", "threads",
                   sort_key=lambda p: p["threads"], searchable=False),
            Column("User", "user"),
            Column("Status", "status"),
        ]

    # -- live lifecycle --
    def _start_live(self):
        """_start_live."""
        self._load()
        if self.auto_chk.isChecked():
            self._timer.start()

    def _toggle_live(self, on: bool):
        """_toggle_live."""
        if on:
            self._timer.start()
            self._tick()
        else:
            self._timer.stop()

    def _tick(self):
        """_tick."""
        if self.isVisible() and not self._loading:
            self._load()

    def _load(self):
        """_load."""
        if self._loading:
            return
        self._loading = True
        if not self._has_data:
            self.state.show_loading("Loading processes…")
        self.refresh_btn.setEnabled(False)
        self.win.run_worker(TaskSnapshotWorker(), self._on_snapshot, self._fail)

    # -- render --
    def _on_snapshot(self, snap: dict):
        """_on_snapshot."""
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
        # One model reset per snapshot, holding every process. The proxy keeps
        # the live search term and the user's sort order across the swap, so a
        # refresh no longer means re-deriving a filtered python list.
        self.table.set_records(self._procs)
        self._restore_selection()

    def _render_breakdown(self, mem: dict):
        """_render_breakdown."""
        # Always-visible one-liner (cheap).
        self.mem_summary.setText(
            f"<b>Memory:</b> {fmt_bytes(mem['used'])} in use, "
            f"{fmt_bytes(mem['available'])} available of {fmt_bytes(mem['total'])} usable.")
        # Build the detailed explanation, but only push it into the rich-text
        # label when it actually changed AND the section is expanded - a big
        # word-wrapped relayout on every live tick is a needless jank source.
        html = self._build_breakdown_html(mem)
        if html != self._breakdown_html:
            self._breakdown_html = html
            if self.breakdown.isVisible():
                self.breakdown.setText(html)

    def _build_breakdown_html(self, mem: dict) -> str:
        """_build_breakdown_html."""
        parts = []
        if "hardware_reserved" in mem:
            parts.append(
                f"You have {fmt_bytes(mem['installed'])} installed, but "
                f"{fmt_bytes(mem['hardware_reserved'])} is hardware-reserved, so "
                f"Windows can only use {fmt_bytes(mem['total'])}."
                "<br><span>That reserved block is your integrated GPU's memory. An "
                "integrated GPU has no VRAM of its own, so the BIOS sets aside a "
                "fixed slice of system RAM as its frame buffer (the 'UMA Frame "
                "Buffer Size' setting). You can lower it in BIOS to reclaim RAM, or "
                "raise it for more graphics headroom - it's reversible. Games can "
                "also borrow more 'shared GPU memory' on demand, which is returned "
                "afterwards.</span><br><br>")
        parts.append(
            f"<span>Adding up the Memory column ("
            f"{fmt_bytes(mem['sum_process_ws'])} across all processes) won't equal "
            f"'in use'. Working sets <b>double-count shared memory</b> (one DLL "
            "loaded by many apps is counted in each), while the kernel, drivers "
            "and cached memory aren't shown per-process at all. So the column is "
            "great for ranking hogs, not for totalling.</span>")
        return "".join(parts)

    def _toggle_why(self, on: bool):
        """_toggle_why."""
        self.why_btn.setText(
            "Hide the memory explanation" if on
            else "Why don't these numbers add up?")
        self.why_btn.setIcon(icons.icon(
            "chevron-up" if on else "chevron-down", 12, self.p.text_muted))
        self.breakdown.setVisible(on)
        if on and self._breakdown_html:
            self.breakdown.setText(self._breakdown_html)

    def _apply_filter(self):
        """_apply_filter."""
        # Search is the proxy's job now. The model keeps the whole snapshot and
        # the view simply stops asking for rows that don't match, so a keystroke
        # costs no list copy and no cell rebuild - and the "Processes" card keeps
        # reporting the true total rather than the filtered subset.
        self.table.set_filter_text(self.search.text())
        self._restore_selection()

    def _on_select(self, *_):
        """_on_select."""
        record = self.table.selected_record()
        self.kill_btn.setEnabled(record is not None)
        if record is not None:
            # Key the selection on the PID, never on the view row: the proxy
            # reorders rows on every sort, filter and live refresh.
            self._selected_pid = record["pid"]

    def _restore_selection(self):
        """_restore_selection."""
        if self._selected_pid is None:
            return
        self.table.select_where(lambda p: p["pid"] == self._selected_pid)

    def _kill(self):
        """_kill."""
        record = self.table.selected_record()
        if record is None:
            return
        pid = int(record["pid"])
        name = record["name"] or "Unknown"
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
        """_fail."""
        self._loading = False
        self.refresh_btn.setEnabled(True)
        if not self._has_data:
            self.state.show_error(msg, on_retry=self._load)
        else:
            self.win.statusBar().showMessage(f"Refresh failed: {msg}", 4000)


class NetworkPage(_Page):
    """Security-minded view of active network connections and their owners."""

    def __init__(self, win):
        """__init__."""
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

        # Model/view instead of an item-based table. This table refreshes more
        # often than any other: the live timer reloads every row every 3 seconds,
        # and the item table rebuilt one QTableWidgetItem per cell each tick
        # (7 columns x however many sockets are open) whether or not the row was
        # on screen. The view now asks the model only for the rows it paints.
        #
        # The risk colouring survives via ``Column.foreground`` - red for a live
        # connection out to the internet, dark yellow for a listener bound to a
        # publicly-reachable address. Colour is never the only cue (Req 10.5):
        # the same rows carry an "(external)"/"(public)" text marker on the
        # address the risk relates to, plus an explanatory tooltip.
        self.tbl = QTableView()
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        # Row selection, single selection, read-only, alternating rows, hidden
        # vertical header and the per-column stretch all come from bind_table.
        # No initial sort column: arrival order is the order the OS reported the
        # sockets in, which is what this page showed before.
        self.table = bind_table(self.tbl, self._columns())
        self.tbl.selectionModel().selectionChanged.connect(
            lambda *_: self.kill_btn.setEnabled(
                self.table.selected_record() is not None))
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
        """_start_live."""
        self._load()
        if self.auto_chk.isChecked():
            self._timer.start()

    def _toggle_live(self, on: bool):
        """_toggle_live."""
        if on:
            self._timer.start()
            self._tick()
        else:
            self._timer.stop()

    def _tick(self):
        """_tick."""
        if self.isVisible() and not self._loading:
            self._load()

    def _load(self):
        """_load."""
        if self._loading:
            return
        self._loading = True
        if not self._has_data:
            self.state.show_loading("Loading connections…")
        self.refresh_btn.setEnabled(False)
        self.win.run_worker(NetworkWorker(), self._on_loaded, self._fail)

    def _on_loaded(self, conns: list, summary: dict):
        """_on_loaded."""
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
        """_apply_filter."""
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

    # -- risk classification ------------------------------------------------
    #
    # One helper decides a row's risk class and everything else (colour, text
    # marker, tooltip) reads off it, so the three cues can never disagree.

    _RISK_COLOUR = {
        "external": Qt.GlobalColor.red,
        "public": Qt.GlobalColor.darkYellow,
    }
    _RISK_TIP = {
        "external": "Connected to an external (non-private) address",
        "public": "Listening on a publicly-reachable address",
    }

    @staticmethod
    def _risk(c: dict) -> str:
        """``"external"``, ``"public"`` or ``""`` for a connection.

        External wins over public: an established connection out to the internet
        is the stronger signal, and it is what the page checked first before the
        model/view migration.
        """
        if c["remote_external"]:
            return "external"
        if c["listening_public"]:
            return "public"
        return ""

    def _risk_colour(self, c: dict):
        """_risk_colour."""
        return self._RISK_COLOUR.get(self._risk(c))

    def _risk_tooltip(self, c: dict) -> str:
        """_risk_tooltip."""
        return self._RISK_TIP.get(self._risk(c), "")

    def _process_icon(self, c: dict):
        """Real native icon where available, else a token placeholder glyph, so
        the connection's owning process is never shown iconless (Req 8.3)."""
        icon = icon_for_exe(c.get("process_exe", ""))
        return icon if icon is not None else placeholder_icon(self.p)

    def _columns(self) -> list[Column]:
        """_columns."""
        colour = self._risk_colour
        tip = self._risk_tooltip
        return [
            # The risk tooltip takes precedence over the process description on
            # this column, which is what the item table did too (it overwrote the
            # description tooltip when the row was risky).
            Column("Process", lambda c: c["process"] or "?", stretch=True,
                   icon=self._process_icon,
                   tooltip=lambda c: tip(c) or (c.get("process_desc") or ""),
                   foreground=colour),
            # Numeric sort key, so PID 9 does not sort above PID 100.
            Column("PID", lambda c: str(c["pid"]) if c["pid"] else "-",
                   sort_key=lambda c: c["pid"] or 0,
                   tooltip=tip, foreground=colour),
            Column("Proto", "protocol", tooltip=tip, foreground=colour),
            Column("Local address", self._local_text,
                   tooltip=tip, foreground=colour),
            Column("Remote address", self._remote_text, stretch=True,
                   tooltip=tip, foreground=colour),
            Column("State", "status", tooltip=tip, foreground=colour),
            Column("Service", "service", tooltip=tip, foreground=colour),
        ]

    def _local_text(self, c: dict) -> str:
        """_local_text."""
        if self._risk(c) == "public":
            return f"{c['local']}  (public)"
        return c["local"]

    def _remote_text(self, c: dict) -> str:
        """_remote_text."""
        if self._risk(c) == "external":
            return f"{c['remote']}  (external)"
        return c["remote"]

    def _fill(self, rows: list[dict]):
        """_fill."""
        # Keep the user's selection across the 3-second live refresh. The item
        # table lost it on every tick because setRowCount destroyed the items,
        # which made "End Owning Task" nearly unusable while Live was on. The
        # row is re-found by socket identity rather than by row number, so it
        # also survives whatever sort the user has applied.
        selected = self.table.selected_record()
        self.table.set_records(rows)
        if selected is not None:
            key = self._socket_key(selected)
            self.table.select_where(lambda c: self._socket_key(c) == key)

    @staticmethod
    def _socket_key(c: dict) -> tuple:
        """Identity of a connection, stable across refreshes."""
        return (c.get("pid"), c.get("protocol"), c.get("local"), c.get("remote"))

    def _kill(self):
        """_kill."""
        conn = self.table.selected_record()
        if conn is None:
            return
        pid = conn.get("pid")
        name = conn.get("process") or "?"
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
        """_fail."""
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
    """UninstallerListWorker class."""
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        """run."""
        try:
            from cortex_unified.system_tools.app_uninstaller import AppUninstaller
            self.finished.emit(AppUninstaller().get_installed_apps())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class LeftoverScanWorker(QObject):
    """Sweep standard locations for the recently uninstalled apps' leftovers."""

    finished = Signal(list)   # list[dict] findings
    failed = Signal(str)

    def __init__(self, apps: list[dict], exclusions=None):
        """__init__."""
        super().__init__()
        self._apps = apps
        self._exclusions = exclusions
        from threading import Event
        self._cancel = Event()

    def cancel(self):
        """Cooperative stop: checked between apps and inside every sweep."""
        self._cancel.set()

    def run(self):
        """run."""
        try:
            from cortex_unified.system_tools.leftover_cleaner import (
                InstalledApp,
                LeftoverScanner,
            )
            scanner = LeftoverScanner(installed_apps=[],
                                      exclusions=self._exclusions,
                                      cancel_event=self._cancel)
            findings: dict[str, dict] = {}
            for record in self._apps:
                if self._cancel.is_set():
                    break
                app = InstalledApp(
                    name=record.get("name", ""),
                    publisher=record.get("publisher", ""),
                    version=record.get("display_version", ""),
                    install_location=record.get("install_location", ""),
                )
                if not app.name:
                    continue
                for f in scanner.scan_app(app):
                    findings[f.path] = f.to_dict()
            self.finished.emit(sorted(findings.values(),
                                      key=lambda d: -d["score"]))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class OrphanScanWorker(QObject):
    """Find orphaned Program Files folders no installed app claims."""

    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, exclusions=None):
        """__init__."""
        super().__init__()
        self._exclusions = exclusions
        from threading import Event
        self._cancel = Event()

    def cancel(self):
        """cancel."""
        self._cancel.set()

    def run(self):
        """run."""
        try:
            from cortex_unified.system_tools.leftover_cleaner import (
                LeftoverScanner,
            )
            scanner = LeftoverScanner(installed_apps=[],
                                      exclusions=self._exclusions,
                                      cancel_event=self._cancel)
            self.finished.emit(
                [f.to_dict() for f in scanner.scan_orphans()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class LeftoverCleanWorker(QObject):
    """Clean a reviewed batch: one journal, one restore point, cancellable."""

    finished = Signal(list)   # list[dict] outcomes
    failed = Signal(str)

    def __init__(self, findings: list[dict], create_restore_point: bool = False,
                 exclusions=None):
        """Initialize worker."""
        super().__init__()
        self._findings = findings
        self._create_restore_point = create_restore_point
        self._exclusions = exclusions
        from threading import Event
        self._cancel = Event()

    def cancel(self):
        """Stop before the next item; items already cleaned stay cleaned."""
        self._cancel.set()

    def run(self):
        """run."""
        try:
            from cortex_unified.system_tools.leftover_cleaner import (
                LeftoverCleaner,
                LeftoverFinding,
            )
            cleaner = LeftoverCleaner()
            models = [LeftoverFinding(kind=d["kind"], path=d["path"],
                                      size_bytes=d.get("size_bytes", 0))
                      for d in self._findings]
            outcomes = cleaner.clean(
                models, create_restore_point=self._create_restore_point,
                exclusions=self._exclusions, cancel_event=self._cancel)
            self.finished.emit([o.to_dict() for o in outcomes])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class TelemetryStatusWorker(QObject):
    """TelemetryStatusWorker class."""
    finished = Signal(dict)
    failed = Signal(str)

    def run(self):
        """run."""
        try:
            from cortex_unified.system_tools.telemetry_blocker import TelemetryBlocker
            self.finished.emit(TelemetryBlocker().check_status())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class TelemetryApplyWorker(QObject):
    """TelemetryApplyWorker class."""
    finished = Signal(bool)
    failed = Signal(str)

    def __init__(self, restore: bool):
        """__init__."""
        super().__init__()
        self._restore = restore

    def run(self):
        """run."""
        try:
            from cortex_unified.system_tools.telemetry_blocker import TelemetryBlocker
            tb = TelemetryBlocker()
            ok = tb.restore_defaults() if self._restore else tb.block_telemetry()
            self.finished.emit(ok)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class RegistryScanWorker(QObject):
    """RegistryScanWorker class."""
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        """run."""
        try:
            from cortex_unified.system_tools.registry_cleaner import RegistryCleaner
            self.finished.emit(RegistryCleaner().scan_orphaned_entries())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class RegistryCleanWorker(QObject):
    """RegistryCleanWorker class."""
    finished = Signal(int, str)   # (removed_count, backup_path)
    failed = Signal(str)

    def __init__(self, entries: list):
        """__init__."""
        super().__init__()
        self._entries = entries

    def run(self):
        """run."""
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
#  Leftover scanner section (post-uninstall residual cleanup)
# =====================================================================

_LEFTOVER_COLUMNS = [
    Column("Type", lambda d: d.get("kind", "?")),
    Column("Location", lambda d: d.get("path", ""), stretch=True,
           tooltip=lambda d: "\n".join(d.get("reasons", []))),
    Column("Size", lambda d: fmt_bytes(d.get("size_bytes", 0)),
           sort_key=lambda d: d.get("size_bytes", 0)),
    Column("Confidence", lambda d: _level_label(d.get("level", "")),
           sort_key=lambda d: d.get("score", 0),
           foreground=lambda d: _level_color(d.get("level", ""))),
]

_LEVEL_LABELS = {"VeryGood": "Very good", "Good": "Good",
                 "Questionable": "Questionable", "Bad": "Poor"}


def _level_label(level: str) -> str:
    """_level_label."""
    return _LEVEL_LABELS.get(level, level or "?")


def _level_color(level: str):
    """Traffic-light the confidence tier so review is instant."""
    from PySide6.QtGui import QColor
    return {"VeryGood": QColor("#3fb950"), "Good": QColor("#8ddb6a"),
            "Questionable": QColor("#d29922")}.get(level, QColor("#f85149"))


class _LeftoverSection:
    """Mixin wiring the leftover scan/clean UI into UninstallerPage."""

    def _build_leftover_section(self) -> None:
        """_build_leftover_section."""
        self.v.addWidget(title_block(
            "Leftover Scanner",
            "Finds the files, folders, caches, shortcuts and registry keys "
            "uninstallers leave behind on C:\\. Files go to the Recycle Bin; "
            "registry keys are exported as .reg backups first. Review every "
            "item - low-confidence rows may be shared with other software.",
        ))

        row = QHBoxLayout()
        self.leftover_scan_btn = QPushButton("Scan for Leftovers")
        self.leftover_scan_btn.setObjectName("Primary")
        self.leftover_scan_btn.setToolTip(
            "Scan for leftovers of the apps you just uninstalled.")
        self.leftover_scan_btn.clicked.connect(self._scan_leftovers)
        row.addWidget(self.leftover_scan_btn)
        self.orphan_scan_btn = QPushButton("Find Orphan Folders")
        self.orphan_scan_btn.setToolTip(
            "Scan Program Files for folders no installed app claims any more.")
        self.orphan_scan_btn.clicked.connect(self._scan_orphans)
        row.addWidget(self.orphan_scan_btn)
        self.clean_leftover_btn = QPushButton("Clean Selected")
        self.clean_leftover_btn.setObjectName("Danger")
        self.clean_leftover_btn.setEnabled(False)
        self.clean_leftover_btn.clicked.connect(self._clean_leftovers)
        row.addWidget(self.clean_leftover_btn)
        self.keep_leftover_btn = QPushButton("Keep Selected")
        self.keep_leftover_btn.setToolTip(
            "Never flag the selected items again (stored per-user in\n"
            "~/.cortex_cleaner/exclusions.json).")
        self.keep_leftover_btn.setEnabled(False)
        self.keep_leftover_btn.clicked.connect(self._keep_selected)
        row.addWidget(self.keep_leftover_btn)
        # Default-on: attempt a System Restore point before any registry-
        # touching cleanup. Windows allows at most one point per 24h; a
        # throttled attempt is reported as a note, not raised as an error.
        # The choice persists via SettingsStore.
        self.restore_point_chk = QCheckBox(
            "Create a System Restore point first")
        settings = getattr(self.win, "settings", None)
        self.restore_point_chk.setChecked(
            settings.leftover_restore_point if settings is not None else True)
        self.restore_point_chk.setToolTip(
            "Attempts a System Restore checkpoint before deleting anything.\n"
            "Windows creates at most one point per 24 hours - if one was made "
            "recently this is noted and cleanup continues.")
        self.restore_point_chk.toggled.connect(self._persist_restore_pref)
        row.addWidget(self.restore_point_chk)
        self.v.addLayout(row)

        self.leftover_progress = QProgressBar()
        self.leftover_progress.setRange(0, 0)
        self.leftover_progress.setVisible(False)
        self.v.addWidget(self.leftover_progress)

        self.leftover_tbl = QTableView()
        self.leftover_tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.leftover_tbl)
        self.leftover_table = bind_table(self.leftover_tbl, _LEFTOVER_COLUMNS)
        self.leftover_tbl.setSelectionMode(
            QTableView.SelectionMode.ExtendedSelection)
        self.leftover_tbl.selectionModel().selectionChanged.connect(
            self._on_leftover_select)
        self.v.addWidget(self.leftover_table.view, 1)

        self.leftover_state = StatePanel(self.p)
        self.leftover_state.bind_content(self.leftover_table.view)
        self.v.addWidget(self.leftover_state, 1)   # must join the layout to appear
        self.leftover_state.show_empty(
            "No scan yet. Uninstall an app, then click 'Scan for Leftovers'.")

    # -- preferences / exclusions -------------------------------------------

    def _persist_restore_pref(self, checked: bool):
        """_persist_restore_pref."""
        settings = getattr(self.win, "settings", None)
        if settings is not None:
            settings.leftover_restore_point = bool(checked)

    @staticmethod
    def _exclusions_store():
        """_exclusions_store."""
        from cortex_unified.system_tools.leftover_cleaner import ExclusionsStore
        return ExclusionsStore()

    def _keep_selected(self):
        """Exclude the selected findings from every future scan."""
        selected = self._selected_findings()
        if not selected:
            return
        store = self._exclusions_store()
        for d in selected:
            store.add(d.get("path", ""))
        paths = {d.get("path") for d in selected}
        remaining = [d for d in self.leftover_table.model.records
                     if d.get("path") not in paths]
        self.leftover_table.set_records(remaining)
        self.win.statusBar().showMessage(
            f"{len(selected)} item(s) added to your exclusions - they will "
            "not be flagged again.", 8000)
        if not remaining:
            self.leftover_state.show_empty(
                "All clear - nothing left to review.")

    # -- scanning -------------------------------------------------------

    def _pending_apps(self) -> list[dict]:
        """The window-level buffer of recently-uninstalled apps.

        The Uninstaller page (which performs uninstalls) pushes metadata
        here; this page consumes it. Living on the window (not on either
        page) keeps the handoff working regardless of lazy construction
        order.
        """
        buf = getattr(self.win, "_pending_leftover_apps", None)
        if buf is None:
            buf = []
            self.win._pending_leftover_apps = buf
        return buf

    def _scan_leftovers(self):
        """_scan_leftovers."""
        pending = self._pending_apps()
        if not pending:
            QMessageBox.information(
                self, "Nothing to scan",
                "No recent uninstalls recorded.\n\nUninstall an app on the "
                "Deep Uninstaller page, finish its uninstaller, then click "
                "this button.")
            return
        apps = list(pending)
        pending.clear()
        self.leftover_progress.setVisible(True)
        self.leftover_state.show_loading(
            f"Scanning leftovers for {len(apps)} app(s)\u2026")
        self.win.run_worker(
            LeftoverScanWorker(apps, exclusions=self._exclusions_store()),
            self._on_leftovers, self._leftover_fail)

    def _scan_orphans(self):
        """_scan_orphans."""
        self.leftover_progress.setVisible(True)
        self.leftover_state.show_loading("Scanning Program Files orphans\u2026")
        self.win.run_worker(OrphanScanWorker(exclusions=self._exclusions_store()),
                            self._on_leftovers, self._leftover_fail)

    def _on_leftovers(self, findings: list):
        """_on_leftovers."""
        self.leftover_progress.setVisible(False)
        if not findings:
            self.leftover_state.show_empty(
                "No leftovers found - the uninstall was clean.")
            return
        self.leftover_state.clear()
        self.leftover_table.set_records(findings)
        total = sum(d.get("size_bytes", 0) for d in findings)
        self.win.statusBar().showMessage(
            f"{len(findings)} leftover item(s), {fmt_bytes(total)} reclaimable",
            8000)

    def _leftover_fail(self, msg: str):
        """_leftover_fail."""
        self.leftover_progress.setVisible(False)
        self.leftover_state.show_error(msg)

    # -- cleaning ---------------------------------------------------------

    def _selected_findings(self) -> list[dict]:
        """_selected_findings."""
        selection = self.leftover_tbl.selectionModel()
        if selection is None:
            return []
        indexes = selection.selectedRows() or selection.selectedIndexes()
        out: list[dict] = []
        for row in sorted({i.row() for i in indexes}, reverse=True):
            source = self.leftover_table.proxy.mapToSource(
                self.leftover_table.proxy.index(row, 0))
            record = self.leftover_table.model.record_at(source.row())
            if record is not None:
                out.append(record)
        return out

    def _on_leftover_select(self, *_):
        """_on_leftover_select."""
        has = bool(self._selected_findings())
        self.clean_leftover_btn.setEnabled(has)
        self.keep_leftover_btn.setEnabled(has)

    def _clean_leftovers(self):
        """_clean_leftovers."""
        selected = self._selected_findings()
        if not selected:
            return
        folders = sum(1 for d in selected if d.get("kind") != "registry")
        keys = sum(1 for d in selected if d.get("kind") == "registry")
        restore = self.restore_point_chk.isChecked()
        restore_line = ("\n  \u2022 A System Restore point will be attempted first"
                        if restore else "")
        confirm = QMessageBox.question(
            self, "Clean leftovers",
            f"Remove {len(selected)} item(s)?\n\n"
            f"  \u2022 {folders} file/folder item(s) \u2192 moved to the Recycle Bin\n"
            f"  \u2022 {keys} registry key(s) \u2192 exported as .reg backup first"
            f"{restore_line}\n\n"
            "Review the list carefully - items marked 'Questionable' may be "
            "shared with other software.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.leftover_progress.setVisible(True)
        self.clean_leftover_btn.setEnabled(False)
        self.keep_leftover_btn.setEnabled(False)
        self.win.run_worker(
            LeftoverCleanWorker(selected, create_restore_point=restore,
                                exclusions=self._exclusions_store()),
            self._on_cleaned, self._leftover_fail)

    def _on_cleaned(self, outcomes: list):
        """_on_cleaned."""
        self.leftover_progress.setVisible(False)
        ok = [o for o in outcomes if o.get("ok")]
        failed = [o for o in outcomes if not o.get("ok")]
        recycled = sum(1 for o in ok if o.get("disposition") == "recycled")
        keys = sum(1 for o in ok if o.get("disposition") == "registry_deleted")
        freed = 0
        by_path = {o.get("path"): o for o in outcomes}
        remaining = [d for d in self.leftover_table.model.records
                     if by_path.get(d.get("path"), {}).get("ok") is not True]
        for d in self.leftover_table.model.records:
            if by_path.get(d.get("path"), {}).get("ok") is True \
                    and d.get("kind") != "registry":
                freed += d.get("size_bytes", 0)
        self.leftover_table.set_records(remaining)
        msg = (f"Done: {recycled} item(s) recycled ({fmt_bytes(freed)} to "
               f"the Recycle Bin), {keys} registry key(s) removed "
               f"(backups in ~/CortexCleanerBackups/leftovers).")
        if failed:
            msg += f"\n\n{len(failed)} item(s) failed:"
            msg += "\n".join(f"\n  \u2022 {o.get('path')}: "
                             f"{o.get('detail', 'error')}" for o in failed[:5])
        QMessageBox.information(self, "Leftover cleanup", msg)
        if not remaining:
            self.leftover_state.show_empty(
                "All clear - nothing left to review.")


# =====================================================================
#  Windows-only pages
# =====================================================================

class UninstallerPage(_Page):
    """List installed apps and launch their official uninstallers.
    Post-uninstall residual cleanup lives in the dedicated Leftover
    Scanner page (sidebar: Apps & Security -> Leftover Scanner)."""

    def __init__(self, win):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Deep Uninstaller",
            "Registry-based app discovery. Launches each app's official "
            "uninstaller. Select multiple apps (Ctrl/Shift-click) to "
            "uninstall them one after another.",
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

        # Model/view instead of an item-based table. A QTableWidget allocated one
        # QTableWidgetItem per cell for every installed app - typically 100-300
        # rows x 3 columns - and the search box rebuilt the whole lot on every
        # keystroke, because filtering meant re-rendering a trimmed python list.
        # The model holds the full app list once and the proxy simply stops
        # offering rows that don't match, so typing costs no allocations and the
        # view only ever asks for the ~20 cells it is painting.
        self.tbl = QTableView()
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        # Row selection, read-only, alternating rows, hidden vertical header and
        # the per-column stretch all come from bind_table.
        self.table = bind_table(
            self.tbl, self._columns(),
            sort_column=0, sort_order=Qt.SortOrder.AscendingOrder,  # Name A-Z
        )
        # bind_table's default is SingleSelection; this page deliberately keeps
        # multi-select, because its whole point is queueing several uninstallers
        # with Ctrl/Shift-click.
        self.tbl.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        # A QTableView has no itemSelectionChanged - the selection model is the
        # equivalent, and it also fires for keyboard navigation.
        self.tbl.selectionModel().selectionChanged.connect(self._on_select)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._autoload = self._load   # lazy-loaded on first visit
        self._loaded = False

    # -- columns --
    def _columns(self) -> list[Column]:
        """Declare the three app columns once, instead of filling cells.

        The whole app dict rides along with its row in the model, so the
        uninstall action reads real records instead of looking up a python list
        by the view's row number - which stops being the record's index the
        moment the user sorts or searches. No ``sort_key`` is needed here: all
        three columns display the string they sort on. (A size column would need
        one - "9 MB" sorts above "10 MB" when the comparison is textual - but
        this table doesn't show size.)
        """
        return [
            Column("Name", lambda a: a.get("name", "?"), stretch=True),
            Column("Publisher", lambda a: a.get("publisher", "")),
            Column("Version", lambda a: a.get("display_version", "")),
        ]

    def _load(self):
        """_load."""
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Listing installed apps…")
        self.win.run_worker(UninstallerListWorker(), self._on_loaded, self._fail)

    def _on_loaded(self, apps: list):
        """_on_loaded."""
        self.refresh_btn.setEnabled(True)
        if not apps:
            self.state.show_empty("No installed applications found.")
        else:
            self.state.clear()
        self._apps = apps
        # One model reset for the whole list; the proxy keeps the current search
        # term and sort order across the swap.
        self.table.set_records(apps)
        self.win.statusBar().showMessage(f"{len(apps)} installed applications", 5000)

    def _filter(self, text: str):
        """_filter."""
        # Searching is the proxy's job now. It matches every searchable column,
        # so the name/publisher pair the old python filter checked is still
        # covered, plus the version - and no rows are rebuilt.
        self.table.set_filter_text(text)

    def _selected_apps(self) -> list[dict]:
        """Every selected app record, resolved through the proxy.

        ``TableBinding.selected_record()`` covers the single-selection tables;
        this one acts on several rows, so it applies the same mapping per row.
        Going through the proxy is the point: a view row number stops matching
        the source list the moment the user sorts or searches, which is exactly
        what the old ``self.tbl.item(r, 0)`` lookup got wrong.
        """
        selection = self.tbl.selectionModel()
        if selection is None:
            return []
        indexes = selection.selectedRows() or selection.selectedIndexes()
        apps: list[dict] = []
        for row in sorted({index.row() for index in indexes}):
            source = self.table.proxy.mapToSource(self.table.proxy.index(row, 0))
            record = self.table.model.record_at(source.row())
            if record is not None:
                apps.append(record)
        return apps

    def _on_select(self, *_):
        """_on_select."""
        self.uninstall_btn.setEnabled(bool(self._selected_apps()))

    def _uninstall(self):
        """_uninstall."""
        apps = self._selected_apps()
        if not apps:
            return
        names = "\n".join(f"  \u2022 {a.get('name')}" for a in apps)
        confirm = QMessageBox.question(
            self, "Confirm uninstall",
            f"Launch the official uninstaller for {len(apps)} app(s)?\n\n{names}\n\n"
            "Each uninstaller opens in turn - complete one before the next appears.\n\n"
            "Afterwards, use the Leftover Scanner (Apps & Security) to remove "
            "what they left behind.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        # Capture metadata BEFORE the uninstallers run: once the apps are
        # gone, Refresh drops their records and a leftover scan would have
        # nothing to match against. The buffer lives on the window so the
        # dedicated Leftover Scanner page can consume it.
        buf = getattr(self.win, "_pending_leftover_apps", None)
        if buf is None:
            buf = []
            self.win._pending_leftover_apps = buf
        known = {a.get("name") for a in buf}
        for a in apps:
            if a.get("name") and a.get("name") not in known:
                buf.append(dict(a))
        from cortex_unified.system_tools.app_uninstaller import AppUninstaller
        uninstaller = AppUninstaller()
        launched = sum(1 for a in apps if uninstaller.uninstall_app(a))
        if launched:
            QMessageBox.information(
                self, "Uninstaller launched",
                f"Launched {launched} of {len(apps)} uninstaller(s). "
                "Complete each one, then open the Leftover Scanner page "
                "to clean what they left behind.")
        else:
            QMessageBox.warning(self, "Error",
                                "Could not launch the uninstaller(s) (may need elevation).")

    def _fail(self, msg: str):
        """_fail."""
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)

class LeftoverScannerPage(_Page, _LeftoverSection):
    """Dedicated sidebar page for the post-uninstall leftover scanner.

    The Deep Uninstaller page only launches official uninstallers; residual
    cleanup lives here so each concern stays on its own page.
    """

    def __init__(self, win):
        """__init__."""
        super().__init__(win)
        if _windows_only(self, "The Leftover Scanner"):
            return
        self._pending_leftovers: list[dict] = []
        self._build_leftover_section()
        self.v.addStretch(1)


class TelemetryPage(_Page):
    """Block / restore Windows telemetry (Windows, admin required to apply)."""

    def __init__(self, win):
        """__init__."""
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
        """_refresh."""
        self.state.show_loading("Reading telemetry status…")
        self.win.run_worker(TelemetryStatusWorker(), self._on_status, self._fail)

    def _on_status(self, status: dict):
        """_on_status."""
        self.state.clear()
        self.tree.clear()
        blocked = sum(1 for v in status.values() if v)
        total = len(status)
        for label, is_blocked in status.items():
            QTreeWidgetItem(self.tree, [label, "Blocked" if is_blocked else "Active"])
        self.status_lbl.setText(f"{blocked} of {total} telemetry features blocked.")

    def _apply(self, restore: bool):
        """_apply."""
        if not require_feature(self, Feature.TELEMETRY_BLOCKER):
            return
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
        """_on_applied."""
        self.block_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        if not ok:
            QMessageBox.warning(self, "Partial", "Some changes failed. Run as Administrator.")
        self._refresh()

    def _fail(self, msg: str):
        """_fail."""
        self.block_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._refresh)


class RegistryPage(_Page):
    """Scan for orphaned registry entries and remove them with a backup first."""

    def __init__(self, win):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Registry Cleaner",
            "Find orphaned entries (missing targets). A .reg backup is exported before removal.",
        ))
        if _windows_only(self, "The Registry Cleaner"):
            return
        self._entries: list[dict] = []

        warn = status_note(self.p, "warning", "Registry edits can affect system behavior. A backup is exported first.")
        warn.setStyleSheet(f"color: {self.p.warning}; font-weight: 600;")
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

        # Model/view instead of an item-based table. This scan can return
        # thousands of orphaned entries, and a QTableWidget built three
        # QTableWidgetItem objects for each of them in one synchronous loop -
        # tens of thousands of throwaway objects for the ~20 rows on screen. The
        # model renders only what the view paints, so the render cost no longer
        # scales with how dirty the registry is.
        self.tbl = QTableView()
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        # Row selection, single selection, read-only, alternating rows, hidden
        # vertical header and the per-column stretch all come from bind_table.
        # Sorting is worth having here: 'Hive' and 'Reason' group the findings.
        self.table = bind_table(
            self.tbl, self._columns(),
            sort_column=0, sort_order=Qt.SortOrder.AscendingOrder,  # Subkey A-Z
        )
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

    # -- columns --
    def _columns(self) -> list[Column]:
        """Declare the three entry columns once, instead of filling cells."""
        return [
            Column("Subkey", lambda e: str(e.get("path", "")), stretch=True),
            Column("Hive", lambda e: str(e.get("hive", ""))),
            Column("Reason", lambda e: str(e.get("reason", ""))),
        ]

    def _scan(self):
        """_scan."""
        if not require_feature(self, Feature.REGISTRY_CLEANER):
            return
        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.state.show_loading("Scanning registry…")
        self.table.set_records([])
        self.win.run_worker(RegistryScanWorker(), self._on_scan, self._fail)

    def _on_scan(self, entries: list):
        """_on_scan."""
        self.scan_btn.setEnabled(True)
        if not entries:
            self.state.show_empty("No orphaned registry entries found.")
        else:
            self.state.clear()
        self._entries = entries
        # One model reset for the whole scan result. ``_entries`` stays the
        # source of truth for "Clean All Found" - it is the complete scan, not
        # whatever subset the view happens to be showing.
        self.table.set_records(entries)
        self.clean_btn.setEnabled(bool(entries))
        self.win.statusBar().showMessage(f"{len(entries)} orphaned entries found", 5000)

    def _clean(self):
        """_clean."""
        if not self._entries:
            return
        if not require_feature(self, Feature.REGISTRY_CLEANER):
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
        """_on_clean."""
        self.progress.setVisible(False)
        note = f"Removed {removed} entries." + (f"\nBackup: {backup}" if backup else "")
        QMessageBox.information(self, "Done", note)
        self.win.statusBar().showMessage(f"Removed {removed} registry entries", 6000)
        self._scan()

    def _fail(self, msg: str):
        """_fail."""
        self.scan_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._scan)
