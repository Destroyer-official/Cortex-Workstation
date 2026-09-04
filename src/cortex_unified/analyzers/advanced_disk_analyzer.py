"""Advanced Disk Analyzer — scandir walk, treemap/sunburst, cloud targets.

Research grounding
------------------
* WizTree: reads NTFS Master File Table directly, scans multi-TB in seconds.
* WinDirStat 2.x (2024 rewrite): multi-threaded, NTFS MFT support, treemap.
* TreeSize Professional: scans SharePoint, S3, Azure, Linux/SSH; dedup via
  NTFS hardlinks; scheduled scans with email; PDF/Excel/HTML/XML export.
* FolderSizes: 4 chart types (treemap, sunburst, bar, pie), 13 file reports,
  snapshots with point-in-time comparison, trend analyzer, capacity planning.
* SpaceSniffer: portable, animated treemap real-time during scan.
* RidNacs: lightweight, fast, portable.

Why this matters for Cortex Cleaner
-----------------------------------
* os.walk is orders of magnitude slower on modern NVMe.
* Direct MFT parsing (Windows) or ioctl/fiemap (Linux) or getattrlistbulk
  (macOS) brings scan times from minutes to seconds.
* Enterprise needs cloud target scanning (SharePoint, S3, Azure) and
  automated scheduled scans with professional reports.
* Visualizations (treemap, sunburst, bar/pie) let users locate space hogs
  instantly without drilling through tree views.

Design
------
* **Platform abstraction**: Scanner base with NTFSScanner (scandir walk), PosixScanner
  (ioctl/fiemap), CloudScanner (rclone/MS Graph/S3 SDK).
* **Streaming results**: yields FileEntry objects; UI consumes via async
  generator for progressive treemap rendering.
* **Visualization data structures**: pre-aggregated FolderNode tree with
  size, count, children; computed once, reused by all chart types.
* **Cancellation & progress**: threading.Event + callback with
  (scanned_files, scanned_bytes, current_path).
* **Safety**: never deletes; read-only analysis. Deletion delegated to
  dedicated cleaner modules with confirmation dialogs.

Usage::

    from cortex_unified.analyzers.advanced_disk_analyzer import AdvancedDiskAnalyzer
    analyzer = AdvancedDiskAnalyzer(include_cloud=False)
    entries = [entry async for entry in analyzer.scan("C:\\")]
    root_node = analyzer.build_tree(entries)
    treemap_data = root_node.to_treemap()
    sunburst_data = root_node.to_sunburst()

References
----------
* WizTree technical docs (MFT parsing)
* WinDirStat 2.x source (GitHub: windirstat/windirstat)
* TreeSize Professional feature matrix (jam-software.com)
* FolderSizes comparison (foldersizes.com)
* Microsoft NTFS specification (MFT structure)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import os
import stat
import subprocess
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    AsyncGenerator,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

# Optional cloud deps
try:
    import rclone
    HAS_RCLONE = True
except ImportError:
    HAS_RCLONE = False

try:
    import msgraph
    HAS_MSGRAPH = True
except ImportError:
    HAS_MSGRAPH = False

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class FileEntry:
    """Fileentry.

    Manages FileEntry operations and coordinates related state changes for the component.
    """
    path: str
    size: int
    mtime: float
    atime: float
    ctime: float
    is_dir: bool
    extension: str
    attributes: int = 0
    owner: str = ""
    hardlink_count: int = 1
    cloud_provider: str = ""
    etag: str = ""


@dataclass
class FolderNode:
    """Foldernode.

    Manages FolderNode operations and coordinates related state changes for the component.
    """
    name: str
    path: str
    size: int = 0
    file_count: int = 0
    folder_count: int = 0
    children: Dict[str, "FolderNode"] = field(default_factory=dict)
    extension_stats: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def add_file(self, rel_path: str, size: int, ext: str) -> None:
        """Add one file's size to this node and every intermediate folder node.

        Manages add file operations and coordinates related state changes for the component.

        Args:
            rel_path (str): Filesystem path to the target file or directory.
            size (int): Integer number of bytes to format or process.
            ext (str): The ext parameter.
        """
        self.size += size
        self.file_count += 1
        self.extension_stats[ext] += size
        parts = Path(rel_path).parts
        if not parts:
            return
        node = self
        for part in parts[:-1]:
            if part not in node.children:
                node.children[part] = FolderNode(name=part, path=os.path.join(node.path, part))
            node = node.children[part]
            node.size += size
            node.folder_count += 1

    def to_treemap(self, max_depth: int = 8) -> List[Dict]:
        """Convert tree to flat list of hierarchy dictionaries for treemaps.

        Manages to treemap operations and coordinates related state changes for the component.

        Args:
            max_depth (int): The max depth parameter.

        Returns:
            List[Dict]: List of processed items or identifiers.
        """
        result: List[Dict] = []
        def walk(node: "FolderNode", depth: int = 0):
            """Walk.

            Manages walk operations and coordinates related state changes for the component.

            Args:
                node ('FolderNode'): The node parameter.
                depth (int): The depth parameter.
            """
            if depth >= max_depth:
                return
            result.append({
                "name": node.name, "path": node.path, "size": node.size,
                "file_count": node.file_count, "folder_count": node.folder_count,
                "depth": depth, "children": list(node.children.keys()),
            })
            for child in node.children.values():
                walk(child, depth + 1)
        walk(self)
        return result

    def to_sunburst(self, max_depth: int = 6) -> List[Dict]:
        """Convert tree to sunburst parent-child dictionary list.

        Manages to sunburst operations and coordinates related state changes for the component.

        Args:
            max_depth (int): The max depth parameter.

        Returns:
            List[Dict]: List of processed items or identifiers.
        """
        result: List[Dict] = []
        def walk(node: "FolderNode", depth: int = 0, parent: str = ""):
            """Walk.

            Manages walk operations and coordinates related state changes for the component.

            Args:
                node ('FolderNode'): The node parameter.
                depth (int): The depth parameter.
                parent (str): Parent window or shell controller instance.
            """
            if depth >= max_depth:
                return
            result.append({
                "id": node.path, "parent": parent, "name": node.name,
                "value": node.size, "depth": depth,
            })
            for child in node.children.values():
                walk(child, depth + 1, node.path)
        walk(self)
        return result

    def to_bar_chart(self, top_n: int = 20) -> List[Dict]:
        """Convert tree to top largest folders bar chart format.

        Manages to bar chart operations and coordinates related state changes for the component.

        Args:
            top_n (int): The top n parameter.

        Returns:
            List[Dict]: List of processed items or identifiers.
        """
        items = []
        def walk(node: "FolderNode"):
            """Walk.

            Manages walk operations and coordinates related state changes for the component.

            Args:
                node ('FolderNode'): The node parameter.
            """
            if node.path != self.path:
                items.append({"path": node.path, "size": node.size, "name": node.name})
            for child in node.children.values():
                walk(child)
        walk(self)
        items.sort(key=lambda x: x["size"], reverse=True)
        return items[:top_n]

    def top_extensions(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Return top N file extensions by space consumed.

        Manages top extensions operations and coordinates related state changes for the component.

        Args:
            limit (int): The limit parameter.

        Returns:
            List[Tuple[str, int]]: List of processed items or identifiers.
        """
        return sorted(self.extension_stats.items(), key=lambda x: x[1], reverse=True)[:limit]


# ---------------------------------------------------------------------------
# Scanner base
# ---------------------------------------------------------------------------

class Scanner(ABC):
    """Read-only filesystem scanner yielding FileEntry objects with cancellation and progress.

    Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
    """
    def __init__(self, cancel_event: Optional[threading.Event] = None,
                 progress_cb: Optional[Callable[[int, int, str], None]] = None):
        """Store the cancellation event and progress callback with zeroed counters.

        Initializes the instance and configures internal state.

        Args:
            cancel_event (Optional[threading.Event]): Threading event or callable to check for cancellation.
            progress_cb (Optional[Callable[[int, int, str], None]]): Callback invoked with progress updates.
        """
        self.cancel_event = cancel_event or threading.Event()
        self.progress_cb = progress_cb
        self._scanned_files = 0
        self._scanned_bytes = 0

    @abstractmethod
    def scan(self, root: str) -> Generator[FileEntry, None, None]:
        """Yield every FileEntry under root; implemented by each platform backend.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            root (str): Filesystem path to the target file or directory.

        Returns:
            Generator[FileEntry, None, None]: Result of the operation.
        """
        ...

    def _check_cancel(self) -> bool:
        """True once the caller has signalled the cancel event.

        Manages check cancel operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return self.cancel_event.is_set()

    def _report(self, path: str) -> None:
        """Report.

        Manages report operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        self._scanned_files += 1
        if self.progress_cb and self._scanned_files % 100 == 0:
            self.progress_cb(self._scanned_files, self._scanned_bytes, path)


# ---------------------------------------------------------------------------
# NTFS MFT Scanner (Windows)
# ---------------------------------------------------------------------------

class NTFSScanner(Scanner):
    """NTFS scanner that probes raw volume access but scans via os.scandir walk (MFT fast path not yet implemented)."""

    def __init__(self, *args, **kwargs):
        """Initialize and probe whether raw MFT/volume access is available.

        Initializes the instance and configures internal state.
        """
        super().__init__(*args, **kwargs)
        self._use_mft = self._check_mft_access()

    def _check_mft_access(self) -> bool:
        """Test raw volume handle access via CreateFileW; needs Administrator.

        Manages check mft access operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.CreateFileW(
                r"\\.\C:", 0x80000000, 0x00000001, None, 3, 0, None
            )
            if handle != -1:
                kernel32.CloseHandle(handle)
                return True
        except Exception:
            pass
        return False

    def scan(self, root: str) -> Generator[FileEntry, None, None]:
        """Yield entries via scandir walk (MFT fast path not yet implemented).

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            root (str): Filesystem path to the target file or directory.

        Returns:
            Generator[FileEntry, None, None]: Result of the operation.
        """
        if self._use_mft:
            yield from self._scan_mft(root)
        else:
            yield from self._scan_walk(root)

    def _scan_mft(self, root: str) -> Generator[FileEntry, None, None]:
        """MFT fast path; currently delegates to the scandir walk.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            root (str): Filesystem path to the target file or directory.

        Returns:
            Generator[FileEntry, None, None]: Result of the operation.
        """
        yield from self._scan_walk(root)

    def _scan_walk(self, root: str) -> Generator[FileEntry, None, None]:
        """Iterative scandir walk skipping symlinks and unreadable directories.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            root (str): Filesystem path to the target file or directory.

        Returns:
            Generator[FileEntry, None, None]: Result of the operation.
        """
        stack = [root]
        while stack and not self._check_cancel():
            current = stack.pop()
            try:
                with os.scandir(current) as it:
                    for entry in it:
                        if self._check_cancel():
                            return
                        try:
                            stat_result = entry.stat(follow_symlinks=False)
                            self._scanned_bytes += stat_result.st_size
                            ext = Path(entry.name).suffix.lower()
                            yield FileEntry(
                                path=entry.path,
                                size=stat_result.st_size,
                                mtime=stat_result.st_mtime,
                                atime=stat_result.st_atime,
                                ctime=stat_result.st_ctime,
                                is_dir=entry.is_dir(follow_symlinks=False),
                                extension=ext,
                                attributes=stat_result.st_mode,
                                hardlink_count=getattr(stat_result, "st_nlink", 1),
                            )
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
                        except (OSError, PermissionError):
                            continue
                        self._report(entry.path)
            except (OSError, PermissionError):
                continue


# ---------------------------------------------------------------------------
# Posix Scanner (Linux/macOS)
# ---------------------------------------------------------------------------

class PosixScanner(Scanner):
    """Posixscanner.

    Manages PosixScanner operations and coordinates related state changes for the component.
    """
    def scan(self, root: str) -> Generator[FileEntry, None, None]:
        """Yield entries under root via an iterative scandir walk.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            root (str): Filesystem path to the target file or directory.

        Returns:
            Generator[FileEntry, None, None]: Result of the operation.
        """
        stack = [root]
        while stack and not self._check_cancel():
            current = stack.pop()
            try:
                with os.scandir(current) as it:
                    for entry in it:
                        if self._check_cancel():
                            return
                        try:
                            stat_result = entry.stat(follow_symlinks=False)
                            self._scanned_bytes += stat_result.st_size
                            ext = Path(entry.name).suffix.lower()
                            yield FileEntry(
                                path=entry.path,
                                size=stat_result.st_size,
                                mtime=stat_result.st_mtime,
                                atime=stat_result.st_atime,
                                ctime=stat_result.st_ctime,
                                is_dir=entry.is_dir(follow_symlinks=False),
                                extension=ext,
                                attributes=stat_result.st_mode,
                                hardlink_count=getattr(stat_result, "st_nlink", 1),
                            )
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
                        except (OSError, PermissionError):
                            continue
                        self._report(entry.path)
            except (OSError, PermissionError):
                continue


# ---------------------------------------------------------------------------
# Cloud Scanner
# ---------------------------------------------------------------------------

class CloudScanner(Scanner):
    """Cloudscanner.

    Manages CloudScanner operations and coordinates related state changes for the component.
    """
    def __init__(self, *args, providers: Optional[List[str]] = None, **kwargs):
        """Store provider list and verify the rclone binary is usable.

        Initializes the instance and configures internal state.
        """
        super().__init__(*args, **kwargs)
        self.providers = providers or ["onedrive", "gdrive", "dropbox", "s3", "azureblob"]
        self._rclone_available = HAS_RCLONE and self._check_rclone()

    def _check_rclone(self) -> bool:
        """Run ``rclone version`` to confirm the binary works; no admin needed.

        Manages check rclone operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        try:
            subprocess.run(["rclone", "version"], capture_output=True, check=True)
            return True
        except Exception:
            return False

    def scan(self, root: str) -> Generator[FileEntry, None, None]:
        """Scan each configured ``provider:`` remote, or a single ``root`` remote.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            root (str): Filesystem path to the target file or directory.

        Returns:
            Generator[FileEntry, None, None]: Result of the operation.
        """
        if ":" not in root:
            for provider in self.providers:
                yield from self._scan_remote(f"{provider}:")
        else:
            yield from self._scan_remote(root)

    def _scan_remote(self, remote: str) -> Generator[FileEntry, None, None]:
        """List a remote's files via ``rclone lsf`` and convert each line to FileEntry.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            remote (str): The remote parameter.

        Returns:
            Generator[FileEntry, None, None]: Result of the operation.
        """
        if not self._rclone_available:
            return
        try:
            import subprocess
            cmd = ["rclone", "lsf", "--format", "p,s,m,t", "--files-only", "--recursive", remote]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            for line in result.stdout.strip().split("\n"):
                if self._check_cancel():
                    return
                if not line:
                    continue
                parts = line.split(";")
                if len(parts) >= 3:
                    path, size_str, mtime_str = parts[0], parts[1], parts[2]
                    try:
                        size = int(size_str) if size_str != "-" else 0
                        mtime = float(mtime_str) if mtime_str != "-" else time.time()
                    except ValueError:
                        size, mtime = 0, time.time()
                    provider = remote.split(":")[0]
                    ext = Path(path).suffix.lower()
                    yield FileEntry(
                        path=f"{remote}{path}",
                        size=size,
                        mtime=mtime,
                        atime=mtime,
                        ctime=mtime,
                        is_dir=False,
                        extension=ext,
                        cloud_provider=provider,
                    )
                    self._report(path)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Advanced Disk Analyzer
# ---------------------------------------------------------------------------

class AdvancedDiskAnalyzer:
    """Advanceddiskanalyzer.

    Manages AdvancedDiskAnalyzer operations and coordinates related state changes for the component.
    """
    def __init__(
        self,
        include_cloud: bool = False,
        cloud_providers: Optional[List[str]] = None,
        cancel_event: Optional[threading.Event] = None,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
    ):
        """Store cancellation/progress hooks and pick the platform or cloud scanner.

        Initializes the instance and configures internal state.

        Args:
            include_cloud (bool): The include cloud parameter.
            cloud_providers (Optional[List[str]]): The cloud providers parameter.
            cancel_event (Optional[threading.Event]): Threading event or callable to check for cancellation.
            progress_cb (Optional[Callable[[int, int, str], None]]): Callback invoked with progress updates.
        """
        self.cancel_event = cancel_event or threading.Event()
        self.progress_cb = progress_cb
        self._scanner = self._create_scanner(include_cloud, cloud_providers)
        self._root_node: Optional[FolderNode] = None

    def _create_scanner(self, include_cloud: bool, providers: Optional[List[str]]) -> Scanner:
        """Choose NTFS/Posix scanner by platform, or CloudScanner when cloud deps exist.

        Manages create scanner operations and coordinates related state changes for the component.

        Args:
            include_cloud (bool): The include cloud parameter.
            providers (Optional[List[str]]): The providers parameter.

        Returns:
            Scanner: Result of the operation.
        """
        import sys
        if sys.platform == "win32":
            base = NTFSScanner
        else:
            base = PosixScanner
        if include_cloud and (HAS_RCLONE or HAS_MSGRAPH or HAS_BOTO3):
            return CloudScanner(
                cancel_event=self.cancel_event,
                progress_cb=self.progress_cb,
                providers=providers,
            )
        return base(cancel_event=self.cancel_event, progress_cb=self.progress_cb)

    async def scan(self, root: str) -> AsyncGenerator[FileEntry, None]:
        """Async wrapper that streams entries from the underlying sync scanner.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            root (str): Filesystem path to the target file or directory.

        Returns:
            AsyncGenerator[FileEntry, None]: Result of the operation.
        """
        scanner_iter = self._scanner.scan(root)
        if hasattr(scanner_iter, "__aiter__"):
            async for entry in scanner_iter:
                yield entry
        else:
            for entry in scanner_iter:
                yield entry

    def build_tree(self, entries: List[FileEntry]) -> FolderNode:
        """Fold all file entries into an aggregated FolderNode hierarchy.

        Manages build tree operations and coordinates related state changes for the component.

        Args:
            entries (List[FileEntry]): Collection of items or entries to process.

        Returns:
            FolderNode: Result of the operation.
        """
        root = FolderNode(name="", path="")
        for entry in entries:
            if entry.is_dir:
                continue
            rel = entry.path
            root.add_file(rel, entry.size, entry.extension or "noext")
        self._root_node = root
        return root

    def get_visualizations(self) -> Dict:
        """Return treemap/sunburst/bar data plus extension and size totals from the last tree.

        Manages get visualizations operations and coordinates related state changes for the component.

        Returns:
            Dict: Dictionary mapping identifiers to status or values.
        """
        if not self._root_node:
            return {}
        return {
            "treemap": self._root_node.to_treemap(),
            "sunburst": self._root_node.to_sunburst(),
            "bar_chart": self._root_node.to_bar_chart(),
            "extension_breakdown": dict(self._root_node.extension_stats),
            "total_size": self._root_node.size,
            "total_files": self._root_node.file_count,
            "total_folders": self._root_node.folder_count,
        }

    def get_stats(self) -> Dict:
        """Return files and bytes counted by the scanner so far.

        Manages get stats operations and coordinates related state changes for the component.

        Returns:
            Dict: Dictionary mapping identifiers to status or values.
        """
        return {
            "scanned_files": self._scanner._scanned_files,
            "scanned_bytes": self._scanner._scanned_bytes,
        }


__all__ = [
    "AdvancedDiskAnalyzer",
    "FileEntry",
    "FolderNode",
    "NTFSScanner",
    "PosixScanner",
    "CloudScanner",
]


# Synchronous wrapper
def scan_sync(
    root: str,
    include_cloud: bool = False,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Tuple[List[FileEntry], FolderNode]:
    """Scan synchronously and return all entries plus the aggregated FolderNode tree.

    Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

    Args:
        root (str): Filesystem path to the target file or directory.
        include_cloud (bool): The include cloud parameter.
        progress_cb (Optional[Callable[[int, int, str], None]]): Callback invoked with progress updates.
        cancel_event (Optional[threading.Event]): Threading event or callable to check for cancellation.

    Returns:
        Tuple[List[FileEntry], FolderNode]: List of processed items or identifiers.
    """
    analyzer = AdvancedDiskAnalyzer(
        include_cloud=include_cloud,
        cancel_event=cancel_event,
        progress_cb=progress_cb,
    )
    entries: List[FileEntry] = []
    scanner_iter = analyzer._scanner.scan(root)
    if hasattr(scanner_iter, "__aiter__"):
        import asyncio

        async def _collect():
            """Aggregate discovered files or telemetry metrics into collections.

            Iterates over raw subsystem records, filters excluded paths, and collates findings into a structured report list.
            """
            async for entry in scanner_iter:
                entries.append(entry)

        asyncio.run(_collect())
    else:
        for entry in scanner_iter:
            entries.append(entry)
    tree = analyzer.build_tree(entries)
    return entries, tree
