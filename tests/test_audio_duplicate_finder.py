"""Tests for Chromaprint-inspired audio duplicate detection."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

import pytest

from cortex_unified.analyzers.audio_duplicate_finder import (
    AudioDuplicateFinder,
    audio_compare,
    compute_audio_fingerprint,
)


def _make_wav(path: Path, freq: float = 440.0, duration: float = 1.0, sr: int = 11025):
    n = int(sr * duration)
    with wave.open(str(path, ), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = struct.pack(
            f"<{n}h",
            *[int(30000 * math.sin(2 * math.pi * freq * i / sr)) for i in range(n)],
        )
        wf.writeframes(frames)


def _make_noise_wav(path: Path, duration: float = 1.0, sr: int = 11025):
    import random
    rnd = random.Random(12345)
    n = int(sr * duration)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        vals = [rnd.randint(-30000, 30000) for _ in range(n)]
        wf.writeframes(struct.pack(f"<{n}h", *vals))


# --- fingerprint primitives ---

def test_fingerprint_is_list_of_ints(tmp_path: Path):
    p = tmp_path / "tone.wav"
    _make_wav(p)
    fp = compute_audio_fingerprint(p)
    assert isinstance(fp, list)
    assert all(isinstance(v, int) and 0 <= v <= 0xFFFFFFFF for v in fp)
    assert len(fp) > 0


def test_identical_wavs_compare_high(tmp_path: Path):
    a = tmp_path / "a.wav"
    b = tmp_path / "b.wav"
    _make_wav(a, freq=440)
    _make_wav(b, freq=440)
    fa = compute_audio_fingerprint(a)
    fb = compute_audio_fingerprint(b)
    assert audio_compare(fa, fb) > 0.85


def test_different_tones_compare_low(tmp_path: Path):
    a = tmp_path / "a.wav"
    b = tmp_path / "b.wav"
    _make_wav(a, freq=440)
    _make_wav(b, freq=880)
    fa = compute_audio_fingerprint(a)
    fb = compute_audio_fingerprint(b)
    # Different frequencies should be less similar than identical
    # Use identical comparison as baseline
    c = tmp_path / "c.wav"
    _make_wav(c, freq=440)
    fc = compute_audio_fingerprint(c)
    assert audio_compare(fa, fb) < audio_compare(fa, fc)


def test_audio_compare_empty():
    assert audio_compare([], []) == 0.0
    assert audio_compare([1], []) == 0.0


# --- finder ---

def test_finder_groups_identical_audio(tmp_path: Path):
    _make_wav(tmp_path / "a.wav", freq=440)
    _make_wav(tmp_path / "b.wav", freq=440)
    _make_wav(tmp_path / "c.wav", freq=880)
    # c is different tone; with high threshold should not group with a/b
    finder = AudioDuplicateFinder(str(tmp_path), threshold=0.75)
    groups = finder.find_audio_duplicates()
    # a and b must be together
    names = sorted(p.name for members in groups.values() for p in members)
    assert "a.wav" in names and "b.wav" in names
    # c should not be in same group as a (if grouped at all, it would be weak)
    for gid, members in groups.items():
        mnames = {p.name for p in members}
        if "a.wav" in mnames:
            assert "c.wav" not in mnames


def test_finder_excludes_non_audio(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("hello")
    _make_wav(tmp_path / "a.wav")
    finder = AudioDuplicateFinder(str(tmp_path))
    # one audio alone => no group
    assert finder.find_audio_duplicates() == {}


def test_finder_respects_exclude_dirs(tmp_path: Path):
    sub = tmp_path / "skip"
    sub.mkdir()
    _make_wav(sub / "a.wav", freq=440)
    _make_wav(sub / "b.wav", freq=440)
    _make_wav(tmp_path / "ta.wav", freq=440)
    _make_wav(tmp_path / "tb.wav", freq=440)
    from cortex_unified.core.config import Config
    cfg = Config()
    cfg.config_data["exclude_dirs"] = ["skip"]
    finder = AudioDuplicateFinder(str(tmp_path), config=cfg)
    groups = finder.find_audio_duplicates()
    names = {p.name for members in groups.values() for p in members}
    assert not names.intersection({"a.wav", "b.wav"})
    assert "ta.wav" in names and "tb.wav" in names


def test_finder_stats(tmp_path: Path):
    _make_wav(tmp_path / "a.wav", freq=440)
    _make_wav(tmp_path / "b.wav", freq=440)
    finder = AudioDuplicateFinder(str(tmp_path))
    finder.find_audio_duplicates()
    stats = finder.get_stats()
    assert stats["total_audio_scanned"] == 2
    assert stats["audio_duplicate_groups"] >= 1


def test_fallback_raw_fingerprint_for_mp3(tmp_path: Path):
    # Without decoders, MP3 fallback should still produce a fingerprint
    p = tmp_path / "fake.mp3"
    p.write_bytes(b"\x00\x01\x02" * 5000 + b"audio-like-bytes" * 1000)
    fp = compute_audio_fingerprint(p)
    assert isinstance(fp, list)
    assert len(fp) > 0
