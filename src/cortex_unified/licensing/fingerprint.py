"""Stable, privacy-preserving machine fingerprint for license binding.

The fingerprint is a SHA-256 digest over hardware identifiers available with
zero privileges. Design goals:

* **Stable** across reboots and ordinary hardware churn (USB devices do not
  change it).
* **Private.** Only the digest is ever stored or compared - the raw
  identifiers never leave this module and are never logged or written to disk.
* **Cross-platform with graceful fallback.** Windows uses the OS MachineGuid
  (registry), macOS uses IOPlatformUUID, Linux uses /etc/machine-id; if none
  of those are readable we fall back to platform identity attributes so
  licensing still functions (weaker binding, but never a crash).

A small salt constant is mixed in so the digest cannot be trivially matched
against public MachineGuid/UUID databases.
"""

from __future__ import annotations

import hashlib
import logging
import platform
import sys

_LOG = logging.getLogger("cortex.licensing.fingerprint")

#: Mixed into every digest so stored fingerprints are not reversible to the
#: underlying OS identifiers even if a license file leaks.
_SALT = b"cortex-cleaner::fingerprint::v1"

_FINGERPRINT: str | None = None


def _windows_ids() -> list[str]:
    """_windows_ids.

    Manages windows ids operations and coordinates related state changes for the component.

    Returns:
        list[str]: List of processed items or identifiers.
    """
    ids: list[str] = []
    try:
        import winreg

        key_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography",
             "MachineGuid"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "ProductId"),
        ]
        for hive, path, value_name in key_paths:
            try:
                with winreg.OpenKey(hive, path) as key:
                    value = winreg.QueryValueEx(key, value_name)[0]
                    if value:
                        ids.append(f"{path}\\{value_name}={value}")
            except OSError:
                continue
    except ImportError:
        pass
    return ids


def _macos_ids() -> list[str]:
    """_macos_ids.

    Manages macos ids operations and coordinates related state changes for the component.

    Returns:
        list[str]: List of processed items or identifiers.
    """
    ids: list[str] = []
    try:
        import subprocess

        out = subprocess.run(
            ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
            capture_output=True, text=True, timeout=10,
        )
        for line in out.stdout.splitlines():
            line = line.strip()
            if line.startswith('"IOPlatformUUID"'):
                uuid = line.split("=", 1)[1].strip().strip('";')
                if uuid:
                    ids.append(f"IOPlatformUUID={uuid}")
                break
    except Exception:  # noqa: BLE001 - best-effort identifier only
        pass
    return ids


def _linux_ids() -> list[str]:
    """_linux_ids.

    Manages linux ids operations and coordinates related state changes for the component.

    Returns:
        list[str]: List of processed items or identifiers.
    """
    ids: list[str] = []
    for candidate in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            with open(candidate, encoding="utf-8") as handle:
                value = handle.read().strip()
            if value:
                ids.append(f"{candidate}={value}")
                break
        except OSError:
            continue
    return ids


def collect_identifiers() -> list[str]:
    """Return labelled platform identifiers (never persisted or logged).

    Manages collect identifiers operations and coordinates related state changes for the component.

    Returns:
        list[str]: List of processed items or identifiers.
    """
    if sys.platform == "win32":
        ids = _windows_ids()
    elif sys.platform == "darwin":
        ids = _macos_ids()
    else:
        ids = _linux_ids()
    # Universal weak identifiers as last-resort stability anchors so the
    # digest still exists on exotic platforms or locked-down machines.
    if not ids:
        ids = [
            f"node={platform.node()}",
            f"machine={platform.machine()}",
            f"system={platform.system()}",
        ]
    return ids


def compute_fingerprint() -> str:
    """Return the stable SHA-256 hex digest identifying this machine.

    Manages compute fingerprint operations and coordinates related state changes for the component.

    Returns:
        str: Formatted string or path.
    """
    parts = "\n".join(sorted(collect_identifiers())).encode("utf-8")
    return hashlib.sha256(_SALT + b"\x00" + parts).hexdigest()


def get_fingerprint() -> str:
    """Memoised :func:`compute_fingerprint` (identifiers never change mid-run).

    Manages get fingerprint operations and coordinates related state changes for the component.

    Returns:
        str: Formatted string or path.
    """
    global _FINGERPRINT
    if _FINGERPRINT is None:
        _FINGERPRINT = compute_fingerprint()
    return _FINGERPRINT


def reset_cache() -> None:
    """Forget the memoised digest (used by tests and diagnostics).

    Manages reset cache operations and coordinates related state changes for the component.
    """
    global _FINGERPRINT
    _FINGERPRINT = None
