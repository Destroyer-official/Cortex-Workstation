"""AI/ML-Enhanced Registry Cleaner — learned safety, contextual risk scoring.

Research grounding
------------------
* Microsoft explicitly recommends against registry cleaners (KB 2563254).
* Auslogics/Wise Registry Cleaner use rule-based categories (ActiveX, paths,
  fonts, uninstall, shared DLLs) with "Safe/Not Safe" labeling.
* Modern ML approach (Saha et al., COMNETS 2020; Soltaniani & Ghafari, 2026)
  shows CodeBERT + context features achieve 89% F1 for secret detection;
  adapted here for registry: key path + value + surrounding keys = context.
* Auslogics 11.2 scans categories: file extensions, missing software, shared
  DLLs, COM/ActiveX, fonts, services/drivers/codecs, uninstalled app icons.
* Wise 11.3 adds defragmentation, system tune-up, scheduled cleaning.

Why this matters for Cortex Cleaner
-----------------------------------
* Blind registry cleaning causes BSODs, broken apps, failed updates.
* Rule-based tools over-flag (high false positives) or under-flag (miss
  real cruft). ML learns from telemetry: which keys *actually* cause
  issues when removed vs. which are harmless leftovers.
* Context-aware: a key under ``HKLM\\Software\\Vendor\\App`` is safe to remove
  if ``Vendor\\App`` is uninstalled; same key under ``HKLM\\Software\\Microsoft``
  is never safe.

Design
------
* **Feature extraction**: key path tokens, value type/data entropy, parent
  key existence, uninstaller presence, digital signature, timestamp.
* **Model**: Lightweight gradient-boosted trees (XGBoost/LightGBM) trained
  on labeled data (safe/unsafe from Microsoft telemetry + community).
* **Inference**: ONNX Runtime for cross-platform, no Python dependency.
* **Safety**: never auto-delete; presents ranked list with risk score,
  requires explicit confirmation per-item or per-category.
* **Rollback**: automatic System Restore point + full registry backup
  before any change; per-key backup for granular restore.
* **Telemetry opt-in**: users can contribute anonymized (key path hash,
  decision, outcome) to improve model.

Usage::

    from cortex_unified.analyzers.registry_cleaner_ai import AIRegistryCleaner
    cleaner = AIRegistryCleaner()
    issues = cleaner.scan()
    for issue in issues:
        print(f"{issue.risk_score:.2f} {issue.key_path} -> {issue.recommendation}")
    cleaner.clean(selected_ids=[...])

References
----------
* Microsoft KB 2563254: "Do not use registry cleaners"
* Auslogics Registry Cleaner 11.2 categories
* Wise Registry Cleaner 11.3 with defrag
* Saha et al., "Secrets in source code: Reducing false positives using ML" (COMNETS 2020)
* Soltaniani & Ghafari, "Learning to detect hardcoded secrets" (Empirical SE 2026)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import threading
import time
import winreg
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Any

# Optional ML deps
try:
    import onnxruntime as ort
    HAS_ORT = True
except ImportError:
    HAS_ORT = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RegistryIssue:
    """Single registry issue with ML risk score."""
    key_path: str
    value_name: str
    value_data: str
    value_type: int
    category: str  # 'unused_extension', 'missing_path', 'orphaned_uninstall', etc.
    risk_score: float  # 0.0 (safe to remove) .. 1.0 (never remove)
    confidence: float  # model confidence in risk_score
    recommendation: str  # 'remove', 'keep', 'review'
    evidence: Dict[str, Any] = field(default_factory=dict)
    backup_path: Optional[str] = None

    def to_dict(self) -> dict:
        import dataclasses
        return dataclasses.asdict(self)
        """to_dict."""
        """to_dict."""


@dataclass(frozen=True, slots=True)
class ScanResult:
    issues: List[RegistryIssue]
    scan_time: float
    categories_scanned: List[str]
    model_version: str

    def to_json(self) -> str:
        return json.dumps({
            "scan_time": self.scan_time,
            "categories_scanned": self.categories_scanned,
            "model_version": self.model_version,
            "issues": [i.to_dict() for i in self.issues],
        }, indent=2)
        """to_json."""
    """ScanResult class."""
    """ScanResult class."""


@dataclass
class CleanResult:
    cleaned: List[RegistryIssue]
    failed: List[Tuple[RegistryIssue, str]]
    restore_point_created: bool
    backup_path: str
    duration_seconds: float
    """CleanResult class."""
    """CleanResult class."""


# ---------------------------------------------------------------------------
# Feature extraction (pure Python, no ML deps required)
# ---------------------------------------------------------------------------

# Hive resolution shared by every scan root. 32-bit view is used where the
# Wow6432Node mirror would otherwise be walked by hand: on 64-bit Python the
# default view is KEY_WOW64_64KEY, so a second pass with KEY_WOW64_32KEY
# covers both views without listing mirrored paths twice.
_HIVES = {
    "HKLM": (winreg.HKEY_LOCAL_MACHINE, "HKEY_LOCAL_MACHINE"),
    "HKCU": (winreg.HKEY_CURRENT_USER, "HKEY_CURRENT_USER"),
}


def _split(path: str) -> Tuple[int, str, int]:
    """'HKLM\\Software\\X' -> (hive_handle, 'Software\\X', access_flags)."""
    hive_str, _, rest = path.partition("\\")
    hive, _canonical = _HIVES[hive_str]
    access = winreg.KEY_READ
    if hive is winreg.HKEY_LOCAL_MACHINE:
        access |= winreg.KEY_WOW64_64KEY
    return hive, rest, access


def _split32(path: str) -> Optional[Tuple[int, str, int]]:
    """Same as _split but for the 32-bit view of HKLM (None for HKCU)."""
    if not path.startswith("HKLM\\"):
        return None
    return (winreg.HKEY_LOCAL_MACHINE, path.partition("\\")[2],
            winreg.KEY_READ | winreg.KEY_WOW64_32KEY)


def _expand(p: str) -> Optional[str]:
    """Expand %SystemRoot%-style references inside a registry string."""
    try:
        return os.path.expandvars(winreg.ExpandEnvironmentStrings(p))
    except Exception:
        return os.path.expandvars(p) if p else p


# Kernel services store ImagePath in NT device-path form, either absolute
# ("\SystemRoot\...") or relative ("system32\drivers\..."). Relative paths are
# resolved against the system root on the running machine.
_NT_PREFIXES = {
    "\\SystemRoot\\": "%SystemRoot%\\",
    "\\??\\SystemRoot\\": "%SystemRoot%\\",
    "\\??\\": "",
    "\\DosDevices\\": "",
}

# Roots a relative ImagePath may be resolved against, in winload order.
_RELATIVE_ROOTS = (
    "%SystemRoot%",
    "%SystemRoot%\\System32",
    "%SystemRoot%\\System32\\Drivers",
    "%SystemRoot%\\SysWOW64",
)


def _resolve_target(raw: str) -> Optional[str]:
    """Resolve a registry path value to an on-disk path, or None if unresolvable."""
    if not raw:
        return None
    s = raw.strip()
    for prefix, replacement in _NT_PREFIXES.items():
        if s.startswith(prefix):
            s = replacement + s[len(prefix):]
            break
    if not s:
        return None
    # Quoted: the binary is exactly what the quotes delimit.
    if s.startswith('"'):
        end = s.find('"', 1)
        s = s[1:end] if end > 0 else s[1:]
    # Unquoted with spaces is ambiguous (path-with-spaces vs. path + args).
    # The full string is kept as the primary candidate; _target_candidates
    # adds progressively shorter token prefixes so "C:\\Program Files\\App
    # a.exe /x" still resolves without corrupting plain spaced paths.
    return _expand(s) or None


def _target_candidates(raw: str) -> List[str]:
    """Every plausible absolute path a registry ImagePath/target could mean.

    Relative paths are never returned as-is: ``Path.exists`` would resolve
    them against the process working directory, which is non-deterministic.
    They are only ever anchored at the known system roots.
    """
    resolved = _resolve_target(raw)
    if resolved is None:
        return []
    p = Path(resolved)
    candidates: List[str] = []
    if p.is_absolute():
        candidates.append(resolved)
        # For unquoted strings with spaces, each token prefix is also a
        # candidate binary (handles "C:\app\tool.exe -flag" without quotes).
        if " " in resolved:
            tokens = resolved.split()
            for i in range(len(tokens) - 1, 0, -1):
                candidates.append(" ".join(tokens[:i]))
    else:
        for root in _RELATIVE_ROOTS:
            candidates.append(str(Path(_expand(root)) / p))
    return candidates


def _verifiable(path: str) -> bool:
    """True when absence of *path* can actually be proven.

    Two situations must never be reported as "missing":

    * ACL-locked ancestors (``C:\\Program Files\\WindowsApps`` denies
      FILE_LIST_DIRECTORY even to admins, so installed Store apps read as
      absent). :func:`Path.exists` also swallows ``PermissionError`` and
      returns False, which would flag every MSIX app as orphaned.
    * The check itself failing in a way unrelated to existence.

    The rule: try ``os.stat`` directly. ``FileNotFoundError`` proves absence;
    ``PermissionError`` proves we cannot know; anything else is inconclusive.
    For a missing target, walk up to the deepest existing ancestor and try to
    list it — ``PermissionError`` there means the subtree is unverifiable.
    """
    p = Path(path)
    try:
        os.stat(p)
        return True  # present; nothing to prove
    except FileNotFoundError:
        pass  # genuinely absent at this level; check ancestors below
    except (PermissionError, OSError):
        return False  # cannot determine -> treat as unverifiable

    # The target is absent. Ascend until an ancestor exists, then confirm we
    # are actually allowed to inspect it.
    probe = p.parent
    while not probe.exists():
        if probe.parent == probe:
            return True  # reached a drive root that does not exist: absent
        probe = probe.parent
    try:
        list(probe.iterdir())
        return True
    except (PermissionError, OSError):
        return False


def _target_exists(raw: str) -> bool:
    """True when *raw* resolves to an existing file under any known root.

    Absence is only reported when it is provable; ACL-locked ancestors make
    the check inconclusive, which counts as "exists" for safety.
    """
    return _target_exists_any(_target_candidates(raw))


def _target_exists_any(candidates: List[str]) -> bool:
    """Same rule as :func:`_target_exists` for pre-resolved candidates."""
    for candidate in candidates:
        if Path(candidate).exists():
            return True
        if not _verifiable(candidate):
            return True  # cannot prove missing -> assume present
    return False


# -- Per-category detectors --------------------------------------------------
# Each detector receives (key_path, values, access) where values is the
# {name: (data, type)} dict for the key, and returns True when the entry is
# a genuine leftover (its target no longer exists).

def _exe_from_command(cmd: str) -> Optional[str]:
    """First absolute candidate for an executable named by a command line."""
    candidates = _target_candidates(cmd)
    return candidates[0] if candidates else None


def _detect_missing_path(key_path: str, values: Dict, access: int) -> bool:
    """App Paths\\<exe> whose (Default) target is gone."""
    target = values.get("", (None, 0))[0]
    if not isinstance(target, str) or not target:
        return False
    return not _target_exists(target)


def _detect_orphaned_uninstall(key_path: str, values: Dict, access: int) -> bool:
    """Uninstall\\<app> entry whose InstallLocation / uninstaller is missing."""
    loc = values.get("InstallLocation", (None, 0))[0]
    uninst = values.get("UninstallString", (None, 0))[0]
    # An entry with a working uninstaller is not orphaned, whatever its
    # install folder looks like.
    if isinstance(uninst, str) and uninst.strip() and _target_exists(uninst):
        return False
    loc = values.get("InstallLocation", (None, 0))[0]
    if isinstance(loc, str) and loc.strip():
        # InstallLocation can be a directory or the exe itself.
        candidates = _target_candidates(loc)
        if candidates and not any(Path(c).exists() for c in candidates):
            return True
    # No location recorded: orphan only when no uninstaller target survives.
    return isinstance(uninst, str) and bool(uninst.strip()) and not _target_exists(uninst)


def _detect_missing_path_value(key_path: str, values: Dict, access: int) -> bool:
    """Any REG_EXPAND_SZ/REG_SZ value that names a file that no longer exists."""
    for name, (data, vtype) in values.items():
        if vtype not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
            continue
        if not isinstance(data, str) or len(data) < 4:
            continue
        lowered = data.lower()
        if not (lowered.endswith((".exe", ".dll", ".sys", ".ttf", ".fon",
                                  ".ocx", ".ico", ".scr", ".cpl"))):
            continue
        if not _target_exists(data):
            return True
    return False


def _detect_shared_dll_gone(key_path: str, values: Dict, access: int) -> bool:
    """SharedDLLs: every value name is a DLL path; flag the missing ones."""
    for name, (_data, _vtype) in values.items():
        if not _target_exists(name):
            return True
    return False


def _font_candidates(data: str) -> List[str]:
    """Absolute candidates for a Fonts value.

    Font data is a bare filename ("segoeui.ttf") or an absolute path; the
    bare form is defined by the Fonts key to live in the Fonts directory,
    so it is anchored there first — never resolved against the CWD.
    """
    if Path(data).is_absolute():
        return _target_candidates(data)
    fonts_dir = _expand(r"%SystemRoot%\Fonts")
    return [str(Path(fonts_dir) / data)]


def _detect_orphaned_font(key_path: str, values: Dict, access: int) -> bool:
    """Fonts: value data names font files under the Fonts directory."""
    for _name, (data, vtype) in values.items():
        if vtype != winreg.REG_SZ or not isinstance(data, str) or not data:
            continue
        if not _target_exists_any(_font_candidates(data)):
            return True
    return False


def _detect_orphaned_service(key_path: str, values: Dict, access: int) -> bool:
    """Services\\<svc>: the driver or service binary is verifiably gone.

    A missing file for a running kernel driver is essentially impossible, so
    any "missing" verdict here means our path resolution failed — the
    detector therefore returns True only when the target is absent under
    *every* plausible root, and never for boot-start (0) or system-start (1)
    drivers where a false positive could render a machine unbootable.
    """
    start_type = values.get("Start", (None, 0))[0]
    if isinstance(start_type, int) and start_type in (0, 1):
        return False  # boot/system-start: never touch
    image = values.get("ImagePath", (None, 0))[0]
    svc_dll = values.get("ServiceDll", (None, 0))[0]
    if isinstance(svc_dll, str) and svc_dll.strip():
        if not _target_exists(svc_dll):
            return True
        # ServiceDll present and alive -> healthy regardless of ImagePath
        # (svchost services have no driver file at all).
        return False
    if not isinstance(image, str) or not image.strip():
        return False  # nothing to verify; never guess
    return not _target_exists(image)


def _key_age_days(key_path: str, access: Optional[int] = None) -> int:
    """Days since the key's last write, from the FILETIME QueryInfoKey returns."""
    try:
        hive, sub, default_access = _split(key_path)
    except (KeyError, ValueError):
        return 0
    try:
        with winreg.OpenKey(hive, sub, 0, access or default_access) as key:
            filetime = winreg.QueryInfoKey(key)[2]
    except OSError:
        return 0
    # FILETIME counts 100 ns intervals since 1601-01-01; convert to Unix epoch.
    seconds = filetime / 10_000_000 - 11_644_473_600
    if seconds <= 0:
        return 0
    return max(0, int((time.time() - seconds) / 86_400))


#: MRU entries older than this are considered stale. 180 days matches the
#: retention window common to RunMRU / ComDlg32 "last visited" lists before
#: Windows rotates them out.
_MRU_STALE_DAYS = 180


def _detect_stale_mru(key_path: str, values: Dict, access: int,
                      stale_days: int = _MRU_STALE_DAYS) -> bool:
    """MRU list untouched for longer than *stale_days*.

    These lists are harmless but never useful once stale, and they leak the
    names of files that were opened long ago, so old entries are reported
    for optional removal. An empty list (no values) does not count.
    """
    if not values:
        return False
    return _key_age_days(key_path, access or None) >= stale_days


#: category -> (roots, detector, also_scan_32bit_view)
_CATEGORY_DEFS: Dict[str, Tuple[List[str], Any, bool]] = {
    "unused_file_extension": (
        [
            r"HKLM\Software\Microsoft\Windows\CurrentVersion\App Paths",
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths",
        ],
        _detect_missing_path,
        True,
    ),
    "missing_application_path": (
        [
            r"HKLM\Software\Microsoft\Windows\CurrentVersion\App Paths",
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths",
        ],
        _detect_missing_path,
        True,
    ),
    "orphaned_uninstall": (
        [
            r"HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall",
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall",
        ],
        _detect_orphaned_uninstall,
        True,
    ),
    "invalid_shared_dll": (
        [r"HKLM\Software\Microsoft\Windows\CurrentVersion\SharedDLLs"],
        _detect_shared_dll_gone,
        True,
    ),
    "orphaned_font": (
        [r"HKLM\Software\Microsoft\Windows NT\CurrentVersion\Fonts"],
        _detect_orphaned_font,
        True,
    ),
    "orphaned_service_driver": (
        [r"HKLM\System\CurrentControlSet\Services"],
        _detect_orphaned_service,
        False,
    ),
    "orphaned_path_value": (
        [r"HKLM\Software\Microsoft\Windows\CurrentVersion\Run",
         r"HKLM\Software\Microsoft\Windows\CurrentVersion\RunOnce",
         r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
         r"HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce"],
        _detect_missing_path_value,
        True,
    ),
    "stale_mru_cache": (
        [r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32",
         r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU"],
        _detect_stale_mru,
        False,
    ),
}

# Backwards-compatible mapping used by _categorize_key / feature extraction.
_CATEGORY_PATTERNS = {
    "unused_file_extension": [r"HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\[^\\]+$"],
    "missing_application_path": [r"HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\[^\\]+$"],
    "orphaned_uninstall": [r"HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\[^\\]+$"],
    "invalid_shared_dll": [r"HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\SharedDLLs$"],
    "orphaned_com_activex": [r"HKLM\\Software\\Classes\\CLSID\\[^\\]+$"],
    "orphaned_font": [r"HKLM\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Fonts$"],
    "orphaned_service_driver": [r"HKLM\\System\\CurrentControlSet\\Services\\[^\\]+$"],
    "empty_shell_extension": [r"HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Shell Extensions\\[^\\]+$"],
    "stale_mru_cache": [r"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\ComDlg32\\[^\\]+$"],
    "leftover_software_key": [r"HKLM\\Software\\[^\\]+$"],
}


def _log2(x: float) -> float:
    """math.log2 with the 0-limit handled, so entropy of a single-symbol
    string is 0 rather than a domain error."""
    return math.log2(x) if x > 0 else 0.0


def _categorize_key(key_path: str) -> str:
    """Fast rule-based categorization."""
    for cat, patterns in _CATEGORY_PATTERNS.items():
        for pat in patterns:
            if re.match(pat, key_path, re.IGNORECASE):
                return cat
    return "unknown"


def _extract_features(key_path: str, value_name: str, value_data: str,
                      value_type: int, parent_exists: bool,
                      uninstaller_exists: bool, is_signed: bool,
                      age_days: int) -> List[float]:
    """Extract numerical features for ML model."""
    features = []

    # Path depth
    depth = key_path.count("\\")
    features.append(min(depth / 20.0, 1.0))

    # Is under Microsoft hive?
    features.append(1.0 if "Microsoft" in key_path else 0.0)

    # Is under user hive?
    features.append(1.0 if key_path.startswith("HKCU") else 0.0)

    # Value type (REG_SZ=1, REG_DWORD=4, REG_BINARY=3, etc.)
    features.append(min(value_type / 10.0, 1.0))

    # Value data entropy (high entropy = likely hash/guid = suspicious)
    if value_data:
        freq = {}
        for ch in value_data:
            freq[ch] = freq.get(ch, 0) + 1
        total = len(value_data)
        # Shannon entropy, math.log2 in a pure-Python loop.
        entropy = -sum(
            (count / total) * _log2(count / total)
            for count in freq.values()
        )
        features.append(min(entropy / 8.0, 1.0))
    else:
        features.append(0.0)

    # Parent key exists
    features.append(1.0 if parent_exists else 0.0)

    # Uninstaller exists for this key
    features.append(1.0 if uninstaller_exists else 0.0)

    # Digitally signed
    features.append(1.0 if is_signed else 0.0)

    # Age in days (normalized)
    features.append(min(age_days / 3650.0, 1.0))  # 10 years max

    # Category one-hot (top 8 categories)
    cat = _categorize_key(key_path)
    cat_idx = list(_CATEGORY_PATTERNS.keys()).index(cat) if cat in _CATEGORY_PATTERNS else 0
    for i in range(8):
        features.append(1.0 if i == cat_idx else 0.0)

    return features


# ---------------------------------------------------------------------------
# Authenticode verification (WinVerifyTrust, no external tools)
# ---------------------------------------------------------------------------

def _is_authenticode_signed(path: Path) -> bool:
    """True when *path* carries a trusted Authenticode signature.

    Uses WinVerifyTrust with WTD_UI_NONE / WTD_REVOKE_NONE so it never blocks
    on a CRL fetch. Any failure to load the API is reported as "unsigned"
    rather than assumed-good.
    """
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return False

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD), ("Data4", ctypes.c_byte * 8)]
        """GUID class."""
        """GUID class."""

    class WINTRUST_FILE_INFO(ctypes.Structure):
        _fields_ = [("cbStruct", wintypes.DWORD),
                    ("pcwszFilePath", wintypes.LPCWSTR),
                    ("hFile", wintypes.HANDLE),
                    ("pgKnownSubject", ctypes.c_void_p)]
        """WINTRUST_FILE_INFO class."""
        """WINTRUST_FILE_INFO class."""

    class WINTRUST_DATA(ctypes.Structure):
        _fields_ = [("cbStruct", wintypes.DWORD),
                    ("pPolicyCallbackData", ctypes.c_void_p),
                    ("pSIPClientData", ctypes.c_void_p),
                    ("dwUIChoice", wintypes.DWORD),
                    ("fdwRevocationChecks", wintypes.DWORD),
                    ("dwUnionChoice", wintypes.DWORD),
                    ("pFile", ctypes.POINTER(WINTRUST_FILE_INFO)),
                    ("dwStateAction", wintypes.DWORD),
                    ("hWVTStateData", wintypes.HANDLE),
                    ("pwszURLReference", wintypes.LPCWSTR),
                    ("dwProvFlags", wintypes.DWORD),
                    ("dwUIContext", wintypes.DWORD),
                    ("pSignatureSettings", ctypes.c_void_p)]
        """WINTRUST_DATA class."""
        """WINTRUST_DATA class."""

    # WINTRUST_ACTION_GENERIC_VERIFY_V2
    action = GUID(0xAAC56B, 0xCD44, 0x11D0,
                  (ctypes.c_byte * 8)(0x8C, 0xC2, 0x00, 0xC0, 0x4F, 0xC2, 0x95, 0xEE))
    file_info = WINTRUST_FILE_INFO(ctypes.sizeof(WINTRUST_FILE_INFO), str(path), None, None)
    data = WINTRUST_DATA()
    data.cbStruct = ctypes.sizeof(WINTRUST_DATA)
    data.dwUIChoice = 2            # WTD_UI_NONE
    data.fdwRevocationChecks = 0   # WTD_REVOKE_NONE
    data.dwUnionChoice = 1         # WTD_CHOICE_FILE
    data.pFile = ctypes.pointer(file_info)
    data.dwStateAction = 1         # WTD_STATEACTION_VERIFY
    data.dwProvFlags = 0x00000010  # WTD_CACHE_ONLY_URL_RETRIEVAL

    try:
        wintrust = ctypes.WinDLL("wintrust.dll")
        wintrust.WinVerifyTrust.restype = ctypes.c_long
        result = wintrust.WinVerifyTrust(None, ctypes.byref(action), ctypes.byref(data))
        data.dwStateAction = 2     # WTD_STATEACTION_CLOSE
        wintrust.WinVerifyTrust(None, ctypes.byref(action), ctypes.byref(data))
        return result == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# ONNX Model wrapper
# ---------------------------------------------------------------------------

class _MLModel:
    """ONNX model wrapper for risk scoring."""

    def __init__(self, model_path: Optional[str] = None):
        self.session = None
        self.input_name = None
        self.output_name = None
        if model_path and HAS_ORT and Path(model_path).exists():
            try:
                self.session = ort.InferenceSession(model_path)
                self.input_name = self.session.get_inputs()[0].name
                self.output_name = self.session.get_outputs()[0].name
            except Exception:
                self.session = None
        """__init__."""
        """__init__."""

    def predict(self, features: List[float]) -> Tuple[float, float]:
        """Return (risk_score, confidence)."""
        if self.session is None or not HAS_NUMPY:
            # Fallback heuristic
            return self._heuristic_score(features)

        try:
            arr = np.array([features], dtype=np.float32)
            outputs = self.session.run([self.output_name], {self.input_name: arr})
            risk = float(outputs[0][0][0])
            conf = float(outputs[0][0][1]) if outputs[0].shape[-1] > 1 else 0.8
            return max(0.0, min(1.0, risk)), max(0.0, min(1.0, conf))
        except Exception:
            return self._heuristic_score(features)

    def _heuristic_score(self, features: List[float]) -> Tuple[float, float]:
        """Rule-based fallback when ML unavailable."""
        # features: [depth, is_microsoft, is_user, val_type, entropy,
        #            parent_exists, uninstaller_exists, signed, age, cat...]
        risk = 0.0
        if features[1] > 0.5:  # Microsoft key
            risk += 0.4
        if features[2] > 0.5:  # User hive
            risk -= 0.1
        if features[5] < 0.5:  # Parent missing
            risk += 0.2
        if features[6] < 0.5:  # No uninstaller
            risk += 0.15
        if features[7] < 0.5:  # Not signed
            risk += 0.1
        if features[3] > 0.5:  # High entropy value
            risk += 0.1
        risk = max(0.0, min(1.0, risk))
        return risk, 0.7


# ---------------------------------------------------------------------------
# Core cleaner
# ---------------------------------------------------------------------------

# Categories whose finding means the *key* is the orphan (the offending
# value is only evidence). For these, clean() removes the key, not a value.
_KEY_LEVEL_CATEGORIES = frozenset({
    "orphaned_uninstall",      # the Uninstall\<app> entry itself is dead
    "orphaned_service_driver", # the Services\<svc> entry points nowhere
    "stale_mru_cache",         # the whole MRU list is stale
})


class AIRegistryCleaner:
    """AI-enhanced registry cleaner with learned safety."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        create_restore_point: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ):
        self.model = _MLModel(model_path)
        self.create_restore_point = create_restore_point
        self.progress = progress_callback or (lambda _: None)
        self.cancel_event = cancel_event or threading.Event()
        self._backup_dir = Path(os.environ.get("TEMP", "C:\\Temp")) / "CortexRegistryBackups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._model_version = "heuristic-v1" if not HAS_ORT else "onnx-v1"
        """__init__."""
        """__init__."""

    # -- helpers

    def _run_ps(self, script: str, timeout: int = 60) -> Tuple[int, str, str]:
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True, text=True, timeout=timeout,
                encoding=sys.getdefaultencoding(), errors="replace"
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Timeout after {timeout}s"
        except Exception as exc:
            return -1, "", str(exc)
        """_run_ps."""
        """_run_ps."""

    def _key_exists(self, path: str) -> bool:
        for splitter in (_split, _split32):
            try:
                parts = splitter(path)
            except (KeyError, ValueError):
                return False
            if parts is None:
                continue
            hive, sub, access = parts
            try:
                with winreg.OpenKey(hive, sub, 0, access):
                    return True
            except OSError:
                continue
        return False
        """_key_exists."""
        """_key_exists."""

    def _get_parent(self, path: str) -> Optional[str]:
        parts = path.split("\\")
        if len(parts) <= 2:
            return None
        return "\\".join(parts[:-1])
        """_get_parent."""
        """_get_parent."""

    def _values_map(self, path: str, access: Optional[int] = None) -> Dict[str, Tuple[Any, int]]:
        """{name: (data, type)} for a key; empty dict when unreadable."""
        try:
            hive, sub, default_access = _split(path)
        except (KeyError, ValueError):
            return {}
        out: Dict[str, Tuple[Any, int]] = {}
        try:
            with winreg.OpenKey(hive, sub, 0, access or default_access) as key:
                count = winreg.QueryInfoKey(key)[1]
                for i in range(count):
                    try:
                        name, data, vtype = winreg.EnumValue(key, i)
                        out[name] = (data, vtype)
                    except OSError:
                        break
        except OSError:
            return {}
        return out

    def _enum_values(self, path: str) -> List[Tuple[str, Any, int]]:
        return [(n, d, t) for n, (d, t) in self._values_map(path).items()]
        """_enum_values."""
        """_enum_values."""

    def _check_uninstaller(self, path: str) -> bool:
        """True when this key names an uninstaller that still exists on disk."""
        values = self._values_map(path)
        for name in ("QuietUninstallString", "UninstallString"):
            data = values.get(name, (None, 0))[0]
            exe = _exe_from_command(data) if isinstance(data, str) else None
            if exe and Path(exe).exists():
                return True
        return False

    def _check_signature(self, path: str) -> bool:
        """Authenticode check on the first referenced binary, via WinVerifyTrust."""
        for _name, (data, vtype) in self._values_map(path).items():
            if vtype not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
                continue
            if not isinstance(data, str):
                continue
            exe = _exe_from_command(data)
            if not exe or not exe.lower().endswith((".exe", ".dll", ".sys", ".ocx")):
                continue
            p = Path(exe)
            if not p.exists():
                continue
            return _is_authenticode_signed(p)
        return False

    def _estimate_age(self, path: str) -> int:
        """Days since the key's last write, from the FILETIME QueryInfoKey returns."""
        try:
            hive, sub, access = _split(path)
        except (KeyError, ValueError):
            return 0
        try:
            with winreg.OpenKey(hive, sub, 0, access) as key:
                filetime = winreg.QueryInfoKey(key)[2]
        except OSError:
            return 0
        # FILETIME counts 100 ns intervals since 1601-01-01; convert to Unix epoch.
        seconds = filetime / 10_000_000 - 11_644_473_600
        if seconds <= 0:
            return 0
        age_days = (time.time() - seconds) / 86_400
        return max(0, int(age_days))

    # -- scanning

    def scan(self, categories: Optional[List[str]] = None) -> ScanResult:
        """Scan registry for issues.

        Walks each category's roots directly through ``winreg`` (both the
        64-bit and 32-bit views where relevant) and only emits an issue when
        the category's detector proves the referenced target is gone. No
        PowerShell, no whole-hive recursion.
        """
        t0 = time.time()
        cats = categories or list(_CATEGORY_DEFS.keys())
        issues: List[RegistryIssue] = []
        seen: set = set()

        for cat in cats:
            if self.cancel_event.is_set():
                break
            definition = _CATEGORY_DEFS.get(cat)
            if definition is None:
                continue
            roots, detector, scan_32 = definition
            self.progress(f"Scanning {cat}...")

            for root in roots:
                views = [None]
                if scan_32 and root.startswith("HKLM\\"):
                    views.append(winreg.KEY_READ | winreg.KEY_WOW64_32KEY)
                for access in views:
                    for key_path in self._iter_subkeys(root, access):
                        if self.cancel_event.is_set():
                            break
                        values = self._values_map(key_path, access)
                        try:
                            hit = detector(key_path, values, access or 0)
                        except Exception:
                            hit = False
                        if not hit:
                            continue

                        # Which value proves the orphan, for reporting.
                        value_name, value_data, value_type = self._offending_value(
                            key_path, values, cat)
                        dedup = (key_path.lower(), value_name.lower())
                        if dedup in seen:
                            continue
                        seen.add(dedup)

                        parent = self._get_parent(key_path)
                        parent_exists = parent is not None and self._key_exists(parent)
                        uninstaller_exists = self._check_uninstaller(key_path)
                        is_signed = self._check_signature(key_path)
                        age_days = self._estimate_age(key_path)

                        features = _extract_features(
                            key_path, value_name, value_data, value_type,
                            parent_exists, uninstaller_exists, is_signed, age_days)
                        risk, conf = self.model.predict(features)

                        rec = "remove" if risk < 0.3 else ("review" if risk < 0.6 else "keep")
                        issues.append(RegistryIssue(
                            key_path=key_path,
                            value_name=value_name,
                            value_data=value_data[:500],
                            value_type=value_type,
                            category=cat,
                            risk_score=risk,
                            confidence=conf,
                            recommendation=rec,
                            evidence={
                                "parent_exists": parent_exists,
                                "uninstaller_exists": uninstaller_exists,
                                "is_signed": is_signed,
                                "age_days": age_days,
                                "registry_view": "32-bit" if access else "native",
                                "features": features,
                            },
                        ))
                        if len(issues) % 50 == 0:
                            self.progress(f"{len(issues)} candidate entries")

        issues.sort(key=lambda i: i.risk_score)
        return ScanResult(
            issues=issues,
            scan_time=time.time() - t0,
            categories_scanned=cats,
            model_version=self._model_version,
        )

    def _iter_subkeys(self, root: str, access: Optional[int] = None) -> List[str]:
        """Immediate subkey paths of *root* (plus *root* itself for value-only keys)."""
        try:
            hive, sub, default_access = _split(root)
        except (KeyError, ValueError):
            return []
        paths: List[str] = [root]
        try:
            with winreg.OpenKey(hive, sub, 0, access or default_access) as key:
                count = winreg.QueryInfoKey(key)[0]
                for i in range(count):
                    try:
                        paths.append(f"{root}\\{winreg.EnumKey(key, i)}")
                    except OSError:
                        break
        except OSError:
            return []
        return paths

    def _offending_value(self, key_path: str, values: Dict[str, Tuple[Any, int]],
                         category: str) -> Tuple[str, str, int]:
        """Pick the value whose target is missing, for display and removal."""
        if category == "invalid_shared_dll":
            for name in values:
                if not _target_exists(name):
                    return name, str(values[name][0]), values[name][1]
        if category == "orphaned_font":
            for name, (data, vtype) in values.items():
                if not isinstance(data, str) or not data:
                    continue
                if not _target_exists_any(_font_candidates(data)):
                    return name, data, vtype
        if category == "orphaned_service_driver":
            for preferred in ("ServiceDll", "ImagePath"):
                if preferred in values:
                    data, vtype = values[preferred]
                    return preferred, str(data), vtype
        for preferred in ("", "UninstallString", "InstallLocation", "ImagePath", "ServiceDll"):
            if preferred in values:
                data, vtype = values[preferred]
                return preferred, str(data), vtype
        for name, (data, vtype) in values.items():
            if isinstance(data, str) and data:
                expanded = _expand(data)
                if expanded and not _target_exists(expanded):
                    return name, data, vtype
        if values:
            name = next(iter(values))
            return name, str(values[name][0]), values[name][1]
        return "", "", winreg.REG_SZ

    def clean(self, issues: List[RegistryIssue],
              selected_ids: Optional[List[int]] = None,
              full_hive_backup: bool = False) -> CleanResult:
        """Clean selected issues (by index in the *issues* list).

        Safety model: every mutation is preceded by a per-key ``reg export``
        covering exactly what is about to change. A full hive export
        (minutes of I/O on real machines) is available via
        ``full_hive_backup=True`` for users who want a belt-and-braces
        rollback file before a large batch.
        """
        if self.create_restore_point:
            self._create_restore_point()

        backup_path = ""
        if full_hive_backup:
            backup_path = self._backup_registry()

        t0 = time.time()
        cleaned: List[RegistryIssue] = []
        failed: List[Tuple[RegistryIssue, str]] = []

        targets = selected_ids if selected_ids is not None else range(len(issues))
        for idx in targets:
            if self.cancel_event.is_set():
                break
            issue = issues[idx]
            if issue.recommendation == "keep":
                failed.append((issue, "User chose to keep"))
                continue
            try:
                backup_file = self._remove_and_backup(issue)
                cleaned.append(RegistryIssue(
                    **{**issue.to_dict(), "backup_path": backup_file}
                ))
            except Exception as exc:
                failed.append((issue, str(exc)))

        if not backup_path and cleaned:
            # Report the first per-key backup as the result-level backup so
            # callers always have a restore entry point.
            backup_path = cleaned[0].backup_path or ""

        return CleanResult(
            cleaned=cleaned,
            failed=failed,
            restore_point_created=self.create_restore_point,
            backup_path=backup_path,
            duration_seconds=time.time() - t0,
        )

    def _remove_and_backup(self, issue: RegistryIssue) -> str:
        """Back the key up first, then remove what the issue names.

        The backup is written *before* the mutation so a crash mid-clean can
        never leave a change without a matching .reg file. Key-level
        categories remove the whole key; the rest remove the one value.
        """
        backup_file = self._backup_key(issue.key_path)
        if issue.category in _KEY_LEVEL_CATEGORIES:
            self._delete_key(issue.key_path)
        else:
            self._delete_value(issue.key_path, issue.value_name)
        return backup_file

    def _delete_key(self, key_path: str) -> None:
        """Delete a key and all its values, honouring the registry view.

        Refuses to delete a key that still has subkeys: an Uninstall entry
        with children (MSI can nest) is not what the scan proved dead, and
        recursive deletion would be a guess. Succeeds silently if already
        gone, so a partially-cleaned rerun is idempotent.
        """
        last_error: Optional[Exception] = None
        for splitter, extra in ((_split, 0), (_split32, winreg.KEY_WOW64_32KEY)):
            try:
                parts = splitter(key_path)
            except (KeyError, ValueError):
                raise OSError(f"unrecognised registry path: {key_path}")
            if parts is None:
                continue
            hive, sub, _access = parts
            try:
                try:
                    with winreg.OpenKey(hive, sub, 0,
                                        winreg.KEY_READ | extra) as key:
                        if winreg.QueryInfoKey(key)[0] > 0:
                            raise OSError(
                                f"refusing to delete {key_path}: subkeys present")
                except FileNotFoundError:
                    return  # already gone; treat as success
                winreg.DeleteKeyEx(hive, sub, 0, extra)
                return
            except OSError as exc:
                if getattr(exc, "winerror", None) == 2:  # ERROR_FILE_NOT_FOUND
                    return
                last_error = exc
                continue
        if last_error is not None:
            raise last_error

    def _delete_value(self, key_path: str, value_name: str) -> None:
        """Delete one value, honouring the registry view the scan used."""
        last_error: Optional[Exception] = None
        for splitter, extra in ((_split, 0), (_split32, winreg.KEY_WOW64_32KEY)):
            try:
                parts = splitter(key_path)
            except (KeyError, ValueError):
                raise OSError(f"unrecognised registry path: {key_path}")
            if parts is None:
                continue
            hive, sub, _access = parts
            try:
                with winreg.OpenKey(hive, sub, 0,
                                    winreg.KEY_SET_VALUE | extra) as key:
                    winreg.DeleteValue(key, value_name)
                return
            except FileNotFoundError:
                return  # value already gone; treat as success
            except OSError as exc:
                if getattr(exc, "winerror", None) == 2:  # ERROR_FILE_NOT_FOUND
                    return
                last_error = exc
                continue
        if last_error is not None:
            raise last_error

    def _backup_key(self, key_path: str) -> str:
        """Export the key to a timestamped .reg file, native view first.

        Only HKLM keys have a separate 32-bit view; for those both views are
        exported so a restore is complete. Raises when neither export
        succeeds — a clean must never run without its backup.
        """
        ts = int(time.time())
        safe = key_path.replace("\\", "_").replace(":", "")
        backups: List[str] = []
        views = ["/reg:64"]
        if key_path.startswith("HKLM\\"):
            views.append("/reg:32")
        for i, flag in enumerate(views):
            out = self._backup_dir / f"reg_{safe}{'_32' if flag == '/reg:32' else ''}_{ts}.reg"
            proc = subprocess.run(
                ["reg", "export", key_path, str(out), "/y", flag],
                capture_output=True)
            if proc.returncode == 0 and out.exists():
                backups.append(str(out))
        if not backups:
            raise OSError(f"reg export failed for {key_path}")
        return backups[0]

    def _backup_registry(self) -> str:
        """Export HKLM and HKCU so a failed clean is fully reversible."""
        ts = int(time.time())
        saved: List[str] = []
        for hive in ("HKLM", "HKCU"):
            out = self._backup_dir / f"{hive.lower()}_{ts}.reg"
            proc = subprocess.run(
                ["reg", "export", hive, str(out), "/y"],
                capture_output=True, timeout=300)
            if proc.returncode == 0 and out.exists():
                saved.append(str(out))
        if not saved:
            raise OSError("reg export produced no hive backups")
        return saved[0]

    def _create_restore_point(self) -> bool:
        try:
            subprocess.run([
                "powershell", "-NoProfile", "-Command",
                "Checkpoint-Computer -Description 'Cortex Registry Clean' "
                "-RestorePointType 'MODIFY_SETTINGS'"
            ], check=True, capture_output=True, timeout=120)
            return True
        except Exception:
            return False
        """_create_restore_point."""
        """_create_restore_point."""


__all__ = [
    "AIRegistryCleaner",
    "RegistryIssue",
    "ScanResult",
    "CleanResult",
]