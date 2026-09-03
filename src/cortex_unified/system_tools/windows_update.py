"""Windows Update status - what's pending and when you last updated.

Two honest layers:

* Offline & instant - the dates of your last successful update *check* and
  *install*, read from the registry. This needs no network and tells you at a
  glance whether Windows has been keeping itself current.
* On demand & online - a search for pending updates via the official Windows
  Update COM API (``Microsoft.Update.Session``). This reaches Microsoft's update
  service (so it needs internet and can take a while), which the UI states
  plainly. Cortex only *reports* pending updates - installing them is left to
  Windows Update itself, which handles reboots and rollback safely.
"""

from __future__ import annotations

import json
import logging
import sys
import subprocess
from dataclasses import dataclass
from typing import Any

from cortex_unified.core import proc as _proc

_LOG = logging.getLogger("cortex.system_tools.windows_update")
_IS_WINDOWS = sys.platform == "win32"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

_RESULTS_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\Results"
_HISTORY_RESULT = {1: "In progress", 2: "Succeeded", 3: "Succeeded with errors",
                   4: "Failed", 5: "Aborted"}


@dataclass(slots=True)
class PendingUpdate:
    """Pending Update data container."""
    title: str
    kb: str = ""
    severity: str = ""
    size_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {"title": self.title, "kb": self.kb, "severity": self.severity,
                "size_bytes": self.size_bytes}


class WindowsUpdate:
    """Read Windows Update state (read-only)."""

    @staticmethod
    def is_supported() -> bool:
        """Is supported."""
        return _IS_WINDOWS

    # -- offline: last activity from registry -------------------------------

    def last_activity(self) -> dict[str, str]:
        """Last activity."""
        if not _IS_WINDOWS:
            return {"last_check": "", "last_install": ""}
        return {
            "last_check": self._read_result_time("Detect"),
            "last_install": self._read_result_time("Install"),
        }

    @staticmethod
    def _read_result_time(sub: str) -> str:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _RESULTS_KEY + "\\" + sub) as key:
                val, _ = winreg.QueryValueEx(key, "LastSuccessTime")
                return str(val)
        except FileNotFoundError:
            return ""
        except Exception as exc:  # noqa: BLE001
            _LOG.debug("read WU %s time failed: %s", sub, exc)
            return ""
        """_read_result_time."""
        """_read_result_time."""

    # -- online: pending updates via COM ------------------------------------

    def check_pending(self) -> list[PendingUpdate]:
        """Check pending."""
        if not _IS_WINDOWS:
            return []
        script = (
            "$s=(New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher();"
            "$r=$s.Search(\"IsInstalled=0 and Type='Software' and IsHidden=0\");"
            "$r.Updates | ForEach-Object { [pscustomobject]@{ Title=$_.Title;"
            " KB=($_.KBArticleIDs -join ','); Severity=$_.MsrcSeverity;"
            " Size=$_.MaxDownloadSize } } | ConvertTo-Json -Compress"
        )
        return self._parse_pending(self._run(script, timeout=180))

    @staticmethod
    def _parse_pending(out: str | None) -> list[PendingUpdate]:
        if not out:
            return []
        try:
            data = json.loads(out)
        except (ValueError, TypeError):
            return []
        if isinstance(data, dict):
            data = [data]

        def _int(v):
            try:
                return int(v) if v is not None else 0
            except (ValueError, TypeError):
                return 0
            """_int."""
            """_int."""

        updates = []
        for u in data:
            if not isinstance(u, dict):
                continue
            title = str(u.get("Title") or "").strip()
            if not title:
                continue
            updates.append(PendingUpdate(
                title=title,
                kb=("KB" + str(u.get("KB")) if u.get("KB") else ""),
                severity=str(u.get("Severity") or ""),
                size_bytes=_int(u.get("Size")),
            ))
        return updates
        """_parse_pending."""
        """_parse_pending."""

    # -- history via COM ----------------------------------------------------

    def recent_history(self, limit: int = 15) -> list[dict[str, Any]]:
        """Recent history."""
        if not _IS_WINDOWS:
            return []
        script = (
            "$s=New-Object -ComObject Microsoft.Update.Session;"
            "$sr=$s.CreateUpdateSearcher();"
            "$c=$sr.GetTotalHistoryCount();"
            f"if($c -gt 0){{ $sr.QueryHistory(0,[Math]::Min($c,{limit})) | ForEach-Object {{"
            " [pscustomobject]@{ Title=$_.Title; Date=$_.Date.ToString('s');"
            " Result=$_.ResultCode } }} | ConvertTo-Json -Compress }}"
        )
        return self._parse_history(self._run(script, timeout=60))

    @staticmethod
    def _parse_history(out: str | None) -> list[dict[str, Any]]:
        if not out:
            return []
        try:
            data = json.loads(out)
        except (ValueError, TypeError):
            return []
        if isinstance(data, dict):
            data = [data]
        rows = []
        for h in data:
            if not isinstance(h, dict):
                continue
            title = str(h.get("Title") or "").strip()
            if not title:
                continue
            try:
                rc = int(h.get("Result"))
            except (ValueError, TypeError):
                rc = 0
            rows.append({
                "title": title,
                "date": str(h.get("Date") or "").replace("T", " "),
                "result": _HISTORY_RESULT.get(rc, "Unknown"),
                "succeeded": rc == 2,
            })
        return rows
        """_parse_history."""
        """_parse_history."""

    def _run(self, script: str, timeout: int) -> str | None:
        try:
            proc = _proc.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                text=True, timeout=timeout, creationflags=_NO_WINDOW,
            )
            return proc.stdout if proc.returncode == 0 else None
        except (_proc.ProcessCancelled, OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("windows update query failed: %s", exc)
            return None
        """_run."""
        """_run."""
