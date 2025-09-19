"""Disk space analyzer for Deep Cleaner."""

import os
import sys
import platform
from pathlib import Path
from typing import List, Dict, Tuple
import json

from ..utils import normalize_path
from ..config import Config


class DiskAnalyzer:
    """Analyzer for disk space usage with visualization support."""
    
    def __init__(self, config: Config = None, root_path: str = "."):
        """Initialize disk analyzer."""
        self.config = config or Config()
        self.root_path = normalize_path(root_path)
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)
        
        # Results
        self.disk_usage = {}
        self.directory_tree = {}
        self.file_type_breakdown = {}
        self.largest_directories = []
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
    
    def analyze_disk_usage(self) -> Dict[str, int]:
        """Analyze disk usage for the root path."""
        try:
            if platform.system() == "Windows":
                # Use Windows-specific method
                import shutil
                total, used, free = shutil.disk_usage(self.root_path)
            else:
                # Use POSIX method
                statvfs = os.statvfs(self.root_path)
                total = statvfs.f_frsize * statvfs.f_blocks
                free = statvfs.f_frsize * statvfs.f_bavail
                used = total - free
            
            self.disk_usage = {
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "used_percent": (used / total * 100) if total > 0 else 0,
                "free_percent": (free / total * 100) if total > 0 else 0
            }
        except Exception as e:
            self.error_count += 1
            self.disk_usage = {
                "total_bytes": 0,
                "used_bytes": 0,
                "free_bytes": 0,
                "used_percent": 0,
                "free_percent": 0,
                "error": str(e)
            }
        
        return self.disk_usage
    
    def analyze_directory_tree(self, max_depth: int = 3) -> Dict:
        """Analyze directory tree structure for visualization.
        
        Args:
            max_depth: Maximum depth to analyze (to prevent excessive recursion)
        """
        self.directory_tree = self._analyze_directory_recursive(
            self.root_path, max_depth, 0
        )
        return self.directory_tree
    
    def _analyze_directory_recursive(self, path: Path, max_depth: int, current_depth: int) -> Dict:
        """Recursively analyze directory structure."""
        if current_depth > max_depth or self._should_exclude_path(path):
            return {}
        
        try:
            # Get directory stats
            stat = path.stat()
            dir_info = {
                "name": path.name,
                "path": str(path),
                "size_bytes": 0,
                "file_count": 0,
                "dir_count": 0,
                "children": [],
                "is_file": False
            }
            
            # Process directory contents
            if path.is_dir():
                try:
                    for item in path.iterdir():
                        if self._should_exclude_path(item):
                            continue
                        
                        if item.is_file():
                            try:
                                file_stat = item.stat()
                                dir_info["size_bytes"] += file_stat.st_size
                                dir_info["file_count"] += 1
                            except Exception:
                                self.error_count += 1
                        elif item.is_dir():
                            child_info = self._analyze_directory_recursive(
                                item, max_depth, current_depth + 1
                            )
                            if child_info:
                                dir_info["size_bytes"] += child_info.get("size_bytes", 0)
                                dir_info["file_count"] += child_info.get("file_count", 0)
                                dir_info["dir_count"] += child_info.get("dir_count", 0) + 1
                                dir_info["children"].append(child_info)
                except Exception:
                    self.error_count += 1
            
            return dir_info
        except Exception:
            self.error_count += 1
            return {}
    
    def analyze_file_types(self) -> Dict[str, Dict]:
        """Analyze files by type/extension."""
        self.file_type_breakdown = {}
        
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
                        # Get file extension
                        ext = filepath.suffix.lower() or "no_extension"
                        
                        # Get file size
                        stat = filepath.stat()
                        size = stat.st_size
                        
                        # Update file type breakdown
                        if ext not in self.file_type_breakdown:
                            self.file_type_breakdown[ext] = {
                                "count": 0,
                                "size_bytes": 0
                            }
                        
                        self.file_type_breakdown[ext]["count"] += 1
                        self.file_type_breakdown[ext]["size_bytes"] += size
                    except Exception:
                        self.error_count += 1
                        continue
        except Exception:
            self.error_count += 1
        
        # Sort by size
        self.file_type_breakdown = dict(
            sorted(
                self.file_type_breakdown.items(),
                key=lambda x: x[1]["size_bytes"],
                reverse=True
            )
        )
        
        return self.file_type_breakdown
    
    def find_largest_directories(self, limit: int = 10) -> List[Tuple[Path, int]]:
        """Find the largest directories."""
        dir_sizes = {}
        
        try:
            for root, dirs, files in os.walk(self.root_path):
                # Remove excluded directories
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                
                root_path = Path(root)
                if self._should_exclude_path(root_path):
                    dirs[:] = []  # Don't recurse into this directory
                    continue
                
                # Calculate directory size
                dir_size = 0
                for file in files:
                    filepath = root_path / file
                    if self._should_exclude_path(filepath):
                        continue
                    
                    try:
                        stat = filepath.stat()
                        dir_size += stat.st_size
                    except Exception:
                        self.error_count += 1
                        continue
                
                dir_sizes[root_path] = dir_size
        except Exception:
            self.error_count += 1
        
        # Sort by size and limit results
        sorted_dirs = sorted(dir_sizes.items(), key=lambda x: x[1], reverse=True)
        self.largest_directories = sorted_dirs[:limit]
        
        return self.largest_directories
    
    def get_stats(self) -> dict:
        """Get comprehensive statistics about the disk analysis."""
        # Format disk usage
        disk_info = self.disk_usage.copy()
        if "total_bytes" in disk_info:
            disk_info["total_human"] = self._format_bytes(disk_info["total_bytes"])
            disk_info["used_human"] = self._format_bytes(disk_info["used_bytes"])
            disk_info["free_human"] = self._format_bytes(disk_info["free_bytes"])
        
        # Format file type breakdown
        file_types_info = {}
        for ext, info in self.file_type_breakdown.items():
            file_types_info[ext] = {
                "count": info["count"],
                "size_bytes": info["size_bytes"],
                "size_human": self._format_bytes(info["size_bytes"])
            }
        
        # Format largest directories
        largest_dirs_info = [
            {
                "path": str(path),
                "size_bytes": size,
                "size_human": self._format_bytes(size)
            }
            for path, size in self.largest_directories
        ]
        
        return {
            "disk_usage": disk_info,
            "file_types": file_types_info,
            "largest_directories": largest_dirs_info,
            "errors": self.error_count
        }
    
    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes into human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"
    
    def export_to_json(self, filepath: str) -> bool:
        """Export analysis results to JSON file."""
        try:
            stats = self.get_stats()
            with open(filepath, 'w') as f:
                json.dump(stats, f, indent=2)
            return True
        except Exception:
            return False