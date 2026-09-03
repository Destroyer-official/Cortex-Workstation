"""Discovery of empty files and directories under a configured root.

The scanner applies exclusion rules (globs, regexes, system directories)
and an optional minimum-age filter before anything is reported as
deletable. Results feed :class:`~cortex_unified.core.deleter.Deleter`,
which performs the actual removal.
"""

import logging
import os
from pathlib import Path
from typing import List, Tuple, Optional
from threading import Lock

from cortex_unified.core.utils import is_system_directory, get_file_age_days
from cortex_unified.core.config import Config
from cortex_unified.performance import ScanManager, ResourceThrottler

log = logging.getLogger(__name__)

class Scanner:
    """Finds empty files and directories eligible for cleanup.

    Supports checkpointing (pause/resume across runs) and resource
    throttling, both opt-in via constructor flags so plain scans stay
    dependency-free.
    """
    
    def __init__(self, config: Config = None, root_path: str = ".", 
                 enable_checkpoints: bool = False, enable_throttling: bool = False):
        """Create a scanner.

        Args:
            config: Exclusion and age rules; defaults to ``Config()``.
            root_path: Directory tree to scan.
            enable_checkpoints: Track progress so interrupted scans can
                resume instead of restarting.
            enable_throttling: Slow the scan when system resources run low.
        """
        self.config = config or Config()
        self.root_path = Path(root_path).resolve()
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)
        self.min_age_days = self.config.min_age_days
        self.follow_symlinks = self.config.follow_symlinks
        
        # Result lists are appended from scan callbacks; guard mutations.
        self._lock = Lock()
        
        self.empty_files: List[Path] = []
        self.empty_dirs: List[Path] = []
        
        self.enable_checkpoints = enable_checkpoints
        self.enable_throttling = enable_throttling
        self._scan_manager: Optional[ScanManager] = None
        self._resource_throttler: Optional[ResourceThrottler] = None
        
        if enable_checkpoints:
            self._scan_manager = ScanManager(config)
        
        if enable_throttling:
            self._resource_throttler = ResourceThrottler()
            self._resource_throttler.start_monitoring()
    
    def _should_exclude_path(self, path: Path) -> bool:
        """True when *path* hits a system directory or a configured pattern."""
        if is_system_directory(path):
            return True
        return self.config.matches_exclude_patterns(str(path))
    
    def _is_file_empty(self, filepath: Path) -> bool:
        """True when *filepath* has zero bytes.

        Unreadable files count as NOT empty -- failing stat() must never
        cause a file we know nothing about to be deleted.
        """
        try:
            return filepath.stat().st_size == 0
        except (OSError, FileNotFoundError):
            return False
    
    def _is_file_old_enough(self, filepath: Path) -> bool:
        """Apply the ``min_age_days`` rule; files younger are skipped."""
        if self.min_age_days <= 0:
            return True
        
        try:
            file_age = get_file_age_days(filepath)
            return file_age >= self.min_age_days
        except (OSError, ValueError):
            # Undeterminable age counts as old enough: deleting an empty
            # file is harmless even if it turns out to be recent.
            return True
    
    def _scan_file(self, filepath: Path) -> bool:
        """True when *filepath* passes every eligibility filter."""
        if self._should_exclude_path(filepath):
            return False
        
        if not self._is_file_empty(filepath):
            return False
        
        if not self._is_file_old_enough(filepath):
            return False
        
        return True
    
    def _scan_directory(self, dirpath: Path, max_depth: int = 1000) -> Tuple[bool, List[Path], List[Path]]:
        """Scan a directory and its contents using iterative BFS to avoid stack overflow.
        
        Args:
            dirpath: Directory to scan
            max_depth: Maximum directory depth to prevent infinite loops (default: 1000)
        
        Returns:
            Tuple of (is_empty, empty_files, empty_subdirs)
        """
        if self._should_exclude_path(dirpath):
            return False, [], []
        
        from collections import deque
        
        # Queue entries: (path, depth, parent path).
        queue = deque([(dirpath, 0, None)])
        
        # First pass: per-directory facts gathered in BFS order.
        # path -> (is_empty_prelim, has_content, empty_files, empty_subdirs, subdirs)
        dir_results = {}
        
        while queue:
            current_path, depth, parent = queue.popleft()
            
            if depth > max_depth:
                import logging
                logging.warning(f"Max depth {max_depth} reached at {current_path}")
                dir_results[current_path] = (False, True, [], [])
                continue
            
            if self._should_exclude_path(current_path):
                dir_results[current_path] = (False, True, [], [])
                continue
            
            try:
                entries = list(current_path.iterdir())
            except (OSError, PermissionError):
                # Unreadable means "not known to be empty" -- never report
                # a directory we could not inspect for deletion.
                dir_results[current_path] = (False, True, [], [])
                continue
            
            if not entries:
                dir_results[current_path] = (True, False, [], [])
                continue
            
            empty_files = []
            empty_subdirs = []
            has_non_excluded_content = False
            subdirs_to_process = []
            
            for entry in entries:
                try:
                    if entry.is_symlink() and not self.follow_symlinks:
                        continue
                    
                    if entry.is_file():
                        if self._scan_file(entry):
                            empty_files.append(entry.resolve())
                        else:
                            has_non_excluded_content = True
                    elif entry.is_dir():
                        subdirs_to_process.append(entry)
                        queue.append((entry, depth + 1, current_path))
                except (OSError, PermissionError):
                    continue
            
            # Preliminary emptiness: children have not been resolved yet,
            # so a directory holding only empty subdirs still looks empty.
            dir_results[current_path] = (
                not has_non_excluded_content and len(subdirs_to_process) == 0,
                has_non_excluded_content,
                empty_files,
                empty_subdirs,
                subdirs_to_process
            )
        
        # Second pass: resolve children before parents so emptiness rolls up
        # bottom-up; sorting by path depth guarantees parents come last.
        processed_paths = sorted(dir_results.keys(), key=lambda p: len(p.parts), reverse=True)
        
        final_results = {}
        for path in processed_paths:
            result = dir_results[path]
            
            if len(result) == 5:  # directory had queued subdirectories
                is_empty_prelim, has_content, empty_files, empty_subdirs, subdirs = result
                
                for subdir in subdirs:
                    if subdir in final_results:
                        sub_is_empty, sub_files, sub_dirs = final_results[subdir]
                        
                        if sub_is_empty:
                            empty_subdirs.append(subdir.resolve())
                        else:
                            has_content = True
                        
                        empty_files.extend(sub_files)
                        empty_subdirs.extend(sub_dirs)
                
                is_empty = not has_content and len(empty_subdirs) == 0
                final_results[path] = (is_empty, empty_files, empty_subdirs)
            else:
                # Leaf directory: the preliminary result is already final.
                is_empty, has_content, empty_files, empty_subdirs = result
                final_results[path] = (is_empty, empty_files, empty_subdirs)
        
        if dirpath in final_results:
            return final_results[dirpath]
        else:
            return False, [], []
    
    def scan(self, threads: int = 0, checkpoint_id: Optional[str] = None, max_depth: int = 1000) -> Tuple[List[Path], List[Path]]:
        """Scan for empty files and directories with optional checkpoint support.
        
        Args:
            threads: Number of threads to use (0 = auto)
            checkpoint_id: Optional checkpoint ID to resume from
            max_depth: Maximum directory depth to prevent stack overflow (default: 1000)
        
        Returns:
            Tuple of (empty_files, empty_dirs)
        """
        if threads <= 0:
            threads = min(32, os.cpu_count() + 4)
        
        if self._resource_throttler:
            threads = self._resource_throttler.adjust_thread_count(threads)
        
        scan_state = {}
        if self._scan_manager and checkpoint_id:
            try:
                scan_state = self._scan_manager.load_checkpoint(checkpoint_id)
                if 'empty_files' in scan_state:
                    self.empty_files = [Path(p) for p in scan_state['empty_files']]
                if 'empty_dirs' in scan_state:
                    self.empty_dirs = [Path(p) for p in scan_state['empty_dirs']]
            except Exception:
                # A corrupt or stale checkpoint must not kill the run;
                # restarting from scratch is always safe.
                scan_state = {}
        
        if self._scan_manager:
            total_items = self._estimate_total_items()
            self._scan_manager.start_scan(total_items)
        
        try:
            is_root_empty, empty_files, empty_dirs = self._scan_directory_enhanced(
                self.root_path, scan_state
            )
            
            if is_root_empty:
                empty_dirs.append(self.root_path.resolve())
            
            self.empty_files = [f.resolve() for f in empty_files]
            self.empty_dirs = [d.resolve() for d in empty_dirs]
            
            if self._scan_manager:
                final_state = {
                    'empty_files': [str(f) for f in self.empty_files],
                    'empty_dirs': [str(d) for d in self.empty_dirs],
                    'completed': True
                }
                self._scan_manager.create_checkpoint(final_state)
                self._scan_manager.stop_scan()
            
            return self.empty_files, self.empty_dirs
            
        except KeyboardInterrupt:
            # Persist partial results so the user can resume instead of
            # losing a long scan to Ctrl+C.
            if self._scan_manager:
                interrupted_state = {
                    'empty_files': [str(f) for f in self.empty_files],
                    'empty_dirs': [str(d) for d in self.empty_dirs],
                    'interrupted': True
                }
                checkpoint_id = self._scan_manager.create_checkpoint(interrupted_state)
                log.warning("Scan interrupted. Checkpoint saved: %s", checkpoint_id)
                self._scan_manager.stop_scan()
            raise
        finally:
            if self._resource_throttler:
                self._resource_throttler.stop_monitoring()
    
    def _estimate_total_items(self) -> int:
        """Rough item count for progress bars; exactness is not required."""
        try:
            count = 0
            for root, dirs, files in os.walk(self.root_path):
                if count > 10000:  # cap the estimation cost itself
                    break
                count += len(dirs) + len(files)
                if count > 1000:
                    # Large tree: extrapolate instead of walking it all.
                    return count * 10
            return count
        except Exception:
            return 1000  # arbitrary but plausible default
    
    def _scan_directory_enhanced(self, dirpath: Path, scan_state: dict, max_depth: int = 20) -> Tuple[bool, List[Path], List[Path]]:
        """Recursive scan with pause/throttle hooks.

        A directory counts as empty when it contains nothing except
        eligible empty files and (recursively) empty subdirectories --
        excluded entries are invisible to the emptiness decision.
        """
        if max_depth <= 0:
            return False, [], []
        
        if self._should_exclude_path(dirpath):
            return False, [], []
        
        if self._scan_manager:
            self._scan_manager.wait_if_paused()
            self._scan_manager.update_progress(str(dirpath))
        
        if self._resource_throttler:
            self._resource_throttler.throttle_if_needed()
        
        empty_files = []
        empty_subdirs = []
        
        try:
            entries = list(dirpath.iterdir())
        except (OSError, PermissionError):
            return False, [], []
        
        if not entries:
            return True, [], []
        
        has_non_excluded_content = False
        for entry in entries:
            try:
                if self._scan_manager:
                    self._scan_manager.wait_if_paused()
                
                if entry.is_symlink() and not self.follow_symlinks:
                    continue
                
                if entry.is_file():
                    if self._scan_file(entry):
                        empty_files.append(entry.resolve())
                    else:
                        has_non_excluded_content = True
                elif entry.is_dir():
                    is_empty, sub_files, sub_dirs = self._scan_directory_enhanced(entry, scan_state, max_depth - 1)
                    if is_empty:
                        empty_subdirs.append(entry.resolve())
                    else:
                        has_non_excluded_content = True
                    empty_files.extend([f.resolve() for f in sub_files])
                    empty_subdirs.extend([d.resolve() for d in sub_dirs])
            except (OSError, PermissionError):
                continue
        
        return not has_non_excluded_content, empty_files, empty_subdirs
    
    def pause_scan(self) -> None:
        """Pause the current scan operation."""
        if self._scan_manager:
            self._scan_manager.pause_scan()
    
    def resume_scan(self, checkpoint_id: Optional[str] = None) -> None:
        if self._scan_manager:
            self._scan_manager.resume_scan(checkpoint_id)
        """resume_scan."""
    
    def get_scan_progress(self):
        """Get current scan progress."""
        if self._scan_manager:
            return self._scan_manager.get_scan_progress()
        return None
    
    def create_checkpoint(self) -> Optional[str]:
        """Create a checkpoint of current scan state."""
        if self._scan_manager:
            scan_state = {
                'empty_files': [str(f) for f in self.empty_files],
                'empty_dirs': [str(d) for d in self.empty_dirs],
                'root_path': str(self.root_path)
            }
            return self._scan_manager.create_checkpoint(scan_state)
        return None
    
    def list_checkpoints(self):
        """List available checkpoints."""
        if self._scan_manager:
            return self._scan_manager.list_checkpoints()
        return []
    
    def get_stats(self) -> dict:
        """Get statistics about the scan."""
        return {
            "empty_files_count": len(self.empty_files),
            "empty_dirs_count": len(self.empty_dirs),
            "total_empty_count": len(self.empty_files) + len(self.empty_dirs),
        }