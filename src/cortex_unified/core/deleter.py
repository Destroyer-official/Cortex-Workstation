"""File and directory deletion functionality for Cortex Cleaner."""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

try:
    from send2trash import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False

from cortex_unified.core.utils import generate_manifest_filename
from cortex_unified.core.security import is_safe_path, check_deletion_safety

class Deleter:
    """Deleter for removing empty files and directories."""
    
    def __init__(self, dry_run: bool = True, use_trash: bool = False):
        """Initialize deleter."""
        self.dry_run = dry_run
        self.use_trash = use_trash and HAS_SEND2TRASH
        self.deleted_items = []
        self.errors = []
    
    def _delete_file(self, filepath: Path) -> bool:
        """Delete a single file."""
        try:
            # SECURITY CHECK: Verify it's safe to delete this file
            if not self.dry_run:  # Only check in real deletion mode
                is_safe, reason = check_deletion_safety(filepath, allow_system_files=False)
                if not is_safe:
                    self.errors.append({
                        "type": "file",
                        "path": str(filepath),
                        "error": f"Security check failed: {reason}"
                    })
                    return False
            
            if self.dry_run:
                # Just record that we would delete it
                self.deleted_items.append({
                    "type": "file",
                    "path": str(filepath),
                    "action": "would_delete"
                })
                return True
            
            if self.use_trash:
                # Move to trash
                send2trash(str(filepath))
                self.deleted_items.append({
                    "type": "file",
                    "path": str(filepath),
                    "action": "moved_to_trash"
                })
            else:
                # Permanently delete
                filepath.unlink()
                self.deleted_items.append({
                    "type": "file",
                    "path": str(filepath),
                    "action": "deleted"
                })
            return True
        except Exception as e:
            self.errors.append({
                "type": "file",
                "path": str(filepath),
                "error": str(e)
            })
            return False
    
    def _delete_directory(self, dirpath: Path) -> bool:
        """Delete a single directory."""
        try:
            if self.dry_run:
                # Just record that we would delete it
                self.deleted_items.append({
                    "type": "directory",
                    "path": str(dirpath),
                    "action": "would_delete"
                })
                return True
            
            if self.use_trash:
                # Move to trash
                send2trash(str(dirpath))
                self.deleted_items.append({
                    "type": "directory",
                    "path": str(dirpath),
                    "action": "moved_to_trash"
                })
            else:
                # Permanently delete
                dirpath.rmdir()
                self.deleted_items.append({
                    "type": "directory",
                    "path": str(dirpath),
                    "action": "deleted"
                })
            return True
        except Exception as e:
            self.errors.append({
                "type": "directory",
                "path": str(dirpath),
                "error": str(e)
            })
            return False
    
    def delete(self, empty_files: List[Path], empty_dirs: List[Path]) -> Dict[str, Any]:
        """Delete empty files and directories."""
        # Process files first, then directories (bottom-up)
        # Reverse the directory list so we process deepest first
        empty_dirs = empty_dirs[::-1]
        
        file_count = 0
        dir_count = 0
        
        # Delete files
        for filepath in empty_files:
            if self._delete_file(filepath):
                file_count += 1
        
        # Delete directories
        for dirpath in empty_dirs:
            if self._delete_directory(dirpath):
                dir_count += 1
        
        return {
            "files_deleted": file_count,
            "dirs_deleted": dir_count,
            "total_deleted": file_count + dir_count,
            "errors": self.errors,
            "deleted_items": self.deleted_items
        }
    
    def generate_manifest(self, output_dir: str = ".") -> str:
        """Generate a manifest file with details of all operations."""
        manifest = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "use_trash": self.use_trash,
            "operations": self.deleted_items,
            "errors": self.errors,
            "stats": {
                "files_processed": len([item for item in self.deleted_items if item["type"] == "file"]),
                "dirs_processed": len([item for item in self.deleted_items if item["type"] == "directory"]),
                "errors_count": len(self.errors)
            }
        }
        
        manifest_filename = generate_manifest_filename()
        manifest_path = Path(output_dir) / manifest_filename
        
        try:
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            return str(manifest_path)
        except Exception as e:
            raise Exception(f"Failed to write manifest file: {e}")