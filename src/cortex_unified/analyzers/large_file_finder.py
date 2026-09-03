"""Discovery of files above a configurable size threshold.

Results are sorted largest-first so callers can present the biggest
reclamation opportunities without further processing.
"""

import os
from pathlib import Path
from typing import List, Dict, Tuple
import threading

from cortex_unified.core.utils import normalize_path
from cortex_unified.core.config import Config

# AI model extensions surfaced separately: models are 1-2GB each,
# re-downloadable but HIGH-risk to delete (user may have no backup).
AI_MODEL_EXTENSIONS = {
    ".gguf", ".safetensors", ".onnx", ".bin",
    ".pt", ".pth", ".ckpt", ".h5", ".hdf5",
    ".model", ".weights", ".safetensor",
}
# Companion extensions for logs that should be excluded from large-file AI surfacing
ARCHIVE_EXCLUDES = {".zip", ".tar", ".gz", ".tgz", ".rar", ".7z"}


def is_ai_model(path: Path) -> bool:
    """True when *path* looks like an LLM / diffusion model file."""
    return path.suffix.lower() in AI_MODEL_EXTENSIONS


class LargeFileFinder:
    """Finds files larger than a size threshold under a root directory."""
    
    def __init__(self, config: Config = None, root_path: str = "."):
        """
        Args:
            config: Exclusion rules; defaults to ``Config()``.
            root_path: Directory tree to search.
        """
        self.config = config or Config()
        self.root_path = normalize_path(root_path)
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)
        self.follow_symlinks = self.config.follow_symlinks
        self.min_size_mb = 100
        
        # Counters are updated from the walk; the lock keeps concurrent
        # callers from losing increments.
        self._lock = threading.Lock()
        
        # (filepath, size_bytes) pairs, largest first after find_large_files().
        self.large_files: List[Tuple[Path, int]] = []
        self.file_count = 0
        self.error_count = 0
    
    def _should_exclude_path(self, path: Path) -> bool:
        """True when *path* hits an excluded directory name or pattern."""
        if path.name in self.exclude_dirs:
            return True
        
        path_str = str(path)
        for pattern in self.exclude_patterns:
            if pattern in path_str or pattern in path.name:
                return True
        
        return False
    
    def _get_file_size(self, filepath: Path) -> int:
        """Size in bytes, or -1 when the file cannot be stat'ed."""
        try:
            return filepath.stat().st_size
        except Exception:
            return -1
    
    def find_large_files(self, min_size_mb: int = None, threads: int = 0) -> List[Tuple[Path, int]]:
        """Find files larger than the specified size threshold.
        
        Args:
            min_size_mb: Minimum file size in MB (defaults to self.min_size_mb)
            threads: Accepted for interface parity; os.walk is single-threaded.
        """
        if min_size_mb is None:
            min_size_mb = self.min_size_mb
        
        min_size_bytes = min_size_mb * 1024 * 1024
        
        if threads <= 0:
            threads = min(32, os.cpu_count() + 4)
        
        self.large_files = []
        
        try:
            for root, dirs, files in os.walk(self.root_path):
                # Prune excluded directories before descending (os.walk idiom).
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                
                if not self.follow_symlinks:
                    dirs[:] = [d for d in dirs if not (Path(root) / d).is_symlink()]
                
                root_path = Path(root)
                if self._should_exclude_path(root_path):
                    dirs[:] = []
                    continue
                
                for file in files:
                    filepath = root_path / file
                    if self._should_exclude_path(filepath):
                        continue
                    
                    try:
                        if filepath.is_symlink() and not self.follow_symlinks:
                            continue
                        
                        size = self._get_file_size(filepath)
                        if size <= 0:
                            continue
                        
                        with self._lock:
                            self.file_count += 1
                        
                        if size >= min_size_bytes:
                            self.large_files.append((filepath, size))
                    except Exception:
                        with self._lock:
                            self.error_count += 1
                        continue
        except Exception:
            pass
        
        self.large_files.sort(key=lambda x: x[1], reverse=True)
        return self.large_files
    
    def get_stats(self) -> dict:
        """Get statistics about the large file finding process."""
        total_size = sum(size for _, size in self.large_files)
        ai_models = self.get_ai_models()
        ai_size = sum(s for _, s in ai_models)
        return {
            "total_files_scanned": self.file_count,
            "large_files_found": len(self.large_files),
            "total_size_bytes": total_size,
            "total_size_human": self._format_bytes(total_size),
            "ai_models_found": len(ai_models),
            "ai_models_size_bytes": ai_size,
            "ai_models_size_human": self._format_bytes(ai_size),
            "errors": self.error_count
        }
    
    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes into human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"
    
    def filter_by_size(self, min_size_mb: int, max_size_mb: int = None) -> List[Tuple[Path, int]]:
        """Filter large files by size range.
        
        Args:
            min_size_mb: Minimum file size in MB
            max_size_mb: Maximum file size in MB (optional)
        """
        min_bytes = min_size_mb * 1024 * 1024
        if max_size_mb:
            max_bytes = max_size_mb * 1024 * 1024
            return [(path, size) for path, size in self.large_files 
                   if min_bytes <= size <= max_bytes]
        else:
            return [(path, size) for path, size in self.large_files 
                   if size >= min_bytes]
    
    def group_by_extension(self) -> Dict[str, List[Tuple[Path, int]]]:
        """Group large files by file extension."""
        extension_groups: Dict[str, List[Tuple[Path, int]]] = {}
        
        for path, size in self.large_files:
            ext = path.suffix.lower()
            if ext not in extension_groups:
                extension_groups[ext] = []
            extension_groups[ext].append((path, size))
        
        return extension_groups

    def group_by_ai_models(self) -> Dict[str, List[Tuple[Path, int]]]:
        """Split large files into ``ai_models`` vs ``other`` for UI surfacing.

        Returns:
            Dict with keys ``ai_models`` and ``other``; ai_models holds
            (*.gguf, *.safetensors, ...) entries tagged HIGH-risk, disabled by default.
        """
        groups: Dict[str, List[Tuple[Path, int]]] = {"ai_models": [], "other": []}
        for path, size in self.large_files:
            if is_ai_model(path):
                groups["ai_models"].append((path, size))
            else:
                groups["other"].append((path, size))
        return groups

    def get_ai_models(self, min_size_mb: int = 100) -> List[Tuple[Path, int]]:
        """Return only AI model files among large files (for HIGH-risk UI)."""
        min_bytes = min_size_mb * 1024 * 1024
        return [(p, s) for p, s in self.large_files if is_ai_model(p) and s >= min_bytes]

    def tag_file(self, path: Path) -> str:
        """Return a display tag for a large file (ai_models, video, archive, etc.)."""
        ext = path.suffix.lower()
        if ext in AI_MODEL_EXTENSIONS:
            return "ai_models"
        if ext in {".mp4", ".mkv", ".avi", ".mov", ".webm"}:
            return "video"
        if ext in ARCHIVE_EXCLUDES:
            return "archive"
        if ext in {".log", ".txt"}:
            return "log"
        return "other"