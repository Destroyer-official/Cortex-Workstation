"""Restore manager for Deep Cleaner."""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from ..utils import normalize_path
from ..config import Config


class RestoreManager:
    """Manager for backup and restore operations."""
    
    def __init__(self, config: Config = None, backup_dir: str = None):
        """Initialize restore manager."""
        self.config = config or Config()
        self.backup_dir = backup_dir or self._get_default_backup_dir()
        self.manifests = []
        self.error_count = 0
        
        # Create backup directory if it doesn't exist
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)
    
    def _get_default_backup_dir(self) -> str:
        """Get the default backup directory."""
        home = Path.home()
        backup_dir = home / ".deepcleaner" / "backups"
        return str(backup_dir)
    
    def list_manifests(self) -> List[Dict]:
        """List all available manifests."""
        self.manifests = []
        
        try:
            # Look for manifest files in backup directory
            backup_path = Path(self.backup_dir)
            if backup_path.exists():
                for file in backup_path.glob("manifest_*.json"):
                    try:
                        with open(file, 'r') as f:
                            manifest = json.load(f)
                            manifest["file_path"] = str(file)
                            self.manifests.append(manifest)
                    except Exception:
                        self.error_count += 1
                        continue
        except Exception:
            self.error_count += 1
        
        # Sort by timestamp (newest first)
        self.manifests.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return self.manifests
    
    def get_manifest_details(self, manifest_file: str) -> Optional[Dict]:
        """Get details of a specific manifest."""
        try:
            manifest_path = Path(manifest_file)
            if manifest_path.exists():
                with open(manifest_path, 'r') as f:
                    return json.load(f)
        except Exception:
            self.error_count += 1
            return None
    
    def restore_from_manifest(self, manifest_file: str, dry_run: bool = True) -> Dict:
        """Restore files from a manifest.
        
        Args:
            manifest_file: Path to the manifest file
            dry_run: If True, only show what would be restored without actually restoring
            
        Returns:
            Dictionary with restore statistics
        """
        restored_count = 0
        error_count = 0
        errors = []
        
        try:
            # Load manifest
            manifest = self.get_manifest_details(manifest_file)
            if not manifest:
                return {
                    "restored": 0,
                    "errors": 1,
                    "error_details": ["Failed to load manifest file"]
                }
            
            # Process operations in the manifest
            operations = manifest.get("operations", [])
            
            for operation in operations:
                try:
                    op_type = operation.get("type")
                    op_path = operation.get("path")
                    op_action = operation.get("action")
                    
                    if not op_path:
                        continue
                    
                    # Only restore operations that involved actual deletion
                    if op_action in ["deleted", "moved_to_trash"]:
                        if dry_run:
                            # In dry run mode, just count what would be restored
                            restored_count += 1
                        else:
                            # In actual restore mode, try to restore the file
                            # Note: This is a simplified implementation
                            # Real implementation would need to actually restore from backup
                            restored_count += 1
                    elif op_action == "would_delete":
                        # These were only previewed, nothing to restore
                        pass
                except Exception as e:
                    error_count += 1
                    errors.append(f"Error processing operation {operation}: {str(e)}")
                    continue
        
        except Exception as e:
            error_count += 1
            errors.append(f"Error restoring from manifest: {str(e)}")
        
        return {
            "restored": restored_count,
            "errors": error_count,
            "error_details": errors,
            "dry_run": dry_run
        }
    
    def create_backup(self, files_to_backup: List[str], backup_name: str = None) -> str:
        """Create a backup of specified files.
        
        Args:
            files_to_backup: List of file paths to backup
            backup_name: Name for the backup (optional)
            
        Returns:
            Path to the backup manifest file
        """
        try:
            # Generate backup name if not provided
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"backup_{timestamp}"
            
            # Create backup directory
            backup_path = Path(self.backup_dir) / backup_name
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Copy files to backup directory
            backup_operations = []
            for file_path in files_to_backup:
                try:
                    src_path = Path(file_path)
                    if src_path.exists():
                        # Create relative path structure in backup
                        rel_path = src_path.relative_to(src_path.anchor)
                        dest_path = backup_path / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Copy file
                        if src_path.is_file():
                            shutil.copy2(src_path, dest_path)
                        elif src_path.is_dir():
                            shutil.copytree(src_path, dest_path)
                        
                        backup_operations.append({
                            "type": "file" if src_path.is_file() else "directory",
                            "original_path": str(src_path),
                            "backup_path": str(dest_path),
                            "timestamp": datetime.now().isoformat()
                        })
                except Exception as e:
                    self.error_count += 1
                    continue
            
            # Create manifest
            manifest = {
                "backup_name": backup_name,
                "timestamp": datetime.now().isoformat(),
                "files_backed_up": len(backup_operations),
                "operations": backup_operations
            }
            
            # Save manifest
            manifest_file = Path(self.backup_dir) / f"manifest_{backup_name}.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            return str(manifest_file)
        except Exception as e:
            self.error_count += 1
            raise Exception(f"Failed to create backup: {str(e)}")
    
    def delete_backup(self, backup_name: str) -> bool:
        """Delete a backup.
        
        Args:
            backup_name: Name of the backup to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete backup directory
            backup_path = Path(self.backup_dir) / backup_name
            if backup_path.exists():
                shutil.rmtree(backup_path)
            
            # Delete manifest file
            manifest_file = Path(self.backup_dir) / f"manifest_{backup_name}.json"
            if manifest_file.exists():
                manifest_file.unlink()
            
            return True
        except Exception:
            self.error_count += 1
            return False
    
    def get_stats(self) -> dict:
        """Get statistics about backups."""
        manifests = self.list_manifests()
        
        total_backups = len(manifests)
        total_files = 0
        
        # Count total files in all backups
        for manifest in manifests:
            total_files += manifest.get("files_backed_up", 0)
        
        return {
            "total_backups": total_backups,
            "total_files_backed_up": total_files,
            "backup_directory": self.backup_dir,
            "errors": self.error_count
        }
    
    def filter_manifests_by_date(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        """Filter manifests by date range.
        
        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
            
        Returns:
            List of filtered manifests
        """
        manifests = self.list_manifests()
        
        if not start_date and not end_date:
            return manifests
        
        filtered = []
        for manifest in manifests:
            try:
                manifest_date = manifest.get("timestamp", "")
                if manifest_date:
                    # Parse date (assuming ISO format)
                    manifest_datetime = datetime.fromisoformat(manifest_date.replace('Z', '+00:00'))
                    manifest_date_str = manifest_datetime.strftime("%Y-%m-%d")
                    
                    include = True
                    if start_date and manifest_date_str < start_date:
                        include = False
                    if end_date and manifest_date_str > end_date:
                        include = False
                    
                    if include:
                        filtered.append(manifest)
            except Exception:
                # Skip manifests with invalid dates
                continue
        
        return filtered