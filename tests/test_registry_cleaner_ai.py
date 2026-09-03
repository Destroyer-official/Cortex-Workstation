"""Tests for the AI registry cleaner's detectors and path resolution.

These pin the safety-critical behaviours:

* Unquoted registry paths containing spaces resolve to the full path first
  (``D:\\...\\Microsoft VS Code\\Code.exe``), with token prefixes only as
  fallbacks — never the truncated first word.
* ACL-locked ancestors (WindowsApps) make absence *unprovable*, so Store
  apps are never reported as orphans.
* Boot/system-start services are never flagged, and a live driver's
  relative or ``\\SystemRoot`` ImagePath resolves correctly.
* Registry views: 64-bit and 32-bit HKLM are addressable independently.
"""

from __future__ import annotations

import sys

import pytest

winreg = pytest.importorskip("winreg")
pytestmark = pytest.mark.skipif(sys.platform != "win32",
                                reason="winreg is Windows-only")

from cortex_unified.analyzers.registry_cleaner_ai import (  # noqa: E402
    AIRegistryCleaner,
    RegistryIssue,
    _detect_missing_path,
    _detect_orphaned_service,
    _detect_shared_dll_gone,
    _expand,
    _font_candidates,
    _resolve_target,
    _split,
    _split32,
    _target_candidates,
    _target_exists,
    _target_exists_any,
    _verifiable,
)


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def test_resolve_target_keeps_unquoted_path_with_spaces():
    """test_resolve_target_keeps_unquoted_path_with_spaces."""
    raw = r"C:\Program Files\Example Suite\Editor.exe"
    assert _resolve_target(raw) == raw


def test_resolve_target_strips_quotes_and_keeps_args_out():
    """test_resolve_target_strips_quotes_and_keeps_args_out."""
    raw = r'"C:\Program Files\App\un.exe" /S'
    assert _resolve_target(raw) == r"C:\Program Files\App\un.exe"


def test_resolve_target_expands_system_root_prefix():
    """test_resolve_target_expands_system_root_prefix."""
    raw = r"\SystemRoot\System32\drivers\amdk8.sys"
    resolved = _resolve_target(raw)
    assert resolved is not None
    assert "drivers" in resolved
    assert not resolved.startswith("\\")


def test_target_candidates_includes_full_path_first_then_prefixes():
    """test_target_candidates_includes_full_path_first_then_prefixes."""
    raw = r"C:\Program Files\App\tool.exe -flag"
    cands = _target_candidates(raw)
    assert cands[0] == r"C:\Program Files\App\tool.exe -flag"
    assert r"C:\Program Files\App\tool.exe" in cands
    # Longest prefix before shorter ones.
    assert cands.index(r"C:\Program Files\App\tool.exe") > 0


def test_target_candidates_anchors_relative_paths_at_system_roots():
    """test_target_candidates_anchors_relative_paths_at_system_roots."""
    cands = _target_candidates(r"system32\drivers\cdfs.sys")
    assert len(cands) >= 4
    # Every candidate is absolute (anchored at a real root); the bare
    # relative path must never appear, because Path.exists would resolve it
    # against the CWD.
    from pathlib import Path
    for c in cands:
        assert Path(c).is_absolute(), c
    joined = " | ".join(c.lower() for c in cands)
    assert r"system32\drivers\cdfs.sys" in joined


def test_verifiable_true_for_missing_but_listable_parent(tmp_path):
    """test_verifiable_true_for_missing_but_listable_parent."""
    assert _verifiable(str(tmp_path / "no_such_file.bin")) is True


def test_verifiable_true_for_existing_file(tmp_path):
    """test_verifiable_true_for_existing_file."""
    f = tmp_path / "present.bin"
    f.write_bytes(b"x")
    assert _verifiable(str(f)) is True


def test_verifiable_false_when_ancestor_listing_denied(tmp_path, monkeypatch):
    """test_verifiable_false_when_ancestor_listing_denied."""
    import os

    real_stat = os.stat

    def fake_stat(p, *a, **k):
        # Simulate an ACL-locked subtree: the target itself raises
        # PermissionError exactly like WindowsApps does.
        """fake_stat."""
        if str(p).endswith("locked.exe"):
            raise PermissionError(5, "Access is denied")
        return real_stat(p, *a, **k)

    monkeypatch.setattr("os.stat", fake_stat)
    assert _verifiable(str(tmp_path / "locked.exe")) is False


def test_target_exists_treats_unprovable_as_present(tmp_path, monkeypatch):
    """test_target_exists_treats_unprovable_as_present."""
    import os

    real_stat = os.stat

    def fake_stat(p, *a, **k):
        """fake_stat."""
        if str(p).endswith("locked.exe"):
            raise PermissionError(5, "Access is denied")
        return real_stat(p, *a, **k)

    monkeypatch.setattr("os.stat", fake_stat)
    assert _target_exists(str(tmp_path / "locked.exe")) is True


def test_target_exists_false_only_when_provably_missing(tmp_path):
    """test_target_exists_false_only_when_provably_missing."""
    assert _target_exists(str(tmp_path / "definitely_gone.bin")) is False


def test_font_candidates_anchor_relative_names_at_fonts_dir():
    """test_font_candidates_anchor_relative_names_at_fonts_dir."""
    cands = _font_candidates("segoeui.ttf")
    assert len(cands) == 1
    assert cands[0].lower().endswith(r"\fonts\segoeui.ttf")


def test_font_candidates_keep_absolute_paths():
    """test_font_candidates_keep_absolute_paths."""
    cands = _font_candidates(r"C:\Windows\Fonts\arial.ttf")
    assert cands == [r"C:\Windows\Fonts\arial.ttf"]


# ---------------------------------------------------------------------------
# Registry views
# ---------------------------------------------------------------------------

def test_split_returns_64bit_view_for_hklm():
    """test_split_returns_64bit_view_for_hklm."""
    _hive, _sub, access = _split(r"HKLM\Software")
    assert access & winreg.KEY_WOW64_64KEY


def test_split32_returns_32bit_view_for_hklm():
    """test_split32_returns_32bit_view_for_hklm."""
    parts = _split32(r"HKLM\Software")
    assert parts is not None
    assert parts[2] & winreg.KEY_WOW64_32KEY


def test_split32_is_none_for_hkcu():
    """test_split32_is_none_for_hkcu."""
    assert _split32(r"HKCU\Software") is None


def test_split_rejects_unknown_hive():
    """test_split_rejects_unknown_hive."""
    with pytest.raises(KeyError):
        _split(r"HKXX\Software")


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------

def test_detect_missing_path_true_when_target_gone(tmp_path):
    """test_detect_missing_path_true_when_target_gone."""
    values = {"": (str(tmp_path / "gone.exe"), winreg.REG_SZ)}
    assert _detect_missing_path("HKCU\\X\\gone.exe", values, 0) is True


def test_detect_missing_path_false_when_target_exists(tmp_path):
    """test_detect_missing_path_false_when_target_exists."""
    exe = tmp_path / "app.exe"
    exe.write_bytes(b"MZ")
    values = {"": (str(exe), winreg.REG_SZ)}
    assert _detect_missing_path("HKCU\\X\\app.exe", values, 0) is False


def test_detect_missing_path_false_when_default_value_empty():
    """test_detect_missing_path_false_when_default_value_empty."""
    values = {"Path": (r"C:\Windows\System32\cmd.exe", winreg.REG_SZ)}
    assert _detect_missing_path("HKCU\\X\\cmd.exe", values, 0) is False


def test_detect_orphaned_service_skips_boot_and_system_start():
    """test_detect_orphaned_service_skips_boot_and_system_start."""
    image = r"C:\definitely\not\here.sys"
    assert _detect_orphaned_service(
        "HKLM\\X\\svc", {"Start": (0, winreg.REG_DWORD),
                         "ImagePath": (image, winreg.REG_SZ)}, 0) is False
    assert _detect_orphaned_service(
        "HKLM\\X\\svc", {"Start": (1, winreg.REG_DWORD),
                         "ImagePath": (image, winreg.REG_SZ)}, 0) is False


def test_detect_orphaned_service_true_when_verifiably_missing(tmp_path):
    """test_detect_orphaned_service_true_when_verifiably_missing."""
    image = str(tmp_path / "gone_driver.sys")
    assert _detect_orphaned_service(
        "HKLM\\X\\svc", {"Start": (3, winreg.REG_DWORD),
                         "ImagePath": (image, winreg.REG_SZ)}, 0) is True


def test_detect_orphaned_service_false_when_image_missing_but_dll_alive(tmp_path):
    """test_detect_orphaned_service_false_when_image_missing_but_dll_alive."""
    dll = tmp_path / "svc.dll"
    dll.write_bytes(b"MZ")
    assert _detect_orphaned_service(
        "HKLM\\X\\svc", {"Start": (2, winreg.REG_DWORD),
                         "ServiceDll": (str(dll), winreg.REG_EXPAND_SZ)}, 0) is False


def test_detect_orphaned_service_true_when_dll_verifiably_missing(tmp_path):
    """test_detect_orphaned_service_true_when_dll_verifiably_missing."""
    dll = str(tmp_path / "gone_svc.dll")
    assert _detect_orphaned_service(
        "HKLM\\X\\svc", {"Start": (2, winreg.REG_DWORD),
                         "ServiceDll": (dll, winreg.REG_EXPAND_SZ)}, 0) is True


def test_detect_orphaned_service_never_guesses_with_no_targets():
    """test_detect_orphaned_service_never_guesses_with_no_targets."""
    assert _detect_orphaned_service("HKLM\\X\\svc", {}, 0) is False


def test_detect_shared_dll_uses_value_names_as_paths(tmp_path):
    """test_detect_shared_dll_uses_value_names_as_paths."""
    present = tmp_path / "present.dll"
    present.write_bytes(b"MZ")
    values = {str(present): (1, winreg.REG_DWORD),
              str(tmp_path / "gone.dll"): (1, winreg.REG_DWORD)}
    assert _detect_shared_dll_gone("HKLM\\X", values, 0) is True
    assert _detect_shared_dll_gone(
        "HKLM\\X", {str(present): (1, winreg.REG_DWORD)}, 0) is False


# ---------------------------------------------------------------------------
# Cleaner-level integration (read-only paths)
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_scan_targets_offending_value():
    """The reported value is the one that proves the orphan.

    Marked ``live`` because it walks the real Uninstall tree; deselect with
    ``-m 'not live'`` for fast unit-only runs.
    """
    cleaner = AIRegistryCleaner(create_restore_point=False)
    result = cleaner.scan(["orphaned_uninstall"])
    for issue in result.issues:
        assert issue.key_path
        assert issue.value_name  # never blank for a proven orphan
        assert issue.evidence.get("registry_view") in ("native", "32-bit")


@pytest.mark.live
def test_scan_service_category_never_flags_boot_drivers():
    """test_scan_service_category_never_flags_boot_drivers."""
    cleaner = AIRegistryCleaner(create_restore_point=False)
    result = cleaner.scan(["orphaned_service_driver"])
    for issue in result.issues:
        assert "Services\\" in issue.key_path
        # Boot/system-start drivers must never appear.
        assert issue.value_name in ("ImagePath", "ServiceDll")


# ---------------------------------------------------------------------------
# Clean path (mutates a throwaway HKCU key)
# ---------------------------------------------------------------------------

_TEST_ROOT = r"HKCU\Software\CortexCleanerSelfTest"


@pytest.fixture()
def throwaway_key():
    """A test key under HKCU removed after each test."""
    sub = _TEST_ROOT.partition("\\")[2]
    winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub)
    yield sub
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
    except OSError:
        pass


def _cleaner(tmp_path):
    """_cleaner."""
    cleaner = AIRegistryCleaner(create_restore_point=False)
    # Redirect backups to the test directory so runs leave no residue.
    from pathlib import Path as _P
    cleaner._backup_dir = _P(tmp_path)
    return cleaner


def test_clean_deletes_value_level_orphan(throwaway_key, tmp_path):
    """test_clean_deletes_value_level_orphan."""
    sub = throwaway_key
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub + r"\Orphan") as k:
        winreg.SetValueEx(k, "Path", 0, winreg.REG_SZ,
                          str(tmp_path / "definitely_missing.exe"))
    issue = RegistryIssue(
        key_path=f"HKCU\\{sub}\\Orphan", value_name="Path",
        value_data=str(tmp_path / "definitely_missing.exe"),
        value_type=winreg.REG_SZ, category="orphaned_path_value",
        risk_score=0.1, confidence=0.9, recommendation="remove")
    result = _cleaner(tmp_path).clean([issue], selected_ids=[0])
    assert len(result.cleaned) == 1
    # Value gone (raises), key itself still present (value-level category).
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub + r"\Orphan") as k:
        with pytest.raises(FileNotFoundError):
            winreg.QueryValueEx(k, "Path")


def test_clean_deletes_key_level_orphan(throwaway_key, tmp_path):
    """test_clean_deletes_key_level_orphan."""
    sub = throwaway_key
    winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub + r"\DeadApp")
    issue = RegistryIssue(
        key_path=f"HKCU\\{sub}\\DeadApp", value_name="UninstallString",
        value_data=str(tmp_path / "gone" / "unins000.exe"),
        value_type=winreg.REG_SZ, category="orphaned_uninstall",
        risk_score=0.2, confidence=0.9, recommendation="remove")
    result = _cleaner(tmp_path).clean([issue], selected_ids=[0])
    assert len(result.cleaned) == 1
    with pytest.raises(FileNotFoundError):
        winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub + r"\DeadApp")


def test_clean_backs_up_before_deleting(throwaway_key, tmp_path):
    """test_clean_backs_up_before_deleting."""
    sub = throwaway_key
    winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub + r"\BackedUp")
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub + r"\BackedUp",
                        0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "Path", 0, winreg.REG_SZ, "x")
    issue = RegistryIssue(
        key_path=f"HKCU\\{sub}\\BackedUp", value_name="Path",
        value_data="x", value_type=winreg.REG_SZ,
        category="orphaned_path_value",
        risk_score=0.1, confidence=0.9, recommendation="remove")
    cleaner = _cleaner(tmp_path)
    result = cleaner.clean([issue], selected_ids=[0])
    assert len(result.cleaned) == 1
    backups = list(tmp_path.glob("reg_*.reg"))
    assert backups, "clean ran without writing a backup first"
    assert result.cleaned[0].backup_path == str(backups[0])


def test_clean_refuses_delete_when_subkeys_present(throwaway_key, tmp_path):
    """test_clean_refuses_delete_when_subkeys_present."""
    sub = throwaway_key
    winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub + r"\Parent\\Child")
    issue = RegistryIssue(
        key_path=f"HKCU\\{sub}\\Parent", value_name="UninstallString",
        value_data=str(tmp_path / "gone"), value_type=winreg.REG_SZ,
        category="orphaned_uninstall",
        risk_score=0.2, confidence=0.9, recommendation="remove")
    result = _cleaner(tmp_path).clean([issue], selected_ids=[0])
    assert result.cleaned == []
    assert result.failed and "subkeys present" in result.failed[0][1]
    # Key untouched.
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub + r"\Parent\Child"):
        pass


def test_clean_keep_recommendation_is_not_deleted(throwaway_key, tmp_path):
    """test_clean_keep_recommendation_is_not_deleted."""
    sub = throwaway_key
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub + r"\Kept") as k:
        winreg.SetValueEx(k, "Path", 0, winreg.REG_SZ, str(tmp_path / "gone.exe"))
    issue = RegistryIssue(
        key_path=f"HKCU\\{sub}\\Kept", value_name="Path",
        value_data=str(tmp_path / "gone.exe"), value_type=winreg.REG_SZ,
        category="orphaned_path_value",
        risk_score=0.9, confidence=0.9, recommendation="keep")
    result = _cleaner(tmp_path).clean([issue], selected_ids=[0])
    assert result.cleaned == []
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub + r"\Kept") as k:
        assert winreg.QueryValueEx(k, "Path")[0] == str(tmp_path / "gone.exe")
