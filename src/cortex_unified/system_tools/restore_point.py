"""Windows System Restore point management - the trust/safety foundation.

Every risky operation (registry cleaning, telemetry changes, driver updates)
should offer to create a restore point first. This module does that *honestly*:
it never claims success it can't verify.

Reality handled (researched, not assumed):
* ``Checkpoint-Computer`` requires **Administrator**; without elevation it is
  silently rejected - so we check elevation first and report NOT_ELEVATED
  rather than pretending a point was made.
* **System Protection is frequently OFF by default** on Windows 10/11 - a
  create call then does nothing; we detect the failure and report
  PROTECTION_DISABLED with guidance to enable it.
* Windows **throttles** creation to once per 24h (a warning, not an error). We
  compare the restore-point count before/after and report THROTTLED truthfully.

Non-Windows platforms report NOT_SUPPORTED. Nothing here creates a point unless
explicitly asked, and all subprocess calls are time-boxed and window-hidden.
"""

from __future__ import annotations

import enum
import logging
import sys
import subprocess
from dataclasses import dataclass
from typing import Any

from cortex_unified.core import proc as _proc

_LOG = logging.getLogger("cortex.system_tools.restore_point")

_IS_WINDOWS = sys.platform == "win32"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

# Valid Windows restore-point types (SRSetRestorePoint / Checkpoint-Computer).
_VALID_TYPES = {
    "APPLICATION_INSTALL",
    "APPLICATION_UNINSTALL",
    "DEVICE_DRIVER_INSTALL",
    "MODIFY_SETTINGS",
    "CANCELLED_OPERATION",
}


class RestoreStatus(str, enum.Enum):
    """Outcome of a restore-point create attempt - each is honest & distinct."""

    CREATED = "created"                      # a new point was verifiably made
    THROTTLED = "throttled"                  # skipped: one exists in last 24h
    PROTECTION_DISABLED = "protection_disabled"  # System Protection is off
    NOT_ELEVATED = "not_elevated"            # needs Administrator
    NOT_SUPPORTED = "not_supported"          # non-Windows
    FAILED = "failed"                        # other error (message attached)


@dataclass(slots=True)
class RestorePointResult:
    """Result of a create attempt."""

    status: RestoreStatus
    message: str = ""

    @property
    def created(self) -> bool:
        """Created."""
        return self.status is RestoreStatus.CREATED

    @property
    def ok_to_proceed(self) -> bool:
        """True if it's reasonable to continue a risky op after this attempt.

        CREATED and THROTTLED both mean a recent restore point exists; the
        others mean the user should be warned before proceeding without one.
        """
        return self.status in (RestoreStatus.CREATED, RestoreStatus.THROTTLED)

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {"status": self.status.value, "message": self.message, "created": self.created}


class RestorePointManager:
    """Create and list Windows System Restore points, honestly."""

    def __init__(self) -> None:
        """Initialize Restore Point Manager."""
        self.logger = _LOG

    # -- capability checks --------------------------------------------------

    @staticmethod
    def is_supported() -> bool:
        """Is supported."""
        return _IS_WINDOWS

    @staticmethod
    def is_elevated() -> bool:
        """True if running as Administrator (required to create a point)."""
        if not _IS_WINDOWS:
            return False
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:  # noqa: BLE001
            return False

    # -- create -------------------------------------------------------------

    def create(
        self,
        description: str = "Cortex Cleaner",
        restore_point_type: str = "MODIFY_SETTINGS",
    ) -> RestorePointResult:
        """Attempt to create a restore point and report the verified outcome."""
        if not _IS_WINDOWS:
            return RestorePointResult(RestoreStatus.NOT_SUPPORTED,
                                      "System Restore is only available on Windows.")
        if restore_point_type not in _VALID_TYPES:
            restore_point_type = "MODIFY_SETTINGS"
        if not self.is_elevated():
            return RestorePointResult(
                RestoreStatus.NOT_ELEVATED,
                "Creating a restore point requires Administrator privileges.",
            )

        # Sanitize description for embedding in a single-quoted PS string.
        desc = description.replace("'", "''")[:250]

        # One script: count -> checkpoint (warnings suppressed) -> count.
        # A count increase proves CREATED; equal count means THROTTLED; a thrown
        # error is mapped to PROTECTION_DISABLED or FAILED.
        script = (
            "$ErrorActionPreference='Stop';"
            "function _n { @(Get-CimInstance -Namespace root/default "
            "-ClassName SystemRestore -ErrorAction SilentlyContinue).Count }"
            "$before=_n;"
            "try {"
            f"  Checkpoint-Computer -Description '{desc}' "
            f"-RestorePointType '{restore_point_type}' -WarningAction SilentlyContinue;"
            "} catch {"
            "  $m=$_.Exception.Message;"
            "  if ($m -match 'disabled|turned off|not enabled|0x81000203') "
            "{ Write-Output 'STATUS=PROTECTION_DISABLED' }"
            "  else { Write-Output ('STATUS=FAILED;MSG='+$m) };"
            "  exit }"
            "$after=_n;"
            "if ($after -gt $before) { Write-Output 'STATUS=CREATED' } "
            "else { Write-Output 'STATUS=THROTTLED' }"
        )
        out = self._run_ps(script, timeout=120)
        return self._parse_create_output(out)

    @staticmethod
    def _parse_create_output(out: str | None) -> RestorePointResult:
        """_parse_create_output."""
        if not out:
            return RestorePointResult(
                RestoreStatus.FAILED,
                "No response from System Restore (it may be disabled or blocked by policy).",
            )
        line = next((ln.strip() for ln in out.splitlines() if ln.strip().startswith("STATUS=")), "")
        if line.startswith("STATUS=CREATED"):
            return RestorePointResult(RestoreStatus.CREATED, "Restore point created.")
        if line.startswith("STATUS=THROTTLED"):
            return RestorePointResult(
                RestoreStatus.THROTTLED,
                "A restore point already exists from the last 24 hours (Windows throttles creation).",
            )
        if line.startswith("STATUS=PROTECTION_DISABLED"):
            return RestorePointResult(
                RestoreStatus.PROTECTION_DISABLED,
                "System Protection is turned off. Enable it in System Properties > "
                "System Protection to allow restore points.",
            )
        if line.startswith("STATUS=FAILED"):
            _, _, msg = line.partition("MSG=")
            return RestorePointResult(RestoreStatus.FAILED, msg or "Restore point creation failed.")
        return RestorePointResult(RestoreStatus.FAILED, "Unexpected System Restore response.")
        """_parse_create_output."""
        """_parse_create_output."""

    # -- list ---------------------------------------------------------------

    def list_points(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return existing restore points (most recent first). Empty on failure."""
        if not _IS_WINDOWS:
            return []
        script = (
            "Get-CimInstance -Namespace root/default -ClassName SystemRestore "
            "-ErrorAction SilentlyContinue | "
            "Sort-Object SequenceNumber -Descending | "
            "Select-Object SequenceNumber, Description, RestorePointType, CreationTime | "
            "ConvertTo-Json -Compress"
        )
        out = self._run_ps(script, timeout=30)
        if not out:
            return []
        import json
        try:
            data = json.loads(out)
        except (ValueError, TypeError):
            return []
        if isinstance(data, dict):
            data = [data]
        points: list[dict[str, Any]] = []
        for item in data[:limit]:
            points.append({
                "sequence": item.get("SequenceNumber"),
                "description": item.get("Description", ""),
                "type": item.get("RestorePointType"),
                "created": self._parse_wmi_time(item.get("CreationTime")),
            })
        return points

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _parse_wmi_time(value: Any) -> str:
        """Best-effort parse of a WMI CreationTime into an ISO-ish string."""
        if not value:
            return ""
        s = str(value)
        # WMI datetime looks like 20240115093000.000000-000
        if len(s) >= 14 and s[:14].isdigit():
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}:{s[12:14]}"
        return s

    def _run_ps(self, script: str, timeout: int) -> str | None:
        """_run_ps."""
        try:
            proc = _proc.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                text=True, timeout=timeout, creationflags=_NO_WINDOW,
            )
            if proc.returncode == 0:
                return proc.stdout
            self.logger.debug("powershell rc=%s stderr=%s", proc.returncode, proc.stderr.strip())
            # Some failures still print a STATUS= line to stdout; return it.
            return proc.stdout or None
        except (_proc.ProcessCancelled, OSError, subprocess.SubprocessError) as exc:
            self.logger.debug("powershell invocation failed: %s", exc)
            return None
        """_run_ps."""
        """_run_ps."""
