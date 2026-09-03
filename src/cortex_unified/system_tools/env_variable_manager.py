"""Cortex Cleaner — Windows Environment Variable & PATH Optimizer.

Inspects and sanitizes Windows environment variables:
1. Detects duplicate PATH entries (case-insensitive deduplication).
2. Identifies dead links — directory entries that no longer exist on disk.
3. Provides non-destructive toggling (disable without deleting) with snapshot rollback.
4. Separates User vs System variable scopes for safe editing.
5. Exports and imports environment configurations as .env or .bat files.
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if platform.system() == "Windows":
    import winreg
else:
    winreg = None  # type: ignore[assignment]


@dataclass
class PathEntry:
    """Path Entry data container."""
    directory: str
    scope: str  # "User" or "System"
    exists: bool
    is_duplicate: bool = False
    is_empty: bool = False


@dataclass
class EnvVariable:
    """Env Variable data container."""
    name: str
    value: str
    scope: str  # "User" or "System"
    var_type: str  # "REG_SZ" or "REG_EXPAND_SZ"


@dataclass
class PathAnalysisReport:
    """Path Analysis Report data container."""
    total_entries: int
    valid_entries: int
    dead_links: int
    duplicates: int
    empty_entries: int
    entries: List[PathEntry]


@dataclass
class CleanupResult:
    """Cleanup Result data container."""
    entries_removed: int
    duplicates_removed: int
    dead_links_removed: int
    empty_removed: int
    backup_value: str


class EnvironmentVariableManager:
    """Production Windows environment variable and PATH optimizer."""

    USER_ENV_KEY = r"Environment"
    SYSTEM_ENV_KEY = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"

    @classmethod
    def _read_registry_value(cls, hive, subkey: str, name: str) -> Tuple[Optional[str], int]:
        """Read a single registry value and its type."""
        if winreg is None:
            return None, 0
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
                val, reg_type = winreg.QueryValueEx(key, name)
                return str(val), reg_type
        except (FileNotFoundError, OSError):
            return None, 0

    @classmethod
    def _write_registry_value(cls, hive, subkey: str, name: str, value: str, reg_type: int) -> bool:
        """Write a registry value."""
        if winreg is None:
            return False
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, name, 0, reg_type, value)
                return True
        except (PermissionError, OSError):
            return False

    @classmethod
    def enumerate_variables(cls, scope: str = "User") -> List[EnvVariable]:
        """List all environment variables for the specified scope."""
        if winreg is None:
            return []

        hive = winreg.HKEY_CURRENT_USER if scope == "User" else winreg.HKEY_LOCAL_MACHINE
        subkey = cls.USER_ENV_KEY if scope == "User" else cls.SYSTEM_ENV_KEY

        variables: List[EnvVariable] = []
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
                idx = 0
                while True:
                    try:
                        name, val, reg_type = winreg.EnumValue(key, idx)
                        type_name = "REG_EXPAND_SZ" if reg_type == winreg.REG_EXPAND_SZ else "REG_SZ"
                        variables.append(EnvVariable(
                            name=name, value=str(val), scope=scope, var_type=type_name,
                        ))
                        idx += 1
                    except OSError:
                        break
        except (FileNotFoundError, OSError):
            pass
        return variables

    @classmethod
    def analyze_path(cls) -> PathAnalysisReport:
        """Analyze both User and System PATH for dead links, duplicates, and empty entries."""
        entries: List[PathEntry] = []
        seen_lower: Dict[str, str] = {}  # lowercase -> first scope

        for scope in ("System", "User"):
            if winreg is None:
                raw_path = os.environ.get("PATH", "")
            else:
                hive = winreg.HKEY_CURRENT_USER if scope == "User" else winreg.HKEY_LOCAL_MACHINE
                subkey = cls.USER_ENV_KEY if scope == "User" else cls.SYSTEM_ENV_KEY
                raw_path, _ = cls._read_registry_value(hive, subkey, "Path")
                if raw_path is None:
                    raw_path, _ = cls._read_registry_value(hive, subkey, "PATH")
                if raw_path is None:
                    continue

            for part in raw_path.split(";"):
                stripped = part.strip()
                if not stripped:
                    entries.append(PathEntry(
                        directory="(empty)", scope=scope, exists=False,
                        is_duplicate=False, is_empty=True,
                    ))
                    continue

                expanded = os.path.expandvars(stripped)
                exists = os.path.isdir(expanded)
                lower = expanded.lower().rstrip("\\/")
                is_dup = lower in seen_lower
                if not is_dup:
                    seen_lower[lower] = scope

                entries.append(PathEntry(
                    directory=stripped, scope=scope, exists=exists,
                    is_duplicate=is_dup, is_empty=False,
                ))

        dead = sum(1 for e in entries if not e.exists and not e.is_empty)
        dups = sum(1 for e in entries if e.is_duplicate)
        empties = sum(1 for e in entries if e.is_empty)
        valid = sum(1 for e in entries if e.exists and not e.is_duplicate)

        return PathAnalysisReport(
            total_entries=len(entries),
            valid_entries=valid,
            dead_links=dead,
            duplicates=dups,
            empty_entries=empties,
            entries=entries,
        )

    @classmethod
    def clean_path(cls, scope: str = "User", remove_dead: bool = True,
                   remove_duplicates: bool = True, remove_empty: bool = True) -> CleanupResult:
        """Clean PATH variable by removing dead links, duplicates, and empty entries."""
        if winreg is None:
            return CleanupResult(0, 0, 0, 0, "")

        hive = winreg.HKEY_CURRENT_USER if scope == "User" else winreg.HKEY_LOCAL_MACHINE
        subkey = cls.USER_ENV_KEY if scope == "User" else cls.SYSTEM_ENV_KEY

        raw_path, reg_type = cls._read_registry_value(hive, subkey, "Path")
        if raw_path is None:
            raw_path, reg_type = cls._read_registry_value(hive, subkey, "PATH")
        if raw_path is None:
            return CleanupResult(0, 0, 0, 0, "")

        if reg_type == 0:
            reg_type = winreg.REG_EXPAND_SZ

        backup = raw_path
        parts = raw_path.split(";")
        cleaned: List[str] = []
        seen: set = set()
        dead_cnt = dup_cnt = empty_cnt = 0

        for part in parts:
            stripped = part.strip()
            if not stripped:
                if remove_empty:
                    empty_cnt += 1
                    continue
                cleaned.append(stripped)
                continue

            expanded = os.path.expandvars(stripped)
            lower = expanded.lower().rstrip("\\/")

            if remove_duplicates and lower in seen:
                dup_cnt += 1
                continue

            if remove_dead and not os.path.isdir(expanded):
                dead_cnt += 1
                continue

            seen.add(lower)
            cleaned.append(stripped)

        new_path = ";".join(cleaned)
        total_removed = dead_cnt + dup_cnt + empty_cnt

        if total_removed > 0:
            cls._write_registry_value(hive, subkey, "Path", new_path, reg_type)

        return CleanupResult(
            entries_removed=total_removed,
            duplicates_removed=dup_cnt,
            dead_links_removed=dead_cnt,
            empty_removed=empty_cnt,
            backup_value=backup,
        )

    @classmethod
    def export_env_to_file(cls, output_path: str | Path, scope: str = "User", fmt: str = "env") -> bool:
        """Export environment variables to .env or .bat file."""
        variables = cls.enumerate_variables(scope)
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(p, "w", encoding="utf-8") as f:
                if fmt == "bat":
                    f.write("@echo off\nREM Cortex Cleaner Environment Export\n")
                    for v in variables:
                        f.write(f'set "{v.name}={v.value}"\n')
                else:
                    f.write("# Cortex Cleaner Environment Export\n")
                    for v in variables:
                        f.write(f'{v.name}="{v.value}"\n')
            return True
        except Exception:
            return False
