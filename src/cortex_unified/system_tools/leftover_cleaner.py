"""Leftover Cleaner - find and safely remove what an uninstaller leaves behind.

Why this exists
---------------
Most Windows uninstallers only remove the files they wrote at install time.
Folders under ``AppData``, ``ProgramData``, ``Program Files``, orphaned Start
Menu shortcuts and ``SOFTWARE`` registry keys routinely survive, and on C:\\
they accumulate to gigabytes over years of installs. This module implements
the detection pipeline used by the reputable open-source uninstallers
(Bulk Crap Uninstaller's published ``JunkManager``/``ConfidenceGenerators``
heuristics, cross-checked against Revo/Geek documented behaviour):

1. **Inventory** every installed app from the four Uninstall registry branches
   (HKLM/HKCU x 64-bit/WOW6432Node) with publisher, InstallLocation and
   installer type (MSI GUID / InnoSetup ``_is1`` / NSIS).
2. **Sweep** the standard leftover locations for folders, registry keys and
   shortcuts whose names match the target app's tokens (bounded edit distance
with a
   hard <=4-char floor and a 1/3-length cut-off - never naive substring).
3. **Score** every finding with signed evidence points (empty folder +4,
   publisher match +4, executables present -4, name claimed by a live app -7,
   ...) and map the raw score to Bad / Questionable / Good / VeryGood.
4. **Gate** results through safety filters: known-folder prohibition, a
   directory-name blacklist (``Microsoft``, ``Common Files``, ``Intel``-style
   shared vendor folders), the Windows System attribute, self-protection, and
   a cross-check against every currently-installed app.
5. **Clean** with three undo layers: Recycle Bin for files (never a silent
   permanent delete), ``reg export`` backups before any registry deletion, and
   an atomic JSON operation journal recording every disposition.

Nothing is deleted by scanning; deletion always happens through
:class:`LeftoverCleaner` with explicit user-reviewed findings.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

logger = logging.getLogger("leftover_cleaner")

try:  # pragma: no cover - platform guard
    import winreg
    HAS_WINREG = True
except ImportError:  # pragma: no cover
    winreg = None  # type: ignore[assignment]
    HAS_WINREG = False

IS_WINDOWS = os.name == "nt"


# =====================================================================
#  String matching (BCU's MatchStringToProductName contract, computed
#  with a bounded Levenshtein distance - exact and deterministic on the
#  short strings folder/key names actually are)
# =====================================================================

def edit_distance(a: str, b: str, max_distance: int | None = None) -> int:
    """Exact Levenshtein distance; early-exits once *max_distance* is exceeded
    (returning a value > max_distance) so scanning stays cheap."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if max_distance is not None and abs(la - lb) > max_distance:
        return max(la, lb)
    if not a or not b:
        return la + lb
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        best = cur[0]
        ca = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ca == b[j - 1] else 1
            cur[j] = min(prev[j] + 1,        # deletion
                         cur[j - 1] + 1,     # insertion
                         prev[j - 1] + cost)  # substitution
            best = min(best, cur[j])
        if max_distance is not None and best > max_distance:
            return max(la, lb)
        prev = cur
    return prev[lb]


def match_string_to_product(candidate: str, product_name: str) -> int:
    """Decide whether *candidate* (a folder/key name) names *product_name*.

    Returns ``-1`` for no match, ``0``/``1`` for perfect/near-perfect,
    ``2`` for substring containment, otherwise a positive distance that is
    only accepted when smaller than a third of the shorter name. Names of
    four characters or fewer never match - this is what keeps "Java" from
    matching "JRE" style false positives.
    """
    candidate = candidate.lower().replace("_", " ").strip()
    product_name = product_name.lower().replace("_", " ").strip()
    if not candidate or not product_name:
        return -1
    if len(candidate) <= 4 or len(product_name) <= 4:
        return -1
    distance = edit_distance(product_name, candidate, max_distance=2)
    if distance == 0:
        return 0
    if distance == 1:
        return 1
    shorter = min(len(candidate), len(product_name))
    if candidate in product_name or product_name in candidate:
        return 2
    if distance < shorter / 3:
        return distance
    return -1


_NAME_NOISE = re.compile(
    r"\((?:x64|x86|64-bit|32-bit)\)|\b(?:free|version|edition|update|setup)\b",
    re.IGNORECASE,
)


#: Words that appear in display names but carry NO product identity.
#: Tokenizing "Definitely Not Installed XYZ" must not yield "installed",
#: or every "InstalledScripts"-style system folder becomes a false positive.
TOKEN_STOPWORDS = frozenset({
    "installed", "uninstall", "installer", "setup", "install", "update",
    "upgrade", "version", "edition", "build", "release", "final", "free",
    "software", "application", "program", "system", "tools", "tool",
    "utility", "utilities", "manager", "client", "server", "runtime",
    "redistributable", "package", "packages", "bundle", "suite", "platform",
    "windows", "microsoft", "bit", "bits", "x64", "x86",
})


def build_tokens(display_name: str, publisher: str = "") -> list[str]:
    """Extract specific-enough search tokens from an app's display name."""
    raw = _NAME_NOISE.sub(" ", display_name.lower())
    parts = [p for p in re.split(r"[\s\-_.,()&+]+", raw.strip()) if p]
    tokens = {p for p in parts
              if len(p) >= 4 and p not in TOKEN_STOPWORDS}
    joined = re.sub(r"[^a-z0-9]", "", raw)
    if len(joined) >= 5:
        tokens.add(joined)
    pub = re.sub(r"[^a-z0-9]", "", publisher.lower())
    generic_publishers = {
        "microsoft", "google", "apple", "intel", "nvidia", "adobe",
        "mozilla", "corporation", "inc", "ltd", "llc", "software",
    }
    if len(pub) >= 5 and pub not in generic_publishers:
        tokens.add(pub)
    return sorted(tokens)


# =====================================================================
#  Confidence scoring (weights follow BCU's ConfidenceCollection)
# =====================================================================

VERY_GOOD, GOOD, QUESTIONABLE, BAD = "VeryGood", "Good", "Questionable", "Bad"

_EXPLICIT_CONNECTION = 4
_EMPTY_FOLDER = 4
_COMPANY_MATCH = 4
_PERFECT_MATCH = 2
_LEAF_FOLDER = 2
_DIRECTLY_IN_KNOWN_FOLDER = -1
_NAME_EQUALS_COMPANY = -2
_MANY_FILES = -2
_SIMILAR_APP_CLAIMS = -2
_QUESTIONABLE_NAME = -3
_EXECUTABLES_PRESENT = -4
_NAME_STILL_USED = -4
_PUBLISHER_STILL_USED = -4
_DIRECTORY_STILL_USED = -7


def confidence_level(raw: int) -> str:
    """Map a raw signed score to a human review tier (BCU mapping)."""
    if raw < 0:
        return BAD
    if raw <= 1:
        return QUESTIONABLE
    if raw <= 4:
        return GOOD
    return VERY_GOOD


# =====================================================================
#  Safety gates
# =====================================================================

#: Directory names that are NEVER candidates, no matter how well they match.
#: Shared vendor/runtime folders ("Intel", "Microsoft", "Common Files") are
#: the classic false-positive trap - see BCU's DirectoryNameBlacklist.
DIRECTORY_NAME_BLACKLIST = frozenset({
    "microsoft", "microsoft games", "temp", "programs", "common", "common files",
    "clients", "downloads", "desktop", "internet explorer", "windows",
    "windows nt", "windows photo viewer", "windows mail", "windows defender",
    "windows media player", "uninstall information", "reference assemblies",
    "installshield installation information", "installer", "winsxs",
    "windowsapps", "directx", "directxredist", "intel", "amd", "nvidia",
    "program files", "program files (x86)", "appdata", "local", "locallow",
    "roaming", "virtualstore", "packages", "modifiablewindowsapps",
})

#: Generic folder names that carry little identity signal on their own.
QUESTIONABLE_NAMES = frozenset({
    "install", "settings", "config", "configuration", "users", "data",
    "cache", "logs", "temp", "bin", "app", "shared", "files",
})

_KNOWN_FOLDER_ENVS = (
    "SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramData",
    "APPDATA", "LOCALAPPDATA", "USERPROFILE", "PUBLIC", "HOMEDRIVE",
    "ALLUSERSPROFILE", "TEMP", "TMP",
)


@dataclass(slots=True)
class SafetyPolicy:
    """Paths the scanner/cleaner must never propose or touch."""

    #: Absolute paths (lowercased, normalized) that are always prohibited.
    protected_paths: frozenset[str] = field(default_factory=frozenset)
    #: The cleaning tool's own install directory (self-protection).
    own_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Normalize stored paths to case-folded absolute form for matching."""
        self.protected_paths = frozenset(
            os.path.normcase(os.path.abspath(p)) for p in self.protected_paths)
        self.own_paths = tuple(
            os.path.normcase(os.path.abspath(p)) for p in self.own_paths)

    @classmethod
    def build(cls, extra_protected: Iterable[str] = ()) -> "SafetyPolicy":
        """Build a policy protecting known-folder roots plus *extra_protected*.

        Protects the directories named by _KNOWN_FOLDER_ENVS (SystemRoot,
        Program Files, ProgramData, APPDATA, TEMP, ...), any caller-supplied
        extra paths, and this module's own directory (self-protection).
        """
        protected: set[str] = set()
        for env in _KNOWN_FOLDER_ENVS:
            value = os.environ.get(env)
            if value:
                protected.add(os.path.normcase(os.path.abspath(value)))
        protected.update(
            os.path.normcase(os.path.abspath(p)) for p in extra_protected)
        own = tuple(
            os.path.normcase(os.path.abspath(p))
            for p in (os.path.dirname(os.path.abspath(__file__)),)
        )
        return cls(protected_paths=frozenset(protected), own_paths=own)

    def is_prohibited(self, path: str | Path) -> bool:
        """True when *path* IS a protected root (its children are allowed)."""
        try:
            norm = os.path.normcase(os.path.abspath(str(path)))
        except OSError:
            return True
        if norm in self.protected_paths or norm in self.own_paths:
            return True
        for root in self.protected_paths:
            if norm == root:
                return True
        return False


def _has_system_attribute(path: str) -> bool:
    """Windows System attribute means 'not a leftover candidate'."""
    if not IS_WINDOWS:
        return False
    try:
        attrs = os.stat(path).st_file_attributes  # type: ignore[attr-defined]
        return bool(attrs & 0x4)  # FILE_ATTRIBUTE_SYSTEM
    except (OSError, AttributeError):
        return False


def _is_reparse_point(path: str) -> bool:
    """Junction/symlink check - such entries are recorded, never descended."""
    try:
        if IS_WINDOWS:
            attrs = os.stat(path, follow_symlinks=False).st_file_attributes  # type: ignore[attr-defined]
            return bool(attrs & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
        return os.path.islink(path)
    except OSError:
        return False


# =====================================================================
#  Inventory
# =====================================================================

_UNINSTALL_BRANCHES = [
    (winreg.HKEY_LOCAL_MACHINE, "HKLM",
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall") if HAS_WINREG else None,
    (winreg.HKEY_LOCAL_MACHINE, "HKLM",
     r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall") if HAS_WINREG else None,
    (winreg.HKEY_CURRENT_USER, "HKCU",
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall") if HAS_WINREG else None,
]
_UNINSTALL_BRANCHES = [b for b in _UNINSTALL_BRANCHES if b is not None]

_MSI_GUID = re.compile(r"^\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-"
                       r"[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}$")


@dataclass(slots=True)
class InstalledApp:
    """One entry from an Uninstall registry branch."""

    name: str
    publisher: str = ""
    version: str = ""
    install_location: str = ""
    uninstall_key: str = ""           # full registry path of the entry
    display_icon: str = ""
    installer_type: str = "unknown"   # msi | inno | nsis | unknown
    tokens: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        """Return a plain-dict view of this app entry (for journals/reports)."""
        return {
            "name": self.name, "publisher": self.publisher,
            "version": self.version, "install_location": self.install_location,
            "uninstall_key": self.uninstall_key,
            "installer_type": self.installer_type,
        }


def detect_installer_type(key_name: str, uninstall_string: str) -> str:
    """Classify the installer family from registry fingerprints."""
    if _MSI_GUID.match(key_name.strip()):
        return "msi"
    if key_name.endswith("_is1"):
        return "inno"
    us = (uninstall_string or "").lower()
    if "uninst" in us and ("/s" in us or "unins" in us):
        return "nsis"
    return "unknown"


def read_installed_apps() -> list[InstalledApp]:
    """Enumerate installed apps from all Uninstall branches (read-only)."""
    apps: list[InstalledApp] = []
    if not HAS_WINREG:
        return apps
    for hive, hive_name, branch in _UNINSTALL_BRANCHES:
        try:
            root = winreg.OpenKey(hive, branch, 0,
                                  winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        except OSError:
            continue
        try:
            count = winreg.QueryInfoKey(root)[0]
            for i in range(count):
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    continue
                app = _read_uninstall_entry(hive, hive_name, branch, sub)
                if app is not None:
                    apps.append(app)
        finally:
            winreg.CloseKey(root)
    # Deduplicate by (name, key) - WOW6432Node can mirror HKLM entries.
    seen: set[tuple[str, str]] = set()
    unique: list[InstalledApp] = []
    for app in apps:
        k = (app.name.lower(), app.uninstall_key.lower())
        if k not in seen:
            seen.add(k)
            unique.append(app)
    return unique


def _read_uninstall_entry(hive, hive_name: str, branch: str,
                          subkey: str) -> InstalledApp | None:
    """Read one Uninstall subkey (DisplayName, Publisher, ...) via winreg.

    Returns None for entries that cannot be opened or that have no
    DisplayName (system-component entries are skipped). Uses read-only
    access with the 64-bit view; nothing is written.
    """
    path = f"{branch}\\{subkey}"
    try:
        key = winreg.OpenKey(hive, path, 0,
                             winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
    except OSError:
        return None
    try:
        values: dict[str, str] = {}
        for name in ("DisplayName", "Publisher", "DisplayVersion",
                     "InstallLocation", "DisplayIcon", "UninstallString"):
            try:
                value, _ = winreg.QueryValueEx(key, name)
                if isinstance(value, str):
                    values[name] = value
            except OSError:
                continue
    finally:
        winreg.CloseKey(key)
    name = values.get("DisplayName", "").strip()
    if not name:
        return None  # system component entries without a display name
    return InstalledApp(
        name=name,
        publisher=values.get("Publisher", "").strip(),
        version=values.get("DisplayVersion", "").strip(),
        install_location=_clean_registry_path(values.get("InstallLocation", "")),
        uninstall_key=path,
        display_icon=values.get("DisplayIcon", ""),
        installer_type=detect_installer_type(subkey, values.get("UninstallString", "")),
    )


def _clean_registry_path(value: str) -> str:
    """Strip quotes/arguments/icon-index suffixes from a registry path value."""
    value = value.strip().strip('"')
    value = value.split(",")[0].strip()      # DisplayIcon "exe,-1" form
    value = value.split(" /")[0].strip()     # trailing uninstaller args
    return value.rstrip("\\").strip()


# =====================================================================
#  Findings
# =====================================================================

def _tasks_root() -> Path:
    """The Windows scheduled-tasks definition folder."""
    return Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "Tasks"


@dataclass(slots=True)
class LeftoverFinding:
    """One reviewed-able leftover candidate with its evidence."""

    kind: str                 # folder | file | registry | shortcut
    path: str                 # filesystem path or full registry key path
    size_bytes: int = 0
    score: int = 0
    level: str = QUESTIONABLE
    reasons: list[str] = field(default_factory=list)
    app_name: str = ""

    def to_dict(self) -> dict:
        """Return a plain-dict view of this finding (for journals/reports)."""
        return {
            "kind": self.kind, "path": self.path,
            "size_bytes": self.size_bytes, "score": self.score,
            "level": self.level, "reasons": list(self.reasons),
            "app_name": self.app_name,
        }


def _add(f: LeftoverFinding, points: int, reason: str) -> None:
    """Add *points* for *reason* to a finding and refresh its confidence level."""
    f.score += points
    f.reasons.append(f"{points:+d} {reason}")
    f.level = confidence_level(f.score)


# =====================================================================
#  User exclusions ("keep this - never flag it again")
# =====================================================================

class ExclusionsStore:
    """Persisted list of paths the user chose to keep.

    When a leftover review flags something the user recognises as wanted
    (a shared vendor folder, a profile they care about), they can exclude it:
    the path is stored in ``~/.cortex_cleaner/exclusions.json`` and every
    later scan silently drops findings at or beneath it. Writes are atomic;
    a corrupt file degrades to an empty list rather than raising.
    """

    def __init__(self, path: str | Path | None = None):
        """Initialize the store, loading from *path* (default
        ``~/.cortex_cleaner/exclusions.json``)."""
        self._path = Path(path) if path else (
            Path.home() / ".cortex_cleaner" / "exclusions.json")
        self._paths: set[str] = set()
        self._load()

    # -- persistence ------------------------------------------------------

    def _load(self) -> None:
        """Load the JSON exclusion list; unreadable/corrupt file means empty."""
        try:
            if self._path.exists():
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    self._paths = {
                        os.path.normcase(os.path.normpath(str(p)))
                        for p in raw if isinstance(p, str) and p.strip()
                    }
        except (OSError, ValueError):
            logger.debug("exclusions unreadable; starting empty",
                         exc_info=True)
            self._paths = set()

    def save(self) -> bool:
        """Atomically persist the exclusion list (tmp file + replace).

        Returns True on success; an OSError is logged and False is returned
        rather than raised.
        """
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = sorted(self._paths)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(self._path)
            return True
        except OSError:
            logger.debug("could not save exclusions", exc_info=True)
            return False

    # -- membership ---------------------------------------------------------

    @staticmethod
    def _norm(path: str | Path) -> str:
        """Normalize a path (case + separators) for exclusion matching."""
        try:
            return os.path.normcase(os.path.normpath(str(path)))
        except OSError:  # pragma: no cover - defensive
            return str(path).lower()

    def add(self, path: str | Path) -> bool:
        """Exclude *path* (and everything beneath it). Persists immediately."""
        norm = self._norm(path)
        if norm not in self._paths:
            self._paths.add(norm)
            return self.save()
        return True

    def discard(self, path: str | Path) -> bool:
        """Remove *path* from the exclusions and persist immediately."""
        norm = self._norm(path)
        if norm in self._paths:
            self._paths.discard(norm)
            return self.save()
        return True

    def paths(self) -> tuple[str, ...]:
        """Sorted tuple of all excluded (normalized) paths."""
        return tuple(sorted(self._paths))

    def __len__(self) -> int:
        """Number of excluded paths."""
        return len(self._paths)

    def is_excluded(self, path: str | Path) -> bool:
        """True when *path* IS an excluded entry or lives beneath one."""
        norm = self._norm(path)
        for ex in self._paths:
            if norm == ex or norm.startswith(ex + os.sep):
                return True
        return False


# =====================================================================
#  Scanner
# =====================================================================

#: Registry value names that explicitly point at an install directory
#: (verified list from BCU's SoftwareRegKeyScanner).
_INSTALL_DIR_VALUE_NAMES = frozenset({
    "installdir", "install_dir", "install directory", "instdir",
    "applicationpath", "install folder", "last stable install path",
    "targetdir", "javahome", "installlocation",
})
_EXE_PATH_VALUE_NAMES = frozenset({
    "exe64", "exe32", "executable", "pathtoexe", "exepath",
})
_AMBIGUOUS_PATH_VALUE_NAMES = frozenset({
    "path", "path64", "pth", "playerpath", "apppath",
})

#: Walk blacklist while descending HKLM/HKCU\\SOFTWARE (BCU list).
_REGISTRY_WALK_BLACKLIST = frozenset({
    "microsoft", "wow6432node", "windows", "classes", "clients",
    "registeredapplications", "policymanager", "personalization",
})

_MAX_FS_DEPTH = 2          # levels below each sweep root (BCU default)
_MAX_REG_DEPTH = 2         # levels below SOFTWARE


class LeftoverScanner:
    """Finds leftovers for one uninstalled app, or orphaned folders generally.

    The scanner is strictly read-only. Every method returns findings with
    evidence; nothing is removed here.

    ``exclusions`` (optional) drops findings the user previously chose to
    keep; ``cancel_event`` makes every long sweep cooperative - once set,
    sweeps stop early and partial results are returned.
    """

    def __init__(self, installed_apps: Sequence[InstalledApp] | None = None,
                 policy: SafetyPolicy | None = None,
                 exclusions: ExclusionsStore | None = None,
                 cancel_event=None):
        """Initialize the scanner; the app inventory loads lazily on first scan."""
        self.policy = policy or SafetyPolicy.build()
        self.exclusions = exclusions
        self.cancel_event = cancel_event
        self._installed = list(installed_apps) if installed_apps is not None else None
        self._live_names: set[str] = set()
        self._live_publishers: set[str] = set()
        self._live_locations: list[str] = []
        self._inventory_loaded = False

    def _cancelled(self) -> bool:
        """True when the caller's cancel_event (if any) has been set."""
        return self.cancel_event is not None and self.cancel_event.is_set()

    def _allowed(self, f: LeftoverFinding) -> bool:
        """True when the finding is not under a user exclusion."""
        return self.exclusions is None or not self.exclusions.is_excluded(f.path)

    # -- inventory ------------------------------------------------------

    def _ensure_inventory(self) -> None:
        """Lazily load installed apps and build name/publisher/location sets."""
        if self._inventory_loaded:
            return
        if self._installed is None:
            self._installed = read_installed_apps()
        for app in self._installed:
            self._live_names.add(re.sub(r"[^a-z0-9]", "", app.name.lower()))
            if app.publisher:
                self._live_publishers.add(
                    re.sub(r"[^a-z0-9]", "", app.publisher.lower()))
            if app.install_location:
                self._live_locations.append(
                    os.path.normcase(os.path.abspath(app.install_location)))
        self._inventory_loaded = True

    def _load_live_inventory(self) -> list[InstalledApp]:
        """Return a copy of the installed-app list (loading it if needed)."""
        self._ensure_inventory()
        assert self._installed is not None
        return list(self._installed)

    # -- public API -------------------------------------------------------

    def scan_app(self, app: InstalledApp) -> list[LeftoverFinding]:
        """Full leftover sweep for one uninstalled application.

        Sweeps run in sequence; setting ``cancel_event`` stops the pipeline
        between sweeps and returns whatever was found so far.
        """
        self._ensure_inventory()
        tokens = tuple(build_tokens(app.name, app.publisher))
        if not tokens:
            return []

        findings: dict[str, LeftoverFinding] = {}
        if not self._cancelled():
            self._sweep_filesystem(app, tokens, findings)
        if not self._cancelled():
            self._sweep_registry(app, tokens, findings)
        if not self._cancelled():
            self._sweep_shortcuts(app, findings)
        if not self._cancelled():
            self._sweep_com(app, findings)
        if not self._cancelled():
            self._sweep_inno_log(app, findings)
        if not self._cancelled():
            self._sweep_services(app, findings)
        if not self._cancelled():
            self._sweep_tasks(app, findings)
        if not self._cancelled():
            self._cross_check(app, findings)
            self._disambiguate_similar(app, findings)
        return [f for f in findings.values()
                if f.level != BAD and self._allowed(f)]

    def scan_orphans(self) -> list[LeftoverFinding]:
        """Find Program Files orphan folders (no live app claims them)."""
        self._ensure_inventory()
        findings: list[LeftoverFinding] = []
        for root in self._program_dir_roots():
            if self._cancelled():
                break
            try:
                entries = list(os.scandir(root))
            except OSError:
                continue
            for entry in entries:
                if not entry.is_dir(follow_symlinks=False):
                    continue
                if entry.name.lower() in DIRECTORY_NAME_BLACKLIST:
                    continue
                path = entry.path
                if self.policy.is_prohibited(path) or _has_system_attribute(path):
                    continue
                if self._claimed_by_live_app(path, entry.name.lower()):
                    continue
                f = LeftoverFinding(kind="folder", path=path,
                                    app_name=self._folder_identity(entry.name))
                self._score_orphan_folder(path, f)
                if f.level in (GOOD, VERY_GOOD) and self._allowed(f):
                    findings.append(f)
        return findings

    # -- similar-name disambiguation ------------------------------------------

    def _disambiguate_similar(self, app: InstalledApp,
                              findings: dict[str, LeftoverFinding]) -> None:
        """Penalise weaker name matches when several folders compete.

        BCU's ``TestForSimilarNames`` guard: if multiple leftover folders
        match the product's tokens, only the one whose name is closest to the
        display name keeps its full confidence - e.g. for "AppX", a folder
        "AppX" must outrank "AppX Extended", which likely belongs to another
        product. Applied only when there IS a clear winner (distance strictly
        smaller than a competitor's).
        """
        folder_findings = [f for f in findings.values() if f.kind == "folder"]
        if len(folder_findings) < 2:
            return
        target = re.sub(r"[^a-z0-9]", "", app.name.lower())
        if len(target) <= 4:
            return
        distances = []
        for f in folder_findings:
            base = re.sub(r"[^a-z0-9]", "",
                          os.path.basename(f.path).lower())
            distances.append((edit_distance(target, base), f))
        best_distance = min(d for d, _f in distances)
        for d, f in distances:
            if d > best_distance:
                _add(f, _SIMILAR_APP_CLAIMS,
                     "weaker name match than a closer leftover folder")

    # -- filesystem sweep -------------------------------------------------

    def _sweep_roots(self) -> list[str]:
        """Sweep roots: Program Files (both), ProgramData, AppData variants.

        Includes LocalLow, VirtualStore and the per-user Programs folders;
        duplicates and non-existent roots are filtered out.
        """
        roots = []
        for env in ("PROGRAMFILES", "ProgramFiles(x86)", "ProgramData",
                    "APPDATA", "LOCALAPPDATA"):
            v = os.environ.get(env)
            if v:
                roots.append(v)
        local = os.environ.get("LOCALAPPDATA")
        if local:
            roots.append(os.path.join(local, "LocalLow"))
            roots.append(os.path.join(local, "VirtualStore"))
            roots.append(os.path.join(local, "Programs"))
        roaming = os.environ.get("APPDATA")
        if roaming:
            roots.append(os.path.join(roaming, "Programs"))
        out, seen = [], set()
        for r in roots:
            n = os.path.normcase(os.path.abspath(r))
            if n not in seen and os.path.isdir(r):
                seen.add(n)
                out.append(r)
        return out

    def _program_dir_roots(self) -> list[str]:
        """Program-directories only (Program Files x2, LocalAppData\\Programs)."""
        roots = []
        for env in ("PROGRAMFILES", "ProgramFiles(x86)"):
            v = os.environ.get(env)
            if v:
                roots.append(v)
        local = os.environ.get("LOCALAPPDATA")
        if local:
            roots.append(os.path.join(local, "Programs"))
        return [r for r in roots if os.path.isdir(r)]

    def _sweep_filesystem(self, app: InstalledApp, tokens: tuple[str, ...],
                          findings: dict[str, LeftoverFinding]) -> None:
        """Walk every sweep root (max 2 levels) matching folder names to tokens."""
        for root in self._sweep_roots():
            self._walk_fs_level(app, tokens, root, depth=0, findings=findings)

    def _walk_fs_level(self, app: InstalledApp, tokens: tuple[str, ...],
                       directory: str, depth: int,
                       findings: dict[str, LeftoverFinding]) -> None:
        """Depth-limited directory walk collecting token-matching folders.

        Skips blacklisted names, prohibited paths, reparse points and
        system-attributed folders; matches folders by cleaned-name
        containment or product-name distance, scores content, and descends
        regardless of match (vendor\\App\\Cache nesting), but never past
        _MAX_FS_DEPTH. Loose files at the root level are ignored.
        """
        if depth > _MAX_FS_DEPTH:
            return
        try:
            entries = list(os.scandir(directory))
        except OSError:
            return
        for entry in entries:
            name_lower = entry.name.lower()
            if name_lower in DIRECTORY_NAME_BLACKLIST:
                continue
            path = entry.path
            if self.policy.is_prohibited(path):
                continue
            if entry.is_dir(follow_symlinks=False):
                if _is_reparse_point(path) or _has_system_attribute(path):
                    continue
                cleaned = re.sub(r"[^a-z0-9]", "", name_lower)
                matched = any(
                    t in cleaned or match_string_to_product(name_lower, t) >= 0
                    for t in tokens)
                if matched:
                    f = findings.get(path)
                    if f is None:
                        f = LeftoverFinding(kind="folder", path=path,
                                            app_name=app.name)
                        findings[path] = f
                    _add(f, max(0, 2 - 2 * depth),
                         f"name token match at depth {depth}")
                    self._score_folder_content(path, f, app)
                # Descend regardless of match: caches often nest one deeper
                # inside a matched vendor folder (e.g. Vendor\AppName\Cache).
                if not _is_reparse_point(path):
                    self._walk_fs_level(app, tokens, path, depth + 1, findings)
            elif depth == 0:
                continue  # loose files directly in a root are never candidates

    def _score_folder_content(self, path: str, f: LeftoverFinding,
                              app: InstalledApp) -> None:
        """Score a matched folder by walking its contents (read-only).

        Counts files and total size (reparse points are not descended),
        awards points for empty/leaf/publisher-parent folders, and penalizes
        executables present, >100 files, and folders named after the publisher
        (shared vendor-folder risk).
        """
        file_count = 0
        has_executable = False
        empty = True
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            if _is_reparse_point(dirpath):
                dirnames[:] = []
                continue
            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                empty = False
                file_count += 1
                try:
                    total += os.stat(fp, follow_symlinks=False).st_size
                except OSError:
                    pass
                if fn.lower().endswith((".exe", ".dll", ".sys")):
                    has_executable = True
        f.size_bytes = total
        if empty:
            _add(f, _EMPTY_FOLDER, "folder is completely empty")
        elif not has_executable:
            _add(f, 0, "only data/config files present")
        else:
            _add(f, _EXECUTABLES_PRESENT, "executables present (shared-install risk)")
        if file_count > 100:
            _add(f, _MANY_FILES, "more than 100 files (actively used?)")
        if not any(os.path.isdir(os.path.join(path, d)) for d in os.listdir(path)):
            _add(f, _LEAF_FOLDER, "no subdirectories")
        parent = os.path.basename(os.path.dirname(path)).lower()
        pub_clean = re.sub(r"[^a-z0-9]", "", app.publisher.lower())
        if pub_clean and len(pub_clean) >= 4 and \
                re.sub(r"[^a-z0-9]", "", parent) == pub_clean:
            _add(f, _COMPANY_MATCH, "parent folder equals publisher name")
        name_clean = re.sub(r"[^a-z0-9]", "", os.path.basename(path).lower())
        pub_only = re.sub(r"[^a-z0-9]", "", app.publisher.lower())
        if pub_only and name_clean == pub_only:
            _add(f, _NAME_EQUALS_COMPANY, "folder name equals publisher (shared vendor folder)")

    def _score_orphan_folder(self, path: str, f: LeftoverFinding) -> None:
        """Score an orphan folder: emptiness, executables, file count, name."""
        file_count = 0
        has_executable = False
        empty = True
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            if _is_reparse_point(dirpath):
                dirnames[:] = []
                continue
            for fn in filenames:
                empty = False
                file_count += 1
                try:
                    total += os.stat(os.path.join(dirpath, fn),
                                     follow_symlinks=False).st_size
                except OSError:
                    pass
                if fn.lower().endswith((".exe", ".dll")):
                    has_executable = True
        f.size_bytes = total
        if empty:
            _add(f, _EMPTY_FOLDER, "orphan folder is completely empty")
        elif not has_executable:
            _add(f, 0, "non-executable files present")
        else:
            _add(f, _EXECUTABLES_PRESENT, "executables present")
        if file_count > 100:
            _add(f, _MANY_FILES, "more than 100 files")
        base = os.path.basename(path).lower()
        if base in QUESTIONABLE_NAMES:
            _add(f, _QUESTIONABLE_NAME, "generic directory name")

    def _claimed_by_live_app(self, path: str, name_lower: str) -> bool:
        """True when a currently-installed app claims this name/location."""
        norm = os.path.normcase(os.path.abspath(path))
        for loc in self._live_locations:
            if loc and (norm == loc or norm.startswith(loc + os.sep)):
                return True
        for live in self._load_live_inventory():
            live_clean = re.sub(r"[^a-z0-9]", "", live.name.lower())
            if live_clean and live_clean == re.sub(r"[^a-z0-9]", "", name_lower):
                return True
        return False

    def _folder_identity(self, name: str) -> str:
        """Strip trailing version numbers/decorations from a folder name."""
        return re.sub(r"\d+(\.\d+)+.*$", "", name).strip("_-. ") or name

    # -- registry sweep ----------------------------------------------------

    _REG_ROOTS = [
        ("HKLM", "SOFTWARE"),
        ("HKLM", r"SOFTWARE\Wow6432Node"),
        ("HKCU", "SOFTWARE"),
        ("HKLM", r"SOFTWARE\Classes\VirtualStore\MACHINE\SOFTWARE"),
        ("HKCU", r"SOFTWARE\Classes\VirtualStore\MACHINE\SOFTWARE"),
    ]

    def _sweep_registry(self, app: InstalledApp, tokens: tuple[str, ...],
                        findings: dict[str, LeftoverFinding]) -> None:
        """Walk HKLM/HKCU SOFTWARE branches (read-only) matching keys to tokens.

        Covers SOFTWARE, Wow6432Node and VirtualStore MACHINE\\SOFTWARE in
        both hives, blacklisting system subtrees and stopping at
        _MAX_REG_DEPTH levels.
        """
        if not HAS_WINREG:
            return
        hive_map = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}
        for hive_name, sub in self._REG_ROOTS:
            hive = hive_map[hive_name]
            full_root = f"{hive_name}\\{sub}"
            try:
                key = winreg.OpenKey(hive, sub, 0,
                                     winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            except OSError:
                continue
            try:
                self._walk_reg_level(app, tokens, hive, hive_name, key,
                                     full_root, depth=0, findings=findings)
            finally:
                winreg.CloseKey(key)

    def _walk_reg_level(self, app: InstalledApp, tokens: tuple[str, ...],
                        hive, hive_name: str, key, display_path: str,
                        depth: int, findings: dict[str, LeftoverFinding]) -> None:
        """Recursive registry walk: matches subkey names or explicit pointers.

        Skips blacklisted subkeys; scores token matches by depth and adds a
        strong bonus when a value in the key points into the app's install
        location; recurses up to _MAX_REG_DEPTH levels (read-only access).
        """
        if depth > _MAX_REG_DEPTH:
            return
        try:
            count = winreg.QueryInfoKey(key)[0]
        except OSError:
            return
        for i in range(count):
            try:
                sub_name = winreg.EnumKey(key, i)
            except OSError:
                continue
            if sub_name.lower() in _REGISTRY_WALK_BLACKLIST:
                continue
            child_display = f"{display_path}\\{sub_name}"
            try:
                child = winreg.OpenKey(key, sub_name, 0, winreg.KEY_READ)
            except OSError:
                continue
            try:
                cleaned = re.sub(r"[^a-z0-9]", "", sub_name.lower())
                matched = any(t in cleaned for t in tokens)
                explicit = self._explicit_pointer(child, app)
                if matched or explicit:
                    f = findings.get(child_display)
                    if f is None:
                        f = LeftoverFinding(kind="registry", path=child_display,
                                            app_name=app.name)
                        findings[child_display] = f
                    _add(f, max(0, 2 - 2 * depth),
                         f"key name match at depth {depth}")
                    if explicit:
                        _add(f, _EXPLICIT_CONNECTION,
                             "registry value points into the app's install location")
                if depth + 1 <= _MAX_REG_DEPTH:
                    self._walk_reg_level(app, tokens, hive, hive_name, child,
                                         child_display, depth + 1, findings)
            finally:
                winreg.CloseKey(child)

    def _explicit_pointer(self, key, app: InstalledApp) -> bool:
        """True when a value under *key* references the app's install dir."""
        if not app.install_location:
            return False
        target = os.path.normcase(app.install_location)
        for i in range(1024):
            try:
                vname, vval, _vtype = winreg.EnumValue(key, i)
            except OSError:
                break
            if not isinstance(vval, str):
                continue
            if vname.lower() in (_INSTALL_DIR_VALUE_NAMES
                                 | _EXE_PATH_VALUE_NAMES
                                 | _AMBIGUOUS_PATH_VALUE_NAMES):
                cleaned = _clean_registry_path(vval)
                if cleaned and os.path.normcase(cleaned).startswith(target):
                    return True
        return False

    # -- residual uninstall keys -------------------------------------------

    def find_residual_uninstall_keys(self, app: InstalledApp) -> list[str]:
        """Uninstall keys still present after the app was removed."""
        if not HAS_WINREG:
            return []
        residuals = []
        for hive, hive_name, branch in _UNINSTALL_BRANCHES:
            try:
                root = winreg.OpenKey(hive, branch, 0,
                                      winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            except OSError:
                continue
            try:
                count = winreg.QueryInfoKey(root)[0]
                for i in range(count):
                    try:
                        sub = winreg.EnumKey(root, i)
                    except OSError:
                        continue
                    entry = _read_uninstall_entry(hive, hive_name, branch, sub)
                    if entry is None:
                        continue
                    if self._same_product(entry, app):
                        residuals.append(entry.uninstall_key)
            finally:
                winreg.CloseKey(root)
        return residuals

    @staticmethod
    def _same_product(a: InstalledApp, b: InstalledApp) -> bool:
        """True when two uninstall entries denote the same product.

        Matches on identical name, identical install location, or a
        near-perfect name distance.
        """
        if a.name.lower() == b.name.lower():
            return True
        if b.install_location and a.install_location:
            na = os.path.normcase(a.install_location)
            nb = os.path.normcase(b.install_location)
            if na == nb:
                return True
        return match_string_to_product(a.name, b.name) in (0, 1)

    # -- shortcuts ------------------------------------------------------------

    def _start_menu_dirs(self) -> list[str]:
        """Existing user and common Start Menu directories, if present."""
        dirs = []
        appdata = os.environ.get("APPDATA")
        programdata = os.environ.get("ProgramData")
        if appdata:
            dirs.append(os.path.join(appdata, r"Microsoft\Windows\Start Menu"))
        if programdata:
            dirs.append(os.path.join(programdata, r"Microsoft\Windows\Start Menu"))
        return [d for d in dirs if os.path.isdir(d)]

    def _sweep_shortcuts(self, app: InstalledApp,
                         findings: dict[str, LeftoverFinding]) -> None:
        """Flag .lnk files whose target lives in the dead install location."""
        if not app.install_location:
            return
        target_norm = os.path.normcase(app.install_location)
        try:
            import win32com.client  # pywin32 ships as a Windows dependency
        except ImportError:
            return
        shell = None
        for start_dir in self._start_menu_dirs():
            for dirpath, _dirnames, filenames in os.walk(start_dir):
                for fn in filenames:
                    if not fn.lower().endswith(".lnk"):
                        continue
                    lnk = os.path.join(dirpath, fn)
                    try:
                        if shell is None:
                            shell = win32com.client.Dispatch("WScript.Shell")
                        sc = shell.CreateShortCut(lnk)
                        resolved = os.path.normcase(str(sc.Targetpath))
                    except Exception:  # noqa: BLE001 - COM can fail per-file
                        continue
                    if resolved and resolved.startswith(target_norm):
                        f = LeftoverFinding(kind="shortcut", path=lnk,
                                            app_name=app.name)
                        _add(f, _EXPLICIT_CONNECTION,
                             "shortcut resolves into the uninstalled location")
                        findings[lnk] = f

    # -- COM registrations (CLSID / TypeLib) ---------------------------------

    #: GUID keys containing this fragment are almost always OS built-ins.
    _COM_OS_GUID_FRAGMENT = "-0000-"
    _MAX_COM_KEYS = 5000          # hard cap so a huge Classes hive can't stall

    def _com_branches(self) -> list[tuple[str, str]]:
        """Registry branches searched for orphaned COM registrations."""
        return [
            ("HKLM", r"SOFTWARE\Classes\CLSID"),
            ("HKCU", r"SOFTWARE\Classes\CLSID"),
            ("HKLM", r"SOFTWARE\Classes\WOW6432Node\CLSID"),
            ("HKLM", r"SOFTWARE\Classes\TypeLib"),
            ("HKCU", r"SOFTWARE\Classes\TypeLib"),
        ]

    def _sweep_com(self, app: InstalledApp,
                   findings: dict[str, LeftoverFinding]) -> None:
        """Flag CLSID/TypeLib registrations whose server binary is gone.

        BCU's guard rails apply: GUIDs containing ``-0000-`` are treated as
        OS classes and skipped, and a registration only counts when its
        InprocServer32/LocalServer32 (or TypeLib win32 path) resolves into
        the app's dead install location.
        """
        if not HAS_WINREG or not app.install_location:
            return
        target = os.path.normcase(app.install_location)
        hive_map = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}
        for hive_name, branch in self._com_branches():
            hive = hive_map[hive_name]
            try:
                root = winreg.OpenKey(hive, branch, 0,
                                      winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            except OSError:
                continue
            try:
                count = min(winreg.QueryInfoKey(root)[0], self._MAX_COM_KEYS)
                for i in range(count):
                    try:
                        guid = winreg.EnumKey(root, i)
                    except OSError:
                        continue
                    if self._COM_OS_GUID_FRAGMENT in guid.lower():
                        continue
                    display = f"{hive_name}\\{branch}\\{guid}"
                    try:
                        key = winreg.OpenKey(root, guid, 0, winreg.KEY_READ)
                    except OSError:
                        continue
                    try:
                        server_path = self._com_server_path(key, branch)
                    finally:
                        winreg.CloseKey(key)
                    if not server_path:
                        continue
                    resolved = os.path.normcase(
                        _clean_registry_path(server_path))
                    if resolved.startswith(target):
                        f = findings.get(display)
                        if f is None:
                            f = LeftoverFinding(kind="registry",
                                                path=display,
                                                app_name=app.name)
                            findings[display] = f
                        _add(f, _EXPLICIT_CONNECTION,
                             "COM registration points into the uninstalled "
                             "location")
            finally:
                winreg.CloseKey(root)

    @staticmethod
    def _com_server_path(key, branch: str) -> str:
        """Default value naming the server binary under a COM key."""
        try:
            sub_names = [winreg.EnumKey(key, i)
                         for i in range(min(winreg.QueryInfoKey(key)[0], 32))]
        except OSError:
            return ""
        candidates = ([v for v in ("InprocServer32", "LocalServer32")
                       if v in sub_names]
                      if branch.endswith("CLSID")
                      else [v for v in sub_names if v in ("win32", "0")])
        for sub in candidates:
            try:
                child = winreg.OpenKey(key, sub, 0, winreg.KEY_READ)
            except OSError:
                continue
            try:
                # TypeLib nests one more level: <ver>\0\win32.
                if branch.endswith("TypeLib") and sub == "0":
                    try:
                        deeper = winreg.OpenKey(child, "win32", 0,
                                                winreg.KEY_READ)
                        value = winreg.QueryValueEx(deeper, "")[0]
                        if isinstance(value, str) and value:
                            return value
                    except OSError:
                        pass
                value = winreg.QueryValueEx(child, "")[0]
                if isinstance(value, str) and value:
                    return value
            except OSError:
                continue
            finally:
                winreg.CloseKey(child)
        return ""

    # -- InnoSetup uninstall log ------------------------------------------------

    #: Absolute Windows paths embedded in the binary log (UTF-16LE runs).
    _INNO_PATH_RE = re.compile(r"[A-Za-z]:\\(?:[^<>:\"|?*\x00-\x1f]){2,220}")

    def _sweep_inno_log(self, app: InstalledApp,
                        findings: dict[str, LeftoverFinding]) -> None:
        """Files the installer wrote that its own uninstaller failed to remove.

        InnoSetup records every installed file in ``unins000.dat`` inside the
        install directory. The format is undocumented, but absolute paths are
        stored as plain UTF-16LE runs - extracting and existence-checking them
        yields an exact leftover manifest without depending on format details.
        """
        if not app.install_location:
            return
        dat = Path(app.install_location) / "unins000.dat"
        if not dat.is_file():
            return
        try:
            data = dat.read_bytes()
        except OSError:
            return
        text = data.decode("utf-16-le", errors="ignore")
        seen: set[str] = set()
        target = os.path.normcase(app.install_location)
        added = 0
        for match in self._INNO_PATH_RE.findall(text):
            candidate = match.rstrip("\\/.,; ")
            norm = os.path.normcase(candidate)
            if norm in seen or not norm.startswith(target):
                continue
            seen.add(norm)
            if not os.path.exists(candidate):
                continue
            kind = "folder" if os.path.isdir(candidate) else "file"
            f = findings.get(candidate)
            if f is None:
                f = LeftoverFinding(kind=kind, path=candidate,
                                    app_name=app.name)
                findings[candidate] = f
            _add(f, _EXPLICIT_CONNECTION + _PERFECT_MATCH,
                 "still exists but is listed in the InnoSetup uninstall log")
            added += 1
            if added >= 500:
                break

    # -- Windows services ---------------------------------------------------

    def _sweep_services(self, app: InstalledApp,
                        findings: dict[str, LeftoverFinding]) -> None:
        """Services whose ImagePath binary lives in the dead install dir."""
        if not HAS_WINREG or not app.install_location:
            return
        target = os.path.normcase(app.install_location)
        branch = r"SYSTEM\CurrentControlSet\Services"
        try:
            root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, branch, 0,
                                  winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        except OSError:
            return
        try:
            count = min(winreg.QueryInfoKey(root)[0], self._MAX_COM_KEYS)
            for i in range(count):
                try:
                    name = winreg.EnumKey(root, i)
                except OSError:
                    continue
                display = f"HKLM\\{branch}\\{name}"
                try:
                    key = winreg.OpenKey(root, name, 0, winreg.KEY_READ)
                except OSError:
                    continue
                try:
                    try:
                        image = winreg.QueryValueEx(key, "ImagePath")[0]
                    except OSError:
                        continue
                    if not isinstance(image, str):
                        continue
                    resolved = os.path.normcase(_clean_registry_path(image))
                    if resolved.startswith(target):
                        f = findings.get(display)
                        if f is None:
                            f = LeftoverFinding(kind="service",
                                                path=display,
                                                app_name=app.name)
                            findings[display] = f
                        _add(f, _EXPLICIT_CONNECTION,
                             f"service '{name}' runs from the uninstalled "
                             "location")
                finally:
                    winreg.CloseKey(key)
        finally:
            winreg.CloseKey(root)

    # -- Scheduled tasks ------------------------------------------------------

    def _sweep_tasks(self, app: InstalledApp,
                     findings: dict[str, LeftoverFinding]) -> None:
        """Scheduled tasks whose <Command> points into the dead install dir."""
        root = _tasks_root()
        if not app.install_location or not root.is_dir():
            return
        target = os.path.normcase(app.install_location)
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                full = Path(dirpath) / fn
                rel = full.relative_to(root)
                task_name = "\\".join(rel.parts)
                try:
                    content = full.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                m = re.search(r"<Command>([^<]+)</Command>", content)
                if not m:
                    continue
                command = _clean_registry_path(m.group(1))
                if command and os.path.normcase(command).startswith(target):
                    display = f"schtasks:{task_name}"
                    f = findings.get(display)
                    if f is None:
                        f = LeftoverFinding(kind="task", path=task_name,
                                            app_name=app.name)
                        findings[display] = f
                    _add(f, _EXPLICIT_CONNECTION,
                         "scheduled task runs from the uninstalled location")

    # -- cross-check ----------------------------------------------------------

    def _cross_check(self, app: InstalledApp,
                     findings: dict[str, LeftoverFinding]) -> None:
        """Penalize findings that a still-installed sibling app claims."""
        self._ensure_inventory()
        for f in findings.values():
            if f.kind != "folder":
                continue
            base = os.path.basename(f.path)
            base_clean = re.sub(r"[^a-z0-9]", "", base.lower())
            loc = os.path.normcase(os.path.abspath(f.path))
            for live in self._load_live_inventory():
                live_clean = re.sub(r"[^a-z0-9]", "", live.name.lower())
                if not live_clean:
                    continue
                if live_clean == base_clean:
                    if live.name.lower() == app.name.lower():
                        # The product itself is still installed - this scan
                        # is premature and every finding is suspect.
                        _add(f, _NAME_STILL_USED,
                             f"product name still installed ('{live.name}')")
                    else:
                        _add(f, _SIMILAR_APP_CLAIMS,
                             f"name also matches installed app '{live.name}'")
                if live.install_location:
                    li = os.path.normcase(live.install_location)
                    if li and (loc == li or loc.startswith(li + os.sep)):
                        _add(f, _DIRECTORY_STILL_USED,
                             f"path is inside installed app '{live.name}'")


# =====================================================================
#  Cleaner
# =====================================================================

@dataclass(slots=True)
class CleanOutcome:
    """What happened to one finding during cleanup."""

    path: str
    kind: str
    ok: bool
    disposition: str   # recycled | registry_deleted | failed | skipped
    detail: str = ""

    def to_dict(self) -> dict:
        """Return a plain-dict view of this outcome (for journals)."""
        return {"path": self.path, "kind": self.kind, "ok": self.ok,
                "disposition": self.disposition, "detail": self.detail}


class LeftoverCleaner:
    """Removes reviewed findings with Recycle Bin + registry backups + journal.

    Undo layers, in order of preference:

    0. Optional **System Restore point** created before anything is touched
       (``create_restore_point=True``). The outcome - created, throttled by
       Windows' 24-hour rule, or unavailable - is recorded honestly in the
       journal either way; a failed checkpoint never blocks the cleanup.
    1. Files/folders go to the **Recycle Bin** via ``send2trash``. If the bin
       cannot hold an item (too large / volume without one) send2trash raises
       instead of silently destroying data - that outcome is surfaced, never
       hidden.
    2. Every registry key is exported with ``reg export`` to a timestamped
       backup folder *before* deletion; double-clicking the ``.reg`` file
       restores it.
    3. An atomic JSON journal records every disposition for support/audit.
    """

    def __init__(self, backup_root: str | Path | None = None,
                 policy: SafetyPolicy | None = None):
        """Initialize with a safety policy and session-backup root
        (default ``~/CortexCleanerBackups/leftovers``)."""
        self.policy = policy or SafetyPolicy.build()
        self.backup_root = Path(backup_root) if backup_root else (
            Path.home() / "CortexCleanerBackups" / "leftovers")

    def clean(self, findings: Sequence[LeftoverFinding],
              create_restore_point: bool = False,
              exclusions: ExclusionsStore | None = None,
              cancel_event=None) -> list[CleanOutcome]:
        """Remove reviewed findings, one per disposition, with undo layers.

        Dispatches by kind: registry keys and services via ``reg`` (backed
        up first), tasks via ``schtasks`` (XML backed up), and
        folders/files/shortcuts via send2trash (Recycle Bin). Honors
        protected paths and user exclusions as defense in depth, supports
        cooperative cancellation between items, optionally creates a System
        Restore point, and always writes a JSON journal of outcomes to a
        timestamped session folder under backup_root.
        """
        outcomes: list[CleanOutcome] = []
        journal: list[dict] = []
        stamp = __import__("time").strftime("%Y%m%d_%H%M%S")
        session = self.backup_root / stamp if findings else None
        restore_note = ""
        if session is not None and create_restore_point:
            restore_note = self._restore_point()
        for f in findings:
            # Cooperative stop between items: anything already cleaned stays
            # cleaned (each item is independently journaled), the rest is left.
            if cancel_event is not None and cancel_event.is_set():
                break
            if self.policy.is_prohibited(f.path):
                outcomes.append(CleanOutcome(f.path, f.kind, False, "skipped",
                                             "protected location"))
                continue
            # Defense in depth: the scanner already filters exclusions, but a
            # stale/buggy caller must never be able to delete an excluded path.
            if exclusions is not None and exclusions.is_excluded(f.path):
                outcomes.append(CleanOutcome(f.path, f.kind, False, "skipped",
                                             "user excluded this path"))
                continue
            if f.kind == "registry":
                outcomes.append(self._clean_registry(f, session))
            elif f.kind == "service":
                outcomes.append(self._clean_service(f, session))
            elif f.kind == "task":
                outcomes.append(self._clean_task(f, session))
            elif f.kind in ("folder", "file", "shortcut"):
                outcomes.append(self._recycle(f))
            journal.append(outcomes[-1].to_dict())
        if session is not None:
            self._write_journal(session, journal, outcomes,
                                restore_note=restore_note)
        return outcomes

    @staticmethod
    def _restore_point() -> str:
        """Best-effort System Restore checkpoint; returns an honest note."""
        try:
            from cortex_unified.system_tools.restore_point import (
                RestorePointManager,
            )
            result = RestorePointManager().create(
                description="Cortex Cleaner - leftover cleanup")
            return f"{result.status.value}: {result.message}"
        except Exception as exc:  # noqa: BLE001 - never block on this
            logger.debug("restore point failed", exc_info=True)
            return f"failed: {exc}"

    # -- filesystem ---------------------------------------------------------

    def _recycle(self, f: LeftoverFinding) -> CleanOutcome:
        """Move a file/folder/shortcut to the Recycle Bin via send2trash.

        Returns a failed outcome when send2trash is not installed or the
        bin rejects the item; never falls back to permanent deletion.
        """
        try:
            from send2trash import send2trash
        except ImportError:
            return CleanOutcome(f.path, f.kind, False, "failed",
                                "send2trash unavailable")
        try:
            send2trash(f.path)
            return CleanOutcome(f.path, f.kind, True, "recycled")
        except Exception as exc:  # noqa: BLE001 - surfaced, never silent
            return CleanOutcome(f.path, f.kind, False, "failed", str(exc))

    # -- registry -----------------------------------------------------------

    def _clean_registry(self, f: LeftoverFinding,
                        session: Path | None) -> CleanOutcome:
        """Export a registry key with ``reg export``, then delete it.

        The .reg backup is written into the session folder so a double-click
        restores the key; both commands run with a 30s timeout and
        shell=False. Requires admin rights for HKLM keys.
        """
        import subprocess
        if session is None:
            return CleanOutcome(f.path, f.kind, False, "failed", "no session")
        hive_and_key = f.path  # display form "HKLM\\SOFTWARE\\..."
        parts = f.path.split("\\", 1)
        if len(parts) != 2:
            return CleanOutcome(f.path, f.kind, False, "failed",
                                "malformed registry path")
        try:
            session.mkdir(parents=True, exist_ok=True)
            backup_file = session / (re.sub(r"[^A-Za-z0-9_]", "_", f.path)[-120:]
                                     + ".reg")
            proc = subprocess.run(
                ["reg", "export", hive_and_key, str(backup_file), "/y"],
                capture_output=True, text=True, timeout=30, shell=False)
            if proc.returncode != 0:
                return CleanOutcome(f.path, f.kind, False, "failed",
                                    f"backup failed: {proc.stderr.strip()}")
            proc = subprocess.run(
                ["reg", "delete", hive_and_key, "/f"],
                capture_output=True, text=True, timeout=30, shell=False)
            if proc.returncode != 0:
                return CleanOutcome(f.path, f.kind, False, "failed",
                                    f"delete failed: {proc.stderr.strip()}")
            return CleanOutcome(f.path, f.kind, True, "registry_deleted",
                                f"backup: {backup_file}")
        except OSError as exc:
            return CleanOutcome(f.path, f.kind, False, "failed", str(exc))

    # -- services / scheduled tasks -------------------------------------------

    def _clean_service(self, f: LeftoverFinding,
                       session: Path | None) -> CleanOutcome:
        """Stop + delete a Windows service, with a .reg backup first."""
        import subprocess
        if session is None:
            return CleanOutcome(f.path, f.kind, False, "failed", "no session")
        parts = f.path.split("\\")
        name = parts[-1] if len(parts) >= 2 else ""
        if not name:
            return CleanOutcome(f.path, f.kind, False, "failed",
                                "malformed service path")
        try:
            session.mkdir(parents=True, exist_ok=True)
            backup_file = session / (re.sub(r"[^A-Za-z0-9_]", "_", f.path)[-120:]
                                     + ".reg")
            proc = subprocess.run(
                ["reg", "export", f.path, str(backup_file), "/y"],
                capture_output=True, text=True, timeout=30, shell=False)
            if proc.returncode != 0:
                return CleanOutcome(f.path, f.kind, False, "failed",
                                    f"backup failed: {proc.stderr.strip()}")
            # Stop is best-effort: a stopped/already-dead service is fine.
            subprocess.run(["sc.exe", "stop", name], capture_output=True,
                           text=True, timeout=30, shell=False)
            proc = subprocess.run(
                ["sc.exe", "delete", name],
                capture_output=True, text=True, timeout=30, shell=False)
            if proc.returncode != 0:
                return CleanOutcome(f.path, f.kind, False, "failed",
                                    f"sc delete failed: {proc.stderr.strip()}")
            return CleanOutcome(f.path, f.kind, True, "service_deleted",
                                f"backup: {backup_file}")
        except OSError as exc:
            return CleanOutcome(f.path, f.kind, False, "failed", str(exc))

    def _clean_task(self, f: LeftoverFinding,
                    session: Path | None) -> CleanOutcome:
        """Delete a scheduled task; its XML definition is backed up first."""
        import subprocess
        if session is None:
            return CleanOutcome(f.path, f.kind, False, "failed", "no session")
        task_name = f.path
        try:
            session.mkdir(parents=True, exist_ok=True)
            xml = self._tasks_root_for(task_name)
            backup_note = "no xml found"
            if xml is not None and xml.is_file():
                dest = session / (re.sub(r"[^A-Za-z0-9_]", "_", task_name)[-120:]
                                  + ".xml")
                dest.write_bytes(xml.read_bytes())
                backup_note = f"backup: {dest}"
            # End a running instance best-effort before deleting.
            subprocess.run(["schtasks", "/end", "/tn", task_name],
                           capture_output=True, text=True, timeout=30,
                           shell=False)
            proc = subprocess.run(
                ["schtasks", "/delete", "/tn", task_name, "/f"],
                capture_output=True, text=True, timeout=30, shell=False)
            if proc.returncode != 0:
                return CleanOutcome(f.path, f.kind, False, "failed",
                                    f"schtasks delete failed: "
                                    f"{proc.stderr.strip() or proc.stdout.strip()}")
            return CleanOutcome(f.path, f.kind, True, "task_deleted",
                                backup_note)
        except OSError as exc:
            return CleanOutcome(f.path, f.kind, False, "failed", str(exc))

    def _tasks_root_for(self, task_name: str) -> Path | None:
        """On-disk XML for a task: Tasks stores '<name>.xml' per task."""
        return _tasks_root().joinpath(*task_name.split("\\")).with_suffix(".xml")

    # -- journal --------------------------------------------------------------

    def _write_journal(self, session: Path, journal: list[dict],
                       outcomes: list[CleanOutcome],
                       restore_note: str = "") -> None:
        """Write the session journal.json atomically (tmp file + os.replace).

        Records the timestamp, restore-point note, per-item dispositions
        and ok/fail counts; write failures are logged, never raised.
        """
        try:
            session.mkdir(parents=True, exist_ok=True)
            payload = {
                "timestamp": stamp_now(),
                "restore_point": restore_note or "not requested",
                "items": journal,
                "ok_count": sum(1 for o in outcomes if o.ok),
                "fail_count": sum(1 for o in outcomes if not o.ok),
            }
            fd, tmp_name = tempfile.mkstemp(dir=str(session), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
            os.replace(tmp_name, str(session / "journal.json"))
        except OSError:
            logger.debug("journal write failed", exc_info=True)


def stamp_now() -> str:
    """Current local time as an ISO-like ``YYYY-MM-DDTHH:MM:SS`` string."""
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%S")


__all__ = [
    "InstalledApp", "LeftoverFinding", "LeftoverScanner", "LeftoverCleaner",
    "SafetyPolicy", "CleanOutcome", "ExclusionsStore",
    "build_tokens", "match_string_to_product", "edit_distance",
    "confidence_level", "read_installed_apps", "detect_installer_type",
    "VERY_GOOD", "GOOD", "QUESTIONABLE", "BAD",
]
