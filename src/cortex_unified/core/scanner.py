"""File and directory scanning functionality for Cortex Cleaner."""

import os
import sys
from pathlib import Path
from typing import List, Set, Generator, Tuple, Optional
import concurrent.futures
from threading import Lock

from cortex_unified.core.utils import is_system_directory, get_file_age_days
from cortex_unified.core.config import Config
from cortex_unified.performance import ScanManager, ResourceThrottler

class Scanner:
    """Scanner for finding empty files and directories."""
    
    def __init__(self, config: Config = None, root_path: str = ".", 
                 enable_checkpoints: bool = False, enable_throttling: bool = False):
        """Initialize scanner."""
        self.config = config or Config()
        self.root_path = Path(root_path).resolve()
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)
        self.min_age_days = self.config.min_age_days
        self.follow_symlinks = self.config.follow_symlinks
        
        # Thread safety
        self._lock = Lock()
        
        # Results
        self.empty_files: List[Path] = []
        self.empty_dirs: List[Path] = []
        
        # Performance enhancements
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
        """Check if a path should be excluded based on patterns and system directories."""
        # Check system directories
        if is_system_directory(path):
            return True
        
        # Check exclude patterns using the enhanced method
        return self.config.matches_exclude_patterns(str(path))
    
    def _is_file_empty(self, filepath: Path) -> bool:
        """Check if a file is empty."""
        try:
            return filepath.stat().st_size == 0
        except (OSError, FileNotFoundError):
            return False
    
    def _is_file_old_enough(self, filepath: Path) -> bool:
        """Check if a file is old enough based on min_age_days setting."""
        if self.min_age_days <= 0:
            return True
        
        try:
            file_age = get_file_age_days(filepath)
            return file_age >= self.min_age_days
        except (OSError, ValueError):
            # If we can't determine the age, include it
            return True
    
    def _scan_file(self, filepath: Path) -> bool:
        """Scan a single file and determine if it should be deleted."""
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
        
        # Use iterative BFS with a queue to avoid recursion
        from collections import deque
        
        # Queue contains: (path, depth, parent_info)
        queue = deque([(dirpath, 0, None)])
        
        # Track results for each directory
        dir_results = {}  # path -> (is_empty, has_content, empty_files, empty_subdirs)
        
        # Process queue in BFS order (breadth-first)
        while queue:
            current_path, depth, parent = queue.popleft()
            
            # Check depth limit
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
                # Can't read directory, mark as non-empty
                dir_results[current_path] = (False, True, [], [])
                continue
            
            # Check if directory is empty
            if not entries:
                dir_results[current_path] = (True, False, [], [])
                continue
            
            # Scan entries
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
                        # Add subdirectory to queue for processing
                        subdirs_to_process.append(entry)
                        queue.append((entry, depth + 1, current_path))
                except (OSError, PermissionError):
                    continue
            
            # Store preliminary results (will be updated after subdirs are processed)
            dir_results[current_path] = (
                not has_non_excluded_content and len(subdirs_to_process) == 0,
                has_non_excluded_content,
                empty_files,
                empty_subdirs,
                subdirs_to_process
            )
        
        # Second pass: aggregate results from children to parents (bottom-up)
        # Process in reverse order (deepest first)
        processed_paths = sorted(dir_results.keys(), key=lambda p: len(p.parts), reverse=True)
        
        final_results = {}
        for path in processed_paths:
            result = dir_results[path]
            
            if len(result) == 5:  # Has subdirs to process
                is_empty_prelim, has_content, empty_files, empty_subdirs, subdirs = result
                
                # Check subdirectory results
                for subdir in subdirs:
                    if subdir in final_results:
                        sub_is_empty, sub_files, sub_dirs = final_results[subdir]
                        
                        if sub_is_empty:
                            empty_subdirs.append(subdir.resolve())
                        else:
                            has_content = True
                        
                        # Aggregate files and dirs from subdirectories
                        empty_files.extend(sub_files)
                        empty_subdirs.extend(sub_dirs)
                
                # Final determination
                is_empty = not has_content and len(empty_subdirs) == 0
                final_results[path] = (is_empty, empty_files, empty_subdirs)
            else:
                # No subdirs, use preliminary result
                is_empty, has_content, empty_files, empty_subdirs = result
                final_results[path] = (is_empty, empty_files, empty_subdirs)
        
        # Return result for the root directory
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
        
        # Apply resource throttling if enabled
        if self._resource_throttler:
            threads = self._resource_throttler.adjust_thread_count(threads)
        
        # Handle checkpoint restoration
        scan_state = {}
        if self._scan_manager and checkpoint_id:
            try:
                scan_state = self._scan_manager.load_checkpoint(checkpoint_id)
                # Restore previous results if available
                if 'empty_files' in scan_state:
                    self.empty_files = [Path(p) for p in scan_state['empty_files']]
                if 'empty_dirs' in scan_state:
                    self.empty_dirs = [Path(p) for p in scan_state['empty_dirs']]
            except Exception:
                # If checkpoint loading fails, start fresh
                scan_state = {}
        
        # Start scan tracking
        if self._scan_manager:
            # Estimate total items (rough approximation)
            total_items = self._estimate_total_items()
            self._scan_manager.start_scan(total_items)
        
        try:
            # Perform the scan with enhanced features
            is_root_empty, empty_files, empty_dirs = self._scan_directory_enhanced(
                self.root_path, scan_state
            )
            
            # If the root directory is empty, add it to the list
            if is_root_empty:
                empty_dirs.append(self.root_path.resolve())
            
            # Resolve all paths to ensure consistency
            self.empty_files = [f.resolve() for f in empty_files]
            self.empty_dirs = [d.resolve() for d in empty_dirs]
            
            # Create final checkpoint if enabled
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
            # Handle interruption gracefully
            if self._scan_manager:
                # Create checkpoint before stopping
                interrupted_state = {
                    'empty_files': [str(f) for f in self.empty_files],
                    'empty_dirs': [str(d) for d in self.empty_dirs],
                    'interrupted': True
                }
                checkpoint_id = self._scan_manager.create_checkpoint(interrupted_state)
                print(f"Scan interrupted. Checkpoint saved: {checkpoint_id}")
                self._scan_manager.stop_scan()
            raise
        finally:
            # Clean up resources
            if self._resource_throttler:
                self._resource_throttler.stop_monitoring()
    
    def _estimate_total_items(self) -> int:
        """Estimate total number of items to scan."""
        try:
            # Quick directory count estimation
            count = 0
            for root, dirs, files in os.walk(self.root_path):
                if count > 10000:  # Cap estimation to avoid long delays
                    break
                count += len(dirs) + len(files)
                if count > 1000:  # Early exit for large directories
                    return count * 10  # Rough extrapolation
            return count
        except Exception:
            return 1000  # Default estimate
    
    def _scan_directory_enhanced(self, dirpath: Path, scan_state: dict) -> Tuple[bool, List[Path], List[Path]]:
        """Enhanced directory scanning with checkpoint and throttling support."""
        if self._should_exclude_path(dirpath):
            return False, [], []
        
        # Check for pause/resume
        if self._scan_manager:
            self._scan_manager.wait_if_paused()
            self._scan_manager.update_progress(str(dirpath))
        
        # Apply throttling if needed
        if self._resource_throttler:
            self._resource_throttler.throttle_if_needed()
        
        empty_files = []
        empty_subdirs = []
        
        try:
            entries = list(dirpath.iterdir())
        except (OSError, PermissionError):
            # Can't read directory, skip it
            return False, [], []
        
        # Check if directory is empty
        if not entries:
            return True, [], []
        
        # Scan all entries
        has_non_excluded_content = False
        for entry in entries:
            try:
                # Check for pause/resume
                if self._scan_manager:
                    self._scan_manager.wait_if_paused()
                
                if entry.is_symlink() and not self.follow_symlinks:
                    continue
                
                if entry.is_file():
                    if self._scan_file(entry):
                        empty_files.append(entry.resolve())
                        # Empty files don't count as non-excluded content
                    else:
                        # Non-empty file counts as non-excluded content
                        has_non_excluded_content = True
                elif entry.is_dir():
                    is_empty, sub_files, sub_dirs = self._scan_directory_enhanced(entry, scan_state)
                    if is_empty:
                        empty_subdirs.append(entry.resolve())
                    else:
                        # Non-empty directory counts as non-excluded content
                        has_non_excluded_content = True
                    # Resolve paths for consistency
                    empty_files.extend([f.resolve() for f in sub_files])
                    empty_subdirs.extend([d.resolve() for d in sub_dirs])
            except (OSError, PermissionError):
                # Can't access entry, skip it
                continue
        
        # A directory is considered empty if it has no non-excluded content
        return not has_non_excluded_content, empty_files, empty_subdirs
    
    def pause_scan(self) -> None:
        """Pause the current scan operation."""
        if self._scan_manager:
            self._scan_manager.pause_scan()
    
    def resume_scan(self, checkpoint_id: Optional[str] = None) -> None:
        """Resume the scan operation."""
        if self._scan_manager:
            self._scan_manager.resume_scan(checkpoint_id)
    
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