"""Undo/redo stack for file operations.

Records every rename, copy, move, and delete so the user can reverse
accidental changes.  The stack is per-session and does not persist
across restarts (intentional — a crash during a batch operation should
not leave the user with a half-reversed state on next launch).
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
from abc import ABC, abstractmethod
from collections import deque
from enum import Enum, auto
from pathlib import Path
from typing import Callable

log = logging.getLogger("nexus.undo")

import string

_UNSAFE_RMTREE_ROOTS = frozenset(
    [f"{c}:\\" for c in string.ascii_uppercase] +
    [f"{c}:/" for c in string.ascii_uppercase] +
    [f"{c}:\\" for c in string.ascii_lowercase] +
    [f"{c}:/" for c in string.ascii_lowercase] +
    ['/', '/home', '/root', '/etc', '/var', '/usr', '/bin', '/sbin', '/tmp']
)


def _safe_rmtree(path: str) -> None:
    """Remove a directory tree with safety validation."""
    resolved = str(Path(path).resolve())
    if resolved in _UNSAFE_RMTREE_ROOTS:
        log.warning("Refusing to rmtree unsafe path: %s", resolved)
        return
    shutil.rmtree(path)


class OpKind(Enum):
    """OpKind."""
    RENAME = auto()
    MOVE = auto()
    COPY = auto()       # records the copy so undo = delete the copy
    DELETE = auto()     # records original path + temp backup so undo = restore
    MKDIR = auto()
    CREATE_FILE = auto()
    BATCH_CREATE = auto()
    """OpKind class."""


class UndoEntry(ABC):
    """Base class for undo/redo entries using the command pattern."""

    def __init__(self, kind: OpKind, original: str, resulting: str,
                 is_dir: bool = False):
        """__init__."""
        self.kind = kind
        self.original = original
        self.resulting = resulting
        self.is_dir = is_dir
        """__init__."""

    @abstractmethod
    def undo(self) -> None:
        """undo."""
        ...
        """undo."""

    @abstractmethod
    def redo(self) -> None:
        """redo."""
        ...
        """redo."""

    def __repr__(self) -> str:
        """__repr__."""
        return (f"<{self.__class__.__name__} {self.kind.name}: "
                f"{self.original} -> {self.resulting}>")
        """__repr__."""


class RenameEntry(UndoEntry):
    """RenameEntry."""
    def __init__(self, original: str, resulting: str, is_dir: bool = False):
        """__init__."""
        super().__init__(OpKind.RENAME, original, resulting, is_dir)
        """__init__."""

    def undo(self) -> None:
        """undo."""
        Path(self.original).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(self.resulting, self.original)
        """undo."""

    def redo(self) -> None:
        """redo."""
        Path(self.resulting).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(self.original, self.resulting)
        """redo."""
    """RenameEntry class."""


class MoveEntry(UndoEntry):
    """MoveEntry."""
    def __init__(self, original: str, resulting: str, is_dir: bool = False):
        """__init__."""
        super().__init__(OpKind.MOVE, original, resulting, is_dir)
        """__init__."""

    def undo(self) -> None:
        """undo."""
        if Path(self.resulting).exists():
            Path(self.original).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(self.resulting, self.original)
        """undo."""

    def redo(self) -> None:
        """redo."""
        if Path(self.original).exists():
            Path(self.resulting).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(self.original, self.resulting)
        """redo."""
    """MoveEntry class."""


class CopyEntry(UndoEntry):
    """CopyEntry."""
    def __init__(self, original: str, resulting: str, is_dir: bool = False):
        """__init__."""
        super().__init__(OpKind.COPY, original, resulting, is_dir)
        """__init__."""

    def undo(self) -> None:
        """undo."""
        target = Path(self.resulting)
        if target.is_dir():
            _safe_rmtree(self.resulting)
        else:
            target.unlink(missing_ok=True)
        """undo."""

    def redo(self) -> None:
        """redo."""
        src = Path(self.original)
        if src.is_dir():
            shutil.copytree(self.original, self.resulting)
        else:
            shutil.copy2(self.original, self.resulting)
        """redo."""
    """CopyEntry class."""


class DeleteEntry(UndoEntry):
    """DeleteEntry."""
    def __init__(self, original: str, resulting: str, is_dir: bool = False):
        """__init__."""
        super().__init__(OpKind.DELETE, original, resulting, is_dir)
        """__init__."""

    def undo(self) -> None:
        """undo."""
        if not self.resulting or not Path(self.resulting).exists():
            log.warning("Delete undo skipped: backup missing or gone for %s",
                        self.original)
            return
        Path(self.original).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(self.resulting, self.original)
        """undo."""

    def redo(self) -> None:
        """redo."""
        if Path(self.original).is_dir():
            _safe_rmtree(self.original)
        else:
            Path(self.original).unlink(missing_ok=True)
        """redo."""
    """DeleteEntry class."""


class MkdirEntry(UndoEntry):
    """MkdirEntry."""
    def __init__(self, original: str, created_parents: list[str] | None = None):
        """__init__."""
        super().__init__(OpKind.MKDIR, original, original, is_dir=True)
        self.created_parents = created_parents or []
        """__init__."""

    def undo(self) -> None:
        """undo."""
        if Path(self.original).is_dir():
            _safe_rmtree(self.original)
        else:
            Path(self.original).unlink(missing_ok=True)
        for p_str in reversed(self.created_parents):
            try:
                p = Path(p_str)
                if p.is_dir() and not any(p.iterdir()):
                    p.rmdir()
            except OSError:
                pass
        """undo."""

    def redo(self) -> None:
        """redo."""
        Path(self.original).mkdir(parents=True, exist_ok=True)
        """redo."""
    """MkdirEntry class."""


class CreateFileEntry(UndoEntry):
    """CreateFileEntry."""
    def __init__(self, original: str, content: str = "", created_parents: list[str] | None = None):
        """__init__."""
        super().__init__(OpKind.CREATE_FILE, original, original, is_dir=False)
        self.content = content
        self.created_parents = created_parents or []
        """__init__."""

    def undo(self) -> None:
        """undo."""
        p = Path(self.original)
        if p.is_file():
            p.unlink(missing_ok=True)
        for p_str in reversed(self.created_parents):
            try:
                parent_p = Path(p_str)
                if parent_p.is_dir() and not any(parent_p.iterdir()):
                    parent_p.rmdir()
            except OSError:
                pass
        """undo."""

    def redo(self) -> None:
        """redo."""
        p = Path(self.original)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.content, encoding="utf-8")
        """redo."""
    """CreateFileEntry class."""


class BatchCreateEntry(UndoEntry):
    """BatchCreateEntry."""
    def __init__(self, entries: list[UndoEntry], label: str = "Batch creation"):
        """__init__."""
        super().__init__(OpKind.BATCH_CREATE, label, f"{len(entries)} items", is_dir=True)
        self.entries = entries
        """__init__."""

    def undo(self) -> None:
        """undo."""
        for entry in reversed(self.entries):
            try:
                entry.undo()
            except Exception as e:
                log.warning("Batch undo step failed: %s", e)
        """undo."""

    def redo(self) -> None:
        """redo."""
        for entry in self.entries:
            try:
                entry.redo()
            except Exception as e:
                log.warning("Batch redo step failed: %s", e)
        """redo."""
    """BatchCreateEntry class."""


class UndoStack:
    """Thread-safe undo/redo stack.  All mutations happen on the GUI thread."""

    MAX_DEPTH = 100

    def __init__(self) -> None:
        """__init__."""
        self._undo: deque[UndoEntry] = deque(maxlen=self.MAX_DEPTH)
        self._redo: deque[UndoEntry] = deque(maxlen=self.MAX_DEPTH)
        self._on_change: Callable[[], None] | None = None
        self._lock = threading.Lock()
        """__init__."""

    def __len__(self) -> int:
        """__len__."""
        with self._lock:
            return len(self._undo)
        """__len__."""

    def __bool__(self) -> bool:
        """__bool__."""
        with self._lock:
            return bool(self._undo)
        """__bool__."""

    def set_on_change(self, fn: Callable[[], None]) -> None:
        """set_on_change."""
        self._on_change = fn
        """set_on_change."""

    def _notify(self) -> None:
        """_notify."""
        if self._on_change:
            self._on_change()
        """_notify."""

    # ------------------------------------------------------------------
    # Recording operations (called BEFORE the operation executes)
    # ------------------------------------------------------------------

    def record_rename(self, old: str, new: str) -> None:
        """record_rename."""
        entry = RenameEntry(
            original=old,
            resulting=new,
            is_dir=Path(old).is_dir(),
        )
        self._push(entry)
        """record_rename."""

    def record_move(self, src: str, dst: str) -> None:
        """record_move."""
        entry = MoveEntry(
            original=src,
            resulting=dst,
            is_dir=Path(src).is_dir(),
        )
        self._push(entry)
        """record_move."""

    def record_copy(self, src: str, dst: str) -> None:
        """record_copy."""
        entry = CopyEntry(
            original=src,
            resulting=dst,
            is_dir=Path(src).is_dir(),
        )
        self._push(entry)
        """record_copy."""

    def record_delete(self, path: str, backup: str | None = None) -> None:
        """Record a deletion.  If backup is given, undo restores from it."""
        is_dir = Path(path).is_dir() if not backup else Path(backup).is_dir()
        entry = DeleteEntry(
            original=path,
            resulting=backup or "",
            is_dir=is_dir,
        )
        self._push(entry)

    def record_mkdir(self, path: str, created_parents: list[str] | None = None) -> None:
        """record_mkdir."""
        entry = MkdirEntry(original=path, created_parents=created_parents)
        self._push(entry)
        """record_mkdir."""

    def record_create_file(self, path: str, content: str = "", created_parents: list[str] | None = None) -> None:
        """record_create_file."""
        entry = CreateFileEntry(original=path, content=content, created_parents=created_parents)
        self._push(entry)
        """record_create_file."""

    def record_batch_create(self, entries: list[UndoEntry], label: str = "Batch creation") -> None:
        """record_batch_create."""
        entry = BatchCreateEntry(entries=entries, label=label)
        self._push(entry)
        """record_batch_create."""

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    def undo(self) -> str | None:
        """Undo the last operation.  Returns a description or None."""
        with self._lock:
            if not self._undo:
                return None
            entry = self._undo.pop()
        try:
            entry.undo()
        except Exception as exc:
            log.warning("undo failed for %s: %s", entry.original, exc)
            with self._lock:
                self._undo.append(entry)
            return None
        with self._lock:
            self._redo.append(entry)
        self._notify()
        return f"Undid {entry.kind.name.lower()}: {Path(entry.original).name}"

    def redo(self) -> str | None:
        """Redo the last undone operation.  Returns a description or None."""
        with self._lock:
            if not self._redo:
                return None
            entry = self._redo.pop()
        try:
            entry.redo()
        except Exception as exc:
            log.warning("redo failed for %s: %s", entry.resulting, exc)
            with self._lock:
                self._redo.append(entry)
            return None
        with self._lock:
            self._undo.append(entry)
        self._notify()
        return f"Redid {entry.kind.name.lower()}: {Path(entry.original).name}"

    def can_undo(self) -> bool:
        """can_undo."""
        with self._lock:
            return len(self._undo) > 0
        """can_undo."""

    def can_redo(self) -> bool:
        """can_redo."""
        with self._lock:
            return len(self._redo) > 0
        """can_redo."""

    def undo_description(self) -> str | None:
        """undo_description."""
        with self._lock:
            if not self._undo:
                return None
            e = self._undo[-1]
        return (f"Undo {e.kind.name.lower()}: "
                f"{Path(e.original).name} -> {Path(e.resulting).name}")
        """undo_description."""

    def redo_description(self) -> str | None:
        """redo_description."""
        with self._lock:
            if not self._redo:
                return None
            e = self._redo[-1]
        return (f"Redo {e.kind.name.lower()}: "
                f"{Path(e.original).name} -> {Path(e.resulting).name}")
        """redo_description."""

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _push(self, entry: UndoEntry) -> None:
        """_push."""
        with self._lock:
            self._undo.append(entry)
            self._redo.clear()
        self._notify()
        """_push."""
