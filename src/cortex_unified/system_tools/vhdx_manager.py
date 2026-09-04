"""Virtual disk (VHDX) reclaim for WSL2, Docker Desktop and Hyper-V.

Dynamically expanding ``.vhdx`` files grow on demand and never shrink on their
own, so data deleted inside a guest does not return space to the host until the
disk is compacted - and compacting an attached disk can corrupt it. This module
finds the disks that matter (WSL distributions from the registry, Docker Desktop
data disks, Hyper-V VM disks), measures host size sparse-aware, refuses to
compact while the owning runtime is running (naming which processes to close),
and compacts via a diskpart attach-read-only/compact/detach sequence, reporting
the measured before/after delta rather than an estimate. Windows-only and
read-only until explicitly asked to act; every subprocess call is time-boxed
with a hidden window.
"""

from __future__ import annotations

import enum
import logging
import sys
import os
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cortex_unified.core import proc as _proc

_LOG = logging.getLogger("cortex.system_tools.vhdx")
_IS_WINDOWS = sys.platform == "win32"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

#: Processes that hold a virtual disk open. Compaction cannot work while these
#: run, so we name them instead of letting diskpart fail cryptically.
_BLOCKERS = {
    "wsl": ("wslservice.exe", "wslhost.exe", "vmwp.exe"),
    "docker": ("com.docker.backend.exe", "Docker Desktop.exe", "dockerd.exe",
               "com.docker.service", "vmmem", "vmmemWSL"),
    "hyperv": ("vmwp.exe", "vmms.exe"),
}


class DiskKind(str, enum.Enum):
    """Diskkind.

    Manages DiskKind operations and coordinates related state changes for the component.
    """

    WSL = "wsl"
    DOCKER = "docker"
    HYPERV = "hyperv"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class VirtualDisk:
    """Virtualdisk.

    Manages VirtualDisk operations and coordinates related state changes for the component.
    """

    path: Path
    kind: DiskKind
    label: str                      # distro / VM / component name
    size_bytes: int = 0             # logical file size on the host
    on_disk_bytes: int = 0          # allocated bytes (sparse-aware)
    #: Bytes used *inside* the guest filesystem, when it could be measured
    #: without starting anything. ``None`` means unknown - we then refuse to
    #: guess a reclaim figure rather than invent one.
    used_inside_bytes: int | None = None
    running: bool = False           # owning runtime currently holds it open
    blockers: tuple[str, ...] = ()  # process names to close first

    @property
    def potential_saving_bytes(self) -> int | None:
        """Best-case reclaim, or ``None`` when it cannot be known yet.

        Compaction can only release space the guest is no longer using, so the
        honest upper bound is ``host size - bytes used inside``. Without a guest
        measurement there is no defensible number, and the UI says "unknown"
        instead of showing a fabricated one.
        """
        if self.used_inside_bytes is None:
            return None
        return max(0, self.on_disk_bytes - self.used_inside_bytes)

    @property
    def can_compact(self) -> bool:
        """True when compaction can be attempted right now.

        Manages can compact operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return not self.running and self.path.exists()

    @property
    def status_note(self) -> str:
        """Plain explanation of the current state, always safe to display.

        Manages status note operations and coordinates related state changes for the component.

        Returns:
            str: Formatted string or path.
        """
        if not self.path.exists():
            return "file no longer exists"
        if self.running:
            names = ", ".join(self.blockers) or "its runtime"
            return f"in use - close {names} first"
        saving = self.potential_saving_bytes
        if saving is None:
            return "ready to compact (reclaim unknown until compaction runs)"
        return "ready to compact"

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "path": str(self.path),
            "kind": self.kind.value,
            "label": self.label,
            "size_bytes": self.size_bytes,
            "on_disk_bytes": self.on_disk_bytes,
            "used_inside_bytes": self.used_inside_bytes,
            "potential_saving_bytes": self.potential_saving_bytes,
            "running": self.running,
            "blockers": list(self.blockers),
            "can_compact": self.can_compact,
            "note": self.status_note,
        }


@dataclass(slots=True)
class CompactResult:
    """Compactresult.

    Manages CompactResult operations and coordinates related state changes for the component.
    """

    path: Path
    label: str
    success: bool
    before_bytes: int = 0
    after_bytes: int = 0
    message: str = ""
    detail: str = ""                # raw tool tail, for the "show details" view

    @property
    def freed_bytes(self) -> int:
        """Actual bytes returned to the host (never negative).

        Manages freed bytes operations and coordinates related state changes for the component.

        Returns:
            int: Result of the operation.
        """
        return max(0, self.before_bytes - self.after_bytes)

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "path": str(self.path),
            "label": self.label,
            "success": self.success,
            "before_bytes": self.before_bytes,
            "after_bytes": self.after_bytes,
            "freed_bytes": self.freed_bytes,
            "message": self.message,
        }


class VhdxManager:
    """Vhdxmanager.

    Manages VhdxManager operations and coordinates related state changes for the component.
    """

    def __init__(self) -> None:
        """Initialize Vhdx Manager.

        Initializes the instance and configures internal state.
        """
        self.logger = _LOG

    @staticmethod
    def is_supported() -> bool:
        """Virtual-disk compaction is a Windows-only concern.

        Manages is supported operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return _IS_WINDOWS

    # -- discovery ----------------------------------------------------------

    def list_disks(self) -> list[VirtualDisk]:
        """Return every virtual disk we can account for, largest first.

        Manages list disks operations and coordinates related state changes for the component.

        Returns:
            list[VirtualDisk]: List of processed items or identifiers.
        """
        if not _IS_WINDOWS:
            return []
        running = self._running_processes()
        disks: list[VirtualDisk] = []
        seen: set[str] = set()

        for disk in (*self._wsl_disks(), *self._docker_disks(), *self._hyperv_disks()):
            key = str(disk.path).lower()
            if key in seen:
                continue
            seen.add(key)
            self._measure(disk)
            blockers = tuple(n for n in _BLOCKERS.get(disk.kind.value, ())
                             if n.lower() in running)
            disk.blockers = blockers
            disk.running = bool(blockers)
            disks.append(disk)

        disks.sort(key=lambda d: d.on_disk_bytes, reverse=True)
        return disks

    def _wsl_disks(self) -> list[VirtualDisk]:
        """Read WSL distributions straight from the registry (no wsl.exe start).

        Shelling out to ``wsl --list`` can spin up the WSL service, which then
        holds the very file we want to compact. The registry has everything we
        need and touching it starts nothing.
        """
        out: list[VirtualDisk] = []
        try:
            import winreg
        except ImportError:  # pragma: no cover - non-Windows
            return out

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Lxss"
        try:
            root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path)
        except OSError:
            return out   # WSL never installed

        with root:
            index = 0
            while True:
                try:
                    guid = winreg.EnumKey(root, index)
                except OSError:
                    break
                index += 1
                try:
                    with winreg.OpenKey(root, guid) as sub:
                        base = self._reg_str(sub, "BasePath")
                        name = self._reg_str(sub, "DistributionName") or guid
                        version = self._reg_int(sub, "Version")
                except OSError:
                    continue
                if not base:
                    continue
                # WSL1 distributions are plain directories - nothing to compact.
                if version == 1:
                    continue
                base_path = Path(base.replace("\\\\?\\", ""))
                for candidate in ("ext4.vhdx", "system.vhd"):
                    vhd = base_path / candidate
                    if vhd.exists():
                        kind = (DiskKind.DOCKER if "docker" in name.lower()
                                else DiskKind.WSL)
                        out.append(VirtualDisk(vhd, kind, name))
                        break
        return out

    def _docker_disks(self) -> list[VirtualDisk]:
        """Find Docker Desktop data disks outside the WSL registry entries.

        Manages docker disks operations and coordinates related state changes for the component.

        Returns:
            list[VirtualDisk]: List of processed items or identifiers.
        """
        out: list[VirtualDisk] = []
        local = os.environ.get("LOCALAPPDATA")
        if not local:
            return out
        roots = [
            Path(local) / "Docker" / "wsl",           # WSL2 backend
            Path(local) / "Docker" / "vms",           # Hyper-V backend
            Path(local) / "DockerDesktop" / "vm-data",
        ]
        for root in roots:
            if not root.is_dir():
                continue
            try:
                for vhd in root.rglob("*.vhdx"):
                    out.append(VirtualDisk(vhd, DiskKind.DOCKER,
                                           f"Docker Desktop ({vhd.stem})"))
            except OSError as exc:
                self.logger.debug("docker disk scan failed under %s: %s", root, exc)
        return out

    def _hyperv_disks(self) -> list[VirtualDisk]:
        """List Hyper-V VM disks, but only when the role is actually installed.

        Manages hyperv disks operations and coordinates related state changes for the component.

        Returns:
            list[VirtualDisk]: List of processed items or identifiers.
        """
        script = (
            "$ErrorActionPreference='SilentlyContinue';"
            "if (Get-Command Get-VM -ErrorAction SilentlyContinue) {"
            "  foreach ($vm in Get-VM) {"
            "    foreach ($hd in ($vm | Get-VMHardDiskDrive)) {"
            "      Write-Output ($vm.Name + '|' + $hd.Path) } } }"
        )
        out: list[VirtualDisk] = []
        text = self._run_ps(script, timeout=45)
        if not text:
            return out
        for line in text.splitlines():
            if "|" not in line:
                continue
            name, _, path = line.partition("|")
            p = Path(path.strip())
            if p.suffix.lower() in (".vhdx", ".vhd") and p.exists():
                out.append(VirtualDisk(p, DiskKind.HYPERV, f"Hyper-V: {name.strip()}"))
        return out

    def _measure(self, disk: VirtualDisk) -> None:
        """Measure.

        Manages measure operations and coordinates related state changes for the component.

        Args:
            disk (VirtualDisk): The disk parameter.
        """
        try:
            disk.size_bytes = disk.path.stat().st_size
        except OSError:
            disk.size_bytes = 0
        disk.on_disk_bytes = disk.size_bytes
        try:
            from cortex_unified.engine import winattrs
            measured = winattrs.on_disk_size(disk.path, disk.size_bytes)
            if measured is not None and measured > 0:
                disk.on_disk_bytes = measured
        except Exception as exc:  # noqa: BLE001 - measurement is best-effort
            self.logger.debug("on-disk measure failed for %s: %s", disk.path, exc)

    # -- guest usage (opt-in, because it starts the distribution) ------------

    def measure_guest_usage(self, disk: VirtualDisk, timeout: int = 60) -> int | None:
        """Return bytes used inside a WSL distribution, or ``None``.

        This **starts the distribution** to run ``df``, which is why it is a
        separate, explicit call rather than part of discovery: the caller has to
        opt in, and must shut WSL down again before compacting.
        """
        if not _IS_WINDOWS or disk.kind is not DiskKind.WSL:
            return None
        try:
            proc = _proc.run(
                ["wsl", "-d", disk.label, "--", "df", "-B1", "--output=used", "/"],
                timeout=timeout, creationflags=_NO_WINDOW,
            )
        except (_proc.ProcessCancelled, OSError, subprocess.SubprocessError) as exc:
            self.logger.debug("guest df failed for %s: %s", disk.label, exc)
            return None
        text = self._decode(proc.stdout)
        for line in reversed(text.splitlines()):
            token = line.strip()
            if token.isdigit():
                used = int(token)
                disk.used_inside_bytes = used
                return used
        return None

    # -- actions ------------------------------------------------------------

    def shutdown_wsl(self, timeout: int = 120) -> tuple[bool, str]:
        """Run ``wsl --shutdown`` so the virtual disks can be detached.

        This stops every WSL distribution *and* Docker Desktop's WSL backend, so
        callers must confirm with the user first - unsaved work inside a distro
        is lost exactly as it would be with a hard stop.
        """
        if not _IS_WINDOWS:
            return False, "Windows-only feature."
        try:
            proc = _proc.run(["wsl", "--shutdown"], timeout=timeout, creationflags=_NO_WINDOW)
        except FileNotFoundError:
            return False, "WSL is not installed on this PC."
        except _proc.ProcessCancelled:
            return False, "Cancelled."
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"Could not shut WSL down: {exc}"
        if proc.returncode != 0:
            return False, self._decode(proc.stderr).strip() or "wsl --shutdown failed."
        return True, "All WSL distributions stopped."

    def compact(self, disk: VirtualDisk, timeout: int = 3600,
               cancel_event: "threading.Event | None" = None) -> CompactResult:
        """Compact one virtual disk and report the measured space returned.

        Uses ``diskpart``: select the vdisk, attach it **read-only** (so the
        guest filesystem cannot be modified), compact, then detach. Refuses when
        the owning runtime still holds the file, because a partial compaction of
        an attached disk is how these files get corrupted.
        """
        before = 0
        try:
            before = disk.path.stat().st_size
        except OSError:
            return CompactResult(disk.path, disk.label, False,
                                 message="The virtual disk file no longer exists.")

        if not _IS_WINDOWS:
            return CompactResult(disk.path, disk.label, False, before, before,
                                 "Windows-only feature.")

        running = self._running_processes()
        blockers = [n for n in _BLOCKERS.get(disk.kind.value, ())
                    if n.lower() in running]
        if blockers:
            return CompactResult(
                disk.path, disk.label, False, before, before,
                message=("Still in use by " + ", ".join(blockers) +
                         ". Stop it first, then compact - compacting an attached "
                         "disk risks corrupting it."),
            )

        script = (
            f'select vdisk file="{disk.path}"\n'
            "attach vdisk readonly\n"
            "compact vdisk\n"
            "detach vdisk\n"
            "exit\n"
        )
        ok, out = self._run_diskpart(script, timeout=timeout, cancel_event=cancel_event)

        after = before
        try:
            after = disk.path.stat().st_size
        except OSError:
            pass
        disk.size_bytes = after
        self._measure(disk)

        tail = "\n".join(line for line in out.splitlines() if line.strip())[-800:] if out else ""

        if not ok:
            cancelled = cancel_event is not None and cancel_event.is_set()
            msg = (
                "Cancelled. The disk was attached read-only during compaction, so no "
                "data can have been corrupted, but it may still be attached - if this "
                "disk fails to mount afterwards, restart Windows to clear it."
                if cancelled else self._explain_failure(out)
            )
            return CompactResult(
                disk.path, disk.label, False, before, after,
                message=msg, detail=tail,
            )

        freed = max(0, before - after)
        if freed == 0:
            # Honest: the operation succeeded but there was nothing to give back.
            return CompactResult(
                disk.path, disk.label, True, before, after,
                message=("Compaction completed, but no space was returned - this "
                         "disk was already as small as its contents allow."),
                detail=tail,
            )
        return CompactResult(disk.path, disk.label, True, before, after,
                             message="Compaction completed.", detail=tail)

    def set_sparse(self, disk: VirtualDisk, enabled: bool = True,
                   timeout: int = 300) -> tuple[bool, str]:
        """Ask WSL to keep a distribution's disk sparse (WSL 2.3+ only).

        A sparse VHDX returns free blocks to the host automatically, which
        prevents the bloat from coming back. Older WSL builds don't support the
        flag; that is reported plainly rather than treated as an error.
        """
        if not _IS_WINDOWS or disk.kind is not DiskKind.WSL:
            return False, "Only WSL distributions support sparse mode."
        flag = "true" if enabled else "false"
        try:
            proc = _proc.run(
                ["wsl", "--manage", disk.label, "--set-sparse", flag],
                timeout=timeout, creationflags=_NO_WINDOW,
            )
        except FileNotFoundError:
            return False, "WSL is not installed on this PC."
        except _proc.ProcessCancelled:
            return False, "Cancelled."
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"Could not change sparse mode: {exc}"
        text = (self._decode(proc.stdout) + self._decode(proc.stderr)).strip()
        if proc.returncode == 0:
            return True, f"Sparse mode {'enabled' if enabled else 'disabled'} for {disk.label}."
        if "invalid" in text.lower() or "unknown" in text.lower():
            return False, ("This version of WSL doesn't support sparse disks. "
                           "Update WSL (wsl --update) to use it.")
        return False, text or "Could not change sparse mode."

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _explain_failure(out: str | None) -> str:
        """Translate diskpart's output into something actionable.

        Manages explain failure operations and coordinates related state changes for the component.

        Args:
            out (str | None): The out parameter.

        Returns:
            str: Formatted string or path.
        """
        low = (out or "").lower()
        if "access is denied" in low or "administrator" in low:
            return ("Administrator rights are required to compact a virtual disk. "
                    "Restart Cortex as Administrator and try again.")
        if "in use" in low or "being used" in low:
            return ("The virtual disk is still attached. Stop WSL / Docker "
                    "Desktop and try again.")
        if "not have write permission" in low or "read-only" in low:
            return ("The disk could not be attached read-only for compaction; "
                    "check that no backup or antivirus tool is holding it.")
        if "could not find" in low or "not found" in low:
            return "diskpart could not open the virtual disk file."
        return "Compaction failed. See the details for diskpart's own output."

    def _run_diskpart(self, script: str, timeout: int,
                      cancel_event: "threading.Event | None" = None) -> tuple[bool, str]:
        """Run a diskpart script from a temp file; return (looks_ok, output).

        Compaction can run for many minutes, so this polls ``timeout`` and
        ``cancel_event`` instead of blocking uninterruptibly (see
        ``core/proc.py``). A kill always lands on the ``diskpart`` process tree,
        never on the calling thread, so it is always safe even if the caller is
        abandoned mid-operation during app shutdown.
        """
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(suffix=".dp.txt", text=True)
            with os.fdopen(fd, "w", encoding="ascii", errors="ignore") as fh:
                fh.write(script)
            proc = _proc.run(
                ["diskpart", "/s", tmp], timeout=timeout,
                cancel_event=cancel_event, creationflags=_NO_WINDOW,
            )
            out = self._decode(proc.stdout) + self._decode(proc.stderr)
            low = out.lower()
            # diskpart exits 0 even for some failures, so check the text too.
            ok = (proc.returncode == 0
                  and "successfully compacted" in low
                  and "access is denied" not in low)
            return ok, out
        except FileNotFoundError:
            return False, "diskpart is not available on this system."
        except _proc.ProcessCancelled:
            return False, ""  # honest cancellation message is built by the caller
        except subprocess.TimeoutExpired:
            return False, ("Compaction timed out. Very large disks can take a "
                           "long time; try again when the PC is otherwise idle.")
        except (OSError, subprocess.SubprocessError) as exc:
            return False, str(exc)
        finally:
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    def _run_ps(self, script: str, timeout: int) -> str | None:
        """Run a PowerShell snippet with a hidden window; None on any failure.

        Manages run ps operations and coordinates related state changes for the component.

        Args:
            script (str): The script parameter.
            timeout (int): The timeout parameter.

        Returns:
            str | None: Formatted string or path.
        """
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, timeout=timeout, creationflags=_NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self.logger.debug("powershell failed: %s", exc)
            return None
        out = self._decode(proc.stdout)
        return out or None

    @staticmethod
    def _running_processes() -> set[str]:
        """Lower-cased names of running processes (empty set if unavailable).

        Manages running processes operations and coordinates related state changes for the component.

        Returns:
            set[str]: Formatted string or path.
        """
        try:
            import psutil
        except ImportError:  # pragma: no cover - psutil is a hard dep in practice
            return set()
        names: set[str] = set()
        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info.get("name")
                if name:
                    names.add(name.lower())
            except Exception:  # noqa: BLE001 - races are expected here
                continue
        return names

    @staticmethod
    def _decode(raw: bytes | str | None) -> str:
        """Decode.

        Manages decode operations and coordinates related state changes for the component.

        Args:
            raw (bytes | str | None): The raw parameter.

        Returns:
            str: Formatted string or path.
        """
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw
        for enc in ("utf-8", "utf-16-le", "cp1252"):
            try:
                return raw.decode(enc).replace("\x00", "")
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")

    @staticmethod
    def _reg_str(key, name: str) -> str:
        """_reg_str.

        Manages reg str operations and coordinates related state changes for the component.

        Args:
            key: The key parameter.
            name (str): The name parameter.

        Returns:
            str: Formatted string or path.
        """
        try:
            import winreg
            value, _ = winreg.QueryValueEx(key, name)
            return str(value)
        except (OSError, ImportError, ValueError):
            return ""

    @staticmethod
    def _reg_int(key, name: str) -> int:
        """_reg_int.

        Manages reg int operations and coordinates related state changes for the component.

        Args:
            key: The key parameter.
            name (str): The name parameter.

        Returns:
            int: Result of the operation.
        """
        try:
            import winreg
            value, _ = winreg.QueryValueEx(key, name)
            return int(value)
        except (OSError, ImportError, ValueError, TypeError):
            return 0
