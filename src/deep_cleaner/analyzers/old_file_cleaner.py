"""Old/unused files cleaner for Deep Cleaner."""

import os
from pathlib import Path
from typing import List, Tuple
from datetime import datetime, timedelta
import platform

from ..utils import normalize_path, get_file_age_days
from ..config import Config


class OldFileCleaner:
    """Cleaner for old and unused files."""
    
    def __init__(self, config: Config = None, root_path: str = "."):
        """Initialize old file cleaner."""
        self.config = config or Config()
        self.root_path = normalize_path(root_path)
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)
        self.follow_symlinks = self.config.follow_symlinks
        self.min_age_days = 30  # Default: files not accessed in 30 days
        
        # Results
        self.old_files: List[Tuple[Path, int]] = []  # (filepath, age_days)
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
    
    def find_old_files(self, min_age_days: int = None) -> List[Tuple[Path, int]]:
        """Find files that haven't been accessed in the specified number of days.
        
        Args:
            min_age_days: Minimum age in days (defaults to self.min_age_days)
        """
        if min_age_days is None:
            min_age_days = self.min_age_days
        
        self.old_files = []
        self.file_count = 0
        self.error_count = 0
        
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
                        self.file_count += 1
                        
                        # Get file age
                        age_days = get_file_age_days(filepath)
                        if age_days >= min_age_days:
                            self.old_files.append((filepath, age_days))
                    except Exception:
                        self.error_count += 1
                        continue
        except Exception:
            pass
        
        # Sort by age (oldest first)
        self.old_files.sort(key=lambda x: x[1], reverse=True)
        return self.old_files
    
    def get_stats(self) -> dict:
        """Get statistics about the old file finding process."""
        total_size = 0
        try:
            for filepath, _ in self.old_files:
                try:
                    total_size += filepath.stat().st_size
                except Exception:
                    continue
        except Exception:
            pass
        
        if self.old_files:
            oldest_age = self.old_files[0][1]
            newest_age = self.old_files[-1][1]
        else:
            oldest_age = newest_age = 0
        
        return {
            "total_files_scanned": self.file_count,
            "old_files_found": len(self.old_files),
            "total_size_bytes": total_size,
            "total_size_human": self._format_bytes(total_size),
            "oldest_file_age_days": oldest_age,
            "newest_file_age_days": newest_age,
            "errors": self.error_count
        }
    
    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes into human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"
    
    def filter_by_age_range(self, min_days: int, max_days: int = None) -> List[Tuple[Path, int]]:
        """Filter old files by age range.
        
        Args:
            min_days: Minimum age in days
            max_days: Maximum age in days (optional)
        """
        if max_days:
            return [(path, age) for path, age in self.old_files 
                   if min_days <= age <= max_days]
        else:
            return [(path, age) for path, age in self.old_files 
                   if age >= min_days]
    
    def group_by_age(self) -> dict:
        """Group old files by age ranges."""
        groups = {
            "30_days": [],      # 30-59 days
            "60_days": [],      # 60-89 days
            "90_days": [],      # 90-179 days
            "180_days": [],     # 180-364 days
            "1_year": [],       # 1+ years
        }
        
        for path, age in self.old_files:
            if 30 <= age < 60:
                groups["30_days"].append((path, age))
            elif 60 <= age < 90:
                groups["60_days"].append((path, age))
            elif 90 <= age < 180:
                groups["90_days"].append((path, age))
            elif 180 <= age < 365:
                groups["180_days"].append((path, age))
            elif age >= 365:
                groups["1_year"].append((path, age))
        
        return groups