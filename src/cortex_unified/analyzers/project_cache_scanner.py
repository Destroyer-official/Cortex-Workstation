"""Auto-discovery of project cache folders across fixed drives.

Without this, ``PackageManagerCleaner.scan_caches`` only finds project caches
when the caller already knows the parent folder (``target_folders``). Manual
cleaning hit 21.9GB in ``NexusExplorer/{target,src-tauri/target,...}`` and
~3GB in ``AEGIS/*/target`` that the UI never surfaced because D:\\code was
never scanned. This module walks all fixed drives (psutil.disk_partitions)
shallowly for PROJECT_CACHE_CATEGORIES patterns without requiring the user to
pick the exact folder, while pruning .git / node_modules already in the skip
set.
"""

from __future__ import annotations

import os
import platform
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from cortex_unified.analyzers.package_manager_cleaner import PROJECT_CACHE_CATEGORIES

_LOG = logging.getLogger(__name__)

# Directories we never descend into (huge/irrelevant/sensitive) - reuse + extend
_SKIP_NAMES = {
    "node_modules", ".git", ".svn", "windows", "winsxs", "system32",
    "syswow64", "$recycle.bin", "system volume information", "assembly",
    "installer", "drivers", "sourceengine",
    ".cargo", ".rustup", "scoop",
}

# Extra prunes for drive-level walks to keep scans cheap
_DRIVE_SKIP_PREFIXES = {".", "$"}


def _fixed_drive_roots() -> List[Path]:
    """Return fixed-drive mount points (C:\\, D:\\ ...) on Windows, or [home] elsewhere."""
    if platform.system() != "Windows":
        return [Path.home()]
    roots: List[Path] = []
    try:
        import psutil
        for p in psutil.disk_partitions(all=False):
            opts = (getattr(p, "opts", "") or "").lower()
            fstype = (getattr(p, "fstype", "") or "").lower()
            # Windows apps: opts often empty; fstype ntfs/refs is reliable
            if "fixed" in opts or fstype in ("ntfs", "refs") or (len(p.mountpoint) == 3 and p.mountpoint[1] == ":"):
                try:
                    pp = Path(p.mountpoint)
                    if pp.is_dir():
                        roots.append(pp)
                except OSError:
                    continue
        if roots:
            return roots
    except Exception as exc:  # noqa: BLE001
        _LOG.debug("psutil fixed-drive detection failed: %s", exc)
    # Fallback: brute probe C-Z
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        d = Path(f"{letter}:\\")
        try:
            if d.is_dir():
                roots.append(d)
        except OSError:
            continue
    return roots or [Path.home()]


def _known_code_roots() -> List[Path]:
    """High-hit-rate code parents to prefer over whole-drive walks.
    
    Dynamically probes all detected fixed drives and user home directories
    for standard development roots (code, Projects, Main_projects, Repos, workspace, etc.).
    """
    candidates: List[Path] = []
    
    # 1. User profile development folders
    home = Path.home()
    user_dev_subdirs = [
        "code", "Projects", "Main_projects", "Development", "Repos", "workspace", "src", "git", "dev",
        "Documents/code", "Documents/Projects", "Documents/Main_projects", "Documents/Development",
        "source/repos", "IdeaProjects", "go/src", "PycharmProjects", "AndroidStudioProjects",
        "Desktop/code", "Desktop/Projects"
    ]
    for sub in user_dev_subdirs:
        candidates.append(home / sub)
        
    # 2. Environment variables if set
    for env_var in ("WORKSPACE", "SRC", "PROJECTS_DIR", "DEV_DIR", "GOPATH"):
        val = os.environ.get(env_var)
        if val:
            candidates.append(Path(val))

    # 3. All detected fixed drives (C:, D:, E:, etc.)
    fixed_drives = _fixed_drive_roots()
    drive_dev_names = [
        "code", "Projects", "Main_projects", "Development", "Repos", "workspace", "src", "git", "dev"
    ]
    for drive in fixed_drives:
        for name in drive_dev_names:
            candidates.append(drive / name)

    out: List[Path] = []
    seen: set[str] = set()
    for p in candidates:
        try:
            resolved = p.resolve()
            p_str = str(resolved).lower()
            if p_str not in seen and resolved.is_dir():
                seen.add(p_str)
                out.append(resolved)
        except OSError:
            continue
    return out


class ProjectCacheScanner:
    """Drive-aware scanner for PROJECT_CACHE_CATEGORIES patterns.

    Usage:
        scanner = ProjectCacheScanner(enabled_categories=["rust_go", "node"])
        resources = scanner.scan_fixed_drives()
        # resources are dicts compatible with PackageManagerCleaner.cleanup_caches
    """

    def __init__(
        self,
        enabled_categories: Optional[List[str]] = None,
        keep_recent_days: int = 7,
    ):
        self.enabled_categories = enabled_categories
        self.keep_recent_days = keep_recent_days
        self.logger = logging.getLogger(__name__)
        # Build active pattern map: name -> (category_id, description)
        self._pattern_map: Dict[str, tuple[str, str]] = {}
        target_cats = enabled_categories if enabled_categories else list(PROJECT_CACHE_CATEGORIES.keys())
        for cat_id in target_cats:
            if cat_id in PROJECT_CACHE_CATEGORIES:
                for pat, desc in PROJECT_CACHE_CATEGORIES[cat_id]["patterns"].items():
                    self._pattern_map[pat] = (cat_id, desc)
        """__init__."""
        """__init__."""

    def scan_fixed_drives(
        self,
        progress_callback: Optional[object] = None,
        cancel_event: Optional[object] = None,
        max_depth: int = 5,
        prefer_code_roots: bool = True,
    ) -> List[Dict]:
        """Scan all fixed drives (or known code roots) for project caches."""
        resources: List[Dict] = []
        roots = _known_code_roots() if prefer_code_roots else []
        if roots:
            # Prefer code roots - they are deep trees; allow unlimited depth there
            for root in roots:
                if cancel_event and getattr(cancel_event, 'is_set', lambda: False)():
                    break
                resources.extend(self._scan_root(root, keep_recent_days=self.keep_recent_days,
                                                 progress_callback=progress_callback,
                                                 cancel_event=cancel_event,
                                                 max_depth=None))
            # Also do a shallow sweep of drive roots to catch stray projects outside D:\code
            drive_roots = [r for r in _fixed_drive_roots() if r not in roots]
            for root in drive_roots:
                if cancel_event and getattr(cancel_event, 'is_set', lambda: False)():
                    break
                resources.extend(self._scan_root(root, keep_recent_days=self.keep_recent_days,
                                                 progress_callback=progress_callback,
                                                 cancel_event=cancel_event,
                                                 max_depth=max_depth))
        else:
            for root in _fixed_drive_roots():
                if cancel_event and getattr(cancel_event, 'is_set', lambda: False)():
                    break
                resources.extend(self._scan_root(root, keep_recent_days=self.keep_recent_days,
                                                 progress_callback=progress_callback,
                                                 cancel_event=cancel_event,
                                                 max_depth=max_depth))
        return resources

    def _scan_root(
        self,
        folder: Path,
        keep_recent_days: int = 0,
        progress_callback: Optional[object] = None,
        cancel_event: Optional[object] = None,
        max_depth: Optional[int] = None,
    ) -> List[Dict]:
        """Walk *folder* matching dir names against PROJECT_CACHE_CATEGORIES."""
        from datetime import datetime as _dt
        resources: List[Dict] = []
        cutoff_date = _dt.now() - timedelta(days=keep_recent_days) if keep_recent_days > 0 else None

        def _match_dir(d_name: str):
            if d_name in self._pattern_map:
                return self._pattern_map[d_name]
            for pat, (cat_id, desc) in self._pattern_map.items():
                if pat.startswith(".") and d_name.endswith(pat):
                    return (cat_id, desc)
                if pat.endswith("*") and d_name.startswith(pat.rstrip("*")):
                    return (cat_id, desc)
            return None
            """_match_dir."""
            """_match_dir."""

        # Iterative stack: (path, depth)
        stack: List[tuple[Path, int]] = [(folder, 0)]

        total_items = 0
        total_size = 0

        # We use os.scandir for speed, with explicit skip logic
        def _should_skip_dir(name: str) -> bool:
            low = name.lower()
            if low in _SKIP_NAMES:
                return True
            if low.startswith("$") or low.startswith(".") and low not in (".cargo", ".rustup"):
                # Keep .cargo etc. at top level but skip hidden elsewhere
                if name.startswith("."):
                    # Allow scanning for .cache/.cargo as patterns but don't descend into random hidden
                    if name not in self._pattern_map and not any(name.endswith(p) for p in self._pattern_map):
                        # Still descend into e.g. D:\code\project\.venv? That starts with ., so we must NOT skip
                        # Only skip truly hidden meta dirs like .git
                        if name in (".git", ".hg", ".svn"):
                            return True
            return False
            """_should_skip_dir."""
            """_should_skip_dir."""

        # For simplicity, use os.walk with pruning when max_depth is None (deep code roots)
        # For drive roots with max_depth, use stack-bounded walk.
        try:
            if max_depth is None:
                for root, dirs, files in os.walk(folder):
                    if cancel_event and getattr(cancel_event, 'is_set', lambda: False)():
                        break
                    # Prune skips before descending, but keep any dir that is a cache pattern (e.g. node_modules)
                    def _keep_for_scan(n: str) -> bool:
                        if _match_dir(n):
                            return True
                        if n.lower() in _SKIP_NAMES:
                            return False
                        if n.startswith("$"):
                            return False
                        return True
                        """_keep_for_scan."""
                        """_keep_for_scan."""
                    dirs[:] = [d for d in dirs if _keep_for_scan(d)]
                    dirs_to_remove = []
                    for d in list(dirs):
                        match = _match_dir(d)
                        if match:
                            cat_id, description = match
                            dir_path = Path(root) / d
                            try:
                                dir_size, file_cnt = self._get_dir_size(dir_path, cutoff_date)
                                if file_cnt > 0:
                                    total_size += dir_size
                                    total_items += 1
                                    project_name = dir_path.parent.name or folder.name
                                    resources.append({
                                        "type": "project_cache",
                                        "category": cat_id,
                                        "path": str(dir_path),
                                        "name": project_name,
                                        "cache_name": d,
                                        "size": dir_size,
                                        "file_count": file_cnt,
                                        "description": f"{description} ({d})",
                                        "manager_name": PROJECT_CACHE_CATEGORIES.get(cat_id, {}).get("label", cat_id.title())
                                    })
                                    if progress_callback and callable(progress_callback):
                                        progress_callback(
                                            f"Found {d} in {project_name} ({self._format_bytes(dir_size)})",
                                            total_items, total_size)
                                dirs_to_remove.append(d)
                            except Exception:
                                continue
                    for d in dirs_to_remove:
                        if d in dirs:
                            dirs.remove(d)
            else:
                # Depth-limited stack walk for whole-drive scans
                stack = [(folder, 0)]
                visited: set[str] = set()
                while stack:
                    if cancel_event and getattr(cancel_event, 'is_set', lambda: False)():
                        break
                    cur, depth = stack.pop()
                    if depth > max_depth:
                        continue
                    key = str(cur).lower()
                    if key in visited:
                        continue
                    visited.add(key)
                    try:
                        entries = list(os.scandir(cur))
                    except OSError:
                        continue
                    dirs_here: List[Path] = []
                    for entry in entries:
                        try:
                            if not entry.is_dir(follow_symlinks=False):
                                continue
                            name = entry.name
                            match = _match_dir(name)
                            if match:
                                # Cache pattern takes precedence over skip (e.g. node_modules)
                                pass
                            elif name.lower() in _SKIP_NAMES or name.startswith("$"):
                                continue
                            if match:
                                cat_id, description = match
                                dir_path = Path(entry.path)
                                try:
                                    dir_size, file_cnt = self._get_dir_size(dir_path, cutoff_date)
                                    if file_cnt > 0:
                                        total_size += dir_size
                                        total_items += 1
                                        project_name = dir_path.parent.name or folder.name
                                        resources.append({
                                            "type": "project_cache",
                                            "category": cat_id,
                                            "path": str(dir_path),
                                            "name": project_name,
                                            "cache_name": name,
                                            "size": dir_size,
                                            "file_count": file_cnt,
                                            "description": f"{description} ({name})",
                                            "manager_name": PROJECT_CACHE_CATEGORIES.get(cat_id, {}).get("label", cat_id.title())
                                        })
                                        if progress_callback and callable(progress_callback):
                                            progress_callback(
                                                f"Found {name} in {project_name} ({self._format_bytes(dir_size)})",
                                                total_items, total_size)
                                except Exception:
                                    continue
                                # Do not descend into a matched cache folder
                                continue
                            dirs_here.append(Path(entry.path))
                        except OSError:
                            continue
                    for d in dirs_here:
                        stack.append((d, depth + 1))
        except Exception as e:
            self.logger.error("Error scanning %s: %s", folder, e)
        return resources

    def _get_dir_size(self, path: Path, cutoff_date: Optional[datetime] = None) -> tuple[int, int]:
        total = 0
        cnt = 0
        try:
            for root, _, files in os.walk(path):
                for f in files:
                    fp = Path(root) / f
                    try:
                        st = fp.stat()
                        if cutoff_date and datetime.fromtimestamp(st.st_mtime) >= cutoff_date:
                            continue
                        total += st.st_size
                        cnt += 1
                    except OSError:
                        continue
        except OSError:
            pass
        return total, cnt
        """_get_dir_size."""
        """_get_dir_size."""

    @staticmethod
    def _format_bytes(n: int) -> str:
        size = float(n)
        for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
            if size < 1024 or unit == 'PB':
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{n} B"
        """_format_bytes."""
        """_format_bytes."""
