"""Network suite pages: live Traffic Monitor and Firewall control.

* TrafficMonitorPage - real-time up/download throughput graph + per-interface
  breakdown, sampled cheaply on a timer (psutil counters, no admin needed).
* FirewallPage - block or allow a program / remote IP via Windows Firewall,
  and manage the rules Cortex created. System-modifying actions are confirmed
  and run on worker threads; listing is read-only.
"""

from __future__ import annotations

import platform
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen

from .states import StatePanel
from .widgets import Card, StatCard, TrafficGraph, title_block
from .window import _Page, fmt_bytes

IS_WINDOWS = platform.system() == "Windows"


def _fmt_rate(bps: float) -> str:
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
    """Live network throughput graph + per-interface breakdown."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Traffic Monitor",
            "Live upload/download throughput for your machine and each network "
            "adapter. Sampled locally and cheaply - no data leaves your PC.",
        ))

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.card_down = StatCard(self.p, "\u2193 Download", "\u2014")
        self.card_up = StatCard(self.p, "\u2191 Upload", "\u2014")
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
            ["Interface", "\u2193 Down", "\u2191 Up", "Total recv", "Total sent"])
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
        from cortex_unified.system_tools.network_traffic import TrafficMonitor
        self._mon = TrafficMonitor.instance()
        self._mon.sample()   # prime so the first visible rate is real
        self._timer.start()
        self._tick()

    def _tick(self):
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
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, cortex_only: bool = True):
        super().__init__()
        self._cortex_only = cortex_only

    def run(self):
        try:
            from cortex_unified.system_tools.firewall_manager import FirewallManager
            rules = FirewallManager().list_rules(cortex_only=self._cortex_only)
            self.finished.emit([r.to_dict() for r in rules])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class FirewallActionWorker(QObject):
    finished = Signal(bool, str)
    failed = Signal(str)

    def __init__(self, action: str, **kwargs):
        super().__init__()
        self._action = action
        self._kw = kwargs

    def run(self):
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
    """Block/allow programs and IPs via Windows Firewall (Cortex-scoped)."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Firewall",
            "Block or allow a program's or address's traffic using Windows "
            "Firewall. Fully reversible - Cortex only manages rules it creates "
            "and never touches your existing Windows rules. Needs Administrator.",
        ))
        if not IS_WINDOWS:
            note = QLabel("\u2139  Firewall control is only available on Windows.")
            note.setObjectName("Muted")
            note.setWordWrap(True)
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
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a program", str(Path.home()), "Programs (*.exe);;All files (*.*)")
        if path:
            self.prog_edit.setText(path)

    def _busy(self, on: bool):
        self.progress.setVisible(on)
        self.refresh_btn.setEnabled(not on)

    def _create(self, action: str):
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
        self._busy(False)
        if ok:
            self.win.statusBar().showMessage(msg, 5000)
        else:
            QMessageBox.warning(self, "Firewall", msg)
        self._load()

    def _load(self):
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Loading firewall rules…")
        self.win.run_worker(FirewallListWorker(True), self._on_listed, self._fail)

    def _on_listed(self, rules: list):
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
        has = bool(self.tbl.selectedIndexes())
        self.toggle_btn.setEnabled(has)
        self.remove_btn.setEnabled(has)

    def _selected(self) -> tuple[str, bool] | None:
        sel = self.tbl.selectedIndexes()
        if not sel:
            return None
        r = sel[0].row()
        name = self.tbl.item(r, 0).data(Qt.ItemDataRole.UserRole)
        enabled = self.tbl.item(r, 4).text() == "Yes"
        return name, enabled

    def _toggle(self):
        sel = self._selected()
        if not sel:
            return
        name, enabled = sel
        self._busy(True)
        self.win.run_worker(
            FirewallActionWorker("toggle", name=name, enabled=not enabled),
            self._on_action, self._fail)

    def _remove(self):
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
        self._busy(False)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Network Map
# =====================================================================

from PySide6.QtWidgets import QWidget  # noqa: E402


class _MapCanvas(QWidget):
    """Draws an offline connection graph: This PC -> apps -> remote endpoints."""

    def __init__(self, palette, parent=None):
        super().__init__(parent)
        self._p = palette
        self._edges: list[tuple[str, str, bool]] = []  # (process, remote, external)
        self.setMinimumHeight(360)

    def set_edges(self, edges: list[tuple[str, str, bool]]):
        # Keep the view readable: cap processes and remotes.
        self._edges = edges[:120]
        self.update()

    def paintEvent(self, event):  # noqa: N802
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
        path = QPainterPath()
        path.moveTo(x1, y1)
        mx = (x1 + x2) / 2
        path.cubicTo(mx, y1, mx, y2, x2, y2)
        pen = QPen(color, 1.4)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    def _node(self, painter, cx, cy, label, color: QColor, big=False, small=False):
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
    """Visual, offline map of which apps connect to which remote hosts."""

    def __init__(self, win):
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
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Building network map…")
        from .system_pages import NetworkWorker
        self.win.run_worker(NetworkWorker(), self._on_loaded, self._fail)

    def _on_loaded(self, conns: list, summary: dict):
        self.state.clear()
        self.refresh_btn.setEnabled(True)
        self._conns = conns
        self._render()

    def _render(self):
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
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  LAN Device Scanner
# =====================================================================

class LanScanWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.lan_scanner import LanScanner
            self.finished.emit([d.to_dict() for d in LanScanner().scan()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class LanDevicesPage(_Page):
    """Devices seen on your local network (from the OS ARP cache)."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Network Devices",
            "Devices your PC has recently communicated with on the local network, "
            "with their IP, hardware (MAC) address and a best-effort vendor. "
            "Read-only and offline - handy for spotting an unfamiliar device.",
        ))

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Scan Devices")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.count = QLabel("")
        self.count.setObjectName("Muted")
        row.addWidget(self.count)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["IP address", "MAC address", "Vendor", "Type"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        note = QLabel("This reads the ARP cache (devices seen recently); it doesn't "
                      "actively probe the network. A device may appear only after "
                      "your PC has talked to it.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        self.v.addWidget(note)

        self._autoload = self._load
        self._loaded = False

    def _load(self):
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Scanning devices…")
        self.win.run_worker(LanScanWorker(), self._on_loaded, self._fail)

    def _on_loaded(self, devices: list):
        self.refresh_btn.setEnabled(True)
        if not devices:
            self.state.show_empty(
                "No devices seen yet. Your PC may not have talked to any "
                "local device recently.")
        else:
            self.state.clear()
        self.tbl.setRowCount(len(devices))
        for r, d in enumerate(devices):
            self.tbl.setItem(r, 0, QTableWidgetItem(d["ip"]))
            self.tbl.setItem(r, 1, QTableWidgetItem(d["mac"]))
            self.tbl.setItem(r, 2, QTableWidgetItem(d["vendor"] or "\u2014"))
            self.tbl.setItem(r, 3, QTableWidgetItem(d["kind"]))
        self.count.setText(f"{len(devices)} device(s)")
        self.win.statusBar().showMessage(f"{len(devices)} device(s) on your network", 5000)

    def _fail(self, msg: str):
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Network Tools (ping / traceroute / DNS / ports / IP info)
# =====================================================================

class _ToolWorker(QObject):
    """Runs one network-tool call off the UI thread."""

    finished = Signal(str, object)   # (tool, result)
    failed = Signal(str)

    def __init__(self, tool: str, target: str):
        super().__init__()
        self._tool = tool
        self._target = target

    def run(self):
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


class NetworkToolsPage(_Page):
    """Classic diagnostics: ping, traceroute, DNS, port check, IP info."""

    def __init__(self, win):
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
        self.progress.setVisible(False)
        self.summary.setText(f"Error: {msg}")


# =====================================================================
#  Load / Resilience Tester  (authorized, own-infrastructure only)
# =====================================================================

from PySide6.QtWidgets import QSpinBox  # noqa: E402


class AuthorizeWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, host: str, token: str = ""):
        super().__init__()
        self._host = host
        self._token = token

    def run(self):
        try:
            from cortex_unified.system_tools.load_tester import TargetAuthorizer
            auth = TargetAuthorizer().authorize(self._host, self._token or None)
            self.finished.emit(auth.to_dict())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class LoadTestWorker(QObject):
    progress = Signal(dict)
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, mode: str, cfg: dict, auth_dict: dict):
        super().__init__()
        self._mode = mode
        self._cfg = cfg
        self._auth_dict = auth_dict
        import threading as _t
        self._cancel = _t.Event()

    def cancel(self):
        self._cancel.set()

    def run(self):
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
    """Measure how much load YOUR OWN service can take before it degrades."""

    def __init__(self, win):
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
        is_tcp = self.mode.currentIndex() == 1
        self.port.setEnabled(is_tcp)

    # -- authorization --
    def _check(self):
        host = self.target.text().strip()
        if not host:
            self.auth_label.setText("Enter a target first.")
            return
        self.check_btn.setEnabled(False)
        self.auth_label.setText("Checking authorization\u2026")
        self.win.run_worker(AuthorizeWorker(host, self._token), self._on_auth, self._auth_fail)

    def _on_auth(self, auth: dict):
        self.check_btn.setEnabled(True)
        self._auth = auth if auth.get("authorized") else None
        if auth.get("authorized"):
            self.auth_label.setText(
                f"\u2705 Authorized \u2014 {auth['category']} ({auth['resolved_ip']}). {auth['reason']}")
            self.auth_label.setStyleSheet(f"color: {self.p.success}; font-weight: 600;")
            self.token_box.setVisible(False)
            self.run_btn.setEnabled(True)
        else:
            self.run_btn.setEnabled(False)
            if auth.get("category") == "denied" and "ownership" in auth.get("reason", "").lower():
                self._offer_token(auth)
            else:
                self.auth_label.setText(f"\u26D4 Not authorized \u2014 {auth.get('reason', '')}")
                self.auth_label.setStyleSheet(f"color: {self.p.danger}; font-weight: 600;")

    def _offer_token(self, auth: dict):
        from cortex_unified.system_tools.load_tester import TargetAuthorizer
        if not self._token:
            self._token = TargetAuthorizer.new_token()
        self.auth_label.setText(
            f"\u26D4 '{auth['host']}' is a public host. Prove you own it to proceed.")
        self.auth_label.setStyleSheet(f"color: {self.p.warning}; font-weight: 600;")
        self.token_box.setText(
            "<b>To authorize this public target:</b><br>"
            f"1. Create a file containing exactly this token:<br><b>{self._token}</b><br>"
            "2. Host it at:  <b>http://YOUR-HOST/.well-known/cortex-loadtest-authorization</b><br>"
            "3. Click <b>Check Authorization</b> again. Cortex will fetch it to confirm "
            "you control the server.")
        self.token_box.setVisible(True)

    def _auth_fail(self, msg: str):
        self.check_btn.setEnabled(True)
        self.auth_label.setText(f"Authorization check failed: {msg}")

    # -- run --
    def _toggle(self):
        if self._running and self._worker is not None:
            self._worker.cancel()
            self.run_btn.setEnabled(False)
            self.live.setText("Stopping\u2026")
            return
        self._start()

    def _start(self):
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
        self.live.setText(
            f"{snap['elapsed_s']}s \u2014 {snap['requests']} requests, "
            f"{snap['rps']} req/s, {snap['errors']} errors ({snap['error_rate']}%)")

    def _on_done(self, s: dict):
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
        er = s.get("error_rate", 0)
        p95 = s.get("p95_ms", 0)
        if er == 0 and p95 < 300:
            return ("<span>\u2705 Healthy: no errors and low latency at this load. "
                    "Try raising concurrency to find the breaking point.</span>")
        if er < 5:
            return ("<span>\u26A0 Approaching limits: latency is climbing. This is near "
                    "your comfortable capacity.</span>")
        return ("<span>\u26D4 Breaking point: high error rate under this load. This is "
                "where your service degrades - a good place to harden (rate limits, "
                "autoscaling, caching, connection limits).</span>")

    def _run_fail(self, msg: str):
        self._running = False
        self._worker = None
        self.run_btn.setText("Start Test")
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.live.setText("")
        self.results.setText(f"Test failed: {msg}")
