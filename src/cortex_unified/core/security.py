"""Security utilities for Cortex Cleaner.

This module provides security functions to prevent accidental deletion of
system files and validate paths before any destructive operations.
"""

import os
import platform
from pathlib import Path
from typing import Union, List, Tuple

# System-critical paths that should never be modified
PROTECTED_PATHS_WINDOWS = {
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\ProgramData",
    "C:\\System Volume Information",
    "C:\\$Recycle.Bin",
    "C:\\Recovery",
}

PROTECTED_PATHS_MACOS = {
    "/System",
    "/Library",
    "/Applications",
    "/usr",
    "/bin",
    "/sbin",
    "/private",
    "/var",
}

PROTECTED_PATHS_LINUX = {
    "/boot",
    "/dev",
    "/proc",
    "/sys",
    "/root",
    "/usr",
    "/bin",
    "/sbin",
    "/lib",
    "/lib64",
}

PROTECTED_PATHS_COMMON = {
    "/etc",
    "/var/log",
}

# System file extensions that should not be deleted
PROTECTED_EXTENSIONS = {
    ".sys", ".dll", ".exe", ".com", ".bat", ".cmd",  # Windows system
    ".dylib", ".framework",  # macOS system
    ".so", ".ko", ".a",  # Linux system
}

def _get_protected_paths() -> set:
    """Get protected paths for current platform."""
    system = platform.system().lower()
    
    if system == "windows":
        return PROTECTED_PATHS_WINDOWS | PROTECTED_PATHS_COMMON
    elif system == "darwin":
        return PROTECTED_PATHS_MACOS | PROTECTED_PATHS_COMMON
    else:  # Linux and others
        return PROTECTED_PATHS_LINUX | PROTECTED_PATHS_COMMON

def is_safe_path(path: Union[str, Path], base_dir: Union[str, Path] = None) -> bool:
    """Check if a path is safe to modify.
    
    This function performs multiple safety checks:
    1. Verifies the path exists
    2. Checks if path is within base_dir (if specified)
    3. Ensures path is not in protected system directories
    4. Checks file extension is not a system file
    
    Args:
        path: Path to check
        base_dir: Optional base directory to restrict operations to
    
    Returns:
        True if path is safe to modify, False otherwise
    
    Examples:
        >>> is_safe_path("/home/user/document.txt")
        True
        >>> is_safe_path("C:\\Windows\\System32\\kernel32.dll")
        False
        >>> is_safe_path("/tmp/test.txt", base_dir="/tmp")
        True
        >>> is_safe_path("/etc/passwd", base_dir="/tmp")
        False
    """
    try:
        path = Path(path).resolve()
        
        # Check if path exists
        if not path.exists():
            return False
        
        # Check if path is within base_dir (if specified)
        if base_dir:
            base_dir = Path(base_dir).resolve()
            try:
                path.relative_to(base_dir)
            except ValueError:
                # Path is outside base_dir
                return False
        
        # Check against protected paths
        path_str = str(path)
        protected_paths = _get_protected_paths()
        
        for protected in protected_paths:
            # Normalize path separators for comparison
            protected_normalized = str(Path(protected))
            path_normalized = str(path)
            
            # Check if path starts with protected path
            if path_normalized.lower().startswith(protected_normalized.lower()):
                return False
        
        # Check file extension for system files
        if path.is_file() and path.suffix.lower() in PROTECTED_EXTENSIONS:
            # Allow if it's in a user directory
            path_str_lower = path_str.lower()
            user_indicators = ["users", "home", "documents", "downloads", "desktop"]
            if not any(indicator in path_str_lower for indicator in user_indicators):
                return False
        
        return True
        
    except Exception:
        # If we can't determine safety, err on the side of caution
        return False

def is_system_file(path: Union[str, Path]) -> bool:
    """Check if a file is a system file.
    
    Args:
        path: Path to check
    
    Returns:
        True if file is a system file, False otherwise
    
    Examples:
        >>> is_system_file("C:\\Windows\\System32\\kernel32.dll")
        True
        >>> is_system_file("/usr/bin/bash")
        True
        >>> is_system_file("/home/user/document.txt")
        False
    """
    try:
        path = Path(path).resolve()
        
        # Check against protected paths
        path_str = str(path)
        protected_paths = _get_protected_paths()
        
        for protected in protected_paths:
            protected_normalized = str(Path(protected))
            path_normalized = str(path)
            
            if path_normalized.lower().startswith(protected_normalized.lower()):
                return True
        
        # Check file extension
        if path.is_file() and path.suffix.lower() in PROTECTED_EXTENSIONS:
            # Check if it's in a system directory
            path_str_lower = path_str.lower()
            system_indicators = ["windows", "system32", "program files", "usr", "bin", "sbin", "lib"]
            if any(indicator in path_str_lower for indicator in system_indicators):
                return True
        
        return False
        
    except Exception:
        # If we can't determine, assume it's a system file to be safe
        return True

def validate_paths(paths: List[Union[str, Path]], 
                   base_dir: Union[str, Path] = None) -> Tuple[List[Path], List[str]]:
    """Validate multiple paths and return safe ones + errors.
    
    Args:
        paths: List of paths to validate
        base_dir: Optional base directory to restrict operations to
    
    Returns:
        Tuple of (safe_paths, error_messages)
        - safe_paths: List of Path objects that passed validation
        - error_messages: List of error messages for rejected paths
    
    Examples:
        >>> safe, errors = validate_paths(["/tmp/test.txt", "/etc/passwd"])
        >>> len(safe)
        1
        >>> len(errors)
        1
    """
    safe_paths = []
    errors = []
    
    for path in paths:
        try:
            if is_safe_path(path, base_dir):
                safe_paths.append(Path(path).resolve())
            else:
                if is_system_file(path):
                    errors.append(f"System file cannot be modified: {path}")
                elif base_dir:
                    errors.append(f"Path outside allowed directory: {path}")
                else:
                    errors.append(f"Unsafe or invalid path: {path}")
        except Exception as e:
            errors.append(f"Error validating path {path}: {e}")
    
    return safe_paths, errors

def is_path_writable(path: Union[str, Path]) -> bool:
    """Check if a path is writable.
    
    Args:
        path: Path to check
    
    Returns:
        True if path is writable, False otherwise
    """
    try:
        path = Path(path)
        
        if path.exists():
            return os.access(path, os.W_OK)
        else:
            # Check if parent directory is writable
            parent = path.parent
            return parent.exists() and os.access(parent, os.W_OK)
            
    except Exception:
        return False

def get_safe_temp_dir() -> Path:
    """Get a safe temporary directory for the current platform.
    
    Returns:
        Path to safe temporary directory
    """
    import tempfile
    return Path(tempfile.gettempdir())

# Convenience function for common use case
def check_deletion_safety(path: Union[str, Path], 
                         allow_system_files: bool = False) -> Tuple[bool, str]:
    """Check if it's safe to delete a path.
    
    Args:
        path: Path to check
        allow_system_files: Whether to allow deletion of system files
    
    Returns:
        Tuple of (is_safe, reason)
        - is_safe: True if safe to delete
        - reason: Explanation if not safe, empty string if safe
    
    Examples:
        >>> safe, reason = check_deletion_safety("/tmp/test.txt")
        >>> safe
        True
        >>> safe, reason = check_deletion_safety("C:\\Windows\\System32\\kernel32.dll")
        >>> safe
        False
        >>> "system file" in reason.lower()
        True
    """
    try:
        path = Path(path)
        
        # Check if path exists
        if not path.exists():
            return False, "Path does not exist"
        
        # Check if it's a system file
        if not allow_system_files and is_system_file(path):
            return False, "Cannot delete system files"
        
        # Check if path is safe
        if not is_safe_path(path):
            return False, "Path is in a protected location"
        
        # Check if we have write permission
        if not is_path_writable(path):
            return False, "No write permission"
        
        return True, ""
        
    except Exception as e:
        return False, f"Error checking path: {e}"
