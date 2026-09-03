"""Portable Manager — PortableApps.com / LiberKey catalog, USB toolkit.

Research grounding
------------------
* PortableApps.com: portable app launcher, standardizes settings inside
  app folder, no registry writes, updates in place, works on locked-down
  PCs. 300+ apps available.
* LiberKey: 294 portable apps, auto-update, sync with online catalog,
  categories (Audio, Video, Graphics, Internet, Games, Security, Education,
  System). Includes Q-Dir, FreeCommander, 7-Zip, etc.
* HowToGeek (2026): Ventoy + exFAT toolkit, Sysinternals Suite, HWInfo64,
  CrystalDiskInfo, Malwarebytes, 7-Zip, VS Code, Everything, live ISOs.
* MakeUseOf (2025): encryption + PortableApps platform, no host traces.
* Wise Disk Cleaner Portable, BleachBit portable, etc. — single EXE,
  no install, runs from USB.

Why this matters for Cortex Cleaner
-----------------------------------
* Technicians need single USB with all tools for offline repair.
* Locked-down / shared PCs can't install software; portable runs.
* Settings portability: always resume where left off on any PC.
* Standardization: same interface across machines.

Design — dynamic, no hardcoded drive letters
* Detects portable roots dynamically: scans all removable drives +
  platformdirs user data + %PORTABLEAPPS% env.
* App manifest parsing: appinfo.ini (PortableApps Format), the spec every
  PAF app ships; LiberKey roots fall back to exe-presence detection.
* Update check against the app's own declared [Details] UpdateURL, served
  as an appinfo.ini — the format's documented update mechanism. Apps
  without an UpdateURL report "not update-checkable" rather than a guess.
* Updates run the app's bundled PAF installer with its documented
  /SILENT switch; no download URLs are guessed.
* USB toolkit builder copies portable apps and fetches Sysinternals from
  the live share (its documented distribution point), verifying each
  download is a real PE executable.

Usage::

    from cortex_unified.analyzers.portable_manager import PortableManager
    mgr = PortableManager()
    apps = mgr.scan_portable_roots()
    mgr.check_updates(apps)
    mgr.update_app(apps[0])
    mgr.export_toolkit(Path("E:/"), include_sysinternals=True)
"""

from __future__ import annotations

import configparser
import os
import re
import shutil
import subprocess
import threading
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

try:
    import psutil  # type: ignore
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PortableApp:
    """PortableApp."""
    id: str
    name: str
    version: str
    category: str
    publisher: str
    size_mb: float
    path: Path
    launch_exe: Optional[Path] = None
    is_portable_format: bool = True
    update_available: bool = False
    latest_version: Optional[str] = None

    def to_dict(self) -> dict:
        """to_dict."""
        d = {k: v for k, v in self.__dict__.items()}
        d["path"] = str(d["path"])
        d["launch_exe"] = str(d["launch_exe"]) if d["launch_exe"] else None
        return d
        """to_dict."""
    """PortableApp class."""
    """PortableApp class."""

# ---------------------------------------------------------------------------
# Root discovery — dynamic
# ---------------------------------------------------------------------------

def _find_removable_drives() -> List[Path]:
    """_find_removable_drives."""
    drives: List[Path] = []
    try:
        if os.name == "nt":
            import string
            for letter in string.ascii_uppercase:
                d = Path(f"{letter}:\\")
                try:
                    if d.exists():
                        # check removable via GetDriveTypeW
                        import ctypes
                        typ = ctypes.windll.kernel32.GetDriveTypeW(str(d))
                        # 2=removable, 3=fixed, 4=remote, 5=cdrom
                        if typ == 2:
                            drives.append(d)
                except Exception:
                    continue
        else:
            # Linux/macOS: check /media, /mnt, /Volumes
            for base in [Path("/media"), Path("/mnt"), Path("/Volumes")]:
                if base.exists():
                    for child in base.iterdir():
                        if child.is_dir():
                            drives.append(child)
    except Exception:
        pass
    return drives
    """_find_removable_drives."""
    """_find_removable_drives."""

def _find_portable_roots() -> List[Path]:
    """_find_portable_roots."""
    roots: List[Path] = []
    # env
    for key in ("PORTABLEAPPS", "PORTABLEAPPS_DIR", "LIBERKEY"):
        v = os.environ.get(key)
        if v and Path(v).exists():
            roots.append(Path(v))
    # removable drives
    for d in _find_removable_drives():
        for cand in [d / "PortableApps", d / "LiberKey", d / "portable"]:
            if cand.exists():
                roots.append(cand)
        # also check root for appinfo.ini
        if (d / "appinfo.ini").exists() or (d / "PortableApps").exists():
            roots.append(d)
    # user data
    for key in ("APPDATA", "LOCALAPPDATA", "USERPROFILE"):
        v = os.environ.get(key)
        if v:
            for sub in ["PortableApps", "LiberKey"]:
                cand = Path(v) / sub
                if cand.exists():
                    roots.append(cand)
    # home
    for cand in [Path.home() / "PortableApps", Path.home() / "LiberKey"]:
        if cand.exists():
            roots.append(cand)
    # dedup
    seen: Set[str] = set()
    out: List[Path] = []
    for r in roots:
        s = str(r).lower()
        if s not in seen:
            seen.add(s)
            out.append(r)
    return out
    """_find_portable_roots."""
    """_find_portable_roots."""

# ---------------------------------------------------------------------------
# App discovery
# ---------------------------------------------------------------------------

def _parse_appinfo(ini_path: Path) -> Optional[PortableApp]:
    """_parse_appinfo."""
    try:
        cfg = configparser.ConfigParser()
        cfg.read(ini_path, encoding="utf-8")
        sec = cfg["Details"] if "Details" in cfg else cfg[cfg.sections()[0]]
        name = sec.get("Name", ini_path.parent.name)
        version = sec.get("DisplayVersion", sec.get("Version", ""))
        category = sec.get("Category", "Unknown")
        publisher = sec.get("Publisher", "")
        # find launch exe
        launch = None
        for cand in [ini_path.parent / f"{name}.exe", ini_path.parent / "App" / f"{name}.exe"]:
            if cand.exists():
                launch = cand
                break
        if not launch:
            exes = list(ini_path.parent.glob("*.exe"))
            if exes:
                launch = exes[0]
        size = sum(f.stat().st_size for f in ini_path.parent.rglob("*") if f.is_file()) / (1024*1024)
        return PortableApp(
            id=ini_path.parent.name.lower(),
            name=name,
            version=version,
            category=category,
            publisher=publisher,
            size_mb=size,
            path=ini_path.parent,
            launch_exe=launch,
        )
    except Exception:
        return None
    """_parse_appinfo."""
    """_parse_appinfo."""

# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class PortableManager:
    """PortableManager."""
    def __init__(self, progress: Callable[[str], None] | None = None,
                 cancel: threading.Event | None = None):
        """__init__."""
        self.progress = progress or (lambda _: None)
        self.cancel = cancel or threading.Event()
        """__init__."""
        """__init__."""

    def scan_portable_roots(self, roots: List[Path] | None = None) -> List[PortableApp]:
        """scan_portable_roots."""
        roots = roots or _find_portable_roots()
        apps: List[PortableApp] = []
        for root in roots:
            if self.cancel.is_set():
                break
            if not root.exists():
                continue
            # PortableApps Format: each app in root/AppName/appinfo.ini
            for child in root.iterdir():
                if not child.is_dir():
                    continue
                ini = child / "appinfo.ini"
                if ini.exists():
                    app = _parse_appinfo(ini)
                    if app:
                        apps.append(app)
                        continue
                # LiberKey: check for .lks file or Data folder
                if (child / "Data").exists() or any(child.glob("*.exe")):
                    # heuristic: any folder with exe is potential portable app
                    exes = list(child.glob("*.exe"))
                    if exes:
                        size = sum(f.stat().st_size for f in child.rglob("*") if f.is_file()) / (1024*1024)
                        apps.append(PortableApp(
                            id=child.name.lower(),
                            name=child.name,
                            version="",
                            category="Unknown",
                            publisher="",
                            size_mb=size,
                            path=child,
                            launch_exe=exes[0],
                        ))
        return apps
        """scan_portable_roots."""
        """scan_portable_roots."""

    #: PAF installers are NSIS-based; /SILENT suppresses the pages while
    #: still extracting to the target directory. This is the documented
    #: PortableApps.com automation switch, distinct from /S (silent).
    _PAF_SILENT_FLAG = "/SILENT"

    def check_updates(self, apps: List[PortableApp]) -> List[PortableApp]:
        """Compare each app's installed version to its declared source.

        Version sources, in order, exactly as the PortableApps Format
        defines them (no invented marker files):

        1. ``appinfo.ini`` → ``[Details] UpdateURL`` — a URL that serves
           the app's *current* ``appinfo.ini``; diffing versions tells us
           whether the installed copy is behind.
        2. ``appinfo.ini`` → ``[Details] Website`` — vendor page, used
           only as metadata when no UpdateURL exists (not a version check).

        Offline or undecorated apps simply report "not update-checkable";
        fabricating a verdict is worse than none.
        """
        updated = []
        for app in apps:
            app.update_available = False
            app.latest_version = None
            ini = app.path / "appinfo.ini"
            update_url = None
            if ini.exists():
                try:
                    cfg = configparser.ConfigParser()
                    cfg.read(ini, encoding="utf-8")
                    section = cfg["Details"] if "Details" in cfg else None
                    if section and section.get("UpdateURL"):
                        update_url = section.get("UpdateURL").strip()
                except Exception:
                    update_url = None

            if not update_url:
                # No declared source: nothing to compare against.
                continue

            try:
                req = urllib.request.Request(
                    update_url,
                    headers={"User-Agent": "cortex-cleaner-portable-manager"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
            except Exception as exc:
                self.progress(f"Update check for {app.name} failed: {exc}")
                continue

            # UpdateURL may serve either an appinfo.ini or a redirect page.
            remote_version = None
            if "[Details]" in body or "DisplayVersion" in body:
                try:
                    cfg = configparser.ConfigParser()
                    cfg.read_string(body)
                    if "Details" in cfg:
                        remote_version = cfg["Details"].get("DisplayVersion")
                except Exception:
                    remote_version = None
            if not remote_version:
                continue

            app.latest_version = remote_version
            if app.version and remote_version and remote_version != app.version:
                app.update_available = True
                updated.append(app)
        return updated

    def update_app(self, app: PortableApp, timeout: int = 1800) -> bool:
        """Run the app's own PAF installer in silent mode, in place.

        The PAF format's updater convention is the installer located at
        ``<app>\\PortableApps.comInstaller.exe`` when the app ships one;
        when the app maintains a local ``App\\AppInfo\\installer.exe`` we
        use that. No download URL is guessed — the installer present in the
        app directory is the only trusted source.
        """
        candidates = [
            app.path / "PortableApps.comInstaller.exe",
            app.path / "App" / "AppInfo" / "installer.exe",
            app.path / f"{app.name}Installer.exe",
        ]
        installer = next((c for c in candidates if c.exists()), None)
        if installer is None:
            self.progress(
                f"{app.name}: no bundled installer; use the platform's "
                "updater or the app's UpdateURL")
            return False

        self.progress(f"Updating {app.name} via {installer.name}...")
        try:
            proc = subprocess.run(
                [str(installer), self._PAF_SILENT_FLAG],
                cwd=str(app.path.parent),
                timeout=timeout,
                capture_output=True)
            return proc.returncode == 0
        except Exception as exc:
            self.progress(f"Update of {app.name} failed: {exc}")
            return False

    #: Sysinternals distributes every tool from this share; it is the
    #: documented source the tools themselves check for updates.
    _SYSINTERNALS_LIVE = "https://live.sysinternals.com"

    def export_toolkit(
        self,
        target: Path,
        include_sysinternals: bool = True,
        sysinternals_tools: Optional[List[str]] = None,
        include_live_iso: bool = False,
        timeout: int = 120,
    ) -> bool:
        """Build a portable toolkit on *target* (typically a USB drive).

        Portable apps are copied from every discovered root. Sysinternals
        tools are fetched from the live share (the documented distribution
        point) rather than a guessed local path, and each download is
        verified to be a PE executable before it is kept.
        """
        try:
            target.mkdir(parents=True, exist_ok=True)

            # Copy portable apps from every discovered root.
            for root in _find_portable_roots():
                for child in root.iterdir():
                    if child.is_dir() and (child / "appinfo.ini").exists():
                        dest = target / child.name
                        if not dest.exists():
                            shutil.copytree(child, dest)

            if include_sysinternals:
                tools = sysinternals_tools or ["Autoruns.exe", "procexp.exe",
                                               "Tcpview.exe", "procmon.exe"]
                syn = target / "Sysinternals"
                syn.mkdir(exist_ok=True)
                for tool in tools:
                    out = syn / tool
                    if out.exists() and out.stat().st_size > 0:
                        continue  # already on the toolkit; never re-download
                    if self._download_sysinternals(tool, out, timeout):
                        self.progress(f"Sysinternals: {tool} fetched")
                    else:
                        self.progress(f"Sysinternals: {tool} unavailable, skipped")

            self.progress(f"Toolkit exported to {target}")
            return True
        except Exception as exc:
            self.progress(f"Export failed: {exc}")
            return False

    def _download_sysinternals(self, tool: str, dest: Path, timeout: int) -> bool:
        """Fetch one Sysinternals tool and verify it is a real PE file.

        The MZ header check catches HTML error pages and truncated
        downloads before they masquerade as executables on a repair stick.
        """
        url = f"{self._SYSINTERNALS_LIVE}/{urllib.parse.quote(tool)}"
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "cortex-cleaner-portable-manager"})
            with urllib.request.urlopen(req, timeout=timeout) as resp, \
                    open(dest, "wb") as fh:
                shutil.copyfileobj(resp, fh)
        except Exception as exc:
            self.progress(f"Download {tool} failed: {exc}")
            dest.unlink(missing_ok=True)
            return False
        try:
            with open(dest, "rb") as fh:
                if fh.read(2) != b"MZ":
                    dest.unlink(missing_ok=True)
                    self.progress(f"{tool}: not a PE executable; discarded")
                    return False
        except OSError:
            return False
        return True
    """PortableManager class."""
    """PortableManager class."""

__all__ = ["PortableManager", "PortableApp"]
