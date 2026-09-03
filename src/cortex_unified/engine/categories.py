"""Data-driven, risk-annotated registry of cleanable locations.

Rather than hardcoding "delete X" logic scattered across the app, cleanup
targets are declared as data with an explicit **risk level** and
**reversibility** note. This mirrors how Windows Disk Cleanup / Storage Sense
model cleanup "handlers" and lets the UI/CLI present honest, informed choices.

Design rules baked in from current best practice:
* Default to the lowest-risk, regenerable targets (temp/cache).
* Never include "previous Windows installations", WinSxS, or system restore
  points in the automatic set - those are destructive/irreversible and must be
  an explicit, separate opt-in (handled elsewhere, not here).
* Everything is age-filterable so "in-use" recent files can be spared.
"""

from __future__ import annotations

import enum
import os
import platform
from dataclasses import dataclass
from pathlib import Path


class RiskLevel(str, enum.Enum):
    """How risky it is to remove a category's contents."""

    LOW = "low"  # regenerable automatically (temp, thumbnail cache)
    MEDIUM = "medium"  # costs a re-download / re-index (package/browser caches)
    HIGH = "high"  # needs explicit user confirmation

    @property
    def rank(self) -> int:
        """rank."""
        return {"low": 0, "medium": 1, "high": 2}[self.value]
        """rank."""
        """rank."""


@dataclass(frozen=True, slots=True)
class CleanupCategory:
    """A declarative cleanup target."""

    id: str
    label: str
    description: str
    risk: RiskLevel
    paths: tuple[Path, ...]
    globs: tuple[str, ...] = ("*",)
    min_age_days: float = 0.0
    recursive: bool = True
    reversible: bool = False  # True only if removal is trivially undone
    default_enabled: bool = True

    def existing_paths(self) -> list[Path]:
        """Subset of declared paths that actually exist on this machine."""
        out: list[Path] = []
        for p in self.paths:
            try:
                if p.exists():
                    out.append(p)
            except OSError:
                continue
        return out


def _env_path(*names: str) -> list[Path]:
    """Return existing directories for the first set env var among *names*."""
    for n in names:
        v = os.environ.get(n)
        if v:
            return [Path(v)]
    return []


def _existing(paths) -> tuple[Path, ...]:
    """Filter to paths that currently exist (cheap, best-effort)."""
    out: list[Path] = []
    for p in paths:
        try:
            if p.exists():
                out.append(p)
        except OSError:
            continue
    return tuple(out)


# Directory NAMES universally understood to hold regenerable cache data.
_CACHE_NAMES = {
    "cache",
    "caches",
    "cachestorage",
    "code cache",
    "codecache",
    "gpucache",
    "gpu cache",
    "shadercache",
    "shader cache",
    "dawncache",
    "dawngraphitecache",
    "graphitedawncache",
    "component_crx_cache",
    "crashpad",
    "blob_storage",
    "cache_data",
    "data_reduction_proxy_leveldb",
    "grshadercache",
    "imagecache",
    "http cache",
    "networkcache",
    "offlinecache",
    "tempstate",
    # AI IDE / automation recordings (antigravity / jetski)
    "browser_recordings",
    "browser-recordings",
    "browserrecordings",
    "recordings",
    "recording",
    "screenshots",
    "screenshot",
    "brain",
    "jetski",
    "jetski_recording",
    "jetski_recording_",
    "artifacts",
    "traces",
    "videos",
    "video",
}
# Directories we must never descend into (huge, irrelevant, or sensitive).
_SKIP_NAMES = {
    "node_modules",
    ".git",
    ".svn",
    "windows",
    "winsxs",
    "system32",
    "syswow64",
    "$recycle.bin",
    "system volume information",
    "assembly",
    "installer",
    "drivers",
    "sourceengine",
}
# Module-level cache: discovery is a bit expensive, and app-data layout doesn't
# change within a session. Computed once per process, keyed by the base set.
_APP_CACHE_CACHE: dict[str, tuple[Path, ...]] = {}


def _fixed_drive_roots() -> list[Path]:
    """Scan all fixed local drives for common temp/project directories."""
    import string

    roots: list[Path] = []
    for letter in string.ascii_uppercase:
        drive = Path(f"{letter}:/")
        try:
            if drive.exists() and drive.is_dir():
                for name in ("tmp", "temp", "code", "projects"):
                    candidate = drive / name
                    try:
                        if candidate.is_dir():
                            roots.append(candidate)
                    except OSError:
                        continue
        except OSError:
            continue
    return roots


def _custom_temp_roots() -> list[Path]:
    """Extra temp roots outside %TEMP% (user custom dirs, secondary drives).

    Returns only existing directories so the registry never advertises missing
    paths. Covers common temp locations across all fixed drives.
    """
    candidates = [
        Path.home() / ".gemini" / "antigravity-ide" / "browser_recordings",
        Path.home() / ".gemini" / "antigravity-ide" / "brain",
    ]
    # Dynamically scan fixed drives for tmp/temp directories
    for drive_root in _fixed_drive_roots():
        if drive_root.name.lower() in ("tmp", "temp"):
            candidates.append(drive_root)
    out: list[Path] = []
    for p in candidates:
        try:
            if p.exists() and p.is_dir():
                out.append(p)
        except OSError:
            continue
    return out


def _discover_app_caches(bases: list[Path], max_depth: int = 6) -> tuple[Path, ...]:
    """Recursively find regenerable cache folders under *bases* (app-data roots).

    Modern apps scatter caches at varying depths (e.g.
    ``LocalAppData\\App\\User Data\\Default\\Cache\\Cache_Data``). We walk each
    base up to *max_depth* levels with ``os.scandir`` (fast), collect any
    directory whose NAME is a recognized cache name, and - crucially - do NOT
    descend into a matched cache (the whole subtree is cache) nor into known
    huge/irrelevant folders. Scoped to app-data roots, so it never walks the
    entire disk. Only known cache NAMES qualify - we never guess by content.
    """
    key = "|".join(sorted(str(b) for b in bases)) + f"#{max_depth}"
    if key in _APP_CACHE_CACHE:
        return _APP_CACHE_CACHE[key]

    found: list[Path] = []
    seen: set[str] = set()

    def _walk(path: Path, depth: int) -> None:
        """_walk."""
        if depth > max_depth:
            return
        for sub in _safe_scandir(path):
            name = sub.name.lower()
            if name in _CACHE_NAMES:
                k = str(sub).lower()
                if k not in seen:
                    seen.add(k)
                    found.append(sub)
                continue  # don't recurse into a cache folder
            if name in _SKIP_NAMES or name.startswith("$"):
                continue
            _walk(sub, depth + 1)
        """_walk."""
        """_walk."""

    for base in bases:
        try:
            if base.is_dir():
                _walk(base, 0)
        except OSError:
            continue
    result = tuple(found)
    _APP_CACHE_CACHE[key] = result
    return result


def _safe_scandir(path: Path) -> list[Path]:
    """List immediate subdirectories of *path*, ignoring errors."""
    out: list[Path] = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        out.append(Path(entry.path))
                except OSError:
                    continue
    except OSError:
        pass
    return out


def _get_dir_size(path: Path) -> int:
    """Fast estimate of reclaimable bytes under *path* (best-effort, no follow)."""
    total = 0
    try:
        for root, _, files in os.walk(path):
            for f in files:
                try:
                    total += (Path(root) / f).stat().st_size
                except OSError:
                    continue
    except OSError:
        pass
    return total


def _ai_ide_recording_dirs(home: Path) -> tuple[Path, ...]:
    """AI IDE automation recording roots (Antigravity / Gemini browser_recordings + brain)."""
    candidates = [
        home / ".gemini" / "antigravity-ide" / "browser_recordings",
        home / ".gemini" / "antigravity-ide" / "brain",
        Path("D:/tmp"),
        Path("D:/code/.tmp"),
    ]
    out: list[Path] = []
    for p in candidates:
        try:
            if p.exists() and p.is_dir():
                out.append(p)
        except OSError:
            continue
    return tuple(out)


def _docker_desktop_cache_dirs(local: Path) -> tuple[Path, ...]:
    """Filesystem cache used by Docker Desktop (parallel to SDK prune)."""
    candidates = [
        local / "Docker",
        local / "DockerDesktop",
        (
            Path(os.environ.get("APPDATA", "")) / "Docker"
            if os.environ.get("APPDATA")
            else None
        ),
    ]
    out: list[Path] = []
    for p in candidates:
        if p is None:
            continue
        try:
            if p.exists() and p.is_dir():
                out.append(p)
        except OSError:
            continue
    return tuple(out)


def _cargo_cache_dirs(home: Path) -> tuple[Path, ...]:
    """Cargo registry + git checkouts (re-downloaded via cargo fetch)."""
    candidates = [
        home / ".cargo" / "registry",
        home / ".cargo" / "git",
        home / ".cargo" / ".package-cache",
    ]
    return tuple(p for p in candidates if p.exists()) if candidates else ()


def _rustup_toolchain_dirs(home: Path) -> tuple[Path, ...]:
    """Rustup toolchains (opt-in, re-download via rustup toolchain install)."""
    p = home / ".rustup" / "toolchains"
    try:
        if p.is_dir():
            return (p,)
    except OSError:
        pass
    return ()


def _scoop_cache_dirs(home: Path) -> tuple[Path, ...]:
    """Scoop package cache (scoop cache rm *)."""
    candidates = [
        home / "scoop" / "cache",
        home / "scoop" / "apps",
        (
            Path(os.environ.get("SCOOP", "")) / "cache"
            if os.environ.get("SCOOP")
            else None
        ),
    ]
    out: list[Path] = []
    for p in candidates:
        if p is None or not str(p):
            continue
        try:
            if p.exists() and p.is_dir():
                out.append(p)
        except OSError:
            continue
    return tuple(out)


def _npm_pip_cache_dirs(home: Path, local: Path) -> tuple[Path, ...]:
    """Global package manager caches (npm, pip, etc.) for categories registry."""
    candidates = [
        local / "npm-cache",
        local / "pip" / "Cache",
        home / ".npm" / "_cacache",
        (
            Path(os.environ.get("APPDATA", "")) / "npm-cache"
            if os.environ.get("APPDATA")
            else None
        ),
        home / "AppData" / "Local" / "pip" / "Cache",
    ]
    out: list[Path] = []
    for p in candidates:
        if p is None or not str(p):
            continue
        try:
            if p.exists() and p.is_dir():
                out.append(p)
        except OSError:
            continue
    return tuple(out)


def _wsl_vhdx_dirs(home: Path) -> tuple[Path, ...]:
    """WSL distro ext4.vhdx host files (compactable, not deletable; surfaced for info)."""
    local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    # vhdx files live under LocalAppData\Packages\...\LocalState\ext4.vhdx and
    # AppData\Local\Docker\wsl etc.; we surface the parent dirs for size probe.
    # The cleaner itself uses VhdxManager for safe compaction; this category is
    # just an informational size estimate (HIGH risk, disabled by default).
    candidates = [
        local / "Packages",
    ]
    return tuple(p for p in candidates if p.exists())


def _browser_cache_dirs(local: Path) -> tuple[Path, ...]:
    """Existing browser cache directories across common Chromium browsers + Firefox."""
    dirs: list[Path] = []
    chromium = {
        "Chrome": local / "Google" / "Chrome" / "User Data",
        "Edge": local / "Microsoft" / "Edge" / "User Data",
        "Brave": local / "BraveSoftware" / "Brave-Browser" / "User Data",
        "Vivaldi": local / "Vivaldi" / "User Data",
    }
    for user_data in chromium.values():
        if not user_data.is_dir():
            continue
        for profile in _safe_scandir(user_data):
            for name in ("Cache", "Code Cache", "GPUCache", "Service Worker"):
                d = profile / name
                if d.is_dir():
                    dirs.append(d)
    # Firefox profiles use cache2
    ff = local / "Mozilla" / "Firefox" / "Profiles"
    if ff.is_dir():
        for profile in _safe_scandir(ff):
            c = profile / "cache2"
            if c.is_dir():
                dirs.append(c)
    return tuple(dirs)


def _windows_categories() -> list[CleanupCategory]:
    """_windows_categories."""
    home = Path.home()
    local_list = _env_path("LOCALAPPDATA") or [home / "AppData" / "Local"]
    roaming_list = _env_path("APPDATA") or [home / "AppData" / "Roaming"]
    local = local_list[0]
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    programdata = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
    cats: list[CleanupCategory] = []

    # 1. Temporary files (%TEMP% + Windows\Temp) -----------------------------
    # Include secondary temp roots on D: (manual-clean hits: D:\tmp 3.86GB, D:\code\.tmp)
    extra_temps = _custom_temp_roots()
    temp_paths = _existing(
        {
            *(_env_path("TEMP", "TMP")),
            local / "Temp",
            windir / "Temp",
            *extra_temps,
        }
    )
    cats.append(
        CleanupCategory(
            id="user_temp",
            label="Temporary files",
            description="OS/app scratch files in %TEMP%, Windows\\Temp, and temp dirs on fixed drives. Regenerated on demand.",
            risk=RiskLevel.LOW,
            paths=temp_paths,
            min_age_days=0.04,  # ~1 hour: spare files being written right now
            reversible=True,
        )
    )

    # 2. Thumbnail / icon cache ----------------------------------------------
    cats.append(
        CleanupCategory(
            id="thumbnail_cache",
            label="Thumbnail cache",
            description="Explorer thumbnail & icon database; rebuilt automatically.",
            risk=RiskLevel.LOW,
            paths=(local / "Microsoft" / "Windows" / "Explorer",),
            globs=("thumbcache_*.db", "iconcache_*.db"),
            recursive=False,
        )
    )

    # 3. Crash dumps & minidumps ---------------------------------------------
    cats.append(
        CleanupCategory(
            id="crash_dumps",
            label="Crash dumps",
            description="Application/system crash dump files (*.dmp).",
            risk=RiskLevel.LOW,
            paths=_existing((local / "CrashDumps", windir / "Minidump")),
            globs=("*.dmp",),
        )
    )

    # 4. DirectX / GPU shader cache ------------------------------------------
    cats.append(
        CleanupCategory(
            id="shader_cache",
            label="GPU shader cache",
            description="DirectX/NVIDIA/AMD shader caches; rebuilt on demand.",
            risk=RiskLevel.LOW,
            paths=_existing(
                (
                    local / "D3DSCache",
                    local / "NVIDIA" / "DXCache",
                    local / "NVIDIA" / "GLCache",
                    local / "AMD" / "DxCache",
                    local / "AMD" / "DxcCache",
                )
            ),
        )
    )

    # 5. Internet / web cache (system components) ----------------------------
    cats.append(
        CleanupCategory(
            id="inet_cache",
            label="System web cache",
            description="Windows/IE (WinINet) temporary internet files; regenerated.",
            risk=RiskLevel.LOW,
            paths=_existing((local / "Microsoft" / "Windows" / "INetCache",)),
        )
    )

    # 6. Windows Error Reporting ---------------------------------------------
    cats.append(
        CleanupCategory(
            id="error_reports",
            label="Error reports (WER)",
            description="Windows Error Reporting queued/archived reports.",
            risk=RiskLevel.LOW,
            paths=_existing(
                (
                    local / "Microsoft" / "Windows" / "WER",
                    programdata / "Microsoft" / "Windows" / "WER",
                )
            ),
        )
    )

    # 7. Auto-detected application caches (dynamic, deep) --------------------
    # Also scan temp roots on fixed drives for scattered caches
    _extra_cache_roots = [
        p
        for p in _custom_temp_roots()
        if p not in (local, roaming_list[0], programdata)
    ]
    app_caches = _discover_app_caches(
        [local, roaming_list[0], programdata, *_extra_cache_roots]
    )
    if app_caches:
        cats.append(
            CleanupCategory(
                id="app_caches",
                label="Application caches",
                description=f"Auto-detected regenerable caches from {len(app_caches)} folder(s), "
                "discovered deep across your app data and fixed drives.",
                risk=RiskLevel.LOW,
                paths=app_caches,
                min_age_days=0.04,
                reversible=True,
            )
        )

    # 8. Browser caches (re-downloaded) --------------------------------------
    browser = _browser_cache_dirs(local)
    if browser:
        cats.append(
            CleanupCategory(
                id="browser_cache",
                label="Browser caches",
                description="Chrome/Edge/Brave/Vivaldi/Firefox web caches; pages re-download.",
                risk=RiskLevel.MEDIUM,
                paths=browser,
            )
        )

    # 9. Delivery Optimization cache (can be very large) ---------------------
    cats.append(
        CleanupCategory(
            id="delivery_optimization",
            label="Delivery Optimization cache",
            description="Windows Update peer-download cache; re-downloaded if needed.",
            risk=RiskLevel.MEDIUM,
            paths=_existing(
                (
                    programdata
                    / "Microsoft"
                    / "Windows"
                    / "DeliveryOptimization"
                    / "Cache",
                )
            ),
            default_enabled=False,  # system dir; opt-in
        )
    )

    # 10. Windows Update download cache --------------------------------------
    cats.append(
        CleanupCategory(
            id="windows_update_cache",
            label="Windows Update download cache",
            description="Downloaded update payloads. Safe once updates are installed; re-downloaded if needed.",
            risk=RiskLevel.MEDIUM,
            paths=_existing((windir / "SoftwareDistribution" / "Download",)),
            default_enabled=False,  # touches a system dir; opt-in
        )
    )

    # 11. Prefetch (regenerated; brief re-learn) -----------------------------
    cats.append(
        CleanupCategory(
            id="prefetch",
            label="Prefetch data",
            description="App launch prefetch files; Windows rebuilds them (may briefly slow next launches).",
            risk=RiskLevel.MEDIUM,
            paths=_existing((windir / "Prefetch",)),
            globs=("*.pf",),
            default_enabled=False,  # opt-in - regenerating can briefly slow launches
        )
    )

    # 12. Recent items / jump lists (privacy) --------------------------------
    cats.append(
        CleanupCategory(
            id="recent_items",
            label="Recent items & jump lists",
            description="Explorer 'recent files' history and jump lists (privacy).",
            risk=RiskLevel.MEDIUM,
            paths=_existing((roaming_list[0] / "Microsoft" / "Windows" / "Recent",)),
            default_enabled=False,  # privacy/opt-in
        )
    )

    # 13. AI IDE recordings (Antigravity / Gemini) -----------------------------
    ai_paths = _ai_ide_recording_dirs(home)
    if ai_paths:
        cats.append(
            CleanupCategory(
                id="ai_ide_recordings",
                label="AI IDE recordings",
                description="Antigravity / Gemini browser recordings & brain screenshots "
                "(*.png/*.webp/*.jpg). Test recordings, safe to delete after runs; regenerated.",
                risk=RiskLevel.LOW,
                paths=ai_paths,
                globs=(
                    "*.png",
                    "*.webp",
                    "*.jpg",
                    "*.jpeg",
                    "*.webm",
                    "*.mp4",
                    "*.json",
                ),
                reversible=True,
                default_enabled=True,
            )
        )
    else:
        # Register even when absent so UI can show the category with 0 size
        # and let users pick D:\tmp manually. Use the would-be paths.
        cats.append(
            CleanupCategory(
                id="ai_ide_recordings",
                label="AI IDE recordings",
                description="Antigravity / Gemini browser recordings & brain screenshots "
                "(*.png/*.webp/*.jpg). Test recordings, safe to delete after runs.",
                risk=RiskLevel.LOW,
                paths=(
                    home / ".gemini" / "antigravity-ide" / "browser_recordings",
                    home / ".gemini" / "antigravity-ide" / "brain",
                    Path("D:/tmp"),
                ),
                globs=(
                    "*.png",
                    "*.webp",
                    "*.jpg",
                    "*.jpeg",
                    "*.webm",
                    "*.mp4",
                    "*.json",
                ),
                reversible=True,
                default_enabled=True,
            )
        )

    # 14. Docker Desktop filesystem cache --------------------------------------
    docker_dirs = _docker_desktop_cache_dirs(local)
    cats.append(
        CleanupCategory(
            id="docker_desktop_cache",
            label="Docker Desktop cache",
            description="Docker Desktop file cache (AppData\\Local\\Docker). Re-pull images if needed; complements docker system prune.",
            risk=RiskLevel.LOW,
            paths=docker_dirs if docker_dirs else (local / "Docker",),
            reversible=True,
            default_enabled=False,  # opt-in: re-download cost
        )
    )

    # 15. Cargo registry cache -------------------------------------------------
    cargo_dirs = _cargo_cache_dirs(home)
    cats.append(
        CleanupCategory(
            id="cargo_registry",
            label="Cargo registry cache",
            description="Rust Cargo registry cache (~/.cargo/registry, ~/.cargo/git). Re-downloaded via cargo fetch; use cargo clean for per-project targets.",
            risk=RiskLevel.MEDIUM,
            paths=(
                cargo_dirs
                if cargo_dirs
                else (home / ".cargo" / "registry", home / ".cargo" / "git")
            ),
            reversible=True,
            default_enabled=False,
        )
    )

    # 16. Rustup toolchains (opt-in, large) -----------------------------------
    rustup_dirs = _rustup_toolchain_dirs(home)
    cats.append(
        CleanupCategory(
            id="rustup_toolchains",
            label="Rustup toolchains",
            description="Rustup toolchains (~/.rustup/toolchains). Reinstall via rustup toolchain install; 1-2GB each.",
            risk=RiskLevel.HIGH,
            paths=rustup_dirs if rustup_dirs else (home / ".rustup" / "toolchains",),
            reversible=False,
            default_enabled=False,
        )
    )

    # 17. Scoop cache ----------------------------------------------------------
    scoop_dirs = _scoop_cache_dirs(home)
    cats.append(
        CleanupCategory(
            id="scoop_cache",
            label="Scoop cache",
            description="Scoop package cache (~/scoop/cache). Re-downloaded via scoop install; clean via scoop cache rm *.",
            risk=RiskLevel.LOW,
            paths=scoop_dirs if scoop_dirs else (home / "scoop" / "cache",),
            reversible=True,
            default_enabled=True,
        )
    )

    # 18. npm / pip caches (global package managers) ---------------------------
    pkg_dirs = _npm_pip_cache_dirs(home, local)
    if pkg_dirs:
        cats.append(
            CleanupCategory(
                id="global_package_caches",
                label="Global package caches (npm/pip)",
                description="npm-cache, pip cache, Yarn/PNPM store. Re-downloaded on next install.",
                risk=RiskLevel.LOW,
                paths=pkg_dirs,
                reversible=True,
                default_enabled=True,
            )
        )

    # 19. WSL distro disks (informational, compact via VhdxManager) -----------
    # Not deletable - vhdx files are compacted, not removed. Surfaced as HIGH-risk
    # informational entry so Storage Sense can show the 1.37GB ext4.vhdx style hit
    # and link to the Virtual Disks tool.
    cats.append(
        CleanupCategory(
            id="wsl_distros",
            label="WSL distro disks",
            description="WSL ext4.vhdx virtual disks. Don't delete - compact via Virtual Disks > WSL (wsl --shutdown + diskpart compact).",
            risk=RiskLevel.HIGH,
            paths=(local / "Packages",),
            globs=("ext4.vhdx", "*.vhdx", "*.vhd"),
            reversible=False,
            default_enabled=False,
        )
    )

    return cats
    """_windows_categories."""
    """_windows_categories."""


def _posix_categories() -> list[CleanupCategory]:
    """_posix_categories."""
    home = Path.home()
    system = platform.system()
    cats: list[CleanupCategory] = []

    if system == "Darwin":
        cats.append(
            CleanupCategory(
                id="user_cache",
                label="User caches",
                description="~/Library/Caches - app caches, safely regenerated.",
                risk=RiskLevel.LOW,
                paths=(home / "Library" / "Caches",),
                min_age_days=1.0,
            )
        )
        cats.append(
            CleanupCategory(
                id="user_logs",
                label="User logs",
                description="~/Library/Logs application log files.",
                risk=RiskLevel.LOW,
                paths=(home / "Library" / "Logs",),
                globs=("*.log", "*.log.*"),
            )
        )
        cats.append(
            CleanupCategory(
                id="tmp",
                label="Temporary files",
                description="/tmp and /var/tmp scratch space.",
                risk=RiskLevel.LOW,
                paths=(Path("/tmp"), Path("/var/tmp")),
                min_age_days=1.0,
                default_enabled=False,  # shared system dirs; opt-in
            )
        )
    else:  # Linux / other POSIX - follow XDG
        cache_home = Path(os.environ.get("XDG_CACHE_HOME", home / ".cache"))
        cats.append(
            CleanupCategory(
                id="user_cache",
                label="User cache (XDG)",
                description="$XDG_CACHE_HOME (~/.cache) - app caches, safely regenerated.",
                risk=RiskLevel.LOW,
                paths=(cache_home,),
                min_age_days=1.0,
            )
        )
        cats.append(
            CleanupCategory(
                id="trash",
                label="Trash",
                description="~/.local/share/Trash - freedesktop recycle bin.",
                risk=RiskLevel.MEDIUM,
                paths=(home / ".local" / "share" / "Trash" / "files",),
                reversible=False,
            )
        )
        cats.append(
            CleanupCategory(
                id="tmp",
                label="Temporary files",
                description="/tmp and /var/tmp scratch space.",
                risk=RiskLevel.LOW,
                paths=(Path("/tmp"), Path("/var/tmp")),
                min_age_days=1.0,
                default_enabled=False,
            )
        )
    return cats
    """_posix_categories."""
    """_posix_categories."""


def default_categories() -> list[CleanupCategory]:
    """Return the platform-appropriate cleanup category registry."""
    if platform.system() == "Windows":
        return _windows_categories()
    return _posix_categories()


def categories_by_id() -> dict[str, CleanupCategory]:
    """categories_by_id."""
    return {c.id: c for c in default_categories()}
    """categories_by_id."""
    """categories_by_id."""
