"""Privacy Cleaner — detects and removes browser traces for all major browsers.

Dynamically discovers Chromium profiles instead of hard-coding 3 profile names.
Supports: Chrome, Edge, Brave, Opera, Vivaldi, Firefox.
Also cleans system-level privacy traces (Recent docs, DNS cache, etc.)
"""

import os
import glob
import shutil
import subprocess
import logging
from typing import List, Dict


class PrivacyCleaner:
    """Cleans browser data, caches, and Windows system traces."""

    def __init__(self):
        self.logger = logging.getLogger("privacy_cleaner")
        self.local_appdata = os.environ.get("LOCALAPPDATA", "")
        self.appdata = os.environ.get("APPDATA", "")

        self.browser_paths: Dict[str, str] = {
            "Chrome":   os.path.join(self.local_appdata, "Google", "Chrome", "User Data"),
            "Edge":     os.path.join(self.local_appdata, "Microsoft", "Edge", "User Data"),
            "Brave":    os.path.join(self.local_appdata, "BraveSoftware", "Brave-Browser", "User Data"),
            "Opera":    os.path.join(self.appdata, "Opera Software", "Opera Stable"),
            "Vivaldi":  os.path.join(self.local_appdata, "Vivaldi", "User Data"),
            "Firefox":  os.path.join(self.appdata, "Mozilla", "Firefox", "Profiles"),
        }

    # ──────────────────────────────────────────────────────────────────
    # Scanning
    # ──────────────────────────────────────────────────────────────────

    def scan_browsers(self) -> Dict[str, Dict[str, int]]:
        """Scan all known browsers and return {browser: {category: size_bytes}}."""
        results: Dict[str, Dict[str, int]] = {}

        for browser, base_path in self.browser_paths.items():
            if not os.path.exists(base_path):
                continue

            stats: Dict[str, int] = {"Cache": 0, "Cookies": 0, "History": 0, "Sessions": 0}

            if browser == "Firefox":
                self._scan_firefox(base_path, stats)
            elif browser == "Opera":
                # Opera stores data directly in the base path (no profile subfolders)
                self._scan_chromium_profile(base_path, stats)
            else:
                # Chromium-based — dynamically discover profiles
                for profile_dir in self._discover_chromium_profiles(base_path):
                    self._scan_chromium_profile(profile_dir, stats)

            if sum(stats.values()) > 0:
                results[browser] = stats

        return results

    def scan_system_traces(self) -> Dict[str, int]:
        """Return sizes of cleanable Windows system privacy traces."""
        traces: Dict[str, int] = {}

        # Recent documents
        recent = os.path.join(self.appdata, "Microsoft", "Windows", "Recent")
        traces["Recent Documents"] = self._get_dir_size(recent)

        # Windows temp internet files
        inet = os.path.join(self.local_appdata, "Microsoft", "Windows", "INetCache")
        traces["Internet Cache"] = self._get_dir_size(inet)

        # Taskbar jump lists
        jumplists_auto = os.path.join(self.appdata, "Microsoft", "Windows", "Recent", "AutomaticDestinations")
        jumplists_custom = os.path.join(self.appdata, "Microsoft", "Windows", "Recent", "CustomDestinations")
        traces["Jump Lists"] = self._get_dir_size(jumplists_auto) + self._get_dir_size(jumplists_custom)

        return {k: v for k, v in traces.items() if v > 0}

    # ──────────────────────────────────────────────────────────────────
    # Cleaning
    # ──────────────────────────────────────────────────────────────────

    def clean_browser(self, browser: str, items: List[str]) -> bool:
        """Delete specified data categories for a browser.  Returns False on partial failure."""
        base_path = self.browser_paths.get(browser)
        if not base_path or not os.path.exists(base_path):
            return False

        success = True
        try:
            if browser == "Firefox":
                for profile in glob.glob(os.path.join(base_path, "*.*")):
                    if "Cookies" in items:
                        self._safe_delete(os.path.join(profile, "cookies.sqlite"))
                    if "History" in items:
                        self._safe_delete(os.path.join(profile, "places.sqlite"))
                    if "Cache" in items:
                        cache2 = os.path.join(profile, "cache2")
                        if os.path.isdir(cache2):
                            self._safe_delete_dir(cache2)
                    if "Sessions" in items:
                        self._safe_delete(os.path.join(profile, "sessionstore.jsonlz4"))
            elif browser == "Opera":
                success = self._clean_chromium_profile(base_path, items)
            else:
                for profile_dir in self._discover_chromium_profiles(base_path):
                    if not self._clean_chromium_profile(profile_dir, items):
                        success = False
        except Exception as exc:
            self.logger.error("Error cleaning %s: %s", browser, exc)
            success = False

        return success

    def clean_system_traces(self) -> int:
        """Clean system-level privacy traces, return bytes freed."""
        freed = 0

        # Recent docs
        recent = os.path.join(self.appdata, "Microsoft", "Windows", "Recent")
        freed += self._clean_directory_contents(recent)

        # Internet cache
        inet = os.path.join(self.local_appdata, "Microsoft", "Windows", "INetCache")
        freed += self._clean_directory_contents(inet)

        # Flush DNS cache
        try:
            subprocess.run(["ipconfig", "/flushdns"],
                           capture_output=True, timeout=10, creationflags=0x08000000)
        except Exception:
            pass

        return freed

    # ──────────────────────────────────────────────────────────────────
    # Chromium helpers
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _discover_chromium_profiles(base_path: str) -> List[str]:
        """Dynamically find Chromium profile directories."""
        profiles: List[str] = []
        if not os.path.isdir(base_path):
            return profiles
        for entry in os.listdir(base_path):
            full = os.path.join(base_path, entry)
            if not os.path.isdir(full):
                continue
            # Default profile or numbered Profile N
            if entry == "Default" or entry.startswith("Profile "):
                profiles.append(full)
            # Also check for "Guest Profile" or "System Profile"
            elif entry in ("Guest Profile", "System Profile"):
                profiles.append(full)
        return profiles

    def _scan_chromium_profile(self, prof_path: str, stats: Dict[str, int]):
        """Accumulate sizes from one Chromium profile."""
        # Cache (new Chromium stores it under Cache/Cache_Data)
        for cache_sub in ("Cache", os.path.join("Cache", "Cache_Data"),
                          "Code Cache", "GPUCache", "Service Worker"):
            stats["Cache"] += self._get_dir_size(os.path.join(prof_path, cache_sub))

        # Cookies (moved to Network/ subdirectory in modern Chromium)
        stats["Cookies"] += self._get_file_size(os.path.join(prof_path, "Network", "Cookies"))
        stats["Cookies"] += self._get_file_size(os.path.join(prof_path, "Cookies"))  # legacy

        # History
        stats["History"] += self._get_file_size(os.path.join(prof_path, "History"))

        # Sessions
        stats["Sessions"] += self._get_file_size(os.path.join(prof_path, "Current Session"))
        stats["Sessions"] += self._get_file_size(os.path.join(prof_path, "Current Tabs"))

    def _clean_chromium_profile(self, prof_path: str, items: List[str]) -> bool:
        """Delete specified items in one Chromium profile."""
        ok = True
        if "Cache" in items:
            for sub in ("Cache", "Code Cache", "GPUCache", "Service Worker"):
                self._safe_delete_dir(os.path.join(prof_path, sub))
        if "Cookies" in items:
            self._safe_delete(os.path.join(prof_path, "Network", "Cookies"))
            self._safe_delete(os.path.join(prof_path, "Cookies"))
        if "History" in items:
            self._safe_delete(os.path.join(prof_path, "History"))
            self._safe_delete(os.path.join(prof_path, "History-journal"))
            self._safe_delete(os.path.join(prof_path, "Visited Links"))
        if "Sessions" in items:
            self._safe_delete(os.path.join(prof_path, "Current Session"))
            self._safe_delete(os.path.join(prof_path, "Current Tabs"))
            self._safe_delete(os.path.join(prof_path, "Last Session"))
            self._safe_delete(os.path.join(prof_path, "Last Tabs"))
        return ok

    # ──────────────────────────────────────────────────────────────────
    # Firefox helpers
    # ──────────────────────────────────────────────────────────────────

    def _scan_firefox(self, profiles_path: str, stats: Dict[str, int]):
        for profile in glob.glob(os.path.join(profiles_path, "*.*")):
            stats["Cookies"] += self._get_file_size(os.path.join(profile, "cookies.sqlite"))
            stats["History"] += self._get_file_size(os.path.join(profile, "places.sqlite"))
            stats["Sessions"] += self._get_file_size(os.path.join(profile, "sessionstore.jsonlz4"))

            # Firefox cache2
            cache2 = os.path.join(profile, "cache2")
            stats["Cache"] += self._get_dir_size(cache2)

            # startupCache
            stats["Cache"] += self._get_dir_size(os.path.join(profile, "startupCache"))

    # ──────────────────────────────────────────────────────────────────
    # Utility
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_file_size(path: str) -> int:
        try:
            return os.path.getsize(path) if os.path.isfile(path) else 0
        except OSError:
            return 0

    @staticmethod
    def _get_dir_size(path: str) -> int:
        total = 0
        if not os.path.isdir(path):
            return 0
        try:
            for root, _dirs, files in os.walk(path):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
        except OSError:
            pass
        return total

    @staticmethod
    def _safe_delete(path: str):
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass

    @staticmethod
    def _safe_delete_dir(path: str):
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)

    def _clean_directory_contents(self, path: str) -> int:
        """Remove all files inside a directory, return bytes freed."""
        freed = 0
        if not os.path.isdir(path):
            return 0
        for root, dirs, files in os.walk(path, topdown=False):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    freed += os.path.getsize(fp)
                    os.remove(fp)
                except OSError:
                    pass
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except OSError:
                    pass
        return freed
