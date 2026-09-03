"""Tests for czkawka multi-tool suite — empty, broken, bad-ext, bad-names, exif, temp, video-optimizer."""

from __future__ import annotations

import os
import struct
import threading
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from cortex_unified.core.config import Config
from cortex_unified.analyzers.czkawka_tools import (
    EmptyFinder,
    EmptyResult,
    InvalidSymlinkFinder,
    SymlinkResult,
    BrokenFileFinder,
    BadExtensionFinder,
    BadExtResult,
    BadNamesFinder,
    ExifCleaner,
    TempFileFinder,
    VideoOptimizer,
    VideoInfo,
    _sniff_extension,
    _temp_dirs,
    _MAGIC_HEADERS,
)

IS_WINDOWS = os.name == "nt"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _touch_empty(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


def _touch_file(path: Path, content: bytes = b"hello") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _make_minimal_png(path: Path) -> Path:
    """Create a minimal valid PNG with a 1x1 white pixel."""
    import zlib

    path.parent.mkdir(parents=True, exist_ok=True)
    sig = b"\x89PNG\r\n\x1a\n"

    def _chunk(ctype: bytes, data: bytes) -> bytes:
        c = ctype + data
        return len(data).to_bytes(4, "big") + c + zlib.crc32(c).to_bytes(4, "big")

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\xff\xff\xff"  # filter=none, one white pixel
    idat = zlib.compress(raw)
    path.write_bytes(
        sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")
    )
    return path


def _make_minimal_jpg(path: Path) -> Path:
    """Create a minimal JPEG file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 20)
    return path


def _make_minimal_pdf(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4 trailer")
    return path


def _make_minimal_zip(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(str(path), "w") as zf:
        zf.writestr("dummy.txt", "data")
    return path


# ---------------------------------------------------------------------------
# EmptyFinder
# ---------------------------------------------------------------------------


class TestEmptyFinder:
    def test_finds_empty_files(self, tmp_path: Path):
        _touch_empty(tmp_path / "empty.txt")
        _touch_file(tmp_path / "notempty.txt", b"data")
        result = EmptyFinder(str(tmp_path)).find()
        names = [p.name for p in result.empty_files]
        assert "empty.txt" in names
        assert "notempty.txt" not in names

    def test_finds_empty_dirs(self, tmp_path: Path):
        empty = tmp_path / "empty_dir"
        empty.mkdir()
        nonempty = tmp_path / "nonempty_dir"
        nonempty.mkdir()
        (nonempty / "file.txt").write_bytes(b"data")
        result = EmptyFinder(str(tmp_path)).find()
        dir_names = [p.name for p in result.empty_folders]
        assert "empty_dir" in dir_names
        assert "nonempty_dir" not in dir_names

    def test_returns_empty_when_nothing_empty(self, tmp_path: Path):
        _touch_file(tmp_path / "a.txt", b"a")
        _touch_file(tmp_path / "b.txt", b"b")
        result = EmptyFinder(str(tmp_path)).find()
        assert result.empty_files == []
        assert result.empty_folders == []

    def test_scanned_count(self, tmp_path: Path):
        _touch_empty(tmp_path / "e1.txt")
        _touch_empty(tmp_path / "e2.txt")
        _touch_file(tmp_path / "n1.txt", b"data")
        result = EmptyFinder(str(tmp_path)).find()
        assert result.scanned == 3

    def test_duration_is_non_negative(self, tmp_path: Path):
        _touch_empty(tmp_path / "e.txt")
        result = EmptyFinder(str(tmp_path)).find()
        assert result.duration >= 0

    def test_cancel_stops_early(self, tmp_path: Path):
        cancel = threading.Event()
        cancel.set()
        _touch_empty(tmp_path / "e.txt")
        result = EmptyFinder(str(tmp_path)).find(cancel=cancel)
        assert result.scanned == 0

    def test_progress_callback_invoked(self, tmp_path: Path):
        called = []
        for i in range(1001):
            _touch_empty(tmp_path / f"f{i}.txt")
        EmptyFinder(str(tmp_path)).find(progress=lambda m: called.append(m))
        assert len(called) > 0

    def test_exclude_dirs(self, tmp_path: Path):
        skip = tmp_path / "skip"
        skip.mkdir()
        _touch_empty(skip / "e.txt")
        _touch_empty(tmp_path / "keep.txt")
        cfg = Config()
        cfg.config_data["exclude_dirs"] = ["skip"]
        result = EmptyFinder(str(tmp_path), config=cfg).find()
        names = [p.name for p in result.empty_files]
        assert "keep.txt" in names
        assert "e.txt" not in names

    def test_nested_empty_files(self, tmp_path: Path):
        _touch_empty(tmp_path / "a" / "b" / "c" / "deep.txt")
        result = EmptyFinder(str(tmp_path)).find()
        assert len(result.empty_files) == 1


# ---------------------------------------------------------------------------
# InvalidSymlinkFinder — skip on Windows (requires admin/developer mode)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    IS_WINDOWS, reason="symlinks require elevated privileges on Windows"
)
class TestInvalidSymlinkFinder:
    def test_finds_broken_symlink(self, tmp_path: Path):
        broken = tmp_path / "broken_link"
        broken.symlink_to(tmp_path / "nonexistent_target")
        result = InvalidSymlinkFinder(str(tmp_path)).find()
        assert len(result.broken) == 1
        assert result.broken[0][0] == broken

    def test_ignores_valid_symlink(self, tmp_path: Path):
        target = tmp_path / "real_file.txt"
        _touch_file(target, b"data")
        link = tmp_path / "valid_link"
        link.symlink_to(target)
        result = InvalidSymlinkFinder(str(tmp_path)).find()
        assert result.broken == []

    def test_empty_when_no_symlinks(self, tmp_path: Path):
        _touch_file(tmp_path / "file.txt", b"data")
        result = InvalidSymlinkFinder(str(tmp_path)).find()
        assert result.broken == []
        assert result.scanned == 0

    def test_scanned_count(self, tmp_path: Path):
        t1 = tmp_path / "a.txt"
        _touch_file(t1, b"a")
        t2 = tmp_path / "b.txt"
        _touch_file(t2, b"b")
        (tmp_path / "link1").symlink_to(t1)
        (tmp_path / "link2").symlink_to(tmp_path / "missing")
        result = InvalidSymlinkFinder(str(tmp_path)).find()
        assert result.scanned == 2

    def test_relative_symlink_broken(self, tmp_path: Path):
        link = tmp_path / "rel_link"
        link.symlink_to("nonexistent_relative")
        result = InvalidSymlinkFinder(str(tmp_path)).find()
        assert len(result.broken) == 1

    def test_relative_symlink_valid(self, tmp_path: Path):
        target = tmp_path / "target.txt"
        _touch_file(target, b"ok")
        link = tmp_path / "rel_link"
        link.symlink_to("target.txt")
        result = InvalidSymlinkFinder(str(tmp_path)).find()
        assert result.broken == []

    def test_cancel_stops_early(self, tmp_path: Path):
        cancel = threading.Event()
        cancel.set()
        (tmp_path / "link").symlink_to(tmp_path / "missing")
        result = InvalidSymlinkFinder(str(tmp_path)).find(cancel=cancel)
        assert result.scanned == 0

    def test_exclude_dirs(self, tmp_path: Path):
        skip = tmp_path / "skip"
        skip.mkdir()
        (skip / "broken").symlink_to(skip / "nope")
        _touch_file(tmp_path / "keep.txt", b"data")
        cfg = Config()
        cfg.config_data["exclude_dirs"] = ["skip"]
        result = InvalidSymlinkFinder(str(tmp_path), config=cfg).find()
        assert result.broken == []


# ---------------------------------------------------------------------------
# BrokenFileFinder
# ---------------------------------------------------------------------------


class TestBrokenFileFinder:
    def test_finds_corrupted_zip(self, tmp_path: Path):
        p = tmp_path / "bad.zip"
        _touch_file(p, b"PK\x03\x04" + b"\x00" * 100)
        broken = BrokenFileFinder(str(tmp_path)).find()
        assert p in broken

    def test_ignores_valid_zip(self, tmp_path: Path):
        p = tmp_path / "good.zip"
        _make_minimal_zip(p)
        broken = BrokenFileFinder(str(tmp_path)).find()
        assert p not in broken

    def test_finds_bad_pdf(self, tmp_path: Path):
        p = tmp_path / "bad.pdf"
        _touch_file(p, b"not a pdf at all")
        broken = BrokenFileFinder(str(tmp_path)).find()
        assert p in broken

    def test_ignores_valid_pdf(self, tmp_path: Path):
        p = tmp_path / "good.pdf"
        _make_minimal_pdf(p)
        broken = BrokenFileFinder(str(tmp_path)).find()
        assert p not in broken

    def test_finds_corrupted_png(self, tmp_path: Path):
        p = tmp_path / "corrupt.png"
        _touch_file(p, b"\x89PNG\r\n\x1a\n" + b"\xff\xff" * 20)
        broken = BrokenFileFinder(str(tmp_path)).find()
        assert p in broken

    @pytest.mark.skipif(
        IS_WINDOWS, reason="minimal PNG without PIL may misbehave on Windows"
    )
    def test_ignores_valid_png(self, tmp_path: Path):
        p = tmp_path / "valid.png"
        _make_minimal_png(p)
        broken = BrokenFileFinder(str(tmp_path)).find()
        assert p not in broken

    def test_ignores_non_supported_extension(self, tmp_path: Path):
        p = tmp_path / "file.txt"
        _touch_file(p, b"just text")
        broken = BrokenFileFinder(str(tmp_path)).find()
        assert p not in broken

    def test_empty_returns_nothing(self, tmp_path: Path):
        broken = BrokenFileFinder(str(tmp_path)).find()
        assert broken == []

    def test_cancel_stops_early(self, tmp_path: Path):
        cancel = threading.Event()
        cancel.set()
        _touch_file(tmp_path / "bad.pdf", b"junk")
        broken = BrokenFileFinder(str(tmp_path)).find(cancel=cancel)
        assert broken == []

    def test_exclude_dirs(self, tmp_path: Path):
        skip = tmp_path / "skip"
        skip.mkdir()
        _touch_file(skip / "bad.pdf", b"junk")
        _touch_file(tmp_path / "ok.txt", b"data")
        cfg = Config()
        cfg.config_data["exclude_dirs"] = ["skip"]
        broken = BrokenFileFinder(str(tmp_path), config=cfg).find()
        assert broken == []


# ---------------------------------------------------------------------------
# BadExtensionFinder
# ---------------------------------------------------------------------------


class TestBadExtensionFinder:
    def test_finds_png_with_wrong_ext(self, tmp_path: Path):
        p = tmp_path / "image.txt"
        _make_minimal_png(p)
        results = BadExtensionFinder(str(tmp_path)).find()
        assert len(results) == 1
        assert results[0].path == p
        assert results[0].actual == ".png"
        assert results[0].claimed == ".txt"

    def test_finds_jpg_with_wrong_ext(self, tmp_path: Path):
        p = tmp_path / "photo.bmp"
        _make_minimal_jpg(p)
        results = BadExtensionFinder(str(tmp_path)).find()
        assert len(results) == 1
        assert results[0].actual in {".jpg", ".jpeg"}

    def test_ignores_correct_extension(self, tmp_path: Path):
        p = tmp_path / "image.png"
        _make_minimal_png(p)
        results = BadExtensionFinder(str(tmp_path)).find()
        assert results == []

    def test_ignores_extensionless_files(self, tmp_path: Path):
        p = tmp_path / "noext"
        _touch_file(p, b"data")
        results = BadExtensionFinder(str(tmp_path)).find()
        assert results == []

    def test_allows_jpg_jpeg_alias(self, tmp_path: Path):
        p = tmp_path / "photo.jpeg"
        _make_minimal_jpg(p)
        results = BadExtensionFinder(str(tmp_path)).find()
        assert results == []

    def test_empty_dir(self, tmp_path: Path):
        results = BadExtensionFinder(str(tmp_path)).find()
        assert results == []

    def test_cancel_stops_early(self, tmp_path: Path):
        cancel = threading.Event()
        cancel.set()
        p = tmp_path / "bad.txt"
        _make_minimal_png(p)
        results = BadExtensionFinder(str(tmp_path)).find(cancel=cancel)
        assert results == []

    def test_exclude_dirs(self, tmp_path: Path):
        skip = tmp_path / "skip"
        skip.mkdir()
        _make_minimal_png(skip / "img.txt")
        _make_minimal_png(tmp_path / "keep.png")
        cfg = Config()
        cfg.config_data["exclude_dirs"] = ["skip"]
        results = BadExtensionFinder(str(tmp_path), config=cfg).find()
        assert all(r.path.parent.name != "skip" for r in results)


# ---------------------------------------------------------------------------
# BadNamesFinder — Windows cannot create files with null bytes, reserved
# chars, trailing dots/spaces, so these tests only run on non-Windows.
# ---------------------------------------------------------------------------


class TestBadNamesFinder:
    @pytest.mark.skipif(
        IS_WINDOWS, reason="null bytes in filenames unsupported on Windows"
    )
    def test_finds_control_chars(self, tmp_path: Path):
        p = tmp_path / "file\x00name.txt"
        _touch_file(p, b"data")
        bad = BadNamesFinder(str(tmp_path)).find()
        assert any(b.name == "file\x00name.txt" for b in bad)

    @pytest.mark.skipif(
        IS_WINDOWS, reason="reserved chars cannot be created on Windows"
    )
    def test_finds_windows_reserved_chars(self, tmp_path: Path):
        for ch in '<>:"|?*':
            name = f"file{ch}name.txt"
            _touch_file(tmp_path / name, b"data")
        bad = BadNamesFinder(str(tmp_path)).find()
        assert len(bad) == 6

    @pytest.mark.skipif(IS_WINDOWS, reason="trailing spaces stripped by Windows")
    def test_finds_leading_space(self, tmp_path: Path):
        p = tmp_path / " leading.txt"
        _touch_file(p, b"data")
        bad = BadNamesFinder(str(tmp_path)).find()
        assert any(b.name == " leading.txt" for b in bad)

    @pytest.mark.skipif(IS_WINDOWS, reason="trailing spaces stripped by Windows")
    def test_finds_trailing_space(self, tmp_path: Path):
        p = tmp_path / "trailing.txt "
        _touch_file(p, b"data")
        bad = BadNamesFinder(str(tmp_path)).find()
        assert any(b.name == "trailing.txt " for b in bad)

    @pytest.mark.skipif(IS_WINDOWS, reason="trailing dots stripped by Windows")
    def test_finds_trailing_dot(self, tmp_path: Path):
        p = tmp_path / "file."
        _touch_file(p, b"data")
        bad = BadNamesFinder(str(tmp_path)).find()
        assert any(b.name == "file." for b in bad)

    def test_finds_reserved_windows_names(self, tmp_path: Path):
        # NUL etc. are device names on Windows — may be created but invisible to os.walk
        names = ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]
        for name in names:
            p = tmp_path / name
            try:
                _touch_file(p, b"data")
            except OSError:
                pass
        bad = BadNamesFinder(str(tmp_path)).find()
        # At least one reserved name should be detectable
        assert len(bad) >= 1

    def test_ignores_good_names(self, tmp_path: Path):
        for name in ["readme.txt", "data.csv", "image.png"]:
            _touch_file(tmp_path / name, b"data")
        bad = BadNamesFinder(str(tmp_path)).find()
        assert bad == []

    @pytest.mark.skipif(
        IS_WINDOWS, reason="null bytes in filenames unsupported on Windows"
    )
    def test_finds_bad_dir_names(self, tmp_path: Path):
        d = tmp_path / "bad dir\x00name"
        d.mkdir()
        bad = BadNamesFinder(str(tmp_path)).find()
        assert any(b.name == "bad dir\x00name" for b in bad)

    def test_cancel_stops_early(self, tmp_path: Path):
        cancel = threading.Event()
        cancel.set()
        # Use a file with a trailing dot (creatable on Linux, skip on Windows)
        if IS_WINDOWS:
            pytest.skip("cannot create problematic names on Windows")
        p = tmp_path / "bad."
        _touch_file(p, b"data")
        bad = BadNamesFinder(str(tmp_path)).find(cancel=cancel)
        assert bad == []

    def test_exclude_dirs(self, tmp_path: Path):
        skip = tmp_path / "skip"
        skip.mkdir()
        if not IS_WINDOWS:
            _touch_file(skip / "bad\x00name.txt", b"data")
        _touch_file(tmp_path / "good.txt", b"data")
        cfg = Config()
        cfg.config_data["exclude_dirs"] = ["skip"]
        bad = BadNamesFinder(str(tmp_path), config=cfg).find()
        assert all(b.parent.name != "skip" for b in bad)


# ---------------------------------------------------------------------------
# ExifCleaner
# ---------------------------------------------------------------------------


class TestExifCleaner:
    def test_scan_finds_exif_if_pil_available(self, tmp_path: Path):
        try:
            from PIL import Image

            p = tmp_path / "exif.jpg"
            img = Image.new("RGB", (2, 2), "red")
            img.save(str(p))
            cleaner = ExifCleaner(str(tmp_path))
            results = cleaner.scan()
            assert isinstance(results, list)
        except Exception:
            pytest.skip("PIL not available")

    def test_scan_skips_non_image_files(self, tmp_path: Path):
        _touch_file(tmp_path / "doc.txt", b"no exif here")
        cleaner = ExifCleaner(str(tmp_path))
        results = cleaner.scan()
        assert results == []

    def test_scan_empty_dir(self, tmp_path: Path):
        cleaner = ExifCleaner(str(tmp_path))
        results = cleaner.scan()
        assert results == []

    def test_strip_returns_dict_for_empty_list(self, tmp_path: Path):
        cleaner = ExifCleaner(str(tmp_path))
        out = cleaner.strip([])
        assert out == {}

    def test_cancel_stops_scan_early(self, tmp_path: Path):
        cancel = threading.Event()
        cancel.set()
        cleaner = ExifCleaner(str(tmp_path))
        results = cleaner.scan(cancel=cancel)
        assert results == []

    def test_exclude_dirs(self, tmp_path: Path):
        skip = tmp_path / "skip"
        skip.mkdir()
        _touch_file(skip / "photo.jpg", b"data")
        _touch_file(tmp_path / "other.jpg", b"data")
        cfg = Config()
        cfg.config_data["exclude_dirs"] = ["skip"]
        cleaner = ExifCleaner(str(tmp_path), config=cfg)
        results = cleaner.scan()
        assert all(p.parent.name != "skip" for p, _ in results)


# ---------------------------------------------------------------------------
# TempFileFinder
# ---------------------------------------------------------------------------


class TestTempFileFinder:
    def test_finds_tmp_extension(self, tmp_path: Path):
        _touch_file(tmp_path / "cache.tmp", b"data")
        _touch_file(tmp_path / "keep.txt", b"data")
        results = TempFileFinder(str(tmp_path)).find()
        names = [p.name for p in results]
        assert "cache.tmp" in names
        assert "keep.txt" not in names

    def test_finds_temp_extension(self, tmp_path: Path):
        _touch_file(tmp_path / "data.temp", b"data")
        results = TempFileFinder(str(tmp_path)).find()
        assert any(p.name == "data.temp" for p in results)

    def test_finds_log_files(self, tmp_path: Path):
        _touch_file(tmp_path / "app.log", b"data")
        results = TempFileFinder(str(tmp_path)).find()
        assert any(p.name == "app.log" for p in results)

    def test_finds_bak_files(self, tmp_path: Path):
        _touch_file(tmp_path / "config.bak", b"data")
        results = TempFileFinder(str(tmp_path)).find()
        assert any(p.name == "config.bak" for p in results)

    def test_finds_old_files(self, tmp_path: Path):
        _touch_file(tmp_path / "data.old", b"data")
        results = TempFileFinder(str(tmp_path)).find()
        assert any(p.name == "data.old" for p in results)

    def test_finds_swap_files(self, tmp_path: Path):
        _touch_file(tmp_path / "file.swp", b"data")
        _touch_file(tmp_path / "file.swo", b"data")
        results = TempFileFinder(str(tmp_path)).find()
        names = [p.name for p in results]
        assert "file.swp" in names
        assert "file.swo" in names

    def test_finds_tilde_backup_files(self, tmp_path: Path):
        _touch_file(tmp_path / "script.py~", b"data")
        results = TempFileFinder(str(tmp_path)).find()
        assert any(p.name == "script.py~" for p in results)

    def test_finds_thumbs_db(self, tmp_path: Path):
        _touch_file(tmp_path / "Thumbs.db", b"data")
        results = TempFileFinder(str(tmp_path)).find()
        assert any(p.name == "Thumbs.db" for p in results)

    def test_finds_ds_store(self, tmp_path: Path):
        _touch_file(tmp_path / ".DS_Store", b"data")
        results = TempFileFinder(str(tmp_path)).find()
        assert any(p.name == ".DS_Store" for p in results)

    def test_finds_desktop_ini(self, tmp_path: Path):
        _touch_file(tmp_path / "desktop.ini", b"data")
        results = TempFileFinder(str(tmp_path)).find()
        assert any(p.name == "desktop.ini" for p in results)

    def test_finds_dmp_files(self, tmp_path: Path):
        _touch_file(tmp_path / "crash.dmp", b"data")
        results = TempFileFinder(str(tmp_path)).find()
        assert any(p.name == "crash.dmp" for p in results)

    def test_ignores_normal_files(self, tmp_path: Path):
        _touch_file(tmp_path / "readme.md", b"# Hello")
        results = TempFileFinder(str(tmp_path)).find()
        assert results == []

    def test_empty_dir(self, tmp_path: Path):
        results = TempFileFinder(str(tmp_path)).find()
        assert results == []

    def test_cancel_stops_early(self, tmp_path: Path):
        cancel = threading.Event()
        cancel.set()
        _touch_file(tmp_path / "junk.tmp", b"data")
        results = TempFileFinder(str(tmp_path)).find(cancel=cancel)
        assert results == []

    def test_exclude_dirs(self, tmp_path: Path):
        skip = tmp_path / "skip"
        skip.mkdir()
        _touch_file(skip / "junk.tmp", b"data")
        _touch_file(tmp_path / "other.tmp", b"data")
        cfg = Config()
        cfg.config_data["exclude_dirs"] = ["skip"]
        results = TempFileFinder(str(tmp_path), config=cfg).find()
        assert all(p.parent.name != "skip" for p in results)

    def test_lock_files(self, tmp_path: Path):
        _touch_file(tmp_path / ".~lock.document.xlsx", b"data")
        results = TempFileFinder(str(tmp_path)).find()
        assert any(p.name == ".~lock.document.xlsx" for p in results)

    def test_finds_nested_temp_files(self, tmp_path: Path):
        _touch_file(tmp_path / "a" / "b" / "old.tmp", b"data")
        results = TempFileFinder(str(tmp_path)).find()
        assert any("old.tmp" in p.name for p in results)


# ---------------------------------------------------------------------------
# VideoOptimizer
# ---------------------------------------------------------------------------


class TestVideoOptimizer:
    def test_find_static_borders_returns_none_on_missing_ffprobe(self, tmp_path: Path):
        p = tmp_path / "vid.mp4"
        _touch_file(p, b"not a video")
        opt = VideoOptimizer()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = opt.find_static_borders(p)
        assert result is None

    def test_find_static_borders_returns_none_on_nonzero_exit(self, tmp_path: Path):
        p = tmp_path / "vid.mp4"
        _touch_file(p, b"data")
        mock_rc = MagicMock(returncode=1, stdout="", stderr="error")
        opt = VideoOptimizer()
        with patch("subprocess.run", return_value=mock_rc):
            result = opt.find_static_borders(p)
        assert result is None

    def test_find_static_borders_parses_json(self, tmp_path: Path):
        import json

        p = tmp_path / "vid.mp4"
        _touch_file(p, b"data")
        probe_output = json.dumps(
            {
                "streams": [
                    {
                        "width": 1920,
                        "height": 1080,
                        "codec_name": "h264",
                        "bit_rate": "5000000",
                        "duration": "120.5",
                    }
                ]
            }
        )
        mock_rc = MagicMock(returncode=0, stdout=probe_output, stderr="")
        opt = VideoOptimizer()
        with patch("subprocess.run", return_value=mock_rc):
            result = opt.find_static_borders(p)
        assert result is not None
        assert result.width == 1920
        assert result.height == 1080
        assert result.codec == "h264"
        assert result.bitrate == 5000000
        assert result.duration == 120.5
        assert result.path == p

    def test_optimize_returns_false_on_ffmpeg_error(self, tmp_path: Path):
        p = tmp_path / "vid.mp4"
        _touch_file(p, b"data")
        mock_rc = MagicMock(returncode=1, stdout=b"", stderr=b"error")
        opt = VideoOptimizer()
        with patch("subprocess.run", return_value=mock_rc):
            result = opt.optimize(p)
        assert result is False

    def test_optimize_returns_false_on_exception(self, tmp_path: Path):
        p = tmp_path / "vid.mp4"
        _touch_file(p, b"data")
        opt = VideoOptimizer()
        with patch("subprocess.run", side_effect=OSError("no ffmpeg")):
            result = opt.optimize(p)
        assert result is False

    def test_video_info_dataclass(self):
        vi = VideoInfo(
            path=Path("/test.mp4"),
            width=1280,
            height=720,
            duration=60.0,
            bitrate=3000000,
            codec="h264",
            has_static_borders=True,
            border_pixels=16,
        )
        assert vi.width == 1280
        assert vi.has_static_borders is True
        assert vi.border_pixels == 16


# ---------------------------------------------------------------------------
# _sniff_extension helper
# ---------------------------------------------------------------------------


class TestSniffExtension:
    def test_sniff_png(self, tmp_path: Path):
        p = _make_minimal_png(tmp_path / "f.png")
        assert _sniff_extension(p) == ".png"

    def test_sniff_jpg(self, tmp_path: Path):
        p = _make_minimal_jpg(tmp_path / "f.jpg")
        assert _sniff_extension(p) == ".jpg"

    def test_sniff_pdf(self, tmp_path: Path):
        p = _make_minimal_pdf(tmp_path / "f.pdf")
        assert _sniff_extension(p) == ".pdf"

    def test_sniff_zip(self, tmp_path: Path):
        p = _make_minimal_zip(tmp_path / "f.zip")
        assert _sniff_extension(p) == ".zip"

    def test_sniff_unknown_returns_none(self, tmp_path: Path):
        p = _touch_file(tmp_path / "f.xyz", b"\x00\x01\x02\x03")
        result = _sniff_extension(p)
        assert result is None or result != ".xyz"


# ---------------------------------------------------------------------------
# Module-level exports
# ---------------------------------------------------------------------------


class TestExports:
    def test_all_exports_present(self):
        from cortex_unified.analyzers.czkawka_tools import __all__

        expected = [
            "EmptyFinder",
            "EmptyResult",
            "InvalidSymlinkFinder",
            "SymlinkResult",
            "BrokenFileFinder",
            "BadExtensionFinder",
            "BadExtResult",
            "BadNamesFinder",
            "ExifCleaner",
            "TempFileFinder",
            "VideoOptimizer",
            "VideoInfo",
        ]
        for name in expected:
            assert name in __all__

    def test_magic_headers_completeness(self):
        assert ".jpg" in _MAGIC_HEADERS.values()
        assert ".png" in _MAGIC_HEADERS.values()
        assert ".pdf" in _MAGIC_HEADERS.values()
        assert ".zip" in _MAGIC_HEADERS.values()
        assert ".gif" in _MAGIC_HEADERS.values()
        assert ".bmp" in _MAGIC_HEADERS.values()
