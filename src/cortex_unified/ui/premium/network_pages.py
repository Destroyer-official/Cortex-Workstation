"""Network suite pages: live Traffic Monitor and Firewall control.

* TrafficMonitorPage - real-time up/download throughput graph + per-interface
  breakdown, sampled cheaply on a timer (psutil counters, no admin needed).
* FirewallPage - block or allow a program / remote IP via Windows Firewall,
  and manage the rules Cortex created. System-modifying actions are confirmed
  and run on worker threads; listing is read-only.
"""

from __future__ import annotations

import csv
import sys
import html
import ipaddress
import json
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtGui import (
    QColor, QDesktopServices, QFont, QPainter, QPainterPath, QPdfWriter,
    QPen, QTextDocument,
)

from .states import StatePanel
from .tablemodel import Column, bind_table
from .widgets import Card, StatCard, TrafficGraph, status_note, title_block
from .window import _Page, fmt_bytes

#: Severity ordering shared by the device table. Sorting the display text would
#: put "CRITICAL" after "HIGH" alphabetically, burying exactly the rows the user
#: opened this page for.
_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def _ip_sort_key(device) -> tuple:
    """Sort IPv4 addresses numerically rather than as dotted strings.

    As text, ``192.168.1.10`` sorts before ``192.168.1.9``. Packing the octets
    into a tuple restores the order a user expects; anything unparseable sorts
    last but stays stable.
    """
    raw = getattr(device, "ip", "") or ""
    try:
        return (0,) + tuple(int(part) for part in raw.split("."))
    except (ValueError, AttributeError):
        return (1, raw)

# ``sys.platform`` is an interned constant; ``platform.system()`` costs
# ~50 ms on its first call because it populates ``uname()`` via WMI.
IS_WINDOWS = sys.platform == "win32"


def _fmt_rate(bps: float) -> str:
    """Format a byte/rate value into a human-readable string (B/s, KB/s, MB/s).

    Converts raw numeric values into formatted, localized, and human-readable string representations.

    Args:
        bps (float): The bps parameter.

    Returns:
        str: Formatted string or path.
    """
    v = float(bps)
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if v < 1024 or unit == "GB/s":
            return f"{v:.1f} {unit}"
        v /= 1024
    return f"{bps} B/s"


# =====================================================================
#  Traffic Monitor
# =====================================================================

class TrafficMonitorPage(_Page):
    """Trafficmonitorpage.

    Manages TrafficMonitorPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Build the page layout (tables, cards, title header) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Traffic Monitor",
            "Live upload/download throughput for your machine and each network "
            "adapter. Sampled locally and cheaply - no data leaves your PC.",
        ))

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.card_down = StatCard(self.p, "Download", "\u2014")
        self.card_up = StatCard(self.p, "Upload", "\u2014")
        self.card_rx = StatCard(self.p, "Received (session)", "\u2014")
        self.card_tx = StatCard(self.p, "Sent (session)", "\u2014")
        for c in (self.card_down, self.card_up, self.card_rx, self.card_tx):
            cards.addWidget(c)
        self.v.addLayout(cards)

        graph_card = Card(self.p)
        gl = QVBoxLayout(graph_card)
        gl.setContentsMargins(14, 12, 14, 12)
        legend = QLabel("<span style='color:#4c8bf5'>\u25CF Download</span>   "
                        "<span style='color:#e0a000'>\u25CF Upload</span>")
        gl.addWidget(legend)
        self.graph = TrafficGraph(self.p)
        gl.addWidget(self.graph, 1)
        self.v.addWidget(graph_card, 1)

        self.nic_tbl = QTableWidget(0, 5)
        self.nic_tbl.setHorizontalHeaderLabels(
            ["Interface", "Down", "Up", "Total recv", "Total sent"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.nic_tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.nic_tbl)
        self.nic_tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.nic_tbl.verticalHeader().setVisible(False)
        self.nic_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.nic_tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.nic_tbl)

        # Sampling is a couple of counter reads - cheap enough to run inline on
        # a 1s timer without a worker thread.
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._autoload = self._start
        self._loaded = False

    def _start(self):
        """Start.

        Manages start operations and coordinates related state changes for the component.
        """
        from cortex_unified.system_tools.network_traffic import TrafficMonitor
        self._mon = TrafficMonitor.instance()
        self._mon.sample()   # prime so the first visible rate is real
        self._timer.start()
        self._tick()

    def _tick(self):
        """Handle recurring timer events for real-time metric updates.

        Samples live system performance statistics, advances animation counters, and updates graphical meters.
        """
        if not self.isVisible():
            return
        try:
            s = self._mon.sample()
        except Exception:  # noqa: BLE001
            return
        self.card_down.set_value(_fmt_rate(s.recv_rate))
        self.card_up.set_value(_fmt_rate(s.send_rate))
        self.card_rx.set_value(fmt_bytes(s.recv_since_start))
        self.card_tx.set_value(fmt_bytes(s.sent_since_start))
        self.graph.add_sample(s.recv_rate, s.send_rate)

        self.nic_tbl.setRowCount(len(s.per_nic))
        for r, n in enumerate(s.per_nic):
            self.nic_tbl.setItem(r, 0, QTableWidgetItem(n.name))
            self.nic_tbl.setItem(r, 1, QTableWidgetItem(_fmt_rate(n.recv_rate)))
            self.nic_tbl.setItem(r, 2, QTableWidgetItem(_fmt_rate(n.send_rate)))
            self.nic_tbl.setItem(r, 3, QTableWidgetItem(fmt_bytes(n.bytes_recv)))
            self.nic_tbl.setItem(r, 4, QTableWidgetItem(fmt_bytes(n.bytes_sent)))


# =====================================================================
#  Firewall workers
# =====================================================================

class FirewallListWorker(QObject):
    """Firewalllistworker.

    Manages FirewallListWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, cortex_only: bool = True):
        """Store constructor arguments (cortex_only) and initialize worker signals.

        Initializes the instance and configures internal state.

        Args:
            cortex_only (bool): The cortex only parameter.
        """
        super().__init__()
        self._cortex_only = cortex_only

    def run(self):
        """Run the FirewallManager (firewall manager) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.firewall_manager import FirewallManager
            rules = FirewallManager().list_rules(cortex_only=self._cortex_only)
            self.finished.emit([r.to_dict() for r in rules])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class FirewallActionWorker(QObject):
    """Firewallactionworker.

    Manages FirewallActionWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(bool, str)
    failed = Signal(str)

    def __init__(self, action: str, **kwargs):
        """Store constructor arguments (action) and initialize worker signals.

        Initializes the instance and configures internal state.

        Args:
            action (str): The action parameter.
        """
        super().__init__()
        self._action = action
        self._kw = kwargs

    def run(self):
        """Run the FirewallManager (firewall manager) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.firewall_manager import FirewallManager
            fw = FirewallManager()
            a = self._action
            if a == "block_program":
                ok, msg = fw.block_program(self._kw["path"], self._kw["direction"])
            elif a == "allow_program":
                ok, msg = fw.allow_program(self._kw["path"], self._kw["direction"])
            elif a == "block_address":
                ok, msg = fw.block_remote_address(self._kw["address"], self._kw["direction"])
            elif a == "toggle":
                ok, msg = fw.set_enabled(self._kw["name"], self._kw["enabled"])
            elif a == "remove":
                ok, msg = fw.remove_rule(self._kw["name"])
            else:
                ok, msg = False, "Unknown action."
            self.finished.emit(ok, msg)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# =====================================================================
#  Firewall page
# =====================================================================

class FirewallPage(_Page):
    """Firewallpage.

    Manages FirewallPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Firewall",
            "Block or allow a program's or address's traffic using Windows "
            "Firewall. Fully reversible - Cortex only manages rules it creates "
            "and never touches your existing Windows rules. Needs Administrator.",
        ))
        if not IS_WINDOWS:
            note = status_note(self.p, "info", "Firewall control is only available on Windows.")
            self.v.addWidget(note)
            self.v.addStretch(1)
            return

        # -- create-rule controls --
        create = Card(self.p)
        cl = QVBoxLayout(create)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(10)

        prog_row = QHBoxLayout()
        prog_row.addWidget(QLabel("Program:"))
        self.prog_edit = QLineEdit()
        self.prog_edit.setPlaceholderText("Path to an .exe\u2026")
        prog_row.addWidget(self.prog_edit, 1)
        browse = QPushButton("Browse\u2026")
        browse.clicked.connect(self._browse)
        prog_row.addWidget(browse)
        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["Outbound", "Inbound"])
        prog_row.addWidget(self.dir_combo)
        block_prog = QPushButton("Block")
        block_prog.setObjectName("Danger")
        block_prog.clicked.connect(lambda: self._create("block_program"))
        allow_prog = QPushButton("Allow")
        allow_prog.clicked.connect(lambda: self._create("allow_program"))
        prog_row.addWidget(block_prog)
        prog_row.addWidget(allow_prog)
        cl.addLayout(prog_row)

        addr_row = QHBoxLayout()
        addr_row.addWidget(QLabel("Remote IP / range:"))
        self.addr_edit = QLineEdit()
        self.addr_edit.setPlaceholderText("e.g. 203.0.113.4  or  203.0.113.0/24")
        addr_row.addWidget(self.addr_edit, 1)
        block_addr = QPushButton("Block Address")
        block_addr.setObjectName("Danger")
        block_addr.clicked.connect(lambda: self._create("block_address"))
        addr_row.addWidget(block_addr)
        cl.addLayout(addr_row)
        self.v.addWidget(create)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        # -- rules table --
        row = QHBoxLayout()
        row.addWidget(QLabel("Rules created by Cortex:"))
        row.addStretch(1)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load)
        self.toggle_btn = QPushButton("Enable/Disable")
        self.toggle_btn.setEnabled(False)
        self.toggle_btn.clicked.connect(self._toggle)
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setObjectName("Danger")
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self._remove)
        row.addWidget(self.refresh_btn)
        row.addWidget(self.toggle_btn)
        row.addWidget(self.remove_btn)
        self.v.addLayout(row)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["Rule", "Action", "Direction", "Target", "Enabled"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.itemSelectionChanged.connect(self._on_sel)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._autoload = self._load
        self._loaded = False

    def _browse(self):
        """Prompt the user to select a filesystem directory or file.

        Launches a native file dialog and populates the selected path into the corresponding target input widget.
        """
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a program", str(Path.home()), "Programs (*.exe);;All files (*.*)")
        if path:
            self.prog_edit.setText(path)

    def _busy(self, on: bool):
        """Update the busy state indicators across the interface.

        Shows or hides loading indicators, adjusts cursor feedback, and toggles action button availability.

        Args:
            on (bool): The on parameter.
        """
        self.progress.setVisible(on)
        self.refresh_btn.setEnabled(not on)

    def _create(self, action: str):
        """Create.

        Manages create operations and coordinates related state changes for the component.

        Args:
            action (str): The action parameter.
        """
        if action == "block_address":
            addr = self.addr_edit.text().strip()
            if not addr:
                QMessageBox.information(self, "No address", "Enter an IP address or range.")
                return
            verb, target = "block traffic to", addr
            kw = {"address": addr, "direction": self.dir_combo.currentText()}
        else:
            path = self.prog_edit.text().strip()
            if not path:
                QMessageBox.information(self, "No program", "Choose a program (.exe) first.")
                return
            verb = "block" if action == "block_program" else "allow"
            target = path
            kw = {"path": path, "direction": self.dir_combo.currentText()}
        confirm = QMessageBox.question(
            self, "Confirm firewall rule",
            f"Create a Windows Firewall rule to {verb} {target} "
            f"({kw['direction'].lower()})?\n\nThis needs Administrator and is reversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._busy(True)
        self.win.run_worker(FirewallActionWorker(action, **kw), self._on_action, self._fail)

    def _on_action(self, ok: bool, msg: str):
        """Handle worker results: note status and clear the busy state.

        Manages on action operations and coordinates related state changes for the component.

        Args:
            ok (bool): The ok parameter.
            msg (str): Informational or progress status message.
        """
        self._busy(False)
        if ok:
            self.win.statusBar().showMessage(msg, 5000)
        else:
            QMessageBox.warning(self, "Firewall", msg)
        self._load()

    def _load(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Loading firewall rules…")
        self.win.run_worker(FirewallListWorker(True), self._on_listed, self._fail)

    def _on_listed(self, rules: list):
        """Handle worker results: refresh tables/trees, update the state panel, note status and clear the busy state.

        Manages on listed operations and coordinates related state changes for the component.

        Args:
            rules (list): The rules parameter.
        """
        self.refresh_btn.setEnabled(True)
        if not rules:
            self.state.show_empty("No Cortex firewall rules yet.")
        else:
            self.state.clear()
        self._rules = rules
        self.tbl.setRowCount(len(rules))
        for r, rule in enumerate(rules):
            name_item = QTableWidgetItem(rule["display_name"].replace("Cortex Cleaner:", "").strip())
            name_item.setData(Qt.ItemDataRole.UserRole, rule["name"])
            self.tbl.setItem(r, 0, name_item)
            self.tbl.setItem(r, 1, QTableWidgetItem(rule["action"]))
            self.tbl.setItem(r, 2, QTableWidgetItem(rule["direction"]))
            target = rule["program"] or rule["remote_address"] or "\u2014"
            self.tbl.setItem(r, 3, QTableWidgetItem(target))
            self.tbl.setItem(r, 4, QTableWidgetItem("Yes" if rule["enabled"] else "No"))
        if not rules:
            self.win.statusBar().showMessage("No Cortex firewall rules yet.", 4000)

    def _on_sel(self):
        """Handle worker results: re-enable buttons and clear the busy state.

        Manages on sel operations and coordinates related state changes for the component.
        """
        has = bool(self.tbl.selectedIndexes())
        self.toggle_btn.setEnabled(has)
        self.remove_btn.setEnabled(has)

    def _selected(self) -> tuple[str, bool] | None:
        """Selected.

        Manages selected operations and coordinates related state changes for the component.

        Returns:
            tuple[str, bool] | None: True if the operation succeeded, False otherwise.
        """
        sel = self.tbl.selectedIndexes()
        if not sel:
            return None
        r = sel[0].row()
        name = self.tbl.item(r, 0).data(Qt.ItemDataRole.UserRole)
        enabled = self.tbl.item(r, 4).text() == "Yes"
        return name, enabled

    def _toggle(self):
        """Toggle via the background worker; results return through worker signals.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        sel = self._selected()
        if not sel:
            return
        name, enabled = sel
        self._busy(True)
        self.win.run_worker(
            FirewallActionWorker("toggle", name=name, enabled=not enabled),
            self._on_action, self._fail)

    def _remove(self):
        """Remove.

        Manages remove operations and coordinates related state changes for the component.
        """
        sel = self._selected()
        if not sel:
            return
        name, _ = sel
        confirm = QMessageBox.question(
            self, "Remove rule", "Remove this firewall rule? (reversible - you can recreate it)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._busy(True)
        self.win.run_worker(FirewallActionWorker("remove", name=name),
                            self._on_action, self._fail)

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self._busy(False)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Network Map
# =====================================================================


class _MapCanvas(QWidget):
    """Mapcanvas.

    Manages MapCanvas operations and coordinates related state changes for the component.
    """

    def __init__(self, palette, parent=None):
        """Build the page layout (widgets) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            palette: The palette parameter.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self._p = palette
        self._edges: list[tuple[str, str, bool]] = []  # (process, remote, external)
        self.setMinimumHeight(360)

    def set_edges(self, edges: list[tuple[str, str, bool]]):
        """Store graph edges and trigger a repaint of the canvas.

        Manages set edges operations and coordinates related state changes for the component.

        Args:
            edges (list[tuple[str, str, bool]]): The edges parameter.
        """
        # Keep the view readable: cap processes and remotes.
        self._edges = edges[:120]
        self.update()

    def paintEvent(self, event):  # noqa: N802
        """Render custom visual elements and borders for the widget.

        Uses QPainter with active theme colors, gradients, and font metrics to draw specialized UI graphics.

        Args:
            event: The Qt event object.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(self.rect(), QColor(self._p.surface_alt))

        if not self._edges:
            painter.setPen(QColor(self._p.text_muted))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             "No active external connections to map.")
            painter.end()
            return

        procs: list[str] = []
        remotes: list[str] = []
        for proc, remote, _ext in self._edges:
            if proc not in procs:
                procs.append(proc)
            if remote not in remotes:
                remotes.append(remote)
        procs = procs[:14]
        remotes = remotes[:22]

        col_pc = w * 0.10
        col_proc = w * 0.42
        col_remote = w * 0.80

        def _ys(n: int) -> list[float]:
            """Ys.

            Manages ys operations and coordinates related state changes for the component.

            Args:
                n (int): The n parameter.

            Returns:
                list[float]: List of processed items or identifiers.
            """
            if n == 0:
                return []
            top, bot = 40, h - 30
            if n == 1:
                return [(top + bot) / 2]
            return [top + (bot - top) * i / (n - 1) for i in range(n)]

        proc_y = {p: y for p, y in zip(procs, _ys(len(procs)))}
        remote_y = {r: y for r, y in zip(remotes, _ys(len(remotes)))}
        pc_y = h / 2

        accent = QColor(self._p.accent)
        danger = QColor(getattr(self._p, "danger", "#e05555"))
        muted = QColor(self._p.border)

        # edges: PC -> proc, proc -> remote
        for proc, remote, ext in self._edges:
            if proc not in proc_y or remote not in remote_y:
                continue
            py = proc_y[proc]
            ry = remote_y[remote]
            # PC -> proc
            self._curve(painter, col_pc + 46, pc_y, col_proc - 60, py, muted)
            # proc -> remote (red if external)
            self._curve(painter, col_proc + 60, py, col_remote - 46, ry,
                        danger if ext else accent)

        # nodes
        self._node(painter, col_pc, pc_y, "This PC", accent, big=True)
        for p, y in proc_y.items():
            self._node(painter, col_proc, y, p, QColor(self._p.text))
        for r, y in remote_y.items():
            ext = any(e[1] == r and e[2] for e in self._edges)
            self._node(painter, col_remote, y, r, danger if ext else accent, small=True)
        painter.end()

    def _curve(self, painter, x1, y1, x2, y2, color: QColor):
        """Curve.

        Manages curve operations and coordinates related state changes for the component.

        Args:
            painter: The painter parameter.
            x1: The x1 parameter.
            y1: The y1 parameter.
            x2: The x2 parameter.
            y2: The y2 parameter.
            color (QColor): The color parameter.
        """
        path = QPainterPath()
        path.moveTo(x1, y1)
        mx = (x1 + x2) / 2
        path.cubicTo(mx, y1, mx, y2, x2, y2)
        pen = QPen(color, 1.4)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    def _node(self, painter, cx, cy, label, color: QColor, big=False, small=False):
        """Node.

        Manages node operations and coordinates related state changes for the component.

        Args:
            painter: The painter parameter.
            cx: The cx parameter.
            cy: The cy parameter.
            label: Display text string.
            color (QColor): The color parameter.
            big: The big parameter.
            small: The small parameter.
        """
        painter.setFont(QFont("Segoe UI", 10 if big else (8 if small else 9),
                              QFont.Weight.DemiBold if big else QFont.Weight.Normal))
        metrics = painter.fontMetrics()
        text = metrics.elidedText(label, Qt.TextElideMode.ElideMiddle, 150)
        tw = metrics.horizontalAdvance(text)
        pad = 10
        rw = tw + 2 * pad
        rh = 26 if big else 22
        from PySide6.QtCore import QRectF
        rect = QRectF(cx - rw / 2, cy - rh / 2, rw, rh)
        bg = QColor(color)
        bg.setAlpha(40)
        painter.setBrush(bg)
        painter.setPen(QPen(color, 1.5))
        painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(QColor(self._p.text))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


class NetworkMapPage(_Page):
    """Networkmappage.

    Manages NetworkMapPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Build the page layout (buttons, cards, title header, state panel) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Network Map",
            "A live picture of your connections: This PC \u2192 the apps using the "
            "network \u2192 the remote hosts they reach. Red links go out to the "
            "internet. Fully offline - built from your own socket table.",
        ))

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh Map")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        self.external_only = QCheckBox("External connections only")
        self.external_only.setChecked(True)
        self.external_only.toggled.connect(self._render)
        row.addWidget(self.external_only)
        row.addStretch(1)
        self.summary = QLabel("")
        self.summary.setObjectName("Muted")
        row.addWidget(self.summary)
        self.v.addLayout(row)

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 10, 10, 10)
        self.canvas = _MapCanvas(self.p)
        cl.addWidget(self.canvas)
        self.v.addWidget(card, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.canvas)
        self.v.addWidget(self.state, 1)

        self._conns: list[dict] = []
        self._autoload = self._load
        self._loaded = False

    def _load(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Building network map…")
        from .system_pages import NetworkWorker
        self.win.run_worker(NetworkWorker(), self._on_loaded, self._fail)

    def _on_loaded(self, conns: list, summary: dict):
        """Handle worker results: refresh tables/trees, re-enable buttons and clear the busy state.

        Manages on loaded operations and coordinates related state changes for the component.

        Args:
            conns (list): The conns parameter.
            summary (dict): The summary parameter.
        """
        self.state.clear()
        self.refresh_btn.setEnabled(True)
        self._conns = conns
        self._render()

    def _render(self):
        """Render.

        Manages render operations and coordinates related state changes for the component.
        """
        ext_only = self.external_only.isChecked()
        edges: list[tuple[str, str, bool]] = []
        for c in self._conns:
            if not c.get("remote"):
                continue
            is_ext = c.get("remote_external", False)
            if ext_only and not is_ext:
                continue
            proc = c.get("process") or "?"
            remote = c["remote"].rsplit(":", 1)[0]  # drop port for grouping
            edges.append((proc, remote, is_ext))
        self.canvas.set_edges(edges)
        procs = {e[0] for e in edges}
        remotes = {e[1] for e in edges}
        self.summary.setText(f"{len(procs)} app(s) \u2192 {len(remotes)} host(s)")

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  LAN Device Scanner
# =====================================================================

class LanScanWorker(QObject):
    """Deep multi-protocol LAN discovery on the worker runtime.

    Cancellable: the discovery engine polls the event between passes and
    inside every sweep, so closing the page stops it promptly instead of
    leaving a subnet sweep running.
    """

    finished = Signal(object)   # DiscoveryResult
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, deep: bool = True, rounds: int = 2,
                 audit_profile: str = "targeted",
                 include_upnp_wan: bool = False,
                 requested_networks=None, custom_ports=None, nmap_modes=None,
                 advisory_catalog_path=None):
        """Initialize discovery worker.

        Initializes the instance and configures internal state.

        Args:
            deep (bool): The deep parameter.
            rounds (int): The rounds parameter.
            audit_profile (str): The audit profile parameter.
            include_upnp_wan (bool): The include upnp wan parameter.
            requested_networks: The requested networks parameter.
            custom_ports: The custom ports parameter.
            nmap_modes: The nmap modes parameter.
            advisory_catalog_path: Filesystem path to the target file or directory.
        """
        super().__init__()
        self._deep = deep
        self._rounds = rounds
        self._audit_profile = audit_profile
        self._include_upnp_wan = include_upnp_wan
        self._requested_networks = requested_networks
        self._custom_ports = custom_ports
        self._nmap_modes = nmap_modes
        self._advisory_catalog_path = advisory_catalog_path
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """Request cooperative cancellation so the background operation stops promptly.

        Sets the internal cancellation event to cooperatively stop worker execution at the next safe boundary.
        """
        self._cancel.set()

    def run(self):
        """Run the NetworkDiscovery (network discovery) backend call off the UI thread; emit finished/failed/progress with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.network_discovery import NetworkDiscovery
            result = NetworkDiscovery().scan(
                progress=self.progress.emit,
                cancel_event=self._cancel,
                deep=self._deep,
                rounds=self._rounds,
                audit_profile=self._audit_profile,
                include_upnp_wan=self._include_upnp_wan,
                record_history=True,
                requested_networks=self._requested_networks,
                custom_ports=self._custom_ports,
                nmap_modes=self._nmap_modes,
                advisory_catalog_path=self._advisory_catalog_path,
            )
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class VendorDatabaseWorker(QObject):
    """Vendordatabaseworker.

    Manages VendorDatabaseWorker operations and coordinates related state changes for the component.
    """

    finished = Signal(bool, str)
    failed = Signal(str)

    def __init__(self):
        """Initialize the worker and its finished/failed signals.

        Initializes the instance and configures internal state.
        """
        super().__init__()
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """Request cooperative cancellation so the background operation stops promptly.

        Sets the internal cancellation event to cooperatively stop worker execution at the next safe boundary.
        """
        self._cancel.set()

    def run(self):
        """Run the oui (system tools) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools import oui
            ok, message = oui.refresh_from_ieee(
                timeout=15, cancel_event=self._cancel)
            self.finished.emit(ok, message)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class NetworkScheduleWorker(QObject):
    """Networkscheduleworker.

    Manages NetworkScheduleWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(str, object)
    failed = Signal(str)

    def __init__(self, action: str, spec=None):
        """Store constructor arguments (action, spec) and initialize worker signals.

        Initializes the instance and configures internal state.

        Args:
            action (str): The action parameter.
            spec: The spec parameter.
        """
        super().__init__()
        self._action = action
        self._spec = spec

    def run(self):
        """Run the network automation backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.network_automation import (
                NetworkScanScheduler,
            )
            scheduler = NetworkScanScheduler()
            if self._action == "create":
                scheduler.create(self._spec)
                self.finished.emit("create", scheduler.status())
            elif self._action == "delete":
                self.finished.emit("delete", {"deleted": scheduler.delete()})
            else:
                self.finished.emit("status", scheduler.status())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ExposureLookupWorker(QObject):
    """Exposurelookupworker.

    Manages ExposureLookupWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, provider: str, public_ip: str,
                 api_key: str, api_secret: str):
        """Initialize worker.

        Initializes the instance and configures internal state.

        Args:
            provider (str): The provider parameter.
            public_ip (str): The public ip parameter.
            api_key (str): The api key parameter.
            api_secret (str): The api secret parameter.
        """
        super().__init__()
        self._provider = provider
        self._public_ip = public_ip
        self._api_key = api_key
        self._api_secret = api_secret

    def run(self):
        """Run the external exposure backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.external_exposure import (
                ExternalExposureClient,
            )
            result = ExternalExposureClient(
                self._provider, self._api_key, self._api_secret).lookup(
                    self._public_ip, consent=True)
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DeviceActionWorker(QObject):
    """Deviceactionworker.

    Manages DeviceActionWorker operations and coordinates related state changes for the component.
    """

    finished = Signal(str, object)
    failed = Signal(str)

    def __init__(self, action: str, device, networks):
        """Store constructor arguments (action, device, networks) and initialize worker signals.

        Initializes the instance and configures internal state.

        Args:
            action (str): The action parameter.
            device: The device parameter.
            networks: The networks parameter.
        """
        super().__init__()
        self._action = action
        self._device = device
        self._networks = tuple(networks)

    def run(self):
        """Run the NetworkTools (network tools) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            if self._action == "ping":
                from cortex_unified.system_tools.network_service_scanner import (
                    is_authorized_target,
                )
                from cortex_unified.system_tools.network_tools import NetworkTools

                if not is_authorized_target(self._device.ip, self._networks):
                    raise ValueError("selected device is outside the active scan scope")
                self.finished.emit("ping", NetworkTools().ping(
                    self._device.ip, count=2, timeout_s=2).to_dict())
                return
            if self._action == "wake":
                import ipaddress

                from cortex_unified.system_tools.wake_on_lan import (
                    send_magic_packet,
                )

                address = ipaddress.IPv4Address(self._device.ip)
                network = next(
                    ipaddress.IPv4Network(value, strict=False)
                    for value in self._networks
                    if address in ipaddress.IPv4Network(value, strict=False)
                )
                sent = send_magic_packet(
                    self._device.mac, str(network.broadcast_address),
                    self._networks)
                self.finished.emit("wake", {"bytes_sent": sent})
                return
            raise ValueError("unsupported device action")
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class LanDevicesPage(_Page):
    """Everything actually on your local network, not just the ARP cache.

    The old version read ``arp -a``, which only lists devices this PC happened
    to talk to recently - so a sleeping phone, a Google TV or an ESP32 board
    were routinely absent. This page runs real discovery: it forces ARP replies
    across the subnet and listens to mDNS, UPnP and WS-Discovery to get names
    and device types as well.
    """

    _COLS = [
        "IP address", "Name", "Type / OS", "Vendor", "MAC address",
        "Services", "Security", "Evidence",
    ]

    def __init__(self, win):
        """Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Network Security Audit",
            "Discovers phones, TVs, PCs, routers and IoT devices, then audits "
            "their reachable services with evidence-based identity and security "
            "findings. Every active probe is restricted to this PC's private "
            "subnets; public targets are never scanned automatically.",
        ))

        self._devices: list = []
        self._last_result = None
        self._device_windows: list = []
        self._action_worker: DeviceActionWorker | None = None
        self._page_busy = False

        primary_row = QHBoxLayout()
        self.refresh_btn = QPushButton("Basic Scan")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.setToolTip(
            "Deep device discovery plus a compact set of common service ports.")
        self.refresh_btn.clicked.connect(
            lambda: self._load(deep=True, rounds=2, audit_profile="targeted"))

        self.scan_lan_btn = QPushButton("Scan LAN")
        self.scan_lan_btn.setToolTip("Enumerate all devices on local network using LanScanner (ARP cache & IEEE OUI registry).")
        self.scan_lan_btn.clicked.connect(self._scan_lan_arp)

        self.thorough_btn = QPushButton("Advanced Audit")
        self.thorough_btn.setToolTip(
            "Multiple discovery passes, common TCP/UDP services, safe banners, "
            "TLS metadata, router WAN address and read-only port mappings.")
        self.thorough_btn.clicked.connect(
            lambda: self._load(deep=True, rounds=3, audit_profile="advanced",
                               include_upnp_wan=True))

        self.deep_btn = QPushButton("All TCP Ports")
        self.deep_btn.setToolTip(
            "Explicit authorized audit of TCP ports 1-65535 on discovered local "
            "devices. This can take several minutes.")
        self.deep_btn.clicked.connect(self._confirm_deep_audit)

        self.quick_btn = QPushButton("Passive Discovery")
        self.quick_btn.setToolTip(
            "Listens for announcements and reads the ARP table without probing "
            "addresses or services. Fast and sends almost nothing.")
        self.quick_btn.clicked.connect(
            lambda: self._load(deep=False, rounds=1, audit_profile="targeted"))

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel)

        self.vendor_btn = QPushButton("Update Vendors")
        self.vendor_btn.setToolTip(
            "Explicitly download official IEEE MA-L/MA-M/MA-S assignments. "
            "No device or project data is sent.")
        self.vendor_btn.clicked.connect(self._update_vendors)

        self.export_btn = QPushButton("Export Report")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export_report)

        self.export_inv_csv_btn = QPushButton("Export CSV (Inventory)")
        self.export_inv_csv_btn.setEnabled(False)
        self.export_inv_csv_btn.setToolTip("Export network inventory with device trust, MACs and findings to CSV.")
        self.export_inv_csv_btn.clicked.connect(self._export_inventory_csv)

        self.wan_audit_btn = QPushButton("Audit WAN")
        self.wan_audit_btn.setToolTip("Run external perimeter audit via WanAuditor / WAN Audit page.")
        self.wan_audit_btn.clicked.connect(self._open_wan_audit)

        self.device_btn = QPushButton("Scan Device")
        self.device_btn.setObjectName("Primary")
        self.device_btn.setEnabled(False)
        self.device_btn.setToolTip(
            "Open the selected device in its own window with a full per-device "
            "service, identity and security audit.")
        self.device_btn.clicked.connect(self._open_device_window)

        self.ping_btn = QPushButton("Ping Device")
        self.ping_btn.setEnabled(False)
        self.ping_btn.clicked.connect(lambda: self._device_action("ping"))
        self.wake_btn = QPushButton("Wake")
        self.wake_btn.setEnabled(False)
        self.wake_btn.clicked.connect(lambda: self._device_action("wake"))
        self.open_btn = QPushButton("Open Service")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._open_selected_service)

        self.more_controls_btn = QPushButton("More Controls  \u203A")
        self.more_controls_btn.setObjectName("CommandDisclosure")
        self.more_controls_btn.setCheckable(True)
        self.more_controls_btn.setToolTip(
            "Show deep scan, passive discovery, reporting, and device actions.")
        self.more_controls_btn.toggled.connect(self._toggle_more_controls)

        primary_row.addWidget(self.refresh_btn)
        primary_row.addWidget(self.scan_lan_btn)
        primary_row.addWidget(self.thorough_btn)
        primary_row.addWidget(self.device_btn)
        primary_row.addWidget(self.more_controls_btn)
        primary_row.addWidget(self.cancel_btn)
        primary_row.addStretch(1)
        self.count = QLabel("")
        self.count.setObjectName("Muted")
        primary_row.addWidget(self.count)
        self.v.addLayout(primary_row)

        self.command_panel = QWidget()
        self.command_panel.setObjectName("CommandPanel")
        command_layout = QVBoxLayout(self.command_panel)
        command_layout.setContentsMargins(10, 8, 10, 8)
        command_layout.setSpacing(6)

        scan_row = QHBoxLayout()
        scan_row.setSpacing(8)
        scan_label = QLabel("SCAN MODES")
        scan_label.setObjectName("CommandGroupLabel")
        scan_row.addWidget(scan_label)
        scan_row.addWidget(self.deep_btn)
        scan_row.addWidget(self.quick_btn)
        data_label = QLabel("DATA & REPORTS")
        data_label.setObjectName("CommandGroupLabel")
        scan_row.addWidget(data_label)
        scan_row.addWidget(self.vendor_btn)
        scan_row.addWidget(self.export_btn)
        scan_row.addWidget(self.export_inv_csv_btn)
        scan_row.addWidget(self.wan_audit_btn)
        scan_row.addStretch(1)
        command_layout.addLayout(scan_row)

        device_row = QHBoxLayout()
        device_row.setSpacing(8)
        device_label = QLabel("SELECTED DEVICE")
        device_label.setObjectName("CommandGroupLabel")
        device_row.addWidget(device_label)
        device_row.addWidget(self.ping_btn)
        device_row.addWidget(self.wake_btn)
        device_row.addWidget(self.open_btn)
        device_row.addStretch(1)
        command_layout.addLayout(device_row)

        self.command_panel.setVisible(False)
        self.v.addWidget(self.command_panel)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        self.v.addWidget(self.status)

        self.main_tabs = QTabWidget()
        self.dashboard_tab = QWidget()
        self.dashboard_layout = QVBoxLayout(self.dashboard_tab)
        dashboard_cards = QHBoxLayout()
        self.card_devices = StatCard(self.p, "Devices", "0")
        self.card_services = StatCard(self.p, "Open services", "0")
        self.card_findings = StatCard(self.p, "Findings", "0")
        self.card_risk = StatCard(self.p, "Risk score", "0")
        for card in (self.card_devices, self.card_services,
                     self.card_findings, self.card_risk):
            dashboard_cards.addWidget(card)
        self.dashboard_layout.addLayout(dashboard_cards)

        self.devices_tab = QWidget()
        self.devices_layout = QVBoxLayout(self.devices_tab)

        self.findings_tbl = QTableWidget(0, 6)
        self.findings_tbl.setHorizontalHeaderLabels([
            "Severity", "Device", "Finding", "Port", "Confidence",
            "Remediation",
        ])
        self.findings_tbl.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch)
        self.findings_tbl.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Stretch)
        self.findings_tbl.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.findings_tbl.setAlternatingRowColors(True)

        self.topology_view = QTextEdit()
        self.topology_view.setReadOnly(True)
        self.topology_view.setPlainText(
            "Logical topology will appear after a scan. It reflects gateway, "
            "subnet, and endpoint evidence—not physical switch/AP cabling.")

        self.history_tbl = QTableWidget(0, 6)
        self.history_tbl.setHorizontalHeaderLabels([
            "Observed", "Devices", "Services", "Findings", "Risk", "Scan",
        ])
        self.history_tbl.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.history_tbl.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)

        self.expert_tab = QWidget()
        expert_layout = QVBoxLayout(self.expert_tab)
        expert_note = QLabel(
            "Manual scopes may only narrow an active local private interface. "
            "Custom ports augment the selected profile. Nmap is optional; "
            "SYN/ACK/OS modes require explicit elevation and are never run by "
            "the normal scan buttons.")
        expert_note.setWordWrap(True)
        expert_layout.addWidget(expert_note)
        scope_row = QHBoxLayout()
        scope_row.addWidget(QLabel("Private IP / range / CIDR:"))
        self.scope_input = QLineEdit()
        self.scope_input.setPlaceholderText(
            "Auto, one IP, full start-end range, or 192.168.1.0/24")
        scope_row.addWidget(self.scope_input)
        scope_row.addWidget(QLabel("TCP ports:"))
        self.ports_input = QLineEdit()
        self.ports_input.setPlaceholderText("e.g. 22,80,443,8000-8010")
        scope_row.addWidget(self.ports_input)
        self.nmap_check = QCheckBox("Use optional Nmap")
        scope_row.addWidget(self.nmap_check)
        self.nmap_mode = QComboBox()
        self.nmap_mode.addItems([
            "Connect + version", "SYN + version (admin)",
            "ACK firewall map (admin)", "SYN + version + OS (admin)",
        ])
        scope_row.addWidget(self.nmap_mode)
        self.expert_btn = QPushButton("Run Expert Scan")
        self.expert_btn.clicked.connect(self._run_expert_scan)
        scope_row.addWidget(self.expert_btn)
        expert_layout.addLayout(scope_row)

        metadata_row = QHBoxLayout()
        metadata_row.addWidget(QLabel("Selected device:"))
        self.custom_name_input = QLineEdit()
        self.custom_name_input.setPlaceholderText("Custom name")
        metadata_row.addWidget(self.custom_name_input)
        self.trust_combo = QComboBox()
        self.trust_combo.addItems(["unknown", "trusted", "guest", "blocked"])
        metadata_row.addWidget(self.trust_combo)
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("tags, comma-separated")
        metadata_row.addWidget(self.tags_input)
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Notes")
        metadata_row.addWidget(self.notes_input)
        self.save_metadata_btn = QPushButton("Save Metadata")
        self.save_metadata_btn.clicked.connect(self._save_selected_metadata)
        metadata_row.addWidget(self.save_metadata_btn)
        expert_layout.addLayout(metadata_row)

        catalog_row = QHBoxLayout()
        catalog_row.addWidget(QLabel("Local advisory catalog:"))
        self.catalog_input = QLineEdit()
        self.catalog_input.setPlaceholderText(
            "Optional bounded JSON catalog for exact product/version matches")
        catalog_row.addWidget(self.catalog_input)
        self.catalog_btn = QPushButton("Browse")
        self.catalog_btn.clicked.connect(self._browse_advisory_catalog)
        catalog_row.addWidget(self.catalog_btn)
        expert_layout.addLayout(catalog_row)

        inventory_row = QHBoxLayout()
        self.export_inventory_btn = QPushButton("Export Inventory CSV")
        self.export_inventory_btn.clicked.connect(self._export_inventory_csv)
        inventory_row.addWidget(self.export_inventory_btn)
        self.import_inventory_btn = QPushButton("Import Metadata CSV")
        self.import_inventory_btn.clicked.connect(self._import_inventory_csv)
        inventory_row.addWidget(self.import_inventory_btn)
        inventory_row.addStretch(1)
        expert_layout.addLayout(inventory_row)

        exposure_row = QHBoxLayout()
        exposure_row.addWidget(QLabel("External index:"))
        self.exposure_provider = QComboBox()
        self.exposure_provider.addItems(["shodan", "censys"])
        exposure_row.addWidget(self.exposure_provider)
        self.exposure_key = QLineEdit()
        self.exposure_key.setPlaceholderText("API key / Censys ID")
        self.exposure_key.setEchoMode(QLineEdit.EchoMode.Password)
        exposure_row.addWidget(self.exposure_key)
        self.exposure_secret = QLineEdit()
        self.exposure_secret.setPlaceholderText("Censys secret (if used)")
        self.exposure_secret.setEchoMode(QLineEdit.EchoMode.Password)
        exposure_row.addWidget(self.exposure_secret)
        self.exposure_consent = QCheckBox(
            "Send only router-reported public IP to provider")
        exposure_row.addWidget(self.exposure_consent)
        self.exposure_btn = QPushButton("Lookup Exposure")
        self.exposure_btn.clicked.connect(self._lookup_external_exposure)
        exposure_row.addWidget(self.exposure_btn)
        expert_layout.addLayout(exposure_row)
        self.exposure_output = QTextEdit()
        self.exposure_output.setReadOnly(True)
        self.exposure_output.setMaximumHeight(170)
        expert_layout.addWidget(self.exposure_output)
        expert_layout.addStretch(1)

        self.automation_tab = QWidget()
        automation_layout = QVBoxLayout(self.automation_tab)
        automation_note = QLabel(
            "Recurring scans run through Windows Task Scheduler and update the "
            "same local SQLite history. They never run deep all-port, Nmap, "
            "UPnP WAN, external API, login, or exploit checks. Cortex can show "
            "local tray alerts for new devices, services, gateway changes, and "
            "medium-or-higher security changes while the GUI is running.")
        automation_note.setWordWrap(True)
        automation_layout.addWidget(automation_note)
        schedule_row = QHBoxLayout()
        schedule_row.addWidget(QLabel("Frequency:"))
        self.schedule_frequency = QComboBox()
        self.schedule_frequency.addItems(["hourly", "daily", "weekly"])
        schedule_row.addWidget(self.schedule_frequency)
        schedule_row.addWidget(QLabel("Time:"))
        self.schedule_time = QLineEdit("09:00")
        self.schedule_time.setMaximumWidth(80)
        schedule_row.addWidget(self.schedule_time)
        schedule_row.addWidget(QLabel("Weekday:"))
        self.schedule_weekday = QComboBox()
        self.schedule_weekday.addItems([
            "MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"])
        schedule_row.addWidget(self.schedule_weekday)
        self.schedule_create_btn = QPushButton("Create / Update Schedule")
        self.schedule_create_btn.clicked.connect(self._create_schedule)
        schedule_row.addWidget(self.schedule_create_btn)
        self.schedule_delete_btn = QPushButton("Remove Schedule")
        self.schedule_delete_btn.clicked.connect(self._delete_schedule)
        schedule_row.addWidget(self.schedule_delete_btn)
        self.schedule_status_btn = QPushButton("Refresh Status")
        self.schedule_status_btn.clicked.connect(
            lambda: self._run_schedule_action("status"))
        schedule_row.addWidget(self.schedule_status_btn)
        automation_layout.addLayout(schedule_row)
        self.schedule_status = QTextEdit()
        self.schedule_status.setReadOnly(True)
        automation_layout.addWidget(self.schedule_status, 1)

        self.main_tabs.addTab(self.dashboard_tab, "Dashboard")
        self.main_tabs.addTab(self.devices_tab, "Devices")
        self.main_tabs.addTab(self.findings_tbl, "Findings")
        self.main_tabs.addTab(self.topology_view, "Logical Topology")
        self.main_tabs.addTab(self.history_tbl, "History & Trends")
        self.main_tabs.addTab(self.automation_tab, "Automation & Alerts")
        self.main_tabs.addTab(self.expert_tab, "Expert")
        self.v.addWidget(self.main_tabs, 1)

        # Model/view instead of an item-based table. Beyond the allocation win,
        # this fixes a latent correctness bug: selection used to resolve as
        # ``self._devices[view_row]``, so the moment the table gained sorting the
        # selected row would map to the wrong device. The binding resolves the
        # record through the proxy, so it stays correct under any sort or filter.
        self.tbl = QTableView()
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.table = bind_table(
            self.tbl, self._device_columns(),
            sort_column=0, sort_order=Qt.SortOrder.AscendingOrder,  # IP order
        )
        # A QTableView exposes the selection model rather than
        # itemSelectionChanged, and it fires for keyboard navigation too.
        self.tbl.selectionModel().selectionChanged.connect(self._show_device_details)
        # Double-clicking a row is the fastest path to the full device window.
        self.tbl.doubleClicked.connect(self._open_device_window)
        self.devices_layout.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.devices_layout.addWidget(self.state, 1)

        self.detail_tabs = QTabWidget()
        self.detail_tabs.setVisible(False)
        self.detail_tabs.setMaximumHeight(220)
        self._detail_views: dict[str, QTextEdit] = {}
        for tab_name in ("Overview", "Services", "Identity", "Security", "History", "Raw Evidence"):
            view = QTextEdit()
            view.setReadOnly(True)
            self._detail_views[tab_name] = view
            self.detail_tabs.addTab(view, tab_name)
        self.devices_layout.addWidget(self.detail_tabs)

        self.wan_status = QLabel("")
        self.wan_status.setObjectName("Muted")
        self.wan_status.setWordWrap(True)
        self.wan_status.setVisible(False)
        self.dashboard_layout.addWidget(self.wan_status)

        self.findings = QLabel("")
        self.findings.setWordWrap(True)
        self.findings.setVisible(False)
        self.dashboard_layout.addWidget(self.findings)

        self.history = QLabel("")
        self.history.setObjectName("Muted")
        self.history.setWordWrap(True)
        self.history.setVisible(False)
        self.dashboard_layout.addWidget(self.history)

        self.notes = QLabel("")
        self.notes.setObjectName("Muted")
        self.notes.setWordWrap(True)
        self.notes.setVisible(False)
        self.dashboard_layout.addWidget(self.notes)

        note = QLabel(
            "A device that is powered off or in deep sleep cannot be detected by "
            "any scanner - it isn't answering. If something you expect is still "
            "missing, wake it and run a Thorough Scan. Devices showing a private "
            "address are hiding their identity on purpose. Per-device bandwidth "
            "is not inferred from this endpoint: accurate attribution requires "
            "router/AP counters or explicit administrator packet capture support."
        )
        note.setObjectName("Muted")
        note.setWordWrap(True)
        self.dashboard_layout.addWidget(note)
        self.dashboard_layout.addStretch(1)

        self._autoload = self._load
        self._loaded = False

    # -- actions -----------------------------------------------------------

    def _toggle_more_controls(self, visible: bool) -> None:
        """Toggle more controls for the results widgets; keeps buttons/state in sync.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.

        Args:
            visible (bool): The visible parameter.
        """
        self.command_panel.setVisible(visible)
        marker = "\u2304" if visible else "\u203A"
        self.more_controls_btn.setText(f"More Controls  {marker}")
        self.more_controls_btn.setProperty("expanded", visible)
        style = self.more_controls_btn.style()
        style.unpolish(self.more_controls_btn)
        style.polish(self.more_controls_btn)

    def _load(self, deep: bool = True, rounds: int = 2,
              audit_profile: str = "targeted",
              include_upnp_wan: bool = False,
              requested_networks=None, custom_ports=None, nmap_modes=None,
              advisory_catalog_path=None):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.

        Args:
            deep (bool): The deep parameter.
            rounds (int): The rounds parameter.
            audit_profile (str): The audit profile parameter.
            include_upnp_wan (bool): The include upnp wan parameter.
            requested_networks: The requested networks parameter.
            custom_ports: The custom ports parameter.
            nmap_modes: The nmap modes parameter.
            advisory_catalog_path: Filesystem path to the target file or directory.
        """
        self._busy(True)
        self.state.show_loading("Discovering and auditing devices\u2026")
        self._worker = LanScanWorker(
            deep=deep, rounds=rounds, audit_profile=audit_profile,
            include_upnp_wan=include_upnp_wan,
            requested_networks=requested_networks,
            custom_ports=custom_ports, nmap_modes=nmap_modes,
            advisory_catalog_path=advisory_catalog_path)
        self.win.run_worker(self._worker, self._on_loaded, self._fail,
                            on_progress=self.status.setText)

    def _run_expert_scan(self):
        """Run expert scan for the results widgets after confirmation; keeps buttons/state in sync.

        Manages run expert scan operations and coordinates related state changes for the component.
        """
        try:
            from cortex_unified.system_tools.network_service_scanner import (
                parse_custom_port_spec,
                parse_network_scope_spec,
            )
            ports = parse_custom_port_spec(self.ports_input.text())
            scopes = parse_network_scope_spec(
                self.scope_input.text()) or None
            nmap_modes = None
            if self.nmap_check.isChecked():
                if not ports:
                    raise ValueError(
                        "Optional Nmap requires an explicit bounded port list")
                modes = (
                    ("connect", "version"), ("syn", "version"), ("ack",),
                    ("syn", "version", "os"),
                )
                nmap_modes = modes[self.nmap_mode.currentIndex()]
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid expert scan", str(exc))
            return
        if nmap_modes:
            answer = QMessageBox.question(
                self, "Run explicit Nmap scan?",
                "Nmap will scan only discovered devices inside the selected "
                "active private scope and only the listed ports. No scripts, "
                "login attempts, exploits, or public targets are used. "
                "Administrator modes may require elevation. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._load(
            deep=True, rounds=2, audit_profile="advanced",
            include_upnp_wan=True, requested_networks=scopes,
            custom_ports=ports, nmap_modes=nmap_modes,
            advisory_catalog_path=self.catalog_input.text().strip() or None)

    def _browse_advisory_catalog(self):
        """Browse advisory catalog for the results widgets via file dialog; keeps buttons/state in sync.

        Manages browse advisory catalog operations and coordinates related state changes for the component.
        """
        path, _selected = QFileDialog.getOpenFileName(
            self, "Select local advisory catalog", "",
            "JSON advisory catalog (*.json)")
        if path:
            self.catalog_input.setText(path)

    # -- device table columns ----------------------------------------------

    def _device_columns(self):
        """Declare the device columns once instead of filling cells per row.

        Each column derives its text from the ``Device`` record on demand, so a
        scan result is handed to the model in a single reset. The IP column sorts
        on a packed integer rather than the dotted string - otherwise
        ``192.168.1.10`` would sort before ``192.168.1.9``.
        """
        return [
            Column("IP address", lambda d: d.ip, sort_key=_ip_sort_key),
            Column("Name", self._device_name, stretch=True),
            Column("Type / OS", self._device_type),
            Column("Vendor", lambda d: d.vendor or "\u2014"),
            Column("MAC address", lambda d: d.mac or "\u2014"),
            Column("Services", self._device_services, stretch=True),
            Column("Security", self._device_security,
                   sort_key=self._device_security_rank),
            Column("Evidence", lambda d: d.evidence, stretch=True),
        ]

    def _device_name(self, dev) -> str:
        """Return the display name for a discovered device (custom name plus router/this-PC tag).

        Manages device name operations and coordinates related state changes for the component.

        Args:
            dev: The dev parameter.

        Returns:
            str: Formatted string or path.
        """
        metadata = self._metadata_by_key.get(self._identity_of(dev))
        name = metadata.custom_name if metadata else dev.label
        if dev.is_gateway:
            name += "  (router)"
        elif dev.is_self:
            name += "  (this PC)"
        return name

    def _device_type(self, dev) -> str:
        """Return the type/OS string for a device including trust state and OS fingerprint.

        Manages device type operations and coordinates related state changes for the component.

        Args:
            dev: The dev parameter.

        Returns:
            str: Formatted string or path.
        """
        metadata = self._metadata_by_key.get(self._identity_of(dev))
        type_os = dev.kind
        if metadata and metadata.trust_state != "unknown":
            type_os += f" / {metadata.trust_state.title()}"
        fingerprint = getattr(dev, "fingerprint", None)
        if fingerprint is not None:
            os_name = getattr(fingerprint, "os_family", "unknown")
            confidence = int(getattr(fingerprint, "confidence", 0.0) * 100)
            if os_name != "unknown":
                type_os += f" / {os_name} ({confidence}% confidence)"
        return type_os

    @staticmethod
    def _device_services(dev) -> str:
        """Return the compact service summary (port/proto/name) for the device row.

        Manages device services operations and coordinates related state changes for the component.

        Args:
            dev: The dev parameter.

        Returns:
            str: Formatted string or path.
        """
        observed = sorted(
            getattr(dev, "service_observations", ()),
            key=lambda item: (item.port, item.transport, item.name))
        services = ", ".join(
            f"{item.port}/{item.transport} {item.name}"
            for item in observed[:8]) or "\u2014"
        if len(observed) > 8:
            services += f"  +{len(observed) - 8} more"
        return services

    def _device_findings(self, dev) -> list:
        """Return the severity-sorted security findings for a device IP.

        Manages device findings operations and coordinates related state changes for the component.

        Args:
            dev: The dev parameter.

        Returns:
            list: List of processed items or identifiers.
        """
        return sorted(
            self._findings_by_ip.get(dev.ip, ()),
            key=lambda item: _SEVERITY_RANK.get(item.severity, 5))

    def _device_security(self, dev) -> str:
        """Return the headline security text for a device row.

        Manages device security operations and coordinates related state changes for the component.

        Args:
            dev: The dev parameter.

        Returns:
            str: Formatted string or path.
        """
        found = self._device_findings(dev)
        if not found:
            return "No evidence-backed finding"
        security = f"{found[0].severity.upper()}: {found[0].title}"
        if len(found) > 1:
            security += f"  +{len(found) - 1} more"
        return security

    def _device_security_rank(self, dev) -> int:
        """Sort worst-first: a device with a critical finding outranks a clean one.

        Manages device security rank operations and coordinates related state changes for the component.

        Args:
            dev: The dev parameter.

        Returns:
            int: Result of the operation.
        """
        found = self._device_findings(dev)
        if not found:
            return len(_SEVERITY_RANK) + 1
        return _SEVERITY_RANK.get(found[0].severity, len(_SEVERITY_RANK))

    def _identity_of(self, dev) -> str:
        """Return the stable identity key used for metadata/findings lookup.

        Manages identity of operations and coordinates related state changes for the component.

        Args:
            dev: The dev parameter.

        Returns:
            str: Formatted string or path.
        """
        resolver = self._identity_key_for
        return resolver(dev) if resolver is not None else ""

    def _open_device_window(self, *_args):
        """Open the selected device in its own full-detail premium window.

        Manages open device window operations and coordinates related state changes for the component.
        """
        device = self._selected_device()
        result = self._last_result
        if device is None or result is None:
            return
        from .device_window import DeviceDetailWindow

        window = DeviceDetailWindow(
            self.win, device, result.networks,
            catalog_path=self.catalog_input.text().strip() or None,
            parent=self.win)
        # Keep a strong reference until the dialog emits its pre-delete close
        # signal, including while it waits for worker cancellation callbacks.
        self._device_windows.append(window)
        window.closed.connect(self._forget_device_window)
        window.show()
        window.raise_()
        window.activateWindow()
        window.start_scan("advanced")

    def _forget_device_window(self, window) -> None:
        """Forget device window for the results widgets; keeps buttons/state in sync.

        Manages forget device window operations and coordinates related state changes for the component.

        Args:
            window: Parent window or shell controller instance.
        """
        self._device_windows = [
            item for item in self._device_windows if item is not window
        ]

    def _selected_device(self):
        """The selected ``Device``, resolved through the proxy.

        Previously this indexed ``self._devices`` by the view's row number, which
        silently returned the wrong device as soon as the table was sorted. The
        binding maps the proxy index back to the source record instead.
        """
        return self.table.selected_record()

    def _device_action(self, action: str):
        """Device action for the results widgets on a worker thread; keeps buttons/state in sync.

        Manages device action operations and coordinates related state changes for the component.

        Args:
            action (str): The action parameter.
        """
        device = self._selected_device()
        result = self._last_result
        if (
            device is None
            or result is None
            or self._action_worker is not None
        ):
            return
        self.status.setText(
            f"{'Pinging' if action == 'ping' else 'Sending wake packet to'} "
            f"{device.label}...")
        self._action_worker = DeviceActionWorker(
            action, device, result.networks)
        self._show_device_details()
        self.win.run_worker(
            self._action_worker,
            self._device_action_done,
            self._device_action_failed,
        )

    def _device_action_done(self, action: str, payload):
        """Handle completion of the device acti asynchronous task.

        Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

        Args:
            action (str): The action parameter.
            payload: The payload parameter.
        """
        self._action_worker = None
        self._show_device_details()
        if action == "ping":
            message = (
                "Device replied to ping" if payload.get("reachable") else
                "Device did not reply to ping; firewalls can block ICMP")
        else:
            message = "Wake-on-LAN magic packet sent to the local broadcast"
        self.status.setText(message)
        self.win.statusBar().showMessage(message, 6000)
        tray = getattr(self.win, "_tray", None)
        if tray is not None:
            tray.show_message("Network device action", message)

    def _device_action_failed(self, message: str) -> None:
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            message (str): Informational or progress status message.
        """
        self._action_worker = None
        self._show_device_details()
        self.status.setText(f"Device action failed: {message}")
        QMessageBox.warning(self, "Device action failed", message)

    def _open_selected_service(self):
        """Open selected service for the results widgets in the browser/tool; keeps buttons/state in sync.

        Manages open selected service operations and coordinates related state changes for the component.
        """
        device = self._selected_device()
        if device is None:
            return
        services = sorted(
            getattr(device, "service_observations", ()),
            key=lambda item: (item.port, item.transport))
        priority = {"https": 0, "http": 1, "ssh": 2, "rdp": 3}
        candidates = [item for item in services if item.name in priority]
        if not candidates:
            return
        service = min(candidates, key=lambda item: priority[item.name])
        if service.name in {"http", "https"}:
            url = f"{service.name}://{device.ip}:{service.port}/"
        elif service.name == "ssh":
            url = f"ssh://{device.ip}:{service.port}"
        else:
            url = f"rdp://{device.ip}:{service.port}"
        QDesktopServices.openUrl(QUrl(url))

    def _load_selected_metadata(self, device):
        """Load selected metadata for the results widgets; keeps buttons/state in sync.

        Manages load selected metadata operations and coordinates related state changes for the component.

        Args:
            device: The device parameter.
        """
        try:
            from cortex_unified.system_tools.network_inventory import (
                NetworkInventory,
            )
            with NetworkInventory() as inventory:
                metadata = inventory.get_metadata(device)
        except (OSError, ValueError, RuntimeError):
            metadata = None
        self.custom_name_input.setText(
            metadata.custom_name if metadata else "")
        self.trust_combo.setCurrentText(
            metadata.trust_state if metadata else "unknown")
        self.tags_input.setText(
            ", ".join(metadata.tags) if metadata else "")
        self.notes_input.setText(metadata.notes if metadata else "")

    def _save_selected_metadata(self):
        """Save selected metadata for the results widgets after confirmation; keeps buttons/state in sync.

        Manages save selected metadata operations and coordinates related state changes for the component.
        """
        device = self._selected_device()
        if device is None:
            QMessageBox.information(
                self, "Select a device", "Select a device in the Devices tab first.")
            return
        try:
            from cortex_unified.system_tools.network_inventory import (
                NetworkInventory,
            )
            with NetworkInventory() as inventory:
                metadata = inventory.set_metadata(
                    device,
                    custom_name=self.custom_name_input.text(),
                    trust_state=self.trust_combo.currentText(),
                    tags=self.tags_input.text(),
                    notes=self.notes_input.text())
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Metadata not saved", str(exc))
            return
        message = f"Metadata saved for {metadata.identity_key}"
        self.status.setText(message)
        # Refresh the cached metadata the Name/Type columns read from, then let
        # the model repaint. Previously this patched one cell by row number,
        # which both bypassed the data source and broke under sorting.
        self._metadata_by_key[metadata.identity_key] = metadata
        self.table.model.set_records(self.table.model.records)

    def _export_inventory_csv(self):
        """Export inventory csv for the results widgets via file dialog as CSV; keeps buttons/state in sync.

        Manages export inventory csv operations and coordinates related state changes for the component.
        """
        path, _selected = QFileDialog.getSaveFileName(
            self, "Export device inventory", "network-inventory.csv",
            "CSV inventory (*.csv)")
        if not path:
            return
        try:
            from cortex_unified.system_tools.network_inventory import (
                NetworkInventory,
            )
            with NetworkInventory() as inventory:
                count = inventory.export_inventory_csv(path)
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Inventory export failed", str(exc))
            return
        self.status.setText(f"Exported {count} inventory device(s) to {path}")

    def _import_inventory_csv(self):
        """Import inventory csv for the results widgets via file dialog as CSV; keeps buttons/state in sync.

        Manages import inventory csv operations and coordinates related state changes for the component.
        """
        path, _selected = QFileDialog.getOpenFileName(
            self, "Import device metadata", "", "CSV inventory (*.csv)")
        if not path:
            return
        try:
            from cortex_unified.system_tools.network_inventory import (
                NetworkInventory,
            )
            with NetworkInventory() as inventory:
                preview = inventory.import_inventory_csv(path, dry_run=True)
                conflicts = len(preview["conflicts"])
                answer = QMessageBox.question(
                    self, "Import device metadata?",
                    f"Validated {preview['rows']} row(s); {conflicts} existing "
                    "metadata record(s) conflict. Existing records will be "
                    "replaced. Continue?",
                    QMessageBox.StandardButton.Yes |
                    QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No)
                if answer != QMessageBox.StandardButton.Yes:
                    return
                report = inventory.import_inventory_csv(
                    path, dry_run=False, overwrite=True)
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Inventory import failed", str(exc))
            return
        self.status.setText(
            f"Imported metadata: {report['created']} new, "
            f"{report['updated']} updated")
        device = self._selected_device()
        if device is not None:
            self._load_selected_metadata(device)

    def _lookup_external_exposure(self):
        """Lookup external exposure for the results widgets after confirmation on a worker thread; keeps buttons/state in sync.

        Manages lookup external exposure operations and coordinates related state changes for the component.
        """
        result = self._last_result
        wan = getattr(result, "wan_status", None) if result is not None else None
        public_ip = getattr(wan, "external_ip", "") if wan is not None else ""
        classification = (
            getattr(wan, "external_ip_classification", "")
            if wan is not None else "")
        if classification != "public" or not public_ip:
            QMessageBox.warning(
                self, "No router-reported public IP",
                "Run Advanced Audit with router WAN reading first. CGNAT, "
                "private-upstream, missing, and local addresses are never sent.")
            return
        if not self.exposure_consent.isChecked():
            QMessageBox.warning(
                self, "Consent required",
                "Check the consent box to send only the displayed public IP "
                "and your API credentials to the selected provider.")
            return
        provider = self.exposure_provider.currentText()
        api_key = self.exposure_key.text()
        api_secret = self.exposure_secret.text()
        if not api_key or (provider == "censys" and not api_secret):
            QMessageBox.warning(
                self, "Credentials required",
                "Enter provider API credentials. They are used for this "
                "lookup only and are not stored in inventory or logs.")
            return
        self.exposure_output.setPlainText(
            f"Querying {provider} for {public_ip}...")
        self.exposure_btn.setEnabled(False)
        self._exposure_worker = ExposureLookupWorker(
            provider, public_ip, api_key, api_secret)
        self.win.run_worker(
            self._exposure_worker, self._exposure_done,
            self._exposure_failed)

    def _exposure_done(self, result):
        """Handle completion of the exposure asynchronous task.

        Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

        Args:
            result: Collection or dictionary holding operation results.
        """
        self.exposure_btn.setEnabled(True)
        self.exposure_secret.clear()
        self.exposure_output.setPlainText(json.dumps(
            result.to_dict(), indent=2, ensure_ascii=False))

    def _exposure_failed(self, message: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            message (str): Informational or progress status message.
        """
        self.exposure_btn.setEnabled(True)
        self.exposure_secret.clear()
        self.exposure_output.setPlainText(message)

    def _create_schedule(self):
        """Create schedule for the results widgets after confirmation; keeps buttons/state in sync.

        Manages create schedule operations and coordinates related state changes for the component.
        """
        answer = QMessageBox.question(
            self, "Create recurring network scan?",
            "This creates or replaces one Windows Task Scheduler entry for "
            "bounded private-LAN inventory scans. It is reversible with Remove "
            "Schedule. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            from cortex_unified.system_tools.network_automation import (
                NetworkSchedule,
            )
            from cortex_unified.system_tools.network_service_scanner import (
                parse_network_scope_spec,
            )
            scopes = parse_network_scope_spec(self.scope_input.text())
            spec = NetworkSchedule(
                frequency=self.schedule_frequency.currentText(),
                time=self.schedule_time.text().strip(),
                weekday=self.schedule_weekday.currentText(),
                profile="advanced", scopes=scopes,
                ports=self.ports_input.text().strip())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid schedule", str(exc))
            return
        self._run_schedule_action("create", spec)

    def _delete_schedule(self):
        """Delete schedule for the results widgets after confirmation; keeps buttons/state in sync.

        Manages delete schedule operations and coordinates related state changes for the component.
        """
        answer = QMessageBox.question(
            self, "Remove recurring scan?",
            "Remove the Cortex recurring network-security scan from Windows "
            "Task Scheduler? Existing local history is kept.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self._run_schedule_action("delete")

    def _run_schedule_action(self, action: str, spec=None):
        """Run schedule action for the results widgets on a worker thread; keeps buttons/state in sync.

        Manages run schedule action operations and coordinates related state changes for the component.

        Args:
            action (str): The action parameter.
            spec: The spec parameter.
        """
        self.schedule_status.setPlainText(
            f"{action.capitalize()} schedule operation in progress...")
        self._schedule_worker = NetworkScheduleWorker(action, spec)
        self.win.run_worker(
            self._schedule_worker, self._schedule_done,
            self._schedule_failed)

    def _schedule_done(self, action: str, payload):
        """Handle completion of the schedule asynchronous task.

        Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

        Args:
            action (str): The action parameter.
            payload: The payload parameter.
        """
        self.schedule_status.setPlainText(
            json.dumps(payload, indent=2, ensure_ascii=False))
        self.win.statusBar().showMessage(
            f"Network schedule {action} completed", 6000)

    def _schedule_failed(self, message: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            message (str): Informational or progress status message.
        """
        self.schedule_status.setPlainText(message)
        QMessageBox.warning(self, "Schedule operation failed", message)

    def _confirm_deep_audit(self):
        """Confirm deep audit for the results widgets after confirmation; keeps buttons/state in sync.

        Manages confirm deep audit operations and coordinates related state changes for the component.
        """
        answer = QMessageBox.question(
            self,
            "Run authorized deep audit?",
            "This checks all 65,535 TCP ports on devices already discovered on "
            "your private LAN. It is read-only and cancellable, but it creates "
            "substantial traffic and may take several minutes.\n\nRun it only "
            "on a network you own or are authorized to assess.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._load(deep=True, rounds=3, audit_profile="deep",
                       include_upnp_wan=True)

    def _update_vendors(self):
        """Update vendors for the results widgets on a worker thread; keeps buttons/state in sync.

        Manages update vendors operations and coordinates related state changes for the component.
        """
        self.vendor_btn.setEnabled(False)
        self.status.setText("Downloading official IEEE vendor assignments\u2026")
        self._vendor_worker = VendorDatabaseWorker()
        self.win.run_worker(
            self._vendor_worker, self._vendors_updated, self._vendor_update_failed)

    def _vendors_updated(self, ok: bool, message: str):
        """Handle worker results: note status, re-enable buttons and clear the busy state.

        Manages vendors updated operations and coordinates related state changes for the component.

        Args:
            ok (bool): The ok parameter.
            message (str): Informational or progress status message.
        """
        self.vendor_btn.setEnabled(True)
        self.status.setText(message)
        self.win.statusBar().showMessage(message, 8000)
        if not ok or self._last_result is None:
            return
        from cortex_unified.system_tools import oui
        for device in self._last_result.devices:
            device.vendor = oui.describe_vendor(device.mac)
        self._on_loaded(self._last_result)

    def _vendor_update_failed(self, message: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            message (str): Informational or progress status message.
        """
        self.vendor_btn.setEnabled(True)
        self.status.setText(f"Vendor update failed: {message}")

    def _export_report(self):
        """Export report for the results widgets via file dialog as CSV; keeps buttons/state in sync.

        Manages export report operations and coordinates related state changes for the component.
        """
        result = self._last_result
        if result is None:
            return
        path, selected = QFileDialog.getSaveFileName(
            self, "Export network security report", "network-security-report.json",
            "JSON report (*.json);;Printable HTML report (*.html);;"
            "PDF report (*.pdf);;CSV services (*.csv)")
        if not path:
            return
        target = Path(path)
        suffix = target.suffix.lower()
        if suffix not in {".json", ".html", ".pdf", ".csv"}:
            if "PDF" in selected:
                suffix = ".pdf"
            elif "HTML" in selected:
                suffix = ".html"
            elif "CSV" in selected:
                suffix = ".csv"
            else:
                suffix = ".json"
            target = target.with_suffix(suffix)
        try:
            if suffix == ".json":
                target.write_text(
                    json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
                    encoding="utf-8")
            elif suffix == ".csv":
                with target.open("w", newline="", encoding="utf-8-sig") as handle:
                    writer = csv.writer(handle)
                    writer.writerow([
                        "ip", "device", "type", "os", "port", "transport",
                        "service", "product", "version", "banner"])
                    for device in result.devices:
                        fingerprint = getattr(device, "fingerprint", None)
                        for service in getattr(device, "service_observations", ()):
                            writer.writerow([
                                device.ip, device.label, device.kind,
                                getattr(fingerprint, "os_family", "unknown"),
                                service.port, service.transport, service.name,
                                service.product, service.version, service.banner])
            else:
                payload = result.to_dict()
                rows = "".join(
                    "<tr>" + "".join(
                        f"<td>{html.escape(str(value))}</td>"
                        for value in (
                            device.label, device.ip, device.kind, device.vendor,
                            ", ".join(str(p) for p in sorted(device.open_ports))))
                    + "</tr>" for device in result.devices)
                findings = "".join(
                    f"<li><strong>{html.escape(item.severity.upper())}</strong> "
                    f"{html.escape(item.device_ip)} \u2014 {html.escape(item.title)}: "
                    f"{html.escape(item.remediation)}</li>"
                    for item in result.findings)
                document = (
                    "<!doctype html><meta charset='utf-8'><title>Cortex Network "
                    "Security Report</title><style>body{font:14px Segoe UI,sans-serif;"
                    "max-width:1100px;margin:32px auto;color:#1f2937}table{border-collapse:"
                    "collapse;width:100%}th,td{border:1px solid #d1d5db;padding:7px;"
                    "text-align:left}th{background:#eef2ff}</style>"
                    "<h1>Cortex Network Security Report</h1>"
                    f"<p>Devices: {payload['device_count']} | Audit: "
                    f"{html.escape(payload['audit_profile'])}. Evidence-only; absence "
                    "of a finding does not prove absence of a vulnerability.</p>"
                    "<table><tr><th>Device</th><th>IP</th><th>Type</th><th>Vendor</th>"
                    f"<th>Open TCP ports</th></tr>{rows}</table>"
                    f"<h2>Findings</h2><ul>{findings or '<li>None observed</li>'}</ul>")
                if suffix == ".pdf":
                    writer = QPdfWriter(str(target))
                    writer.setTitle("Cortex Network Security Report")
                    document_view = QTextDocument()
                    document_view.setHtml(document)
                    document_view.print_(writer)
                else:
                    target.write_text(document, encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
            return
        self.win.statusBar().showMessage(f"Report exported to {target}", 8000)

    def _export_inventory_csv(self):
        """Export full network inventory to CSV via NetworkInventory.

        Manages export inventory csv operations and coordinates related state changes for the component.
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Network Inventory CSV", "network_inventory.csv", "CSV Files (*.csv)"
        )
        if not file_path:
            return
        try:
            from cortex_unified.system_tools.network_inventory import NetworkInventory, normalize_device
            with NetworkInventory() as inv:
                if self._last_result and hasattr(self._last_result, 'devices'):
                    for d in self._last_result.devices:
                        norm = normalize_device(d)
                        inv.update([norm])
                inv.export_inventory_csv(file_path)
            QMessageBox.information(self, "Export Complete", f"Network inventory exported to:\n{file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", f"Failed to export inventory CSV:\n{exc}")

    def _open_wan_audit(self):
        """Navigate to WAN Audit page or run external WAN audit.

        Manages open wan audit operations and coordinates related state changes for the component.
        """
        try:
            if hasattr(self.win, "nav_to"):
                self.win.nav_to("wan_audit")
            elif hasattr(self.win, "set_active_page"):
                self.win.set_active_page("wan_audit")
            else:
                raise AttributeError("No nav_to")
        except Exception:
            try:
                from cortex_unified.system_tools.wan_audit import WanAuditor
                auditor = WanAuditor()
                res = auditor.audit()
                QMessageBox.information(
                    self, "WAN Audit Quick Result",
                    f"External IP: {res.public_ip}\n"
                    f"ISP: {res.isp}\n"
                    f"Open Ports: {len(res.open_ports)}"
                )
            except Exception as e:
                QMessageBox.warning(self, "WAN Audit", str(e))

    def _scan_lan_arp(self):
        """Enumerate LAN devices via LanScanner (ARP cache & IEEE OUI lookup).

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
        try:
            from cortex_unified.system_tools.lan_scanner import LanScanner
            scanner = LanScanner()
            devices = scanner.scan()
            if not devices:
                QMessageBox.information(self, "Scan LAN", "No active devices found in local ARP cache.")
                return
            lines = [f"Discovered {len(devices)} device(s) in local ARP cache:\n"]
            for d in devices[:20]:
                vendor = f" [{d.vendor}]" if d.vendor else ""
                lines.append(f"• {d.ip} — {d.mac} ({d.kind}){vendor}")
            if len(devices) > 20:
                lines.append(f"\n...and {len(devices) - 20} more devices.")
            self.win.statusBar().showMessage(f"LAN Scan: {len(devices)} devices found via ARP", 6000)
            QMessageBox.information(self, "Scan LAN (ARP Cache)", "\n".join(lines))
        except Exception as exc:
            QMessageBox.critical(self, "Scan LAN Error", str(exc))

    def _show_device_details(self, *_args):
        """Show device details for the results widgets; keeps buttons/state in sync.

        Manages show device details operations and coordinates related state changes for the component.
        """
        device = self.table.selected_record()
        if device is None or self._last_result is None:
            self.detail_tabs.setVisible(False)
            self.device_btn.setEnabled(False)
            self.ping_btn.setEnabled(False)
            self.wake_btn.setEnabled(False)
            self.open_btn.setEnabled(False)
            return
        result = self._last_result
        action_busy = self._action_worker is not None
        controls_available = not self._page_busy and not action_busy
        self._load_selected_metadata(device)
        self.device_btn.setEnabled(controls_available)
        self.ping_btn.setEnabled(controls_available)
        try:
            from cortex_unified.system_tools.wake_on_lan import validate_mac
            validate_mac(device.mac)
            can_wake = True
        except ValueError:
            can_wake = False
        self.wake_btn.setEnabled(controls_available and can_wake)
        actionable = {"http", "https", "ssh", "rdp"}
        self.open_btn.setEnabled(
            controls_available
            and any(
                item.name in actionable
                for item in getattr(device, "service_observations", ())
            )
        )
        fingerprint = getattr(device, "fingerprint", None)
        services = [
            item.to_dict() if hasattr(item, "to_dict") else str(item)
            for item in getattr(device, "service_observations", ())]
        findings = [
            item.to_dict() for item in result.findings
            if item.device_ip == device.ip]
        changes = result.inventory_changes.to_dict() if result.inventory_changes else {}
        relevant_changes = {
            group: [item for item in items if device.ip in str(item)]
            for group, items in changes.items()
        }
        overview = {
            "name": device.label, "ip": device.ip, "mac": device.mac,
            "vendor": device.vendor, "type": device.kind,
            "gateway": device.is_gateway, "this_pc": device.is_self,
            "discovery_evidence": device.evidence,
        }
        identity = fingerprint.to_dict() if fingerprint is not None else {
            "confidence": 0, "note": "No fingerprint evidence available"}
        views = {
            "Overview": overview,
            "Services": services,
            "Identity": identity,
            "Security": findings,
            "History": relevant_changes,
            "Raw Evidence": device.to_dict(),
        }
        for name, payload in views.items():
            self._detail_views[name].setPlainText(
                json.dumps(payload, indent=2, ensure_ascii=False))
        self.detail_tabs.setVisible(True)

    def _cancel(self):
        """Cancel.

        Manages cancel operations and coordinates related state changes for the component.
        """
        worker = getattr(self, "_worker", None)
        if worker is not None:
            worker.cancel()
        vendor_worker = getattr(self, "_vendor_worker", None)
        if vendor_worker is not None:
            vendor_worker.cancel()
        self.status.setText("Cancelling\u2026")

    def _busy(self, busy: bool) -> None:
        """Update the busy state indicators across the interface.

        Shows or hides loading indicators, adjusts cursor feedback, and toggles action button availability.

        Args:
            busy (bool): The busy parameter.
        """
        self._page_busy = busy
        for btn in (self.refresh_btn, self.thorough_btn, self.deep_btn,
                    self.quick_btn, self.vendor_btn, self.expert_btn):
            btn.setEnabled(not busy)
        self.export_btn.setEnabled(
            not busy and self._last_result is not None)
        self.cancel_btn.setEnabled(busy)
        self.cancel_btn.setVisible(busy)
        self.progress.setVisible(busy)
        if busy:
            # The per-device window depends on the finished scan's scope, so it
            # stays unavailable until this scan produces a result.
            for btn in (self.device_btn, self.ping_btn, self.wake_btn,
                        self.open_btn):
                btn.setEnabled(False)
        else:
            self._show_device_details()

    def _on_loaded(self, result):
        """Handle worker results: refresh tables/trees, update cards/labels, update the state panel and clear the busy state.

        Manages on loaded operations and coordinates related state changes for the component.

        Args:
            result: Collection or dictionary holding operation results.
        """
        self._busy(False)
        self._last_result = result
        self.export_btn.setEnabled(True)
        self.export_inv_csv_btn.setEnabled(True)

        def _ip_key(dev):
            """Build a numeric sort key for IP addresses so dotted octets order correctly.

            Manages ip key operations and coordinates related state changes for the component.

            Args:
                dev: The dev parameter.
            """
            try:
                return (0,) + tuple(int(p) for p in dev.ip.split("."))
            except (ValueError, AttributeError):
                return (1, dev.ip)

        # Sort here as well as in the engine: the table should always read in
        # address order regardless of how the results arrived.
        devices = sorted(result.devices, key=_ip_key)
        self._devices = devices

        # Lookups the column accessors read from. Resolved once per scan rather
        # than per row, then the model derives every cell on demand.
        self._findings_by_ip = {}
        for finding in result.findings:
            self._findings_by_ip.setdefault(finding.device_ip, []).append(finding)
        try:
            from cortex_unified.system_tools.network_inventory import (
                NetworkInventory, identity_key_for,
            )
            with NetworkInventory() as inventory:
                self._metadata_by_key = {
                    item.identity_key: item for item in inventory.list_metadata()
                }
            self._identity_key_for = identity_key_for
        except (OSError, ValueError, RuntimeError):
            self._metadata_by_key = {}
            self._identity_key_for = None

        self.table.set_records(devices)

        if not devices:
            self.state.show_empty(
                "No devices answered. If you are on Wi-Fi, the access point may "
                "be using client isolation, which blocks devices from seeing "
                "each other.")
        else:
            self.state.clear()

        nets = ", ".join(result.networks) or "no sweepable subnet"
        summary = (f"{len(devices)} device(s) on {nets} "
                   f"in {result.duration_seconds:.0f}s")
        if result.cancelled:
            summary += " (cancelled early - results may be incomplete)"
        self.count.setText(f"{len(devices)} device(s)")
        self.status.setText(summary)
        self.win.statusBar().showMessage(summary, 6000)

        wan = result.wan_status
        if wan is not None:
            gateway = wan.gateway or "not detected"
            public = wan.external_ip or "not reported by the local router"
            classification = wan.external_ip_classification.replace("_", " ")
            mappings = len(wan.port_mappings)
            self.wan_status.setText(
                f"WAN (router-reported only): gateway {gateway}; external address "
                f"{public} ({classification}); {mappings} enabled/configured mapping "
                f"record(s). Internet reachability was not tested.")
            self.wan_status.setVisible(True)
        else:
            self.wan_status.setVisible(False)

        if result.findings:
            counts: dict[str, int] = {}
            for finding in result.findings:
                counts[finding.severity] = counts.get(finding.severity, 0) + 1
            count_text = ", ".join(
                f"{counts[level]} {level}"
                for level in ("critical", "high", "medium", "low", "info")
                if counts.get(level))
            top = result.findings[:5]
            lines = [f"Security findings: {count_text}"]
            lines.extend(
                f"\u2022 {item.severity.upper()} \u2014 {item.device_ip}: "
                f"{item.title}. {item.remediation}"
                for item in top)
            if len(result.findings) > len(top):
                lines.append(f"\u2022 {len(result.findings) - len(top)} more in device rows")
            self.findings.setText("\n".join(lines))
            self.findings.setVisible(True)
        else:
            self.findings.setText(
                "No evidence-backed security finding was produced. This does not "
                "prove the devices are vulnerability-free.")
            self.findings.setVisible(True)

        changes = result.inventory_changes
        if changes is not None:
            parts = []
            if changes.new_devices:
                parts.append(f"{len(changes.new_devices)} newly seen device(s)")
            if changes.changed_addresses:
                parts.append(f"{len(changes.changed_addresses)} address change(s)")
            if changes.new_services:
                parts.append(f"{len(changes.new_services)} newly exposed service(s)")
            if getattr(changes, "new_findings", ()):
                parts.append(f"{len(changes.new_findings)} new security finding(s)")
            if getattr(changes, "severity_changes", ()):
                parts.append(
                    f"{len(changes.severity_changes)} severity change(s)")
            if getattr(changes, "disappeared_devices", ()):
                parts.append(
                    f"{len(changes.disappeared_devices)} device(s) offline")
            if changes.gateway_mac_changes:
                parts.append("gateway hardware address changed")
            self.history.setText(
                "History: " + (", ".join(parts) if parts else "no changes since the previous scan"))
            self.history.setVisible(True)
            tray = getattr(self.win, "_tray", None)
            if tray is not None:
                tray.notify_network_changes(changes)
        else:
            self.history.setVisible(False)

        if result.notes:
            self.notes.setText("  \u2022  " + "\n  \u2022  ".join(result.notes))
            self.notes.setVisible(True)
        else:
            self.notes.setVisible(False)

        service_count = sum(
            len(getattr(device, "service_observations", ()))
            for device in devices)
        risk_weights = {
            "critical": 10, "high": 7, "medium": 4, "low": 1,
            "info": 0,
        }
        risk_score = sum(
            risk_weights.get(item.severity, 0) for item in result.findings)
        self.card_devices.set_value(str(len(devices)))
        self.card_services.set_value(str(service_count))
        self.card_findings.set_value(str(len(result.findings)))
        self.card_risk.set_value(str(risk_score))

        self.findings_tbl.setRowCount(len(result.findings))
        for row, finding in enumerate(result.findings):
            values = (
                finding.severity.upper(), finding.device_ip, finding.title,
                str(finding.port or "\u2014"),
                f"{finding.confidence * 100:.0f}%", finding.remediation,
            )
            for column, value in enumerate(values):
                self.findings_tbl.setItem(
                    row, column, QTableWidgetItem(value))

        gateways = [device for device in devices if device.is_gateway]
        gateway_label = gateways[0].label if gateways else "Gateway (unseen)"
        topology = [
            "LOGICAL TOPOLOGY — not physical switch/AP cabling",
            f"{gateway_label}",
        ]
        for network in result.networks:
            topology.append(f"  \u2514\u2500 Subnet {network}")
            for device in devices:
                try:
                    inside = ipaddress.IPv4Address(
                        device.ip) in ipaddress.ip_network(
                            network, strict=False)
                except ValueError:
                    inside = False
                if inside and not device.is_gateway:
                    trust = "private MAC" if device.randomized_mac else device.kind
                    topology.append(
                        f"       \u251c\u2500 {device.label} [{device.ip}] — {trust}")
        self.topology_view.setPlainText("\n".join(topology))

        try:
            from cortex_unified.system_tools.network_inventory import (
                NetworkInventory,
            )
            with NetworkInventory() as inventory:
                trends = inventory.exposure_trends(50)
        except (OSError, ValueError, RuntimeError):
            trends = []
        self.history_tbl.setRowCount(len(trends))
        for row, trend in enumerate(trends):
            values = (
                trend["observed_at"], trend["device_count"],
                trend["service_count"], trend["finding_count"],
                trend["risk_score"], trend["snapshot_id"],
            )
            for column, value in enumerate(values):
                self.history_tbl.setItem(
                    row, column, QTableWidgetItem(str(value)))

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self._busy(False)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Network Tools (ping / traceroute / DNS / ports / IP info)
# =====================================================================

class _ToolWorker(QObject):
    """Toolworker.

    Manages ToolWorker operations and coordinates related state changes for the component.
    """

    finished = Signal(str, object)   # (tool, result)
    failed = Signal(str)

    def __init__(self, tool: str, target: str):
        """Store constructor arguments (tool, target) and initialize worker signals.

        Initializes the instance and configures internal state.

        Args:
            tool (str): The tool parameter.
            target (str): The target parameter.
        """
        super().__init__()
        self._tool = tool
        self._target = target

    def run(self):
        """Run the NetworkTools (network tools) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.network_tools import NetworkTools
            nt = NetworkTools()
            t = self._tool
            if t == "ping":
                res = nt.ping(self._target)
                self.finished.emit(t, res.to_dict())
            elif t == "traceroute":
                res = [h.to_dict() for h in nt.traceroute(self._target)]
                self.finished.emit(t, res)
            elif t == "dns":
                fwd = nt.dns_lookup(self._target)
                rev = {ip: nt.reverse_dns(ip) for ip in fwd}
                self.finished.emit(t, {"forward": fwd, "reverse": rev})
            elif t == "ports":
                self.finished.emit(t, nt.scan_common_ports(self._target))
            elif t == "ipinfo":
                info = nt.ip_info(self._target)
                if not info.get("valid"):
                    # Resolve a hostname to an IP first, then classify.
                    ips = nt.dns_lookup(self._target)
                    if ips:
                        info = nt.ip_info(ips[0])
                        info["resolved_from"] = self._target
                self.finished.emit(t, info)
            else:
                self.failed.emit("Unknown tool.")
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class RemoteServerDialog(QDialog):
    """Remoteserverdialog.

    Manages RemoteServerDialog operations and coordinates related state changes for the component.
    """

    def __init__(self, parent=None):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setWindowTitle("Remote Network Server Browser (SMB / FTP / SFTP / WebDAV)")
        self.resize(750, 520)
        from cortex_unified.explorer.network import NetworkManager, NetworkProtocol
        self._mgr = NetworkManager(self)
        self._connected_proto = None

        layout = QVBoxLayout(self)

        # Connection setup group
        conn_group = QGroupBox("Server Connection Parameters")
        conn_form = QFormLayout(conn_group)

        self.proto_combo = QComboBox()
        self.proto_combo.addItems(["SMB (Windows Share)", "FTP", "SFTP (SSH)", "WebDAV"])
        self.proto_combo.currentIndexChanged.connect(self._on_proto_changed)
        conn_form.addRow("Protocol:", self.proto_combo)

        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("e.g. 192.168.1.100 or server.local")
        conn_form.addRow("Host / Address:", self.host_input)

        self.port_input = QLineEdit("445")
        conn_form.addRow("Port:", self.port_input)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username (leave empty for anonymous)")
        conn_form.addRow("Username:", self.user_input)

        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        conn_form.addRow("Password:", self.pass_input)

        self.remember_chk = QCheckBox("Remember Credentials")
        conn_form.addRow("", self.remember_chk)

        btn_row = QHBoxLayout()
        self.connect_btn = QPushButton("Connect to Server")
        self.connect_btn.setObjectName("Primary")
        self.connect_btn.clicked.connect(self._connect)
        btn_row.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.clicked.connect(self._disconnect)
        btn_row.addWidget(self.disconnect_btn)

        conn_form.addRow("", btn_row)
        layout.addWidget(conn_group)

        # File browser group
        browse_group = QGroupBox("Remote File Explorer")
        browse_layout = QVBoxLayout(browse_group)

        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("Remote Path:"))
        self.remote_path_input = QLineEdit("/")
        path_row.addWidget(self.remote_path_input)
        self.list_btn = QPushButton("List / Refresh")
        self.list_btn.setEnabled(False)
        self.list_btn.clicked.connect(self._list_remote_files)
        path_row.addWidget(self.list_btn)
        browse_layout.addLayout(path_row)

        self.files_table = QTableWidget()
        self.files_table.setColumnCount(4)
        self.files_table.setHorizontalHeaderLabels(["Name", "Type", "Size", "Modified"])
        self.files_table.horizontalHeader().setStretchLastSection(True)
        self.files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        browse_layout.addWidget(self.files_table)

        action_row = QHBoxLayout()
        self.download_btn = QPushButton("Download Selected")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self._download_selected)
        action_row.addWidget(self.download_btn)
        action_row.addStretch()
        browse_layout.addLayout(action_row)

        layout.addWidget(browse_group)

        self.status_lbl = QLabel("Enter server details and click Connect.")
        layout.addWidget(self.status_lbl)

    def _get_active_protocol(self):
        """Get active protocol.

        Manages get active protocol operations and coordinates related state changes for the component.
        """
        from cortex_unified.explorer.network import NetworkProtocol
        idx = self.proto_combo.currentIndex()
        return [NetworkProtocol.SMB, NetworkProtocol.FTP, NetworkProtocol.SFTP, NetworkProtocol.WEBDAV][idx]

    def _on_proto_changed(self, idx: int):
        """On proto changed.

        Manages on proto changed operations and coordinates related state changes for the component.

        Args:
            idx (int): The idx parameter.
        """
        ports = ["445", "21", "22", "443"]
        self.port_input.setText(ports[idx])

    def _connect(self):
        """Connect to the configured remote network server.

        Validates host address, port, and credentials for the selected protocol
        (SMB, FTP, SFTP, or WebDAV) and mounts the remote filesystem in the UI.
        """
        proto = self._get_active_protocol()
        host = self.host_input.text().strip()
        if not host:
            QMessageBox.warning(self, "Invalid Host", "Please enter a server host address.")
            return
        port = int(self.port_input.text().strip() or "0")
        user = self.user_input.text().strip()
        pwd = self.pass_input.text()

        self.status_lbl.setText(f"Connecting to {host} via {proto.name}...")
        try:
            ok = self._mgr.connect(proto, host, port=port, username=user, password=pwd)
            if ok:
                self._connected_proto = proto
                self.status_lbl.setText(f"Connected to {host} ({proto.name}).")
                self.disconnect_btn.setEnabled(True)
                self.list_btn.setEnabled(True)
                self.connect_btn.setEnabled(False)
                if self.remember_chk.isChecked():
                    try:
                        self._mgr.store_credentials(proto, host, user, pwd)
                    except Exception:
                        pass
                self._list_remote_files()
            else:
                self.status_lbl.setText(f"Connection failed to {host}.")
                QMessageBox.warning(self, "Connection Failed", f"Could not connect to {host}. Please verify server credentials and network availability.")
        except Exception as exc:
            self.status_lbl.setText(f"Error: {exc}")
            QMessageBox.critical(self, "Connection Error", str(exc))

    def _disconnect(self):
        """Disconnect.

        Manages disconnect operations and coordinates related state changes for the component.
        """
        if self._connected_proto:
            self._mgr.disconnect(self._connected_proto)
            self._connected_proto = None
        self.status_lbl.setText("Disconnected.")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.list_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.files_table.setRowCount(0)

    def _list_remote_files(self):
        """List remote files.

        Manages list remote files operations and coordinates related state changes for the component.
        """
        if not self._connected_proto:
            return
        path = self.remote_path_input.text().strip() or "/"
        provider = self._mgr.get_provider(self._connected_proto)
        if not provider:
            return
        try:
            files = provider.list_files(path)
            self.files_table.setRowCount(len(files))
            for i, f in enumerate(files):
                self.files_table.setItem(i, 0, QTableWidgetItem(f.name))
                self.files_table.setItem(i, 1, QTableWidgetItem("Directory" if f.is_dir else "File"))
                sz_str = "" if f.is_dir else fmt_bytes(f.size)
                self.files_table.setItem(i, 2, QTableWidgetItem(sz_str))
                self.files_table.setItem(i, 3, QTableWidgetItem(str(f.modified_time)))
            self.download_btn.setEnabled(len(files) > 0)
            self.status_lbl.setText(f"Listed {len(files)} items in {path}")
        except Exception as exc:
            self.status_lbl.setText(f"Failed to list: {exc}")

    def _download_selected(self):
        """Download selected.

        Manages download selected operations and coordinates related state changes for the component.
        """
        row = self.files_table.currentRow()
        if row < 0 or not self._connected_proto:
            return
        fname = self.files_table.item(row, 0).text()
        provider = self._mgr.get_provider(self._connected_proto)
        if not provider:
            return
        local_dir = QFileDialog.getExistingDirectory(self, "Select Download Destination")
        if not local_dir:
            return
        remote_path = f"{self.remote_path_input.text().rstrip('/')}/{fname}"
        import os
        local_path = os.path.join(local_dir, fname)
        try:
            ok = provider.download_file(remote_path, local_path)
            if ok:
                QMessageBox.information(self, "Download Finished", f"File downloaded to:\n{local_path}")
            else:
                QMessageBox.warning(self, "Download Failed", f"Could not download {fname}.")
        except Exception as exc:
            QMessageBox.critical(self, "Download Error", str(exc))


class NetworkToolsPage(_Page):
    """Networktoolspage.

    Manages NetworkToolsPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Network Tools",
            "Everyday diagnostics - ping, traceroute, DNS lookup, port and IP "
            "checks. These reach the target you enter (that's their job); IP "
            "classification is computed offline with no external lookups.",
        ))

        inp = QHBoxLayout()
        inp.addWidget(QLabel("Target:"))
        self.target = QLineEdit()
        self.target.setPlaceholderText("hostname or IP  (e.g. google.com or 1.1.1.1)")
        self.target.returnPressed.connect(lambda: self._run("ping"))
        inp.addWidget(self.target, 1)
        self.selfpc_btn = QPushButton("This PC")
        self.selfpc_btn.clicked.connect(lambda: self.target.setText("127.0.0.1"))
        inp.addWidget(self.selfpc_btn)
        self.v.addLayout(inp)

        btns = QHBoxLayout()
        for label, tool in (("Ping", "ping"), ("Traceroute", "traceroute"),
                            ("DNS Lookup", "dns"), ("IP Info", "ipinfo"),
                            ("Open Ports", "ports")):
            b = QPushButton(label)
            if tool == "ping":
                b.setObjectName("Primary")
            b.clicked.connect(lambda _=False, t=tool: self._run(t))
            btns.addWidget(b)

        self.server_btn = QPushButton("Connect Server (SMB/FTP/SFTP/WebDAV)")
        self.server_btn.setToolTip("Connect Server dialog & remote file browser (SMB, FTP, SFTP, WebDAV)")
        self.server_btn.clicked.connect(self._open_remote_server_dialog)
        btns.addWidget(self.server_btn)

        btns.addStretch(1)
        self.v.addLayout(btns)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 16, 18, 16)
        self.summary = QLabel("Enter a target and choose a tool.")
        self.summary.setWordWrap(True)
        self.summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        cl.addWidget(self.summary)
        self.v.addWidget(card)

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["#", "Host / Port", "Detail"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setVisible(False)
        self.v.addWidget(self.tbl, 1)

        self._busy_count = 0

    def _run(self, tool: str):
        """Run.

        Manages run operations and coordinates related state changes for the component.

        Args:
            tool (str): The tool parameter.
        """
        target = self.target.text().strip()
        if not target and tool != "ports":
            self.summary.setText("Please enter a hostname or IP first.")
            return
        if tool == "ports" and not target:
            target = "127.0.0.1"
            self.target.setText(target)
        self.progress.setVisible(True)
        self.summary.setText(f"Running {tool}\u2026")
        self.tbl.setVisible(False)
        self.win.run_worker(_ToolWorker(tool, target), self._on_result, self._fail)

    def _on_result(self, tool: str, result):
        """Handle worker results: update widgets and clear the busy state.

        Manages on result operations and coordinates related state changes for the component.

        Args:
            tool (str): The tool parameter.
            result: Collection or dictionary holding operation results.
        """
        self.progress.setVisible(False)
        if tool == "ping":
            self._show_ping(result)
        elif tool == "traceroute":
            self._show_traceroute(result)
        elif tool == "dns":
            self._show_dns(result)
        elif tool == "ports":
            self._show_ports(result)
        elif tool == "ipinfo":
            self._show_ipinfo(result)

    # -- renderers --
    def _show_ping(self, r: dict):
        """Show ping for the results widgets; keeps buttons/state in sync.

        Manages show ping operations and coordinates related state changes for the component.

        Args:
            r (dict): The r parameter.
        """
        self.tbl.setVisible(False)
        if not r["reachable"]:
            self.summary.setText(f"<b>{r['host']}</b> is <b>unreachable</b>. "
                                 + (r.get("error") or "No reply received."))
            return
        self.summary.setText(
            f"<b>{r['host']}</b> is reachable.<br>"
            f"Packets: sent {r['sent']}, received {r['received']}, "
            f"loss {r['loss_percent']}%<br>"
            f"Latency: min {r['min_ms']} ms, avg <b>{r['avg_ms']} ms</b>, max {r['max_ms']} ms")

    def _show_traceroute(self, hops: list):
        """Show traceroute for the results widgets; keeps buttons/state in sync.

        Manages show traceroute operations and coordinates related state changes for the component.

        Args:
            hops (list): The hops parameter.
        """
        self.summary.setText(f"Route traced - {len(hops)} hop(s):")
        self.tbl.setHorizontalHeaderLabels(["#", "Host", "Avg latency"])
        self.tbl.setRowCount(len(hops))
        for i, h in enumerate(hops):
            self.tbl.setItem(i, 0, QTableWidgetItem(str(h["number"])))
            self.tbl.setItem(i, 1, QTableWidgetItem(h["host"] or "*"))
            avg = h.get("avg_ms")
            self.tbl.setItem(i, 2, QTableWidgetItem(f"{avg} ms" if avg is not None else "timeout"))
        self.tbl.setVisible(True)

    def _show_dns(self, r: dict):
        """Show dns for the results widgets; keeps buttons/state in sync.

        Manages show dns operations and coordinates related state changes for the component.

        Args:
            r (dict): The r parameter.
        """
        fwd = r["forward"]
        if not fwd:
            self.summary.setText("No DNS records found (or the name doesn't resolve).")
            self.tbl.setVisible(False)
            return
        self.summary.setText(f"Resolved to {len(fwd)} address(es):")
        self.tbl.setHorizontalHeaderLabels(["#", "IP address", "Reverse (PTR)"])
        self.tbl.setRowCount(len(fwd))
        for i, ip in enumerate(fwd):
            self.tbl.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.tbl.setItem(i, 1, QTableWidgetItem(ip))
            self.tbl.setItem(i, 2, QTableWidgetItem(r["reverse"].get(ip, "") or "\u2014"))
        self.tbl.setVisible(True)

    def _show_ports(self, res: dict):
        """Show ports for the results widgets; keeps buttons/state in sync.

        Manages show ports operations and coordinates related state changes for the component.

        Args:
            res (dict): The res parameter.
        """
        from cortex_unified.system_tools.network_tools import COMMON_PORTS
        open_ports = [(p, o) for p, o in res.items()]
        open_count = sum(1 for _, o in open_ports if o)
        self.summary.setText(
            f"Checked {len(open_ports)} common ports on <b>{self.target.text()}</b> - "
            f"<b>{open_count} open</b>. Open ports are potential entry points; "
            "close services you don't need.")
        shown = sorted(open_ports, key=lambda x: (not x[1], x[0]))
        self.tbl.setHorizontalHeaderLabels(["Port", "Service", "State"])
        self.tbl.setRowCount(len(shown))
        for i, (port, is_open) in enumerate(shown):
            self.tbl.setItem(i, 0, QTableWidgetItem(str(port)))
            self.tbl.setItem(i, 1, QTableWidgetItem(COMMON_PORTS.get(port, "")))
            state = QTableWidgetItem("OPEN" if is_open else "closed")
            if is_open:
                state.setForeground(Qt.GlobalColor.red)
            self.tbl.setItem(i, 2, state)
        self.tbl.setVisible(True)

    def _show_ipinfo(self, info: dict):
        """Show ipinfo for the results widgets; keeps buttons/state in sync.

        Manages show ipinfo operations and coordinates related state changes for the component.

        Args:
            info (dict): The info parameter.
        """
        self.tbl.setVisible(False)
        if not info.get("valid"):
            self.summary.setText("That isn't a valid IP, and the name couldn't be resolved.")
            return
        origin = (f" (resolved from {info['resolved_from']})"
                  if info.get("resolved_from") else "")
        self.summary.setText(
            f"<b>{info['address']}</b>{origin}<br>"
            f"Type: <b>{info['category']}</b> \u2014 IPv{info['version']}<br>"
            f"private={info['private']}, loopback={info['loopback']}, "
            f"global={info['global']}, reserved={info['reserved']}<br>"
            "<span>Classification is computed locally from the address - Cortex "
            "does not query any external geolocation or reputation service.</span>")

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.progress.setVisible(False)
        self.summary.setText(f"Error: {msg}")

    def _open_remote_server_dialog(self):
        """Open the interactive Remote Server Browser (SMB/FTP/SFTP/WebDAV) dialog.

        Manages open remote server dialog operations and coordinates related state changes for the component.
        """
        dlg = RemoteServerDialog(self)
        dlg.exec()


# =====================================================================
#  Load / Resilience Tester  (authorized, own-infrastructure only)
# =====================================================================

from PySide6.QtWidgets import QSpinBox  # noqa: E402


class AuthorizeWorker(QObject):
    """Authorizeworker.

    Manages AuthorizeWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, host: str, token: str = ""):
        """Store constructor arguments (host, token) and initialize worker signals.

        Initializes the instance and configures internal state.

        Args:
            host (str): The host parameter.
            token (str): The token parameter.
        """
        super().__init__()
        self._host = host
        self._token = token

    def run(self):
        """Run the TargetAuthorizer (load tester) backend call off the UI thread; emit finished/failed with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.load_tester import TargetAuthorizer
            auth = TargetAuthorizer().authorize(self._host, self._token or None)
            self.finished.emit(auth.to_dict())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class LoadTestWorker(QObject):
    """Loadtestworker.

    Manages LoadTestWorker operations and coordinates related state changes for the component.
    """
    progress = Signal(dict)
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, mode: str, cfg: dict, auth_dict: dict):
        """Store constructor arguments (mode, cfg, auth_dict) and initialize worker signals.

        Initializes the instance and configures internal state.

        Args:
            mode (str): The mode parameter.
            cfg (dict): The cfg parameter.
            auth_dict (dict): The auth dict parameter.
        """
        super().__init__()
        self._mode = mode
        self._cfg = cfg
        self._auth_dict = auth_dict
        import threading as _t
        self._cancel = _t.Event()

    def cancel(self):
        """Request cooperative cancellation so the background operation stops promptly.

        Sets the internal cancellation event to cooperatively stop worker execution at the next safe boundary.
        """
        self._cancel.set()

    def run(self):
        """Run the load tester backend call off the UI thread; emit finished/failed/progress with results.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.load_tester import (
                Authorization, HttpLoadConfig, LoadTester, TcpLoadConfig,
            )
            auth = Authorization(**self._auth_dict)
            tester = LoadTester()
            if self._mode == "http":
                cfg = HttpLoadConfig(**self._cfg)
                res = tester.run_http(cfg, auth, progress=self.progress.emit,
                                      cancel_event=self._cancel)
            else:
                cfg = TcpLoadConfig(**self._cfg)
                res = tester.run_tcp(cfg, auth, progress=self.progress.emit,
                                     cancel_event=self._cancel)
            self.finished.emit(res.summary())
        except PermissionError as exc:
            self.failed.emit(f"Not authorized: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class LoadTesterPage(_Page):
    """Loadtesterpage.

    Manages LoadTesterPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Build the page layout (buttons, cards, title header, controls) and connect button/worker actions.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Load / Resilience Tester",
            "Push realistic load at infrastructure you control and see where it "
            "degrades - so you fix the weak point before an incident. Targets are "
            "limited to your own machines (localhost / LAN) or a public host you "
            "prove you own. No spoofing, no evasion - honest, measurable load.",
        ))

        self._auth: dict | None = None
        self._token = ""

        # -- target + authorization --
        cfg_card = Card(self.p)
        cl = QVBoxLayout(cfg_card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(10)

        trow = QHBoxLayout()
        trow.addWidget(QLabel("Target:"))
        self.target = QLineEdit()
        self.target.setPlaceholderText("http://127.0.0.1:8000/  or  192.168.1.50")
        trow.addWidget(self.target, 1)
        self.check_btn = QPushButton("Check Authorization")
        self.check_btn.clicked.connect(self._check)
        trow.addWidget(self.check_btn)
        cl.addLayout(trow)

        self.auth_label = QLabel("Enter a target and check authorization.")
        self.auth_label.setObjectName("Muted")
        self.auth_label.setWordWrap(True)
        cl.addWidget(self.auth_label)

        # token workflow (hidden until a public host needs it)
        self.token_box = QLabel("")
        self.token_box.setObjectName("Muted")
        self.token_box.setWordWrap(True)
        self.token_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.token_box.setVisible(False)
        cl.addWidget(self.token_box)

        # -- load parameters --
        prow = QHBoxLayout()
        prow.addWidget(QLabel("Mode:"))
        self.mode = QComboBox()
        self.mode.addItems(["HTTP requests (L7)", "TCP connections (L4)"])
        self.mode.currentIndexChanged.connect(self._mode_changed)
        prow.addWidget(self.mode)
        prow.addWidget(QLabel("Port:"))
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(80)
        self.port.setEnabled(False)
        prow.addWidget(self.port)
        prow.addWidget(QLabel("Concurrency:"))
        self.conc = QSpinBox()
        self.conc.setRange(1, 500)
        self.conc.setValue(20)
        prow.addWidget(self.conc)
        prow.addWidget(QLabel("Duration (s):"))
        self.dur = QSpinBox()
        self.dur.setRange(1, 600)
        self.dur.setValue(15)
        prow.addWidget(self.dur)
        prow.addStretch(1)
        cl.addLayout(prow)
        self.v.addWidget(cfg_card)

        # -- run row --
        run_row = QHBoxLayout()
        self.run_btn = QPushButton("Start Test")
        self.run_btn.setObjectName("Primary")
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._toggle)
        run_row.addWidget(self.run_btn)
        self.live = QLabel("")
        self.live.setObjectName("Muted")
        run_row.addWidget(self.live, 1)
        self.v.addLayout(run_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        # -- results --
        res_card = Card(self.p)
        rl = QVBoxLayout(res_card)
        rl.setContentsMargins(18, 16, 18, 16)
        self.results = QLabel("Results will appear here after a test.")
        self.results.setWordWrap(True)
        self.results.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        rl.addWidget(self.results)
        self.v.addWidget(res_card, 1)

        self._worker = None
        self._running = False

    # -- mode --
    def _mode_changed(self):
        """Mode changed via the worker/widgets; results return through worker signals.

        Manages mode changed operations and coordinates related state changes for the component.
        """
        is_tcp = self.mode.currentIndex() == 1
        self.port.setEnabled(is_tcp)

    # -- authorization --
    def _check(self):
        """Check.

        Manages check operations and coordinates related state changes for the component.
        """
        host = self.target.text().strip()
        if not host:
            self.auth_label.setText("Enter a target first.")
            return
        self.check_btn.setEnabled(False)
        self.auth_label.setText("Checking authorization\u2026")
        self.win.run_worker(AuthorizeWorker(host, self._token), self._on_auth, self._auth_fail)

    def _on_auth(self, auth: dict):
        """Handle worker results: update cards/labels, re-enable buttons and clear the busy state.

        Manages on auth operations and coordinates related state changes for the component.

        Args:
            auth (dict): The auth parameter.
        """
        self.check_btn.setEnabled(True)
        self._auth = auth if auth.get("authorized") else None
        if auth.get("authorized"):
            self.auth_label.setText(
                f"Authorized \u2014 {auth['category']} ({auth['resolved_ip']}). {auth['reason']}")
            self.auth_label.setStyleSheet(f"color: {self.p.success}; font-weight: 600;")
            self.token_box.setVisible(False)
            self.run_btn.setEnabled(True)
        else:
            self.run_btn.setEnabled(False)
            if auth.get("category") == "denied" and "ownership" in auth.get("reason", "").lower():
                self._offer_token(auth)
            else:
                self.auth_label.setText(f"Not authorized \u2014 {auth.get('reason', '')}")
                self.auth_label.setStyleSheet(f"color: {self.p.danger}; font-weight: 600;")

    def _offer_token(self, auth: dict):
        """Offer token via the confirmation dialog; results return through worker signals.

        Manages offer token operations and coordinates related state changes for the component.

        Args:
            auth (dict): The auth parameter.
        """
        from cortex_unified.system_tools.load_tester import TargetAuthorizer
        if not self._token:
            self._token = TargetAuthorizer.new_token()
        self.auth_label.setText(
            f"'{auth['host']}' is a public host. Prove you own it to proceed.")
        self.auth_label.setStyleSheet(f"color: {self.p.warning}; font-weight: 600;")
        self.token_box.setText(
            "<b>To authorize this public target:</b><br>"
            f"1. Create a file containing exactly this token:<br><b>{self._token}</b><br>"
            "2. Host it at:  <b>http://YOUR-HOST/.well-known/cortex-loadtest-authorization</b><br>"
            "3. Click <b>Check Authorization</b> again. Cortex will fetch it to confirm "
            "you control the server.")
        self.token_box.setVisible(True)

    def _auth_fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.check_btn.setEnabled(True)
        self.auth_label.setText(f"Authorization check failed: {msg}")

    # -- run --
    def _toggle(self):
        """Toggle via the background worker; results return through worker signals.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        if self._running and self._worker is not None:
            self._worker.cancel()
            self.run_btn.setEnabled(False)
            self.live.setText("Stopping\u2026")
            return
        self._start()

    def _start(self):
        """Start.

        Manages start operations and coordinates related state changes for the component.
        """
        if not self._auth:
            self.auth_label.setText("Check authorization first.")
            return
        is_tcp = self.mode.currentIndex() == 1
        if is_tcp:
            host = self._auth["host"]
            if "://" in host:
                host = host.split("://", 1)[1].split("/", 1)[0].split(":", 1)[0]
            cfg = {"host": host, "port": self.port.value(),
                   "concurrency": self.conc.value(), "duration_s": self.dur.value()}
            mode = "tcp"
        else:
            url = self.target.text().strip()
            if "://" not in url:
                url = "http://" + url
            cfg = {"url": url, "concurrency": self.conc.value(),
                   "duration_s": self.dur.value()}
            mode = "http"
        confirm = QMessageBox.question(
            self, "Start load test",
            f"Start a {mode.upper()} load test against your authorized target "
            f"({self._auth['category']}) for {self.dur.value()}s at "
            f"{self.conc.value()} concurrent workers?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._worker = LoadTestWorker(mode, cfg, self._auth)
        self._running = True
        self.run_btn.setText("Stop")
        self.progress.setVisible(True)
        self.results.setText("Running\u2026")
        self.win.run_worker(self._worker, self._on_done, self._run_fail,
                            on_progress=self._on_progress)

    def _on_progress(self, snap: dict):
        """Handle worker results: update widgets and clear the busy state.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            snap (dict): The snap parameter.
        """
        self.live.setText(
            f"{snap['elapsed_s']}s \u2014 {snap['requests']} requests, "
            f"{snap['rps']} req/s, {snap['errors']} errors ({snap['error_rate']}%)")

    def _on_done(self, s: dict):
        """Handle worker results: note status, re-enable buttons and clear the busy state.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            s (dict): The s parameter.
        """
        self._running = False
        self._worker = None
        self.run_btn.setText("Start Test")
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.live.setText("")
        status = ", ".join(f"{k}:{v}" for k, v in sorted(s.get("status_counts", {}).items()))
        errs = ", ".join(f"{k}:{v}" for k, v in sorted(s.get("error_counts", {}).items())) or "none"
        verdict = self._verdict(s)
        self.results.setText(
            f"<b>Result for {s['target']}</b><br>"
            f"Throughput: <b>{s['rps']} req/s</b> over {s['duration_s']}s "
            f"({s['total']} requests, {s['succeeded']} ok, {s['failed']} failed)<br>"
            f"Error rate: <b>{s['error_rate']}%</b><br>"
            f"Latency: p50 {s['p50_ms']} ms, p95 <b>{s['p95_ms']} ms</b>, "
            f"p99 {s['p99_ms']} ms (min {s['min_ms']}, max {s['max_ms']}, avg {s['avg_ms']})<br>"
            f"Status codes: {status or 'n/a'}<br>"
            f"Errors: {errs}<br><br>{verdict}")
        self.win.statusBar().showMessage(
            f"Load test done: {s['rps']} req/s, {s['error_rate']}% errors", 6000)

    @staticmethod
    def _verdict(s: dict) -> str:
        """Verdict.

        Manages verdict operations and coordinates related state changes for the component.

        Args:
            s (dict): The s parameter.

        Returns:
            str: Formatted string or path.
        """
        er = s.get("error_rate", 0)
        p95 = s.get("p95_ms", 0)
        if er == 0 and p95 < 300:
            return ("<span><b>Healthy</b> &middot; no errors and low latency at this load. "
                    "Try raising concurrency to find the breaking point.</span>")
        if er < 5:
            return ("<span><b>Approaching limits</b> &middot; latency is climbing. This is near "
                    "your comfortable capacity.</span>")
        return ("<span><b>Breaking point</b> &middot; high error rate under this load. This is "
                "where your service degrades - a good place to harden (rate limits, "
                "autoscaling, caching, connection limits).</span>")

    def _run_fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self._running = False
        self._worker = None
        self.run_btn.setText("Start Test")
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.live.setText("")
        self.results.setText(f"Test failed: {msg}")
