"""Tests for video near-duplicate detection (keyframe pHash + temporal)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex_unified.analyzers.video_duplicate_finder import (
    VideoDuplicateFinder,
    compute_video_fingerprint,
    video_compare,
)


def _make_fake_video(path: Path, payload: bytes, size_kb: int = 128):
    # Create a raw byte payload that the fallback chunker will hash.
    # Repeat payload to reach size_kb
    """_make_fake_video.

    Manages make fake video operations and coordinates related state changes for the component.

    Args:
        path (Path): Filesystem path to the target file or directory.
        payload (bytes): The payload parameter.
        size_kb (int): The size kb parameter.
    """
    chunk = payload * max(1, (size_kb * 1024) // max(1, len(payload)))
    path.write_bytes(chunk[: size_kb * 1024])


# --- primitives ---

def test_fingerprint_is_list(tmp_path: Path):
    """test_fingerprint_is_list.

    Manages test fingerprint is list operations and coordinates related state changes for the component.

    Args:
        tmp_path (Path): Filesystem path to the target file or directory.
    """
    p = tmp_path / "a.mp4"
    _make_fake_video(p, b"framebytes" * 100)
    fp = compute_video_fingerprint(p)
    assert isinstance(fp, list)
    assert all(isinstance(v, int) for v in fp)


def test_identical_videos_compare_high(tmp_path: Path):
    """test_identical_videos_compare_high.

    Manages test identical videos compare high operations and coordinates related state changes for the component.

    Args:
        tmp_path (Path): Filesystem path to the target file or directory.
    """
    a = tmp_path / "a.mp4"
    b = tmp_path / "b.mp4"
    _make_fake_video(a, b"identical-video-content" * 50)
    _make_fake_video(b, b"identical-video-content" * 50)
    fa = compute_video_fingerprint(a)
    fb = compute_video_fingerprint(b)
    assert video_compare(fa, fb) > 0.6


def test_different_videos_compare_low(tmp_path: Path):
    """test_different_videos_compare_low.

    Manages test different videos compare low operations and coordinates related state changes for the component.

    Args:
        tmp_path (Path): Filesystem path to the target file or directory.
    """
    a = tmp_path / "a.mp4"
    b = tmp_path / "b.mp4"
    _make_fake_video(a, b"video-A-content" * 80)
    _make_fake_video(b, b"completely-different-B" * 80)
    # Identical baseline
    c = tmp_path / "c.mp4"
    _make_fake_video(c, b"video-A-content" * 80)
    fa = compute_video_fingerprint(a)
    fb = compute_video_fingerprint(b)
    fc = compute_video_fingerprint(c)
    assert video_compare(fa, fb) < video_compare(fa, fc)


def test_video_compare_empty():
    """test_video_compare_empty.

    Manages test video compare empty operations and coordinates related state changes for the component.
    """
    assert video_compare([], []) == 0.0
    assert video_compare([1, 2], []) == 0.0


def test_video_compare_identity():
    """test_video_compare_identity.

    Manages test video compare identity operations and coordinates related state changes for the component.
    """
    fp = [0x12345678, 0x9ABCDEF0, 0x11111111]
    assert video_compare(fp, fp) == 1.0


# --- finder ---

def test_finder_groups_identical_videos(tmp_path: Path):
    """test_finder_groups_identical_videos.

    Manages test finder groups identical videos operations and coordinates related state changes for the component.

    Args:
        tmp_path (Path): Filesystem path to the target file or directory.
    """
    _make_fake_video(tmp_path / "a.mp4", b"dup-video" * 60)
    _make_fake_video(tmp_path / "b.mp4", b"dup-video" * 60)
    _make_fake_video(tmp_path / "c.mp4", b"other-video-xyz" * 60)
    finder = VideoDuplicateFinder(str(tmp_path), threshold=0.5)
    groups = finder.find_video_duplicates()
    names = sorted(p.name for members in groups.values() for p in members)
    assert "a.mp4" in names and "b.mp4" in names
    for members in groups.values():
        mnames = {p.name for p in members}
        if "a.mp4" in mnames:
            assert "c.mp4" not in mnames


def test_finder_excludes_non_video(tmp_path: Path):
    """test_finder_excludes_non_video.

    Manages test finder excludes non video operations and coordinates related state changes for the component.

    Args:
        tmp_path (Path): Filesystem path to the target file or directory.
    """
    (tmp_path / "notes.txt").write_text("hello")
    _make_fake_video(tmp_path / "a.mp4", b"video")
    finder = VideoDuplicateFinder(str(tmp_path))
    assert finder.find_video_duplicates() == {}


def test_finder_respects_exclude_dirs(tmp_path: Path):
    """test_finder_respects_exclude_dirs.

    Manages test finder respects exclude dirs operations and coordinates related state changes for the component.

    Args:
        tmp_path (Path): Filesystem path to the target file or directory.
    """
    sub = tmp_path / "skip"
    sub.mkdir()
    _make_fake_video(sub / "a.mp4", b"dup" * 100)
    _make_fake_video(sub / "b.mp4", b"dup" * 100)
    _make_fake_video(tmp_path / "ta.mp4", b"dup" * 100)
    _make_fake_video(tmp_path / "tb.mp4", b"dup" * 100)
    from cortex_unified.core.config import Config
    cfg = Config()
    cfg.config_data["exclude_dirs"] = ["skip"]
    finder = VideoDuplicateFinder(str(tmp_path), config=cfg)
    groups = finder.find_video_duplicates()
    names = {p.name for members in groups.values() for p in members}
    assert not names.intersection({"a.mp4", "b.mp4"})
    assert "ta.mp4" in names and "tb.mp4" in names


def test_finder_stats(tmp_path: Path):
    """test_finder_stats.

    Manages test finder stats operations and coordinates related state changes for the component.

    Args:
        tmp_path (Path): Filesystem path to the target file or directory.
    """
    _make_fake_video(tmp_path / "a.mp4", b"stat-video" * 50)
    _make_fake_video(tmp_path / "b.mp4", b"stat-video" * 50)
    finder = VideoDuplicateFinder(str(tmp_path))
    finder.find_video_duplicates()
    stats = finder.get_stats()
    assert stats["total_videos_scanned"] == 2
    assert stats["video_duplicate_groups"] >= 1
