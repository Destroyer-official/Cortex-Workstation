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
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def window(app):
    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import PremiumMainWindow
    apply_theme(app, "dark")
    win = PremiumMainWindow("dark")
    win.resize(1180, 760)
    yield win
    win.close()


def test_stylesheet_builds_for_both_themes(app):
    from cortex_unified.ui.premium.theme import THEMES, build_stylesheet
    for name, palette in THEMES.items():
        qss = build_stylesheet(palette)
        assert "QPushButton#Primary" in qss
        assert palette.accent in qss


def test_all_pages_present(window):
    assert set(window._pages) == {
        "dashboard", "health", "duplicates", "photos", "dupfolders", "large", "empty",
        "analyzer", "brokenlinks", "packages", "updater", "drives", "diskhealth",
        "bootperf", "winupdate", "repair", "schedule", "performance", "privacy", "startup", "processes", "network",
        "traffic", "netmap", "landevices", "nettools", "loadtest", "firewall",
        "extensions", "drivers", "uninstaller", "telemetry", "registry", "security",
        "storagesense", "secrets", "shred", "backups", "report", "sysinfo", "settings",
    }


def test_navigate_every_page(window):
    """Selecting each page must switch the stack without error."""
    for pid in window._pages:
        window._select(pid)
        assert window._stack.currentWidget() is window._pages[pid]


def test_theme_toggle_does_not_crash(window):
    window.set_theme("light")
    assert window.theme_name == "light"
    window.set_theme("dark")
    assert window.theme_name == "dark"


def test_navigation_switches_pages(window):
    window._select("duplicates")
    assert window._stack.currentWidget() is window._pages["duplicates"]
    window._select("dashboard")
    assert window._stack.currentWidget() is window._pages["dashboard"]


def test_dashboard_populates_from_report(window):
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
    """Expanding a category must lazily reveal its contents (preview)."""
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
    """The drill-down grouping helpers must aggregate correctly and fast."""
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
    """App caches must group by their owning app with friendly names."""
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
    """Unchecking an app/folder in the preview must exclude it from cleaning."""
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
    dash = window._pages["dashboard"]
    dash.gauge.animate_to(75.0, display="75")
    # value property is animated; end value must be within range
    assert 0.0 <= dash.gauge.value <= 100.0


def test_render_to_pixmap(window):
    """The window must render to a non-empty pixmap (catches paint crashes)."""
    window.show()
    pix = window.grab()
    assert pix.width() > 0 and pix.height() > 0


def test_responsive_resize(window):
    """Content must adapt (and render) across small and large window sizes."""
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
    """The per-core CPU bar widget must accept values and paint without error."""
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
    from cortex_unified.ui.premium.theme import THEMES
    from cortex_unified.ui.premium.widgets import StatCard
    card = StatCard(THEMES["dark"], "Test", "0")
    card.set_value("42", animate=True)      # animated path
    assert card._value.text() == "42"
    card.set_value("99")                    # plain path
    assert card._value.text() == "99"


def test_shred_page_present_and_wired(window):
    page = window._pages["shred"]
    assert hasattr(page, "shred_btn") and hasattr(page, "passes")
    # No file selected yet -> shred action disabled.
    assert page.shred_btn.isEnabled() is False


def test_recycle_worker_actually_removes(app, tmp_path):
    """DeleteSelectedWorker (recycle) must remove a real file, run synchronously."""
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
    """ShredWorker with force_flash must overwrite+delete regardless of medium."""
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
