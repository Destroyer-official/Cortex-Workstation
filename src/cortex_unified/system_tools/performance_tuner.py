"""Windows power-plan tuner - safe, reversible performance control.

Wraps ``powercfg`` to list the available power schemes and switch the active
one (e.g. High Performance for gaming, Balanced for everyday, Power Saver on
battery). Switching a power plan is fully reversible and does not delete
anything, so this is a low-risk optimization. We deliberately do NOT touch
registry-based visual-effects tweaks or "game mode" hacks here - those are
easy to get wrong and hard to undo.
"""

from __future__ import annotations

import logging
import sys
import re
import subprocess
from dataclasses import dataclass
from typing import Any

from cortex_unified.core import proc as _proc

_LOG = logging.getLogger("cortex.system_tools.performance_tuner")
_IS_WINDOWS = sys.platform == "win32"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

# GUID -> friendly parsing regex for `powercfg /list` lines like:
#   Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced) *
_SCHEME_RE = re.compile(
    r"GUID:\s*([0-9a-fA-F-]{36})\s*\(([^)]*)\)\s*(\*?)"
)


@dataclass(slots=True)
class PowerPlan:
    """Powerplan.

    Manages PowerPlan operations and coordinates related state changes for the component.
    """

    guid: str
    name: str
    active: bool = False

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {"guid": self.guid, "name": self.name, "active": self.active}


class PerformanceTuner:
    """Performancetuner.

    Manages PerformanceTuner operations and coordinates related state changes for the component.
    """

    @staticmethod
    def is_supported() -> bool:
        """powercfg-based control only exists on Windows.

        Manages is supported operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return _IS_WINDOWS

    def list_plans(self) -> list[PowerPlan]:
        """Return available schemes; empty off-Windows or if powercfg fails.

        Manages list plans operations and coordinates related state changes for the component.

        Returns:
            list[PowerPlan]: List of processed items or identifiers.
        """
        if not _IS_WINDOWS:
            return []
        return self._parse(self._run(["powercfg", "/list"]))

    @staticmethod
    def _parse(out: str | None) -> list[PowerPlan]:
        """Parse and decode structured data from strings or byte streams.

        Extracts fields, validates expected formats, and instantiates corresponding strongly-typed model objects.

        Args:
            out (str | None): The out parameter.

        Returns:
            list[PowerPlan]: List of processed items or identifiers.
        """
        if not out:
            return []
        plans: list[PowerPlan] = []
        for line in out.splitlines():
            m = _SCHEME_RE.search(line)
            if m:
                guid, name, star = m.group(1), m.group(2).strip(), m.group(3)
                plans.append(PowerPlan(guid=guid, name=name, active=bool(star)))
        return plans

    def active_plan(self) -> PowerPlan | None:
        """Return the scheme powercfg marks active, or ``None`` if unknown.

        Manages active plan operations and coordinates related state changes for the component.

        Returns:
            PowerPlan | None: Result of the operation.
        """
        for p in self.list_plans():
            if p.active:
                return p
        return None

    def set_active(self, guid: str) -> tuple[bool, str]:
        """Switch the active power plan. Reversible; returns (ok, message).

        The GUID is shape-checked before it reaches argv because it comes from
        UI state, not from a prior ``/list`` call.
        """
        if not _IS_WINDOWS:
            return False, "Power plans are only available on Windows."
        if not re.fullmatch(r"[0-9a-fA-F-]{36}", guid or ""):
            return False, "Invalid power-plan identifier."
        out = self._run(["powercfg", "/setactive", guid], want_returncode=True)
        if out is True:
            return True, "Power plan activated."
        return False, "Could not switch power plan (Administrator may be required)."

    def _run(self, args: list[str], want_returncode: bool = False):
        """Run.

        Manages run operations and coordinates related state changes for the component.

        Args:
            args (list[str]): The args parameter.
            want_returncode (bool): The want returncode parameter.
        """
        try:
            proc = _proc.run(args, text=True, timeout=20, creationflags=_NO_WINDOW)
            if want_returncode:
                return proc.returncode == 0
            return proc.stdout if proc.returncode == 0 else None
        except (_proc.ProcessCancelled, OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("powercfg failed: %s", exc)
            return False if want_returncode else None
