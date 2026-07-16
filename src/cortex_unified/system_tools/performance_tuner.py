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
import platform
import re
import subprocess
from dataclasses import dataclass
from typing import Any

_LOG = logging.getLogger("cortex.system_tools.performance_tuner")
_IS_WINDOWS = platform.system() == "Windows"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

# GUID -> friendly parsing regex for `powercfg /list` lines like:
#   Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced) *
_SCHEME_RE = re.compile(
    r"GUID:\s*([0-9a-fA-F-]{36})\s*\(([^)]*)\)\s*(\*?)"
)


@dataclass(slots=True)
class PowerPlan:
    guid: str
    name: str
    active: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"guid": self.guid, "name": self.name, "active": self.active}


class PerformanceTuner:
    """List and switch Windows power plans via powercfg."""

    @staticmethod
    def is_supported() -> bool:
        return _IS_WINDOWS

    def list_plans(self) -> list[PowerPlan]:
        if not _IS_WINDOWS:
            return []
        return self._parse(self._run(["powercfg", "/list"]))

    @staticmethod
    def _parse(out: str | None) -> list[PowerPlan]:
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
        for p in self.list_plans():
            if p.active:
                return p
        return None

    def set_active(self, guid: str) -> tuple[bool, str]:
        """Switch the active power plan. Reversible; returns (ok, message)."""
        if not _IS_WINDOWS:
            return False, "Power plans are only available on Windows."
        if not re.fullmatch(r"[0-9a-fA-F-]{36}", guid or ""):
            return False, "Invalid power-plan identifier."
        out = self._run(["powercfg", "/setactive", guid], want_returncode=True)
        if out is True:
            return True, "Power plan activated."
        return False, "Could not switch power plan (Administrator may be required)."

    def _run(self, args: list[str], want_returncode: bool = False):
        try:
            proc = subprocess.run(
                args, capture_output=True, text=True, timeout=20,
                creationflags=_NO_WINDOW,
            )
            if want_returncode:
                return proc.returncode == 0
            return proc.stdout if proc.returncode == 0 else None
        except (OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("powercfg failed: %s", exc)
            return False if want_returncode else None
