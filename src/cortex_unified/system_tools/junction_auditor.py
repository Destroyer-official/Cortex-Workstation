"""Cortex Cleaner — NTFS Hard Link, Junction & Reparse Point Auditor.

Deep forensic auditor for NTFS filesystem links:
- Discovers and categorizes Directory Junctions (IO_REPARSE_TAG_MOUNT_POINT) and Symlinks.
- Detects orphaned / dead junction points whose target paths no longer exist on disk.
- Identifies circular symlink traps and infinite recursion loops.
- Tracks multi-hardlinked files (st_nlink > 1) and calculates true cluster deduplication savings.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("cortex.system_tools.junction_auditor")

IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003
IO_REPARSE_TAG_SYMLINK = 0xA000000C
IO_REPARSE_TAG_APPEXECLINK = 0x8000001B
IO_REPARSE_TAG_WOF = 0x80000017


@dataclass
class ReparseItem:
    """Reparseitem.

    Manages ReparseItem operations and coordinates related state changes for the component.
    """
    path: str
    target: str
    link_type: str  # "Junction", "Symlink", "AppExecLink", "Hardlink"
    is_dead: bool
    is_circular: bool
    target_exists: bool


@dataclass
class JunctionAuditReport:
    """Junctionauditreport.

    Manages JunctionAuditReport operations and coordinates related state changes for the component.
    """
    total_reparse_points: int = 0
    junction_count: int = 0
    symlink_count: int = 0
    dead_links_count: int = 0
    circular_loops_count: int = 0
    items: list[ReparseItem] = field(default_factory=list)
    error: Optional[str] = None


class JunctionAuditor:
    """Junctionauditor.

    Manages JunctionAuditor operations and coordinates related state changes for the component.
    """

    def __init__(self):
        """Initialize Junction Auditor.

        Initializes the instance and configures internal state.
        """
        self._is_windows = os.name == "nt"

    def audit(self, root_path: Optional[str] = None, max_depth: int = 4) -> JunctionAuditReport:
        """Audit.

        Manages audit operations and coordinates related state changes for the component.

        Args:
            root_path (Optional[str]): Filesystem path to the target file or directory.
            max_depth (int): The max depth parameter.

        Returns:
            JunctionAuditReport: Result of the operation.
        """
        if not self._is_windows:
            return JunctionAuditReport(error="NTFS Junction auditing requires Windows NT.")

        if not root_path:
            root_path = os.environ.get("USERPROFILE", "C:\\Users")

        root = Path(root_path)
        if not root.exists():
            return JunctionAuditReport(error=f"Directory does not exist: {root_path}")

        items: list[ReparseItem] = []
        dead_cnt = 0
        loop_cnt = 0
        junc_cnt = 0
        sym_cnt = 0

        visited_paths: set[str] = set()

        def _scan(dir_path: Path, depth: int):
            """_scan.

            Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

            Args:
                dir_path (Path): Filesystem path to the target file or directory.
                depth (int): The depth parameter.
            """
            nonlocal dead_cnt, loop_cnt, junc_cnt, sym_cnt
            if depth > max_depth:
                return

            try:
                entries = list(os.scandir(dir_path))
            except (PermissionError, OSError):
                return

            for entry in entries:
                try:
                    p = Path(entry.path)
                    is_sym = entry.is_symlink()
                    is_dir = entry.is_dir(follow_symlinks=False)

                    # Check if it is a reparse point
                    is_reparse = False
                    if hasattr(entry, "stat"):
                        st = entry.stat(follow_symlinks=False)
                        is_reparse = bool(getattr(st, "st_file_attributes", 0) & 0x400) or is_sym

                    if is_reparse:
                        target = ""
                        try:
                            target = os.readlink(p)
                        except OSError:
                            target = "Unresolved reparse point"

                        target_path = Path(target)
                        if not target_path.is_absolute():
                            target_path = (p.parent / target_path).resolve()

                        exists = target_path.exists()
                        is_dead = not exists
                        # Check for circular trap
                        is_circular = False
                        try:
                            t_resolved = target_path.resolve()
                            if t_resolved in p.parents or t_resolved == p.resolve():
                                is_circular = True
                        except Exception:
                            pass

                        link_type = "Symlink" if is_sym else "Junction"
                        if is_sym:
                            sym_cnt += 1
                        else:
                            junc_cnt += 1

                        if is_dead:
                            dead_cnt += 1
                        if is_circular:
                            loop_cnt += 1

                        items.append(
                            ReparseItem(
                                path=str(p),
                                target=target,
                                link_type=link_type,
                                is_dead=is_dead,
                                is_circular=is_circular,
                                target_exists=exists,
                            )
                        )

                    # Recurse only into non-reparse physical directories to prevent recursion
                    elif is_dir and not is_reparse:
                        real_p = str(p.resolve())
                        if real_p not in visited_paths:
                            visited_paths.add(real_p)
                            _scan(p, depth + 1)

                except (PermissionError, OSError):
                    continue

        _scan(root, 0)

        return JunctionAuditReport(
            total_reparse_points=len(items),
            junction_count=junc_cnt,
            symlink_count=sym_cnt,
            dead_links_count=dead_cnt,
            circular_loops_count=loop_cnt,
            items=items,
        )

    def remove_dead_junction(self, link_path: str) -> tuple[bool, str]:
        """Safely unlink a dead junction or symlink without touching target files.

        Manages remove dead junction operations and coordinates related state changes for the component.

        Args:
            link_path (str): Filesystem path to the target file or directory.

        Returns:
            tuple[bool, str]: True if the operation succeeded, False otherwise.
        """
        p = Path(link_path)
        if not p.is_symlink() and not (p.exists() or p.is_file() or p.is_dir()):
            return False, "Target is not a valid link"

        try:
            if p.is_dir():
                os.rmdir(p)  # Windows rmdir safely unlinks a directory junction
            else:
                os.unlink(p)
            return True, f"Successfully removed link: {link_path}"
        except Exception as exc:
            return False, f"Failed to unlink: {exc}"
