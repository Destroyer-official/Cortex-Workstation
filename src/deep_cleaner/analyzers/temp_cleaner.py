"""Temporary/junk file cleaner for Deep Cleaner."""

import os
import sys
from pathlib import Path
from typing import List, Set
import platform

from ..utils import normalize_path
from ..config import Config


class TempCleaner:
    """Cleaner for temporary and junk files across platforms."""
    
    def __init__(self, config: Config = None):
        """Initialize temp cleaner."""
        self.config = config or Config()
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)
        
        # Platform-specific temp directories
        self.temp_paths = self._get_platform_temp_paths()
        
        # Common temp/junk file patterns
        self.temp_patterns = {
            # Windows patterns
            "*.tmp", "*.temp", "~*.tmp", "~*.temp",
            "*.log", "*.old", "*.bak", "*.backup",
            "Thumbs.db", "desktop.ini",
            "*.dmp", "*.mdmp",  # Crash dumps
            # General patterns
            "*.swp", "*.swo",  # Vim swap files
            "*~",  # Backup files
            ".DS_Store",  # macOS
            ".Spotlight-V100", ".Trashes",  # macOS
            ".Trash-*",  # Linux
            "lost+found",  # Linux
        }
        
        # Results
        self.found_files: List[Path] = []
        self.error_count = 0
    
    def _get_platform_temp_paths(self) -> List[Path]:
        """Get platform-specific temporary directories."""
        paths = []
        
        # Standard temp directories
        if "TEMP" in os.environ:
            paths.append(normalize_path(os.environ["TEMP"]))
        if "TMP" in os.environ:
            paths.append(normalize_path(os.environ["TMP"]))
        
        # Platform-specific paths
        system = platform.system().lower()
        if system == "windows":
            # Windows-specific temp paths
            if "SystemRoot" in os.environ:
                paths.append(normalize_path(os.path.join(os.environ["SystemRoot"], "Temp")))
            if "LOCALAPPDATA" in os.environ:
                paths.append(normalize_path(os.path.join(os.environ["LOCALAPPDATA"], "Temp")))
            # Prefetch and recent files
            if "SystemRoot" in os.environ:
                paths.append(normalize_path(os.path.join(os.environ["SystemRoot"], "Prefetch")))
        elif system == "darwin":  # macOS
            paths.append(normalize_path("/tmp"))
            paths.append(normalize_path("~/Library/Caches"))
            paths.append(normalize_path("/var/folders"))
        elif system == "linux":
            paths.append(normalize_path("/tmp"))
            paths.append(normalize_path("/var/tmp"))
            paths.append(normalize_path("~/.cache"))
        
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
    
    def _matches_temp_pattern(self, path: Path) -> bool:
        """Check if a file matches any temp/junk pattern."""
        from fnmatch import fnmatch
        
        # Check against temp patterns
        for pattern in self.temp_patterns:
            if fnmatch(path.name, pattern):
                return True
            # Also check full path for some patterns
            if fnmatch(str(path), pattern):
                return True
        
        return False
    
    def find_temp_files(self, custom_paths: List[str] = None) -> List[Path]:
        """Find temporary and junk files.
        
        Args:
            custom_paths: Optional list of custom paths to scan instead of default temp paths
        """
        self.found_files = []
        self.error_count = 0
        
        # Determine paths to scan
        if custom_paths:
            scan_paths = [normalize_path(p) for p in custom_paths]
        else:
            scan_paths = self.temp_paths
        
        # Scan each path
        for temp_path in scan_paths:
            try:
                if not temp_path.exists():
                    continue
                
                # Walk through directory
                for root, dirs, files in os.walk(temp_path):
                    # Remove excluded directories
                    dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                    
                    root_path = Path(root)
                    if self._should_exclude_path(root_path):
                        dirs[:] = []  # Don't recurse into this directory
                        continue
                    
                    # Check files
                    for file in files:
                        filepath = root_path / file
                        if self._should_exclude_path(filepath):
                            continue
                        
                        # Check if file matches temp pattern
                        if self._matches_temp_pattern(filepath):
                            self.found_files.append(filepath)
            except Exception:
                self.error_count += 1
                continue
        
        return self.found_files
    
    def get_stats(self) -> dict:
        """Get statistics about the temp file finding process."""
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
            "temp_files_found": len(self.found_files),
            "total_size_bytes": total_size,
            "total_size_human": self._format_bytes(total_size),
            "temp_paths_scanned": len(self.temp_paths),
            "errors": self.error_count
        }
    
    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes into human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"
    
    def get_temp_directories(self) -> List[Path]:
        """Get list of temp directories that would be scanned."""
        return self.temp_paths