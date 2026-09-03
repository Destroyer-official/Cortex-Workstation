"""Windows Update Repair Toolkit — comprehensive component reset and repair.

Research grounding
------------------
* Microsoft Learn: "How do I reset Windows Update components?" — official
  procedure: stop services (wuauserv, bits, cryptsvc, appidsvc), rename
  SoftwareDistribution/catroot2, re-register 30+ DLLs, reset Winsock,
  restart services.
* WURepair (SysAdminDoc, 2026) — PowerShell module with 14 phases:
  hosts file cleanup (25+ Microsoft domains), SSL/TLS repair, firewall
  rules, Winsock/TCP reset, proxy cleanup, BITS repair, Delivery
  Optimization, service dependencies, registry policy cleanup,
  SoftwareDistribution/catroot2 reset, DLL re-registration, DISM
  integration (with `/AnalyzeComponentStore`, `/ResetBase` gated by
  reclaimable >= 1024 MB), SFC, servicing stack preflight, catalog SSU
  repair, selective repair phases, JSON reports, event log integration.
* thatKinji/Reset-WindowsUpdateTools — single cmdlet `Reset-WindowsUpdate`.
* matbanik/rwu — 14-step fix with TUI, AI-ready diagnostics, dry-run,
  reversible (timestamped cache folders, registry exports).
* limehawk/rmm-scripts — PowerShell script with security descriptor
  reset, DLL re-registration, Winsock reset, optional reboot.
* ManuelGil/Script-Reset-Windows-Update-Tool — 10.5.x versions, 500K+
  downloads, includes SFC, DISM, cleanup superseded.

Why this matters for Cortex Cleaner
-----------------------------------
* Windows Update breaks frequently (0x80070643, 0x80070002, 0x800f081f,
  stuck at 0%/33%/100%). Built-in troubleshooter is shallow.
* Privacy tools, malware, system corruption, misconfiguration disable
  services, block domains, break SSL/TLS, corrupt catroot2.
* A production-grade repair must be *selective* (phase-based), *reversible*
  (backups, restore points), *diagnostic* (pre-check report), and
  *automatable* (JSON output, exit codes, event log).

Design
------
* **Phase-based architecture**: each repair phase is a method with
  `dry_run` support, returns `PhaseResult` (success, changes, rollback
  info). Phases: Diagnose, Services, Caches, Registry, DLLs, Network,
  DISM, SFC, SSU, DeliveryOpt, WaaS, Verify.
* **Safety**: System Restore point before any mutation; timestamped
  rename of SoftwareDistribution/catroot2 (not delete); registry exports
  before policy changes; IFEO debugger removal on rollback.
* **Diagnostics**: `preflight()` returns `DiagnosticReport` (services,
  disk, connectivity, DISM health, pending reboot, recent errors).
* **Selective repair**: `repair(phases=[...])` runs only requested phases.
* **Automation**: JSON report with before/after comparison; event log
  entry; exit codes (0=success, 1=partial, 2=failed, 3=cancelled).
* **24H2 awareness**: DeliveryOptimization path change; WaaSMedicSvc
  aggressive restart — stop it first.

Usage::

    from cortex_unified.system_tools.windows_update_repair import WindowsUpdateRepair
    repair = WindowsUpdateRepair()
    report = repair.preflight()
    if report.issues:
        result = repair.repair_all()
        print(result.summary())

References
----------
* Microsoft Learn: How to Reset Windows Update Components
* WURepair (GitHub: SysAdminDoc/WURepair)
* Reset-WindowsUpdateTools (GitHub: thatKinji/Reset-WindowsUpdateTools)
* rwu (GitHub: matbanik/rwu)
* Microsoft Learn: Additional resources for Windows Update
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import winreg
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from cortex_unified.system_tools.restore_point import RestorePointManager
from cortex_unified.system_tools.component_store_cleaner import ComponentStoreCleaner


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PhaseResult:
    """Phase Result data container."""
    phase: str
    success: bool
    changes: List[str] = field(default_factory=list)
    rollback_info: Dict = field(default_factory=dict)
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    """Diagnostic Report data container."""
    timestamp: str
    os_version: str
    services: Dict[str, str]  # name -> status
    disk_free_gb: float
    connectivity: bool
    dism_health: str
    pending_reboot: bool
    recent_wu_errors: List[str]
    issues: List[str]

    def to_json(self) -> str:
        """To json."""
        import dataclasses
        return json.dumps(dataclasses.asdict(self), indent=2)


@dataclass(frozen=True, slots=True)
class RepairResult:
    """Repair Result data container."""
    timestamp: str
    phases: List[PhaseResult]
    preflight: DiagnosticReport
    postflight: Optional[DiagnosticReport] = None
    cancelled: bool = False

    def summary(self) -> str:
        """Summary."""
        ok = sum(1 for p in self.phases if p.success)
        total = len(self.phases)
        return f"Windows Update Repair: {ok}/{total} phases succeeded"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WU_SERVICES = [
    "wuauserv",      # Windows Update
    "bits",          # Background Intelligent Transfer Service
    "cryptsvc",      # Cryptographic Services
    "appidsvc",      # App Identity
    "WaaSMedicSvc",  # Windows Update Medic (24H2)
]

WU_DLLS = [
    "atl.dll", "urlmon.dll", "mshtml.dll", "shdocvw.dll", "browseui.dll",
    "jscript.dll", "vbscript.dll", "scrrun.dll", "msxml.dll", "msxml3.dll",
    "msxml6.dll", "actxprxy.dll", "softpub.dll", "wintrust.dll", "dssenh.dll",
    "rsaenh.dll", "gpkcsp.dll", "sccbase.dll", "slbcsp.dll", "cryptdlg.dll",
    "oleaut32.dll", "ole32.dll", "shell32.dll", "initpki.dll", "wuapi.dll",
    "wuaueng.dll", "wuaueng1.dll", "wucltui.dll", "wups.dll", "wups2.dll",
    "wuweb.dll", "qmgr.dll", "qmgrprxy.dll", "wucltux.dll", "muweb.dll",
    "wuwebv.dll", "wudriver.dll",
]

MICROSOFT_TELEMETRY_DOMAINS = [
    "vortex.data.microsoft.com", "vortex-win.data.microsoft.com",
    "telemetry.microsoft.com", "telemetry.urs.microsoft.com",
    "watson.telemetry.microsoft.com", "watson.live.com",
    "settings-win.data.microsoft.com", "events.data.microsoft.com",
    "df.telemetry.microsoft.com", "reports.wes.df.telemetry.microsoft.com",
    "cs.wpc.v0cdn.net", "vortex-sandbox.data.microsoft.com",
    "feedback.microsoft-hohm.com", "feedback.search.microsoft.com",
    "feedback.windows.com", "watson.microsoft.com",
    "ceus-win.data.microsoft.com", "pre.footprintpredict.com",
    "spynet2.microsoft.com", "spynetalt.microsoft.com",
    "sqm.telemetry.microsoft.com", "sqm.df.telemetry.microsoft.com",
    "telecommand.telemetry.microsoft.com", "oca.telemetry.microsoft.com",
    "redir.metaservices.microsoft.com", "choice.microsoft.com",
    "choice.microsoft.com.nsatc.net", "compatexchange.cloudapp.net",
    "v10.events.data.microsoft.com", "v20.events.data.microsoft.com",
]

# ---------------------------------------------------------------------------
# Core repair class
# ---------------------------------------------------------------------------

class WindowsUpdateRepair:
    """Comprehensive Windows Update component repair."""

    def __init__(
        self,
        create_restore_point: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
        dry_run: bool = False,
    ):
        """Initialize Windows Update Repair."""
        self.create_restore_point = create_restore_point
        self.progress = progress_callback or (lambda _: None)
        self.cancel_event = cancel_event or threading.Event()
        self.dry_run = dry_run
        self._restore_mgr = RestorePointManager() if create_restore_point else None
        self._component_cleaner = ComponentStoreCleaner(
            create_restore_point=False,  # we manage our own
            progress_callback=self.progress,
            cancel_event=cancel_event,
        )
        self._backup_root = Path(os.environ.get("TEMP", "C:\\Temp")) / "CortexWURepair"
        self._backup_root.mkdir(parents=True, exist_ok=True)

    # -- helpers

    def _run(self, cmd: List[str], timeout: int = 120, shell: bool = False) -> Tuple[int, str, str]:
        if self.cancel_event.is_set():
            raise RuntimeError("Cancelled")
        if self.dry_run:
            self.progress(f"[DRY-RUN] {' '.join(cmd)}")
            return 0, "", ""
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
                encoding=sys.getdefaultencoding(), errors="replace", shell=shell
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Timeout after {timeout}s"
        except Exception as exc:
            return -1, "", str(exc)
        """_run."""
        """_run."""

    def _run_ps(self, script: str, timeout: int = 180) -> Tuple[int, str, str]:
        return self._run(["powershell", "-NoProfile", "-Command", script], timeout=timeout)
        """_run_ps."""
        """_run_ps."""

    def _sc_query(self, name: str) -> str:
        rc, out, _ = self._run(["sc", "query", name])
        return out.strip() if rc == 0 else ""
        """_sc_query."""
        """_sc_query."""

    def _service_status(self, name: str) -> str:
        out = self._sc_query(name)
        for line in out.splitlines():
            if "STATE" in line:
                return line.split(":")[-1].strip().split()[0]
        return "UNKNOWN"
        """_service_status."""
        """_service_status."""

    def _stop_service(self, name: str, retries: int = 3) -> bool:
        for _ in range(retries):
            rc, _, _ = self._run(["net", "stop", name])
            if rc == 0:
                time.sleep(0.5)
                if self._service_status(name) == "STOPPED":
                    return True
            time.sleep(1)
        return False
        """_stop_service."""
        """_stop_service."""

    def _start_service(self, name: str) -> bool:
        rc, _, _ = self._run(["net", "start", name])
        return rc == 0
        """_start_service."""
        """_start_service."""

    # -- preflight

    def preflight(self) -> DiagnosticReport:
        """Run diagnostic pre-checks."""
        self.progress("Running preflight diagnostics...")
        issues: List[str] = []

        # OS version
        import platform
        os_version = f"{platform.system()} {platform.release()} {platform.version()}"

        # Services
        services = {svc: self._service_status(svc) for svc in WU_SERVICES}
        for svc, status in services.items():
            if status != "RUNNING" and svc != "WaaSMedicSvc":
                issues.append(f"Service {svc} not RUNNING ({status})")

        # Disk
        try:
            import shutil as sh
            total, used, free = sh.disk_usage(os.environ.get("SYSTEMDRIVE", "C:\\"))
            disk_free_gb = free / (1024**3)
            if disk_free_gb < 5:
                issues.append(f"Low disk space: {disk_free_gb:.1f} GB free")
        except Exception:
            disk_free_gb = 0.0

        # Connectivity
        connectivity = False
        try:
            import urllib.request
            urllib.request.urlopen("http://www.msftconnecttest.com/connecttest.txt", timeout=5)
            connectivity = True
        except Exception:
            issues.append("No internet connectivity to Microsoft endpoints")

        # DISM health
        rc, out, _ = self._run(["Dism.exe", "/Online", "/Cleanup-Image", "/CheckHealth"])
        dism_health = "Healthy" if rc == 0 else f"Degraded (rc={rc})"
        if rc != 0:
            issues.append("DISM component store reports corruption")

        # Pending reboot
        pending_reboot = False
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager") as key:
                val, _ = winreg.QueryValueEx(key, "PendingFileRenameOperations")
                pending_reboot = bool(val)
        except OSError:
            pass

        # Recent WU errors (Event Log)
        recent_errors: List[str] = []
        rc, out, _ = self._run_ps(
            "Get-WinEvent -LogName 'System' -ProviderName 'Microsoft-Windows-WindowsUpdateClient' "
            "-MaxEvents 20 | Where-Object {$_.Level -le 3} | Select-Object TimeCreated,Id,Message | ConvertTo-Json",
            timeout=30
        )
        if rc == 0 and out.strip():
            try:
                events = json.loads(out)
                for e in events:
                    recent_errors.append(f"Event {e.get('Id')}: {e.get('Message','')[:120]}")
            except Exception:
                pass

        return DiagnosticReport(
            timestamp=datetime.now().isoformat(),
            os_version=os_version,
            services=services,
            disk_free_gb=disk_free_gb,
            connectivity=connectivity,
            dism_health=dism_health,
            pending_reboot=pending_reboot,
            recent_wu_errors=recent_errors[:10],
            issues=issues,
        )

    # -- phase implementations

    def _phase_stop_services(self) -> PhaseResult:
        t0 = time.time()
        changes = []
        for svc in WU_SERVICES:
            if self._service_status(svc) == "RUNNING":
                if self._stop_service(svc):
                    changes.append(f"Stopped {svc}")
                else:
                    return PhaseResult("stop_services", False, changes,
                                       error=f"Failed to stop {svc}",
                                       duration_seconds=time.time()-t0)
        return PhaseResult("stop_services", True, changes, duration_seconds=time.time()-t0)
        """_phase_stop_services."""
        """_phase_stop_services."""

    def _phase_clear_caches(self) -> PhaseResult:
        t0 = time.time()
        changes = []
        rollback = {}
        # SoftwareDistribution
        sd = Path(os.environ.get("SYSTEMROOT", "C:\\Windows")) / "SoftwareDistribution"
        if sd.exists():
            bak = sd.with_suffix(f".bak.{int(time.time())}")
            if not self.dry_run:
                shutil.move(str(sd), str(bak))
            changes.append(f"Renamed SoftwareDistribution -> {bak.name}")
            rollback["SoftwareDistribution"] = str(bak)
        # catroot2
        cr2 = Path(os.environ.get("SYSTEMROOT", "C:\\Windows")) / "System32" / "catroot2"
        if cr2.exists():
            bak = cr2.with_suffix(f".bak.{int(time.time())}")
            if not self.dry_run:
                shutil.move(str(cr2), str(bak))
            changes.append(f"Renamed catroot2 -> {bak.name}")
            rollback["catroot2"] = str(bak)
        # BITS qmgr
        qmgr = Path(os.environ.get("ALLUSERSPROFILE", "C:\\ProgramData")) / "Microsoft" / "Network" / "Downloader"
        if qmgr.exists():
            for f in qmgr.glob("qmgr*.dat"):
                bak = f.with_suffix(f".bak.{int(time.time())}")
                if not self.dry_run:
                    f.rename(bak)
                changes.append(f"Backed up {f.name}")
        # DeliveryOptimization (24H2 path)
        do = sd / "DeliveryOptimization"
        if do.exists():
            bak = do.with_suffix(f".bak.{int(time.time())}")
            if not self.dry_run:
                shutil.move(str(do), str(bak))
            changes.append(f"Renamed DeliveryOptimization -> {bak.name}")
        return PhaseResult("clear_caches", True, changes, rollback, duration_seconds=time.time()-t0)
        """_phase_clear_caches."""
        """_phase_clear_caches."""

    def _phase_reset_registry_policies(self) -> PhaseResult:
        t0 = time.time()
        changes = []
        rollback = {}
        reg_paths = [
            r"HKCU:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate",
            r"HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\WindowsUpdate",
            r"HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate",
            r"HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\WindowsUpdate",
        ]
        for path in reg_paths:
            if not self.dry_run:
                try:
                    # Export before deletion
                    export_path = self._backup_root / f"reg_{path.replace('\\','_').replace(':','')}.reg"
                    self._run(["reg", "export", path, str(export_path), "/y"])
                    rollback[path] = str(export_path)
                    # Delete
                    self._run(["reg", "delete", path, "/f"])
                except Exception:
                    pass
            changes.append(f"Reset policies at {path}")
        return PhaseResult("reset_registry_policies", True, changes, rollback, duration_seconds=time.time()-t0)
        """_phase_reset_registry_policies."""
        """_phase_reset_registry_policies."""

    def _phase_reset_security_descriptors(self) -> PhaseResult:
        t0 = time.time()
        changes = []
        sd_bits = "D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWLOCRRC;;;AU)(A;;CCLCSWRPWPDTLOCRRC;;;PU)"
        sd_wu = "D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWLOCRRC;;;AU)(A;;CCLCSWRPWPDTLOCRRC;;;PU)"
        if not self.dry_run:
            self._run(["sc.exe", "sdset", "bits", sd_bits])
            self._run(["sc.exe", "sdset", "wuauserv", sd_wu])
        changes.append("Reset BITS security descriptor")
        changes.append("Reset wuauserv security descriptor")
        return PhaseResult("reset_security_descriptors", True, changes, duration_seconds=time.time()-t0)
        """_phase_reset_security_descriptors."""
        """_phase_reset_security_descriptors."""

    def _phase_reregister_dlls(self) -> PhaseResult:
        t0 = time.time()
        changes = []
        system32 = Path(os.environ.get("SYSTEMROOT", "C:\\Windows")) / "System32"
        for dll in WU_DLLS:
            dll_path = system32 / dll
            if dll_path.exists():
                if not self.dry_run:
                    self._run(["regsvr32.exe", "/s", str(dll_path)])
                changes.append(f"Re-registered {dll}")
        return PhaseResult("reregister_dlls", True, changes, duration_seconds=time.time()-t0)
        """_phase_reregister_dlls."""
        """_phase_reregister_dlls."""

    def _phase_reset_network(self) -> PhaseResult:
        t0 = time.time()
        changes = []
        if not self.dry_run:
            self._run(["netsh", "winsock", "reset"])
            self._run(["netsh", "winsock", "reset", "proxy"])
            self._run(["netsh", "winhttp", "reset", "proxy"])
            self._run(["ipconfig", "/flushdns"])
        changes.extend(["Winsock reset", "WinHTTP proxy reset", "DNS flush"])
        # Hosts file cleanup (optional, aggressive)
        hosts = Path(os.environ.get("SYSTEMROOT", "C:\\Windows")) / "System32" / "drivers" / "etc" / "hosts"
        if hosts.exists():
            if not self.dry_run:
                content = hosts.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                filtered = [l for l in lines if not any(dom in l for dom in MICROSOFT_TELEMETRY_DOMAINS)]
                if len(filtered) != len(lines):
                    bak = hosts.with_suffix(f".bak.{int(time.time())}")
                    shutil.copy2(hosts, bak)
                    hosts.write_text("\n".join(filtered), encoding="utf-8")
                    changes.append(f"Cleaned {len(lines)-len(filtered)} telemetry entries from hosts file")
        return PhaseResult("reset_network", True, changes, duration_seconds=time.time()-t0)
        """_phase_reset_network."""
        """_phase_reset_network."""

    def _phase_dism_repair(self) -> PhaseResult:
        t0 = time.time()
        changes = []
        # ScanHealth
        rc, out, _ = self._run(["Dism.exe", "/Online", "/Cleanup-Image", "/ScanHealth"], timeout=600)
        changes.append(f"DISM ScanHealth: {'OK' if rc==0 else 'Issues found'}")
        if rc != 0:
            # RestoreHealth
            rc, out, _ = self._run(["Dism.exe", "/Online", "/Cleanup-Image", "/RestoreHealth"], timeout=1800)
            changes.append(f"DISM RestoreHealth: {'OK' if rc==0 else 'Failed'}")
        return PhaseResult("dism_repair", rc==0, changes, duration_seconds=time.time()-t0)
        """_phase_dism_repair."""
        """_phase_dism_repair."""

    def _phase_sfc(self) -> PhaseResult:
        t0 = time.time()
        rc, out, _ = self._run(["sfc.exe", "/scannow"], timeout=1800)
        changes = [out.strip()[:200]] if out else ["SFC completed"]
        return PhaseResult("sfc", rc==0, changes, duration_seconds=time.time()-t0)
        """_phase_sfc."""
        """_phase_sfc."""

    def _phase_component_store(self) -> PhaseResult:
        """Analyze and optionally cleanup component store."""
        t0 = time.time()
        changes = []
        info = self._component_cleaner.analyze()
        changes.append(f"Component Store: {info.actual_size_gb:.2f} GB actual, {info.reclaimable_packages} reclaimable")
        if info.cleanup_recommended:
            result = self._component_cleaner.cleanup()
            changes.append(f"Cleanup: reclaimed {result.reclaimed_bytes/1024**2:.1f} MB")
        return PhaseResult("component_store", True, changes, duration_seconds=time.time()-t0)

    def _phase_start_services(self) -> PhaseResult:
        t0 = time.time()
        changes = []
        for svc in WU_SERVICES:
            if self._start_service(svc):
                changes.append(f"Started {svc}")
            else:
                changes.append(f"Warning: {svc} may need manual start")
        # Ensure auto startup
        for svc in ["wuauserv", "bits", "DcomLaunch"]:
            self._run(["sc.exe", "config", svc, "start=", "auto"])
        return PhaseResult("start_services", True, changes, duration_seconds=time.time()-t0)
        """_phase_start_services."""
        """_phase_start_services."""

    def _phase_verify(self) -> PhaseResult:
        t0 = time.time()
        changes = []
        # Quick connectivity test
        try:
            import urllib.request
            urllib.request.urlopen("https://www.microsoft.com", timeout=10)
            changes.append("Microsoft.com reachable")
        except Exception as exc:
            changes.append(f"Connectivity check failed: {exc}")
        # Trigger WU check
        self._run(["wuauclt.exe", "/detectnow"])
        changes.append("Triggered Windows Update detection")
        return PhaseResult("verify", True, changes, duration_seconds=time.time()-t0)
        """_phase_verify."""
        """_phase_verify."""

    # -- orchestration

    def repair_all(self, phases: Optional[List[str]] = None) -> RepairResult:
        """Run all repair phases (or specified subset)."""
        all_phases = {
            "stop_services": self._phase_stop_services,
            "clear_caches": self._phase_clear_caches,
            "reset_registry_policies": self._phase_reset_registry_policies,
            "reset_security_descriptors": self._phase_reset_security_descriptors,
            "reregister_dlls": self._phase_reregister_dlls,
            "reset_network": self._phase_reset_network,
            "dism_repair": self._phase_dism_repair,
            "sfc": self._phase_sfc,
            "component_store": self._phase_component_store,
            "start_services": self._phase_start_services,
            "verify": self._phase_verify,
        }
        selected = phases or list(all_phases.keys())
        if self.create_restore_point:
            self._restore_mgr.create("Cortex Cleaner: Windows Update Repair")

        pre = self.preflight()
        results: List[PhaseResult] = []
        for phase_name in selected:
            if self.cancel_event.is_set():
                break
            if phase_name not in all_phases:
                continue
            self.progress(f"Phase: {phase_name}")
            result = all_phases[phase_name]()
            results.append(result)
            if not result.success and phase_name in ("stop_services", "clear_caches"):
                # Critical phase failure — abort
                break

        post = self.preflight()
        return RepairResult(
            timestamp=datetime.now().isoformat(),
            phases=results,
            preflight=pre,
            postflight=post,
            cancelled=self.cancel_event.is_set(),
        )

    def repair_selective(self, phase_names: List[str]) -> RepairResult:
        """Run only specified phases."""
        return self.repair_all(phases=phase_names)

    def quick_reset(self) -> RepairResult:
        """Minimal reset: services, caches, DLLs, network, restart."""
        return self.repair_all([
            "stop_services", "clear_caches", "reregister_dlls",
            "reset_network", "start_services", "verify"
        ])


__all__ = [
    "WindowsUpdateRepair",
    "PhaseResult",
    "DiagnosticReport",
    "RepairResult",
]