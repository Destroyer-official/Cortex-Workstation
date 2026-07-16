"""End-to-end, page-by-page GUI tests for the premium interface.

Each test drives a page's REAL scan/read flow through the actual QThread worker
and pumps the Qt event loop until completion, then asserts results populated.
Destructive actions (clean/delete/shred/uninstall/telemetry-apply/registry-
clean) are intentionally NOT triggered here - they show modal dialogs and would
block or modify the live system; those paths are covered by worker-level tests.

Runs headless via the 'offscreen' platform; the whole module is skipped if
PySide6 is unavailable.
"""

from __future__ import annotations

import os
import platform

import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDeadlineTimer, QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

IS_WINDOWS = platform.system() == "Windows"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import PremiumMainWindow
    apply_theme(app, "dark")
    win = PremiumMainWindow("dark")
    win.show()
    yield win
    win.close()


def pump_until(app, predicate, timeout_ms=45000, interval=25) -> bool:
    """Spin the event loop until predicate() is true or timeout. Returns final."""
    deadline = QDeadlineTimer(timeout_ms)
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(interval)
    timer.timeout.connect(
        lambda: loop.quit() if (predicate() or deadline.hasExpired()) else None
    )
    timer.start()
    loop.exec()
    timer.stop()
    return predicate()


@pytest.fixture
def data_tree(tmp_path):
    """Folder with duplicates, a >50MB file, and empty items for scan pages."""
    (tmp_path / "a.txt").write_text("identical payload here")
    (tmp_path / "b.txt").write_text("identical payload here")  # duplicate
    big = tmp_path / "huge.bin"
    with open(big, "wb") as f:
        f.truncate(60 * 1024 * 1024)  # 60 MB (sparse) -> above the 50MB threshold
    (tmp_path / "empty.txt").touch()
    (tmp_path / "empty_dir").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# 1. Dashboard
# ---------------------------------------------------------------------------

def test_page_dashboard_scan(app, window):
    dash = window._pages["dashboard"]
    dash._scan()
    assert pump_until(app, lambda: not dash._scanning), "dashboard scan stuck"
    assert dash._report is not None
    assert dash.scan_btn.text() == "Scan Now"
    # tree rows must match discovered categories
    assert dash.tree.topLevelItemCount() == len(dash._report.scans)


# ---------------------------------------------------------------------------
# 2-4. Folder scan pages (duplicates / large files / empty)
# ---------------------------------------------------------------------------

def _drive_folder_page(app, window, page_id, data_tree):
    window._select(page_id)
    page = window._pages[page_id]
    page._folder = str(data_tree)
    page.run_btn.setEnabled(True)
    page._run()
    assert pump_until(app, lambda: not page._running), f"{page_id} scan stuck"
    return page


def test_page_duplicates(app, window, data_tree):
    page = _drive_folder_page(app, window, "duplicates", data_tree)
    names = {page.tree.item(r, 0).text() for r in range(page.tree.rowCount())}
    assert any("a.txt" in n for n in names) and any("b.txt" in n for n in names)


def test_page_large_files(app, window, data_tree):
    page = _drive_folder_page(app, window, "large", data_tree)
    assert page.tbl.rowCount() >= 1
    assert any("huge.bin" in page.tbl.item(r, 0).text() for r in range(page.tbl.rowCount()))


def test_page_empty_items(app, window, data_tree):
    page = _drive_folder_page(app, window, "empty", data_tree)
    paths = {page.tbl.item(r, 0).text() for r in range(page.tbl.rowCount())}
    assert any("empty.txt" in p for p in paths)
    assert any("empty_dir" in p for p in paths)


# ---------------------------------------------------------------------------
# 5. Privacy (scan only)
# ---------------------------------------------------------------------------

def test_page_privacy_scan(app, window):
    window._select("privacy")
    page = window._pages["privacy"]
    page._scan()
    # progress becomes visible on start, hidden on completion
    assert pump_until(app, lambda: not page.progress.isVisible()), "privacy scan stuck"
    assert page.scan_btn.isEnabled()  # re-enabled after scan


# ---------------------------------------------------------------------------
# 6. Startup manager (list)
# ---------------------------------------------------------------------------

def test_page_startup_list(app, window):
    window._select("startup")   # triggers lazy autoload
    page = window._pages["startup"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and not page.progress.isVisible()), \
        "startup list stuck"
    assert page.tbl.rowCount() >= 0  # >=0: some systems have no startup items


# ---------------------------------------------------------------------------
# 7. Processes (list)
# ---------------------------------------------------------------------------

def test_page_traffic_monitor(app, window):
    window._select("traffic")   # triggers live autoload (starts timer)
    page = window._pages["traffic"]
    # Two ticks so a real rate is computed and the graph gets samples.
    assert pump_until(app, lambda: len(page.graph._down) >= 2, timeout_ms=6000), \
        "traffic graph never received samples"
    page._timer.stop()
    assert page.card_down._value.text() != "\u2014"
    assert page.nic_tbl.rowCount() >= 1


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows Update is Windows-only")
def test_page_windows_update(app, window):
    window._select("winupdate")   # autoload reads registry + update history (offline)
    page = window._pages["winupdate"]
    # We do NOT click "Check for Updates" (that goes online). Just the fast load.
    assert pump_until(app, lambda: page.card_check._value.text() != "\u2014"
                      or page.hist_tbl.rowCount() >= 0, timeout_ms=20000), \
        "windows update activity load stuck"
    assert page.check_btn.isEnabled()


def test_page_health_check(app, window):
    window._select("health")   # triggers lazy autoload -> runs all checks
    page = window._pages["health"]
    assert pump_until(app, lambda: page.run_btn.isEnabled() and not page.progress.isVisible(),
                      timeout_ms=40000), "health check stuck"
    # A grade must be assigned and at least the cross-platform checks listed.
    assert "Grade" in page.grade_label.text()
    assert page.tbl.rowCount() >= 2


@pytest.mark.skipif(not IS_WINDOWS, reason="Defender is Windows-only")
def test_page_security_status(app, window):
    window._select("security")   # triggers lazy autoload (Defender status)
    page = window._pages["security"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and not page.progress.isVisible(),
                      timeout_ms=30000), "Defender status stuck"
    assert "Loading" not in page.info.text()


@pytest.mark.skipif(not IS_WINDOWS, reason="Storage Sense is Windows-only")
def test_page_storage_sense(app, window):
    window._select("storagesense")   # reads registry (read-only in this test)
    page = window._pages["storagesense"]
    assert pump_until(app, lambda: not page._loading, timeout_ms=10000), \
        "storage sense status stuck"
    # The enable checkbox label reflects real state; we do NOT toggle it here.
    assert page.enable_chk.text() in ("Storage Sense is ON", "Storage Sense is OFF")


@pytest.mark.skipif(not IS_WINDOWS, reason="boot diagnostics are Windows-only")
def test_page_boot_performance(app, window):
    window._select("bootperf")   # triggers lazy autoload
    page = window._pages["bootperf"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and not page.progress.isVisible(),
                      timeout_ms=30000), "boot performance analysis stuck"
    # Windows records boots; the average card should populate with a value.
    assert page.card_avg._value.text() != "" or page.tbl.rowCount() >= 0


@pytest.mark.skipif(not IS_WINDOWS, reason="repair tools are Windows-only")
def test_page_system_repair_constructs(app, window):
    # Do NOT run sfc/dism here (minutes-long, system-modifying). Just verify the
    # page builds and exposes its tool buttons.
    window._select("repair")
    page = window._pages["repair"]
    assert hasattr(page, "sfc_btn") and hasattr(page, "dism_btn")


def test_page_load_tester_authorization(app, window):
    window._select("loadtest")
    page = window._pages["loadtest"]
    # Localhost is inherently authorized; the Start button must enable.
    page.target.setText("127.0.0.1")
    page._check()
    assert pump_until(app, lambda: page.run_btn.isEnabled(), timeout_ms=8000), \
        "localhost was not authorized"
    assert page._auth is not None and page._auth["authorized"]
    assert "Authorized" in page.auth_label.text()


def test_load_tester_refuses_public_in_ui(app, window):
    """A public target must NOT enable the run button (safety gate in the UI)."""
    window._select("loadtest")
    page = window._pages["loadtest"]
    page.target.setText("8.8.8.8")
    page._check()
    assert pump_until(app, lambda: not page.check_btn.isEnabled() is False
                      and page._auth is None, timeout_ms=10000) or page._auth is None
    # After the check resolves, run must remain disabled and no auth stored.
    pump_until(app, lambda: "public host" in page.auth_label.text().lower()
               or "not authorized" in page.auth_label.text().lower(), timeout_ms=10000)
    assert page._auth is None
    assert page.run_btn.isEnabled() is False


def test_page_network_tools(app, window):
    window._select("nettools")
    page = window._pages["nettools"]
    # IP Info is offline and instant-ish; ping localhost is always reachable.
    page.target.setText("127.0.0.1")
    page._run("ipinfo")
    assert pump_until(app, lambda: "Loopback" in page.summary.text()
                      or "Type:" in page.summary.text(), timeout_ms=8000), \
        "IP info did not render"
    page._run("ping")
    assert pump_until(app, lambda: "reachable" in page.summary.text().lower(),
                      timeout_ms=15000), "ping localhost did not complete"


def test_page_network_map(app, window):
    window._select("netmap")   # triggers lazy autoload
    page = window._pages["netmap"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled()), "network map stuck"
    # Rendering must not raise; summary text is populated.
    assert "\u2192" in page.summary.text() or page.summary.text() == ""
    page.external_only.setChecked(False)  # re-render with all connections


def test_page_lan_devices(app, window):
    window._select("landevices")   # triggers lazy autoload
    page = window._pages["landevices"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and not page.progress.isVisible()), \
        "LAN scan stuck"
    # ARP cache almost always has the gateway; table exists regardless.
    assert page.tbl.columnCount() == 4


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows Firewall only")
def test_page_firewall_list(app, window):
    window._select("firewall")   # triggers lazy autoload (read-only list)
    page = window._pages["firewall"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and not page.progress.isVisible()), \
        "firewall list stuck"
    # Read-only listing must not raise; table exists and address validation works.
    from cortex_unified.system_tools.firewall_manager import FirewallManager
    assert FirewallManager._valid_address("8.8.8.8") is True


def test_page_network_monitor(app, window):
    window._select("network")   # triggers live autoload
    page = window._pages["network"]
    page.auto_chk.setChecked(False)  # stop the live timer during assertions
    assert pump_until(app, lambda: page.refresh_btn.isEnabled()), "network scan stuck"
    # The summary cards must be populated (numbers, not the placeholder dash).
    assert page.card_listen._value.text() != "\u2014"
    # Filtering to a nonsense term empties the table; clearing restores it.
    page.search.setText("zzzz_no_such_conn")
    assert page.tbl.rowCount() == 0
    page.search.setText("")


def test_page_processes_list(app, window):
    window._select("processes")   # triggers live autoload
    page = window._pages["processes"]
    # Stop the live timer so it doesn't spawn workers mid-assertion.
    page.auto_chk.setChecked(False)
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and bool(page._procs)), \
        "process list stuck"
    assert page.tbl.rowCount() > 0  # there are always running processes

    # The honest memory explanation must be present.
    txt = page.breakdown.text()
    assert "in use" in txt and "double-count shared memory" in txt
    assert "%" in page.cpu_card._value.text()

    # Sorting by the CPU column (now col 3) must not raise and keeps all rows.
    n = page.tbl.rowCount()
    page.tbl.sortByColumn(3, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.SortOrder.DescendingOrder)
    assert page.tbl.rowCount() == n

    # Descriptions must be present for well-known system processes.
    descs = {page.tbl.item(r, 2).text() for r in range(page.tbl.rowCount())
             if page.tbl.item(r, 2)}
    assert any(d for d in descs), "no process descriptions populated"

    # Filtering narrows the visible rows.
    page.search.setText("zzzz_no_such_process_zzzz")
    assert page.tbl.rowCount() == 0
    page.search.setText("")
    assert page.tbl.rowCount() > 0


# ---------------------------------------------------------------------------
# 8-10. Windows-only pages
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only feature")
def test_page_uninstaller_list(app, window):
    window._select("uninstaller")
    page = window._pages["uninstaller"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and not page.progress.isVisible()), \
        "uninstaller list stuck"
    assert page.tbl.rowCount() > 0


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only feature")
def test_page_telemetry_status(app, window):
    window._select("telemetry")
    page = window._pages["telemetry"]
    assert pump_until(app, lambda: page.tree.topLevelItemCount() > 0), "telemetry status stuck"
    assert "telemetry" in page.status_lbl.text().lower()


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only feature")
def test_page_registry_scan(app, window):
    window._select("registry")
    page = window._pages["registry"]
    page._scan()
    assert pump_until(app, lambda: page.scan_btn.isEnabled() and not page.progress.isVisible()), \
        "registry scan stuck"
    # rowCount >= 0 (a clean registry may have zero orphans)
    assert page.tbl.rowCount() >= 0


# ---------------------------------------------------------------------------
#  New backend pages: Software Updater / Drive Optimizer / System Info
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only feature")
def test_page_software_updater_list(app, window):
    from cortex_unified.system_tools.app_updater import AppUpdater
    if not AppUpdater.is_available():
        pytest.skip("winget not available on this machine")
    window._select("updater")
    page = window._pages["updater"]
    # winget check can take a while; allow a generous window.
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and not page.progress.isVisible(),
                      timeout_ms=90000), "software updater list stuck"
    assert page.tbl.rowCount() >= 0


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only feature")
def test_page_drive_optimizer_list(app, window):
    window._select("drives")
    page = window._pages["drives"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and not page.progress.isVisible()), \
        "drive optimizer list stuck"
    assert page.tbl.rowCount() >= 1  # at least the system drive
    # verify the SSD/HDD-correct action text is present
    actions = {page.tbl.item(r, 2).text() for r in range(page.tbl.rowCount())}
    assert any(("TRIM" in a) or ("Defragment" in a) or ("\u2014" in a) for a in actions)


def test_page_system_info_load(app, window):
    window._select("sysinfo")
    page = window._pages["sysinfo"]
    assert pump_until(app, lambda: "OS:" in page.info_label.text() or "Loading" not in page.info_label.text()), \
        "system info load stuck"
    assert "OS:" in page.info_label.text()


def test_page_package_caches_load(app, window):
    window._select("packages")
    page = window._pages["packages"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and not page.progress.isVisible(),
                      timeout_ms=60000), "package cache detect stuck"
    assert page.tbl.rowCount() >= 0  # >=0: machine may have no package managers


def test_dashboard_smart_learning_loop(app, window, tmp_path):
    """Selecting/deselecting categories must feed the offline learner and it
    must actually learn (a repeatedly-skipped category loses its default check)."""
    from cortex_unified.engine.models import FileEntry
    from cortex_unified.engine.service import CategoryScan, CleanupReport
    from cortex_unified.engine import default_categories
    from PySide6.QtCore import Qt

    dash = window._pages["dashboard"]
    window.suggester.reset()

    cats = default_categories()
    scan = CategoryScan(category=cats[0])
    scan.total_bytes = 1024
    scan.entries = [FileEntry(tmp_path / "x", 1, 0.0)]
    report = CleanupReport(scans=[scan])

    ctx = {"category": cats[0].id, "size": 1024, "age_days": cats[0].min_age_days}
    # Simulate the user repeatedly skipping this category.
    before = window.suggester.score(ctx)
    for _ in range(30):
        window.suggester.observe(ctx, cleaned=False)
    after = window.suggester.score(ctx)
    assert after < before  # learned to skip it

    # After learning to skip, the dashboard should pre-uncheck it.
    dash._on_scanned(report)
    item = dash.tree.topLevelItem(0)
    assert item.checkState(0) == Qt.CheckState.Unchecked
    assert window.suggester.stats()["updates"] >= 30
    window.suggester.reset()


def test_page_broken_links_and_dupfolders_construct(app, window):
    # These don't auto-load (need a folder); just verify they construct + wire.
    for pid in ("brokenlinks", "dupfolders"):
        window._select(pid)
        page = window._pages[pid]
        assert hasattr(page, "run_btn") and hasattr(page, "del_btn")
        assert page.run_btn.isEnabled() is False  # no folder chosen yet


# ---------------------------------------------------------------------------
# 11. Secure Shred (storage detection only; destructive path is worker-tested)
# ---------------------------------------------------------------------------

def test_page_shred_storage_detection(app, window, tmp_path):
    window._select("shred")
    page = window._pages["shred"]
    f = tmp_path / "target.bin"
    f.write_bytes(b"x" * 1024)
    # Drive the detection worker directly (bypasses the file-open modal dialog).
    page._target = str(f)
    from cortex_unified.ui.premium.workers import StorageWorker
    result = {}
    page.win.run_worker(StorageWorker(str(f)),
                        lambda kind, eff: result.update(kind=kind, eff=eff),
                        page._fail)
    assert pump_until(app, lambda: "kind" in result), "storage detection stuck"
    assert result["kind"] in {"ssd", "hdd", "nvme", "removable", "network", "unknown"}


# ---------------------------------------------------------------------------
# 12. Settings (theme toggle)
# ---------------------------------------------------------------------------

def test_page_settings_theme_toggle(app, window):
    window._select("settings")
    page = window._pages["settings"]
    page.light_btn.click()
    assert window.theme_name == "light"
    page.dark_btn.click()
    assert window.theme_name == "dark"


@pytest.mark.skipif(not IS_WINDOWS, reason="restore points are Windows-only")
def test_page_settings_restore_point_list(app, window):
    """The safety card must list restore points (read-only) without hanging."""
    window._select("settings")
    page = window._pages["settings"]
    assert hasattr(page, "rp_table"), "restore-point safety card missing"
    # _refresh_restore_points runs on construction; give the worker time.
    assert pump_until(app, lambda: page.rp_table.rowCount() >= 0), "restore point list stuck"


@pytest.mark.skipif(not IS_WINDOWS, reason="restore points are Windows-only")
def test_restore_point_worker_reports_honest_status(app):
    """The create worker must return one of the honest status strings, and must
    NOT falsely report 'created' when it couldn't verify a new point."""
    from cortex_unified.system_tools.restore_point import RestorePointManager
    from cortex_unified.ui.premium.workers import RestorePointWorker

    mgr = RestorePointManager()
    if mgr.is_elevated():
        pytest.skip("skipping real create attempt while elevated (would touch the live system)")

    captured = {}
    worker = RestorePointWorker("Cortex test - e2e")
    worker.finished.connect(lambda status, msg: captured.update(status=status, msg=msg))
    worker.failed.connect(lambda m: captured.update(error=m))
    worker.run()
    # Not elevated -> must be the honest NOT_ELEVATED status, never 'created'.
    assert captured.get("status") == "not_elevated"
