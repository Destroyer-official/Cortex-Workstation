"""MAC address identity: IEEE-backed vendor lookup and privacy detection.

Vendor names come only from authoritative sources: the IEEE Registration
Authority registry (MA-L/MA-M/MA-S, downloaded and cached locally) and the
device's own self-reported identity collected elsewhere in the discovery
engine. A hand-curated table was removed deliberately - an audit of its 322
entries against IEEE found 43 wrong vendors, 6 prefixes claimed twice, and
coverage of well under 1% of real assignments, and a wrong name is worse
than none. Whether an address is locally administered (privacy/randomized)
or multicast is computed from the MAC's own bits, so those answers cannot go
stale.
"""

from __future__ import annotations

import csv
import logging
import os
from pathlib import Path

_LOG = logging.getLogger("cortex.system_tools.oui")

#: 24-bit OUI (MA-L) prefix -> organisation, from the IEEE registry.
#: Keys are lower-case colon-separated ("aa:bb:cc"). Empty until a registry is
#: loaded - deliberately, so an absent registry reads as "unknown" rather than
#: as a guess.
_OUI: dict[str, str] = {}

#: MA-M (28-bit) and MA-S (36-bit) assignments keyed by bare hex prefix
#: (7 or 9 characters). Checked before the 24-bit block that contains them.
_LONG_ASSIGNMENTS: dict[str, str] = {}

#: Locally-administered ranges the IEEE registry can never contain, because
#: they are conventions rather than assignments. Kept because they are
#: documented behaviours of the software that uses them, not vendor guesses:
#: Docker builds container MACs under 02:42, and QEMU/KVM's default range is
#: 52:54:00. Both would otherwise be reported only as "private address".
_LOCAL_CONVENTIONS: dict[str, str] = {
    "02:42": "Docker container",
    "52:54:00": "QEMU/KVM virtual machine",
}

# -- Win32-style bit flags in the first octet of a MAC ----------------------

#: Bit 0x02 marks a *locally administered* address - one not assigned by the
#: IEEE to a manufacturer. Modern phones use this for per-network privacy
#: addresses, so it is the reliable signal that a vendor lookup is *expected*
#: to fail rather than a gap in the data.
_LOCALLY_ADMINISTERED_BIT = 0x02
_MULTICAST_BIT = 0x01

#: Corporate suffixes stripped for display. Purely cosmetic - the underlying
#: value from IEEE is never altered, so no mapping can become wrong.
_NOISE_SUFFIXES = (
    "co.,ltd.", "co.,ltd", "co., ltd.", "co., ltd", "co ltd", "co.ltd",
    "company limited", "limited", "ltd.", "ltd", "inc.", "inc", "corporation",
    "corp.", "corp", "gmbh", "s.a.", "b.v.", "pty", "plc", "llc",
    "technologies", "technology", "electronics", "private",
)


def normalize(mac: str) -> str:
    """Normalize.

    Manages normalize operations and coordinates related state changes for the component.

    Args:
        mac (str): The mac parameter.

    Returns:
        str: Formatted string or path.
    """
    if not mac:
        return ""
    cleaned = mac.strip().replace("-", ":").replace(".", ":").lower()
    parts = [p for p in cleaned.split(":") if p]
    if len(parts) != 6 or not all(len(p) <= 2 and p.isalnum() for p in parts):
        return ""
    return ":".join(p.zfill(2) for p in parts)


def _first_octet(mac: str) -> int | None:
    """_first_octet.

    Manages first octet operations and coordinates related state changes for the component.

    Args:
        mac (str): The mac parameter.

    Returns:
        int | None: Result of the operation.
    """
    norm = normalize(mac)
    if not norm:
        return None
    try:
        return int(norm[:2], 16)
    except ValueError:
        return None


# -- pure bit-level facts (never stale, never wrong) -----------------------

def is_randomized(mac: str) -> bool:
    """True when *mac* is a locally-administered (typically privacy) address.

    A device using one is deliberately not revealing its manufacturer, and the
    address will change again on a future join - so any per-MAC record of it is
    temporary by design.
    """
    octet = _first_octet(mac)
    if octet is None:
        return False
    return bool(octet & _LOCALLY_ADMINISTERED_BIT) and not (octet & _MULTICAST_BIT)


def is_multicast(mac: str) -> bool:
    """True for a multicast/broadcast MAC (not a real device address).

    Manages is multicast operations and coordinates related state changes for the component.

    Args:
        mac (str): The mac parameter.

    Returns:
        bool: True if the operation succeeded, False otherwise.
    """
    octet = _first_octet(mac)
    return octet is not None and bool(octet & _MULTICAST_BIT)


# -- vendor lookup (IEEE-backed only) --------------------------------------

def lookup(mac: str) -> str:
    """Return the registered organisation for *mac*, or ``""`` if unknown.

    Longer assignments are checked first: a 36-bit (MA-S) or 28-bit (MA-M)
    block is more specific than the 24-bit OUI containing it, and those small
    blocks are how most modern IoT hardware is registered.

    Returns ``""`` rather than a guess - including when no registry is loaded.
    Use :func:`describe_vendor` for display text that explains *why* a vendor
    is absent.
    """
    norm = normalize(mac)
    if not norm:
        return ""
    ensure_registry_loaded()

    digits = norm.replace(":", "")
    for length in (9, 7):                     # MA-S, then MA-M
        vendor = _LONG_ASSIGNMENTS.get(digits[:length])
        if vendor:
            return vendor
    vendor = _OUI.get(norm[:8], "")
    if vendor:
        return vendor

    # Locally-administered conventions (Docker/QEMU) - longest prefix first.
    for prefix in sorted(_LOCAL_CONVENTIONS, key=len, reverse=True):
        if norm.startswith(prefix):
            return _LOCAL_CONVENTIONS[prefix]
    return ""


def shorten(vendor: str) -> str:
    """Trim corporate boilerplate for display, keeping the recognisable name.

    ``"Espressif Inc."`` -> ``"Espressif"``, ``"TP-LINK TECHNOLOGIES CO.,LTD."``
    -> ``"TP-LINK"``. Cosmetic only: it transforms whatever IEEE returned and
    invents nothing, so it cannot introduce a wrong mapping.
    """
    if not vendor:
        return ""
    text = vendor.strip().rstrip(",.")
    lowered = text.lower()
    changed = True
    while changed:
        changed = False
        for suffix in _NOISE_SUFFIXES:
            if lowered.endswith(suffix):
                text = text[: len(text) - len(suffix)].strip(" ,.-")
                lowered = text.lower()
                changed = True
    return text or vendor.strip()


def describe_vendor(mac: str) -> str:
    """Human-facing vendor text that explains an absent vendor honestly.

    Manages describe vendor operations and coordinates related state changes for the component.

    Args:
        mac (str): The mac parameter.

    Returns:
        str: Formatted string or path.
    """
    vendor = lookup(mac)
    if vendor:
        return shorten(vendor)
    if is_randomized(mac):
        # The single most common reason a phone shows up unnamed.
        return "private address (randomized by the device)"
    if not has_full_registry():
        # Distinguish "we don't know" from "we couldn't look it up".
        return "unknown (vendor database not downloaded)"
    return ""


# -- registry loading ------------------------------------------------------

def cache_dir() -> Path:
    """Directory holding the downloaded IEEE registry.

    Manages cache dir operations and coordinates related state changes for the component.

    Returns:
        Path: Result of the operation.
    """
    return Path.home() / ".cortex_cleaner" / "netdata"


def cached_registry_path() -> Path:
    """Where a downloaded IEEE registry is kept between runs.

    Manages cached registry path operations and coordinates related state changes for the component.

    Returns:
        Path: Result of the operation.
    """
    return cache_dir() / "ieee-oui.csv"


def load_ieee_registry(path: str | os.PathLike[str]) -> int:
    """Merge an IEEE registry CSV into the lookup tables.

    Accepts the official layout (``Registry,Assignment,Organization Name,...``)
    for all three block sizes - MA-L (24-bit), MA-M (28-bit) and MA-S (36-bit).
    Returns the number of prefixes added; never raises.
    """
    added = 0
    try:
        with open(Path(path), newline="", encoding="utf-8", errors="replace") as handle:
            for row in csv.DictReader(handle):
                assignment = (row.get("Assignment") or "").strip().upper()
                org = (row.get("Organization Name") or "").strip()
                if not org or len(assignment) not in (6, 7, 9):
                    continue
                if not all(c in "0123456789ABCDEF" for c in assignment):
                    continue
                # "IEEE Registration Authority" is the placeholder used for
                # blocks subdivided into MA-M/MA-S ranges; it names no vendor,
                # so recording it would actively mislead.
                if org.lower().startswith("ieee registration authority"):
                    continue
                if len(assignment) == 6:
                    prefix = ":".join(
                        assignment[i:i + 2] for i in range(0, 6, 2)).lower()
                    if prefix not in _OUI:
                        _OUI[prefix] = org
                        added += 1
                elif assignment.lower() not in _LONG_ASSIGNMENTS:
                    _LONG_ASSIGNMENTS[assignment.lower()] = org
                    added += 1
    except (OSError, csv.Error, ValueError) as exc:
        _LOG.debug("could not load IEEE registry from %s: %s", path, exc)
        return 0
    return added


_registry_loaded = False


def load_cached_registry() -> int:
    """Load the previously downloaded registry, if present. Never raises.

    Manages load cached registry operations and coordinates related state changes for the component.

    Returns:
        int: Result of the operation.
    """
    path = cached_registry_path()
    if not path.is_file():
        return 0
    return load_ieee_registry(path)


def ensure_registry_loaded() -> bool:
    """Load the cached IEEE registry once, on first use.

    Runs automatically so a previously downloaded registry is always used - the
    user should not have to remember to refresh it. Returns True when a
    registry is in memory.
    """
    global _registry_loaded
    if _registry_loaded:
        return True
    _registry_loaded = True          # only ever attempt the disk read once
    return load_cached_registry() > 0


def has_full_registry() -> bool:
    """True when a real IEEE registry is loaded (not just the LA conventions).

    Manages has full registry operations and coordinates related state changes for the component.

    Returns:
        bool: True if the operation succeeded, False otherwise.
    """
    ensure_registry_loaded()
    return len(_OUI) > 1000


def registry_age_days() -> float | None:
    """Age of the cached registry in days, or ``None`` when absent.

    Manages registry age days operations and coordinates related state changes for the component.

    Returns:
        float | None: Result of the operation.
    """
    try:
        import time
        return max(0.0, (time.time() - cached_registry_path().stat().st_mtime) / 86400.0)
    except OSError:
        return None


def registry_status() -> dict[str, object]:
    """Describe the vendor database for display in the UI.

    Manages registry status operations and coordinates related state changes for the component.

    Returns:
        dict[str, object]: Dictionary mapping identifiers to status or values.
    """
    ensure_registry_loaded()
    age = registry_age_days()
    return {
        "loaded": has_full_registry(),
        "prefixes": prefix_count(),
        "age_days": None if age is None else round(age, 1),
        "path": str(cached_registry_path()),
        "stale": age is not None and age > 90,
    }


#: IEEE publishes each block size as its own CSV; all are public.
_IEEE_SOURCES = (
    "https://standards-oui.ieee.org/oui/oui.csv",      # MA-L, 24-bit
    "https://standards-oui.ieee.org/oui28/mam.csv",    # MA-M, 28-bit
    "https://standards-oui.ieee.org/oui36/oui36.csv",  # MA-S, 36-bit
)


def refresh_from_ieee(timeout: int = 60, cancel_event=None) -> tuple[bool, str]:
    """Download the official IEEE registries and cache them locally.

    This is what turns "unknown device" into a real manufacturer name for the
    long tail of hardware. It is an **explicit, user-triggered** action because
    it is the only part of device identification that touches the internet, and
    it sends nothing about the user - it just fetches IEEE's public assignment
    list.

    Returns ``(ok, message)`` and never raises.
    """
    global _registry_loaded
    import urllib.error
    import urllib.request

    target = cached_registry_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"Could not create the cache folder: {exc}"

    chunks: list[str] = []
    fetched: list[str] = []
    errors: list[str] = []
    for url in _IEEE_SOURCES:
        if cancel_event is not None and cancel_event.is_set():
            return False, "Vendor database update cancelled."
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "Cortex-Cleaner (MAC vendor lookup)"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                text = response.read().decode("utf-8", "replace")
            lines = text.splitlines()
            if not lines or "Assignment" not in lines[0]:
                errors.append(f"{url.rsplit('/', 1)[-1]}: unexpected format")
                continue
            # Keep the header only once so the result is a single valid CSV.
            chunks.append(text if not chunks else "\n".join(lines[1:]))
            fetched.append(url.rsplit("/", 1)[-1])
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            errors.append(f"{url.rsplit('/', 1)[-1]}: {exc}")
            continue

    if not chunks:
        detail = "; ".join(errors[:2])
        return False, ("Could not reach the IEEE registry "
                       f"({detail}). Device makers will stay unnamed until this "
                       "succeeds, but discovery itself still works.")
    try:
        target.write_text("\n".join(chunks), encoding="utf-8")
    except OSError as exc:
        return False, f"Downloaded the registry but could not save it: {exc}"

    _OUI.clear()
    _LONG_ASSIGNMENTS.clear()
    _registry_loaded = False
    added = load_ieee_registry(target)
    _registry_loaded = True
    message = (f"Loaded {added:,} vendor assignments from "
               f"{len(fetched)} IEEE file(s).")
    if errors:
        message += f" ({len(errors)} registry file(s) unavailable.)"
    return True, message


def prefix_count() -> int:
    """Number of known assignment prefixes (useful for diagnostics/tests).

    Manages prefix count operations and coordinates related state changes for the component.

    Returns:
        int: Result of the operation.
    """
    return len(_OUI) + len(_LONG_ASSIGNMENTS)
