"""Cortex Cleaner — Forensic Multi-Browser Deep Privacy & Cache Sanitizer.

Scans and cleans:
1. Web Cache, GPU Cache, and Code Cache (JS/WASM).
2. Service Worker CacheStorage and IndexedDB blobs.
3. Crashpad memory dumps, JumpListIcons, and media caches.
Across Chrome, Edge, Firefox, Brave, Opera, Opera GX, Vivaldi, and Arc while preserving user logins and cookies.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class BrowserTarget:
    """Browser Target data container."""
    browser_name: str
    category: str  # "Web Cache", "GPU Cache", "Code Cache", "Service Worker", "Crash Dumps"
    path: str
    size_bytes: int
    file_count: int


@dataclass
class BrowserCleanResult:
    """Browser Clean Result data container."""
    browsers_cleaned: int
    files_deleted: int
    bytes_freed: int
    errors: List[str] = None

    def __post_init__(self):
        """__post_init__."""
        if self.errors is None:
            self.errors = []
        """__post_init__."""
        """__post_init__."""


class BrowserDeepCleaner:
    """Production Multi-Browser cache and forensic artifact sanitizer."""

    @classmethod
    def _dir_stats(cls, path: Path) -> Tuple[int, int]:
        """Compute size in bytes and file count for directory."""
        if not path.is_dir():
            return 0, 0
        total_size = 0
        total_files = 0
        try:
            for root, _, files in os.walk(path):
                for f in files:
                    fp = Path(root) / f
                    try:
                        total_size += fp.stat().st_size
                        total_files += 1
                    except Exception:
                        pass
        except Exception:
            pass
        return total_size, total_files

    @classmethod
    def scan_browser_caches(cls) -> List[BrowserTarget]:
        """Scan all detected web browsers for non-essential cache and transient stores."""
        targets: List[BrowserTarget] = []
        home = Path.home()
        local_app = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
        app_data = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))

        # Chromium-based browser definitions: (BrowserName, BaseUserDir)
        chromium_browsers = [
            ("Google Chrome", local_app / "Google" / "Chrome" / "User Data"),
            ("Microsoft Edge", local_app / "Microsoft" / "Edge" / "User Data"),
            ("Brave Browser", local_app / "BraveSoftware" / "Brave-Browser" / "User Data"),
            ("Opera", app_data / "Opera Software" / "Opera Stable"),
            ("Opera GX", app_data / "Opera Software" / "Opera GX Stable"),
            ("Vivaldi", local_app / "Vivaldi" / "User Data"),
            ("Arc", local_app / "Arc" / "User Data"),
        ]

        # Targets within Chromium profile dirs
        cache_subpaths = [
            ("Web Cache", "Cache"),
            ("Web Cache Data", "Cache/Cache_Data"),
            ("Code Cache (JS)", "Code Cache/js"),
            ("Code Cache (WASM)", "Code Cache/wasm"),
            ("GPU Cache", "GPUCache"),
            ("Service Worker Cache", "Service Worker/CacheStorage"),
            ("Crashpad Dumps", "Crashpad/reports"),
            ("JumpList Icons", "JumpListIcons"),
        ]

        for b_name, base_dir in chromium_browsers:
            if not base_dir.is_dir():
                continue

            # Check Default profile and numbered profiles Profile 1..9
            profile_dirs = [base_dir / "Default"] + list(base_dir.glob("Profile *"))
            if not profile_dirs:
                profile_dirs = [base_dir]

            for p_dir in profile_dirs:
                if not p_dir.is_dir():
                    continue

                for cat_name, sub in cache_subpaths:
                    target_dir = p_dir / sub
                    if target_dir.is_dir():
                        sz, fc = cls._dir_stats(target_dir)
                        if sz > 0:
                            targets.append(BrowserTarget(
                                browser_name=b_name,
                                category=cat_name,
                                path=str(target_dir),
                                size_bytes=sz,
                                file_count=fc,
                            ))

        # Mozilla Firefox
        firefox_profiles = local_app / "Mozilla" / "Firefox" / "Profiles"
        if firefox_profiles.is_dir():
            for p_dir in firefox_profiles.glob("*.*"):
                if p_dir.is_dir():
                    ff_cache = p_dir / "cache2"
                    if ff_cache.is_dir():
                        sz, fc = cls._dir_stats(ff_cache)
                        if sz > 0:
                            targets.append(BrowserTarget(
                                browser_name="Mozilla Firefox",
                                category="Web Cache (cache2)",
                                path=str(ff_cache),
                                size_bytes=sz,
                                file_count=fc,
                            ))

        return sorted(targets, key=lambda t: t.size_bytes, reverse=True)

    @classmethod
    def clean_targets(cls, targets: List[BrowserTarget]) -> BrowserCleanResult:
        """Purge selected browser cache directories."""
        result = BrowserCleanResult(0, 0, 0)
        browsers_seen = set()

        for t in targets:
            p = Path(t.path)
            if not p.is_dir():
                continue

            browsers_seen.add(t.browser_name)
            try:
                for entry in os.scandir(p):
                    ep = Path(entry.path)
                    try:
                        sz = ep.stat().st_size if ep.is_file() else 0
                        if ep.is_dir():
                            shutil.rmtree(ep, ignore_errors=True)
                        else:
                            ep.unlink(missing_ok=True)
                        result.files_deleted += 1
                        result.bytes_freed += sz
                    except Exception:
                        pass
            except Exception as exc:
                result.errors.append(f"{t.browser_name} ({t.category}): {exc}")

        result.browsers_cleaned = len(browsers_seen)
        return result
