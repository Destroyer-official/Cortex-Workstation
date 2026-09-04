"""The premium main window: sidebar navigation + engine-backed pages."""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    QRunnable,
    QSize,
    QThreadPool,
    QTimer,
    Qt,
    QThread,
    Signal,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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

from cortex_unified.licensing import Feature
from . import icons, motion, registry
from .smoothscroll import install_smooth_scroll
from .theme import THEMES, Palette, apply_theme
from .widgets import (
    Badge,
    Card,
    CircularGauge,
    StatCard,
    hline,
    require_feature,
    status_note,
    title_block,
)

_LOG = logging.getLogger("cortex.ui.premium")


def fmt_bytes(n: int) -> str:
    """Format a byte count with the largest fitting binary unit.

    Converts raw numeric values into formatted, localized, and human-readable string representations.

    Args:
        n (int): The n parameter.

    Returns:
        str: Formatted string or path.
    """
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if size < 1024 or unit == "PB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


# Navigation is *derived* from the single declarative registry in
# ``registry.py`` - see that module to add or reorder a tool. These aliases
# exist only so long-standing call sites and tests keep working; nothing here
# is a second source of truth.
#
#: ``[(page_id, label, icon)]`` in sidebar order.
_NAV = [(spec.id, spec.title, spec.icon) for spec in registry.ordered_specs()]

#: ``[(group_id, group_title, (page_id, ...))]`` in sidebar order.
_NAV_GROUPS = tuple(
    (group.id, group.title, tuple(spec.id for spec in specs))
    for group, specs in registry.grouped()
)


#: Logical size of a sidebar icon, in device-independent pixels.
_NAV_ICON_PX = 17

#: Title-bar brand mark and window-control icon sizes.
_TITLE_GLYPH_PX = 19
_WIN_BTN_PX = 13

#: Sidebar brand mark size.
_BRAND_MARK_PX = 20

#: Backwards-compatible view of the registry: ``page_id -> (class, module)``.
#: Derived, never maintained by hand.
_PAGE_FACTORIES: dict[str, tuple[str, str]] = {
    spec.id: (spec.factory.split(":")[1], spec.factory.split(":")[0])
    for spec in registry.PAGES
}


class _TitleBarChrome:
    """Read-only handle to the window's chrome: brand mark + window controls.

    The individual widgets live on the window (``_brand_mark``,
    ``_min_btn``, ...) because the title-bar row is wired up inline during
    construction; this small namespace exposes them under the conventional
    ``_brand``/``_min``/``_max``/``_close`` names so chrome code and tests
    don't reach into the concrete attributes.
    """

    __slots__ = ("_brand", "_min", "_max", "_close")

    def __init__(self, brand, min_btn, max_btn, close_btn):
        """Store the brand mark and the three window-control buttons.

        Initializes the instance and configures internal state.

        Args:
            brand: The brand parameter.
            min_btn: The min btn parameter.
            max_btn: The max btn parameter.
            close_btn: The close btn parameter.
        """
        self._brand = brand
        self._min = min_btn
        self._max = max_btn
        self._close = close_btn


class _LazyPageRegistry(Mapping):
    """A ``dict[str, QWidget]``-compatible view that builds pages on demand.

    Reads like the eager dictionary it replaced - ``len()``, iteration,
    ``in``, and ``registry["dashboard"]`` all behave identically and report all
    43 pages - but a page widget is only constructed the first time it is
    actually requested, and is then cached and added to the window's
    ``QStackedWidget``.

    This keeps every existing call site and test working (``set(win._pages)``,
    ``win._pages["dashboard"]``) while removing ~2.6 s from window startup.
    """

    def __init__(self, win: "PremiumMainWindow") -> None:
        """Keep the owning window and the cache of already-built pages.

        Initializes the instance and configures internal state.

        Args:
            win ('PremiumMainWindow'): Parent window or shell controller instance.
        """
        self._win = win
        self._built: dict[str, QWidget] = {}

    # -- Mapping protocol ---------------------------------------------------

    def __getitem__(self, page_id: str) -> QWidget:
        """Getitem.

        Manages getitem operations and coordinates related state changes for the component.

        Args:
            page_id (str): The page id parameter.

        Returns:
            QWidget: Result of the operation.
        """
        page = self._built.get(page_id)
        if page is not None:
            return page
        try:
            spec = registry.BY_ID[page_id]
        except KeyError:
            raise KeyError(page_id) from None
        _LOG.debug("constructing page %s (%s)", page_id, spec.factory)
        page = spec.load()(self._win)
        self._built[page_id] = page
        self._win._stack.addWidget(page)
        return page

    def __iter__(self):
        """Iter.

        Manages iter operations and coordinates related state changes for the component.
        """
        # Navigation order, so iteration matches what the user sees.
        return iter(registry.ordered_ids())

    def __len__(self) -> int:
        """Len.

        Manages len operations and coordinates related state changes for the component.

        Returns:
            int: Result of the operation.
        """
        return len(registry.PAGES)

    def __contains__(self, page_id: object) -> bool:
        """Contains.

        Manages contains operations and coordinates related state changes for the component.

        Args:
            page_id (object): The page id parameter.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return page_id in registry.BY_ID

    # -- introspection ------------------------------------------------------

    def is_built(self, page_id: str) -> bool:
        """True when *page_id* has actually been constructed.

        Manages is built operations and coordinates related state changes for the component.

        Args:
            page_id (str): The page id parameter.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return page_id in self._built

    @property
    def built_ids(self) -> frozenset[str]:
        """The pages constructed so far - useful for tests and diagnostics.

        Manages built ids operations and coordinates related state changes for the component.

        Returns:
            frozenset[str]: Formatted string or path.
        """
        return frozenset(self._built)




class _WorkerTaskSignals(QObject):
    """Workertasksignals.

    Manages WorkerTaskSignals operations and coordinates related state changes for the component.
    """
    finished = Signal(object)
    failed = Signal(object)


class _WorkerTaskRunnable(QRunnable):
    """Workertaskrunnable.

    Manages WorkerTaskRunnable operations and coordinates related state changes for the component.
    """
    def __init__(self, work_fn, signals: _WorkerTaskSignals):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            work_fn: The work fn parameter.
            signals (_WorkerTaskSignals): The signals parameter.
        """
        super().__init__()
        self.work_fn = work_fn
        self.signals = signals

    def run(self):
        """Run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            res = self.work_fn()
            self.signals.finished.emit(res)
        except Exception as exc:
            self.signals.failed.emit(exc)


class WorkerRuntime(QObject):
    """Workerruntime.

    Manages WorkerRuntime operations and coordinates related state changes for the component.
    """

    def __init__(self, parent=None):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()

    def run(self, work_fn, on_result=None, on_error=None):
        """Execute work_fn off the UI thread and dispatch results/errors via Qt signals.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.

        Args:
            work_fn: The work fn parameter.
            on_result: The on result parameter.
            on_error: Error message string or exception instance.
        """
        signals = _WorkerTaskSignals(self)
        if on_result:
            signals.finished.connect(on_result)
        if on_error:
            signals.failed.connect(on_error)
        runnable = _WorkerTaskRunnable(work_fn, signals)
        self._pool.start(runnable)


class PremiumMainWindow(QMainWindow):
    """Premiummainwindow.

    Manages PremiumMainWindow operations and coordinates related state changes for the component.
    """

    def __init__(self, theme: str = "dark", settings=None):
        """Build the frameless shell: sidebar, title bar, page stack, tray, and lazy page registry.

        Initializes the instance and configures internal state.

        Args:
            theme (str): The theme parameter.
            settings: The settings parameter.
        """
        super().__init__()
        self.worker_runtime = WorkerRuntime(self)
        # Durable user preferences (theme, close-to-tray). The store is shared
        # with the entry point when provided so both read/write one file; a
        # standalone construction (tests) gets its own default-backed store.
        from .settings_store import SettingsStore
        self.settings = settings if settings is not None else SettingsStore()
        # Apps recently uninstalled on the Deep Uninstaller page, awaiting a
        # leftover scan on the Leftover Scanner page (cross-page handoff).
        self._pending_leftover_apps: list[dict] = []
        self.theme_name = theme
        self.palette_tokens: Palette = THEMES[theme]
        self._threads: list[QThread] = []
        self._closing = False              # set in closeEvent; blocks new workers
        self._force_quit = False           # set by the tray's Exit action
        self._tray = None                  # PremiumTray, created after pages
        self._tray_hint_shown = False      # one-time "still running in tray" hint
        #: Threads that ignored every shutdown attempt. Detached from the
        #: window (so Qt teardown can never destroy a live QThread) and kept
        #: referenced here; the app entry point reads this to decide whether a
        #: hard exit is needed (see app.main / _shutdown_workers).
        self._workers_stuck: list[QThread] = []

        self.setWindowTitle("Cortex Workstation")
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
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._sidebar = self._build_sidebar()
        outer.addWidget(self._sidebar)

        right_col = QWidget()
        right_lay = QVBoxLayout(right_col)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        # Thin title bar at top with tab area and window controls on the right
        title_row = QWidget()
        title_row.setFixedHeight(36)
        title_row.setObjectName("TitleBar")
        title_lay = QHBoxLayout(title_row)
        title_lay.setContentsMargins(4, 0, 4, 0)
        title_lay.setSpacing(4)

        # Tab bar host container (for Nexus File Manager tabs aligned with window buttons)
        self._titlebar_tab_area = QWidget()
        self._titlebar_tab_area.setObjectName("TitleBarTabArea")
        self._titlebar_tab_layout = QHBoxLayout(self._titlebar_tab_area)
        self._titlebar_tab_layout.setContentsMargins(0, 0, 0, 0)
        self._titlebar_tab_layout.setSpacing(4)
        title_lay.addWidget(self._titlebar_tab_area)
        self._titlebar_tab_area.hide()

        title_lay.addStretch(1)

        muted = self.palette_tokens.text_muted
        self._min_btn = QPushButton()
        self._max_btn = QPushButton()
        self._close_btn = QPushButton()
        for b in (self._min_btn, self._max_btn):
            b.setObjectName("WinBtn")
        self._close_btn.setObjectName("CloseBtn")
        for b, name in ((self._min_btn, "win-minimize"),
                        (self._max_btn, "win-maximize"),
                        (self._close_btn, "win-close")):
            b.setIcon(icons.icon(name, _WIN_BTN_PX, muted))
            b.setIconSize(icons.icon_size(_WIN_BTN_PX))
            b.setFixedSize(36, 28)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            title_lay.addWidget(b)
        self._min_btn.setAccessibleName("Minimize")
        self._max_btn.setAccessibleName("Maximize")
        self._close_btn.setAccessibleName("Close")
        self._min_btn.clicked.connect(self.showMinimized)
        self._max_btn.clicked.connect(self._toggle_max)
        self._close_btn.clicked.connect(self.close)

        # Expose the window-control buttons + brand under the conventional
        # ``_titlebar`` names for chrome code and accessibility tests.
        self._titlebar = _TitleBarChrome(
            self._brand_mark, self._min_btn, self._max_btn, self._close_btn)

        right_lay.addWidget(title_row)

        self._stack = QStackedWidget()
        content_wrap = QWidget()
        content_wrap.setObjectName("ContentArea")
        cw = QVBoxLayout(content_wrap)
        cw.setContentsMargins(20, 8, 20, 16)
        cw.addWidget(self._stack)
        self._content_layout = cw
        right_lay.addWidget(content_wrap, 1)

        outer.addWidget(right_col, 1)
        self.setCentralWidget(central)

        if self._frameless:
            QApplication.instance().installEventFilter(self)

        # Pages are built on first view, not up front. Constructing all 43
        # eagerly cost ~2.6 s before the window could appear, even though a
        # session typically touches a handful of tools. ``_pages`` still behaves
        # like the old ``dict[str, QWidget]`` (see :class:`_LazyPageRegistry`).
        self._pages = _LazyPageRegistry(self)

        self.statusBar().showMessage("Ready")
        self._select(registry.DEFAULT_PAGE_ID)

        # Ctrl+H toggle sidebar
        from PySide6.QtGui import QShortcut, QKeySequence
        self._sidebar_shortcut = QShortcut(QKeySequence("Ctrl+H"), self)
        self._sidebar_shortcut.activated.connect(self._toggle_sidebar)

        # Collapse sidebar by default for full-screen file manager experience
        self._toggle_sidebar()
        self._menu_btn.setToolTip("Expand sidebar (Ctrl+H)")

        # System-tray presence + background resource monitor. Created last so
        # it can reference the fully-built pages/palette; availability-gated so
        # it is inert on headless/offscreen hosts and never affects startup.
        from .tray import PremiumTray
        self._tray = PremiumTray(self, self.settings)

    # -- sidebar ------------------------------------------------------------

    def _build_sidebar(self) -> QWidget:
        """Build the sidebar: brand, search box, grouped nav buttons, and status labels.

        Manages build sidebar operations and coordinates related state changes for the component.

        Returns:
            QWidget: Result of the operation.
        """
        bar = QWidget()
        bar.setObjectName("Sidebar")
        bar.setMinimumWidth(60)
        bar.setMaximumWidth(220)
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(10, 4, 10, 10)
        lay.setSpacing(4)

        # Top row: hamburger + window controls
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(2)

        self._menu_btn = QPushButton()
        self._menu_btn.setObjectName("MenuBtn")
        self._menu_btn.setFixedSize(24, 24)
        self._menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._menu_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Real SVG rather than the U+2630 hamburger: Qt 6 ships no fonts, so a
        # codepoint glyph would fall through to system font fallback.
        self._menu_btn.setIcon(icons.icon("menu", _NAV_ICON_PX, self.palette_tokens.text_muted))
        self._menu_btn.setIconSize(icons.icon_size(_NAV_ICON_PX))
        self._menu_btn.setToolTip("Collapse sidebar (Ctrl+H)")
        self._menu_btn.setAccessibleName("Toggle sidebar")
        self._menu_btn.clicked.connect(self._toggle_sidebar)
        top_row.addWidget(self._menu_btn)

        lay.addLayout(top_row)
        lay.addSpacing(2)

        # SVG mark + wordmark, not a codepoint prefix: U+25C8 rendered at a
        # different weight and baseline depending on the system fallback font.
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(9)
        self._brand_mark = QLabel()
        self._brand_mark.setPixmap(
            icons.pixmap("brand", _BRAND_MARK_PX, self.palette_tokens.accent))
        self._brand_mark.setFixedSize(icons.icon_size(_BRAND_MARK_PX))
        brand_row.addWidget(self._brand_mark, 0, Qt.AlignmentFlag.AlignVCenter)
        brand = QLabel("CORTEX")
        brand.setObjectName("Brand")
        brand_row.addWidget(brand, 1, Qt.AlignmentFlag.AlignVCenter)
        lay.addLayout(brand_row)
        sub = QLabel("SYSTEM CARE // CONSOLE")
        sub.setObjectName("BrandSub")
        lay.addWidget(sub)
        lay.addSpacing(4)

        self._nav_search = QLineEdit()
        self._nav_search.setObjectName("NavSearch")
        self._nav_search.setPlaceholderText("Find a tool\u2026")
        self._nav_search.setClearButtonEnabled(True)
        self._nav_search.setAccessibleName("Search Cortex tools")
        lay.addWidget(self._nav_search)
        lay.addSpacing(2)

        # One scroll container owns the hierarchical navigation. Sections use
        # real focusable buttons so mouse, keyboard, and assistive technology
        # all receive the same disclosure behavior.
        nav_scroll = QScrollArea()
        nav_scroll.setObjectName("NavScroll")
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav_holder = QWidget()
        nav_holder.setObjectName("NavHolder")
        nav_lay = QVBoxLayout(nav_holder)
        nav_lay.setContentsMargins(0, 0, 0, 0)
        nav_lay.setSpacing(3)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        self._nav_sections: dict[str, dict] = {}
        self._nav_sections_by_page: dict[str, str] = {}
        self._nav_buttons_by_page: dict[str, QPushButton] = {}

        # Built straight from the declarative registry: the sidebar cannot
        # disagree with the page stack, because both read the same source.
        for group, specs in registry.grouped():
            group_id, title = group.id, group.title
            header = QPushButton()
            header.setObjectName("NavGroupHeader")
            header.setCheckable(True)
            header.setChecked(group_id == registry.group_of(
                registry.DEFAULT_PAGE_ID))
            header.setCursor(Qt.CursorShape.PointingHandCursor)
            header.setAccessibleName(f"{title} navigation group")
            header.setToolTip(f"Show or hide {title} tools")
            header._group_title = title  # type: ignore[attr-defined]

            body = QWidget()
            body.setObjectName("NavGroupBody")
            body_lay = QVBoxLayout(body)
            body_lay.setContentsMargins(8, 0, 0, 3)
            body_lay.setSpacing(2)

            section = {
                "title": title,
                "header": header,
                "body": body,
                "pages": tuple(spec.id for spec in specs),
            }
            self._nav_sections[group_id] = section
            nav_lay.addWidget(header)
            nav_lay.addWidget(body)

            for spec in specs:
                button = QPushButton(f"  {spec.title}")
                button.setObjectName("NavItem")
                button.setCheckable(True)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setAccessibleName(spec.title)
                button.setToolTip(f"Open {spec.title}")
                # Real SVG, rasterised at the screen's device pixel ratio, so
                # it stays sharp at 125%/150% scaling instead of relying on
                # system font fallback for a Unicode glyph.
                button.setIcon(icons.icon(
                    spec.icon, _NAV_ICON_PX, self.palette_tokens.text_muted))
                button.setIconSize(icons.icon_size(_NAV_ICON_PX))
                button.clicked.connect(
                    lambda _checked=False, pid=spec.id: self._select(pid))
                button._page_id = spec.id  # type: ignore[attr-defined]
                button._nav_label = spec.title  # type: ignore[attr-defined]
                self._nav_group.addButton(button)
                self._nav_buttons_by_page[spec.id] = button
                self._nav_sections_by_page[spec.id] = group_id
                body_lay.addWidget(button)

            expanded = header.isChecked()
            body.setVisible(expanded)
            self._update_nav_header(group_id, expanded)
            header.toggled.connect(
                lambda open_, gid=group_id: self._set_nav_section(
                    gid, open_))

        self._nav_empty = QLabel("NO TOOLS MATCH")
        self._nav_empty.setObjectName("NavEmpty")
        self._nav_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._nav_empty.setVisible(False)
        nav_lay.addWidget(self._nav_empty)
        nav_lay.addStretch(1)
        nav_scroll.setWidget(nav_holder)
        install_smooth_scroll(nav_scroll)
        lay.addWidget(nav_scroll, 1)

        self._nav_search.textChanged.connect(self._filter_navigation)

        signal = QLabel("\u25CF  SYSTEM READY")
        signal.setObjectName("SidebarStatus")
        version = QLabel("CORE v2.1  //  LOCAL ENGINE")
        version.setObjectName("SidebarVersion")
        lay.addWidget(signal)
        lay.addWidget(version)

        # Store refs for collapse toggle
        self._sidebar_brand_row = brand_row
        self._sidebar_brand_label = brand
        self._sidebar_sub = sub
        self._sidebar_search = self._nav_search
        self._sidebar_signal = signal
        self._sidebar_version = version
        self._sidebar_nav_scroll = nav_scroll
        self._sidebar_expanded = True
        self._sidebar_pinned = True  # pinned = stays open
        self._sidebar_hover_expanded = False  # temporary hover expand
        self._sidebar_collapsed_width = 60
        self._sidebar_expanded_width = 220
        self._sidebar_anim = None
        self._sidebar_anim2 = None
        self._sidebar_leave_timer = QTimer(self)
        self._sidebar_leave_timer.setSingleShot(True)
        self._sidebar_leave_timer.setInterval(350)
        self._sidebar_leave_timer.timeout.connect(self._sidebar_hover_collapse)

        # Install event filter for hover detection
        bar.installEventFilter(self)

        return bar

    def eventFilter(self, obj, event):
        """Filter monitored Qt events for target child widgets.

        Intercepts specific mouse, keyboard, or focus events to provide custom interactive behaviors before standard event dispatch.

        Args:
            obj: The obj parameter.
            event: The Qt event object.
        """
        if obj is self._sidebar and not self._sidebar_pinned and not self._sidebar_expanded:
            if event.type() == QEvent.Type.Enter:
                self._sidebar_leave_timer.stop()
                if not self._sidebar_hover_expanded:
                    self._sidebar_hover_expand()
            elif event.type() == QEvent.Type.Leave:
                self._sidebar_leave_timer.start()
        return super().eventFilter(obj, event)

    def _sidebar_hover_expand(self) -> None:
        """Temporarily expand sidebar on hover (when collapsed & not pinned).

        Manages sidebar hover expand operations and coordinates related state changes for the component.
        """
        self._sidebar_hover_expanded = True
        bar = self._sidebar

        # Show content immediately for smooth feel
        self._sidebar_brand_label.show()
        self._sidebar_sub.show()
        self._sidebar_search.show()
        self._sidebar_signal.show()
        self._sidebar_version.show()
        for btn in self._nav_buttons_by_page.values():
            btn.setText(f"  {getattr(btn, '_nav_label', '')}")
            btn.setProperty("collapsed", False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        for gid, sec in self._nav_sections.items():
            sec["header"].setProperty("collapsed", False)
            self._update_nav_header(gid, sec["header"].isChecked())

        # Animate expand
        self._stop_sidebar_anim()
        w = bar.width()
        self._sidebar_anim = QPropertyAnimation(bar, b"minimumWidth", bar)
        self._sidebar_anim.setDuration(180)
        self._sidebar_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._sidebar_anim.setStartValue(w)
        self._sidebar_anim.setEndValue(self._sidebar_expanded_width)
        self._sidebar_anim2 = QPropertyAnimation(bar, b"maximumWidth", bar)
        self._sidebar_anim2.setDuration(180)
        self._sidebar_anim2.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._sidebar_anim2.setStartValue(w)
        self._sidebar_anim2.setEndValue(self._sidebar_expanded_width)
        self._sidebar_anim.start()
        self._sidebar_anim2.start()

    def _sidebar_hover_collapse(self) -> None:
        """Collapse sidebar after mouse leaves (when not pinned).

        Manages sidebar hover collapse operations and coordinates related state changes for the component.
        """
        if self._sidebar_pinned or self._sidebar_expanded:
            self._sidebar_hover_expanded = False
            return
        self._sidebar_hover_expanded = False
        self._collapse_sidebar_content()

        # Animate collapse
        bar = self._sidebar
        self._stop_sidebar_anim()
        w = bar.width()
        self._sidebar_anim = QPropertyAnimation(bar, b"minimumWidth", bar)
        self._sidebar_anim.setDuration(200)
        self._sidebar_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._sidebar_anim.setStartValue(w)
        self._sidebar_anim.setEndValue(self._sidebar_collapsed_width)
        self._sidebar_anim2 = QPropertyAnimation(bar, b"maximumWidth", bar)
        self._sidebar_anim2.setDuration(200)
        self._sidebar_anim2.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._sidebar_anim2.setStartValue(w)
        self._sidebar_anim2.setEndValue(self._sidebar_collapsed_width)
        self._sidebar_anim.start()
        self._sidebar_anim2.start()

    def _stop_sidebar_anim(self) -> None:
        """Stop any running sidebar animations.

        Manages stop sidebar anim operations and coordinates related state changes for the component.
        """
        for attr in ('_sidebar_anim', '_sidebar_anim2'):
            anim = getattr(self, attr, None)
            if anim is not None:
                anim.stop()

    def _toggle_max(self):
        """Switch between maximized and normal, updating the title-bar icon.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        muted = self.palette_tokens.text_muted
        if self.isMaximized():
            self.showNormal()
            self._max_btn.setIcon(icons.icon("win-maximize", _WIN_BTN_PX, muted))
            self._max_btn.setAccessibleName("Maximize")
        else:
            self.showMaximized()
            self._max_btn.setIcon(icons.icon("win-restore", _WIN_BTN_PX, muted))
            self._max_btn.setAccessibleName("Restore")

    def _toggle_sidebar(self) -> None:
        """Toggle sidebar pin: pinned = always expanded, unpinned = collapsed + hover-expand.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        if self._sidebar_expanded and self._sidebar_pinned:
            # Unpin and collapse
            self._sidebar_pinned = False
            self._sidebar_expanded = False
            self._collapse_sidebar_content()
            bar = self._sidebar
            self._stop_sidebar_anim()
            w = bar.width()
            self._sidebar_anim = QPropertyAnimation(bar, b"minimumWidth", bar)
            self._sidebar_anim.setDuration(220)
            self._sidebar_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self._sidebar_anim.setStartValue(w)
            self._sidebar_anim.setEndValue(self._sidebar_collapsed_width)
            self._sidebar_anim2 = QPropertyAnimation(bar, b"maximumWidth", bar)
            self._sidebar_anim2.setDuration(220)
            self._sidebar_anim2.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self._sidebar_anim2.setStartValue(w)
            self._sidebar_anim2.setEndValue(self._sidebar_collapsed_width)
            self._sidebar_anim.start()
            self._sidebar_anim2.start()
            self._menu_btn.setToolTip("Expand sidebar (Ctrl+H)")
        else:
            # Pin and expand
            self._sidebar_pinned = True
            self._sidebar_expanded = True
            self._sidebar_hover_expanded = False
            self._sidebar_leave_timer.stop()
            bar = self._sidebar

            # Show content
            self._sidebar_brand_label.show()
            self._sidebar_sub.show()
            self._sidebar_search.show()
            self._sidebar_signal.show()
            self._sidebar_version.show()
            self._sidebar_nav_scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            for btn in self._nav_buttons_by_page.values():
                btn.setText(f"  {getattr(btn, '_nav_label', '')}")
                btn.setToolTip("")
                btn.setProperty("collapsed", False)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            for gid, sec in self._nav_sections.items():
                sec["header"].setProperty("collapsed", False)
                self._update_nav_header(gid, sec["header"].isChecked())

            # Animate expand
            self._stop_sidebar_anim()
            w = bar.width()
            self._sidebar_anim = QPropertyAnimation(bar, b"minimumWidth", bar)
            self._sidebar_anim.setDuration(220)
            self._sidebar_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self._sidebar_anim.setStartValue(w)
            self._sidebar_anim.setEndValue(self._sidebar_expanded_width)
            self._sidebar_anim2 = QPropertyAnimation(bar, b"maximumWidth", bar)
            self._sidebar_anim2.setDuration(220)
            self._sidebar_anim2.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self._sidebar_anim2.setStartValue(w)
            self._sidebar_anim2.setEndValue(self._sidebar_expanded_width)
            self._sidebar_anim.start()
            self._sidebar_anim2.start()
            self._menu_btn.setToolTip("Collapse sidebar (Ctrl+H)")

    def _collapse_sidebar_content(self) -> None:
        """Hide sidebar text content after collapse animation.

        Manages collapse sidebar content operations and coordinates related state changes for the component.
        """
        if self._sidebar_expanded:
            return  # User expanded during animation
        self._sidebar_brand_label.hide()
        self._sidebar_sub.hide()
        self._sidebar_search.hide()
        self._sidebar_signal.hide()
        self._sidebar_version.hide()
        self._sidebar_nav_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Keep the icon-plus-title text so the button stays label-addressable,
        # but mark it collapsed so the stylesheet hides the text (font-size: 0)
        # while the sidebar shrinks to icon-width.
        for page_id, btn in self._nav_buttons_by_page.items():
            btn.setText(f"  {getattr(btn, '_nav_label', '')}")
            btn.setToolTip(getattr(btn, '_nav_label', ''))
            btn.setProperty("collapsed", True)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Collapse all sections and set collapsed property on headers
        for sec in self._nav_sections.values():
            sec["header"].setIcon(icons.icon("chevron-right", 12, self.palette_tokens.text_muted))
            sec["header"].setIconSize(icons.icon_size(12))
            sec["header"].setText("")
            sec["header"].setProperty("collapsed", True)
            sec["header"].style().unpolish(sec["header"])
            sec["header"].style().polish(sec["header"])
            body = sec["body"]
            if body.isVisible():
                body.setVisible(False)

    def _retint_nav_icons(self) -> None:
        """Re-render sidebar icons for the active palette.

        Icons are tinted at rasterisation time, so a theme switch has to
        rebuild them - otherwise dark-theme strokes would persist on the light
        palette. The pixmap cache is dropped first so stale colours cannot be
        served back.
        """
        icons.clear_cache()
        color = self.palette_tokens.text_muted
        for page_id, button in getattr(self, "_nav_buttons_by_page", {}).items():
            spec = registry.BY_ID.get(page_id)
            if spec is None:
                continue
            button.setIcon(icons.icon(spec.icon, _NAV_ICON_PX, color))
        mark = getattr(self, "_brand_mark", None)
        if mark is not None:
            mark.setPixmap(icons.pixmap(
                "brand", _BRAND_MARK_PX, self.palette_tokens.accent))
        muted = self.palette_tokens.text_muted
        if hasattr(self, '_min_btn'):
            for b, name in ((self._min_btn, "win-minimize"),
                            (self._max_btn, "win-maximize" if not self.isMaximized() else "win-restore"),
                            (self._close_btn, "win-close")):
                b.setIcon(icons.icon(name, _WIN_BTN_PX, muted))
        for gid, sec in getattr(self, "_nav_sections", {}).items():
            self._update_nav_header(gid, sec["header"].isChecked())

    def _update_nav_header(self, group_id: str, expanded: bool) -> None:
        """Set a nav group header's chevron, escaped title, and expanded style.

        Manages update nav header operations and coordinates related state changes for the component.

        Args:
            group_id (str): The group id parameter.
            expanded (bool): The expanded parameter.
        """
        section = self._nav_sections[group_id]
        header = section["header"]
        icon_name = "chevron-down" if expanded else "chevron-right"
        chevron_color = self.palette_tokens.accent if expanded else self.palette_tokens.text_muted
        header.setIcon(icons.icon(icon_name, 12, chevron_color))
        header.setIconSize(icons.icon_size(12))
        # Escape '&' as '&&' so Qt does not treat it as an underscore accelerator mnemonic
        title_escaped = section["title"].replace("&", "&&").upper()
        header.setText(f"  {title_escaped}")
        header.setProperty("expanded", expanded)
        header.style().unpolish(header)
        header.style().polish(header)

    def _set_nav_section(self, group_id: str, expanded: bool) -> None:
        """Open one nav group exclusively (accordion) and show/hide its page buttons.

        Manages set nav section operations and coordinates related state changes for the component.

        Args:
            group_id (str): The group id parameter.
            expanded (bool): The expanded parameter.
        """
        section = self._nav_sections[group_id]
        searching = bool(self._nav_search.text().strip())
        if expanded and not searching:
            for other_id, other in self._nav_sections.items():
                if other_id == group_id or not other["header"].isChecked():
                    continue
                other["header"].blockSignals(True)
                other["header"].setChecked(False)
                other["header"].blockSignals(False)
                other["body"].setVisible(False)
                self._update_nav_header(other_id, False)
        section["body"].setVisible(expanded)
        self._update_nav_header(group_id, expanded)
        if searching:
            self._filter_navigation(self._nav_search.text())

    def _filter_navigation(self, text: str) -> None:
        """Show only nav buttons matching the search text, revealing their groups.

        Manages filter navigation operations and coordinates related state changes for the component.

        Args:
            text (str): Display text string.
        """
        query = text.strip().casefold()
        found_any = False
        for group_id, section in self._nav_sections.items():
            group_match = query in section["title"].casefold()
            matched = False
            for page_id in section["pages"]:
                button = self._nav_buttons_by_page[page_id]
                label = getattr(button, "_nav_label", "")
                visible = not query or group_match or query in label.casefold()
                button.setVisible(visible)
                matched = matched or visible
            section["header"].setVisible(not query or matched)
            section["body"].setVisible(
                matched if query else section["header"].isChecked())
            found_any = found_any or matched
        self._nav_empty.setVisible(bool(query) and not found_any)

    def set_titlebar_tab_widget(self, widget: QWidget | None) -> None:
        """Mount or unmount an external tab bar (e.g. NexusExplorer) in the top window title bar row.

        Manages set titlebar tab widget operations and coordinates related state changes for the component.

        Args:
            widget (QWidget | None): The widget parameter.
        """
        while self._titlebar_tab_layout.count():
            item = self._titlebar_tab_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        if widget is not None:
            self._titlebar_tab_layout.addWidget(widget)
            self._titlebar_tab_area.show()
        else:
            self._titlebar_tab_area.hide()

    def _select(self, page_id: str) -> None:
        """Select.

        Manages select operations and coordinates related state changes for the component.

        Args:
            page_id (str): The page id parameter.
        """
        if page_id not in self._nav_buttons_by_page:
            return
        self._current_page_id = page_id
        button = self._nav_buttons_by_page[page_id]
        if self._nav_search.text() and not button.isVisible():
            self._nav_search.clear()
        group_id = self._nav_sections_by_page[page_id]
        header = self._nav_sections[group_id]["header"]
        if not header.isChecked():
            header.setChecked(True)

        # Update titlebar tab visibility & content margins
        if page_id == "nexus":
            self._titlebar_tab_area.show()
            self._content_layout.setContentsMargins(0, 0, 0, 0)
        else:
            self._titlebar_tab_area.hide()
            w = self.width()
            side = 16 if w < 1040 else (28 if w < 1400 else 44)
            top = 14 if w < 1040 else (24 if w < 1400 else 30)
            bot = 12 if w < 1040 else (20 if w < 1400 else 24)
            self._content_layout.setContentsMargins(side, top, side, bot)

        # Pages are added to the stack as they are built, so stack indices no
        # longer match _NAV order; switch by widget identity instead.
        page = self._pages[page_id]
        self._stack.setCurrentWidget(page)
        button.setChecked(True)
        self._fade_in(self._stack.currentWidget())

        # Lazy-load a page only on its first visit, avoiding a startup burst of
        # workers for tools the user may never open.
        page = self._pages.get(page_id)
        autoload = getattr(page, "_autoload", None) if page is not None else None
        if callable(autoload) and not getattr(page, "_loaded", False):
            page._loaded = True
            autoload()

    def _fade_in(self, widget: QWidget | None) -> None:
        """Animated fade/rise when a page becomes visible.

        Delegates to the shared :func:`motion.reveal` so every page appearance
        uses one duration/easing language. The animation is stored in a single
        ``_page_anim`` reference: starting a new transition replaces any
        in-flight one, so at most one appearance animation runs per page
        transition. The opacity effect is removed once the animation finishes
        so it never interferes with drop-shadow effects on child cards.
        """
        if widget is None:
            return
        try:
            self._page_anim = motion.reveal(widget)  # fade + gentle rise; supersedes prior
        except Exception:  # noqa: BLE001 - animation is cosmetic, never fatal
            pass

    # -- worker lifecycle ---------------------------------------------------

    def run_worker(self, worker, on_done, on_fail=None, on_progress=None) -> None:
        """Move *worker* to a fresh QThread and wire signals safely.

        The result callbacks (``on_done``/``on_fail``/``on_progress``)
        must be bound methods of main-thread QObjects so Qt uses *queued*
        connections and they run on the GUI thread - never in the worker
        thread. Thread teardown is driven by ``QThread.finished`` (never by
        calling ``wait()`` from inside a worker-thread slot, which deadlocks).
        """
        wname = type(worker).__name__
        if self._closing:
            # The window is shutting down its threads; starting new work now
            # would outlive the shutdown sweep and crash process teardown.
            _LOG.warning("refusing to start worker %s: window is closing", wname)
            return
        _LOG.debug("starting worker: %s", wname)
        thread = QThread(self)
        thread.setObjectName(wname)
        worker.moveToThread(thread)
        # Keep a strong Python reference to the worker. PySide6 does not keep
        # worker objects alive via signal connections alone, so an inline
        # `run_worker(SomeWorker(), ...)` call would let the worker be
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
        """Remove and delete any finished worker threads (runs on GUI thread).

        Manages reap threads operations and coordinates related state changes for the component.
        """
        for t in list(self._threads):
            if t.isFinished():
                self._threads.remove(t)
                t.deleteLater()

    def _default_fail(self, msg: str) -> None:
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.statusBar().showMessage(f"Error: {msg}", 6000)
        QMessageBox.warning(self, "Operation failed", msg)

    def set_theme(self, theme: str) -> None:
        """Apply a theme app-wide, retint icons, persist the choice, and refresh the tray.

        Manages set theme operations and coordinates related state changes for the component.

        Args:
            theme (str): The theme parameter.
        """
        from PySide6.QtWidgets import QApplication
        self.theme_name = theme
        self.palette_tokens = THEMES[theme]
        apply_theme(QApplication.instance(), theme)
        self._retint_nav_icons()
        # Persist the choice so the next launch opens in the same theme, and
        # re-render the tray glyph to match the new palette.
        try:
            self.settings.theme = theme
        except Exception:  # noqa: BLE001 - a failed save must never break theming
            _LOG.debug("could not persist theme", exc_info=True)
        if self._tray is not None:
            self._tray.refresh_theme(self.palette_tokens)

    # -- frameless edge resize ---------------------------------------------

    def eventFilter(self, obj, event):  # noqa: N802
        """App-level filter that turns the 6px window edge into a resize grip.

        Uses the platform's native ``startSystemResize`` so resizing feels
        exactly like a normal window (with live preview + snap)."""
        try:
            if getattr(self, "_in_event_filter", False):
                return super().eventFilter(obj, event)
            if not self._frameless or self.isMaximized() or not self.isActiveWindow():
                return super().eventFilter(obj, event)
            self._in_event_filter = True
            try:
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
            finally:
                self._in_event_filter = False
            return super().eventFilter(obj, event)
        except KeyboardInterrupt:
            return False

    def _edge_at(self, gpos):
        """Return the window edges within the resize margin of a global position.

        Manages edge at operations and coordinates related state changes for the component.

        Args:
            gpos: The gpos parameter.
        """
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
        """Set the resize cursor matching the hovered window edges.

        Manages update edge cursor operations and coordinates related state changes for the component.

        Args:
            edges: The edges parameter.
        """
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
        if getattr(self, "_current_page_id", None) == "nexus":
            layout.setContentsMargins(0, 0, 0, 0)
            return
        w = self.width()
        if w < 1040:
            side, top, bot = 16, 14, 12
        elif w < 1400:
            side, top, bot = 28, 24, 20
        else:
            side, top, bot = 44, 30, 24
        layout.setContentsMargins(side, top, side, bot)

    def mousePressEvent(self, event):  # noqa: N802
        """Handle mouse mousePress interaction events.

        Tracks cursor coordinates, button states, drag-and-drop actions, or item selection changes within the widget.

        Args:
            event: The Qt event object.
        """
        if event.button() == Qt.MouseButton.LeftButton and self._frameless and not self.isMaximized():
            if event.position().y() <= 40:
                handle = self.windowHandle()
                if handle is not None:
                    handle.startSystemMove()
                    return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        """Mousedoubleclickevent.

        Manages mouseDoubleClickEvent operations and coordinates related state changes for the component.

        Args:
            event: The Qt event object.
        """
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 40:
            self._toggle_max()
            return
        super().mouseDoubleClickEvent(event)

    # Grace period (seconds) for workers to stop cooperatively on close. A
    # worker that ignores this is detached (never force-killed - see
    # _shutdown_workers for why). Generous enough for in-flight scans/cleans to
    # honour their cancel event, bounded so the app always exits promptly.
    _CLOSE_GRACE_S = 8.0

    def closeEvent(self, event):  # noqa: N802
        """Handle the window or widget close event.

        Performs graceful shutdown, releases active workers and system hooks, persists window geometry, and accepts the close event.

        Args:
            event: The Qt event object.
        """
        # Close-to-tray: when enabled and a tray is available, a window close
        # (the X button) hides to the tray instead of quitting - unless a real
        # quit was requested via the tray's Exit action (_force_quit). Workers
        # keep running untouched, so an in-flight scan/clean is never aborted.
        if (self.settings.close_to_tray and self._tray is not None
                and self._tray.available and not self._force_quit):
            event.ignore()
            self.hide()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self._tray.show_message(
                    "Cortex Cleaner is still running",
                    "Closed to the system tray. Right-click the tray icon to exit.",
                )
            return

        self._closing = True
        if self._frameless:
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)
        # Stop the tray's background monitor before tearing workers down so no
        # timer tick fires during shutdown.
        if self._tray is not None:
            self._tray.stop()
        self._shutdown_workers()
        super().closeEvent(event)

    def _shutdown_workers(self) -> None:
        """Stop every worker thread without ever destroying one mid-run.

        Destroying a ``QThread`` that is still running aborts the process
        (Qt fatal: "QThread: Destroyed while thread is still running" ->
        0xC0000409). ``QThread.terminate()`` (Windows' ``TerminateThread``) is
        not a safe alternative either: if it fires while the thread holds a
        CRT/heap lock - exactly what happens when a worker is blocked inside
        ``subprocess.communicate()`` reading a pipe, which most of this app's
        workers do for minutes at a time - that lock is never released, and any
        *other* thread that later needs it (even something as ordinary as
        ``malloc``) hangs forever. That is a corrupted-process bug, not a slow
        shutdown, and it can surface as an apparently unrelated hang much later
        in the process's life. So this method never calls ``terminate()``.

        The shutdown is staged instead:

        1. **Cancel** every worker cooperatively. Workers backed by an external
           tool (SFC, DISM, winget, diskpart...) route their
           ``threading.Event`` down to :mod:`core.proc`, which polls the event
           and kills the *process tree* - never the Python thread - so
           cancellation is both prompt and always safe to call.
        2. **Quit** all thread event loops, then wait on one shared deadline
           while pumping the GUI event loop - queued ``finished``/``failed``
           signals deliver, ``deleteLater`` teardown runs, and the window stays
           responsive instead of blocking per-thread.
        3. Anything STILL alive once the deadline passes (a worker with no
           cancellation hook, or a bug that never checks the event) is
           detached from the window and left running (recorded on
           ``_workers_stuck``): a ``QThread`` must never be destroyed while
           running, so the app entry point performs a hard ``os._exit`` for
           this path instead, which ends the process without ever calling a
           destructor on the dangling wrapper.
        """
        threads = list(self._threads)

        def _running(t: QThread) -> bool:
            """Running.

            Manages running operations and coordinates related state changes for the component.

            Args:
                t (QThread): The t parameter.

            Returns:
                bool: True if the operation succeeded, False otherwise.
            """
            # While we pump events below, finished threads are reaped
            # (deleteLater) and their wrappers become dangling; a deleted
            # QThread is finished by definition, so treat it as not running.
            try:
                return t.isRunning()
            except RuntimeError:
                return False

        for t in threads:
            worker = getattr(t, "_cortex_worker", None)
            if worker is not None and hasattr(worker, "cancel"):
                try:
                    worker.cancel()
                except Exception:  # noqa: BLE001 - cancel is best-effort
                    pass
        for t in threads:
            try:
                t.quit()
            except RuntimeError:  # noqa: BLE001 - already reaped; nothing to quit
                pass

        app = QApplication.instance()
        deadline = time.monotonic() + self._CLOSE_GRACE_S
        while time.monotonic() < deadline:
            if not any(_running(t) for t in threads):
                break
            if app is not None:
                # Deliver queued worker signals + deferred deletions so the
                # shutdown path makes progress instead of deadlocking.
                app.processEvents()
            time.sleep(0.02)

        self._workers_stuck = [t for t in threads if _running(t)]
        for t in self._workers_stuck:
            _LOG.error(
                "worker thread %r could not be stopped; detaching it so "
                "teardown never destroys a running thread", t.objectName())
            t.setParent(None)
            if t in self._threads:
                self._threads.remove(t)


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
        """Store the inner scrollable view and the outer page scroll area.

        Initializes the instance and configures internal state.

        Args:
            inner (QWidget): The inner parameter.
            outer (QScrollArea | None): The outer parameter.
            parent (QObject | None): Parent window or shell controller instance.
        """
        super().__init__(parent)
        self._inner = inner
        self._outer = outer

    def eventFilter(self, obj, event):  # noqa: N802
        """Filter monitored Qt events for target child widgets.

        Intercepts specific mouse, keyboard, or focus events to provide custom interactive behaviors before standard event dispatch.

        Args:
            obj: The obj parameter.
            event: The Qt event object.
        """
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
        """Set up the page: window/palette refs and an outer momentum-scrolling vertical layout.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
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
        # Momentum scrolling: the page glides on the mouse wheel instead of
        # jumping in coarse steps (touchpads stay native; suppressed when the
        # reduce-motion setting is on).
        install_smooth_scroll(self._scroll)
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
    """Dashboardpage.

    Manages DashboardPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win: PremiumMainWindow):
        """Build the hero gauge, metric tiles, category tree, and pinned Clean action.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self._report = None
        self._preview_targets: dict = {}
        self._preview_counter = 0
        self._excluded: dict[int, set[str]] = {}   # scan_idx -> excluded path prefixes
        self._updating = False                      # guard for programmatic check changes

        self.v.addWidget(title_block(
            "System Overview Dashboard",
            "One-click health analysis and safe storage reclamation across your entire PC.",
        ))

        # Hero: a modular bento grid - a tall gauge tile beside a cluster of
        # metric tiles, laid out with uniform gaps and rounded tiles.
        hero_grid = QGridLayout()
        hero_grid.setHorizontalSpacing(16)
        hero_grid.setVerticalSpacing(16)

        gauge_card = Card(self.p, "HeroCard")
        gauge_card.setMinimumWidth(248)
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
        # Smaller glow (radius 20, alpha 40) so the halo stays inside the
        # constrained gauge bounds and never clips into green lines at the top.
        attach_glow(self.gauge, self.p.accent, 20, 40)
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

        # Explains cloud-only files that were deliberately left out of the total,
        # so a large OneDrive folder not showing up reads as a decision rather
        # than a missed scan.
        self.cloud_note = QLabel("")
        self.cloud_note.setObjectName("Muted")
        self.cloud_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cloud_note.setWordWrap(True)
        self.cloud_note.setVisible(False)
        gc.addWidget(self.cloud_note)

        self._scan_worker = None
        self._scanning = False

        # Metric tiles, styled as interactive bento tiles (accent border on
        # hover) and set to expand so they fill the grid uniformly.
        self.card_space = StatCard(self.p, "Total reclaimable", "\u2014")
        self.card_files = StatCard(self.p, "Files found", "\u2014")
        self.card_cats = StatCard(self.p, "Categories", "\u2014")
        for c in (self.card_space, self.card_files, self.card_cats):
            c.setObjectName("BentoTile")
            c.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Bento arrangement: the gauge tile spans both rows on the left; two
        # metric tiles sit top-right; a wide tile spans the bottom-right.
        hero_grid.addWidget(gauge_card, 0, 0, 2, 1)
        hero_grid.addWidget(self.card_space, 0, 1)
        hero_grid.addWidget(self.card_files, 0, 2)
        hero_grid.addWidget(self.card_cats, 1, 1, 1, 2)
        hero_grid.setColumnStretch(1, 1)
        hero_grid.setColumnStretch(2, 1)
        self.v.addLayout(hero_grid)

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
        # ~5 visible category rows even when the outer page has to scroll; the
        # tree's own scrollbar takes the rest. Mirrors the minimum_height
        # passed to add_scrolling_list below.
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
        # Tactile press feedback (a subtle sink) on the hero actions.
        motion.press_feedback(self.scan_btn)
        motion.press_feedback(self.recycle_btn)

    # -- actions --
    def _toggle_scan(self):
        """Start or cancel the scan depending on current state.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        if self._scanning:
            self._cancel_scan()
        else:
            self._scan()

    def _scan(self):
        """Launch the ScanWorker and flip the hero into scanning UI.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
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
        """Cancel the running scan worker and show Cancelling state.

        Manages cancel scan operations and coordinates related state changes for the component.
        """
        if self._scan_worker is not None:
            self._scan_worker.cancel()
            self.scan_status.setText("Cancelling\u2026")
            self.scan_btn.setEnabled(False)

    def _on_progress(self, text: str):
        """Show live scan progress text in the status label.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            text (str): Display text string.
        """
        self.scan_status.setText(text)

    def _on_scanned(self, report):
        """Render the CleanupReport: metrics, auto-checked category tree, risk badges, gauge.

        Manages on scanned operations and coordinates related state changes for the component.

        Args:
            report: The generated report data object from the backend.
        """
        self._report = report
        self._scanning = False
        self._scan_worker = None
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan Now")
        note = getattr(report, "cloud_note", "")
        self.cloud_note.setText(note)
        self.cloud_note.setVisible(bool(note))
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
        """Sum of what's currently checked, respecting per-app/folder exclusions.

        Manages selected bytes operations and coordinates related state changes for the component.

        Returns:
            int: Result of the operation.
        """
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
        """Refresh the gauge + Clean button to show the live selected size.

        Manages update selection operations and coordinates related state changes for the component.
        """
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
        """Replace a node's placeholder with worker-computed children as checkable rows.

        Manages apply preview operations and coordinates related state changes for the component.

        Args:
            nid (int): The nid parameter.
            children (list): The children parameter.
        """
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
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        # Preview is non-critical; just log to the status bar.
        self.win.statusBar().showMessage(f"Preview failed: {msg}", 4000)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Track per-app / per-folder selection so cleaning respects it.

        Manages on item changed operations and coordinates related state changes for the component.

        Args:
            item (QTreeWidgetItem): The item parameter.
            column (int): The column parameter.
        """
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
        self._update_selection()

    def _set_subtree_check(self, item: QTreeWidgetItem, state) -> None:
        """Recursively apply a check state to a node's loaded checkable descendants.

        Manages set subtree check operations and coordinates related state changes for the component.

        Args:
            item (QTreeWidgetItem): The item parameter.
            state: The state parameter.
        """
        for i in range(item.childCount()):
            child = item.child(i)
            if child.text(0) == "Loading\u2026":
                continue
            if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                child.setCheckState(0, state)
            self._set_subtree_check(child, state)

    def _filtered_entries(self, scan, scan_idx: int):
        """Entries for *scan* minus any the user deselected in the preview.

        Manages filtered entries operations and coordinates related state changes for the component.

        Args:
            scan: The scan parameter.
            scan_idx (int): The scan idx parameter.
        """
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
        """Clean the checked (and not excluded) categories after a confirm dialog, via CleanWorker.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

        Args:
            method (str): The method parameter.
        """
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
        """Show live cleaning progress text.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            text (str): Display text string.
        """
        self.scan_status.setText(text)

    def _on_cleaned(self, freed: int, items: int, skipped: int):
        """Report freed space and skipped files, then rescan to refresh the report.

        Manages on cleaned operations and coordinates related state changes for the component.

        Args:
            freed (int): The freed parameter.
            items (int): Collection of items or entries to process.
            skipped (int): The skipped parameter.
        """
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
        """Reset the scan UI and surface the error via the window's default handler.

        Captures worker error messages, presents diagnostic feedback to the user, and resets interactive controls for retry.

        Args:
            msg (str): Informational or progress status message.
        """
        self._scanning = False
        self._scan_worker = None
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan Now")
        self.recycle_btn.setEnabled(True)
        self.win._default_fail(msg)


class _FolderScanPage(_Page):
    """Shared scaffold for pages that pick a folder and list results.

    Premium redesign: Card-wrapped picker, StatCard metrics, styled table,
    and a polished empty state.
    """

    title = ""
    subtitle = ""
    action_label = "Scan folder"

    def __init__(self, win: PremiumMainWindow):
        """Build the shared scaffold: picker card, metric strip, results table, and delete action row.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(self.title, self.subtitle))

        # ── folder picker card ────────────────────────────────────────────
        picker_card = Card(self.p, "Card")
        pc_lay = QVBoxLayout(picker_card)
        pc_lay.setContentsMargins(16, 12, 16, 12)
        pc_lay.setSpacing(10)

        picker_row = QHBoxLayout()
        picker_row.setSpacing(8)
        pick_btn = QPushButton("Choose Folder\u2026")
        pick_btn.setObjectName("Ghost")
        pick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pick_btn.clicked.connect(self._pick)
        self.path_label = QLabel("No folder selected")
        self.path_label.setObjectName("Muted")
        self.run_btn = QPushButton(self.action_label)
        self.run_btn.setObjectName("Primary")
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._toggle_run)
        picker_row.addWidget(pick_btn)
        picker_row.addWidget(self.path_label, 1)
        picker_row.addWidget(self.run_btn)
        pc_lay.addLayout(picker_row)

        # ── progress + status ─────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        pc_lay.addWidget(self.progress)
        self.scan_status = QLabel("")
        self.scan_status.setObjectName("Muted")
        pc_lay.addWidget(self.scan_status)

        self.v.addWidget(picker_card)

        self._worker = None
        self._running = False

        # ── metric strip ──────────────────────────────────────────────────
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(12)
        self.card_items = StatCard(self.p, "Items Found", "\u2014")
        self.card_items.setObjectName("BentoTile")
        self.card_items.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.card_items.setMinimumHeight(64)
        self.card_size = StatCard(self.p, "Total Size", "\u2014")
        self.card_size.setObjectName("BentoTile")
        self.card_size.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.card_size.setMinimumHeight(64)
        self.card_groups = StatCard(self.p, "Groups", "\u2014")
        self.card_groups.setObjectName("BentoTile")
        self.card_groups.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.card_groups.setMinimumHeight(64)
        metrics_row.addWidget(self.card_items)
        metrics_row.addWidget(self.card_size)
        metrics_row.addWidget(self.card_groups)
        self.v.addLayout(metrics_row)

        # ── results table (Card-wrapped) ──────────────────────────────────
        table_card = Card(self.p, "Card")
        tc_lay = QVBoxLayout(table_card)
        tc_lay.setContentsMargins(0, 0, 0, 0)
        tc_lay.setSpacing(0)

        # Subclasses assign self.results_table (path in column 0) here.
        self.results_table: QTableWidget | None = None
        self.result_area = self._build_results()
        if self.results_table is not None:
            self.results_table.setShowGrid(False)
            self.results_table.setAlternatingRowColors(True)
            self.results_table.verticalHeader().setVisible(False)
            self.results_table.setSelectionBehavior(
                QTableWidget.SelectionBehavior.SelectRows)
            self.results_table.setEditTriggers(
                QTableWidget.EditTrigger.NoEditTriggers)
            self.results_table.setSortingEnabled(True)
            header = self.results_table.horizontalHeader()
            header.setStretchLastSection(True)
            header.setDefaultAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        tc_lay.addWidget(self.result_area)
        self.v.addWidget(table_card, 1)

        # Shared "reclaim selected" action row.
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 8, 0, 0)
        self.hint = QLabel("Select rows, then move them to the Recycle Bin.")
        self.hint.setObjectName("Muted")
        action_row.addWidget(self.hint)
        action_row.addStretch(1)
        self.del_btn = QPushButton("Move Selected to Recycle Bin")
        self.del_btn.setObjectName("Danger")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setEnabled(False)
        self.del_btn.clicked.connect(self._delete_selected)
        action_row.addWidget(self.del_btn)
        self.v.addLayout(action_row)

        self._folder: str | None = None

    def _build_results(self) -> QWidget:
        """Subclasses construct and return their specific results widget.

        Manages build results operations and coordinates related state changes for the component.

        Returns:
            QWidget: Result of the operation.
        """
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["Path", "Size", "Details"])
        return table

    def _pick(self):
        """Prompt the user to select a filesystem directory or file.

        Launches a native file dialog and populates the selected path into the corresponding target input widget.
        """
        folder = QFileDialog.getExistingDirectory(
            self, "Select a folder", str(Path.home()))
        if folder:
            self._folder = folder
            self.path_label.setText(folder)
            self.path_label.setObjectName("")
            self.path_label.setStyleSheet("color: inherit;")
            self.run_btn.setEnabled(True)

    def _run(self):
        """Run.

        Manages run operations and coordinates related state changes for the component.
        """
        if not self._folder:
            return
        self._finish()

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
        """Cancel the running worker, or start the subclass's scan.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        if self._running and self._worker is not None:
            if hasattr(self._worker, "cancel"):
                self._worker.cancel()
            self.scan_status.setText("Cancelling\u2026")
            self.run_btn.setEnabled(False)
        else:
            self._run()

    def _on_progress(self, text: str):
        """Show live scan progress text.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            text (str): Display text string.
        """
        self.scan_status.setText(text)

    def _finish(self):
        """Finish.

        Manages finish operations and coordinates related state changes for the component.
        """
        self._running = False
        self._worker = None
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.run_btn.setText(self.action_label)
        self.run_btn.setEnabled(True)

    def _busy(self, on: bool):
        """Update the busy state indicators across the interface.

        Shows or hides loading indicators, adjusts cursor feedback, and toggles action button availability.

        Args:
            on (bool): The on parameter.
        """
        self.progress.setVisible(on)
        self.run_btn.setEnabled(not on)

    def _enable_actions(self, has_rows: bool):
        """Enable or disable the delete action based on whether rows exist.

        Manages enable actions operations and coordinates related state changes for the component.

        Args:
            has_rows (bool): The has rows parameter.
        """
        if self.results_table is not None:
            self.results_table.setSelectionBehavior(
                QTableWidget.SelectionBehavior.SelectRows)
        self.del_btn.setEnabled(has_rows)

    def _selected_paths(self) -> list[str]:
        """Return the paths in column 0 of the currently selected table rows.

        Manages selected paths operations and coordinates related state changes for the component.

        Returns:
            list[str]: List of processed items or identifiers.
        """
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
        """Confirm and recycle the selected rows via DeleteSelectedWorker.

        Manages delete selected operations and coordinates related state changes for the component.
        """
        paths = self._selected_paths()
        if not paths:
            QMessageBox.information(
                self, "No selection", "Select one or more rows first.")
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
        """Report the recycle result and rescan the folder.

        Manages on deleted operations and coordinates related state changes for the component.

        Args:
            freed (int): The freed parameter.
            ok (int): The ok parameter.
            blocked (int): The blocked parameter.
        """
        self._busy(False)
        msg = f"Recycled {ok} item(s), freeing {fmt_bytes(freed)}."
        if blocked:
            msg += (f" {blocked} blocked by the safety guard or"
                    " unavailable Recycle Bin.")
        self.win.statusBar().showMessage(msg, 6000)
        QMessageBox.information(self, "Done", msg)
        if self._folder:
            self._run()  # refresh listing

    def _del_fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self._busy(False)
        self.del_btn.setEnabled(True)
        self.win._default_fail(msg)


class DuplicatesPage(_FolderScanPage):
    """Duplicatespage.

    Manages DuplicatesPage operations and coordinates related state changes for the component.
    """
    title = "Duplicate Files Finder"
    subtitle = "Find and safely reclaim space from identical files using byte-for-byte checksum verification."
    action_label = "Find Duplicates"

    def _build_results(self) -> QWidget:
        """Build the two-column duplicate file / group table.

        Manages build results operations and coordinates related state changes for the component.

        Returns:
            QWidget: Result of the operation.
        """
        self.tree = QTableWidget(0, 2)
        self.tree.setHorizontalHeaderLabels(["Duplicate file", "Group"])
        self.tree.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.verticalHeader().setVisible(False)
        self.tree.setAlternatingRowColors(True)
        self.results_table = self.tree
        return self.tree

    def _run(self):
        """Run.

        Manages run operations and coordinates related state changes for the component.
        """
        from .workers import DuplicateWorker
        self._start(DuplicateWorker([self._folder]), self._done, self._fail)

    def _done(self, groups: dict):
        """Handle completion of the asynchronous task.

        Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

        Args:
            groups (dict): The groups parameter.
        """
        self._finish()
        rows = [(p, i) for i, (_, members) in enumerate(groups.items(), 1) for p in members]
        self.tree.setRowCount(len(rows))
        for r, (path, gid) in enumerate(rows):
            self.tree.setItem(r, 0, QTableWidgetItem(str(path)))
            self.tree.setItem(r, 1, QTableWidgetItem(f"#{gid}"))
        total = sum(
            Path(p).stat().st_size
            for p, _ in rows
            if Path(p).is_file()
        )
        self.card_items.set_value(f"{len(rows)}", animate=True)
        self.card_size.set_value(fmt_bytes(total), animate=True)
        self.card_groups.set_value(str(len(groups)), animate=True)
        self.hint.setText("Keep one copy per group; select the extras to recycle.")
        self._enable_actions(bool(rows))
        self.win.statusBar().showMessage(
            f"{len(groups)} duplicate groups found", 5000)

    def _fail(self, msg):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg: Informational or progress status message.
        """
        self._finish()
        self.win._default_fail(msg)


class DuplicatePhotosPage(_FolderScanPage):
    """Duplicatephotospage.

    Manages DuplicatePhotosPage operations and coordinates related state changes for the component.
    """
    title = "Similar & Duplicate Photos"
    subtitle = ("Find duplicate and visually identical images (JPG, PNG, HEIC, RAW). "
                "Review copies and free up storage.")
    action_label = "Find Duplicate Photos"

    def _build_results(self) -> QWidget:
        """Build the two-column duplicate photo / group table.

        Manages build results operations and coordinates related state changes for the component.

        Returns:
            QWidget: Result of the operation.
        """
        self.tree = QTableWidget(0, 2)
        self.tree.setHorizontalHeaderLabels(["Duplicate photo", "Group"])
        self.tree.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.results_table = self.tree
        return self.tree

    def _run(self):
        """Run.

        Manages run operations and coordinates related state changes for the component.
        """
        from .workers import DuplicatePhotosWorker
        self._start(
            DuplicatePhotosWorker([self._folder]), self._done, self._fail)

    def _done(self, groups: dict):
        """Handle completion of the asynchronous task.

        Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

        Args:
            groups (dict): The groups parameter.
        """
        self._finish()
        rows = [
            (p, i)
            for i, (_, members) in enumerate(groups.items(), 1)
            for p in members
        ]
        self.tree.setRowCount(len(rows))
        for r, (path, gid) in enumerate(rows):
            self.tree.setItem(r, 0, QTableWidgetItem(str(path)))
            self.tree.setItem(r, 1, QTableWidgetItem(f"#{gid}"))
        total = sum(
            Path(p).stat().st_size
            for p, _ in rows
            if Path(p).is_file()
        )
        self.card_items.set_value(f"{len(rows)}", animate=True)
        self.card_size.set_value(fmt_bytes(total), animate=True)
        self.card_groups.set_value(str(len(groups)), animate=True)
        self.hint.setText(
            "Keep one photo per group; select the extra copies to recycle.")
        self._enable_actions(bool(rows))
        self.win.statusBar().showMessage(
            f"{len(groups)} duplicate photo groups found", 5000)

    def _fail(self, msg):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg: Informational or progress status message.
        """
        self._finish()
        self.win._default_fail(msg)


class LargeFilesPage(_FolderScanPage):
    """Largefilespage.

    Manages LargeFilesPage operations and coordinates related state changes for the component.
    """
    title = "Large Files Finder"
    subtitle = "Locate space-consuming files across your drives. Large AI models and installer archives are safely highlighted."
    action_label = "Find Large Files"

    def _build_results(self) -> QWidget:
        """Build the file / size / tag results table.

        Manages build results operations and coordinates related state changes for the component.

        Returns:
            QWidget: Result of the operation.
        """
        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["File", "Size", "Tag"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        # Tag column surfaces the AI model surfacing: HIGH-risk, disabled by default
        self.results_table = self.tbl
        return self.tbl

    def _run(self):
        """Run.

        Manages run operations and coordinates related state changes for the component.
        """
        from .workers import LargeFilesWorker
        self._start(LargeFilesWorker(self._folder, 50.0), self._done, self._fail)

    def _done(self, entries: list):
        """Handle completion of the asynchronous task.

        Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

        Args:
            entries (list): Collection of items or entries to process.
        """
        self._finish()
        try:
            from cortex_unified.analyzers.large_file_finder import AI_MODEL_EXTENSIONS
        except Exception:
            AI_MODEL_EXTENSIONS = {".gguf", ".safetensors", ".onnx", ".bin"}
        self.tbl.setRowCount(len(entries))
        total = 0
        ai_count = 0
        ai_bytes = 0
        from PySide6.QtGui import QColor
        for r, e in enumerate(entries):
            path_str = str(e.path)
            self.tbl.setItem(r, 0, QTableWidgetItem(path_str))
            self.tbl.setItem(r, 1, QTableWidgetItem(fmt_bytes(e.size)))
            ext = Path(path_str).suffix.lower()
            tag = "AI model" if ext in AI_MODEL_EXTENSIONS else ""
            tag_item = QTableWidgetItem(tag)
            if tag:
                tag_item.setForeground(QColor("#FB7185"))
                tag_item.setToolTip("AI model — 1-2GB each, re-downloadable but HIGH risk (no auto-delete).")
                ai_count += 1
                ai_bytes += e.size
            self.tbl.setItem(r, 2, tag_item)
            total += e.size
        self.card_items.set_value(f"{len(entries)}", animate=True)
        self.card_size.set_value(fmt_bytes(total), animate=True)
        self.card_groups.set_value(f"{ai_count} AI ({fmt_bytes(ai_bytes)})" if ai_count else "\u2014", animate=True)
        if ai_count:
            self.hint.setText(f"{ai_count} AI model(s) flagged HIGH — models re-download but are 1-2GB each. Deselect them unless you intend to re-fetch.")
        else:
            self.hint.setText("Select rows to move to Recycle Bin; AI models are flagged but deselected by default.")
        self._enable_actions(bool(entries))
        self.win.statusBar().showMessage(
            f"{len(entries)} large files ({ai_count} AI models)", 5000)

    def _fail(self, msg):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg: Informational or progress status message.
        """
        self._finish()
        self.win._default_fail(msg)


class EmptyPage(_FolderScanPage):
    """Emptypage.

    Manages EmptyPage operations and coordinates related state changes for the component.
    """
    title = "Empty Files & Folders"
    subtitle = "Locate and safely clean empty directories and 0-byte orphan files left behind by uninstalled software."
    action_label = "Find Empty Items"

    def _build_results(self) -> QWidget:
        """Build the two-column path / type results table.

        Manages build results operations and coordinates related state changes for the component.

        Returns:
            QWidget: Result of the operation.
        """
        self.tbl = QTableWidget(0, 2)
        self.tbl.setHorizontalHeaderLabels(["Path", "Type"])
        self.tbl.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.results_table = self.tbl
        return self.tbl

    def _run(self):
        """Run.

        Manages run operations and coordinates related state changes for the component.
        """
        from .workers import EmptyWorker
        self._start(EmptyWorker(self._folder), self._done, self._fail)

    def _done(self, files: list, dirs: list):
        """Handle completion of the asynchronous task.

        Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

        Args:
            files (list): The files parameter.
            dirs (list): The dirs parameter.
        """
        self._finish()
        rows = [(p, "File") for p in files] + [
            (p, "Directory") for p in dirs]
        self.tbl.setRowCount(len(rows))
        for r, (path, kind) in enumerate(rows):
            self.tbl.setItem(r, 0, QTableWidgetItem(str(path)))
            self.tbl.setItem(r, 1, QTableWidgetItem(kind))
        self.card_items.set_value(f"{len(rows)}", animate=True)
        self.card_size.set_value(
            f"{len(files)} files, {len(dirs)} dirs", animate=True)
        self.card_groups.set_value("\u2014", animate=True)
        self._enable_actions(bool(rows))
        self.win.statusBar().showMessage(
            f"{len(files)} empty files, {len(dirs)} empty dirs", 5000)

    def _fail(self, msg):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg: Informational or progress status message.
        """
        self._finish()
        self.win._default_fail(msg)


class ShredPage(_Page):
    """Shredpage.

    Manages ShredPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win: PremiumMainWindow):
        """Build the shredder card (target picker, passes, privacy level) and the free-space wipe card.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self._target: str | None = None

        self.v.addWidget(title_block(
            "Secure File Shredder",
            "Permanently destroy confidential files beyond forensic recovery using NIST 800-88 sanitized overwriting.",
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
        from PySide6.QtWidgets import QCheckBox, QComboBox, QSpinBox
        self.passes = QSpinBox()
        self.passes.setRange(1, 35)
        self.passes.setValue(3)
        opts.addWidget(self.passes)
        opts.addWidget(QLabel(" Privacy level:"))
        self.pl_combo = QComboBox()
        self.pl_combo.addItems([
            "Auto (WAS/PULSE)",
            "PL0 block erase (HDD)",
            "PL1 page scrub (PULSE)",
            "PL2 ECC crypto-erase",
            "PL3 TRIM lockout",
        ])
        self.pl_combo.setToolTip(
            "PL0 strongest (HDD 3-pass, SSD device-level) – heavy wear\n"
            "PL1 PULSE 2-pulse scrub low-disturbance (RBER <0.57% FG)\n"
            "PL2 header/ECC destroy + rename + TRIM (FlashFox)\n"
            "PL3 logical unmap + TRIM (fastest, logical only)\n"
            "Auto picks by storage kind & file hotness (WAS-Deletion)."
        )
        opts.addWidget(self.pl_combo)
        opts.addStretch(1)
        self.force_flash = QCheckBox("Overwrite on SSD anyway (best-effort)")
        opts.addWidget(self.force_flash)
        cl.addLayout(opts)
        # Research note card
        note = QLabel(
            "Research: HolePunch TPM+PPRF crash-consistent, PULSE RBER 0.93% SLC→0.57%, "
            "WAS-Deletion 1.2-12.9× overhead cut, FlashFox -15% wear. Auto PL avoids "
            "false-secure overwrites on SSD/NVMe (wear-leveling)."
        )
        note.setObjectName("Muted")
        note.setWordWrap(True)
        cl.addWidget(note)

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

        # -- Free-space wipe --
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
        """Fill the wipe drive combo with all existing drive letters.

        Refreshes table or tree items with formatted values, tooltips, and status indicators based on the provided dataset.
        """
        import string
        from pathlib import Path as _P
        for letter in string.ascii_uppercase:
            if _P(f"{letter}:\\").exists():
                self.wipe_drive.addItem(f"{letter}:", letter)

    def _wipe_free_space(self):
        """License-gate, confirm, and start a FreeSpaceWipeWorker on the chosen drive.

        Manages wipe free space operations and coordinates related state changes for the component.
        """
        if not require_feature(self, Feature.FREE_SPACE_WIPE):
            return
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
        """Report the free-space wipe result and reset the button.

        Manages on wiped operations and coordinates related state changes for the component.

        Args:
            success (bool): The success parameter.
            message (str): Informational or progress status message.
        """
        self.wipe_progress.setVisible(False)
        self.wipe_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Free space wiped", message)
        else:
            QMessageBox.warning(self, "Free-space wipe", message)
        self.win.statusBar().showMessage(message, 6000)

    def _on_wipe_fail(self, msg: str):
        """Reset the wipe UI and surface the error.

        Captures worker error messages, presents diagnostic feedback to the user, and resets interactive controls for retry.

        Args:
            msg (str): Informational or progress status message.
        """
        self.wipe_progress.setVisible(False)
        self.wipe_btn.setEnabled(True)
        self.win._default_fail(msg)

    def _pick(self):
        """Prompt the user to select a filesystem directory or file.

        Launches a native file dialog and populates the selected path into the corresponding target input widget.
        """
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
        """Show the detected medium and whether overwriting is reliable on it.

        Manages on medium operations and coordinates related state changes for the component.

        Args:
            kind (str): The kind parameter.
            overwrite_effective (bool): The overwrite effective parameter.
        """
        self._last_kind = kind
        self._last_overwrite = overwrite_effective
        note = "" if overwrite_effective else "  \u2014 overwrite NOT reliable here (PL2/PL3 recommended)"
        color = self.p.success if overwrite_effective else self.p.warning
        self.medium_label.setText(f"Medium: {kind}{note}")
        self.medium_label.setStyleSheet(f"color: {color}; font-weight: 600;")

    def _shred(self):
        """Shred.

        Manages shred operations and coordinates related state changes for the component.
        """
        if not self._target:
            return
        # Single-pass delete stays Free; only multi-pass overwrite is premium.
        if (self.passes.value() > 1
                and not require_feature(self, Feature.SHRED_MULTIPASS)):
            return
        confirm = QMessageBox.warning(
            self, "Confirm secure shred",
            f"Permanently shred this file? This CANNOT be undone.\n\n{self._target}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        # Adaptive PL selection (HolePunch/PULSE/WAS)
        pl_text = self.pl_combo.currentText() if hasattr(self, "pl_combo") else "Auto"
        pl_map = {
            "Auto": None,
            "PL0": "pl0",
            "PL1": "pl1",
            "PL2": "pl2",
            "PL3": "pl3",
        }
        chosen = None
        for k, v in pl_map.items():
            if pl_text.startswith(k):
                chosen = v
                break
        overwrite_ok = getattr(self, "_last_overwrite", True)
        # If PL explicitly chosen (not Auto) or flash medium, use adaptive sanitizer
        use_adaptive = (chosen is not None) or (not overwrite_ok)
        if use_adaptive:
            from .workers import AdaptiveShredWorker

            self.shred_btn.setEnabled(False)
            self.progress.setVisible(True)
            worker = AdaptiveShredWorker(self._target, level=chosen, verify=True)
            self.win.run_worker(worker, self._on_adaptive_done, self._fail)
            return
        from .workers import ShredWorker
        self.shred_btn.setEnabled(False)
        self.progress.setVisible(True)
        worker = ShredWorker(self._target, self.passes.value(), self.force_flash.isChecked())
        # ShredWorker has an extra 'refused' signal; wire it before run_worker.
        worker.refused.connect(self._on_refused)
        self.win.run_worker(worker, self._on_done, self._fail)

    def _on_adaptive_done(self, outcome: str, message: str, detail: str):
        """Report the adaptive shred outcome and reset the picker.

        Receives the completed data from the adaptive background worker, populates the view with results, and restores button states.

        Args:
            outcome (str): The outcome parameter.
            message (str): Informational or progress status message.
            detail (str): The detail parameter.
        """
        self.progress.setVisible(False)
        self.shred_btn.setEnabled(True)
        msg = f"{outcome}: {message}\n{detail}"
        self.win.statusBar().showMessage(f"Adaptive shred: {outcome}", 6000)
        QMessageBox.information(self, "Adaptive shred complete", msg)
        self._target = None
        self.target_label.setText("No file selected")
        self.shred_btn.setEnabled(False)

    def _on_done(self, outcome: str, reason: str):
        """Report the shred outcome and reset the picker.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            outcome (str): The outcome parameter.
            reason (str): The reason parameter.
        """
        self.progress.setVisible(False)
        self.shred_btn.setEnabled(True)
        msg = f"{outcome}" + (f"  ({reason})" if reason else "")
        self.win.statusBar().showMessage(f"Shred: {msg}", 6000)
        QMessageBox.information(self, "Shred complete", msg)
        self._target = None
        self.target_label.setText("No file selected")
        self.shred_btn.setEnabled(False)

    def _on_refused(self, kind: str, guidance: str):
        """Explain why overwriting was refused for this medium and offer guidance.

        Manages on refused operations and coordinates related state changes for the component.

        Args:
            kind (str): The kind parameter.
            guidance (str): The guidance parameter.
        """
        self.progress.setVisible(False)
        self.shred_btn.setEnabled(True)
        QMessageBox.information(
            self, "Not effective on this medium",
            guidance + "\n\nTip: enable 'Overwrite on SSD anyway' only if you understand "
            "it wears the drive without a hard guarantee. For real assurance use full-disk "
            "encryption + key destruction, or the drive's hardware secure-erase.",
        )

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.progress.setVisible(False)
        self.shred_btn.setEnabled(True)
        self.win._default_fail(msg)


class SettingsPage(_Page):
    """Settingspage.

    Manages SettingsPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the appearance/preference card plus the smart-suggestion and safety cards.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
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
        self.dark_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.light_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dark_btn.clicked.connect(lambda: self._choose_theme("dark"))
        self.light_btn.clicked.connect(lambda: self._choose_theme("light"))
        theme_row.addWidget(self.dark_btn)
        theme_row.addWidget(self.light_btn)
        cl.addLayout(theme_row)
        # Mark the active theme so the choice is visible at a glance.
        self._sync_theme_buttons()

        # Close-to-tray preference (keeps the app + monitor running in the
        # background when the window is closed).
        self.tray_check = QCheckBox(
            "Close to system tray (keep running in the background)")
        self.tray_check.setChecked(bool(self.win.settings.close_to_tray))
        # The tray object is created after the pages, so query the platform
        # capability directly rather than the not-yet-built window tray.
        from PySide6.QtWidgets import QSystemTrayIcon
        try:
            tray_ok = bool(QSystemTrayIcon.isSystemTrayAvailable())
        except Exception:  # noqa: BLE001
            tray_ok = False
        if not tray_ok:
            self.tray_check.setEnabled(False)
            self.tray_check.setToolTip(
                "A system tray is not available on this system.")
        self.tray_check.toggled.connect(self._on_close_to_tray_toggled)
        cl.addWidget(self.tray_check)

        # Reduce motion (accessibility): suppress non-essential animation - page
        # reveals and the smooth-scroll glide fall back to instant.
        self.motion_check = QCheckBox(
            "Reduce motion (minimise animations and smooth scrolling)")
        self.motion_check.setChecked(bool(self.win.settings.reduced_motion))
        self.motion_check.toggled.connect(self._on_reduced_motion_toggled)
        cl.addWidget(self.motion_check)

        # Update check: strictly opt-in. When enabled, the app performs ONE
        # informational release check per run - no downloads, no installs.
        self.update_check_box = QCheckBox(
            "Check for newer releases on startup (one request, informational only)")
        self.update_check_box.setChecked(bool(self.win.settings.update_check))
        self.update_check_box.toggled.connect(self._on_update_check_toggled)
        cl.addWidget(self.update_check_box)
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

    def _choose_theme(self, theme: str) -> None:
        """Apply the chosen theme and refresh the button highlight.

        Manages choose theme operations and coordinates related state changes for the component.

        Args:
            theme (str): The theme parameter.
        """
        self.win.set_theme(theme)
        self._sync_theme_buttons()

    def _sync_theme_buttons(self) -> None:
        """Give the active theme's button the accent (Primary) styling.

        Uses the object-name/repolish mechanism so the highlight is driven by
        the same token-based QSS as every other control, and updates live when
        the theme is switched.
        """
        active = self.win.theme_name
        for btn, name in ((self.dark_btn, "dark"), (self.light_btn, "light")):
            btn.setObjectName("Primary" if name == active else "")
            style = btn.style()
            if style is not None:
                style.unpolish(btn)
                style.polish(btn)

    def _on_close_to_tray_toggled(self, checked: bool) -> None:
        """Persist the close-to-tray preference.

        Manages on close to tray toggled operations and coordinates related state changes for the component.

        Args:
            checked (bool): The checked parameter.
        """
        self.win.settings.close_to_tray = bool(checked)

    def _on_reduced_motion_toggled(self, checked: bool) -> None:
        """Apply and persist the reduce-motion preference.

        Manages on reduced motion toggled operations and coordinates related state changes for the component.

        Args:
            checked (bool): The checked parameter.
        """
        from . import motion
        motion.set_reduced_motion(bool(checked))
        self.win.settings.reduced_motion = bool(checked)

    def _on_update_check_toggled(self, checked: bool) -> None:
        """Persist the opt-in startup release-check preference.

        Manages on update check toggled operations and coordinates related state changes for the component.

        Args:
            checked (bool): The checked parameter.
        """
        self.win.settings.update_check = bool(checked)

    def _build_smart_card(self):
        """Build the Smart Suggestions card showing learning stats and a reset button.

        Manages build smart card operations and coordinates related state changes for the component.
        """
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
        """Confirm, then wipe and reload the offline learning model.

        Manages reset smart operations and coordinates related state changes for the component.
        """
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
        """Build the restore-point card (Windows-only) with create/refresh actions and list.

        Manages build safety card operations and coordinates related state changes for the component.
        """
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
            cl.addWidget(status_note(
                self.p, "info",
                "System Restore points are a Windows-only feature."))
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

        elev = ("Administrator" if mgr.is_elevated()
                else "Not elevated (needed to create points)")
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
        # yet (Req 1.5). The list still loads off the UI thread via the worker
        # runtime when Settings is first shown.
        self._autoload = self._refresh_restore_points
        self._loaded = False

    def _create_restore_point(self):
        """Start a RestorePointWorker to create a restore point.

        Manages create restore point operations and coordinates related state changes for the component.
        """
        from .workers import RestorePointWorker
        self.rp_create_btn.setEnabled(False)
        self.rp_progress.setVisible(True)
        self.win.statusBar().showMessage("Creating restore point\u2026")
        self.win.run_worker(RestorePointWorker("Cortex Cleaner - manual"),
                            self._on_rp_created, self._on_rp_fail)

    def _on_rp_created(self, status: str, message: str):
        """Report the create outcome per status and refresh the list.

        Manages on rp created operations and coordinates related state changes for the component.

        Args:
            status (str): The status parameter.
            message (str): Informational or progress status message.
        """
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
        """Reset the restore-point UI and surface the error.

        Captures worker error messages, presents diagnostic feedback to the user, and resets interactive controls for retry.

        Args:
            msg (str): Informational or progress status message.
        """
        self.rp_progress.setVisible(False)
        self.rp_create_btn.setEnabled(True)
        self.win._default_fail(msg)

    def _refresh_restore_points(self):
        """Load existing restore points via RestorePointListWorker.

        Manages refresh restore points operations and coordinates related state changes for the component.
        """
        from .workers import RestorePointListWorker
        self.win.run_worker(RestorePointListWorker(), self._on_rp_listed, self._on_rp_fail)

    def _on_rp_listed(self, points: list):
        """Fill the restore-point table from the listed points.

        Manages on rp listed operations and coordinates related state changes for the component.

        Args:
            points (list): The points parameter.
        """
        self.rp_table.setRowCount(len(points))
        for r, p in enumerate(points):
            self.rp_table.setItem(r, 0, QTableWidgetItem(str(p.get("description", ""))))
            self.rp_table.setItem(r, 1, QTableWidgetItem(str(p.get("created", ""))))
            self.rp_table.setItem(r, 2, QTableWidgetItem(str(p.get("type", ""))))
