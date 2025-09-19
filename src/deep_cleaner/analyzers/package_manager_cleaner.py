"""Package manager cleaner for Deep Cleaner."""

import json
import os
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
import logging

from ..config import Config
from ..utils import normalize_path


@dataclass
class Package:
    """Represents a package in a package manager."""
    name: str
    version: str
    size: int
    install_date: Optional[datetime] = None
    dependencies: List[str] = None
    is_orphaned: bool = False
    manager: str = ""
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class PackageManager:
    """Represents a package manager on the system."""
    name: str
    executable: str
    version: str
    cache_path: Optional[Path] = None
    config_path: Optional[Path] = None
    is_available: bool = False
    health_status: str = "unknown"


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    success: bool
    files_removed: int
    space_freed: int
    errors: List[str] = None
    backup_path: Optional[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class HealthStatus:
    """Health status of a package manager."""
    is_healthy: bool
    issues: List[str] = None
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.recommendations is None:
            self.recommendations = []


class PackageManagerCleaner:
    """Enhanced package manager cleaner with multi-platform support."""
    
    def __init__(self, config: Config = None):
        """Initialize package manager cleaner."""
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
        
        # Package manager definitions
        self.package_managers = {
            "pip": {
                "executable": "pip",
                "cache_commands": ["cache", "dir"],
                "list_command": ["list"],
                "cache_clean_command": ["cache", "purge"],
                "platforms": ["windows", "linux", "darwin"]
            },
            "npm": {
                "executable": "npm",
                "cache_commands": ["config", "get", "cache"],
                "list_command": ["list", "-g", "--depth=0"],
                "cache_clean_command": ["cache", "clean", "--force"],
                "platforms": ["windows", "linux", "darwin"]
            },
            "yarn": {
                "executable": "yarn",
                "cache_commands": ["cache", "dir"],
                "list_command": ["global", "list"],
                "cache_clean_command": ["cache", "clean"],
                "platforms": ["windows", "linux", "darwin"]
            },
            "conda": {
                "executable": "conda",
                "cache_commands": ["info", "--json"],
                "list_command": ["list"],
                "cache_clean_command": ["clean", "--all", "-y"],
                "platforms": ["windows", "linux", "darwin"]
            },
            "apt": {
                "executable": "apt",
                "cache_commands": ["config", "dump"],
                "list_command": ["list", "--installed"],
                "cache_clean_command": ["clean"],
                "platforms": ["linux"]
            },
            "dnf": {
                "executable": "dnf",
                "cache_commands": ["config-manager", "--dump"],
                "list_command": ["list", "installed"],
                "cache_clean_command": ["clean", "all"],
                "platforms": ["linux"]
            },
            "pacman": {
                "executable": "pacman",
                "cache_commands": ["-Sc"],
                "list_command": ["-Q"],
                "cache_clean_command": ["-Scc", "--noconfirm"],
                "platforms": ["linux"]
            },
            "brew": {
                "executable": "brew",
                "cache_commands": ["--cache"],
                "list_command": ["list"],
                "cache_clean_command": ["cleanup", "-s"],
                "platforms": ["darwin", "linux"]
            },
            "chocolatey": {
                "executable": "choco",
                "cache_commands": ["config", "get", "cacheLocation"],
                "list_command": ["list", "--local-only"],
                "cache_clean_command": ["cache", "clean"],
                "platforms": ["windows"]
            }
        }
        
        self.detected_managers: List[PackageManager] = []
        self.backup_dir = Path.home() / ".deep_cleaner_backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def detect_package_managers(self) -> List[PackageManager]:
        """Detect available package managers on the system."""
        self.detected_managers = []
        current_platform = platform.system().lower()
        
        for name, config in self.package_managers.items():
            # Check if package manager is supported on current platform
            if current_platform not in config["platforms"]:
                continue
            
            try:
                # Check if executable exists
                executable_path = shutil.which(config["executable"])
                if not executable_path:
                    continue
                
                # Try to get version
                version = self._get_package_manager_version(name, config["executable"])
                if not version:
                    continue
                
                # Get cache path
                cache_path = self._get_cache_path(name, config)
                
                # Create PackageManager object
                manager = PackageManager(
                    name=name,
                    executable=executable_path,
                    version=version,
                    cache_path=cache_path,
                    is_available=True,
                    health_status="healthy"
                )
                
                self.detected_managers.append(manager)
                self.logger.info(f"Detected package manager: {name} v{version}")
                
            except Exception as e:
                self.logger.debug(f"Failed to detect {name}: {e}")
                continue
        
        return self.detected_managers
    
    def _get_package_manager_version(self, name: str, executable: str) -> Optional[str]:
        """Get version of a package manager."""
        try:
            if name == "pip":
                result = subprocess.run([executable, "--version"], 
                                      capture_output=True, text=True, timeout=10)
            elif name in ["npm", "yarn"]:
                result = subprocess.run([executable, "--version"], 
                                      capture_output=True, text=True, timeout=10)
            elif name == "conda":
                result = subprocess.run([executable, "--version"], 
                                      capture_output=True, text=True, timeout=10)
            elif name in ["apt", "dnf"]:
                result = subprocess.run([executable, "--version"], 
                                      capture_output=True, text=True, timeout=10)
            elif name == "pacman":
                result = subprocess.run([executable, "--version"], 
                                      capture_output=True, text=True, timeout=10)
            elif name == "brew":
                result = subprocess.run([executable, "--version"], 
                                      capture_output=True, text=True, timeout=10)
            elif name == "chocolatey":
                result = subprocess.run([executable, "--version"], 
                                      capture_output=True, text=True, timeout=10)
            else:
                return None
            
            if result.returncode == 0:
                # Extract version from output
                output = result.stdout.strip()
                if name == "pip":
                    # pip 21.3.1 from /usr/lib/python3/dist-packages/pip (python 3.9)
                    parts = output.split()
                    if len(parts) >= 2:
                        return parts[1]
                elif name in ["npm", "yarn", "conda"]:
                    return output
                elif name in ["apt", "dnf", "pacman", "brew"]:
                    # Extract version from first line
                    first_line = output.split('\n')[0]
                    parts = first_line.split()
                    for part in parts:
                        if part[0].isdigit():
                            return part
                elif name == "chocolatey":
                    return output
            
        except Exception as e:
            self.logger.debug(f"Failed to get version for {name}: {e}")
        
        return None
    
    def _get_cache_path(self, name: str, config: Dict) -> Optional[Path]:
        """Get cache directory path for a package manager."""
        try:
            cache_commands = config.get("cache_commands", [])
            if not cache_commands:
                return None
            
            executable = config["executable"]
            
            if name == "pip":
                result = subprocess.run([executable] + cache_commands, 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return Path(result.stdout.strip())
            
            elif name == "npm":
                result = subprocess.run([executable] + cache_commands, 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return Path(result.stdout.strip())
            
            elif name == "yarn":
                result = subprocess.run([executable] + cache_commands, 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return Path(result.stdout.strip())
            
            elif name == "conda":
                result = subprocess.run([executable] + cache_commands, 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    info = json.loads(result.stdout)
                    pkgs_dirs = info.get("pkgs_dirs", [])
                    if pkgs_dirs:
                        return Path(pkgs_dirs[0])
            
            elif name == "brew":
                result = subprocess.run([executable] + cache_commands, 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return Path(result.stdout.strip())
            
            elif name == "chocolatey":
                result = subprocess.run([executable] + cache_commands, 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return Path(result.stdout.strip())
            
        except Exception as e:
            self.logger.debug(f"Failed to get cache path for {name}: {e}")
        
        return None
    
    def clean_pip_cache(self, keep_recent_days: int = 7) -> CleanupResult:
        """Clean pip cache with age-based filtering."""
        pip_manager = self._get_manager_by_name("pip")
        if not pip_manager or not pip_manager.cache_path:
            return CleanupResult(False, 0, 0, ["Pip not available or cache path not found"])
        
        try:
            # Create backup of pip configuration
            backup_path = self._backup_package_lists(["pip"])
            
            files_removed = 0
            space_freed = 0
            errors = []
            
            cache_path = pip_manager.cache_path
            if not cache_path.exists():
                return CleanupResult(False, 0, 0, ["Pip cache directory does not exist"])
            
            cutoff_date = datetime.now() - timedelta(days=keep_recent_days)
            
            # Walk through cache directory
            for root, dirs, files in os.walk(cache_path):
                for file in files:
                    file_path = Path(root) / file
                    try:
                        # Check file age
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cutoff_date:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            files_removed += 1
                            space_freed += file_size
                    except Exception as e:
                        errors.append(f"Failed to remove {file_path}: {e}")
            
            return CleanupResult(
                success=True,
                files_removed=files_removed,
                space_freed=space_freed,
                errors=errors,
                backup_path=backup_path.get("pip")
            )
            
        except Exception as e:
            return CleanupResult(False, 0, 0, [f"Failed to clean pip cache: {e}"])
    
    def clean_npm_cache(self, verify_integrity: bool = True) -> CleanupResult:
        """Clean npm cache with integrity verification."""
        npm_manager = self._get_manager_by_name("npm")
        if not npm_manager:
            return CleanupResult(False, 0, 0, ["NPM not available"])
        
        try:
            # Create backup
            backup_path = self._backup_package_lists(["npm"])
            
            # Get cache size before cleaning
            cache_size_before = self._get_cache_size(npm_manager.cache_path)
            
            # Clean cache
            result = subprocess.run([npm_manager.executable, "cache", "clean", "--force"], 
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                return CleanupResult(False, 0, 0, [f"NPM cache clean failed: {result.stderr}"])
            
            # Verify integrity if requested
            if verify_integrity:
                verify_result = subprocess.run([npm_manager.executable, "cache", "verify"], 
                                             capture_output=True, text=True, timeout=60)
                if verify_result.returncode != 0:
                    return CleanupResult(False, 0, 0, [f"NPM cache verification failed: {verify_result.stderr}"])
            
            # Get cache size after cleaning
            cache_size_after = self._get_cache_size(npm_manager.cache_path)
            space_freed = cache_size_before - cache_size_after
            
            return CleanupResult(
                success=True,
                files_removed=1,  # We don't know exact file count
                space_freed=space_freed,
                backup_path=backup_path.get("npm")
            )
            
        except Exception as e:
            return CleanupResult(False, 0, 0, [f"Failed to clean npm cache: {e}"])
    
    def clean_system_packages(self, package_manager: str) -> CleanupResult:
        """Clean system package manager caches."""
        manager = self._get_manager_by_name(package_manager)
        if not manager:
            return CleanupResult(False, 0, 0, [f"{package_manager} not available"])
        
        try:
            # Create backup
            backup_path = self._backup_package_lists([package_manager])
            
            # Get cache size before cleaning
            cache_size_before = self._get_cache_size(manager.cache_path)
            
            # Execute clean command
            config = self.package_managers[package_manager]
            clean_command = [manager.executable] + config["cache_clean_command"]
            
            result = subprocess.run(clean_command, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                return CleanupResult(False, 0, 0, [f"{package_manager} clean failed: {result.stderr}"])
            
            # Get cache size after cleaning
            cache_size_after = self._get_cache_size(manager.cache_path)
            space_freed = cache_size_before - cache_size_after
            
            return CleanupResult(
                success=True,
                files_removed=1,  # We don't know exact file count
                space_freed=space_freed,
                backup_path=backup_path.get(package_manager)
            )
            
        except Exception as e:
            return CleanupResult(False, 0, 0, [f"Failed to clean {package_manager}: {e}"])
    
    def find_orphaned_packages(self, package_manager: str) -> List[Package]:
        """Find orphaned packages that are no longer needed."""
        manager = self._get_manager_by_name(package_manager)
        if not manager:
            return []
        
        try:
            if package_manager == "pip":
                return self._find_pip_orphaned_packages(manager)
            elif package_manager == "npm":
                return self._find_npm_orphaned_packages(manager)
            elif package_manager == "apt":
                return self._find_apt_orphaned_packages(manager)
            elif package_manager == "dnf":
                return self._find_dnf_orphaned_packages(manager)
            elif package_manager == "pacman":
                return self._find_pacman_orphaned_packages(manager)
            elif package_manager == "brew":
                return self._find_brew_orphaned_packages(manager)
            else:
                self.logger.warning(f"Orphaned package detection not implemented for {package_manager}")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to find orphaned packages for {package_manager}: {e}")
            return []
    
    def _find_pip_orphaned_packages(self, manager: PackageManager) -> List[Package]:
        """Find orphaned pip packages."""
        try:
            # Get installed packages
            result = subprocess.run([manager.executable, "list", "--format=json"], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return []
            
            packages_data = json.loads(result.stdout)
            packages = []
            
            for pkg_data in packages_data:
                # For pip, we consider packages orphaned if they're not in requirements files
                # This is a simplified heuristic
                package = Package(
                    name=pkg_data["name"],
                    version=pkg_data["version"],
                    size=0,  # Pip doesn't provide size info easily
                    manager="pip",
                    is_orphaned=False  # Would need more sophisticated analysis
                )
                packages.append(package)
            
            return packages
            
        except Exception as e:
            self.logger.error(f"Failed to find pip orphaned packages: {e}")
            return []
    
    def _find_npm_orphaned_packages(self, manager: PackageManager) -> List[Package]:
        """Find orphaned npm packages."""
        try:
            # Use npm ls to find packages not required by others
            result = subprocess.run([manager.executable, "ls", "--json", "--depth=0"], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return []
            
            packages_data = json.loads(result.stdout)
            packages = []
            
            # This would need more sophisticated dependency analysis
            # For now, return empty list as placeholder
            return packages
            
        except Exception as e:
            self.logger.error(f"Failed to find npm orphaned packages: {e}")
            return []
    
    def _find_apt_orphaned_packages(self, manager: PackageManager) -> List[Package]:
        """Find orphaned apt packages."""
        try:
            # Use apt-mark to find auto-installed packages that are no longer needed
            result = subprocess.run(["apt-mark", "showauto"], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return []
            
            auto_packages = result.stdout.strip().split('\n')
            
            # Check which ones are actually orphaned
            orphaned_result = subprocess.run(["apt", "autoremove", "--dry-run"], 
                                           capture_output=True, text=True, timeout=30)
            
            packages = []
            if orphaned_result.returncode == 0:
                # Parse dry-run output to find packages that would be removed
                lines = orphaned_result.stdout.split('\n')
                for line in lines:
                    if "The following packages will be REMOVED:" in line:
                        # Next lines contain package names
                        continue
                    # This would need more parsing logic
            
            return packages
            
        except Exception as e:
            self.logger.error(f"Failed to find apt orphaned packages: {e}")
            return []
    
    def _find_dnf_orphaned_packages(self, manager: PackageManager) -> List[Package]:
        """Find orphaned dnf packages."""
        try:
            # Use dnf to find leaf packages
            result = subprocess.run([manager.executable, "leaves"], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return []
            
            packages = []
            # Parse output and create Package objects
            # This would need implementation based on dnf output format
            
            return packages
            
        except Exception as e:
            self.logger.error(f"Failed to find dnf orphaned packages: {e}")
            return []
    
    def _find_pacman_orphaned_packages(self, manager: PackageManager) -> List[Package]:
        """Find orphaned pacman packages."""
        try:
            # Use pacman to find orphaned packages
            result = subprocess.run([manager.executable, "-Qtdq"], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return []
            
            orphaned_names = result.stdout.strip().split('\n')
            packages = []
            
            for name in orphaned_names:
                if name.strip():
                    package = Package(
                        name=name.strip(),
                        version="unknown",
                        size=0,
                        manager="pacman",
                        is_orphaned=True
                    )
                    packages.append(package)
            
            return packages
            
        except Exception as e:
            self.logger.error(f"Failed to find pacman orphaned packages: {e}")
            return []
    
    def _find_brew_orphaned_packages(self, manager: PackageManager) -> List[Package]:
        """Find orphaned brew packages."""
        try:
            # Use brew to find unused dependencies
            result = subprocess.run([manager.executable, "leaves"], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return []
            
            packages = []
            # Parse output and create Package objects
            # This would need implementation based on brew output format
            
            return packages
            
        except Exception as e:
            self.logger.error(f"Failed to find brew orphaned packages: {e}")
            return []
    
    def backup_package_lists(self) -> Dict[str, str]:
        """Create backups of package lists for all detected managers."""
        return self._backup_package_lists([manager.name for manager in self.detected_managers])
    
    def _backup_package_lists(self, managers: List[str]) -> Dict[str, str]:
        """Create backups of package lists for specified managers."""
        backups = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for manager_name in managers:
            manager = self._get_manager_by_name(manager_name)
            if not manager:
                continue
            
            try:
                backup_file = self.backup_dir / f"{manager_name}_packages_{timestamp}.txt"
                
                # Get package list
                config = self.package_managers[manager_name]
                list_command = [manager.executable] + config["list_command"]
                
                result = subprocess.run(list_command, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    with open(backup_file, 'w', encoding='utf-8') as f:
                        f.write(f"# Package list backup for {manager_name}\n")
                        f.write(f"# Created: {datetime.now().isoformat()}\n")
                        f.write(f"# Command: {' '.join(list_command)}\n\n")
                        f.write(result.stdout)
                    
                    backups[manager_name] = str(backup_file)
                    self.logger.info(f"Created backup for {manager_name}: {backup_file}")
                
            except Exception as e:
                self.logger.error(f"Failed to backup {manager_name} package list: {e}")
        
        return backups
    
    def verify_package_manager_health(self, package_manager: str) -> HealthStatus:
        """Verify package manager health after operations."""
        manager = self._get_manager_by_name(package_manager)
        if not manager:
            return HealthStatus(False, ["Package manager not found"])
        
        issues = []
        recommendations = []
        
        try:
            # Test basic functionality
            config = self.package_managers[package_manager]
            test_command = [manager.executable] + config["list_command"]
            
            result = subprocess.run(test_command, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                issues.append(f"Basic command failed: {result.stderr}")
            
            # Check cache directory accessibility
            if manager.cache_path and manager.cache_path.exists():
                try:
                    # Try to create a test file in cache directory
                    test_file = manager.cache_path / ".health_check"
                    test_file.touch()
                    test_file.unlink()
                except Exception as e:
                    issues.append(f"Cache directory not writable: {e}")
            
            # Package manager specific health checks
            if package_manager == "npm":
                # Check npm doctor
                doctor_result = subprocess.run([manager.executable, "doctor"], 
                                             capture_output=True, text=True, timeout=60)
                if doctor_result.returncode != 0:
                    issues.append("npm doctor reported issues")
                    recommendations.append("Run 'npm doctor' for detailed diagnostics")
            
            elif package_manager == "pip":
                # Check pip check
                check_result = subprocess.run([manager.executable, "check"], 
                                            capture_output=True, text=True, timeout=30)
                if check_result.returncode != 0:
                    issues.append("pip check found dependency conflicts")
                    recommendations.append("Run 'pip check' to see dependency issues")
            
        except Exception as e:
            issues.append(f"Health check failed: {e}")
        
        is_healthy = len(issues) == 0
        return HealthStatus(is_healthy, issues, recommendations)
    
    def _get_manager_by_name(self, name: str) -> Optional[PackageManager]:
        """Get package manager by name."""
        for manager in self.detected_managers:
            if manager.name == name:
                return manager
        return None
    
    def _get_cache_size(self, cache_path: Optional[Path]) -> int:
        """Get total size of cache directory."""
        if not cache_path or not cache_path.exists():
            return 0
        
        total_size = 0
        try:
            for root, dirs, files in os.walk(cache_path):
                for file in files:
                    file_path = Path(root) / file
                    try:
                        total_size += file_path.stat().st_size
                    except Exception:
                        continue
        except Exception:
            pass
        
        return total_size
    
    def get_stats(self) -> Dict[str, any]:
        """Get statistics about detected package managers."""
        stats = {
            "detected_managers": len(self.detected_managers),
            "managers": {}
        }
        
        for manager in self.detected_managers:
            cache_size = self._get_cache_size(manager.cache_path)
            stats["managers"][manager.name] = {
                "version": manager.version,
                "cache_path": str(manager.cache_path) if manager.cache_path else None,
                "cache_size": cache_size,
                "cache_size_human": self._format_bytes(cache_size),
                "is_healthy": manager.health_status == "healthy"
            }
        
        return stats
    
    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes into human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"