"""Tests for perceptual image duplicate detection (pHash/dHash/aHash)."""

from __future__ import annotations

from pathlib import Path

import pytest

pil = pytest.importorskip("PIL", reason="Pillow not installed")
from PIL import Image  # noqa: E402

from cortex_unified.analyzers.perceptual_duplicate_finder import (  # noqa: E402
    HASH_KINDS,
    PerceptualDuplicateFinder,
    average_hash,
    compute_hash,
    difference_hash,
    hamming_distance,
    perceptual_hash,
)


def _make_image(path: Path, size: int = 128):
    """_make_image.

    Manages make image operations and coordinates related state changes for the component.

    Args:
        path (Path): Filesystem path to the target file or directory.
        size (int): Integer number of bytes to format or process.
    """
    w = h = size
    px = [((x * 3) % 255, (y * 5) % 255, ((x + y) * 7) % 255)
          for y in range(h) for x in range(w)]
    img = Image.new("RGB", (w, h))
    img.putdata(px)
    img.save(path)


def _make_plain(path: Path, size: int = 128, color: str = "red"):
    """_make_plain.

    Manages make plain operations and coordinates related state changes for the component.

    Args:
        path (Path): Filesystem path to the target file or directory.
        size (int): Integer number of bytes to format or process.
        color (str): The color parameter.
    """
    Image.new("RGB", (size, size), color).save(path)


# --- hashing primitives ----------------------------------------------------

def test_hashes_are_int(tmp_path):
    """test_hashes_are_int.

    Manages test hashes are int operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    _make_image(tmp_path / "x.png")
    for kind in HASH_KINDS:
        val = compute_hash(tmp_path / "x.png", kind)
        assert isinstance(val, int)
        assert 0 <= val <= 0xFFFFFFFFFFFFFFFF

def test_hashes_deterministic_on_identical_image(tmp_path):
    """test_hashes_deterministic_on_identical_image.

    Manages test hashes deterministic on identical image operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    _make_image(a)
    _make_image(b)
    for kind in HASH_KINDS:
        assert compute_hash(a, kind) == compute_hash(b, kind)


def test_hamming_distance_basic():
    """test_hamming_distance_basic.

    Manages test hamming distance basic operations and coordinates related state changes for the component.
    """
    assert hamming_distance(0, 0) == 0
    assert hamming_distance(0, 0xFFFFFFFFFFFFFFFF) == 64
    assert hamming_distance(0b1010, 0b1000) == 1


def test_perceptual_hashes_agree_across_rescales(tmp_path):
    """test_perceptual_hashes_agree_across_rescales.

    Manages test perceptual hashes agree across rescales operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    big = tmp_path / "big.jpg"
    small = tmp_path / "small.jpg"
    _make_image(big, size=256)
    im = Image.open(big)
    im.resize((80, 80), Image.Resampling.LANCZOS).save(small)
    for kind in HASH_KINDS:
        assert hamming_distance(
            compute_hash(big, kind), compute_hash(small, kind)) <= 10


def test_different_images_are_far_apart_in_phash(tmp_path):
    # pHash drops the DC (brightness) term, so two plain solid colours are
    # *not* a good "different" case - they share near-zero AC structure. Use a
    # structured pattern vs a plain fill instead.
    """test_different_images_are_far_apart_in_phash.

    Manages test different images are far apart in phash operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    _make_image(tmp_path / "pattern.png", size=128)
    _make_plain(tmp_path / "plain.png", color="green")
    assert hamming_distance(
        perceptual_hash(tmp_path / "pattern.png"),
        perceptual_hash(tmp_path / "plain.png")) > 20


def test_unknown_kind_raises(tmp_path):
    """test_unknown_kind_raises.

    Manages test unknown kind raises operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    with pytest.raises(ValueError):
        compute_hash(Path(__file__), "nope")


# --- finder -----------------------------------------------------------------

def test_finder_groups_rescaled_identical_images(tmp_path):
    """test_finder_groups_rescaled_identical_images.

    Manages test finder groups rescaled identical images operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    _make_image(tmp_path / "a.jpg", size=256)
    Image.open(tmp_path / "a.jpg").resize((90, 90), Image.Resampling.LANCZOS) \
        .save(tmp_path / "b.jpg")
    _make_plain(tmp_path / "c.png", color="red")
    finder = PerceptualDuplicateFinder(str(tmp_path), max_distance=10)
    groups = finder.find_perceptual_duplicates()
    # Both rescaled copies must land in one group together; the plain red
    # image must not.
    names = sorted(p.name for paths in groups.values() for p in paths)
    assert "a.jpg" in names and "b.jpg" in names
    assert "c.png" not in names


def test_finder_excludes_non_images(tmp_path):
    """test_finder_excludes_non_images.

    Manages test finder excludes non images operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    (tmp_path / "notes.txt").write_text("hello")
    _make_image(tmp_path / "a.png")
    finder = PerceptualDuplicateFinder(str(tmp_path))
    # one image alone => no group of size >=2
    assert finder.find_perceptual_duplicates() == {}

def test_finder_respects_exclude_dirs(tmp_path):
    """test_finder_respects_exclude_dirs.

    Manages test finder respects exclude dirs operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    sub = tmp_path / "skip"
    sub.mkdir()
    _make_image(sub / "a.png")
    _make_image(sub / "b.png")
    top_a = tmp_path / "ta.png"
    top_b = tmp_path / "tb.png"
    _make_image(top_a)
    _make_image(top_b)
    from cortex_unified.core.config import Config
    cfg = Config()
    cfg.config_data["exclude_dirs"] = ["skip"]
    finder = PerceptualDuplicateFinder(str(tmp_path), config=cfg)
    groups = finder.find_perceptual_duplicates()
    names = {p.name for paths in groups.values() for p in paths}
    assert not names.intersection({"a.png", "b.png"})
    assert names.intersection({"ta.png", "tb.png"})


def test_finder_stats(tmp_path):
    """test_finder_stats.

    Manages test finder stats operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    _make_image(tmp_path / "a.jpg", size=128)
    Image.open(tmp_path / "a.jpg").resize((64, 64), Image.Resampling.LANCZOS) \
        .save(tmp_path / "b.jpg")
    finder = PerceptualDuplicateFinder(str(tmp_path))
    finder.find_perceptual_duplicates()
    stats = finder.get_stats()
    assert stats["total_images_scanned"] == 2
    assert stats["visual_duplicate_groups"] >= 1
    assert stats["kinds"] == ["phash"]


def test_finder_error_handling_skips_corrupt(tmp_path):
    """test_finder_error_handling_skips_corrupt.

    Manages test finder error handling skips corrupt operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    bad = tmp_path / "broken.jpg"
    bad.write_bytes(b"this is not a real jpeg" * 4)
    _make_image(tmp_path / "a.png")
    _make_image(tmp_path / "b.png")
    finder = PerceptualDuplicateFinder(str(tmp_path))
    finder.find_perceptual_duplicates()
    assert finder.error_count >= 1
