"""Content-identical folder detection.

Each folder gets a single content fingerprint: per-file MD5s combined with
their relative paths, order-independent. Two folders match only when every
file matches AND the relative structure matches, so a folder plus a renamed
copy of it still compare equal while reorganized copies do not.
"""

import os
import hashlib
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from cortex_unified.core.utils import normalize_path
from cortex_unified.core.config import Config

class DuplicateFolderFinder:
    """Finds folders whose contents are byte-for-byte identical."""
    
    def __init__(self, config: Config = None, root_path: str = "."):
        """
        Args:
            config: Exclusion rules applied inside each folder hash.
            root_path: Directory tree to search.
        """
        self.config = config or Config()
        self.root_path = normalize_path(root_path)
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)
        self.follow_symlinks = self.config.follow_symlinks
        
        # Folder hashing runs on a thread pool; counters must survive
        # concurrent updates.
        self._lock = threading.Lock()
        
        self.duplicate_folders: Dict[str, List[Path]] = {}
        self.folder_count = 0
        self.error_count = 0
    
    def _should_exclude_path(self, path: Path) -> bool:
        """True when *path* hits an excluded directory name or pattern."""
        if path.name in self.exclude_dirs:
            return True
        
        path_str = str(path)
        for pattern in self.exclude_patterns:
            if pattern in path_str or pattern in path.name:
                return True
        
        return False
    
    def _get_folder_hash(self, folderpath: Path) -> str:
        """Order-independent content fingerprint of *folderpath*.

        Combines each file's relative path with its content hash. Sorting
        the pairs before folding them in makes the result independent of
        filesystem enumeration order, so identical trees hash identically.
        Unreadable files are skipped -- they weaken the fingerprint but
        must not crash the scan.
        """
        try:
            file_hashes = []
            
            for root, dirs, files in os.walk(folderpath):
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                
                root_path = Path(root)
                if self._should_exclude_path(root_path):
                    dirs[:] = []
                    continue
                
                files.sort()
                
                for file in files:
                    filepath = root_path / file
                    if self._should_exclude_path(filepath):
                        continue
                    
                    try:
                        hash_obj = hashlib.md5()
                        with open(filepath, 'rb') as f:
                            for chunk in iter(lambda: f.read(8192), b""):
                                hash_obj.update(chunk)
                        
                        rel_path = filepath.relative_to(folderpath)
                        file_hashes.append((str(rel_path), hash_obj.hexdigest()))
                    except Exception:
                        continue
            
            file_hashes.sort()
            
            folder_hash = hashlib.md5()
            for rel_path, file_hash in file_hashes:
                folder_hash.update(rel_path.encode('utf-8'))
                folder_hash.update(file_hash.encode('utf-8'))
            
            return folder_hash.hexdigest()
        except Exception:
            # An unreadable folder cannot participate; None filters it out.
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
            """_cancelled."""
            """_cancelled."""

        def _emit(text: str) -> None:
            if progress is not None:
                try:
                    progress(text)
                except Exception:
                    pass
            """_emit."""
            """_emit."""

        # Pass 1: index every folder under the root.
        folders = []
        try:
            for root, dirs, files in os.walk(self.root_path):
                if _cancelled():
                    break
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                
                root_path = Path(root)
                if self._should_exclude_path(root_path):
                    dirs[:] = []
                    continue
                
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

        # Pass 2: fingerprint folders in parallel; hashing is I/O-bound so
        # the thread pool keeps disks saturated.
        hash_map: Dict[str, List[Path]] = {}
        total = len(folders)
        done = 0

        with ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_folder = {}
            
            for folderpath in folders:
                future = executor.submit(self._get_folder_hash, folderpath)
                future_to_folder[future] = folderpath
            
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
        """Pick the redundant folder from each duplicate group.

        Args:
            strategy: Which copy to keep -- "keep_first", "keep_last",
                "keep_shortest_path", or "keep_longest_path". All other
                members are returned for deletion.
        """
        folders_to_delete = []
        
        for hash_val, paths in self.duplicate_folders.items():
            if len(paths) <= 1:
                continue
            
            if strategy == "keep_first":
                folders_to_delete.extend(paths[1:])
            elif strategy == "keep_last":
                folders_to_delete.extend(paths[:-1])
            elif strategy == "keep_shortest_path":
                sorted_paths = sorted(paths, key=lambda p: len(str(p)))
                folders_to_delete.extend(sorted_paths[1:])
            elif strategy == "keep_longest_path":
                sorted_paths = sorted(paths, key=lambda p: len(str(p)), reverse=True)
                folders_to_delete.extend(sorted_paths[1:])
            else:
                # Unknown strategy: keep the first entry as-is.
                folders_to_delete.extend(paths[1:])
        
        return folders_to_delete