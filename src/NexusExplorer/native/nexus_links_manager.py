"""Nexus Explorer — NTFS Links, Junctions & Reparse Points Manager.

Provides discovery, inspection, creation, and safe deletion for:
1. NTFS Directory Junctions (IO_REPARSE_TAG_MOUNT_POINT)
2. Symbolic Links (Directory & File symlinks, IO_REPARSE_TAG_SYMLINK)
3. Hardlinks (multi-entry inode tracking & space savings calculation)
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import platform
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple


class LinkType(Enum):
    """Linktype.

    Manages LinkType operations and coordinates related state changes for the component.
    """
    DIRECTORY_JUNCTION = "Directory Junction"
    DIRECTORY_SYMLINK = "Directory Symlink"
    FILE_SYMLINK = "File Symlink"
    HARDLINK = "Hardlink"
    REGULAR = "Regular Item"


@dataclass
class LinkItem:
    """Linkitem.

    Manages LinkItem operations and coordinates related state changes for the component.
    """
    path: str
    name: str
    link_type: LinkType
    target_path: str
    is_broken: bool
    is_directory: bool
    size_bytes: int = 0
    hardlink_count: int = 1
    error: Optional[str] = None


@dataclass
class LinkOperationResult:
    """Linkoperationresult.

    Manages LinkOperationResult operations and coordinates related state changes for the component.
    """
    success: bool
    message: str
    created_path: Optional[str] = None
    target_path: Optional[str] = None


class LinksManager:
    """Linksmanager.

    Manages LinksManager operations and coordinates related state changes for the component.
    """

    @staticmethod
    def is_junction(path: str | Path) -> bool:
        """Returns True for both NTFS directory junctions AND symlinks (does not distinguish)."""
        p = Path(path)
        if not p.is_dir():
            return False
        try:
            # On Windows, os.readlink works for junctions and symlinks
            if os.path.islink(p):
                # If it's a directory link, check if it's a junction or directory symlink
                return True
            # Check reparse point attribute via stat
            st = p.lstat()
            # FILE_ATTRIBUTE_REPARSE_POINT = 0x400
            return bool(st.st_file_attributes & 0x400) if hasattr(st, "st_file_attributes") else False
        except Exception:
            return False

    @classmethod
    def get_link_info(cls, file_or_dir: str | Path) -> LinkItem:
        """Inspect a file or directory and extract link metadata.

        Manages get link info operations and coordinates related state changes for the component.

        Args:
            file_or_dir (str | Path): The file or dir parameter.

        Returns:
            LinkItem: Result of the operation.
        """
        p = Path(file_or_dir).resolve(strict=False)
        p_orig = Path(file_or_dir)
        is_dir = p_orig.is_dir()

        link_type = LinkType.REGULAR
        target_path = ""
        is_broken = False
        nlink = 1

        try:
            lstat = p_orig.lstat()
            nlink = getattr(lstat, "st_nlink", 1)

            if os.path.islink(p_orig):
                try:
                    target_raw = os.readlink(p_orig)
                    target_path = str(target_raw)
                    # Check if target exists
                    resolved = (p_orig.parent / target_raw).resolve() if not os.path.isabs(target_raw) else Path(target_raw).resolve()
                    is_broken = not resolved.exists()
                    if is_dir:
                        # Determine if junction or symlink
                        if hasattr(lstat, "st_file_attributes") and (lstat.st_file_attributes & 0x400):
                            link_type = LinkType.DIRECTORY_JUNCTION
                        else:
                            link_type = LinkType.DIRECTORY_SYMLINK
                    else:
                        link_type = LinkType.FILE_SYMLINK
                except Exception as exc:
                    is_broken = True
                    target_path = f"Error reading link: {exc}"
            elif nlink > 1 and not is_dir:
                link_type = LinkType.HARDLINK
                target_path = f"{nlink} references sharing the same MFT record"
        except Exception as exc:
            return LinkItem(
                path=str(p_orig),
                name=p_orig.name,
                link_type=LinkType.REGULAR,
                target_path="",
                is_broken=False,
                is_directory=is_dir,
                error=str(exc),
            )

        size = 0
        try:
            size = p_orig.stat().st_size if not is_broken else 0
        except Exception:
            pass

        return LinkItem(
            path=str(p_orig.resolve()),
            name=p_orig.name,
            link_type=link_type,
            target_path=target_path,
            is_broken=is_broken,
            is_directory=is_dir,
            size_bytes=size,
            hardlink_count=nlink,
        )

    @classmethod
    def scan_links_in_directory(
        cls,
        root_dir: str | Path,
        recursive: bool = False,
        progress_cb: Optional[Callable[[int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> List[LinkItem]:
        """Scan a folder to discover all Junctions, Symlinks, and Hardlinked items.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            root_dir (str | Path): The root dir parameter.
            recursive (bool): The recursive parameter.
            progress_cb (Optional[Callable[[int, str], None]]): Callback invoked with progress updates.
            cancel_check (Optional[Callable[[], bool]]): Threading event or callable to check for cancellation.

        Returns:
            List[LinkItem]: List of processed items or identifiers.
        """
        root = Path(root_dir).resolve()
        if not root.is_dir():
            return []

        results: List[LinkItem] = []
        count = 0

        try:
            if recursive:
                for parent, dirs, files in os.walk(root, followlinks=False):
                    if cancel_check and cancel_check():
                        break
                    # Check directories (including junctions and symlinks)
                    for d in dirs:
                        count += 1
                        dp = Path(parent) / d
                        if progress_cb and count % 50 == 0:
                            progress_cb(count, str(dp))
                        info = cls.get_link_info(dp)
                        if info.link_type != LinkType.REGULAR:
                            results.append(info)

                    for f in files:
                        count += 1
                        fp = Path(parent) / f
                        if progress_cb and count % 50 == 0:
                            progress_cb(count, str(fp))
                        info = cls.get_link_info(fp)
                        if info.link_type != LinkType.REGULAR:
                            results.append(info)
            else:
                for entry in os.scandir(root):
                    if cancel_check and cancel_check():
                        break
                    count += 1
                    ep = Path(entry.path)
                    info = cls.get_link_info(ep)
                    if info.link_type != LinkType.REGULAR:
                        results.append(info)
                    if progress_cb:
                        progress_cb(count, str(ep))
        except Exception:
            pass

        return results

    @classmethod
    def create_junction(cls, link_path: str | Path, target_dir: str | Path) -> LinkOperationResult:
        """Create an NTFS Directory Junction.

        Manages create junction operations and coordinates related state changes for the component.

        Args:
            link_path (str | Path): Filesystem path to the target file or directory.
            target_dir (str | Path): The target dir parameter.

        Returns:
            LinkOperationResult: Result of the operation.
        """
        link = Path(link_path).resolve()
        target = Path(target_dir).resolve()

        if not target.is_dir():
            return LinkOperationResult(False, f"Target directory does not exist: {target}")

        if link.exists():
            return LinkOperationResult(False, f"Link destination already exists: {link}")

        if platform.system() == "Windows":
            import subprocess
            try:
                # mklink /J <Link> <Target>
                cmd = ["cmd", "/c", "mklink", "/J", str(link), str(target)]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if res.returncode == 0:
                    return LinkOperationResult(True, f"Directory Junction created: {link.name} -> {target}", str(link), str(target))
                return LinkOperationResult(False, res.stderr.strip() or res.stdout.strip() or "mklink failed")
            except Exception as exc:
                return LinkOperationResult(False, str(exc))

        # Fallback for non-Windows (symlink)
        try:
            os.symlink(str(target), str(link), target_is_directory=True)
            return LinkOperationResult(True, f"Symlink created: {link.name} -> {target}", str(link), str(target))
        except Exception as exc:
            return LinkOperationResult(False, str(exc))

    @classmethod
    def create_symlink(
        cls,
        link_path: str | Path,
        target_path: str | Path,
        target_is_directory: Optional[bool] = None,
    ) -> LinkOperationResult:
        """Create a Symbolic Link (File or Directory).

        Manages create symlink operations and coordinates related state changes for the component.

        Args:
            link_path (str | Path): Filesystem path to the target file or directory.
            target_path (str | Path): Filesystem path to the target file or directory.
            target_is_directory (Optional[bool]): The target is directory parameter.

        Returns:
            LinkOperationResult: Result of the operation.
        """
        link = Path(link_path).resolve()
        target = Path(target_path).resolve()

        if not target.exists():
            return LinkOperationResult(False, f"Target does not exist: {target}")

        if link.exists():
            return LinkOperationResult(False, f"Link path already exists: {link}")

        if target_is_directory is None:
            target_is_directory = target.is_dir()

        try:
            os.symlink(str(target), str(link), target_is_directory=target_is_directory)
            return LinkOperationResult(True, f"Symbolic Link created: {link.name} -> {target}", str(link), str(target))
        except OSError as exc:
            # On Windows without Developer Mode or Admin rights, os.symlink can raise WinError 1314
            return LinkOperationResult(False, f"Symlink creation failed (Admin rights or Developer Mode required): {exc}")

    @classmethod
    def create_hardlink(cls, link_path: str | Path, target_file: str | Path) -> LinkOperationResult:
        """Create an NTFS Hardlink to an existing file.

        Manages create hardlink operations and coordinates related state changes for the component.

        Args:
            link_path (str | Path): Filesystem path to the target file or directory.
            target_file (str | Path): The target file parameter.

        Returns:
            LinkOperationResult: Result of the operation.
        """
        link = Path(link_path).resolve()
        target = Path(target_file).resolve()

        if not target.is_file():
            return LinkOperationResult(False, f"Target is not a regular file: {target}")

        if link.exists():
            return LinkOperationResult(False, f"Link path already exists: {link}")

        try:
            os.link(str(target), str(link))
            return LinkOperationResult(True, f"Hardlink created: {link.name} -> {target}", str(link), str(target))
        except Exception as exc:
            return LinkOperationResult(False, f"Hardlink creation failed (Must be on the same volume): {exc}")

    @classmethod
    def remove_link_safely(cls, link_path: str | Path) -> LinkOperationResult:
        """Safely delete a junction or symlink without removing the contents of the target folder.

        Manages remove link safely operations and coordinates related state changes for the component.

        Args:
            link_path (str | Path): Filesystem path to the target file or directory.

        Returns:
            LinkOperationResult: Result of the operation.
        """
        p = Path(link_path)
        if not p.exists() and not os.path.islink(p):
            return LinkOperationResult(False, f"Path does not exist: {p}")

        try:
            if p.is_dir() or cls.is_junction(p):
                # On Windows, os.rmdir safely removes the directory reparse point without touching target
                os.rmdir(p)
                return LinkOperationResult(True, f"Link removed safely: {p.name}")
            else:
                # File symlink or hardlink
                os.unlink(p)
                return LinkOperationResult(True, f"File link removed: {p.name}")
        except Exception as exc:
            return LinkOperationResult(False, f"Failed to remove link: {exc}")
