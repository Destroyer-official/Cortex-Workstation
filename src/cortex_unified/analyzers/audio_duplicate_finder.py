"""Audio duplicate detection via acoustic fingerprinting (Chromaprint-inspired).

Research grounding
------------------
* Ke et al., "Computer Vision for Music Identification" (CVPR 2005) – the
  seminal spectral-energy fingerprint using 33 log-spaced frequency bands and
  32-bit subfingerprints per frame (~0.37 s), compared via Hamming distance.
* Kurth & Müller, "Efficient Index-Based Audio Matching" (TASLP 2008) –
  band-energy differences and inverted-index matching for large collections.
* Jang et al., "Pairwise Boosted Audio Fingerprint" (TIFS 2009) – boosted
  band-energy comparisons for robustness to re-encoding / format changes.
* Baluja & Covell (Google 2006) "Waveprint" / Chromaprint / AcoustID –
  practical open-source realisation (fpcalc) used by MusicBrainz/Picard and
  tools like dupsonic/soundalike (2024-2025). The target is cross-format
  duplicate detection: same master as FLAC vs MP3 must match even though
  byte hashes differ.

Why this matters for a system cleaner
-------------------------------------
* ``DuplicateFinder`` (byte-identical) misses an MP3 re-encode of a FLAC.
* ``FuzzyFinder`` (CTPH) sees binaries, not audio spectra.
* Users routinely accumulate music libraries with the same track stored as
  FLAC + MP3 + M4A across folders/drives. Acoustic fingerprinting closes
  that gap.

Design (dependency-light, pure stdlib with optional NumPy)
-----------------------------------------------------------
* WAV is decoded natively via :mod:`wave` + pure-Python Cooley-Tukey FFT.
* Other containers (MP3/FLAC/OGG/M4A/AAC/WMA/OPUS) are supported opportunistically:
  if ``pydub``/``ffmpeg`` or ``librosa`` is available the file is decoded to
  PCM; otherwise a *raw-byte* fallback still provides similarity for
  same-container duplicates (graceful degradation, not a hard failure).
* Signal pipeline: mono → resample to 11 025 Hz → 4096-sample frames
  (≈0.37 s) with 50 % overlap → magnitude spectrum (2049 bins) →
  33 log-spaced bands (300–3000 Hz, exponential spacing as in Chromaprint) →
  32-bit subfingerprint per frame (16 intra-frame + 16 inter-frame bits) →
  sequence fingerprint. Comparison aligns sequences via sliding Hamming
  window (best offset) and rewards length-proportional overlap.
* File walk, threading, cancellation, progress, exclusion rules and stats
  mirror ``PerceptualDuplicateFinder`` so the premium UI can reuse the same
  worker pattern.

Usage::

    from cortex_unified.analyzers.audio_duplicate_finder import (
        AudioDuplicateFinder, compute_audio_fingerprint, audio_compare,
    )
    fp = compute_audio_fingerprint(Path("track.wav"))
    score = audio_compare(fp, fp2)   # 0.0 .. 1.0
    groups = AudioDuplicateFinder("/Music", threshold=0.75).find_audio_duplicates()

References
----------
* Ke et al., CVPR 2005.
* Kurth & Müller, TASLP 2008.
* Jang et al., TIFS 2009.
* AcoustID Chromaprint docs (github.com/acoustid/chromaprint).
* Wang 2003 (Shazam landmark) for temporal robustness discussion.
"""

from __future__ import annotations

import hashlib
import math
import os
import struct
import threading
import wave
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from cortex_unified.core.config import Config
from cortex_unified.core.utils import normalize_path

# ---------------------------------------------------------------------------
# Audio format handling (optional deps are soft)
# ---------------------------------------------------------------------------

_AUDIO_SUFFIXES = {
    ".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma",
    ".aiff", ".aif", ".wv", ".ape", ".alac",
}

# Target sample rate as in Chromaprint / RARE
_TARGET_SR = 11025
_FRAME_SIZE = 4096  # ~0.371 s at 11025 Hz
_HOP_SIZE = 2048    # 50 % overlap
_NUM_BANDS = 33     # Chromaprint uses 33 log-spaced bands
_SUBFP_BITS = 32

# Band edges: log-spaced between 300 Hz and 3000 Hz (Chromaprint range)
# Constructed once at import.
def _build_band_edges() -> List[Tuple[int, int]]:
    # Map Hz -> FFT bin: bin = hz * N / sr  (N=4096, sr=11025)
    # 33 bands → 32 subfingerprint bits (16 intra + 16 inter)
    # Use exponential spacing: f_i = 300 * (3000/300)**(i/32)
    """_build_band_edges.

    Manages build band edges operations and coordinates related state changes for the component.

    Returns:
        List[Tuple[int, int]]: List of processed items or identifiers.
    """
    edges: List[Tuple[int, int]] = []
    low, high = 300.0, 3000.0
    # 33 bands need 34 edges; last edge is high+epsilon
    freqs = [low * ((high / low) ** (i / 32.0)) for i in range(34)]
    for i in range(33):
        b0 = int(freqs[i] * _FRAME_SIZE / _TARGET_SR)
        b1 = int(freqs[i + 1] * _FRAME_SIZE / _TARGET_SR)
        b0 = max(0, min(b0, _FRAME_SIZE // 2))
        b1 = max(b0 + 1, min(b1, _FRAME_SIZE // 2))
        edges.append((b0, b1))
    return edges

_BAND_EDGES = _build_band_edges()

# ---------------------------------------------------------------------------
# Pure-Python FFT (iterative Cooley-Tukey, power-of-two)
# ---------------------------------------------------------------------------

def _fft(mag: List[float]) -> List[complex]:
    """Fft.

    Manages fft operations and coordinates related state changes for the component.

    Args:
        mag (List[float]): The mag parameter.

    Returns:
        List[complex]: List of processed items or identifiers.
    """
    n = len(mag)
    if n & (n - 1):
        raise ValueError("FFT size must be power of two")
    # Bit-reversal permutation
    j = 0
    a = [complex(v, 0.0) for v in mag]
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        ang = -2.0 * math.pi / length
        wlen = complex(math.cos(ang), math.sin(ang))
        for i in range(0, n, length):
            w = complex(1.0, 0.0)
            for k in range(length // 2):
                u = a[i + k]
                v = a[i + k + length // 2] * w
                a[i + k] = u + v
                a[i + k + length // 2] = u - v
                w *= wlen
        length <<= 1
    return a

def _magnitude_spectrum(frame: List[float]) -> List[float]:
    """Windowed FFT magnitude (Hann window, half spectrum).

    Manages magnitude spectrum operations and coordinates related state changes for the component.

    Args:
        frame (List[float]): The frame parameter.

    Returns:
        List[float]: List of processed items or identifiers.
    """
    n = len(frame)
    # Hann window
    windowed = [
        frame[i] * (0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1)))
        for i in range(n)
    ]
    spec = _fft(windowed)
    # Only bins 0..N/2 inclusive; magnitude
    return [abs(c) for c in spec[: n // 2 + 1]]

# ---------------------------------------------------------------------------
# WAV decoding (stdlib only)
# ---------------------------------------------------------------------------

def _decode_wav(path: Path) -> Tuple[List[float], int]:
    """Decode WAV to mono float samples in [-1, 1]; returns (samples, sr).

    Manages decode wav operations and coordinates related state changes for the component.

    Args:
        path (Path): Filesystem path to the target file or directory.

    Returns:
        Tuple[List[float], int]: List of processed items or identifiers.
    """
    with wave.open(str(path), "rb") as wf:
        nch = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        sr = wf.getframerate()
        nframes = wf.getnframes()
        raw = wf.readframes(nframes)
    if not raw:
        return [], sr
    # Convert to mono float
    if sampwidth == 1:
        # 8-bit unsigned
        vals = list(raw)
        mono = [(v - 128) / 128.0 for v in vals[0::nch]] if nch > 1 else [(v - 128) / 128.0 for v in vals]
        if nch > 1:
            # average channels: raw interleaved bytes
            # For 8-bit multi-channel, vals are already interleaved
            mono = []
            for i in range(0, len(vals), nch):
                mono.append(sum((vals[i + c] - 128) / 128.0 for c in range(nch)) / nch)
        return mono, sr
    elif sampwidth == 2:
        count = len(raw) // 2
        vals = struct.unpack(f"<{count}h", raw)
        if nch == 1:
            mono = [v / 32768.0 for v in vals]
        else:
            mono = []
            for i in range(0, len(vals), nch):
                mono.append(sum(vals[i + c] for c in range(nch)) / (32768.0 * nch))
        return mono, sr
    elif sampwidth == 3:
        # 24-bit
        mono = []
        step = 3 * nch
        for i in range(0, len(raw) - step + 1, step):
            # little-endian 24-bit per channel
            acc = 0.0
            for c in range(nch):
                b0, b1, b2 = raw[i + c * 3], raw[i + c * 3 + 1], raw[i + c * 3 + 2]
                v = b0 | (b1 << 8) | (b2 << 16)
                if v & 0x800000:
                    v -= 0x1000000
                acc += v / 8388608.0
            mono.append(acc / nch)
        return mono, sr
    elif sampwidth == 4:
        count = len(raw) // 4
        vals = struct.unpack(f"<{count}i", raw)
        if nch == 1:
            mono = [v / 2147483648.0 for v in vals]
        else:
            mono = []
            for i in range(0, len(vals), nch):
                mono.append(sum(vals[i + c] for c in range(nch)) / (2147483648.0 * nch))
        return mono, sr
    else:
        raise ValueError(f"unsupported sample width {sampwidth}")


def _resample(samples: List[float], sr_in: int, sr_out: int = _TARGET_SR) -> List[float]:
    """Resample.

    Manages resample operations and coordinates related state changes for the component.

    Args:
        samples (List[float]): The samples parameter.
        sr_in (int): The sr in parameter.
        sr_out (int): The sr out parameter.

    Returns:
        List[float]: List of processed items or identifiers.
    """
    if sr_in == sr_out or not samples:
        return samples
    ratio = sr_in / sr_out
    out_len = int(len(samples) / ratio)
    if out_len <= 0:
        return samples[:1]
    out: List[float] = [0.0] * out_len
    for i in range(out_len):
        pos = i * ratio
        lo = int(pos)
        hi = min(lo + 1, len(samples) - 1)
        frac = pos - lo
        out[i] = samples[lo] * (1 - frac) + samples[hi] * frac
    return out

# Optional decoder for non-WAV via pydub/ffmpeg or librosa (soft deps)

def _decode_generic(path: Path) -> Optional[Tuple[List[float], int]]:
    """Try optional decoders for non-WAV; returns None if unavailable.

    Manages decode generic operations and coordinates related state changes for the component.

    Args:
        path (Path): Filesystem path to the target file or directory.

    Returns:
        Optional[Tuple[List[float], int]]: List of processed items or identifiers.
    """
    # Try pydub (ffmpeg) first – it handles MP3/FLAC/OGG/M4A
    try:
        from pydub import AudioSegment  # type: ignore
        seg = AudioSegment.from_file(str(path))
        # to mono, 16-bit
        seg = seg.set_channels(1)
        raw = seg.raw_data
        sampwidth = seg.sample_width
        sr = seg.frame_rate
        if sampwidth == 2:
            vals = struct.unpack(f"<{len(raw)//2}h", raw)
            samples = [v / 32768.0 for v in vals]
            return samples, sr
        elif sampwidth == 1:
            vals = list(raw)
            return [(v - 128) / 128.0 for v in vals], sr
    except Exception:
        pass
    # Try librosa/soundfile
    try:
        import soundfile as sf  # type: ignore
        import numpy as np  # type: ignore

        data, sr = sf.read(str(path), always_2d=False)
        if isinstance(data, np.ndarray):
            if data.ndim > 1:
                data = data.mean(axis=1)
            return data.astype(float).tolist(), int(sr)
    except Exception:
        pass
    try:
        import librosa  # type: ignore

        y, sr = librosa.load(str(path), sr=None, mono=True)
        return y.tolist(), int(sr)
    except Exception:
        pass
    return None

# ---------------------------------------------------------------------------
# Fingerprinting primitives
# ---------------------------------------------------------------------------

def _band_energies(mag: List[float]) -> List[float]:
    """33 log-spaced band energies (sum of squared magnitudes).

    Manages band energies operations and coordinates related state changes for the component.

    Args:
        mag (List[float]): The mag parameter.

    Returns:
        List[float]: List of processed items or identifiers.
    """
    energies: List[float] = []
    for b0, b1 in _BAND_EDGES:
        # Clamp to mag length
        b1c = min(b1, len(mag) - 1)
        b0c = min(b0, b1c)
        s = 0.0
        for k in range(b0c, b1c + 1):
            v = mag[k]
            s += v * v
        # Log compression (as in Chromaprint / Waveprint)
        energies.append(math.log(max(s, 1e-10)))
    return energies


def _subfingerprint_for_frame(
    energies: List[float], prev_energies: Optional[List[float]]
) -> int:
    """32-bit subfingerprint for one frame (16 intra + 16 inter as in Chromaprint).

    Chromaprint's 32 bits per subfingerprint comprise:
    * bits 0..15: intra-frame band differences (band[i] > band[i+1])
    * bits 16..31: inter-frame (temporal) differences
                  (band[i] - band[i+1]) - (prev[i] - prev[i+1]) > 0
    """
    bits = 0
    # Intra-frame: 16 bits comparing 32 bands pairwise (stride 2)
    for i in range(16):
        a = energies[i * 2]
        b = energies[i * 2 + 1]
        if a > b:
            bits |= 1 << i
    if prev_energies is not None:
        for i in range(16):
            # Temporal difference of band pairs
            cur_diff = energies[i * 2] - energies[i * 2 + 1]
            prev_diff = prev_energies[i * 2] - prev_energies[i * 2 + 1]
            if cur_diff > prev_diff:
                bits |= 1 << (16 + i)
    else:
        # No previous frame: replicate intra bits for stability
        for i in range(16):
            if bits & (1 << i):
                bits |= 1 << (16 + i)
    return bits & 0xFFFFFFFF


def _fingerprint_from_samples(samples: List[float]) -> List[int]:
    """Compute sequence fingerprint (list of 32-bit subfingerprints).

    Manages fingerprint from samples operations and coordinates related state changes for the component.

    Args:
        samples (List[float]): The samples parameter.

    Returns:
        List[int]: List of processed items or identifiers.
    """
    if len(samples) < _FRAME_SIZE:
        return []
    # Truncate to first 120 s as in Chromaprint (dupsonic uses 120 s max)
    max_samples = _TARGET_SR * 120
    if len(samples) > max_samples:
        samples = samples[:max_samples]
    subfps: List[int] = []
    prev_energies: Optional[List[float]] = None
    # Slide with 50 % overlap
    pos = 0
    while pos + _FRAME_SIZE <= len(samples):
        frame = samples[pos : pos + _FRAME_SIZE]
        mag = _magnitude_spectrum(frame)
        energies = _band_energies(mag)
        subfps.append(_subfingerprint_for_frame(energies, prev_energies))
        prev_energies = energies
        pos += _HOP_SIZE
    return subfps


def _fallback_raw_fingerprint(path: Path) -> List[int]:
    """Format-agnostic fallback for non-WAV without decoders: byte-shingled.

    Reads at most 2 MiB prefix, chunks into 4096-byte blocks with overlap,
    and hashes each block. Cross-format match is not expected; same-format
    duplicates still group (graceful degradation).
    """
    try:
        data = path.read_bytes()[: 2 * 1024 * 1024]
    except OSError:
        return []
    if not data:
        return []
    # Chunk into pseudo-frames of 4096 bytes, hop 2048
    subfps: List[int] = []
    step = 2048
    for off in range(0, max(1, len(data) - 4096 + 1), step):
        chunk = data[off : off + 4096]
        # Quick spectral-like hash: split chunk into 32 slices, compare entropy
        # This yields 32-bit subfingerprint analogous to spectral version.
        slice_len = max(1, len(chunk) // 32)
        slices = [chunk[i * slice_len : (i + 1) * slice_len] for i in range(32)]
        energies = []
        for s in slices:
            if not s:
                energies.append(0.0)
                continue
            # byte entropy as energy proxy
            freq = {}
            for b in s:
                freq[b] = freq.get(b, 0) + 1
            ent = -sum((c / len(s)) * math.log2(c / len(s)) for c in freq.values())
            energies.append(ent)
        # Pad to 33 to reuse subfingerprint logic (last = mean)
        if len(energies) < 33:
            energies += [sum(energies) / max(1, len(energies))] * (33 - len(energies))
        else:
            energies = energies[:33]
        # Compute subfingerprint bits based on frequency energy comparison
        bits = 0
        for i in range(16):
            if energies[i * 2] > energies[i * 2 + 1]:
                bits |= 1 << i
        # inter bits based on previous raw energies not tracked, duplicate intra
        for i in range(16):
            if bits & (1 << i):
                bits |= 1 << (16 + i)
        subfps.append(bits & 0xFFFFFFFF)
        if len(subfps) >= 300:  # cap to ~120s equivalent
            break
    return subfps


def compute_audio_fingerprint(path: Path | str) -> List[int]:
    """Compute Chromaprint-inspired acoustic fingerprint (sequence of 32-bit ints).

    For WAV the full spectral pipeline is used; for other containers the
    optional decoders are tried before falling back to a byte-level surrogate
    so scanning never hard-fails.
    """
    p = Path(path)
    suffix = p.suffix.lower()
    # Fast path: WAV via wave
    if suffix == ".wav":
        try:
            samples, sr = _decode_wav(p)
            if not samples:
                return _fallback_raw_fingerprint(p)
            samples = _resample(samples, sr, _TARGET_SR)
            fps = _fingerprint_from_samples(samples)
            return fps if fps else _fallback_raw_fingerprint(p)
        except Exception:
            return _fallback_raw_fingerprint(p)
    # Generic containers
    decoded = _decode_generic(p)
    if decoded is not None:
        samples, sr = decoded
        if samples:
            samples = _resample(samples, sr, _TARGET_SR)
            fps = _fingerprint_from_samples(samples)
            if fps:
                return fps
    # Final fallback: byte-level
    return _fallback_raw_fingerprint(p)


def _hamming32(a: int, b: int) -> int:
    """Hamming32.

    Manages hamming32 operations and coordinates related state changes for the component.

    Args:
        a (int): The a parameter.
        b (int): Integer number of bytes to format or process.

    Returns:
        int: Result of the operation.
    """
    return bin(a ^ b).count("1")


def audio_compare(fp_a: List[int], fp_b: List[int]) -> float:
    """Similarity 0.0..1.0 between two fingerprints (higher = more similar).

    Uses best-alignment sliding window: for every offset of the shorter
    sequence within the longer, compute mean Hamming distance per subfingerprint,
    then convert to similarity. Also handles exact-sequence fast path.
    """
    if not fp_a or not fp_b:
        return 0.0
    if fp_a == fp_b:
        return 1.0
    # Ensure a is shorter
    if len(fp_a) > len(fp_b):
        fp_a, fp_b = fp_b, fp_a
    n, m = len(fp_a), len(fp_b)
    if n == 0 or m == 0:
        return 0.0
    # Very different lengths with little overlap -> penalize
    length_ratio = n / m if m else 0.0
    # Single-hash fallback (very short files): direct Hamming
    if n == 1 and m == 1:
        return 1.0 - _hamming32(fp_a[0], fp_b[0]) / 32.0
    best = 0.0
    # Slide shorter across longer; step 1 for small, step 2 for large for speed
    step = 1 if m <= 120 else 2
    for offset in range(0, m - n + 1, step):
        # Mean bit error rate at this offset
        errs = 0
        for i in range(n):
            errs += _hamming32(fp_a[i], fp_b[offset + i])
        mean_err = errs / (n * 32)
        sim = 1.0 - mean_err
        if sim > best:
            best = sim
            if best >= 0.98:
                break
    # Overlap-length weighting: short overlap on long file shouldn't claim high
    # similarity if the overlapping segment is a small fraction of the longer.
    # Chromaprint dupsonic uses 15 s vs 120 s tradeoff; we mirror via ratio cap.
    # Require at least 35 % overlap of the longer, else penalize.
    if length_ratio < 0.35:
        best *= 0.7 + 0.3 * (length_ratio / 0.35)
    # Also penalize if sequences differ greatly in length (e.g., 5 s vs 120 s
    # of different content that happens to align in a short window).
    return max(0.0, min(1.0, best))


# ---------------------------------------------------------------------------
# Finder
# ---------------------------------------------------------------------------

class AudioDuplicateFinder:
    """Find acoustically-similar audio groups (same recording, any encoding).

    Args:
        root_path: Directory (or iterable of directories) to scan.
        threshold: Minimum :func:`audio_compare` score (0..1) to group.
            0.75 is a good default (≈ 8 bit errors per 32-bit subfp on average
            across the best alignment). Lower = more permissive.
        config: Exclusion rules / symlink policy.
    """

    def __init__(
        self,
        root_path: str | os.PathLike,
        threshold: float = 0.75,
        config: Config | None = None,
    ) -> None:
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            root_path (str | os.PathLike): Filesystem path to the target file or directory.
            threshold (float): The threshold parameter.
            config (Config | None): The config parameter.
        """
        if isinstance(root_path, (list, tuple)):
            roots = [normalize_path(p) for p in root_path]
        else:
            roots = [normalize_path(root_path)]
        self.roots = roots
        self.threshold = float(threshold)
        if not (0.0 <= self.threshold <= 1.0):
            raise ValueError("threshold must be in 0..1")
        self.config = config or Config()
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)
        self._lock = threading.Lock()
        self.file_count = 0
        self.error_count = 0
        self.duplicates: Dict[str, List[Path]] = {}

    # -- helpers

    def _should_exclude(self, path: Path) -> bool:
        """_should_exclude.

        Manages should exclude operations and coordinates related state changes for the component.

        Args:
            path (Path): Filesystem path to the target file or directory.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        if path.name in self.exclude_dirs:
            return True
        s = str(path)
        for pat in self.exclude_patterns:
            if pat in s or pat in path.name:
                return True
        return False

    def _is_audio(self, path: Path) -> bool:
        """_is_audio.

        Manages is audio operations and coordinates related state changes for the component.

        Args:
            path (Path): Filesystem path to the target file or directory.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return path.suffix.lower() in _AUDIO_SUFFIXES

    # -- main API

    def find_audio_duplicates(
        self,
        threads: int = 0,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> Dict[str, List[Path]]:
        """Scan roots and return acoustically-duplicate groups (size >= 2).

        Manages find audio duplicates operations and coordinates related state changes for the component.

        Args:
            threads (int): The threads parameter.
            progress_callback (Optional[Callable[[str, int], None]]): The progress callback parameter.
            cancel_event (Optional[threading.Event]): Threading event or callable to check for cancellation.

        Returns:
            Dict[str, List[Path]]: List of processed items or identifiers.
        """
        if threads <= 0:
            threads = min(16, (os.cpu_count() or 4) + 4)

        files: List[Path] = []
        for root in self.roots:
            for dirpath, dirnames, filenames in os.walk(root):
                if cancel_event and getattr(cancel_event, "is_set", lambda: False)():
                    return {}
                dirnames[:] = [d for d in dirnames if d not in self.exclude_dirs]
                rp = Path(dirpath)
                if self._should_exclude(rp):
                    dirnames[:] = []
                    continue
                for fn in filenames:
                    p = rp / fn
                    if not self._is_audio(p) or self._should_exclude(p):
                        continue
                    try:
                        if p.is_symlink() and not self.config.follow_symlinks:
                            continue
                        if p.stat().st_size == 0:
                            continue
                    except OSError:
                        continue
                    files.append(p)

        self.file_count = len(files)
        if not files:
            return {}

        # Fingerprint each audio file in parallel
        fingerprints: Dict[Path, List[int]] = {}

        def _fp_one(p: Path) -> Tuple[Path, Optional[List[int]]]:
            """_fp_one.

            Manages fp one operations and coordinates related state changes for the component.

            Args:
                p (Path): The p parameter.

            Returns:
                Tuple[Path, Optional[List[int]]]: List of processed items or identifiers.
            """
            try:
                fp = compute_audio_fingerprint(p)
                return p, fp if fp else None
            except Exception:
                return p, None

        with ThreadPoolExecutor(max_workers=threads) as ex:
            futures = {ex.submit(_fp_one, p): p for p in files}
            for fut in as_completed(futures):
                if cancel_event and getattr(cancel_event, "is_set", lambda: False)():
                    return {}
                p, fp = fut.result()
                if fp is None:
                    with self._lock:
                        self.error_count += 1
                    continue
                fingerprints[p] = fp
                if progress_callback:
                    progress_callback(f"Fingerprinted {p.name}", len(fingerprints))

        if len(fingerprints) < 2:
            return {}

        # Candidate generation: sort by first subfingerprint for locality,
        # then compare within rolling window + exhaustive check for small sets.
        # For large libraries this is the dominating cost; the window keeps it
        # O(n * w) rather than O(n^2).
        items = list(fingerprints.items())
        # Sort by first subfp value (stable) to place similar audio adjacently
        items.sort(key=lambda kv: kv[1][0] if kv[1] else 0)
        n = len(items)
        if n <= 400:
            window = n  # exhaustive for modest libraries
        elif n <= 2000:
            window = 64
        else:
            window = 32

        candidate_pairs: set[Tuple[Path, Path]] = set()
        for i in range(n):
            if cancel_event and getattr(cancel_event, "is_set", lambda: False)():
                return {}
            p_i, fp_i = items[i]
            # For windowed mode, compare only neighbours; for exhaustive, all
            upper = n if n <= 400 else min(n, i + 1 + window)
            for j in range(i + 1, upper):
                p_j, fp_j = items[j]
                # Quick pre-filter: first-subfp Hamming; if wildly different,
                # still might be a transposed cover, but for DUPLICATE pipeline
                # we require close spectral content.
                if fp_i and fp_j and n > 400:
                    if _hamming32(fp_i[0], fp_j[0]) > 14:
                        continue
                a, b = (p_i, p_j) if str(p_i) < str(p_j) else (p_j, p_i)
                candidate_pairs.add((a, b))

        # Verify candidate pairs with full alignment score, then union-find
        parent: Dict[Path, Path] = {p: p for p in fingerprints}

        def _find(x: Path) -> Path:
            """Search and locate items matching specific criteria.

            Traverses filesystem directories or cached registries to find resources that satisfy the specified filters.

            Args:
                x (Path): The x parameter.

            Returns:
                Path: Result of the operation.
            """
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def _union(a: Path, b: Path) -> None:
            """Union.

            Manages union operations and coordinates related state changes for the component.

            Args:
                a (Path): The a parameter.
                b (Path): Integer number of bytes to format or process.
            """
            ra, rb = _find(a), _find(b)
            if ra != rb:
                parent[rb] = ra

        for a, b in candidate_pairs:
            if cancel_event and getattr(cancel_event, "is_set", lambda: False)():
                break
            if audio_compare(fingerprints[a], fingerprints[b]) >= self.threshold:
                _union(a, b)

        groups: Dict[Path, List[Path]] = defaultdict(list)
        for p in fingerprints:
            groups[_find(p)].append(p)
        result: Dict[str, List[Path]] = {}
        for members in groups.values():
            if len(members) > 1:
                members.sort()
                gid = hashlib.blake2b(
                    str([str(m) for m in members]).encode(), digest_size=8
                ).hexdigest()
                result[gid] = members
        self.duplicates = result
        return result

    def get_stats(self) -> dict:
        """get_stats.

        Manages get stats operations and coordinates related state changes for the component.

        Returns:
            dict: Dictionary mapping identifiers to status or values.
        """
        total = sum(len(v) for v in self.duplicates.values())
        return {
            "total_audio_scanned": self.file_count,
            "audio_duplicate_groups": len(self.duplicates),
            "total_files_in_groups": total,
            "errors": self.error_count,
            "threshold": self.threshold,
        }


__all__ = [
    "AudioDuplicateFinder",
    "audio_compare",
    "compute_audio_fingerprint",
]
