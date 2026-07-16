"""Cache/log cleaner for Cortex Cleaner."""

import os
import sys
from pathlib import Path
from typing import List, Dict, Set
import platform

from cortex_unified.core.utils import normalize_path
from cortex_unified.core.config import Config

class CacheCleaner:
    """Cleaner for application caches and log files."""
    
    def __init__(self, config: Config = None):
        """Initialize cache cleaner."""
        self.config = config or Config()
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)
        
        # Platform-specific cache directories
        self.cache_paths = self._get_platform_cache_paths()
        
        # Common cache/log patterns and directories
        self.cache_patterns = {
            # Browser caches
            "Chrome", "chrome", "Chromium", "chromium",
            "Firefox", "firefox", "Mozilla", "mozilla",
            "Safari", "safari", "Opera", "opera",
            "Edge", "edge", "Brave", "brave",
            # IDE caches
            ".vscode", "Code", "code", "JetBrains", "jetbrains",
            "AndroidStudio", "android-studio", "IntelliJ", "intellij",
            "PyCharm", "pycharm", "WebStorm", "webstorm",
            # Game caches
            "Steam", "steam", "Origin", "origin",
            "Epic", "epic", "Uplay", "uplay",
            # General cache directories
            "Cache", "cache", "Caches", "caches",
            "Logs", "logs", "Log", "log",
            ".cache", ".logs",
        }
        
        self.cache_file_patterns = {
            # Log files
            "*.log", "*.log.*", "log.*", "logs.*",
            "*.out", "*.err", "*.trace",
            # Cache files
            "*.cache", "*.tmp", "*.temp",
            "*.idx", "*.db", "*.sqlite", "*.sqlite3",
            # Build artifacts
            "*.o", "*.obj", "*.class", "*.pyc", "*.pyo",
            "*.so", "*.dll", "*.dylib", "*.exe",
            # Package manager caches
            "*.whl", "*.tar.gz", "*.zip",
        }
        
        # Results
        self.found_files: List[Path] = []
        self.found_dirs: List[Path] = []
        self.error_count = 0
    
    def _get_platform_cache_paths(self) -> List[Path]:
        """Get platform-specific cache directories."""
        paths = []
        
        # User home directory
        home = Path.home()
        paths.append(home)
        
        # Platform-specific paths
        system = platform.system().lower()
        if system == "windows":
            # Windows-specific cache paths
            if "LOCALAPPDATA" in os.environ:
                paths.append(normalize_path(os.environ["LOCALAPPDATA"]))
            if "APPDATA" in os.environ:
                paths.append(normalize_path(os.environ["APPDATA"]))
            if "PROGRAMDATA" in os.environ:
                paths.append(normalize_path(os.environ["PROGRAMDATA"]))
        elif system == "darwin":  # macOS
            paths.append(normalize_path("~/Library"))
            paths.append(normalize_path("~/Library/Caches"))
            paths.append(normalize_path("~/Library/Logs"))
        elif system == "linux":
            paths.append(normalize_path("~/.cache"))
            paths.append(normalize_path("~/.local/share"))
            paths.append(normalize_path("/var/log"))
            paths.append(normalize_path("/var/cache"))
        
        # Remove duplicates and non-existent paths
        unique_paths = []
        for path in paths:
            try:
                if path.exists() and path not in unique_paths:
                    unique_paths.append(path)
            except Exception:
                continue
        
        return unique_paths
    
    def _should_exclude_path(self, path: Path) -> bool:
        """Check if a path should be excluded based on patterns."""
        # Check exclude directories by name
        if path.name in self.exclude_dirs:
            return True
        
        # Check exclude patterns
        path_str = str(path)
        for pattern in self.exclude_patterns:
            if pattern in path_str or pattern in path.name:
                return True
        
        return False
    
    def _is_cache_directory(self, path: Path) -> bool:
        """Check if a directory is likely a cache directory."""
        # Check against cache directory patterns
        for pattern in self.cache_patterns:
            if pattern.lower() in path.name.lower():
                return True
        
        return False
    
    def _is_cache_file(self, path: Path) -> bool:
        """Check if a file is likely a cache or log file."""
        from fnmatch import fnmatch
        
        # Check against cache file patterns
        for pattern in self.cache_file_patterns:
            if fnmatch(path.name, pattern):
                return True
        
        return False
    
    def find_cache_files(self, custom_paths: List[str] = None) -> tuple[List[Path], List[Path]]:
        """Find cache and log files.
        
        Args:
            custom_paths: Optional list of custom paths to scan instead of default cache paths
            
        Returns:
            Tuple of (files, directories) that are cache/log related
        """
        self.found_files = []
        self.found_dirs = []
        self.error_count = 0
        
        # Determine paths to scan
        if custom_paths:
            scan_paths = [normalize_path(p) for p in custom_paths]
        else:
            scan_paths = self.cache_paths
        
        # Scan each path
        for cache_path in scan_paths:
            try:
                if not cache_path.exists():
                    continue
                
                # Walk through directory
                for root, dirs, files in os.walk(cache_path):
                    # Remove excluded directories
                    dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                    
                    root_path = Path(root)
                    if self._should_exclude_path(root_path):
                        dirs[:] = []  # Don't recurse into this directory
                        continue
                    
                    # Check if this directory is a cache directory
                    if self._is_cache_directory(root_path):
                        # Add all files and subdirectories in this cache directory
                        for file in files:
                            filepath = root_path / file
                            if not self._should_exclude_path(filepath):
                                self.found_files.append(filepath)
                        
                        # Add subdirectories
                        for dir_name in dirs:
                            dirpath = root_path / dir_name
                            if not self._should_exclude_path(dirpath):
                                self.found_dirs.append(dirpath)
                        
                        # Don't recurse further into cache directories
                        dirs[:] = []
                        continue
                    
                    # Check individual files
                    for file in files:
                        filepath = root_path / file
                        if self._should_exclude_path(filepath):
                            continue
                        
                        # Check if file is cache/log file
                        if self._is_cache_file(filepath):
                            self.found_files.append(filepath)
            except Exception:
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
            "errors": self.error_count
        }
    
    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes into human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"
    
    def get_cache_directories(self) -> List[Path]:
        """Get list of cache directories that would be scanned."""
        return self.cache_paths