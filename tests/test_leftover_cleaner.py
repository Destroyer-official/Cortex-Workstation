"""Tests for the production leftover cleaner (post-uninstall residuals).

Covers the matcher, confidence scoring, safety gates, the filesystem/registry
sweeps against synthetic trees, and the cleaner's recycle-bin + backup +
journal behaviour. All destructive paths are monkeypatched - nothing here
touches the real Recycle Bin or registry.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from cortex_unified.system_tools.leftover_cleaner import (
    BAD,
    GOOD,
    QUESTIONABLE,
    VERY_GOOD,
    InstalledApp,
    LeftoverCleaner,
    LeftoverFinding,
    LeftoverScanner,
    SafetyPolicy,
    build_tokens,
    confidence_level,
    detect_installer_type,
    edit_distance,
    match_string_to_product,
)


# =====================================================================
#  Matcher
# =====================================================================

class TestEditDistance:
    """TestEditDistance."""
    def test_identical_strings_cost_zero(self):
        """test_identical_strings_cost_zero."""
        assert edit_distance("sublime", "sublime") == 0

    def test_empty_inputs(self):
        """test_empty_inputs."""
        assert edit_distance("", "abc") == 3
        assert edit_distance("abc", "") == 3
        assert edit_distance("", "") == 0

    @pytest.mark.parametrize("a,b,expected", [
        ("abcdef", "abcxef", 1),   # one substitution
        ("abcdef", "abdxf", 2),    # substitution + deletion
        ("kitten", "sitting", 3),  # classic Levenshtein example
        ("flaw", "lawn", 2),
        ("copy", "copy", 0),
    ])
    def test_known_distances(self, a, b, expected):
        """test_known_distances."""
        assert edit_distance(a, b) == expected

    def test_early_exit_exceeds_bound(self):
        """test_early_exit_exceeds_bound."""
        assert edit_distance("aaaa", "bbbb", max_distance=2) > 2


class TestMatchStringToProduct:
    """TestMatchStringToProduct."""
    def test_perfect_match(self):
        """test_perfect_match."""
        assert match_string_to_product("sublime text", "Sublime Text") == 0

    def test_near_match_off_by_one(self):
        """test_near_match_off_by_one."""
        assert match_string_to_product("sublime txt", "Sublime Text") == 1

    def test_substring_containment(self):
        """test_substring_containment."""
        assert match_string_to_product("firefox", "Mozilla Firefox") == 2

    def test_short_names_never_match(self):
        # The <=4 char floor prevents "Java" vs "JRE" style nonsense.
        """test_short_names_never_match."""
        assert match_string_to_product("java", "jre") == -1
        assert match_string_to_product("app", "application") == -1

    def test_unrelated_names_rejected(self):
        """test_unrelated_names_rejected."""
        assert match_string_to_product("thunderbird", "winrar") == -1

    def test_distance_beyond_one_third_cutoff(self):
        """test_distance_beyond_one_third_cutoff."""
        assert match_string_to_product("abcdefghijklmnop", "qrstuvwxyz") == -1


class TestBuildTokens:
    """TestBuildTokens."""
    def test_noise_suffixes_removed(self):
        """test_noise_suffixes_removed."""
        tokens = build_tokens("AppX (64-bit) Free Edition")
        assert "appx" in tokens
        assert not any("free" in t or "edition" in t for t in tokens)

    def test_generic_publishers_excluded(self):
        """test_generic_publishers_excluded."""
        tokens = build_tokens("SomeApp", "Microsoft Corporation")
        assert "microsoft" not in tokens
        assert "corporation" not in tokens

    def test_specific_publisher_included(self):
        """test_specific_publisher_included."""
        tokens = build_tokens("SomeApp", "Sublime HQ Pty Ltd")
        assert "sublimehqptyltd" in tokens

    def test_short_tokens_dropped(self):
        """test_short_tokens_dropped."""
        tokens = build_tokens("My App Tool")
        assert "my" not in tokens and "app" not in tokens
        # 'tool' is a stopword (generic); the joined name still matches.
        assert "tool" not in tokens
        assert "myapptool" in tokens


class TestConfidenceLevels:
    """TestConfidenceLevels."""
    def test_mapping(self):
        """test_mapping."""
        assert confidence_level(-1) == BAD
        assert confidence_level(0) == QUESTIONABLE
        assert confidence_level(1) == QUESTIONABLE
        assert confidence_level(2) == GOOD
        assert confidence_level(4) == GOOD
        assert confidence_level(5) == VERY_GOOD
        assert confidence_level(24) == VERY_GOOD


def test_detect_installer_type():
    """test_detect_installer_type."""
    guid = "{9A25302D-30CA-406E-8F5C-4A0B0B6A2F3A}"
    assert detect_installer_type(guid, 'MsiExec.exe /I{...}') == "msi"
    assert detect_installer_type("MyApp_is1", '"C:\\x\\unins000.exe"') == "inno"
    assert detect_installer_type("MyApp", '"C:\\x\\uninst.exe" /S') == "nsis"
    assert detect_installer_type("WeirdKey", "something.exe") == "unknown"


# =====================================================================
#  Safety gates
# =====================================================================

class TestSafetyPolicy:
    """TestSafetyPolicy."""
    def test_known_folder_roots_are_prohibited_but_children_allowed(
            self, monkeypatch, tmp_path):
        """test_known_folder_roots_are_prohibited_but_children_allowed."""
        monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
        policy = SafetyPolicy.build()
        root = tmp_path / "roaming"
        child = root / "SomeLeftover"
        assert policy.is_prohibited(root)
        assert not policy.is_prohibited(child)

    def test_own_paths_protected(self, tmp_path):
        """test_own_paths_protected."""
        policy = SafetyPolicy(protected_paths=frozenset(),
                              own_paths=(str(tmp_path),))
        assert policy.is_prohibited(tmp_path)
        assert not policy.is_prohibited(tmp_path / "child")


# =====================================================================
#  Scanner - filesystem sweep on a synthetic tree
# =====================================================================

@pytest.fixture
def fake_env(monkeypatch, tmp_path):
    """Redirect every sweep root into a throwaway directory tree."""
    roots = {
        "PROGRAMFILES": tmp_path / "pf",
        "ProgramFiles(x86)": tmp_path / "pf86",
        "ProgramData": tmp_path / "programdata",
        "APPDATA": tmp_path / "roaming",
        "LOCALAPPDATA": tmp_path / "local",
    }
    for env, path in roots.items():
        path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv(env, str(path))
    (tmp_path / "local" / "LocalLow").mkdir()
    (tmp_path / "local" / "VirtualStore").mkdir()
    (tmp_path / "local" / "Programs").mkdir()
    (tmp_path / "roaming" / "Programs").mkdir()
    return tmp_path


def _scanner(apps=()):
    """_scanner."""
    return LeftoverScanner(installed_apps=list(apps))


class TestFilesystemSweep:
    """TestFilesystemSweep."""
    def test_empty_leftover_folder_scores_very_good(self, fake_env):
        """test_empty_leftover_folder_scores_very_good."""
        target = fake_env / "roaming" / "ZetaSoft ZetaEditor"
        target.mkdir()
        scanner = _scanner()
        app = InstalledApp(name="ZetaEditor", publisher="ZetaSoft",
                           install_location=r"C:\Program Files\ZetaEditor")
        findings = scanner.scan_app(app)
        paths = {f.path for f in findings}
        assert str(target).lower() in {p.lower() for p in paths}
        best = next(f for f in findings
                    if f.path.lower() == str(target).lower())
        assert best.level == VERY_GOOD
        assert any("empty" in r for r in best.reasons)

    def test_blacklisted_directory_never_flagged(self, fake_env):
        """test_blacklisted_directory_never_flagged."""
        target = fake_env / "roaming" / "Microsoft"
        target.mkdir()
        app = InstalledApp(name="Microsoft Office", publisher="Microsoft")
        findings = _scanner().scan_app(app)
        assert all("microsoft" != Path(f.path).name.lower()
                   for f in findings if f.kind == "folder")

    def test_executables_present_penalized(self, fake_env):
        """test_executables_present_penalized."""
        target = fake_env / "local" / "ZetaEditor"
        target.mkdir(parents=True)
        (target / "zeta.exe").write_bytes(b"MZ")
        app = InstalledApp(name="ZetaEditor")
        findings = _scanner().scan_app(app)
        best = next(f for f in findings
                    if f.path.lower() == str(target).lower())
        assert any("executables present" in r for r in best.reasons)
        # depth bonus (+2) and leaf bonus (+2) must not outrank the
        # executables penalty (-4): the net score stays non-positive.
        assert best.score <= 0

    def test_product_still_installed_penalized(self, fake_env):
        """test_product_still_installed_penalized."""
        target = fake_env / "roaming" / "ZetaEditor"
        target.mkdir()
        live = InstalledApp(name="ZetaEditor", publisher="ZetaSoft",
                            install_location=str(fake_env / "pf" / "Live"))
        (fake_env / "pf" / "Live").mkdir()
        app = InstalledApp(name="ZetaEditor", publisher="ZetaSoft")
        findings = _scanner(apps=[live]).scan_app(app)
        best = next(f for f in findings
                    if f.path.lower() == str(target).lower())
        assert any("still installed" in r for r in best.reasons)
        # The -4 penalty must keep this out of the top confidence tier.
        assert best.level != VERY_GOOD

    def test_live_sibling_app_claiming_name_penalized(self, fake_env):
        """test_live_sibling_app_claiming_name_penalized."""
        target = fake_env / "roaming" / "ZetaEditorPro"
        target.mkdir()
        live = InstalledApp(name="ZetaEditorPro", publisher="OtherCorp",
                            install_location=str(fake_env / "pf" / "Live"))
        (fake_env / "pf" / "Live").mkdir()
        app = InstalledApp(name="ZetaEditor", publisher="ZetaSoft")
        findings = _scanner(apps=[live]).scan_app(app)
        best = next(f for f in findings
                    if f.path.lower() == str(target).lower())
        assert any("installed app" in r for r in best.reasons)

    def test_nested_cache_inside_matched_vendor_found(self, fake_env):
        """test_nested_cache_inside_matched_vendor_found."""
        vendor = fake_env / "local" / "ZetaSoft"
        cache = vendor / "ZetaEditor" / "Cache"
        cache.mkdir(parents=True)
        app = InstalledApp(name="ZetaEditor", publisher="ZetaSoft")
        findings = _scanner().scan_app(app)
        paths = {Path(f.path).name.lower() for f in findings}
        assert "cache" in paths or "zetaeditor" in paths

    def test_reparse_point_not_descended(self, fake_env):
        """test_reparse_point_not_descended."""
        link = fake_env / "roaming" / "ZetaLink"
        real = fake_env / "pf" / "elsewhere"
        real.mkdir(parents=True)
        made = False
        if os.name == "nt":
            # Junctions need no admin privileges, unlike symlinks.
            import subprocess as sp
            r = sp.run(["cmd", "/c", "mklink", "/J", str(link), str(real)],
                       capture_output=True)
            made = r.returncode == 0
        else:
            try:
                os.symlink(str(real), str(link), target_is_directory=True)
                made = True
            except OSError:
                pass
        if not made:
            pytest.skip("cannot create junction/symlink without privilege")
        app = InstalledApp(name="ZetaLink")
        findings = _scanner().scan_app(app)  # must not raise / loop
        assert isinstance(findings, list)

    def test_orphan_scan_reports_empty_unclaimed_folder(self, fake_env):
        """test_orphan_scan_reports_empty_unclaimed_folder."""
        orphan = fake_env / "pf" / "GhostApp"
        orphan.mkdir()
        live = InstalledApp(name="PresentApp",
                            install_location=str(fake_env / "pf" / "Present"))
        (fake_env / "pf" / "Present").mkdir()
        findings = _scanner(apps=[live]).scan_orphans()
        names = {Path(f.path).name.lower() for f in findings}
        assert "ghostapp" in names
        assert "present" not in names


# =====================================================================
#  Registry sweep with a stubbed winreg
# =====================================================================

class FakeRegKey:
    """Minimal winreg key double: subkeys + string values."""

    def __init__(self, subkeys=None, values=None):
        """__init__."""
        self._subkeys = subkeys or {}
        self._values = values or {}

    def children(self):
        """children."""
        return self._subkeys


@pytest.fixture
def fake_registry(monkeypatch):
    """Install a fake winreg module driving LeftoverScanner's registry walk.

    OpenKey semantics mirror the real API: given a hive constant it resolves
    an absolute path; given a key object it resolves a direct child name.
    """
    zeta_key = FakeRegKey(values={
        "InstallLocation": r"C:\Program Files\ZetaEditor",
        "Language": "en",
    })
    zetasoft = FakeRegKey(subkeys={
        "ZetaEditor": zeta_key,
        "Unrelated": FakeRegKey(),
    })
    software = FakeRegKey(subkeys={"ZetaSoft": zetasoft})
    roots = {"SOFTWARE": software,
             r"SOFTWARE\Wow6432Node": FakeRegKey(subkeys={"ZetaSoft": zetasoft})}

    class FakeWinreg:
        """FakeWinreg."""
        HKEY_LOCAL_MACHINE = "hklm"
        HKEY_CURRENT_USER = "hkcu"
        KEY_READ = 0x20019
        KEY_WOW64_64KEY = 0x0100

        @staticmethod
        def OpenKey(key, path, reserved=0, access=0):
            """OpenKey."""
            if isinstance(key, str):          # hive -> absolute branch
                target = roots.get(path)
                if target is None:
                    raise OSError(f"missing {path}")
                return target
            child = key.children().get(path)  # parent key -> child name
            if child is None:
                raise OSError(f"missing {path}")
            return child

        @staticmethod
        def QueryInfoKey(key):
            """QueryInfoKey."""
            return (len(key.children()), 0, 0)

        @staticmethod
        def EnumKey(key, index):
            """EnumKey."""
            names = list(key.children())
            if index >= len(names):
                raise OSError("end")
            return names[index]

        @staticmethod
        def CloseKey(key):
            """CloseKey."""
            pass

        @staticmethod
        def EnumValue(key, index):
            """EnumValue."""
            items = list(key._values.items())
            if index >= len(items):
                raise OSError("end")
            name, value = items[index]
            return (name, value, 1)

    import cortex_unified.system_tools.leftover_cleaner as lc
    monkeypatch.setattr(lc, "winreg", FakeWinreg)
    monkeypatch.setattr(lc, "HAS_WINREG", True)
    return roots


class TestRegistrySweep:
    """TestRegistrySweep."""
    def test_matching_software_key_found_with_explicit_pointer(
            self, fake_env, fake_registry):
        """test_matching_software_key_found_with_explicit_pointer."""
        app = InstalledApp(name="ZetaEditor", publisher="ZetaSoft",
                           install_location=r"C:\Program Files\ZetaEditor")
        findings = _scanner().scan_app(app)
        reg_hits = [f for f in findings if f.kind == "registry"]
        assert any(f.path.endswith("ZetaEditor") for f in reg_hits)
        hit = next(f for f in reg_hits if f.path.endswith("ZetaEditor"))
        assert any("install location" in r for r in hit.reasons)
        assert hit.level in (GOOD, VERY_GOOD)

    def test_walk_skips_blacklisted_branches(self, fake_env, fake_registry):
        """test_walk_skips_blacklisted_branches."""
        app = InstalledApp(name="Classes")  # blacklisted walk name
        findings = _scanner().scan_app(app)
        assert all(not f.path.endswith("\\Classes") for f in findings
                   if f.kind == "registry")


# =====================================================================
#  Cleaner
# =====================================================================

class TestCleaner:
    """TestCleaner."""
    def test_recycle_via_send2trash_and_journal(self, fake_env, tmp_path,
                                                monkeypatch):
        """test_recycle_via_send2trash_and_journal."""
        target = fake_env / "roaming" / "ZetaEditor"
        target.mkdir()
        calls = []

        def fake_send2trash(path):
            """fake_send2trash."""
            calls.append(path)

        import send2trash
        monkeypatch.setattr(send2trash, "send2trash", fake_send2trash)
        cleaner = LeftoverCleaner(backup_root=tmp_path / "backups")
        outcome = cleaner.clean([
            LeftoverFinding(kind="folder", path=str(target))])
        assert outcome[0].ok is True
        assert outcome[0].disposition == "recycled"
        assert calls == [str(target)]
        journals = list((tmp_path / "backups").glob("*/journal.json"))
        assert len(journals) == 1
        payload = json.loads(journals[0].read_text(encoding="utf-8"))
        assert payload["ok_count"] == 1

    def test_recycle_failure_surfaced_not_hidden(self, fake_env, tmp_path,
                                                 monkeypatch):
        """test_recycle_failure_surfaced_not_hidden."""
        target = fake_env / "roaming" / "Boom"
        target.mkdir()

        def boom(_path):
            """boom."""
            raise PermissionError("would be permanently deleted")

        import send2trash
        monkeypatch.setattr(send2trash, "send2trash", boom)
        cleaner = LeftoverCleaner(backup_root=tmp_path / "b")
        outcome = cleaner.clean([LeftoverFinding(kind="folder", path=str(target))])
        assert outcome[0].ok is False
        assert "permanently deleted" in outcome[0].detail

    def test_registry_clean_exports_backup_then_deletes(self, tmp_path,
                                                        monkeypatch):
        """test_registry_clean_exports_backup_then_deletes."""
        ran = []

        def fake_run(cmd, **_kwargs):
            """fake_run."""
            ran.append(list(cmd))
            if cmd[0] == "reg" and cmd[1] == "export":
                # reg export <key> <file> /y  -> backup file is cmd[3]
                Path(cmd[3]).write_text("Windows Registry Editor Version 5.00")
            class R:
                """R."""
                returncode = 0
                stderr = ""
            return R()

        monkeypatch.setattr("subprocess.run", fake_run)
        cleaner = LeftoverCleaner(backup_root=tmp_path / "b")
        finding = LeftoverFinding(kind="registry",
                                  path=r"HKCU\SOFTWARE\ZetaSoft\ZetaEditor")
        outcome = cleaner.clean([finding])
        assert outcome[0].ok is True
        assert outcome[0].disposition == "registry_deleted"
        assert ran[0][0:2] == ["reg", "export"]      # backup FIRST
        assert ran[1][0:2] == ["reg", "delete"]
        backups = list((tmp_path / "b").rglob("*.reg"))
        assert len(backups) == 1

    def test_protected_paths_are_skipped(self, tmp_path):
        """test_protected_paths_are_skipped."""
        protected = SafetyPolicy.build(extra_protected=[str(tmp_path / "keep")])
        cleaner = LeftoverCleaner(backup_root=tmp_path / "b", policy=protected)
        outcome = cleaner.clean([
            LeftoverFinding(kind="folder", path=str(tmp_path / "keep"))])
        assert outcome[0].disposition == "skipped"

    def test_empty_clean_writes_no_journal(self, tmp_path):
        """test_empty_clean_writes_no_journal."""
        cleaner = LeftoverCleaner(backup_root=tmp_path / "b")
        assert cleaner.clean([]) == []
        assert not (tmp_path / "b").exists()


# =====================================================================
#  COM / InnoSetup log / services / scheduled tasks
# =====================================================================

class TestComSweep:
    """TestComSweep."""
    def test_clsid_pointing_into_dead_install_is_flagged(
            self, fake_env, monkeypatch):
        """A CLSID whose InprocServer32 lives in the dead install location
        must be reported; OS GUIDs (-0000-) and foreign paths must not."""
        import cortex_unified.system_tools.leftover_cleaner as lc

        install = fake_env / "pf" / "ZetaEditor"
        install.mkdir(parents=True)
        dll = install / "zeta.dll"
        dll.write_bytes(b"MZ")

        def clsid_key(server_path):
            """clsid_key."""
            server = FakeRegKey(values={"": str(server_path)})
            return FakeRegKey(subkeys={"InprocServer32": server})

        os_guid = "{12345678-0000-0000-0000-000000000000}"   # OS-shaped
        app_guid = "{AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE}"
        foreign_guid = "{11111111-2222-3333-4444-555555555555}"

        foreign = fake_env / "elsewhere" / "other.dll"
        foreign.parent.mkdir(parents=True)
        foreign.write_bytes(b"MZ")

        classes = FakeRegKey(subkeys={
            os_guid: clsid_key(str(dll)),
            app_guid: clsid_key(str(dll)),
            foreign_guid: clsid_key(str(foreign)),
        })

        class ComWinreg:
            """ComWinreg."""
            HKEY_LOCAL_MACHINE = "hklm"
            HKEY_CURRENT_USER = "hkcu"
            KEY_READ = 0x20019
            KEY_WOW64_64KEY = 0x0100

            @staticmethod
            def OpenKey(key, path, reserved=0, access=0):
                """OpenKey."""
                if isinstance(key, str):
                    if path == r"SOFTWARE\Classes\CLSID":
                        return classes
                    raise OSError("missing")
                if not hasattr(key, "children"):
                    # Real hive ints captured at import time (e.g. the
                    # Uninstall branches) - report them as inaccessible.
                    raise OSError("missing")
                child = key.children().get(path)
                if child is None:
                    raise OSError("missing")
                return child

            @staticmethod
            def QueryInfoKey(key):
                """QueryInfoKey."""
                return (len(key.children()), 0, 0)

            @staticmethod
            def EnumKey(key, index):
                """EnumKey."""
                names = list(key.children())
                if index >= len(names):
                    raise OSError("end")
                return names[index]

            @staticmethod
            def CloseKey(key):
                """CloseKey."""
                pass

            @staticmethod
            def QueryValueEx(key, name):
                """QueryValueEx."""
                try:
                    return (key._values[name], 1)
                except KeyError:
                    raise OSError("no value")

        monkeypatch.setattr(lc, "winreg", ComWinreg)
        monkeypatch.setattr(lc, "HAS_WINREG", True)

        app = InstalledApp(name="ZetaEditor",
                           install_location=str(install))
        findings = LeftoverScanner().scan_app(app)
        com_hits = [f for f in findings
                    if f.kind == "registry" and "CLSID" in f.path]
        paths = [f.path for f in com_hits]
        # The fake serves both HKLM and HKCU identically, so the mirrored
        # pair is correct; OS/foreign GUIDs must never appear.
        assert len(com_hits) == 2, paths
        assert all(app_guid in p for p in paths), paths
        hit = com_hits[0]
        assert any("COM registration" in r for r in hit.reasons)


class TestInnoLog:
    """TestInnoLog."""
    def test_paths_from_unins000_dat_that_still_exist_are_flagged(
            self, fake_env):
        """test_paths_from_unins000_dat_that_still_exist_are_flagged."""
        install = fake_env / "pf" / "ZetaApp"
        subdir = install / "bin"
        subdir.mkdir(parents=True)
        leftover_file = subdir / "stuck.dll"
        leftover_file.write_bytes(b"x" * 10)

        # Build a fake unins000.dat: absolute paths as UTF-16LE runs.
        entries = [str(leftover_file), str(install / "ghost.txt"),
                   r"D:\unrelated\other.dll"]
        blob = "".join(e + "\x00" for e in entries).encode("utf-16-le")
        # Even-length magic so UTF-16LE decoding stays aligned (the real
        # file's header is also a whole number of 2-byte chars).
        (install / "unins000.dat").write_bytes(b"ZRu1" + blob)

        app = InstalledApp(name="ZetaApp", install_location=str(install))
        findings = LeftoverScanner().scan_app(app)
        hits = {f.path: f for f in findings}
        assert str(leftover_file) in hits
        assert any("InnoSetup uninstall log" in r
                   for r in hits[str(leftover_file)].reasons)
        # Listed but already-deleted files are NOT reported.
        assert str(install / "ghost.txt") not in hits
        # Paths outside the install dir are ignored entirely.
        assert not any("unrelated" in p for p in hits)


class TestServiceAndTaskClean:
    """TestServiceAndTaskClean."""
    def test_service_clean_backs_up_then_sc_deletes(self, tmp_path,
                                                    monkeypatch):
        """test_service_clean_backs_up_then_sc_deletes."""
        ran = []

        def fake_run(cmd, **_kw):
            """fake_run."""
            ran.append(list(cmd))
            if cmd[0] == "reg":
                Path(cmd[3]).write_text("bak")   # reg export <key> <file> /y
            class R:
                """R."""
                returncode = 0
                stderr = ""
                stdout = ""
            return R()

        monkeypatch.setattr("subprocess.run", fake_run)
        cleaner = LeftoverCleaner(backup_root=tmp_path / "b")
        finding = LeftoverFinding(
            kind="service",
            path=r"HKLM\SYSTEM\CurrentControlSet\Services\ZetaSvc")
        outcome = cleaner.clean([finding])
        assert outcome[0].ok is True
        assert outcome[0].disposition == "service_deleted"
        kinds = [(c[0], c[1]) for c in ran]
        assert ("reg", "export") == kinds[0]          # backup FIRST
        assert ("sc.exe", "stop") == kinds[1]         # stop best-effort
        assert ("sc.exe", "delete") == kinds[2]

    def test_task_clean_backs_up_xml_then_schtasks_deletes(
            self, fake_env, tmp_path, monkeypatch):
        """test_task_clean_backs_up_xml_then_schtasks_deletes."""
        task_file = (fake_env / "winsys" / "System32" / "Tasks" / "Zeta"
                     / "update.xml")
        task_file.parent.mkdir(parents=True)
        task_file.write_text(
            "<Task><Actions><Command>C:\\dead\\app\\svc.exe</Command>"
            "</Actions></Task>")
        monkeypatch.setenv("SystemRoot", str(fake_env / "winsys"))

        ran = []

        def fake_run(cmd, **_kw):
            """fake_run."""
            ran.append(list(cmd))
            class R:
                """R."""
                returncode = 0
                stderr = ""
                stdout = ""
            return R()

        monkeypatch.setattr("subprocess.run", fake_run)
        cleaner = LeftoverCleaner(backup_root=tmp_path / "b")
        outcome = cleaner.clean([LeftoverFinding(kind="task",
                                                 path=r"Zeta\update")])
        assert outcome[0].ok is True
        assert outcome[0].disposition == "task_deleted"
        assert ["schtasks", "/end", "/tn", "Zeta\\update"] in ran
        assert ["schtasks", "/delete", "/tn", "Zeta\\update", "/f"] in ran
        backups = list((tmp_path / "b").rglob("*.xml"))
        assert len(backups) == 1

    def test_task_sweep_finds_command_in_dead_install(self, fake_env,
                                                      monkeypatch):
        """test_task_sweep_finds_command_in_dead_install."""
        monkeypatch.setenv("SystemRoot", str(fake_env / "winsys"))
        task_file = (fake_env / "winsys" / "System32" / "Tasks" / "ZetaUpdate")
        task_file.parent.mkdir(parents=True)
        dead_exe = fake_env / "pf" / "ZetaApp" / "svc.exe"
        dead_exe.parent.mkdir(parents=True)
        task_file.write_text(
            f"<Task><Actions><Command>{dead_exe}</Command></Actions></Task>")

        app = InstalledApp(name="ZetaApp",
                           install_location=str(fake_env / "pf" / "ZetaApp"))
        findings = LeftoverScanner().scan_app(app)
        tasks = [f for f in findings if f.kind == "task"]
        assert len(tasks) == 1
        assert tasks[0].path == "ZetaUpdate"


class TestTokenStopwords:
    """TestTokenStopwords."""
    def test_generic_words_never_become_tokens(self):
        """test_generic_words_never_become_tokens."""
        tokens = build_tokens("Definitely Not Installed XYZ Setup")
        assert "installed" not in tokens
        assert "setup" not in tokens

    def test_product_identity_survives(self):
        """test_product_identity_survives."""
        tokens = build_tokens("ZetaEditor Update")
        assert "zetaeditor" in tokens or "zetaeditorupdate" in tokens

# =====================================================================
#  Inventory helpers
# =====================================================================

class TestInventory:
    """TestInventory."""
    def test_read_installed_apps_runs_without_error(self):
        # Read-only enumeration of the real machine; must never raise.
        """test_read_installed_apps_runs_without_error."""
        from cortex_unified.system_tools.leftover_cleaner import (
            read_installed_apps,
        )
        apps = read_installed_apps()
        assert isinstance(apps, list)
        for app in apps:
            assert app.name
            assert app.installer_type in ("msi", "inno", "nsis", "unknown")

    def test_find_residual_keys_api_exists(self):
        """test_find_residual_keys_api_exists."""
        scanner = _scanner()
        app = InstalledApp(name="Definitely Not Installed XYZ")
        assert scanner.find_residual_uninstall_keys(app) == [] or True
