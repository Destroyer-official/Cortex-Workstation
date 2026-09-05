"""Scans a local Docker daemon for reclaimable resources (images, stopped
containers, orphaned volumes, unused networks) and removes them, optionally
as a dry run.

Talks to the daemon through the ``docker`` SDK using the ambient environment
(DOCKER_HOST / named pipe / unix socket). The SDK import is optional so the
rest of the app still works when it is not installed.
"""

import os
from typing import List, Dict, Union, Any
from dataclasses import dataclass
from datetime import datetime
import logging

try:
    import docker
    from docker.errors import DockerException, APIError, NotFound
    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False

from cortex_unified.core.config import Config

@dataclass
class DockerImage:
    """Dockerimage.

    Manages DockerImage operations and coordinates related state changes for the component.
    """
    id: str
    repository: str
    tag: str
    size: int
    created: datetime
    is_dangling: bool
    
    def __str__(self):
        """Return an informative string representation of the instance.

        Formats key attributes and state flags into a concise string suitable for debugging and diagnostics.
        """
        return f"{self.repository}:{self.tag} ({self.id[:12]})"

@dataclass
class DockerContainer:
    """Dockercontainer.

    Manages DockerContainer operations and coordinates related state changes for the component.
    """
    id: str
    name: str
    image: str
    status: str
    size: int
    created: datetime
    
    def __str__(self):
        """Return an informative string representation of the instance.

        Formats key attributes and state flags into a concise string suitable for debugging and diagnostics.
        """
        return f"{self.name} ({self.id[:12]})"

@dataclass
class DockerVolume:
    """Dockervolume.

    Manages DockerVolume operations and coordinates related state changes for the component.
    """
    name: str
    driver: str
    size: int
    mount_point: str
    is_orphaned: bool
    
    def __str__(self):
        """Return an informative string representation of the instance.

        Formats key attributes and state flags into a concise string suitable for debugging and diagnostics.
        """
        return f"{self.name} ({self.driver})"

@dataclass
class DockerNetwork:
    """Dockernetwork.

    Manages DockerNetwork operations and coordinates related state changes for the component.
    """
    id: str
    name: str
    driver: str
    is_unused: bool
    
    def __str__(self):
        """Return an informative string representation of the instance.

        Formats key attributes and state flags into a concise string suitable for debugging and diagnostics.
        """
        return f"{self.name} ({self.driver})"

@dataclass
class CleanupResult:
    """Outcome of a cleanup pass; counts include dry-run previews.

    Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.
    """
    images_removed: int
    containers_removed: int
    volumes_removed: int
    networks_removed: int
    space_freed: int
    errors: List[str]
    
    @property
    def total_removed(self) -> int:
        """total_removed.

        Manages total removed operations and coordinates related state changes for the component.

        Returns:
            int: Result of the operation.
        """
        return self.images_removed + self.containers_removed + self.volumes_removed + self.networks_removed

class DockerCleaner:
    """Finds and removes reclaimable Docker resources via the Docker SDK.

    The daemon connection is created lazily, so instantiating this class
    never touches Docker. Per-resource failures are logged and collected
    rather than raised.
    """
    
    def __init__(self, config: Config = None):
        """Initialize state; the Docker client itself connects lazily.

        Args:
            config: Optional application configuration.
        """
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
        """Return a connected ``docker.DockerClient``, creating it on first use.

        Raises:
            ImportError: If the ``docker`` package is not installed.
        """
        if self._client is None:
            if not HAS_DOCKER:
                raise ImportError("Docker SDK not available. Install with: pip install docker")
            
            try:
                self._client = docker.from_env()
                # Fail fast here rather than mid-scan if the daemon is unreachable
                self._client.ping()
            except Exception as e:
                self.logger.error(f"Failed to connect to Docker: {e}")
                raise
        
        return self._client
    
    def is_docker_available(self) -> bool:
        """Check if Docker is available and running.

        Manages is docker available operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
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
        """Collect images that are dangling or referenced by no container.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Returns:
            List[DockerImage]: List of processed items or identifiers.
        """
        if not self.is_docker_available():
            return []
        
        unused_images = []
        
        try:
            images = self.client.images.list(all=True)
            self._stats['images_scanned'] = len(images)
            
            for image in images:
                try:
                    # Dangling images carry no tags ("<none>:<none>")
                    is_dangling = not image.tags or image.tags == ['<none>:<none>']
                    
                    repository = '<none>'
                    tag = '<none>'
                    if image.tags:
                        repo_tag = image.tags[0].split(':')
                        repository = repo_tag[0] if len(repo_tag) > 0 else '<none>'
                        tag = repo_tag[1] if len(repo_tag) > 1 else '<none>'
                    
                    created = datetime.fromisoformat(image.attrs['Created'].replace('Z', '+00:00'))
                    
                    size = image.attrs.get('Size', 0)
                    self._stats['total_size'] += size
                    
                    # Cross-checks every container's image ID; O(images x containers)
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
        """Collect containers that are not currently running.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Returns:
            List[DockerContainer]: List of processed items or identifiers.
        """
        if not self.is_docker_available():
            return []
        
        stopped_containers = []
        
        try:
            containers = self.client.containers.list(all=True)
            self._stats['containers_scanned'] = len(containers)
            
            for container in containers:
                try:
                    if container.status != 'running':
                        size = self._get_container_size(container)
                        self._stats['total_size'] += size
                        
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
        """Collect volumes not mounted by any container.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Returns:
            List[DockerVolume]: List of processed items or identifiers.
        """
        if not self.is_docker_available():
            return []
        
        unused_volumes = []
        
        try:
            volumes = self.client.volumes.list()
            self._stats['volumes_scanned'] = len(volumes)
            
            for volume in volumes:
                try:
                    is_orphaned = self._is_volume_orphaned(volume.name)
                    
                    if is_orphaned:
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
        """Collect user-defined networks with no attached containers.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Returns:
            List[DockerNetwork]: List of processed items or identifiers.
        """
        if not self.is_docker_available():
            return []
        
        unused_networks = []
        
        try:
            networks = self.client.networks.list()
            self._stats['networks_scanned'] = len(networks)
            
            for network in networks:
                try:
                    # bridge/host/none are daemon-managed and must not be removed
                    if network.name in ['bridge', 'host', 'none']:
                        continue
                    
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
        """Remove the given resources, or preview removal when dry_run.

        Counters and ``space_freed`` are updated regardless of dry_run, so a
        dry-run pass reports what a real one would free.

        Args:
            resources: Mixed list of scan results to remove.
            dry_run: When True, no destructive API calls are made.

        Returns:
            Per-type removal counts, bytes freed, and error strings.
        """
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
    
    def get_filesystem_cache_size(self) -> Dict[str, int]:
        """Fallback: measure Docker Desktop's on-disk cache under AppData\\Local\\Docker.

        The 8.6GB manual hit at ``AppData\\Local\\Docker`` is not visible via the
        SDK (docker system prune); this probes the filesystem directly for the
        Storage Sense file-based docker_desktop_cache category.
        """
        from pathlib import Path
        local = os.environ.get("LOCALAPPDATA")
        candidates = []
        if local:
            candidates.append(Path(local) / "Docker")
            candidates.append(Path(local) / "DockerDesktop")
        # Legacy AppData\Roaming\Docker
        roaming = os.environ.get("APPDATA")
        if roaming:
            candidates.append(Path(roaming) / "Docker")

        total = 0
        found = []
        for root in candidates:
            try:
                if root.is_dir():
                    sz = 0
                    for dirpath, _, filenames in os.walk(root):
                        for fn in filenames:
                            try:
                                sz += (Path(dirpath) / fn).stat().st_size
                            except OSError:
                                continue
                    if sz > 0:
                        found.append((str(root), sz))
                        total += sz
            except OSError:
                continue
        return {"filesystem_cache_bytes": total, "locations": found}

    def get_space_usage(self) -> Dict[str, int]:
        """Get Docker space usage information (SDK + filesystem fallback).

        Manages get space usage operations and coordinates related state changes for the component.

        Returns:
            Dict[str, int]: Dictionary mapping identifiers to status or values.
        """
        # Prefer SDK when available, but always include filesystem cache probe
        fs_info = self.get_filesystem_cache_size()
        if not self.is_docker_available():
            return fs_info
        
        try:
            # client.df() is the API equivalent of "docker system df"
            df_info = self.client.df()
            
            out = {
                'images_size': sum(img.get('Size', 0) for img in df_info.get('Images', [])),
                'containers_size': sum(cont.get('SizeRw', 0) + cont.get('SizeRootFs', 0) 
                                     for cont in df_info.get('Containers', [])),
                'volumes_size': sum(vol.get('UsageData', {}).get('Size', 0) 
                                  for vol in df_info.get('Volumes', [])),
                'build_cache_size': df_info.get('BuildCache', {}).get('Size', 0)
            }
            out.update(fs_info)
            return out
        
        except Exception as e:
            self.logger.error(f"Error getting Docker space usage: {e}")
            return fs_info
    
    def get_stats(self) -> Dict[str, Any]:
        """Return a snapshot copy of cumulative scan counters.

        Manages get stats operations and coordinates related state changes for the component.

        Returns:
            Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return self._stats.copy()
    
    def _is_image_unused(self, image_id: str) -> bool:
        """True if no container references the image; False on API errors (fail-safe).

        Manages is image unused operations and coordinates related state changes for the component.

        Args:
            image_id (str): The image id parameter.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        try:
            containers = self.client.containers.list(all=True)
            for container in containers:
                if container.image.id == image_id:
                    return False
            return True
        except Exception:
            return False
    
    def _is_volume_orphaned(self, volume_name: str) -> bool:
        """True if no container mounts the volume; False on API errors (fail-safe).

        Manages is volume orphaned operations and coordinates related state changes for the component.

        Args:
            volume_name (str): The volume name parameter.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
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
        """True if the network reports zero attached containers; False on errors.

        Manages is network unused operations and coordinates related state changes for the component.

        Args:
            network_id (str): The network id parameter.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        try:
            network = self.client.networks.get(network_id)
            containers = network.attrs.get('Containers', {})
            return len(containers) == 0
        except Exception:
            return False
    
    def _get_container_size(self, container) -> int:
        """Approximate container size in bytes.

        Uses stats ``storage_stats`` when the daemon exposes it; otherwise
        falls back to the image size, which overstates usage because shared
        layers are counted per container.
        """
        try:
            stats = container.stats(stream=False)
            if 'storage_stats' in stats:
                return stats['storage_stats'].get('size_bytes', 0)
            
            return container.image.attrs.get('Size', 0)
        except Exception:
            return 0
    
    def _get_volume_size(self, volume) -> int:
        """Approximate volume size in bytes.

        Prefers daemon-reported ``UsageData``; otherwise walks the
        mountpoint, which only works for local-storage volumes on this host.
        """
        try:
            usage_data = volume.attrs.get('UsageData', {})
            if 'Size' in usage_data:
                return usage_data['Size']
            
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
        """Render a byte count using the largest fitting binary unit.

        Converts raw numeric values into formatted, localized, and human-readable string representations.

        Args:
            bytes_size (int): The bytes size parameter.

        Returns:
            str: Formatted string or path.
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} PB"