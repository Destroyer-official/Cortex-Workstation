"""Tool pages: Performance (power plans), Browser Extensions, Driver inventory.

All three are low-risk: power-plan switching is fully reversible; the extension
audit and driver inventory are strictly read-only. Anything that changes system
state (only the power plan here) goes through a confirmation dialog.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableView,
)

from . import icons
from .states import StatePanel
from .tablemodel import Column, bind_table
from .widgets import status_note, title_block
from .window import _Page

# ``sys.platform`` is an interned constant; ``platform.system()`` costs ~50 ms
# on its first call because it populates ``uname()`` via WMI on Windows.
IS_WINDOWS = sys.platform == "win32"


def _windows_only(page: _Page, feature: str) -> bool:
    """_windows_only.

    Manages windows only operations and coordinates related state changes for the component.

    Args:
        page (_Page): The page parameter.
        feature (str): The feature parameter.

    Returns:
        bool: True if the operation succeeded, False otherwise.
    """
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

class PowerPlanListWorker(QObject):
    """Powerplanlistworker.

    Manages PowerPlanListWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        """run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.performance_tuner import PerformanceTuner
            self.finished.emit([p.to_dict() for p in PerformanceTuner().list_plans()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class PowerPlanSetWorker(QObject):
    """Powerplansetworker.

    Manages PowerPlanSetWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(bool, str)
    failed = Signal(str)

    def __init__(self, guid: str):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            guid (str): The guid parameter.
        """
        super().__init__()
        self._guid = guid

    def run(self):
        """run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.performance_tuner import PerformanceTuner
            ok, msg = PerformanceTuner().set_active(self._guid)
            self.finished.emit(ok, msg)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ExtensionAuditWorker(QObject):
    """Extensionauditworker.

    Manages ExtensionAuditWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        """run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.browser_extensions import BrowserExtensionAuditor
            self.finished.emit([e.to_dict() for e in BrowserExtensionAuditor().audit()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


def _permissions_display(ext: dict) -> str:
    """The permission list, trimmed to six entries with an ellipsis.

    Some extensions request dozens of permissions; the full list would push the
    other columns off screen. The browser itself is the place to read all of
    them, so the cell shows enough to recognise the scope and stops.
    """
    perms = ext["permissions"]
    return ", ".join(perms[:6]) + ("\u2026" if len(perms) > 6 else "")


def _version_sort_key(driver: dict) -> str:
    """Driver versions as a zero-padded string, so 10.0.1 sorts above 9.9.9.

    Compared as displayed text, "10.0.19041.1" lands below "9.0.0" - the same
    class of bug as "9 MB" sorting above "10 MB". Each numeric part is padded to
    a fixed width so plain text comparison gives numeric order.

    Why a string and not a tuple of ints: the proxy sorts on values handed back
    through a Qt data role, and Qt cannot order an opaque Python tuple - it
    leaves the rows where they were, which looks exactly like "sorting does
    nothing". A padded string is a type Qt compares natively. Non-numeric parts
    become 0 rather than raising: vendors ship versions like "1.0.0-beta", and
    one odd string must not take the whole sort down with it.
    """
    parts = []
    for chunk in str(driver.get("version") or "").split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(f"{int(digits) if digits else 0:08d}")
    return ".".join(parts)


def _date_sort_key(driver: dict) -> str:
    """Driver dates as the raw ISO string the inventory already produces.

    ``DriverInventory`` normalises WMI dates to ``YYYY-MM-DD``, which compares
    correctly as text; the explicit key exists so an undated driver becomes a
    predictable empty string instead of depending on the display cell.
    """
    return str(driver.get("date") or "")


class DriverListWorker(QObject):
    """Driverlistworker.

    Manages DriverListWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        """run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.driver_inventory import DriverInventory
            self.finished.emit([d.to_dict() for d in DriverInventory().list_drivers()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# =====================================================================
#  Performance (power plans)  (feature C)
# =====================================================================

class PerformancePage(_Page):
    """Performancepage.

    Manages PerformancePage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
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

        # Model/view rather than QTableWidget. Only three rows here, but the
        # item-based table carries the same shape of cost everywhere - one
        # QTableWidgetItem per cell for every row, visible or not - and keeping
        # every table on one foundation means selection, sorting and filtering
        # behave identically across the app instead of per page.
        self.tbl = QTableView()
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        # bind_table applies the shared presentation defaults (row selection,
        # single selection, read-only, alternating rows, hidden vertical header)
        # and the per-column stretch declared below.
        self.table = bind_table(
            self.tbl,
            [
                Column("Power plan", "name", stretch=True),
                # Non-colour signalling (Req 10.5): the active plan gets a check
                # glyph *and* the word "active", so the state never depends on a
                # single visual cue. sort_key is the raw bool, so sorting groups
                # by state rather than comparing the strings "active" and "".
                Column(
                    "Active",
                    lambda plan: "active" if plan["active"] else "",
                    sort_key=lambda plan: bool(plan["active"]),
                    icon=lambda plan: (icons.icon("check", 14, self.p.success)
                                       if plan["active"] else None),
                ),
            ],
            # Active plan first on arrival - it is the answer to "what am I on?".
            sort_column=1,
            sort_order=Qt.SortOrder.DescendingOrder,
        )
        # A QTableView has no itemSelectionChanged; the selection model is the
        # equivalent and also fires for keyboard navigation.
        self.tbl.selectionModel().selectionChanged.connect(
            lambda *_: self.apply_btn.setEnabled(
                self.tbl.selectionModel().hasSelection()))
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._autoload = self._load
        self._loaded = False

    def _load(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Detecting power plans\u2026")
        self.win.run_worker(PowerPlanListWorker(), self._on_listed, self._fail)

    def _on_listed(self, plans: list):
        """_on_listed.

        Manages on listed operations and coordinates related state changes for the component.

        Args:
            plans (list): The plans parameter.
        """
        if not plans:
            self.state.show_empty("No power plans found.")
        else:
            self.state.clear()
        self.refresh_btn.setEnabled(True)
        # One model reset replaces the per-cell fill loop; the plan dicts stay in
        # the model, so the GUID no longer has to ride along in a UserRole.
        self.table.set_records(plans)
        # The reset drops the selection, so the action button must follow it.
        self.apply_btn.setEnabled(self.tbl.selectionModel().hasSelection())
        self.win.statusBar().showMessage(f"{len(plans)} power plan(s)", 5000)

    def _apply(self):
        """Apply.

        Manages apply operations and coordinates related state changes for the component.
        """
        # Resolved through the binding, not by indexing a list with the view's
        # row number - that pattern quietly activates the wrong plan as soon as
        # the table is sorted.
        plan = self.table.selected_record()
        if not plan:
            return
        name = plan["name"]
        guid = plan["guid"]
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
        """_on_applied.

        Manages on applied operations and coordinates related state changes for the component.

        Args:
            ok (bool): The ok parameter.
            msg (str): Informational or progress status message.
        """
        self.progress.setVisible(False)
        if ok:
            self.win.statusBar().showMessage(msg, 5000)
        else:
            QMessageBox.warning(self, "Power plan", msg)
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
#  Browser Extensions  (feature E - read-only audit)
# =====================================================================

class BrowserExtensionsPage(_Page):
    """Browserextensionspage.

    Manages BrowserExtensionsPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
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

        # Model/view rather than QTableWidget, like every other table in the app:
        # the view queries the model only for the rows it paints, and one shared
        # foundation keeps selection, sorting and filtering identical per page.
        # The risk cue survives the migration - Column.foreground paints a
        # broad-permission extension red, paired with a warning icon and a
        # tooltip so colour is never the only signal (Req 10.5).
        self.tbl = QTableView()
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        # bind_table applies the shared presentation defaults (row selection,
        # single selection, read-only, alternating rows, hidden vertical header);
        # Extension and Permissions carry stretch=True, which is what the two
        # Stretch header sections used to do.
        self.table = bind_table(
            self.tbl,
            [
                Column(
                    "Extension",
                    lambda e: e["name"] or "Unknown extension",
                    stretch=True,
                    foreground=lambda e: (Qt.GlobalColor.red
                                          if e["broad_permissions"] else None),
                    icon=lambda e: (icons.icon("warning", 14, self.p.warning)
                                    if e["broad_permissions"] else None),
                    tooltip=lambda e: ("Requests broad permissions - review this extension"
                                       if e["broad_permissions"] else ""),
                ),
                Column("Browser", "browser"),
                Column("Version", "version"),
                Column("Permissions", _permissions_display, stretch=True),
            ],
        )
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
        self.state.show_loading("Scanning extensions\u2026")
        self.win.run_worker(ExtensionAuditWorker(), self._on_done, self._fail)

    def _on_done(self, exts: list):
        """_on_done.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            exts (list): The exts parameter.
        """
        if not exts:
            self.state.show_empty("No extensions found (no supported browser profiles detected).")
        else:
            self.state.clear()
        self.refresh_btn.setEnabled(True)
        # One model reset replaces the per-cell fill loop; the extension dicts
        # live in the model, so every column - including the red foreground, the
        # warning icon and the tooltip - reads straight off the record.
        self.table.set_records(exts)
        broad = sum(1 for e in exts if e["broad_permissions"])
        if not exts:
            self.hint.setText("No extensions found (no supported browser profiles detected).")
        else:
            self.hint.setText(
                f"{len(exts)} extension(s); {broad} request broad permissions "
                "(flagged with a warning icon and shown in red). "
                "Broad permissions aren't necessarily bad, but review ones you don't recognize.")
        self.win.statusBar().showMessage(f"{len(exts)} extension(s)", 5000)

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Driver Inventory  (feature F - read-only, no auto-update)
# =====================================================================

class DriverInventoryPage(_Page):
    """Driverinventorypage.

    Manages DriverInventoryPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
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

        # Model/view rather than QTableWidget - the biggest table in this file.
        # A typical machine reports 200-400 signed drivers, and the item-based
        # table allocated one QTableWidgetItem per cell for every one of them
        # (5 columns, so ~1,000-2,000 objects) in a single synchronous loop,
        # whether or not the row was ever scrolled into view. A QTableView asks
        # the model only for the rows it is painting, so the cost tracks the
        # viewport instead of the driver count.
        self.tbl = QTableView()
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.table = bind_table(
            self.tbl,
            [
                Column("Device", "device_name", stretch=True),
                Column("Class", "device_class"),
                Column("Provider", "provider"),
                # Typed sort keys, because both of these columns display
                # formatted text: sorting the strings puts driver 9.x above 10.x
                # and files an undated driver wherever "" happens to land.
                Column("Version", "version", sort_key=_version_sort_key),
                Column("Date", "date", sort_key=_date_sort_key),
            ],
            # Newest driver first - the reason to open this page is usually
            # "what did Windows install lately?".
            sort_column=4,
            sort_order=Qt.SortOrder.DescendingOrder,
        )
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._autoload = self._load
        self._loaded = False

    def _load(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Enumerating drivers\u2026")
        self.win.statusBar().showMessage("Enumerating drivers\u2026")
        self.win.run_worker(DriverListWorker(), self._on_done, self._fail)

    def _on_done(self, drivers: list):
        """_on_done.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            drivers (list): List of detected driver records or driver instance.
        """
        if not drivers:
            self.state.show_empty("No drivers found.")
        else:
            self.state.clear()
        self.refresh_btn.setEnabled(True)
        # One model reset instead of ~2,000 item allocations, so a 400-driver
        # machine costs the same to display as a 40-driver one.
        self.table.set_records(drivers)
        self.win.statusBar().showMessage(f"{len(drivers)} driver(s)", 5000)

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)
