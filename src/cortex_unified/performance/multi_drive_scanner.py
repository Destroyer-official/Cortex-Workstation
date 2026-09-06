"""Parallel scanning across multiple drives, volumes, and user profiles.

Provides drive discovery (fixed, removable, network shares), per-user-profile
enumeration with permission checks, and thread-pool fan-out scanning with
unified progress reporting and cross-location result aggregation.
"""

import concurrent.futures
import os
import platform
import psutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable, Set
from dataclasses import dataclass, asdict
import logging

# keyring is optional; without it, network credentials live only in the in-memory cache.
try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False
    keyring = None

logger = logging.getLogger(__name__)

if not HAS_KEYRING:
    logger.info("keyring not installed - network credentials will only be stored in memory")

@dataclass
class DriveInfo:
    """Snapshot of one mounted drive with capacity, type, and readiness."""
    path: str
    label: str
    filesystem: str
    total_size: int
    free_size: int
    drive_type: str
    is_ready: bool = True
    mount_point: Optional[str] = None
    
    @property
    def used_size(self) -> int:
        """Used bytes computed as total minus free.
        
        Returns:
                    int: Result of the operation."""
        return self.total_size - self.free_size
    
    @property
    def usage_percent(self) -> float:
        """Used capacity percent; 0.0 when total size is zero.
        
        Returns:
                    float: Result of the operation."""
        if self.total_size == 0:
            return 0.0
        return (self.used_size / self.total_size) * 100

@dataclass
class NetworkDrive:
    """One network share with connection and auth state."""
    path: str
    server: str
    share: str
    is_connected: bool
    requires_auth: bool
    username: Optional[str] = None
    last_error: Optional[str] = None

@dataclass
class UserProfile:
    """One OS user profile with accessibility and permission metadata."""
    username: str
    profile_path: str
    is_active: bool
    last_login: Optional[datetime] = None
    is_accessible: bool = True
    sid: Optional[str] = None  # Windows Security Identifier
    profile_size: Optional[int] = None
    permissions: Optional[Dict[str, bool]] = None

@dataclass
class ScanProgress:
    """Mutable counters describing progress through a multi-location scan."""
    total_locations: int
    completed_locations: int
    current_location: str
    current_progress: float
    start_time: datetime
    estimated_completion: Optional[datetime] = None
    errors: List[str] = None
    
    def __post_init__(self):
        """Initialize the error list when None."""
        if self.errors is None:
            self.errors = []
    
    @property
    def overall_progress(self) -> float:
        """((completed/total)*100) + (current_progress/total) (note: current_progress 0-100 divided by total)."""
        if self.total_locations == 0:
            return 0.0
        base_progress = (self.completed_locations / self.total_locations) * 100
        current_contribution = (self.current_progress / self.total_locations)
        return min(100.0, base_progress + current_contribution)

@dataclass
class AggregatedResult:
    """Totals and per-location results aggregated across a scan."""
    total_empty_files: int
    total_empty_dirs: int
    total_size_freed: int
    location_results: Dict[str, Dict[str, Any]]
    scan_duration: float
    errors: List[str]
    summary_stats: Dict[str, Any]

class MultiUserScanner:
    """Scans across multiple OS user profiles with per-profile permission handling.

    Discovery covers Windows (C:/Users) and Unix (/home, /root) layouts;
    unreadable profiles are reported but produce error entries when scanned.
    """
    
    def __init__(self, config: Any = None):
        """Set up scan state.

        Args:
            config: Optional application configuration forwarded to scanners.
        """
        self.config = config
        self._scan_results: Dict[str, Any] = {}
        self._scan_lock = threading.Lock()
        self._progress_callbacks: List[Callable] = []
        self._current_progress = ScanProgress(0, 0, "", 0.0, datetime.now())
        
    def detect_user_profiles(self) -> List[UserProfile]:
        """Enumerate user profiles with permission and activity metadata.

        Returns:
            Detected profiles; falls back to the current user's home directory
            if platform detection raises.
        """
        profiles = []
        system = platform.system().lower()
        
        try:
            if system == "windows":
                profiles = self._detect_windows_user_profiles_enhanced()
            else:
                profiles = self._detect_unix_user_profiles_enhanced()
        except Exception as e:
            logger.error(f"Error detecting user profiles: {e}")
            # Fallback to current user only
            current_user = os.getenv('USERNAME') or os.getenv('USER') or 'unknown'
            home_dir = str(Path.home())
            
            profiles = [UserProfile(
                username=current_user,
                profile_path=home_dir,
                is_active=True,
                is_accessible=True,
                permissions={"read": True, "write": True}
            )]
        
        return profiles
    
    def _detect_windows_user_profiles_enhanced(self) -> List[UserProfile]:
        """List C:/Users profiles skipping built-ins; records permissions and size.
        
        Returns:
                    List[UserProfile]: List of processed items or identifiers."""
        profiles = []
        
        try:
            # Check common user profile locations dynamically
            users_dir = Path.home().parent if Path.home().parent.exists() else Path(os.environ.get("SystemDrive", "C:") + "/Users")
            if users_dir.exists():
                for user_dir in users_dir.iterdir():
                    if user_dir.is_dir() and not user_dir.name.startswith('.'):
                        # Built-in/shared accounts, not real user profiles
                        if user_dir.name.lower() in ['public', 'default', 'all users', 'defaultapppool']:
                            continue
                        
                        permissions = self._check_path_permissions(user_dir)
                        is_accessible = permissions.get("read", False)
                        
                        # Size needs a full recursive walk; only pay it for readable profiles
                        profile_size = None
                        if is_accessible:
                            try:
                                profile_size = sum(f.stat().st_size for f in user_dir.rglob('*') if f.is_file())
                            except (PermissionError, OSError):
                                pass
                        
                        last_login = self._get_windows_last_login(user_dir.name)
                        
                        profile = UserProfile(
                            username=user_dir.name,
                            profile_path=str(user_dir),
                            is_active=self._is_user_active_windows(user_dir.name),
                            is_accessible=is_accessible,
                            last_login=last_login,
                            profile_size=profile_size,
                            permissions=permissions
                        )
                        profiles.append(profile)
        
        except Exception as e:
            logger.error(f"Error detecting Windows user profiles: {e}")
        
        return profiles
    
    def _detect_unix_user_profiles_enhanced(self) -> List[UserProfile]:
        """List /home profiles plus /root; records permissions and size.
        
        Returns:
                    List[UserProfile]: List of processed items or identifiers."""
        profiles = []
        
        try:
            # Check /home directory
            home_dir = Path("/home")
            if home_dir.exists():
                for user_dir in home_dir.iterdir():
                    if user_dir.is_dir():
                        permissions = self._check_path_permissions(user_dir)
                        is_accessible = permissions.get("read", False)
                        
                        # Size needs a full recursive walk; only pay it for readable profiles
                        profile_size = None
                        if is_accessible:
                            try:
                                profile_size = sum(f.stat().st_size for f in user_dir.rglob('*') if f.is_file())
                            except (PermissionError, OSError):
                                pass
                        
                        # Get last login from wtmp/utmp if available
                        last_login = self._get_unix_last_login(user_dir.name)
                        
                        profile = UserProfile(
                            username=user_dir.name,
                            profile_path=str(user_dir),
                            is_active=self._is_user_active_unix(user_dir.name),
                            is_accessible=is_accessible,
                            last_login=last_login,
                            profile_size=profile_size,
                            permissions=permissions
                        )
                        profiles.append(profile)
            
            root_dir = Path("/root")
            if root_dir.exists():
                permissions = self._check_path_permissions(root_dir)
                profile = UserProfile(
                    username="root",
                    profile_path=str(root_dir),
                    is_active=True,
                    is_accessible=permissions.get("read", False),
                    permissions=permissions
                )
                profiles.append(profile)
        
        except Exception as e:
            logger.error(f"Error detecting Unix user profiles: {e}")
        
        return profiles
    
    def _check_path_permissions(self, path: Path) -> Dict[str, bool]:
        """Probe read/write/execute access for the current process; never elevates.
        
        No elevation attempted; reflect current-process access only.
        
        Args:
                    path (Path): Filesystem path to the target file or directory.
        
                Returns:
                    Dict[str, bool]: Dictionary mapping identifiers to status or values."""
        permissions = {"read": False, "write": False, "execute": False}
        
        try:
            permissions["read"] = os.access(path, os.R_OK)
            permissions["write"] = os.access(path, os.W_OK)
            permissions["execute"] = os.access(path, os.X_OK)
        except Exception:
            pass
        
        return permissions
    
    def _get_windows_last_login(self, username: str) -> Optional[datetime]:
        """Best-effort last logon via net user; None when unavailable.
        
        Args:
                    username (str): The username parameter.
        
                Returns:
                    Optional[datetime]: Result of the operation."""
        try:
            if platform.system().lower() == "windows":
                import subprocess
                result = subprocess.run(
                    ["net", "user", username],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if "Last logon" in line:
                            parts = line.split("Last logon", 1)[-1].strip()
                            if not parts or "never" in parts.lower():
                                return None
                            # Try common locale date/time formats
                            for fmt in (
                                "%m/%d/%Y %I:%M:%S %p",
                                "%m/%d/%Y %I:%M %p",
                                "%d/%m/%Y %H:%M:%S",
                                "%d/%m/%Y %H:%M",
                                "%Y-%m-%d %H:%M:%S",
                                "%d.%m.%Y %H:%M:%S",
                            ):
                                try:
                                    return datetime.strptime(parts, fmt)
                                except ValueError:
                                    continue
        except Exception:
            pass
        return None
    
    def _get_unix_last_login(self, username: str) -> Optional[datetime]:
        """Best-effort last login via last -1; None when unavailable.
        
        Args:
                    username (str): The username parameter.
        
                Returns:
                    Optional[datetime]: Result of the operation."""
        try:
            import subprocess
            result = subprocess.run(
                ["last", "-1", username],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                first_line = result.stdout.strip().split('\n')[0]
                # Format: username tty hostname Day Mon DD HH:MM
                tokens = first_line.split()
                if len(tokens) >= 7:
                    # tokens[3:7] e.g. ["Mon", "Sep", "2", "14:15"]
                    date_str = f"{tokens[4]} {tokens[5]} {datetime.now().year} {tokens[6]}"
                    try:
                        return datetime.strptime(date_str, "%b %d %Y %H:%M")
                    except ValueError:
                        pass
        except Exception:
            pass
        return None
    
    def _is_user_active_windows(self, username: str) -> bool:
        """True when the user appears in query user output.
        
        Args:
                    username (str): The username parameter.
        
                Returns:
                    bool: True if the operation succeeded, False otherwise."""
        try:
            import subprocess
            result = subprocess.run(
                ["query", "user"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return username.lower() in result.stdout.lower()
        except Exception:
            return False
    
    def _is_user_active_unix(self, username: str) -> bool:
        """True when the user appears in who output.
        
        Args:
                    username (str): The username parameter.
        
                Returns:
                    bool: True if the operation succeeded, False otherwise."""
        try:
            import subprocess
            result = subprocess.run(
                ["who"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return username in result.stdout
        except Exception:
            return False
    
    def scan_user_profile(self, profile: UserProfile, scanner_factory: Optional[Callable] = None) -> Dict[str, Any]:
        """Scan one user profile via a Scanner factory; permission gaps yield error dicts.
        
        Needs read access; admin may be required for other users profiles.
        
        Args:
                    profile (UserProfile): The profile parameter.
                    scanner_factory (Optional[Callable]): The scanner factory parameter.
        
                Returns:
                    Dict[str, Any]: Dictionary mapping identifiers to status or values."""
        if not profile.is_accessible:
            return {
                "error": "Access denied",
                "empty_files": [],
                "empty_dirs": [],
                "profile_info": asdict(profile)
            }
        
        try:
            if not scanner_factory:
                from cortex_unified.core.scanner import Scanner
                scanner_factory = lambda path: Scanner(root_path=path)
            
            # Fresh scanner per profile keeps results/stats from bleeding across profiles
            scanner = scanner_factory(profile.profile_path)
            
            empty_files, empty_dirs = scanner.scan()
            
            result = {
                "profile_path": profile.profile_path,
                "empty_files": [str(f) for f in empty_files],
                "empty_dirs": [str(d) for d in empty_dirs],
                "stats": scanner.get_stats(),
                "profile_info": asdict(profile)
            }
            
            logger.info(f"Completed scan of user profile: {profile.username}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to scan user profile {profile.username}: {e}"
            logger.error(error_msg)
            return {
                "error": str(e),
                "empty_files": [],
                "empty_dirs": [],
                "profile_info": asdict(profile)
            }
    
    def handle_permissions(self, path: str) -> Dict[str, Any]:
        """Check access to a path and whether elevation would grant it.

        Returns:
            Dict with the permission map and accessible flag; when read access
            is denied, includes requires_elevation and elevation_available.
        """
        path_obj = Path(path)
        
        result = {
            "path": path,
            "accessible": False,
            "permissions": {},
            "requires_elevation": False,
            "elevation_available": False
        }
        
        try:
            permissions = self._check_path_permissions(path_obj)
            result["permissions"] = permissions
            result["accessible"] = permissions.get("read", False)
            
            # Admin rights unlock some protected trees, so note elevation as
            # a remedy rather than failing the drive outright.
            if not result["accessible"]:
                result["requires_elevation"] = True
                result["elevation_available"] = self._can_elevate()
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _can_elevate(self) -> bool:
        """True when a UAC elevation prompt can succeed for this session.
        
        Admin check only; does not itself elevate.
        
        Returns:
                    bool: True if the operation succeeded, False otherwise."""
        try:
            if platform.system().lower() == "windows":
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except Exception:
            return False
    
    def aggregate_results(self, results: Dict[str, Dict[str, Any]]) -> AggregatedResult:
        """Sum empty files, dirs, and sizes; collect errors and per-location stats.
        
        Args:
                    results (Dict[str, Dict[str, Any]]): Collection or dictionary holding operation results.
        
                Returns:
                    AggregatedResult: Result of the operation."""
        total_empty_files = 0
        total_empty_dirs = 0
        total_size_freed = 0
        errors = []
        
        # Collect statistics
        for location, result in results.items():
            if "error" in result:
                errors.append(f"{location}: {result['error']}")
                continue
            
            total_empty_files += len(result.get("empty_files", []))
            total_empty_dirs += len(result.get("empty_dirs", []))
            
            stats = result.get("stats", {})
            if isinstance(stats, dict):
                total_size_freed += stats.get("total_size", 0)
        
        # Generate summary statistics
        summary_stats = {
            "locations_scanned": len(results),
            "successful_scans": len([r for r in results.values() if "error" not in r]),
            "failed_scans": len([r for r in results.values() if "error" in r]),
            "average_files_per_location": total_empty_files / max(1, len(results)),
            "average_dirs_per_location": total_empty_dirs / max(1, len(results))
        }
        
        return AggregatedResult(
            total_empty_files=total_empty_files,
            total_empty_dirs=total_empty_dirs,
            total_size_freed=total_size_freed,
            location_results=results,
            scan_duration=0.0,  # Will be set by caller
            errors=errors,
            summary_stats=summary_stats
        )

class DriveManager:
    """Discovers drives, caches info, and manages network credentials and monitoring."""
    
    def __init__(self, config: Any = None):
        """Store config and initialize drive cache, credentials, and monitoring state.
        
        Args:
                    config (Any): The config parameter."""
        self.config = config
        self._drive_cache: Dict[str, DriveInfo] = {}
        self._network_credentials: Dict[str, Dict[str, str]] = {}
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._change_callbacks: List[Callable] = []
        self._disconnected_drives: Set[str] = set()
    
    def detect_all_drives(self) -> List[DriveInfo]:
        """List all partitions via psutil with fallback; caches by mountpoint.
        
        Returns:
                    List[DriveInfo]: List of processed items or identifiers."""
        drives = []
        
        try:
            # Get all disk partitions including network drives
            partitions = psutil.disk_partitions(all=True)
            
            for partition in partitions:
                try:
                    drive_info = self._create_drive_info(partition)
                    drives.append(drive_info)
                    
                    # Cache the drive info
                    self._drive_cache[partition.mountpoint] = drive_info
                    
                except Exception as e:
                    logger.warning(f"Could not process drive {partition.mountpoint}: {e}")
                    # Create minimal drive info for inaccessible drives
                    drive_info = DriveInfo(
                        path=partition.mountpoint,
                        label="",
                        filesystem=partition.fstype,
                        total_size=0,
                        free_size=0,
                        drive_type=self._get_drive_type(partition),
                        is_ready=False,
                        mount_point=partition.mountpoint
                    )
                    drives.append(drive_info)
        
        except Exception as e:
            logger.error(f"Error detecting drives: {e}")
            # Fallback detection
            drives.extend(self._fallback_drive_detection())
        
        return drives
    
    def _create_drive_info(self, partition) -> DriveInfo:
        """Build DriveInfo from a psutil partition; inaccessible drives are marked not ready.
        
        Args:
                    partition: The partition parameter.
        
                Returns:
                    DriveInfo: Result of the operation."""
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            
            # Determine drive type
            drive_type = self._get_drive_type(partition)
            
            label = self._get_drive_label(partition.mountpoint)
            
            return DriveInfo(
                path=partition.mountpoint,
                label=label,
                filesystem=partition.fstype,
                total_size=usage.total,
                free_size=usage.free,
                drive_type=drive_type,
                is_ready=True,
                mount_point=partition.mountpoint
            )
            
        except (PermissionError, OSError, psutil.Error):
            # Drive not accessible
            return DriveInfo(
                path=partition.mountpoint,
                label="",
                filesystem=partition.fstype,
                total_size=0,
                free_size=0,
                drive_type=self._get_drive_type(partition),
                is_ready=False,
                mount_point=partition.mountpoint
            )
    
    def _get_drive_type(self, partition) -> str:
        """Classify a drive as network, removable, optical, ram, or fixed.
        
        Args:
                    partition: The partition parameter.
        
                Returns:
                    str: Formatted string or path."""
        opts = getattr(partition, 'opts', '').lower()
        fstype = getattr(partition, 'fstype', '').lower()
        device = getattr(partition, 'device', '').lower()
        
        # Network drives
        if 'network' in opts or fstype in ['nfs', 'cifs', 'smb', 'smbfs']:
            return 'network'
        
        # Removable drives
        if 'removable' in opts or fstype in ['fat32', 'exfat', 'vfat']:
            return 'removable'
        
        # CD/DVD drives
        if fstype in ['iso9660', 'udf']:
            return 'optical'
        
        # RAM drives
        if fstype in ['tmpfs', 'ramfs']:
            return 'ram'
        
        # Check device name for hints
        if any(hint in device for hint in ['usb', 'sd', 'mmc']):
            return 'removable'
        
        return 'fixed'
    
    def _get_drive_label(self, path: str) -> str:
        """Read the Windows volume label; empty elsewhere or on failure.
        
        Args:
                    path (str): Filesystem path to the target file or directory.
        
                Returns:
                    str: Formatted string or path."""
        try:
            if platform.system().lower() == "windows":
                import ctypes
                from ctypes import wintypes
                
                volume_name_buffer = ctypes.create_unicode_buffer(1024)
                file_system_name_buffer = ctypes.create_unicode_buffer(1024)
                
                result = ctypes.windll.kernel32.GetVolumeInformationW(
                    ctypes.c_wchar_p(path),
                    volume_name_buffer,
                    ctypes.sizeof(volume_name_buffer),
                    None,
                    None,
                    None,
                    file_system_name_buffer,
                    ctypes.sizeof(file_system_name_buffer)
                )
                
                if result:
                    return volume_name_buffer.value or ""
        except Exception:
            pass
        
        return ""
    
    def _fallback_drive_detection(self) -> List[DriveInfo]:
        """Drive-listing fallback dispatching to OS-specific detectors.
        
        Returns:
                    List[DriveInfo]: List of processed items or identifiers."""
        drives = []
        system = platform.system().lower()
        
        try:
            if system == "windows":
                drives.extend(self._detect_windows_drives())
            else:
                drives.extend(self._detect_unix_drives())
        except Exception as e:
            logger.error(f"Fallback drive detection failed: {e}")
        
        return drives
    
    def _detect_windows_drives(self) -> List[DriveInfo]:
        """List logical drives via GetLogicalDrives; not-ready drives are flagged.
        
        Returns:
                    List[DriveInfo]: List of processed items or identifiers."""
        drives = []
        
        try:
            import ctypes
            
            drive_bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            
            for i in range(26):
                if drive_bitmask & (1 << i):
                    drive_letter = chr(ord('A') + i) + ':\\'
                    
                    try:
                        usage = psutil.disk_usage(drive_letter)
                        label = self._get_drive_label(drive_letter)
                        
                        drives.append(DriveInfo(
                            path=drive_letter,
                            label=label,
                            filesystem="NTFS",  # Default assumption
                            total_size=usage.total,
                            free_size=usage.free,
                            drive_type="fixed",
                            is_ready=True,
                            mount_point=drive_letter
                        ))
                    except (OSError, psutil.Error):
                        # Drive not ready
                        drives.append(DriveInfo(
                            path=drive_letter,
                            label="",
                            filesystem="",
                            total_size=0,
                            free_size=0,
                            drive_type="unknown",
                            is_ready=False,
                            mount_point=drive_letter
                        ))
        except Exception:
            pass
        
        return drives
    
    def _detect_unix_drives(self) -> List[DriveInfo]:
        """Probe common mount points via disk_usage; skips inaccessible ones.
        
        Returns:
                    List[DriveInfo]: List of processed items or identifiers."""
        drives = []
        
        # Common mount points to check
        common_mounts = ["/", "/home", "/tmp", "/var", "/usr", "/boot"]
        
        for mount_point in common_mounts:
            if os.path.exists(mount_point):
                try:
                    usage = psutil.disk_usage(mount_point)
                    
                    drives.append(DriveInfo(
                        path=mount_point,
                        label="",
                        filesystem="ext4",  # Default assumption
                        total_size=usage.total,
                        free_size=usage.free,
                        drive_type="fixed",
                        is_ready=True,
                        mount_point=mount_point
                    ))
                except (OSError, psutil.Error):
                    pass
        
        return drives
    
    def handle_network_drives(self, credentials: Dict[str, str] = None) -> List[NetworkDrive]:
        """List network partitions, cache credentials, and attempt reconnects.
        
        Args:
                    credentials (Dict[str, str]): The credentials parameter.
        
                Returns:
                    List[NetworkDrive]: List of processed items or identifiers."""
        network_drives = []
        
        if credentials:
            self._store_credentials(credentials)
        
        try:
            # Get all partitions and filter for network drives
            partitions = psutil.disk_partitions(all=True)
            
            for partition in partitions:
                if self._get_drive_type(partition) == 'network':
                    network_drive = self._process_network_drive(partition)
                    network_drives.append(network_drive)
        
        except Exception as e:
            logger.error(f"Error handling network drives: {e}")
            if network_drives:
                network_drives[0].last_error = str(e)
        
        return network_drives
    
    def _process_network_drive(self, partition) -> NetworkDrive:
        """Build NetworkDrive state and reconnect when credentials exist.
        
        Args:
                    partition: The partition parameter.
        
                Returns:
                    NetworkDrive: Result of the operation."""
        server, share = self._parse_network_path(partition.device)
        
        is_connected = os.path.exists(partition.mountpoint)
        
        # Get stored credentials for this server
        stored_creds = self._get_stored_credentials(server)
        
        network_drive = NetworkDrive(
            path=partition.mountpoint,
            server=server,
            share=share,
            is_connected=is_connected,
            requires_auth=not is_connected and server not in self._network_credentials,
            username=stored_creds.get("username") if stored_creds else None
        )
        
        # Try to connect if we have credentials but drive is not connected
        if not is_connected and stored_creds:
            try:
                self._attempt_network_connection(network_drive, stored_creds)
            except Exception as e:
                network_drive.last_error = str(e)
        
        return network_drive
    
    def _store_credentials(self, credentials: Dict[str, str]) -> None:
        """Cache credentials in memory and in keyring when available.
        
        Side effect: caches in memory and optionally in OS keyring.
        
        Args:
                    credentials (Dict[str, str]): The credentials parameter."""
        for server, cred_info in credentials.items():
            try:
                if isinstance(cred_info, dict):
                    username = cred_info.get("username", "")
                    password = cred_info.get("password", "")
                else:
                    # Assume it's just a username
                    username = str(cred_info)
                    password = ""
                
                # Store in memory (always)
                self._network_credentials[server] = {
                    "username": username,
                    "password": password
                }
                
                # Store securely using keyring if available
                if HAS_KEYRING and password:
                    try:
                        keyring.set_password("cortex_cleaner_network", f"{server}:{username}", password)
                        logger.info(f"Credentials for {server} stored securely in keyring")
                    except Exception as e:
                        logger.warning(f"Could not store credentials in keyring: {e}")
                elif not HAS_KEYRING and password:
                    logger.info(f"Keyring not available - credentials for {server} stored in memory only")
                    
            except Exception as e:
                logger.error(f"Error storing credentials for {server}: {e}")
    
    def _get_stored_credentials(self, server: str) -> Optional[Dict[str, str]]:
        """Return in-memory credentials for a server, or None.
        
        Args:
                    server (str): The server parameter.
        
                Returns:
                    Optional[Dict[str, str]]: Dictionary mapping identifiers to status or values."""
        # First check memory cache
        if server in self._network_credentials:
            return self._network_credentials[server]
        
        # Try to retrieve from keyring
        try:
            # This is a simplified approach - in practice you'd need to store username separately
            # For now, return None if not in memory cache
            return None
        except Exception:
            return None
    
    def _attempt_network_connection(self, network_drive: NetworkDrive, credentials: Dict[str, str]) -> None:
        """Dispatch a network reconnect to the OS-specific connector.
        
        Args:
                    network_drive (NetworkDrive): The network drive parameter.
                    credentials (Dict[str, str]): The credentials parameter."""
        if platform.system().lower() == "windows":
            self._connect_windows_network_drive(network_drive, credentials)
        else:
            self._connect_unix_network_drive(network_drive, credentials)
    
    def _connect_windows_network_drive(self, network_drive: NetworkDrive, credentials: Dict[str, str]) -> None:
        """Run net use with credentials; records stderr on failure.
        
        Args:
                    network_drive (NetworkDrive): The network drive parameter.
                    credentials (Dict[str, str]): The credentials parameter."""
        try:
            import subprocess
            
            unc_path = f"\\\\{network_drive.server}\\{network_drive.share}"
            username = credentials.get("username", "")
            password = credentials.get("password", "")
            
            cmd = ["net", "use", unc_path]
            if username:
                cmd.extend([f"/user:{username}", password])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                network_drive.is_connected = True
            else:
                network_drive.last_error = result.stderr.strip()
                
        except Exception as e:
            network_drive.last_error = str(e)
    
    def _connect_unix_network_drive(self, network_drive: NetworkDrive, credentials: Dict[str, str]) -> None:
        # For now, just check if the mount point exists
        """Unix stub: refresh is_connected from path existence; no mount attempted.
        
        Args:
                    network_drive (NetworkDrive): The network drive parameter.
                    credentials (Dict[str, str]): The credentials parameter."""
        network_drive.is_connected = os.path.exists(network_drive.path)
    
    def monitor_drive_changes(self, callback: Callable[[str, str], None]) -> None:
        """Register a callback and start the polling thread on first use.
        
        Side effect: starts a daemon thread on first registration.
        
        Args:
                    callback (Callable[[str, str], None]): The callback parameter."""
        self._change_callbacks.append(callback)
        
        if not self._monitoring_active:
            self._start_monitoring()
    
    def _start_monitoring(self) -> None:
        """Start the daemon monitor thread once; no-op when already active.
        
        Side effect: starts a daemon thread."""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def _monitor_loop(self) -> None:
        """Poll partitions every 5 seconds and notify on attach or remove."""
        last_drives = set()
        
        while self._monitoring_active:
            try:
                current_drives = set()
                partitions = psutil.disk_partitions(all=True)
                
                for partition in partitions:
                    current_drives.add(partition.mountpoint)
                
                # Check for new drives
                new_drives = current_drives - last_drives
                for drive in new_drives:
                    self._notify_drive_change(drive, "connected")
                
                # Check for removed drives
                removed_drives = last_drives - current_drives
                for drive in removed_drives:
                    self._disconnected_drives.add(drive)
                    self._notify_drive_change(drive, "disconnected")
                
                last_drives = current_drives
                
            except Exception as e:
                logger.error(f"Error in drive monitoring: {e}")
            
            time.sleep(5)  # Check every 5 seconds
    
    def _notify_drive_change(self, drive_path: str, change_type: str) -> None:
        """Invoke drive-change callbacks; per-callback errors are logged.
        
        Args:
                    drive_path (str): Filesystem path to the target file or directory.
                    change_type (str): The change type parameter."""
        for callback in self._change_callbacks:
            try:
                callback(drive_path, change_type)
            except Exception as e:
                logger.error(f"Error in drive change callback: {e}")
    
    def handle_disconnected_drives(self, drive_id: str) -> Dict[str, Any]:
        """Recheck a dropped drive path and refresh the cache on reconnect.
        
        Args:
                    drive_id (str): The drive id parameter.
        
                Returns:
                    Dict[str, Any]: Dictionary mapping identifiers to status or values."""
        result = {
            "drive_id": drive_id,
            "was_disconnected": drive_id in self._disconnected_drives,
            "reconnected": False,
            "error": None
        }
        
        try:
            if os.path.exists(drive_id):
                result["reconnected"] = True
                self._disconnected_drives.discard(drive_id)
                
                partitions = psutil.disk_partitions(all=True)
                for partition in partitions:
                    if partition.mountpoint == drive_id:
                        self._drive_cache[drive_id] = self._create_drive_info(partition)
                        break
            else:
                result["error"] = "Drive still not accessible"
                
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def stop_monitoring(self) -> None:
        """Stop the polling thread and join with a timeout.
        
        Side effect: stops the monitor thread."""
        self._monitoring_active = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=10)
    
    def _parse_network_path(self, device_path: str) -> Tuple[str, str]:
        """Split a UNC or host:share device path into server and share.
        
        Args:
                    device_path (str): Filesystem path to the target file or directory.
        
                Returns:
                    Tuple[str, str]: Formatted string or path."""
        try:
            # Handle UNC paths (\\server\share)
            if device_path.startswith('\\\\'):
                parts = device_path[2:].split('\\', 1)
                if len(parts) >= 2:
                    return parts[0], parts[1]
                elif len(parts) == 1:
                    return parts[0], ""
            
            # Handle other network path formats
            if ':' in device_path:
                parts = device_path.split(':', 1)
                return parts[0], parts[1] if len(parts) > 1 else ""
        
        except Exception:
            pass
        
        return device_path, ""

class MultiDriveScanner:
    """Fan-out empty-file and empty-dir scans across drives and profiles with progress."""
    
    def __init__(self, config: Any = None):
        """Store config and initialize results, locks, callbacks, and sub-scanners.
        
        Args:
                    config (Any): The config parameter."""
        self.config = config
        self._scan_results: Dict[str, Any] = {}
        self._scan_lock = threading.Lock()
        self._progress_callbacks: List[Callable] = []
        self._current_progress = ScanProgress(0, 0, "", 0.0, datetime.now())
        self.user_scanner = MultiUserScanner(config)
        self.drive_manager = DriveManager(config)
    
    def detect_drives(self) -> List[DriveInfo]:
        """Detect drives via the DriveManager.
        
        Returns:
                    List[DriveInfo]: List of processed items or identifiers."""
        return self.drive_manager.detect_all_drives()
    
    def detect_all_drives(self) -> List[DriveInfo]:
        """List all partitions via psutil with OS-specific fallback.
        
        Returns:
                    List[DriveInfo]: List of processed items or identifiers."""
        drives = []
        system = platform.system().lower()
        
        try:
            # Get all disk partitions
            partitions = psutil.disk_partitions(all=True)
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    # Determine drive type
                    drive_type = self._get_drive_type(partition)
                    
                    label = self._get_drive_label(partition.mountpoint)
                    
                    drive_info = DriveInfo(
                        path=partition.mountpoint,
                        label=label,
                        filesystem=partition.fstype,
                        total_size=usage.total,
                        free_size=usage.free,
                        drive_type=drive_type,
                        is_ready=True,
                        mount_point=partition.mountpoint
                    )
                    
                    drives.append(drive_info)
                    
                except (PermissionError, OSError, psutil.Error):
                    # Drive not accessible or not ready
                    drive_info = DriveInfo(
                        path=partition.mountpoint,
                        label="",
                        filesystem=partition.fstype,
                        total_size=0,
                        free_size=0,
                        drive_type=self._get_drive_type(partition),
                        is_ready=False,
                        mount_point=partition.mountpoint
                    )
                    drives.append(drive_info)
        
        except Exception:
            # Fallback to basic detection
            if system == "windows":
                drives.extend(self._detect_windows_drives())
            else:
                drives.extend(self._detect_unix_drives())
        
        return drives
    
    def scan_multiple_drives(self, drives: List[str], parallel: bool = True, 
                           scanner_factory: Optional[Callable] = None) -> Dict[str, Any]:
        """Scan drives sequentially or in a thread pool with progress and error capture.
        
        Read-only scans; inaccessible drives yield error entries.
        
        Args:
                    drives (List[str]): The drives parameter.
                    parallel (bool): The parallel parameter.
                    scanner_factory (Optional[Callable]): The scanner factory parameter.
        
                Returns:
                    Dict[str, Any]: Dictionary mapping identifiers to status or values."""
        start_time = datetime.now()
        
        # Initialize progress tracking
        self._current_progress = ScanProgress(
            total_locations=len(drives),
            completed_locations=0,
            current_location="",
            current_progress=0.0,
            start_time=start_time
        )
        
        results = {}
        
        if not scanner_factory:
            def default_scanner_factory(path: str):
                """Build a Scanner for a path; lazy import avoids a cycle.

                Args:
                    path (str): Filesystem path to the target file or directory.
                """
                from cortex_unified.core.scanner import Scanner
                return Scanner(root_path=path)
            scanner_factory = default_scanner_factory
        
        try:
            if parallel and len(drives) > 1:
                results = self._scan_drives_parallel(drives, scanner_factory)
            else:
                results = self._scan_drives_sequential(drives, scanner_factory)
        
        except Exception as e:
            logger.error(f"Error in multi-drive scanning: {e}")
            self._current_progress.errors.append(f"Scanning error: {e}")
        
        scan_duration = (datetime.now() - start_time).total_seconds()
        
        aggregated = self.user_scanner.aggregate_results(results)
        aggregated.scan_duration = scan_duration
        
        with self._scan_lock:
            self._scan_results.update(results)
            self._scan_results["_aggregated"] = asdict(aggregated)
        
        return results
    
    def _scan_drives_parallel(self, drives: List[str], scanner_factory: Callable) -> Dict[str, Any]:
        """Scan drives in a thread pool with progress and error capture.
        
        Args:
                    drives (List[str]): The drives parameter.
                    scanner_factory (Callable): The scanner factory parameter.
        
                Returns:
                    Dict[str, Any]: Dictionary mapping identifiers to status or values."""
        results = {}
        max_workers = min(len(drives), os.cpu_count() or 4)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit scan tasks
            future_to_drive = {
                executor.submit(self._scan_single_drive_with_progress, drive, scanner_factory): drive
                for drive in drives
            }
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_drive):
                drive = future_to_drive[future]
                try:
                    result = future.result()
                    results[drive] = result
                    
                    with self._scan_lock:
                        self._current_progress.completed_locations += 1
                    
                    self._notify_progress(f"Completed scan of {drive}")
                    
                except Exception as e:
                    error_msg = f"Failed to scan {drive}: {e}"
                    results[drive] = {
                        "error": str(e), 
                        "empty_files": [], 
                        "empty_dirs": [],
                        "location_type": "drive"
                    }
                    self._current_progress.errors.append(error_msg)
                    self._notify_progress(error_msg)
        
        return results
    
    def _scan_drives_sequential(self, drives: List[str], scanner_factory: Callable) -> Dict[str, Any]:
        """Scan drives in order with progress and error capture.
        
        Args:
                    drives (List[str]): The drives parameter.
                    scanner_factory (Callable): The scanner factory parameter.
        
                Returns:
                    Dict[str, Any]: Dictionary mapping identifiers to status or values."""
        results = {}
        
        for i, drive in enumerate(drives):
            try:
                self._current_progress.current_location = drive
                self._current_progress.current_progress = 0.0
                
                result = self._scan_single_drive_with_progress(drive, scanner_factory)
                results[drive] = result
                
                self._current_progress.completed_locations = i + 1
                self._current_progress.current_progress = 100.0
                
                self._notify_progress(f"Completed scan of {drive}")
                
            except Exception as e:
                error_msg = f"Failed to scan {drive}: {e}"
                results[drive] = {
                    "error": str(e), 
                    "empty_files": [], 
                    "empty_dirs": [],
                    "location_type": "drive"
                }
                self._current_progress.errors.append(error_msg)
                self._notify_progress(error_msg)
        
        return results
    
    def _scan_single_drive_with_progress(self, drive_path: str, scanner_factory: Callable) -> Dict[str, Any]:
        """Scan one drive with an existence guard and disk-usage enrichment.
        
        Args:
                    drive_path (str): Filesystem path to the target file or directory.
                    scanner_factory (Callable): The scanner factory parameter.
        
                Returns:
                    Dict[str, Any]: Dictionary mapping identifiers to status or values."""
        try:
            if not os.path.exists(drive_path):
                return {
                    "error": "Drive not accessible",
                    "empty_files": [],
                    "empty_dirs": [],
                    "location_type": "drive"
                }
            
            scanner = scanner_factory(drive_path)
            
            # Perform scan
            empty_files, empty_dirs = scanner.scan()
            
            # Get additional drive information
            drive_info = None
            try:
                usage = psutil.disk_usage(drive_path)
                drive_info = {
                    "total_size": usage.total,
                    "free_size": usage.free,
                    "used_size": usage.used
                }
            except Exception:
                pass
            
            result = {
                "empty_files": [str(f) for f in empty_files],
                "empty_dirs": [str(d) for d in empty_dirs],
                "stats": scanner.get_stats(),
                "location_type": "drive",
                "drive_info": drive_info
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error scanning drive {drive_path}: {e}")
            raise
    
    def _scan_single_drive(self, drive_path: str, scanner_factory: Callable) -> Dict[str, Any]:
        """Scan one drive without progress bookkeeping.
        
        Args:
                    drive_path (str): Filesystem path to the target file or directory.
                    scanner_factory (Callable): The scanner factory parameter.
        
                Returns:
                    Dict[str, Any]: Dictionary mapping identifiers to status or values."""
        scanner = scanner_factory(drive_path)
        empty_files, empty_dirs = scanner.scan()
        
        return {
            "empty_files": [str(f) for f in empty_files],
            "empty_dirs": [str(d) for d in empty_dirs],
            "stats": scanner.get_stats()
        }
    
    def handle_network_drives(self, credentials: Dict[str, str] = None) -> List[NetworkDrive]:
        """Delegate network-drive handling to the DriveManager.
        
        Args:
                    credentials (Dict[str, str]): The credentials parameter.
        
                Returns:
                    List[NetworkDrive]: List of processed items or identifiers."""
        return self.drive_manager.handle_network_drives(credentials)
    
    def monitor_drive_changes(self, callback: Callable[[str, str], None]) -> None:
        """Delegate drive-change monitoring to the DriveManager.
        
        Args:
                    callback (Callable[[str, str], None]): The callback parameter."""
        self.drive_manager.monitor_drive_changes(callback)
    
    def handle_disconnected_drives(self, drive_id: str) -> Dict[str, Any]:
        """Delegate disconnected-drive recovery to the DriveManager.
        
        Args:
                    drive_id (str): The drive id parameter.
        
                Returns:
                    Dict[str, Any]: Dictionary mapping identifiers to status or values."""
        return self.drive_manager.handle_disconnected_drives(drive_id)
    
    def scan_user_profiles(self, admin_mode: bool = False) -> Dict[str, Any]:
        """Scan all detected profiles with progress tracking and aggregation.
        
        Read-only scans; admin may be required for other users profiles.
        
        Args:
                    admin_mode (bool): The admin mode parameter.
        
                Returns:
                    Dict[str, Any]: Dictionary mapping identifiers to status or values."""
        start_time = datetime.now()
        user_profiles = self.user_scanner.detect_user_profiles()
        
        # Initialize progress tracking
        self._current_progress = ScanProgress(
            total_locations=len(user_profiles),
            completed_locations=0,
            current_location="",
            current_progress=0.0,
            start_time=start_time
        )
        
        results = {}
        
        for i, profile in enumerate(user_profiles):
            self._current_progress.current_location = f"User: {profile.username}"
            self._current_progress.current_progress = 0.0
            
            try:
                result = self.user_scanner.scan_user_profile(profile)
                results[profile.username] = result
                
                self._current_progress.completed_locations = i + 1
                self._current_progress.current_progress = 100.0
                
                self._notify_progress(f"Completed scan of user profile: {profile.username}")
                
            except Exception as e:
                error_msg = f"Failed to scan user profile {profile.username}: {e}"
                results[profile.username] = {
                    "error": str(e),
                    "empty_files": [],
                    "empty_dirs": [],
                    "location_type": "user_profile"
                }
                self._current_progress.errors.append(error_msg)
                self._notify_progress(error_msg)
        
        # Calculate final duration and create aggregated result
        scan_duration = (datetime.now() - start_time).total_seconds()
        aggregated = self.user_scanner.aggregate_results(results)
        aggregated.scan_duration = scan_duration
        
        with self._scan_lock:
            self._scan_results.update(results)
            self._scan_results["_aggregated"] = asdict(aggregated)
        
        return results
    
    def detect_user_profiles(self, admin_mode: bool = False) -> List[UserProfile]:
        """Delegate profile enumeration to the MultiUserScanner.
        
        Args:
                    admin_mode (bool): The admin mode parameter.
        
                Returns:
                    List[UserProfile]: List of processed items or identifiers."""
        return self.user_scanner.detect_user_profiles()
    
    def add_progress_callback(self, callback: Callable[[str], None]) -> None:
        """Register a string-message progress callback.
        
        Args:
                    callback (Callable[[str], None]): The callback parameter."""
        self._progress_callbacks.append(callback)
    
    def _notify_progress(self, message: str) -> None:
        """Fan-out a message to callbacks and log it; callback errors are ignored.
        
        Args:
                    message (str): Informational or progress status message."""
        # Update progress callbacks with message
        for callback in self._progress_callbacks:
            try:
                callback(message)
            except Exception:
                # Ignore callback errors
                pass
        
        # Log progress
        logger.info(message)
    
    def get_scan_progress(self) -> ScanProgress:
        """Return the current ScanProgress snapshot under lock.
        
        Returns:
                    ScanProgress: Result of the operation."""
        with self._scan_lock:
            return self._current_progress
    
    def get_scan_results(self) -> Dict[str, Any]:
        """Return a copy of per-location results under lock.
        
        Returns:
                    Dict[str, Any]: Dictionary mapping identifiers to status or values."""
        with self._scan_lock:
            return self._scan_results.copy()
    
    def get_aggregated_results(self) -> Optional[AggregatedResult]:
        """Return the cached AggregatedResult, or None before any scan.
        
        Returns:
                    Optional[AggregatedResult]: Result of the operation."""
        with self._scan_lock:
            aggregated_data = self._scan_results.get("_aggregated")
            if aggregated_data:
                return AggregatedResult(**aggregated_data)
            return None
    
    def clear_results(self) -> None:
        """Clear cached results and reset progress under lock.
        
        Side effect: clears in-memory caches."""
        with self._scan_lock:
            self._scan_results.clear()
            self._current_progress = ScanProgress(0, 0, "", 0.0, datetime.now())
    
    def scan_multiple_locations(self, locations: List[Dict[str, Any]], 
                              parallel: bool = True) -> Dict[str, Any]:
        """Scan each location in `locations` and return per-location results (parallel flag is ignored; locations scanned sequentially)."""
        start_time = datetime.now()
        
        # Initialize progress tracking
        self._current_progress = ScanProgress(
            total_locations=len(locations),
            completed_locations=0,
            current_location="",
            current_progress=0.0,
            start_time=start_time
        )
        
        results = {}
        
        try:
            for i, location in enumerate(locations):
                location_type = location.get("type", "unknown")
                location_path = location.get("path", "")
                
                self._current_progress.current_location = f"{location_type}: {location_path}"
                self._current_progress.current_progress = 0.0
                
                try:
                    if location_type == "drive":
                        result = self._scan_single_drive_with_progress(
                            location_path, 
                            location.get("scanner_factory")
                        )
                    elif location_type == "user_profile":
                        profile = UserProfile(**location.get("profile_data", {}))
                        result = self.user_scanner.scan_user_profile(profile)
                    else:
                        result = {"error": f"Unknown location type: {location_type}"}
                    
                    results[location_path] = result
                    
                    self._current_progress.completed_locations = i + 1
                    self._current_progress.current_progress = 100.0
                    
                    self._notify_progress(f"Completed scan of {location_type}: {location_path}")
                    
                except Exception as e:
                    error_msg = f"Failed to scan {location_type} {location_path}: {e}"
                    results[location_path] = {
                        "error": str(e),
                        "empty_files": [],
                        "empty_dirs": [],
                        "location_type": location_type
                    }
                    self._current_progress.errors.append(error_msg)
                    self._notify_progress(error_msg)
        
        except Exception as e:
            logger.error(f"Error in multi-location scanning: {e}")
            self._current_progress.errors.append(f"Scanning error: {e}")
        
        # Calculate final duration and create aggregated result
        scan_duration = (datetime.now() - start_time).total_seconds()
        aggregated = self.user_scanner.aggregate_results(results)
        aggregated.scan_duration = scan_duration
        
        with self._scan_lock:
            self._scan_results.update(results)
            self._scan_results["_aggregated"] = asdict(aggregated)
        
        return results
    
    def stop_monitoring(self) -> None:
        """Stop DriveManager monitoring."""
        self.drive_manager.stop_monitoring()