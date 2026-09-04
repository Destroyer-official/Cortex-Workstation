"""Durable, atomically-written user settings for the premium GUI.

The premium shell needs a handful of preferences to survive restarts (which
theme the user chose, whether closing the window should minimise to the system
tray). This stores them as a tiny JSON document under the user's home so it is
per-user, needs no admin rights, and never touches the registry.

Design mirrors ``core.smart_suggest``'s persistence: writes go to a sibling
``.tmp`` file which is then ``replace``d over the target, so a crash mid-write
can never leave a half-written / corrupt settings file. A corrupt or missing
file always degrades to the built-in defaults rather than raising - settings are
a convenience, never a hard dependency of startup.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

_LOG = logging.getLogger("cortex.ui.premium.settings")

#: Bumped only if the on-disk shape changes incompatibly; an older/newer file is
#: ignored (defaults used) rather than mis-read.
_VERSION = 1

#: Built-in defaults. ``load`` returns a copy of these merged with any valid
#: stored values, so a key added in a future release is always present even when
#: reading a file written by an older build.
_DEFAULTS: dict[str, Any] = {
    "theme": "dark",          # "dark" | "light"
    "close_to_tray": False,   # minimise to tray on window close instead of quit
    "reduced_motion": False,  # suppress non-essential animation (accessibility)
    # Opt-in ONLY (consent research: phoning home without asking is not
    # acceptable for a cleaner that knows the user's software inventory).
    # When True the app performs one informational release check per run.
    "update_check": False,
    # Attempt a System Restore checkpoint before leftover cleanup.
    "leftover_restore_point": True,
}

_VALID_THEMES = ("dark", "light")


def settings_path() -> Path:
    """Return the settings file path (``~/.cortex_cleaner/settings.json``).

    Manages settings path operations and coordinates related state changes for the component.

    Returns:
        Path: Result of the operation.
    """
    return Path.home() / ".cortex_cleaner" / "settings.json"


class SettingsStore:
    """A tiny, corruption-tolerant key/value store persisted as JSON.

    Values are held in memory and written through to disk on every ``set`` so a
    preference toggled in the UI survives an immediate restart. All disk access
    is wrapped: any failure (read-only home, permission error, malformed file)
    degrades to in-memory defaults and is logged at debug level rather than
    surfacing to the user.
    """

    def __init__(self, path: Path | None = None):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            path (Path | None): Filesystem path to the target file or directory.
        """
        self._path = path or settings_path()
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self._load()

    # -- persistence --------------------------------------------------------

    def _load(self) -> None:
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        try:
            if self._path.exists():
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and raw.get("version") == _VERSION:
                    stored = raw.get("settings", {})
                    if isinstance(stored, dict):
                        for key in _DEFAULTS:
                            if key in stored:
                                self._data[key] = stored[key]
        except Exception as exc:  # noqa: BLE001 - a corrupt file must never crash startup
            _LOG.debug("could not load settings (%s); using defaults", exc)
            self._data = dict(_DEFAULTS)
        # Normalise after loading so an out-of-range stored value can't poison
        # callers that trust these keys.
        self._sanitize()

    def _sanitize(self) -> None:
        """Sanitize.

        Manages sanitize operations and coordinates related state changes for the component.
        """
        if self._data.get("theme") not in _VALID_THEMES:
            self._data["theme"] = _DEFAULTS["theme"]
        self._data["close_to_tray"] = bool(self._data.get("close_to_tray", False))
        self._data["reduced_motion"] = bool(self._data.get("reduced_motion", False))
        self._data["update_check"] = bool(self._data.get("update_check", False))
        # Default ON: a restore checkpoint before deletions is the safe choice.
        self._data["leftover_restore_point"] = bool(
            self._data.get("leftover_restore_point", True))

    def save(self) -> bool:
        """Save configuration settings or analysis reports to persistent storage.

        Serializes current user preferences or generated report data to disk with integrity validation.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"version": _VERSION, "settings": self._data}
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(self._path)
            return True
        except Exception as exc:  # noqa: BLE001 - never crash on a failed save
            _LOG.debug("could not save settings: %s", exc)
            return False

    # -- accessors ----------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Get.

        Manages get operations and coordinates related state changes for the component.

        Args:
            key (str): The key parameter.
            default (Any): The default parameter.

        Returns:
            Any: Result of the operation.
        """
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set.

        Manages set operations and coordinates related state changes for the component.

        Args:
            key (str): The key parameter.
            value (Any): The value parameter.
        """
        self._data[key] = value
        self._sanitize()
        self.save()

    # Convenience typed accessors used by the shell -------------------------

    @property
    def theme(self) -> str:
        """Theme.

        Manages theme operations and coordinates related state changes for the component.

        Returns:
            str: Formatted string or path.
        """
        return str(self._data.get("theme", _DEFAULTS["theme"]))

    @theme.setter
    def theme(self, value: str) -> None:
        """Theme.

        Manages theme operations and coordinates related state changes for the component.

        Args:
            value (str): The value parameter.
        """
        self.set("theme", value)

    @property
    def close_to_tray(self) -> bool:
        """close_to_tray.

        Manages close to tray operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return bool(self._data.get("close_to_tray", False))

    @close_to_tray.setter
    def close_to_tray(self, value: bool) -> None:
        """close_to_tray.

        Manages close to tray operations and coordinates related state changes for the component.

        Args:
            value (bool): The value parameter.
        """
        self.set("close_to_tray", bool(value))

    @property
    def reduced_motion(self) -> bool:
        """reduced_motion.

        Manages reduced motion operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return bool(self._data.get("reduced_motion", False))

    @reduced_motion.setter
    def reduced_motion(self, value: bool) -> None:
        """reduced_motion.

        Manages reduced motion operations and coordinates related state changes for the component.

        Args:
            value (bool): The value parameter.
        """
        self.set("reduced_motion", bool(value))

    @property
    def update_check(self) -> bool:
        """update_check.

        Manages update check operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return bool(self._data.get("update_check", False))

    @update_check.setter
    def update_check(self, value: bool) -> None:
        """update_check.

        Manages update check operations and coordinates related state changes for the component.

        Args:
            value (bool): The value parameter.
        """
        self.set("update_check", bool(value))

    @property
    def leftover_restore_point(self) -> bool:
        """leftover_restore_point.

        Manages leftover restore point operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return bool(self._data.get("leftover_restore_point", True))

    @leftover_restore_point.setter
    def leftover_restore_point(self, value: bool) -> None:
        """leftover_restore_point.

        Manages leftover restore point operations and coordinates related state changes for the component.

        Args:
            value (bool): The value parameter.
        """
        self.set("leftover_restore_point", bool(value))
