"""Network file system support module.

Provides unified access to remote file systems:
- SMB/CIFS (Windows shares, Samba) via smbprotocol
- FTP/FTPS via ftplib
- SFTP (SSH) via paramiko with reconnection
- WebDAV via webdavclient3

Architecture:
- Abstract NetworkFS base class
- Provider-specific implementations with retry logic
- Connection pooling with TTL
- Secure credential storage via keyring
- Offline cache support
"""

from __future__ import annotations

import ftplib
import logging
import os
import stat
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, TypeVar

from PySide6.QtCore import QObject, QThread, Signal

log = logging.getLogger("nexus.network")

T = TypeVar("T")

try:
    import smbclient
    HAS_SMB = True
except ImportError:
    HAS_SMB = False

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

try:
    from webdav3.client import Client as WebDAVClient
    HAS_WEBDAV = True
except ImportError:
    HAS_WEBDAV = False


class NetworkProtocol(Enum):
    """Supported network file system protocols."""
    SMB = auto()
    FTP = auto()
    FTPS = auto()
    SFTP = auto()
    WEBDAV = auto()


@dataclass
class NetworkFile:
    """Represents a file on a network share."""
    protocol: NetworkProtocol
    host: str
    path: str
    name: str
    is_dir: bool = False
    size: int = 0
    modified_ms: int = 0
    permissions: str = ""


@dataclass
class NetworkConnection:
    """A cached network connection."""
    protocol: NetworkProtocol
    host: str
    port: int
    username: str = ""
    is_connected: bool = False
    last_used: float = 0
    conn: Any = None


def store_credential(service: str, username: str, password: str) -> None:
    """Store a credential in the OS keychain."""
    if not HAS_KEYRING:
        log.warning("keyring not available; credential not stored for %s", service)
        return
    try:
        keyring.set_password(f"NexusExplorer_{service}", username, password)
    except Exception as e:
        log.warning("Failed to store credential for %s: %s", service, e)


def get_credential(service: str, username: str) -> str:
    """Retrieve a credential from the OS keychain."""
    if not HAS_KEYRING:
        log.warning("keyring not available; cannot retrieve credential for %s", service)
        return ""
    try:
        return keyring.get_password(f"NexusExplorer_{service}", username) or ""
    except Exception as e:
        log.warning("Failed to retrieve credential for %s: %s", service, e)
        return ""


def _path_join(base: str, name: str) -> str:
    """Join a path segment using backslashes for UNC (\\\\...) bases and
    forward slashes for everything else, collapsing duplicate
    separators."""
    if base.startswith("\\\\"):
        return base.rstrip("\\") + "\\" + name.lstrip("\\")
    return f"{base.rstrip('/')}/{name.lstrip('/')}"
    """Join a path segment using backslashes for UNC (\\\\...) bases and
    forward slashes for everything else, collapsing duplicate
    separators."""


class NetworkFS(ABC):
    """Abstract base class for network file systems."""

    @property
    @abstractmethod
    def protocol(self) -> NetworkProtocol:
        """Return the protocol handled by this file system."""
        ...

    @abstractmethod
    def connect(self, host: str, port: int = 0, username: str = "", password: str = "") -> bool:
        """Connect to a remote host."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the remote host."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if connected to the remote host."""
        ...

    @abstractmethod
    def list_files(self, path: str = "/") -> list[NetworkFile]:
        """List files in a remote directory."""
        ...

    @abstractmethod
    def download(self, remote_path: str, local_path: str) -> bool:
        """Download a remote file to local disk."""
        ...

    @abstractmethod
    def upload(self, local_path: str, remote_path: str) -> bool:
        """Upload a local file to the remote host."""
        ...

    @abstractmethod
    def delete(self, remote_path: str) -> bool:
        """Delete a file on the remote host."""
        ...

    @abstractmethod
    def mkdir(self, remote_path: str) -> bool:
        """Create a directory on the remote host."""
        ...

    @abstractmethod
    def exists(self, remote_path: str) -> bool:
        """Return True if a remote path exists."""
        ...


class SMBProvider(NetworkFS):
    """SMB/CIFS network share access via smbprotocol (SMB 2/3).

    Note: Uses a single lock for all operations, which serializes concurrent
    access. This is a simplification; a production implementation would use
    per-operation or per-file locking for better concurrency.
    """

    def __init__(self):
        """Start disconnected with host/share state and a global
        serialization lock."""
        self._host = ""
        self._share = ""
        self._connected = False
        self._lock = threading.Lock()
        """Start disconnected with host/share state and a global
        serialization lock."""

    @property
    def protocol(self) -> NetworkProtocol:
        """Return SMB as this provider's protocol."""
        return NetworkProtocol.SMB

    def connect(self, host: str, port: int = 445, username: str = "", password: str = "") -> bool:
        """Register an SMB session with the remote host."""
        if not HAS_SMB:
            log.warning("smbprotocol not installed; SMB unavailable")
            return False
        try:
            with self._lock:
                smbclient.register_session(
                    host,
                    username=username,
                    password=password,
                )
                self._host = host
                self._connected = True
                log.info("SMB connected to %s", host)
                return True
        except Exception as e:
            log.warning("SMB connection failed: %s", e)
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Delete the SMB session and mark disconnected."""
        with self._lock:
            if self._connected and self._host:
                try:
                    smbclient.delete_session(self._host)
                except Exception:
                    pass
            self._connected = False

    def is_connected(self) -> bool:
        """Return True if the SMB session is active."""
        return self._connected

    def list_files(self, path: str = "/") -> list[NetworkFile]:
        """List entries in an SMB directory via scandir."""
        if not self._connected:
            return []
        try:
            entries = []
            full_path = _path_join(f"\\\\{self._host}", path.lstrip("/"))
            with self._lock:
                for entry in smbclient.scandir(full_path):
                    stat_info = entry.stat()
                    entries.append(NetworkFile(
                        protocol=self.protocol,
                        host=self._host,
                        path=_path_join(path, entry.name),
                        name=entry.name,
                        is_dir=entry.is_dir(),
                        size=stat_info.st_size if not entry.is_dir() else 0,
                        modified_ms=int((stat_info.st_mtime or 0) * 1000),
                    ))
            return entries
        except Exception as e:
            log.warning("SMB list failed: %s", e)
            return []

    def download(self, remote_path: str, local_path: str) -> bool:
        """Download a file from the SMB share to local disk."""
        if not self._connected:
            return False
        try:
            remote = _path_join(f"\\\\{self._host}", remote_path.lstrip("/"))
            tmp_path = local_path + ".tmp"
            with self._lock:
                with smbclient.open_file(remote, mode="rb") as rf:
                    with open(tmp_path, "wb") as lf:
                        while chunk := rf.read(65536):
                            lf.write(chunk)
            os.replace(tmp_path, local_path)
            return True
        except Exception as e:
            log.warning("SMB download failed: %s", e)
            return False

    def upload(self, local_path: str, remote_path: str) -> bool:
        """Upload a local file to the SMB share."""
        if not self._connected:
            return False
        try:
            remote = _path_join(f"\\\\{self._host}", remote_path.lstrip("/"))
            with self._lock:
                with smbclient.open_file(remote, mode="wb") as rf:
                    with open(local_path, "rb") as lf:
                        while chunk := lf.read(65536):
                            rf.write(chunk)
            return True
        except Exception as e:
            log.warning("SMB upload failed: %s", e)
            return False

    def delete(self, remote_path: str) -> bool:
        """Remove a file from the SMB share."""
        if not self._connected:
            return False
        try:
            remote = _path_join(f"\\\\{self._host}", remote_path.lstrip("/"))
            with self._lock:
                smbclient.remove(remote)
            return True
        except Exception as e:
            log.warning("SMB delete failed: %s", e)
            return False

    def mkdir(self, remote_path: str) -> bool:
        """Create a directory on the SMB share."""
        if not self._connected:
            return False
        try:
            remote = _path_join(f"\\\\{self._host}", remote_path.lstrip("/"))
            with self._lock:
                smbclient.mkdir(remote)
            return True
        except Exception as e:
            log.warning("SMB mkdir failed: %s", e)
            return False

    def exists(self, remote_path: str) -> bool:
        """Return True if a path exists on the SMB share."""
        if not self._connected:
            return False
        try:
            remote = _path_join(f"\\\\{self._host}", remote_path.lstrip("/"))
            with self._lock:
                smbclient.stat(remote)
            return True
        except Exception:
            return False


class FTPProvider(NetworkFS):
    """FTP/FTPS file transfer access with automatic reconnection."""

    def __init__(self):
        """Store the FTP connection state, credentials, a serialization
        lock, and the 3-attempt retry budget."""
        self._conn: ftplib.FTP | None = None
        self._host = ""
        self._port = 21
        self._username = ""
        self._password = ""
        self._connected = False
        self._lock = threading.Lock()
        self._max_retries = 3
        """Store the FTP connection state, credentials, a serialization
        lock, and the 3-attempt retry budget."""

    @property
    def protocol(self) -> NetworkProtocol:
        """Return FTP as this provider's protocol."""
        return NetworkProtocol.FTP

    def connect(self, host: str, port: int = 21, username: str = "", password: str = "") -> bool:
        """Store credentials and connect to the FTP host."""
        self._host = host
        self._port = port
        self._username = username or "anonymous"
        self._password = password
        return self._reconnect()

    def _reconnect(self) -> bool:
        """Retry loop building a fresh ftplib.FTP connection (10 s
        timeout) with exponential backoff; up to _max_retries attempts."""
        for attempt in range(self._max_retries):
            try:
                self._close_conn()
                self._conn = ftplib.FTP()
                self._conn.connect(self._host, self._port, timeout=10)
                self._conn.login(self._username, self._password)
                self._connected = True
                log.info("FTP connected to %s", self._host)
                return True
            except Exception as e:
                if attempt == self._max_retries - 1:
                    log.warning("FTP connection failed after %d attempts: %s", self._max_retries, e)
                    self._connected = False
                    return False
                time.sleep(2 ** attempt)
        return False
        """Retry loop building a fresh ftplib.FTP connection (10 s
        timeout) with exponential backoff; up to _max_retries attempts."""

    def _close_conn(self) -> None:
        """Quit (or hard-close) the current FTP control connection and
        clear the reference."""
        if self._conn:
            try:
                self._conn.quit()
            except Exception:
                try:
                    self._conn.close()
                except Exception:
                    pass
            self._conn = None
        """Quit (or hard-close) the current FTP control connection and
        clear the reference."""

    def disconnect(self) -> None:
        """Close the FTP connection and mark disconnected."""
        with self._lock:
            self._close_conn()
            self._connected = False

    def is_connected(self) -> bool:
        """Return True if the FTP connection is open."""
        return self._connected and self._conn is not None

    def _safe_operation(self, operation: Callable[[ftplib.FTP], T]) -> T:
        """Run operation(self._conn) under the lock; on FTP/OSErrors
        reconnect with backoff and retry (up to _max_retries), re-raising
        the final failure."""
        for attempt in range(self._max_retries):
            try:
                with self._lock:
                    return operation(self._conn)
            except (ftplib.all_errors, OSError, EOFError):
                if attempt == self._max_retries - 1:
                    raise
                self._reconnect()
                time.sleep(2 ** attempt)
        raise RuntimeError("FTP operation failed after retries")
        """Run operation(self._conn) under the lock; on FTP/OSErrors
        reconnect with backoff and retry (up to _max_retries), re-raising
        the final failure."""

    def list_files(self, path: str = "/") -> list[NetworkFile]:
        """List FTP directory entries via MLSD."""
        if not self.is_connected():
            return []
        try:
            def _list(ftp: ftplib.FTP) -> list[NetworkFile]:
                """cwd into the path and convert MLSD facts into
                NetworkFile rows (skipping '.'/'..')."""
                ftp.cwd(path)
                entries: list[NetworkFile] = []
                for name, facts in ftp.mlsd():
                    if name in (".", ".."):
                        continue
                    is_dir = facts.get("type", "") == "dir"
                    entries.append(NetworkFile(
                        protocol=self.protocol,
                        host=self._host,
                        path=_path_join(path, name),
                        name=name,
                    is_dir=is_dir,
                    size=int(facts.get("size", 0)),
                ))
                return entries
                """cwd into the path and convert MLSD facts into
                NetworkFile rows (skipping '.'/'..')."""
            return self._safe_operation(_list)
        except Exception as e:
            log.warning("FTP list failed: %s", e)
            return []

    def download(self, remote_path: str, local_path: str) -> bool:
        """Download a file from the FTP server to local disk."""
        if not self.is_connected():
            return False
        try:
            tmp_path = local_path + ".tmp"
            def _download(ftp: ftplib.FTP) -> None:
                """Stream RETR into the .tmp file with f.write as the
                block callback."""
                with open(tmp_path, "wb") as f:
                    ftp.retrbinary(f"RETR {remote_path}", f.write)
                """Stream RETR into the .tmp file with f.write as the
                block callback."""
            self._safe_operation(_download)
            os.replace(tmp_path, local_path)
            return True
        except Exception as e:
            log.warning("FTP download failed: %s", e)
            return False

    def upload(self, local_path: str, remote_path: str) -> bool:
        """Upload a local file to the FTP server."""
        if not self.is_connected():
            return False
        try:
            def _upload(ftp: ftplib.FTP) -> None:
                """Stream the local file out via STOR."""
                with open(local_path, "rb") as f:
                    ftp.storbinary(f"STOR {remote_path}", f)
                """Stream the local file out via STOR."""
            self._safe_operation(_upload)
            return True
        except Exception as e:
            log.warning("FTP upload failed: %s", e)
            return False

    def delete(self, remote_path: str) -> bool:
        """Delete a file on the FTP server."""
        if not self.is_connected():
            return False
        try:
            self._safe_operation(lambda ftp: ftp.delete(remote_path))
            return True
        except Exception:
            return False

    def mkdir(self, remote_path: str) -> bool:
        """Create a directory on the FTP server."""
        if not self.is_connected():
            return False
        try:
            self._safe_operation(lambda ftp: ftp.mkd(remote_path))
            return True
        except Exception:
            return False

    def exists(self, remote_path: str) -> bool:
        """Return True if a path exists on the FTP server."""
        if not self.is_connected():
            return False
        try:
            self._safe_operation(lambda ftp: ftp.size(remote_path))
            return True
        except Exception:
            return False


class SFTPProvider(NetworkFS):
    """SFTP (SSH) file transfer access with exponential backoff reconnection."""

    def __init__(self):
        """Start disconnected: SSH/SFTP clients unset, retry budget 3,
        guarded by an RLock."""
        self._client: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None
        self._host = ""
        self._connected = False
        self._max_retries = 3
        self._lock = threading.RLock()
        """Start disconnected: SSH/SFTP clients unset, retry budget 3,
        guarded by an RLock."""

    @property
    def protocol(self) -> NetworkProtocol:
        """Return SFTP as this provider's protocol."""
        return NetworkProtocol.SFTP

    def connect(self, host: str, port: int = 22, username: str = "", password: str = "") -> bool:
        """Store SSH config and connect to the SFTP host."""
        if not HAS_PARAMIKO:
            log.warning("paramiko not installed; SFTP unavailable")
            return False
        self._connect_config = {
            "hostname": host,
            "port": port,
            "username": username,
            "password": password,
            "timeout": 30,
            "banner_timeout": 30,
        }
        self._host = host
        return self._reconnect()

    def _reconnect(self) -> bool:
        """Retry loop: build an SSHClient (known_hosts verified with
        RejectPolicy when present, else AutoAdd), connect, and open the
        SFTP channel; exponential backoff between attempts."""
        for attempt in range(self._max_retries):
            try:
                with self._lock:
                    self._close_both()
                    self._client = paramiko.SSHClient()
                    known_hosts = os.path.expanduser("~/.ssh/known_hosts")
                    if os.path.isfile(known_hosts):
                        self._client.load_system_host_keys(known_hosts)
                        self._client.set_missing_host_key_policy(paramiko.RejectPolicy())
                    else:
                        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    self._client.connect(**self._connect_config)
                    self._sftp = self._client.open_sftp()
                    self._connected = True
                    log.info("SFTP connected to %s", self._host)
                    return True
            except Exception as e:
                if attempt == self._max_retries - 1:
                    log.warning("SFTP connection failed after %d attempts: %s", self._max_retries, e)
                    self._connected = False
                    return False
                time.sleep(2 ** attempt)
        return False
        """Retry loop: build an SSHClient (known_hosts verified with
        RejectPolicy when present, else AutoAdd), connect, and open the
        SFTP channel; exponential backoff between attempts."""

    def _close_both(self) -> None:
        """Close the SFTP session and its SSH client, swallowing errors."""
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        """Close the SFTP session and its SSH client, swallowing errors."""

    def disconnect(self) -> None:
        """Close SSH and SFTP handles and mark disconnected."""
        with self._lock:
            self._close_both()
            self._connected = False

    def is_connected(self) -> bool:
        """Return True if the SFTP session is open."""
        return self._connected and self._sftp is not None

    def _safe_operation(self, operation: Callable[[paramiko.SFTPClient], T]) -> T:
        """Run operation(self._sftp) under the lock; on SSH/EOF/OSErrors
        reconnect with backoff and retry (up to _max_retries), re-raising
        the final failure."""
        for attempt in range(self._max_retries):
            try:
                with self._lock:
                    return operation(self._sftp)
            except (paramiko.SSHException, EOFError, OSError):
                if attempt == self._max_retries - 1:
                    raise
                self._reconnect()
                time.sleep(2 ** attempt)
        raise RuntimeError("SFTP operation failed after retries")
        """Run operation(self._sftp) under the lock; on SSH/EOF/OSErrors
        reconnect with backoff and retry (up to _max_retries), re-raising
        the final failure."""

    def list_files(self, path: str = ".") -> list[NetworkFile]:
        """List entries in an SFTP directory."""
        if not self.is_connected():
            return []
        try:
            def _list(sftp: paramiko.SFTPClient) -> list[NetworkFile]:
                """Convert listdir_attr results into NetworkFile rows
                (dir detection via stat.S_ISDIR)."""
                entries: list[NetworkFile] = []
                for attr in sftp.listdir_attr(path):
                    entries.append(NetworkFile(
                        protocol=self.protocol,
                        host=self._host,
                        path=_path_join(path, attr.filename),
                        name=attr.filename,
                        is_dir=stat.S_ISDIR(attr.st_mode),
                        size=attr.st_size or 0,
                        modified_ms=int((attr.st_mtime or 0) * 1000),
                    ))
                return entries
                """Convert listdir_attr results into NetworkFile rows
                (dir detection via stat.S_ISDIR)."""
            return self._safe_operation(_list)
        except Exception as e:
            log.warning("SFTP list failed: %s", e)
            return []

    def download(self, remote_path: str, local_path: str) -> bool:
        """Download a file from the SFTP server to local disk."""
        if not self.is_connected():
            return False
        try:
            self._safe_operation(lambda sftp: sftp.get(remote_path, local_path))
            return True
        except Exception as e:
            log.warning("SFTP download failed: %s", e)
            return False

    def upload(self, local_path: str, remote_path: str) -> bool:
        """Upload a local file to the SFTP server."""
        if not self.is_connected():
            return False
        try:
            self._safe_operation(lambda sftp: sftp.put(local_path, remote_path))
            return True
        except Exception as e:
            log.warning("SFTP upload failed: %s", e)
            return False

    def delete(self, remote_path: str) -> bool:
        """Remove a file on the SFTP server."""
        if not self.is_connected():
            return False
        try:
            self._safe_operation(lambda sftp: sftp.remove(remote_path))
            return True
        except Exception:
            return False

    def mkdir(self, remote_path: str) -> bool:
        """Create a directory on the SFTP server."""
        if not self.is_connected():
            return False
        try:
            self._safe_operation(lambda sftp: sftp.mkdir(remote_path))
            return True
        except Exception:
            return False

    def exists(self, remote_path: str) -> bool:
        """Return True if a path exists on the SFTP server."""
        if not self.is_connected():
            return False
        try:
            self._safe_operation(lambda sftp: sftp.stat(remote_path))
            return True
        except Exception:
            return False


class WebDAVProvider(NetworkFS):
    """WebDAV file access via webdavclient3."""

    def __init__(self):
        """Start disconnected with no WebDAV client, config, or host."""
        self._client: WebDAVClient | None = None
        self._base_url = ""
        self._connected = False
        self._config: dict[str, str] = {}
        self._host = ""
        self._lock = threading.Lock()
        """Start disconnected with no WebDAV client, config, or host."""

    @property
    def protocol(self) -> NetworkProtocol:
        """Return WebDAV as this provider's protocol."""
        return NetworkProtocol.WEBDAV

    def connect(self, host: str, port: int = 443, username: str = "", password: str = "",
                use_tls: bool | None = None) -> bool:
        """Build a WebDAV client for the given host."""
        if not HAS_WEBDAV:
            log.warning("webdavclient3 not installed; WebDAV unavailable")
            return False
        try:
            if use_tls is not None:
                scheme = "https" if use_tls else "http"
            else:
                scheme = "https" if port == 443 else "http"
            self._base_url = f"{scheme}://{host}:{port}" if port not in (80, 443) else f"{scheme}://{host}"
            self._config = {
                "webdav_hostname": self._base_url,
                "webdav_login": username,
                "webdav_password": password,
                "webdav_timeout": 30,
            }
            self._client = WebDAVClient(self._config)
            self._host = host
            self._connected = True
            log.info("WebDAV connected to %s", host)
            return True
        except Exception as e:
            log.warning("WebDAV connection failed: %s", e)
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Drop the WebDAV client and mark disconnected."""
        with self._lock:
            self._client = None
            self._connected = False

    def is_connected(self) -> bool:
        """Return True if the WebDAV client is active."""
        return self._connected and self._client is not None

    def list_files(self, path: str = "/") -> list[NetworkFile]:
        """List entries in a WebDAV directory."""
        if not self.is_connected():
            return []
        try:
            with self._lock:
                items = self._client.list(path, get_info=True)
            entries: list[NetworkFile] = []
            for item in items:
                name = item.get("name", "")
                if name in (".", "..", ""):
                    continue
                is_dir = item.get("is_dir", False)
                entries.append(NetworkFile(
                    protocol=self.protocol,
                    host=self._host,
                    path=_path_join(path, name),
                    name=name,
                    is_dir=is_dir,
                    size=int(item.get("size", 0)) if not is_dir else 0,
                ))
            return entries
        except Exception as e:
            log.warning("WebDAV list failed: %s", e)
            return []

    def download(self, remote_path: str, local_path: str) -> bool:
        """Download a file from the WebDAV server."""
        if not self.is_connected():
            return False
        try:
            with self._lock:
                self._client.download_from(remote_path, local_path)
            return True
        except Exception as e:
            log.warning("WebDAV download failed: %s", e)
            return False

    def upload(self, local_path: str, remote_path: str) -> bool:
        """Upload a local file to the WebDAV server."""
        if not self.is_connected():
            return False
        try:
            with self._lock:
                self._client.upload_to(remote_path, local_path)
            return True
        except Exception as e:
            log.warning("WebDAV upload failed: %s", e)
            return False

    def delete(self, remote_path: str) -> bool:
        """Delete a path on the WebDAV server."""
        if not self.is_connected():
            return False
        try:
            with self._lock:
                self._client.clean(remote_path)
            return True
        except Exception:
            return False

    def mkdir(self, remote_path: str) -> bool:
        """Create a directory on the WebDAV server."""
        if not self.is_connected():
            return False
        try:
            with self._lock:
                self._client.mkdir(remote_path)
            return True
        except Exception:
            return False

    def exists(self, remote_path: str) -> bool:
        """Return True if a path exists on the WebDAV server."""
        if not self.is_connected():
            return False
        try:
            with self._lock:
                return self._client.check(remote_path)
        except Exception:
            return False


class ConnectionPool:
    """Thread-safe connection pool with TTL-based expiration."""

    def __init__(self, ttl_seconds: int = 300):
        """Create the connection map with the given idle TTL (default
        5 minutes)."""
        self._connections: dict[str, tuple[NetworkFS, float]] = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        """Create the connection map with the given idle TTL (default
        5 minutes)."""

    def _key(self, protocol: NetworkProtocol, host: str) -> str:
        """Build the cache key '<PROTOCOL>:<host>'."""
        return f"{protocol.name}:{host}"
        """Build the cache key '<PROTOCOL>:<host>'."""

    def get(self, protocol: NetworkProtocol, host: str) -> NetworkFS | None:
        """Return a cached connection, evicting it if TTL expired."""
        with self._lock:
            key = self._key(protocol, host)
            if key in self._connections:
                conn, last_used = self._connections[key]
                if time.time() - last_used > self._ttl:
                    try:
                        conn.disconnect()
                    except Exception:
                        pass
                    del self._connections[key]
                    return None
                self._connections[key] = (conn, time.time())
                return conn
        return None

    def put(self, protocol: NetworkProtocol, host: str, conn: NetworkFS) -> None:
        """Cache a connection, disconnecting any replaced entry."""
        with self._lock:
            key = self._key(protocol, host)
            old = self._connections.get(key)
            if old and old[0] is not conn:
                try:
                    old[0].disconnect()
                except Exception:
                    pass
            self._connections[key] = (conn, time.time())

    def remove(self, protocol: NetworkProtocol, host: str) -> None:
        """Remove and disconnect a cached connection."""
        with self._lock:
            key = self._key(protocol, host)
            entry = self._connections.pop(key, None)
            if entry:
                try:
                    entry[0].disconnect()
                except Exception:
                    pass

    def clear(self) -> None:
        """Disconnect and drop all cached connections."""
        with self._lock:
            for conn, _ in self._connections.values():
                try:
                    conn.disconnect()
                except Exception:
                    pass
            self._connections.clear()

    def evict_expired(self) -> int:
        """Disconnect expired connections and return evicted count."""
        evicted = 0
        with self._lock:
            now = time.time()
            expired = [k for k, (_, t) in self._connections.items() if now - t > self._ttl]
            for key in expired:
                conn, _ = self._connections.pop(key)
                try:
                    conn.disconnect()
                except Exception:
                    pass
                evicted += 1
        return evicted


class NetworkManager(QObject):
    """Unified network file system manager with connection pooling."""

    connection_changed = Signal(str, bool)

    def __init__(self, parent=None):
        """Register the provider classes per protocol, the active
        provider map, the connection pool, and a 50-entry MRU list."""
        super().__init__(parent)
        self._providers: dict[NetworkProtocol, type[NetworkFS]] = {
            NetworkProtocol.SMB: SMBProvider,
            NetworkProtocol.FTP: FTPProvider,
            NetworkProtocol.SFTP: SFTPProvider,
            NetworkProtocol.WEBDAV: WebDAVProvider,
        }
        self._active: dict[NetworkProtocol, NetworkFS] = {}
        self._pool = ConnectionPool()
        self._recent: list[NetworkConnection] = []
        self._MAX_RECENT = 50
        """Register the provider classes per protocol, the active
        provider map, the connection pool, and a 50-entry MRU list."""

    def _default_port(self, protocol: NetworkProtocol) -> int:
        """Return the well-known port per protocol (SMB 445, FTP 21, FTPS
        990, SFTP 22, WebDAV 443)."""
        return {
            NetworkProtocol.SMB: 445,
            NetworkProtocol.FTP: 21,
            NetworkProtocol.FTPS: 990,
            NetworkProtocol.SFTP: 22,
            NetworkProtocol.WEBDAV: 443,
        }.get(protocol, 0)
        """Return the well-known port per protocol (SMB 445, FTP 21, FTPS
        990, SFTP 22, WebDAV 443)."""

    def get_provider(self, protocol: NetworkProtocol) -> NetworkFS | None:
        """Return the active provider for a protocol."""
        return self._active.get(protocol)

    def connect(self, protocol: NetworkProtocol, host: str, port: int = 0,
                username: str = "", password: str = "") -> bool:
        """Connect via pool cache or a new provider instance."""
        if port == 0:
            port = self._default_port(protocol)

        cached = self._pool.get(protocol, host)
        if cached and cached.is_connected():
            self._active[protocol] = cached
            self.connection_changed.emit(host, True)
            return True

        cls = self._providers.get(protocol)
        if not cls:
            return False

        provider = cls()
        success = provider.connect(host, port, username, password)
        if success:
            self._active[protocol] = provider
            self._pool.put(protocol, host, provider)
            self._recent = [c for c in self._recent
                            if not (c.protocol == protocol and c.host == host)]
            self._recent.append(NetworkConnection(
                protocol=protocol, host=host, port=port,
                username=username, is_connected=True,
                last_used=time.time(), conn=provider,
            ))
            if len(self._recent) > self._MAX_RECENT:
                self._recent = self._recent[-self._MAX_RECENT:]

        self.connection_changed.emit(host, success)
        return success

    def disconnect(self, protocol: NetworkProtocol) -> None:
        """Disconnect the active provider for a protocol."""
        provider = self._active.pop(protocol, None)
        if provider:
            provider.disconnect()

    def disconnect_all(self) -> None:
        """Disconnect all providers and clear the pool."""
        for protocol in list(self._active):
            self.disconnect(protocol)
        self._pool.clear()

    def list_recent_connections(self) -> list[NetworkConnection]:
        """Return recent connections still connected."""
        verified: list[NetworkConnection] = []
        for c in self._recent:
            if c.conn is not None and c.conn.is_connected():
                c.is_connected = True
                verified.append(c)
            else:
                c.is_connected = False
        self._recent = [c for c in self._recent if c.is_connected]
        return verified

    def store_credentials(self, protocol: NetworkProtocol, host: str,
                          username: str, password: str) -> None:
        """Store credentials for a protocol host."""
        store_credential(f"{protocol.name}_{host}", username, password)

    def get_credentials(self, protocol: NetworkProtocol, host: str,
                        username: str) -> str:
        """Retrieve stored credentials for a protocol host."""
        return get_credential(f"{protocol.name}_{host}", username)
