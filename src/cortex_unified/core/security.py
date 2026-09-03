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
    """Protected system locations for the current platform.

    The platform-specific set is always merged with ``PROTECTED_PATHS_COMMON``
    so callers cannot accidentally skip the entries that apply everywhere.
    On Windows, this dynamically resolves system environment paths and drive roots.
    """
    system = platform.system().lower()

    if system == "windows":
        paths = set(PROTECTED_PATHS_WINDOWS)
        # Dynamically add current environment paths
        for env_k in ("SystemRoot", "WINDIR", "ProgramFiles", "ProgramFiles(x86)", "ProgramData", "PUBLIC"):
            val = os.environ.get(env_k)
            if val:
                paths.add(val)
        # Dynamically protect drive roots system directories across all drives
        try:
            import psutil
            for part in psutil.disk_partitions(all=False):
                mount = part.mountpoint.rstrip("\\/")
                if mount:
                    paths.add(f"{mount}\\$Recycle.Bin")
                    paths.add(f"{mount}\\System Volume Information")
                    paths.add(f"{mount}\\Recovery")
        except Exception:
            for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
                paths.add(f"{letter}:\\$Recycle.Bin")
                paths.add(f"{letter}:\\System Volume Information")
                paths.add(f"{letter}:\\Recovery")
        return paths | PROTECTED_PATHS_COMMON
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

        if not path.exists():
            return False

        # Constrain operations to a subtree when the caller provides one;
        # relative_to() raises ValueError for anything outside it.
        if base_dir:
            base_dir = Path(base_dir).resolve()
            try:
                path.relative_to(base_dir)
            except ValueError:
                return False

        # Prefix match against protected roots. Comparison is lowercased
        # because Windows paths are case-insensitive and macOS preserves
        # case while still matching insensitively on its default FS.
        path_str = str(path)
        protected_paths = _get_protected_paths()

        for protected in protected_paths:
            protected_resolved = Path(protected).resolve()

            if path == protected_resolved:
                return False
            try:
                if path.is_relative_to(protected_resolved):
                    return False
            except (ValueError, OSError):
                pass

        # System binaries outside user areas are off limits. The user-area
        # exemption exists so users can still clean their own Downloads or
        # Desktop copies of .exe/.dll files.
        if path.is_file() and path.suffix.lower() in PROTECTED_EXTENSIONS:
            path_str_lower = path_str.lower()
            user_indicators = ["users", "home", "documents", "downloads", "desktop"]
            if not any(indicator in path_str_lower for indicator in user_indicators):
                return False

        return True

    except Exception:
        # Undeterminable safety means unsafe; never fail open here.
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

        path_str = str(path)
        protected_paths = _get_protected_paths()

        for protected in protected_paths:
            protected_resolved = Path(protected).resolve()

            if path == protected_resolved:
                return True
            try:
                if path.is_relative_to(protected_resolved):
                    return True
            except (ValueError, OSError):
                pass

        # Not under a protected root, but a system binary type in a
        # system-ish directory still counts as a system file.
        if path.is_file() and path.suffix.lower() in PROTECTED_EXTENSIONS:
            path_str_lower = path_str.lower()
            system_indicators = ["windows", "system32", "program files", "usr", "bin", "sbin", "lib"]
            if any(indicator in path_str_lower for indicator in system_indicators):
                return True

        return False

    except Exception:
        # Undeterminable means assume the worst; callers treat this as
        # undeletable rather than risking an OS file.
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

    For paths that do not exist yet, writability of the parent directory is
    used as the proxy -- creating the file is what matters in that case.

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

        if not path.exists():
            return False, "Path does not exist"

        if not allow_system_files and is_system_file(path):
            return False, "Cannot delete system files"

        if not is_safe_path(path):
            return False, "Path is in a protected location"

        if not is_path_writable(path):
            return False, "No write permission"

        return True, ""

    except Exception as e:
        return False, f"Error checking path: {e}"
