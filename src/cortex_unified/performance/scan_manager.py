"""
Scan management with checkpoint and resume functionality.
"""

import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

@dataclass
class ScanCheckpoint:
    """Data structure for scan checkpoint information."""
    id: str
    timestamp: datetime
    current_path: str
    processed_paths: List[str]
    scan_state: Dict[str, Any]
    progress_percentage: float
    total_items: int
    processed_items: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanCheckpoint':
        """from_dict."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
        """from_dict."""
        """from_dict."""

@dataclass
class ScanProgress:
    """Data structure for scan progress information."""
    current_path: str
    processed_count: int
    total_count: int
    percentage: float
    elapsed_time: float
    is_paused: bool = False
    is_completed: bool = False

class ScanManager:
    """Manages scan operations with checkpoint and resume capabilities."""
    
    def __init__(self, config: Any = None):
        """Initialize scan manager with configuration."""
        self.config = config
        self._is_paused = False
        self._is_running = False
        self._current_checkpoint: Optional[ScanCheckpoint] = None
        self._scan_start_time = 0.0
        self._pause_lock = threading.Lock()
        self._progress_lock = threading.Lock()
        
        # Progress tracking
        self._current_path = ""
        self._processed_count = 0
        self._total_count = 0
        self._processed_paths: List[str] = []
        
        # Checkpoint storage
        self._checkpoint_dir = Path.home() / ".cortex_cleaner" / "checkpoints"
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def create_checkpoint(self, scan_state: Dict[str, Any]) -> str:
        """Create a checkpoint of current scan state."""
        checkpoint_id = str(uuid.uuid4())
        
        with self._progress_lock:
            progress_percentage = (
                (self._processed_count / self._total_count * 100) 
                if self._total_count > 0 else 0.0
            )
            
            checkpoint = ScanCheckpoint(
                id=checkpoint_id,
                timestamp=datetime.now(),
                current_path=self._current_path,
                processed_paths=self._processed_paths.copy(),
                scan_state=scan_state.copy(),
                progress_percentage=progress_percentage,
                total_items=self._total_count,
                processed_items=self._processed_count
            )
        
        # Save checkpoint to disk
        checkpoint_file = self._checkpoint_dir / f"{checkpoint_id}.json"
        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint.to_dict(), f, indent=2)
            
            # Also save scan state as JSON
            state_file = self._checkpoint_dir / f"{checkpoint_id}_state.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(scan_state, f, default=str)
                
            self._current_checkpoint = checkpoint
            return checkpoint_id
            
        except Exception as e:
            raise RuntimeError(f"Failed to create checkpoint: {e}")
    
    def load_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """Load scan state from checkpoint."""
        checkpoint_file = self._checkpoint_dir / f"{checkpoint_id}.json"
        state_file = self._checkpoint_dir / f"{checkpoint_id}_state.json"
        
        if not checkpoint_file.exists():
            raise FileNotFoundError(f"Checkpoint {checkpoint_id} not found")
        
        try:
            # Load checkpoint metadata
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            checkpoint = ScanCheckpoint.from_dict(checkpoint_data)
            
            # Load scan state
            scan_state = {}
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    scan_state = json.load(f)
            
            # Restore progress tracking
            with self._progress_lock:
                self._current_path = checkpoint.current_path
                self._processed_count = checkpoint.processed_items
                self._total_count = checkpoint.total_items
                self._processed_paths = checkpoint.processed_paths.copy()
                self._current_checkpoint = checkpoint
            
            return scan_state
            
        except Exception as e:
            raise RuntimeError(f"Failed to load checkpoint: {e}")
    
    def pause_scan(self) -> None:
        """Pause current scan operation."""
        with self._pause_lock:
            self._is_paused = True
    
    def resume_scan(self, checkpoint_id: Optional[str] = None) -> None:
        """Resume scan from checkpoint or current state."""
        with self._pause_lock:
            if checkpoint_id:
                # Load from specific checkpoint
                self.load_checkpoint(checkpoint_id)
            self._is_paused = False
    
    def is_paused(self) -> bool:
        """Check if scan is currently paused."""
        with self._pause_lock:
            return self._is_paused
    
    def wait_if_paused(self) -> None:
        """Wait while scan is paused."""
        while self.is_paused():
            time.sleep(0.1)
    
    def start_scan(self, total_items: int = 0) -> None:
        """Start a new scan operation."""
        with self._progress_lock:
            self._is_running = True
            self._is_paused = False
            self._scan_start_time = time.time()
            self._processed_count = 0
            self._total_count = total_items
            self._processed_paths = []
            self._current_path = ""
    
    def stop_scan(self) -> None:
        """Stop the current scan operation."""
        with self._progress_lock:
            self._is_running = False
            self._is_paused = False
    
    def update_progress(self, current_path: str, increment: int = 1) -> None:
        """Update scan progress."""
        with self._progress_lock:
            self._current_path = current_path
            self._processed_count += increment
            if current_path not in self._processed_paths:
                self._processed_paths.append(current_path)
    
    def get_scan_progress(self) -> ScanProgress:
        """Get current scan progress information."""
        with self._progress_lock:
            elapsed_time = time.time() - self._scan_start_time if self._is_running else 0.0
            percentage = (
                (self._processed_count / self._total_count * 100) 
                if self._total_count > 0 else 0.0
            )
            
            return ScanProgress(
                current_path=self._current_path,
                processed_count=self._processed_count,
                total_count=self._total_count,
                percentage=percentage,
                elapsed_time=elapsed_time,
                is_paused=self._is_paused,
                is_completed=not self._is_running and self._processed_count > 0
            )
    
    def list_checkpoints(self) -> List[ScanCheckpoint]:
        """List all available checkpoints."""
        checkpoints = []
        
        for checkpoint_file in self._checkpoint_dir.glob("*.json"):
            if not checkpoint_file.name.endswith("_state.json"):
                try:
                    with open(checkpoint_file, 'r', encoding='utf-8') as f:
                        checkpoint_data = json.load(f)
                    checkpoints.append(ScanCheckpoint.from_dict(checkpoint_data))
                except Exception:
                    # Skip corrupted checkpoints
                    continue
        
        # Sort by timestamp, newest first
        checkpoints.sort(key=lambda x: x.timestamp, reverse=True)
        return checkpoints
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a specific checkpoint."""
        checkpoint_file = self._checkpoint_dir / f"{checkpoint_id}.json"
        state_file = self._checkpoint_dir / f"{checkpoint_id}_state.json"
        
        deleted = False
        
        if checkpoint_file.exists():
            try:
                checkpoint_file.unlink()
                deleted = True
            except Exception:
                pass
        
        if state_file.exists():
            try:
                state_file.unlink()
            except Exception:
                pass
        
        return deleted
    
    def cleanup_old_checkpoints(self, max_age_days: int = 7) -> int:
        """Clean up checkpoints older than specified days."""
        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
        deleted_count = 0
        
        for checkpoint_file in self._checkpoint_dir.glob("*.json"):
            try:
                if checkpoint_file.stat().st_mtime < cutoff_time:
                    checkpoint_id = checkpoint_file.stem
                    if self.delete_checkpoint(checkpoint_id):
                        deleted_count += 1
            except Exception:
                continue
        
        return deleted_count