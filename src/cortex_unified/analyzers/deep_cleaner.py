"""Deep disk cleaner for Cortex Cleaner."""

import os
import shutil
import platform
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict

from cortex_unified.core.config import Config

SYSTEM = platform.system()
HOME = Path.home()

def get_path_size_safe(path: Path) -> int:
    """Safely calculate folder size in bytes using cortex's get_path_size logic, 
    but with a fallback to raw os.walk.
    """
    try:
        if path.is_file():
            return path.stat().st_size
        total = 0
        for p in path.rglob("*"):
            try:
                if p.is_file():
                    total += p.stat().st_size
            except Exception:
                pass
        return total
    except Exception:
        return 0

class DeepCleaner:
    """Cleaner for temporary files, caches, and orphaned app data across platforms."""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.found_items = [] # List of dicts
    
    def _find_orphaned_app_data(self) -> List[Path]:
        """Find app data folders for apps that are no longer installed."""
        orphans = []
        if SYSTEM == "Linux":
            check_dirs = [HOME / ".config", HOME / ".local/share", HOME / ".cache"]
            installed_binaries = set()
            for d in os.environ.get("PATH", "").split(os.pathsep):
                try:
                    for f in Path(d).iterdir():
                        if f.is_file():
                            installed_binaries.add(f.name.lower())
                except Exception:
                    pass
            desktop_apps = set()
            for dp in [Path("/usr/share/applications"), HOME / ".local/share/applications"]:
                if dp.exists():
                    for df in dp.glob("*.desktop"):
                        desktop_apps.add(df.stem.lower())
            
            known_system = {"dconf", "gvfs-metadata", "recently-used.xbel", "recently-used",
                            "sounds", "fonts", "icons", "themes", "applications", "mime",
                            "pkgconfig", "doc", "man", "locale", "keyrings", "systemd",
                            "glib-2.0", "tracker", "icc", "color", "xorg", "plasma", "kwin",
                            "baloo", "akonadi", "gnome", "nautilus", "gedit", "evince", 
                            "file-manager", "networkmanager", "pulseaudio", "pipewire", 
                            "bluetooth", "input-sources"}
            
            for base_dir in check_dirs:
                if not base_dir.exists():
                    continue
                try:
                    for item in base_dir.iterdir():
                        if not item.is_dir():
                            continue
                        name = item.name.lower()
                        if any(k in name for k in known_system):
                            continue
                        has_binary = name in installed_binaries or any(b.startswith(name[:4]) for b in installed_binaries if len(name) > 4)
                        has_desktop = name in desktop_apps or any(d.startswith(name[:4]) for d in desktop_apps if len(name) > 4)
                        if not has_binary and not has_desktop:
                            size = get_path_size_safe(item)
                            if size > 0:
                                orphans.append(item)
                except PermissionError:
                    pass

        elif SYSTEM == "Darwin":
            check_dirs = [HOME / "Library/Application Support", HOME / "Library/Preferences", HOME / "Library/Caches"]
            apps_dir = Path("/Applications")
            installed = set()
            if apps_dir.exists():
                for a in apps_dir.glob("*.app"):
                    installed.add(a.stem.lower())
            for base_dir in check_dirs:
                if not base_dir.exists():
                    continue
                try:
                    for item in base_dir.iterdir():
                        if not item.is_dir():
                            continue
                        name = item.name.lower()
                        short = name.split(".")[-1] if "." in name else name
                        if short not in installed and name not in installed:
                            orphans.append(item)
                except PermissionError:
                    pass

        elif SYSTEM == "Windows":
            appdata = Path(os.environ.get("APPDATA", HOME / "AppData/Roaming"))
            localapp = Path(os.environ.get("LOCALAPPDATA", HOME / "AppData/Local"))
            installed = set()
            try:
                import winreg
                for hive in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
                    for sub in [r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"]:
                        try:
                            key = winreg.OpenKey(hive, sub)
                            for i in range(winreg.QueryInfoKey(key)[0]):
                                try:
                                    skey = winreg.OpenKey(key, winreg.EnumKey(key, i))
                                    name = winreg.QueryValueEx(skey, "DisplayName")[0].lower()
                                    installed.add(name)
                                except Exception:
                                    pass
                        except Exception:
                            pass
            except ImportError:
                pass
            
            for base_dir in [appdata, localapp]:
                if not base_dir.exists():
                    continue
                try:
                    for item in base_dir.iterdir():
                        if not item.is_dir():
                            continue
                        name = item.name.lower()
                        if not any(name in app or app.startswith(name[:5]) for app in installed if len(name) > 4):
                            size = get_path_size_safe(item)
                            # > 100 KB for orphans in windows to avoid false small metadata
                            if size > 1024 * 100:
                                orphans.append(item)
                except PermissionError:
                    pass
        return orphans

    def _get_scan_targets(self):
        targets = {}
        if SYSTEM == "Linux":
            targets = {
                "🗑️  Trash": {"paths": [HOME / ".local/share/Trash/files", HOME / ".local/share/Trash/info"], "pattern": "*", "desc": "Recycle bin contents", "category": "Temp"},
                "🌡️  Temp Files": {"paths": [Path("/tmp"), Path("/var/tmp"), HOME / ".cache/tmp"], "pattern": "*", "desc": "Temporary system files", "category": "Temp"},
                "🖥️  Thumbnail Cache": {"paths": [HOME / ".cache/thumbnails"], "pattern": "*", "desc": "Image preview cache", "category": "Cache"},
                "📦  APT Package Cache": {"paths": [Path("/var/cache/apt/archives")], "pattern": "*.deb", "desc": "Downloaded .deb package installers", "category": "Cache"},
                "🐍  Python Bytecode": {"paths": [HOME], "pattern": "__pycache__", "recursive": True, "desc": "Python compiled bytecode folders", "category": "Cache"},
                "📋  Log Files": {"paths": [HOME / ".local/share", HOME / ".config"], "pattern": "*.log", "recursive": True, "desc": "Log files", "category": "Logs"},
                "🌐  Browser Cache": {"paths": [HOME / ".cache/google-chrome", HOME / ".cache/chromium", HOME / ".cache/mozilla/firefox"], "pattern": "*", "desc": "Web browser caches", "category": "Cache"},
                "📦  Package Cache": {"paths": [HOME / ".cache/pip", HOME / ".npm/_cacache", HOME / ".npm/cache"], "pattern": "*", "desc": "Package manager caches", "category": "Cache"},
                "🔧  VSCode Cache": {"paths": [HOME / ".config/Code/Cache", HOME / ".config/Code/CachedData", HOME / ".config/Code/logs"], "pattern": "*", "desc": "VS Code editor cache", "category": "Cache"},
                "🎵  Spotify Cache": {"paths": [HOME / ".config/spotify/Storage", HOME / ".cache/spotify"], "pattern": "*", "desc": "Spotify local cache", "category": "Cache"},
                "⚙️  Recently Used": {"paths": [HOME / ".local/share"], "pattern": "recently-used.xbel", "desc": "Recently opened history", "category": "Other"},
                "👻  Orphaned Data": {"paths": [], "pattern": "*", "desc": "Uninstalled app data", "is_orphan": True, "category": "Orphaned"}
            }
        elif SYSTEM == "Darwin":
            targets = {
                "🗑️  Trash": {"paths": [HOME / ".Trash"], "pattern": "*", "desc": "Trash contents", "category": "Temp"},
                "🌡️  Temp Files": {"paths": [Path("/tmp"), Path("/var/folders")], "pattern": "*", "desc": "Temporary system files", "category": "Temp"},
                "🖥️  Thumbnail Cache": {"paths": [HOME / "Library/Caches/com.apple.QuickLook.thumbnailcache"], "pattern": "*", "desc": "Preview thumbnails", "category": "Cache"},
                "🌐  Browser Cache": {"paths": [HOME / "Library/Caches/com.apple.Safari", HOME / "Library/Caches/Google/Chrome"], "pattern": "*", "desc": "Web browser caches", "category": "Cache"},
                "📦  Package Cache": {"paths": [HOME / "Library/Caches/pip"], "pattern": "*", "desc": "Package manager caches", "category": "Cache"},
                "🐍  Python Bytecode": {"paths": [HOME], "pattern": "__pycache__", "recursive": True, "desc": "Python compiled bytecode", "category": "Cache"},
                "📋  Log Files": {"paths": [HOME / "Library/Logs"], "pattern": "*.log", "recursive": True, "desc": "System and App logs", "category": "Logs"},
                "⚙️  App Caches": {"paths": [HOME / "Library/Caches"], "pattern": "*", "desc": "General application caches", "category": "Cache"},
                "👻  Orphaned Data": {"paths": [], "pattern": "*", "desc": "Uninstalled app data", "is_orphan": True, "category": "Orphaned"}
            }
        elif SYSTEM == "Windows":
            appdata = Path(os.environ.get("APPDATA", HOME / "AppData/Roaming"))
            localapp = Path(os.environ.get("LOCALAPPDATA", HOME / "AppData/Local"))
            temp = Path(os.environ.get("TEMP", HOME / "AppData/Local/Temp"))
            targets = {
                "🌡️  Temp Files": {"paths": [temp, Path("C:/Windows/Temp")], "pattern": "*", "desc": "Temporary system files", "category": "Temp"},
                "🌐  Browser Cache": {"paths": [localapp / "Google/Chrome/User Data/Default/Cache", localapp / "Google/Chrome/User Data/Default/Code Cache", localapp / "Microsoft/Edge/User Data/Default/Cache"], "pattern": "*", "desc": "Web browser caches", "category": "Cache"},
                "📦  Package Cache": {"paths": [localapp / "pip/Cache"], "pattern": "*", "desc": "Python package caches", "category": "Cache"},
                "🐍  Python Bytecode": {"paths": [HOME], "pattern": "__pycache__", "recursive": True, "desc": "Python bytecode", "category": "Cache"},
                "🔧  Windows Update Cache": {"paths": [Path("C:/Windows/SoftwareDistribution/Download")], "pattern": "*", "desc": "Windows Update downloads", "category": "Cache"},
                "📋  Log Files": {"paths": [appdata, localapp], "pattern": "*.log", "recursive": True, "desc": "App logs", "category": "Logs"},
                "👻  Orphaned Data": {"paths": [], "pattern": "*", "desc": "Uninstalled app data", "is_orphan": True, "category": "Orphaned"}
            }
        return targets

    def find_junk(self, progress_callback=None) -> List[Dict[str, Any]]:
        self.found_items = []
        targets = self._get_scan_targets()
        
        for name, cfg in targets.items():
            if progress_callback:
                progress_callback(f"Scanning: {name}")
                
            is_orphan = cfg.get("is_orphan", False)
            cat = cfg.get("category", "Other")
            recursive = cfg.get("recursive", False)
            pattern = cfg.get("pattern", "*")
            
            if is_orphan:
                orphans = self._find_orphaned_app_data()
                for p in orphans:
                    size = get_path_size_safe(p)
                    if size > 0:
                        self.found_items.append({
                            "category": cat,
                            "description": f"Orphaned App Data: {p.name}",
                            "path": p,
                            "size": size,
                            "is_orphan": True
                        })
                continue
            
            for base_path in cfg.get("paths", []):
                if not base_path.exists():
                    continue
                try:
                    matches = list(base_path.rglob(pattern)) if recursive else list(base_path.glob(pattern))
                    for p in matches:
                        if p == base_path:
                            continue
                        size = get_path_size_safe(p)
                        if size > 0:
                            self.found_items.append({
                                "category": cat,
                                "description": cfg.get("desc", name),
                                "path": p,
                                "size": size,
                                "is_orphan": False
                            })
                except PermissionError:
                    pass
                except Exception:
                    pass
        return self.found_items
    
    def get_stats(self) -> dict:
        total_size = sum(item["size"] for item in self.found_items)
        return {
            "items_found": len(self.found_items),
            "total_size_bytes": total_size,
            "total_size_human": self._format_bytes(total_size)
        }
    
    def _format_bytes(self, bytes_count: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"
