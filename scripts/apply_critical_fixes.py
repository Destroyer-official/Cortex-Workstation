#!/usr/bin/env python3
"""
Apply Critical Fixes to Cortex Cleaner
Automatically fixes the 3 most critical issues identified in code analysis.

Usage:
    python apply_critical_fixes.py [--dry-run]
"""

import sys
import os
import shutil
from pathlib import Path
from datetime import datetime

# Color output for terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(msg):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{msg}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(msg):
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKCYAN}ℹ {msg}{Colors.ENDC}")

def backup_file(filepath):
    """Create backup of file before modification."""
    backup_dir = Path("backups") / datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    backup_path = backup_dir / filepath.name
    shutil.copy2(filepath, backup_path)
    return backup_path

def fix_keyring_import(dry_run=False):
    """Fix #1: Keyring import crash in multi_drive_scanner.py"""
    print_header("FIX #1: Keyring Import Crash")
    
    file_path = Path("performance/multi_drive_scanner.py")
    
    if not file_path.exists():
        print_error(f"File not found: {file_path}")
        return False
    
    print_info(f"Processing: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already fixed
    if "HAS_KEYRING" in content:
        print_warning("Already fixed - skipping")
        return True
    
    # Find the import keyring line
    if "import keyring" not in content:
        print_warning("keyring import not found - may already be fixed differently")
        return True
    
    # Create the fix
    old_import = "import keyring"
    new_import = """try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False
    keyring = None
    logger.warning("keyring not installed - network credentials will only be stored in memory")"""
    
    new_content = content.replace(old_import, new_import, 1)
    
    if dry_run:
        print_info("DRY RUN - Would replace:")
        print(f"  OLD: {old_import}")
        print(f"  NEW: {new_import[:50]}...")
        return True
    
    # Backup original
    backup_path = backup_file(file_path)
    print_info(f"Backup created: {backup_path}")
    
    # Write fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print_success(f"Fixed keyring import in {file_path}")
    return True

def create_security_module(dry_run=False):
    """Fix #2: Create security.py module for path validation"""
    print_header("FIX #2: Path Validation Security Module")
    
    file_path = Path("core/security.py")
    
    if file_path.exists():
        print_warning("security.py already exists - skipping")
        return True
    
    security_code = '''"""Security utilities for Cortex Cleaner."""

import os
from pathlib import Path
from typing import Union, List

# System-critical paths that should never be modified
PROTECTED_PATHS = {
    # Windows
    "C:\\\\Windows", "C:\\\\Program Files", "C:\\\\Program Files (x86)",
    "C:\\\\ProgramData", "C:\\\\System Volume Information",
    # macOS
    "/System", "/Library", "/Applications", "/usr", "/bin", "/sbin",
    # Linux
    "/boot", "/dev", "/proc", "/sys", "/root",
    # Common
    "/etc", "/var/log"
}

PROTECTED_EXTENSIONS = {
    ".sys", ".dll", ".exe", ".com", ".bat", ".cmd",  # Windows system
    ".dylib", ".framework",  # macOS system
    ".so", ".ko"  # Linux system
}

def is_safe_path(path: Union[str, Path], base_dir: Union[str, Path] = None) -> bool:
    """Check if a path is safe to modify.
    
    Args:
        path: Path to check
        base_dir: Optional base directory to restrict operations to
    
    Returns:
        True if path is safe to modify
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
        path_str = str(path).lower()
        for protected in PROTECTED_PATHS:
            if path_str.startswith(protected.lower()):
                return False
        
        # Check file extension
        if path.is_file() and path.suffix.lower() in PROTECTED_EXTENSIONS:
            return False
        
        return True
        
    except Exception:
        return False

def is_system_file(path: Union[str, Path]) -> bool:
    """Check if a file is a system file."""
    try:
        path = Path(path).resolve()
        
        # Check against protected paths
        path_str = str(path).lower()
        for protected in PROTECTED_PATHS:
            if path_str.startswith(protected.lower()):
                return True
        
        # Check file extension
        if path.is_file() and path.suffix.lower() in PROTECTED_EXTENSIONS:
            return True
        
        return False
        
    except Exception:
        return True  # Err on the side of caution

def validate_paths(paths: List[Union[str, Path]], 
                   base_dir: Union[str, Path] = None) -> tuple:
    """Validate multiple paths and return safe ones + errors.
    
    Returns:
        (safe_paths, error_messages)
    """
    safe_paths = []
    errors = []
    
    for path in paths:
        if is_safe_path(path, base_dir):
            safe_paths.append(Path(path).resolve())
        else:
            errors.append(f"Unsafe or invalid path: {path}")
    
    return safe_paths, errors
'''
    
    if dry_run:
        print_info(f"DRY RUN - Would create: {file_path}")
        print_info(f"  Size: {len(security_code)} bytes")
        return True
    
    # Create the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(security_code)
    
    print_success(f"Created security module: {file_path}")
    return True

def update_duplicate_finder_hash(dry_run=False):
    """Fix #3: Switch from MD5 to xxHash/BLAKE2b"""
    print_header("FIX #3: Switch to Fast Hashing Algorithm")
    
    file_path = Path("analyzers/duplicate_finder.py")
    
    if not file_path.exists():
        print_error(f"File not found: {file_path}")
        return False
    
    print_info(f"Processing: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already fixed
    if "HAS_XXHASH" in content or "xxhash" in content:
        print_warning("Already fixed - skipping")
        return True
    
    # Find the hash algorithm line
    if 'self.hash_algorithm = "md5"' not in content:
        print_warning("MD5 hash not found - may already be fixed differently")
        return True
    
    # Add xxhash import after other imports
    import_section = """import hashlib
from pathlib import Path"""
    
    new_import_section = """import hashlib
from pathlib import Path

# Try to import xxhash (10x faster than MD5)
try:
    import xxhash
    HAS_XXHASH = True
except ImportError:
    HAS_XXHASH = False"""
    
    new_content = content.replace(import_section, new_import_section, 1)
    
    # Replace hash algorithm initialization
    old_init = '''        self.chunk_size = 8192  # Read files in 8KB chunks for hashing
        self.hash_algorithm = "md5"  # Default hash algorithm'''
    
    new_init = '''        self.chunk_size = 8192  # Read files in 8KB chunks for hashing
        
        # Use xxHash if available, fallback to BLAKE2b (faster than MD5)
        if HAS_XXHASH:
            self.hash_algorithm = "xxhash"
        else:
            self.hash_algorithm = "blake2b"  # Built-in, faster than MD5'''
    
    new_content = new_content.replace(old_init, new_init, 1)
    
    if dry_run:
        print_info("DRY RUN - Would apply hash algorithm changes")
        return True
    
    # Backup original
    backup_path = backup_file(file_path)
    print_info(f"Backup created: {backup_path}")
    
    # Write fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print_success(f"Updated hash algorithm in {file_path}")
    print_info("Note: Install xxhash for best performance: pip install xxhash")
    return True

def main():
    """Main execution function."""
    dry_run = "--dry-run" in sys.argv
    
    print_header("Cortex Cleaner - Critical Fixes Applicator")
    
    if dry_run:
        print_warning("DRY RUN MODE - No files will be modified")
    
    print_info("This script will apply 3 critical fixes:")
    print("  1. Fix keyring import crash")
    print("  2. Create security module for path validation")
    print("  3. Switch to fast hashing algorithm (xxHash/BLAKE2b)")
    print()
    
    if not dry_run:
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            print_warning("Aborted by user")
            return 1
    
    # Apply fixes
    results = []
    
    results.append(("Keyring Import Fix", fix_keyring_import(dry_run)))
    results.append(("Security Module", create_security_module(dry_run)))
    results.append(("Hash Algorithm Update", update_duplicate_finder_hash(dry_run)))
    
    # Summary
    print_header("Summary")
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for name, success in results:
        if success:
            print_success(f"{name}: OK")
        else:
            print_error(f"{name}: FAILED")
    
    print()
    print(f"Results: {success_count}/{total_count} fixes applied successfully")
    
    if success_count == total_count:
        print_success("All critical fixes applied!")
        if not dry_run:
            print_info("Backups saved in: ./backups/")
            print_info("Next steps:")
            print("  1. Review changes: git diff")
            print("  2. Run tests: pytest tests/")
            print("  3. See IMPLEMENTATION_PLAN_V2.md for remaining fixes")
        return 0
    else:
        print_error("Some fixes failed - check errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
