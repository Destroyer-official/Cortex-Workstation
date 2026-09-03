"""Cloud storage integration module.

Provides a unified interface for accessing files across multiple
cloud storage providers: OneDrive, Google Drive, and Dropbox.

Architecture:
- Abstract CloudProvider base class
- Provider-specific implementations with official SDKs
- Automatic token refresh and persistence via OS keychain
- Rate limiting with exponential backoff
- Local cache with sync status
- Offline mode support
"""

from __future__ import annotations

import functools
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

log = logging.getLogger("nexus.cloud")

# ---------------------------------------------------------------------------
# Optional SDK imports
# ---------------------------------------------------------------------------

try:
    import msal
    HAS_MSAL = True
except ImportError:
    HAS_MSAL = False

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GoogleRequest
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build as google_build
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

try:
    import dropbox as dropbox_sdk
    HAS_DROPBOX = True
except ImportError:
    HAS_DROPBOX = False

try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SERVICE_NAME = "nexus_explorer_cloud"


def _parse_iso_datetime(iso_str: str) -> int:
    """Parse an ISO 8601 / RFC 3339 datetime string to milliseconds since epoch."""
    if not iso_str:
        return 0
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except Exception:
        return 0


def _secure_store(key: str, value: str) -> None:
    """Store a secret via keyring, falling back to a local file."""
    if HAS_KEYRING:
        try:
            keyring.set_password(_SERVICE_NAME, key, value)
            return
        except Exception as exc:
            log.debug("keyring store failed, using file fallback: %s", exc)
    fallback = Path.home() / ".nexus" / "secrets.json"
    fallback.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, str] = {}
    if fallback.exists():
        data = json.loads(fallback.read_text(encoding="utf-8"))
    data[key] = value
    fallback.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.chmod(str(fallback), 0o600)
    except OSError:
        pass


def _secure_load(key: str) -> str:
    """Load a secret via keyring, falling back to a local file."""
    if HAS_KEYRING:
        try:
            val = keyring.get_password(_SERVICE_NAME, key)
            if val:
                return val
        except Exception as exc:
            log.debug("keyring load failed, using file fallback: %s", exc)
    fallback = Path.home() / ".nexus" / "secrets.json"
    if fallback.exists():
        data = json.loads(fallback.read_text(encoding="utf-8"))
        return data.get(key, "")
    return ""


def _secure_delete(key: str) -> None:
    """Delete a stored secret."""
    if HAS_KEYRING:
        try:
            keyring.delete_password(_SERVICE_NAME, key)
        except Exception:
            pass
    fallback = Path.home() / ".nexus" / "secrets.json"
    if fallback.exists():
        data = json.loads(fallback.read_text(encoding="utf-8"))
        data.pop(key, None)
        fallback.write_text(json.dumps(data, indent=2), encoding="utf-8")


def retry_on_rate_limit(max_retries: int = 4):
    """Decorator factory: retry the wrapped call up to max_retries times
    with exponential backoff (1s, 2s, 4s, ...) on HTTP 429 / rate-limit /
    throttling errors; re-raises the last exception otherwise."""
    def decorator(func):
        """Inner decorator capturing func."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """Call func, catching 429-shaped exceptions (code/status attr
            or 'rate'/'throttl' text) and retrying with 2^attempt sleeps."""
            last_exc: Exception | None = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    status_code = getattr(exc, "code", None) or getattr(exc, "status", None)
                    if status_code == 429:
                        wait = 2 ** attempt
                        log.warning(
                            "Rate limited (attempt %d/%d), retrying in %ds",
                            attempt + 1, max_retries, wait,
                        )
                        time.sleep(wait)
                        last_exc = exc
                        continue
                    msg = str(exc).lower()
                    if "429" in msg or "rate" in msg or "throttl" in msg:
                        wait = 2 ** attempt
                        log.warning(
                            "Rate limited (attempt %d/%d), retrying in %ds",
                            attempt + 1, max_retries, wait,
                        )
                        time.sleep(wait)
                        last_exc = exc
                        continue
                    raise
            raise last_exc or RuntimeError(f"Rate limit exceeded after {max_retries} retries")
            """Call func, catching 429-shaped exceptions (code/status attr
            or 'rate'/'throttl' text) and retrying with 2^attempt sleeps."""
        return wrapper
        """Inner decorator capturing func."""
    return decorator
    """Decorator factory: retry the wrapped call up to max_retries times
    with exponential backoff (1s, 2s, 4s, ...) on HTTP 429 / rate-limit /
    throttling errors; re-raises the last exception otherwise."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class CloudProviderType(Enum):
    """Supported cloud storage providers."""
    ONEDRIVE = auto()
    GOOGLE_DRIVE = auto()
    DROPBOX = auto()
    S3 = auto()


class SyncStatus(Enum):
    """Local-vs-cloud synchronization states of a cloud file."""
    SYNCED = "synced"
    SYNCING = "syncing"
    LOCAL_ONLY = "local_only"
    CLOUD_ONLY = "cloud_only"
    CONFLICT = "conflict"
    ERROR = "error"
    """Local-vs-cloud synchronization states of a cloud file."""


@dataclass
class CloudFile:
    """Represents a file in cloud storage."""
    provider: CloudProviderType
    cloud_id: str
    name: str
    path: str  # cloud path
    local_path: str = ""
    is_dir: bool = False
    size: int = 0
    modified_ms: int = 0
    mime_type: str = ""
    sync_status: SyncStatus = SyncStatus.CLOUD_ONLY
    download_url: str = ""


@dataclass
class CloudAccount:
    """A connected cloud account."""
    provider: CloudProviderType
    email: str = ""
    display_name: str = ""
    space_used: int = 0
    space_total: int = 0
    is_connected: bool = False


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class CloudProvider(ABC):
    """Abstract base class for cloud storage providers."""

    @property
    @abstractmethod
    def provider_type(self) -> CloudProviderType:
        """Return the provider this implementation handles."""
        ...
        """Return the provider this implementation handles."""

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the provider. Returns True on success."""
        ...

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Return True when the provider holds valid credentials."""
        ...
        """Return True when the provider holds valid credentials."""

    @abstractmethod
    def disconnect(self) -> None:
        """Clear tokens and mark disconnected."""
        ...

    @abstractmethod
    def get_account_info(self) -> CloudAccount | None:
        """Fetch account identity and quota; None when unavailable."""
        ...
        """Fetch account identity and quota; None when unavailable."""

    @abstractmethod
    def list_files(self, path: str = "/", max_results: int = 1000) -> list[CloudFile]:
        """List files in a cloud directory."""
        ...

    @abstractmethod
    def search(self, query: str, max_results: int = 1000) -> list[CloudFile]:
        """Search for files by name."""
        ...

    @abstractmethod
    def download(self, cloud_id: str, local_path: str) -> bool:
        """Download a file to local disk."""
        ...

    @abstractmethod
    def upload(self, local_path: str, cloud_path: str) -> bool:
        """Upload a file to cloud storage."""
        ...

    @abstractmethod
    def delete(self, cloud_id: str) -> bool:
        """Delete a file from cloud storage."""
        ...

    @abstractmethod
    def get_quota(self) -> tuple[int, int]:
        """Return (used_bytes, total_bytes)."""
        ...


# ---------------------------------------------------------------------------
# OneDrive – Microsoft Graph API via MSAL
# ---------------------------------------------------------------------------

_ONEDRIVE_SCOPES = ["Files.ReadWrite.All", "User.Read"]
_ONEDRIVE_GRAPH = "https://graph.microsoft.com/v1.0"


class OneDriveProvider(CloudProvider):
    """Microsoft OneDrive integration via MSAL + Graph API."""

    def __init__(self, client_id: str = ""):
        """Set the app client id (arg or ONEDRIVE_CLIENT_ID env) and load
        the persisted MSAL token cache from secure storage when msal is
        installed."""
        self._client_id = client_id or os.environ.get("ONEDRIVE_CLIENT_ID", "")
        self._app: msal.PublicClientApplication | None = None
        self._token_cache: msal.SerializableTokenCache | None = None
        self._token: str = ""
        self._connected: bool = False
        self._account_name: str = ""

        if HAS_MSAL:
            cache_data = _secure_load("onedrive_cache")
            self._token_cache = msal.SerializableTokenCache(cache_data) if cache_data else msal.SerializableTokenCache()
        """Set the app client id (arg or ONEDRIVE_CLIENT_ID env) and load
        the persisted MSAL token cache from secure storage when msal is
        installed."""

    @property
    def provider_type(self) -> CloudProviderType:
        """Return ONEDRIVE as this provider's type."""
        return CloudProviderType.ONEDRIVE
        """Return ONEDRIVE as this provider's type."""

    def _persist_cache(self) -> None:
        """Serialize the MSAL token cache back to secure storage when it
        has changed."""
        if self._token_cache and self._token_cache.has_state_changed:
            _secure_store("onedrive_cache", self._token_cache.serialize())
        """Serialize the MSAL token cache back to secure storage when it
        has changed."""

    def _ensure_token(self) -> bool:
        """Attempt silent token acquisition. Returns True if a valid token is held."""
        if not self._app or not HAS_MSAL:
            return False
        accounts = self._app.get_accounts()
        if not accounts:
            return False
        result = self._app.acquire_token_silent(_ONEDRIVE_SCOPES, account=accounts[0])
        if result and "access_token" in result:
            self._token = result["access_token"]
            self._connected = True
            return True
        return False

    @retry_on_rate_limit()
    def authenticate(self) -> bool:
        """Authenticate via MSAL: build the PublicClientApplication, try
        silent token acquisition from the cache, then fall back to the
        interactive browser flow (port 8080) — recording the account name
        and persisting the token cache on success."""
        if not HAS_MSAL:
            log.warning("msal is not installed – OneDrive unavailable")
            return False
        if not self._client_id:
            log.warning("ONEDRIVE_CLIENT_ID not set")
            return False

        self._app = msal.PublicClientApplication(
            self._client_id,
            authority="https://login.microsoftonline.com/common",
            token_cache=self._token_cache,
        )

        # Try silent first
        if self._ensure_token():
            self._persist_cache()
            log.info("OneDrive: authenticated via cached token")
            return True

        # Interactive browser auth
        try:
            result = self._app.acquire_token_interactive(
                _ONEDRIVE_SCOPES, port=8080,
            )
            if result and "access_token" in result:
                self._token = result["access_token"]
                self._connected = True
                self._account_name = result.get("id_token_claims", {}).get("preferred_username", "")
                self._persist_cache()
                log.info("OneDrive: authenticated interactively")
                return True
            log.warning("OneDrive auth returned no token: %s", result.get("error", "unknown"))
            return False
        except Exception as exc:
            log.warning("OneDrive interactive auth failed: %s", exc)
            return False
        """Authenticate via MSAL: build the PublicClientApplication, try
        silent token acquisition from the cache, then fall back to the
        interactive browser flow (port 8080) — recording the account name
        and persisting the token cache on success."""

    def is_authenticated(self) -> bool:
        """True when a token is held, else attempt a silent refresh."""
        if self._connected and self._token:
            return True
        return self._ensure_token()
        """True when a token is held, else attempt a silent refresh."""

    def disconnect(self) -> None:
        """Drop the token/connection and delete the persisted MSAL cache."""
        self._token = ""
        self._connected = False
        _secure_delete("onedrive_cache")
        """Drop the token/connection and delete the persisted MSAL cache."""

    def _graph_get(self, url: str) -> dict:
        """GET a Microsoft Graph URL with the bearer token (30 s timeout)
        and return the parsed JSON body."""
        if not self._ensure_token():
            raise RuntimeError("OneDrive: not authenticated")
        import urllib.request
        import urllib.error
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self._token}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
        """GET a Microsoft Graph URL with the bearer token (30 s timeout)
        and return the parsed JSON body."""

    @retry_on_rate_limit()
    def get_account_info(self) -> CloudAccount | None:
        """Fetch /me/drive quota plus /me profile into a CloudAccount."""
        try:
            data = self._graph_get(f"{_ONEDRIVE_GRAPH}/me/drive")
            quota = data.get("quota", {})
            user = self._graph_get(f"{_ONEDRIVE_GRAPH}/me")
            return CloudAccount(
                provider=self.provider_type,
                email=user.get("mail", user.get("userPrincipalName", "")),
                display_name=user.get("displayName", ""),
                space_used=quota.get("used", 0),
                space_total=quota.get("total", 0),
                is_connected=True,
            )
        except Exception as exc:
            log.warning("OneDrive account info failed: %s", exc)
            return None
        """Fetch /me/drive quota plus /me profile into a CloudAccount."""

    @retry_on_rate_limit()
    def list_files(self, path: str = "/", max_results: int = 1000) -> list[CloudFile]:
        """List children of a OneDrive path via Graph, following
        @odata.nextLink pages up to max_results (page size capped at 200)."""
        try:
            graph_path = path.strip("/") or "root"
            url = f"{_ONEDRIVE_GRAPH}/me/drive/{graph_path}/children?$top={min(max_results, 200)}"
            files: list[CloudFile] = []
            while url and len(files) < max_results:
                data = self._graph_get(url)
                for item in data.get("value", []):
                    files.append(CloudFile(
                        provider=self.provider_type,
                        cloud_id=item["id"],
                        name=item["name"],
                        path=f"{path.rstrip('/')}/{item['name']}",
                        is_dir="folder" in item,
                        size=item.get("size", 0),
                        modified_ms=_parse_iso_datetime(item.get("lastModifiedDateTime", "")),
                        mime_type=item.get("file", {}).get("mimeType", ""),
                    ))
                url = data.get("@odata.nextLink")
            return files[:max_results]
        except Exception as exc:
            log.warning("OneDrive list_files failed: %s", exc)
            return []
        """List children of a OneDrive path via Graph, following
        @odata.nextLink pages up to max_results (page size capped at 200)."""

    @retry_on_rate_limit()
    def search(self, query: str, max_results: int = 1000) -> list[CloudFile]:
        """Search drive items by name via Graph search, deriving each
        parent path from parentReference."""
        try:
            url = f"{_ONEDRIVE_GRAPH}/me/drive/search(q='{query}')?$top={max_results}"
            data = self._graph_get(url)
            files: list[CloudFile] = []
            for item in data.get("value", []):
                parent_path = item.get("parentReference", {}).get("path", "/drive/root:").split(":")[-1]
                files.append(CloudFile(
                    provider=self.provider_type,
                    cloud_id=item["id"],
                    name=item["name"],
                    path=f"{parent_path}/{item['name']}",
                    is_dir="folder" in item,
                    size=item.get("size", 0),
                    modified_ms=_parse_iso_datetime(item.get("lastModifiedDateTime", "")),
                    mime_type=item.get("file", {}).get("mimeType", ""),
                ))
            return files
        except Exception as exc:
            log.warning("OneDrive search failed: %s", exc)
            return []
        """Search drive items by name via Graph search, deriving each
        parent path from parentReference."""

    @retry_on_rate_limit()
    def download(self, cloud_id: str, local_path: str) -> bool:
        """Stream an item's /content endpoint to local_path via a .tmp
        file (64 KB chunks) and atomically os.replace it into place."""
        try:
            import urllib.request
            url = f"{_ONEDRIVE_GRAPH}/me/drive/items/{cloud_id}/content"
            if not self._ensure_token():
                return False
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self._token}"})
            dest = Path(local_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = str(dest) + ".tmp"
            with urllib.request.urlopen(req, timeout=120) as resp, open(tmp_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            os.replace(tmp_path, str(dest))
            return True
        except Exception as exc:
            log.warning("OneDrive download failed: %s", exc)
            return False
        """Stream an item's /content endpoint to local_path via a .tmp
        file (64 KB chunks) and atomically os.replace it into place."""

    @retry_on_rate_limit()
    def upload(self, local_path: str, cloud_path: str) -> bool:
        """PUT the local file to its Graph ':/content' URL in 64 KB
        chunks; target parents resolve via the cloud path prefix."""
        try:
            import io
            import urllib.request
            import urllib.parse
            src = Path(local_path)
            if not src.is_file():
                return False
            parent, _, name = cloud_path.rpartition("/")
            parent = parent.strip("/") or "root"
            url = f"{_ONEDRIVE_GRAPH}/me/drive/{parent}:/{urllib.parse.quote(name)}:/content"
            if not self._ensure_token():
                return False
            file_size = src.stat().st_size
            chunk_size = 65536
            with open(src, "rb") as f:
                def _upload_chunked():
                    """Repeatedly PUT the next 64 KB chunk of the open file
                    to the Graph content URL until EOF."""
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        req = urllib.request.Request(
                            url,
                            data=chunk,
                            headers={
                                "Authorization": f"Bearer {self._token}",
                                "Content-Type": "application/octet-stream",
                                "Content-Length": str(len(chunk)),
                            },
                            method="PUT",
                        )
                        with urllib.request.urlopen(req, timeout=120):
                            pass
                    """Repeatedly PUT the next 64 KB chunk of the open file
                    to the Graph content URL until EOF."""
                _upload_chunked()
            return True
        except Exception as exc:
            log.warning("OneDrive upload failed: %s", exc)
            return False
        """PUT the local file to its Graph ':/content' URL in 64 KB
        chunks; target parents resolve via the cloud path prefix."""

    @retry_on_rate_limit()
    def delete(self, cloud_id: str) -> bool:
        """DELETE the drive item by id via Graph."""
        try:
            import urllib.request
            url = f"{_ONEDRIVE_GRAPH}/me/drive/items/{cloud_id}"
            if not self._ensure_token():
                return False
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {self._token}"},
                method="DELETE",
            )
            with urllib.request.urlopen(req, timeout=30):
                pass
            return True
        except Exception as exc:
            log.warning("OneDrive delete failed: %s", exc)
            return False
        """DELETE the drive item by id via Graph."""

    @retry_on_rate_limit()
    def get_quota(self) -> tuple[int, int]:
        """Return (used_bytes, total_bytes) from /me/drive quota; (0, 0)
        on failure."""
        try:
            data = self._graph_get(f"{_ONEDRIVE_GRAPH}/me/drive")
            q = data.get("quota", {})
            return (q.get("used", 0), q.get("total", 0))
        except Exception:
            return (0, 0)
        """Return (used_bytes, total_bytes) from /me/drive quota; (0, 0)
        on failure."""


# ---------------------------------------------------------------------------
# Google Drive – google-api-python-client
# ---------------------------------------------------------------------------

_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
]
_GOOGLE_CREDENTIALS_FILE = Path.home() / ".nexus" / "google_credentials.json"


class GoogleDriveProvider(CloudProvider):
    """Google Drive integration via google-api-python-client."""

    _TOKEN_DIR = Path.home() / ".nexus" / "tokens"

    def __init__(self, credentials_file: str = "", token_dir: str = ""):
        """Set the OAuth client-secrets file and the token storage
        directory (defaults under ~/.nexus)."""
        self._credentials_file = Path(credentials_file) if credentials_file else _GOOGLE_CREDENTIALS_FILE
        self._token_dir = Path(token_dir) if token_dir else self._TOKEN_DIR
        self._service = None
        self._creds: Credentials | None = None
        self._connected: bool = False
        self._account_email: str = ""
        """Set the OAuth client-secrets file and the token storage
        directory (defaults under ~/.nexus)."""

    @property
    def provider_type(self) -> CloudProviderType:
        """Return GOOGLE_DRIVE as this provider's type."""
        return CloudProviderType.GOOGLE_DRIVE
        """Return GOOGLE_DRIVE as this provider's type."""

    def _token_path(self) -> Path:
        """Return the cached token file path, creating the token dir."""
        self._token_dir.mkdir(parents=True, exist_ok=True)
        return self._token_dir / "google_drive_token.json"
        """Return the cached token file path, creating the token dir."""

    @retry_on_rate_limit()
    def authenticate(self) -> bool:
        """Authenticate: reuse the saved token, refresh it when expired,
        or run the InstalledAppFlow OAuth loop; then build the Drive v3
        service and capture the account email."""
        if not HAS_GOOGLE:
            log.warning("google-api-python-client / google-auth not installed – Google Drive unavailable")
            return False

        creds = None
        token_path = self._token_path()

        # Load existing token
        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_path), _GOOGLE_SCOPES)
            except Exception as exc:
                log.debug("Failed to load cached Google token: %s", exc)

        # Refresh or run new flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(GoogleRequest())
                except Exception as exc:
                    log.warning("Google token refresh failed: %s", exc)
                    creds = None
            if not creds:
                if not self._credentials_file.exists():
                    log.warning("Google credentials file not found: %s", self._credentials_file)
                    return False
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self._credentials_file), _GOOGLE_SCOPES,
                    )
                    creds = flow.run_local_server(port=0, open_browser=True)
                except Exception as exc:
                    log.warning("Google OAuth flow failed: %s", exc)
                    return False

            # Persist
            try:
                token_path.write_text(creds.to_json(), encoding="utf-8")
            except Exception as exc:
                log.debug("Failed to persist Google token: %s", exc)

        try:
            self._service = google_build("drive", "v3", credentials=creds)
            self._creds = creds
            self._connected = True

            # Fetch user email for account info
            about = self._service.about().get(fields="user").execute()
            self._account_email = about.get("user", {}).get("emailAddress", "")
            log.info("Google Drive: authenticated as %s", self._account_email)
            return True
        except Exception as exc:
            log.warning("Google Drive service build failed: %s", exc)
            return False
        """Authenticate: reuse the saved token, refresh it when expired,
        or run the InstalledAppFlow OAuth loop; then build the Drive v3
        service and capture the account email."""

    def is_authenticated(self) -> bool:
        """Verify the service exists and the token is still valid,
        refreshing (and rebuilding the service) when expired."""
        if self._connected and self._service:
            # Verify token still valid
            if self._creds and not self._creds.valid:
                if self._creds.expired and self._creds.refresh_token:
                    try:
                        self._creds.refresh(GoogleRequest())
                        self._service = google_build("drive", "v3", credentials=self._creds)
                    except Exception:
                        self._connected = False
                        return False
            return True
        return False
        """Verify the service exists and the token is still valid,
        refreshing (and rebuilding the service) when expired."""

    def disconnect(self) -> None:
        """Drop the service/creds and delete the stored token file."""
        self._connected = False
        self._service = None
        self._creds = None
        token_path = self._token_path()
        if token_path.exists():
            token_path.unlink(missing_ok=True)
        """Drop the service/creds and delete the stored token file."""

    def get_account_info(self) -> CloudAccount | None:
        """Fetch user profile and storage quota via about().get."""
        if not self.is_authenticated():
            return None
        try:
            about = self._service.about().get(fields="user,storageQuota").execute()
            user = about.get("user", {})
            quota = about.get("storageQuota", {})
            return CloudAccount(
                provider=self.provider_type,
                email=user.get("emailAddress", ""),
                display_name=user.get("displayName", ""),
                space_used=int(quota.get("usage", 0)),
                space_total=int(quota.get("limit", 0)),
                is_connected=True,
            )
        except Exception as exc:
            log.warning("Google Drive account info failed: %s", exc)
            return None
        """Fetch user profile and storage quota via about().get."""

    @retry_on_rate_limit()
    def list_files(self, path: str = "/", max_results: int = 1000) -> list[CloudFile]:
        """List a Drive folder by files().list — root query by parent,
        non-root by folder name (last path segment), trashed excluded."""
        if not self.is_authenticated():
            return []
        try:
            # If path is root, list root folder; otherwise query by name
            if path.strip("/") in ("", "root"):
                query = "'root' in parents and trashed=false"
            else:
                folder_name = path.strip("/").split("/")[-1]
                query = f"name='{folder_name}' and trashed=false"

            results = (
                self._service.files()
                .list(
                    q=query,
                    pageSize=min(max_results, 1000),
                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            files: list[CloudFile] = []
            for item in results.get("files", []):
                is_dir = item.get("mimeType") == "application/vnd.google-apps.folder"
                files.append(CloudFile(
                    provider=self.provider_type,
                    cloud_id=item["id"],
                    name=item["name"],
                    path=f"{path.rstrip('/')}/{item['name']}",
                    is_dir=is_dir,
                    size=int(item.get("size", 0)),
                    modified_ms=_parse_iso_datetime(item.get("modifiedTime", "")),
                    mime_type=item.get("mimeType", ""),
                ))
            return files
        except Exception as exc:
            log.warning("Google Drive list_files failed: %s", exc)
            return []
        """List a Drive folder by files().list — root query by parent,
        non-root by folder name (last path segment), trashed excluded."""

    @retry_on_rate_limit()
    def search(self, query: str, max_results: int = 1000) -> list[CloudFile]:
        """Search Drive by 'name contains' query (trashed excluded)."""
        if not self.is_authenticated():
            return []
        try:
            q = f"name contains '{query}' and trashed=false"
            results = (
                self._service.files()
                .list(
                    q=q,
                    pageSize=min(max_results, 1000),
                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            files: list[CloudFile] = []
            for item in results.get("files", []):
                is_dir = item.get("mimeType") == "application/vnd.google-apps.folder"
                files.append(CloudFile(
                    provider=self.provider_type,
                    cloud_id=item["id"],
                    name=item["name"],
                    path=f"/{item['name']}",
                    is_dir=is_dir,
                    size=int(item.get("size", 0)),
                    modified_ms=_parse_iso_datetime(item.get("modifiedTime", "")),
                    mime_type=item.get("mimeType", ""),
                ))
            return files
        except Exception as exc:
            log.warning("Google Drive search failed: %s", exc)
            return []
        """Search Drive by 'name contains' query (trashed excluded)."""

    @retry_on_rate_limit()
    def download(self, cloud_id: str, local_path: str) -> bool:
        """Download via MediaIoBaseDownload (64 KB chunks) into a .tmp
        file, then atomically move to the destination."""
        if not self.is_authenticated():
            return False
        try:
            dest = Path(local_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = str(dest) + ".tmp"
            request = self._service.files().get_media(fileId=cloud_id)
            from googleapiclient.http import MediaIoBaseDownload
            import io
            with open(tmp_path, "wb") as f:
                downloader = MediaIoBaseDownload(f, request, chunksize=65536)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            os.replace(tmp_path, str(dest))
            return True
        except Exception as exc:
            log.warning("Google Drive download failed: %s", exc)
            return False
        """Download via MediaIoBaseDownload (64 KB chunks) into a .tmp
        file, then atomically move to the destination."""

    @retry_on_rate_limit()
    def upload(self, local_path: str, cloud_path: str) -> bool:
        """Resumable MediaFileUpload to Drive with the cloud path's last
        segment as the file name."""
        if not self.is_authenticated():
            return False
        try:
            src = Path(local_path)
            if not src.is_file():
                return False
            name = cloud_path.strip("/").split("/")[-1]
            file_metadata = {"name": name}
            from googleapiclient.http import MediaFileUpload
            media = MediaFileUpload(str(src), resumable=True, chunksize=65536)
            self._service.files().create(
                body=file_metadata, media_body=media, fields="id",
            ).execute()
            return True
        except Exception as exc:
            log.warning("Google Drive upload failed: %s", exc)
            return False
        """Resumable MediaFileUpload to Drive with the cloud path's last
        segment as the file name."""

    @retry_on_rate_limit()
    def delete(self, cloud_id: str) -> bool:
        """Delete a Drive file by id via files().delete."""
        if not self.is_authenticated():
            return False
        try:
            self._service.files().delete(fileId=cloud_id).execute()
            return True
        except Exception as exc:
            log.warning("Google Drive delete failed: %s", exc)
            return False
        """Delete a Drive file by id via files().delete."""

    @retry_on_rate_limit()
    def get_quota(self) -> tuple[int, int]:
        """Return (used_bytes, total_bytes) from about().storageQuota;
        (0, 0) on failure or when not connected."""
        if not self.is_authenticated():
            return (0, 0)
        try:
            about = self._service.about().get(fields="storageQuota").execute()
            q = about.get("storageQuota", {})
            return (int(q.get("usage", 0)), int(q.get("limit", 0)))
        except Exception:
            return (0, 0)
        """Return (used_bytes, total_bytes) from about().storageQuota;
        (0, 0) on failure or when not connected."""


# ---------------------------------------------------------------------------
# Dropbox – official SDK
# ---------------------------------------------------------------------------

class DropboxProvider(CloudProvider):
    """Dropbox integration via the official dropbox SDK."""

    def __init__(self, access_token: str = ""):
        """Load the access token (arg or secure storage) and start
        disconnected until authenticate() succeeds."""
        self._access_token = access_token or _secure_load("dropbox_token")
        self._dbx: dropbox_sdk.Dropbox | None = None
        self._connected: bool = False
        """Load the access token (arg or secure storage) and start
        disconnected until authenticate() succeeds."""

    @property
    def provider_type(self) -> CloudProviderType:
        """Return DROPBOX as this provider's type."""
        return CloudProviderType.DROPBOX
        """Return DROPBOX as this provider's type."""

    @retry_on_rate_limit()
    def authenticate(self) -> bool:
        """Build a Dropbox client from the stored token, verify it via
        users_get_current_account, and persist the token on success."""
        if not HAS_DROPBOX:
            log.warning("dropbox SDK not installed – Dropbox unavailable")
            return False
        if not self._access_token:
            log.warning("Dropbox access token not configured")
            return False
        try:
            self._dbx = dropbox_sdk.Dropbox(self._access_token, timeout=30)
            acct = self._dbx.users_get_current_account()
            self._connected = True
            _secure_store("dropbox_token", self._access_token)
            log.info("Dropbox: authenticated as %s", acct.email)
            return True
        except dropbox_sdk.AuthError as exc:
            log.warning("Dropbox auth failed (bad token): %s", exc)
            self._connected = False
            return False
        except Exception as exc:
            log.warning("Dropbox auth failed: %s", exc)
            self._connected = False
            return False
        """Build a Dropbox client from the stored token, verify it via
        users_get_current_account, and persist the token on success."""

    def is_authenticated(self) -> bool:
        """Probe the connection with users_get_current_account; a failure
        marks the provider disconnected."""
        if not self._connected or not self._dbx:
            return False
        try:
            self._dbx.users_get_current_account()
            return True
        except Exception:
            self._connected = False
            return False
        """Probe the connection with users_get_current_account; a failure
        marks the provider disconnected."""

    def disconnect(self) -> None:
        """Clear the token/client and delete the stored token."""
        self._access_token = ""
        self._connected = False
        self._dbx = None
        _secure_delete("dropbox_token")
        """Clear the token/client and delete the stored token."""

    @retry_on_rate_limit()
    def get_account_info(self) -> CloudAccount | None:
        """Fetch the current account plus space usage (individual
        allocation) into a CloudAccount."""
        if not self.is_authenticated():
            return None
        try:
            acct = self._dbx.users_get_current_account()
            space = self._dbx.users_get_space_usage()
            used = space.used if hasattr(space, "used") else 0
            total = 0
            if hasattr(space, "allocation") and hasattr(space.allocation, "get_individual"):
                total = space.allocation.get_individual().allocated
            return CloudAccount(
                provider=self.provider_type,
                email=acct.email,
                display_name=acct.name.display_name,
                space_used=used,
                space_total=total,
                is_connected=True,
            )
        except Exception as exc:
            log.warning("Dropbox account info failed: %s", exc)
            return None
        """Fetch the current account plus space usage (individual
        allocation) into a CloudAccount."""

    def _parse_dropbox_entry(self, entry: Any) -> CloudFile:
        """Convert a Dropbox file entry to a CloudFile."""
        is_dir = isinstance(entry, dropbox_sdk.files.FolderMetadata)
        return CloudFile(
            provider=self.provider_type,
            cloud_id=entry.id,
            name=entry.name,
            path=entry.path_display,
            is_dir=is_dir,
            size=entry.size if hasattr(entry, "size") else 0,
            modified_ms=int(entry.server_modified.timestamp() * 1000) if hasattr(entry, "server_modified") else 0,
        )

    @retry_on_rate_limit()
    def list_files(self, path: str = "/", max_results: int = 1000) -> list[CloudFile]:
        """List a Dropbox folder via files_list_folder, following the
        cursor (files_list_folder_continue) up to max_results."""
        if not self.is_authenticated():
            return []
        try:
            dbx_path = path.strip("/") or ""
            result = self._dbx.files_list_folder(dbx_path, limit=min(max_results, 2000))
            files: list[CloudFile] = []
            for entry in result.entries:
                files.append(self._parse_dropbox_entry(entry))
            while result.has_more and len(files) < max_results:
                result = self._dbx.files_list_folder_continue(result.cursor)
                for entry in result.entries:
                    files.append(self._parse_dropbox_entry(entry))
            return files[:max_results]
        except Exception as exc:
            log.warning("Dropbox list_files failed: %s", exc)
            return []
        """List a Dropbox folder via files_list_folder, following the
        cursor (files_list_folder_continue) up to max_results."""

    @retry_on_rate_limit()
    def search(self, query: str, max_results: int = 1000) -> list[CloudFile]:
        """Search via files_search_v2 (capped at 200), mapping file and
        folder metadata matches to CloudFile."""
        if not self.is_authenticated():
            return []
        try:
            result = self._dbx.files_search_v2(query, max_results=min(max_results, 200))
            files: list[CloudFile] = []
            for match in result.matches:
                meta = match.metadata.get_metadata()
                if isinstance(meta, dropbox_sdk.files.FileMetadata):
                    files.append(CloudFile(
                        provider=self.provider_type,
                        cloud_id=meta.id,
                        name=meta.name,
                        path=meta.path_display,
                        is_dir=False,
                        size=meta.size,
                        modified_ms=int(meta.server_modified.timestamp() * 1000),
                    ))
                elif isinstance(meta, dropbox_sdk.files.FolderMetadata):
                    files.append(CloudFile(
                        provider=self.provider_type,
                        cloud_id=meta.id,
                        name=meta.name,
                        path=meta.path_display,
                        is_dir=True,
                    ))
            return files
        except Exception as exc:
            log.warning("Dropbox search failed: %s", exc)
            return []
        """Search via files_search_v2 (capped at 200), mapping file and
        folder metadata matches to CloudFile."""

    @retry_on_rate_limit()
    def download(self, cloud_id: str, local_path: str) -> bool:
        """Download the file content into a .tmp file and atomically move
        it into place."""
        if not self.is_authenticated():
            return False
        try:
            dest = Path(local_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = str(dest) + ".tmp"
            _metadata, response = self._dbx.files_download(cloud_id)
            with open(tmp_path, "wb") as f:
                f.write(response.content)
            os.replace(tmp_path, str(dest))
            return True
        except Exception as exc:
            log.warning("Dropbox download failed: %s", exc)
            return False
        """Download the file content into a .tmp file and atomically move
        it into place."""

    @retry_on_rate_limit()
    def upload(self, local_path: str, cloud_path: str, mode: str = "overwrite") -> bool:
        """Upload via files_upload (small files) or a chunked upload
        session (64 KB pieces, append/finish) with overwrite/add mode."""
        if not self.is_authenticated():
            return False
        try:
            src = Path(local_path)
            if not src.is_file():
                return False
            dbx_path = cloud_path if cloud_path.startswith("/") else f"/{cloud_path}"
            write_mode = dropbox_sdk.files.WriteMode.overwrite if mode == "overwrite" else dropbox_sdk.files.WriteMode.add
            chunk_size = 65536
            file_size = src.stat().st_size
            with open(src, "rb") as f:
                if file_size <= chunk_size:
                    self._dbx.files_upload(f.read(), dbx_path, mode=write_mode)
                else:
                    chunk = f.read(chunk_size)
                    upload_session = self._dbx.files_upload_session_start(chunk)
                    offset = len(chunk)
                    while offset < file_size:
                        remaining = file_size - offset
                        chunk = f.read(min(chunk_size, remaining))
                        if remaining <= chunk_size:
                            self._dbx.files_upload_session_finish(
                                upload_session.start,
                                upload_session.session_id,
                                chunk,
                                dropbox_sdk.files.CommitInfo(dbx_path, mode=write_mode),
                            )
                        else:
                            self._dbx.files_upload_session_append_v2(
                                chunk,
                                upload_session.session_id,
                                offset,
                            )
                        offset += len(chunk)
            return True
        except Exception as exc:
            log.warning("Dropbox upload failed: %s", exc)
            return False
        """Upload via files_upload (small files) or a chunked upload
        session (64 KB pieces, append/finish) with overwrite/add mode."""

    @retry_on_rate_limit()
    def delete(self, cloud_id: str) -> bool:
        """Delete a file/folder via files_delete_v2."""
        if not self.is_authenticated():
            return False
        try:
            self._dbx.files_delete_v2(cloud_id)
            return True
        except Exception as exc:
            log.warning("Dropbox delete failed: %s", exc)
            return False
        """Delete a file/folder via files_delete_v2."""

    @retry_on_rate_limit()
    def get_quota(self) -> tuple[int, int]:
        """Return (used_bytes, total_bytes) from users_get_space_usage
        (individual allocation); (0, 0) on failure."""
        if not self.is_authenticated():
            return (0, 0)
        try:
            space = self._dbx.users_get_space_usage()
            used = space.used if hasattr(space, "used") else 0
            total = 0
            if hasattr(space, "allocation") and hasattr(space.allocation, "get_individual"):
                total = space.allocation.get_individual().allocated
            return (used, total)
        except Exception:
            return (0, 0)
        """Return (used_bytes, total_bytes) from users_get_space_usage
        (individual allocation); (0, 0) on failure."""


class S3Provider(CloudProvider):
    """Amazon S3 / MinIO storage provider using boto3."""

    def __init__(self, bucket_name: str = "", region: str = "us-east-1"):
        """Set the bucket (arg or AWS_S3_BUCKET env) and region (arg or
        AWS_REGION env); the boto3 client is created at authenticate."""
        self._bucket_name = bucket_name or os.environ.get("AWS_S3_BUCKET", "")
        self._region = region or os.environ.get("AWS_REGION", "us-east-1")
        self._s3 = None
        self._authenticated = False
        """Set the bucket (arg or AWS_S3_BUCKET env) and region (arg or
        AWS_REGION env); the boto3 client is created at authenticate."""

    @property
    def provider_type(self) -> CloudProviderType:
        """Return S3 as this provider's type."""
        return CloudProviderType.S3
        """Return S3 as this provider's type."""

    def authenticate(self) -> bool:
        """Create a boto3 S3 client (shared-credential chain) and verify
        the configured bucket via head_bucket."""
        try:
            import boto3
            self._s3 = boto3.client("s3", region_name=self._region)
            if self._bucket_name:
                self._s3.head_bucket(Bucket=self._bucket_name)
            self._authenticated = True
            return True
        except Exception as exc:
            log.warning("S3 authentication failed: %s", exc)
            self._authenticated = False
            return False
        """Create a boto3 S3 client (shared-credential chain) and verify
        the configured bucket via head_bucket."""

    def is_authenticated(self) -> bool:
        """Return True when the client exists and auth succeeded."""
        return self._authenticated and self._s3 is not None
        """Return True when the client exists and auth succeeded."""

    def disconnect(self) -> None:
        """Drop the client and clear the authenticated flag."""
        self._s3 = None
        self._authenticated = False
        """Drop the client and clear the authenticated flag."""

    def get_account_info(self) -> CloudAccount | None:
        """Return a synthetic account descriptor for the bucket (S3 has
        no email/quota model); note: field names below don't match the
        current CloudAccount schema (space_used/space_total)."""
        if not self.is_authenticated():
            return None
        return CloudAccount(
            provider=CloudProviderType.S3,
            account_id="AWS-S3",
            display_name=f"Amazon S3 ({self._bucket_name or 'All Buckets'})",
            email="",
            total_bytes=0,
            used_bytes=0,
            connected=True,
        )
        """Return a synthetic account descriptor for the bucket (S3 has
        no email/quota model); note: field names below don't match the
        current CloudAccount schema (space_used/space_total)."""

    def list_files(self, path: str = "/", max_results: int = 1000) -> list[CloudFile]:
        """List objects under a key prefix via list_objects_v2 (paths
        become '/<key>' and names the key's last segment)."""
        if not self.is_authenticated() or not self._bucket_name:
            return []
        prefix = path.lstrip("/")
        try:
            resp = self._s3.list_objects_v2(Bucket=self._bucket_name, Prefix=prefix, MaxKeys=max_results)
            files = []
            for obj in resp.get("Contents", []):
                key = obj.get("Key", "")
                name = Path(key).name
                size = obj.get("Size", 0)
                mtime = int(obj.get("LastModified").timestamp() * 1000) if obj.get("LastModified") else 0
                files.append(CloudFile(
                    provider=CloudProviderType.S3,
                    cloud_id=key,
                    name=name,
                    path=f"/{key}",
                    size=size,
                    modified_ms=mtime,
                ))
            return files
        except Exception as exc:
            log.warning("S3 list_files failed: %s", exc)
            return []
        """List objects under a key prefix via list_objects_v2 (paths
        become '/<key>' and names the key's last segment)."""

    def search(self, query: str, max_results: int = 1000) -> list[CloudFile]:
        """Client-side substring search over the root listing (S3 has no
        server-side name search)."""
        all_files = self.list_files("/", max_results=max_results)
        q = query.lower()
        return [f for f in all_files if q in f.name.lower()]
        """Client-side substring search over the root listing (S3 has no
        server-side name search)."""

    def download(self, cloud_id: str, local_path: str) -> bool:
        """Download an object (cloud_id = key) via download_file."""
        if not self.is_authenticated() or not self._bucket_name:
            return False
        try:
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            self._s3.download_file(self._bucket_name, cloud_id, local_path)
            return True
        except Exception as exc:
            log.warning("S3 download failed: %s", exc)
            return False
        """Download an object (cloud_id = key) via download_file."""

    def upload(self, local_path: str, cloud_path: str) -> bool:
        """Upload a local file to the cloud_path key via upload_file."""
        if not self.is_authenticated() or not self._bucket_name:
            return False
        try:
            key = cloud_path.lstrip("/")
            self._s3.upload_file(local_path, self._bucket_name, key)
            return True
        except Exception as exc:
            log.warning("S3 upload failed: %s", exc)
            return False
        """Upload a local file to the cloud_path key via upload_file."""

    def delete(self, cloud_id: str) -> bool:
        """Delete an object (cloud_id = key) via delete_object."""
        if not self.is_authenticated() or not self._bucket_name:
            return False
        try:
            self._s3.delete_object(Bucket=self._bucket_name, Key=cloud_id)
            return True
        except Exception as exc:
            log.warning("S3 delete failed: %s", exc)
            return False
        """Delete an object (cloud_id = key) via delete_object."""

    def get_quota(self) -> tuple[int, int]:
        """Return (0, 0) — S3 exposes no bucket quota."""
        return (0, 0)
        """Return (0, 0) — S3 exposes no bucket quota."""


# ---------------------------------------------------------------------------
# CloudManager – unified interface
# ---------------------------------------------------------------------------

class CloudManager(QObject):
    """Unified cloud storage manager supporting multiple providers."""

    account_connected = Signal(str)
    account_disconnected = Signal(str)
    sync_started = Signal(str)
    sync_completed = Signal(str, bool)

    def __init__(self, parent=None):
        """Instantiate all four providers (OneDrive, Google Drive,
        Dropbox, S3) and prepare the ~/.nexus/cloud_cache directory."""
        super().__init__(parent)
        self._providers: dict[CloudProviderType, CloudProvider] = {
            CloudProviderType.ONEDRIVE: OneDriveProvider(),
            CloudProviderType.GOOGLE_DRIVE: GoogleDriveProvider(),
            CloudProviderType.DROPBOX: DropboxProvider(),
            CloudProviderType.S3: S3Provider(),
        }
        self._cache_dir = Path.home() / ".nexus" / "cloud_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        """Instantiate all four providers (OneDrive, Google Drive,
        Dropbox, S3) and prepare the ~/.nexus/cloud_cache directory."""

    def get_provider(self, provider_type: CloudProviderType) -> CloudProvider | None:
        """Return the provider instance for a type, or None."""
        return self._providers.get(provider_type)
        """Return the provider instance for a type, or None."""

    def get_connected_providers(self) -> list[CloudProvider]:
        """Return only providers that currently report authenticated."""
        return [p for p in self._providers.values() if p.is_authenticated()]
        """Return only providers that currently report authenticated."""

    def connect_provider(self, provider_type: CloudProviderType) -> bool:
        """Authenticate a provider and emit account_connected on
        success."""
        provider = self._providers.get(provider_type)
        if not provider:
            return False
        ok = provider.authenticate()
        if ok:
            self.account_connected.emit(provider_type.name)
        return ok
        """Authenticate a provider and emit account_connected on
        success."""

    def disconnect_provider(self, provider_type: CloudProviderType) -> None:
        """Disconnect a provider and emit account_disconnected."""
        provider = self._providers.get(provider_type)
        if provider:
            provider.disconnect()
            self.account_disconnected.emit(provider_type.name)
        """Disconnect a provider and emit account_disconnected."""

    def list_all_cloud_files(self, max_per_provider: int = 1000) -> list[CloudFile]:
        """List root files from every connected provider in parallel
        (ThreadPoolExecutor, up to 4 workers) and merge the results."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        connected = self.get_connected_providers()
        if not connected:
            return []

        results: list[CloudFile] = []

        def _fetch(provider: CloudProvider) -> list[CloudFile]:
            """List one provider's root, mapping exceptions to []."""
            try:
                return provider.list_files("/", max_per_provider)
            except Exception as exc:
                log.warning("Failed to list files from %s: %s", provider.provider_type.name, exc)
                return []
            """List one provider's root, mapping exceptions to []."""

        with ThreadPoolExecutor(max_workers=min(len(connected), 4)) as executor:
            futures = {executor.submit(_fetch, p): p for p in connected}
            for future in as_completed(futures):
                results.extend(future.result())
        return results
        """List root files from every connected provider in parallel
        (ThreadPoolExecutor, up to 4 workers) and merge the results."""

    def search_all(self, query: str, max_results: int = 1000) -> list[CloudFile]:
        """Run the name search sequentially across every connected
        provider, merging (not deduplicating) the results."""
        results: list[CloudFile] = []
        for provider in self.get_connected_providers():
            try:
                files = provider.search(query, max_results)
                results.extend(files)
            except Exception as exc:
                log.warning("Failed to search %s: %s", provider.provider_type.name, exc)
        return results
        """Run the name search sequentially across every connected
        provider, merging (not deduplicating) the results."""
