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

Trials: one PRO trial of :data:`TRIAL_DAYS` per machine.
Tracked only by a single license file (~/.cortex_cleaner/license.json); deleting that file clears trial state (a new trial can then be started).
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
    """Today.

    Manages today operations and coordinates related state changes for the component.

    Returns:
        date: Result of the operation.
    """
    return date.today()


def _parse_date(value: str) -> date | None:
    """_parse_date.

    Manages parse date operations and coordinates related state changes for the component.

    Args:
        value (str): The value parameter.

    Returns:
        date | None: Result of the operation.
    """
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


@dataclass(slots=True)
class LicensePayload:
    """Licensepayload.

    Manages LicensePayload operations and coordinates related state changes for the component.
    """

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
        """Canonical.

        Manages canonical operations and coordinates related state changes for the component.

        Returns:
            bytes: Result of the operation.
        """
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
        """Sign.

        Manages sign operations and coordinates related state changes for the component.

        Returns:
            str: Formatted string or path.
        """
        return hmac.new(_SECRET, self.canonical(), hashlib.sha256).hexdigest()

    def verify_signature(self, signature: str) -> bool:
        """verify_signature.

        Manages verify signature operations and coordinates related state changes for the component.

        Args:
            signature (str): The signature parameter.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return hmac.compare_digest(self.sign(), signature or "")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LicensePayload | None":
        """from_dict.

        Manages from dict operations and coordinates related state changes for the component.

        Args:
            raw (dict[str, Any]): The raw parameter.

        Returns:
            'LicensePayload | None': Result of the operation.
        """
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


@dataclass(slots=True)
class LicenseState:
    """Licensestate.

    Manages LicenseState operations and coordinates related state changes for the component.
    """

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
        """Features.

        Manages features operations and coordinates related state changes for the component.

        Returns:
            set[Feature]: Result of the operation.
        """
        return features_for_tier(self.tier)

    def allows(self, feature: Feature) -> bool:
        """Allows.

        Manages allows operations and coordinates related state changes for the component.

        Args:
            feature (Feature): The feature parameter.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return feature in self.features

    def to_dict(self) -> dict[str, Any]:
        """to_dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
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

    def _masked_key(self) -> str:
        """_masked_key.

        Manages masked key operations and coordinates related state changes for the component.

        Returns:
            str: Formatted string or path.
        """
        if not self.key:
            return ""
        if len(self.key) <= 8:
            return "*" * len(self.key)
        return f"{self.key[:4]}...{self.key[-4:]}"


def license_path() -> Path:
    """Where this machine's license lives (per-user, no admin rights).

    Manages license path operations and coordinates related state changes for the component.

    Returns:
        Path: Result of the operation.
    """
    return Path.home() / ".cortex_cleaner" / "license.json"


class LicenseManager:
    """Activate, validate and revoke the local license. Thread-safe.

    Validation results are memoised, but the cache is keyed to the license
    file's ``(mtime_ns, size)``: any change to the file - tampering while the
    app runs, a replaced file, deletion - invalidates it and forces a fresh
    read + signature check on the next validation.
    """

    def __init__(self, path: Path | None = None):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            path (Path | None): Filesystem path to the target file or directory.
        """
        self._path = path or license_path()
        # Reentrant: activate() holds this while _save()->invalidate() runs.
        self._lock = threading.RLock()
        self._cache: LicenseState | None = None
        self._cache_sig: tuple[int, int] | None = None

    # -- persistence --------------------------------------------------------

    @staticmethod
    def _file_signature(path: Path) -> tuple[int, int] | None:
        """Cheap identity of the on-disk license (None when absent).

        Manages file signature operations and coordinates related state changes for the component.

        Args:
            path (Path): Filesystem path to the target file or directory.

        Returns:
            tuple[int, int] | None: Result of the operation.
        """
        try:
            stat = path.stat()
            return (stat.st_mtime_ns, stat.st_size)
        except OSError:
            return None

    def invalidate(self) -> None:
        """Invalidate.

        Manages invalidate operations and coordinates related state changes for the component.
        """
        with self._lock:
            self._cache = None
            self._cache_sig = None

    def _save(self, payload: LicensePayload) -> None:
        """Save configuration settings or analysis reports to persistent storage.

        Serializes current user preferences or generated report data to disk with integrity validation.

        Args:
            payload (LicensePayload): The payload parameter.
        """
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
        """_load_document.

        Manages load document operations and coordinates related state changes for the component.

        Returns:
            tuple[LicensePayload | None, str]: Formatted string or path.
        """
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
        """Start the once-per-machine PRO trial.

        Manages start trial operations and coordinates related state changes for the component.

        Returns:
            LicenseState: Result of the operation.
        """
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
        """Deactivate.

        Manages deactivate operations and coordinates related state changes for the component.
        """
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
        """_validate_uncached.

        Manages validate uncached operations and coordinates related state changes for the component.

        Returns:
            LicenseState: Result of the operation.
        """
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

    def status(self) -> dict[str, Any]:
        """Status.

        Manages status operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return self.validate().to_dict()


_MANAGER: LicenseManager | None = None
_MANAGER_LOCK = threading.Lock()


def get_license_manager() -> LicenseManager:
    """Process-wide singleton (tests may construct their own instances).

    Manages get license manager operations and coordinates related state changes for the component.

    Returns:
        LicenseManager: Result of the operation.
    """
    global _MANAGER
    with _MANAGER_LOCK:
        if _MANAGER is None:
            _MANAGER = LicenseManager()
        return _MANAGER


def reset_singleton() -> None:
    """Forget the singleton (test isolation).

    Manages reset singleton operations and coordinates related state changes for the component.
    """
    global _MANAGER
    with _MANAGER_LOCK:
        _MANAGER = None
