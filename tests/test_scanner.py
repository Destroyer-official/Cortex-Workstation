"""Tests for the filesystem Scanner component."""

import os
from pathlib import Path
from cortex_unified.core.scanner import Scanner

def test_scanner_finds_empty_files(test_env, clean_config):
    """Test that scanner identifies empty files correctly."""
    scanner = Scanner(clean_config, str(test_env))
    empty_files, empty_dirs = scanner.scan()
    
    assert len(empty_files) == 2
    filenames = [Path(f).name for f in empty_files]
    assert "empty1.txt" in filenames
    assert "empty2.log" in filenames
    assert "nonempty.txt" not in filenames

def test_scanner_finds_empty_dirs(test_env, clean_config):
    """Test that scanner identifies empty directories correctly."""
    scanner = Scanner(clean_config, str(test_env))
    empty_files, empty_dirs = scanner.scan()
    
    assert len(empty_dirs) == 2
    dirnames = [Path(d).name for d in empty_dirs]
    assert "empty_dir1" in dirnames
    assert "empty_dir2" in dirnames
    assert "nonempty_dir" not in dirnames

def test_scanner_exclude_patterns(test_env, clean_config):
    """Test that scanner respects exclude patterns."""
    clean_config.config_data["exclude_patterns"] = ["*.log"]
    scanner = Scanner(clean_config, str(test_env))
    empty_files, empty_dirs = scanner.scan()
    
    assert len(empty_files) == 1
    filenames = [Path(f).name for f in empty_files]
    assert "empty1.txt" in filenames
    assert "empty2.log" not in filenames

def test_scanner_stats(test_env, clean_config):
    """Test that scanner calculates statistics correctly."""
    scanner = Scanner(clean_config, str(test_env))
    scanner.scan()
    stats = scanner.get_stats()
    
    assert stats["empty_files_count"] == 2
    assert stats["empty_dirs_count"] == 2
    assert stats["total_empty_count"] == 4
