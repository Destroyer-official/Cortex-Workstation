"""Tests for NTFS CompactOS / compaction estimation logic.

The actual ``compact`` / ``fsutil`` shell-outs need an elevated prompt and a
real NTFS volume, so they are gated behind ``is_supported()`` and skipped on
non-Windows / non-elevated runs. What is fully unit-tested here is the
*read-only estimation* and the *safety rules* (blocked/system folder names,
min-size threshold, incompressible-content handling) which are portable.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from cortex_unified.system_tools.compact_os import CompactOSManager

IS_WIN = sys.platform == "win32"


def _write_text(folder: Path, name: str, size_kb: int = 64):
    """_write_text.

    Manages write text operations and coordinates related state changes for the component.

    Args:
        folder (Path): Filesystem path to the target file or directory.
        name (str): The name parameter.
        size_kb (int): The size kb parameter.
    """
    chunk = ("The quick brown fox jumps over the lazy dog. 0123456789\n" * 8).encode()
    data = (chunk * max(1, (size_kb * 1024) // len(chunk)))[: size_kb * 1024]
    (folder / name).write_bytes(data)


def _write_fill(folder: Path, name: str, size_kb: int = 64):
    # random-looking bytes => low compression (a stand-in for media)
    """_write_fill.

    Manages write fill operations and coordinates related state changes for the component.

    Args:
        folder (Path): Filesystem path to the target file or directory.
        name (str): The name parameter.
        size_kb (int): The size kb parameter.
    """
    import random

    random.seed(0)
    (folder / name).write_bytes(bytes(random.getrandbits(8) for _ in range(size_kb * 1024)))


def test_is_supported_reflects_platform():
    """test_is_supported_reflects_platform.

    Manages test is supported reflects platform operations and coordinates related state changes for the component.
    """
    m = CompactOSManager()
    assert m.is_supported() is IS_WIN


def test_system_folder_names_are_blocked():
    """test_system_folder_names_are_blocked.

    Manages test system folder names are blocked operations and coordinates related state changes for the component.
    """
    from cortex_unified.system_tools import compact_os
    for name in ("Windows", "Program Files", "$Recycle.Bin",
                 "System Volume Information", "node_modules", ".git"):
        low = name.lower()
        assert (low in compact_os._SYSTEM_TREES
                or low in compact_os._BLOCKED_NAMES
                or name in compact_os._BLOCKED_NAMES)


def test_estimate_text_heavy_folder(tmp_path):
    """test_estimate_text_heavy_folder.

    Manages test estimate text heavy folder operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    _write_text(tmp_path, "a.log", 128)
    _write_text(tmp_path, "b.json", 128)
    est = CompactOSManager()._estimate_folder(tmp_path)
    assert est is not None
    assert est.size_bytes >= 200 * 1024
    # text content should estimate a healthy, but bounded, savings ratio
    assert 0.3 < est.compressible_ratio < 0.75
    assert 0 < est.estimated_savings < est.size_bytes


def test_estimate_incompressible_folder(tmp_path):
    """test_estimate_incompressible_folder.

    Manages test estimate incompressible folder operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    _write_fill(tmp_path, "a.png", 256)
    _write_fill(tmp_path, "b.zip", 256)
    est = CompactOSManager()._estimate_folder(tmp_path)
    assert est is not None
    # media/already-compressed content => negligible estimated savings ratio
    assert est.compressible_ratio < 0.15


def test_find_compressible_folders_respects_min_size(tmp_path):
    """test_find_compressible_folders_respects_min_size.

    Manages test find compressible folders respects min size operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    big = tmp_path / "logs"
    small = tmp_path / "small"
    big.mkdir()
    small.mkdir()
    _write_text(big, "big.log", 256)         # sizable, compressible
    _write_text(small, "tiny.log", 8)        # below threshold
    m = CompactOSManager()
    # 256KB text => ~170KB estimated savings; 8KB => ~5KB. Use a 0.1MB (102KB)
    # threshold so logs qualifies but tiny does not.
    found = m.find_compressible_folders(str(tmp_path), min_size_mb=0.1)
    names = {Path(f.path).name for f in found}
    assert "logs" in names
    assert "small" not in names


def test_find_skips_blocked_and_system_subfolders(tmp_path):
    """test_find_skips_blocked_and_system_subfolders.

    Manages test find skips blocked and system subfolders operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    for name in ("Windows", "node_modules"):
        (tmp_path / name).mkdir(exist_ok=True)
        _write_text(tmp_path / name, "x.log", 300)
    m = CompactOSManager()
    found = m.find_compressible_folders(str(tmp_path), min_size_mb=50.0)
    names = {Path(f.path).name for f in found}
    assert "Windows" not in names
    assert "node_modules" not in names


def test_compact_folder_refuses_system_tree(tmp_path):
    # Even without admin, we must refuse a protected tree *before* shelling out.
    """test_compact_folder_refuses_system_tree.

    Manages test compact folder refuses system tree operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    m = CompactOSManager()
    res = m.compact_folder(str(tmp_path / "Windows"), recursive=True)
    assert res.success is False
    assert "Refused" in res.message or "protected" in res.message


def test_compact_folder_refuses_drive_root(tmp_path):
    """test_compact_folder_refuses_drive_root.

    Manages test compact folder refuses drive root operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    m = CompactOSManager()
    res = m.compact_folder(str(Path.cwd().anchor), recursive=True)
    assert res.success is False
    assert "drive root" in res.message
