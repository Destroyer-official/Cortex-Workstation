"""Release update checker - informational only.

Queries the project's GitHub releases API over HTTPS and reports whether a
newer tagged release exists. It NEVER downloads or installs anything: the
result is surfaced to the user (status bar / tray), who then updates through
the signed installer. This keeps the security surface minimal until a
verified auto-update channel (tufup / WinSparkle) is adopted - see
installer/README.md.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request

logger = logging.getLogger("update_checker")

RELEASES_API = "https://api.github.com/repos/Destroyer40/Cortex_Cleaner/releases/latest"
_TIMEOUT_S = 10

_TAG_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def parse_version(tag: str) -> tuple[int, int, int] | None:
    """'v1.2.3' / '1.2.3' -> (1, 2, 3); anything else -> None."""
    m = _TAG_RE.match((tag or "").strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def current_version() -> str:
    """The installed package version, from package metadata."""
    try:
        from importlib.metadata import version
        return version("cortex-cleaner")
    except Exception:  # noqa: BLE001 - unfrozen dev checkout
        return "0.0.0"


def fetch_latest_tag(api_url: str = RELEASES_API,
                     timeout: float = _TIMEOUT_S) -> str | None:
    """Latest release tag from GitHub, or None when offline/blocked."""
    req = urllib.request.Request(
        api_url,
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "cortex-cleaner-update-check"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError,
            json.JSONDecodeError) as exc:
        logger.debug("update check failed: %s", exc)
        return None
    tag = payload.get("tag_name")
    return tag if isinstance(tag, str) else None


def check_for_update(api_url: str = RELEASES_API,
                     timeout: float = _TIMEOUT_S,
                     installed: str | None = None) -> dict:
    """Compare installed version against the latest published release.

    Returns ``{"status": "up_to_date" | "update_available" | "unknown",
    ...}`` - never raises, so callers can fire it in the background and
    simply ignore failures.
    """
    installed = installed if installed is not None else current_version()
    installed_v = parse_version(installed)
    if installed_v is None:
        return {"status": "unknown", "installed": installed,
                "reason": "installed version not parseable"}
    tag = fetch_latest_tag(api_url, timeout)
    latest_v = parse_version(tag or "")
    if tag is None or latest_v is None:
        return {"status": "unknown", "installed": installed,
                "reason": "could not reach releases"}
    if latest_v > installed_v:
        return {"status": "update_available", "installed": installed,
                "latest": tag}
    return {"status": "up_to_date", "installed": installed,
            "latest": tag}
