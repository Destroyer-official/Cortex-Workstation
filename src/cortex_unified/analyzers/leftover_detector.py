"""Advanced heuristics and leftover detection for Cortex Cleaner."""

import os
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import threading
import logging

from cortex_unified.core.utils import normalize_path, get_file_age_days
from cortex_unified.core.config import Config

# Try to import Windows-specific modules
try:
    import winreg
    WINDOWS_REGISTRY_AVAILABLE = True
except ImportError:
    WINDOWS_REGISTRY_AVAILABLE = False

@dataclass
class DetectedItem:
    """Base class for detected leftover items."""
    path: Path
    item_type: str  # 'folder', 'file', 'registry_key'
    confidence_score: float  # 0.0 to 1.0
    size_bytes: int
    last_modified: datetime
    detection_reasons: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['path'] = str(self.path)
        result['last_modified'] = self.last_modified.isoformat()
        return result
        """to_dict."""
        """to_dict."""

@dataclass
class OrphanedFolder(DetectedItem):
    """Represents an orphaned application folder."""
    app_name: str
    installation_path_type: str  # 'program_files', 'appdata', 'temp', 'user_profile'
    contains_executables: bool
    contains_config_files: bool
    contains_data_files: bool
    
    def __post_init__(self):
        """Set item type after initialization."""
        self.item_type = 'folder'

@dataclass
class InstallerFile(DetectedItem):
    """Represents a detected installer file."""
    installer_type: str  # 'msi', 'exe', 'dmg', 'deb', 'rpm', etc.
    is_duplicate: bool
    original_name: str
    version: Optional[str]
    
    def __post_init__(self):
        """Set item type after initialization."""
        self.item_type = 'file'

@dataclass
class RegistryOrphan(DetectedItem):
    """Represents an orphaned registry entry (Windows only)."""
    registry_key: str
    registry_hive: str  # 'HKLM', 'HKCU', etc.
    referenced_path: str
    key_type: str  # 'uninstall', 'startup', 'file_association', etc.
    
    def __post_init__(self):
        """Set item type after initialization."""
        self.item_type = 'registry_key'

@dataclass
class CleanupRecommendation:
    """Represents a cleanup recommendation with risk assessment."""
    items: List[DetectedItem]
    recommendation_type: str  # 'safe_delete', 'review_required', 'high_risk'
    risk_level: str  # 'low', 'medium', 'high'
    potential_space_saved: int
    description: str
    warnings: List[str]

class LeftoverDetector:
    """Advanced heuristics and leftover detection system."""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Detection results
        self.orphaned_folders: List[OrphanedFolder] = []
        self.installer_files: List[InstallerFile] = []
        self.registry_orphans: List[RegistryOrphan] = []
        
        # Statistics
        self.scan_stats = {
            'folders_scanned': 0,
            'files_scanned': 0,
            'registry_keys_scanned': 0,
            'errors': 0
        }
        
        # ML patterns and heuristics
        self._load_detection_patterns()
        
        # Common installation paths by platform
        self._setup_installation_paths()
        """__init__."""
        """__init__."""
    
    def _setup_installation_paths(self):
        """Set up common installation paths for different platforms."""
        if sys.platform.startswith("win"):
            self.installation_paths = {
                'program_files': [
                    Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')),
                    Path(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'))
                ],
                'appdata': [
                    Path(os.environ.get('APPDATA', '')),
                    Path(os.environ.get('LOCALAPPDATA', ''))
                ],
                'temp': [
                    Path(os.environ.get('TEMP', 'C:\\Windows\\Temp')),
                    Path(os.environ.get('TMP', 'C:\\Windows\\Temp'))
                ],
                'user_profile': [
                    Path(os.environ.get('USERPROFILE', 'C:\\Users\\Default'))
                ]
            }
        elif sys.platform == "darwin":  # macOS
            home = Path.home()
            self.installation_paths = {
                'applications': [Path('/Applications'), home / 'Applications'],
                'library': [Path('/Library'), home / 'Library'],
                'temp': [Path('/tmp'), Path('/var/tmp')],
                'user_profile': [home]
            }
        else:  # Linux and other Unix-like systems
            home = Path.home()
            self.installation_paths = {
                'usr_local': [Path('/usr/local')],
                'opt': [Path('/opt')],
                'home_local': [home / '.local'],
                'temp': [Path('/tmp'), Path('/var/tmp')],
                'user_profile': [home]
            }
    
    def _load_detection_patterns(self):
        """Load ML patterns and heuristics for leftover detection."""
        # Common patterns for orphaned folders
        self.orphaned_folder_patterns = {
            'uninstaller_remnants': [
                r'.*uninstall.*',
                r'.*uninst.*',
                r'.*remove.*'
            ],
            'temp_install_folders': [
                r'.*_temp_.*',
                r'.*\.tmp.*',
                r'.*install.*temp.*',
                r'.*setup.*temp.*'
            ],
            'version_folders': [
                r'.*\d+\.\d+.*',  # Version numbers
                r'.*v\d+.*',      # Version prefixes
                r'.*_\d{4}.*'     # Year patterns
            ],
            'backup_folders': [
                r'.*backup.*',
                r'.*\.bak.*',
                r'.*_old.*',
                r'.*\.old.*'
            ]
        }
        
        # Installer file patterns
        self.installer_patterns = {
            'windows': ['.msi', '.exe', '.cab', '.msp'],
            'macos': ['.dmg', '.pkg', '.app'],
            'linux': ['.deb', '.rpm', '.tar.gz', '.tar.xz', '.appimage']
        }
        
        # Registry key patterns (Windows)
        self.registry_patterns = {
            'uninstall_keys': [
                r'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\.*',
                r'SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\.*'
            ],
            'startup_keys': [
                r'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run\\.*',
                r'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce\\.*'
            ],
            'file_associations': [
                r'SOFTWARE\\Classes\\.*'
            ]
        }
        
        # Confidence scoring weights
        self.confidence_weights = {
            'name_pattern_match': 0.3,
            'location_relevance': 0.2,
            'file_age': 0.15,
            'size_factor': 0.1,
            'content_analysis': 0.15,
            'registry_correlation': 0.1
        }
    
    def scan_orphaned_folders(self, paths: List[str] = None) -> List[OrphanedFolder]:
        """Scan for orphaned application folders in common installation paths."""
        if paths is None:
            # No InstallLocation recorded: fall back to the standard roots.
            scan_paths = []
            for path_type, path_list in self.installation_paths.items():
                scan_paths.extend(path_list)
        else:
            scan_paths = [normalize_path(p) for p in paths]
        
        self.orphaned_folders = []
        
        for base_path in scan_paths:
            if not base_path.exists() or not base_path.is_dir():
                continue
            
            try:
                self._scan_directory_for_orphans(base_path)
            except Exception as e:
                self.logger.error(f"Error scanning {base_path}: {e}")
                with self._lock:
                    self.scan_stats['errors'] += 1
        
        return self.orphaned_folders
    
    def _scan_directory_for_orphans(self, directory: Path):
        """Scan a specific directory for orphaned folders."""
        try:
            for item in directory.iterdir():
                if not item.is_dir():
                    continue
                
                with self._lock:
                    self.scan_stats['folders_scanned'] += 1
                
                # Skip system directories
                if self._is_system_directory(item):
                    continue
                
                # Analyze folder for orphan characteristics
                orphan_score = self._analyze_folder_for_orphan_signs(item)
                
                if orphan_score > 0.3:  # Threshold for considering as orphan
                    orphaned_folder = self._create_orphaned_folder_object(item, orphan_score)
                    if orphaned_folder:
                        with self._lock:
                            self.orphaned_folders.append(orphaned_folder)
        
        except PermissionError:
            self.logger.warning(f"Permission denied accessing {directory}")
        except Exception as e:
            self.logger.error(f"Error scanning directory {directory}: {e}")
            with self._lock:
                self.scan_stats['errors'] += 1
    
    def _is_system_directory(self, path: Path) -> bool:
        """Check if a directory is a system directory that should be skipped."""
        system_dirs = {
            'Windows', 'System32', 'SysWOW64', 'WinSxS',  # Windows
            'System', 'Library/System',  # macOS
            'bin', 'sbin', 'lib', 'lib64', 'usr/bin', 'usr/sbin'  # Linux
        }
        
        return any(sys_dir in str(path) for sys_dir in system_dirs)
    
    def _analyze_folder_for_orphan_signs(self, folder: Path) -> float:
        """Analyze a folder for signs that it might be an orphan."""
        score = 0.0
        reasons = []
        
        try:
            folder_name = folder.name.lower()
            
            # Pattern matching
            for pattern_type, patterns in self.orphaned_folder_patterns.items():
                for pattern in patterns:
                    if re.match(pattern, folder_name):
                        score += 0.2
                        reasons.append(f"Name matches {pattern_type} pattern")
                        break
            
            # Age is evidence, not proof: old alone never flags a folder.
            age_days = get_file_age_days(folder)
            if age_days > 30:  # Older than 30 days
                score += 0.1
                reasons.append("Folder is old")
            
            if self._folder_appears_abandoned(folder):
                score += 0.3
                reasons.append("Folder appears abandoned")
            
            # Check for uninstaller remnants
            if self._contains_uninstaller_remnants(folder):
                score += 0.4
                reasons.append("Contains uninstaller remnants")
            
        except Exception as e:
            self.logger.debug(f"Error analyzing folder {folder}: {e}")
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _folder_appears_abandoned(self, folder: Path) -> bool:
        """Check if a folder appears to be abandoned."""
        try:
            items = list(folder.iterdir())
            
            # Empty folder
            if not items:
                return True
            
            # Only contains temp files or logs
            temp_extensions = {'.tmp', '.temp', '.log', '.bak', '.old'}
            non_temp_files = [
                item for item in items 
                if item.is_file() and item.suffix.lower() not in temp_extensions
            ]
            
            return len(non_temp_files) == 0
            
        except Exception:
            return False
    
    def _contains_uninstaller_remnants(self, folder: Path) -> bool:
        """Check if folder contains uninstaller remnants."""
        try:
            for item in folder.iterdir():
                if item.is_file():
                    name_lower = item.name.lower()
                    if any(keyword in name_lower for keyword in ['uninstall', 'uninst', 'remove']):
                        return True
            return False
        except Exception:
            return False
    
    def _create_orphaned_folder_object(self, folder: Path, confidence: float) -> Optional[OrphanedFolder]:
        """Create an OrphanedFolder object from analysis results."""
        try:
            # Determine installation path type
            path_type = self._determine_installation_path_type(folder)
            
            # Analyze folder contents
            contains_executables = self._contains_executables(folder)
            contains_config_files = self._contains_config_files(folder)
            contains_data_files = self._contains_data_files(folder)
            
            size_bytes = self._calculate_folder_size(folder)
            
            # Get last modified time
            last_modified = datetime.fromtimestamp(folder.stat().st_mtime)
            
            # Extract app name from folder name
            app_name = self._extract_app_name(folder.name)
            
            return OrphanedFolder(
                path=folder,
                confidence_score=confidence,
                size_bytes=size_bytes,
                last_modified=last_modified,
                detection_reasons=[f"Orphaned folder analysis score: {confidence:.2f}"],
                metadata={'analysis_timestamp': datetime.now().isoformat()},
                app_name=app_name,
                installation_path_type=path_type,
                contains_executables=contains_executables,
                contains_config_files=contains_config_files,
                contains_data_files=contains_data_files
            )
        
        except Exception as e:
            self.logger.error(f"Error creating orphaned folder object for {folder}: {e}")
            return None
    
    def _determine_installation_path_type(self, folder: Path) -> str:
        """Determine the type of installation path."""
        folder_str = str(folder).lower()
        
        if 'program files' in folder_str:
            return 'program_files'
        elif 'appdata' in folder_str:
            return 'appdata'
        elif 'temp' in folder_str or 'tmp' in folder_str:
            return 'temp'
        elif 'applications' in folder_str:
            return 'applications'
        elif 'library' in folder_str:
            return 'library'
        else:
            return 'user_profile'
    
    def _contains_executables(self, folder: Path) -> bool:
        """Check if folder contains executable files."""
        executable_extensions = {'.exe', '.msi', '.app', '.deb', '.rpm'}
        try:
            for item in folder.rglob('*'):
                if item.is_file() and item.suffix.lower() in executable_extensions:
                    return True
        except Exception:
            pass
        return False
    
    def _contains_config_files(self, folder: Path) -> bool:
        """Check if folder contains configuration files."""
        config_extensions = {'.ini', '.cfg', '.conf', '.config', '.xml', '.json', '.plist'}
        config_names = {'config', 'settings', 'preferences'}
        
        try:
            for item in folder.rglob('*'):
                if item.is_file():
                    if (item.suffix.lower() in config_extensions or 
                        any(name in item.name.lower() for name in config_names)):
                        return True
        except Exception:
            pass
        return False
    
    def _contains_data_files(self, folder: Path) -> bool:
        """Check if folder contains data files."""
        data_extensions = {'.dat', '.db', '.sqlite', '.log', '.txt', '.csv'}
        try:
            for item in folder.rglob('*'):
                if item.is_file() and item.suffix.lower() in data_extensions:
                    return True
        except Exception:
            pass
        return False
    
    def _calculate_folder_size(self, folder: Path) -> int:
        """Calculate total size of folder in bytes."""
        total_size = 0
        try:
            for item in folder.rglob('*'):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                    except Exception:
                        continue
        except Exception:
            pass
        return total_size
    
    def _extract_app_name(self, folder_name: str) -> str:
        """Extract application name from folder name."""
        # Remove version numbers and common suffixes
        name = re.sub(r'\d+\.\d+.*', '', folder_name)
        name = re.sub(r'_old|_backup|\.old|\.bak', '', name)
        name = name.strip('_- ')
        return name or folder_name
    
    def detect_installer_files(self, paths: List[str] = None) -> List[InstallerFile]:
        if paths is None:
            # Scan common download and temp directories
            scan_paths = []
            if sys.platform.startswith("win"):
                scan_paths.extend([
                    Path(os.environ.get('USERPROFILE', '')) / 'Downloads',
                    Path(os.environ.get('TEMP', '')),
                    Path(os.environ.get('TMP', ''))
                ])
            else:
                home = Path.home()
                scan_paths.extend([
                    home / 'Downloads',
                    Path('/tmp'),
                    Path('/var/tmp')
                ])
        else:
            scan_paths = [normalize_path(p) for p in paths]
        
        self.installer_files = []
        
        # Get installer extensions for current platform
        if sys.platform.startswith("win"):
            installer_extensions = set(self.installer_patterns['windows'])
        elif sys.platform == "darwin":
            installer_extensions = set(self.installer_patterns['macos'])
        else:
            installer_extensions = set(self.installer_patterns['linux'])
        
        # Scan paths for installer files
        for base_path in scan_paths:
            if not base_path.exists() or not base_path.is_dir():
                continue
            
            try:
                self._scan_for_installer_files(base_path, installer_extensions)
            except Exception as e:
                self.logger.error(f"Error scanning {base_path} for installers: {e}")
                with self._lock:
                    self.scan_stats['errors'] += 1
        
        return self.installer_files
        """detect_installer_files."""
        """detect_installer_files."""
    
    def _scan_for_installer_files(self, directory: Path, installer_extensions: set):
        """Scan directory for installer files."""
        try:
            for item in directory.rglob('*'):
                if not item.is_file():
                    continue
                
                with self._lock:
                    self.scan_stats['files_scanned'] += 1
                
                if item.suffix.lower() in installer_extensions:
                    installer_file = self._analyze_installer_file(item)
                    if installer_file:
                        with self._lock:
                            self.installer_files.append(installer_file)
        
        except PermissionError:
            self.logger.warning(f"Permission denied accessing {directory}")
        except Exception as e:
            self.logger.error(f"Error scanning directory {directory} for installers: {e}")
            with self._lock:
                self.scan_stats['errors'] += 1
    
    def _analyze_installer_file(self, file_path: Path) -> Optional[InstallerFile]:
        """Analyze a potential installer file."""
        try:
            # Get file stats
            stat_info = file_path.stat()
            size_bytes = stat_info.st_size
            last_modified = datetime.fromtimestamp(stat_info.st_mtime)
            
            # Determine installer type
            installer_type = file_path.suffix.lower().lstrip('.')
            
            is_duplicate = self._check_installer_duplicate(file_path)
            
            # Extract version if possible
            version = self._extract_version_from_filename(file_path.name)
            
            confidence = self._calculate_installer_confidence(file_path, size_bytes)
            
            return InstallerFile(
                path=file_path,
                item_type='file',
                confidence_score=confidence,
                size_bytes=size_bytes,
                last_modified=last_modified,
                detection_reasons=[f"Installer file detected: {installer_type}"],
                metadata={'scan_timestamp': datetime.now().isoformat()},
                installer_type=installer_type,
                is_duplicate=is_duplicate,
                original_name=file_path.name,
                version=version
            )
        
        except Exception as e:
            self.logger.error(f"Error analyzing installer file {file_path}: {e}")
            return None
    
    def _check_installer_duplicate(self, file_path: Path) -> bool:
        """Check if installer file is a duplicate (simplified implementation)."""
        # file hashes, names, and metadata more thoroughly
        base_name = file_path.stem.lower()
        
        # Check against already found installers
        for existing in self.installer_files:
            existing_base = existing.path.stem.lower()
            if base_name in existing_base or existing_base in base_name:
                return True
        
        return False
    
    def _extract_version_from_filename(self, filename: str) -> Optional[str]:
        """Extract version number from filename."""
        # Look for version patterns like 1.2.3, v1.2, 2023.1, etc.
        version_patterns = [
            r'v?(\d+\.\d+\.\d+)',
            r'v?(\d+\.\d+)',
            r'(\d{4}\.\d+)',
            r'_v?(\d+\.\d+)'
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _calculate_installer_confidence(self, file_path: Path, size_bytes: int) -> float:
        """Calculate confidence score for installer file detection."""
        score = 0.5  # Base score for having installer extension
        
        # Size factor (installers are usually substantial)
        if size_bytes > 1024 * 1024:  # > 1MB
            score += 0.2
        if size_bytes > 10 * 1024 * 1024:  # > 10MB
            score += 0.1
        
        # Name patterns
        name_lower = file_path.name.lower()
        installer_keywords = ['setup', 'install', 'installer', 'update', 'patch']
        if any(keyword in name_lower for keyword in installer_keywords):
            score += 0.2
        
        return min(score, 1.0)
    
    def analyze_registry_orphans(self) -> List[RegistryOrphan]:
        """Analyze Windows registry for orphaned entries."""
        if not WINDOWS_REGISTRY_AVAILABLE or not sys.platform.startswith("win"):
            self.logger.warning("Registry analysis not available on this platform")
            return []
        
        self.registry_orphans = []
        
        # Analyze different registry areas
        registry_areas = [
            (winreg.HKEY_LOCAL_MACHINE, "HKLM", "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"),
            (winreg.HKEY_CURRENT_USER, "HKCU", "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"),
            (winreg.HKEY_LOCAL_MACHINE, "HKLM", "SOFTWARE\\Classes")
        ]
        
        for hive, hive_name, key_path in registry_areas:
            try:
                self._analyze_registry_key(hive, hive_name, key_path)
            except Exception as e:
                self.logger.error(f"Error analyzing registry key {hive_name}\\{key_path}: {e}")
                with self._lock:
                    self.scan_stats['errors'] += 1
        
        return self.registry_orphans
    
    def _analyze_registry_key(self, hive, hive_name: str, key_path: str):
        """Analyze a specific registry key for orphaned entries."""
        try:
            with winreg.OpenKey(hive, key_path) as key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with self._lock:
                            self.scan_stats['registry_keys_scanned'] += 1
                        
                        # Analyze subkey for orphaned references
                        self._check_registry_subkey_for_orphans(
                            hive, hive_name, f"{key_path}\\{subkey_name}", subkey_name
                        )
                        i += 1
                    except WindowsError:
                        break
        
        except Exception as e:
            self.logger.debug(f"Could not access registry key {hive_name}\\{key_path}: {e}")
    
    def _check_registry_subkey_for_orphans(self, hive, hive_name: str, full_key_path: str, subkey_name: str):
        """Check a registry subkey for orphaned file references."""
        try:
            with winreg.OpenKey(hive, full_key_path) as subkey:
                # Look for file path references
                file_path_values = ['InstallLocation', 'UninstallString', 'DisplayIcon', 'InstallSource']
                
                for value_name in file_path_values:
                    try:
                        value, _ = winreg.QueryValueEx(subkey, value_name)
                        if isinstance(value, str) and (value.startswith('C:') or value.startswith('"C:')):
                            # Clean up the path
                            clean_path = value.strip('"').split(' ')[0]  # Remove arguments
                            
                            if not Path(clean_path).exists():
                                orphan = self._create_registry_orphan(
                                    full_key_path, hive_name, clean_path, 'uninstall'
                                )
                                if orphan:
                                    with self._lock:
                                        self.registry_orphans.append(orphan)
                    except FileNotFoundError:
                        continue  # Value doesn't exist
        
        except Exception as e:
            self.logger.debug(f"Error checking registry subkey {full_key_path}: {e}")
    
    def _create_registry_orphan(self, registry_key: str, hive: str, referenced_path: str, key_type: str) -> Optional[RegistryOrphan]:
        """Create a RegistryOrphan object."""
        try:
            # Uninstall keys are strong evidence of an installed app, so they
            # start at higher confidence than generic registry references.
            confidence = 0.7 if key_type == 'uninstall' else 0.5
            
            return RegistryOrphan(
                path=Path(registry_key),  # Use registry key as path
                confidence_score=confidence,
                size_bytes=0,  # Registry entries don't have meaningful size
                last_modified=datetime.now(),  # We can't easily get registry modification time
                detection_reasons=[f"Registry key references non-existent path: {referenced_path}"],
                metadata={'scan_timestamp': datetime.now().isoformat()},
                registry_key=registry_key,
                registry_hive=hive,
                referenced_path=referenced_path,
                key_type=key_type
            )
        
        except Exception as e:
            self.logger.error(f"Error creating registry orphan object: {e}")
            return None
    
    def apply_ml_patterns(self, items: List[DetectedItem]) -> List[DetectedItem]:
        """Apply machine learning patterns to improve detection accuracy."""
        # This is a simplified ML pattern application
        
        enhanced_items = []
        
        for item in items:
            # Apply pattern-based confidence adjustments
            adjusted_confidence = self._apply_pattern_adjustments(item)
            
            # Create new item with adjusted confidence
            if isinstance(item, OrphanedFolder):
                enhanced_item = OrphanedFolder(
                    path=item.path,
                    confidence_score=adjusted_confidence,
                    size_bytes=item.size_bytes,
                    last_modified=item.last_modified,
                    detection_reasons=item.detection_reasons + ["ML pattern adjustment applied"],
                    metadata=item.metadata,
                    app_name=item.app_name,
                    installation_path_type=item.installation_path_type,
                    contains_executables=item.contains_executables,
                    contains_config_files=item.contains_config_files,
                    contains_data_files=item.contains_data_files
                )
            elif isinstance(item, InstallerFile):
                enhanced_item = InstallerFile(
                    path=item.path,
                    item_type='file',
                    confidence_score=adjusted_confidence,
                    size_bytes=item.size_bytes,
                    last_modified=item.last_modified,
                    detection_reasons=item.detection_reasons + ["ML pattern adjustment applied"],
                    metadata=item.metadata,
                    installer_type=item.installer_type,
                    is_duplicate=item.is_duplicate,
                    original_name=item.original_name,
                    version=item.version
                )
            else:
                enhanced_item = item
                enhanced_item.confidence_score = adjusted_confidence
            
            enhanced_items.append(enhanced_item)
        
        return enhanced_items
    
    def _apply_pattern_adjustments(self, item: DetectedItem) -> float:
        """Apply pattern-based adjustments to confidence score."""
        confidence = item.confidence_score
        
        # Age-based adjustments
        age_days = (datetime.now() - item.last_modified).days
        if age_days > 90:  # Very old items are more likely to be leftovers
            confidence += 0.1
        elif age_days < 7:  # Very recent items are less likely to be leftovers
            confidence -= 0.2
        
        # Size-based adjustments
        if item.size_bytes < 1024:  # Very small items might be remnants
            confidence += 0.05
        elif item.size_bytes > 100 * 1024 * 1024:  # Very large items need careful review
            confidence -= 0.1
        
        # Path-based adjustments
        path_str = str(item.path).lower()
        if 'temp' in path_str or 'tmp' in path_str:
            confidence += 0.15
        elif 'program files' in path_str:
            confidence -= 0.1  # Be more careful with program files
        
        return max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
    
    def calculate_confidence_score(self, item: DetectedItem) -> float:
        """Calculate overall confidence score for a detected item."""
        return item.confidence_score
    
    def generate_cleanup_recommendations(self, confidence_threshold: float = 0.7) -> List[CleanupRecommendation]:
        """Generate cleanup recommendations based on detected items."""
        all_items = self.orphaned_folders + self.installer_files + self.registry_orphans
        
        if not all_items:
            return []
        
        # Filter by confidence threshold
        high_confidence_items = [item for item in all_items if item.confidence_score >= confidence_threshold]
        medium_confidence_items = [item for item in all_items if 0.4 <= item.confidence_score < confidence_threshold]
        low_confidence_items = [item for item in all_items if item.confidence_score < 0.4]
        
        recommendations = []
        
        # High confidence recommendation
        if high_confidence_items:
            total_size = sum(item.size_bytes for item in high_confidence_items)
            recommendations.append(CleanupRecommendation(
                items=high_confidence_items,
                recommendation_type='safe_delete',
                risk_level='low',
                potential_space_saved=total_size,
                description=f"Safe to clean {len(high_confidence_items)} high-confidence leftover items",
                warnings=["Always review items before deletion", "Create backup if unsure"]
            ))
        
        # Medium confidence recommendation
        if medium_confidence_items:
            total_size = sum(item.size_bytes for item in medium_confidence_items)
            recommendations.append(CleanupRecommendation(
                items=medium_confidence_items,
                recommendation_type='review_required',
                risk_level='medium',
                potential_space_saved=total_size,
                description=f"Review required for {len(medium_confidence_items)} medium-confidence items",
                warnings=["Manual review strongly recommended", "May contain legitimate files"]
            ))
        
        # Low confidence recommendation
        if low_confidence_items:
            total_size = sum(item.size_bytes for item in low_confidence_items)
            recommendations.append(CleanupRecommendation(
                items=low_confidence_items,
                recommendation_type='high_risk',
                risk_level='high',
                potential_space_saved=total_size,
                description=f"High risk: {len(low_confidence_items)} low-confidence items detected",
                warnings=["Do not delete without expert review", "Likely contains legitimate files"]
            ))
        
        return recommendations
    
    def export_results(self, filepath: str) -> bool:
        """Export detection results to JSON file."""
        try:
            results = {
                'scan_timestamp': datetime.now().isoformat(),
                'scan_stats': self.scan_stats,
                'orphaned_folders': [item.to_dict() for item in self.orphaned_folders],
                'installer_files': [item.to_dict() for item in self.installer_files],
                'registry_orphans': [item.to_dict() for item in self.registry_orphans],
                'total_items': len(self.orphaned_folders) + len(self.installer_files) + len(self.registry_orphans)
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Results exported to {filepath}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error exporting results: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detection statistics."""
        return {
            **self.scan_stats,
            'orphaned_folders_found': len(self.orphaned_folders),
            'installer_files_found': len(self.installer_files),
            'registry_orphans_found': len(self.registry_orphans),
            'total_items_found': len(self.orphaned_folders) + len(self.installer_files) + len(self.registry_orphans)
        }