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
    """Operation categories recorded on the undo stack."""
    RENAME = auto()
    MOVE = auto()
    COPY = auto()       # records the copy so undo = delete the copy
    DELETE = auto()     # records original path + temp backup so undo = restore
    MKDIR = auto()
    CREATE_FILE = auto()
    BATCH_CREATE = auto()
    """Operation categories recorded on the undo stack."""


class UndoEntry(ABC):
    """Base class for undo/redo entries using the command pattern."""

    def __init__(self, kind: OpKind, original: str, resulting: str,
                 is_dir: bool = False):
        """Store the operation kind, the original path, the resulting
        path, and whether the subject is a directory."""
        self.kind = kind
        self.original = original
        self.resulting = resulting
        self.is_dir = is_dir
        """Store the operation kind, the original path, the resulting
        path, and whether the subject is a directory."""

    @abstractmethod
    def undo(self) -> None:
        """Reverse the recorded operation."""
        ...
        """Reverse the recorded operation."""

    @abstractmethod
    def redo(self) -> None:
        """Re-apply the recorded operation."""
        ...
        """Re-apply the recorded operation."""

    def __repr__(self) -> str:
        """Debug representation: <Class KIND: original -> resulting>."""
        return (f"<{self.__class__.__name__} {self.kind.name}: "
                f"{self.original} -> {self.resulting}>")
        """Debug representation: <Class KIND: original -> resulting>."""


class RenameEntry(UndoEntry):
    """Undo entry for a rename: undo/redo move the item between the old
    and new paths (recreating the parent as needed)."""
    def __init__(self, original: str, resulting: str, is_dir: bool = False):
        """Record a rename from original to resulting."""
        super().__init__(OpKind.RENAME, original, resulting, is_dir)
        """Record a rename from original to resulting."""

    def undo(self) -> None:
        """Move the item back to its original name (creating the parent
        directory if it vanished)."""
        Path(self.original).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(self.resulting, self.original)
        """Move the item back to its original name (creating the parent
        directory if it vanished)."""

    def redo(self) -> None:
        """Re-apply the rename (creating the target parent as needed)."""
        Path(self.resulting).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(self.original, self.resulting)
        """Re-apply the rename (creating the target parent as needed)."""
    """Undo entry for a rename: undo/redo move the item between the old
    and new paths (recreating the parent as needed)."""


class MoveEntry(UndoEntry):
    """Undo entry for a move: undo/redo shuttle the item between source
    and destination, each step guarded by an existence check."""
    def __init__(self, original: str, resulting: str, is_dir: bool = False):
        """Record a move from original to resulting."""
        super().__init__(OpKind.MOVE, original, resulting, is_dir)
        """Record a move from original to resulting."""

    def undo(self) -> None:
        """Move the item back only when it still exists at the destination."""
        if Path(self.resulting).exists():
            Path(self.original).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(self.resulting, self.original)
        """Move the item back only when it still exists at the destination."""

    def redo(self) -> None:
        """Move the item forward only when it still exists at the source."""
        if Path(self.original).exists():
            Path(self.resulting).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(self.original, self.resulting)
        """Move the item forward only when it still exists at the source."""
    """Undo entry for a move: undo/redo shuttle the item between source
    and destination, each step guarded by an existence check."""


class CopyEntry(UndoEntry):
    """Undo entry for a copy: undo deletes the copy (safely for trees),
    redo re-copies from the original source."""
    def __init__(self, original: str, resulting: str, is_dir: bool = False):
        """Record a copy of original to resulting."""
        super().__init__(OpKind.COPY, original, resulting, is_dir)
        """Record a copy of original to resulting."""

    def undo(self) -> None:
        """Remove the copied item (safe rmtree for directories)."""
        target = Path(self.resulting)
        if target.is_dir():
            _safe_rmtree(self.resulting)
        else:
            target.unlink(missing_ok=True)
        """Remove the copied item (safe rmtree for directories)."""

    def redo(self) -> None:
        """Re-create the copy via copytree (dirs) or copy2 (files)."""
        src = Path(self.original)
        if src.is_dir():
            shutil.copytree(self.original, self.resulting)
        else:
            shutil.copy2(self.original, self.resulting)
        """Re-create the copy via copytree (dirs) or copy2 (files)."""
    """Undo entry for a copy: undo deletes the copy (safely for trees),
    redo re-copies from the original source."""


class DeleteEntry(UndoEntry):
    """Undo entry for a delete: undo restores from the recorded backup
    (when present); redo deletes again (safe rmtree for trees)."""
    def __init__(self, original: str, resulting: str, is_dir: bool = False):
        """Record a deletion of original with optional backup in resulting."""
        super().__init__(OpKind.DELETE, original, resulting, is_dir)
        """Record a deletion of original with optional backup in resulting."""

    def undo(self) -> None:
        """Restore the item from its backup; warn and skip when the backup
        is missing or has disappeared."""
        if not self.resulting or not Path(self.resulting).exists():
            log.warning("Delete undo skipped: backup missing or gone for %s",
                        self.original)
            return
        Path(self.original).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(self.resulting, self.original)
        """Restore the item from its backup; warn and skip when the backup
        is missing or has disappeared."""

    def redo(self) -> None:
        """Delete the item again (safe rmtree for directories)."""
        if Path(self.original).is_dir():
            _safe_rmtree(self.original)
        else:
            Path(self.original).unlink(missing_ok=True)
        """Delete the item again (safe rmtree for directories)."""
    """Undo entry for a delete: undo restores from the recorded backup
    (when present); redo deletes again (safe rmtree for trees)."""


class MkdirEntry(UndoEntry):
    """Undo entry for mkdir: undo removes the directory plus any now-empty
    intermediate parents that were created alongside it; redo recreates it."""
    def __init__(self, original: str, created_parents: list[str] | None = None):
        """Record a directory creation and the missing parents it created."""
        super().__init__(OpKind.MKDIR, original, original, is_dir=True)
        self.created_parents = created_parents or []
        """Record a directory creation and the missing parents it created."""

    def undo(self) -> None:
        """Remove the created directory (tree) and prune its newly created,
        now-empty parent directories in reverse creation order."""
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
        """Remove the created directory (tree) and prune its newly created,
        now-empty parent directories in reverse creation order."""

    def redo(self) -> None:
        """Recreate the directory (including parents)."""
        Path(self.original).mkdir(parents=True, exist_ok=True)
        """Recreate the directory (including parents)."""
    """Undo entry for mkdir: undo removes the directory plus any now-empty
    intermediate parents that were created alongside it; redo recreates it."""


class CreateFileEntry(UndoEntry):
    """Undo entry for file creation: undo removes the file (and prunes
    created parents); redo rewrites the recorded content."""
    def __init__(self, original: str, content: str = "", created_parents: list[str] | None = None):
        """Record a file creation with its content and created parents."""
        super().__init__(OpKind.CREATE_FILE, original, original, is_dir=False)
        self.content = content
        self.created_parents = created_parents or []
        """Record a file creation with its content and created parents."""

    def undo(self) -> None:
        """Delete the created file and remove now-empty created parents in
        reverse order."""
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
        """Delete the created file and remove now-empty created parents in
        reverse order."""

    def redo(self) -> None:
        """Recreate parent dirs and rewrite the file's recorded content."""
        p = Path(self.original)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.content, encoding="utf-8")
        """Recreate parent dirs and rewrite the file's recorded content."""
    """Undo entry for file creation: undo removes the file (and prunes
    created parents); redo rewrites the recorded content."""


class BatchCreateEntry(UndoEntry):
    """Composite undo entry: groups several creation entries so a single
    undo/redo replays the children (undo in reverse order)."""
    def __init__(self, entries: list[UndoEntry], label: str = "Batch creation"):
        """Wrap a list of child entries under a display label."""
        super().__init__(OpKind.BATCH_CREATE, label, f"{len(entries)} items", is_dir=True)
        self.entries = entries
        """Wrap a list of child entries under a display label."""

    def undo(self) -> None:
        """Undo each child in reverse order, logging (not raising) on
        per-entry failure so the rest of the batch still reverses."""
        for entry in reversed(self.entries):
            try:
                entry.undo()
            except Exception as e:
                log.warning("Batch undo step failed: %s", e)
        """Undo each child in reverse order, logging (not raising) on
        per-entry failure so the rest of the batch still reverses."""

    def redo(self) -> None:
        """Redo each child in original order, logging per-entry failures."""
        for entry in self.entries:
            try:
                entry.redo()
            except Exception as e:
                log.warning("Batch redo step failed: %s", e)
        """Redo each child in original order, logging per-entry failures."""
    """Composite undo entry: groups several creation entries so a single
    undo/redo replays the children (undo in reverse order)."""


class UndoStack:
    """Thread-safe undo/redo stack.  All mutations happen on the GUI thread."""

    MAX_DEPTH = 100

    def __init__(self) -> None:
        """Create bounded undo/redo deques (MAX_DEPTH 100, oldest entries
        evicted automatically) plus a change-notification callback slot."""
        self._undo: deque[UndoEntry] = deque(maxlen=self.MAX_DEPTH)
        self._redo: deque[UndoEntry] = deque(maxlen=self.MAX_DEPTH)
        self._on_change: Callable[[], None] | None = None
        self._lock = threading.Lock()
        """Create bounded undo/redo deques (MAX_DEPTH 100, oldest entries
        evicted automatically) plus a change-notification callback slot."""

    def __len__(self) -> int:
        """Return the number of undoable operations (under lock)."""
        with self._lock:
            return len(self._undo)
        """Return the number of undoable operations (under lock)."""

    def __bool__(self) -> int:
        """Return True when at least one operation can be undone."""
        with self._lock:
            return bool(self._undo)
        """Return True when at least one operation can be undone."""

    def set_on_change(self, fn: Callable[[], None]) -> None:
        """Register a callback fired after every stack mutation."""
        self._on_change = fn
        """Register a callback fired after every stack mutation."""

    def _notify(self) -> None:
        """Invoke the change callback when one is registered."""
        if self._on_change:
            self._on_change()
        """Invoke the change callback when one is registered."""

    # ------------------------------------------------------------------
    # Recording operations (called BEFORE the operation executes)
    # ------------------------------------------------------------------

    def record_rename(self, old: str, new: str) -> None:
        """Push a RenameEntry for old -> new (is_dir inferred from old)."""
        entry = RenameEntry(
            original=old,
            resulting=new,
            is_dir=Path(old).is_dir(),
        )
        self._push(entry)
        """Push a RenameEntry for old -> new (is_dir inferred from old)."""

    def record_move(self, src: str, dst: str) -> None:
        """Push a MoveEntry for src -> dst (is_dir inferred from src)."""
        entry = MoveEntry(
            original=src,
            resulting=dst,
            is_dir=Path(src).is_dir(),
        )
        self._push(entry)
        """Push a MoveEntry for src -> dst (is_dir inferred from src)."""

    def record_copy(self, src: str, dst: str) -> None:
        """Push a CopyEntry for src -> dst (is_dir inferred from src)."""
        entry = CopyEntry(
            original=src,
            resulting=dst,
            is_dir=Path(src).is_dir(),
        )
        self._push(entry)
        """Push a CopyEntry for src -> dst (is_dir inferred from src)."""

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
        """Push a MkdirEntry for path with the list of missing parents the
        mkdir created (used for undo pruning)."""
        entry = MkdirEntry(original=path, created_parents=created_parents)
        self._push(entry)
        """Push a MkdirEntry for path with the list of missing parents the
        mkdir created (used for undo pruning)."""

    def record_create_file(self, path: str, content: str = "", created_parents: list[str] | None = None) -> None:
        """Push a CreateFileEntry with the file's content and its created
        parent directories."""
        entry = CreateFileEntry(original=path, content=content, created_parents=created_parents)
        self._push(entry)
        """Push a CreateFileEntry with the file's content and its created
        parent directories."""

    def record_batch_create(self, entries: list[UndoEntry], label: str = "Batch creation") -> None:
        """Push a BatchCreateEntry grouping child creation entries under a
        display label."""
        entry = BatchCreateEntry(entries=entries, label=label)
        self._push(entry)
        """Push a BatchCreateEntry grouping child creation entries under a
        display label."""

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
        """Return True when the undo stack is non-empty."""
        with self._lock:
            return len(self._undo) > 0
        """Return True when the undo stack is non-empty."""

    def can_redo(self) -> bool:
        """Return True when the redo stack is non-empty."""
        with self._lock:
            return len(self._redo) > 0
        """Return True when the redo stack is non-empty."""

    def undo_description(self) -> str | None:
        """Return a human description of the next undo ('Undo kind: a -> b')
        or None when nothing is undoable."""
        with self._lock:
            if not self._undo:
                return None
            e = self._undo[-1]
        return (f"Undo {e.kind.name.lower()}: "
                f"{Path(e.original).name} -> {Path(e.resulting).name}")
        """Return a human description of the next undo ('Undo kind: a -> b')
        or None when nothing is undoable."""

    def redo_description(self) -> str | None:
        """Return a human description of the next redo ('Redo kind: a -> b')
        or None when nothing is redoable."""
        with self._lock:
            if not self._redo:
                return None
            e = self._redo[-1]
        return (f"Redo {e.kind.name.lower()}: "
                f"{Path(e.original).name} -> {Path(e.resulting).name}")
        """Return a human description of the next redo ('Redo kind: a -> b')
        or None when nothing is redoable."""

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _push(self, entry: UndoEntry) -> None:
        """Append an entry to the undo deque under lock, clear the redo
        stack (a new action invalidates the redo branch), and notify."""
        with self._lock:
            self._undo.append(entry)
            self._redo.clear()
        self._notify()
        """Append an entry to the undo deque under lock, clear the redo
        stack (a new action invalidates the redo branch), and notify."""
