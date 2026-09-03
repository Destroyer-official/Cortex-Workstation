"""WSL distro cleanup: size reporting, shutdown + vhdx compaction.

The 1.37GB AppData\\Local\\wsl hit from manual cleaning was a WSL2
ext4.vhdx that never shrinks on its own. This module offers:

* list_distros() - parse ``wsl --list --verbose`` + registry fallback
* get_sizes() - ext4.vhdx sizes via VhdxManager (sparse-aware)
* shutdown() - ``wsl --shutdown`` (stops all distros + Docker WSL backend)
* compact(vhdx) - diskpart compact via VhdxManager
* export_size(distro) - estimate export cost via ``wsl --export`` dry probe

Windows-only; all methods degrade gracefully on other platforms.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cortex_unified.core import proc as _proc

_LOG = logging.getLogger("cortex.system_tools.wsl_cleaner")
_IS_WINDOWS = platform.system() == "Windows"
_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0


@dataclass(slots=True)
class WslDistro:
    """One WSL distribution with its vhdx estimate."""
    name: str
    state: str
    version: int
    vhdx_path: Path | None
    vhdx_bytes: int
    vhdx_on_disk_bytes: int

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "name": self.name,
            "state": self.state,
            "version": self.version,
            "vhdx_path": str(self.vhdx_path) if self.vhdx_path else None,
            "vhdx_bytes": self.vhdx_bytes,
            "vhdx_on_disk_bytes": self.vhdx_on_disk_bytes,
            "vhdx_human": _fmt_bytes(self.vhdx_bytes),
            "on_disk_human": _fmt_bytes(self.vhdx_on_disk_bytes),
        }


def _fmt_bytes(n: int) -> str:
    """_fmt_bytes."""
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"
    """_fmt_bytes."""
    """_fmt_bytes."""


def _decode(raw: bytes | str | None) -> str:
    """_decode."""
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
    """_decode."""
    """_decode."""


class WslCleaner:
    """Discover and clean WSL distro disks (Windows-only)."""

    @staticmethod
    def is_supported() -> bool:
        """Is supported."""
        return _IS_WINDOWS

    def is_wsl_available(self) -> bool:
        """Is wsl available."""
        if not _IS_WINDOWS:
            return False
        try:
            proc = _proc.run(["wsl", "--status"], text=False, timeout=10, creationflags=_NO_WINDOW)
            return proc.returncode == 0 or b"Default Distribution" in proc.stdout or b"WSL" in _decode(proc.stdout)
        except Exception:
            # Fallback: check wsl.exe exists and registry key
            import shutil
            if shutil.which("wsl"):
                return True
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Lxss"):
                    return True
            except OSError:
                return False

    def list_distros(self) -> list[WslDistro]:
        """Enumerate distros via ``wsl --list --verbose`` + vhdx size probe."""
        if not _IS_WINDOWS:
            return []
        distros: list[WslDistro] = []
        # Try wsl CLI first
        try:
            proc = _proc.run(["wsl", "--list", "--verbose"], text=False, timeout=15, creationflags=_NO_WINDOW)
            text = _decode(proc.stdout) + _decode(proc.stderr)
            for line in text.splitlines():
                line = line.strip()
                if not line or line.lower().startswith("name") or line.startswith("-"):
                    continue
                # Format: NAME  STATE  VERSION
                # The default marker "*" is glued to the name: "* Ubuntu  Running  2"
                line = line.lstrip("*").strip()
                parts = line.split()
                if len(parts) < 2:
                    continue
                name = parts[0]
                # Heuristic: last token is version digit, middle is state
                try:
                    version = int(parts[-1])
                except ValueError:
                    version = 2
                state = parts[1] if len(parts) >= 3 else "Unknown"
                distros.append(WslDistro(name=name, state=state, version=version,
                                         vhdx_path=None, vhdx_bytes=0, vhdx_on_disk_bytes=0))
        except Exception as exc:
            _LOG.debug("wsl --list failed: %s", exc)

        # Fallback / enrich via registry for vhdx paths
        try:
            import winreg
            reg_map: dict[str, Path] = {}
            try:
                root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Lxss")
                with root:
                    i = 0
                    while True:
                        try:
                            guid = winreg.EnumKey(root, i)
                        except OSError:
                            break
                        i += 1
                        try:
                            with winreg.OpenKey(root, guid) as sub:
                                base = self._reg_str(sub, "BasePath")
                                name = self._reg_str(sub, "DistributionName") or guid
                                version = self._reg_int(sub, "Version")
                                if base:
                                    base_path = Path(base.replace("\\\\?\\", ""))
                                    vhdx = base_path / "ext4.vhdx"
                                    if vhdx.exists():
                                        reg_map[name] = vhdx
                                    # Also handle system.vhd (WSL1 import)
                                    sys_vhd = base_path / "system.vhd"
                                    if sys_vhd.exists() and name not in reg_map:
                                        reg_map[name] = sys_vhd
                        except OSError:
                            continue
            except OSError:
                pass
            # Merge: enrich CLI list with vhdx, or create from registry if CLI empty
            if not distros:
                for name, vhdx in reg_map.items():
                    distros.append(WslDistro(name=name, state="Unknown", version=2,
                                             vhdx_path=vhdx, vhdx_bytes=0, vhdx_on_disk_bytes=0))
            else:
                for d in distros:
                    if d.name in reg_map:
                        d.vhdx_path = reg_map[d.name]
        except ImportError:
            pass

        # Measure sizes
        for d in distros:
            if d.vhdx_path and d.vhdx_path.exists():
                try:
                    d.vhdx_bytes = d.vhdx_path.stat().st_size
                    d.vhdx_on_disk_bytes = d.vhdx_bytes
                    try:
                        from cortex_unified.engine import winattrs
                        measured = winattrs.on_disk_size(d.vhdx_path, d.vhdx_bytes)
                        if measured is not None and measured > 0:
                            d.vhdx_on_disk_bytes = measured
                    except Exception:
                        pass
                except OSError:
                    continue
        distros.sort(key=lambda x: x.vhdx_on_disk_bytes, reverse=True)
        return distros

    def shutdown(self, timeout: int = 120) -> tuple[bool, str]:
        """Run ``wsl --shutdown`` so vhdx files can be detached for compaction."""
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
            return False, _decode(proc.stderr).strip() or "wsl --shutdown failed."
        return True, "All WSL distributions stopped."

    def compact_vhdx(self, vhdx_path: Path, timeout: int = 3600,
                     cancel_event=None) -> dict[str, Any]:
        """Compact a single vhdx via VhdxManager.diskpart path (read-only attach)."""
        from cortex_unified.system_tools.vhdx_manager import VhdxManager, VirtualDisk, DiskKind
        mgr = VhdxManager()
        # Find existing VirtualDisk for label/path if possible; else synthesize
        disks = mgr.list_disks()
        target = None
        for d in disks:
            if d.path == vhdx_path:
                target = d
                break
        if target is None:
            target = VirtualDisk(path=vhdx_path, kind=DiskKind.WSL, label=vhdx_path.stem)
            mgr._measure(target)
        result = mgr.compact(target, timeout=timeout, cancel_event=cancel_event)
        return {
            "success": result.success,
            "before_bytes": result.before_bytes,
            "after_bytes": result.after_bytes,
            "freed_bytes": result.freed_bytes,
            "message": result.message,
            "detail": result.detail,
        }

    def get_total_vhdx_size(self) -> tuple[int, int]:
        """Total (logical, on-disk) bytes across all distro vhdx files."""
        distros = self.list_distros()
        return sum(d.vhdx_bytes for d in distros), sum(d.vhdx_on_disk_bytes for d in distros)

    @staticmethod
    def _reg_str(key, name: str) -> str:
        """_reg_str."""
        try:
            import winreg
            value, _ = winreg.QueryValueEx(key, name)
            return str(value)
        except (OSError, ImportError, ValueError):
            return ""
        """_reg_str."""
        """_reg_str."""

    @staticmethod
    def _reg_int(key, name: str) -> int:
        """_reg_int."""
        try:
            import winreg
            value, _ = winreg.QueryValueEx(key, name)
            return int(value)
        except (OSError, ImportError, ValueError, TypeError):
            return 0
        """_reg_int."""
        """_reg_int."""
