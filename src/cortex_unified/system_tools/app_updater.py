"""Software Updater - a safe GUI-friendly wrapper over Windows Package Manager.

``winget`` can update most installed apps, but it's command-line only and
intimidating. This wraps it: list what's upgradable, then upgrade selected apps
(or all) with explicit confirmation. Keeping third-party apps current is a real
security win, and unlike shady updaters this bundles nothing and hides nothing -
it just drives Microsoft's own tool.

Parsing note: ``winget upgrade`` has no stable machine-readable output, so we
parse its fixed-width table by locating column offsets from the header row -
robust to winget truncating long names with an ellipsis. All calls are
time-boxed; upgrades are launched non-interactively with agreements accepted.
"""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

_LOG = logging.getLogger("cortex.system_tools.app_updater")
_IS_WINDOWS = platform.system() == "Windows"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0


@dataclass(slots=True)
class UpgradableApp:
    name: str
    package_id: str
    current: str
    available: str
    source: str = "winget"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "id": self.package_id,
            "current": self.current,
            "available": self.available,
            "source": self.source,
        }


class AppUpdater:
    """List and apply application updates via winget."""

    def __init__(self) -> None:
        self.logger = _LOG

    @staticmethod
    def is_available() -> bool:
        """True if winget is installed and usable."""
        return _IS_WINDOWS and shutil.which("winget") is not None

    def list_upgradable(self) -> list[UpgradableApp]:
        """Return apps with available updates. Empty list if winget is absent."""
        if not self.is_available():
            return []
        out = self._run([
            "winget", "upgrade", "--include-unknown", "--disable-interactivity",
        ], timeout=120)
        return self.parse_upgrade_output(out or "")

    def upgrade(self, package_id: str) -> tuple[bool, str]:
        """Upgrade a single package by its winget Id."""
        if not self.is_available():
            return False, "winget is not available."
        if not package_id:
            return False, "No package id provided."
        out = self._run([
            "winget", "upgrade", "--id", package_id, "--exact", "--silent",
            "--accept-package-agreements", "--accept-source-agreements",
            "--disable-interactivity",
        ], timeout=1800)
        text = out or ""
        # winget prints "Successfully installed" on success.
        if "Successfully installed" in text or "No available upgrade found" in text:
            return True, "Update completed."
        if "No installed package found" in text:
            return False, "Package not found."
        return False, "Update did not report success (it may need elevation or a reboot)."

    def upgrade_all(self) -> tuple[bool, str]:
        """Upgrade every upgradable package (caller must confirm first)."""
        if not self.is_available():
            return False, "winget is not available."
        out = self._run([
            "winget", "upgrade", "--all", "--silent",
            "--accept-package-agreements", "--accept-source-agreements",
            "--disable-interactivity", "--include-unknown",
        ], timeout=3600)
        return (out is not None), ("Bulk update finished." if out is not None else "Bulk update failed.")

    # -- parsing (unit-testable, no winget needed) --------------------------

    @staticmethod
    def parse_upgrade_output(text: str) -> list[UpgradableApp]:
        """Parse winget's fixed-width upgrade table into structured rows."""
        lines = text.splitlines()
        header_idx = -1
        for i, line in enumerate(lines):
            if ("Name" in line and "Id" in line and "Version" in line
                    and "Available" in line):
                header_idx = i
                break
        if header_idx == -1:
            return []

        header = lines[header_idx]
        try:
            id_pos = header.index("Id")
            ver_pos = header.index("Version")
            avail_pos = header.index("Available")
            src_pos = header.index("Source")
        except ValueError:
            return []

        apps: list[UpgradableApp] = []
        for line in lines[header_idx + 1:]:
            stripped = line.strip()
            if not stripped:
                continue
            # separator row of dashes
            if set(stripped) <= {"-"}:
                continue
            # footer like "14 upgrades available."
            low = stripped.lower()
            if "upgrade" in low and "available" in low and stripped[0].isdigit():
                break
            # A valid data row is at least as wide as the Source column start.
            if len(line) < avail_pos:
                continue
            name = line[0:id_pos].strip()
            pkg_id = line[id_pos:ver_pos].strip()
            current = line[ver_pos:avail_pos].strip()
            available = line[avail_pos:src_pos].strip() if len(line) >= src_pos else line[avail_pos:].strip()
            source = line[src_pos:].strip() if len(line) > src_pos else "winget"
            if not pkg_id:
                continue
            apps.append(UpgradableApp(name, pkg_id, current, available, source or "winget"))
        return apps

    # -- helper -------------------------------------------------------------

    def _run(self, cmd: list[str], timeout: int) -> str | None:
        try:
            proc = subprocess.run(
                cmd, capture_output=True, timeout=timeout, creationflags=_NO_WINDOW,
            )
            # winget emits UTF-8 (ellipsis etc.); decode explicitly.
            return proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
        except (OSError, subprocess.SubprocessError) as exc:
            self.logger.debug("winget invocation failed: %s", exc)
            return None
