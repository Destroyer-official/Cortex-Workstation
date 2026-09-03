"""Gaming Mode - one-click, fully reversible PC boost for game sessions.

What "boost" honestly means here (no FPS fairy dust):

* **Power plan switch** - move to the machine's best high-performance scheme
  for the session, restore the previous plan on exit.
* **Background quieting** - *suspend* (never kill) known-noise processes such
  as sync clients and updaters so they stop competing for CPU/disk during the
  session, then resume exactly those processes afterwards.

Safety model:

* A fixed protected list keeps every OS-critical process (and Cortex itself)
  untouchable; suspend candidates come from a conservative default allowlist
  plus caller-supplied extras - nothing arbitrary is ever touched.
* ``preview()`` shows exactly what would change before anything happens;
  ``start()`` returns per-item results and ``stop()`` restores state even if
  the session ended abnormally (see :meth:`GameMode.__exit__`).

Requires Premium (``Feature.GAMING_MODE``); callers gate via licensing.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover - psutil is a core dependency
    psutil = None  # type: ignore

from cortex_unified.core import proc as _proc
from cortex_unified.system_tools.performance_tuner import PerformanceTuner

_LOG = logging.getLogger("cortex.system_tools.game_mode")
_IS_WINDOWS = sys.platform == "win32"

#: Processes never eligible for suspension, ever. Lower-case names.
_PROTECTED: frozenset[str] = frozenset({
    "system", "registry", "memory compression", "idle",
    "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe",
    "lsass.exe", "svchost.exe", "dwm.exe", "winmgmt.exe", "audiodg.exe",
    "explorer.exe", "fontdrvhost.exe", "conhost.exe", "sihost.exe",
    # Ourselves (any interpreter name) so boosting can't suspend Cortex.
    "python.exe", "pythonw.exe", "python3.exe", "cortex.exe",
})

#: Conservative default suspend candidates: sync/updater noise whose pause
#: cannot cost user data (they resume cleanly). Users may extend this list.
_DEFAULT_SUSPEND_CANDIDATES: tuple[str, ...] = (
    "onedrive.exe", "dropbox.exe", "googledrivefs.exe", "googledrivesync.exe",
    "icloudservices.exe", "itunes_helper.exe", "spotify.exe",
    "adobearmhelper.exe", "acrotray.exe", "teams.exe", "slack.exe",
    "discorduptileservice.exe", "steamwebhelper_quiet.exe",
    "epicgameslauncher.exe", "originwebhelperservice.exe", "updater.exe",
)


@dataclass(slots=True)
class BoostReport:
    """Outcome of starting or stopping a boosted session."""

    ok: bool
    phase: str                       # "start" | "stop"
    power_from: str | None = None
    power_to: str | None = None
    suspended: list[str] = field(default_factory=list)
    resumed: list[str] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "ok": self.ok,
            "phase": self.phase,
            "power_from": self.power_from,
            "power_to": self.power_to,
            "suspended": self.suspended,
            "resumed": self.resumed,
            "skipped": self.skipped,
            "errors": self.errors,
            "message": self.message,
        }


class GameMode:
    """Apply and revert a gaming-session performance profile."""

    def __init__(
        self,
        extra_suspend: tuple[str, ...] = (),
        dry_run: bool = False,
    ) -> None:
        """Initialize Game Mode."""
        self._extra = tuple(n.strip().lower() for n in extra_suspend if n.strip())
        self._dry_run = bool(dry_run)
        self._tuner = PerformanceTuner()
        self._original_plan: str | None = None   # GUID of plan before boost
        self._boosted_plan_guid: str | None = None
        self._suspended_pids: dict[int, str] = {}  # pid -> name
        self.active = False

    # -- discovery ----------------------------------------------------------

    @staticmethod
    def is_supported() -> bool:
        """Boost needs Windows power plans + psutil."""
        return _IS_WINDOWS and psutil is not None

    def _candidates(self) -> list[tuple[int, str]]:
        """Running processes matching the suspend lists (protected excluded)."""
        found: list[tuple[int, str]] = []
        wanted = set(_DEFAULT_SUSPEND_CANDIDATES) | set(self._extra)
        if psutil is None:
            return found
        for proc in psutil.process_iter(attrs=["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if not name or name in _PROTECTED:
                    continue
                if name in wanted and proc.info.get("pid", 0) != os.getpid():
                    found.append((proc.info["pid"], proc.info["name"]))
            except Exception:  # noqa: BLE001 - processes vanish mid-iteration
                continue
        return sorted(found, key=lambda item: item[1].lower())

    def preview(self) -> dict[str, Any]:
        """Read-only view of exactly what ``start()`` would change."""
        plans = self._tuner.list_plans()
        best = self._pick_boost_plan(plans)
        return {
            "supported": self.is_supported(),
            "power_now": (self._tuner.active_plan() or {}).get("name")
            if isinstance(self._tuner.active_plan(), dict)
            else getattr(self._tuner.active_plan(), "name", None),
            "power_would_switch_to": getattr(best, "name", None),
            "would_suspend": [name for _pid, name in self._candidates()],
            "dry_run": self._dry_run,
        }

    # -- lifecycle -------------------------------------------------------------

    def start(self) -> BoostReport:
        """Apply the boost profile (idempotent; safe while already active)."""
        if not self.is_supported():
            return BoostReport(False, "start",
                               message="Gaming mode requires Windows and psutil.")
        report = BoostReport(ok=True, phase="start")

        # 1) Power plan ------------------------------------------------------
        active = self._tuner.active_plan()
        report.power_from = getattr(active, "name", None)
        if active is not None:
            self._original_plan = active.guid
        best = self._pick_boost_plan(self._tuner.list_plans())
        if best is not None and (active is None or best.guid != active.guid):
            if self._dry_run:
                report.power_to = best.name
            else:
                switched, message = self._tuner.set_active(best.guid)
                if switched:
                    self._boosted_plan_guid = best.guid
                    report.power_to = best.name
                else:
                    report.errors.append(f"power plan: {message}")

        # 2) Background quieting ----------------------------------------------
        for pid, name in self._candidates():
            try:
                proc = psutil.Process(pid)
                if not self._dry_run:
                    proc.suspend()
                    self._suspended_pids[pid] = name
                report.suspended.append(name)
            except Exception as exc:  # noqa: BLE001 - per-process isolation
                report.skipped.append({"name": name, "reason": str(exc)})

        self.active = True
        parts = []
        if report.power_to:
            parts.append(f"power plan -> {report.power_to}")
        if report.suspended:
            parts.append(f"{len(report.suspended)} background app(s) paused")
        report.message = ("; ".join(parts) + (" (dry run)" if self._dry_run else "")) \
            or "already optimal; nothing changed"
        _LOG.info("game mode start: %s", report.message)
        return report

    def stop(self) -> BoostReport:
        """Restore power plan and resume everything this session suspended."""
        report = BoostReport(ok=True, phase="stop")
        if self._boosted_plan_guid and self._original_plan:
            switched, message = self._tuner.set_active(self._original_plan)
            if switched:
                report.power_to = self._original_plan
            else:
                report.errors.append(f"restore plan: {message}")
        self._boosted_plan_guid = None

        if not self._dry_run:
            for pid, name in list(self._suspended_pids.items()):
                try:
                    psutil.Process(pid).resume()
                    report.resumed.append(name)
                except Exception as exc:  # noqa: BLE001
                    report.errors.append(f"resume {name}: {exc}")
        self._suspended_pids.clear()
        self.active = False
        report.message = f"restored ({len(report.resumed)} resumed)" \
            if report.resumed else "restored"
        _LOG.info("game mode stop: %s", report.message)
        return report

    # -- context-manager sugar ------------------------------------------------

    def __enter__(self) -> "GameMode":
        self.start()
        return self
        """__enter__."""
        """__enter__."""

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self.stop()
        except Exception:  # noqa: BLE001 - restoring must never mask errors
            _LOG.exception("game-mode restore failed")
        """__exit__."""
        """__exit__."""

    # -- helpers ------------------------------------------------------------------

    def _pick_boost_plan(self, plans):
        """Choose the highest-performance scheme available, else None."""
        if not plans:
            return None
        keywords = ("high performance", "ultimate", "high", "performance")
        for keyword in keywords:
            for plan in plans:
                if keyword in plan.name.lower():
                    return plan
        return None


def run_proc_checked(args: list[str]) -> bool:  # pragma: no cover - thin helper
    """Convenience wrapper used by diagnostics; True when exit code is 0."""
    try:
        completed = _proc.run(args, text=True, timeout=15)
        return completed.returncode == 0
    except Exception:
        return False
