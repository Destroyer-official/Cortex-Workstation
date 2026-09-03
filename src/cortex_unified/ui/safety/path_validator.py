"""Path validation with OS-specific safety rules and symlink protection."""

import os
import sys
import stat
from pathlib import Path
from typing import Set, List, Optional
import logging

from cortex_unified.core.utils import get_system_excludes, DeepCleanerError

class PathValidationError(DeepCleanerError):
    """Exception raised for path validation errors."""
    pass

class PathValidator:
    """Validates file paths for safe operations with OS-specific rules."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize path validator.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self._system_excludes = get_system_excludes()
        self._user_whitelists: Set[str] = set()
        self._additional_blacklists: Set[str] = set()
        
        # OS-specific critical directories
        self._critical_directories = self._get_critical_directories()
        
    def _get_critical_directories(self) -> Set[str]:
        """Get OS-specific critical directories that should never be deleted."""
        if sys.platform.startswith("win"):
            sys_drive = os.environ.get("SystemDrive", "C:").rstrip("\\/")
            critical = {
                f"{sys_drive}\\Windows",
                f"{sys_drive}\\Program Files", 
                f"{sys_drive}\\Program Files (x86)",
                f"{sys_drive}\\System Volume Information",
                f"{sys_drive}\\$Recycle.Bin",
                f"{sys_drive}\\ProgramData",
                f"{sys_drive}\\Users\\All Users",
                f"{sys_drive}\\Users\\Default",
                f"{sys_drive}\\Users\\Public",
            }
            for env_k in ("SystemRoot", "WINDIR", "ProgramFiles", "ProgramFiles(x86)", "ProgramData", "PUBLIC"):
                val = os.environ.get(env_k)
                if val:
                    critical.add(val)
            try:
                import psutil
                for p in psutil.disk_partitions(all=False):
                    m = p.mountpoint.rstrip("\\/")
                    if m:
                        critical.add(f"{m}\\$Recycle.Bin")
                        critical.add(f"{m}\\System Volume Information")
                        critical.add(f"{m}\\Recovery")
            except Exception:
                pass
            return critical
        else:  # POSIX systems (Linux, macOS)
            return {
                "/bin", "/sbin", "/usr/bin", "/usr/sbin",
                "/etc", "/var", "/opt", "/boot",
                "/proc", "/sys", "/dev", "/run",
                "/lib", "/lib64", "/usr/lib", "/usr/lib64",
                "/root", "/home"
            }
    
    def add_user_whitelist(self, path: str) -> None:
        """Add a path to user whitelist (allows deletion even if normally protected).
        
        Args:
            path: Path to whitelist
        """
        normalized_path = str(Path(path).resolve())
        self._user_whitelists.add(normalized_path)
        self.logger.debug(f"Added path to whitelist: {normalized_path}")
    
    def add_blacklist(self, path: str) -> None:
        """Add a path to additional blacklist (prevents deletion).
        
        Args:
            path: Path to blacklist
        """
        normalized_path = str(Path(path).resolve())
        self._additional_blacklists.add(normalized_path)
        self.logger.debug(f"Added path to blacklist: {normalized_path}")
    
    def is_safe_to_delete(self, path: Path) -> bool:
        """Check if a path is safe to delete.
        
        Args:
            path: Path to validate
            
        Returns:
            True if safe to delete, False otherwise
        """
        try:
            resolved_path = path.resolve()
            path_str = str(resolved_path)
            
            # Check user whitelist first (overrides other protections)
            if path_str in self._user_whitelists:
                self.logger.debug(f"Path allowed by whitelist: {path_str}")
                return True
            
            # Check additional blacklists
            if path_str in self._additional_blacklists:
                self.logger.warning(f"Path blocked by blacklist: {path_str}")
                return False
            
            if self._is_critical_directory(resolved_path):
                self.logger.warning(f"Path is critical system directory: {path_str}")
                return False
            
            if self._is_under_critical_directory(resolved_path):
                self.logger.warning(f"Path is under critical directory: {path_str}")
                return False
            
            # Check system excludes
            if resolved_path.name in self._system_excludes:
                self.logger.warning(f"Path matches system excludes: {path_str}")
                return False
            
            # Check symlink safety
            if not self.check_symlink_safety(resolved_path):
                return False
            
            # Check user permissions
            if not self.validate_user_permissions(resolved_path):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating path {path}: {e}")
            return False
    
    def _is_critical_directory(self, path: Path) -> bool:
        """Check if path is a critical system directory."""
        path_str = str(path)
        
        # Exact match check
        if path_str in self._critical_directories:
            return True
        
        # Case-insensitive check for Windows
        if sys.platform.startswith("win"):
            path_lower = path_str.lower()
            for critical in self._critical_directories:
                if path_lower == critical.lower():
                    return True
        
        return False
    
    def _is_under_critical_directory(self, path: Path) -> bool:
        """Check if path is under a critical system directory."""
        try:
            for critical_dir in self._critical_directories:
                critical_path = Path(critical_dir)
                try:
                    # relative_to() raises ValueError when the path is
                    # outside the critical tree.
                    path.relative_to(critical_path)
                    return True
                except ValueError:
                    # Not under this critical directory
                    continue
            return False
        except Exception:
            # If we can't determine, err on the side of caution
            return True
    
    def check_symlink_safety(self, path: Path) -> bool:
        """Check if symlink operations are safe (prevents symlink attacks).
        
        Args:
            path: Path to check
            
        Returns:
            True if safe, False otherwise
        """
        try:
            if path.is_symlink():
                target = path.readlink()
                
                # Resolve the target and check if it's safe
                try:
                    resolved_target = target.resolve()
                    
                    if self._is_critical_directory(resolved_target):
                        self.logger.warning(f"Symlink points to critical directory: {path} -> {resolved_target}")
                        return False
                    
                    # Check for directory traversal attempts
                    if ".." in str(target):
                        self.logger.warning(f"Symlink contains directory traversal: {path} -> {target}")
                        return False
                    
                except (OSError, RuntimeError) as e:
                    # Broken symlink or circular reference
                    self.logger.warning(f"Broken or circular symlink detected: {path} ({e})")
                    return False
            
            # Check parent directories for symlinks that might affect safety
            current = path.parent
            while current != current.parent:  # Stop at root
                if current.is_symlink():
                    # Parent is a symlink, need to validate its target
                    try:
                        target = current.resolve()
                        if self._is_critical_directory(target):
                            self.logger.warning(f"Parent symlink points to critical directory: {current} -> {target}")
                            return False
                    except (OSError, RuntimeError):
                        self.logger.warning(f"Broken parent symlink: {current}")
                        return False
                current = current.parent
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking symlink safety for {path}: {e}")
            return False
    
    def validate_user_permissions(self, path: Path) -> bool:
        """Check if user has appropriate permissions for the operation.
        
        Args:
            path: Path to check
            
        Returns:
            True if user has permissions, False otherwise
        """
        try:
            if not path.exists():
                # For non-existent paths, check parent directory permissions
                parent = path.parent
                if not parent.exists():
                    self.logger.warning(f"Parent directory does not exist: {parent}")
                    return False
                path_to_check = parent
            else:
                path_to_check = path
            
            # Check read permissions (needed to analyze the file/directory)
            if not os.access(path_to_check, os.R_OK):
                self.logger.warning(f"No read permission for: {path_to_check}")
                return False
            
            # Check write permissions (needed for deletion)
            if not os.access(path_to_check, os.W_OK):
                self.logger.warning(f"No write permission for: {path_to_check}")
                return False
            
            # On Unix systems, check if file is owned by root and we're not root
            if not sys.platform.startswith("win"):
                try:
                    file_stat = path_to_check.stat()
                    if file_stat.st_uid == 0 and os.getuid() != 0:
                        self.logger.warning(f"File owned by root, insufficient privileges: {path_to_check}")
                        return False
                except (OSError, AttributeError):
                    # If we can't get ownership info, proceed with caution
                    pass
            
            # Check for immutable files (Unix systems)
            if not sys.platform.startswith("win"):
                try:
                    file_stat = path_to_check.stat()
                    # Check for immutable flag (if supported)
                    if hasattr(stat, 'UF_IMMUTABLE') and (file_stat.st_flags & stat.UF_IMMUTABLE):
                        self.logger.warning(f"File is immutable: {path_to_check}")
                        return False
                except (OSError, AttributeError):
                    # Immutable flags not supported on this system
                    pass
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking permissions for {path}: {e}")
            return False
    
    def validate_operation_paths(self, paths: List[Path]) -> List[Path]:
        """Validate multiple paths for safe operations.
        
        Args:
            paths: List of paths to validate
            
        Returns:
            List of safe paths (filtered)
            
        Raises:
            PathValidationError: If critical validation errors occur
        """
        safe_paths = []
        blocked_paths = []
        
        for path in paths:
            try:
                if self.is_safe_to_delete(path):
                    safe_paths.append(path)
                else:
                    blocked_paths.append(path)
            except Exception as e:
                self.logger.error(f"Error validating path {path}: {e}")
                blocked_paths.append(path)
        
        if blocked_paths:
            self.logger.warning(f"Blocked {len(blocked_paths)} unsafe paths")
            for blocked in blocked_paths[:5]:  # Log first 5 blocked paths
                self.logger.warning(f"  Blocked: {blocked}")
            if len(blocked_paths) > 5:
                self.logger.warning(f"  ... and {len(blocked_paths) - 5} more")
        
        self.logger.info(f"Validated {len(paths)} paths: {len(safe_paths)} safe, {len(blocked_paths)} blocked")
        return safe_paths
    
    def get_validation_summary(self, paths: List[Path]) -> dict:
        """Get a summary of path validation results.
        
        Args:
            paths: List of paths to analyze
            
        Returns:
            Dictionary with validation summary
        """
        summary = {
            'total_paths': len(paths),
            'safe_paths': 0,
            'blocked_paths': 0,
            'blocked_reasons': {},
            'validation_errors': 0
        }
        
        for path in paths:
            try:
                if self.is_safe_to_delete(path):
                    summary['safe_paths'] += 1
                else:
                    summary['blocked_paths'] += 1
                    # Determine blocking reason
                    reason = self._get_blocking_reason(path)
                    summary['blocked_reasons'][reason] = summary['blocked_reasons'].get(reason, 0) + 1
            except Exception:
                summary['validation_errors'] += 1
        
        return summary
    
    def _get_blocking_reason(self, path: Path) -> str:
        """Get the reason why a path is blocked."""
        try:
            resolved_path = path.resolve()
            path_str = str(resolved_path)
            
            if path_str in self._additional_blacklists:
                return "user_blacklist"
            elif self._is_critical_directory(resolved_path):
                return "critical_directory"
            elif self._is_under_critical_directory(resolved_path):
                return "under_critical_directory"
            elif resolved_path.name in self._system_excludes:
                return "system_exclude"
            elif not self.check_symlink_safety(resolved_path):
                return "symlink_unsafe"
            elif not self.validate_user_permissions(resolved_path):
                return "insufficient_permissions"
            else:
                return "unknown"
        except Exception:
            return "validation_error"