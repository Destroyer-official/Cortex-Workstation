"""Component store (WinSxS) analysis, cleanup and leftover inventory.

The rules that must hold, because getting them wrong breaks Windows:

* WinSxS and ``Windows\\Installer`` are reported but never deletable here -
  hand-deleting them breaks Windows Update and software repair permanently;
* figures come from Windows' own DISM analysis, and an unreadable report yields
  zero rather than a guess;
* ``/ResetBase`` is never implied - it must be asked for explicitly;
* cleanup without Administrator is refused up front, not attempted and failed;
* a cleanup that frees nothing says so instead of implying success.

DISM output is fed in as fixtures so the parser is tested without a 20-minute
subprocess run.
"""

from __future__ import annotations

import platform

import pytest

from cortex_unified.system_tools.component_store import (
    ComponentStore,
    Leftover,
    LeftoverRisk,
    StoreAnalysis,
)

IS_WINDOWS = platform.system() == "Windows"

# Real DISM output shape (trimmed), as emitted by Windows 11.
_ANALYZE_OK = """
Deployment Image Servicing and Management tool
Version: 10.0.26100.1

Image Version: 10.0.26100.4061

[==========================100.0%==========================]

Component Store (WinSxS) information:

Windows Explorer Reported Size of Component Store : 10.44 GB

Actual Size of Component Store : 9.73 GB

    Shared with Windows : 4.30 GB
    Backups and Disabled Features : 5.42 GB
    Cache and Temporary Data : 0 bytes

Number of Reclaimable Packages : 4
Component Store Cleanup Recommended : Yes

Date of Last Cleanup : 2026-07-26 09:12:44

The operation completed successfully.
"""

_ANALYZE_CLEAN = """
Component Store (WinSxS) information:

Windows Explorer Reported Size of Component Store : 6.11 GB

Actual Size of Component Store : 5.98 GB

    Shared with Windows : 5.90 GB
    Backups and Disabled Features : 80.00 MB
    Cache and Temporary Data : 0 bytes

Number of Reclaimable Packages : 0
Component Store Cleanup Recommended : No

The operation completed successfully.
"""

_ANALYZE_ERROR = """
Deployment Image Servicing and Management tool

Error: 0x800f081f

The source files could not be found.
"""


# ---------------------------------------------------------------------------
# Analysis parsing
# ---------------------------------------------------------------------------

def test_parses_windows_own_figures():
    """test_parses_windows_own_figures."""
    a = ComponentStore._parse_analysis(_ANALYZE_OK)
    assert a.ok is True
    assert a.actual_size == pytest.approx(int(9.73 * 1024 ** 3))
    assert a.reported_size == pytest.approx(int(10.44 * 1024 ** 3))
    assert a.shared_with_windows == pytest.approx(int(4.30 * 1024 ** 3))
    assert a.backups_and_features == pytest.approx(int(5.42 * 1024 ** 3))
    assert a.cache_and_temp == 0
    assert a.reclaimable_packages == 4
    assert a.cleanup_recommended is True
    assert a.last_cleanup.startswith("2026-07-26")


def test_reclaimable_estimate_excludes_shared_bytes():
    """Space shared with Windows can never be reclaimed - don't promise it."""
    a = ComponentStore._parse_analysis(_ANALYZE_OK)
    assert a.reclaimable_estimate == a.backups_and_features + a.cache_and_temp
    assert a.reclaimable_estimate < a.actual_size
    assert a.shared_with_windows not in (a.reclaimable_estimate,)


def test_explains_the_explorer_size_gap():
    """test_explains_the_explorer_size_gap."""
    a = ComponentStore._parse_analysis(_ANALYZE_OK)
    note = a.explorer_gap_note
    assert "hard links" in note
    # When Explorer agrees with reality there's nothing to explain.
    equal = StoreAnalysis(reported_size=100, actual_size=100)
    assert equal.explorer_gap_note == ""


def test_no_cleanup_needed_is_stated_plainly():
    """test_no_cleanup_needed_is_stated_plainly."""
    a = ComponentStore._parse_analysis(_ANALYZE_CLEAN)
    assert a.ok is True
    assert a.cleanup_recommended is False
    assert a.reclaimable_packages == 0
    assert "not consider a cleanup necessary" in a.message


def test_dism_error_is_surfaced_with_its_code():
    """test_dism_error_is_surfaced_with_its_code."""
    a = ComponentStore._parse_analysis(_ANALYZE_ERROR)
    assert a.ok is False
    assert "0x800f081f" in a.message


def test_unreadable_report_yields_zero_not_a_guess():
    """test_unreadable_report_yields_zero_not_a_guess."""
    a = ComponentStore._parse_analysis("something entirely unexpected")
    assert a.actual_size == 0
    assert a.reclaimable_estimate == 0
    assert a.ok is False


def test_analysis_to_dict_is_json_ready():
    """test_analysis_to_dict_is_json_ready."""
    import json
    payload = json.loads(json.dumps(
        ComponentStore._parse_analysis(_ANALYZE_OK).to_dict()))
    assert payload["reclaimable_packages"] == 4
    assert payload["cleanup_recommended"] is True


def test_unsupported_platform_is_reported(monkeypatch):
    """test_unsupported_platform_is_reported."""
    import cortex_unified.system_tools.component_store as mod
    monkeypatch.setattr(mod, "_IS_WINDOWS", False)
    a = ComponentStore().analyze()
    assert a.supported is False
    assert ComponentStore().find_leftovers() == []
    assert ComponentStore().run_servicing_task()[0] is False


# ---------------------------------------------------------------------------
# Leftover policy
# ---------------------------------------------------------------------------

def test_windows_managed_items_are_never_removable_here(tmp_path):
    """test_windows_managed_items_are_never_removable_here."""
    winsxs = Leftover(tmp_path, "Component store (WinSxS)", 1, LeftoverRisk.MANAGED,
                      "hard links", supported_removal="Use DISM.")
    installer = Leftover(tmp_path, "Installer cache", 1, LeftoverRisk.MANAGED,
                         "needed for repair", supported_removal="Leave it alone.")
    assert winsxs.removable_here is False
    assert installer.removable_here is False
    # And each one names the supported alternative.
    assert winsxs.supported_removal and installer.supported_removal


def test_safe_and_rollback_items_are_removable(tmp_path):
    """test_safe_and_rollback_items_are_removable."""
    assert Leftover(tmp_path, "Setup logs", 1, LeftoverRisk.SAFE, "logs").removable_here
    assert Leftover(tmp_path, "Windows.old", 1, LeftoverRisk.LOSES_ROLLBACK,
                    "rollback").removable_here


def test_rollback_window_is_computed_from_age(tmp_path):
    """test_rollback_window_is_computed_from_age."""
    fresh = Leftover(tmp_path, "Windows.old", 1, LeftoverRisk.LOSES_ROLLBACK,
                     "rollback", age_days=3.0)
    stale = Leftover(tmp_path, "Windows.old", 1, LeftoverRisk.LOSES_ROLLBACK,
                     "rollback", age_days=45.0)
    unknown = Leftover(tmp_path, "Windows.old", 1, LeftoverRisk.LOSES_ROLLBACK,
                       "rollback")
    assert fresh.rollback_expired is False
    assert stale.rollback_expired is True
    assert unknown.rollback_expired is False   # unknown age: never claim expired


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows leftovers only")
def test_real_leftover_scan_is_readonly_and_sorted():
    """test_real_leftover_scan_is_readonly_and_sorted."""
    items = ComponentStore().find_leftovers()
    assert isinstance(items, list)
    sizes = [i.size_bytes for i in items]
    assert sizes == sorted(sizes, reverse=True), "largest first"
    for item in items:
        assert item.path.exists()
        assert item.explanation, "every item must explain what removing it costs"
        if item.risk is LeftoverRisk.MANAGED:
            assert item.supported_removal


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows leftovers only")
def test_winsxs_size_comes_from_dism_not_a_folder_walk():
    """Walking WinSxS counts each hard link separately - the inflated figure
    this page exists to explain. It must be sourced from DISM instead."""
    analysis = ComponentStore._parse_analysis(_ANALYZE_OK)
    items = ComponentStore().find_leftovers(analysis=analysis)
    winsxs = next((i for i in items if "WinSxS" in i.label), None)
    if winsxs is None:
        pytest.skip("no WinSxS folder on this machine")
    assert winsxs.size_bytes == analysis.actual_size
    assert winsxs.risk is LeftoverRisk.MANAGED
    assert winsxs.removable_here is False

    # Without an analysis there is no defensible number, so it isn't listed at all.
    assert all("WinSxS" not in i.label
               for i in ComponentStore().find_leftovers())


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows leftovers only")
def test_installer_cache_is_flagged_managed_when_present():
    """test_installer_cache_is_flagged_managed_when_present."""
    by_label = {i.label: i for i in ComponentStore().find_leftovers()}
    if "Installer cache" in by_label:
        assert by_label["Installer cache"].risk is LeftoverRisk.MANAGED
        assert by_label["Installer cache"].removable_here is False


def test_leftover_scan_is_cancellable(tmp_path, monkeypatch):
    """test_leftover_scan_is_cancellable."""
    import threading
    event = threading.Event()
    event.set()
    items = ComponentStore().find_leftovers(cancel_event=event)
    assert items == [], "an already-cancelled scan must do no work"


# ---------------------------------------------------------------------------
# Cleanup safety
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not IS_WINDOWS, reason="DISM cleanup is Windows-only")
def test_cleanup_refuses_without_administrator(monkeypatch):
    """test_cleanup_refuses_without_administrator."""
    store = ComponentStore()
    monkeypatch.setattr(ComponentStore, "is_elevated", staticmethod(lambda: False))

    def _boom(*_a, **_k):
        """_boom."""
        raise AssertionError("DISM must not run without elevation")

    monkeypatch.setattr(store, "_run_dism", _boom)

    outcome = store.cleanup()
    assert outcome.success is False
    assert "administrator" in outcome.message.lower()


@pytest.mark.skipif(not IS_WINDOWS, reason="DISM cleanup is Windows-only")
def test_cleanup_reports_measured_delta(monkeypatch):
    """test_cleanup_reports_measured_delta."""
    store = ComponentStore()
    monkeypatch.setattr(ComponentStore, "is_elevated", staticmethod(lambda: True))
    calls = []

    def _fake_dism(args, timeout, cancel_event=None):
        """_fake_dism."""
        calls.append(args)
        if "/AnalyzeComponentStore" in args:
            # Shrink on the second analysis to simulate a real cleanup.
            return _ANALYZE_CLEAN if len(calls) > 2 else _ANALYZE_OK
        return "The operation completed successfully."

    monkeypatch.setattr(store, "_run_dism", _fake_dism)

    outcome = store.cleanup()
    assert outcome.success is True
    assert outcome.before_bytes > outcome.after_bytes
    assert outcome.freed_bytes > 0
    assert outcome.reset_base is False
    # ResetBase must never be added unless asked for.
    cleanup_args = next(a for a in calls if "/StartComponentCleanup" in a)
    assert "/ResetBase" not in cleanup_args


@pytest.mark.skipif(not IS_WINDOWS, reason="DISM cleanup is Windows-only")
def test_reset_base_is_passed_only_when_requested(monkeypatch):
    """test_reset_base_is_passed_only_when_requested."""
    store = ComponentStore()
    monkeypatch.setattr(ComponentStore, "is_elevated", staticmethod(lambda: True))
    seen = []

    def _fake_dism(args, timeout, cancel_event=None):
        """_fake_dism."""
        seen.append(args)
        if "/AnalyzeComponentStore" in args:
            return _ANALYZE_OK
        return "The operation completed successfully."

    monkeypatch.setattr(store, "_run_dism", _fake_dism)

    outcome = store.cleanup(reset_base=True)
    assert outcome.reset_base is True
    cleanup_args = next(a for a in seen if "/StartComponentCleanup" in a)
    assert "/ResetBase" in cleanup_args


@pytest.mark.skipif(not IS_WINDOWS, reason="DISM cleanup is Windows-only")
def test_cleanup_is_honest_when_nothing_shrank(monkeypatch):
    """test_cleanup_is_honest_when_nothing_shrank."""
    store = ComponentStore()
    monkeypatch.setattr(ComponentStore, "is_elevated", staticmethod(lambda: True))
    monkeypatch.setattr(store, "_run_dism", lambda args, timeout, cancel_event=None: (
        _ANALYZE_OK if "/AnalyzeComponentStore" in args
        else "The operation completed successfully."))

    outcome = store.cleanup()
    assert outcome.success is True
    assert outcome.freed_bytes == 0
    assert "did not shrink" in outcome.message


@pytest.mark.skipif(not IS_WINDOWS, reason="DISM cleanup is Windows-only")
def test_cleanup_failure_explains_pending_servicing(monkeypatch):
    """test_cleanup_failure_explains_pending_servicing."""
    store = ComponentStore()
    monkeypatch.setattr(ComponentStore, "is_elevated", staticmethod(lambda: True))
    monkeypatch.setattr(store, "_run_dism", lambda args, timeout, cancel_event=None: (
        _ANALYZE_OK if "/AnalyzeComponentStore" in args
        else "Error: 0x800f0806 - the operation could not be completed."))

    outcome = store.cleanup()
    assert outcome.success is False
    assert "0x800f0806" in outcome.message
    assert "restart" in outcome.message.lower()
    assert outcome.freed_bytes == 0


def test_decode_handles_dism_utf16_output():
    """test_decode_handles_dism_utf16_output."""
    raw = "The operation completed successfully.".encode("utf-16-le")
    assert "completed successfully" in ComponentStore._decode(raw)
    assert ComponentStore._decode(None) == ""


def test_dir_size_never_raises_on_unreadable_paths(tmp_path):
    """test_dir_size_never_raises_on_unreadable_paths."""
    (tmp_path / "a.bin").write_bytes(b"x" * 1000)
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.bin").write_bytes(b"y" * 500)
    assert ComponentStore._dir_size(tmp_path) == 1500
    # A path that doesn't exist yields 0 rather than an exception.
    assert ComponentStore._dir_size(tmp_path / "nope") == 0
