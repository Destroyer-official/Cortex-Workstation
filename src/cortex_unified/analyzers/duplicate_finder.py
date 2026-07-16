"""Duplicate file finder for Cortex Cleaner."""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from cortex_unified.core.utils import normalize_path
from cortex_unified.core.config import Config

# Try to import xxhash (10x faster than MD5)
try:
    import xxhash
    HAS_XXHASH = True
except ImportError:
    HAS_XXHASH = False

class DuplicateFinder:
    """Finder for duplicate files using hash-based detection."""
    
    def __init__(self, config: Config = None, root_path: str = "."):
        """Initialize duplicate finder."""
        self.config = config or Config()
        self.root_path = normalize_path(root_path)
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)
        self.follow_symlinks = self.config.follow_symlinks
        self.chunk_size = 8192  # Read files in 8KB chunks for hashing
        
        # Use xxHash if available (10x faster), fallback to BLAKE2b (2.5x faster than MD5)
        if HAS_XXHASH:
            self.hash_algorithm = "xxhash"
        else:
            self.hash_algorithm = "blake2b"  # Built-in, faster than MD5
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Results
        self.duplicates: Dict[str, List[Path]] = {}
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
    
    def _get_file_hash(self, filepath: Path) -> Optional[str]:
        """Calculate hash of a file using fast algorithm with optimizations.
        
        For small files (<1MB), hashes the entire file.
        For large files (>1MB), uses partial hashing for speed.
        """
        try:
            file_size = filepath.stat().st_size
            
            # For very small files (<1KB), hash entire file at once
            if file_size < 1024:
                with open(filepath, 'rb') as f:
                    data = f.read()
                    if HAS_XXHASH:
                        return xxhash.xxh3_64(data).hexdigest()
                    else:
                        return hashlib.blake2b(data).hexdigest()
            
            # For small files (<1MB), hash entire file in chunks
            if file_size < 1_000_000:
                if HAS_XXHASH:
                    hash_obj = xxhash.xxh3_64()
                else:
                    hash_obj = hashlib.blake2b()
                
                with open(filepath, 'rb') as f:
                    for chunk in iter(lambda: f.read(self.chunk_size), b""):
                        hash_obj.update(chunk)
                return hash_obj.hexdigest()
            
            # For large files (>1MB), use partial hashing for speed
            # Hash: first 64KB + middle 64KB + last 64KB + file size
            if HAS_XXHASH:
                hash_obj = xxhash.xxh3_64()
            else:
                hash_obj = hashlib.blake2b()
            
            # Include file size in hash to differentiate files quickly
            hash_obj.update(str(file_size).encode())
            
            with open(filepath, 'rb') as f:
                # Hash first 64KB
                hash_obj.update(f.read(65536))
                
                # Hash middle 64KB
                f.seek(file_size // 2)
                hash_obj.update(f.read(65536))
                
                # Hash last 64KB
                f.seek(max(0, file_size - 65536))
                hash_obj.update(f.read(65536))
            
            return hash_obj.hexdigest()
            
        except Exception:
            # If we can't read the file, return None
            with self._lock:
                self.error_count += 1
            return None
    
    def _get_file_size(self, filepath: Path) -> int:
        """Get file size in bytes."""
        try:
            return filepath.stat().st_size
        except Exception:
            return -1
    
    def _find_files_by_size(self) -> Dict[int, List[Path]]:
        """First pass: group files by size to identify potential duplicates."""
        size_map: Dict[int, List[Path]] = {}
        
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
                        
                        # Group files by size
                        if size not in size_map:
                            size_map[size] = []
                        size_map[size].append(filepath)
                        
                        with self._lock:
                            self.file_count += 1
                    except Exception:
                        with self._lock:
                            self.error_count += 1
                        continue
        except Exception:
            pass
        
        # Only keep groups with more than one file (potential duplicates)
        return {size: paths for size, paths in size_map.items() if len(paths) > 1}
    
    def find_duplicates(self, threads: int = 0) -> Dict[str, List[Path]]:
        """Find duplicate files using hash-based detection."""
        if threads <= 0:
            threads = min(32, os.cpu_count() + 4)
        
        # First pass: group files by size
        size_groups = self._find_files_by_size()
        
        # Second pass: calculate hashes for files with same size
        hash_map: Dict[str, List[Path]] = {}
        
        # Use ThreadPoolExecutor for parallel hashing
        with ThreadPoolExecutor(max_workers=threads) as executor:
            # Submit hash calculation tasks
            future_to_file = {}
            
            for size, files in size_groups.items():
                for filepath in files:
                    future = executor.submit(self._get_file_hash, filepath)
                    future_to_file[future] = filepath
            
            # Collect results
            for future in as_completed(future_to_file):
                filepath = future_to_file[future]
                try:
                    file_hash = future.result()
                    if file_hash:
                        if file_hash not in hash_map:
                            hash_map[file_hash] = []
                        hash_map[file_hash].append(filepath)
                except Exception:
                    with self._lock:
                        self.error_count += 1
        
        # Only keep groups with more than one file (actual duplicates)
        self.duplicates = {hash_val: paths for hash_val, paths in hash_map.items() if len(paths) > 1}
        return self.duplicates
    
    def get_stats(self) -> dict:
        """Get statistics about the duplicate finding process."""
        duplicate_count = sum(len(paths) for paths in self.duplicates.values())
        unique_files = len(self.duplicates)
        
        return {
            "total_files_scanned": self.file_count,
            "duplicate_groups": unique_files,
            "total_duplicates": duplicate_count,
            "errors": self.error_count,
            "bytes_saved_if_deleted": self._calculate_potential_savings()
        }
    
    def _calculate_potential_savings(self) -> int:
        """Calculate potential bytes that could be saved by removing duplicates."""
        total_savings = 0
        for paths in self.duplicates.values():
            if paths:
                try:
                    # Size of one file * (number of duplicates - 1)
                    size = self._get_file_size(paths[0])
                    total_savings += size * (len(paths) - 1)
                except Exception:
                    continue
        return total_savings
    
    def auto_select_duplicates(self, strategy: str = "keep_newest") -> List[Path]:
        """Automatically select duplicates to delete based on strategy.
        
        Args:
            strategy: One of "keep_newest", "keep_oldest", "keep_largest", "keep_smallest"
        """
        files_to_delete = []
        
        for hash_val, paths in self.duplicates.items():
            if len(paths) <= 1:
                continue
            
            # Sort paths based on strategy
            if strategy == "keep_newest":
                # Sort by modification time, newest first
                sorted_paths = sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)
                # Keep the first (newest), mark others for deletion
                files_to_delete.extend(sorted_paths[1:])
            elif strategy == "keep_oldest":
                # Sort by modification time, oldest first
                sorted_paths = sorted(paths, key=lambda p: p.stat().st_mtime)
                # Keep the first (oldest), mark others for deletion
                files_to_delete.extend(sorted_paths[1:])
            elif strategy == "keep_largest":
                # Sort by file size, largest first
                sorted_paths = sorted(paths, key=lambda p: p.stat().st_size, reverse=True)
                # Keep the first (largest), mark others for deletion
                files_to_delete.extend(sorted_paths[1:])
            elif strategy == "keep_smallest":
                # Sort by file size, smallest first
                sorted_paths = sorted(paths, key=lambda p: p.stat().st_size)
                # Keep the first (smallest), mark others for deletion
                files_to_delete.extend(sorted_paths[1:])
            else:
                # Default: keep the first one, mark others for deletion
                files_to_delete.extend(paths[1:])
        
        return files_to_delete
    
    def _format_bytes(self, size: int) -> str:
        """Format bytes to human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
    
    def get_hash_algorithm_info(self) -> dict:
        """Get information about the current hash algorithm."""
        return {
            "algorithm": self.hash_algorithm,
            "xxhash_available": HAS_XXHASH,
            "performance": "10x faster than MD5" if HAS_XXHASH else "2.5x faster than MD5",
            "recommendation": "Install xxhash for best performance: pip install xxhash" if not HAS_XXHASH else "Using optimal hash algorithm"
        }