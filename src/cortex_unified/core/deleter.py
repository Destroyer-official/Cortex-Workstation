"""File and directory deletion functionality for Cortex Cleaner."""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

try:
    from send2trash import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False

from cortex_unified.core.utils import generate_manifest_filename
from cortex_unified.core.security import check_deletion_safety

class Deleter:
    """Removes empty files and directories, recording every outcome.

    Two independent switches control behaviour: ``dry_run`` records what
    would happen without touching the filesystem, and ``use_trash`` routes
    real deletions through the recycle bin (send2trash) instead of an
    irreversible ``unlink``/``rmdir``.
    """

    def __init__(self, dry_run: bool = True, use_trash: bool = False):
        """Create a deleter.

        Args:
            dry_run: Record intended deletions without touching disk.
            use_trash: Send items to the recycle bin instead of deleting
                them outright. Silently disabled when send2trash is not
                installed.
        """
        self.dry_run = dry_run
        self.use_trash = use_trash and HAS_SEND2TRASH
        self.deleted_items = []
        self.errors = []
    
    def _delete_file(self, filepath: Path) -> bool:
        """Remove one file, or record it when running as a dry run.

        Returns:
            True on success, including a successful dry-run recording.
            False after appending the failure reason to ``errors``.
        """
        try:
            # The safety gate only runs for real deletions; in dry-run mode
            # nothing is touched, so the check would be wasted work.
            if not self.dry_run:
                is_safe, reason = check_deletion_safety(filepath, allow_system_files=False)
                if not is_safe:
                    self.errors.append({
                        "type": "file",
                        "path": str(filepath),
                        "error": f"Security check failed: {reason}"
                    })
                    return False
            
            if self.dry_run:
                self.deleted_items.append({
                    "type": "file",
                    "path": str(filepath),
                    "action": "would_delete"
                })
                return True

            if self.use_trash:
                send2trash(str(filepath))
                self.deleted_items.append({
                    "type": "file",
                    "path": str(filepath),
                    "action": "moved_to_trash"
                })
            else:
                filepath.unlink()
                self.deleted_items.append({
                    "type": "file",
                    "path": str(filepath),
                    "action": "deleted"
                })
            return True
        except Exception as e:
            # One unreadable/locked path must not abort a batch run, so
            # failures are recorded instead of raised.
            self.errors.append({
                "type": "file",
                "path": str(filepath),
                "error": str(e)
            })
            return False
    
    def _delete_directory(self, dirpath: Path) -> bool:
        """Remove one directory, or record it when running as a dry run.

        Uses ``rmdir``, which only succeeds on empty directories; callers
        must guarantee the directory has already been emptied.
        """
        try:
            if self.dry_run:
                self.deleted_items.append({
                    "type": "directory",
                    "path": str(dirpath),
                    "action": "would_delete"
                })
                return True

            if self.use_trash:
                send2trash(str(dirpath))
                self.deleted_items.append({
                    "type": "directory",
                    "path": str(dirpath),
                    "action": "moved_to_trash"
                })
            else:
                dirpath.rmdir()
                self.deleted_items.append({
                    "type": "directory",
                    "path": str(dirpath),
                    "action": "deleted"
                })
            return True
        except Exception as e:
            # Same rationale as _delete_file: record and continue.
            self.errors.append({
                "type": "directory",
                "path": str(dirpath),
                "error": str(e)
            })
            return False
    
    def delete(self, empty_files: List[Path], empty_dirs: List[Path]) -> Dict[str, Any]:
        """Delete the given empty files and directories.

        Files are removed first, then directories deepest-first (the caller's
        list is reversed in place) so a child never outlives its parent --
        ``rmdir`` refuses to remove non-empty directories.
        """
        empty_dirs = empty_dirs[::-1]

        file_count = 0
        dir_count = 0

        for filepath in empty_files:
            if self._delete_file(filepath):
                file_count += 1

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
        """Write a JSON manifest describing every operation performed.

        Args:
            output_dir: Directory the manifest file is written to.

        Returns:
            Path of the written manifest.

        Raises:
            Exception: Re-raised with context if the manifest cannot be
                written; callers should surface this rather than lose the
                audit trail.
        """
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
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
            return str(manifest_path)
        except Exception as e:
            raise Exception(f"Failed to write manifest file: {e}")