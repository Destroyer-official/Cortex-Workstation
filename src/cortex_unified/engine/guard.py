"""Path safety guard for destructive operations.

Replaces the old ``core/security.py`` prefix-matching approach, which had two
problems:

1. ``str.startswith`` matching meant ``/usr`` also "matched" ``/usrdata`` -
   a correctness bug (false positives on sibling names).
2. Directory deletion in the old ``Deleter`` bypassed the check entirely.

This guard uses real path-relationship checks (``Path.is_relative_to``) against
a platform-aware protected set, refuses to touch drive/filesystem roots and the
user-profile root, optionally confines operations to a sandbox base directory,
and verifies writability. It is deliberately conservative: when in doubt, it
returns *unsafe*.
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GuardVerdict:
    """Guard Verdict.

 Frozen verdict holding safe flag and human-readable reason.
 """

    safe: bool
    reason: str = ""

    def __bool__(self) -> bool:  # allow ``if guard.check(p):``
        """Boolean safety test.

 Returns the safe flag so verdicts work directly in if statements.

 Returns:
 bool: True if the operation succeeded, False otherwise.
 """
        return self.safe


def _windows_protected() -> set[Path]:
    """Windows protected.

 Builds the Windows protected set from SystemDrive, SystemRoot, and well-known locations.

 Returns:
 set[Path]: Result of the operation.
 """
    system_drive = os.environ.get("SystemDrive", "C:") + "\\"
    roots = {
        Path(system_drive) / "Windows",
        Path(system_drive) / "Program Files",
        Path(system_drive) / "Program Files (x86)",
        Path(system_drive) / "ProgramData",
        Path(system_drive) / "System Volume Information",
        Path(system_drive) / "$Recycle.Bin",
        Path(system_drive) / "Recovery",
        Path(system_drive) / "Users" / "Default",
        Path(system_drive) / "Users" / "Public",
    }
    win = os.environ.get("SystemRoot")
    if win:
        roots.add(Path(win))
    return {p.resolve(strict=False) for p in roots}


def _posix_protected() -> set[Path]:
    """Posix protected.

 Builds the POSIX protected set, adding macOS locations on Darwin.

 Returns:
 set[Path]: Result of the operation.
 """
    base = {
        "/", "/bin", "/sbin", "/usr", "/lib", "/lib64", "/etc", "/boot",
        "/dev", "/proc", "/sys", "/run", "/var", "/root",
    }
    if platform.system() == "Darwin":
        base |= {"/System", "/Library", "/Applications", "/private", "/cores"}
    return {Path(p).resolve(strict=False) for p in base}


class PathGuard:
    """Path Guard.

    Uses real path-relative checks instead of prefix matching so siblings like /usrdata never mismatch /usr; confines operations to the sandbox base when configured and refuses filesystem/drive roots and the home root.
    """

    def __init__(self, sandbox: os.PathLike[str] | str | None = None,
                 allow_system: bool = False) -> None:
        """Initialize the instance.

        Initializes the instance and configures internal state.

        Args:
            sandbox (os.PathLike[str] | str | None): The sandbox parameter.
            allow_system (bool): The allow system parameter.
        """
        self._system = platform.system()
        self._protected = (
            _windows_protected() if self._system == "Windows" else _posix_protected()
        )
        self._allow_system = allow_system
        self._sandbox = Path(sandbox).resolve(strict=False) if sandbox else None
        # The user's home directory root itself must never be deleted wholesale,
        # even though files *inside* it are fair game.
        try:
            self._home = Path.home().resolve(strict=False)
        except (OSError, RuntimeError):
            self._home = None

    def check(self, path: os.PathLike[str] | str) -> GuardVerdict:
        """Check helper.

        Confines operations to the sandbox base when configured and refuses filesystem/drive roots and the home root.

        Args:
            path (os.PathLike[str] | str): Filesystem path to the target file or directory.

        Returns:
            GuardVerdict: Dictionary mapping identifiers to status or values.
        """
        try:
            resolved = Path(path).resolve(strict=False)
        except (OSError, ValueError) as exc:
            return GuardVerdict(False, f"cannot resolve path: {exc}")

        # 1. Never operate on a filesystem/drive root.
        if resolved == resolved.anchor and resolved.parent == resolved:
            return GuardVerdict(False, "refusing to touch a filesystem root")
        if str(resolved) in {a.rstrip("\\/") for a in (resolved.anchor,)} and len(resolved.parts) <= 1:
            return GuardVerdict(False, "refusing to touch a drive root")

        # 2. Never delete the home directory itself.
        if self._home is not None and resolved == self._home:
            return GuardVerdict(False, "refusing to delete the home directory root")

        # 3. Protected system locations (path == protected OR inside protected).
        if not self._allow_system:
            for prot in self._protected:
                if resolved == prot or self._is_within(resolved, prot):
                    return GuardVerdict(False, f"protected system location: {prot}")

        # 4. Sandbox confinement, if configured.
        if self._sandbox is not None and not self._is_within(resolved, self._sandbox):
            return GuardVerdict(False, f"outside sandbox: {self._sandbox}")

        return GuardVerdict(True)

    def is_writable(self, path: os.PathLike[str] | str) -> bool:
        """True if *path* (or its parent, for not-yet-existing paths) is writable.

 Checks os.access(W_OK) on the path or its parent, failing closed on errors.

 Args:
 path (os.PathLike[str] | str): Filesystem path to the target file or directory.

 Returns:
 bool: True if the operation succeeded, False otherwise.
 """
        p = Path(path)
        try:
            if p.exists():
                return os.access(p, os.W_OK)
            return p.parent.exists() and os.access(p.parent, os.W_OK)
        except OSError:
            return False

    @staticmethod
    def _is_within(child: Path, parent: Path) -> bool:
        """Robust replacement for prefix matching (handles sibling-name traps).

        Uses real path-relative checks instead of prefix matching so siblings like /usrdata never mismatch /usr.

        Args:
            child (Path): The child parameter.
            parent (Path): Parent window or shell controller instance.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        try:
            return child.is_relative_to(parent)  # py>=3.9
        except AttributeError:  # pragma: no cover - very old interpreters
            try:
                child.relative_to(parent)
                return True
            except ValueError:
                return False
