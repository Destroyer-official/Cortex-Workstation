"""Duplicate folder finder for Cortex Cleaner."""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from cortex_unified.core.utils import normalize_path
from cortex_unified.core.config import Config

class DuplicateFolderFinder:
    """Finder for duplicate folders with identical content."""
    
    def __init__(self, config: Config = None, root_path: str = "."):
        """Initialize duplicate folder finder."""
        self.config = config or Config()
        self.root_path = normalize_path(root_path)
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)
        self.follow_symlinks = self.config.follow_symlinks
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Results
        self.duplicate_folders: Dict[str, List[Path]] = {}
        self.folder_count = 0
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
    
    def _get_folder_hash(self, folderpath: Path) -> str:
        """Calculate a hash representing the content of a folder."""
        try:
            # Get all files in the folder recursively
            file_hashes = []
            
            for root, dirs, files in os.walk(folderpath):
                # Remove excluded directories
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                
                root_path = Path(root)
                if self._should_exclude_path(root_path):
                    dirs[:] = []  # Don't recurse into this directory
                    continue
                
                # Sort files for consistent ordering
                files.sort()
                
                for file in files:
                    filepath = root_path / file
                    if self._should_exclude_path(filepath):
                        continue
                    
                    try:
                        # Calculate hash of file content
                        hash_obj = hashlib.md5()
                        with open(filepath, 'rb') as f:
                            # Read file in chunks for memory efficiency
                            for chunk in iter(lambda: f.read(8192), b""):
                                hash_obj.update(chunk)
                        
                        # Store relative path and file hash
                        rel_path = filepath.relative_to(folderpath)
                        file_hashes.append((str(rel_path), hash_obj.hexdigest()))
                    except Exception:
                        continue
            
            # Sort file hashes for consistent ordering
            file_hashes.sort()
            
            # Create a hash of all file hashes
            folder_hash = hashlib.md5()
            for rel_path, file_hash in file_hashes:
                folder_hash.update(rel_path.encode('utf-8'))
                folder_hash.update(file_hash.encode('utf-8'))
            
            return folder_hash.hexdigest()
        except Exception:
            # If we can't read the folder, return None
            return None
    
    def find_duplicate_folders(self, threads: int = 0, progress=None,
                               cancel_event=None) -> Dict[str, List[Path]]:
        """Find folders with identical content.
        
        Args:
            threads: Number of threads to use (0 = auto)
            progress: Optional callable(str) invoked with live status text.
            cancel_event: Optional threading.Event; if set, the scan stops early.
        """
        if threads <= 0:
            threads = min(32, os.cpu_count() + 4)

        def _cancelled() -> bool:
            return cancel_event is not None and cancel_event.is_set()

        def _emit(text: str) -> None:
            if progress is not None:
                try:
                    progress(text)
                except Exception:
                    pass

        # First pass: collect all folders
        folders = []
        try:
            for root, dirs, files in os.walk(self.root_path):
                if _cancelled():
                    break
                # Remove excluded directories
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                
                root_path = Path(root)
                if self._should_exclude_path(root_path):
                    dirs[:] = []  # Don't recurse into this directory
                    continue
                
                # Add this folder to our list
                folders.append(root_path)
                
                with self._lock:
                    self.folder_count += 1
                if self.folder_count % 200 == 0:
                    _emit(f"Indexing folders: {self.folder_count:,}\u2026")
        except Exception:
            with self._lock:
                self.error_count += 1

        if _cancelled():
            self.duplicate_folders = {}
            return {}

        # Second pass: calculate hashes for folders
        hash_map: Dict[str, List[Path]] = {}
        total = len(folders)
        done = 0

        # Use ThreadPoolExecutor for parallel hashing
        with ThreadPoolExecutor(max_workers=threads) as executor:
            # Submit hash calculation tasks
            future_to_folder = {}
            
            for folderpath in folders:
                future = executor.submit(self._get_folder_hash, folderpath)
                future_to_folder[future] = folderpath
            
            # Collect results
            for future in as_completed(future_to_folder):
                folderpath = future_to_folder[future]
                done += 1
                if done % 100 == 0:
                    _emit(f"Hashing folders: {done:,}/{total:,}\u2026")
                    if _cancelled():
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                try:
                    folder_hash = future.result()
                    if folder_hash:
                        if folder_hash not in hash_map:
                            hash_map[folder_hash] = []
                        hash_map[folder_hash].append(folderpath)
                except Exception:
                    with self._lock:
                        self.error_count += 1
        
        # Only keep groups with more than one folder (actual duplicates)
        self.duplicate_folders = {hash_val: paths for hash_val, paths in hash_map.items() if len(paths) > 1}
        return self.duplicate_folders
    
    def get_stats(self) -> dict:
        """Get statistics about the duplicate folder finding process."""
        duplicate_count = sum(len(paths) for paths in self.duplicate_folders.values())
        unique_folders = len(self.duplicate_folders)
        
        return {
            "total_folders_scanned": self.folder_count,
            "duplicate_groups": unique_folders,
            "total_duplicates": duplicate_count,
            "errors": self.error_count
        }
    
    def auto_select_folders(self, strategy: str = "keep_first") -> List[Path]:
        """Automatically select duplicate folders to delete based on strategy.
        
        Args:
            strategy: One of "keep_first", "keep_last", "keep_shortest_path", "keep_longest_path"
        """
        folders_to_delete = []
        
        for hash_val, paths in self.duplicate_folders.items():
            if len(paths) <= 1:
                continue
            
            # Sort paths based on strategy
            if strategy == "keep_first":
                # Keep the first one, mark others for deletion
                folders_to_delete.extend(paths[1:])
            elif strategy == "keep_last":
                # Keep the last one, mark others for deletion
                folders_to_delete.extend(paths[:-1])
            elif strategy == "keep_shortest_path":
                # Sort by path length, shortest first
                sorted_paths = sorted(paths, key=lambda p: len(str(p)))
                # Keep the first (shortest), mark others for deletion
                folders_to_delete.extend(sorted_paths[1:])
            elif strategy == "keep_longest_path":
                # Sort by path length, longest first
                sorted_paths = sorted(paths, key=lambda p: len(str(p)), reverse=True)
                # Keep the first (longest), mark others for deletion
                folders_to_delete.extend(sorted_paths[1:])
            else:
                # Default: keep the first one, mark others for deletion
                folders_to_delete.extend(paths[1:])
        
        return folders_to_delete