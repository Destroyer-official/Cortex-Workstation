"""Tool pages: Performance (power plans), Browser Extensions, Driver inventory.

All three are low-risk: power-plan switching is fully reversible; the extension
audit and driver inventory are strictly read-only. Anything that changes system
state (only the power plan here) goes through a confirmation dialog.
"""

from __future__ import annotations

import platform

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
from .widgets import title_block
from .window import _Page

IS_WINDOWS = platform.system() == "Windows"


def _windows_only(page: _Page, feature: str) -> bool:
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

class PowerPlanListWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.performance_tuner import PerformanceTuner
            self.finished.emit([p.to_dict() for p in PerformanceTuner().list_plans()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class PowerPlanSetWorker(QObject):
    finished = Signal(bool, str)
    failed = Signal(str)

    def __init__(self, guid: str):
        super().__init__()
        self._guid = guid

    def run(self):
        try:
            from cortex_unified.system_tools.performance_tuner import PerformanceTuner
            ok, msg = PerformanceTuner().set_active(self._guid)
            self.finished.emit(ok, msg)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ExtensionAuditWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.browser_extensions import BrowserExtensionAuditor
            self.finished.emit([e.to_dict() for e in BrowserExtensionAuditor().audit()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DriverListWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.driver_inventory import DriverInventory
            self.finished.emit([d.to_dict() for d in DriverInventory().list_drivers()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# =====================================================================
#  Performance (power plans)  (feature C)
# =====================================================================

class PerformancePage(_Page):
    """Switch Windows power plans - reversible, low-risk performance control."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Performance",
            "Switch your Windows power plan: High performance for demanding work "
            "or gaming, Balanced for everyday use, Power saver on battery. Fully "
            "reversible - it changes a setting, never deletes anything.",
        ))
        if _windows_only(self, "Power-plan tuning"):
            return

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Detect Plans")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.apply_btn = QPushButton("Activate Selected")
        self.apply_btn.setObjectName("Primary")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply)
        row.addWidget(self.apply_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tbl = QTableWidget(0, 2)
        self.tbl.setHorizontalHeaderLabels(["Power plan", "Active"])
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
            lambda: self.apply_btn.setEnabled(bool(self.tbl.selectedIndexes())))
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._autoload = self._load
        self._loaded = False

    def _load(self):
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Detecting power plans\u2026")
        self.win.run_worker(PowerPlanListWorker(), self._on_listed, self._fail)

    def _on_listed(self, plans: list):
        if not plans:
            self.state.show_empty("No power plans found.")
        else:
            self.state.clear()
        self.refresh_btn.setEnabled(True)
        self.tbl.setRowCount(len(plans))
        for r, p in enumerate(plans):
            item = QTableWidgetItem(p["name"])
            item.setData(Qt.ItemDataRole.UserRole, p["guid"])
            self.tbl.setItem(r, 0, item)
            self.tbl.setItem(r, 1, QTableWidgetItem("\u2713 active" if p["active"] else ""))
        self.win.statusBar().showMessage(f"{len(plans)} power plan(s)", 5000)

    def _apply(self):
        sel = self.tbl.selectedIndexes()
        if not sel:
            return
        r = sel[0].row()
        name = self.tbl.item(r, 0).text()
        guid = self.tbl.item(r, 0).data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(
            self, "Activate power plan",
            f"Switch the active power plan to '{name}'?\n\n"
            "This is reversible - you can switch back anytime.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.apply_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.run_worker(PowerPlanSetWorker(guid), self._on_applied, self._fail)

    def _on_applied(self, ok: bool, msg: str):
        self.progress.setVisible(False)
        if ok:
            self.win.statusBar().showMessage(msg, 5000)
        else:
            QMessageBox.warning(self, "Power plan", msg)
        self._load()

    def _fail(self, msg: str):
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Browser Extensions  (feature E - read-only audit)
# =====================================================================

class BrowserExtensionsPage(_Page):
    """Read-only inventory of installed browser extensions and permissions."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Browser Extensions",
            "Review extensions installed in Chrome, Edge, Brave, Vivaldi and "
            "Firefox, and which request broad permissions. Read-only - manage or "
            "remove them from within your browser.",
        ))

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Scan Extensions")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Extension", "Browser", "Version", "Permissions"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
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
        self.state.show_loading("Scanning extensions\u2026")
        self.win.run_worker(ExtensionAuditWorker(), self._on_done, self._fail)

    def _on_done(self, exts: list):
        if not exts:
            self.state.show_empty("No extensions found (no supported browser profiles detected).")
        else:
            self.state.clear()
        self.refresh_btn.setEnabled(True)
        self.tbl.setRowCount(len(exts))
        broad = 0
        for r, e in enumerate(exts):
            name_item = QTableWidgetItem(e["name"] or "Unknown extension")
            if e["broad_permissions"]:
                broad += 1
                # Non-color signalling (Req 10.5): the red foreground alone must
                # not be the only cue - prefix a warning glyph and set a text
                # tooltip so the "broad permissions" state is conveyed by label
                # too, not colour alone.
                name_item.setText(f"\u26A0 {e['name'] or 'Unknown extension'}")
                name_item.setToolTip("Requests broad permissions - review this extension")
                name_item.setForeground(Qt.GlobalColor.red)
            self.tbl.setItem(r, 0, name_item)
            self.tbl.setItem(r, 1, QTableWidgetItem(e["browser"]))
            self.tbl.setItem(r, 2, QTableWidgetItem(e["version"]))
            perms = ", ".join(e["permissions"][:6]) + ("\u2026" if len(e["permissions"]) > 6 else "")
            self.tbl.setItem(r, 3, QTableWidgetItem(perms))
        if not exts:
            self.hint.setText("No extensions found (no supported browser profiles detected).")
        else:
            self.hint.setText(
                f"{len(exts)} extension(s); {broad} request broad permissions "
                "(marked \u26A0 and shown in red). "
                "Broad permissions aren't necessarily bad, but review ones you don't recognize.")
        self.win.statusBar().showMessage(f"{len(exts)} extension(s)", 5000)

    def _fail(self, msg: str):
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Driver Inventory  (feature F - read-only, no auto-update)
# =====================================================================

class DriverInventoryPage(_Page):
    """Read-only device-driver inventory (Cortex never auto-installs drivers)."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Driver Inventory",
            "An honest, read-only list of your installed drivers with versions "
            "and dates. Cortex does NOT download or install drivers - automatic "
            "driver updaters are a common source of scareware. Check versions "
            "against your manufacturer's site.",
        ))
        if _windows_only(self, "Driver inventory"):
            return

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("List Drivers")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["Device", "Class", "Provider", "Version", "Date"])
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

        self._autoload = self._load
        self._loaded = False

    def _load(self):
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Enumerating drivers\u2026")
        self.win.statusBar().showMessage("Enumerating drivers\u2026")
        self.win.run_worker(DriverListWorker(), self._on_done, self._fail)

    def _on_done(self, drivers: list):
        if not drivers:
            self.state.show_empty("No drivers found.")
        else:
            self.state.clear()
        self.refresh_btn.setEnabled(True)
        self.tbl.setRowCount(len(drivers))
        for r, d in enumerate(drivers):
            self.tbl.setItem(r, 0, QTableWidgetItem(d["device_name"]))
            self.tbl.setItem(r, 1, QTableWidgetItem(d["device_class"]))
            self.tbl.setItem(r, 2, QTableWidgetItem(d["provider"]))
            self.tbl.setItem(r, 3, QTableWidgetItem(d["version"]))
            self.tbl.setItem(r, 4, QTableWidgetItem(d["date"]))
        self.win.statusBar().showMessage(f"{len(drivers)} driver(s)", 5000)

    def _fail(self, msg: str):
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)
