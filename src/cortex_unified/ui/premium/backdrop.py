"""Optional native window backdrop (Windows 11 Mica/Acrylic).

This module applies a best-effort system backdrop behind the frameless shell
using the Desktop Window Manager (DWM) via ``ctypes``. It is a *progressive
enhancement*: on Windows 11 builds that support it, the window gains a Mica or
Acrylic composited backdrop; on anything else (older Windows, non-Windows,
headless/offscreen) it does nothing and reports ``"opaque"`` so the app keeps
its solid, token-defined background with full contrast preserved.

Design contract (Req 12.4, 12.8):
  * ``apply_backdrop(win)`` NEVER raises on any platform.
  * It returns the applied mode name (e.g. ``"mica"``, ``"acrylic"``,
    ``"tabbed"``) or ``"opaque"`` when no native backdrop was applied.
  * Failure to apply an effect degrades silently to the opaque fallback.
"""

from __future__ import annotations

import logging
import platform

_LOG = logging.getLogger("cortex.ui.premium.backdrop")

# --- DWM constants (Windows 11) -------------------------------------------
# DwmSetWindowAttribute attribute ids.
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_SYSTEMBACKDROP_TYPE = 38

# DWM_SYSTEMBACKDROP_TYPE values (Windows 11 22H2+).
_DWMSBT_AUTO = 0
_DWMSBT_NONE = 1
_DWMSBT_MAINWINDOW = 2  # Mica
_DWMSBT_TRANSIENTWINDOW = 3  # Acrylic
_DWMSBT_TABBEDWINDOW = 4  # Tabbed (Mica Alt)

_BACKDROP_NAMES = {
    _DWMSBT_MAINWINDOW: "mica",
    _DWMSBT_TRANSIENTWINDOW: "acrylic",
    _DWMSBT_TABBEDWINDOW: "tabbed",
}

# Minimum Windows 11 build that exposes DWMWA_SYSTEMBACKDROP_TYPE.
_MIN_BACKDROP_BUILD = 22000


def _windows_build() -> int:
    """Return the Windows build number, or 0 if it cannot be determined."""
    try:
        # e.g. "10.0.22631" -> 22631
        release = platform.version()
        parts = release.split(".")
        if len(parts) >= 3:
            return int(parts[2])
    except Exception:  # noqa: BLE001
        pass
    return 0


def apply_backdrop(win) -> str:
    """Apply a best-effort native system backdrop behind ``win``.

    Returns the applied mode name (``"mica"``/``"acrylic"``/``"tabbed"``) or
    ``"opaque"`` when no native backdrop could be applied. Never raises.
    """
    try:
        if platform.system() != "Windows":
            return "opaque"

        build = _windows_build()
        if build and build < _MIN_BACKDROP_BUILD:
            # Older Windows (10 / early 11) lacks the backdrop attribute.
            return "opaque"

        import ctypes

        # Resolve the native window handle from the Qt window.
        try:
            hwnd = int(win.winId())
        except Exception:  # noqa: BLE001
            return "opaque"
        if not hwnd:
            return "opaque"

        dwmapi = ctypes.windll.dwmapi  # type: ignore[attr-defined]

        # Prefer immersive dark mode so the composited backdrop matches the
        # dark shell; failure here is non-fatal.
        try:
            dark = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                ctypes.c_int(_DWMWA_USE_IMMERSIVE_DARK_MODE),
                ctypes.byref(dark),
                ctypes.sizeof(dark),
            )
        except Exception:  # noqa: BLE001
            pass

        # Request the Mica (main window) backdrop.
        backdrop = _DWMSBT_MAINWINDOW
        value = ctypes.c_int(backdrop)
        hr = dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            ctypes.c_int(_DWMWA_SYSTEMBACKDROP_TYPE),
            ctypes.byref(value),
            ctypes.sizeof(value),
        )

        # DwmSetWindowAttribute returns an HRESULT; 0 (S_OK) means success.
        if hr == 0:
            return _BACKDROP_NAMES.get(backdrop, "opaque")

        _LOG.debug("DwmSetWindowAttribute returned HRESULT 0x%08X; using opaque", hr & 0xFFFFFFFF)
        return "opaque"
    except Exception as exc:  # noqa: BLE001
        # Fail soft: any unexpected error keeps the opaque token background.
        _LOG.debug("apply_backdrop failed, falling back to opaque: %s", exc)
        return "opaque"
