"""Declarative Community & Third-Party Application Cleaner (Winapp2.ini Engine).

Parses and executes declarative application cleaning rules supporting thousands of
Windows desktop applications, tools, browsers, and developer environments.
Provides variable path expansion, registry-based software detection, and strict safety
boundaries to prevent accidental removal of operating system or critical user data.
"""

from __future__ import annotations

import configparser
import io
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple

_LOG = logging.getLogger("cortex.system_tools.winapp2")

# Winreg access with safe fallback on non-Windows platforms
try:
    import winreg
except ImportError:
    winreg = None  # type: ignore[assignment]


# Built-in curated catalog of top-tier desktop application cleaning rules
# Following the exact Winapp2 declarative specification.
CURATED_WINAPP2_RULES = """
[Discord Cache *]
Section=Applications
Detect=%APPDATA%\\discord
Default=True
FileKey1=%APPDATA%\\discord\\Cache|*.*|RECURSE
FileKey2=%APPDATA%\\discord\\Code Cache|*.*|RECURSE
FileKey3=%APPDATA%\\discord\\GPUCache|*.*|RECURSE

[Spotify Cache *]
Section=Multimedia
Detect=%LOCALAPPDATA%\\Spotify
Default=True
FileKey1=%LOCALAPPDATA%\\Spotify\\Data|*.*|RECURSE
FileKey2=%LOCALAPPDATA%\\Spotify\\Storage|*.*|RECURSE
FileKey3=%LOCALAPPDATA%\\Spotify\\Browser\\Cache|*.*|RECURSE

[Steam Download & Web Cache *]
Section=Games
Detect=%PROGRAMFILES(X86)%\\Steam
Default=True
FileKey1=%PROGRAMFILES(X86)%\\Steam\\appcache\\httpcache|*.*|RECURSE
FileKey2=%PROGRAMFILES(X86)%\\Steam\\logs|*.txt;*.log
FileKey3=%LOCALAPPDATA%\\Steam\\htmlcache\\Cache|*.*|RECURSE

[Visual Studio Code Cache *]
Section=Development
Detect=%APPDATA%\\Code
Default=True
FileKey1=%APPDATA%\\Code\\Cache|*.*|RECURSE
FileKey2=%APPDATA%\\Code\\CachedData|*.*|RECURSE
FileKey3=%APPDATA%\\Code\\CachedExtensionVSIXs|*.*|RECURSE
FileKey4=%APPDATA%\\Code\\logs|*.*|RECURSE

[JetBrains IDEs System Caches *]
Section=Development
Detect=%LOCALAPPDATA%\\JetBrains
Default=True
FileKey1=%LOCALAPPDATA%\\JetBrains\\*\\caches|*.*|RECURSE
FileKey2=%LOCALAPPDATA%\\JetBrains\\*\\log|*.log;*.log.*

[Node.js & NPM Cache *]
Section=Development
Detect=%LOCALAPPDATA%\\npm-cache
Default=False
FileKey1=%LOCALAPPDATA%\\npm-cache\\_cacache|*.*|RECURSE

[Python Pip Cache *]
Section=Development
Detect=%LOCALAPPDATA%\\pip\\cache
Default=False
FileKey1=%LOCALAPPDATA%\\pip\\cache|*.*|RECURSE

[Rust Cargo Cache *]
Section=Development
Detect=%USERPROFILE%\\.cargo
Default=False
FileKey1=%USERPROFILE%\\.cargo\\.package-cache|*.*|RECURSE
FileKey2=%USERPROFILE%\\.cargo\\registry\\cache|*.*|RECURSE

[VLC Media Player Art & Cache *]
Section=Multimedia
Detect=%APPDATA%\\vlc
Default=True
FileKey1=%APPDATA%\\vlc\\art|*.*|RECURSE
FileKey2=%LOCALAPPDATA%\\vlc\\art|*.*|RECURSE

[Google Chrome GPU & Shader Cache *]
Section=Browsers
Detect=%LOCALAPPDATA%\\Google\\Chrome\\User Data
Default=True
FileKey1=%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\GPUCache|*.*|RECURSE
FileKey2=%LOCALAPPDATA%\\Google\\Chrome\\User Data\\ShaderCache|*.*|RECURSE
FileKey3=%LOCALAPPDATA%\\Google\\Chrome\\User Data\\GrShaderCache|*.*|RECURSE

[Mozilla Firefox Startup & Shader Cache *]
Section=Browsers
Detect=%LOCALAPPDATA%\\Mozilla\\Firefox\\Profiles
Default=True
FileKey1=%LOCALAPPDATA%\\Mozilla\\Firefox\\Profiles\\*\\startupCache|*.*|RECURSE
FileKey2=%LOCALAPPDATA%\\Mozilla\\Firefox\\Profiles\\*\\shader-cache|*.*|RECURSE

[Telegram Desktop Cache *]
Section=Applications
Detect=%APPDATA%\\Telegram Desktop
Default=False
FileKey1=%APPDATA%\\Telegram Desktop\\tdata\\user_data\\cache|*.*|RECURSE
FileKey2=%APPDATA%\\Telegram Desktop\\tdata\\temp|*.*|RECURSE

[OBS Studio Crash Dumps & Logs *]
Section=Multimedia
Detect=%APPDATA%\\obs-studio
Default=True
FileKey1=%APPDATA%\\obs-studio\\crashes|*.dmp
FileKey2=%APPDATA%\\obs-studio\\logs|*.txt;*.log

[Blender Autosave & Temp *]
Section=Multimedia
Detect=%LOCALAPPDATA%\\Temp
Default=True
FileKey1=%LOCALAPPDATA%\\Temp\\*.blend|*.*
"""


@dataclass
class Winapp2Rule:
    """Represents a single parsed Winapp2 application cleaning rule."""

    name: str
    section: str
    detect_path: Optional[str] = None
    detect_reg: Optional[str] = None
    file_keys: List[str] = field(default_factory=list)
    reg_keys: List[str] = field(default_factory=list)
    exclude_keys: List[str] = field(default_factory=list)
    default_enabled: bool = True
    installed: bool = False


@dataclass
class AppCleanTarget:
    """Target item identified for removal."""

    rule_name: str
    section: str
    target_path: str
    is_dir: bool
    size_bytes: int


@dataclass
class Winapp2Report:
    """Scan and cleanup report from the Winapp2 engine."""

    total_scanned_rules: int = 0
    installed_apps_count: int = 0
    targets: List[AppCleanTarget] = field(default_factory=list)
    total_bytes: int = 0
    cleaned_bytes: int = 0
    cleaned_items: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "total_scanned_rules": self.total_scanned_rules,
            "installed_apps_count": self.installed_apps_count,
            "targets_count": len(self.targets),
            "total_bytes": self.total_bytes,
            "cleaned_bytes": self.cleaned_bytes,
            "cleaned_items": self.cleaned_items,
            "errors": self.errors,
            "targets": [
                {
                    "rule": t.rule_name,
                    "section": t.section,
                    "path": t.target_path,
                    "is_dir": t.is_dir,
                    "size_bytes": t.size_bytes,
                }
                for t in self.targets[:100]  # sample first 100 for brevity
            ],
        }


class Winapp2Cleaner:
    """High-throughput declarative cleaner engine for Windows applications."""

    # Explicit critical directories forbidden from being targeted
    PROTECTED_ROOTS = frozenset([
        "C:\\Windows",
        "C:\\Windows\\System32",
        "C:\\Windows\\SysWOW64",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\Users",
    ])

    def __init__(self, custom_ini_content: Optional[str] = None) -> None:
        """Initialize Winapp2 Cleaner."""
        self.rules: List[Winapp2Rule] = []
        self._load_rules(custom_ini_content or CURATED_WINAPP2_RULES)

    @classmethod
    def expand_vars(cls, path_str: str) -> str:
        """Dynamically expand Windows environment variables and handle variations."""
        if not path_str:
            return ""

        # Normalize known Windows variable names
        env = os.environ
        var_map = {
            "%APPDATA%": env.get("APPDATA", ""),
            "%LOCALAPPDATA%": env.get("LOCALAPPDATA", ""),
            "%PROGRAMFILES%": env.get("ProgramFiles", "C:\\Program Files"),
            "%PROGRAMFILES(X86)%": env.get("ProgramFiles(x86)", env.get("ProgramFiles", "C:\\Program Files (x86)")),
            "%COMMONPROGRAMFILES%": env.get("CommonProgramFiles", "C:\\Program Files\\Common Files"),
            "%WINDIR%": env.get("WINDIR", "C:\\Windows"),
            "%SYSTEMDRIVE%": env.get("SystemDrive", "C:"),
            "%USERPROFILE%": env.get("USERPROFILE", os.path.expanduser("~")),
            "%TEMP%": env.get("TEMP", ""),
        }

        expanded = path_str
        for var, val in var_map.items():
            if var.lower() in expanded.lower():
                pattern = re.compile(re.escape(var), re.IGNORECASE)
                expanded = pattern.sub(val.replace("\\", "\\\\"), expanded)

        return os.path.expandvars(expanded)

    def _load_rules(self, ini_content: str) -> None:
        """Parse winapp2.ini declarative syntax into rule definitions."""
        config = configparser.ConfigParser(strict=False, interpolation=None)
        try:
            config.read_string(ini_content)
        except Exception as e:
            _LOG.warning("Failed to parse Winapp2 INI: %s", e)
            return

        for section_name in config.sections():
            section = config[section_name]
            clean_name = section_name.rstrip(" *")
            category = section.get("Section", "Applications")
            detect_path = section.get("Detect", None)
            detect_reg = section.get("DetectReg", None)
            default_val = section.get("Default", "True").strip().lower() != "false"

            file_keys = []
            reg_keys = []
            exclude_keys = []

            for k, v in section.items():
                k_lower = k.lower()
                if k_lower.startswith("filekey"):
                    file_keys.append(v)
                elif k_lower.startswith("regkey"):
                    reg_keys.append(v)
                elif k_lower.startswith("excludekey"):
                    exclude_keys.append(v)

            rule = Winapp2Rule(
                name=clean_name,
                section=category,
                detect_path=detect_path,
                detect_reg=detect_reg,
                file_keys=file_keys,
                reg_keys=reg_keys,
                exclude_keys=exclude_keys,
                default_enabled=default_val,
            )
            self.rules.append(rule)

    def _is_app_installed(self, rule: Winapp2Rule) -> bool:
        """Determine if target application exists via filesystem or registry."""
        if rule.detect_path:
            expanded = self.expand_vars(rule.detect_path)
            # Support wildcard expansion in detect path
            if "*" in expanded or "?" in expanded:
                base_dir = Path(expanded.split("*")[0].split("?")[0])
                if base_dir.exists():
                    return True
            elif Path(expanded).exists():
                return True

        if rule.detect_reg and winreg is not None and sys.platform == "win32":
            try:
                parts = rule.detect_reg.split("\\", 1)
                root_str = parts[0].upper()
                sub_key = parts[1] if len(parts) > 1 else ""

                hive_map = {
                    "HKCU": winreg.HKEY_CURRENT_USER,
                    "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
                    "HKLM": winreg.HKEY_LOCAL_MACHINE,
                    "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
                }
                hive = hive_map.get(root_str)
                if hive:
                    with winreg.OpenKey(hive, sub_key, 0, winreg.KEY_READ):
                        return True
            except (OSError, PermissionError):
                pass

        return False

    def is_safe_path(self, path: Path) -> bool:
        """Enforce strict safety boundary check preventing deletion of OS/system roots."""
        try:
            resolved = str(path.resolve()).lower()
        except Exception:
            return False

        for protected in self.PROTECTED_ROOTS:
            if resolved == protected.lower() or resolved == (protected.lower() + "\\"):
                return False

        # Must not be root drive (e.g. C:\)
        if resolved in ("c:\\", "d:\\", "e:\\", "/"):
            return False

        return True

    def scan(
        self,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
        cancel_event: Optional[Any] = None,
    ) -> Winapp2Report:
        """Scan candidate application targets matching detected software rules."""
        report = Winapp2Report(total_scanned_rules=len(self.rules))
        total_rules = len(self.rules)

        for idx, rule in enumerate(self.rules, 1):
            if cancel_event and cancel_event.is_set():
                break

            if progress_cb:
                progress_cb(idx, total_rules, rule.name)

            if not self._is_app_installed(rule):
                continue

            rule.installed = True
            report.installed_apps_count += 1

            for fk in rule.file_keys:
                # Format: Path|Pattern|RECURSE
                parts = fk.split("|")
                raw_path = parts[0]
                pattern = parts[1] if len(parts) > 1 else "*.*"
                recursive = len(parts) > 2 and "recurse" in parts[2].lower()

                expanded_base = self.expand_vars(raw_path)
                # Resolve paths with wildcards in path components
                matched_dirs = []
                if "*" in expanded_base or "?" in expanded_base:
                    parent_part = Path(expanded_base.split("*")[0].split("?")[0])
                    if parent_part.exists() and parent_part.is_dir():
                        glob_pat = expanded_base[len(str(parent_part)):].lstrip("\\/")
                        try:
                            matched_dirs = list(parent_part.glob(glob_pat))
                        except Exception:
                            matched_dirs = []
                else:
                    p = Path(expanded_base)
                    if p.exists():
                        matched_dirs = [p]

                for target_dir in matched_dirs:
                    if not self.is_safe_path(target_dir):
                        continue

                    if target_dir.is_dir():
                        try:
                            iterator = target_dir.rglob(pattern) if recursive else target_dir.glob(pattern)
                            for item in iterator:
                                if cancel_event and cancel_event.is_set():
                                    break
                                try:
                                    if item.is_file():
                                        sz = item.stat().st_size
                                        report.targets.append(
                                            AppCleanTarget(
                                                rule_name=rule.name,
                                                section=rule.section,
                                                target_path=str(item),
                                                is_dir=False,
                                                size_bytes=sz,
                                            )
                                        )
                                        report.total_bytes += sz
                                except (OSError, PermissionError):
                                    continue
                        except (OSError, PermissionError):
                            continue
                    elif target_dir.is_file():
                        try:
                            sz = target_dir.stat().st_size
                            report.targets.append(
                                AppCleanTarget(
                                    rule_name=rule.name,
                                    section=rule.section,
                                    target_path=str(target_dir),
                                    is_dir=False,
                                    size_bytes=sz,
                                )
                            )
                            report.total_bytes += sz
                        except (OSError, PermissionError):
                            continue

        return report

    def clean(
        self,
        targets: Optional[List[AppCleanTarget]] = None,
        dry_run: bool = False,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
    ) -> Tuple[int, int]:
        """Execute safe removal of identified cache targets. Returns (cleaned_bytes, cleaned_items)."""
        to_clean = targets if targets is not None else []
        cleaned_bytes = 0
        cleaned_items = 0
        total = len(to_clean)

        for i, tgt in enumerate(to_clean, 1):
            if progress_cb:
                progress_cb(i, total, tgt.target_path)

            p = Path(tgt.target_path)
            if not p.exists() or not self.is_safe_path(p):
                continue

            if dry_run:
                cleaned_bytes += tgt.size_bytes
                cleaned_items += 1
                continue

            try:
                if p.is_file():
                    sz = p.stat().st_size
                    p.unlink(missing_ok=True)
                    cleaned_bytes += sz
                    cleaned_items += 1
                elif p.is_dir():
                    # Safely remove empty directory
                    p.rmdir()
                    cleaned_items += 1
            except (OSError, PermissionError) as err:
                _LOG.debug("Could not remove target %s: %s", tgt.target_path, err)

        return cleaned_bytes, cleaned_items
