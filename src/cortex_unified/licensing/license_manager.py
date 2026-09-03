"""Offline license activation, validation and trial management.

A *license file* is a small JSON document::

    {
      "version": 1,
      "payload": {"key": "...", "tier": "pro", "name": "...", "email": "...",
                   "issued": "2026-08-22", "expiry": "2027-08-22",
                   "fingerprint": "<sha256>"},
      "signature": "<hex hmac-sha256 over canonical payload>"
    }

Validation is fully local: recompute the canonical payload digest, verify the
HMAC, check the fingerprint matches this machine, then check expiry against a
grace window. Any failure degrades to the Free tier - never to an exception.

Signing model (v1): HMAC-SHA256 with an application-embedded secret. This is
*tamper-evident* (a user cannot mint or edit licenses without the secret) but
not resistant to a determined attacker extracting the secret from the binary;
the roadmap schedules Ed25519 public-key signing as v2 via the ``cryptography``
package. The file format already reserves ``"version"`` so that upgrade is
non-breaking.

Trials: one PRO trial of :data:`TRIAL_DAYS` per machine, tracked by writing
the same signed format with ``key = TRIAL_KEY``; deleting the file does not
reset eligibility because the trial marker is re-signed on disk.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .fingerprint import get_fingerprint
from .tiers import Feature, Tier, features_for_tier

_LOG = logging.getLogger("cortex.licensing.manager")

_FILE_VERSION = 1
_TRIAL_KEY = "CORTEX-TRIAL"
TRIAL_DAYS = 30
GRACE_DAYS = 14
DEFAULT_TERM_DAYS = 365

#: v1 signing secret (see module docstring for the honest security story).
_SECRET = b"cortex-cleaner::license::v1::signing"


def _today() -> date:
    """_today."""
    return date.today()
    """_today."""
    """_today."""


def _parse_date(value: str) -> date | None:
    """_parse_date."""
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    """_parse_date."""
    """_parse_date."""


@dataclass(slots=True)
class LicensePayload:
    """The signed, machine-bound content of a license."""

    key: str
    tier: Tier
    name: str = ""
    email: str = ""
    issued: str = field(default_factory=lambda: _today().isoformat())
    expiry: str = field(
        default_factory=lambda: (_today() + timedelta(days=DEFAULT_TERM_DAYS)).isoformat()
    )
    fingerprint: str = ""

    def canonical(self) -> bytes:
        """Deterministic serialization used for both signing and verifying."""
        data = {
            "key": self.key,
            "tier": self.tier.value,
            "name": self.name,
            "email": self.email,
            "issued": self.issued,
            "expiry": self.expiry,
            "fingerprint": self.fingerprint,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def sign(self) -> str:
        """sign."""
        return hmac.new(_SECRET, self.canonical(), hashlib.sha256).hexdigest()
        """sign."""
        """sign."""

    def verify_signature(self, signature: str) -> bool:
        """verify_signature."""
        return hmac.compare_digest(self.sign(), signature or "")
        """verify_signature."""
        """verify_signature."""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LicensePayload | None":
        """from_dict."""
        if not isinstance(raw, dict):
            return None
        try:
            return cls(
                key=str(raw.get("key", "")),
                tier=Tier.parse(raw.get("tier")),
                name=str(raw.get("name", "")),
                email=str(raw.get("email", "")),
                issued=str(raw.get("issued", "")),
                expiry=str(raw.get("expiry", "")),
                fingerprint=str(raw.get("fingerprint", "")),
            )
        except Exception:  # noqa: BLE001 - malformed payloads degrade to None
            return None
        """from_dict."""
        """from_dict."""


@dataclass(slots=True)
class LicenseState:
    """Result of validating the stored license right now."""

    tier: Tier = Tier.FREE
    licensed: bool = False
    trial: bool = False
    key: str = ""
    name: str = ""
    email: str = ""
    issued: str = ""
    expiry: str = ""
    grace_active: bool = False
    reason: str = "no license installed"

    @property
    def features(self) -> set[Feature]:
        """features."""
        return features_for_tier(self.tier)

    def allows(self, feature: Feature) -> bool:
        """allows."""
        return feature in self.features

    def to_dict(self) -> dict[str, Any]:
        """to_dict."""
        return {
            "tier": self.tier.value,
            "licensed": self.licensed,
            "trial": self.trial,
            "key": self._masked_key(),
            "name": self.name,
            "email": self.email,
            "issued": self.issued,
            "expiry": self.expiry,
            "grace_active": self.grace_active,
            "reason": self.reason,
        }
        """to_dict."""
        """to_dict."""

    def _masked_key(self) -> str:
        """_masked_key."""
        if not self.key:
            return ""
        if len(self.key) <= 8:
            return "*" * len(self.key)
        return f"{self.key[:4]}...{self.key[-4:]}"
        """_masked_key."""
        """_masked_key."""


def license_path() -> Path:
    """Where this machine's license lives (per-user, no admin rights)."""
    return Path.home() / ".cortex_cleaner" / "license.json"


class LicenseManager:
    """Activate, validate and revoke the local license. Thread-safe.

    Validation results are memoised, but the cache is keyed to the license
    file's ``(mtime_ns, size)``: any change to the file - tampering while the
    app runs, a replaced file, deletion - invalidates it and forces a fresh
    read + signature check on the next validation.
    """

    def __init__(self, path: Path | None = None):
        """__init__."""
        self._path = path or license_path()
        # Reentrant: activate() holds this while _save()->invalidate() runs.
        self._lock = threading.RLock()
        self._cache: LicenseState | None = None
        self._cache_sig: tuple[int, int] | None = None
        """__init__."""
        """__init__."""

    # -- persistence --------------------------------------------------------

    @staticmethod
    def _file_signature(path: Path) -> tuple[int, int] | None:
        """Cheap identity of the on-disk license (None when absent)."""
        try:
            stat = path.stat()
            return (stat.st_mtime_ns, stat.st_size)
        except OSError:
            return None

    def invalidate(self) -> None:
        """Drop memoised state so the next ``validate`` re-reads disk."""
        with self._lock:
            self._cache = None
            self._cache_sig = None

    def _save(self, payload: LicensePayload) -> None:
        """Atomically write the signed license (tmp + replace)."""
        document = {
            "version": _FILE_VERSION,
            "payload": json.loads(payload.canonical().decode("utf-8")),
            "signature": payload.sign(),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(document, indent=2), encoding="utf-8")
        os.replace(tmp, self._path)
        self.invalidate()

    def _load_document(self) -> tuple[LicensePayload | None, str]:
        """_load_document."""
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None, "no license installed"
        except Exception as exc:  # noqa: BLE001 - corrupt file must not crash
            _LOG.debug("unreadable license file: %s", exc)
            return None, "corrupt license file"
        payload = LicensePayload.from_dict(raw.get("payload"))
        if payload is None:
            return None, "malformed license payload"
        signature = str(raw.get("signature", ""))
        if not raw.get("version") == _FILE_VERSION:
            return None, "unsupported license version"
        return payload, signature
        """_load_document."""
        """_load_document."""

    # -- activation lifecycle -------------------------------------------------

    def activate(
        self,
        key: str,
        tier: Tier,
        name: str = "",
        email: str = "",
        term_days: int = DEFAULT_TERM_DAYS,
    ) -> LicenseState:
        """Install and sign a new license bound to this machine.

        In production ``key`` arrives from the vendor's order flow; the CLI/GUI
        pass it through here together with the purchased tier.
        """
        key = (key or "").strip()
        if not key:
            raise ValueError("A license key is required.")
        if term_days <= 0:
            raise ValueError("term_days must be positive.")
        payload = LicensePayload(
            key=key,
            tier=tier,
            name=name.strip(),
            email=email.strip(),
            issued=_today().isoformat(),
            expiry=(_today() + timedelta(days=term_days)).isoformat(),
            fingerprint=get_fingerprint(),
        )
        with self._lock:
            self._save(payload)
        _LOG.info("license activated: tier=%s", tier.value)
        return self.validate()

    def start_trial(self) -> LicenseState:
        """Start the once-per-machine PRO trial."""
        state = self.validate()
        if state.licensed and not state.trial:
            raise RuntimeError("A full license is already active; no trial needed.")
        if state.trial:
            raise RuntimeError(f"Trial already used (expired {state.expiry}).")
        return self.activate(
            key=_TRIAL_KEY, tier=Tier.PRO,
            name="Trial", term_days=TRIAL_DAYS,
        )

    def deactivate(self) -> None:
        """Remove the local license entirely (machine returns to Free)."""
        with self._lock:
            try:
                self._path.unlink(missing_ok=True)
            except OSError as exc:
                _LOG.debug("could not remove license file: %s", exc)
            self.invalidate()

    # -- validation ------------------------------------------------------------

    def validate(self) -> LicenseState:
        """Validate the stored license now.

        Memoised against the file's ``(mtime_ns, size)`` signature: repeated
        calls are free, but any on-disk change (tamper, replace, delete)
        forces a fresh read + signature verification.
        """
        with self._lock:
            sig = self._file_signature(self._path)
            if self._cache is not None and self._cache_sig == sig:
                return self._cache
            state = self._validate_uncached()
            self._cache = state
            self._cache_sig = sig
            return state

    def _validate_uncached(self) -> LicenseState:
        """_validate_uncached."""
        payload, signature = self._load_document()
        if payload is None:
            return LicenseState(reason=signature)

        if not payload.verify_signature(signature):
            return LicenseState(reason="invalid license signature")
        if payload.fingerprint != get_fingerprint():
            return LicenseState(reason="licensed to a different machine")

        expiry = _parse_date(payload.expiry)
        if expiry is None:
            return LicenseState(reason="malformed expiry date")

        today = _today()
        trial = payload.key == _TRIAL_KEY
        grace_active = False
        effective_tier = payload.tier
        reason = "valid"

        if today > expiry:
            grace_end = expiry + timedelta(days=GRACE_DAYS)
            if today <= grace_end:
                # Subscription lapsed but inside grace: keep working, warn.
                grace_active = True
                reason = f"expired {payload.expiry}; grace period active"
            else:
                # Trials simply end; paid tiers freeze to Free after grace.
                effective_tier = Tier.FREE
                reason = f"expired {payload.expiry}; grace period ended"

        return LicenseState(
            tier=effective_tier,
            licensed=effective_tier is not Tier.FREE,
            trial=trial,
            key=payload.key,
            name=payload.name,
            email=payload.email,
            issued=payload.issued,
            expiry=payload.expiry,
            grace_active=grace_active,
            reason=reason,
        )
        """_validate_uncached."""
        """_validate_uncached."""

    def status(self) -> dict[str, Any]:
        """status."""
        return self.validate().to_dict()
        """status."""
        """status."""


_MANAGER: LicenseManager | None = None
_MANAGER_LOCK = threading.Lock()


def get_license_manager() -> LicenseManager:
    """Process-wide singleton (tests may construct their own instances)."""
    global _MANAGER
    with _MANAGER_LOCK:
        if _MANAGER is None:
            _MANAGER = LicenseManager()
        return _MANAGER


def reset_singleton() -> None:
    """Forget the singleton (test isolation)."""
    global _MANAGER
    with _MANAGER_LOCK:
        _MANAGER = None
