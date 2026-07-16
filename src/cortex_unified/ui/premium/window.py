"""The premium main window: sidebar navigation + engine-backed pages."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QThread
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import motion
from .theme import THEMES, Palette, apply_theme
from .widgets import Badge, Card, CircularGauge, StatCard, hline, title_block

_LOG = logging.getLogger("cortex.ui.premium")


def fmt_bytes(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if size < 1024 or unit == "PB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


# Navigation definition: (page_id, label, icon-glyph)
_NAV = [
    ("dashboard", "Dashboard", "\u25C9"),
    ("health", "Health Check", "\u2764"),
    ("duplicates", "Duplicates", "\u29C9"),
    ("photos", "Duplicate Photos", "\u25A3"),
    ("dupfolders", "Duplicate Folders", "\u25A3"),
    ("large", "Large Files", "\u25B0"),
    ("empty", "Empty Items", "\u25CB"),
    ("analyzer", "Disk Analyzer", "\u25F0"),
    ("brokenlinks", "Broken Links", "\u26D3"),
    ("packages", "Package Caches", "\u25A9"),
    ("updater", "Software Updater", "\u21BB"),
    ("drives", "Drive Optimizer", "\u25A4"),
    ("diskhealth", "Disk Health", "\u2665"),
    ("bootperf", "Boot Performance", "\u23F1"),
    ("winupdate", "Windows Update", "\u2B73"),
    ("repair", "System File Health", "\u2695"),
    ("schedule", "Scheduled Tasks", "\u23F0"),
    ("performance", "Performance", "\u26A1"),
    ("privacy", "Privacy", "\u26E8"),
    ("startup", "Startup", "\u25B6"),
    ("processes", "Processes", "\u2637"),
    ("network", "Network Monitor", "\u21C4"),
    ("traffic", "Traffic Monitor", "\u2248"),
    ("netmap", "Network Map", "\u26B8"),
    ("landevices", "Network Devices", "\u2637"),
    ("nettools", "Network Tools", "\u2692"),
    ("loadtest", "Load Tester", "\u25F4"),
    ("firewall", "Firewall", "\u26E8"),
    ("extensions", "Browser Extensions", "\u2b50"),
    ("drivers", "Driver Inventory", "\u2699"),
    ("uninstaller", "Uninstaller", "\u2718"),
    ("telemetry", "Telemetry", "\u25C8"),
    ("registry", "Registry", "\u25A6"),
    ("security", "Security", "\u26E8"),
    ("storagesense", "Storage Sense", "\u267B"),
    ("secrets", "Secrets Scanner", "\u26BF"),
    ("shred", "Secure Shred", "\u2726"),
    ("backups", "Backups & Restore", "\u21A9"),
    ("report", "Health Report", "\u25A4"),
    ("sysinfo", "System Info", "\u2139"),
    ("settings", "Settings", "\u2699"),
]


class _TitleBar(QWidget):
    """Custom window chrome: brand + native window controls (frameless shell).

    Dragging uses the platform's own ``startSystemMove`` so Windows aero-snap
    (drag-to-top maximize, drag-to-side half-snap) keeps working. Double-click
    toggles maximize.
    """

    def __init__(self, win: "PremiumMainWindow"):
        super().__init__(win)
        self._win = win
        self.setObjectName("TitleBar")
        self.setFixedHeight(42)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 8, 0)
        lay.setSpacing(9)

        glyph = QLabel("\u26E8")
        glyph.setObjectName("TitleGlyph")
        title = QLabel("Cortex Cleaner")
        title.setObjectName("TitleText")
        lay.addWidget(glyph)
        lay.addWidget(title)
        lay.addStretch(1)

        self._min = QPushButton("\uFF0D")
        self._max = QPushButton("\u2610")
        self._close = QPushButton("\u2715")
        for b in (self._min, self._max):
            b.setObjectName("WinBtn")
        self._close.setObjectName("CloseBtn")
        for b in (self._min, self._max, self._close):
            b.setFixedSize(44, 30)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            lay.addWidget(b)

        self._min.clicked.connect(win.showMinimized)
        self._max.clicked.connect(self._toggle_max)
        self._close.clicked.connect(win.close)

    def _toggle_max(self):
        if self._win.isMaximized():
            self._win.showNormal()
            self._max.setText("\u2610")
        else:
            self._win.showMaximized()
            self._max.setText("\u2750")

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._win.windowHandle()
            if handle is not None:
                handle.startSystemMove()

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_max()


class PremiumMainWindow(QMainWindow):
    """Modern shell hosting all engine-backed pages."""

    def __init__(self, theme: str = "dark"):
        super().__init__()
        self.theme_name = theme
        self.palette_tokens: Palette = THEMES[theme]
        self._threads: list[QThread] = []

        self.setWindowTitle("Cortex Cleaner")
        self.resize(1180, 760)
        self.setMinimumSize(840, 560)

        # Frameless shell with our own title bar; native drag/resize/snap are
        # preserved via startSystemMove / startSystemResize. Guarded so any
        # platform that dislikes it still yields a normal, working window.
        self._frameless = False
        try:
            self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            self._frameless = True
        except Exception:  # noqa: BLE001
            self._frameless = False
        self._resize_margin = 6
        self._edge_cursor_active = False

        # Best-effort native backdrop (Windows 11 Mica/Acrylic); degrades to an
        # opaque token background on any other platform. Never raises.
        from .backdrop import apply_backdrop
        self.backdrop_mode = apply_backdrop(self)

        # Shared, fully-offline learning engine (learns which categories you
        # keep vs. skip). Loads a tiny local model; never touches the network.
        from cortex_unified.core.smart_suggest import SmartSuggester
        self.suggester = SmartSuggester()

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._titlebar = _TitleBar(self)
        outer.addWidget(self._titlebar)

        body = QWidget()
        root = QHBoxLayout(body)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._sidebar = self._build_sidebar()
        root.addWidget(self._sidebar)

        self._stack = QStackedWidget()
        content_wrap = QWidget()
        content_wrap.setObjectName("ContentArea")
        cw = QVBoxLayout(content_wrap)
        cw.setContentsMargins(28, 24, 28, 20)
        cw.addWidget(self._stack)
        self._content_layout = cw
        root.addWidget(content_wrap, 1)

        outer.addWidget(body, 1)
        self.setCentralWidget(central)

        if self._frameless:
            QApplication.instance().installEventFilter(self)

        # Pages (import lazily to keep this module cohesive)
        self._pages: dict[str, QWidget] = {}
        # System-tool pages live in a separate module; import lazily here (after
        # this module is fully defined) to avoid a circular import.
        from .system_pages import (
            NetworkPage,
            PrivacyPage,
            ProcessesPage,
            RegistryPage,
            StartupPage,
            TelemetryPage,
            UninstallerPage,
        )
        from .more_pages import (
            BrokenLinksPage,
            DriveOptimizerPage,
            DuplicateFoldersPage,
            PackageCachePage,
            SecretsScannerPage,
            SoftwareUpdaterPage,
            SystemInfoPage,
        )
        from .analysis_pages import (
            BootPerformancePage,
            DiskAnalyzerPage,
            DiskHealthPage,
            HealthCheckPage,
            ScheduledTasksPage,
            SecurityPage,
            StorageSensePage,
            SystemRepairPage,
            WindowsUpdatePage,
        )
        from .report_pages import (
            BackupsPage,
            HealthReportPage,
        )
        from .tools_pages import (
            BrowserExtensionsPage,
            DriverInventoryPage,
            PerformancePage,
        )
        from .network_pages import (
            FirewallPage,
            LanDevicesPage,
            LoadTesterPage,
            NetworkMapPage,
            NetworkToolsPage,
            TrafficMonitorPage,
        )

        self._pages["dashboard"] = DashboardPage(self)
        self._pages["health"] = HealthCheckPage(self)
        self._pages["duplicates"] = DuplicatesPage(self)
        self._pages["photos"] = DuplicatePhotosPage(self)
        self._pages["dupfolders"] = DuplicateFoldersPage(self)
        self._pages["large"] = LargeFilesPage(self)
        self._pages["empty"] = EmptyPage(self)
        self._pages["analyzer"] = DiskAnalyzerPage(self)
        self._pages["brokenlinks"] = BrokenLinksPage(self)
        self._pages["packages"] = PackageCachePage(self)
        self._pages["updater"] = SoftwareUpdaterPage(self)
        self._pages["drives"] = DriveOptimizerPage(self)
        self._pages["diskhealth"] = DiskHealthPage(self)
        self._pages["bootperf"] = BootPerformancePage(self)
        self._pages["winupdate"] = WindowsUpdatePage(self)
        self._pages["repair"] = SystemRepairPage(self)
        self._pages["schedule"] = ScheduledTasksPage(self)
        self._pages["performance"] = PerformancePage(self)
        self._pages["privacy"] = PrivacyPage(self)
        self._pages["startup"] = StartupPage(self)
        self._pages["processes"] = ProcessesPage(self)
        self._pages["network"] = NetworkPage(self)
        self._pages["traffic"] = TrafficMonitorPage(self)
        self._pages["netmap"] = NetworkMapPage(self)
        self._pages["landevices"] = LanDevicesPage(self)
        self._pages["nettools"] = NetworkToolsPage(self)
        self._pages["loadtest"] = LoadTesterPage(self)
        self._pages["firewall"] = FirewallPage(self)
        self._pages["extensions"] = BrowserExtensionsPage(self)
        self._pages["drivers"] = DriverInventoryPage(self)
        self._pages["uninstaller"] = UninstallerPage(self)
        self._pages["telemetry"] = TelemetryPage(self)
        self._pages["registry"] = RegistryPage(self)
        self._pages["security"] = SecurityPage(self)
        self._pages["storagesense"] = StorageSensePage(self)
        self._pages["secrets"] = SecretsScannerPage(self)
        self._pages["shred"] = ShredPage(self)
        self._pages["backups"] = BackupsPage(self)
        self._pages["report"] = HealthReportPage(self)
        self._pages["sysinfo"] = SystemInfoPage(self)
        self._pages["settings"] = SettingsPage(self)
        for pid, _, _ in _NAV:
            self._stack.addWidget(self._pages[pid])

        self.statusBar().showMessage("Ready")
        self._select("dashboard")

    # -- sidebar ------------------------------------------------------------

    def _build_sidebar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("Sidebar")
        bar.setFixedWidth(214)
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(14, 20, 14, 16)
        lay.setSpacing(6)

        brand = QLabel("\u26E8  Cortex")
        brand.setObjectName("Brand")
        sub = QLabel("CLEANER SUITE")
        sub.setObjectName("BrandSub")
        lay.addWidget(brand)
        lay.addWidget(sub)
        lay.addSpacing(14)

        # Scrollable nav area (there are many tools; never let them clip).
        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav_holder = QWidget()
        nav_lay = QVBoxLayout(nav_holder)
        nav_lay.setContentsMargins(0, 0, 0, 0)
        nav_lay.setSpacing(4)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        for pid, label, glyph in _NAV:
            btn = QPushButton(f"  {glyph}   {label}")
            btn.setObjectName("NavItem")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, p=pid: self._select(p))
            self._nav_group.addButton(btn)
            btn._page_id = pid  # type: ignore[attr-defined]
            nav_lay.addWidget(btn)
        nav_lay.addStretch(1)
        nav_scroll.setWidget(nav_holder)
        lay.addWidget(nav_scroll, 1)

        version = QLabel("v2.1  \u2022  engine-backed")
        version.setObjectName("Muted")
        version.setStyleSheet("font-size: 11px;")
        lay.addWidget(version)
        return bar

    def _select(self, page_id: str) -> None:
        for i, (pid, _, _) in enumerate(_NAV):
            if pid == page_id:
                self._stack.setCurrentIndex(i)
        for btn in self._nav_group.buttons():
            btn.setChecked(getattr(btn, "_page_id", None) == page_id)
        self._fade_in(self._stack.currentWidget())
        # Lazy-load: a page with an ``_autoload`` callable fetches its data the
        # first time it's viewed, so the app doesn't spawn workers for every
        # page at startup.
        page = self._pages.get(page_id)
        if page is not None and getattr(page, "_autoload", None) and not getattr(page, "_loaded", False):
            page._loaded = True
            page._autoload()

    def _fade_in(self, widget: QWidget | None) -> None:
        """Subtle fade when a page becomes visible - a smooth, premium touch.

        Delegates to the shared :func:`motion.fade_in` so page appearances use
        the Motion_System's single duration/easing language. The animation is
        stored in a single ``_page_anim`` reference: starting a new transition
        replaces any in-flight one, so at most one appearance animation runs per
        page transition. The opacity effect is removed once the animation
        finishes so it never interferes with drop-shadow effects on child cards.
        """
        if widget is None:
            return
        try:
            self._page_anim = motion.fade_in(widget)  # single reference; supersedes prior
        except Exception:  # noqa: BLE001 - animation is cosmetic, never fatal
            pass

    # -- worker lifecycle ---------------------------------------------------

    def run_worker(self, worker, on_done, on_fail=None, on_progress=None) -> None:
        """Move *worker* to a fresh QThread and wire signals safely.

        Crucially, the result callbacks (``on_done``/``on_fail``/``on_progress``)
        must be bound methods of main-thread QObjects so Qt uses *queued*
        connections and they run on the GUI thread - never in the worker
        thread. Thread teardown is driven by ``QThread.finished`` (never by
        calling ``wait()`` from inside a worker-thread slot, which deadlocks).
        """
        wname = type(worker).__name__
        _LOG.debug("starting worker: %s", wname)
        thread = QThread(self)
        thread.setObjectName(wname)
        worker.moveToThread(thread)
        # CRITICAL: keep a strong Python reference to the worker. PySide6 does
        # not keep worker objects alive via signal connections alone, so an
        # inline `run_worker(SomeWorker(), ...)` call would let the worker be
        # garbage-collected before it finishes - its `finished` signal would
        # never fire and the UI would hang forever. Anchoring it to the tracked
        # thread object keeps it alive until the thread is reaped.
        thread._cortex_worker = worker  # type: ignore[attr-defined]
        self._threads.append(thread)

        thread.started.connect(worker.run)

        # Live progress (optional) -> queued to GUI thread.
        if on_progress is not None and hasattr(worker, "progress"):
            worker.progress.connect(on_progress)
        if hasattr(worker, "finished"):
            worker.finished.connect(lambda *a: _LOG.debug("worker finished: %s", wname))
        if hasattr(worker, "failed"):
            worker.failed.connect(lambda m: _LOG.error("worker failed: %s: %s", wname, m))

        # Terminal signals -> user callback (queued to GUI thread) + quit loop.
        if hasattr(worker, "finished"):
            worker.finished.connect(on_done)
            worker.finished.connect(thread.quit)
        if hasattr(worker, "failed"):
            worker.failed.connect(on_fail or self._default_fail)
            worker.failed.connect(thread.quit)
        if hasattr(worker, "refused"):
            # ShredPage connects its own handler to 'refused'; we just stop the loop.
            worker.refused.connect(thread.quit)

        # Teardown happens after the event loop has actually stopped.
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._reap_threads)
        thread.start()

    def _reap_threads(self) -> None:
        """Remove and delete any finished worker threads (runs on GUI thread)."""
        for t in list(self._threads):
            if t.isFinished():
                self._threads.remove(t)
                t.deleteLater()

    def _default_fail(self, msg: str) -> None:
        self.statusBar().showMessage(f"Error: {msg}", 6000)
        QMessageBox.warning(self, "Operation failed", msg)

    def set_theme(self, theme: str) -> None:
        from PySide6.QtWidgets import QApplication
        self.theme_name = theme
        self.palette_tokens = THEMES[theme]
        apply_theme(QApplication.instance(), theme)

    # -- frameless edge resize ---------------------------------------------

    def eventFilter(self, obj, event):  # noqa: N802
        """App-level filter that turns the 6px window edge into a resize grip.

        Uses the platform's native ``startSystemResize`` so resizing feels
        exactly like a normal window (with live preview + snap)."""
        if not self._frameless or self.isMaximized() or not self.isActiveWindow():
            return super().eventFilter(obj, event)
        et = event.type()
        try:
            if et == QEvent.Type.MouseMove:
                edges = self._edge_at(event.globalPosition().toPoint())
                self._update_edge_cursor(edges)
            elif et == QEvent.Type.MouseButtonPress and \
                    event.button() == Qt.MouseButton.LeftButton:
                edges = self._edge_at(event.globalPosition().toPoint())
                if edges:
                    handle = self.windowHandle()
                    if handle is not None:
                        handle.startSystemResize(edges)
                        return True
        except Exception:  # noqa: BLE001 - resize assist must never crash the app
            pass
        return super().eventFilter(obj, event)

    def _edge_at(self, gpos):
        r = self.frameGeometry()
        m = self._resize_margin
        left = abs(gpos.x() - r.left()) <= m
        right = abs(gpos.x() - r.right()) <= m
        top = abs(gpos.y() - r.top()) <= m
        bottom = abs(gpos.y() - r.bottom()) <= m
        # Only treat as an edge if the cursor is actually within the window band.
        if not (r.left() - m <= gpos.x() <= r.right() + m
                and r.top() - m <= gpos.y() <= r.bottom() + m):
            return Qt.Edge(0)
        edges = Qt.Edge(0)
        if left:
            edges |= Qt.Edge.LeftEdge
        if right:
            edges |= Qt.Edge.RightEdge
        if top:
            edges |= Qt.Edge.TopEdge
        if bottom:
            edges |= Qt.Edge.BottomEdge
        return edges

    def _update_edge_cursor(self, edges):
        cursors = {
            Qt.Edge.LeftEdge: Qt.CursorShape.SizeHorCursor,
            Qt.Edge.RightEdge: Qt.CursorShape.SizeHorCursor,
            Qt.Edge.TopEdge: Qt.CursorShape.SizeVerCursor,
            Qt.Edge.BottomEdge: Qt.CursorShape.SizeVerCursor,
            Qt.Edge.LeftEdge | Qt.Edge.TopEdge: Qt.CursorShape.SizeFDiagCursor,
            Qt.Edge.RightEdge | Qt.Edge.BottomEdge: Qt.CursorShape.SizeFDiagCursor,
            Qt.Edge.RightEdge | Qt.Edge.TopEdge: Qt.CursorShape.SizeBDiagCursor,
            Qt.Edge.LeftEdge | Qt.Edge.BottomEdge: Qt.CursorShape.SizeBDiagCursor,
        }
        cur = cursors.get(edges)
        if cur is not None:
            self.setCursor(cur)
            self._edge_cursor_active = True
        elif self._edge_cursor_active:
            self.unsetCursor()
            self._edge_cursor_active = False

    def resizeEvent(self, event):  # noqa: N802
        """Scale content margins to the window width so the layout breathes on
        large screens and reclaims space on small ones."""
        super().resizeEvent(event)
        layout = getattr(self, "_content_layout", None)
        if layout is None:
            return
        w = self.width()
        if w < 1040:
            side, top, bot = 16, 14, 12
        elif w < 1400:
            side, top, bot = 28, 24, 20
        else:
            side, top, bot = 44, 30, 24
        layout.setContentsMargins(side, top, side, bot)

    def closeEvent(self, event):  # noqa: N802
        if self._frameless:
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)
        # Ask any running worker to stop cleanly (scan/clean/etc. honor cancel),
        # so we don't tear down a thread mid-operation.
        for t in list(self._threads):
            worker = getattr(t, "_cortex_worker", None)
            if worker is not None and hasattr(worker, "cancel"):
                try:
                    worker.cancel()
                except Exception:  # noqa: BLE001
                    pass
        for t in list(self._threads):
            t.quit()
            t.wait(3000)
        super().closeEvent(event)


# =====================================================================
#  Scroll behavior policy (Req 5)
# =====================================================================

class SingleScrollFilter(QObject):
    """Route a wheel gesture to a single Scroll_Container (Req 5.5).

    Installed on an inner scrollable view (a list/tree/table) that lives inside
    a page's outer ``QScrollArea``. Without it, a wheel gesture over the inner
    view can scroll *both* the inner view and the outer page area at once - the
    janky "scroll-jump" where the whole page jumps while the list also moves.

    The rule this filter enforces is: **one gesture, one container.**

    - While the inner view can still scroll in the wheel's direction, the inner
      view consumes the wheel and the outer area stays put (a ``QScrollArea``
      does not propagate a consumed wheel event to its parent, so the outer
      value never changes while the inner list can still scroll).
    - Once the inner view reaches its scroll boundary (top/bottom), or when it
      has nothing to scroll at all, the gesture is forwarded to the outer
      ``Scroll_Container`` so the page scrolls instead.

    ``outer`` is the page's outer ``QScrollArea``; it may be ``None`` (in which
    case the filter simply lets the inner view handle its own wheel events).
    """

    def __init__(self, inner: QWidget, outer: QScrollArea | None = None,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._inner = inner
        self._outer = outer

    def eventFilter(self, obj, event):  # noqa: N802
        if event.type() != QEvent.Type.Wheel:
            return super().eventFilter(obj, event)
        try:
            sbar = self._inner.verticalScrollBar()
            can_scroll = sbar is not None and sbar.minimum() < sbar.maximum()
            if can_scroll:
                delta = event.angleDelta().y()
                at_top = sbar.value() <= sbar.minimum()
                at_bottom = sbar.value() >= sbar.maximum()
                # At a boundary and pushing further out: hand off to the outer
                # container so the page scrolls instead of dead-ending here.
                if (delta > 0 and at_top) or (delta < 0 and at_bottom):
                    return self._forward_to_outer(event)
                # Otherwise the inner view can still move: let it consume the
                # wheel itself. Returning False keeps default handling, and the
                # inner scroll area will not propagate to the outer area.
                return False
            # Inner view has nothing to scroll: route the gesture to the page.
            return self._forward_to_outer(event)
        except Exception:  # noqa: BLE001 - scroll routing must never crash the UI
            return super().eventFilter(obj, event)

    def _forward_to_outer(self, event) -> bool:
        """Send the wheel event to the outer Scroll_Container and consume it
        here so exactly one container reacts to the gesture."""
        if self._outer is None:
            return False
        QApplication.sendEvent(self._outer.viewport(), event)
        return True


# =====================================================================
#  Keyboard, focus, and modal helpers (Req 10)
# =====================================================================

def set_tab_order(parent: QWidget | None, widgets) -> list[QWidget]:
    """Chain keyboard Tab traversal across *widgets* in a predictable order.

    Qt derives the default Tab order from widget *construction* order, which can
    differ from the intended visual/logical order (a control built earlier may
    sit lower on screen). This helper enforces a deliberate order (Req 10.2) by
    chaining :meth:`QWidget.setTabOrder` over the given sequence so pressing Tab
    moves focus ``widgets[0] -> widgets[1] -> ... -> widgets[-1]``.

    ``None`` entries are skipped so callers can pass optional controls inline.
    ``parent`` is accepted for call-site clarity/consistency (the widget that
    owns the group); it is not required by Qt and may be ``None``. Returns the
    filtered list of widgets actually chained. Never raises - a failure to set
    tab order is cosmetic and must not break page construction.
    """
    focusable = [w for w in widgets if w is not None]
    for first, second in zip(focusable, focusable[1:]):
        try:
            QWidget.setTabOrder(first, second)
        except Exception:  # noqa: BLE001 - tab-order assist must never crash the UI
            _LOG.debug("set_tab_order: could not chain %r -> %r", first, second)
    return focusable


def ensure_focusable(*widgets) -> None:
    """Guarantee primary action controls can receive keyboard focus (Req 10.1).

    Any widget whose focus policy is ``NoFocus`` is promoted to ``StrongFocus``
    so it is reachable and activatable by keyboard. Buttons and inputs are
    natively focusable already; this is a defensive nudge for controls that were
    explicitly opted out (as the window controls in the title bar are) but that
    should be part of the keyboard path. ``None`` entries are ignored and any
    failure is swallowed.
    """
    for w in widgets:
        if w is None:
            continue
        try:
            if w.focusPolicy() == Qt.FocusPolicy.NoFocus:
                w.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        except Exception:  # noqa: BLE001 - focus assist must never crash the UI
            _LOG.debug("ensure_focusable: could not adjust %r", w)


def run_modal(dialog, trigger: QWidget | None = None):
    """Show *dialog* modally and return keyboard focus to *trigger* on close.

    Centralizes the modal-focus contract (Req 10.6): the dialog is shown modal
    (Qt moves keyboard focus into it), and when it closes, focus is restored to
    the ``trigger`` control that opened it so keyboard users are not dropped
    back at the top of the page. Returns the dialog's exec result code.

    Focus restoration runs even if the dialog raises, and any failure to restore
    focus is swallowed so it never masks the dialog's own outcome.
    """
    try:
        dialog.setModal(True)
    except Exception:  # noqa: BLE001 - some dialogs manage modality themselves
        pass
    try:
        return dialog.exec()
    finally:
        if trigger is not None:
            try:
                trigger.setFocus(Qt.FocusReason.OtherFocusReason)
            except Exception:  # noqa: BLE001 - focus return is best-effort
                _LOG.debug("run_modal: could not return focus to %r", trigger)


# =====================================================================
#  Pages
# =====================================================================

class _Page(QWidget):
    """Base page with access to the window + palette and a vertical layout.

    Scroll policy (Req 5)
    ---------------------
    Content sits inside a single outer vertical ``QScrollArea`` (the page's
    ``Scroll_Container``) with ``widgetResizable=True`` and ``ScrollBarAsNeeded``
    on both axes, so a scrollbar appears only when content exceeds the viewport
    (Req 5.1, 5.4) and is hidden when the page fits.

    Two page shapes share this base:

    - **Card-heavy pages** simply add cards to ``self.v``; the *outer* area
      scrolls when the stacked cards exceed the viewport (Req 5.1).
    - **List/tree/table-dominant pages** call :meth:`add_scrolling_list` (or
      apply the same policy by hand): the list gets a stretch factor plus a
      small ``minimumHeight`` so the page fits the viewport and only the *inner*
      list scrolls - no janky whole-page jump (Req 5.2). A
      :class:`SingleScrollFilter` is attached so a wheel gesture is routed to a
      single ``Scroll_Container`` and nested regions never scroll at once
      (Req 5.5).

    Subclasses keep using ``self.v`` as before.
    """

    #: Default small minimum height for an inner list/tree so the page fits the
    #: viewport while the inner view (not the whole page) does the scrolling.
    LIST_MIN_HEIGHT = 140

    def __init__(self, win: PremiumMainWindow):
        super().__init__()
        self.win = win
        self.p = win.palette_tokens

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        # ScrollBarAsNeeded on both axes: no scrollbar shows when the page fits
        # its viewport (Req 5.4); one appears only when content overflows.
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        _content = QWidget()
        self.v = QVBoxLayout(_content)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(18)
        self._scroll.setWidget(_content)
        self._outer.addWidget(self._scroll, 1)
        # Keep strong references to installed wheel filters so they outlive this
        # method (an event filter is dropped the moment it is garbage-collected).
        self._scroll_filters: list[SingleScrollFilter] = []

    # -- pinned footer (Req 5) ----------------------------------------------

    def pin_footer(self, widget: QWidget) -> QWidget:
        """Pin *widget* below the scroll area so it is ALWAYS fully visible.

        A footer added here lives *outside* the page's outer ``QScrollArea`` and
        therefore is never pushed below the fold or clipped when the scrollable
        content overflows. Use this for a page's primary action row (e.g. the
        dashboard "Clean" button) so it stays reachable at every window size
        while the scroll area (or an inner list) absorbs the overflow. Returns
        the widget for convenient chaining.
        """
        self._outer.addWidget(widget, 0)
        return widget

    # -- scroll policy helpers (Req 5.2, 5.5) -------------------------------

    def attach_single_scroll(self, inner: QWidget) -> SingleScrollFilter:
        """Route wheel gestures over ``inner`` to a single ``Scroll_Container``.

        Installs a :class:`SingleScrollFilter` on ``inner`` (and its viewport
        when it exposes one) wired to this page's outer scroll area, so a wheel
        gesture scrolls either the inner list or the page - never both at once
        (Req 5.5). Returns the filter (also retained on ``self``).
        """
        filt = SingleScrollFilter(inner, self._scroll, parent=inner)
        inner.installEventFilter(filt)
        viewport = getattr(inner, "viewport", None)
        if callable(viewport):
            vp = viewport()
            if vp is not None:
                vp.installEventFilter(filt)
        self._scroll_filters.append(filt)
        return filt

    def add_scrolling_list(self, inner: QWidget, *, stretch: int = 1,
                           minimum_height: int | None = None) -> QWidget:
        """Add a list/tree/table under the page's scroll policy (Req 5.2, 5.5).

        Gives ``inner`` a small ``minimumHeight`` and a layout stretch factor so
        the page fits the viewport and only the inner view scrolls, then routes
        its wheel gestures to a single ``Scroll_Container``. Returns ``inner``
        for convenient chaining.
        """
        inner.setMinimumHeight(self.LIST_MIN_HEIGHT if minimum_height is None
                               else minimum_height)
        self.v.addWidget(inner, stretch)
        self.attach_single_scroll(inner)
        return inner


class DashboardPage(_Page):
    """1-click hero scan + reclaimable overview + category table."""

    def __init__(self, win: PremiumMainWindow):
        super().__init__(win)
        self._report = None
        self._preview_targets: dict = {}
        self._preview_counter = 0
        self._excluded: dict[int, set[str]] = {}   # scan_idx -> excluded path prefixes
        self._updating = False                      # guard for programmatic check changes

        self.v.addWidget(title_block(
            "Dashboard",
            "One click to find safely-reclaimable space across your system.",
        ))

        # Hero row: gauge card + stat cards
        hero_row = QHBoxLayout()
        hero_row.setSpacing(18)

        gauge_card = Card(self.p, "HeroCard")
        gauge_card.setFixedWidth(268)
        gc = QVBoxLayout(gauge_card)
        gc.setContentsMargins(16, 14, 16, 14)
        gc.setSpacing(8)
        self.gauge = CircularGauge(self.p, caption="selected to clean")
        # Trim the hero gauge on the dashboard specifically (not the shared
        # CircularGauge class) so the tall hero row does not dominate the
        # viewport and starve the category tree of vertical space. A compact
        # gauge keeps the hero bounded so the tree can grow to show more rows.
        self.gauge.setMinimumSize(128, 128)
        self.gauge.setMaximumHeight(146)
        from .widgets import attach_glow
        attach_glow(self.gauge, self.p.accent, 34, 55)
        gc.addWidget(self.gauge, alignment=Qt.AlignmentFlag.AlignCenter)

        self.scan_btn = QPushButton("Scan Now")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.clicked.connect(self._toggle_scan)
        gc.addWidget(self.scan_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        gc.addWidget(self.progress)

        self.scan_status = QLabel("")
        self.scan_status.setObjectName("Muted")
        self.scan_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scan_status.setWordWrap(True)
        gc.addWidget(self.scan_status)

        self._scan_worker = None
        self._scanning = False
        hero_row.addWidget(gauge_card, 0)

        # stat column
        stat_col = QVBoxLayout()
        stat_col.setSpacing(14)
        self.card_space = StatCard(self.p, "Total reclaimable", "—")
        self.card_files = StatCard(self.p, "Files found", "—")
        self.card_cats = StatCard(self.p, "Categories", "—")
        for c in (self.card_space, self.card_files, self.card_cats):
            stat_col.addWidget(c)
        stat_col.addStretch(1)
        hero_row.addLayout(stat_col, 1)
        self.v.addLayout(hero_row)

        # category tree (expandable to preview contents before cleaning)
        section = QLabel("Cleanup categories  \u2014  expand any row to preview what's inside")
        section.setObjectName("SectionTitle")
        self.v.addWidget(section)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Category", "Risk", "Files", "Size"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.setColumnWidth(1, 90)
        self.tree.setColumnWidth(2, 90)
        self.tree.setColumnWidth(3, 110)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setRootIsDecorated(True)
        # The tree is the page's single INTERNAL scroller: give it an expanding
        # vertical size policy so it grows to fill whatever space is left after
        # the (fixed-ish) hero, and a modest minimum so it always shows a useful
        # number of rows. Its own scrollbar (not the outer page) absorbs the
        # overflow, so the pinned Clean action below never gets pushed off.
        self.tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # A generous minimum so the tree always shows a useful number of rows
        # (well beyond the ~3 it used to reveal) even on smaller windows where
        # the outer page has to scroll: the tree keeps this height and reveals
        # 5+ categories, with its own scrollbar for the rest.
        self.tree.setMinimumHeight(230)
        self.tree.itemExpanded.connect(self._expand_category)
        self.tree.itemChanged.connect(self._on_item_changed)
        # add_scrolling_list wires the single-scroll wheel routing so a wheel
        # gesture over the tree scrolls the tree (not the whole page) until it
        # hits a boundary (Req 5.2, 5.5).
        self.add_scrolling_list(self.tree, stretch=1, minimum_height=230)

        self.smart_label = QLabel("")
        self.smart_label.setObjectName("Muted")
        self.smart_label.setVisible(False)
        self.v.addWidget(self.smart_label)

        # action row - PINNED below the scroll area so the primary "Clean"
        # action is ALWAYS fully visible and never clipped by the viewport or
        # overlapped by the status bar, at any window size (the tree absorbs
        # overflow via its own scrollbar instead of pushing this row off-screen).
        actions_row = QWidget()
        actions = QHBoxLayout(actions_row)
        actions.setContentsMargins(0, 12, 0, 0)
        actions.addStretch(1)
        self.recycle_btn = QPushButton("Clean Selected")
        self.recycle_btn.setObjectName("Primary")
        self.recycle_btn.setEnabled(False)
        self.recycle_btn.clicked.connect(lambda: self._clean("delete"))
        actions.addWidget(self.recycle_btn)
        self.pin_footer(actions_row)

        # Subtle accent glow on the two hero CTAs only (perf-safe, gentle).
        from .widgets import attach_glow
        attach_glow(self.scan_btn, self.p.accent, 22, 80)
        attach_glow(self.recycle_btn, self.p.accent, 18, 70)

    # -- actions --
    def _toggle_scan(self):
        if self._scanning:
            self._cancel_scan()
        else:
            self._scan()

    def _scan(self):
        from .workers import ScanWorker
        self._scanning = True
        self.scan_btn.setText("Cancel")
        self.progress.setVisible(True)
        self.scan_status.setText("Starting scan\u2026")
        self.win.statusBar().showMessage("Scanning...")
        self.gauge.set_center_text("\u2026")
        self._scan_worker = ScanWorker(max_risk="medium")
        self.win.run_worker(
            self._scan_worker, self._on_scanned, self._on_fail, on_progress=self._on_progress
        )

    def _cancel_scan(self):
        if self._scan_worker is not None:
            self._scan_worker.cancel()
            self.scan_status.setText("Cancelling\u2026")
            self.scan_btn.setEnabled(False)

    def _on_progress(self, text: str):
        self.scan_status.setText(text)

    def _on_scanned(self, report):
        self._report = report
        self._scanning = False
        self._scan_worker = None
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan Now")
        total = report.total_reclaimable_bytes
        self.card_space.set_value(fmt_bytes(total), animate=True)
        self.card_files.set_value(str(report.total_files), animate=True)
        self.card_cats.set_value(str(len(report.scans)), animate=True)

        self._excluded = {}
        self._preview_targets = {}
        self._updating = True
        self.tree.clear()
        risk_labels = {"low": "SAFE", "medium": "REVIEW", "high": "CAUTION"}
        for idx, scan in enumerate(report.scans):
            ctx = {"category": scan.category.id, "size": scan.total_bytes,
                   "age_days": scan.category.min_age_days}
            top = QTreeWidgetItem([
                scan.category.label,
                "",   # risk shown as a pill badge widget below
                str(scan.file_count),
                fmt_bytes(scan.total_bytes),
            ])
            top.setFlags(top.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            # Only auto-check SAFE (low-risk) categories. Medium/review (e.g.
            # browser cache) start unchecked so the user opts in deliberately.
            # The offline learner can still un-check a low one it learned you skip.
            is_safe = scan.category.risk.value == "low"
            checked = is_safe and self.win.suggester.recommend(ctx)
            top.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            top.setData(0, Qt.ItemDataRole.UserRole, ctx)
            top.setData(0, Qt.ItemDataRole.UserRole + 1, idx)      # scan index
            top.setToolTip(0, scan.category.description)
            # placeholder child so the expand arrow shows; real contents load lazily
            if scan.file_count:
                placeholder = QTreeWidgetItem(["Loading\u2026", "", "", ""])
                top.addChild(placeholder)
            self.tree.addTopLevelItem(top)
            # Real rounded pill badge for the risk column, with a plain-language
            # tooltip so users understand exactly how safe each category is.
            badge = Badge(self.p, scan.category.risk.value)
            badge.setToolTip({
                "low": "Safe to delete \u2014 auto-regenerating cache. No personal "
                       "data, passwords or settings. Goes to the Recycle Bin.",
                "medium": "Safe to delete, but it will re-download later (e.g. browser "
                          "cache means pages re-fetch). Goes to the Recycle Bin.",
                "high": "Review carefully before deleting.",
            }.get(scan.category.risk.value, ""))
            self.tree.setItemWidget(top, 1, badge)
        self._updating = False
        self._update_selection()   # reflect the auto-checked (SAFE) size live
        self.win.statusBar().showMessage(
            f"Found {fmt_bytes(total)} across {report.total_files} files", 5000)

    # -- live "selected to clean" total ------------------------------------

    def _selected_bytes(self) -> int:
        """Sum of what's currently checked, respecting per-app/folder exclusions."""
        if self._report is None:
            return 0
        total = 0
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            idx = item.data(0, self._ROLE_SCANIDX)
            if idx is None or item.checkState(0) == Qt.CheckState.Unchecked:
                continue
            scan = self._report.scans[idx]
            excl = self._excluded.get(idx)
            if not excl:
                total += scan.total_bytes           # whole category (fast path)
            else:
                total += sum(e.size for e in self._filtered_entries(scan, idx))
        return total

    def _update_selection(self):
        """Refresh the gauge + Clean button to show the live selected size."""
        if self._report is None:
            return
        sel = self._selected_bytes()
        grand = self._report.total_reclaimable_bytes or 1
        pct = min(100.0, sel / grand * 100.0)
        self.gauge.animate_to(pct, display=fmt_bytes(sel))
        self.recycle_btn.setText(f"Clean {fmt_bytes(sel)}" if sel else "Clean Selected")
        self.recycle_btn.setEnabled(sel > 0)

    # Tree item data roles for the preview drill-down.
    _ROLE_CTX = Qt.ItemDataRole.UserRole
    _ROLE_SCANIDX = Qt.ItemDataRole.UserRole + 1
    _ROLE_PREFIX = Qt.ItemDataRole.UserRole + 2
    _ROLE_LOADED = Qt.ItemDataRole.UserRole + 3
    _ROLE_NODEPATH = Qt.ItemDataRole.UserRole + 4   # this node's own fs path (preview)

    def _expand_category(self, item: QTreeWidgetItem):
        """Lazily populate a node's contents off the UI thread when expanded.

        Works for both category nodes (aggregate per root folder) and folder
        nodes (drill into subfolders/files) - to any depth. All grouping runs
        in a background worker so expanding never freezes the UI, even for
        categories with 100k+ files.
        """
        if self._report is None:
            return
        if item.data(0, self._ROLE_LOADED):
            return
        scan_idx = item.data(0, self._ROLE_SCANIDX)
        if scan_idx is None:
            return
        try:
            scan = self._report.scans[scan_idx]
        except (IndexError, TypeError):
            return
        item.setData(0, self._ROLE_LOADED, True)

        # Show a lightweight "loading" placeholder while the worker runs.
        item.takeChildren()
        loading = QTreeWidgetItem(["Loading\u2026", "", "", ""])
        loading.setFlags(loading.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
        item.addChild(loading)

        nid = self._preview_counter
        self._preview_counter += 1
        self._preview_targets[nid] = item

        from .workers import DirPreviewWorker
        prefix = item.data(0, self._ROLE_PREFIX)
        if prefix:   # folder / app node -> drill into its contents
            worker = DirPreviewWorker(nid, scan.entries, "folder", prefix=prefix)
        elif scan.category.id == "app_caches":
            # Application caches -> group by owning app (Chrome, Discord, ...).
            import os
            bases = [os.environ.get("LOCALAPPDATA", ""), os.environ.get("APPDATA", ""),
                     os.environ.get("PROGRAMDATA", "")]
            bases = [b for b in bases if b]
            worker = DirPreviewWorker(nid, scan.entries, "appwise", roots=bases)
        else:        # generic category node
            roots = scan.category.existing_paths() or list(scan.category.paths)
            if len(roots) == 1:
                worker = DirPreviewWorker(nid, scan.entries, "folder", prefix=str(roots[0]))
            else:
                worker = DirPreviewWorker(nid, scan.entries, "category", roots=roots)
        self.win.run_worker(worker, self._apply_preview, self._preview_fail)

    def _apply_preview(self, nid: int, children: list):
        item = self._preview_targets.pop(nid, None)
        if item is None:
            return
        scan_idx = item.data(0, self._ROLE_SCANIDX)
        parent_checked = item.checkState(0) != Qt.CheckState.Unchecked
        self._updating = True   # setting check states below must not fire the handler
        item.takeChildren()   # remove the "Loading..." placeholder
        if not children:
            empty = QTreeWidgetItem(["(nothing to preview)", "", "", ""])
            empty.setFlags(empty.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            item.addChild(empty)
            self._updating = False
            return
        excl = self._excluded.get(scan_idx, set())
        for c in children:
            glyph = "\U0001F4C1 " if c["is_dir"] else "\U0001F4C4 "
            child = QTreeWidgetItem([glyph + c["name"], "",
                                    str(c["count"]), fmt_bytes(c["size"])])
            child.setToolTip(0, c["path"])
            child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            child.setData(0, self._ROLE_SCANIDX, scan_idx)
            child.setData(0, self._ROLE_NODEPATH, c["path"])
            # Initial check state: unchecked if parent is unchecked or this path
            # was previously excluded; otherwise checked.
            npath = c["path"].replace("/", "\\")
            is_excluded = (not parent_checked) or any(
                npath == x or npath.startswith(x + "\\") for x in excl)
            child.setCheckState(0, Qt.CheckState.Unchecked if is_excluded
                                else Qt.CheckState.Checked)
            if c["expandable"]:
                child.setData(0, self._ROLE_PREFIX, c["path"])
                ph = QTreeWidgetItem(["Loading\u2026", "", "", ""])
                child.addChild(ph)   # placeholder so the expand arrow appears
            item.addChild(child)
        self._updating = False

    def _preview_fail(self, msg: str):
        # Preview is non-critical; just log to the status bar.
        self.win.statusBar().showMessage(f"Preview failed: {msg}", 4000)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Track per-app / per-folder selection so cleaning respects it."""
        if self._updating or column != 0:
            return
        scan_idx = item.data(0, self._ROLE_SCANIDX)
        if scan_idx is None:
            return
        node_path = item.data(0, self._ROLE_NODEPATH)
        state = item.checkState(0)
        if node_path is not None:
            excl = self._excluded.setdefault(scan_idx, set())
            npath = str(node_path).replace("/", "\\")
            if state == Qt.CheckState.Unchecked:
                excl.add(npath)
            else:
                # Re-include this node and anything beneath it.
                self._excluded[scan_idx] = {
                    x for x in excl if x != npath and not x.startswith(npath + "\\")}
        # Cascade the new state to already-loaded descendants for visual consistency.
        self._updating = True
        self._set_subtree_check(item, state)
        self._updating = False
        # Reflect the new selection size live in the gauge + Clean button.
        self._update_selection()

    def _set_subtree_check(self, item: QTreeWidgetItem, state) -> None:
        for i in range(item.childCount()):
            child = item.child(i)
            if child.text(0) == "Loading\u2026":
                continue
            if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                child.setCheckState(0, state)
            self._set_subtree_check(child, state)

    def _filtered_entries(self, scan, scan_idx: int):
        """Entries for *scan* minus any the user deselected in the preview."""
        excl = self._excluded.get(scan_idx)
        if not excl:
            return scan.entries
        out = []
        for e in scan.entries:
            ep = str(e.path).replace("/", "\\")
            if any(ep == x or ep.startswith(x + "\\") for x in excl):
                continue
            out.append(e)
        return out

    def _clean(self, method: str):
        if not self._report or not self._report.scans:
            return
        from cortex_unified.engine.service import CleanupReport

        # Record the offline learning signal from the user's selection, and
        # collect the checked categories to actually clean.
        from cortex_unified.engine.service import CategoryScan
        checked_scans = []
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            idx = item.data(0, self._ROLE_SCANIDX)
            if idx is None:
                continue
            scan = self._report.scans[idx]
            ctx = item.data(0, self._ROLE_CTX) or {"category": scan.category.id}
            is_checked = item.checkState(0) != Qt.CheckState.Unchecked
            self.win.suggester.observe(ctx, cleaned=is_checked)
            if not is_checked:
                continue
            # Honor per-app / per-folder deselection inside this category.
            entries = self._filtered_entries(scan, idx)
            if not entries:
                continue
            fs = CategoryScan(category=scan.category)
            fs.entries = entries
            fs.total_bytes = sum(e.size for e in entries)
            checked_scans.append(fs)
        self.win.suggester.save()

        if not checked_scans:
            QMessageBox.information(self, "Nothing selected",
                                   "Check at least one category to clean.")
            return
        filtered = CleanupReport(scans=checked_scans)
        confirm = QMessageBox.question(
            self, "Confirm cleanup",
            f"Free {fmt_bytes(filtered.total_reclaimable_bytes)} by removing "
            f"{filtered.total_files:,} regenerable cache/temp files across "
            f"{len(checked_scans)} categ(ies)?\n\n"
            "These are auto-regenerating caches (no personal data), so they're "
            "deleted permanently \u2014 which is fast and frees the space "
            "immediately. Files in use will be skipped.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        from .workers import CleanWorker
        self.recycle_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.scan_status.setText("Cleaning\u2026")
        self.win.statusBar().showMessage("Cleaning...")
        self._clean_worker = CleanWorker(filtered, method)
        self.win.run_worker(self._clean_worker, self._on_cleaned, self._on_fail,
                            on_progress=self._on_clean_progress)

    def _on_clean_progress(self, text: str):
        self.scan_status.setText(text)

    def _on_cleaned(self, freed: int, items: int, skipped: int):
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self._clean_worker = None
        msg = f"Reclaimed {fmt_bytes(freed)} from {items:,} items."
        if skipped:
            msg += (f"  {skipped:,} were in use and skipped \u2014 close the app "
                    "(e.g. your browser) and clean again to remove those.")
        self.win.statusBar().showMessage(msg, 8000)
        QMessageBox.information(self, "Cleanup complete", msg)
        self._scan()  # refresh

    def _on_fail(self, msg: str):
        self._scanning = False
        self._scan_worker = None
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan Now")
        self.recycle_btn.setEnabled(True)
        self.win._default_fail(msg)


class _FolderScanPage(_Page):
    """Shared scaffold for pages that pick a folder and list results."""

    title = ""
    subtitle = ""
    action_label = "Scan folder"

    def __init__(self, win: PremiumMainWindow):
        super().__init__(win)
        self.v.addWidget(title_block(self.title, self.subtitle))

        picker = QHBoxLayout()
        self.path_label = QLabel("No folder selected")
        self.path_label.setObjectName("Muted")
        pick_btn = QPushButton("Choose Folder\u2026")
        pick_btn.clicked.connect(self._pick)
        self.run_btn = QPushButton(self.action_label)
        self.run_btn.setObjectName("Primary")
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._toggle_run)
        picker.addWidget(pick_btn)
        picker.addWidget(self.path_label, 1)
        picker.addWidget(self.run_btn)
        self.v.addLayout(picker)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.scan_status = QLabel("")
        self.scan_status.setObjectName("Muted")
        self.v.addWidget(self.scan_status)

        self._worker = None
        self._running = False

        # Subclasses assign self.results_table (path in column 0) here.
        self.results_table: QTableWidget | None = None
        self.result_area = self._build_results()
        self.v.addWidget(self.result_area, 1)

        # Shared "reclaim selected" action row.
        action_row = QHBoxLayout()
        self.hint = QLabel("Select rows, then move them to the Recycle Bin.")
        self.hint.setObjectName("Muted")
        action_row.addWidget(self.hint)
        action_row.addStretch(1)
        self.del_btn = QPushButton("Move Selected to Recycle Bin")
        self.del_btn.setObjectName("Danger")
        self.del_btn.setEnabled(False)
        self.del_btn.clicked.connect(self._delete_selected)
        action_row.addWidget(self.del_btn)
        self.v.addLayout(action_row)

        self._folder: str | None = None

    def _build_results(self) -> QWidget:
        raise NotImplementedError

    def _pick(self):
        folder = QFileDialog.getExistingDirectory(self, "Select a folder", str(Path.home()))
        if folder:
            self._folder = folder
            self.path_label.setText(folder)
            self.run_btn.setEnabled(True)

    def _run(self):
        raise NotImplementedError

    def _start(self, worker, on_done, on_fail):
        """Start a scan worker with live progress + cancel support.

        on_done/on_fail MUST be bound methods of this page (main-thread
        QObject) so Qt queues them onto the GUI thread.
        """
        self._worker = worker
        self._running = True
        self.progress.setVisible(True)
        self.scan_status.setText("Starting\u2026")
        self.run_btn.setText("Cancel")
        self.run_btn.setEnabled(True)
        self.del_btn.setEnabled(False)
        self.win.run_worker(worker, on_done, on_fail, on_progress=self._on_progress)

    def _toggle_run(self):
        if self._running and self._worker is not None:
            if hasattr(self._worker, "cancel"):
                self._worker.cancel()
            self.scan_status.setText("Cancelling\u2026")
            self.run_btn.setEnabled(False)
        else:
            self._run()

    def _on_progress(self, text: str):
        self.scan_status.setText(text)

    def _finish(self):
        self._running = False
        self._worker = None
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.run_btn.setText(self.action_label)
        self.run_btn.setEnabled(True)

    def _busy(self, on: bool):
        self.progress.setVisible(on)
        self.run_btn.setEnabled(not on)

    def _enable_actions(self, has_rows: bool):
        if self.results_table is not None:
            self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.del_btn.setEnabled(has_rows)

    def _selected_paths(self) -> list[str]:
        if self.results_table is None:
            return []
        rows = {idx.row() for idx in self.results_table.selectedIndexes()}
        out: list[str] = []
        for r in sorted(rows):
            item = self.results_table.item(r, 0)
            if item and item.text():
                out.append(item.text())
        return out

    def _delete_selected(self):
        paths = self._selected_paths()
        if not paths:
            QMessageBox.information(self, "No selection", "Select one or more rows first.")
            return
        confirm = QMessageBox.question(
            self, "Move to Recycle Bin",
            f"Move {len(paths)} selected item(s) to the Recycle Bin?\n\n"
            "You can restore them from the Recycle Bin if needed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        from .workers import DeleteSelectedWorker
        self._busy(True)
        self.del_btn.setEnabled(False)
        worker = DeleteSelectedWorker(paths, "recycle")
        self.win.run_worker(worker, self._on_deleted, self._del_fail)

    def _on_deleted(self, freed: int, ok: int, blocked: int):
        self._busy(False)
        msg = f"Recycled {ok} item(s), freeing {fmt_bytes(freed)}."
        if blocked:
            msg += f" {blocked} blocked by the safety guard or unavailable Recycle Bin."
        self.win.statusBar().showMessage(msg, 6000)
        QMessageBox.information(self, "Done", msg)
        if self._folder:
            self._run()  # refresh listing

    def _del_fail(self, msg: str):
        self._busy(False)
        self.del_btn.setEnabled(True)
        self.win._default_fail(msg)


class DuplicatesPage(_FolderScanPage):
    title = "Duplicate Finder"
    subtitle = "Byte-for-byte duplicate detection (size-prefiltered, xxHash/BLAKE3)."
    action_label = "Find Duplicates"

    def _build_results(self) -> QWidget:
        self.tree = QTableWidget(0, 2)
        self.tree.setHorizontalHeaderLabels(["Duplicate file", "Group"])
        self.tree.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.verticalHeader().setVisible(False)
        self.tree.setAlternatingRowColors(True)
        self.results_table = self.tree
        return self.tree

    def _run(self):
        from .workers import DuplicateWorker
        self._start(DuplicateWorker([self._folder]), self._done, self._fail)

    def _done(self, groups: dict):
        self._finish()
        rows = [(p, i) for i, (_, members) in enumerate(groups.items(), 1) for p in members]
        self.tree.setRowCount(len(rows))
        for r, (path, gid) in enumerate(rows):
            self.tree.setItem(r, 0, QTableWidgetItem(str(path)))
            self.tree.setItem(r, 1, QTableWidgetItem(f"#{gid}"))
        self.hint.setText("Keep one copy per group; select the extras to recycle.")
        self._enable_actions(bool(rows))
        self.win.statusBar().showMessage(f"{len(groups)} duplicate groups found", 5000)

    def _fail(self, msg):
        self._finish()
        self.win._default_fail(msg)


class DuplicatePhotosPage(_FolderScanPage):
    title = "Duplicate Photos"
    subtitle = ("Find duplicate images (JPG, PNG, HEIC, RAW, ...) byte-for-byte. "
                "Free up space taken by copied photos.")
    action_label = "Find Duplicate Photos"

    def _build_results(self) -> QWidget:
        self.tree = QTableWidget(0, 2)
        self.tree.setHorizontalHeaderLabels(["Duplicate photo", "Group"])
        self.tree.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.verticalHeader().setVisible(False)
        self.tree.setAlternatingRowColors(True)
        self.results_table = self.tree
        return self.tree

    def _run(self):
        from .workers import DuplicatePhotosWorker
        self._start(DuplicatePhotosWorker([self._folder]), self._done, self._fail)

    def _done(self, groups: dict):
        self._finish()
        rows = [(p, i) for i, (_, members) in enumerate(groups.items(), 1) for p in members]
        self.tree.setRowCount(len(rows))
        for r, (path, gid) in enumerate(rows):
            self.tree.setItem(r, 0, QTableWidgetItem(str(path)))
            self.tree.setItem(r, 1, QTableWidgetItem(f"#{gid}"))
        self.hint.setText("Keep one photo per group; select the extra copies to recycle.")
        self._enable_actions(bool(rows))
        self.win.statusBar().showMessage(f"{len(groups)} duplicate photo groups found", 5000)

    def _fail(self, msg):
        self._finish()
        self.win._default_fail(msg)


class LargeFilesPage(_FolderScanPage):
    title = "Large Files"
    subtitle = "Find the biggest space hogs, largest first."
    action_label = "Find Large Files"

    def _build_results(self) -> QWidget:
        self.tbl = QTableWidget(0, 2)
        self.tbl.setHorizontalHeaderLabels(["File", "Size"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.results_table = self.tbl
        return self.tbl

    def _run(self):
        from .workers import LargeFilesWorker
        self._start(LargeFilesWorker(self._folder, 50.0), self._done, self._fail)

    def _done(self, entries: list):
        self._finish()
        self.tbl.setRowCount(len(entries))
        for r, e in enumerate(entries):
            self.tbl.setItem(r, 0, QTableWidgetItem(str(e.path)))
            self.tbl.setItem(r, 1, QTableWidgetItem(fmt_bytes(e.size)))
        self._enable_actions(bool(entries))
        self.win.statusBar().showMessage(f"{len(entries)} large files", 5000)

    def _fail(self, msg):
        self._finish()
        self.win._default_fail(msg)


class EmptyPage(_FolderScanPage):
    title = "Empty Items"
    subtitle = "Locate empty files and directories."
    action_label = "Find Empty Items"

    def _build_results(self) -> QWidget:
        self.tbl = QTableWidget(0, 2)
        self.tbl.setHorizontalHeaderLabels(["Path", "Type"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.results_table = self.tbl
        return self.tbl

    def _run(self):
        from .workers import EmptyWorker
        self._start(EmptyWorker(self._folder), self._done, self._fail)

    def _done(self, files: list, dirs: list):
        self._finish()
        rows = [(p, "File") for p in files] + [(p, "Directory") for p in dirs]
        self.tbl.setRowCount(len(rows))
        for r, (path, kind) in enumerate(rows):
            self.tbl.setItem(r, 0, QTableWidgetItem(str(path)))
            self.tbl.setItem(r, 1, QTableWidgetItem(kind))
        self._enable_actions(bool(rows))
        self.win.statusBar().showMessage(f"{len(files)} empty files, {len(dirs)} empty dirs", 5000)

    def _fail(self, msg):
        self._finish()
        self.win._default_fail(msg)


class ShredPage(_Page):
    """Storage-aware secure deletion, honest about SSD limitations."""

    def __init__(self, win: PremiumMainWindow):
        super().__init__(win)
        self._target: str | None = None

        self.v.addWidget(title_block(
            "Secure Shred",
            "Overwrite-then-delete. Honest: multi-pass overwrite is only reliable on HDDs.",
        ))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(14)

        picker = QHBoxLayout()
        pick_btn = QPushButton("Choose File\u2026")
        pick_btn.clicked.connect(self._pick)
        self.target_label = QLabel("No file selected")
        self.target_label.setObjectName("Muted")
        picker.addWidget(pick_btn)
        picker.addWidget(self.target_label, 1)
        cl.addLayout(picker)

        self.medium_label = QLabel("Medium: \u2014")
        cl.addWidget(self.medium_label)

        opts = QHBoxLayout()
        opts.addWidget(QLabel("Overwrite passes:"))
        from PySide6.QtWidgets import QCheckBox, QSpinBox
        self.passes = QSpinBox()
        self.passes.setRange(1, 35)
        self.passes.setValue(3)
        opts.addWidget(self.passes)
        opts.addStretch(1)
        self.force_flash = QCheckBox("Overwrite on SSD anyway (best-effort)")
        opts.addWidget(self.force_flash)
        cl.addLayout(opts)

        cl.addWidget(hline(self.p))
        row = QHBoxLayout()
        row.addStretch(1)
        self.shred_btn = QPushButton("Shred Permanently")
        self.shred_btn.setObjectName("Danger")
        self.shred_btn.setEnabled(False)
        self.shred_btn.clicked.connect(self._shred)
        row.addWidget(self.shred_btn)
        cl.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        cl.addWidget(self.progress)

        self.v.addWidget(card)

        # -- Free-space wipe (feature D) --
        import platform as _platform
        if _platform.system() == "Windows":
            wipe_card = Card(self.p)
            wl = QVBoxLayout(wipe_card)
            wl.setContentsMargins(22, 20, 22, 20)
            wl.setSpacing(12)
            wl.addWidget(title_block(
                "Wipe Free Space",
                "Overwrite unused space so already-deleted files can't be "
                "recovered by undelete tools. Uses Windows 'cipher /w'. Can take "
                "a long time and needs plenty of free space to churn through.",
            ))
            wrow = QHBoxLayout()
            wrow.addWidget(QLabel("Drive letter:"))
            from PySide6.QtWidgets import QComboBox
            self.wipe_drive = QComboBox()
            self.wipe_drive.setEditable(False)
            self._populate_drives()
            wrow.addWidget(self.wipe_drive)
            wrow.addStretch(1)
            self.wipe_btn = QPushButton("Wipe Free Space")
            self.wipe_btn.setObjectName("Danger")
            self.wipe_btn.clicked.connect(self._wipe_free_space)
            wrow.addWidget(self.wipe_btn)
            wl.addLayout(wrow)
            self.wipe_progress = QProgressBar()
            self.wipe_progress.setRange(0, 0)
            self.wipe_progress.setVisible(False)
            wl.addWidget(self.wipe_progress)
            self.v.addWidget(wipe_card)

        self.v.addStretch(1)

    def _populate_drives(self):
        import string
        from pathlib import Path as _P
        for letter in string.ascii_uppercase:
            if _P(f"{letter}:\\").exists():
                self.wipe_drive.addItem(f"{letter}:", letter)

    def _wipe_free_space(self):
        letter = self.wipe_drive.currentData()
        if not letter:
            return
        confirm = QMessageBox.warning(
            self, "Wipe free space",
            f"Overwrite all free space on {letter}:?\n\n"
            "This does NOT touch your existing files, but it can take a long "
            "time and keep the disk busy. Requires Administrator.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        from .workers import FreeSpaceWipeWorker
        self.wipe_btn.setEnabled(False)
        self.wipe_progress.setVisible(True)
        self.win.statusBar().showMessage(f"Wiping free space on {letter}:\u2026")
        self.win.run_worker(FreeSpaceWipeWorker(letter), self._on_wiped, self._on_wipe_fail)

    def _on_wiped(self, success: bool, message: str):
        self.wipe_progress.setVisible(False)
        self.wipe_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Free space wiped", message)
        else:
            QMessageBox.warning(self, "Free-space wipe", message)
        self.win.statusBar().showMessage(message, 6000)

    def _on_wipe_fail(self, msg: str):
        self.wipe_progress.setVisible(False)
        self.wipe_btn.setEnabled(True)
        self.win._default_fail(msg)

    def _pick(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select a file to shred", str(Path.home()))
        if not path:
            return
        self._target = path
        self.target_label.setText(path)
        self.shred_btn.setEnabled(True)
        self.medium_label.setText("Medium: detecting\u2026")
        from .workers import StorageWorker
        self.win.run_worker(StorageWorker(path), self._on_medium, self._fail)

    def _on_medium(self, kind: str, overwrite_effective: bool):
        note = "" if overwrite_effective else "  \u2014 overwrite NOT reliable here"
        color = self.p.success if overwrite_effective else self.p.warning
        self.medium_label.setText(f"Medium: {kind}{note}")
        self.medium_label.setStyleSheet(f"color: {color}; font-weight: 600;")

    def _shred(self):
        if not self._target:
            return
        confirm = QMessageBox.warning(
            self, "Confirm secure shred",
            f"Permanently shred this file? This CANNOT be undone.\n\n{self._target}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        from .workers import ShredWorker
        self.shred_btn.setEnabled(False)
        self.progress.setVisible(True)
        worker = ShredWorker(self._target, self.passes.value(), self.force_flash.isChecked())
        # ShredWorker has an extra 'refused' signal; wire it before run_worker.
        worker.refused.connect(self._on_refused)
        self.win.run_worker(worker, self._on_done, self._fail)

    def _on_done(self, outcome: str, reason: str):
        self.progress.setVisible(False)
        self.shred_btn.setEnabled(True)
        msg = f"{outcome}" + (f"  ({reason})" if reason else "")
        self.win.statusBar().showMessage(f"Shred: {msg}", 6000)
        QMessageBox.information(self, "Shred complete", msg)
        self._target = None
        self.target_label.setText("No file selected")
        self.shred_btn.setEnabled(False)

    def _on_refused(self, kind: str, guidance: str):
        self.progress.setVisible(False)
        self.shred_btn.setEnabled(True)
        QMessageBox.information(
            self, "Not effective on this medium",
            guidance + "\n\nTip: enable 'Overwrite on SSD anyway' only if you understand "
            "it wears the drive without a hard guarantee. For real assurance use full-disk "
            "encryption + key destruction, or the drive's hardware secure-erase.",
        )

    def _fail(self, msg: str):
        self.progress.setVisible(False)
        self.shred_btn.setEnabled(True)
        self.win._default_fail(msg)


class SettingsPage(_Page):
    def __init__(self, win: PremiumMainWindow):
        super().__init__(win)
        self.v.addWidget(title_block("Settings", "Appearance and engine information."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(14)

        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme"))
        theme_row.addStretch(1)
        self.dark_btn = QPushButton("Dark")
        self.light_btn = QPushButton("Light")
        self.dark_btn.clicked.connect(lambda: self.win.set_theme("dark"))
        self.light_btn.clicked.connect(lambda: self.win.set_theme("light"))
        theme_row.addWidget(self.dark_btn)
        theme_row.addWidget(self.light_btn)
        cl.addLayout(theme_row)
        cl.addWidget(hline(self.p))

        from cortex_unified.engine import HASH_ALGORITHM
        info = QLabel(
            f"Hash backend: {HASH_ALGORITHM}\n"
            "Deletions are storage-aware: overwrite-shredding is only applied on\n"
            "rotational (HDD) media; on SSD/NVMe it is reported honestly."
        )
        info.setObjectName("Muted")
        cl.addWidget(info)
        self.v.addWidget(card)

        # -- Smart Suggestions (offline learning) --------------------------
        self._build_smart_card()

        # -- System Safety: restore points ---------------------------------
        self._build_safety_card()
        self.v.addStretch(1)

    def _build_smart_card(self):
        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(10)
        title = QLabel("Smart Suggestions \u2014 On-device Learning")
        title.setObjectName("SectionTitle")
        cl.addWidget(title)

        st = self.win.suggester.stats()
        self.smart_stats = QLabel(
            f"Signals learned: {st['updates']}  \u2022  "
            f"Status: {'personalized' if st['trained'] else 'gathering data'}\n"
            "Learns which cleanup categories you keep vs. skip and pre-selects "
            "accordingly. 100% offline \u2014 no data ever leaves your PC."
        )
        self.smart_stats.setObjectName("Muted")
        self.smart_stats.setWordWrap(True)
        cl.addWidget(self.smart_stats)

        reset_btn = QPushButton("Reset Learned Model")
        reset_btn.clicked.connect(self._reset_smart)
        cl.addWidget(reset_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self.v.addWidget(card)

    def _reset_smart(self):
        confirm = QMessageBox.question(
            self, "Reset learning",
            "Forget everything Smart Suggestions has learned? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.win.suggester.reset()
        self.win.suggester.save()
        st = self.win.suggester.stats()
        self.smart_stats.setText(
            f"Signals learned: {st['updates']}  \u2022  Status: gathering data\n"
            "Learns which cleanup categories you keep vs. skip and pre-selects "
            "accordingly. 100% offline \u2014 no data ever leaves your PC."
        )

    def _build_safety_card(self):
        from cortex_unified.system_tools.restore_point import RestorePointManager

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        title = QLabel("System Safety \u2014 Restore Points")
        title.setObjectName("SectionTitle")
        cl.addWidget(title)

        mgr = RestorePointManager()
        if not mgr.is_supported():
            note = QLabel("\u2139  System Restore points are a Windows-only feature.")
            note.setObjectName("Muted")
            note.setWordWrap(True)
            cl.addWidget(note)
            self.v.addWidget(card)
            return

        desc = QLabel(
            "Create a Windows restore point before making risky changes "
            "(registry, telemetry, uninstalls). Requires Administrator; if System "
            "Protection is off, you'll be told honestly rather than given a false confirmation."
        )
        desc.setObjectName("Muted")
        desc.setWordWrap(True)
        cl.addWidget(desc)

        elev = "\u2705 Administrator" if mgr.is_elevated() else "\u26A0 Not elevated (needed to create points)"
        self.rp_status = QLabel(f"Status: {elev}")
        cl.addWidget(self.rp_status)

        row = QHBoxLayout()
        self.rp_create_btn = QPushButton("Create Restore Point Now")
        self.rp_create_btn.setObjectName("Primary")
        self.rp_create_btn.clicked.connect(self._create_restore_point)
        row.addWidget(self.rp_create_btn)
        self.rp_refresh_btn = QPushButton("Refresh List")
        self.rp_refresh_btn.clicked.connect(self._refresh_restore_points)
        row.addWidget(self.rp_refresh_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.rp_progress = QProgressBar()
        self.rp_progress.setRange(0, 0)
        self.rp_progress.setVisible(False)
        cl.addWidget(self.rp_progress)

        self.rp_table = QTableWidget(0, 3)
        self.rp_table.setHorizontalHeaderLabels(["Description", "Created", "Type"])
        self.rp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.rp_table.verticalHeader().setVisible(False)
        self.rp_table.setMaximumHeight(180)
        cl.addWidget(self.rp_table)

        self.v.addWidget(card)
        # Load the (PowerShell-backed) restore-point list on first view via the
        # _autoload mechanism rather than eagerly in the constructor, so opening
        # the app never spawns a subprocess for a page the user hasn't visited
        # yet (Req 1.5). The list still loads off the UI thread on the
        # Worker_Runtime when Settings is first shown.
        self._autoload = self._refresh_restore_points
        self._loaded = False

    def _create_restore_point(self):
        from .workers import RestorePointWorker
        self.rp_create_btn.setEnabled(False)
        self.rp_progress.setVisible(True)
        self.win.statusBar().showMessage("Creating restore point\u2026")
        self.win.run_worker(RestorePointWorker("Cortex Cleaner - manual"),
                            self._on_rp_created, self._on_rp_fail)

    def _on_rp_created(self, status: str, message: str):
        self.rp_progress.setVisible(False)
        self.rp_create_btn.setEnabled(True)
        if status == "created":
            QMessageBox.information(self, "Restore point", message)
        elif status == "throttled":
            QMessageBox.information(self, "Restore point", message)
        elif status == "protection_disabled":
            QMessageBox.warning(self, "System Protection is off", message)
        elif status == "not_elevated":
            QMessageBox.warning(self, "Administrator required", message)
        else:
            QMessageBox.warning(self, "Restore point", message or "Could not create a restore point.")
        self.win.statusBar().showMessage(f"Restore point: {status}", 6000)
        self._refresh_restore_points()

    def _on_rp_fail(self, msg: str):
        self.rp_progress.setVisible(False)
        self.rp_create_btn.setEnabled(True)
        self.win._default_fail(msg)

    def _refresh_restore_points(self):
        from .workers import RestorePointListWorker
        self.win.run_worker(RestorePointListWorker(), self._on_rp_listed, self._on_rp_fail)

    def _on_rp_listed(self, points: list):
        self.rp_table.setRowCount(len(points))
        for r, p in enumerate(points):
            self.rp_table.setItem(r, 0, QTableWidgetItem(str(p.get("description", ""))))
            self.rp_table.setItem(r, 1, QTableWidgetItem(str(p.get("created", ""))))
            self.rp_table.setItem(r, 2, QTableWidgetItem(str(p.get("type", ""))))
