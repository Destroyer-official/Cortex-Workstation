"""Folder tree widget for hierarchical filesystem navigation.

Provides a QTreeView-based folder tree with lazy loading, drive detection,
and navigation sync with the main file list.
"""

from __future__ import annotations

import ctypes
import os
import string
from pathlib import Path

from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QFileIconProvider, QTreeView, QVBoxLayout, QWidget
try:
    from nexus_icons import folder_icon as _material_folder_icon
except ImportError:
    from .nexus_icons import folder_icon as _material_folder_icon


class FolderTreeModel(QStandardItemModel):
    """Foldertreemodel.

    Manages FolderTreeModel operations and coordinates related state changes for the component.
    """

    _MAX_DEPTH = 20

    def __init__(self, parent=None):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self._loaded: set[str] = set()
        self._provider = QFileIconProvider()
        self._visited_inodes: set[tuple[int, int]] = set()

    def populate_drives(self):
        """Add top-level drive items.

        Refreshes table or tree items with formatted values, tooltips, and status indicators based on the provided dataset.
        """
        self.clear()
        self.setHorizontalHeaderLabels(["Name"])
        self._visited_inodes.clear()

        # Add quick access locations
        home = Path.home()
        quick_items = [
            ("Home", str(home)),
            ("Desktop", str(home / "Desktop")),
            ("Documents", str(home / "Documents")),
            ("Downloads", str(home / "Downloads")),
        ]
        for name, path in quick_items:
            if Path(path).exists():
                item = QStandardItem(name)
                item.setData(path, Qt.ItemDataRole.UserRole)
                item.setIcon(_material_folder_icon(name, 16))
                self.appendRow(item)
                self._setup_children(item, path)

        # Add drives
        drives = self._get_drives()
        for drive_path, label in drives:
            display = f"{label} ({drive_path})" if label else drive_path
            item = QStandardItem(display)
            item.setData(drive_path, Qt.ItemDataRole.UserRole)
            item.setIcon(self._provider.icon(QFileIconProvider.IconType.Drive))
            self.appendRow(item)
            self._setup_children(item, drive_path)

    def _get_drives(self) -> list[tuple[str, str]]:
        """List local drives with volume labels (empty label on failure).

        Manages get drives operations and coordinates related state changes for the component.

        Returns:
            list[tuple[str, str]]: List of processed items or identifiers.
        """
        drives = []
        if os.name == "nt":
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if Path(drive).exists():
                    try:
                        buf = ctypes.create_unicode_buffer(261)
                        ok = ctypes.windll.kernel32.GetVolumeInformationW(
                            drive, buf, 261, None, None, None, None, 0
                        )
                        label = buf.value if ok else ""
                    except Exception:
                        label = ""
                    drives.append((drive, label))
        else:
            drives.append(("/", "Root"))
        return drives

    def _setup_children(self, parent_item: QStandardItem, path: str, depth: int = 0):
        """Add a lazy expansion sentinel child to display an expand chevron until contents load.

        Manages setup children operations and coordinates related state changes for the component.

        Args:
            parent_item (QStandardItem): The parent item parameter.
            path (str): Filesystem path to the target file or directory.
            depth (int): The depth parameter.
        """
        lazy_sentinel = QStandardItem("")
        lazy_sentinel.setData("", Qt.ItemDataRole.UserRole)
        parent_item.appendRow(lazy_sentinel)
        parent_item.setData(
            {"path": path, "loaded": False, "depth": depth},
            Qt.ItemDataRole.UserRole + 1,
        )

    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        """Haschildren.

        Manages hasChildren operations and coordinates related state changes for the component.

        Args:
            parent (QModelIndex): Parent window or shell controller instance.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        if not parent.isValid():
            return self.rowCount() > 0
        item = self.itemFromIndex(parent)
        if item is None:
            return False
        data = item.data(Qt.ItemDataRole.UserRole + 1)
        if data is None:
            return item.hasChildren()
        if not data.get("loaded", False):
            return True
        return item.hasChildren()

    def canFetchMore(self, parent: QModelIndex) -> bool:
        """Canfetchmore.

        Manages canFetchMore operations and coordinates related state changes for the component.

        Args:
            parent (QModelIndex): Parent window or shell controller instance.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        if not parent.isValid():
            return False
        item = self.itemFromIndex(parent)
        if item is None:
            return False
        data = item.data(Qt.ItemDataRole.UserRole + 1)
        if data is None:
            return False
        return not data.get("loaded", True)

    def fetchMore(self, parent: QModelIndex):
        """Fetchmore.

        Manages fetchMore operations and coordinates related state changes for the component.

        Args:
            parent (QModelIndex): Parent window or shell controller instance.
        """
        if not parent.isValid():
            return
        item = self.itemFromIndex(parent)
        if item is None:
            return
        data = item.data(Qt.ItemDataRole.UserRole + 1)
        if data is None or data.get("loaded", True):
            return

        path = data.get("path", "")
        depth = data.get("depth", 0)

        if depth >= self._MAX_DEPTH:
            item.setData({**data, "loaded": True}, Qt.ItemDataRole.UserRole + 1)
            return

        try:
            path_stat = Path(path).stat()
            inode_key = (path_stat.st_dev, path_stat.st_ino)
            if inode_key in self._visited_inodes:
                item.setData({**data, "loaded": True}, Qt.ItemDataRole.UserRole + 1)
                return
            self._visited_inodes.add(inode_key)
        except OSError:
            item.setData({**data, "loaded": True}, Qt.ItemDataRole.UserRole + 1)
            return

        try:
            with os.scandir(path) as scandir_iter:
                entries = sorted(
                    (e for e in scandir_iter if e.is_dir(follow_symlinks=False)),
                    key=lambda e: e.name.lower(),
                )
        except (PermissionError, OSError):
            item.setData({**data, "loaded": False}, Qt.ItemDataRole.UserRole + 1)
            return

        item.removeRow(0)
        item.setData({**data, "loaded": True}, Qt.ItemDataRole.UserRole + 1)

        for entry in entries:
            name = entry.name
            if name.startswith(".") and name not in (".", ".."):
                continue

            try:
                entry_stat = entry.stat(follow_symlinks=False)
                attrs = getattr(entry_stat, "st_file_attributes", 0)
                if attrs & 0x2:  # FILE_ATTRIBUTE_HIDDEN
                    continue
                if attrs & 0x4:  # FILE_ATTRIBUTE_SYSTEM
                    continue
            except (AttributeError, OSError):
                pass

            child = QStandardItem(name)
            child_path = str(Path(path) / name)
            child.setData(child_path, Qt.ItemDataRole.UserRole)
            child.setIcon(_material_folder_icon(name, 16))
            item.appendRow(child)
            self._setup_children(child, child_path, depth=depth + 1)


class FolderTreeWidget(QWidget):
    """Foldertreewidget.

    Manages FolderTreeWidget operations and coordinates related state changes for the component.
    """

    navigate_to = Signal(str)  # Emitted when user clicks a folder

    def __init__(self, parent=None):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setObjectName("FolderTree")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.tree = QTreeView()
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(16)
        self.tree.setRootIsDecorated(True)
        self.tree.setItemsExpandable(True)
        self.tree.setExpandsOnDoubleClick(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setAlternatingRowColors(True)

        self.model = FolderTreeModel(self)
        self.tree.setModel(self.model)
        self.tree.clicked.connect(self._on_clicked)

        lay.addWidget(self.tree)

        # Populate on construction
        self.model.populate_drives()

    def _on_clicked(self, idx: QModelIndex):
        """_on_clicked.

        Manages on clicked operations and coordinates related state changes for the component.

        Args:
            idx (QModelIndex): The idx parameter.
        """
        item = self.model.itemFromIndex(idx)
        if item:
            path = item.data(Qt.ItemDataRole.UserRole)
            if path and Path(path).is_dir():
                self.navigate_to.emit(path)

    def select_path(self, path: str):
        """Expand and select the given path in the tree.

        Walks the tree model to find and select the node matching *path*.
        """
        current = self.model.invisibleRootItem()
        accumulated = ""

        for part in Path(path).parts:
            accumulated = str(Path(accumulated) / part) if accumulated else part

            found = False
            for row in range(current.rowCount()):
                child = current.child(row, 0)
                if child is None:
                    continue
                child_path = child.data(Qt.ItemDataRole.UserRole)
                if child_path and Path(child_path) == Path(accumulated):
                    idx = child.index()
                    if idx.isValid():
                        self.tree.setCurrentIndex(idx)
                        self.tree.scrollTo(idx)
                    # NOTE: do NOT expand() lazily-unloaded nodes here —
                    # expanding mutates the model (fetchMore -> removeRow/
                    # appendRow) inside the view's own expand path, which
                    # has produced native access violations. Nodes load on
                    # real user expansion instead.
                    current = child
                    found = True
                    break

            if not found:
                break

    def refresh(self):
        """Refresh the entire tree.

        This is a full reset — all previously loaded state, expanded nodes,
        and in-flight selections are discarded. The tree is repopulated from
        the root (drives and quick-access locations).
        """
        self.model.populate_drives()

    def cleanup(self):
        """Clean up resources.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.
        """
        self.model.clear()
        self.model._visited_inodes.clear()
