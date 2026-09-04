"""Atomic manifest creation and operation logging system."""

import json
import uuid
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import os

from cortex_unified.core.utils import DeepCleanerError, ensure_directory

class ManifestError(DeepCleanerError):
    """Manifesterror.

    Manages ManifestError operations and coordinates related state changes for the component.
    """
    pass

class ManifestSystem:
    """Manifestsystem.

    Manages ManifestSystem operations and coordinates related state changes for the component.
    """
    
    def __init__(self, manifest_dir: Optional[str] = None, logger: Optional[logging.Logger] = None):
        """Initialize manifest system.
        
        Args:
            manifest_dir: Directory to store manifests (optional)
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.manifest_dir = Path(manifest_dir) if manifest_dir else self._get_default_manifest_dir()
        
        # Ensure manifest directory exists
        try:
            ensure_directory(self.manifest_dir, create=True)
        except Exception as e:
            raise ManifestError(f"Failed to create manifest directory: {e}")
        
        self._current_operations: Dict[str, Dict] = {}
    
    def _get_default_manifest_dir(self) -> Path:
        """_get_default_manifest_dir.

        Manages get default manifest dir operations and coordinates related state changes for the component.

        Returns:
            Path: Result of the operation.
        """
        home = Path.home()
        return home / ".cortex_cleaner" / "manifests"
    
    def create_operation_manifest(self, operation_type: str, parameters: Dict[str, Any] = None) -> str:
        """Create atomic manifest with unique operation ID.
        
        Args:
            operation_type: Type of operation (e.g., 'clean', 'delete', 'move')
            parameters: Operation parameters
            
        Returns:
            Unique operation ID
            
        Raises:
            ManifestError: If manifest creation fails
        """
        try:
            # Generate unique operation ID
            timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            random_suffix = uuid.uuid4().hex[:6]
            op_id = f"{timestamp}_{random_suffix}"
            
            manifest = {
                "op_id": op_id,
                "timestamp": datetime.now().isoformat(),
                "user": self._get_user_info(),
                "os": self._get_os_info(),
                "operation": operation_type,
                "parameters": parameters or {},
                "options": {
                    "dry_run": parameters.get("dry_run", True) if parameters else True,
                    "ruleset": parameters.get("ruleset", "default") if parameters else "default"
                },
                "items": [],
                "summary": {
                    "files_processed": 0,
                    "dirs_processed": 0,
                    "errors_count": 0,
                    "bytes_processed": 0
                },
                "status": "created"
            }
            
            # Store in memory for atomic updates
            self._current_operations[op_id] = manifest
            
            self.logger.info(f"Created operation manifest: {op_id}")
            return op_id
            
        except Exception as e:
            raise ManifestError(f"Failed to create operation manifest: {e}")
    
    def _get_user_info(self) -> Dict[str, Any]:
        """Get current user information.

        Manages get user info operations and coordinates related state changes for the component.

        Returns:
            Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        try:
            import getpass
            user_info = {
                "username": getpass.getuser()
            }
            
            # Owner identity is only available on POSIX; recorded so a
            # restored file can be attributed correctly.
            if hasattr(os, 'getuid'):
                user_info["uid"] = os.getuid()
            
            return user_info
        except Exception:
            return {"username": "unknown"}
    
    def _get_os_info(self) -> str:
        """_get_os_info.

        Manages get os info operations and coordinates related state changes for the component.

        Returns:
            str: Formatted string or path.
        """
        try:
            import platform
            return f"{platform.system()} {platform.release()}"
        except Exception:
            return "unknown"
    
    def log_file_action(self, op_id: str, action_type: str, file_path: Path, 
                       action: str, **kwargs) -> None:
        """Log individual file operation.
        
        Args:
            op_id: Operation ID
            action_type: Type of item ('file' or 'directory')
            file_path: Path of the file/directory
            action: Action performed ('deleted', 'moved_to_trash', 'would_delete', etc.)
            **kwargs: Additional action details
        """
        try:
            if op_id not in self._current_operations:
                raise ManifestError(f"Operation {op_id} not found")
            
            manifest = self._current_operations[op_id]
            
            # Generate item ID
            item_id = str(len(manifest["items"]) + 1)
            
            action_entry = {
                "id": item_id,
                "type": action_type,
                "original_path": str(file_path.resolve()),
                "action": action,
                "timestamp": datetime.now().isoformat(),
                "status": "ok"
            }
            
            # Add file metadata if available
            try:
                if file_path.exists():
                    stat_info = file_path.stat()
                    action_entry.update({
                        "size": stat_info.st_size,
                        "modified_time": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        "permissions": oct(stat_info.st_mode)[-3:]
                    })
                    
                    # Add file hash for files (not directories)
                    if file_path.is_file() and stat_info.st_size < 100 * 1024 * 1024:  # < 100MB
                        action_entry["sha256"] = self._calculate_file_hash(file_path)
            except Exception as e:
                action_entry["metadata_error"] = str(e)
            
            # Add additional details from kwargs
            for key, value in kwargs.items():
                if key not in action_entry:
                    action_entry[key] = value
            
            manifest["items"].append(action_entry)
            
            if action_type == "file":
                manifest["summary"]["files_processed"] += 1
            elif action_type == "directory":
                manifest["summary"]["dirs_processed"] += 1
            
            if "size" in action_entry:
                manifest["summary"]["bytes_processed"] += action_entry["size"]
            
            self.logger.debug(f"Logged action for {op_id}: {action} on {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to log file action: {e}")
            # Don't raise exception to avoid breaking the main operation
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file.

        Manages calculate file hash operations and coordinates related state changes for the component.

        Args:
            file_path (Path): Filesystem path to the target file or directory.

        Returns:
            str: Formatted string or path.
        """
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return ""
    
    def log_error(self, op_id: str, error: Exception, context: Dict[str, Any] = None) -> None:
        """Log an error for an operation.
        
        Args:
            op_id: Operation ID
            error: Exception that occurred
            context: Additional error context
        """
        try:
            if op_id not in self._current_operations:
                return
            
            manifest = self._current_operations[op_id]
            
            # Initialize errors list if not exists
            if "errors" not in manifest:
                manifest["errors"] = []
            
            error_entry = {
                "timestamp": datetime.now().isoformat(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {}
            }
            
            manifest["errors"].append(error_entry)
            manifest["summary"]["errors_count"] += 1
            
            self.logger.debug(f"Logged error for {op_id}: {error}")
            
        except Exception as e:
            self.logger.error(f"Failed to log error: {e}")
    
    def finalize_manifest(self, op_id: str, success: bool = True) -> Path:
        """Finalize and atomically write manifest to disk.
        
        Args:
            op_id: Operation ID
            success: Whether operation completed successfully
            
        Returns:
            Path to the written manifest file
            
        Raises:
            ManifestError: If finalization fails
        """
        try:
            if op_id not in self._current_operations:
                raise ManifestError(f"Operation {op_id} not found")
            
            manifest = self._current_operations[op_id]
            
            manifest["status"] = "completed" if success else "failed"
            manifest["completion_time"] = datetime.now().isoformat()
            
            total_items = len(manifest["items"])
            manifest["summary"]["total_items"] = total_items
            
            # Temp-file + rename so a crash mid-write can never leave a
            # truncated (unrestorable) manifest behind.
            manifest_filename = f"manifest_{op_id}.json"
            manifest_path = self.manifest_dir / manifest_filename
            
            # Create temporary file in same directory for atomic move
            with tempfile.NamedTemporaryFile(
                mode='w', 
                dir=self.manifest_dir, 
                prefix=f"tmp_{manifest_filename}_",
                suffix='.json',
                delete=False
            ) as tmp_file:
                json.dump(manifest, tmp_file, indent=2, ensure_ascii=False)
                tmp_path = Path(tmp_file.name)
            
            # Atomic move
            tmp_path.replace(manifest_path)
            
            # Remove from memory
            del self._current_operations[op_id]
            
            self.logger.info(f"Finalized manifest: {manifest_path}")
            return manifest_path
            
        except Exception as e:
            # Clean up temporary file if it exists
            try:
                if 'tmp_path' in locals() and tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
            
            raise ManifestError(f"Failed to finalize manifest {op_id}: {e}")
    
    def get_restore_operations(self, manifest_path: Path) -> List[Dict[str, Any]]:
        """Generate restore actions from manifest.
        
        Args:
            manifest_path: Path to manifest file
            
        Returns:
            List of restore action dictionaries
            
        Raises:
            ManifestError: If manifest cannot be read or parsed
        """
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            restore_actions = []
            
            for item in manifest.get("items", []):
                action = item.get("action", "")
                
                # Only create restore actions for destructive operations
                if action in ["deleted", "moved_to_trash"]:
                    restore_action = {
                        "type": "restore",
                        "original_path": item["original_path"],
                        "item_type": item["type"],
                        "restore_from": item.get("trash_path") or item.get("backup_path"),
                        "original_size": item.get("size"),
                        "original_hash": item.get("sha256"),
                        "operation_id": manifest["op_id"]
                    }
                    
                    # Add parent directory creation if needed
                    original_path = Path(item["original_path"])
                    if not original_path.parent.exists():
                        restore_actions.append({
                            "type": "create_directory",
                            "path": str(original_path.parent),
                            "operation_id": manifest["op_id"]
                        })
                    
                    restore_actions.append(restore_action)
            
            return restore_actions
            
        except Exception as e:
            raise ManifestError(f"Failed to generate restore operations: {e}")
    
    def list_manifests(self, limit: int = None) -> List[Dict[str, Any]]:
        """List available manifests.
        
        Args:
            limit: Maximum number of manifests to return
            
        Returns:
            List of manifest summaries
        """
        try:
            manifests = []
            
            # Find all manifest files
            for manifest_file in self.manifest_dir.glob("manifest_*.json"):
                try:
                    with open(manifest_file, 'r') as f:
                        manifest = json.load(f)
                    
                    summary = {
                        "file_path": str(manifest_file),
                        "op_id": manifest.get("op_id"),
                        "timestamp": manifest.get("timestamp"),
                        "operation": manifest.get("operation"),
                        "status": manifest.get("status"),
                        "items_count": len(manifest.get("items", [])),
                        "files_processed": manifest.get("summary", {}).get("files_processed", 0),
                        "dirs_processed": manifest.get("summary", {}).get("dirs_processed", 0),
                        "bytes_processed": manifest.get("summary", {}).get("bytes_processed", 0),
                        "errors_count": manifest.get("summary", {}).get("errors_count", 0)
                    }
                    
                    manifests.append(summary)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to read manifest {manifest_file}: {e}")
                    continue
            
            # Sort by timestamp (newest first)
            manifests.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            if limit:
                manifests = manifests[:limit]
            
            return manifests
            
        except Exception as e:
            self.logger.error(f"Failed to list manifests: {e}")
            return []
    
    def get_manifest_details(self, manifest_path: Path) -> Optional[Dict[str, Any]]:
        """Get full details of a specific manifest.
        
        Args:
            manifest_path: Path to manifest file
            
        Returns:
            Full manifest dictionary or None if not found
        """
        try:
            with open(manifest_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to read manifest {manifest_path}: {e}")
            return None
    
    def cleanup_old_manifests(self, keep_days: int = 30) -> int:
        """Clean up old manifest files.
        
        Args:
            keep_days: Number of days to keep manifests
            
        Returns:
            Number of manifests cleaned up
        """
        try:
            cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 3600)
            cleaned_count = 0
            
            for manifest_file in self.manifest_dir.glob("manifest_*.json"):
                try:
                    if manifest_file.stat().st_mtime < cutoff_time:
                        manifest_file.unlink()
                        cleaned_count += 1
                        self.logger.debug(f"Cleaned up old manifest: {manifest_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up manifest {manifest_file}: {e}")
            
            self.logger.info(f"Cleaned up {cleaned_count} old manifests")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old manifests: {e}")
            return 0