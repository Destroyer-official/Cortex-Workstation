"""Headless smoke tests for the premium GUI.

These run under Qt's 'offscreen' platform so they work in CI without a display.
The whole module is skipped if PySide6 isn't installed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def app():
    """App.

    Manages app operations and coordinates related state changes for the component.
    """
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def window(app):
    """Window.

    Manages window operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    import gc
    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import PremiumMainWindow
    if not getattr(app, "_theme_applied", False):
        apply_theme(app, "dark")
        app._theme_applied = True
    win = PremiumMainWindow("dark")
    win.resize(1180, 760)
    yield win
    win._force_quit = True
    win.close()
    win.deleteLater()
    app.processEvents()
    gc.collect()


def test_stylesheet_builds_for_both_themes(app):
    """test_stylesheet_builds_for_both_themes.

    Manages test stylesheet builds for both themes operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from cortex_unified.ui.premium.theme import THEMES, build_stylesheet
    for name, palette in THEMES.items():
        qss = build_stylesheet(palette)
        assert "QPushButton#Primary" in qss
        assert palette.accent in qss


def test_all_pages_present(window):
    """test_all_pages_present.

    Manages test all pages present operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    from cortex_unified.ui.premium import registry
    assert set(window._pages) == {p.id for p in registry.PAGES}


def test_navigate_every_page(window):
    """Selecting each page must switch the stack without error.

    Manages test navigate every page operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    for pid in window._pages:
        window._select(pid)
        assert window._stack.currentWidget() is window._pages[pid]


def test_theme_toggle_does_not_crash(window):
    """test_theme_toggle_does_not_crash.

    Manages test theme toggle does not crash operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    window.set_theme("light")
    assert window.theme_name == "light"
    window.set_theme("dark")
    assert window.theme_name == "dark"


def test_navigation_switches_pages(window):
    """test_navigation_switches_pages.

    Manages test navigation switches pages operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    window._select("duplicates")
    assert window._stack.currentWidget() is window._pages["duplicates"]
    window._select("dashboard")
    assert window._stack.currentWidget() is window._pages["dashboard"]


def test_dashboard_populates_from_report(window):
    """test_dashboard_populates_from_report.

    Manages test dashboard populates from report operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    from cortex_unified.engine import default_categories
    from cortex_unified.engine.models import FileEntry
    from cortex_unified.engine.service import CategoryScan, CleanupReport

    cats = default_categories()
    scan = CategoryScan(category=cats[0])
    scan.total_bytes = 1_500_000_000
    scan.entries = [FileEntry(Path("x"), 1, 0.0)] * 42
    report = CleanupReport(scans=[scan], duration_seconds=0.5)

    dash = window._pages["dashboard"]
    dash._on_scanned(report)

    assert dash.tree.topLevelItemCount() == 1
    assert dash.recycle_btn.isEnabled()
    assert "GB" in dash.card_space._value.text()  # 1.5 GB formatted


def test_dashboard_preview_expands(window):
    """Expanding a category must lazily reveal its contents (preview).

    Manages test dashboard preview expands operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    from pathlib import Path
    from cortex_unified.engine.categories import CleanupCategory, RiskLevel
    from cortex_unified.engine.models import FileEntry
    from cortex_unified.engine.service import CategoryScan, CleanupReport
    from PySide6.QtCore import Qt

    # A single-root synthetic category so expanding drills straight into its
    # contents (sub1 folder with 2 files, sub2 folder with 1 file).
    root = Path("C:/CortexTestCache")
    cat = CleanupCategory(id="test", label="Test cache", description="",
                          risk=RiskLevel.LOW, paths=(root,))
    scan = CategoryScan(category=cat)
    scan.entries = [FileEntry(root / "sub1" / "a", 500, 0.0),
                    FileEntry(root / "sub1" / "b", 300, 0.0),
                    FileEntry(root / "sub2" / "c", 100, 0.0)]
    scan.total_bytes = 900
    report = CleanupReport(scans=[scan])

    from PySide6.QtCore import QDeadlineTimer
    from PySide6.QtWidgets import QApplication

    dash = window._pages["dashboard"]
    dash._on_scanned(report)
    top = dash.tree.topLevelItem(0)
    # Before expansion: a single placeholder child.
    assert top.childCount() == 1
    top.setExpanded(True)   # triggers itemExpanded -> async populate on a worker

    # Population is off-thread; pump the loop until it lands.
    app = QApplication.instance()
    deadline = QDeadlineTimer(8000)
    while not deadline.hasExpired():
        app.processEvents()
        if top.childCount() == 2:
            break
    # After expansion: real folder groups (sub1 with 2 files, sub2 with 1).
    assert top.childCount() == 2
    names = {top.child(i).text(0) for i in range(top.childCount())}
    assert any("sub1" in n for n in names)


def test_preview_helpers(app):
    """The drill-down grouping helpers must aggregate correctly and fast.

    Manages test preview helpers operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from cortex_unified.ui.premium.workers import aggregate_roots, children_under
    from cortex_unified.engine.models import FileEntry

    root = "C:\\Cache"
    entries = [
        FileEntry(f"{root}\\a\\1.bin", 100, 0.0),
        FileEntry(f"{root}\\a\\2.bin", 200, 0.0),
        FileEntry(f"{root}\\b\\3.bin", 50, 0.0),
        FileEntry(f"{root}\\top.bin", 10, 0.0),
    ]
    kids = children_under(entries, root)
    # 'a' (300, dir) > 'b' (50, dir) > top.bin (10, file)
    assert kids[0]["name"] == "a" and kids[0]["is_dir"] and kids[0]["size"] == 300
    assert kids[0]["count"] == 2 and kids[0]["expandable"]
    assert any(k["name"] == "top.bin" and not k["is_dir"] for k in kids)

    # Drill deeper into 'a'
    deep = children_under(entries, root + "\\a")
    assert {k["name"] for k in deep} == {"1.bin", "2.bin"}
    assert all(not k["is_dir"] for k in deep)

    # Multi-root aggregation
    roots_out = aggregate_roots(entries, [root])
    assert len(roots_out) == 1 and roots_out[0]["size"] == 360


def test_group_by_app(app):
    """App caches must group by their owning app with friendly names.

    Manages test group by app operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from cortex_unified.ui.premium.workers import group_by_app
    from cortex_unified.engine.models import FileEntry
    base = "C:\\Users\\x\\AppData\\Local"
    entries = [
        FileEntry(f"{base}\\Google\\Chrome\\User Data\\Default\\Cache\\a", 500, 0.0),
        FileEntry(f"{base}\\Google\\Chrome\\User Data\\Default\\Cache\\b", 300, 0.0),
        FileEntry(f"{base}\\Discord\\Cache\\c", 100, 0.0),
    ]
    apps = group_by_app(entries, [base])
    by_name = {a["name"]: a for a in apps}
    assert "Google Chrome" in by_name          # friendly name applied
    assert "Discord" in by_name
    assert by_name["Google Chrome"]["size"] == 800
    assert by_name["Google Chrome"]["count"] == 2
    # sorted biggest first
    assert apps[0]["name"] == "Google Chrome"


def test_dashboard_selection_excludes(window):
    """Unchecking an app/folder in the preview must exclude it from cleaning.

    Manages test dashboard selection excludes operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    from pathlib import Path
    from cortex_unified.engine.categories import CleanupCategory, RiskLevel
    from cortex_unified.engine.models import FileEntry
    from cortex_unified.engine.service import CategoryScan, CleanupReport
    from PySide6.QtCore import QDeadlineTimer, Qt
    from PySide6.QtWidgets import QApplication

    root = Path("C:/CortexSelTest")
    cat = CleanupCategory(id="test", label="Test", description="",
                          risk=RiskLevel.LOW, paths=(root,))
    scan = CategoryScan(category=cat)
    scan.entries = [FileEntry(root / "AppA" / "x", 500, 0.0),
                    FileEntry(root / "AppB" / "y", 300, 0.0)]
    scan.total_bytes = 800
    report = CleanupReport(scans=[scan])

    dash = window._pages["dashboard"]
    dash._on_scanned(report)
    top = dash.tree.topLevelItem(0)
    top.setExpanded(True)

    app_ = QApplication.instance()
    deadline = QDeadlineTimer(8000)
    while not deadline.hasExpired():
        app_.processEvents()
        if top.childCount() == 2:
            break
    assert top.childCount() == 2

    # Uncheck the AppA folder node -> it must be excluded from the clean set.
    appA = next(top.child(i) for i in range(top.childCount())
                if "AppA" in top.child(i).text(0))
    appA.setCheckState(0, Qt.CheckState.Unchecked)   # fires _on_item_changed
    app_.processEvents()

    filtered = dash._filtered_entries(scan, 0)
    paths = {str(e.path).replace("/", "\\") for e in filtered}
    assert all("AppA" not in p for p in paths)       # AppA excluded
    assert any("AppB" in p for p in paths)           # AppB still cleaned


def test_circular_gauge_animates(window):
    """test_circular_gauge_animates.

    Manages test circular gauge animates operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    dash = window._pages["dashboard"]
    dash.gauge.animate_to(75.0, display="75")
    # value property is animated; end value must be within range
    assert 0.0 <= dash.gauge.value <= 100.0


def test_render_to_pixmap(window):
    """The window must render to a non-empty pixmap (catches paint crashes).

    Manages test render to pixmap operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    window.show()
    pix = window.grab()
    assert pix.width() > 0 and pix.height() > 0


def test_responsive_resize(window):
    """Content must adapt (and render) across small and large window sizes.

    Manages test responsive resize operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    window.show()
    # Small window: margins shrink, pages stay scrollable (no clip/crash).
    window.resize(840, 560)
    window._select("dashboard")
    small = window.grab()
    assert small.width() > 0
    m_small = window._content_layout.contentsMargins().left()
    # Large window: margins grow to breathe.
    window.resize(1600, 1000)
    window._select("processes")
    big = window.grab()
    assert big.width() > 0
    m_big = window._content_layout.contentsMargins().left()
    assert m_big > m_small   # margins scale with width

    # Every page must still render at the small size without error.
    window.resize(860, 580)
    for pid in window._pages:
        window._select(pid)
        assert window._stack.currentWidget() is window._pages[pid]


def test_core_bars_widget_renders(app):
    """The per-core CPU bar widget must accept values and paint without error.

    Manages test core bars widget renders operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from cortex_unified.ui.premium.theme import THEMES
    from cortex_unified.ui.premium.widgets import CoreBars
    bars = CoreBars(THEMES["dark"])
    bars.resize(300, 64)
    bars.set_values([12.0, 88.0, 45.0, 99.0])   # mixed loads -> green/amber/red
    bars.show()
    pix = bars.grab()
    assert pix.width() > 0 and pix.height() > 0
    bars.set_values([])  # empty must not crash
    bars.grab()


def test_stat_card_animate_value(app):
    """test_stat_card_animate_value.

    Manages test stat card animate value operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from cortex_unified.ui.premium.theme import THEMES
    from cortex_unified.ui.premium.widgets import StatCard
    card = StatCard(THEMES["dark"], "Test", "0")
    card.set_value("42", animate=True)      # animated path
    assert card._value.text() == "42"
    card.set_value("99")                    # plain path
    assert card._value.text() == "99"


def test_shred_page_present_and_wired(window):
    """test_shred_page_present_and_wired.

    Manages test shred page present and wired operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    page = window._pages["shred"]
    assert hasattr(page, "shred_btn") and hasattr(page, "standard_combo")
    # No file selected yet -> shred action disabled.
    assert page.shred_btn.isEnabled() is False


def test_recycle_worker_actually_removes(app, tmp_path):
    """DeleteSelectedWorker (recycle) must remove a real file, run synchronously.

    Manages test recycle worker actually removes operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
        tmp_path: Filesystem path to the target file or directory.
    """
    from cortex_unified.ui.premium.workers import DeleteSelectedWorker

    f = tmp_path / "junk.txt"
    f.write_text("bye")
    captured = {}
    worker = DeleteSelectedWorker([str(f)], "recycle")
    worker.finished.connect(lambda freed, ok, blocked: captured.update(ok=ok, blocked=blocked))
    worker.run()
    assert captured.get("ok") == 1
    assert not f.exists()


def test_dashboard_live_scan_completes(app, window):
    """The real 'Scan Now' flow must run on a worker thread and populate results.

    Regression test for the reported 'stuck on Scanning...' bug.
    """
    from PySide6.QtCore import QDeadlineTimer, QEventLoop, QTimer

    dash = window._pages["dashboard"]
    dash._scan()
    assert dash._scanning is True

    # Pump the event loop until the scan finishes or a timeout elapses.
    deadline = QDeadlineTimer(30000)  # 30s ceiling
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(50)
    timer.timeout.connect(lambda: (loop.quit() if (not dash._scanning or deadline.hasExpired()) else None))
    timer.start()
    loop.exec()
    timer.stop()

    assert dash._scanning is False, "scan never completed (stuck)"
    assert dash.scan_btn.text() == "Scan Now"      # button reset
    assert dash._report is not None                # results captured


def test_shred_worker_overwrites_and_removes(app, tmp_path):
    """ShredWorker with force_flash must overwrite+delete regardless of medium.

    Manages test shred worker overwrites and removes operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
        tmp_path: Filesystem path to the target file or directory.
    """
    from cortex_unified.ui.premium.workers import ShredWorker

    f = tmp_path / "secret.bin"
    f.write_bytes(b"S" * 4096)
    captured = {}
    worker = ShredWorker(str(f), passes=2, force_flash=True)
    worker.finished.connect(lambda outcome, reason: captured.update(outcome=outcome))
    worker.refused.connect(lambda kind, guidance: captured.update(refused=kind))
    worker.run()
    assert captured.get("outcome") == "overwritten"
    assert not f.exists()


# ---------------------------------------------------------------------------
#  Worker-shutdown contract (crash-on-close regression: 0xC0000409 abort when
#  a QThread outlived the old fixed 3s wait and was destroyed while running)
# ---------------------------------------------------------------------------

class _CoopWorker:
    """Coopworker.

    Manages CoopWorker operations and coordinates related state changes for the component.
    """

    def __new__(cls):
        """New.

        Manages new operations and coordinates related state changes for the component.
        """
        import threading
        from PySide6.QtCore import QObject, Signal

        class W(QObject):
            """W.

            Manages W operations and coordinates related state changes for the component.
            """
            finished = Signal(str)
            failed = Signal(str)

            def __init__(self):
                """Initialize the instance and configure internal state.

                Sets up sub-widgets, event signal connections, and default options.
                """
                super().__init__()
                self._cancel = threading.Event()

            def cancel(self):
                """cancel.

                Sets the internal cancellation event to cooperatively stop worker execution at the next safe boundary.
                """
                self._cancel.set()

            def run(self):
                """run.

                Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
                """
                import time
                for _ in range(300):
                    if self._cancel.is_set():
                        return
                    time.sleep(0.05)

        return W()


def test_close_with_cooperative_worker_is_fast_and_clean(app, window):
    """A cancellable worker must stop within the close grace, leave nothing
    stuck, and not block closing."""
    import time

    window.run_worker(_CoopWorker(), lambda *a: None)
    assert len(window._threads) == 1
    t0 = time.monotonic()
    window.close()
    elapsed = time.monotonic() - t0
    assert elapsed < 5.0                       # no multi-second freeze on close
    assert window._workers_stuck == []         # everything stopped cooperatively
    assert not any(t.isRunning() for t in window._threads)


def test_close_with_unkillable_worker_detaches_instead_of_crashing(app, window):
    """A worker that ignores cancel/quit/terminate must be detached + recorded
    (never destroyed while running), and closeEvent must still return."""
    import threading
    import time
    from PySide6.QtCore import QObject, Signal

    class StuckWorker(QObject):
        """Stuckworker.

        Manages StuckWorker operations and coordinates related state changes for the component.
        """
        finished = Signal(str)
        failed = Signal(str)

        def run(self):
            """run.

            Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
            """
            event = threading.Event()
            event.wait(6)   # uninterruptible-ish; outlives the shortened grace

    stuck = StuckWorker()
    window._CLOSE_GRACE_S = 0.5                # keep the test fast
    window.run_worker(stuck, lambda *a: None)
    thread = window._threads[0]

    t0 = time.monotonic()
    window.close()
    elapsed = time.monotonic() - t0

    # Grace (0.5s) + terminate attempt + wait must bound the close, not hang.
    assert elapsed < 6.0
    # The still-running thread was detached and recorded for the app-level
    # hard-exit path instead of being destroyed mid-run (which aborts).
    assert thread in window._workers_stuck
    assert thread not in window._threads
    assert thread.parent() is None
    # Let the worker finish naturally so teardown never deletes a live thread.
    assert thread.wait(8000)


def test_run_worker_refused_after_close(app, window):
    """Once shutdown begins, no new worker may start (it would outlive the
    shutdown sweep and crash teardown)."""
    window.close()
    n = len(window._threads)
    ran = []

    class Probe(_CoopWorker().__class__):
        """Probe.

        Manages Probe operations and coordinates related state changes for the component.
        """
        def run(self):
            """run.

            Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
            """
            ran.append(True)

    window.run_worker(Probe(), lambda *a: None)
    import time
    time.sleep(0.2)
    assert len(window._threads) == n           # nothing started
    assert ran == []                           # run() never invoked


# ---------------------------------------------------------------------------
#  Settings persistence (theme + close-to-tray) and the premium system tray
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_window(app, tmp_path):
    """A real window backed by a throwaway settings file so persistence tests
    never touch the user's real ~/.cortex_cleaner/settings.json."""
    from cortex_unified.ui.premium.settings_store import SettingsStore
    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import PremiumMainWindow
    apply_theme(app, "dark")
    store = SettingsStore(tmp_path / "settings.json")
    win = PremiumMainWindow("dark", settings=store)
    yield win, store
    win._force_quit = True
    win.close()
    win.deleteLater()
    app.processEvents()


def _fake_qobject_window(app):
    """A minimal QObject that quacks like the window for tray-action tests.

    Manages fake qobject window operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from PySide6.QtCore import QObject
    from cortex_unified.ui.premium.theme import THEMES

    class FakeWin(QObject):
        """Fakewin.

        Manages FakeWin operations and coordinates related state changes for the component.
        """
        def __init__(self):
            """Initialize the instance and configure internal state.

            Sets up sub-widgets, event signal connections, and default options.
            """
            super().__init__()
            self.palette_tokens = THEMES["dark"]
            self._force_quit = False
            self._pages: dict = {}
            self.calls: list = []

        def isMinimized(self):  # noqa: N802
            """Isminimized.

            Manages isMinimized operations and coordinates related state changes for the component.
            """
            return False

        def show(self):
            """Show.

            Manages show operations and coordinates related state changes for the component.
            """
            self.calls.append("show")

        def showNormal(self):  # noqa: N802
            """Shownormal.

            Manages showNormal operations and coordinates related state changes for the component.
            """
            self.calls.append("showNormal")

        def raise_(self):
            """Raise.

            Manages raise operations and coordinates related state changes for the component.
            """
            self.calls.append("raise")

        def activateWindow(self):  # noqa: N802
            """Activatewindow.

            Manages activateWindow operations and coordinates related state changes for the component.
            """
            self.calls.append("activate")

        def _select(self, pid):
            """Select.

            Manages select operations and coordinates related state changes for the component.

            Args:
                pid: The pid parameter.
            """
            self.calls.append(("select", pid))

        def close(self):
            """Close.

            Manages close operations and coordinates related state changes for the component.
            """
            self.calls.append("close")

    return FakeWin()


def test_settings_store_defaults_and_roundtrip(tmp_path):
    """test_settings_store_defaults_and_roundtrip.

    Manages test settings store defaults and roundtrip operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    from cortex_unified.ui.premium.settings_store import SettingsStore
    p = tmp_path / "s.json"
    s = SettingsStore(p)
    assert s.theme == "dark"
    assert s.close_to_tray is False
    s.theme = "light"
    s.close_to_tray = True
    # A fresh store reading the same file sees the persisted values.
    assert SettingsStore(p).theme == "light"
    assert SettingsStore(p).close_to_tray is True


def test_settings_store_tolerates_corrupt_file(tmp_path):
    """test_settings_store_tolerates_corrupt_file.

    Manages test settings store tolerates corrupt file operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    from cortex_unified.ui.premium.settings_store import SettingsStore
    p = tmp_path / "s.json"
    p.write_text("{ this is not valid json", encoding="utf-8")
    s = SettingsStore(p)                 # must not raise
    assert s.theme == "dark"             # falls back to defaults
    assert s.close_to_tray is False


def test_settings_store_sanitizes_bad_values(tmp_path):
    """test_settings_store_sanitizes_bad_values.

    Manages test settings store sanitizes bad values operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    import json
    from cortex_unified.ui.premium.settings_store import SettingsStore
    p = tmp_path / "s.json"
    p.write_text(json.dumps(
        {"version": 1, "settings": {"theme": "neon", "close_to_tray": "yes"}}),
        encoding="utf-8")
    s = SettingsStore(p)
    assert s.theme == "dark"             # unknown theme -> default
    assert s.close_to_tray is True       # truthy string coerced to bool


def test_theme_choice_persists_across_restart(temp_window):
    """test_theme_choice_persists_across_restart.

    Manages test theme choice persists across restart operations and coordinates related state changes for the component.

    Args:
        temp_window: The temp window parameter.
    """
    win, store = temp_window
    win.set_theme("light")
    assert store.theme == "light"
    # Simulate a restart: a brand-new store reading the same file.
    from cortex_unified.ui.premium.settings_store import SettingsStore
    assert SettingsStore(store._path).theme == "light"


def test_settings_page_marks_active_theme(temp_window):
    """test_settings_page_marks_active_theme.

    Manages test settings page marks active theme operations and coordinates related state changes for the component.

    Args:
        temp_window: The temp window parameter.
    """
    win, store = temp_window
    page = win._pages["settings"]
    # Dark is active at construction, so its button carries the accent style.
    assert page.dark_btn.objectName() == "Primary"
    assert page.light_btn.objectName() == ""
    page._choose_theme("light")
    assert page.light_btn.objectName() == "Primary"
    assert page.dark_btn.objectName() == ""
    assert store.theme == "light"


def test_tray_icon_renders_for_both_themes(app):
    """test_tray_icon_renders_for_both_themes.

    Manages test tray icon renders for both themes operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from cortex_unified.ui.premium.theme import THEMES
    from cortex_unified.ui.premium.tray import _render_tray_icon
    for palette in THEMES.values():
        assert not _render_tray_icon(palette).isNull()


def test_tray_is_inert_when_unavailable(app, tmp_path):
    """Offscreen has no system tray, so PremiumTray must construct cleanly and
    be a safe no-op rather than raising."""
    from cortex_unified.ui.premium.settings_store import SettingsStore
    from cortex_unified.ui.premium.tray import PremiumTray
    fw = _fake_qobject_window(app)
    tray = PremiumTray(fw, SettingsStore(tmp_path / "s.json"))
    assert tray.available is False
    tray.show_message("t", "m")          # no-op, must not raise
    tray.refresh_theme(fw.palette_tokens)
    tray.stop()                          # idempotent
    tray.stop()


def test_tray_menu_actions_drive_window(app, tmp_path):
    """test_tray_menu_actions_drive_window.

    Manages test tray menu actions drive window operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
        tmp_path: Filesystem path to the target file or directory.
    """
    from cortex_unified.ui.premium.settings_store import SettingsStore
    from cortex_unified.ui.premium.tray import PremiumTray
    fw = _fake_qobject_window(app)
    tray = PremiumTray(fw, SettingsStore(tmp_path / "s.json"))
    tray._restore_window()
    assert "show" in fw.calls or "showNormal" in fw.calls
    tray._run_health_check()
    assert ("select", "health") in fw.calls
    tray._quit_app()
    assert fw._force_quit is True
    assert "close" in fw.calls


def test_close_to_tray_hides_instead_of_quitting(temp_window):
    """With close-to-tray on and a tray available, closing the window hides it
    (workers untouched); a tray Exit (_force_quit) performs the real quit."""
    win, store = temp_window

    class FakeTray:
        """Faketray.

        Manages FakeTray operations and coordinates related state changes for the component.
        """
        def __init__(self):
            """Initialize the instance and configure internal state.

            Sets up sub-widgets, event signal connections, and default options.
            """
            self.available = True
            self.msgs: list = []
            self.stopped = False

        def show_message(self, title, message, msecs=6000):
            """show_message.

            Manages show message operations and coordinates related state changes for the component.

            Args:
                title: Display text string.
                message: Informational or progress status message.
                msecs: The msecs parameter.
            """
            self.msgs.append((title, message))

        def stop(self):
            """Stop active background operations.

            Manages worker thread execution states, signaling termination flags or initializing scheduled execution timers.
            """
            self.stopped = True

        def refresh_theme(self, palette):
            """refresh_theme.

            Manages refresh theme operations and coordinates related state changes for the component.

            Args:
                palette: The palette parameter.
            """
            pass

    win._tray = FakeTray()
    store.close_to_tray = True
    win.show()

    win.close()                          # closeEvent should ignore + hide
    assert win.isVisible() is False      # hidden to tray
    assert win._closing is False         # not shutting down
    assert win._tray.msgs                # one-time "still running" hint shown
    assert win._tray.stopped is False    # background monitor left running

    # A real quit via the tray Exit action bypasses the guard.
    win._force_quit = True
    win.close()
    assert win._closing is True
    assert win._tray.stopped is True     # monitor stopped on real quit


def test_close_to_tray_only_hints_once(temp_window):
    """test_close_to_tray_only_hints_once.

    Manages test close to tray only hints once operations and coordinates related state changes for the component.

    Args:
        temp_window: The temp window parameter.
    """
    win, store = temp_window

    class FakeTray:
        """Faketray.

        Manages FakeTray operations and coordinates related state changes for the component.
        """
        def __init__(self):
            """Initialize the instance and configure internal state.

            Sets up sub-widgets, event signal connections, and default options.
            """
            self.available = True
            self.msgs: list = []

        def show_message(self, title, message, msecs=6000):
            """show_message.

            Manages show message operations and coordinates related state changes for the component.

            Args:
                title: Display text string.
                message: Informational or progress status message.
                msecs: The msecs parameter.
            """
            self.msgs.append((title, message))

        def stop(self):
            """Stop active background operations.

            Manages worker thread execution states, signaling termination flags or initializing scheduled execution timers.
            """
            pass

    win._tray = FakeTray()
    store.close_to_tray = True
    win.show()
    win.close()
    win.show()
    win.close()
    assert len(win._tray.msgs) == 1      # the hint is shown at most once


# ---------------------------------------------------------------------------
#  Focus-visible: clicked buttons must not show a boxy focus outline
# ---------------------------------------------------------------------------

def test_focus_ring_is_clean_border_not_boxy_outline(app):
    """Both themes must draw focus as a clean border, never a boxy 'outline'
    rectangle (that inner box is what made clicked buttons look unpolished),
    and the button ring must be gated behind the keyboard-only focusVisible
    property."""
    from cortex_unified.ui.premium.theme import THEMES, build_stylesheet
    for palette in THEMES.values():
        qss = build_stylesheet(palette)
        assert "outline: 2px" not in qss            # no boxy focus rectangles
        assert '[focusVisible="true"]' in qss        # keyboard-only ring gate


def test_focus_visible_ring_only_for_keyboard(app):
    """The ring (focusVisible=true) appears when focus arrives via the keyboard
    and never on a plain mouse click."""
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QFocusEvent, QKeyEvent
    from PySide6.QtWidgets import QPushButton
    from cortex_unified.ui.premium.focus import FocusVisibleFilter

    flt = FocusVisibleFilter(app)
    btn = QPushButton("x")

    # A navigation key press switches the modality to keyboard.
    flt.eventFilter(btn, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Tab,
                                   Qt.KeyboardModifier.NoModifier))
    assert flt._keyboard is True
    # Focus arriving now (keyboard) shows the ring.
    flt.eventFilter(btn, QFocusEvent(QEvent.Type.FocusIn))
    assert bool(btn.property("focusVisible")) is True

    # Focus-out clears the ring.
    flt.eventFilter(btn, QFocusEvent(QEvent.Type.FocusOut))
    assert bool(btn.property("focusVisible")) is False

    # Mouse modality (the default) means focus arriving shows NO ring.
    flt._keyboard = False
    flt.eventFilter(btn, QFocusEvent(QEvent.Type.FocusIn))
    assert bool(btn.property("focusVisible")) is False


def test_install_focus_visible_is_idempotent(app):
    """test_install_focus_visible_is_idempotent.

    Manages test install focus visible is idempotent operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from cortex_unified.ui.premium.focus import install_focus_visible
    install_focus_visible(app)
    first = getattr(app, "_cortex_focus_filter", None)
    assert first is not None
    install_focus_visible(app)
    assert getattr(app, "_cortex_focus_filter", None) is first  # not stacked


# ---------------------------------------------------------------------------
#  Smooth momentum scrolling (premium 'every scroll' feel)
# ---------------------------------------------------------------------------

def _scroll_area(app, rng: int = 1000):
    """A scroll area with a deterministic vertical range for wheel tests.

    Manages scroll area operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
        rng (int): The rng parameter.
    """
    from PySide6.QtWidgets import QScrollArea, QWidget
    area = QScrollArea()
    area.setWidget(QWidget())
    bar = area.verticalScrollBar()
    bar.setRange(0, rng)
    bar.setValue(0)
    return area, bar


def _wheel(down: bool = True, pixel: bool = False):
    """Wheel.

    Manages wheel operations and coordinates related state changes for the component.

    Args:
        down (bool): The down parameter.
        pixel (bool): The pixel parameter.
    """
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    angle = QPoint(0, -120 if down else 120)
    pdelta = QPoint(0, -30 if pixel else 0)  # non-null only for the touchpad case
    return QWheelEvent(QPointF(10, 10), QPointF(10, 10), pdelta, angle,
                       Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                       Qt.ScrollPhase.NoScrollPhase, False)


def test_smooth_scroll_glides_on_mouse_wheel(app):
    """test_smooth_scroll_glides_on_mouse_wheel.

    Manages test smooth scroll glides on mouse wheel operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from cortex_unified.ui.premium.smoothscroll import install_smooth_scroll
    area, bar = _scroll_area(app)
    sc = install_smooth_scroll(area)
    assert sc is not None
    consumed = sc.eventFilter(area.viewport(), _wheel(down=True))
    assert consumed is True            # we own the scroll (glide it)
    assert sc._target > 0              # target advanced downward
    assert sc._anim.endValue() == sc._target   # animation aims at the target


def test_smooth_scroll_ignores_touchpad(app):
    """test_smooth_scroll_ignores_touchpad.

    Manages test smooth scroll ignores touchpad operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from cortex_unified.ui.premium.smoothscroll import install_smooth_scroll
    area, bar = _scroll_area(app)
    sc = install_smooth_scroll(area)
    # A pixel-delta (touchpad) event is left to native smooth scrolling.
    assert sc.eventFilter(area.viewport(), _wheel(down=True, pixel=True)) is False


def test_smooth_scroll_hands_off_at_boundary(app):
    """test_smooth_scroll_hands_off_at_boundary.

    Manages test smooth scroll hands off at boundary operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from cortex_unified.ui.premium.smoothscroll import install_smooth_scroll
    area, bar = _scroll_area(app)
    bar.setValue(0)                    # already at the top
    sc = install_smooth_scroll(area)
    # Scrolling up at the top must NOT be consumed, so SingleScrollFilter can
    # forward the gesture to the outer container.
    assert sc.eventFilter(area.viewport(), _wheel(down=False)) is False


def test_smooth_scroll_respects_reduced_motion(app):
    """test_smooth_scroll_respects_reduced_motion.

    Manages test smooth scroll respects reduced motion operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from cortex_unified.ui.premium import motion
    from cortex_unified.ui.premium.smoothscroll import install_smooth_scroll
    area, bar = _scroll_area(app)
    sc = install_smooth_scroll(area)
    motion.set_reduced_motion(True)
    try:
        # Reduced motion -> don't animate; fall back to native scrolling.
        assert sc.eventFilter(area.viewport(), _wheel(down=True)) is False
    finally:
        motion.set_reduced_motion(False)


def test_install_smooth_scroll_is_idempotent(app):
    """test_install_smooth_scroll_is_idempotent.

    Manages test install smooth scroll is idempotent operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from cortex_unified.ui.premium.smoothscroll import install_smooth_scroll
    area, bar = _scroll_area(app)
    a = install_smooth_scroll(area)
    b = install_smooth_scroll(area)
    assert a is b                      # not stacked on repeated install


def test_pages_have_smooth_scroll_installed(window):
    """Every page's outer scroll area gets the premium glide.

    Manages test pages have smooth scroll installed operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    dash = window._pages["dashboard"]
    assert getattr(dash._scroll, "_cortex_smooth_scroller", None) is not None


# ---------------------------------------------------------------------------
#  Motion polish: reveal transition, reduced-motion setting, shimmer loading
# ---------------------------------------------------------------------------

def test_reveal_respects_reduced_motion(app):
    """test_reveal_respects_reduced_motion.

    Manages test reveal respects reduced motion operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from PySide6.QtWidgets import QWidget
    from cortex_unified.ui.premium import motion
    w = QWidget()
    w.resize(120, 80)
    called = []
    motion.set_reduced_motion(True)
    try:
        result = motion.reveal(w, on_done=lambda: called.append(True))
        assert result is None            # no animation under reduced motion
        assert called == [True]          # ...but on_done still runs
    finally:
        motion.set_reduced_motion(False)
    grp = motion.reveal(w)               # motion on -> an animation group
    assert grp is not None
    grp.stop()


def test_settings_store_reduced_motion_roundtrip(tmp_path):
    """test_settings_store_reduced_motion_roundtrip.

    Manages test settings store reduced motion roundtrip operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    from cortex_unified.ui.premium.settings_store import SettingsStore
    p = tmp_path / "s.json"
    s = SettingsStore(p)
    assert s.reduced_motion is False
    s.reduced_motion = True
    assert SettingsStore(p).reduced_motion is True


def test_shimmer_skeleton_start_stop(app):
    """test_shimmer_skeleton_start_stop.

    Manages test shimmer skeleton start stop operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from cortex_unified.ui.premium import motion
    from cortex_unified.ui.premium.skeleton import ShimmerSkeleton
    from cortex_unified.ui.premium.theme import THEMES
    sk = ShimmerSkeleton(THEMES["dark"], rows=4)
    sk.resize(320, 140)
    sk.start()
    sk._set_phase(0.5)
    assert sk.phase == 0.5
    sk.stop()                            # safe to stop
    motion.set_reduced_motion(True)
    try:
        sk.start()                       # reduced motion: no crash, no sweep
    finally:
        motion.set_reduced_motion(False)


def test_settings_page_reduced_motion_toggle(temp_window):
    """test_settings_page_reduced_motion_toggle.

    Manages test settings page reduced motion toggle operations and coordinates related state changes for the component.

    Args:
        temp_window: The temp window parameter.
    """
    from cortex_unified.ui.premium import motion
    win, store = temp_window
    page = win._pages["settings"]
    assert hasattr(page, "motion_check")
    try:
        page._on_reduced_motion_toggled(True)
        assert motion.prefers_reduced_motion() is True
        assert store.reduced_motion is True
    finally:
        motion.set_reduced_motion(False)


def test_health_page_has_shimmer_skeleton(window):
    """test_health_page_has_shimmer_skeleton.

    Manages test health page has shimmer skeleton operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    from cortex_unified.ui.premium.skeleton import ShimmerSkeleton
    hp = window._pages["health"]
    assert isinstance(getattr(hp, "skeleton", None), ShimmerSkeleton)


# ---------------------------------------------------------------------------
#  Tactile press feedback + bento dashboard
# ---------------------------------------------------------------------------

def test_press_feedback_sinks_and_restores(app):
    """test_press_feedback_sinks_and_restores.

    Manages test press feedback sinks and restores operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QPushButton
    from cortex_unified.ui.premium import motion
    b = QPushButton("x")
    b.move(20, 20)
    motion.press_feedback(b, sink=3)
    b.pressed.emit()
    assert b._press_active is True
    assert b._press_anim.endValue() == QPoint(20, 23)   # sunk down by 3px
    b.released.emit()
    assert b._press_anim.endValue() == QPoint(20, 20)   # eased back home


def test_press_feedback_respects_reduced_motion(app):
    """test_press_feedback_respects_reduced_motion.

    Manages test press feedback respects reduced motion operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from PySide6.QtWidgets import QPushButton
    from cortex_unified.ui.premium import motion
    b = QPushButton("x")
    motion.press_feedback(b)
    motion.set_reduced_motion(True)
    try:
        b.pressed.emit()
        assert getattr(b, "_press_active", False) is False   # no motion at all
    finally:
        motion.set_reduced_motion(False)


def test_bento_tile_hover_in_stylesheet(app):
    """test_bento_tile_hover_in_stylesheet.

    Manages test bento tile hover in stylesheet operations and coordinates related state changes for the component.

    Args:
        app: The app parameter.
    """
    from cortex_unified.ui.premium.theme import THEMES, build_stylesheet
    for palette in THEMES.values():
        qss = build_stylesheet(palette)
        assert "QFrame#BentoTile" in qss
        assert "QFrame#BentoTile:hover" in qss


def test_dashboard_uses_bento_tiles(window):
    """test_dashboard_uses_bento_tiles.

    Manages test dashboard uses bento tiles operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    dash = window._pages["dashboard"]
    for attr in ("card_space", "card_files", "card_cats"):
        tile = getattr(dash, attr)
        assert tile.objectName() == "BentoTile"
    # The hero gauge and metric setters are preserved by the restructure.
    assert hasattr(dash, "gauge")
    dash.card_space.set_value("1.2 GB")
    assert dash.card_space._value.text() == "1.2 GB"


# ---------------------------------------------------------------------------
#  Clarity / layout fixes: badge rendering, processes density, health columns
# ---------------------------------------------------------------------------

def test_badge_uses_rgba_not_ambiguous_hex(app):
    """Badges must build their translucent fill from rgba() - an 8-digit
    #RRGGBBAA hex is parsed unreliably by Qt QSS and made the pills look
    muddy/distorted."""
    from cortex_unified.ui.premium.theme import THEMES
    from cortex_unified.ui.premium.widgets import Badge
    for kind in ("low", "medium", "high"):
        ss = Badge(THEMES["dark"], kind).styleSheet()
        assert "rgba(" in ss                       # explicit, well-defined alpha
        assert "background-color: rgba(" in ss


def test_processes_memory_details_collapsed_by_default(window):
    """The long memory explanation must be collapsed (progressive disclosure)
    so it doesn't squeeze the process table; the toggle reveals it."""
    pp = window._pages["processes"]
    assert hasattr(pp, "why_btn") and hasattr(pp, "mem_summary")
    assert pp.breakdown.isHidden() is True         # collapsed on load
    pp._toggle_why(True)
    assert pp.breakdown.isHidden() is False        # expands on demand
    pp._toggle_why(False)
    assert pp.breakdown.isHidden() is True


def test_health_check_columns_size_to_content(window):
    """The Check + Fix columns size to content so "Fix ->" is never clipped,
    while Detail stretches to fill the remaining width."""
    from PySide6.QtWidgets import QHeaderView
    hp = window._pages["health"]
    hdr = hp.tbl.horizontalHeader()
    assert hdr.sectionResizeMode(1) == QHeaderView.ResizeMode.ResizeToContents
    assert hdr.sectionResizeMode(2) == QHeaderView.ResizeMode.Stretch
    assert hdr.sectionResizeMode(3) == QHeaderView.ResizeMode.ResizeToContents


# ---------------------------------------------------------------------------
#  Leftover scanner (post-uninstall residual cleanup) - dedicated page
# ---------------------------------------------------------------------------

def test_uninstaller_page_has_leftover_section(window):
    """test_uninstaller_page_has_leftover_section.

    Manages test uninstaller page has leftover section operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    lp = window._pages["leftovers"]
    for attr in ("leftover_scan_btn", "orphan_scan_btn", "clean_leftover_btn",
                 "leftover_tbl", "leftover_state"):
        assert hasattr(lp, attr), attr
    # Clean starts disabled: nothing reviewed yet.
    assert lp.clean_leftover_btn.isEnabled() is False


def test_leftover_findings_populate_table_and_status(window):
    """test_leftover_findings_populate_table_and_status.

    Manages test leftover findings populate table and status operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    lp = window._pages["leftovers"]
    findings = [
        {"kind": "folder", "path": r"C:\x\AppData\Local\Zeta",
         "size_bytes": 4096, "score": 8, "level": "VeryGood",
         "reasons": ["+4 folder is completely empty"]},
        {"kind": "registry", "path": r"HKCU\SOFTWARE\Zeta",
         "size_bytes": 0, "score": 4, "level": "Good",
         "reasons": ["+2 key name match at depth 0"]},
    ]
    lp._on_leftovers(findings)
    assert lp.leftover_table.model.rowCount() == 2
    assert lp.leftover_state.isHidden() or not lp.leftover_state.isVisible()


def test_leftover_clean_button_needs_selection(window):
    """test_leftover_clean_button_needs_selection.

    Manages test leftover clean button needs selection operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
    """
    lp = window._pages["leftovers"]
    lp._on_leftovers([
        {"kind": "folder", "path": r"C:\x\Zeta", "size_bytes": 1,
         "score": 6, "level": "VeryGood", "reasons": []},
    ])
    lp.clean_leftover_btn.setEnabled(False)
    lp._on_leftover_select()
    assert lp.clean_leftover_btn.isEnabled() is False


def test_leftover_scan_without_pending_shows_hint(window, monkeypatch):
    """Clicking Scan with no recorded uninstall must hint, never crash.

    Manages test leftover scan without pending shows hint operations and coordinates related state changes for the component.

    Args:
        window: Parent window or shell controller instance.
        monkeypatch: The monkeypatch parameter.
    """
    from PySide6.QtWidgets import QMessageBox
    lp = window._pages["leftovers"]
    shown = []
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: shown.append(a)))
    window._pending_leftover_apps.clear()      # the real handoff buffer
    lp._scan_leftovers()
    assert shown, "expected the 'nothing to scan' hint"


def test_leftover_clean_worker_recycles_and_reports(tmp_path, monkeypatch):
    """LeftoverCleanWorker routes findings through LeftoverCleaner.

    Manages test leftover clean worker recycles and reports operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
        monkeypatch: The monkeypatch parameter.
    """
    import cortex_unified.ui.premium.system_pages as sp
    calls = {}

    class FakeCleaner:
        """Fakecleaner.

        Manages FakeCleaner operations and coordinates related state changes for the component.
        """
        def __init__(self):
            """Initialize the instance and configure internal state.

            Sets up sub-widgets, event signal connections, and default options.
            """
            pass

        def clean(self, models, create_restore_point=False,
                  exclusions=None, cancel_event=None):
            """clean.

            Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

            Args:
                models: The models parameter.
                create_restore_point: The create restore point parameter.
                exclusions: Error message string or exception instance.
                cancel_event: Threading event or callable to check for cancellation.
            """
            assert create_restore_point is False
            assert exclusions is None
            calls["paths"] = [m.path for m in models]
            from cortex_unified.system_tools.leftover_cleaner import CleanOutcome
            return [CleanOutcome(models[0].path, models[0].kind, True,
                                 "recycled")]

    from cortex_unified.system_tools import leftover_cleaner as lc
    monkeypatch.setattr(lc, "LeftoverCleaner", FakeCleaner)
    worker = sp.LeftoverCleanWorker([
        {"kind": "folder", "path": str(tmp_path / "gone"),
         "size_bytes": 10, "score": 8, "level": "VeryGood", "reasons": []},
    ])
    results = []
    worker.finished.connect(lambda out: results.append(out))
    worker.run()
    assert results and results[0][0]["disposition"] == "recycled"
    assert calls["paths"] == [str(tmp_path / "gone")]


def test_leftover_clean_worker_requests_restore_point_when_asked(
        tmp_path, monkeypatch):
    """The checkbox's choice reaches the cleaner as create_restore_point.

    Manages test leftover clean worker requests restore point when asked operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
        monkeypatch: The monkeypatch parameter.
    """
    import cortex_unified.ui.premium.system_pages as sp
    seen = {}

    class FakeCleaner:
        """Fakecleaner.

        Manages FakeCleaner operations and coordinates related state changes for the component.
        """
        def __init__(self):
            """Initialize the instance and configure internal state.

            Sets up sub-widgets, event signal connections, and default options.
            """
            pass

        def clean(self, models, create_restore_point=False,
                  exclusions=None, cancel_event=None):
            """clean.

            Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

            Args:
                models: The models parameter.
                create_restore_point: The create restore point parameter.
                exclusions: Error message string or exception instance.
                cancel_event: Threading event or callable to check for cancellation.
            """
            seen["restore"] = create_restore_point
            from cortex_unified.system_tools.leftover_cleaner import CleanOutcome
            return [CleanOutcome(models[0].path, models[0].kind, True,
                                 "recycled")]

    from cortex_unified.system_tools import leftover_cleaner as lc
    monkeypatch.setattr(lc, "LeftoverCleaner", FakeCleaner)
    worker = sp.LeftoverCleanWorker(
        [{"kind": "registry", "path": r"HKCU\SOFTWARE\Z",
          "size_bytes": 0, "score": 4, "level": "Good", "reasons": []}],
        create_restore_point=True)
    results = []
    worker.finished.connect(results.append)
    worker.run()
    assert seen["restore"] is True
    assert results[0][0]["ok"] is True


def test_leftover_scan_worker_emits_sorted_findings(monkeypatch):
    """Findings come back as plain dicts sorted by score descending.

    Manages test leftover scan worker emits sorted findings operations and coordinates related state changes for the component.

    Args:
        monkeypatch: The monkeypatch parameter.
    """
    import cortex_unified.ui.premium.system_pages as sp
    from cortex_unified.system_tools import leftover_cleaner as lc

    class FakeScanner:
        """Fakescanner.

        Manages FakeScanner operations and coordinates related state changes for the component.
        """
        def __init__(self, installed_apps=None, exclusions=None,
                     cancel_event=None, policy=None):
            """__init__.

            Initializes the instance and configures internal state.

            Args:
                installed_apps: The installed apps parameter.
                exclusions: Error message string or exception instance.
                cancel_event: Threading event or callable to check for cancellation.
                policy: The policy parameter.
            """
            assert installed_apps == []
            self._calls = 0

        def scan_app(self, app):
            """scan_app.

            Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

            Args:
                app: The app parameter.
            """
            assert app.name == "ZetaEditor"
            return [
                lc.LeftoverFinding(kind="folder", path=r"C:\low",
                                   score=2, level="Good"),
                lc.LeftoverFinding(kind="registry", path=r"HKCU\SOFTWARE\hi",
                                   score=9, level="VeryGood"),
            ]

    monkeypatch.setattr(lc, "LeftoverScanner", FakeScanner)
    worker = sp.LeftoverScanWorker([{"name": "ZetaEditor",
                                     "publisher": "Zeta"}])
    out = []
    worker.finished.connect(out.append)
    worker.run()
    assert len(out) == 1
    rows = out[0]
    assert rows[0]["path"] == r"HKCU\SOFTWARE\hi"     # highest score first
    assert all(isinstance(r, dict) for r in rows)


def test_leftover_workers_support_cooperative_cancel():
    """cancel() must exist on all three workers (window shutdown calls it).

    Manages test leftover workers support cooperative cancel operations and coordinates related state changes for the component.
    """
    from cortex_unified.ui.premium.system_pages import (
        LeftoverScanWorker,
        OrphanScanWorker,
        LeftoverCleanWorker,
    )
    scan = LeftoverScanWorker([{"name": "X"}])
    orphan = OrphanScanWorker()
    clean = LeftoverCleanWorker([])
    for w in (scan, orphan, clean):
        assert callable(getattr(w, "cancel", None))
        w.cancel()
    assert scan._cancel.is_set() and orphan._cancel.is_set() \
        and clean._cancel.is_set()


def test_uninstall_hands_off_metadata_to_leftover_page(window, monkeypatch):
    """Uninstaller page captures app metadata; Leftover Scanner consumes it.

    This is the cross-page handoff: without it, 'Scan for Leftovers' on the
    dedicated page would never have anything to scan.
    """
    import cortex_unified.ui.premium.system_pages as sp
    from PySide6.QtWidgets import QMessageBox

    shown: list = []
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: shown.append(a)))
    # launched==0 path shows a warning modal - must never exec() in tests.
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: None))

    app_record = {"name": "ZetaEditor", "publisher": "ZetaSoft",
                  "install_location": r"C:\Program Files\ZetaEditor"}
    window._pending_leftover_apps.clear()

    up = window._pages["uninstaller"]
    monkeypatch.setattr(up, "_selected_apps", lambda: [app_record],
                        raising=False)
    up._uninstall()
    assert window._pending_leftover_apps, "metadata not captured"
    assert window._pending_leftover_apps[0]["name"] == "ZetaEditor"

    # The Leftover Scanner page consumes the same buffer via its worker.
    seen_apps: list = []

    def fake_worker_init(self, apps, exclusions=None):
        """fake_worker_init.

        Manages fake worker init operations and coordinates related state changes for the component.

        Args:
            apps: The apps parameter.
            exclusions: Error message string or exception instance.
        """
        from PySide6.QtCore import QObject
        QObject.__init__(self)                 # initialise the Qt shell first
        self._apps = list(apps)
        seen_apps.append(list(apps))
        from threading import Event
        self._cancel = Event()

    def fake_worker_run(self):
        """fake_worker_run.

        Manages fake worker run operations and coordinates related state changes for the component.
        """
        self.finished.emit([{"kind": "folder", "path": r"C:\x\Zeta",
                             "size_bytes": 1, "score": 8,
                             "level": "VeryGood", "reasons": []}]
                           if self._apps else [])

    monkeypatch.setattr(sp.LeftoverScanWorker, "__init__", fake_worker_init)
    monkeypatch.setattr(sp.LeftoverScanWorker, "run", fake_worker_run)

    lp = window._pages["leftovers"]
    lp._scan_leftovers()
    assert seen_apps and seen_apps[0][0]["name"] == "ZetaEditor"
    assert window._pending_leftover_apps == [], "buffer must be consumed"



