# Cortex Cleaner - Production Implementation Plan V2

**Based on:** Deep Code Analysis (May 13, 2026)  
**Timeline:** 5-6 weeks (200 hours)  
**Priority:** Critical fixes → Security → Cross-platform → Performance

---

## Quick Start: Fix Critical Issues (Day 1)

### Issue #1: Keyring Import Crash (30 minutes)

**File:** `performance/multi_drive_scanner.py`

**Problem:** Hard import crashes if keyring not installed
```python
import keyring  # Line 9 - CRASHES if not installed!
```

**Fix:**
```python
# Replace line 9 with:
try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False
    keyring = None
    logging.getLogger(__name__).warning(
        "keyring not installed - network credentials will only be stored in memory"
    )
```

**Then update `_store_credentials` method (line ~450):**
```python
def _store_credentials(self, credentials: Dict[str, str]) -> None:
    """Securely store network drive credentials."""
    for server, cred_info in credentials.items():
        try:
            # ... existing code to parse credentials ...
            
            # Store in memory (always)
            self._network_credentials[server] = {
                "username": username,
                "password": password
            }
            
            # Store securely using keyring if available
            if HAS_KEYRING and password:
                try:
                    keyring.set_password(
                        "cortex_cleaner_network", 
                        f"{server}:{username}", 
                        password
                    )
                    logger.info(f"Credentials for {server} stored securely")
                except Exception as e:
                    logger.warning(f"Could not store credentials in keyring: {e}")
            elif not HAS_KEYRING:
                logger.info("Keyring not available - credentials stored in memory only")
                
        except Exception as e:
            logger.error(f"Error storing credentials for {server}: {e}")
```

**Test:**
```bash
# Should work even without keyring installed
python -c "from cortex_unified.performance.multi_drive_scanner import DriveManager; print('OK')"
```

---

### Issue #2: Path Traversal Vulnerability (1 hour)

**Files:** `analyzers/file_shredder.py`, `core/deleter.py`

**Problem:** No validation of `..` in paths - can delete files outside target directory

**Create new security module:** `core/security.py`
```python
"""Security utilities for Cortex Cleaner."""

import os
from pathlib import Path
from typing import Union, List

# System-critical paths that should never be modified
PROTECTED_PATHS = {
    # Windows
    "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",
    "C:\\ProgramData", "C:\\System Volume Information",
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
                   base_dir: Union[str, Path] = None) -> tuple[List[Path], List[str]]:
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
```

**Update `file_shredder.py`:**
```python
from cortex_unified.core.security import is_safe_path, is_system_file

def shred_file(self, filepath: Path, passes: int = None, 
               allow_system_files: bool = False) -> bool:
    """Securely delete a file with safety checks."""
    if passes is None:
        passes = self.passes
    
    filepath = normalize_path(str(filepath))
    
    # SAFETY CHECKS
    if not filepath.exists():
        self.errors.append({"file": str(filepath), "error": "File does not exist"})
        return False
    
    # Check if path is safe
    if not is_safe_path(filepath):
        self.errors.append({"file": str(filepath), "error": "Path is outside allowed directory"})
        return False
    
    # Check if it's a system file
    if not allow_system_files and is_system_file(filepath):
        self.errors.append({"file": str(filepath), "error": "Cannot shred system files"})
        return False
    
    # Check permissions
    if not os.access(filepath, os.W_OK):
        self.errors.append({"file": str(filepath), "error": "No write permission"})
        return False
    
    # ... rest of existing code ...
```

---

### Issue #3: Switch to xxHash (2 hours)

**File:** `analyzers/duplicate_finder.py`

**Problem:** MD5 is slow (10-50x slower than xxHash)

**Step 1: Add xxhash to requirements**
```bash
pip install xxhash
```

**Step 2: Update duplicate_finder.py**
```python
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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
        self.chunk_size = 8192
        
        # Use xxHash if available, fallback to BLAKE2b (faster than MD5)
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
    
    def _get_file_hash(self, filepath: Path) -> Optional[str]:
        """Calculate hash of a file using fast algorithm."""
        try:
            file_size = filepath.stat().st_size
            
            # For very small files (<1KB), hash entire file
            if file_size < 1024:
                with open(filepath, 'rb') as f:
                    data = f.read()
                    if HAS_XXHASH:
                        return xxhash.xxh3_64(data).hexdigest()
                    else:
                        return hashlib.blake2b(data).hexdigest()
            
            # For small files (<1MB), hash entire file
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
            
        except Exception as e:
            with self._lock:
                self.error_count += 1
            return None
    
    def _verify_duplicates(self, paths: List[Path]) -> bool:
        """Verify that files are truly identical (byte-by-byte comparison).
        
        This is called after hash matching to ensure no false positives,
        especially when using partial hashing for large files.
        """
        if len(paths) < 2:
            return True
        
        try:
            # Compare first file with all others
            reference = paths[0]
            ref_size = reference.stat().st_size
            
            for path in paths[1:]:
                # Size must match
                if path.stat().st_size != ref_size:
                    return False
                
                # Byte-by-byte comparison
                with open(reference, 'rb') as f1, open(path, 'rb') as f2:
                    while True:
                        chunk1 = f1.read(self.chunk_size)
                        chunk2 = f2.read(self.chunk_size)
                        
                        if chunk1 != chunk2:
                            return False
                        
                        if not chunk1:  # EOF
                            break
            
            return True
            
        except Exception:
            return False
```

**Performance comparison:**
- MD5: ~400 MB/s
- BLAKE2b: ~1 GB/s (2.5x faster)
- xxHash: ~4 GB/s (10x faster)

---

## Phase 1: Critical Fixes (Week 1)

### Day 1: Security & Stability
- ✅ Fix keyring import (30 min)
- ✅ Add path validation (1 hour)
- ✅ Switch to xxHash (2 hours)
- ✅ Add security.py module (1 hour)
- ✅ Update file_shredder.py (1 hour)
- ✅ Update deleter.py (30 min)

### Day 2: Fix Recursion Limit
- ✅ Refactor scanner.py to use iterative BFS (4 hours)
- ✅ Add max_depth parameter (1 hour)
- ✅ Add progress tracking (1 hour)

### Day 3: Config Migration
- ✅ Update all modules to use config_v2.py (4 hours)
- ✅ Create migration script (2 hours)
- ✅ Test configuration loading (2 hours)

---

## Phase 2: Cross-Platform Support (Week 2)

### macOS Browser Support
**File:** `analyzers/privacy_cleaner.py`

Add macOS-specific browser paths and methods.

### Linux Browser Support
**File:** `analyzers/privacy_cleaner.py`

Add Linux-specific browser paths and methods.

---

## Testing Strategy

### Unit Tests
Create `tests/test_security.py`:
```python
import pytest
from pathlib import Path
from cortex_unified.core.security import is_safe_path, is_system_file

def test_safe_path_within_base_dir():
    """Test that paths within base_dir are safe."""
    base = Path("/tmp/test")
    safe = Path("/tmp/test/file.txt")
    assert is_safe_path(safe, base) == True

def test_unsafe_path_outside_base_dir():
    """Test that paths outside base_dir are unsafe."""
    base = Path("/tmp/test")
    unsafe = Path("/tmp/other/file.txt")
    assert is_safe_path(unsafe, base) == False

def test_system_file_detection():
    """Test that system files are detected."""
    assert is_system_file(Path("C:\\Windows\\System32\\kernel32.dll")) == True
    assert is_system_file(Path("/usr/bin/bash")) == True
    assert is_system_file(Path("/home/user/document.txt")) == False
```

---

## Deployment Checklist

- [ ] All critical fixes applied
- [ ] Tests passing (80%+ coverage)
- [ ] Documentation updated
- [ ] Security audit passed
- [ ] Performance benchmarks met
- [ ] Cross-platform testing complete
- [ ] User acceptance testing done
- [ ] Rollback plan prepared

---

**Ready to implement?** Start with Day 1 fixes above!
