"""Cortex Cleaner — Windows Context Menu & Shell Extension Manager.

Inspects and manages right-click context menu bloat:
1. Enumerates all shell extensions registered in HKCR\\*\\shell, Directory\\shell, etc.
2. Detects orphaned context menu entries (pointing to uninstalled programs).
3. Provides non-destructive disable/enable toggle for individual menu items.
4. Flags orphaned entries and LegacyDisable state for review (no timing measurement).
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if platform.system() == "Windows":
    import winreg
else:
    winreg = None  # type: ignore[assignment]


@dataclass
class ContextMenuItem:
    """Context Menu Item data container."""
    name: str
    command: str
    registry_path: str
    icon: str
    scope: str  # "AllFiles", "Directory", "Background", "Drive"
    is_enabled: bool
    is_orphaned: bool
    program_exists: bool


@dataclass
class ContextMenuReport:
    """Context Menu Report data container."""
    total_entries: int
    orphaned_entries: int
    entries: List[ContextMenuItem]


class ContextMenuManager:
    """Production Windows shell context menu inspector and cleaner."""

    _SHELL_ROOTS = [
        ("AllFiles", r"*\shell"),
        ("AllFiles", r"*\shellex\ContextMenuHandlers"),
        ("Directory", r"Directory\shell"),
        ("Directory", r"Directory\shellex\ContextMenuHandlers"),
        ("Background", r"Directory\Background\shell"),
        ("Background", r"Directory\Background\shellex\ContextMenuHandlers"),
        ("Drive", r"Drive\shell"),
    ]

    @classmethod
    def _extract_command(cls, key_path: str) -> str:
        """Read the command value from a shell key."""
        if winreg is None:
            return ""
        try:
            cmd_path = f"{key_path}\\command"
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, cmd_path, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, "")
                return str(val)
        except (FileNotFoundError, OSError):
            return ""

    @classmethod
    def _check_program_exists(cls, command: str) -> bool:
        """Check if the executable referenced in the command actually exists."""
        if not command:
            return False
        # Extract path from command string like '"C:\Program Files\App\app.exe" "%1"'
        cmd = command.strip()
        if cmd.startswith('"'):
            end = cmd.find('"', 1)
            if end > 0:
                exe = cmd[1:end]
            else:
                exe = cmd.strip('"')
        else:
            exe = cmd.split(" ")[0]

        exe = os.path.expandvars(exe)
        return os.path.isfile(exe)

    @classmethod
    def enumerate_context_menu(cls) -> List[ContextMenuItem]:
        """Enumerate all right-click context menu entries from the registry."""
        if winreg is None:
            return []

        items: List[ContextMenuItem] = []

        for scope, root_path in cls._SHELL_ROOTS:
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, root_path, 0, winreg.KEY_READ) as root_key:
                    idx = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(root_key, idx)
                            full_path = f"{root_path}\\{subkey_name}"

                            # Read default value (display name) and icon
                            display_name = subkey_name
                            icon = ""
                            is_enabled = True
                            try:
                                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, full_path, 0, winreg.KEY_READ) as sk:
                                    try:
                                        val, _ = winreg.QueryValueEx(sk, "")
                                        if val:
                                            display_name = str(val)
                                    except (FileNotFoundError, OSError):
                                        pass
                                    try:
                                        icon_val, _ = winreg.QueryValueEx(sk, "Icon")
                                        icon = str(icon_val)
                                    except (FileNotFoundError, OSError):
                                        pass
                                    # Check for LegacyDisable or Extended flag
                                    try:
                                        winreg.QueryValueEx(sk, "LegacyDisable")
                                        is_enabled = False
                                    except (FileNotFoundError, OSError):
                                        pass
                            except (FileNotFoundError, OSError):
                                pass

                            command = cls._extract_command(full_path)
                            prog_exists = cls._check_program_exists(command)
                            is_orphaned = bool(command) and not prog_exists

                            items.append(ContextMenuItem(
                                name=display_name,
                                command=command,
                                registry_path=full_path,
                                icon=icon,
                                scope=scope,
                                is_enabled=is_enabled,
                                is_orphaned=is_orphaned,
                                program_exists=prog_exists,
                            ))
                            idx += 1
                        except OSError:
                            break
            except (FileNotFoundError, OSError):
                continue

        return items

    @classmethod
    def analyze(cls) -> ContextMenuReport:
        """Generate analysis report of context menu entries."""
        entries = cls.enumerate_context_menu()
        orphaned = sum(1 for e in entries if e.is_orphaned)
        return ContextMenuReport(
            total_entries=len(entries),
            orphaned_entries=orphaned,
            entries=entries,
        )

    @classmethod
    def disable_entry(cls, registry_path: str) -> Tuple[bool, str]:
        """Disable a context menu entry by setting LegacyDisable."""
        if winreg is None:
            return False, "Windows only"
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, registry_path,
                                0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "LegacyDisable", 0, winreg.REG_SZ, "")
                return True, "Context menu entry disabled."
        except PermissionError:
            return False, "Administrator privileges required."
        except Exception as exc:
            return False, str(exc)

    @classmethod
    def enable_entry(cls, registry_path: str) -> Tuple[bool, str]:
        """Re-enable a disabled context menu entry."""
        if winreg is None:
            return False, "Windows only"
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, registry_path,
                                0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, "LegacyDisable")
                return True, "Context menu entry enabled."
        except FileNotFoundError:
            return True, "Already enabled."
        except PermissionError:
            return False, "Administrator privileges required."
        except Exception as exc:
            return False, str(exc)
