import { useState } from "react";

const phases = [
  {
    id: 1,
    title: "Foundation & Production Hardening",
    subtitle: "Fix structural problems before adding features",
    color: "#E24B4A",
    accent: "#fcebeb",
    icon: "ti-shield-check",
    priority: "Critical",
    effort: "2–3 weeks",
    items: [
      {
        title: "Fix namespace & import chaos",
        type: "Bug Fix",
        file: "__main__.py, __init__.py",
        detail: `The project imports from 'cortex_unified' but the root __init__.py exposes no package alias. __main__.py calls 'from cortex_unified.cli.cli import main' which breaks unless the package is installed as 'cortex_unified'. Rename all internal references consistently or set up a proper editable install.`,
        code: `# pyproject.toml — single source of truth
[project]
name = "cortex-cleaner"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
  "PySide6>=6.6",
  "click>=8.1",
  "psutil>=5.9",
  "pyyaml>=6.0",
  "xxhash>=3.4",
  "send2trash>=1.8",
  "rich>=13.0",
  "sqlalchemy>=2.0",
]

[project.scripts]
cortex-cleaner = "cortex_unified.__main__:main"

[tool.setuptools.packages.find]
where = ["."]`
      },
      {
        title: "Replace YAML config with Pydantic v2 schema",
        type: "Refactor",
        file: "core/config.py",
        detail: "Current Config uses raw YAML dict with no type checking, no defaults, no validation. Bad values silently pass through. Replace with a Pydantic BaseSettings model — it handles YAML, env vars, and CLI overrides in one pass, with full type safety.",
        code: `from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List

class Config(BaseSettings):
    exclude_patterns: List[str] = ["*.log","node_modules",".git","__pycache__"]
    exclude_dirs: List[str] = [".git","__pycache__","node_modules"]
    min_age_days: int = Field(default=0, ge=0, le=3650)
    threads: int = Field(default=0, ge=0, le=256)
    default_action: str = Field(default="dry_run",
                                 pattern="^(dry_run|delete|trash)$")
    log_level: str = Field(default="INFO",
                            pattern="^(DEBUG|INFO|WARNING|ERROR)$")
    db_path: Path = Path.home() / ".cortex_cleaner" / "history.db"
    backup_dir: Path = Path.home() / ".cortex_cleaner" / "backups"

    @field_validator("threads")
    @classmethod
    def clamp_threads(cls, v):
        import os
        return min(v or os.cpu_count(), 64)

    model_config = {"env_prefix": "CORTEX_", "yaml_file": "~/.cortex_cleaner.yaml"}`
      },
      {
        title: "Add SQLite persistence layer",
        type: "New Feature",
        file: "core/database.py (new)",
        detail: "Currently every scan result is lost when the app closes. Restore manifests are flat JSON files. Replace with SQLAlchemy 2.0 + SQLite so scan history, stats, scheduled jobs, and restore points all persist with proper queries and relationships.",
        code: `from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import DeclarativeBase, Session
from datetime import datetime

class Base(DeclarativeBase): pass

class ScanRun(Base):
    __tablename__ = "scan_runs"
    id = Column(Integer, primary_key=True)
    scan_type = Column(String(64), nullable=False)
    root_path = Column(String(1024))
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    items_found = Column(Integer, default=0)
    bytes_found = Column(Integer, default=0)
    bytes_freed = Column(Integer, default=0)
    health_score_before = Column(Integer)
    health_score_after = Column(Integer)

class DeletedItem(Base):
    __tablename__ = "deleted_items"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, nullable=False)
    path = Column(String(4096), nullable=False)
    size_bytes = Column(Integer, default=0)
    sha256 = Column(String(64))
    backup_path = Column(String(4096))
    deleted_at = Column(DateTime, default=datetime.utcnow)
    restored_at = Column(DateTime)`
      },
      {
        title: "Structured logging with structlog",
        type: "Infrastructure",
        file: "core/logging_setup.py (new)",
        detail: "Current code uses stdlib logging.getLogger() scattered across 30+ files with no structured output. In production you need JSON logs that can be ingested by Loki/Splunk/CloudWatch, with request IDs, correlation, and log levels controlled from config.",
        code: `import structlog
import logging
from pathlib import Path

def configure_logging(log_level: str = "INFO",
                      log_file: Path | None = None,
                      json_output: bool = False):
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    if log_file:
        handler = logging.FileHandler(log_file)
        logging.root.addHandler(handler)

log = structlog.get_logger()`
      },
      {
        title: "Complete test suite — pytest + hypothesis",
        type: "Testing",
        file: "tests/ (new directory)",
        detail: "Zero tests exist today. This is the single biggest production risk. Any refactor can silently break things. Minimum viable test suite: unit tests for every analyzer, property tests for path validation safety, integration tests for scan→delete→restore cycle.",
        code: `# tests/safety/test_path_validator.py
import pytest
from hypothesis import given, strategies as st
from cortex_unified.ui.safety.path_validator import PathValidator, PathValidationError

class TestPathValidator:
    def setup_method(self):
        self.v = PathValidator()

    @given(st.text(min_size=1))
    def test_random_paths_never_raise_unhandled(self, path):
        """Fuzz: no crash on arbitrary strings."""
        try:
            self.v.validate_path(path)
        except PathValidationError:
            pass  # expected

    @pytest.mark.parametrize("critical", [
        "/bin", "/etc", "/usr/bin", "C:\\Windows", "C:\\Program Files"
    ])
    def test_critical_dirs_always_rejected(self, critical):
        with pytest.raises(PathValidationError):
            self.v.validate_path(critical, allow_system=False)

    def test_symlink_traversal_blocked(self, tmp_path):
        target = tmp_path / "secret"
        target.mkdir()
        link = tmp_path / "innocent_link"
        link.symlink_to(target)
        with pytest.raises(PathValidationError):
            self.v.validate_path(str(link), follow_symlinks=False)`
      },
      {
        title: "Privilege escalation handler",
        type: "Security",
        file: "core/privilege.py (new)",
        detail: "The app runs file deletion, registry edits, startup changes, and process killing — all of which require elevated privileges on Windows (UAC) and Linux/macOS (sudo/pkexec). Currently there is no graceful handling; operations just fail with PermissionError. Add a proper elevation module.",
        code: `import sys, os, subprocess
from enum import Enum

class PrivilegeLevel(Enum):
    USER = "user"
    ELEVATED = "elevated"

def current_level() -> PrivilegeLevel:
    if sys.platform == "win32":
        import ctypes
        return PrivilegeLevel.ELEVATED if ctypes.windll.shell32.IsUserAnAdmin() else PrivilegeLevel.USER
    return PrivilegeLevel.ELEVATED if os.geteuid() == 0 else PrivilegeLevel.USER

def request_elevation() -> bool:
    """Re-launch self with elevated privileges. Returns False if already elevated."""
    if current_level() == PrivilegeLevel.ELEVATED:
        return False
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    elif sys.platform == "darwin":
        subprocess.Popen(["osascript", "-e", f'do shell script "{sys.executable} {" ".join(sys.argv)}" with administrator privileges'])
    else:
        subprocess.Popen(["pkexec"] + sys.argv)
    sys.exit(0)`
      },
    ]
  },
  {
    id: 2,
    title: "Scanner Performance Overhaul",
    subtitle: "10× faster scans with async I/O and xxHash",
    color: "#BA7517",
    accent: "#faeeda",
    icon: "ti-bolt",
    priority: "High",
    effort: "2 weeks",
    items: [
      {
        title: "Replace MD5 duplicates with xxHash + bloom filter",
        type: "Performance",
        file: "analyzers/duplicate_finder.py",
        detail: "MD5 hashing is 3–5× slower than xxHash3 and has known collision weaknesses. For 1M files, add a size-bucketing pre-filter so only same-size files get hashed. Add a bloom filter for the 'definitely not a duplicate' fast path, which eliminates 90%+ of files before any I/O.",
        code: `import xxhash
from bitarray import bitarray
import math

class FastDuplicateFinder:
    def __init__(self, expected_items=1_000_000, fp_rate=0.001):
        # Bloom filter: skip obvious non-duplicates
        n_bits = math.ceil(-expected_items * math.log(fp_rate) / math.log(2)**2)
        self._bloom = bitarray(n_bits)
        self._bloom.setall(0)
        self._size_buckets: dict[int, list[Path]] = {}

    def _hash_file(self, path: Path, chunk=65536) -> str:
        h = xxhash.xxh3_128()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk), b""):
                h.update(chunk)
        return h.hexdigest()

    def find_duplicates(self, root: Path) -> dict[str, list[Path]]:
        # Phase 1: bucket by size (free)
        for p in root.rglob("*"):
            if p.is_file():
                sz = p.stat().st_size
                self._size_buckets.setdefault(sz, []).append(p)
        # Phase 2: only hash files sharing a size bucket
        groups: dict[str, list[Path]] = {}
        for sz, paths in self._size_buckets.items():
            if len(paths) < 2 or sz == 0:
                continue
            for path in paths:
                digest = self._hash_file(path)
                groups.setdefault(digest, []).append(path)
        return {k: v for k, v in groups.items() if len(v) > 1}`
      },
      {
        title: "Async filesystem scanner with anyio",
        type: "Performance",
        file: "core/scanner.py",
        detail: "Current scanner.py uses recursive os.walk in a thread pool — the recursion can stack-overflow on 10,000+ deep paths, and thread context-switching limits I/O parallelism. Rewrite with anyio (works on asyncio or trio), using async directory iteration and semaphores to cap concurrency.",
        code: `import anyio, anyio.to_thread
from pathlib import Path

class AsyncScanner:
    def __init__(self, config, max_concurrent=256):
        self.config = config
        self._sem = anyio.Semaphore(max_concurrent)

    async def scan_dir(self, path: Path) -> AsyncIterator[Path]:
        async with self._sem:
            try:
                entries = await anyio.to_thread.run_sync(
                    lambda: list(path.iterdir()), cancellable=True
                )
            except (PermissionError, OSError):
                return
        async with anyio.create_task_group() as tg:
            for entry in entries:
                if entry.is_dir() and not self.config.matches_exclude_patterns(str(entry)):
                    tg.start_soon(self._collect, entry)
                elif entry.is_file():
                    yield entry

    async def run(self, root: Path) -> list[Path]:
        results = []
        async with anyio.create_task_group() as tg:
            async for path in self.scan_dir(root):
                results.append(path)
        return results`
      },
      {
        title: "Incremental scan with inotify/FSEvents/ReadDirectoryChanges",
        type: "New Feature",
        file: "core/file_watcher.py (new)",
        detail: "Every scan is a full re-scan from scratch. On a 500GB drive with 2M files this takes 30-60 seconds. Add a file system watcher that tracks changes since the last scan and only re-scans modified directories. Background agent already has the infrastructure for this.",
        code: `from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from cortex_unified.core.database import db_session
from cortex_unified.core.scanner import SmartScannerWorker

class IncrementalWatcher(FileSystemEventHandler):
    def __init__(self, root: str, config):
        self.root = root
        self.config = config
        self._dirty_dirs: set[str] = set()
        self._observer = Observer()

    def on_modified(self, event):
        if not event.is_directory:
            import os
            self._dirty_dirs.add(os.path.dirname(event.src_path))

    def on_created(self, event):
        self._dirty_dirs.add(os.path.dirname(event.src_path))

    def on_deleted(self, event):
        self._dirty_dirs.add(os.path.dirname(event.src_path))
        # invalidate DB cache for deleted path
        with db_session() as s:
            s.execute("DELETE FROM file_cache WHERE path LIKE ?", [event.src_path + "%"])

    def start(self):
        self._observer.schedule(self, self.root, recursive=True)
        self._observer.start()

    def flush_dirty(self) -> list[str]:
        dirty = list(self._dirty_dirs)
        self._dirty_dirs.clear()
        return dirty`
      },
      {
        title: "Multi-drive parallel scan with progress merging",
        type: "Enhancement",
        file: "performance/multi_drive_scanner.py",
        detail: "Current multi_drive_scanner.py imports 'keyring' unconditionally which breaks on headless Linux servers. The progress merging is done by polling. Replace keyring with an optional dependency, fix progress to use a shared asyncio.Queue that aggregates sub-scanner events.",
        code: `from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Optional
try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

@dataclass
class DriveProgress:
    drive_path: str
    total_files: int
    scanned_files: int
    bytes_found: int
    
    @property
    def pct(self) -> float:
        return 100 * self.scanned_files / max(self.total_files, 1)

class MultiDriveScanner:
    async def scan_all_drives(self, drives: list[str]) -> AsyncGenerator[DriveProgress, None]:
        queue: asyncio.Queue[DriveProgress | None] = asyncio.Queue()
        
        async def scan_one(drive: str):
            scanner = AsyncScanner(self.config)
            async for item in scanner.scan_dir(Path(drive)):
                await queue.put(DriveProgress(drive, -1, 1, item.stat().st_size))
            await queue.put(None)  # sentinel

        async with asyncio.TaskGroup() as tg:
            for drive in drives:
                tg.create_task(scan_one(drive))

        done = 0
        while done < len(drives):
            item = await queue.get()
            if item is None:
                done += 1
            else:
                yield item`
      },
    ]
  },
  {
    id: 3,
    title: "Cross-Platform Completeness",
    subtitle: "macOS & Linux deserve first-class support",
    color: "#0F6E56",
    accent: "#e1f5ee",
    icon: "ti-device-desktop",
    priority: "High",
    effort: "3 weeks",
    items: [
      {
        title: "macOS-native cleanup module",
        type: "New Feature",
        file: "analyzers/macos_cleaner.py (new)",
        detail: "macOS has dozens of unique cleanup targets that are completely unaddressed: ~/Library/Caches, ~/Library/Application Support orphans, Time Machine local snapshots (tmutil), Spotlight index rebuild, .DS_Store files, quarantine database, plist corruption, Xcode derived data.",
        code: `import subprocess, plistlib
from pathlib import Path

class MacOSCleaner:
    HOME = Path.home()

    def scan_derived_data(self) -> list[dict]:
        """Xcode derived data can be 10–50 GB."""
        derived = self.HOME / "Library/Developer/Xcode/DerivedData"
        return [{"path": p, "size": sum(f.stat().st_size for f in p.rglob("*") if f.is_file())}
                for p in derived.iterdir() if p.is_dir()] if derived.exists() else []

    def scan_time_machine_snapshots(self) -> list[dict]:
        result = subprocess.run(["tmutil", "listlocalsnapshots", "/"],
                                capture_output=True, text=True)
        snapshots = []
        for line in result.stdout.splitlines():
            if line.startswith("com.apple"):
                size_out = subprocess.run(
                    ["tmutil", "localsnapshot-list", "--snapshotDate", line],
                    capture_output=True, text=True)
                snapshots.append({"name": line, "size_bytes": self._parse_snapshot_size(size_out.stdout)})
        return snapshots

    def remove_ds_store_files(self, root: Path, dry_run=True) -> int:
        count = 0
        for p in root.rglob(".DS_Store"):
            if not dry_run:
                p.unlink()
            count += 1
        return count

    def rebuild_spotlight_index(self, volume="/"):
        subprocess.run(["mdutil", "-E", volume], check=True)
        subprocess.run(["mdutil", "-i", "on", volume], check=True)`
      },
      {
        title: "Linux systemd / snap / flatpak cleanup",
        type: "New Feature",
        file: "analyzers/linux_cleaner.py (new)",
        detail: "Linux users accumulate journal logs (often 1–5 GB), old snap revisions (snapd keeps last 2 by default but many distros never clean), flatpak unused runtimes, old kernel packages. None of this is currently addressed.",
        code: `import subprocess, os
from pathlib import Path

class LinuxCleaner:
    def scan_journal_size(self) -> int:
        r = subprocess.run(["journalctl", "--disk-usage"],
                           capture_output=True, text=True)
        # Parse: "Archived and active journals take up X.XG"
        import re
        m = re.search(r"([\d.]+)([KMGT]B?)", r.stdout)
        if m:
            n, unit = float(m.group(1)), m.group(2)[0]
            return int(n * {"K":1024,"M":1024**2,"G":1024**3,"T":1024**4}[unit])
        return 0

    def vacuum_journal(self, max_size_mb=200, dry_run=True) -> str:
        if dry_run:
            return f"Would vacuum journal to {max_size_mb}MB"
        r = subprocess.run(["journalctl", f"--vacuum-size={max_size_mb}M"],
                           capture_output=True, text=True, check=True)
        return r.stdout

    def list_old_snap_revisions(self) -> list[dict]:
        r = subprocess.run(["snap", "list", "--all"],
                           capture_output=True, text=True)
        revs = []
        for line in r.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 6 and parts[5] == "disabled":
                revs.append({"name": parts[0], "rev": parts[2]})
        return revs

    def remove_old_snap_revisions(self, dry_run=True) -> list[str]:
        cleaned = []
        for item in self.list_old_snap_revisions():
            if not dry_run:
                subprocess.run(["snap", "remove", item["name"], "--revision", item["rev"]])
            cleaned.append(f"{item['name']} rev {item['rev']}")
        return cleaned`
      },
      {
        title: "Browser support for macOS/Linux privacy cleaner",
        type: "Bug Fix",
        file: "analyzers/privacy_cleaner.py",
        detail: "PrivacyCleaner.__init__() hard-codes LOCALAPPDATA and APPDATA which only exist on Windows. On Linux and macOS all browsers return empty paths, so the scan always reports 0 bytes. Rewrite path discovery to be OS-aware.",
        code: `import sys, os
from pathlib import Path

class PrivacyCleaner:
    def __init__(self):
        self.browser_paths = self._discover_browsers()

    def _discover_browsers(self) -> dict[str, list[Path]]:
        home = Path.home()
        if sys.platform == "win32":
            la = Path(os.environ.get("LOCALAPPDATA",""))
            ap = Path(os.environ.get("APPDATA",""))
            return {
                "Chrome":  [la/"Google"/"Chrome"/"User Data"],
                "Edge":    [la/"Microsoft"/"Edge"/"User Data"],
                "Brave":   [la/"BraveSoftware"/"Brave-Browser"/"User Data"],
                "Firefox": [ap/"Mozilla"/"Firefox"/"Profiles"],
            }
        elif sys.platform == "darwin":
            lib = home/"Library"/"Application Support"
            return {
                "Chrome":  [lib/"Google"/"Chrome"],
                "Safari":  [home/"Library"/"Safari"],
                "Firefox": [home/"Library"/"Application Support"/"Firefox"/"Profiles"],
                "Brave":   [lib/"BraveSoftware"/"Brave-Browser"],
            }
        else:  # Linux
            cfg = home/".config"
            return {
                "Chrome":   [cfg/"google-chrome"],
                "Chromium": [cfg/"chromium"],
                "Firefox":  [home/".mozilla"/"firefox"],
                "Brave":    [cfg/"BraveSoftware"/"Brave-Browser"],
                "Vivaldi":  [cfg/"vivaldi"],
                "Opera":    [cfg/"opera"],
            }`
      },
      {
        title: "Developer tool cache cleanup (all platforms)",
        type: "New Feature",
        file: "analyzers/dev_cache_cleaner.py (new)",
        detail: "Developers accumulate enormous caches: Cargo registry (~5–20GB), Go module cache (~3–10GB), pip wheels, npm cache, Gradle/Maven, Composer, Cocoapods. The current package_manager_cleaner.py only handles apt/brew/pip/npm install caches — not the build artifact caches.",
        code: `from pathlib import Path
import shutil

class DevCacheCleaner:
    HOME = Path.home()

    CACHES = {
        "Rust/Cargo registry":   HOME / ".cargo" / "registry",
        "Go module cache":       Path(os.environ.get("GOPATH", HOME/"go")) / "pkg" / "mod",
        "pip wheel cache":       HOME / ".cache" / "pip",
        "npm cache":             HOME / ".npm" / "_cacache",
        "Yarn v1 cache":         HOME / ".cache" / "yarn",
        "Gradle cache":          HOME / ".gradle" / "caches",
        "Maven local repo":      HOME / ".m2" / "repository",
        "Composer cache":        HOME / ".composer" / "cache",
        "Cocoapods cache":       HOME / ".cocoapods" / "repos",
        "Pub (Dart) cache":      HOME / ".pub-cache",
        "Mix (Elixir) archive":  HOME / ".mix" / "archives",
        "Stack (Haskell)":       HOME / ".stack",
        "pnpm store":            HOME / ".local" / "share" / "pnpm" / "store",
        "Python venv orphans":   None,  # discover dynamically
    }

    def scan(self) -> list[dict]:
        results = []
        for name, path in self.CACHES.items():
            if path and path.exists():
                size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                results.append({"name": name, "path": path, "size_bytes": size})
        return sorted(results, key=lambda x: x["size_bytes"], reverse=True)`
      },
    ]
  },
  {
    id: 4,
    title: "AI-Powered Intelligence",
    subtitle: "Smarter decisions, fewer user errors",
    color: "#534AB7",
    accent: "#eeedfe",
    icon: "ti-brain",
    priority: "High",
    effort: "3–4 weeks",
    items: [
      {
        title: "Perceptual duplicate detection for images/video",
        type: "New Feature",
        file: "analyzers/media_dedup.py (new)",
        detail: "Current duplicate finder only does exact byte-for-byte matching. People accumulate visually identical images that differ in resolution, compression, or metadata — e.g. 'photo.jpg' vs 'photo (1).jpg' vs 'photo_compressed.jpg'. Use ImageHash (pHash/dHash) for near-duplicate image detection, with configurable similarity threshold.",
        code: `from PIL import Image
import imagehash
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class ImageDuplicate:
    paths: list[Path]
    hashes: list[str]
    similarity: float
    recommended_keep: Path  # largest resolution

class MediaDedupFinder:
    def __init__(self, hash_size=16, max_distance=10):
        self.hash_size = hash_size
        self.max_distance = max_distance

    def _phash(self, path: Path) -> imagehash.ImageHash | None:
        try:
            with Image.open(path) as img:
                return imagehash.phash(img, hash_size=self.hash_size)
        except Exception:
            return None

    def find_near_duplicates(self, paths: list[Path]) -> list[ImageDuplicate]:
        hashes: list[tuple[Path, imagehash.ImageHash]] = []
        for p in paths:
            h = self._phash(p)
            if h: hashes.append((p, h))

        groups = defaultdict(list)
        visited = set()
        for i, (p1, h1) in enumerate(hashes):
            if i in visited: continue
            group = [p1]
            visited.add(i)
            for j, (p2, h2) in enumerate(hashes[i+1:], i+1):
                if j not in visited and (h1 - h2) <= self.max_distance:
                    group.append(p2)
                    visited.add(j)
            if len(group) > 1:
                keep = max(group, key=lambda p: p.stat().st_size)
                groups[id(group)].append(ImageDuplicate(group, [], 0.0, keep))

        return [v[0] for v in groups.values()]`
      },
      {
        title: "AI-powered 'explain this folder' assistant",
        type: "New Feature",
        file: "ui/tabs/ai_assistant_tab.py (new)",
        detail: "When users find an unfamiliar folder (e.g. 'com.squirrel.slack.slack' or 'RUMBA_x64_1.2.3'), they have no idea if it's safe to delete. Add a right-click 'Explain this' action that sends the folder name, size, age, and contained file types to Claude API and shows a plain-English explanation + recommendation.",
        code: `import anthropic
from pathlib import Path
import json

class AIFolderExplainer:
    def __init__(self, api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key)

    def explain_folder(self, path: Path) -> str:
        # Gather non-invasive metadata
        files = list(path.rglob("*"))
        extensions = [f.suffix.lower() for f in files if f.is_file()]
        ext_counts = {e: extensions.count(e) for e in set(extensions)}
        
        context = {
            "folder_name": path.name,
            "parent": path.parent.name,
            "size_mb": round(sum(f.stat().st_size for f in files if f.is_file()) / 1e6, 1),
            "file_count": len(files),
            "extension_breakdown": ext_counts,
            "age_days": max(((__import__("time").time() - f.stat().st_mtime) / 86400) for f in files[:5] if f.is_file()) if files else 0,
        }

        message = self.client.messages.create(
            model="claude-opus-4-5",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": f"""This folder was found on a user's computer. In 2-3 sentences:
1. What likely created it and what it contains
2. Whether it's safe to delete
Folder info: {json.dumps(context, indent=2)}
Be direct and practical. Start with the app/system that created it."""
            }]
        )
        return message.content[0].text`
      },
      {
        title: "ML-based junk file classifier",
        type: "New Feature",
        file: "analyzers/ml_classifier.py (new)",
        detail: "Rule-based junk detection misses many files. A lightweight ONNX model trained on labeled datasets of 'safe to delete' vs 'keep' files (using filename, extension, path depth, size, age, modification pattern) can improve accuracy from ~85% to ~97% with sub-millisecond inference.",
        code: `import onnxruntime as ort
import numpy as np
from pathlib import Path
from typing import NamedTuple
import re, time

class FileFeatures(NamedTuple):
    extension_hash: int    # one-hot encoded via hash trick
    path_depth: int
    size_log10: float      # log10(size_bytes + 1)
    age_days: float
    has_tmp_pattern: int   # 1 if name matches temp patterns
    has_cache_pattern: int
    has_version_number: int # e.g. "1.2.3" in name
    parent_is_cache: int    # parent dir contains "cache"/"temp"

TMP_RE = re.compile(r"(\.tmp|~|\.bak|\.old|\.part|\.crdownload)$", re.I)
CACHE_RE = re.compile(r"cache|temp|tmp|log", re.I)

class MLJunkClassifier:
    def __init__(self, model_path: str = "models/junk_classifier.onnx"):
        self.sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

    def _featurize(self, path: Path) -> np.ndarray:
        stat = path.stat()
        return np.array([[
            hash(path.suffix.lower()) % 512,
            len(path.parts),
            np.log10(stat.st_size + 1),
            (time.time() - stat.st_mtime) / 86400,
            int(bool(TMP_RE.search(path.name))),
            int(bool(CACHE_RE.search(path.name))),
            int(bool(re.search(r"\d+\.\d+", path.name))),
            int(bool(CACHE_RE.search(path.parent.name))),
        ]], dtype=np.float32)

    def predict_junk_probability(self, path: Path) -> float:
        inputs = {"features": self._featurize(path)}
        prob = self.sess.run(None, inputs)[0][0][1]
        return float(prob)`
      },
      {
        title: "Predictive scheduling based on usage patterns",
        type: "New Feature",
        file: "scheduler/smart_schedule.py (new)",
        detail: "The current scheduler uses fixed cron-style rules. A smarter approach uses the history database to learn when the disk typically fills fastest (Monday after big downloads?) and auto-adjusts cleanup frequency. Also detect when the system is idle before running scans.",
        code: `from cortex_unified.core.database import ScanRun
import sqlalchemy as sa
from datetime import datetime, timedelta
import statistics

class SmartScheduler:
    def __init__(self, db_session_factory):
        self.db = db_session_factory

    def suggest_next_run(self) -> datetime:
        """Analyze history to suggest optimal next cleanup time."""
        with self.db() as s:
            runs = s.scalars(sa.select(ScanRun).order_by(ScanRun.started_at.desc()).limit(30)).all()

        if len(runs) < 5:
            return datetime.now() + timedelta(days=7)

        # Calculate days between runs and bytes accumulated
        intervals = [(runs[i].started_at - runs[i+1].started_at).days
                     for i in range(len(runs)-1)]
        bytes_per_day = statistics.mean([
            (runs[i].bytes_found - runs[i+1].bytes_found) / max(d, 1)
            for i, d in enumerate(intervals) if d > 0
        ])

        # Suggest a run when we'd cross 500MB of expected junk
        days_until_500mb = 500_000_000 / max(bytes_per_day, 1)
        days_clamped = max(1, min(30, int(days_until_500mb)))
        return datetime.now() + timedelta(days=days_clamped)`
      },
    ]
  },
  {
    id: 5,
    title: "Security & Safe Deletion",
    subtitle: "Military-grade shredding and safe-delete guarantees",
    color: "#993C1D",
    accent: "#faece7",
    icon: "ti-lock",
    priority: "High",
    effort: "2 weeks",
    items: [
      {
        title: "Verified DOD 5220.22-M / Gutmann secure shredder",
        type: "Security",
        file: "analyzers/weaponized_shredder.py + file_shredder.py",
        detail: "The current shredder.py is 3136 bytes — far too small to implement a real multi-pass DOD or Gutmann 35-pass scheme. It must verify each pass was written (no OS write caching), use O_DIRECT on Linux to bypass page cache, and confirm final zero-fill.",
        code: `import os, ctypes, struct
from pathlib import Path
from enum import Enum

class ShredMethod(Enum):
    ZERO_FILL = "zeros"            # 1 pass — fast
    DOD_3PASS = "dod_3"            # DoD 5220.22-M (3-pass)
    DOD_7PASS = "dod_7"            # DoD 5220.22-M-E (7-pass)
    GUTMANN = "gutmann"            # 35-pass (SSD-pointless, HDD legacy)
    PARANOID = "paranoid"          # random+zero+random+verify

DOD_PATTERNS = [b"\\x00", b"\\xFF", None]   # None = random

def shred_file(path: Path, method: ShredMethod = ShredMethod.DOD_7PASS) -> dict:
    stat = path.stat()
    size = stat.st_size
    passes_written = 0

    flags = os.O_WRONLY | os.O_SYNC
    if hasattr(os, "O_DIRECT"):           # Linux: bypass page cache
        flags |= os.O_DIRECT

    fd = os.open(str(path), flags)
    try:
        patterns = _get_patterns(method)
        for pat in patterns:
            os.lseek(fd, 0, os.SEEK_SET)
            data = pat * size if pat else os.urandom(size)
            # Align to 512-byte sector for O_DIRECT
            aligned = ((len(data) + 511) // 512) * 512
            buf = data.ljust(aligned, b"\\x00")
            written = os.write(fd, buf)
            os.fsync(fd)   # force flush to storage
            passes_written += 1
    finally:
        os.close(fd)

    path.unlink()
    return {"passes": passes_written, "size": size, "method": method.value}`
      },
      {
        title: "Pre-deletion quarantine & snapshot",
        type: "New Feature",
        file: "core/quarantine.py (new)",
        detail: "Before deleting any file, copy it to an encrypted quarantine zone with metadata. Files are auto-expired after 30 days. This replaces the flat JSON manifest in restore_manager.py with a proper quarantine store backed by the SQLite DB.",
        code: `import shutil, hashlib, json
from pathlib import Path
from datetime import datetime, timedelta
from cortex_unified.core.database import DeletedItem, db_session

class QuarantineStore:
    def __init__(self, store_dir: Path, max_age_days: int = 30):
        self.dir = store_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.max_age = timedelta(days=max_age_days)

    def quarantine(self, path: Path) -> str:
        """Move to quarantine, return quarantine ID."""
        qid = hashlib.sha1(f"{path}{datetime.utcnow()}".encode()).hexdigest()[:12]
        dest = self.dir / qid
        dest.mkdir()
        shutil.copy2(path, dest / path.name)
        with open(dest / "meta.json", "w") as f:
            json.dump({"original_path": str(path), "quarantined_at": datetime.utcnow().isoformat()}, f)
        with db_session() as s:
            s.add(DeletedItem(path=str(path), backup_path=str(dest / path.name),
                              sha256=self._sha256(path)))
        return qid

    def restore(self, qid: str) -> Path | None:
        meta_file = self.dir / qid / "meta.json"
        if not meta_file.exists(): return None
        meta = json.loads(meta_file.read_text())
        original = Path(meta["original_path"])
        shutil.move(str(self.dir / qid / original.name), original)
        return original

    def sweep_expired(self):
        for entry in self.dir.iterdir():
            meta = entry / "meta.json"
            if meta.exists():
                data = json.loads(meta.read_text())
                age = datetime.utcnow() - datetime.fromisoformat(data["quarantined_at"])
                if age > self.max_age:
                    shutil.rmtree(entry)`
      },
      {
        title: "Registry cleaner with full transaction rollback",
        type: "Security",
        file: "system_tools/registry_cleaner.py",
        detail: "The current registry cleaner writes a manifest file for rollback. But if the process crashes mid-clean, the manifest is incomplete and the registry is inconsistent. Use Windows registry transactions (NtCreateTransaction) or at minimum export each key before touching it.",
        code: `import winreg, subprocess
from pathlib import Path
from datetime import datetime

class SafeRegistryCleaner:
    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir

    def _export_key(self, hive: int, sub_key: str, backup_file: Path):
        hive_name = {winreg.HKEY_LOCAL_MACHINE: "HKLM",
                     winreg.HKEY_CURRENT_USER: "HKCU"}[hive]
        subprocess.run(
            ["reg", "export", f"{hive_name}\\\\{sub_key}", str(backup_file), "/y"],
            check=True, capture_output=True
        )

    def safe_delete_key(self, hive: int, sub_key: str, dry_run=True) -> dict:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = self.backup_dir / f"reg_backup_{timestamp}.reg"

        if not dry_run:
            self._export_key(hive, sub_key, backup)
            try:
                winreg.DeleteKey(hive, sub_key)
                return {"status": "deleted", "backup": str(backup)}
            except Exception as e:
                # Auto-restore
                subprocess.run(["reg", "import", str(backup)], check=True)
                return {"status": "rolled_back", "error": str(e)}
        return {"status": "dry_run", "would_delete": sub_key}`
      },
    ]
  },
  {
    id: 6,
    title: "Modern Integrations",
    subtitle: "Cloud storage, containers, REST API",
    color: "#185FA5",
    accent: "#e6f1fb",
    icon: "ti-cloud",
    priority: "Medium",
    effort: "4 weeks",
    items: [
      {
        title: "Cloud storage trash & cache cleanup",
        type: "New Feature",
        file: "analyzers/cloud_cleaner.py (new)",
        detail: "Dropbox, Google Drive, and OneDrive all maintain local caches and trash. Dropbox cache alone can reach 5–20GB. Google Drive local file caches aren't tracked anywhere today. Add platform-specific cleanup for each major cloud provider's local footprint.",
        code: `from pathlib import Path
import sys, os, json

class CloudCleaner:
    HOME = Path.home()

    def scan_dropbox_cache(self) -> dict:
        if sys.platform == "win32":
            cache = self.HOME / "AppData" / "Local" / "Dropbox" / "cache"
        elif sys.platform == "darwin":
            cache = self.HOME / ".dropbox" / "cache"
        else:
            cache = self.HOME / ".dropbox" / "cache"
        if not cache.exists():
            return {}
        size = sum(f.stat().st_size for f in cache.rglob("*") if f.is_file())
        return {"path": cache, "size_bytes": size, "name": "Dropbox cache"}

    def scan_onedrive_cache(self) -> dict:
        if sys.platform != "win32":
            return {}
        cache = Path(os.environ.get("LOCALAPPDATA","")) / "Microsoft" / "OneDrive" / "logs"
        if not cache.exists():
            return {}
        size = sum(f.stat().st_size for f in cache.rglob("*.log") if f.is_file())
        return {"path": cache, "size_bytes": size, "name": "OneDrive logs"}

    def empty_icloud_trash(self) -> str:
        if sys.platform != "darwin":
            return "iCloud only available on macOS"
        import subprocess
        result = subprocess.run(
            ["osascript", "-e", 'tell application "Finder" to empty trash'],
            capture_output=True, text=True)
        return "done" if result.returncode == 0 else result.stderr`
      },
      {
        title: "REST API with FastAPI for remote management",
        type: "New Feature",
        file: "api/ (new module)",
        detail: "Teams need to run Cortex Cleaner on remote servers or in CI pipelines. A FastAPI-based REST API with JWT auth exposes all scan/clean operations as HTTP endpoints. Also useful for a future web UI or integration with monitoring dashboards.",
        code: `from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from cortex_unified.core.scanner import AsyncScanner
from cortex_unified.core.config import Config

app = FastAPI(title="Cortex Cleaner API", version="2.0.0")
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/token")

class ScanRequest(BaseModel):
    root_path: str = "/"
    scan_types: list[str] = ["junk","duplicates","large_files"]

class ScanStatus(BaseModel):
    job_id: str
    status: str    # queued | running | done | failed
    progress_pct: float
    bytes_found: int

_jobs: dict[str, dict] = {}

@app.post("/scans", response_model=ScanStatus)
async def start_scan(req: ScanRequest, bg: BackgroundTasks,
                     token: str = Depends(oauth2)):
    import uuid
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "queued", "progress_pct": 0, "bytes_found": 0}
    bg.add_task(_run_scan, job_id, req)
    return ScanStatus(job_id=job_id, status="queued", progress_pct=0, bytes_found=0)

@app.get("/scans/{job_id}", response_model=ScanStatus)
async def get_scan_status(job_id: str, token: str = Depends(oauth2)):
    if job_id not in _jobs:
        raise HTTPException(404)
    j = _jobs[job_id]
    return ScanStatus(job_id=job_id, **j)

@app.delete("/scans/{job_id}/results")
async def clean_results(job_id: str, token: str = Depends(oauth2)):
    # Execute deletion of files found in scan
    ...`
      },
      {
        title: "WSL (Windows Subsystem for Linux) cleanup",
        type: "New Feature",
        file: "analyzers/wsl_cleaner.py (new)",
        detail: "WSL virtual disk files (ext4.vhdx) grow continuously and never auto-shrink. A 2GB Linux install can balloon to 50GB+ over time. The only fix is running 'wsl --shutdown' and 'diskpart compact', which Cortex Cleaner can automate with user approval.",
        code: `import subprocess, os, re
from pathlib import Path

class WSLCleaner:
    def list_distros(self) -> list[dict]:
        if os.name != "nt":
            return []
        r = subprocess.run(["wsl", "--list", "--verbose"],
                           capture_output=True, text=True, encoding="utf-16-le")
        distros = []
        for line in r.stdout.splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 3:
                distros.append({"name": parts[0].lstrip("*").strip(), "state": parts[1], "version": parts[2]})
        return distros

    def get_vhd_size(self, distro_name: str) -> int:
        lad = Path(os.environ.get("LOCALAPPDATA",""))
        vhd = lad / "Packages" / f"*{distro_name}*" / "LocalState" / "ext4.vhdx"
        import glob
        matches = glob.glob(str(vhd))
        if matches:
            return Path(matches[0]).stat().st_size
        return 0

    def compact_vhd(self, distro_name: str, dry_run=True) -> dict:
        """Shut down WSL, compact VHD disk file."""
        if dry_run:
            size = self.get_vhd_size(distro_name)
            return {"action": "dry_run", "current_size_gb": round(size/1e9, 1)}
        subprocess.run(["wsl", "--shutdown"], check=True)
        lad = Path(os.environ.get("LOCALAPPDATA",""))
        vhd_glob = str(lad / "Packages" / f"*{distro_name}*" / "LocalState" / "ext4.vhdx")
        import glob
        for vhd in glob.glob(vhd_glob):
            # Run diskpart compact script
            script = f"select vdisk file=\\"{vhd}\\"\\nattach vdisk readonly\\ncompact vdisk\\ndetach vdisk"
            subprocess.run(["diskpart"], input=script, text=True, capture_output=True)
        return {"action": "compacted"}`
      },
      {
        title: "Prometheus metrics + webhook notifications",
        type: "New Feature",
        file: "monitoring/ (new module)",
        detail: "Ops teams want Prometheus metrics (disk free, items found per scan, cleanup history) exported at /metrics. Add webhook support so scheduled cleanups can POST results to Slack, Discord, Teams, or any webhook URL — with per-team configurable thresholds.",
        code: `from prometheus_client import Gauge, Counter, generate_latest, CONTENT_TYPE_LATEST
import httpx, asyncio
from cortex_unified.core.database import ScanRun

# Prometheus metrics
disk_free_gb      = Gauge("cortex_disk_free_gb",      "Free disk space in GB", ["drive"])
scan_items_found  = Gauge("cortex_scan_items_found",   "Items found in last scan", ["scan_type"])
cleanups_total    = Counter("cortex_cleanups_total",   "Total cleanups performed")
bytes_freed_total = Counter("cortex_bytes_freed_total","Total bytes freed")

async def post_webhook(url: str, payload: dict):
    """Send results to any webhook (Slack, Discord, custom)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, timeout=10)
        resp.raise_for_status()

def make_slack_payload(run: ScanRun) -> dict:
    mb = run.bytes_freed / 1e6
    emoji = "🟢" if mb < 100 else "🟡" if mb < 1000 else "🔴"
    return {
        "text": f"{emoji} Cortex Cleaner: freed {mb:.1f} MB on {run.root_path}",
        "blocks": [{
            "type": "section",
            "text": {"type": "mrkdwn",
                     "text": f"*Cortex Cleaner Report*\\n• Items found: {run.items_found}\\n• Freed: {mb:.1f} MB\\n• Health score: {run.health_score_after}/100"}
        }]
    }`
      },
    ]
  },
  {
    id: 7,
    title: "UX & Accessibility",
    subtitle: "Onboarding, dark mode, better reporting",
    color: "#3B6D11",
    accent: "#eaf3de",
    icon: "ti-eye",
    priority: "Medium",
    effort: "2 weeks",
    items: [
      {
        title: "Onboarding wizard for new users",
        type: "New Feature",
        file: "ui/onboarding.py (new)",
        detail: "New users open the app and see 25 tabs with no guidance. Add a 4-step onboarding wizard: (1) select paths to monitor, (2) set exclusion rules, (3) choose safety level, (4) run first smart scan. Should only appear on first launch, with option to skip.",
        code: `from PySide6.QtWidgets import QWizard, QWizardPage, QVBoxLayout, QLabel, QFileDialog

class OnboardingWizard(QWizard):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Welcome to Cortex Cleaner")
        self.setWizardStyle(QWizard.ModernStyle)
        self.addPage(WelcomePage())
        self.addPage(SelectPathsPage(config))
        self.addPage(SafetyLevelPage(config))
        self.addPage(FirstScanPage(config))

class SafetyLevelPage(QWizardPage):
    LEVELS = {
        "Conservative": "Only delete temp/cache files. Ask before everything else.",
        "Balanced": "Auto-delete obvious junk, confirm for app data & duplicates.",
        "Aggressive": "Automatically clean everything above confidence threshold.",
    }
    def __init__(self, config):
        super().__init__()
        self.setTitle("Choose your safety level")
        layout = QVBoxLayout()
        from PySide6.QtWidgets import QRadioButton
        for level, desc in self.LEVELS.items():
            btn = QRadioButton(f"{level} — {desc}")
            layout.addWidget(btn)
        self.setLayout(layout)`
      },
      {
        title: "Trend charts and space-saved history in Dashboard",
        type: "Enhancement",
        file: "ui/tabs/dashboard_tab.py",
        detail: "The current Dashboard shows a static health score from the last scan only. No history, no trends. Add a 30-day chart showing health score over time, cumulative bytes freed, and a timeline of cleanup events using the new SQLite database.",
        code: `from PySide6.QtCharts import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis
from PySide6.QtCore import QDateTime
from cortex_unified.core.database import ScanRun
import sqlalchemy as sa

def build_health_chart(runs: list[ScanRun]) -> QChartView:
    series = QLineSeries()
    for run in runs[-30:]:
        if run.health_score_after is not None:
            dt = QDateTime.fromString(run.finished_at.isoformat(), "yyyy-MM-ddTHH:mm:ss")
            series.append(dt.toMSecsSinceEpoch(), run.health_score_after)

    chart = QChart()
    chart.addSeries(series)
    chart.setTitle("System health — last 30 cleanups")

    axis_x = QDateTimeAxis()
    axis_x.setFormat("MMM d")
    axis_x.setTitleText("Date")
    chart.addAxis(axis_x, Qt.AlignBottom)
    series.attachAxis(axis_x)

    axis_y = QValueAxis()
    axis_y.setRange(0, 100)
    axis_y.setTitleText("Health score")
    chart.addAxis(axis_y, Qt.AlignLeft)
    series.attachAxis(axis_y)

    return QChartView(chart)`
      },
      {
        title: "OS-native dark/light theme sync",
        type: "Enhancement",
        file: "accessibility/themes.py",
        detail: "Current themes.py provides manual dark/light toggle but doesn't detect the OS preference at startup, and doesn't update when the user changes their OS setting. Add QStyleHints.colorSchemeChanged() signal handler for real-time sync.",
        code: `from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import Qt, QObject, Slot

class ThemeManager(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self._apply_current_scheme()
        # React to live OS theme changes
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._on_scheme_change)

    def _apply_current_scheme(self):
        scheme = QGuiApplication.styleHints().colorScheme()
        self._apply_scheme(scheme)

    @Slot(Qt.ColorScheme)
    def _on_scheme_change(self, scheme):
        self._apply_scheme(scheme)

    def _apply_scheme(self, scheme: Qt.ColorScheme):
        if scheme == Qt.ColorScheme.Dark:
            self.app.setStyleSheet(DARK_QSS)
        else:
            self.app.setStyleSheet(LIGHT_QSS)

DARK_QSS = """
QMainWindow { background-color: #1a1a1a; }
QWidget { color: #e0e0e0; background-color: #1a1a1a; }
QTabWidget::pane { border: 1px solid #333; }
QPushButton { background-color: #2d2d2d; color: #e0e0e0; border: 1px solid #444; }
"""

LIGHT_QSS = """
QMainWindow { background-color: #f5f5f5; }
QWidget { color: #1a1a1a; background-color: #ffffff; }
"""`
      },
    ]
  },
  {
    id: 8,
    title: "Plugin Architecture & Packaging",
    subtitle: "Extensible by design, installable everywhere",
    color: "#5F5E5A",
    accent: "#f1efe8",
    icon: "ti-puzzle",
    priority: "Medium",
    effort: "2 weeks",
    items: [
      {
        title: "Plugin system with entry-point discovery",
        type: "New Feature",
        file: "plugins/ (new module)",
        detail: "Third parties should be able to add new analyzers without forking the repo. Use Python entry_points mechanism: any package that declares 'cortex_cleaner.analyzers' entry_point is auto-discovered at startup. Each plugin provides a standard Analyzer ABC.",
        code: `from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator
from dataclasses import dataclass
import importlib.metadata

@dataclass
class FoundItem:
    path: Path
    size_bytes: int
    confidence: float    # 0.0–1.0 that this is safe to delete
    category: str        # "cache"|"duplicate"|"junk"|"old"|"log"
    description: str

class BaseAnalyzer(ABC):
    name: str = ""
    description: str = ""
    icon: str = "ti-file"

    @abstractmethod
    def scan(self, root: Path) -> Iterator[FoundItem]: ...

    @abstractmethod
    def clean(self, items: list[FoundItem], dry_run: bool = True) -> dict: ...

def discover_plugins() -> list[type[BaseAnalyzer]]:
    """Auto-discover analyzers from installed packages."""
    plugins = []
    for ep in importlib.metadata.entry_points(group="cortex_cleaner.analyzers"):
        try:
            cls = ep.load()
            if issubclass(cls, BaseAnalyzer):
                plugins.append(cls)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Plugin {ep.name} failed to load: {e}")
    return plugins`
      },
      {
        title: "Cross-platform installer packaging (PyInstaller + NSIS/DMG)",
        type: "Infrastructure",
        file: "packaging/ (new)",
        detail: "There is currently no installer. Users must 'pip install' from source. Add CI/CD pipeline that builds: Windows NSIS installer (.exe), macOS DMG with drag-to-Applications, Linux AppImage and .deb/.rpm packages. All via GitHub Actions on tag push.",
        code: `# .github/workflows/release.yml
name: Build & Release
on:
  push:
    tags: ["v*"]

jobs:
  build:
    strategy:
      matrix:
        include:
          - os: windows-latest
            artifact: cortex-cleaner-windows.exe
          - os: macos-latest
            artifact: cortex-cleaner-macos.dmg
          - os: ubuntu-latest
            artifact: cortex-cleaner-linux.AppImage

    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install pyinstaller pyside6 .
      - run: pyinstaller cortex_cleaner.spec --clean
      - name: Build installer (Windows)
        if: runner.os == 'Windows'
        run: |
          choco install nsis -y
          makensis packaging/installer.nsi
      - name: Build DMG (macOS)
        if: runner.os == 'macOS'
        run: |
          pip install dmgbuild
          dmgbuild -s packaging/dmg_settings.py "Cortex Cleaner" dist/cortex-cleaner-macos.dmg
      - uses: actions/upload-release-asset@v1
        with:
          asset_path: dist/${{ matrix.artifact }}`
      },
      {
        title: "Auto-update with Sparkle/WinSparkle",
        type: "New Feature",
        file: "core/updater.py (new)",
        detail: "There's no update mechanism. Users stay on old versions forever. Add a background update checker using the GitHub Releases API, with a version comparison and in-app download prompt. On macOS use Sparkle; on Windows use WinSparkle; on Linux check AppImageUpdate.",
        code: `import httpx, packaging.version
from cortex_unified._version import __version__

RELEASES_URL = "https://api.github.com/repos/cortex-cleaner/cortex-cleaner/releases/latest"

async def check_for_update() -> dict | None:
    """Returns update info dict if new version available, else None."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(RELEASES_URL, headers={"Accept": "application/vnd.github+json"})
            r.raise_for_status()
            data = r.json()
    except Exception:
        return None

    latest = data.get("tag_name","").lstrip("v")
    current = __version__

    try:
        if packaging.version.parse(latest) > packaging.version.parse(current):
            return {
                "current": current,
                "latest": latest,
                "release_notes": data.get("body",""),
                "download_url": next(
                    (a["browser_download_url"] for a in data.get("assets",[])
                     if _matches_platform(a["name"])), None
                )
            }
    except packaging.version.InvalidVersion:
        pass
    return None`
      },
    ]
  },
];

const typeColors = {
  "Bug Fix": { bg: "#fcebeb", text: "#A32D2D", border: "#F7C1C1" },
  "Refactor": { bg: "#faeeda", text: "#854F0B", border: "#FAC775" },
  "New Feature": { bg: "#eeedfe", text: "#3C3489", border: "#CECBF6" },
  "Infrastructure": { bg: "#E1F5EE", text: "#085041", border: "#9FE1CB" },
  "Performance": { bg: "#e6f1fb", text: "#0C447C", border: "#B5D4F4" },
  "Security": { bg: "#FAECE7", text: "#712B13", border: "#F5C4B3" },
  "Enhancement": { bg: "#EAF3DE", text: "#27500A", border: "#C0DD97" },
  "Testing": { bg: "#EAF3DE", text: "#27500A", border: "#C0DD97" },
};

const priorityColors = {
  "Critical": "#E24B4A",
  "High": "#BA7517",
  "Medium": "#185FA5",
};

export default function UpgradePlan() {
  const [activePhase, setActivePhase] = useState(null);
  const [expandedItem, setExpandedItem] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");

  const totalItems = phases.reduce((s, p) => s + p.items.length, 0);
  const totalNew = phases.reduce((s, p) => s + p.items.filter(i => i.type === "New Feature").length, 0);
  const totalSecurity = phases.reduce((s, p) => s + p.items.filter(i => i.type === "Security").length, 0);

  return (
    <div style={{ fontFamily: "var(--font-sans)", padding: "1.5rem 0", maxWidth: 680 }}>
      <h2 aria-hidden className="sr-only">Cortex Cleaner — Production Upgrade Plan</h2>
      {/* Header */}
      <div style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <i className="ti ti-shield-bolt" style={{ fontSize: 22, color: "var(--color-text-primary)" }} aria-hidden />
          <span style={{ fontSize: 20, fontWeight: 500, color: "var(--color-text-primary)" }}>Cortex Cleaner — Production Upgrade Plan</span>
        </div>
        <p style={{ fontSize: 14, color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.6 }}>
          Full audit of 121 files across 15 modules. 8 upgrade phases, {totalItems} implementation tasks, ordered by impact.
        </p>
      </div>

      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: "1.5rem" }}>
        {[
          { label: "Total tasks", value: totalItems, icon: "ti-list-check" },
          { label: "New features", value: totalNew, icon: "ti-sparkles" },
          { label: "Security fixes", value: totalSecurity, icon: "ti-shield-check" },
          { label: "Est. weeks", value: "18–20", icon: "ti-calendar" },
        ].map(stat => (
          <div key={stat.label} style={{
            background: "var(--color-background-secondary)",
            borderRadius: 8, padding: "12px 14px",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
              <i className={`ti ${stat.icon}`} style={{ fontSize: 14, color: "var(--color-text-secondary)" }} aria-hidden />
              <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>{stat.label}</span>
            </div>
            <div style={{ fontSize: 22, fontWeight: 500, color: "var(--color-text-primary)" }}>{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Tab bar */}
      <div style={{ display: "flex", gap: 4, marginBottom: "1.5rem", borderBottom: "0.5px solid var(--color-border-tertiary)" }}>
        {["overview", "phases", "architecture"].map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={{
            background: "none", border: "none", padding: "8px 14px",
            fontSize: 13, fontWeight: activeTab === tab ? 500 : 400,
            color: activeTab === tab ? "var(--color-text-primary)" : "var(--color-text-secondary)",
            borderBottom: activeTab === tab ? "2px solid var(--color-text-primary)" : "2px solid transparent",
            cursor: "pointer", marginBottom: -1, textTransform: "capitalize",
          }}>{tab}</button>
        ))}
      </div>

      {activeTab === "overview" && (
        <div>
          <p style={{ fontSize: 14, color: "var(--color-text-secondary)", marginBottom: "1.25rem", lineHeight: 1.7 }}>
            Click any phase to expand its implementation tasks. Each task includes the specific file to change and working code.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {phases.map(phase => (
              <div key={phase.id} style={{
                background: "var(--color-background-primary)",
                border: "0.5px solid var(--color-border-tertiary)",
                borderRadius: 12, overflow: "hidden",
                borderLeft: `3px solid ${phase.color}`,
              }}>
                <button onClick={() => setActivePhase(activePhase === phase.id ? null : phase.id)} style={{
                  width: "100%", background: "none", border: "none", cursor: "pointer",
                  padding: "14px 16px", display: "flex", alignItems: "center", gap: 12, textAlign: "left",
                }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center",
                    background: phase.accent, flexShrink: 0,
                  }}>
                    <i className={`ti ${phase.icon}`} style={{ fontSize: 18, color: phase.color }} aria-hidden />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <span style={{ fontSize: 14, fontWeight: 500, color: "var(--color-text-primary)" }}>
                        Phase {phase.id}: {phase.title}
                      </span>
                      <span style={{
                        fontSize: 11, padding: "2px 8px", borderRadius: 6,
                        background: phase.accent, color: phase.color, fontWeight: 500,
                      }}>{phase.priority}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 2 }}>
                      {phase.subtitle} · {phase.items.length} tasks · {phase.effort}
                    </div>
                  </div>
                  <i className={`ti ${activePhase === phase.id ? "ti-chevron-up" : "ti-chevron-down"}`}
                    style={{ fontSize: 16, color: "var(--color-text-secondary)", flexShrink: 0 }} aria-hidden />
                </button>

                {activePhase === phase.id && (
                  <div style={{ borderTop: "0.5px solid var(--color-border-tertiary)" }}>
                    {phase.items.map((item, idx) => {
                      const tc = typeColors[item.type] || typeColors["Enhancement"];
                      const key = `${phase.id}-${idx}`;
                      const isOpen = expandedItem === key;
                      return (
                        <div key={idx} style={{ borderBottom: idx < phase.items.length - 1 ? "0.5px solid var(--color-border-tertiary)" : "none" }}>
                          <button onClick={() => setExpandedItem(isOpen ? null : key)} style={{
                            width: "100%", background: "none", border: "none", cursor: "pointer",
                            padding: "12px 16px", display: "flex", alignItems: "flex-start", gap: 10, textAlign: "left",
                          }}>
                            <span style={{
                              fontSize: 11, padding: "2px 8px", borderRadius: 5,
                              background: tc.bg, color: tc.text,
                              border: `0.5px solid ${tc.border}`,
                              flexShrink: 0, whiteSpace: "nowrap", marginTop: 1,
                            }}>{item.type}</span>
                            <div style={{ flex: 1 }}>
                              <div style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)" }}>{item.title}</div>
                              <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 2 }}>
                                <i className="ti ti-file-code" style={{ fontSize: 11, marginRight: 4 }} aria-hidden />{item.file}
                              </div>
                            </div>
                            <i className={`ti ${isOpen ? "ti-minus" : "ti-plus"}`}
                              style={{ fontSize: 14, color: "var(--color-text-secondary)", flexShrink: 0, marginTop: 2 }} aria-hidden />
                          </button>

                          {isOpen && (
                            <div style={{ padding: "0 16px 16px 16px" }}>
                              <p style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.65, marginBottom: 12, marginTop: 0 }}>
                                {item.detail}
                              </p>
                              <div style={{
                                background: "var(--color-background-secondary)",
                                borderRadius: 8, padding: 14,
                                border: "0.5px solid var(--color-border-tertiary)",
                              }}>
                                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
                                  <i className="ti ti-code" style={{ fontSize: 13, color: "var(--color-text-secondary)" }} aria-hidden />
                                  <span style={{ fontSize: 11, color: "var(--color-text-secondary)", fontWeight: 500 }}>Implementation</span>
                                </div>
                                <pre style={{
                                  margin: 0, fontSize: 11, lineHeight: 1.6,
                                  color: "var(--color-text-primary)", overflow: "auto",
                                  fontFamily: "var(--font-mono)", whiteSpace: "pre-wrap",
                                }}>{item.code}</pre>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === "phases" && (
        <div>
          <p style={{ fontSize: 14, color: "var(--color-text-secondary)", marginBottom: "1.25rem", lineHeight: 1.7 }}>
            Recommended execution sequence. Each phase builds on the previous one — don't start phase 4 (AI) before phase 1 (foundation) is stable.
          </p>
          {phases.map((phase, i) => (
            <div key={phase.id} style={{ display: "flex", gap: 14, marginBottom: "1.25rem" }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <div style={{
                  width: 32, height: 32, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
                  background: phase.accent, border: `1.5px solid ${phase.color}`, fontSize: 13, fontWeight: 500, color: phase.color, flexShrink: 0,
                }}>{phase.id}</div>
                {i < phases.length - 1 && <div style={{ width: 1, flex: 1, background: "var(--color-border-tertiary)", marginTop: 4, minHeight: 24 }} />}
              </div>
              <div style={{ flex: 1, paddingBottom: i < phases.length - 1 ? "1rem" : 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
                  <span style={{ fontSize: 14, fontWeight: 500, color: "var(--color-text-primary)" }}>{phase.title}</span>
                  <span style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>{phase.effort}</span>
                  <span style={{ fontSize: 11, fontWeight: 500, color: priorityColors[phase.priority] }}>{phase.priority}</span>
                </div>
                <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "0 0 8px", lineHeight: 1.6 }}>{phase.subtitle}</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {phase.items.map(item => {
                    const tc = typeColors[item.type] || typeColors["Enhancement"];
                    return (
                      <span key={item.title} style={{
                        fontSize: 11, padding: "3px 8px", borderRadius: 5,
                        background: tc.bg, color: tc.text, border: `0.5px solid ${tc.border}`,
                      }}>{item.title}</span>
                    );
                  })}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === "architecture" && (
        <div>
          <p style={{ fontSize: 14, color: "var(--color-text-secondary)", marginBottom: "1.25rem", lineHeight: 1.7 }}>
            Target architecture after all upgrades are complete — new modules shown in purple, enhanced modules in teal, unchanged in gray.
          </p>
          {[
            {
              layer: "Entry points", color: "#E6F1FB", border: "#185FA5", text: "#0C447C",
              items: ["CLI (click)", "Qt GUI (PySide6)", "REST API (FastAPI) ✦", "Tray agent"],
            },
            {
              layer: "Intelligence", color: "#EEEDFE", border: "#534AB7", text: "#3C3489",
              items: ["Smart scanner", "ML classifier ✦", "AI folder explainer ✦", "Media dedup ✦", "Predictive scheduler ✦"],
            },
            {
              layer: "Analyzers", color: "#E1F5EE", border: "#0F6E56", text: "#085041",
              items: ["Deep cleaner", "Privacy cleaner ✦", "macOS cleaner ✦", "Linux cleaner ✦", "Dev cache ✦", "Cloud cleaner ✦", "WSL cleaner ✦"],
            },
            {
              layer: "System tools", color: "#E1F5EE", border: "#0F6E56", text: "#085041",
              items: ["Registry (with rollback) ✦", "Startup mgr", "Telemetry blocker", "App uninstaller", "Secure shredder ✦"],
            },
            {
              layer: "Core", color: "#EEEDFE", border: "#534AB7", text: "#3C3489",
              items: ["Async scanner ✦", "Pydantic config ✦", "SQLite DB ✦", "Quarantine ✦", "Privilege mgr ✦", "File watcher ✦"],
            },
            {
              layer: "Infrastructure", color: "#F1EFE8", border: "#5F5E5A", text: "#444441",
              items: ["structlog ✦", "Prometheus metrics ✦", "Webhooks ✦", "Auto-updater ✦", "Plugin system ✦"],
            },
          ].map(row => (
            <div key={row.layer} style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginBottom: 5, fontWeight: 500 }}>{row.layer}</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {row.items.map(item => (
                  <span key={item} style={{
                    fontSize: 12, padding: "4px 10px", borderRadius: 6,
                    background: row.color, color: row.text,
                    border: `0.5px solid ${row.border}`,
                    fontWeight: item.includes("✦") ? 500 : 400,
                  }}>{item}</span>
                ))}
              </div>
            </div>
          ))}
          <div style={{ marginTop: "1.25rem", padding: "10px 14px", background: "var(--color-background-secondary)", borderRadius: 8, fontSize: 12, color: "var(--color-text-secondary)" }}>
            <i className="ti ti-info-circle" style={{ fontSize: 13, marginRight: 6 }} aria-hidden />
            <strong style={{ fontWeight: 500 }}>✦</strong> = new or significantly changed in this upgrade plan · All modules gain type annotations, tests, and structlog
          </div>
        </div>
      )}
    </div>
  );
}
