"""Docker cleaner for Cortex Cleaner."""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Union, Any
from dataclasses import dataclass
from datetime import datetime
import logging

try:
    import docker
    from docker.errors import DockerException, APIError, NotFound
    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False

from cortex_unified.core.utils import normalize_path
from cortex_unified.core.config import Config

@dataclass
class DockerImage:
    """Docker image data model."""
    id: str
    repository: str
    tag: str
    size: int
    created: datetime
    is_dangling: bool
    
    def __str__(self):
        return f"{self.repository}:{self.tag} ({self.id[:12]})"

@dataclass
class DockerContainer:
    """Docker container data model."""
    id: str
    name: str
    image: str
    status: str
    size: int
    created: datetime
    
    def __str__(self):
        return f"{self.name} ({self.id[:12]})"

@dataclass
class DockerVolume:
    """Docker volume data model."""
    name: str
    driver: str
    size: int
    mount_point: str
    is_orphaned: bool
    
    def __str__(self):
        return f"{self.name} ({self.driver})"

@dataclass
class DockerNetwork:
    """Docker network data model."""
    id: str
    name: str
    driver: str
    is_unused: bool
    
    def __str__(self):
        return f"{self.name} ({self.driver})"

@dataclass
class CleanupResult:
    """Docker cleanup result data model."""
    images_removed: int
    containers_removed: int
    volumes_removed: int
    networks_removed: int
    space_freed: int
    errors: List[str]
    
    @property
    def total_removed(self) -> int:
        return self.images_removed + self.containers_removed + self.volumes_removed + self.networks_removed

class DockerCleaner:
    """Docker resource cleaner."""
    
    def __init__(self, config: Config = None):
        """Initialize Docker cleaner."""
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
        self._client = None
        self._stats = {
            'images_scanned': 0,
            'containers_scanned': 0,
            'volumes_scanned': 0,
            'networks_scanned': 0,
            'total_size': 0,
            'errors': []
        }
    
    @property
    def client(self):
        """Get Docker client with lazy initialization."""
        if self._client is None:
            if not HAS_DOCKER:
                raise ImportError("Docker SDK not available. Install with: pip install docker")
            
            try:
                self._client = docker.from_env()
                # Test connection
                self._client.ping()
            except Exception as e:
                self.logger.error(f"Failed to connect to Docker: {e}")
                raise
        
        return self._client
    
    def is_docker_available(self) -> bool:
        """Check if Docker is available and running."""
        if not HAS_DOCKER:
            self.logger.warning("Docker SDK not installed")
            return False
        
        try:
            client = docker.from_env()
            client.ping()
            return True
        except DockerException as e:
            self.logger.warning(f"Docker daemon not available: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error checking Docker availability: {e}")
            return False
    
    def scan_unused_images(self) -> List[DockerImage]:
        """Scan for unused Docker images including dangling images."""
        if not self.is_docker_available():
            return []
        
        unused_images = []
        
        try:
            # Get all images
            images = self.client.images.list(all=True)
            self._stats['images_scanned'] = len(images)
            
            for image in images:
                try:
                    # Check if image is dangling (no repository/tag)
                    is_dangling = not image.tags or image.tags == ['<none>:<none>']
                    
                    # Get image details
                    repository = '<none>'
                    tag = '<none>'
                    if image.tags:
                        repo_tag = image.tags[0].split(':')
                        repository = repo_tag[0] if len(repo_tag) > 0 else '<none>'
                        tag = repo_tag[1] if len(repo_tag) > 1 else '<none>'
                    
                    # Get creation date
                    created = datetime.fromisoformat(image.attrs['Created'].replace('Z', '+00:00'))
                    
                    # Get size
                    size = image.attrs.get('Size', 0)
                    self._stats['total_size'] += size
                    
                    # Check if image is unused (not referenced by any container)
                    is_unused = self._is_image_unused(image.id)
                    
                    if is_dangling or is_unused:
                        docker_image = DockerImage(
                            id=image.id,
                            repository=repository,
                            tag=tag,
                            size=size,
                            created=created,
                            is_dangling=is_dangling
                        )
                        unused_images.append(docker_image)
                
                except Exception as e:
                    error_msg = f"Error processing image {image.id[:12]}: {e}"
                    self.logger.error(error_msg)
                    self._stats['errors'].append(error_msg)
        
        except Exception as e:
            error_msg = f"Error scanning Docker images: {e}"
            self.logger.error(error_msg)
            self._stats['errors'].append(error_msg)
        
        return unused_images
    
    def scan_stopped_containers(self) -> List[DockerContainer]:
        """Scan for stopped Docker containers."""
        if not self.is_docker_available():
            return []
        
        stopped_containers = []
        
        try:
            # Get all containers (including stopped ones)
            containers = self.client.containers.list(all=True)
            self._stats['containers_scanned'] = len(containers)
            
            for container in containers:
                try:
                    # Only include stopped containers
                    if container.status != 'running':
                        # Calculate container size
                        size = self._get_container_size(container)
                        self._stats['total_size'] += size
                        
                        # Get creation date
                        created = datetime.fromisoformat(container.attrs['Created'].replace('Z', '+00:00'))
                        
                        docker_container = DockerContainer(
                            id=container.id,
                            name=container.name,
                            image=container.image.tags[0] if container.image.tags else container.image.id[:12],
                            status=container.status,
                            size=size,
                            created=created
                        )
                        stopped_containers.append(docker_container)
                
                except Exception as e:
                    error_msg = f"Error processing container {container.id[:12]}: {e}"
                    self.logger.error(error_msg)
                    self._stats['errors'].append(error_msg)
        
        except Exception as e:
            error_msg = f"Error scanning Docker containers: {e}"
            self.logger.error(error_msg)
            self._stats['errors'].append(error_msg)
        
        return stopped_containers
    
    def scan_unused_volumes(self) -> List[DockerVolume]:
        """Scan for unused Docker volumes."""
        if not self.is_docker_available():
            return []
        
        unused_volumes = []
        
        try:
            # Get all volumes
            volumes = self.client.volumes.list()
            self._stats['volumes_scanned'] = len(volumes)
            
            for volume in volumes:
                try:
                    # Check if volume is orphaned (not used by any container)
                    is_orphaned = self._is_volume_orphaned(volume.name)
                    
                    if is_orphaned:
                        # Get volume size (approximate)
                        size = self._get_volume_size(volume)
                        self._stats['total_size'] += size
                        
                        docker_volume = DockerVolume(
                            name=volume.name,
                            driver=volume.attrs.get('Driver', 'unknown'),
                            size=size,
                            mount_point=volume.attrs.get('Mountpoint', ''),
                            is_orphaned=is_orphaned
                        )
                        unused_volumes.append(docker_volume)
                
                except Exception as e:
                    error_msg = f"Error processing volume {volume.name}: {e}"
                    self.logger.error(error_msg)
                    self._stats['errors'].append(error_msg)
        
        except Exception as e:
            error_msg = f"Error scanning Docker volumes: {e}"
            self.logger.error(error_msg)
            self._stats['errors'].append(error_msg)
        
        return unused_volumes
    
    def scan_unused_networks(self) -> List[DockerNetwork]:
        """Scan for unused Docker networks."""
        if not self.is_docker_available():
            return []
        
        unused_networks = []
        
        try:
            # Get all networks
            networks = self.client.networks.list()
            self._stats['networks_scanned'] = len(networks)
            
            for network in networks:
                try:
                    # Skip default networks
                    if network.name in ['bridge', 'host', 'none']:
                        continue
                    
                    # Check if network is unused
                    is_unused = self._is_network_unused(network.id)
                    
                    if is_unused:
                        docker_network = DockerNetwork(
                            id=network.id,
                            name=network.name,
                            driver=network.attrs.get('Driver', 'unknown'),
                            is_unused=is_unused
                        )
                        unused_networks.append(docker_network)
                
                except Exception as e:
                    error_msg = f"Error processing network {network.name}: {e}"
                    self.logger.error(error_msg)
                    self._stats['errors'].append(error_msg)
        
        except Exception as e:
            error_msg = f"Error scanning Docker networks: {e}"
            self.logger.error(error_msg)
            self._stats['errors'].append(error_msg)
        
        return unused_networks
    
    def cleanup_resources(self, resources: List[Union[DockerImage, DockerContainer, DockerVolume, DockerNetwork]], 
                         dry_run: bool = True) -> CleanupResult:
        """Clean up Docker resources with dry-run support."""
        result = CleanupResult(
            images_removed=0,
            containers_removed=0,
            volumes_removed=0,
            networks_removed=0,
            space_freed=0,
            errors=[]
        )
        
        if not self.is_docker_available():
            result.errors.append("Docker not available")
            return result
        
        for resource in resources:
            try:
                if isinstance(resource, DockerImage):
                    if not dry_run:
                        self.client.images.remove(resource.id, force=True)
                    result.images_removed += 1
                    result.space_freed += resource.size
                    self.logger.info(f"{'Would remove' if dry_run else 'Removed'} image: {resource}")
                
                elif isinstance(resource, DockerContainer):
                    if not dry_run:
                        container = self.client.containers.get(resource.id)
                        container.remove(force=True)
                    result.containers_removed += 1
                    result.space_freed += resource.size
                    self.logger.info(f"{'Would remove' if dry_run else 'Removed'} container: {resource}")
                
                elif isinstance(resource, DockerVolume):
                    if not dry_run:
                        volume = self.client.volumes.get(resource.name)
                        volume.remove(force=True)
                    result.volumes_removed += 1
                    result.space_freed += resource.size
                    self.logger.info(f"{'Would remove' if dry_run else 'Removed'} volume: {resource}")
                
                elif isinstance(resource, DockerNetwork):
                    if not dry_run:
                        network = self.client.networks.get(resource.id)
                        network.remove()
                    result.networks_removed += 1
                    self.logger.info(f"{'Would remove' if dry_run else 'Removed'} network: {resource}")
            
            except Exception as e:
                error_msg = f"Error {'simulating removal of' if dry_run else 'removing'} {resource}: {e}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
        
        return result
    
    def get_space_usage(self) -> Dict[str, int]:
        """Get Docker space usage information."""
        if not self.is_docker_available():
            return {}
        
        try:
            # Use Docker system df to get space usage
            df_info = self.client.df()
            
            return {
                'images_size': sum(img.get('Size', 0) for img in df_info.get('Images', [])),
                'containers_size': sum(cont.get('SizeRw', 0) + cont.get('SizeRootFs', 0) 
                                     for cont in df_info.get('Containers', [])),
                'volumes_size': sum(vol.get('UsageData', {}).get('Size', 0) 
                                  for vol in df_info.get('Volumes', [])),
                'build_cache_size': df_info.get('BuildCache', {}).get('Size', 0)
            }
        
        except Exception as e:
            self.logger.error(f"Error getting Docker space usage: {e}")
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scanning statistics."""
        return self._stats.copy()
    
    def _is_image_unused(self, image_id: str) -> bool:
        """Check if an image is unused by any container."""
        try:
            containers = self.client.containers.list(all=True)
            for container in containers:
                if container.image.id == image_id:
                    return False
            return True
        except Exception:
            return False
    
    def _is_volume_orphaned(self, volume_name: str) -> bool:
        """Check if a volume is orphaned (not used by any container)."""
        try:
            containers = self.client.containers.list(all=True)
            for container in containers:
                mounts = container.attrs.get('Mounts', [])
                for mount in mounts:
                    if mount.get('Name') == volume_name:
                        return False
            return True
        except Exception:
            return False
    
    def _is_network_unused(self, network_id: str) -> bool:
        """Check if a network is unused by any container."""
        try:
            network = self.client.networks.get(network_id)
            containers = network.attrs.get('Containers', {})
            return len(containers) == 0
        except Exception:
            return False
    
    def _get_container_size(self, container) -> int:
        """Get container size (approximate)."""
        try:
            # Get container stats
            stats = container.stats(stream=False)
            # Use filesystem size if available
            if 'storage_stats' in stats:
                return stats['storage_stats'].get('size_bytes', 0)
            
            # Fallback: use image size as approximation
            return container.image.attrs.get('Size', 0)
        except Exception:
            return 0
    
    def _get_volume_size(self, volume) -> int:
        """Get volume size (approximate)."""
        try:
            # Try to get size from volume usage data
            usage_data = volume.attrs.get('UsageData', {})
            if 'Size' in usage_data:
                return usage_data['Size']
            
            # Fallback: try to estimate from mountpoint if accessible
            mountpoint = volume.attrs.get('Mountpoint', '')
            if mountpoint and os.path.exists(mountpoint):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(mountpoint):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(filepath)
                        except (OSError, IOError):
                            continue
                return total_size
            
            return 0
        except Exception:
            return 0
    
    def _format_bytes(self, bytes_size: int) -> str:
        """Format bytes to human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} PB"