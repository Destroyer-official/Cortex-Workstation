"""Unit and integration tests for Winapp2Cleaner engine."""

import os
import tempfile
from pathlib import Path
import pytest

from cortex_unified.system_tools.winapp2_cleaner import (
    AppCleanTarget,
    Winapp2Cleaner,
    Winapp2Report,
    Winapp2Rule,
)


def test_winapp2_cleaner_initialization():
    cleaner = Winapp2Cleaner()
    assert len(cleaner.rules) >= 10
    names = [r.name for r in cleaner.rules]
    assert "Discord Cache" in names
    assert "Spotify Cache" in names


def test_winapp2_expand_vars(monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", "C:\\Users\\TestUser\\AppData\\Local")
    monkeypatch.setenv("APPDATA", "C:\\Users\\TestUser\\AppData\\Roaming")

    res = Winapp2Cleaner.expand_vars("%LOCALAPPDATA%\\Google\\Chrome")
    assert "C:\\Users\\TestUser\\AppData\\Local\\Google\\Chrome" in res

    res2 = Winapp2Cleaner.expand_vars("%APPDATA%\\discord")
    assert "C:\\Users\\TestUser\\AppData\\Roaming\\discord" in res2


def test_winapp2_path_safety():
    cleaner = Winapp2Cleaner()
    # Critical roots must not be considered safe
    assert not cleaner.is_safe_path(Path("C:/Windows"))
    assert not cleaner.is_safe_path(Path("C:/Windows/System32"))
    assert not cleaner.is_safe_path(Path("C:/"))

    # Safe subdirectory in AppData
    assert cleaner.is_safe_path(Path("C:/Users/User/AppData/Local/Temp/cache.tmp"))


def test_winapp2_scan_and_clean(tmp_path, monkeypatch):
    # Setup simulated app tree
    app_root = tmp_path / "DummyApp"
    app_root.mkdir()
    cache_dir = app_root / "Cache"
    cache_dir.mkdir()
    file1 = cache_dir / "item1.dat"
    file1.write_bytes(b"hello world")
    file2 = cache_dir / "item2.dat"
    file2.write_bytes(b"1234567890")

    ini_content = f"""
[DummyApp *]
Section=Applications
Detect={app_root}
Default=True
FileKey1={cache_dir}|*.dat|RECURSE
"""
    cleaner = Winapp2Cleaner(custom_ini_content=ini_content)
    assert len(cleaner.rules) == 1
    assert cleaner.rules[0].name == "DummyApp"

    report = cleaner.scan()
    assert report.installed_apps_count == 1
    assert len(report.targets) == 2
    assert report.total_bytes == (len(b"hello world") + len(b"1234567890"))

    # Dry-run clean
    cleaned_bytes, cleaned_items = cleaner.clean(report.targets, dry_run=True)
    assert cleaned_bytes == report.total_bytes
    assert cleaned_items == 2
    assert file1.exists()

    # Real clean
    cleaned_bytes, cleaned_items = cleaner.clean(report.targets, dry_run=False)
    assert cleaned_bytes == report.total_bytes
    assert cleaned_items == 2
    assert not file1.exists()
    assert not file2.exists()
