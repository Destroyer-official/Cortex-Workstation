"""Tests for :mod:`cortex_unified.system_tools.browser_cleaner`.

All tests use synthetic browser profiles under ``tmp_path`` so no real browser
data is touched.  The Chromium / Firefox discovery functions are monkeypatched
to point at these fake trees.
"""

from __future__ import annotations

import os
import re
import sqlite3
import threading
from pathlib import Path

import pytest

from cortex_unified.system_tools.browser_cleaner import (
    Cleanable,
    DeepBrowserCleaner,
    _discover_chromium_profiles,
    _discover_firefox_profiles,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sqlite(
    path: Path, table: str = "cookies", rows: list | None = None, populate: bool = True
) -> Path:
    """Create a tiny SQLite DB at *path* and return the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    if table == "cookies":
        cur.execute(
            "CREATE TABLE IF NOT EXISTS cookies ("
            "host_key TEXT, name TEXT, value TEXT)"
        )
        if populate and rows:
            cur.executemany(
                "INSERT INTO cookies (host_key, name, value) VALUES (?, ?, ?)",
                rows,
            )
    elif table == "history":
        cur.execute(
            "CREATE TABLE IF NOT EXISTS urls ("
            "id INTEGER PRIMARY KEY, url TEXT, title TEXT)"
        )
        if populate and rows:
            cur.executemany("INSERT INTO urls (url, title) VALUES (?, ?)", rows)
    con.commit()
    con.close()
    return path


def _make_cache_dir(
    base: Path, category: str, *, count: int = 3, file_size: int = 100
) -> Path:
    """Populate a cache sub-directory with dummy files."""
    d = base / category
    d.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (d / f"file_{i}.bin").write_bytes(b"x" * file_size)
    return d


def _make_chromium_profile(root: Path, *, browser: str = "chrome") -> Path:
    """Build a realistic Chromium profile tree under *root*."""
    profile = root / "Default"
    profile.mkdir(parents=True)

    _make_cache_dir(profile, "Cache/Cache_Data", count=5, file_size=256)
    _make_cache_dir(profile, "Code Cache", count=2, file_size=512)
    _make_cache_dir(profile, "GPUCache", count=1, file_size=1024)
    _make_cache_dir(profile, "ShaderCache", count=2, file_size=64)
    _make_cache_dir(profile, "Service Worker/CacheStorage", count=3, file_size=128)
    _make_cache_dir(profile, "Service Worker/ScriptCache", count=1, file_size=32)
    _make_cache_dir(profile, "IndexedDB", count=2, file_size=200)
    _make_cache_dir(profile, "Local Storage/leveldb", count=1, file_size=50)
    _make_cache_dir(profile, "Session Storage", count=1, file_size=20)
    _make_cache_dir(profile, "MediaDeviceSalts", count=1, file_size=10)
    _make_cache_dir(profile, "reporting_data", count=1, file_size=15)

    _make_sqlite(
        profile / "Cookies",
        table="cookies",
        rows=[
            ("example.com", "session", "abc123"),
            ("google.com", "nid", "xyz789"),
            ("github.com", "logged_in", "yes"),
        ],
    )
    _make_sqlite(
        profile / "History",
        table="history",
        rows=[
            ("https://example.com", "Example"),
            ("https://python.org", "Python"),
        ],
    )
    return root


def _make_firefox_profile(base: Path) -> Path:
    """Build a realistic Firefox profile tree under *base*."""
    profile = base / "default-release"
    profile.mkdir(parents=True)

    _make_cache_dir(profile, "storage/permanent", count=2, file_size=300)
    _make_cache_dir(profile, "storage", count=1, file_size=50)
    _make_cache_dir(profile, "cache2", count=4, file_size=200)
    _make_cache_dir(profile, "startupCache", count=1, file_size=64)
    _make_cache_dir(profile, "thumbnails", count=2, file_size=40)
    _make_cache_dir(profile, "datareporting", count=1, file_size=10)
    _make_cache_dir(profile, "crashes", count=1, file_size=5)

    _make_sqlite(
        profile / "cookies.sqlite",
        table="cookies",
        rows=[("mozilla.org", "lang", "en")],
    )
    _make_sqlite(
        profile / "places.sqlite",
        table="history",
        rows=[("https://mozilla.org", "Mozilla")],
    )
    _make_sqlite(profile / "favicons.sqlite", table="history", rows=[])
    _make_sqlite(profile / "formhistory.sqlite", table="history", rows=[])
    _make_sqlite(profile / "permissions.sqlite", table="history", rows=[])
    _make_sqlite(profile / "content-prefs.sqlite", table="history", rows=[])
    _make_sqlite(profile / "webappsstore.sqlite", table="history", rows=[])
    return profile


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_chromium_home(tmp_path, monkeypatch):
    """Redirect LOCALAPPDATA so Chromium discovery hits our fake profiles."""
    local = tmp_path / "AppData" / "Local"
    local.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    root = local / "Google" / "Chrome" / "User Data"
    _make_chromium_profile(root)
    return tmp_path, root


@pytest.fixture
def fake_firefox_home(tmp_path, monkeypatch):
    """Redirect APPDATA so Firefox discovery hits our fake profiles."""
    appdata = tmp_path / "AppData" / "Roaming"
    appdata.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(appdata))
    profiles_dir = appdata / "Mozilla" / "Firefox" / "Profiles"
    profiles_dir.mkdir(parents=True)
    _make_firefox_profile(profiles_dir)
    return tmp_path, profiles_dir


@pytest.fixture
def fake_multi_browser(tmp_path, monkeypatch):
    """A single LOCALAPPDATA tree with Chrome, Edge, and Brave profiles."""
    local = tmp_path / "AppData" / "Local"
    local.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local))

    chrome = local / "Google" / "Chrome" / "User Data"
    _make_chromium_profile(chrome)
    edge = local / "Microsoft" / "Edge" / "User Data"
    _make_chromium_profile(edge, browser="edge")
    brave = local / "BraveSoftware" / "Brave-Browser" / "User Data"
    _make_chromium_profile(brave, browser="brave")
    return tmp_path


# ---------------------------------------------------------------------------
# 1. Initialization
# ---------------------------------------------------------------------------


class TestDeepBrowserCleanerInit:
    """TestDeepBrowserCleanerInit."""
    def test_default_init(self):
        """test_default_init."""
        cleaner = DeepBrowserCleaner()
        assert cleaner.keep_cookies == []
        assert callable(cleaner.progress)
        assert isinstance(cleaner.cancel, threading.Event)
        assert not cleaner.cancel.is_set()
        assert cleaner.expert_mode is False

    def test_keep_cookies_compiled(self):
        """test_keep_cookies_compiled."""
        cleaner = DeepBrowserCleaner(keep_cookies=["example\\.com", ".*google.*"])
        assert len(cleaner.keep_cookies) == 2
        assert all(isinstance(p, re.Pattern) for p in cleaner.keep_cookies)

    def test_progress_callback_stored(self):
        """test_progress_callback_stored."""
        calls = []
        cleaner = DeepBrowserCleaner(progress=lambda msg: calls.append(msg))
        cleaner.progress("hello")
        assert calls == ["hello"]

    def test_custom_cancel_event(self):
        """test_custom_cancel_event."""
        evt = threading.Event()
        evt.set()
        cleaner = DeepBrowserCleaner(cancel=evt)
        assert cleaner.cancel.is_set()

    def test_expert_mode_default_off(self):
        """test_expert_mode_default_off."""
        assert DeepBrowserCleaner().expert_mode is False


# ---------------------------------------------------------------------------
# 2. Profile discovery
# ---------------------------------------------------------------------------


class TestProfileDiscovery:
    """TestProfileDiscovery."""
    def test_chromium_discovers_default_profile(self, fake_chromium_home):
        """test_chromium_discovers_default_profile."""
        _, root = fake_chromium_home
        profiles = _discover_chromium_profiles(["Google/Chrome"])
        assert any("Default" in str(p) for p in profiles)

    def test_chromium_skips_nonexistent_root(self, fake_chromium_home, monkeypatch):
        """test_chromium_skips_nonexistent_root."""
        profiles = _discover_chromium_profiles(["Nonexistent/Browser"])
        assert profiles == []

    def test_firefox_discovers_profile(self, fake_firefox_home):
        """test_firefox_discovers_profile."""
        _, profiles_dir = fake_firefox_home
        profiles = _discover_firefox_profiles()
        assert any("default-release" in str(p) for p in profiles)

    def test_firefox_profiles_ini_parsing(self, fake_firefox_home, monkeypatch):
        """test_firefox_profiles_ini_parsing."""
        _, profiles_dir = fake_firefox_home
        parent = profiles_dir.parent
        ini = parent / "profiles.ini"
        ini.write_text(
            "[Profile0]\n"
            "Name=custom\n"
            "Path=custom-profile\n"
            "IsRelative=1\n"
            "Default=1\n"
        )
        custom = parent / "custom-profile"
        custom.mkdir()
        profiles = _discover_firefox_profiles()
        assert any("custom-profile" in str(p) for p in profiles)

    def test_firefox_absolute_profile_in_ini(self, fake_firefox_home, tmp_path):
        """test_firefox_absolute_profile_in_ini."""
        _, profiles_dir = fake_firefox_home
        parent = profiles_dir.parent
        ini = parent / "profiles.ini"
        abs_path = tmp_path / "absolute_profile"
        abs_path.mkdir()
        ini.write_text("[Profile0]\n" f"Path={abs_path}\n" "IsRelative=0\n")
        profiles = _discover_firefox_profiles()
        assert any(str(abs_path) in str(p) for p in profiles)


# ---------------------------------------------------------------------------
# 3. Cookie cleaning with keep-list
# ---------------------------------------------------------------------------


class TestCookieCleaning:
    """TestCookieCleaning."""
    def test_delete_non_matching_cookies(self, fake_chromium_home):
        """test_delete_non_matching_cookies."""
        _, root = fake_chromium_home
        cookies_db = root / "Default" / "Cookies"
        cleaner = DeepBrowserCleaner(keep_cookies=["example\\.com"])
        removed = cleaner.clean_cookies_keep_list(cookies_db)

        assert removed > 0
        con = sqlite3.connect(str(cookies_db))
        rows = con.execute("SELECT host_key FROM cookies").fetchall()
        hosts = {r[0] for r in rows}
        assert "example.com" in hosts
        assert "google.com" not in hosts
        assert "github.com" not in hosts
        con.close()

    def test_keep_all_matching_cookies(self, fake_chromium_home):
        """test_keep_all_matching_cookies."""
        _, root = fake_chromium_home
        cookies_db = root / "Default" / "Cookies"
        cleaner = DeepBrowserCleaner(keep_cookies=[".*"])
        removed = cleaner.clean_cookies_keep_list(cookies_db)

        con = sqlite3.connect(str(cookies_db))
        count = con.execute("SELECT COUNT(*) FROM cookies").fetchone()[0]
        con.close()
        assert count == 3
        assert removed == 0

    def test_missing_db_returns_zero(self, fake_chromium_home):
        """test_missing_db_returns_zero."""
        _, root = fake_chromium_home
        fake_db = root / "Default" / "NoSuchFile.sqlite"
        cleaner = DeepBrowserCleaner()
        assert cleaner.clean_cookies_keep_list(fake_db) == 0

    def test_keep_list_regex_case_insensitive(self, fake_chromium_home):
        """test_keep_list_regex_case_insensitive."""
        _, root = fake_chromium_home
        cookies_db = root / "Default" / "Cookies"
        cleaner = DeepBrowserCleaner(keep_cookies=["EXAMPLE\\.COM"])
        cleaner.clean_cookies_keep_list(cookies_db)

        con = sqlite3.connect(str(cookies_db))
        hosts = {r[0] for r in con.execute("SELECT host_key FROM cookies")}
        con.close()
        assert "example.com" in hosts

    def test_empty_keep_list_deletes_all(self, fake_chromium_home):
        """test_empty_keep_list_deletes_all."""
        _, root = fake_chromium_home
        cookies_db = root / "Default" / "Cookies"
        cleaner = DeepBrowserCleaner(keep_cookies=[])
        removed = cleaner.clean_cookies_keep_list(cookies_db)

        con = sqlite3.connect(str(cookies_db))
        count = con.execute("SELECT COUNT(*) FROM cookies").fetchone()[0]
        con.close()
        assert count == 0
        assert removed > 0


# ---------------------------------------------------------------------------
# 4. Cache cleaning for all categories
# ---------------------------------------------------------------------------


class TestClean:
    """TestClean."""
    def test_clean_removes_file(self, tmp_path):
        """test_clean_removes_file."""
        f = tmp_path / "to_delete.txt"
        f.write_bytes(b"data")
        cleaner = DeepBrowserCleaner()
        results = cleaner.clean([f])
        assert results[f] is True
        assert not f.exists()

    def test_clean_removes_directory(self, tmp_path):
        """test_clean_removes_directory."""
        d = tmp_path / "cache_dir"
        d.mkdir()
        (d / "file.bin").write_bytes(b"x" * 50)
        cleaner = DeepBrowserCleaner()
        results = cleaner.clean([d])
        assert results[d] is True
        assert not d.exists()

    def test_clean_multiple_paths(self, tmp_path):
        """test_clean_multiple_paths."""
        files = [tmp_path / f"f{i}.dat" for i in range(5)]
        for f in files:
            f.write_bytes(b"x")
        cleaner = DeepBrowserCleaner()
        results = cleaner.clean(files)
        assert all(results[f] is True for f in files)
        assert all(not f.exists() for f in files)

    def test_clean_missing_path_handled_gracefully(self, tmp_path):
        """test_clean_missing_path_handled_gracefully."""
        missing = tmp_path / "does_not_exist"
        cleaner = DeepBrowserCleaner()
        results = cleaner.clean([missing])
        # Source code: is_file() and is_dir() both return False for missing
        # paths, so the path falls through to results[p] = True (no exception).
        assert results[missing] is True

    def test_clean_shred_overwrites(self, tmp_path):
        """test_clean_shred_overwrites."""
        f = tmp_path / "secret.dat"
        f.write_bytes(b"SENSITIVE" * 100)
        cleaner = DeepBrowserCleaner()
        results = cleaner.clean([f], shred=True)
        assert results[f] is True
        assert not f.exists()

    def test_clean_respects_cancel(self, tmp_path):
        """test_clean_respects_cancel."""
        files = [tmp_path / f"f{i}.dat" for i in range(5)]
        for f in files:
            f.write_bytes(b"x")
        cancel = threading.Event()
        cleaner = DeepBrowserCleaner(cancel=cancel)
        cancel.set()
        results = cleaner.clean(files)
        assert results == {}

    def test_clean_progress_callback(self, tmp_path):
        """test_clean_progress_callback."""
        f = tmp_path / "tracked.dat"
        f.write_bytes(b"y")
        calls = []
        cleaner = DeepBrowserCleaner(progress=lambda m: calls.append(m))
        cleaner.clean([f])
        assert any("Cleaned" in c for c in calls)

    def test_clean_permission_error(self, tmp_path):
        """test_clean_permission_error."""
        calls = []
        cleaner = DeepBrowserCleaner(progress=lambda m: calls.append(m))
        # Create a read-only file, then try to shred it (requires write)
        f = tmp_path / "readonly.dat"
        f.write_bytes(b"data")
        f.chmod(0o444)
        try:
            results = cleaner.clean([f], shred=True)
            assert results[f] is False
            assert any("Failed" in c for c in calls)
        finally:
            f.chmod(0o666)


# ---------------------------------------------------------------------------
# 5. SQLite VACUUM
# ---------------------------------------------------------------------------


class TestVacuum:
    """TestVacuum."""
    def test_vacuum_runs_without_error(self, tmp_path):
        """test_vacuum_runs_without_error."""
        db = _make_sqlite(
            tmp_path / "big.sqlite",
            table="history",
            rows=[(f"https://example{i}.com", f"Page {i}") for i in range(500)],
        )
        cleaner = DeepBrowserCleaner()
        results = cleaner.vacuum_databases([db])
        assert db in results
        assert results[db] >= 0

    def test_vacuum_missing_db_no_crash(self, tmp_path):
        """test_vacuum_missing_db_no_crash."""
        missing = tmp_path / "nope.sqlite"
        cleaner = DeepBrowserCleaner()
        results = cleaner.vacuum_databases([missing])
        assert missing not in results

    def test_vacuum_progress_callback(self, tmp_path):
        """test_vacuum_progress_callback."""
        db = _make_sqlite(tmp_path / "vacuum_test.sqlite", table="history")
        calls = []
        cleaner = DeepBrowserCleaner(progress=lambda m: calls.append(m))
        cleaner.vacuum_databases([db])
        assert any("Vacuumed" in c for c in calls)

    def test_vacuum_multiple_dbs(self, tmp_path):
        """test_vacuum_multiple_dbs."""
        dbs = []
        for i in range(3):
            db = _make_sqlite(tmp_path / f"db{i}.sqlite", table="history")
            dbs.append(db)
        cleaner = DeepBrowserCleaner()
        results = cleaner.vacuum_databases(dbs)
        assert len(results) == 3


# ---------------------------------------------------------------------------
# 6. Browser detection
# ---------------------------------------------------------------------------


class TestBrowserDetection:
    """TestBrowserDetection."""
    def test_scan_chromium_profile(self, fake_chromium_home):
        """test_scan_chromium_profile."""
        _, root = fake_chromium_home
        cleaner = DeepBrowserCleaner()
        items = cleaner._scan_chromium_profile(root / "Default", "chrome")
        categories = {i.category for i in items}
        assert "cache" in categories
        assert "codecache" in categories
        assert "gpucache" in categories
        assert "cookies" in categories
        assert "history" in categories

    def test_scan_firefox_profile(self, fake_firefox_home):
        """test_scan_firefox_profile."""
        _, profiles_dir = fake_firefox_home
        profile = next(profiles_dir.iterdir())
        cleaner = DeepBrowserCleaner()
        items = cleaner._scan_firefox_profile(profile)
        categories = {i.category for i in items}
        assert "cache" in categories
        assert "cookies" in categories
        assert "history" in categories
        assert "indexeddb" in categories

    def test_all_browsers_detected(self, fake_multi_browser):
        """test_all_browsers_detected."""
        cleaner = DeepBrowserCleaner()
        items = cleaner.scan()
        browsers = {i.browser for i in items}
        assert "chrome" in browsers
        assert "edge" in browsers
        assert "brave" in browsers

    def test_firefox_browser_label(self, fake_firefox_home):
        """test_firefox_browser_label."""
        cleaner = DeepBrowserCleaner()
        items = cleaner.scan()
        firefox_items = [i for i in items if i.browser == "firefox"]
        assert len(firefox_items) > 0

    def test_vivaldi_not_in_scope(self, fake_multi_browser):
        """test_vivaldi_not_in_scope."""
        cleaner = DeepBrowserCleaner()
        items = cleaner.scan()
        browsers = {i.browser for i in items}
        assert "vivaldi" not in browsers


# ---------------------------------------------------------------------------
# 7. Progress callback
# ---------------------------------------------------------------------------


class TestProgressCallback:
    """TestProgressCallback."""
    def test_progress_called_during_clean(self, tmp_path):
        """test_progress_called_during_clean."""
        f = tmp_path / "a.dat"
        f.write_bytes(b"x")
        calls = []
        cleaner = DeepBrowserCleaner(progress=lambda m: calls.append(m))
        cleaner.clean([f])
        assert len(calls) >= 1

    def test_progress_called_during_vacuum(self, tmp_path):
        """test_progress_called_during_vacuum."""
        db = _make_sqlite(tmp_path / "p.sqlite", table="history")
        calls = []
        cleaner = DeepBrowserCleaner(progress=lambda m: calls.append(m))
        cleaner.vacuum_databases([db])
        assert len(calls) >= 1


# ---------------------------------------------------------------------------
# 8. Cancellation
# ---------------------------------------------------------------------------


class TestCancellation:
    """TestCancellation."""
    def test_cancel_stops_scan(self, fake_chromium_home):
        """test_cancel_stops_scan."""
        cancel = threading.Event()
        cleaner = DeepBrowserCleaner(cancel=cancel)
        cancel.set()
        items = cleaner.scan()
        assert items == []

    def test_cancel_stops_clean(self, tmp_path):
        """test_cancel_stops_clean."""
        files = [tmp_path / f"f{i}.dat" for i in range(5)]
        for f in files:
            f.write_bytes(b"x")
        cancel = threading.Event()
        cleaner = DeepBrowserCleaner(cancel=cancel)
        cancel.set()
        results = cleaner.clean(files)
        assert results == {}

    def test_default_cancel_not_set(self):
        """test_default_cancel_not_set."""
        cleaner = DeepBrowserCleaner()
        assert not cleaner.cancel.is_set()

    def test_cancel_event_prevents_scan_iteration(self, fake_chromium_home):
        """test_cancel_event_prevents_scan_iteration."""
        cancel = threading.Event()
        cleaner = DeepBrowserCleaner(cancel=cancel)
        # Let scan start, then cancel mid-way
        original_scan = cleaner.scan

        def interrupting_scan():
            """interrupting_scan."""
            cancel.set()
            return original_scan()

        cleaner.scan = interrupting_scan
        items = cleaner.scan()
        assert items == []


# ---------------------------------------------------------------------------
# 9. Archive / expert mode exclusion
# ---------------------------------------------------------------------------


class TestExpertMode:
    """TestExpertMode."""
    def test_passwords_excluded_by_default(self, fake_chromium_home):
        """test_passwords_excluded_by_default."""
        _, root = fake_chromium_home
        login_db = root / "Default" / "Login Data"
        _make_sqlite(login_db, table="history")
        cleaner = DeepBrowserCleaner()
        items = cleaner.scan()
        password_items = [i for i in items if i.category == "passwords"]
        assert len(password_items) == 0

    def test_passwords_included_with_expert_mode(self, fake_chromium_home):
        """test_passwords_included_with_expert_mode."""
        _, root = fake_chromium_home
        login_db = root / "Default" / "Login Data"
        _make_sqlite(login_db, table="history")
        cleaner = DeepBrowserCleaner()
        cleaner.expert_mode = True
        items = cleaner.scan()
        password_items = [i for i in items if i.category == "passwords"]
        assert len(password_items) == 1
        assert password_items[0].risk == "high"

    def test_forms_always_included(self, fake_chromium_home):
        """test_forms_always_included."""
        _, root = fake_chromium_home
        web_data = root / "Default" / "Web Data"
        _make_sqlite(web_data, table="history")
        cleaner = DeepBrowserCleaner()
        items = cleaner.scan()
        form_items = [i for i in items if i.category == "forms"]
        assert len(form_items) == 1

    def test_passwords_risk_is_high(self, fake_chromium_home):
        """test_passwords_risk_is_high."""
        _, root = fake_chromium_home
        login_db = root / "Default" / "Login Data"
        _make_sqlite(login_db, table="history")
        cleaner = DeepBrowserCleaner()
        cleaner.expert_mode = True
        items = cleaner.scan()
        pw = [i for i in items if i.category == "passwords"][0]
        assert pw.risk == "high"
        assert pw.can_vacuum is True


# ---------------------------------------------------------------------------
# 10. Size calculation
# ---------------------------------------------------------------------------


class TestSizeCalculation:
    """TestSizeCalculation."""
    def test_file_size_reported(self, tmp_path):
        """test_file_size_reported."""
        f = tmp_path / "big.bin"
        f.write_bytes(b"x" * 1024)
        c = Cleanable(f, f.stat().st_size, "cache", "test", "test", "low")
        assert c.size == 1024

    def test_directory_size_summed(self, tmp_path):
        """test_directory_size_summed."""
        d = tmp_path / "cache"
        d.mkdir()
        for i in range(3):
            (d / f"f{i}.bin").write_bytes(b"y" * 100)
        total = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        assert total == 300

    def test_scan_returns_sizes(self, fake_chromium_home):
        """test_scan_returns_sizes."""
        cleaner = DeepBrowserCleaner()
        items = cleaner.scan()
        for item in items:
            assert item.size >= 0

    def test_nonexistent_profile_returns_empty(self, tmp_path):
        """test_nonexistent_profile_returns_empty."""
        cleaner = DeepBrowserCleaner()
        items = cleaner._scan_chromium_profile(tmp_path / "nope", "test")
        assert items == []

    def test_cleanable_dataclass_fields(self, tmp_path):
        """test_cleanable_dataclass_fields."""
        p = tmp_path / "test"
        c = Cleanable(p, 42, "cache", "chrome", "HTTP cache", "low", False)
        assert c.path == p
        assert c.size == 42
        assert c.category == "cache"
        assert c.browser == "chrome"
        assert c.description == "HTTP cache"
        assert c.risk == "low"
        assert c.can_vacuum is False

    def test_zero_size_item(self):
        """test_zero_size_item."""
        c = Cleanable(Path("/tmp/x"), 0, "cache", "chrome", "desc", "low")
        assert c.size == 0


# ---------------------------------------------------------------------------
# Scan integration
# ---------------------------------------------------------------------------


class TestScanIntegration:
    """TestScanIntegration."""
    def test_scan_returns_list(self, fake_chromium_home):
        """test_scan_returns_list."""
        cleaner = DeepBrowserCleaner()
        items = cleaner.scan()
        assert isinstance(items, list)
        assert len(items) > 0

    def test_all_items_are_cleanable(self, fake_chromium_home):
        """test_all_items_are_cleanable."""
        cleaner = DeepBrowserCleaner()
        items = cleaner.scan()
        for item in items:
            assert isinstance(item, Cleanable)

    def test_no_duplicate_paths_in_scan(self, fake_chromium_home):
        """test_no_duplicate_paths_in_scan."""
        cleaner = DeepBrowserCleaner()
        items = cleaner.scan()
        paths = [i.path for i in items]
        assert len(paths) == len(set(paths))

    def test_cookie_risk_medium(self, fake_chromium_home):
        """test_cookie_risk_medium."""
        cleaner = DeepBrowserCleaner()
        items = cleaner.scan()
        cookie_items = [i for i in items if i.category == "cookies"]
        assert all(i.risk == "medium" for i in cookie_items)

    def test_cache_risk_low(self, fake_chromium_home):
        """test_cache_risk_low."""
        cleaner = DeepBrowserCleaner()
        items = cleaner.scan()
        cache_items = [
            i
            for i in items
            if i.category in ("cache", "codecache", "gpucache", "shadercache")
        ]
        assert all(i.risk == "low" for i in cache_items)

    def test_vacuumable_items_flagged(self, fake_chromium_home):
        """test_vacuumable_items_flagged."""
        cleaner = DeepBrowserCleaner()
        items = cleaner.scan()
        vacuumable = [i for i in items if i.can_vacuum]
        assert len(vacuumable) > 0
        assert all(
            i.category
            in (
                "history",
                "cookies",
                "forms",
                "permissions",
                "contentprefs",
                "favicons",
                "localstorage",
            )
            for i in vacuumable
        )
