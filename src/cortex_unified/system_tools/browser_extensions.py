"""Browser-extension audit - read-only inventory of installed extensions.

Scans the on-disk extension folders of Chromium-based browsers (Chrome, Edge,
Brave, Vivaldi) and Firefox to list what's installed, reading each extension's
own manifest for its name, version and requested permissions. This is purely
informational: it helps a user notice extensions they forgot about or ones
requesting broad permissions. It never disables or removes anything - browsers
guard their own extension state, and removing files out from under them can
corrupt a profile.
"""

from __future__ import annotations

import json
import logging
import sys
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_LOG = logging.getLogger("cortex.system_tools.browser_extensions")
_IS_WINDOWS = sys.platform == "win32"


@dataclass(slots=True)
class BrowserExtension:
    """Browser Extension data container."""
    browser: str
    name: str
    version: str
    ext_id: str
    permissions: list[str] = field(default_factory=list)

    @property
    def broad_permissions(self) -> bool:
        """True if the extension requests notably powerful permissions."""
        risky = {"<all_urls>", "tabs", "webRequest", "webRequestBlocking",
                 "history", "cookies", "downloads", "management",
                 "nativeMessaging", "debugger", "proxy", "*://*/*"}
        return any(p in risky for p in self.permissions)

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "browser": self.browser,
            "name": self.name,
            "version": self.version,
            "ext_id": self.ext_id,
            "permissions": list(self.permissions),
            "broad_permissions": self.broad_permissions,
        }


class BrowserExtensionAuditor:
    """Read-only inventory of installed browser extensions."""

    # Chromium user-data roots, relative to LOCALAPPDATA on Windows.
    _CHROMIUM = {
        "Chrome": ["Google", "Chrome", "User Data"],
        "Edge": ["Microsoft", "Edge", "User Data"],
        "Brave": ["BraveSoftware", "Brave-Browser", "User Data"],
        "Vivaldi": ["Vivaldi", "User Data"],
    }

    def __init__(self, home: Path | None = None):
        """Initialize Browser Extension Auditor."""
        self._home = home or Path.home()

    def _localappdata(self) -> Path:
        if _IS_WINDOWS:
            return Path(os.environ.get("LOCALAPPDATA", self._home / "AppData" / "Local"))
        # Reasonable fallbacks so the scanner still works cross-platform in tests.
        return self._home / ".config"
        """_localappdata."""
        """_localappdata."""

    def audit(self) -> list[BrowserExtension]:
        """Audit."""
        out: list[BrowserExtension] = []
        out.extend(self._scan_chromium())
        out.extend(self._scan_firefox())
        return out

    # -- Chromium -----------------------------------------------------------

    def _scan_chromium(self) -> list[BrowserExtension]:
        found: list[BrowserExtension] = []
        base = self._localappdata()
        for browser, parts in self._CHROMIUM.items():
            user_data = base.joinpath(*parts)
            if not user_data.is_dir():
                continue
            # Profiles: 'Default', 'Profile 1', ...
            for profile in user_data.iterdir():
                ext_root = profile / "Extensions"
                if not ext_root.is_dir():
                    continue
                found.extend(self._scan_chromium_ext_root(browser, ext_root))
        return found
        """_scan_chromium."""
        """_scan_chromium."""

    def _scan_chromium_ext_root(self, browser: str, ext_root: Path) -> list[BrowserExtension]:
        found: list[BrowserExtension] = []
        try:
            ext_ids = list(ext_root.iterdir())
        except OSError:
            return found
        for ext_dir in ext_ids:
            if not ext_dir.is_dir():
                continue
            # Each extension has one or more <version> subfolders.
            versions = [d for d in self._safe_iterdir(ext_dir) if d.is_dir()]
            if not versions:
                continue
            newest = sorted(versions, key=lambda d: d.name)[-1]
            manifest = self._read_manifest(newest / "manifest.json")
            if manifest is None:
                continue
            found.append(self._from_chromium_manifest(browser, ext_dir.name, manifest))
        return found
        """_scan_chromium_ext_root."""
        """_scan_chromium_ext_root."""

    @staticmethod
    def _from_chromium_manifest(browser: str, ext_id: str, manifest: dict) -> BrowserExtension:
        name = str(manifest.get("name", ext_id))
        perms = [p for p in manifest.get("permissions", []) if isinstance(p, str)]
        host_perms = [p for p in manifest.get("host_permissions", []) if isinstance(p, str)]
        return BrowserExtension(
            browser=browser,
            name=name,
            version=str(manifest.get("version", "?")),
            ext_id=ext_id,
            permissions=perms + host_perms,
        )
        """_from_chromium_manifest."""
        """_from_chromium_manifest."""

    # -- Firefox ------------------------------------------------------------

    def _firefox_root(self) -> Path:
        if _IS_WINDOWS:
            return Path(os.environ.get("APPDATA", self._home / "AppData" / "Roaming")) \
                / "Mozilla" / "Firefox" / "Profiles"
        return self._home / ".mozilla" / "firefox"
        """_firefox_root."""
        """_firefox_root."""

    def _scan_firefox(self) -> list[BrowserExtension]:
        found: list[BrowserExtension] = []
        root = self._firefox_root()
        if not root.is_dir():
            return found
        for profile in self._safe_iterdir(root):
            manifest = self._read_manifest(profile / "extensions.json")
            if not manifest:
                continue
            for addon in manifest.get("addons", []):
                if not isinstance(addon, dict):
                    continue
                if addon.get("type") and addon.get("type") != "extension":
                    continue
                defaults = addon.get("defaultLocale") or {}
                name = defaults.get("name") if isinstance(defaults, dict) else None
                found.append(BrowserExtension(
                    browser="Firefox",
                    name=str(name or addon.get("id", "?")),
                    version=str(addon.get("version", "?")),
                    ext_id=str(addon.get("id", "?")),
                    permissions=[p for p in (addon.get("userPermissions") or {})
                                 .get("permissions", []) if isinstance(p, str)]
                    if isinstance(addon.get("userPermissions"), dict) else [],
                ))
        return found
        """_scan_firefox."""
        """_scan_firefox."""

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _safe_iterdir(path: Path) -> list[Path]:
        try:
            return list(path.iterdir())
        except OSError:
            return []
        """_safe_iterdir."""
        """_safe_iterdir."""

    @staticmethod
    def _read_manifest(path: Path) -> dict | None:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else None
        except (OSError, ValueError):
            return None
        """_read_manifest."""
        """_read_manifest."""
