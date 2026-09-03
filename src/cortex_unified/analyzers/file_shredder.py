"""Overwrite-based file shredding.

Multi-pass overwrite (random ... random, final zero pass) followed by
unlink. Note the physical reality: overwrite passes are only meaningful on
rotational HDDs; on SSD/NVMe, wear-leveling means the original blocks may
survive. The storage-aware engine path (``engine.secure_delete``) enforces
that distinction; this module is the simple legacy shredder.
"""

import os
from pathlib import Path
from typing import List, Dict

from cortex_unified.core.utils import normalize_path
from cortex_unified.core.config import Config
from cortex_unified.core.security import check_deletion_safety

class FileShredder:
    """Securely deletes files by overwriting contents before unlinking."""
    
    def __init__(self, config: Config = None):
        """
        Args:
            config: Unused today beyond interface parity with other analyzers;
                defaults are applied when omitted.
        """
        self.config = config or Config()
        self.passes = 3  # overwrite passes per file
        self.verify = True
        
        self.shredded_files: List[Path] = []
        self.errors: List[Dict[str, str]] = []
    
    def _generate_random_data(self, size: int) -> bytes:
        return os.urandom(size)
        """_generate_random_data."""
        """_generate_random_data."""
    
    def _generate_pattern_data(self, size: int, pattern: int) -> bytes:
        return bytes([pattern] * size)
        """_generate_pattern_data."""
        """_generate_pattern_data."""
    
    def shred_file(self, filepath: Path, passes: int = None, allow_system_files: bool = False) -> bool:
        """Overwrite *filepath* in place, then unlink it.
        
        Args:
            filepath: Path to the file to shred
            passes: Number of overwrite passes (defaults to self.passes)
            allow_system_files: Whether to allow shredding system files
            
        Returns:
            True if successful, False otherwise (reason recorded in ``errors``)
        """
        if passes is None:
            passes = self.passes
        
        filepath = normalize_path(str(filepath))
        
        try:
            # Safety gate first: refuse before a single byte is touched.
            is_safe, reason = check_deletion_safety(filepath, allow_system_files)
            if not is_safe:
                self.errors.append({
                    "file": str(filepath),
                    "error": f"Security check failed: {reason}"
                })
                return False
            
            if not filepath.exists():
                self.errors.append({
                    "file": str(filepath),
                    "error": "File does not exist"
                })
                return False
            
            file_size = filepath.stat().st_size
            if file_size == 0:
                # Nothing to overwrite; deletion alone is complete.
                filepath.unlink()
                self.shredded_files.append(filepath)
                return True
            
            with open(filepath, "r+b") as f:
                for i in range(passes):
                    f.seek(0)
                    
                    # Final pass writes zeros so no recognizable pattern of
                    # the original data remains even at the magnetic level.
                    if i == passes - 1:
                        data = self._generate_pattern_data(file_size, 0x00)
                    else:
                        data = self._generate_random_data(file_size)
                    
                    f.write(data)
                    # fsync forces the pass through OS caches to platters;
                    # without it the overwrite may never leave the page cache.
                    f.flush()
                    os.fsync(f.fileno())
            
            filepath.unlink()
            
            if self.verify and filepath.exists():
                self.errors.append({
                    "file": str(filepath),
                    "error": "File still exists after deletion"
                })
                return False
            
            self.shredded_files.append(filepath)
            return True
            
        except Exception as e:
            self.errors.append({
                "file": str(filepath),
                "error": str(e)
            })
            return False
    
    def shred_files(self, filepaths: List[Path], passes: int = None) -> Dict[str, int]:
        """Securely delete multiple files.
        
        Args:
            filepaths: List of file paths to shred
            passes: Number of overwrite passes (defaults to self.passes)
            
        Returns:
            Dictionary with statistics
        """
        if passes is None:
            passes = self.passes
        
        shredded_count = 0
        error_count = 0
        
        for filepath in filepaths:
            if self.shred_file(filepath, passes):
                shredded_count += 1
            else:
                error_count += 1
        
        return {
            "shredded": shredded_count,
            "errors": error_count,
            "total": len(filepaths)
        }
    
    def get_stats(self) -> dict:
        """Get statistics about the shredding process."""
        return {
            "files_shredded": len(self.shredded_files),
            "errors": len(self.errors),
            "passes_per_file": self.passes
        }
    
    def set_passes(self, passes: int):
        """Set the number of overwrite passes."""
        if passes < 1:
            raise ValueError("Number of passes must be at least 1")
        self.passes = passes
    
    def verify_deletion(self, verify: bool):
        """Set whether to verify file deletion."""
        self.verify = verify