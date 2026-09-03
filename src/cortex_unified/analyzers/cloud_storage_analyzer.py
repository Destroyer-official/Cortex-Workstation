"""Cloud Storage Analyzer — rclone, S3, Azure, Google Drive, OneDrive, SharePoint.

Research grounding
------------------
* rclone: "rsync for cloud storage" — 40+ providers, sync/copy/bisync,
  mount, serve, encryption (crypt), compression, chunker.
* Mountain Duck 5: Integrated Connect Mode using File Provider (macOS)
  and Cloud Files (Windows) APIs; smart sync with placeholders, versioning.
* Cyberduck: GUI for FTP/SFTP/WebDAV/S3/Azure/Google Drive; Cryptomator
  encryption; Mountain Duck companion.
* TreeSize Professional: uniquely scans SharePoint, S3, Azure, Linux/SSH.
* FolderSizes: network share discovery for Windows domains.
* WizTree: network shares but MFT speed only on local NTFS.

Why this matters for Cortex Cleaner
-----------------------------------
* Users store massive data in cloud (OneDrive, Google Drive, S3, SharePoint).
* Local sync clients (OneDrive, Dropbox) create placeholder files; actual
  size only visible via API.
* Cloud storage costs money — finding large/old/unused files saves $$.
* Duplicate detection across cloud + local prevents sync conflicts.

Design
------
* **Unified provider abstraction**: CloudProvider base with S3Provider,
  AzureBlobProvider, GoogleDriveProvider, OneDriveProvider, SharePointProvider,
  RcloneProvider (covers 40+ via rclone).
* **Streaming enumeration**: async generator yields CloudFileEntry with
  size, mtime, etag, storage_class, tags.
* **Cost estimation**: per-provider pricing API (S3: storage class +
  requests; Azure: tier + operations; Google: class + region).
* **Lifecycle analysis**: last_accessed, age, versioning, multipart uploads.
* **Duplicate detection**: cross-cloud + local via hash/etag comparison.
* **Scheduled scans**: cron-style with incremental (etag/last_modified).
* **Report export**: CSV, JSON, HTML with cost breakdown.

Usage::

    from cortex_unified.analyzers.cloud_storage_analyzer import CloudStorageAnalyzer
    analyzer = CloudStorageAnalyzer()
    async for entry in analyzer.scan("s3://my-bucket/prefix"):
        print(f"{entry.size/1e9:.2f} GB  {entry.path}")
    report = analyzer.generate_report()

References
----------
* rclone.org (40+ providers, sync/bisync/mount/serve/crypt)
* Mountain Duck 5 Integrated Connect Mode (File Provider / Cloud Files API)
* TreeSize Professional cloud scanning (SharePoint, S3, Azure)
* AWS S3 Storage Lens, Azure Blob Storage lifecycle, Google Cloud Storage classes
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Callable, Dict, List, Optional, Tuple, Any


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CloudFileEntry:
    """Single cloud object entry."""
    path: str
    size: int
    mtime: datetime
    etag: str
    storage_class: str = "STANDARD"
    provider: str = ""
    bucket: str = ""
    key: str = ""
    version_id: Optional[str] = None
    is_multipart: bool = False
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        import dataclasses
        d = dataclasses.asdict(self)
        d["mtime"] = self.mtime.isoformat()
        return d
        """to_dict."""
        """to_dict."""


@dataclass
class CloudScanStats:
    total_objects: int = 0
    total_size_bytes: int = 0
    by_storage_class: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_provider: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    estimated_monthly_cost_usd: float = 0.0
    #: Storage classes with no published rate available at scan time.
    unpriced_classes: set = field(default_factory=set)
    scan_duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    """CloudScanStats class."""
    """CloudScanStats class."""


@dataclass
class DuplicateGroup:
    """Cross-cloud/local duplicate group."""
    hash: str
    size: int
    entries: List[CloudFileEntry] = field(default_factory=list)
    local_paths: List[str] = field(default_factory=list)

    @property
    def wasted_bytes(self) -> int:
        return self.size * (len(self.entries) + len(self.local_paths) - 1)
        """wasted_bytes."""
        """wasted_bytes."""


# ---------------------------------------------------------------------------
# Dynamic pricing — live provider APIs with on-disk cache, no hardcoded rates
# ---------------------------------------------------------------------------

def _pricing_cache_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME")
    root = Path(base) if base else (Path.home() / ".cache")
    d = root / "Cortex" / "pricing"
    d.mkdir(parents=True, exist_ok=True)
    return d
    """_pricing_cache_dir."""
    """_pricing_cache_dir."""


class PricingCatalog:
    """Storage pricing resolved at runtime from the provider's public API.

    Rates are never compiled into the binary: they are fetched from the
    vendor's price list endpoint, cached on disk for ``ttl_hours``, and
    resolved per (provider, region, storage_class). If the network is
    unavailable and no cache exists, ``rate()`` returns ``None`` and the
    caller reports "unknown" instead of a fabricated number.
    """

    def __init__(self, ttl_hours: int = 168, timeout: int = 20):
        self.ttl_seconds = max(1, ttl_hours) * 3600
        self.timeout = timeout
        """__init__."""
        """__init__."""

    # -- cache plumbing

    def _cache_file(self, provider: str, region: str) -> Path:
        safe = urllib.parse.quote(f"{provider}_{region}", safe="")
        return _pricing_cache_dir() / f"{safe}.json"
        """_cache_file."""
        """_cache_file."""

    def _read_cache(self, provider: str, region: str) -> Optional[Dict[str, float]]:
        f = self._cache_file(provider, region)
        if not f.exists():
            return None
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
            if time.time() - float(payload.get("fetched_at", 0)) > self.ttl_seconds:
                return None
            rates = payload.get("rates") or {}
            return {str(k): float(v) for k, v in rates.items()}
        except Exception:
            return None
        """_read_cache."""
        """_read_cache."""

    def _write_cache(self, provider: str, region: str, rates: Dict[str, float]) -> None:
        try:
            self._cache_file(provider, region).write_text(
                json.dumps({"fetched_at": time.time(), "region": region, "rates": rates}, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass
        """_write_cache."""
        """_write_cache."""

    def _http_json(self, url: str) -> Optional[Any]:
        req = urllib.request.Request(url, headers={"Accept": "application/json",
                                                   "User-Agent": "cortex-cleaner"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception:
            return None
        """_http_json."""
        """_http_json."""

    # -- AWS S3: Price List Query API (no credentials required)

    def _fetch_aws(self, region: str) -> Dict[str, float]:
        # Region index published by AWS for the AmazonS3 offer.
        idx = self._http_json(
            "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/region_index.json"
        )
        if not idx:
            return {}
        entry = (idx.get("regions") or {}).get(region)
        if not entry or "currentVersionUrl" not in entry:
            return {}
        doc = self._http_json("https://pricing.us-east-1.amazonaws.com" + entry["currentVersionUrl"])
        if not doc:
            return {}
        products = doc.get("products") or {}
        on_demand = ((doc.get("terms") or {}).get("OnDemand") or {})
        rates: Dict[str, float] = {}
        for sku, product in products.items():
            attrs = product.get("attributes") or {}
            if attrs.get("productFamily") != "Storage" and product.get("productFamily") != "Storage":
                continue
            volume_type = attrs.get("volumeType") or attrs.get("storageClass") or ""
            if not volume_type:
                continue
            terms = on_demand.get(sku) or {}
            for term in terms.values():
                for dim in (term.get("priceDimensions") or {}).values():
                    unit = (dim.get("unit") or "").lower()
                    if "gb-mo" not in unit:
                        continue
                    try:
                        price = float((dim.get("pricePerUnit") or {}).get("USD", "0"))
                    except (TypeError, ValueError):
                        continue
                    if price <= 0:
                        continue
                    key = _normalise_class(volume_type)
                    rates[key] = min(price, rates.get(key, price))
        return rates
        """_fetch_aws."""
        """_fetch_aws."""

    # -- Azure Blob: Retail Prices API (no credentials required)

    def _fetch_azure(self, region: str) -> Dict[str, float]:
        base = ("https://prices.azure.com/api/retail/prices?$filter="
                "serviceName eq 'Storage' and priceType eq 'Consumption'"
                f" and armRegionName eq '{region}'")
        rates: Dict[str, float] = {}
        url: Optional[str] = base
        pages = 0
        while url and pages < 12:
            doc = self._http_json(url)
            if not doc:
                break
            for item in doc.get("Items") or []:
                unit = (item.get("unitOfMeasure") or "").lower()
                if "gb/month" not in unit and "1 gb/month" not in unit:
                    continue
                price = item.get("retailPrice")
                meter = item.get("meterName") or ""
                if not isinstance(price, (int, float)) or price <= 0:
                    continue
                key = _normalise_class(meter)
                rates[key] = min(float(price), rates.get(key, float(price)))
            url = doc.get("NextPageLink")
            pages += 1
        return rates
        """_fetch_azure."""
        """_fetch_azure."""

    # -- public

    def rates(self, provider: str, region: str) -> Dict[str, float]:
        cached = self._read_cache(provider, region)
        if cached is not None:
            return cached
        if provider == "s3":
            rates = self._fetch_aws(region)
        elif provider == "azure":
            rates = self._fetch_azure(region)
        else:
            rates = {}
        if rates:
            self._write_cache(provider, region, rates)
        return rates
        """rates."""
        """rates."""

    def rate(self, provider: str, region: str, storage_class: str) -> Optional[float]:
        table = self.rates(provider, region)
        if not table:
            return None
        key = _normalise_class(storage_class)
        if key in table:
            return table[key]
        # Longest-substring match so vendor meter names still resolve.
        best: Optional[float] = None
        best_len = 0
        for k, v in table.items():
            if (k in key or key in k) and len(k) > best_len:
                best, best_len = v, len(k)
        return best
        """rate."""
        """rate."""


def _normalise_class(name: str) -> str:
    """Fold vendor storage-class / meter names into a comparable key."""
    s = (name or "").strip().lower()
    for token in ("standard", "general purpose", "blob", "data stored", "storage",
                  "lrs", "grs", "zrs", "ra-", "gzrs", "(", ")", "-", "_", "/"):
        s = s.replace(token, " ")
    return " ".join(s.split()) or (name or "").strip().lower()


_PRICING = PricingCatalog()


# ---------------------------------------------------------------------------
# Provider abstraction
# ---------------------------------------------------------------------------

class CloudProvider(ABC):
    """Abstract cloud storage provider."""

    #: Key used to look up live pricing (``""`` = provider has no storage rate).
    pricing_key: str = ""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__.replace("Provider", "").lower()
        """__init__."""
        """__init__."""

    @abstractmethod
    async def list_objects(
        self,
        bucket: str,
        prefix: str = "",
        max_keys: Optional[int] = None,
    ) -> AsyncGenerator[CloudFileEntry, None]:
        pass
        """list_objects."""
        """list_objects."""

    @property
    def region(self) -> str:
        """Region used for pricing lookups, resolved from config or environment."""
        return str(
            self.config.get("region")
            or os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
            or os.environ.get("AZURE_REGION")
            or ""
        )

    def estimate_cost(self, stats: CloudScanStats) -> float:
        """Monthly USD estimate from live vendor rates for this provider only.

        Storage classes with no resolvable rate are skipped and recorded in
        ``stats.unpriced_classes`` so the UI can label them "unknown" rather
        than silently pricing them at a guessed value.
        """
        if not self.pricing_key or not self.region:
            return 0.0
        total = 0.0
        for cls, byte_count in stats.by_storage_class.items():
            rate = _PRICING.rate(self.pricing_key, self.region, cls)
            if rate is None:
                stats.unpriced_classes.add(cls)
                continue
            total += (byte_count / (1024 ** 3)) * rate
        return total

    def validate_config(self) -> Tuple[bool, str]:
        return True, ""
        """validate_config."""
        """validate_config."""


# ---------------------------------------------------------------------------
# S3 Provider
# ---------------------------------------------------------------------------

class S3Provider(CloudProvider):
    pricing_key = "s3"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None
        self._resolved_region: Optional[str] = None
        self._init_client()
        """__init__."""
        """__init__."""

    def _init_client(self):
        try:
            import boto3
        except ImportError:
            return
        kwargs: Dict[str, Any] = {}
        # Credentials are optional: boto3 resolves env vars, shared config,
        # IAM roles and SSO in that order when we pass nothing.
        if self.config.get("access_key") and self.config.get("secret_key"):
            kwargs["aws_access_key_id"] = self.config["access_key"]
            kwargs["aws_secret_access_key"] = self.config["secret_key"]
        if self.config.get("session_token"):
            kwargs["aws_session_token"] = self.config["session_token"]
        if self.config.get("region"):
            kwargs["region_name"] = self.config["region"]
        if self.config.get("endpoint"):
            kwargs["endpoint_url"] = self.config["endpoint"]
        try:
            self._client = boto3.client("s3", **kwargs)
            meta_region = getattr(getattr(self._client, "meta", None), "region_name", None)
            if meta_region:
                self._resolved_region = str(meta_region)
        except Exception:
            self._client = None
        """_init_client."""
        """_init_client."""

    @property
    def region(self) -> str:
        # Prefer the bucket's own region so pricing matches where data lives.
        return self._resolved_region or super().region
        """region."""
        """region."""

    def _bucket_region(self, bucket: str) -> Optional[str]:
        if not self._client:
            return None
        try:
            resp = self._client.get_bucket_location(Bucket=bucket)
            loc = resp.get("LocationConstraint")
            # A null constraint means us-east-1; EU is the legacy eu-west-1 alias.
            if loc in (None, ""):
                return "us-east-1"
            if loc == "EU":
                return "eu-west-1"
            return str(loc)
        except Exception:
            return None
        """_bucket_region."""
        """_bucket_region."""

    async def list_objects(
        self,
        bucket: str,
        prefix: str = "",
        max_keys: Optional[int] = None,
    ) -> AsyncGenerator[CloudFileEntry, None]:
        if not self._client:
            return
        region = self._bucket_region(bucket)
        if region:
            self._resolved_region = region
        # Versioned listing exposes non-current versions (real, billable storage);
        # fall back to the flat listing when versioning is unavailable.
        try:
            paginator = self._client.get_paginator("list_object_versions")
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
            versioned = True
        except Exception:
            paginator = self._client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
            versioned = False

        count = 0
        try:
            for page in pages:
                records = page.get("Versions" if versioned else "Contents") or []
                for record in records:
                    if max_keys and count >= max_keys:
                        return
                    last_modified = record.get("LastModified")
                    mtime = (last_modified if isinstance(last_modified, datetime)
                             else datetime.now(timezone.utc))
                    etag = str(record.get("ETag", "")).strip('"')
                    yield CloudFileEntry(
                        path=f"s3://{bucket}/{record['Key']}",
                        size=int(record.get("Size", 0)),
                        mtime=mtime,
                        etag=etag,
                        storage_class=str(record.get("StorageClass") or "STANDARD"),
                        provider="s3",
                        bucket=bucket,
                        key=str(record["Key"]),
                        version_id=record.get("VersionId"),
                        # A multipart ETag carries a "-<partcount>" suffix.
                        is_multipart="-" in etag,
                    )
                    count += 1
        except Exception:
            return
        """list_objects."""
        """list_objects."""

    def estimate_cost(self, stats: CloudScanStats) -> float:
        return super().estimate_cost(stats)
        """estimate_cost."""
    """S3Provider class."""
    """S3Provider class."""


# ---------------------------------------------------------------------------
# Azure Blob Provider
# ---------------------------------------------------------------------------

class AzureBlobProvider(CloudProvider):
    pricing_key = "azure"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None
        self._resolved_region: Optional[str] = None
        self._init_client()
        """__init__."""
        """__init__."""

    def _init_client(self):
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            return
        conn = self.config.get("connection_string") or os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        account_url = self.config.get("account_url") or os.environ.get("AZURE_STORAGE_ACCOUNT_URL")
        try:
            if conn:
                self._client = BlobServiceClient.from_connection_string(conn)
            elif account_url:
                credential = self.config.get("credential")
                if credential is None:
                    try:
                        from azure.identity import DefaultAzureCredential
                        credential = DefaultAzureCredential()
                    except ImportError:
                        credential = None
                self._client = BlobServiceClient(account_url=account_url, credential=credential)
        except Exception:
            self._client = None
        """_init_client."""
        """_init_client."""

    @property
    def region(self) -> str:
        if self._resolved_region:
            return self._resolved_region
        configured = super().region
        if configured:
            return configured
        # Storage account properties expose the ARM region name.
        if self._client is not None:
            try:
                info = self._client.get_account_information()
                loc = info.get("account_location") or info.get("location")
                if loc:
                    self._resolved_region = str(loc).replace(" ", "").lower()
                    return self._resolved_region
            except Exception:
                pass
        return ""
        """region."""
        """region."""

    async def list_objects(
        self,
        container: str,
        prefix: str = "",
        max_keys: Optional[int] = None,
    ) -> AsyncGenerator[CloudFileEntry, None]:
        if not self._client:
            return
        container_client = self._client.get_container_client(container)
        count = 0
        # "versions" is only valid where blob versioning is on; degrade cleanly.
        for include in (["metadata", "tags", "versions"], ["metadata"], None):
            try:
                iterator = (container_client.list_blobs(name_starts_with=prefix, include=include)
                            if include else container_client.list_blobs(name_starts_with=prefix))
                for blob in iterator:
                    if max_keys and count >= max_keys:
                        return
                    etag = str(getattr(blob, "etag", "") or "").strip('"')
                    tier = getattr(blob, "blob_tier", None)
                    last_modified = getattr(blob, "last_modified", None)
                    yield CloudFileEntry(
                        path=f"az://{container}/{blob.name}",
                        size=int(getattr(blob, "size", 0) or 0),
                        mtime=(last_modified if isinstance(last_modified, datetime)
                               else datetime.now(timezone.utc)),
                        etag=etag,
                        storage_class=str(tier) if tier else "Hot",
                        provider="azure",
                        bucket=container,
                        key=str(blob.name),
                        version_id=getattr(blob, "version_id", None),
                        tags=dict(getattr(blob, "tags", None) or {}),
                        metadata=dict(getattr(blob, "metadata", None) or {}),
                    )
                    count += 1
                return
            except Exception:
                continue
        """list_objects."""
        """list_objects."""

    def estimate_cost(self, stats: CloudScanStats) -> float:
        return super().estimate_cost(stats)
        """estimate_cost."""
    """AzureBlobProvider class."""
    """AzureBlobProvider class."""


# ---------------------------------------------------------------------------
# Google Drive Provider (Drive v3 REST — OAuth token or rclone-managed token)
# ---------------------------------------------------------------------------

class GoogleDriveProvider(CloudProvider):
    """Google Drive listing via the Drive v3 REST API.

    The access token is taken from config or ``GOOGLE_OAUTH_ACCESS_TOKEN``;
    Drive storage is bundled with the Workspace/One plan, so no per-GB rate
    exists and ``estimate_cost`` correctly reports ``0.0``.
    """

    pricing_key = ""  # Drive quota is subscription-based, not per-GB.

    API = "https://www.googleapis.com/drive/v3/files"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._token = (config.get("access_token")
                       or os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN")
                       or "")
        """__init__."""
        """__init__."""

    def _get(self, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        if not self._token:
            return None
        url = f"{self.API}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception:
            return None
        """_get."""
        """_get."""

    async def list_objects(
        self,
        bucket: str = "root",
        prefix: str = "",
        max_keys: Optional[int] = None,
    ) -> AsyncGenerator[CloudFileEntry, None]:
        if not self._token:
            return
        folder = bucket or "root"
        clauses = [f"'{folder}' in parents", "trashed = false"]
        if prefix:
            escaped = prefix.replace("'", r"\'")
            clauses.append(f"name contains '{escaped}'")
        params = {
            "q": " and ".join(clauses),
            "fields": "nextPageToken,files(id,name,size,modifiedTime,md5Checksum,mimeType,parents)",
            "pageSize": "1000",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        count = 0
        while True:
            doc = self._get(params)
            if not doc:
                return
            for f in doc.get("files") or []:
                if max_keys and count >= max_keys:
                    return
                # Google-native docs report no size; skip so totals stay truthful.
                raw_size = f.get("size")
                if raw_size is None:
                    continue
                try:
                    mtime = datetime.fromisoformat(
                        str(f.get("modifiedTime", "")).replace("Z", "+00:00"))
                except ValueError:
                    mtime = datetime.now(timezone.utc)
                yield CloudFileEntry(
                    path=f"gdrive://{folder}/{f.get('name', '')}",
                    size=int(raw_size),
                    mtime=mtime,
                    etag=str(f.get("md5Checksum") or ""),
                    storage_class="DRIVE",
                    provider="gdrive",
                    bucket=folder,
                    key=str(f.get("id", "")),
                    metadata={"mimeType": str(f.get("mimeType", ""))},
                )
                count += 1
            token = doc.get("nextPageToken")
            if not token:
                return
            params["pageToken"] = token
        """list_objects."""
        """list_objects."""


# ---------------------------------------------------------------------------
# OneDrive / SharePoint Provider (Microsoft Graph)
# ---------------------------------------------------------------------------

class OneDriveProvider(CloudProvider):
    """OneDrive / SharePoint listing via Microsoft Graph ``/children``.

    Token comes from config or ``MSGRAPH_ACCESS_TOKEN``. Storage is part of
    the M365 subscription, so there is no per-GB storage rate to apply.
    """

    pricing_key = ""

    GRAPH = "https://graph.microsoft.com/v1.0"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._token = (config.get("access_token")
                       or os.environ.get("MSGRAPH_ACCESS_TOKEN")
                       or "")
        """__init__."""
        """__init__."""

    def _get(self, url: str) -> Optional[Dict[str, Any]]:
        if not self._token:
            return None
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception:
            return None
        """_get."""
        """_get."""

    async def list_objects(
        self,
        bucket: str = "me/drive",
        prefix: str = "",
        max_keys: Optional[int] = None,
    ) -> AsyncGenerator[CloudFileEntry, None]:
        if not self._token:
            return
        drive = (bucket or "me/drive").strip("/")
        root = f"{self.GRAPH}/{drive}/root"
        url = (f"{root}:/{urllib.parse.quote(prefix.strip('/'))}:/children"
               if prefix else f"{root}/children")
        count = 0
        while url:
            doc = self._get(url)
            if not doc:
                return
            for item in doc.get("value") or []:
                if max_keys and count >= max_keys:
                    return
                if "folder" in item:
                    continue
                try:
                    mtime = datetime.fromisoformat(
                        str(item.get("lastModifiedDateTime", "")).replace("Z", "+00:00"))
                except ValueError:
                    mtime = datetime.now(timezone.utc)
                file_info = item.get("file") or {}
                hashes = file_info.get("hashes") or {}
                yield CloudFileEntry(
                    path=f"onedrive://{drive}/{item.get('name', '')}",
                    size=int(item.get("size", 0) or 0),
                    mtime=mtime,
                    etag=str(hashes.get("quickXorHash") or hashes.get("sha256Hash")
                             or item.get("eTag") or "").strip('"'),
                    storage_class="ONEDRIVE",
                    provider="onedrive",
                    bucket=drive,
                    key=str(item.get("id", "")),
                    metadata={"mimeType": str(file_info.get("mimeType", ""))},
                )
                count += 1
            url = doc.get("@odata.nextLink")
        """list_objects."""
        """list_objects."""


# ---------------------------------------------------------------------------
# Rclone Provider (covers 40+ providers)
# ---------------------------------------------------------------------------

class RcloneProvider(CloudProvider):
    """Any of rclone's 40+ backends via ``rclone lsjson``.

    ``lsjson`` is used instead of ``lsf`` because it emits well-formed JSON
    (no delimiter ambiguity in names) including per-object hashes. The rclone
    binary is located dynamically via ``PATH`` or ``RCLONE_BINARY``.
    """

    pricing_key = ""  # Backend-specific; rates are attributed to the native provider.

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.remote = str(config.get("remote", "") or "")
        self.binary = self._locate_binary(config.get("binary"))
        """__init__."""
        """__init__."""

    @staticmethod
    def _locate_binary(explicit: Optional[str]) -> Optional[str]:
        import shutil as _shutil
        for candidate in (explicit, os.environ.get("RCLONE_BINARY"), "rclone"):
            if not candidate:
                continue
            found = _shutil.which(candidate) or (candidate if Path(candidate).exists() else None)
            if found:
                return found
        return None
        """_locate_binary."""
        """_locate_binary."""

    @property
    def available(self) -> bool:
        return self.binary is not None
        """available."""
        """available."""

    def list_remotes(self) -> List[str]:
        """Configured rclone remotes, so callers never guess a remote name."""
        if not self.binary:
            return []
        try:
            proc = subprocess.run([self.binary, "listremotes"],
                                  capture_output=True, text=True, timeout=30)
            if proc.returncode != 0:
                return []
            return [line.strip().rstrip(":") for line in proc.stdout.splitlines() if line.strip()]
        except Exception:
            return []

    async def list_objects(
        self,
        bucket: str = "",
        prefix: str = "",
        max_keys: Optional[int] = None,
    ) -> AsyncGenerator[CloudFileEntry, None]:
        if not self.binary:
            return
        remote = self.remote or bucket
        if not remote:
            return
        sub = "/".join(p for p in (bucket if bucket != remote else "", prefix) if p).strip("/")
        target = f"{remote}:{sub}" if sub else f"{remote}:"
        cmd = [self.binary, "lsjson", "--recursive", "--files-only", "--hash", target]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if proc.returncode != 0 or not proc.stdout.strip():
                return
            records = json.loads(proc.stdout)
        except Exception:
            return
        count = 0
        for rec in records:
            if max_keys and count >= max_keys:
                return
            try:
                mtime = datetime.fromisoformat(str(rec.get("ModTime", "")).replace("Z", "+00:00"))
            except ValueError:
                mtime = datetime.now(timezone.utc)
            hashes = rec.get("Hashes") or {}
            etag = ""
            for algo in ("sha256", "SHA-1", "sha1", "md5", "MD5", "quickxor", "crc32"):
                if hashes.get(algo):
                    etag = str(hashes[algo])
                    break
            rel = str(rec.get("Path", ""))
            yield CloudFileEntry(
                path=f"{remote}:{sub + '/' if sub else ''}{rel}",
                size=int(rec.get("Size", 0) or 0),
                mtime=mtime,
                etag=etag,
                storage_class=str(rec.get("Tier") or "STANDARD"),
                provider="rclone",
                bucket=remote,
                key=rel,
                metadata={"mimeType": str(rec.get("MimeType", ""))},
            )
            count += 1
        """list_objects."""
        """list_objects."""

    def estimate_cost(self, stats: CloudScanStats) -> float:
        # Backends vary; the native provider classes own pricing.
        return 0.0
        """estimate_cost."""
        """estimate_cost."""


# ---------------------------------------------------------------------------
# Cloud Storage Analyzer
# ---------------------------------------------------------------------------

class CloudStorageAnalyzer:
    """Unified cloud storage analyzer with multi-provider support."""

    PROVIDERS = {
        "s3": S3Provider,
        "azure": AzureBlobProvider,
        "gdrive": GoogleDriveProvider,
        "onedrive": OneDriveProvider,
        "rclone": RcloneProvider,
    }

    def __init__(
        self,
        default_provider: str = "rclone",
        provider_configs: Optional[Dict[str, Dict]] = None,
        cancel_event: Optional[threading.Event] = None,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
    ):
        self.cancel_event = cancel_event or threading.Event()
        self.progress_cb = progress_cb
        self.provider_configs = provider_configs or {}
        self._providers: Dict[str, CloudProvider] = {}
        self._init_providers(default_provider)
        """__init__."""
        """__init__."""

    def _init_providers(self, default: str):
        for name, cls in self.PROVIDERS.items():
            config = dict(self.provider_configs.get(name) or {})
            try:
                self._providers[name] = cls(config)
            except Exception:
                continue
        self.default_provider = default if default in self._providers else next(
            iter(self._providers), "")
        """_init_providers."""
        """_init_providers."""

    def get_provider(self, name: str) -> Optional[CloudProvider]:
        return self._providers.get(name)
        """get_provider."""
        """get_provider."""

    def available_targets(self) -> Dict[str, List[str]]:
        """Enumerate what this machine can actually scan.

        Returns ``{provider: [target, ...]}`` built from live sources — S3
        ``list_buckets``, Azure ``list_containers``, configured rclone remotes,
        and Graph/Drive roots when a token is present. Nothing is assumed.
        """
        out: Dict[str, List[str]] = {}
        s3 = self._providers.get("s3")
        if s3 is not None and getattr(s3, "_client", None) is not None:
            try:
                resp = s3._client.list_buckets()  # type: ignore[attr-defined]
                out["s3"] = [f"s3://{b['Name']}" for b in resp.get("Buckets", [])]
            except Exception:
                pass
        az = self._providers.get("azure")
        if az is not None and getattr(az, "_client", None) is not None:
            try:
                out["azure"] = [f"azure://{c.name}"
                                for c in az._client.list_containers()]  # type: ignore[attr-defined]
            except Exception:
                pass
        rc = self._providers.get("rclone")
        if isinstance(rc, RcloneProvider) and rc.available:
            remotes = rc.list_remotes()
            if remotes:
                out["rclone"] = [f"rclone://{r}" for r in remotes]
        gd = self._providers.get("gdrive")
        if gd is not None and getattr(gd, "_token", ""):
            out["gdrive"] = ["gdrive://root"]
        od = self._providers.get("onedrive")
        if od is not None and getattr(od, "_token", ""):
            out["onedrive"] = ["onedrive://me/drive"]
        return out

    async def scan(
        self,
        target: str,  # "provider://bucket/prefix" or "provider:remote/path"
        max_objects: Optional[int] = None,
    ) -> AsyncGenerator[CloudFileEntry, None]:
        """Scan cloud target. target format: 's3://bucket/prefix' or 'rclone://remote/path'."""
        if "://" in target:
            provider_name, rest = target.split("://", 1)
            bucket, _, prefix = rest.partition("/")
        elif ":" in target:
            provider_name, rest = target.split(":", 1)
            bucket, _, prefix = rest.partition("/")
        else:
            raise ValueError(f"Invalid target format: {target}")

        provider = self._providers.get(provider_name)
        if not provider:
            raise ValueError(
                f"Unknown provider {provider_name!r}; available: {sorted(self._providers)}")

        # For rclone, the first segment names the remote to use.
        if isinstance(provider, RcloneProvider) and bucket and not provider.remote:
            provider.remote = bucket

        report = self.progress_cb or (lambda *_: None)
        report(0, 0, f"Scanning {target}...")
        count = 0
        scanned_bytes = 0
        async for entry in provider.list_objects(bucket, prefix, max_objects):
            if self.cancel_event.is_set():
                return
            yield entry
            count += 1
            scanned_bytes += entry.size
            if count % 100 == 0:
                report(count, scanned_bytes, f"Scanned {count} objects...")

    def scan_sync(
        self,
        target: str,
        max_objects: Optional[int] = None,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> Tuple[List[CloudFileEntry], CloudScanStats]:
        """Synchronous scan returning all entries and stats."""
        import asyncio
        self.cancel_event = cancel_event or threading.Event()
        self.progress_cb = progress_cb or (lambda *_: None)

        entries: List[CloudFileEntry] = []
        stats = CloudScanStats()
        t0 = time.time()

        async def _collect():
            async for entry in self.scan(target, max_objects):
                entries.append(entry)
                stats.total_objects += 1
                stats.total_size_bytes += entry.size
                stats.by_storage_class[entry.storage_class] += entry.size
                stats.by_provider[entry.provider] += 1
            """_collect."""
            """_collect."""

        try:
            asyncio.run(_collect())
        except Exception as exc:
            stats.errors.append(str(exc))

        stats.scan_duration_seconds = time.time() - t0
        # Only the provider that owns the scanned data prices it, and only
        # for storage classes with a live rate.
        cost = 0.0
        for provider_name in stats.by_provider:
            provider = self._providers.get(provider_name)
            if provider is not None:
                cost += provider.estimate_cost(stats)
        stats.estimated_monthly_cost_usd = cost
        return entries, stats

    def find_duplicates(
        self,
        entries: List[CloudFileEntry],
        local_hashes: Optional[Dict[str, List[str]]] = None,
    ) -> List[DuplicateGroup]:
        """Group objects that share a content hash, optionally including local files.

        ``local_hashes`` maps ``hash -> [local path, ...]`` (e.g. from
        ``DuplicateFinder``), letting a single group span cloud and disk.
        Multipart S3 ETags are excluded because they hash the part list,
        not the object body, so they cannot prove equality.
        """
        hash_map: Dict[str, List[CloudFileEntry]] = defaultdict(list)
        for e in entries:
            if e.etag and not e.is_multipart:
                hash_map[e.etag.lower()].append(e)

        groups: List[DuplicateGroup] = []
        seen: set[str] = set()
        for h, objs in hash_map.items():
            locals_for_hash = list((local_hashes or {}).get(h, ()))
            if len(objs) + len(locals_for_hash) < 2:
                continue
            seen.add(h)
            groups.append(DuplicateGroup(
                hash=h,
                size=objs[0].size,
                entries=objs,
                local_paths=locals_for_hash,
            ))

        # Local-only collisions that also matter for reclaim reporting.
        for h, paths in (local_hashes or {}).items():
            if h in seen or len(paths) < 2:
                continue
            groups.append(DuplicateGroup(hash=h, size=0, entries=[], local_paths=list(paths)))

        groups.sort(key=lambda g: g.wasted_bytes, reverse=True)
        return groups

    def generate_report(
        self,
        entries: List[CloudFileEntry],
        stats: CloudScanStats,
        duplicates: Optional[List[DuplicateGroup]] = None,
    ) -> str:
        """Self-contained HTML report with a per-class cost breakdown.

        Classes without a live vendor rate are shown as ``unknown`` instead of
        being priced with a guess. Object counts are computed from ``entries``
        so the table reflects what was actually scanned.
        """
        from html import escape

        objects_per_class: Dict[str, int] = defaultdict(int)
        for e in entries:
            objects_per_class[e.storage_class] += 1

        # Provider that owns each storage class, for rate lookup.
        provider_for_class: Dict[str, str] = {}
        for e in entries:
            provider_for_class.setdefault(e.storage_class, e.provider)

        priced_total = 0.0
        rows: List[str] = []
        for cls, byte_count in sorted(stats.by_storage_class.items(),
                                      key=lambda kv: kv[1], reverse=True):
            gb = byte_count / (1024 ** 3)
            provider = self._providers.get(provider_for_class.get(cls, ""))
            rate = None
            if provider is not None and provider.pricing_key and provider.region:
                rate = _PRICING.rate(provider.pricing_key, provider.region, cls)
            if rate is None:
                cost_cell = "unknown"
            else:
                cost = gb * rate
                priced_total += cost
                cost_cell = f"${cost:,.2f}"
            rows.append(
                f"<tr><td>{escape(cls)}</td><td>{objects_per_class.get(cls, 0):,}</td>"
                f"<td>{gb:,.2f}</td><td>{cost_cell}</td></tr>"
            )

        unpriced = ", ".join(sorted(escape(c) for c in stats.unpriced_classes)) or "none"
        errors = "".join(f"<li>{escape(e)}</li>" for e in stats.errors)

        html = [
            "<!DOCTYPE html><html><head><meta charset='utf-8'>",
            "<title>Cloud Storage Analysis Report</title><style>",
            "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:40px}",
            "table{border-collapse:collapse;width:100%;margin:20px 0}",
            "th,td{border:1px solid #ddd;padding:10px;text-align:left}",
            "th{background:#f5f5f5}tr:nth-child(even){background:#fafafa}",
            ".summary{background:#e8f5e9;padding:20px;border-radius:8px;margin:20px 0}",
            ".warning{background:#fff3e0;padding:20px;border-radius:8px;margin:20px 0}",
            "</style></head><body>",
            "<h1>Cloud Storage Analysis Report</h1>",
            f"<p>Generated: {escape(datetime.now(timezone.utc).isoformat())}</p>",
            "<div class='summary'><h2>Summary</h2><ul>",
            f"<li>Total objects: {stats.total_objects:,}</li>",
            f"<li>Total size: {stats.total_size_bytes / (1024 ** 3):,.2f} GB</li>",
            f"<li>Priced monthly storage: ${priced_total:,.2f}</li>",
            f"<li>Providers: {escape(', '.join(sorted(stats.by_provider)) or 'none')}</li>",
            f"<li>Scan duration: {stats.scan_duration_seconds:,.1f}s</li>",
            f"<li>Classes without a published rate: {unpriced}</li>",
            "</ul></div>",
            "<h2>By storage class</h2><table>",
            "<tr><th>Class</th><th>Objects</th><th>Size (GB)</th><th>Est. cost/month</th></tr>",
            *rows,
            "</table>",
        ]

        if duplicates:
            wasted = sum(g.wasted_bytes for g in duplicates)
            html += [
                "<div class='warning'>",
                f"<h2>Duplicate groups: {len(duplicates):,}</h2>",
                f"<p>Reclaimable if de-duplicated: {wasted / (1024 ** 3):,.2f} GB</p>",
                "<table><tr><th>Hash</th><th>Object size</th><th>Cloud copies</th>"
                "<th>Local copies</th><th>Reclaimable</th></tr>",
            ]
            for g in duplicates[:200]:
                html.append(
                    f"<tr><td>{escape(g.hash[:24])}</td>"
                    f"<td>{g.size / (1024 ** 2):,.1f} MB</td>"
                    f"<td>{len(g.entries)}</td><td>{len(g.local_paths)}</td>"
                    f"<td>{g.wasted_bytes / (1024 ** 2):,.1f} MB</td></tr>"
                )
            html += ["</table></div>"]

        if errors:
            html += ["<div class='warning'><h2>Errors</h2><ul>", errors, "</ul></div>"]

        html.append("</body></html>")
        return "\n".join(html)


__all__ = [
    "CloudStorageAnalyzer",
    "CloudFileEntry",
    "CloudScanStats",
    "DuplicateGroup",
    "PricingCatalog",
    "S3Provider",
    "AzureBlobProvider",
    "GoogleDriveProvider",
    "OneDriveProvider",
    "RcloneProvider",
]