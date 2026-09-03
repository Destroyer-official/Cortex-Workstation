"""Enhanced broken link detector for Cortex Cleaner."""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import threading

from cortex_unified.core.utils import normalize_path
from cortex_unified.core.config import Config

@dataclass
class BrokenLink:
    """Base class for broken link information."""
    path: Path
    target: str
    link_type: str
    size: int
    created: datetime
    last_accessed: datetime
    is_repairable: bool = False
    confidence_score: float = 0.0
    error_message: str = ""

@dataclass
class BrokenSymlink(BrokenLink):
    """Information about a broken symlink."""
    is_absolute: bool = False
    
    def __post_init__(self):
        self.link_type = "symlink"
        """__post_init__."""
        """__post_init__."""

@dataclass
class BrokenShortcut(BrokenLink):
    """Information about a broken Windows shortcut (.lnk file)."""
    working_directory: str = ""
    arguments: str = ""
    icon_path: str = ""
    
    def __post_init__(self):
        self.link_type = "shortcut"
        """__post_init__."""
        """__post_init__."""

@dataclass
class BrokenRegistryRef(BrokenLink):
    """Information about a broken registry reference (Windows only)."""
    registry_key: str = ""
    registry_value: str = ""
    
    def __post_init__(self):
        self.link_type = "registry_ref"
        """__post_init__."""
        """__post_init__."""

@dataclass
class RepairResult:
    """Result of a repair attempt."""
    success: bool
    original_path: Path
    new_target: Optional[str] = None
    backup_created: bool = False
    backup_path: Optional[Path] = None
    error_message: str = ""


@dataclass
class RepairOutcome:
    """Per-item outcome of a :func:`repair` run."""
    path: Path
    action: str
    ok: bool
    detail: str = ""


def _is_reparse_link(path: Path) -> bool:
    """True when *path* is itself a link (symlink or Windows junction).

    Never true for real files or directories, which lets callers remove the
    link entry without ever touching the thing it points at.
    """
    try:
        if path.is_symlink():
            return True
        if sys.platform.startswith("win"):
            import stat as _stat
            st = os.lstat(path)
            return getattr(st, "st_reparse_tag", 0) == _stat.IO_REPARSE_TAG_MOUNT_POINT
    except (OSError, ValueError):
        return False
    return False


def _resolve_send2trash():
    """Return ``send2trash`` or ``None`` when the package is unavailable."""
    try:
        from send2trash import send2trash  # noqa: PLC0415 - optional dependency
        return send2trash
    except ImportError:
        return None


def repair(items, use_trash=True, dry_run=True) -> List[RepairOutcome]:
    """Safely clean up broken links found by a scan.

    Only two safe actions are ever taken:

    * broken ``.lnk`` shortcuts -> moved to the Recycle Bin (``send2trash``)
      when ``use_trash`` is set; otherwise unlinked.
    * dangling symlinks / junctions -> the LINK ONLY is removed
      (``os.unlink``, or ``os.rmdir`` on junction/dir-link paths). Real
      directories are never touched and ``shutil.rmtree`` is never used.

    Registry-reference items are never modified; they are excluded with an
    explanation because registry edits require manual review.

    Args:
        items: BrokenLink instances (or anything with ``path``/``link_type``).
        use_trash: Route shortcut removal through the Recycle Bin.
        dry_run: When True (the default) nothing is changed; each outcome
            reports the action that would be taken.

    Returns:
        One :class:`RepairOutcome` per input item.
    """
    outcomes: List[RepairOutcome] = []
    send2trash = _resolve_send2trash() if use_trash else None

    for item in items:
        path = Path(getattr(item, "path", item))
        link_type = getattr(item, "link_type", "")

        try:
            # -- Registry references: hands off, always -------------------
            if isinstance(item, BrokenRegistryRef) or link_type == "registry_ref":
                outcomes.append(RepairOutcome(
                    path=path, action="excluded", ok=False,
                    detail="registry refs require manual review"))
                continue

            # -- Broken .lnk shortcuts ------------------------------------
            if isinstance(item, BrokenShortcut) or link_type == "shortcut":
                if not path.is_file() and not path.is_symlink():
                    outcomes.append(RepairOutcome(
                        path=path, action="skipped", ok=False,
                        detail="shortcut file not found"))
                    continue
                if dry_run:
                    outcomes.append(RepairOutcome(
                        path=path, action="recycle shortcut", ok=True,
                        detail="planned: move .lnk to Recycle Bin"))
                    continue
                if use_trash:
                    if send2trash is None:
                        outcomes.append(RepairOutcome(
                            path=path, action="failed", ok=False,
                            detail="send2trash not installed; cannot recycle"))
                        continue
                    send2trash(str(path))
                    outcomes.append(RepairOutcome(
                        path=path, action="recycle shortcut", ok=True,
                        detail="moved to Recycle Bin"))
                else:
                    os.unlink(str(path))
                    outcomes.append(RepairOutcome(
                        path=path, action="delete shortcut", ok=True,
                        detail="shortcut deleted"))
                continue

            # -- Dangling symlinks / junctions -----------------------------
            if isinstance(item, BrokenSymlink) or link_type == "symlink" \
                    or link_type in ("junction", "mount_point"):
                if not _is_reparse_link(path):
                    outcomes.append(RepairOutcome(
                        path=path, action="skipped", ok=False,
                        detail="not a link; refusing to touch real file or folder"))
                    continue
                if dry_run:
                    action = "remove junction" if link_type == "junction" else "remove symlink"
                    outcomes.append(RepairOutcome(
                        path=path, action=action, ok=True,
                        detail="planned: remove link only"))
                    continue
                try:
                    os.unlink(str(path))          # file symlink / junction
                except OSError:
                    os.rmdir(str(path))           # dir symlink: removes link only
                outcomes.append(RepairOutcome(
                    path=path, action="remove symlink", ok=True,
                    detail="link removed"))
                continue

            # -- Anything else: unsupported -------------------------------
            outcomes.append(RepairOutcome(
                path=path, action="skipped", ok=False,
                detail=f"unsupported link type: {link_type or type(item).__name__}"))

        except Exception as exc:  # noqa: BLE001 - one bad item must stop the rest
            outcomes.append(RepairOutcome(
                path=path, action="failed", ok=False, detail=str(exc)))

    return outcomes

class BrokenLinkDetector:
    """Detector for broken symlinks, shortcuts, and registry references."""
    
    def __init__(self, config: Config = None):
        """Initialize broken link detector."""
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.exclude_patterns = set(self.config.exclude_patterns)
        self.exclude_dirs = set(self.config.exclude_dirs)
        self.follow_symlinks = self.config.follow_symlinks
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Results
        self.broken_links: List[BrokenLink] = []
        self.scan_count = 0
        self.error_count = 0
        
        # Platform detection
        self.is_windows = sys.platform.startswith("win")
        
        # Import Windows-specific modules if available
        self._setup_windows_modules()
    
    def _setup_windows_modules(self):
        """Set up Windows-specific modules for shortcut and registry handling."""
        self.has_win32 = False
        self.has_winreg = False
        
        if self.is_windows:
            try:
                import win32com.client
                import pythoncom
                self.win32com = win32com
                self.pythoncom = pythoncom
                self.has_win32 = True
            except ImportError:
                self.logger.warning("win32com not available - Windows shortcut support limited")
            
            try:
                import winreg
                self.winreg = winreg
                self.has_winreg = True
            except ImportError:
                self.logger.warning("winreg not available - registry reference checking disabled")
    
    def _should_exclude_path(self, path: Path) -> bool:
        """Check if a path should be excluded based on patterns."""
        if path.name in self.exclude_dirs:
            return True
        
        path_str = str(path)
        path_name = path.name
        
        for pattern in self.exclude_patterns:
            # Handle glob-like patterns
            if pattern.startswith('*.'):
                # Extension pattern like *.tmp
                extension = pattern[2:]
                if path_name.endswith('.' + extension):
                    return True
            elif pattern in path_str or pattern in path_name:
                return True
        
        return False
    
    def _get_file_stats(self, path: Path) -> Tuple[int, datetime, datetime]:
        """Get file size and timestamps."""
        try:
            stat = path.stat()
            size = stat.st_size
            created = datetime.fromtimestamp(stat.st_ctime)
            accessed = datetime.fromtimestamp(stat.st_atime)
            return size, created, accessed
        except (OSError, ValueError):
            return 0, datetime.now(), datetime.now()
    
    def scan_symlinks(self, path: str) -> List[BrokenSymlink]:
        """Scan for broken symlinks in the given path."""
        self.logger.info(f"Scanning for broken symlinks in: {path}")
        broken_symlinks = []
        scan_path = normalize_path(path)
        
        if not scan_path.exists():
            self.logger.error(f"Scan path does not exist: {scan_path}")
            return broken_symlinks
        
        try:
            for root, dirs, files in os.walk(scan_path, followlinks=False):
                if self._cancelled():
                    self.logger.info("Symlink scan cancelled by user")
                    break
                root_path = Path(root)
                
                if self._should_exclude_path(root_path):
                    dirs.clear()  # Don't recurse into excluded directories
                    continue

                self.scan_count += len(files) + len(dirs)
                self._emit(f"Scanning symlinks: {self.scan_count:,} items \u2014 "
                           f"{len(broken_symlinks)} broken so far\u2026")

                # Check all entries (files and directories) for symlinks
                all_entries = files + dirs
                for entry_name in all_entries:
                    entry_path = root_path / entry_name
                    
                    try:
                        if entry_path.is_symlink():
                            try:
                                target = os.readlink(entry_path)
                                is_absolute = os.path.isabs(target)
                                
                                # Resolve the target path
                                if is_absolute:
                                    resolved_target = Path(target)
                                else:
                                    resolved_target = (entry_path.parent / target).resolve()
                                
                                if not resolved_target.exists():
                                    size, created, accessed = self._get_file_stats(entry_path)
                                    
                                    broken_link = BrokenSymlink(
                                        path=entry_path,
                                        target=target,
                                        link_type="symlink",
                                        size=size,
                                        created=created,
                                        last_accessed=accessed,
                                        is_absolute=is_absolute,
                                        error_message=f"Target does not exist: {resolved_target}"
                                    )
                                    
                                    broken_link.is_repairable = self._assess_symlink_repairability(broken_link)
                                    broken_link.confidence_score = self._calculate_confidence_score(broken_link)
                                    
                                    broken_symlinks.append(broken_link)
                                    self.logger.debug(f"Found broken symlink: {entry_path} -> {target}")
                            
                            except (OSError, ValueError) as e:
                                self.error_count += 1
                                self.logger.warning(f"Error reading symlink {entry_path}: {e}")
                    
                    except (OSError, PermissionError) as e:
                        self.error_count += 1
                        self.logger.debug(f"Error accessing {entry_path}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error scanning for symlinks: {e}")
            self.error_count += 1
        
        self.logger.info(f"Found {len(broken_symlinks)} broken symlinks")
        return broken_symlinks
    
    def scan_windows_shortcuts(self, path: str) -> List[BrokenShortcut]:
        """Scan for broken Windows shortcuts (.lnk files)."""
        if not self.is_windows:
            self.logger.debug("Not on Windows - skipping shortcut scan")
            return []
        
        self.logger.info(f"Scanning for broken Windows shortcuts in: {path}")
        broken_shortcuts = []
        scan_path = normalize_path(path)
        
        if not scan_path.exists():
            self.logger.error(f"Scan path does not exist: {scan_path}")
            return broken_shortcuts
        
        try:
            checked = 0
            for lnk_file in scan_path.rglob("*.lnk"):
                if self._cancelled():
                    self.logger.info("Shortcut scan cancelled by user")
                    break
                if self._should_exclude_path(lnk_file):
                    continue
                
                self.scan_count += 1
                checked += 1
                if checked % 25 == 0:
                    self._emit(f"Scanning shortcuts: {checked} .lnk files \u2014 "
                               f"{len(broken_shortcuts)} broken so far\u2026")
                
                try:
                    shortcut_info = self._analyze_shortcut(lnk_file)
                    if shortcut_info and not shortcut_info.get('target_exists', True):
                        size, created, accessed = self._get_file_stats(lnk_file)
                        
                        broken_shortcut = BrokenShortcut(
                            path=lnk_file,
                            target=shortcut_info.get('target', ''),
                            link_type="shortcut",
                            size=size,
                            created=created,
                            last_accessed=accessed,
                            working_directory=shortcut_info.get('working_directory', ''),
                            arguments=shortcut_info.get('arguments', ''),
                            icon_path=shortcut_info.get('icon_path', ''),
                            error_message=f"Target does not exist: {shortcut_info.get('target', '')}"
                        )
                        
                        broken_shortcut.is_repairable = self._assess_shortcut_repairability(broken_shortcut)
                        broken_shortcut.confidence_score = self._calculate_confidence_score(broken_shortcut)
                        
                        broken_shortcuts.append(broken_shortcut)
                        self.logger.debug(f"Found broken shortcut: {lnk_file}")
                
                except Exception as e:
                    self.error_count += 1
                    self.logger.warning(f"Error analyzing shortcut {lnk_file}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error scanning for shortcuts: {e}")
            self.error_count += 1
        
        self.logger.info(f"Found {len(broken_shortcuts)} broken shortcuts")
        return broken_shortcuts
    
    def _analyze_shortcut(self, lnk_path: Path) -> Optional[Dict]:
        """Analyze a Windows shortcut file to extract target information."""
        if not self.has_win32:
            # Fallback: basic parsing without COM
            return self._analyze_shortcut_basic(lnk_path)
        
        try:
            # COM must be initialized on whichever thread creates the
            # WScript.Shell object; MTA/STA state is per-thread.
            self.pythoncom.CoInitialize()
            
            shell = self.win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(lnk_path))
            
            target = shortcut.Targetpath
            working_dir = shortcut.WorkingDirectory
            arguments = shortcut.Arguments
            icon_path = shortcut.IconLocation
            
            target_exists = False
            if target:
                target_path = Path(target)
                target_exists = target_path.exists()
            
            return {
                'target': target,
                'working_directory': working_dir,
                'arguments': arguments,
                'icon_path': icon_path,
                'target_exists': target_exists
            }
        
        except Exception as e:
            self.logger.debug(f"Error analyzing shortcut with COM: {e}")
            return self._analyze_shortcut_basic(lnk_path)
        
        finally:
            try:
                self.pythoncom.CoUninitialize()
            except Exception:
                pass
    
    def _analyze_shortcut_basic(self, lnk_path: Path) -> Optional[Dict]:
        """Basic shortcut analysis without COM (limited functionality)."""
        try:
            # In a real scenario, you'd need to parse the .lnk file format
            # For now, we'll just check if the file exists and assume it's broken
            # if it's very small (likely corrupted) or very old
            
            stat = lnk_path.stat()
            if stat.st_size < 100:  # Very small .lnk files are likely broken
                return {
                    'target': 'Unknown (basic parser)',
                    'working_directory': '',
                    'arguments': '',
                    'icon_path': '',
                    'target_exists': False
                }
            
            # For basic parsing, we can't determine the actual target
            # so we'll assume it exists unless the file is suspicious
            return {
                'target': 'Unknown (basic parser)',
                'working_directory': '',
                'arguments': '',
                'icon_path': '',
                'target_exists': True  # Conservative assumption
            }
        
        except Exception as e:
            self.logger.debug(f"Error in basic shortcut analysis: {e}")
            return None
    
    def scan_registry_references(self) -> List[BrokenRegistryRef]:
        """Scan for broken registry references (Windows only)."""
        if not self.is_windows or not self.has_winreg:
            self.logger.debug("Registry scanning not available")
            return []
        
        self.logger.info("Scanning for broken registry references")
        broken_refs = []
        
        # Common registry locations that contain file paths
        registry_locations = [
            (self.winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (self.winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (self.winreg.HKEY_CURRENT_USER, r"Software\Classes\Applications"),
            (self.winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\Applications"),
        ]
        
        for hkey, subkey_path in registry_locations:
            try:
                broken_refs.extend(self._scan_registry_key(hkey, subkey_path))
            except Exception as e:
                self.logger.debug(f"Error scanning registry key {subkey_path}: {e}")
        
        self.logger.info(f"Found {len(broken_refs)} broken registry references")
        return broken_refs
    
    def _scan_registry_key(self, hkey, subkey_path: str) -> List[BrokenRegistryRef]:
        """Scan a specific registry key for broken file references."""
        broken_refs = []
        
        try:
            with self.winreg.OpenKey(hkey, subkey_path) as key:
                i = 0
                while True:
                    try:
                        value_name, value_data, value_type = self.winreg.EnumValue(key, i)
                        i += 1
                        
                        if isinstance(value_data, str) and ('\\' in value_data or '/' in value_data):
                            # Extract potential file paths from the value
                            potential_paths = self._extract_paths_from_string(value_data)
                            
                            for path_str in potential_paths:
                                path_obj = Path(path_str)
                                if not path_obj.exists():
                                    broken_ref = BrokenRegistryRef(
                                        path=Path(f"Registry:{subkey_path}\\{value_name}"),
                                        target=path_str,
                                        link_type="registry_ref",
                                        size=0,
                                        created=datetime.now(),
                                        last_accessed=datetime.now(),
                                        registry_key=subkey_path,
                                        registry_value=value_name,
                                        error_message=f"Referenced file does not exist: {path_str}"
                                    )
                                    
                                    broken_ref.is_repairable = self._assess_registry_repairability(broken_ref)
                                    broken_ref.confidence_score = self._calculate_confidence_score(broken_ref)
                                    
                                    broken_refs.append(broken_ref)
                    
                    except OSError:
                        # No more values
                        break
        
        except Exception as e:
            self.logger.debug(f"Error accessing registry key {subkey_path}: {e}")
        
        return broken_refs
    
    def _extract_paths_from_string(self, text: str) -> List[str]:
        """Extract potential file paths from a string."""
        import re
        
        paths = []
        
        # First try to find quoted paths (handles spaces)
        quoted_pattern = r'"([A-Za-z]:\\[^"]*)"'
        quoted_matches = re.findall(quoted_pattern, text)
        for match in quoted_matches:
            if len(match) > 3 and '\\' in match:
                paths.append(match)
        
        # For unquoted paths, we need to be more careful with spaces
        # Split by common delimiters and check each part
        parts = re.split(r'[\s,;]+', text)
        for part in parts:
            # Look for Windows path pattern
            if re.match(r'^[A-Za-z]:\\', part):
                # Clean up the path
                path = part.strip('"').strip("'").strip()
                path = re.sub(r'[^\w\\\.:/-]+$', '', path)
                if len(path) > 3 and '\\' in path and path not in paths:
                    paths.append(path)
        
        # Also try to find paths that might have spaces but aren't quoted
        # This is a more aggressive approach for registry values
        space_pattern = r'[A-Za-z]:\\[^"]*?\.(?:exe|dll|bat|cmd|com|scr|msi|lnk)'
        space_matches = re.findall(space_pattern, text, re.IGNORECASE)
        for match in space_matches:
            if match not in paths and len(match) > 3:
                paths.append(match)
        
        return paths
    
    def _assess_symlink_repairability(self, broken_link: BrokenSymlink) -> bool:
        """True when a plausible new target for the symlink exists.

        A moved-but-present target means repair is just a retarget; with no
        candidates there is nothing sane to point the link at.
        """
        potential_targets = self.find_moved_targets(broken_link.target)
        return len(potential_targets) > 0
    
    def _assess_shortcut_repairability(self, broken_shortcut: BrokenShortcut) -> bool:
        """True when a plausible new target for the shortcut exists."""
        potential_targets = self.find_moved_targets(broken_shortcut.target)
        return len(potential_targets) > 0
    
    def _assess_registry_repairability(self, broken_ref: BrokenRegistryRef) -> bool:
        """Assess if a broken registry reference can potentially be repaired."""
        # Registry references are generally not repairable automatically
        # as they require careful registry editing
        return False
    
    def _calculate_confidence_score(self, broken_link: BrokenLink) -> float:
        """Calculate confidence score for a broken link detection."""
        score = 0.5  # Base confidence
        
        # Higher confidence for recently accessed files
        days_since_access = (datetime.now() - broken_link.last_accessed).days
        if days_since_access < 30:
            score += 0.2
        elif days_since_access > 365:
            score -= 0.1
        
        # Higher confidence for files in common locations
        path_str = str(broken_link.path).lower()
        if any(common in path_str for common in ['desktop', 'documents', 'downloads']):
            score += 0.1
        
        # Lower confidence for system locations
        if any(system in path_str for system in ['system32', 'windows', 'program files']):
            score -= 0.2
        
        # Adjust based on repairability
        if broken_link.is_repairable:
            score += 0.2
        
        return max(0.0, min(1.0, score)) 
   
    def find_moved_targets(self, original_target: str) -> List[str]:
        """Find potential new locations for a moved target using heuristics."""
        self.logger.debug(f"Searching for moved target: {original_target}")
        potential_targets = []
        
        if not original_target:
            return potential_targets
        
        original_path = Path(original_target)
        filename = original_path.name
        
        if not filename:
            return potential_targets
        
        # Search locations in order of likelihood
        search_locations = self._get_search_locations(original_path)
        
        for search_dir in search_locations:
            try:
                if not search_dir.exists():
                    continue
                
                # Look for exact filename matches
                for match in search_dir.rglob(filename):
                    if match.is_file() and match != original_path:
                        potential_targets.append(str(match))
                        self.logger.debug(f"Found potential target: {match}")
                
                # Limit search results to avoid performance issues
                if len(potential_targets) >= 10:
                    break
            
            except (PermissionError, OSError) as e:
                self.logger.debug(f"Error searching in {search_dir}: {e}")
        
        return potential_targets
    
    def _get_search_locations(self, original_path: Path) -> List[Path]:
        """Get prioritized list of locations to search for moved files."""
        search_locations = []
        
        # 1. Parent directory and siblings
        if original_path.parent.exists():
            search_locations.append(original_path.parent)
        
        # 2. Common user directories
        home = Path.home()
        user_dirs = [
            home / "Desktop",
            home / "Documents", 
            home / "Downloads",
            home / "Pictures",
            home / "Videos",
            home / "Music"
        ]
        
        for user_dir in user_dirs:
            if user_dir.exists():
                search_locations.append(user_dir)
        
        # 3. Program Files & AppData directories (Windows)
        if self.is_windows:
            program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
            program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
            local_app_data = os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
            app_data = os.environ.get("APPDATA", str(home / "AppData" / "Roaming"))
            program_dirs = [
                Path(program_files),
                Path(program_files_x86),
                Path(local_app_data),
                Path(app_data)
            ]
            
            for prog_dir in program_dirs:
                if prog_dir.exists():
                    search_locations.append(prog_dir)
        
        # 4. Common application directories (Unix-like)
        else:
            unix_dirs = [
                Path("/usr/bin"),
                Path("/usr/local/bin"),
                Path("/opt"),
                Path("/Applications") if sys.platform == "darwin" else None
            ]
            
            for unix_dir in unix_dirs:
                if unix_dir and unix_dir.exists():
                    search_locations.append(unix_dir)
        
        return search_locations
    
    def attempt_repair(self, broken_link: BrokenLink) -> RepairResult:
        self.logger.info(f"Attempting to repair broken link: {broken_link.path}")
        
        potential_targets = self.find_moved_targets(broken_link.target)
        
        if not potential_targets:
            return RepairResult(
                success=False,
                original_path=broken_link.path,
                error_message="No potential targets found"
            )
        
        # Use the first (most likely) target
        new_target = potential_targets[0]
        
        backup_result = self._create_backup(broken_link.path)
        
        try:
            if isinstance(broken_link, BrokenSymlink):
                return self._repair_symlink(broken_link, new_target, backup_result)
            elif isinstance(broken_link, BrokenShortcut):
                return self._repair_shortcut(broken_link, new_target, backup_result)
            elif isinstance(broken_link, BrokenRegistryRef):
                return self._repair_registry_ref(broken_link, new_target, backup_result)
            else:
                return RepairResult(
                    success=False,
                    original_path=broken_link.path,
                    error_message="Unknown link type"
                )
        
        except Exception as e:
            self.logger.error(f"Error during repair: {e}")
            return RepairResult(
                success=False,
                original_path=broken_link.path,
                backup_created=backup_result['success'],
                backup_path=backup_result.get('backup_path'),
                error_message=str(e)
            )
        """attempt_repair."""
        """attempt_repair."""
    
    def _create_backup(self, original_path: Path) -> Dict:
        """Create a backup of the original link before repair."""
        try:
            backup_dir = original_path.parent / ".deepcleaner_backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{original_path.name}.backup_{timestamp}"
            backup_path = backup_dir / backup_name
            
            # Copy the original file/link
            import shutil
            shutil.copy2(original_path, backup_path)
            
            return {
                'success': True,
                'backup_path': backup_path
            }
        
        except Exception as e:
            self.logger.warning(f"Failed to create backup for {original_path}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _repair_symlink(self, broken_link: BrokenSymlink, new_target: str, backup_result: Dict) -> RepairResult:
        """Repair a broken symlink."""
        try:
            broken_link.path.unlink()
            
            broken_link.path.symlink_to(new_target)
            
            return RepairResult(
                success=True,
                original_path=broken_link.path,
                new_target=new_target,
                backup_created=backup_result['success'],
                backup_path=backup_result.get('backup_path')
            )
        
        except Exception as e:
            return RepairResult(
                success=False,
                original_path=broken_link.path,
                backup_created=backup_result['success'],
                backup_path=backup_result.get('backup_path'),
                error_message=f"Failed to repair symlink: {e}"
            )
    
    def _repair_shortcut(self, broken_shortcut: BrokenShortcut, new_target: str, backup_result: Dict) -> RepairResult:
        """Repair a broken Windows shortcut."""
        if not self.has_win32:
            return RepairResult(
                success=False,
                original_path=broken_shortcut.path,
                backup_created=backup_result['success'],
                backup_path=backup_result.get('backup_path'),
                error_message="Windows COM libraries not available for shortcut repair"
            )
        
        try:
            # COM must be initialized on whichever thread creates the
            # WScript.Shell object; MTA/STA state is per-thread.
            self.pythoncom.CoInitialize()
            
            # Create shell object and load shortcut
            shell = self.win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(broken_shortcut.path))
            
            shortcut.Targetpath = new_target
            
            # Preserve other properties if they exist
            if broken_shortcut.working_directory:
                shortcut.WorkingDirectory = broken_shortcut.working_directory
            if broken_shortcut.arguments:
                shortcut.Arguments = broken_shortcut.arguments
            if broken_shortcut.icon_path:
                shortcut.IconLocation = broken_shortcut.icon_path
            
            shortcut.save()
            
            return RepairResult(
                success=True,
                original_path=broken_shortcut.path,
                new_target=new_target,
                backup_created=backup_result['success'],
                backup_path=backup_result.get('backup_path')
            )
        
        except Exception as e:
            return RepairResult(
                success=False,
                original_path=broken_shortcut.path,
                backup_created=backup_result['success'],
                backup_path=backup_result.get('backup_path'),
                error_message=f"Failed to repair shortcut: {e}"
            )
        
        finally:
            try:
                self.pythoncom.CoUninitialize()
            except Exception:
                pass
    
    def _repair_registry_ref(self, broken_ref: BrokenRegistryRef, new_target: str, backup_result: Dict) -> RepairResult:
        """Repair a broken registry reference (not implemented for safety)."""
        # Registry editing is dangerous and should be done manually
        return RepairResult(
            success=False,
            original_path=broken_ref.path,
            backup_created=backup_result['success'],
            backup_path=backup_result.get('backup_path'),
            error_message="Registry reference repair not implemented for safety reasons"
        )
    
    def categorize_broken_links(self, links: List[BrokenLink]) -> Dict[str, List[BrokenLink]]:
        """Categorize broken links by type and repairability."""
        categories = {
            'symlinks': [],
            'shortcuts': [],
            'registry_refs': [],
            'repairable': [],
            'non_repairable': [],
            'high_confidence': [],
            'low_confidence': []
        }
        
        for link in links:
            # Categorize by type
            if isinstance(link, BrokenSymlink):
                categories['symlinks'].append(link)
            elif isinstance(link, BrokenShortcut):
                categories['shortcuts'].append(link)
            elif isinstance(link, BrokenRegistryRef):
                categories['registry_refs'].append(link)
            
            # Categorize by repairability
            if link.is_repairable:
                categories['repairable'].append(link)
            else:
                categories['non_repairable'].append(link)
            
            # Categorize by confidence
            if link.confidence_score >= 0.7:
                categories['high_confidence'].append(link)
            else:
                categories['low_confidence'].append(link)
        
        return categories
    
    def scan_all(self, path: str, progress=None, cancel_event=None,
                 include_registry: bool = False) -> List[BrokenLink]:
        """Scan for broken symlinks and shortcuts under the given folder.

        Args:
            path: Root directory to scan.
            progress: Optional callable(str) invoked with live status text.
            cancel_event: Optional threading.Event; if set, the scan stops early.
            include_registry: Off by default. Registry references are NOT tied
                to the chosen folder, and the path-extraction heuristic can
                mis-parse registry values that contain spaces, producing false
                positives (e.g. truncating ``D:\\Program Files\\App`` to
                ``D:\\Program``). We therefore exclude them from a folder scan
                unless explicitly requested. Startup Run-key auditing lives in
                the dedicated Startup page instead.
        """
        self.logger.info(f"Starting broken link scan in: {path}")

        self.scan_count = 0
        self.error_count = 0
        self.broken_links.clear()
        self._progress = progress
        self._cancel_event = cancel_event

        # Scan for symlinks (all platforms)
        symlinks = self.scan_symlinks(path)
        self.broken_links.extend(symlinks)

        # Scan for Windows shortcuts
        if self.is_windows and not self._cancelled():
            shortcuts = self.scan_windows_shortcuts(path)
            self.broken_links.extend(shortcuts)

            # Registry references are opt-in only (see docstring).
            if include_registry and not self._cancelled():
                registry_refs = self.scan_registry_references()
                self.broken_links.extend(registry_refs)

        self.logger.info(f"Scan complete. Found {len(self.broken_links)} broken links "
                        f"({self.scan_count} items scanned, {self.error_count} errors)")

        return self.broken_links.copy()

    def _cancelled(self) -> bool:
        ev = getattr(self, "_cancel_event", None)
        return ev is not None and ev.is_set()
        """_cancelled."""
        """_cancelled."""

    def _emit(self, text: str) -> None:
        cb = getattr(self, "_progress", None)
        if cb is not None:
            try:
                cb(text)
            except Exception:  # noqa: BLE001 - never let UI callback break the scan
                pass
        """_emit."""
        """_emit."""
    
    def get_scan_statistics(self) -> Dict[str, int]:
        """Get statistics about the last scan."""
        categories = self.categorize_broken_links(self.broken_links)
        
        return {
            'total_scanned': self.scan_count,
            'total_broken': len(self.broken_links),
            'errors': self.error_count,
            'symlinks': len(categories['symlinks']),
            'shortcuts': len(categories['shortcuts']),
            'registry_refs': len(categories['registry_refs']),
            'repairable': len(categories['repairable']),
            'non_repairable': len(categories['non_repairable']),
            'high_confidence': len(categories['high_confidence']),
            'low_confidence': len(categories['low_confidence'])
        }