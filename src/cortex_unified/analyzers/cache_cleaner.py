"""Discovery of application caches and log files.

Heuristic name/pattern matching over the well-known per-user cache roots
(browser profiles, IDE state, game launchers). Findings are reported only;
deletion stays with the caller's deleter so safety rules apply in one place.
"""

import os
from pathlib import Path
from typing import List
import platform

from cortex_unified.core.utils import normalize_path
from cortex_unified.core.config import Config


class CacheCleaner:
    """Finds cache/log files and directories under the platform's cache roots."""

    def __init__(self, config: Config = None):
        """
        Args:
            config: Exclusion rules; defaults to ``Config()``.
        """
        self.config = config or Config()
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)

        self.cache_paths = self._get_platform_cache_paths()

        # Directory-name fragments treated as cache markers. Both cases are
        # listed because matching is substring-based and case-folded later,
        # but keeping both makes intent obvious when editing the set.
        self.cache_patterns = {
            # Browser caches
            "Chrome",
            "chrome",
            "Chromium",
            "chromium",
            "Firefox",
            "firefox",
            "Mozilla",
            "mozilla",
            "Safari",
            "safari",
            "Opera",
            "opera",
            "Edge",
            "edge",
            "Brave",
            "brave",
            # IDE caches
            ".vscode",
            "Code",
            "code",
            "JetBrains",
            "jetbrains",
            "AndroidStudio",
            "android-studio",
            "IntelliJ",
            "intellij",
            "PyCharm",
            "pycharm",
            "WebStorm",
            "webstorm",
            # Game caches
            "Steam",
            "steam",
            "Origin",
            "origin",
            "Epic",
            "epic",
            "Uplay",
            "uplay",
            # General cache directories
            "Cache",
            "cache",
            "Caches",
            "caches",
            "Logs",
            "logs",
            "Log",
            "log",
            ".cache",
            ".logs",
        }

        self.cache_file_patterns = {
            # Log files
            "*.log",
            "*.log.*",
            "log.*",
            "logs.*",
            "*.out",
            "*.err",
            "*.trace",
            # Cache files
            "*.cache",
            "*.tmp",
            "*.temp",
            "*.idx",
            "*.db",
            "*.sqlite",
            "*.sqlite3",
            # Build artifacts
            "*.o",
            "*.obj",
            "*.class",
            "*.pyc",
            "*.pyo",
            # Package manager caches
            "*.whl",
            "*.tar.gz",
            "*.zip",
        }

        self.found_files: List[Path] = []
        self.found_dirs: List[Path] = []
        self.error_count = 0

    # Archives to exclude from log sweeper (keep .zip/.tar.gz as used in manual clean)
    ARCHIVE_SUFFIXES = {".zip", ".tar", ".gz", ".tgz", ".rar", ".7z"}

    def _get_platform_cache_paths(self) -> List[Path]:
        """Cache roots for this platform, deduplicated, existing ones only."""
        paths = []

        home = Path.home()
        paths.append(home)

        system = platform.system().lower()
        if system == "windows":
            if "LOCALAPPDATA" in os.environ:
                paths.append(normalize_path(os.environ["LOCALAPPDATA"]))
            if "APPDATA" in os.environ:
                paths.append(normalize_path(os.environ["APPDATA"]))
            if "PROGRAMDATA" in os.environ:
                paths.append(normalize_path(os.environ["PROGRAMDATA"]))
            # Secondary drive code roots - not included by default in auto-scan
            # but kept as known candidates for the UI's "Select D:\\code" shortcut.
            # The sweeper can be pointed at them via custom_paths.
        elif system == "darwin":
            paths.append(normalize_path("~/Library"))
            paths.append(normalize_path("~/Library/Caches"))
            paths.append(normalize_path("~/Library/Logs"))
        elif system == "linux":
            paths.append(normalize_path("~/.cache"))
            paths.append(normalize_path("~/.local/share"))
            paths.append(normalize_path("/var/log"))
            paths.append(normalize_path("/var/cache"))

        unique_paths = []
        for path in paths:
            try:
                if path.exists() and path not in unique_paths:
                    unique_paths.append(path)
            except Exception:
                continue

        return unique_paths

    def get_custom_scan_roots(self) -> List[Path]:
        """Suggest user-selected roots for deeper sweeps.

        Returns existing directories that are safe to offer as shortcuts in the UI
        without forcing a full fixed-drive walk.
        """
        import string

        candidates: List[Path] = []
        # Scan all fixed drives for common project directories
        for letter in string.ascii_uppercase:
            drive = Path(f"{letter}:/")
            try:
                if drive.exists() and drive.is_dir():
                    for name in ("code", "projects", "tmp", "temp"):
                        candidate = drive / name
                        try:
                            if candidate.is_dir() and candidate not in candidates:
                                candidates.append(candidate)
                        except OSError:
                            continue
            except OSError:
                continue
        # Add home directory common locations
        for name in ("code", "Projects"):
            home_candidate = Path.home() / name
            try:
                if home_candidate.is_dir() and home_candidate not in candidates:
                    candidates.append(home_candidate)
            except OSError:
                continue
        return candidates

    def is_archive(self, path: Path) -> bool:
        """True when *path* is a keep-as-backup archive (.zip/.tar.gz)."""
        name = path.name.lower()
        return any(
            name.endswith(suf) for suf in self.ARCHIVE_SUFFIXES
        ) or name.endswith(".tar.gz")

    def _should_exclude_path(self, path: Path) -> bool:
        """True when *path* hits an excluded directory name or pattern."""
        if path.name in self.exclude_dirs:
            return True

        path_str = str(path)
        for pattern in self.exclude_patterns:
            if pattern in path_str or pattern in path.name:
                return True

        return False

    def _is_cache_directory(self, path: Path) -> bool:
        """True when the directory name contains a known cache marker."""
        for pattern in self.cache_patterns:
            if pattern.lower() in path.name.lower():
                return True

        return False

    def _is_cache_file(self, path: Path) -> bool:
        """True when the file name matches a cache/log/build-artifact glob."""
        from fnmatch import fnmatch

        for pattern in self.cache_file_patterns:
            if fnmatch(path.name, pattern):
                return True

        return False

    def find_large_logs(
        self,
        roots: List[str] | List[Path],
        min_size_mb: float = 100.0,
        exclude_archives: bool = True,
        progress_callback=None,
        cancel_event=None,
    ) -> List[tuple[Path, int]]:
        """Find large log/text files across user-selected roots (D:\\code sweeper).

        Args:
            roots: Directories to walk (e.g. ["D:\\code"]).
            min_size_mb: Minimum size to report (manual hits were 7.6GB of >100MB logs).
            exclude_archives: When True, skip .zip/.tar.gz (they are backups, not logs).
            progress_callback: Optional fn(msg, count, bytes).
            cancel_event: Optional threading.Event to abort early.

        Returns:
            List of (path, size) sorted largest-first.
        """
        import fnmatch as _fnm  # local import to avoid cycle

        min_bytes = int(min_size_mb * 1024 * 1024)
        found: List[tuple[Path, int]] = []
        log_patterns = ("*.log", "*.log.*", "*.txt", "*.out", "*.err")

        def _is_log(name: str) -> bool:
            """_is_log."""
            return any(_fnm.fnmatch(name, pat) for pat in log_patterns)
            """_is_log."""
            """_is_log."""

        for root in roots:
            if cancel_event and getattr(cancel_event, "is_set", lambda: False)():
                break
            root_path = Path(root)
            if not root_path.is_dir():
                continue
            try:
                for dirpath, dirnames, filenames in os.walk(root_path):
                    # prune excluded dirs + .git etc.
                    dirnames[:] = [
                        d
                        for d in dirnames
                        if d not in self.exclude_dirs and d != ".git"
                    ]
                    if (
                        cancel_event
                        and getattr(cancel_event, "is_set", lambda: False)()
                    ):
                        break
                    if self._should_exclude_path(Path(dirpath)):
                        dirnames[:] = []
                        continue
                    for fname in filenames:
                        p = Path(dirpath) / fname
                        if self._should_exclude_path(p):
                            continue
                        if exclude_archives and self.is_archive(p):
                            continue
                        if not _is_log(p.name):
                            continue
                        try:
                            sz = p.stat().st_size
                            if sz >= min_bytes:
                                found.append((p, sz))
                                if progress_callback and callable(progress_callback):
                                    progress_callback(
                                        f"Found {p.name} ({self._format_bytes(sz)})",
                                        len(found),
                                        sz,
                                    )
                        except OSError:
                            continue
            except Exception:
                self.error_count += 1
                continue
        found.sort(key=lambda x: x[1], reverse=True)
        return found

    def find_cache_files(
        self, custom_paths: List[str] = None
    ) -> tuple[List[Path], List[Path]]:
        """Find cache and log files.

        Args:
            custom_paths: Optional list of custom paths to scan instead of default cache paths

        Returns:
            Tuple of (files, directories) that are cache/log related
        """
        self.found_files = []
        self.found_dirs = []
        self.error_count = 0

        if custom_paths:
            scan_paths = [normalize_path(p) for p in custom_paths]
        else:
            scan_paths = self.cache_paths

        for cache_path in scan_paths:
            try:
                if not cache_path.exists():
                    continue

                for root, dirs, files in os.walk(cache_path):
                    # Prune excluded directories before descending; mutating
                    # ``dirs`` in place is the documented os.walk pruning idiom.
                    dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

                    root_path = Path(root)
                    if self._should_exclude_path(root_path):
                        dirs[:] = []
                        continue

                    if self._is_cache_directory(root_path):
                        # The whole subtree is cache: take its files and
                        # immediate subdirs, then stop descending (everything
                        # below is already accounted for).
                        for file in files:
                            filepath = root_path / file
                            if not self._should_exclude_path(filepath):
                                self.found_files.append(filepath)

                        for dir_name in dirs:
                            dirpath = root_path / dir_name
                            if not self._should_exclude_path(dirpath):
                                self.found_dirs.append(dirpath)

                        dirs[:] = []
                        continue

                    # Outside a cache directory, only individually matching
                    # files (e.g. stray *.log) are reported.
                    for file in files:
                        filepath = root_path / file
                        if self._should_exclude_path(filepath):
                            continue

                        if self._is_cache_file(filepath):
                            self.found_files.append(filepath)
            except Exception:
                # One unreadable tree must not abort the sweep.
                self.error_count += 1
                continue

        return self.found_files, self.found_dirs

    def get_stats(self) -> dict:
        """Get statistics about the cache file finding process."""
        total_size = 0
        try:
            for filepath in self.found_files:
                try:
                    total_size += filepath.stat().st_size
                except Exception:
                    continue
        except Exception:
            pass

        return {
            "cache_files_found": len(self.found_files),
            "cache_dirs_found": len(self.found_dirs),
            "total_size_bytes": total_size,
            "total_size_human": self._format_bytes(total_size),
            "cache_paths_scanned": len(self.cache_paths),
            "errors": self.error_count,
        }

    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes into human-readable format."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"

    def get_cache_directories(self) -> List[Path]:
        """Get list of cache directories that would be scanned."""
        return self.cache_paths
