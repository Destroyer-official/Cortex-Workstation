"""Detects and removes browser traces (cache, cookies, history, sessions)
for Chrome, Edge, Brave, Opera, Vivaldi, and Firefox, plus Windows-level
privacy artifacts (Recent items, INetCache, jump lists, DNS cache).

Chromium profiles are discovered from disk instead of assuming profile
names, so secondary and guest profiles are covered. Deletion is
best-effort: files locked by a running browser are skipped silently.
"""

import os
import glob
import shutil
import subprocess
import logging
from typing import List, Dict


class PrivacyCleaner:
    """Removes privacy-sensitive browser data and Windows activity traces.

    Every deletion helper swallows OS errors, so a locked or missing file
    never aborts a cleaning pass.
    """

    def __init__(self):
        """Initialize the instance and configure internal state.

        Sets up sub-widgets, event signal connections, and default options.
        """
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
        """Scan all known browsers and return {browser: {category: size_bytes}}.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Returns:
            Dict[str, Dict[str, int]]: Dictionary mapping identifiers to status or values.
        """
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
                # Chromium layout: per-profile dirs (Default, Profile N, ...)
                # live directly under "User Data"
                for profile_dir in self._discover_chromium_profiles(base_path):
                    self._scan_chromium_profile(profile_dir, stats)

            if sum(stats.values()) > 0:
                results[browser] = stats

        return results

    def scan_system_traces(self) -> Dict[str, int]:
        """Return sizes of cleanable Windows system privacy traces.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Returns:
            Dict[str, int]: Dictionary mapping identifiers to status or values.
        """
        traces: Dict[str, int] = {}

        # Shell MRU list: exposes which files were recently opened
        recent = os.path.join(self.appdata, "Microsoft", "Windows", "Recent")
        traces["Recent Documents"] = self._get_dir_size(recent)

        inet = os.path.join(self.local_appdata, "Microsoft", "Windows", "INetCache")
        traces["Internet Cache"] = self._get_dir_size(inet)

        # Jump lists index per-application file access; stored alongside Recent
        jumplists_auto = os.path.join(self.appdata, "Microsoft", "Windows", "Recent", "AutomaticDestinations")
        jumplists_custom = os.path.join(self.appdata, "Microsoft", "Windows", "Recent", "CustomDestinations")
        traces["Jump Lists"] = self._get_dir_size(jumplists_auto) + self._get_dir_size(jumplists_custom)

        return {k: v for k, v in traces.items() if v > 0}

    # ──────────────────────────────────────────────────────────────────
    # Cleaning
    # ──────────────────────────────────────────────────────────────────

    def clean_browser(self, browser: str, items: List[str]) -> bool:
        """Delete selected data categories for one browser.

        Args:
            browser: Key into ``browser_paths`` (e.g. "Chrome").
            items: Subset of {"Cache", "Cookies", "History", "Sessions"}.

        Returns:
            False if any profile could not be fully cleaned.
        """
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

    def clean_system_traces(self, clean_recent: bool = False) -> int:
        """Clean system-level privacy traces, return bytes freed.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

        Args:
            clean_recent (bool): The clean recent parameter.

        Returns:
            int: Result of the operation.
        """
        freed = 0

        if clean_recent:
            recent = os.path.join(self.appdata, "Microsoft", "Windows", "Recent")
            freed += self._clean_directory_contents(recent)

        inet = os.path.join(self.local_appdata, "Microsoft", "Windows", "INetCache")
        if os.path.isdir(inet):
            freed += self._clean_directory_contents(inet)

        # Resolved hostnames linger in the DNS cache; flushdns needs no
        # elevation. 0x08000000 (CREATE_NO_WINDOW) suppresses the console flash.
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
        """Dynamically find Chromium profile directories.

        Manages discover chromium profiles operations and coordinates related state changes for the component.

        Args:
            base_path (str): Filesystem path to the target file or directory.

        Returns:
            List[str]: List of processed items or identifiers.
        """
        profiles: List[str] = []
        if not os.path.isdir(base_path):
            return profiles
        for entry in os.listdir(base_path):
            full = os.path.join(base_path, entry)
            if not os.path.isdir(full):
                continue
            # Regular profiles ("Default", "Profile N") plus the ephemeral
            # guest/system profiles; other dirs are shared component storage
            if entry == "Default" or entry.startswith("Profile "):
                profiles.append(full)
            elif entry in ("Guest Profile", "System Profile"):
                profiles.append(full)
        return profiles

    def _scan_chromium_profile(self, prof_path: str, stats: Dict[str, int]):
        """Accumulate sizes from one Chromium profile.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            prof_path (str): Filesystem path to the target file or directory.
            stats (Dict[str, int]): The stats parameter.
        """
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
        """Delete specified items in one Chromium profile.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

        Args:
            prof_path (str): Filesystem path to the target file or directory.
            items (List[str]): Collection of items or entries to process.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
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
        """_scan_firefox.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            profiles_path (str): Filesystem path to the target file or directory.
            stats (Dict[str, int]): The stats parameter.
        """
        for profile in glob.glob(os.path.join(profiles_path, "*.*")):
            stats["Cookies"] += self._get_file_size(os.path.join(profile, "cookies.sqlite"))
            stats["History"] += self._get_file_size(os.path.join(profile, "places.sqlite"))
            stats["Sessions"] += self._get_file_size(os.path.join(profile, "sessionstore.jsonlz4"))

            # Disk cache spans cache2 (HTTP cache) and startupCache
            # (precompiled script bytecode)
            cache2 = os.path.join(profile, "cache2")
            stats["Cache"] += self._get_dir_size(cache2)

            stats["Cache"] += self._get_dir_size(os.path.join(profile, "startupCache"))

    # ──────────────────────────────────────────────────────────────────
    # Utility
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_file_size(path: str) -> int:
        """_get_file_size.

        Manages get file size operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.

        Returns:
            int: Result of the operation.
        """
        try:
            return os.path.getsize(path) if os.path.isfile(path) else 0
        except OSError:
            return 0

    @staticmethod
    def _get_dir_size(path: str) -> int:
        """_get_dir_size.

        Manages get dir size operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.

        Returns:
            int: Result of the operation.
        """
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
        """Remove a file, ignoring errors (browsers commonly hold locks).

        Manages safe delete operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass

    @staticmethod
    def _safe_delete_dir(path: str):
        """Recursively remove a directory tree, ignoring failures.

        Manages safe delete dir operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)

    def _clean_directory_contents(self, path: str) -> int:
        """Remove all files inside a directory, return bytes freed.

        Walks bottom-up so emptied subdirectories can be pruned too.
        """
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
