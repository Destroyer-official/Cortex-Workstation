"""File shredder for secure deletion in Deep Cleaner."""

import os
import random
import struct
from pathlib import Path
from typing import List, Dict
import hashlib

from ..utils import normalize_path
from ..config import Config


class FileShredder:
    """Secure file deletion with overwrite passes."""
    
    def __init__(self, config: Config = None):
        """Initialize file shredder."""
        self.config = config or Config()
        self.passes = 3  # Default number of overwrite passes
        self.verify = True  # Verify deletion by default
        
        # Results
        self.shredded_files: List[Path] = []
        self.errors: List[Dict[str, str]] = []
    
    def _generate_random_data(self, size: int) -> bytes:
        """Generate random data of specified size."""
        return os.urandom(size)
    
    def _generate_pattern_data(self, size: int, pattern: int) -> bytes:
        """Generate data with specific byte pattern."""
        return bytes([pattern] * size)
    
    def shred_file(self, filepath: Path, passes: int = None) -> bool:
        """Securely delete a file by overwriting it multiple times.
        
        Args:
            filepath: Path to the file to shred
            passes: Number of overwrite passes (defaults to self.passes)
            
        Returns:
            True if successful, False otherwise
        """
        if passes is None:
            passes = self.passes
        
        filepath = normalize_path(str(filepath))
        
        try:
            # Check if file exists
            if not filepath.exists():
                self.errors.append({
                    "file": str(filepath),
                    "error": "File does not exist"
                })
                return False
            
            # Get file size
            file_size = filepath.stat().st_size
            if file_size == 0:
                # For empty files, just delete normally
                filepath.unlink()
                self.shredded_files.append(filepath)
                return True
            
            # Open file for writing
            with open(filepath, "r+b") as f:
                # Perform overwrite passes
                for i in range(passes):
                    # Seek to beginning
                    f.seek(0)
                    
                    # Generate and write data for this pass
                    if i == passes - 1:
                        # Last pass: write zeros
                        data = self._generate_pattern_data(file_size, 0x00)
                    else:
                        # Other passes: write random data
                        data = self._generate_random_data(file_size)
                    
                    # Write data
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk
            
            # Delete the file
            filepath.unlink()
            
            # Verify deletion if requested
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