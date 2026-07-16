"""Large file finder for Cortex Cleaner."""

import os
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from cortex_unified.core.utils import normalize_path
from cortex_unified.core.config import Config

class LargeFileFinder:
    """Finder for large files with configurable size filters."""
    
    def __init__(self, config: Config = None, root_path: str = "."):
        """Initialize large file finder."""
        self.config = config or Config()
        self.root_path = normalize_path(root_path)
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)
        self.follow_symlinks = self.config.follow_symlinks
        self.min_size_mb = 100  # Default minimum size: 100MB
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Results
        self.large_files: List[Tuple[Path, int]] = []  # (filepath, size_bytes)
        self.file_count = 0
        self.error_count = 0
    
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
    
    def _get_file_size(self, filepath: Path) -> int:
        """Get file size in bytes."""
        try:
            return filepath.stat().st_size
        except Exception:
            return -1
    
    def find_large_files(self, min_size_mb: int = None, threads: int = 0) -> List[Tuple[Path, int]]:
        """Find files larger than the specified size threshold.
        
        Args:
            min_size_mb: Minimum file size in MB (defaults to self.min_size_mb)
            threads: Number of threads to use (0 = auto)
        """
        if min_size_mb is None:
            min_size_mb = self.min_size_mb
        
        min_size_bytes = min_size_mb * 1024 * 1024  # Convert MB to bytes
        
        if threads <= 0:
            threads = min(32, os.cpu_count() + 4)
        
        self.large_files = []
        
        try:
            for root, dirs, files in os.walk(self.root_path):
                # Remove excluded directories
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                
                root_path = Path(root)
                if self._should_exclude_path(root_path):
                    dirs[:] = []  # Don't recurse into this directory
                    continue
                
                for file in files:
                    filepath = root_path / file
                    if self._should_exclude_path(filepath):
                        continue
                    
                    try:
                        # Get file size
                        size = self._get_file_size(filepath)
                        if size <= 0:
                            continue
                        
                        with self._lock:
                            self.file_count += 1
                        
                        # Check if file is large enough
                        if size >= min_size_bytes:
                            self.large_files.append((filepath, size))
                    except Exception:
                        with self._lock:
                            self.error_count += 1
                        continue
        except Exception:
            pass
        
        # Sort by size (largest first)
        self.large_files.sort(key=lambda x: x[1], reverse=True)
        return self.large_files
    
    def get_stats(self) -> dict:
        """Get statistics about the large file finding process."""
        total_size = sum(size for _, size in self.large_files)
        
        return {
            "total_files_scanned": self.file_count,
            "large_files_found": len(self.large_files),
            "total_size_bytes": total_size,
            "total_size_human": self._format_bytes(total_size),
            "errors": self.error_count
        }
    
    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes into human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"
    
    def filter_by_size(self, min_size_mb: int, max_size_mb: int = None) -> List[Tuple[Path, int]]:
        """Filter large files by size range.
        
        Args:
            min_size_mb: Minimum file size in MB
            max_size_mb: Maximum file size in MB (optional)
        """
        min_bytes = min_size_mb * 1024 * 1024
        if max_size_mb:
            max_bytes = max_size_mb * 1024 * 1024
            return [(path, size) for path, size in self.large_files 
                   if min_bytes <= size <= max_bytes]
        else:
            return [(path, size) for path, size in self.large_files 
                   if size >= min_bytes]
    
    def group_by_extension(self) -> Dict[str, List[Tuple[Path, int]]]:
        """Group large files by file extension."""
        extension_groups: Dict[str, List[Tuple[Path, int]]] = {}
        
        for path, size in self.large_files:
            ext = path.suffix.lower()
            if ext not in extension_groups:
                extension_groups[ext] = []
            extension_groups[ext].append((path, size))
        
        return extension_groups