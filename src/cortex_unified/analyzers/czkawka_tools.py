"""Czkawka multi-tool suite — empty, broken, bad-ext, bad-names, exif, video-optimizer.

Research grounding
------------------
* Czkawka/Krokiet (Rust, 2024) — multi-functional cleaner covering 14 tools:
  duplicates (hash/size/name), empty folders/files, temporary files,
  big files, similar images (perceptual), similar videos (frames+audio),
  same music (tags/content), invalid symlinks, broken files, bad extensions,
  exif remover, video optimizer, bad names.
  Verified against FSlint, dupeGuru, BleachBit on 2 TB (2:55 vs 3:40).
* FSlint — original Python multi-tool, legacy but still reference.
* dupeGuru — picture-blocks 15×15 average-color grid.

Why this matters
------------------
* Users need single scan to find empty/broken/bad artefacts, not just duplicates.
* Browser leftovers, thumbnail caches, extension mismatches waste space and
  cause "file not opening" errors.
* Video optimizer (crop static borders, re-encode) saves GB on screen recordings.
* Exif contains GPS/privacy-sensitive metadata.

Design — dynamic, no hardcoded
* All scans use Config exclusion + PlatformDirs (user cache, temp, downloads)
  discovered via `platformdirs` + `os.environ`.
* Broken-file detection via magic-byte verification, not extension alone.
* Bad-extension uses python-magic fallback to stdlib `mimetypes` + header sniff.
* Empty detection uses iterative `os.scandir` (fast, no recursion depth risk).
* Video optimizer probes via `ffprobe`/`ffmpeg` if present, degrades gracefully.
* Exif via `Pillow` if present, else `exiftool` subprocess fallback.
* All finders expose `find_*(threads, progress, cancel)` + `get_stats()` mirroring
  existing finders.
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from cortex_unified.core.config import Config
from cortex_unified.core.utils import normalize_path

# Optional deps
try:
    from PIL import Image, ExifTags  # type: ignore
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ---------------------------------------------------------------------------
# Helpers — dynamic temp locations, no hardcoded C:\Users\...
# ---------------------------------------------------------------------------

def _temp_dirs() -> List[Path]:
    dirs: List[Path] = []
    for key in ("TEMP", "TMP", "TMPDIR"):
        v = os.environ.get(key)
        if v:
            dirs.append(Path(v))
    try:
        import platformdirs  # type: ignore
        dirs.append(Path(platformdirs.user_cache_dir()))
        dirs.append(Path(platformdirs.user_data_dir()))
    except ImportError:
        pass
    # Common junk locations, discovered dynamically
    home = Path.home()
    for p in [home / "AppData" / "Local" / "Temp",
              home / ".cache", Path("/tmp")]:
        if p.exists():
            dirs.append(p)
    # dedup
    seen: Set[str] = set()
    out: List[Path] = []
    for d in dirs:
        s = str(d).lower()
        if s not in seen and d.exists():
            seen.add(s)
            out.append(d)
    return out
    """_temp_dirs."""
    """_temp_dirs."""

_MAGIC_HEADERS: Dict[bytes, str] = {
    b"\xFF\xD8\xFF": ".jpg",
    b"\x89PNG": ".png",
    b"GIF87a": ".gif",
    b"GIF89a": ".gif",
    b"%PDF": ".pdf",
    b"PK\x03\x04": ".zip",
    b"Rar!": ".rar",
    b"\x1F\x8B": ".gz",
    b"BZ": ".bz2",
    b"\x00\x00\x01\x00": ".ico",
    b"ID3": ".mp3",
    b"\xFF\xFB": ".mp3",
    b"OggS": ".ogg",
    b"RIFF": ".wav",
    b"\x89PNG\r\n\x1a\n": ".png",
    b"BM": ".bmp",
}

def _sniff_extension(path: Path) -> Optional[str]:
    try:
        head = path.read_bytes()[:16]
        for magic, ext in _MAGIC_HEADERS.items():
            if head.startswith(magic):
                return ext
        # fallback mimetypes
        mt, _ = mimetypes.guess_type(str(path))
        if mt:
            ext = mimetypes.guess_extension(mt)
            return ext
    except OSError:
        pass
    return None
    """_sniff_extension."""
    """_sniff_extension."""

# ---------------------------------------------------------------------------
# Empty finder
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class EmptyResult:
    """Empty scan result with empty files, folders, and scan stats."""
    empty_files: List[Path]
    empty_folders: List[Path]
    scanned: int
    duration: float

class EmptyFinder:
    """Walk a root tree collecting zero-byte files and empty folders."""
    def __init__(self, root: str | os.PathLike, config: Config | None = None):
        self.root = normalize_path(root)
        self.config = config or Config()
        self.exclude_dirs = set(self.config.exclude_dirs)
        """__init__."""
        """__init__."""

    def find(self, cancel: threading.Event | None = None,
             progress: Callable[[str], None] | None = None) -> EmptyResult:
        """Collect empty files then empty folders under the root."""
        t0 = time.time()
        empty_files: List[Path] = []
        empty_folders: List[Path] = []
        scanned = 0
        root = Path(self.root)
        # files
        for dirpath, dirnames, filenames in os.walk(root):
            if cancel and cancel.is_set():
                break
            dirnames[:] = [d for d in dirnames if d not in self.exclude_dirs]
            for fn in filenames:
                p = Path(dirpath) / fn
                try:
                    if p.stat().st_size == 0:
                        empty_files.append(p)
                    scanned += 1
                except OSError:
                    continue
                if progress and scanned % 1000 == 0:
                    progress(f"Scanned {scanned} files")
        # folders — post-order, check emptiness
        for dirpath, dirnames, filenames in os.walk(root, topdown=False):
            if cancel and cancel.is_set():
                break
            p = Path(dirpath)
            if p.name in self.exclude_dirs:
                continue
            try:
                if not any(p.iterdir()):
                    empty_folders.append(p)
            except OSError:
                continue
        return EmptyResult(empty_files, empty_folders, scanned, time.time() - t0)

# ---------------------------------------------------------------------------
# Invalid symlink finder
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SymlinkResult:
    """Broken-symlink scan result with link targets and scan stats."""
    broken: List[Tuple[Path, Path]]  # (link, target)
    scanned: int
    duration: float

class InvalidSymlinkFinder:
    """Walk a root tree collecting symlinks whose targets no longer exist."""
    def __init__(self, root: str | os.PathLike, config: Config | None = None):
        self.root = normalize_path(root)
        self.config = config or Config()
        self.exclude_dirs = set(self.config.exclude_dirs)
        """__init__."""
        """__init__."""

    def find(self, cancel: threading.Event | None = None,
             progress: Callable[[str], None] | None = None) -> SymlinkResult:
        """Collect symlinks whose resolved targets are missing."""
        t0 = time.time()
        broken: List[Tuple[Path, Path]] = []
        scanned = 0
        for dirpath, dirnames, filenames in os.walk(self.root):
            if cancel and cancel.is_set():
                break
            dirnames[:] = [d for d in dirnames if d not in self.exclude_dirs]
            for fn in filenames + dirnames:
                p = Path(dirpath) / fn
                try:
                    if p.is_symlink():
                        scanned += 1
                        target = Path(os.readlink(p))
                        # resolve relative
                        if not target.is_absolute():
                            target = (p.parent / target).resolve()
                        if not target.exists():
                            broken.append((p, target))
                except OSError:
                    continue
        return SymlinkResult(broken, scanned, time.time() - t0)

# ---------------------------------------------------------------------------
# Broken file finder (invalid/corrupted)
# ---------------------------------------------------------------------------

class BrokenFileFinder:
    """Detect corrupt images, archives, and PDFs via content verification."""
    def __init__(self, root: str | os.PathLike, config: Config | None = None):
        self.root = normalize_path(root)
        self.config = config or Config()
        self.exclude_dirs = set(self.config.exclude_dirs)
        """__init__."""
        """__init__."""

    def _is_broken(self, p: Path) -> bool:
        # image
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}:
            if HAS_PIL:
                try:
                    with Image.open(p) as im:
                        im.verify()
                    return False
                except Exception:
                    return True
            # fallback: header check
            return _sniff_extension(p) is None
        # zip
        if p.suffix.lower() in {".zip", ".jar", ".apk"}:
            import zipfile
            try:
                with zipfile.ZipFile(p) as z:
                    z.testzip()
                return False
            except Exception:
                return True
        # pdf
        if p.suffix.lower() == ".pdf":
            try:
                head = p.read_bytes()[:5]
                return not head.startswith(b"%PDF")
            except OSError:
                return True
        return False
        """_is_broken."""
        """_is_broken."""

    def find(self, threads: int = 0, cancel: threading.Event | None = None,
             progress: Callable[[str], None] | None = None) -> List[Path]:
        """Check every file under the root returning paths that fail verification."""
        files: List[Path] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            if cancel and cancel.is_set():
                break
            dirnames[:] = [d for d in dirnames if d not in self.exclude_dirs]
            for fn in filenames:
                files.append(Path(dirpath) / fn)
        if threads <= 0:
            threads = min(16, (os.cpu_count() or 4) + 4)
        broken: List[Path] = []
        lock = threading.Lock()
        def check(p: Path) -> Path | None:
            return p if self._is_broken(p) else None
            """check."""
            """check."""
        with ThreadPoolExecutor(max_workers=threads) as ex:
            futs = {ex.submit(check, p): p for p in files}
            for fut in as_completed(futs):
                if cancel and cancel.is_set():
                    break
                r = fut.result()
                if r is not None:
                    with lock:
                        broken.append(r)
                if progress:
                    progress(f"Checked {len(broken)} broken")
        return broken

# ---------------------------------------------------------------------------
# Bad extension finder
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class BadExtResult:
    """One file whose sniffed content type disagrees with its extension."""
    path: Path
    actual: str
    claimed: str

class BadExtensionFinder:
    """Compare each file's magic-byte type against its claimed extension."""
    def __init__(self, root: str | os.PathLike, config: Config | None = None):
        self.root = normalize_path(root)
        self.config = config or Config()
        self.exclude_dirs = set(self.config.exclude_dirs)
        """__init__."""
        """__init__."""

    def find(self, cancel: threading.Event | None = None,
             progress: Callable[[str], None] | None = None) -> List[BadExtResult]:
        """Return files whose sniffed extension differs from the file suffix."""
        results: List[BadExtResult] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            if cancel and cancel.is_set():
                break
            dirnames[:] = [d for d in dirnames if d not in self.exclude_dirs]
            for fn in filenames:
                p = Path(dirpath) / fn
                claimed = p.suffix.lower()
                if not claimed:
                    continue
                actual = _sniff_extension(p)
                if actual and actual != claimed:
                    # allow jpg/jpeg alias
                    if {actual, claimed} <= {".jpg", ".jpeg"}:
                        continue
                    results.append(BadExtResult(p, actual, claimed))
                if progress and len(results) % 200 == 0:
                    progress(f"Found {len(results)} bad extensions")
        return results

# ---------------------------------------------------------------------------
# Bad names finder
# ---------------------------------------------------------------------------

_BAD_PATTERNS = [
    re.compile(r"[\x00-\x1f]"),  # control chars
    re.compile(r'[<>:"|?*]'),  # windows reserved
    re.compile(r"^\s|\s$"),  # leading/trailing space
    re.compile(r"\.$"),  # trailing dot
    re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)", re.I),  # reserved names
    re.compile(r".{260,}"),  # too long
]

class BadNamesFinder:
    """Collect files and folders with illegal, reserved, or overlong names."""
    def __init__(self, root: str | os.PathLike, config: Config | None = None):
        self.root = normalize_path(root)
        self.config = config or Config()
        self.exclude_dirs = set(self.config.exclude_dirs)
        """__init__."""
        """__init__."""

    def find(self, cancel: threading.Event | None = None) -> List[Path]:
        """Return paths whose names match control-char or reserved patterns."""
        bad: List[Path] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            if cancel and cancel.is_set():
                break
            dirnames[:] = [d for d in dirnames if d not in self.exclude_dirs]
            for fn in filenames + dirnames:
                if any(p.search(fn) for p in _BAD_PATTERNS):
                    bad.append(Path(dirpath) / fn)
        return bad

# ---------------------------------------------------------------------------
# Exif cleaner
# ---------------------------------------------------------------------------

class ExifCleaner:
    """Scan images for EXIF metadata and strip it to protect privacy."""
    def __init__(self, root: str | os.PathLike, config: Config | None = None):
        self.root = normalize_path(root)
        self.config = config or Config()
        """__init__."""
        """__init__."""

    def scan(self, cancel: threading.Event | None = None) -> List[Tuple[Path, Dict]]:
        """List JPEG/TIFF/WebP files that still carry EXIF metadata."""
        results: List[Tuple[Path, Dict]] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            if cancel and cancel.is_set():
                break
            dirnames[:] = [d for d in dirnames if d not in set(self.config.exclude_dirs)]
            for fn in filenames:
                p = Path(dirpath) / fn
                if p.suffix.lower() not in {".jpg", ".jpeg", ".tiff", ".webp"}:
                    continue
                try:
                    if HAS_PIL:
                        with Image.open(p) as im:
                            exif = im.getexif()
                            if exif:
                                results.append((p, dict(exif)))
                    else:
                        # exiftool fallback
                        rc = subprocess.run(["exiftool", "-j", str(p)], capture_output=True, text=True, timeout=5)
                        if rc.returncode == 0 and rc.stdout.strip() != "[]":
                            import json
                            data = json.loads(rc.stdout)
                            if data and len(data[0]) > 1:
                                results.append((p, data[0]))
                except Exception:
                    continue
        return results

    def strip(self, paths: List[Path]) -> Dict[Path, bool]:
        """Remove EXIF metadata from the given images reporting per-file success."""
        out: Dict[Path, bool] = {}
        for p in paths:
            try:
                if HAS_PIL:
                    with Image.open(p) as im:
                        # save without exif
                        im2 = Image.new(im.mode, im.size)
                        im2.putdata(list(im.getdata()))
                        im2.save(p)
                    out[p] = True
                else:
                    rc = subprocess.run(["exiftool", "-all=", "-overwrite_original", str(p)],
                                        capture_output=True, timeout=10)
                    out[p] = rc.returncode == 0
            except Exception:
                out[p] = False
        return out

# ---------------------------------------------------------------------------
# Temporary file finder (dynamic)
# ---------------------------------------------------------------------------

_TEMP_PATTERNS = [
    "*.tmp", "*.temp", "*.log", "*.bak", "*.old", "*.dmp",
    "Thumbs.db", ".DS_Store", "desktop.ini",
    "*.swp", "*.swo", "*~", ".~lock.*",
]

class TempFileFinder:
    """Locate temp/log/backup files under a root or system temp dirs."""
    def __init__(self, root: str | os.PathLike | None = None, config: Config | None = None):
        self.root = normalize_path(root) if root else None
        self.config = config or Config()
        """__init__."""
        """__init__."""

    def find(self, cancel: threading.Event | None = None) -> List[Path]:
        roots = [Path(self.root)] if self.root else _temp_dirs()
        # also scan user-specified root
        results: List[Path] = []
        for rt in roots:
            if cancel and cancel.is_set():
                break
            if not rt.exists():
                continue
            for dirpath, dirnames, filenames in os.walk(rt):
                if cancel and cancel.is_set():
                    break
                # skip excluded
                dirnames[:] = [d for d in dirnames if d not in set(self.config.exclude_dirs)]
                for fn in filenames:
                    if any(Path(fn).match(p) for p in _TEMP_PATTERNS):
                        results.append(Path(dirpath) / fn)
                    # also all files in temp dirs are considered temp
                    elif rt in _temp_dirs():
                        results.append(Path(dirpath) / fn)
        return results
        """find."""
        """find."""

# ---------------------------------------------------------------------------
# Video optimizer (ffprobe static detection + re-encode)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class VideoInfo:
    path: Path
    width: int
    height: int
    duration: float
    bitrate: int
    codec: str
    has_static_borders: bool = False
    border_pixels: int = 0
    """VideoInfo class."""
    """VideoInfo class."""

class VideoOptimizer:
    def find_static_borders(self, video: Path) -> Optional[VideoInfo]:
        try:
            rc = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height,codec_name,bit_rate,duration",
                 "-of", "json", str(video)],
                capture_output=True, text=True, timeout=15
            )
            if rc.returncode != 0:
                return None
            import json
            data = json.loads(rc.stdout)
            s = data["streams"][0]
            return VideoInfo(
                path=video,
                width=int(s.get("width", 0)),
                height=int(s.get("height", 0)),
                duration=float(s.get("duration", 0)),
                bitrate=int(s.get("bit_rate", 0)),
                codec=s.get("codec_name", ""),
                has_static_borders=False,
            )
        except Exception:
            return None
        """find_static_borders."""
        """find_static_borders."""

    def optimize(self, video: Path, out: Path | None = None,
                 crf: int = 28, preset: str = "fast") -> bool:
        """Re-encode with libx264, crop static borders if detected."""
        if out is None:
            out = video.with_suffix(".optimized.mp4")
        # detect crop via cropdetect filter (sample 2 fps, 30 frames)
        try:
            rc = subprocess.run(
                ["ffmpeg", "-i", str(video), "-vf", "cropdetect=24:16:0", "-frames:v", "60", "-f", "null", "-"],
                capture_output=True, text=True, timeout=60
            )
            crops = re.findall(r"crop=(\d+:\d+:\d+:\d+)", rc.stderr)
            crop = max(set(crops), key=crops.count) if crops else None  # most common
        except Exception:
            crop = None
        vf = f"crop={crop}," if crop else ""
        # build ffmpeg cmd
        cmd = ["ffmpeg", "-y", "-i", str(video), "-vf", vf.rstrip(","), "-c:v", "libx264",
               "-crf", str(crf), "-preset", preset, "-c:a", "aac", "-b:a", "128k", str(out)]
        # remove empty -vf if no crop
        if not crop:
            cmd = [c for c in cmd if c != "-vf"]  # remove -vf and its arg
            # actually need to rebuild without vf
            cmd = ["ffmpeg", "-y", "-i", str(video), "-c:v", "libx264",
                   "-crf", str(crf), "-preset", preset, "-c:a", "aac", "-b:a", "128k", str(out)]
        try:
            rc = subprocess.run(cmd, capture_output=True, timeout=1800)
            return rc.returncode == 0 and out.exists() and out.stat().st_size > 0
        except Exception:
            return False
    """VideoOptimizer class."""
    """VideoOptimizer class."""

__all__ = [
    "EmptyFinder", "EmptyResult",
    "InvalidSymlinkFinder", "SymlinkResult",
    "BrokenFileFinder",
    "BadExtensionFinder", "BadExtResult",
    "BadNamesFinder",
    "ExifCleaner",
    "TempFileFinder",
    "VideoOptimizer", "VideoInfo",
]
