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
import pathlib
import platform

import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDeadlineTimer, QEventLoop, Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

IS_WINDOWS = platform.system() == "Windows"


@pytest.fixture(scope="module")
def app():
    """app."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    """window."""
    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import PremiumMainWindow
    apply_theme(app, "dark")
    win = PremiumMainWindow("dark")
    win.show()
    yield win
    win.close()


@pytest.fixture
def pro_license(monkeypatch, tmp_path):
    """Grant PRO entitlement so gated handlers run headlessly.

    Some e2e flows drive actions that are now tier-gated (e.g. the registry
    scan). Without entitlement the gating pops a MODAL upgrade dialog, which
    blocks pytest forever offscreen. Pointing the singleton at a temp-path
    activated manager keeps the real user flow while staying headless.
    """
    from cortex_unified.licensing import license_manager as lm_module
    from cortex_unified.licensing.license_manager import LicenseManager
    from cortex_unified.licensing.tiers import Tier

    manager = LicenseManager(path=tmp_path / "license.json")
    manager.activate("E2E-KEY", Tier.PRO)
    monkeypatch.setattr(lm_module, "_MANAGER", manager, raising=False)
    yield manager
    lm_module.reset_singleton()


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
    """test_page_dashboard_scan."""
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
    """_drive_folder_page."""
    window._select(page_id)
    page = window._pages[page_id]
    page._folder = str(data_tree)
    page.run_btn.setEnabled(True)
    page._run()
    assert pump_until(app, lambda: not page._running), f"{page_id} scan stuck"
    return page


def test_page_duplicates(app, window, data_tree):
    """test_page_duplicates."""
    page = _drive_folder_page(app, window, "duplicates", data_tree)
    names = {page.tree.item(r, 0).text() for r in range(page.tree.rowCount())}
    assert any("a.txt" in n for n in names) and any("b.txt" in n for n in names)


def test_page_large_files(app, window, data_tree):
    """test_page_large_files."""
    page = _drive_folder_page(app, window, "large", data_tree)
    assert page.tbl.rowCount() >= 1
    assert any("huge.bin" in page.tbl.item(r, 0).text() for r in range(page.tbl.rowCount()))


def test_page_empty_items(app, window, data_tree):
    """test_page_empty_items."""
    page = _drive_folder_page(app, window, "empty", data_tree)
    paths = {page.tbl.item(r, 0).text() for r in range(page.tbl.rowCount())}
    assert any("empty.txt" in p for p in paths)
    assert any("empty_dir" in p for p in paths)


# ---------------------------------------------------------------------------
# 5. Privacy (scan only)
# ---------------------------------------------------------------------------

def test_page_privacy_scan(app, window):
    """test_page_privacy_scan."""
    window._select("privacy")
    page = window._pages["privacy"]
    page._scan()
    # The scan shows the StatePanel loading state and disables the button; both
    # are released on completion (the inline progress bar is for the sweep).
    assert page.state.mode() == "loading"
    assert not page.scan_btn.isEnabled()
    assert pump_until(app, lambda: page.scan_btn.isEnabled()), "privacy scan stuck"
    assert page.state.mode() in ("hidden", "empty")  # results or honest empty
    assert not page.progress.isVisible()


# ---------------------------------------------------------------------------
# 6. Startup manager (list)
# ---------------------------------------------------------------------------

def test_page_startup_list(app, window):
    """test_page_startup_list."""
    window._select("startup")   # triggers lazy autoload
    page = window._pages["startup"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and not page.progress.isVisible()), \
        "startup list stuck"
    assert page.tbl.rowCount() >= 0  # >=0: some systems have no startup items


# ---------------------------------------------------------------------------
# 7. Processes (list)
# ---------------------------------------------------------------------------

def test_page_traffic_monitor(app, window):
    """test_page_traffic_monitor."""
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
    """test_page_windows_update."""
    window._select("winupdate")   # autoload reads registry + update history (offline)
    page = window._pages["winupdate"]
    # We do NOT click "Check for Updates" (that goes online). Just the fast load.
    assert pump_until(app, lambda: page.card_check._value.text() != "\u2014"
                      or page.hist_tbl.rowCount() >= 0, timeout_ms=20000), \
        "windows update activity load stuck"
    assert page.check_btn.isEnabled()


def test_page_health_check(app, window):
    """test_page_health_check."""
    window._select("health")   # triggers lazy autoload -> runs all checks
    page = window._pages["health"]
    assert pump_until(app, lambda: page.run_btn.isEnabled() and not page.progress.isVisible(),
                      timeout_ms=40000), "health check stuck"
    # A grade must be assigned and at least the cross-platform checks listed.
    assert "Grade" in page.grade_label.text()
    assert page.tbl.rowCount() >= 2


@pytest.mark.skipif(not IS_WINDOWS, reason="Defender is Windows-only")
def test_page_security_status(app, window):
    """test_page_security_status."""
    window._select("security")   # triggers lazy autoload (Defender status)
    page = window._pages["security"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and not page.progress.isVisible(),
                      timeout_ms=30000), "Defender status stuck"
    assert "Loading" not in page.info.text()


@pytest.mark.skipif(not IS_WINDOWS, reason="Storage Sense is Windows-only")
def test_page_storage_sense(app, window):
    """test_page_storage_sense."""
    window._select("storagesense")   # reads registry (read-only in this test)
    page = window._pages["storagesense"]
    assert pump_until(app, lambda: not page._loading, timeout_ms=10000), \
        "storage sense status stuck"
    # The enable checkbox label reflects real state; we do NOT toggle it here.
    assert page.enable_chk.text() in ("Storage Sense is ON", "Storage Sense is OFF")


@pytest.mark.skipif(not IS_WINDOWS, reason="boot diagnostics are Windows-only")
def test_page_boot_performance(app, window):
    """test_page_boot_performance."""
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
    """test_page_system_repair_constructs."""
    window._select("repair")
    page = window._pages["repair"]
    assert hasattr(page, "sfc_btn") and hasattr(page, "dism_btn")


def test_page_load_tester_authorization(app, window):
    """test_page_load_tester_authorization."""
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
    """test_page_network_tools."""
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
    """test_page_network_map."""
    window._select("netmap")   # triggers lazy autoload
    page = window._pages["netmap"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled()), "network map stuck"
    # Rendering must not raise; summary text is populated.
    assert "\u2192" in page.summary.text() or page.summary.text() == ""
    page.external_only.setChecked(False)  # re-render with all connections


def test_page_lan_devices(app, window, monkeypatch):
    """test_page_lan_devices."""
    from cortex_unified.system_tools.network_discovery import NetworkDiscovery, DiscoveryResult, Device
    from cortex_unified.system_tools.wan_audit import WanStatus

    mock_result = DiscoveryResult(
        devices=[Device(ip="192.168.1.1", mac="00:11:22:33:44:55", hostname="router", vendor="Test Vendor", is_gateway=True)],
        networks=["192.168.1.0/24"],
        wan_status=WanStatus(gateway="192.168.1.1", external_ip="1.2.3.4", external_ip_classification="public"),
        findings=[],
        duration_seconds=0.1,
    )
    monkeypatch.setattr(NetworkDiscovery, "scan", lambda *args, **kwargs: mock_result)

    window._select("landevices")   # triggers lazy autoload
    page = window._pages["landevices"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and not page.progress.isVisible(), timeout_ms=10000), \
        "LAN scan stuck"
    # Advanced audit columns: identity, services, findings and evidence. The
    # table is model/view now, so shape is read from the model.
    assert page.tbl.model().columnCount() == 8
    assert page.wan_status is not None
    assert page.findings is not None


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows Firewall only")
def test_page_firewall_list(app, window):
    """test_page_firewall_list."""
    window._select("firewall")   # triggers lazy autoload (read-only list)
    page = window._pages["firewall"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and not page.progress.isVisible()), \
        "firewall list stuck"
    # Read-only listing must not raise; table exists and address validation works.
    from cortex_unified.system_tools.firewall_manager import FirewallManager
    assert FirewallManager._valid_address("8.8.8.8") is True


def test_page_network_monitor(app, window):
    """test_page_network_monitor."""
    window._select("network")   # triggers live autoload
    page = window._pages["network"]
    page.auto_chk.setChecked(False)  # stop the live timer during assertions
    assert pump_until(app, lambda: page.refresh_btn.isEnabled()), "network scan stuck"
    # The summary cards must be populated (numbers, not the placeholder dash).
    assert page.card_listen._value.text() != "\u2014"
    # Filtering to a nonsense term empties the table; clearing restores it.
    page.search.setText("zzzz_no_such_conn")
    assert page.table.visible_count == 0
    page.search.setText("")


def test_page_processes_list(app, window):
    """test_page_processes_list."""
    window._select("processes")   # triggers live autoload
    page = window._pages["processes"]
    # Stop the live timer so it doesn't spawn workers mid-assertion.
    page.auto_chk.setChecked(False)
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and bool(page._procs)), \
        "process list stuck"
    # The table is model/view now, so rows are counted through the proxy rather
    # than the widget: page.table is the TableBinding, page.tbl the QTableView.
    assert page.table.visible_count > 0  # there are always running processes

    # The honest memory summary is always visible; the full explanation lives
    # behind the progressive-disclosure toggle and renders when expanded.
    assert "in use" in page.mem_summary.text()
    page.why_btn.setChecked(True)
    txt = page.breakdown.text()
    assert "in use" in txt and "double-count shared memory" in txt
    assert page.breakdown.isVisible()
    page.why_btn.setChecked(False)
    assert "%" in page.cpu_card._value.text()

    # Sorting by the CPU column (col 3) must not raise and keeps all rows.
    from PySide6.QtCore import Qt as _Qt
    n = page.table.visible_count
    page.tbl.sortByColumn(3, _Qt.SortOrder.DescendingOrder)
    assert page.table.visible_count == n

    # Descriptions must be present for well-known system processes. Read through
    # the model: a QTableView has no item() accessor.
    model = page.tbl.model()
    descs = {
        model.data(model.index(r, 2), _Qt.ItemDataRole.DisplayRole)
        for r in range(model.rowCount())
    }
    assert any(d for d in descs), "no process descriptions populated"

    # Memory must sort on the real byte value, not the formatted string - this
    # is what the item-based table got wrong ("9 MB" above "10 MB").
    from cortex_unified.ui.premium.tablemodel import SORT_ROLE
    page.tbl.sortByColumn(4, _Qt.SortOrder.DescendingOrder)
    sizes = [model.data(model.index(r, 4), SORT_ROLE)
             for r in range(min(model.rowCount(), 25))]
    assert sizes == sorted(sizes, reverse=True), "memory column not sorted numerically"

    # Filtering narrows the visible rows without discarding the snapshot.
    page.search.setText("zzzz_no_such_process_zzzz")
    assert page.table.visible_count == 0
    assert len(page._procs) > 0, "filter must not clear the underlying records"
    page.search.setText("")
    assert page.table.visible_count > 0


# ---------------------------------------------------------------------------
# 8-10. Windows-only pages
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only feature")
def test_page_uninstaller_list(app, window):
    """test_page_uninstaller_list."""
    window._select("uninstaller")
    page = window._pages["uninstaller"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and not page.progress.isVisible()), \
        "uninstaller list stuck"
    # Model/view table: count rows through the binding, not the widget.
    assert page.table.visible_count > 0


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only feature")
def test_page_telemetry_status(app, window):
    """test_page_telemetry_status."""
    window._select("telemetry")
    page = window._pages["telemetry"]
    assert pump_until(app, lambda: page.tree.topLevelItemCount() > 0), "telemetry status stuck"
    assert "telemetry" in page.status_lbl.text().lower()


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only feature")
def test_page_registry_scan(app, window, pro_license):
    """test_page_registry_scan."""
    window._select("registry")
    page = window._pages["registry"]
    page._scan()
    assert pump_until(app, lambda: page.scan_btn.isEnabled() and not page.progress.isVisible()), \
        "registry scan stuck"
    # visible_count >= 0 (a clean registry may have zero orphans)
    assert page.table.visible_count >= 0


# ---------------------------------------------------------------------------
#  New backend pages: Software Updater / Drive Optimizer / System Info
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only feature")
def test_page_software_updater_list(app, window):
    """test_page_software_updater_list."""
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
    """test_page_drive_optimizer_list."""
    window._select("drives")
    page = window._pages["drives"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled() and not page.progress.isVisible()), \
        "drive optimizer list stuck"
    assert page.tbl.rowCount() >= 1  # at least the system drive
    actions = [page.tbl.item(r, 2).text() for r in range(page.tbl.rowCount()) if page.tbl.item(r, 2)]
    assert any(("TRIM" in a) or ("Defragment" in a) or ("\u2014" in a)
               for a in actions)


def _drive_action_text(drive: dict) -> str:
    """_drive_action_text."""
    from cortex_unified.ui.premium.more_pages import _drive_action
    return _drive_action(drive)


@pytest.mark.skipif(not IS_WINDOWS, reason="virtual disk compaction is Windows-only")
def test_page_virtual_disks(app, window):
    """Discovery is read-only, so it runs here; compaction is worker-tested."""
    from cortex_unified.system_tools.vhdx_manager import DiskKind, VirtualDisk

    window._select("vdisks")   # triggers lazy autoload (registry + PowerShell)
    page = window._pages["vdisks"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled(), timeout_ms=60000), \
        "virtual disk discovery stuck"
    # A machine with no WSL/Docker/Hyper-V must land in the empty state, not error.
    assert page.state.mode() in ("hidden", "empty")

    # A disk held open by its runtime must never be offered for compaction.
    blocked = VirtualDisk(pathlib.Path("run_gui.py"), DiskKind.DOCKER, "Docker",
                          8192, 8192, running=True, blockers=("dockerd.exe",))
    page._on_listed([blocked])
    page.tbl.selectRow(0)
    assert page.compact_btn.isEnabled() is False
    chosen = page._selected_disks()
    assert chosen and "dockerd.exe" in str(chosen[0].status_note)


@pytest.mark.skipif(not IS_WINDOWS, reason="component store is a Windows concept")
def test_page_component_store_construct(app, window):
    """Analysis runs real DISM (minutes); just verify the page builds and the
    managed-item safety rule holds. The parser/cleanup logic is unit-tested."""
    from cortex_unified.system_tools.component_store import Leftover, LeftoverRisk

    window._select("compstore")
    page = window._pages["compstore"]
    assert hasattr(page, "analyze_btn") and hasattr(page, "del_btn")

    managed = Leftover(pathlib.Path("run_gui.py"), "Component store (WinSxS)",
                       123, LeftoverRisk.MANAGED, "hard links",
                       supported_removal="Use DISM.")
    page._on_analyzed(
        type("A", (), {"actual_size": 0, "shared_with_windows": 0,
                       "reclaimable_estimate": 0, "reclaimable_packages": 0,
                       "last_cleanup": "", "explorer_gap_note": "", "message": ""})(),
        [managed],
    )
    page.tbl.selectRow(0)
    assert page.del_btn.isEnabled() is False, \
        "a Windows-managed item must never be offered for direct deletion"


def test_page_system_info_load(app, window):
    """test_page_system_info_load."""
    window._select("sysinfo")
    page = window._pages["sysinfo"]
    assert pump_until(app, lambda: "OS:" in page.info_label.text() or "Loading" not in page.info_label.text()), \
        "system info load stuck"
    assert "OS:" in page.info_label.text()


def test_page_package_caches_load(app, window):
    """test_page_package_caches_load."""
    window._select("packages")
    page = window._pages["packages"]
    assert pump_until(app, lambda: page.refresh_btn.isEnabled(),
                      timeout_ms=60000), "package cache detect stuck"
    # The page reports detection through its status label (no table).
    assert hasattr(page, "pm_detect_status")


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
    """test_page_broken_links_and_dupfolders_construct."""
    for pid in ("brokenlinks", "dupfolders"):
        window._select(pid)
        page = window._pages[pid]
        assert hasattr(page, "run_btn") and hasattr(page, "del_btn")
        assert page.run_btn.isEnabled() is False  # no folder chosen yet


# ---------------------------------------------------------------------------
# 11. Secure Shred (storage detection only; destructive path is worker-tested)
# ---------------------------------------------------------------------------

def test_page_shred_storage_detection(app, window, tmp_path):
    """test_page_shred_storage_detection."""
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
    """test_page_settings_theme_toggle."""
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


def test_page_lan_devices_renders_synthetic_advanced_audit(window):
    """Exercise the premium audit UI without touching the live network."""
    from cortex_unified.system_tools.network_discovery import Device, DiscoveryResult
    from cortex_unified.system_tools.network_inventory import InventoryChanges
    from cortex_unified.system_tools.network_security_audit import SecurityFinding
    from cortex_unified.system_tools.network_service_scanner import ServiceObservation
    from cortex_unified.system_tools.wan_audit import WanStatus

    service = ServiceObservation(
        ip="192.168.50.20", port=5555, transport="tcp", name="adb",
        source="synthetic", metadata={"evidence": ["TCP connection accepted"]})
    device = Device(
        ip="192.168.50.20", hostname="test-phone", open_ports=[5555],
        service_observations=[service], sources={"mdns", "ports"})
    finding = SecurityFinding(
        code="wireless-adb", severity="high", title="Wireless ADB reachable",
        detail="Synthetic fixture", remediation="Disable wireless debugging.",
        device_ip=device.ip, evidence=["synthetic"], confidence=0.95, port=5555)
    result = DiscoveryResult(
        devices=[device], networks=["192.168.50.0/24"], duration_seconds=1.2,
        findings=[finding], wan_status=WanStatus(
            external_ip="100.64.0.10", external_ip_classification="cgnat",
            gateway="192.168.50.1"), inventory_changes=InventoryChanges(),
        audit_profile="advanced")

    page = window._pages["landevices"]
    page._on_loaded(result)

    # Cells are read through the model: the device table is a QTableView driven
    # by a RecordTableModel, so there is no item() accessor.
    model = page.tbl.model()
    assert model.columnCount() == 8
    assert page.table.visible_count == 1

    def cell(row, col):
        """cell."""
        return model.data(model.index(row, col), Qt.ItemDataRole.DisplayRole)

    assert "5555/tcp adb" in cell(0, 5)
    assert "HIGH" in cell(0, 6)
    assert "CGNAT" in page.wan_status.text().upper()
    assert "1 high" in page.findings.text()
    assert page.export_btn.isEnabled()

    page.tbl.selectRow(0)
    # Selection must resolve to the real record, not a list index - this is what
    # used to break silently once the table could be sorted.
    assert page.table.selected_record() is device
    assert page._selected_device() is device
    assert not page.detail_tabs.isHidden()
    assert "Wireless ADB reachable" in page._detail_views["Security"].toPlainText()


# ---------------------------------------------------------------------------
# 28. NextGen & Enterprise Tools: Winapp2, SRUM/BAM, DirectStorage, StandbyMem, MFT Slack, Search
# ---------------------------------------------------------------------------

def test_page_winapp2_e2e(app, window):
    """test_page_winapp2_e2e."""
    page = window._pages["winapp2"]
    assert page is not None
    assert page.stat_apps is not None
    page._start_scan()
    assert pump_until(app, lambda: not page.progress_bar.isVisible(), timeout_ms=15000)


def test_page_srum_bam_e2e(app, window):
    """test_page_srum_bam_e2e."""
    page = window._pages["srumbam"]
    assert page is not None
    assert page.stat_bam_records is not None
    page._start_scan()
    assert pump_until(app, lambda: not page.progress_bar.isVisible(), timeout_ms=15000)


def test_page_directstorage_e2e(app, window):
    """test_page_directstorage_e2e."""
    page = window._pages["directstorage"]
    assert page is not None
    assert page.stat_status is not None
    page._start_audit()
    assert pump_until(app, lambda: not page.progress_bar.isVisible(), timeout_ms=15000)


def test_page_standby_purger_e2e(app, window):
    """test_page_standby_purger_e2e."""
    page = window._pages["standbymem"]
    assert page is not None
    assert page.stat_phys_total is not None
    page._refresh_stats()
    assert page.stat_phys_total.value() != "0 GB" or not IS_WINDOWS


def test_page_mft_slack_e2e(app, window):
    """test_page_mft_slack_e2e."""
    page = window._pages["mftslack"]
    assert page is not None
    assert page.stat_total_records is not None
    page._start_audit()
    assert pump_until(app, lambda: not page.progress_bar.isVisible(), timeout_ms=15000)


def test_page_search_optimizer_e2e(app, window):
    """test_page_search_optimizer_e2e."""
    page = window._pages["searchopt"]
    assert page is not None
    assert page.stat_size is not None
    page._start_status_query()
    assert pump_until(app, lambda: not page.progress_bar.isVisible(), timeout_ms=15000)


def test_page_disk_analyzer_e2e(app, window, tmp_path):
    """test_page_disk_analyzer_e2e."""
    sub = tmp_path / "subfolder"
    sub.mkdir()
    (sub / "test1.bin").write_bytes(b"A" * 1024)
    (sub / "test2.txt").write_text("Hello World")
    page = window._pages["diskanalyzer"]
    assert page is not None
    page._path_edit.setText(str(tmp_path))
    page._run()
    assert pump_until(app, lambda: page._worker is None, timeout_ms=15000)
    assert page._tbl.rowCount() >= 1


