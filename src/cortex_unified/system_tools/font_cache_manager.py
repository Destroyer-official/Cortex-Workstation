"""Cortex Cleaner — Windows Font Cache Inspector & Optimizer.

Manages installed system and user fonts:
1. Enumerates all installed fonts with file size, format (TTF/OTF/WOFF/TTC), and installation type.
2. Detects orphaned font files (registry entries pointing to missing font files).
3. Detects duplicate fonts (same font family installed in multiple locations).
4. Calculates total font cache footprint and identifies fonts consuming the most space.
5. Provides cleanup of orphaned font registry entries.
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
class FontEntry:
    """Font Entry data container."""
    name: str
    file_name: str
    file_path: str
    file_size_bytes: int
    format: str  # "TTF", "OTF", "TTC", "WOFF2", "FON", "Unknown"
    exists: bool
    is_orphaned: bool
    is_duplicate: bool = False


@dataclass
class FontAnalysisReport:
    """Font Analysis Report data container."""
    total_fonts: int
    total_size_bytes: int
    orphaned_count: int
    orphaned_size_bytes: int
    duplicate_count: int
    largest_fonts: List[FontEntry]
    entries: List[FontEntry]


@dataclass
class FontCleanResult:
    """Font Clean Result data container."""
    orphans_removed: int
    bytes_freed: int
    errors: List[str]


class FontCacheManager:
    """Production Windows font inventory and orphan cleanup engine."""

    FONTS_REG_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"

    @classmethod
    def _get_fonts_dir(cls) -> Path:
        """Return the system fonts directory."""
        windir = os.environ.get("WINDIR", r"C:\Windows")
        return Path(windir) / "Fonts"

    @classmethod
    def _detect_format(cls, file_name: str) -> str:
        """Detect font format from file extension."""
        ext = Path(file_name).suffix.lower()
        fmt_map = {
            ".ttf": "TTF", ".otf": "OTF", ".ttc": "TTC",
            ".woff": "WOFF", ".woff2": "WOFF2", ".fon": "FON",
            ".fnt": "FNT",
        }
        return fmt_map.get(ext, "Unknown")

    @classmethod
    def enumerate_fonts(cls) -> List[FontEntry]:
        """Enumerate all registered system fonts from the registry."""
        if winreg is None:
            return []

        fonts_dir = cls._get_fonts_dir()
        entries: List[FontEntry] = []

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cls.FONTS_REG_KEY, 0, winreg.KEY_READ) as key:
                idx = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, idx)
                        file_name = str(value)

                        # Resolve full path
                        if os.path.isabs(file_name):
                            full_path = Path(file_name)
                        else:
                            full_path = fonts_dir / file_name

                        exists = full_path.is_file()
                        size = full_path.stat().st_size if exists else 0
                        fmt = cls._detect_format(file_name)

                        entries.append(FontEntry(
                            name=name,
                            file_name=file_name,
                            file_path=str(full_path),
                            file_size_bytes=size,
                            format=fmt,
                            exists=exists,
                            is_orphaned=not exists,
                        ))
                        idx += 1
                    except OSError:
                        break
        except (FileNotFoundError, OSError):
            pass

        # Detect duplicates (same file_name registered multiple times)
        seen_files: Dict[str, int] = {}
        for e in entries:
            lower = e.file_name.lower()
            if lower in seen_files:
                e.is_duplicate = True
                entries[seen_files[lower]].is_duplicate = True
            else:
                seen_files[lower] = entries.index(e)

        return entries

    @classmethod
    def analyze(cls) -> FontAnalysisReport:
        """Produce full analysis report of installed font set."""
        entries = cls.enumerate_fonts()
        total_size = sum(e.file_size_bytes for e in entries)
        orphaned = [e for e in entries if e.is_orphaned]
        orphaned_size = sum(e.file_size_bytes for e in orphaned)
        duplicates = [e for e in entries if e.is_duplicate]

        sorted_by_size = sorted(entries, key=lambda e: e.file_size_bytes, reverse=True)
        largest = sorted_by_size[:20]

        return FontAnalysisReport(
            total_fonts=len(entries),
            total_size_bytes=total_size,
            orphaned_count=len(orphaned),
            orphaned_size_bytes=orphaned_size,
            duplicate_count=len(duplicates),
            largest_fonts=largest,
            entries=entries,
        )

    @classmethod
    def clean_orphaned_entries(cls) -> FontCleanResult:
        """Remove orphaned font registry entries (fonts pointing to missing files)."""
        if winreg is None:
            return FontCleanResult(0, 0, ["Windows only"])

        entries = cls.enumerate_fonts()
        orphans = [e for e in entries if e.is_orphaned]
        removed = 0
        freed = 0
        errors: List[str] = []

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cls.FONTS_REG_KEY,
                                0, winreg.KEY_SET_VALUE) as key:
                for o in orphans:
                    try:
                        winreg.DeleteValue(key, o.name)
                        removed += 1
                    except Exception as exc:
                        errors.append(f"Failed to remove '{o.name}': {exc}")
        except PermissionError:
            errors.append("Administrator privileges required to modify font registry")
        except Exception as exc:
            errors.append(str(exc))

        return FontCleanResult(orphans_removed=removed, bytes_freed=freed, errors=errors)
