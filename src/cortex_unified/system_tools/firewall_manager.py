"""Windows Firewall control - block/allow programs and remote addresses.

This drives Windows Defender Firewall via the ``NetSecurity`` PowerShell module
(``New-NetFirewallRule`` etc.), which is the supported, fully-reversible way to
add rules without a kernel driver. Real per-packet filtering (like simplewall or
GlassWire) needs a signed WFP driver, which is out of scope for a lightweight
app; firewall rules achieve the user-facing goal - stop or allow a program's
traffic - safely and undoably.

Safety design:
* Every rule we create is prefixed ``Cortex Cleaner:`` so we can list and manage
  *only our own* rules and never touch built-in Windows or third-party rules.
* Creating/removing rules needs Administrator; we surface that honestly.
* Listing existing rules is read-only.
"""

from __future__ import annotations

import logging
import sys
import subprocess
from dataclasses import dataclass
from typing import Any

from cortex_unified.core import proc as _proc

_LOG = logging.getLogger("cortex.system_tools.firewall_manager")
_IS_WINDOWS = sys.platform == "win32"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

_PREFIX = "Cortex Cleaner:"


@dataclass(slots=True)
class FirewallRule:
    """Firewall Rule data container."""
    name: str
    display_name: str
    direction: str        # Inbound / Outbound
    action: str           # Allow / Block
    enabled: bool
    program: str = ""
    remote_address: str = ""
    protocol: str = ""
    managed_by_cortex: bool = False

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "direction": self.direction,
            "action": self.action,
            "enabled": self.enabled,
            "program": self.program,
            "remote_address": self.remote_address,
            "protocol": self.protocol,
            "managed_by_cortex": self.managed_by_cortex,
        }


class FirewallManager:
    """Create, list, toggle and remove Windows Firewall rules (Cortex-scoped)."""

    @staticmethod
    def is_supported() -> bool:
        """Is supported."""
        return _IS_WINDOWS

    # -- creation -----------------------------------------------------------

    def block_program(self, program_path: str, direction: str = "Outbound",
                      label: str = "") -> tuple[bool, str]:
        """Block a program's traffic. Reversible via remove_rule/toggle."""
        return self._new_rule(action="Block", program=program_path,
                              direction=direction, label=label or program_path)

    def allow_program(self, program_path: str, direction: str = "Outbound",
                      label: str = "") -> tuple[bool, str]:
        """Allow program."""
        return self._new_rule(action="Allow", program=program_path,
                              direction=direction, label=label or program_path)

    def block_remote_address(self, address: str, direction: str = "Outbound",
                            label: str = "") -> tuple[bool, str]:
        """Block traffic to/from a remote IP or range."""
        if not self._valid_address(address):
            return False, "Invalid IP address or range."
        return self._new_rule(action="Block", remote_address=address,
                              direction=direction, label=label or address)

    def _new_rule(self, action: str, direction: str, label: str,
                  program: str = "", remote_address: str = "") -> tuple[bool, str]:
        """_new_rule."""
        if not _IS_WINDOWS:
            return False, "Firewall control is only available on Windows."
        if direction not in ("Inbound", "Outbound"):
            return False, "Direction must be Inbound or Outbound."
        display = f"{_PREFIX} {action} {label}"
        args = [
            "New-NetFirewallRule",
            "-DisplayName", self._ps_quote(display),
            "-Direction", self._ps_quote(direction),
            "-Action", self._ps_quote(action),
            "-Profile", "Any",
        ]
        if program:
            args += ["-Program", self._ps_quote(program)]
        if remote_address:
            args += ["-RemoteAddress", self._ps_quote(remote_address)]
        ok = self._run(" ".join(args))
        if ok:
            return True, f"{action} rule created for {label}."
        return False, "Could not create the rule (Administrator is required)."
        """_new_rule."""
        """_new_rule."""

    # -- listing / management ----------------------------------------------

    def list_rules(self, cortex_only: bool = True) -> list[FirewallRule]:
        """List rules."""
        if not _IS_WINDOWS:
            return []
        # Pull rules plus their program/address filters in one JSON blob.
        script = (
            "$rs = Get-NetFirewallRule" + (f" -DisplayName '{_PREFIX}*'" if cortex_only else "") + ";"
            "$out=@();"
            "foreach($r in $rs){"
            "  $app=($r | Get-NetFirewallApplicationFilter -ErrorAction SilentlyContinue).Program;"
            "  $addr=($r | Get-NetFirewallAddressFilter -ErrorAction SilentlyContinue).RemoteAddress;"
            "  $port=($r | Get-NetFirewallPortFilter -ErrorAction SilentlyContinue).Protocol;"
            "  $out += [pscustomobject]@{"
            "    Name=$r.Name; Disp=$r.DisplayName; Dir=$r.Direction.ToString();"
            "    Act=$r.Action.ToString(); En=[bool]$r.Enabled; "
            "    App=$app; Addr=($addr -join ','); Proto=$port"
            "  }"
            "}"
            "$out | ConvertTo-Json -Compress"
        )
        return self._parse_rules(self._run(script, want_output=True))

    def set_enabled(self, name: str, enabled: bool) -> tuple[bool, str]:
        """Set enabled."""
        if not _IS_WINDOWS:
            return False, "Firewall control is only available on Windows."
        state = "True" if enabled else "False"
        ok = self._run(f"Set-NetFirewallRule -Name {self._ps_quote(name)} -Enabled {state}")
        return (ok, "Rule updated." if ok else "Could not update rule (Administrator required).")

    def remove_rule(self, name: str) -> tuple[bool, str]:
        """Remove rule."""
        if not _IS_WINDOWS:
            return False, "Firewall control is only available on Windows."
        ok = self._run(f"Remove-NetFirewallRule -Name {self._ps_quote(name)}")
        return (ok, "Rule removed." if ok else "Could not remove rule (Administrator required).")

    # -- parsing / helpers --------------------------------------------------

    @staticmethod
    def _parse_rules(out: str | None) -> list[FirewallRule]:
        """_parse_rules."""
        if not out:
            return []
        import json
        try:
            data = json.loads(out)
        except (ValueError, TypeError):
            return []
        if isinstance(data, dict):
            data = [data]
        rules: list[FirewallRule] = []
        for d in data:
            if not isinstance(d, dict):
                continue
            disp = str(d.get("Disp") or "")
            rules.append(FirewallRule(
                name=str(d.get("Name") or ""),
                display_name=disp,
                direction=str(d.get("Dir") or ""),
                action=str(d.get("Act") or ""),
                enabled=bool(d.get("En")),
                program=str(d.get("App") or "") if d.get("App") not in (None, "Any") else "",
                remote_address=str(d.get("Addr") or "") if d.get("Addr") not in (None, "Any") else "",
                protocol=str(d.get("Proto") or "") if d.get("Proto") else "",
                managed_by_cortex=disp.startswith(_PREFIX),
            ))
        return rules
        """_parse_rules."""
        """_parse_rules."""

    @staticmethod
    def _valid_address(addr: str) -> bool:
        """_valid_address."""
        import ipaddress
        addr = (addr or "").strip()
        if not addr:
            return False
        try:
            if "/" in addr:
                ipaddress.ip_network(addr, strict=False)
            elif "-" in addr:
                lo, hi = addr.split("-", 1)
                ipaddress.ip_address(lo.strip())
                ipaddress.ip_address(hi.strip())
            else:
                ipaddress.ip_address(addr)
            return True
        except ValueError:
            return False
        """_valid_address."""
        """_valid_address."""

    @staticmethod
    def _ps_quote(value: str) -> str:
        """Single-quote a value for PowerShell, escaping embedded quotes."""
        return "'" + str(value).replace("'", "''") + "'"

    def _run(self, script: str, want_output: bool = False):
        """_run."""
        try:
            proc = _proc.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                text=True, timeout=30, creationflags=_NO_WINDOW,
            )
            if want_output:
                return proc.stdout if proc.returncode == 0 else None
            return proc.returncode == 0
        except (_proc.ProcessCancelled, OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("firewall command failed: %s", exc)
            return None if want_output else False
        """_run."""
        """_run."""
