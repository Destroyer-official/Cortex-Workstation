"""NexusExplorerWidget — premium native Qt6 file explorer.

Drop this widget into any PySide6 window (e.g. a Cortex Cleaner page).
It is fully in-process: no extra window, no subprocess UI, no web.

Features: tabs, breadcrumbs, details+icons dual view, preview pane,
collapsible sidebar, inline search, F12 debug overlay, smooth hover effects,
DPI-aware, loading/empty/error states, full keyboard shortcuts.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    QAbstractTableModel,
    QFileSystemWatcher,
    QModelIndex,
    QObject,
    QProcess,
    QSettings,
    QRect,
    QSize,
    Qt,
    QThread,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QStandardItem,
    QStandardItemModel,
    QAction,
    QBrush,
    QColor,
    QCursor,
    QDrag,
    QDragEnterEvent,
    QDragMoveEvent,
    QFont,
    QFontMetrics,
    QIcon,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
    QShortcut,
)
from PySide6.QtCore import (
    QMimeData,
    QUrl,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTabBar,
    QTableView,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

try:
    from nexus_core import (
        Engine,
        FileTableModel,
        IconThumbs,
        SortProxy,
        _get_marshal,
        _SHUTTING_DOWN,
        fmt_ms,
        human,
        create_nested_folder,
        create_nested_file,
        scaffold_hierarchy,
        FILE_TEMPLATES,
        PROJECT_SCAFFOLD_PRESETS,
    )
    from nexus_undo import UndoStack
    from nexus_icons import (
        icon as _fluent_icon,
        action_icon as _fluent_action,
        sidebar_icon as _fluent_sidebar,
        icon_for_ext as _fluent_ext_icon,
        _CLR_ACCENT as _FLUENT_ACCENT,
        _CLR_DEFAULT as _FLUENT_DEFAULT,
    )
except ImportError:
    from .nexus_core import (
        Engine,
        FileTableModel,
        IconThumbs,
        SortProxy,
        _get_marshal,
        _SHUTTING_DOWN,
        fmt_ms,
        human,
        create_nested_folder,
        create_nested_file,
        scaffold_hierarchy,
        FILE_TEMPLATES,
        PROJECT_SCAFFOLD_PRESETS,
    )
    from .nexus_undo import UndoStack
    from .nexus_icons import (
        icon as _fluent_icon,
        action_icon as _fluent_action,
        sidebar_icon as _fluent_sidebar,
        icon_for_ext as _fluent_ext_icon,
        _CLR_ACCENT as _FLUENT_ACCENT,
        _CLR_DEFAULT as _FLUENT_DEFAULT,
    )

from collections import deque

log = logging.getLogger("nexus.explorer")




def _safe_ts(ms: float) -> str:
    """Format epoch-ms defensively; out-of-range timestamps (corrupt
    metadata, year > 9999, negatives from some filesystems) previously
    raised OverflowError straight through Qt slots."""
    try:
        return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M")
    except (OverflowError, OSError, ValueError):
        return "?"

# ── DPI scaling ──────────────────────────────────────────────────────────────
_dpi_scale = 1.0


def _scaled(px: int) -> int:
    """Scaled.

    Manages scaled operations and coordinates related state changes for the component.

    Args:
        px (int): The px parameter.

    Returns:
        int: Result of the operation.
    """
    return int(px * _dpi_scale)


def _init_dpi():
    """Detect the primary monitor DPI and set the global scaling factor.

    Reads LOGPIXELSX via Win32 GetDeviceCaps; the scale is clamped to at
    least 1.0 and falls back to 1.0 on any OS/attribute error.
    """
    global _dpi_scale
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        ctypes.windll.user32.ReleaseDC(0, hdc)
        _dpi_scale = max(dpi / 96.0, 1.0)
    except (OSError, ValueError, AttributeError):
        _dpi_scale = 1.0


_init_dpi()


# ── Premium QSS ──────────────────────────────────────────────────────────────
DARK_QSS = """
/* NexusExplorer Premium Windows 11 Fluent Theme */

/* Explorer root */
#NexusRoot {
    background: #141418;
    border: none;
}
#NexusRoot QWidget {
    font-family: 'Segoe UI Variable', 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 9pt;
    color: #E2E8F0;
}

/* ── Tier 1: Modern Tab Bar Row (Windows 11 Inline TitleBar) ────────── */
#TabBarContainer, #TitleBarTabArea {
    background: transparent;
    border: none;
    min-height: 32px;
    max-height: 36px;
}
#TabBar {
    background: transparent;
    border: none;
}
#TabBar::tab {
    background: transparent;
    color: #94A3B8;
    padding: 6px 14px 6px 12px;
    border: 1px solid transparent;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-size: 8.5pt;
    font-weight: 500;
    min-width: 100px;
    max-width: 220px;
    margin-right: 3px;
}
#TabBar::tab:selected {
    color: #FFFFFF;
    background: rgba(30, 36, 46, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-bottom: 2px solid #00E5FF;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}
#TabBar::tab:hover:!selected {
    background: rgba(255, 255, 255, 0.05);
    color: #E2E8F0;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
#TabBar::close-button {
    subcontrol-position: right;
    padding: 2px;
    margin-right: 2px;
    border-radius: 4px;
}
#TabBar::close-button:hover {
    background: rgba(239, 83, 80, 0.85);
    color: #FFFFFF;
}
QToolButton#NewTabBtn {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 3px;
    min-width: 26px;
    min-height: 26px;
    max-width: 26px;
    max-height: 26px;
}
QToolButton#NewTabBtn:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.12);
}

/* ── Tier 2: Navigation & Full-Width Address & Search ───────────────────── */
#NavAddressContainer {
    background: #18181C;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    min-height: 42px;
    max-height: 42px;
    padding: 3px 8px;
}
#NavAddressContainer QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px 6px;
    min-width: 30px;
    min-height: 28px;
}
#NavAddressContainer QToolButton:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.1);
}
#NavAddressContainer QToolButton:pressed {
    background: rgba(96, 205, 255, 0.15);
    border-color: #60CDFF;
}
#NavAddressContainer QToolButton:disabled {
    opacity: 0.3;
}

#AddressBarBox {
    background: #121215;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 6px;
}
#AddressBarBox:hover {
    border-color: rgba(255, 255, 255, 0.18);
    background: #141418;
}

#Crumbs {
    background: transparent;
    border: none;
    padding: 2px 8px;
}

QLineEdit#AddrBar {
    background: transparent;
    border: none;
    padding: 4px 10px;
    font-size: 9pt;
    color: #FFFFFF;
    selection-background-color: rgba(96, 205, 255, 0.35);
}

QLineEdit#SearchInput {
    background: #121215;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 9pt;
    min-width: 220px;
    max-width: 320px;
    color: #FFFFFF;
}
QLineEdit#SearchInput:hover {
    border-color: rgba(255, 255, 255, 0.18);
    background: #141418;
}
QLineEdit#SearchInput:focus {
    border-color: #60CDFF;
    background: #18181E;
}

/* ── Tier 3: Windows 11 Fluent Command Bar ──────────────────────────────── */
#CommandBarContainer, #Toolbar {
    background: #141418;
    border-bottom: 1px solid rgba(255, 255, 255, 0.07);
    min-height: 42px;
    max-height: 42px;
    padding: 3px 8px;
}
#CommandBarContainer QToolButton, #Toolbar QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 9pt;
    font-weight: 500;
    color: #CBD5E1;
    min-height: 28px;
}
#CommandBarContainer QToolButton:hover, #Toolbar QToolButton:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.1);
    color: #FFFFFF;
}
#CommandBarContainer QToolButton:pressed, #Toolbar QToolButton:pressed {
    background: rgba(96, 205, 255, 0.15);
    border-color: #60CDFF;
    color: #60CDFF;
}
#CommandBarContainer QToolButton:checked, #Toolbar QToolButton:checked {
    background: rgba(96, 205, 255, 0.15);
    border: 1px solid rgba(96, 205, 255, 0.4);
    color: #60CDFF;
}
#CommandBarContainer QToolButton#NewItemBtn {
    font-weight: 600;
    color: #FFFFFF;
    padding: 4px 12px;
}
#CommandBarContainer QToolButton#DetailsBtn {
    font-weight: 500;
}

/* Buttons - premium glassmorphism */
QPushButton {
    background: rgba(42,42,42,180);
    border: 1px solid rgba(51,51,51,0.8);
    border-radius: 8px;
    padding: 6px 16px;
    font-size: 8.5pt;
    color: #CCCCCC;
}
QPushButton:hover {
    background: rgba(51,51,51,200);
    border-color: rgba(144,202,249,0.2);
    color: #E0E0E0;
}
QPushButton:pressed {
    background: rgba(144,202,249,0.12);
    border-color: #90CAF9;
    color: #FFFFFF;
}
QPushButton:disabled {
    color: #3A3A3A;
    background: rgba(30,30,30,120);
    border-color: rgba(51,51,51,0.4);
}
QPushButton#accent {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #90CAF9, stop:1 #4DD0E1);
    border: none;
    color: #0D0D0D;
    font-weight: 700;
    border-radius: 8px;
}
QPushButton#accent:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #B3E5FC, stop:1 #80DEEA);
}
QPushButton#accent:pressed {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #64B5F6, stop:1 #26C6DA);
}

/* Sidebar - deep glass */
#SidePanel {
    background: #121216;
    border-right: 1px solid rgba(255, 255, 255, 0.07);
}
#SideTitle {
    color: #64748B;
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 0.8px;
    padding: 12px 14px 4px;
}

/* Tree / Table / List - premium Windows 11 selection */
QTreeView, QTableView, QListWidget {
    background: #141418;
    alternate-background-color: #16161B;
    border: none;
    outline: 0;
    selection-background-color: rgba(96, 205, 255, 0.16);
    selection-color: #FFFFFF;
    font-size: 9pt;
    color: #F1F5F9;
}
QTreeView::item, QTableView::item, QListWidget::item {
    padding: 5px 8px;
    border: none;
    border-radius: 4px;
}
QTreeView::item:hover, QTableView::item:hover, QListWidget::item:hover {
    background: rgba(255, 255, 255, 0.05);
}
QTreeView::item:selected, QTableView::item:selected,
QListWidget::item:selected {
    background: rgba(96, 205, 255, 0.18);
    color: #FFFFFF;
}
QTreeView::item:selected:hover, QTableView::item:selected:hover,
QListWidget::item:selected:hover {
    background: rgba(96, 205, 255, 0.24);
}

/* Table headers - Windows 11 Fluent style */
QHeaderView {
    background: #18181C;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
QHeaderView::section {
    background: #18181C;
    color: #94A3B8;
    border: none;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
    padding: 6px 12px;
    font-weight: 600;
    font-size: 8.5pt;
}
QHeaderView::section:hover {
    background: rgba(255, 255, 255, 0.04);
    color: #FFFFFF;
}
QHeaderView::section:pressed {
    background: rgba(96, 205, 255, 0.12);
    color: #60CDFF;
}

/* Icon view - premium */
QListView#icons {
    icon-size: 96px;
    spacing: 8px;
    background: #141418;
}
QListView#icons::item {
    padding: 12px;
    border-radius: 10px;
    border: 2px solid transparent;
}
QListView#icons::item:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.1);
}
QListView#icons::item:selected {
    background: rgba(96, 205, 255, 0.15);
    border-color: #60CDFF;
}

/* Preview - frosted panel */
#Preview {
    background: rgba(13,13,13,240);
    border-left: 1px solid rgba(51,51,51,0.5);
}
#PreviewName {
    font-weight: 700;
    font-size: 10pt;
    color: #FFFFFF;
}
#PreviewMeta {
    color: #888888;
    font-size: 8pt;
}

/* Status bar - minimal */
#Status {
    background: rgba(18,18,18,240);
    border-top: 1px solid rgba(51,51,51,0.4);
    color: #666666;
    font-size: 8pt;
}
#StatusTransfer {
    color: #4DD0E1;
    font-weight: bold;
}

/* Context menu - glassmorphism */
QMenu {
    background: rgba(30,30,30,240);
    border: 1px solid rgba(51,51,51,0.8);
    border-radius: 12px;
    padding: 6px;
}
QMenu::item {
    padding: 8px 32px 8px 16px;
    border-radius: 8px;
    color: #CCCCCC;
}
QMenu::item:selected {
    background: rgba(144,202,249,0.10);
    color: #FFFFFF;
}
QMenu::item:disabled {
    color: #3A3A3A;
}
QMenu::separator {
    height: 1px;
    background: rgba(51,51,51,0.6);
    margin: 5px 12px;
}

/* Scrollbar - minimal pill */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: rgba(80,80,80,120);
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(144,202,249,0.3);
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: rgba(80,80,80,120);
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(144,202,249,0.3);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    height: 0;
    width: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* Splitter - subtle drag handle */
QSplitter::handle {
    background: rgba(51,51,51,0.4);
    width: 1px;
}
QSplitter::handle:hover {
    background: #90CAF9;
}

/* Focus ring */
QLineEdit:focus {
    border-color: #90CAF9;
}

/* Tab add button */
QTabBar::tear {
    image: none;
    width: 0;
}

/* Progress bar - gradient */
QProgressBar {
    background: rgba(34,34,34,180);
    border: none;
    border-radius: 3px;
    max-height: 4px;
}
QProgressBar::chunk {
    border-radius: 3px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #90CAF9, stop:1 #4DD0E1);
}

/* Tooltip - glass */
QToolTip {
    background: rgba(39,39,39,240);
    color: #E0E0E0;
    border: 1px solid rgba(144,202,249,0.15);
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 8.5pt;
}

/* Toolbar QPushButton */
#Toolbar QPushButton {
    background: rgba(42,42,42,150);
    border: 1px solid rgba(51,51,51,0.6);
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 8.5pt;
    font-weight: 600;
    color: #999999;
}
#Toolbar QPushButton:hover {
    background: rgba(144,202,249,0.08);
    border-color: rgba(144,202,249,0.2);
    color: #E0E0E0;
}
#Toolbar QPushButton:pressed {
    background: rgba(144,202,249,0.15);
    border-color: #90CAF9;
    color: #FFFFFF;
}
#Toolbar QPushButton:checked {
    background: rgba(144,202,249,0.10);
    border-color: rgba(144,202,249,0.3);
    color: #90CAF9;
}
#Toolbar QPushButton:disabled {
    color: #3A3A3A;
    background: transparent;
}

/* Debug overlay */
#DebugOverlay {
    background: rgba(13,13,13,240);
    border: 1px solid rgba(51,51,51,0.8);
    border-radius: 10px;
    color: #66BB6A;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 8pt;
    padding: 12px 16px;
}

/* Empty state */
#EmptyState {
    color: #555555;
    font-size: 10pt;
}

/* Command Palette */
#CommandPalette {
    background: rgba(26,26,26,240);
    border: 1px solid rgba(144,202,249,0.2);
    border-radius: 14px;
}
#PaletteSearch {
    background: transparent;
    border: none;
    border-bottom: 1px solid rgba(51,51,51,0.6);
    padding: 12px 16px;
    font-size: 10pt;
    color: #FFFFFF;
    selection-background-color: rgba(144,202,249,0.25);
}
#PaletteList {
    background: transparent;
    border: none;
    outline: 0;
    font-size: 9pt;
    padding: 4px;
}
#PaletteList::item {
    padding: 8px 14px;
    border-left: 3px solid transparent;
    border-radius: 6px;
    margin: 1px 4px;
}
#PaletteList::item:selected {
    background: rgba(144,202,249,0.10);
    border-left-color: #90CAF9;
}

/* Properties dialog */
QDialog QWidget {
    background: transparent;
}

/* Accent button disabled */
QPushButton#accent:disabled {
    color: #3A3A3A;
    background: rgba(19,24,36,120);
}

/* Shortcuts dialog */
#ShortcutsDialog {
    background: rgba(26,26,26,240);
    border: 1px solid rgba(144,202,249,0.15);
    border-radius: 14px;
}
#ShortcutsDialog QLabel {
    color: #E0E0E0;
    font-size: 9pt;
}
#ShortcutsDialog QTableWidget {
    background: transparent;
    border: none;
    gridline-color: rgba(51,51,51,0.6);
    font-size: 9pt;
    color: #E0E0E0;
    selection-background-color: rgba(144,202,249,0.12);
}
#ShortcutsDialog QTableWidget::item {
    padding: 6px 10px;
    border: none;
}
#ShortcutsDialog QHeaderView::section {
    background: rgba(30,30,30,200);
    color: #90CAF9;
    border: none;
    border-bottom: 1px solid rgba(144,202,249,0.15);
    border-right: 1px solid rgba(51,51,51,0.4);
    padding: 8px 12px;
    font-weight: 700;
    font-size: 8.5pt;
    letter-spacing: 0.5px;
}
#ShortcutsDialog QPushButton {
    background: rgba(42,42,42,180);
    border: 1px solid rgba(51,51,51,0.8);
    border-radius: 8px;
    padding: 6px 20px;
    font-size: 8.5pt;
    color: #CCCCCC;
    min-width: 60px;
}
#ShortcutsDialog QPushButton:hover {
    background: rgba(144,202,249,0.10);
    border-color: rgba(144,202,249,0.25);
    color: #FFFFFF;
}
"""


QUICK_FOLDERS = [
    ("Home", "~", "home"), ("Desktop", "~/Desktop", "desktop"),
    ("Downloads", "~/Downloads", "downloads"),
    ("Documents", "~/Documents", "documents"), ("Pictures", "~/Pictures", "pictures"),
    ("Videos", "~/Videos", "videos"), ("Music", "~/Music", "music"),
]


# ═════════════════════════════════════════════════════════════════════════════
# Debug overlay (F12 toggle)
# ═════════════════════════════════════════════════════════════════════════════
class DebugOverlay(QWidget):
    """Debugoverlay.

    Manages DebugOverlay operations and coordinates related state changes for the component.
    """

    def __init__(self, parent=None):
        """Build the frameless overlay window and zero the FPS counters.

        Initializes the instance and configures internal state.

        Args:
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setObjectName("DebugOverlay")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedWidth(_scaled(380))
        self.setMinimumHeight(220)
        self._lines: list[str] = []
        self._max_lines = 28
        self._frame_count = 0
        self._last_time = time.monotonic()
        self._fps = 0.0

    def log_event(self, text: str):
        """Append a timestamped line to the debug log and repaint.

        The log is capped at ``_max_lines`` entries; oldest lines are dropped.
        """
        ts = time.strftime("%H:%M:%S")
        self._lines.append(f"[{ts}] {text}")
        if len(self._lines) > self._max_lines:
            self._lines = self._lines[-self._max_lines:]
        self.update()

    def tick_fps(self):
        """Count a rendered frame; recompute FPS once per elapsed second.

        Manages tick fps operations and coordinates related state changes for the component.
        """
        self._frame_count += 1
        now = time.monotonic()
        dt = now - self._last_time
        if dt >= 1.0:
            self._fps = self._frame_count / dt
            self._frame_count = 0
            self._last_time = now
            self.update()

    def paintEvent(self, ev):  # noqa: N802
        """Render custom visual elements and borders for the widget.

        Uses QPainter with active theme colors, gradients, and font metrics to draw specialized UI graphics.

        Args:
            ev: The Qt event object.
        """
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.fillRect(self.rect(), QColor(10, 14, 20, 230))
            p.setPen(QColor(0, 255, 136))

            fm = QFontMetrics(self.font())
            y = fm.height() + 6
            p.drawText(10, y, f"Nexus Explorer — Debug Overlay (F12)")
            y += fm.height() + 2
            p.setPen(QColor(0, 200, 100))
            p.drawText(10, y, f"FPS: {self._fps:.0f}")
            y += fm.height()
            p.drawText(10, y, f"Lines logged: {len(self._lines)}")
            y += fm.height() + 6

            p.setPen(QColor(0, 255, 136))
            for line in self._lines[-22:]:
                if y > self.height() - 10:
                    break
                p.drawText(10, y, line[:70])
                y += fm.height()
        finally:
            p.end()


# ═════════════════════════════════════════════════════════════════════════════
# CrumbBar — painted breadcrumb path with hover highlight
# ═════════════════════════════════════════════════════════════════════════════
class CrumbBar(QWidget):
    """Crumbbar.

    Manages CrumbBar operations and coordinates related state changes for the component.
    """

    navigate = Signal(str)
    editRequested = Signal()

    def __init__(self, parent=None):
        """Initialize the bar with empty path and no hit zones; enable mouse tracking.

        Initializes the instance and configures internal state.

        Args:
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self._path = path = ""
        self._path = ""
        self._hits: list[tuple[int, int, str]] = []
        self.setFixedHeight(32)
        self.setObjectName("Crumbs")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self._bold_font = QFont()
        self._bold_font.setBold(True)
        self._normal_font = QFont()
        self._normal_font.setBold(False)

    def setPath(self, path: str) -> None:
        """Setpath.

        Manages setPath operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        self._path = path
        self._hits = []
        self.update()

    def _segments(self):
        """Split ``_path`` into (label, absolute-path) breadcrumb segments.

        Handles both drive letters ("C:") and UNC-style components, building
        each cumulative target path as it walks the parts.
        """
        parts = [p for p in self._path.replace("/", "\\").split("\\") if p]
        out, cum = [], ""
        for i, p in enumerate(parts):
            if i == 0 and len(p) == 2 and p[1] == ":":
                cum = p + "\\"
            else:
                cum = (cum if cum.endswith("\\") else cum + "\\") + p
            out.append((p, cum))
        return out

    def mouseMoveEvent(self, ev):  # noqa: N802
        """Handle mouse mouseMove interaction events.

        Tracks cursor coordinates, button states, drag-and-drop actions, or item selection changes within the widget.

        Args:
            ev: The Qt event object.
        """
        self.update()

    def leaveEvent(self, ev):  # noqa: N802
        """Leaveevent.

        Manages leaveEvent operations and coordinates related state changes for the component.

        Args:
            ev: The Qt event object.
        """
        self.update()

    def paintEvent(self, ev):  # noqa: N802
        """Paint breadcrumb segments with hover highlight and ellipsis collapsing.

        Paths longer than 6 segments are collapsed to drive + "…" + last 3
        segments. Records clickable hit rectangles in ``_hits`` for
        :meth:`mouseReleaseEvent`.
        """
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.fillRect(self.rect(), QColor(13, 13, 13, 200))
            fm = QFontMetrics(self.font())
            mouse = self.mapFromGlobal(QCursor.pos())
            x = 12
            segs = self._segments()
            if not segs:
                p.setPen(QColor("#555555"))
                p.drawText(12, 22, "\u2302  This PC  (double-click to type a path)")
                return
            shown = segs if len(segs) <= 6 else \
                [segs[0], ("\u2026", segs[len(segs) // 2][1])] + segs[-3:]
            self._hits = []
            for i, (label, target) in enumerate(shown):
                w = fm.horizontalAdvance(label) + 20
                r = QRect(x, 5, w, 22)
                is_hover = r.contains(mouse)
                if is_hover:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(144, 202, 249, 20))
                    p.drawRoundedRect(r, 6, 6)
                if i == 0:
                    p.setPen(QColor("#FFFFFF"))
                    p.setFont(self._bold_font)
                else:
                    p.setPen(QColor("#888888") if not is_hover else QColor("#BBBBBB"))
                    p.setFont(self._normal_font)
                p.drawText(r, Qt.AlignmentFlag.AlignCenter, label)
                self._hits.append((x, x + w, target))
                x += w + 2
                if i < len(shown) - 1:
                    p.setPen(QColor(144, 202, 249, 80))
                    p.drawText(x, 22, "\u203a")
                    x += fm.horizontalAdvance("\u203a") + 6
            p.setFont(self._normal_font)
        finally:
            p.end()

    def mouseReleaseEvent(self, ev):
        """Navigate to the clicked segment, or start path editing on empty space.

        Emits ``navigate`` with the segment's absolute path when the release
        lands inside a recorded hit zone; otherwise emits ``editRequested``.
        """
        x = ev.position().x()
        for x0, x1, target in self._hits:
            if x0 <= x <= x1:
                self.navigate.emit(target)
                return
        self.editRequested.emit()

    def mouseDoubleClickEvent(self, ev):  # noqa: N802
        """Mousedoubleclickevent.

        Manages mouseDoubleClickEvent operations and coordinates related state changes for the component.

        Args:
            ev: The Qt event object.
        """
        self.editRequested.emit()


# ═════════════════════════════════════════════════════════════════════════════
# QuickLookPopup — Space bar preview (macOS Quick Look style)
# ═════════════════════════════════════════════════════════════════════════════
class QuickLookPopup(QWidget):
    """Quicklookpopup.

    Manages QuickLookPopup operations and coordinates related state changes for the component.
    """

    def __init__(self, icons: IconThumbs, parent=None):
        """Build the frameless 480x400 popup with icon, name, and metadata labels.

        Initializes the instance and configures internal state.

        Args:
            icons (IconThumbs): The icons parameter.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setWindowTitle("Quick Look")
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self._icons = icons
        self.setFixedSize(480, 400)
        self.setStyleSheet("background: rgba(30,30,30,220); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        self.icon_lbl = QLabel()
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setMinimumHeight(200)
        self.icon_lbl.setStyleSheet(
            "background: rgba(30,30,30,220); border-radius: 10px; border: 1px solid rgba(255,255,255,0.08);")

        self.name_lbl = QLabel("")
        self.name_lbl.setStyleSheet("font-size: 11pt; font-weight: 600; color: #FFFFFF;")
        self.name_lbl.setWordWrap(True)

        self.meta_lbl = QLabel("")
        self.meta_lbl.setStyleSheet("color: #AAAAAA; font-size: 8.5pt;")
        self.meta_lbl.setWordWrap(True)

        lay.addWidget(self.icon_lbl)
        lay.addWidget(self.name_lbl)
        lay.addWidget(self.meta_lbl)

    def show_file(self, row: dict, pos=None):
        """Populate and show the popup for a file row.

        Args:
            row: engine row dict (path, name, isDir, size, ext, modifiedMs).
            pos: optional cursor position to anchor the popup near.

        Renders image files (up to 50MB, common raster formats) as a scaled
        preview via QImageReader; everything else falls back to a large
        file-type icon from the shared IconThumbs cache.
        """
        from PySide6.QtGui import QImageReader, QPixmap

        path = row.get("path", "")
        name = row.get("name", "")
        is_dir = row.get("isDir", False)
        size = "" if is_dir else human(row.get("size", 0))
        ext = (row.get("ext") or "").upper()
        kind = "Folder" if is_dir else (ext or "FILE")

        meta_parts = [f"{kind}"]
        if size:
            meta_parts.append(size)
        ms = int(row.get("modifiedMs", 0) or 0)
        if ms:
            from datetime import datetime
            meta_parts.append(_safe_ts(ms))
        meta_parts.append(path)

        self.name_lbl.setText(name)
        self.meta_lbl.setText("\n".join(meta_parts))

        # Try image preview first (skip files >50MB)
        ext_l = "." + (row.get("ext") or "").lower()
        if not is_dir and ext_l in {".png", ".jpg", ".jpeg", ".gif", ".bmp",
                                     ".webp", ".ico"} and Path(path).is_file():
            try:
                if Path(path).stat().st_size > 50 * 1024 * 1024:
                    ico = self._icons.icon_for(row)
                    self.icon_lbl.setPixmap(ico.pixmap(128, 128))
                    self._show_at(pos)
                    return
            except OSError:
                pass
            r = QImageReader(path)
            r.setAutoTransform(True)
            r.setScaledSize(QSize(512, 512))
            img = r.read()
            if not img.isNull():
                img = img.scaled(440, 220,
                                 Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
                self.icon_lbl.setPixmap(QPixmap.fromImage(img))
                self._show_at(pos)
                return

        # Fall back to large icon
        ico = self._icons.icon_for(row)
        self.icon_lbl.setPixmap(ico.pixmap(128, 128))
        self._show_at(pos)

    def _show_at(self, pos=None):
        """Show the popup, flipping its anchor to stay on-screen.

        Positions at ``pos`` + 12px offset by default; flips left/up when the
        popup would overflow the current screen's available geometry.
        """
        if pos:
            x = pos.x() + 12
            y = pos.y() + 12
            screen = self.screen()
            if screen:
                geo = screen.availableGeometry()
                if x + self.width() > geo.right():
                    x = pos.x() - self.width() - 12
                if y + self.height() > geo.bottom():
                    y = pos.y() - self.height() - 12
            self.move(x, y)
        self.show()
        self.raise_()


# ═════════════════════════════════════════════════════════════════════════════
# BulkRenameDialog — regex rename with live preview
# ═════════════════════════════════════════════════════════════════════════════
class BulkRenameDialog(QDialog):
    """Bulkrenamedialog.

    Manages BulkRenameDialog operations and coordinates related state changes for the component.
    """

    MODES = [
        "Find & Replace",
        "Sequential Numbering",
        "Date Prefix",
        "Case Transform",
        "Add / Remove Suffix & Prefix",
    ]

    def __init__(self, paths: list[str], parent=None):
        """Build the dialog with mode combo, stacked input pages, and preview table.

        Args:
            paths: absolute file paths to rename (all assumed in one folder).
            parent: parent widget; when it is an ExplorerWidget its undo
                stack is used to record each rename.
        """
        super().__init__(parent)
        self.setWindowTitle("Bulk Rename")
        self.setMinimumSize(700, 540)
        self.setWindowFlags(Qt.WindowType.Dialog)
        self._originals = paths
        self._previews: list[tuple[str, str]] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        # Mode selector
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(self.MODES)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo, 1)
        mode_row.addStretch(1)
        lay.addLayout(mode_row)

        # Stacked widget for mode-specific inputs
        self._stack = QStackedWidget()

        # ── Mode 0: Find & Replace ────────────────────────────────────
        fr_page = QWidget()
        fr_lay = QHBoxLayout(fr_page)
        fr_lay.setContentsMargins(0, 0, 0, 0)
        fr_lay.addWidget(QLabel("Find:"))
        self.fr_find = QLineEdit()
        self.fr_find.setPlaceholderText("regex pattern (e.g. IMG_(\\d+))")
        self.fr_find.textChanged.connect(self._update_preview)
        fr_lay.addWidget(self.fr_find, 1)
        fr_lay.addWidget(QLabel("Replace:"))
        self.fr_replace = QLineEdit()
        self.fr_replace.setPlaceholderText("replacement (e.g. Photo_\\1)")
        self.fr_replace.textChanged.connect(self._update_preview)
        fr_lay.addWidget(self.fr_replace, 1)
        self._stack.addWidget(fr_page)

        # ── Mode 1: Sequential Numbering ──────────────────────────────
        sn_page = QWidget()
        sn_lay = QHBoxLayout(sn_page)
        sn_lay.setContentsMargins(0, 0, 0, 0)
        sn_lay.addWidget(QLabel("Prefix:"))
        self.sn_prefix = QLineEdit()
        self.sn_prefix.setPlaceholderText("e.g. Photo_")
        self.sn_prefix.textChanged.connect(self._update_preview)
        sn_lay.addWidget(self.sn_prefix, 1)
        sn_lay.addWidget(QLabel("Start:"))
        self.sn_start = QSpinBox()
        self.sn_start.setRange(0, 999999)
        self.sn_start.setValue(1)
        self.sn_start.valueChanged.connect(self._update_preview)
        sn_lay.addWidget(self.sn_start)
        sn_lay.addWidget(QLabel("Padding:"))
        self.sn_pad = QSpinBox()
        self.sn_pad.setRange(1, 10)
        self.sn_pad.setValue(3)
        self.sn_pad.valueChanged.connect(self._update_preview)
        sn_lay.addWidget(self.sn_pad)
        self._stack.addWidget(sn_page)

        # ── Mode 2: Date Prefix ───────────────────────────────────────
        dp_page = QWidget()
        dp_lay = QHBoxLayout(dp_page)
        dp_lay.setContentsMargins(0, 0, 0, 0)
        self.dp_use_mtime = QCheckBox("Use modification date")
        self.dp_use_mtime.setChecked(True)
        self.dp_use_mtime.toggled.connect(self._update_preview)
        dp_lay.addWidget(self.dp_use_mtime)
        self.dp_separator = QLineEdit("-")
        self.dp_separator.setPlaceholderText("Separator after date")
        self.dp_separator.setMaximumWidth(60)
        self.dp_separator.textChanged.connect(self._update_preview)
        dp_lay.addWidget(self.dp_separator)
        dp_lay.addStretch(1)
        self._stack.addWidget(dp_page)

        # ── Mode 3: Case Transform ────────────────────────────────────
        ct_page = QWidget()
        ct_lay = QHBoxLayout(ct_page)
        ct_lay.setContentsMargins(0, 0, 0, 0)
        self.ct_combo = QComboBox()
        self.ct_combo.addItems([
            "UPPERCASE", "lowercase", "Title Case", "Sentence case",
        ])
        self.ct_combo.currentIndexChanged.connect(self._update_preview)
        ct_lay.addWidget(QLabel("Transform:"))
        ct_lay.addWidget(self.ct_combo, 1)
        ct_lay.addStretch(1)
        self._stack.addWidget(ct_page)

        # ── Mode 4: Add / Remove Suffix & Prefix ─────────────────────
        ap_page = QWidget()
        ap_lay = QGridLayout(ap_page)
        ap_lay.setContentsMargins(0, 0, 0, 0)
        ap_lay.addWidget(QLabel("Action:"), 0, 0)
        self.ap_action = QComboBox()
        self.ap_action.addItems(["Add Prefix", "Remove Prefix",
                                 "Add Suffix", "Remove Suffix"])
        self.ap_action.currentIndexChanged.connect(self._update_preview)
        ap_lay.addWidget(self.ap_action, 0, 1)
        ap_lay.addWidget(QLabel("Text:"), 0, 2)
        self.ap_text = QLineEdit()
        self.ap_text.setPlaceholderText("text to add / remove")
        self.ap_text.textChanged.connect(self._update_preview)
        ap_lay.addWidget(self.ap_text, 0, 3, 1, 2)
        self._stack.addWidget(ap_page)

        lay.addWidget(self._stack)

        # Preview table
        self.preview_table = QTableView()
        self._preview_model = _RenamePreviewModel()
        self.preview_table.setModel(self._preview_model)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.verticalHeader().setVisible(False)
        hh = self.preview_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.preview_table, 1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_apply = QPushButton("Apply Rename")
        self.btn_apply.setIcon(_fluent_action("check", size=16))
        self.btn_apply.setObjectName("accent")
        self.btn_apply.clicked.connect(self._apply)
        btn_row.addWidget(self.btn_apply)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setIcon(_fluent_action("close", size=16))
        btn_cancel.clicked.connect(self.close)
        btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

        self._update_preview()

    def _on_mode_changed(self, idx: int):
        """Switch the stacked input page to the newly selected mode and refresh preview.

        Manages on mode changed operations and coordinates related state changes for the component.

        Args:
            idx (int): The idx parameter.
        """
        self._stack.setCurrentIndex(idx)
        self._update_preview()

    # ── preview / apply per mode ───────────────────────────────────────────

    def _rename_for_mode(self, name: str, index: int) -> str:
        """Compute the new filename for one entry under the current mode.

        Args:
            name: current filename (with extension).
            index: position in the original list, used for sequential
                numbering start offsets and date lookups.

        Returns the transformed name, or the original on invalid regex /
        unmet prefix-suffix conditions. Modes: 0 regex find/replace,
        1 sequential numbering (prefix + zero-padded counter + ext),
        2 date prefix from mtime/ctime, 3 case transform, 4 add/remove
        prefix or suffix.
        """
        mode = self.mode_combo.currentIndex()

        if mode == 0:
            import re
            find = self.fr_find.text()
            replace = self.fr_replace.text()
            try:
                return re.sub(find, replace, name)
            except re.error:
                return name

        if mode == 1:
            stem = name
            p = Path(name)
            ext = p.suffix
            prefix = self.sn_prefix.text()
            num = self.sn_start.value() + index
            pad = self.sn_pad.value()
            return f"{prefix}{str(num).zfill(pad)}{ext}"

        if mode == 2:
            p = Path(self._originals[index])
            if self.dp_use_mtime.isChecked():
                ts = p.stat().st_mtime
            else:
                ts = p.stat().st_ctime
            from datetime import datetime
            try:
                date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            except (OverflowError, OSError, ValueError):
                date_str = "?"
            sep = self.dp_separator.text()
            return f"{date_str}{sep}{name}"

        if mode == 3:
            ct = self.ct_combo.currentIndex()
            p = Path(name)
            stem = p.stem
            ext = p.suffix
            if ct == 0:
                return stem.upper() + ext
            if ct == 1:
                return stem.lower() + ext
            if ct == 2:
                return stem.title() + ext
            return stem.capitalize() + ext

        if mode == 4:
            act = self.ap_action.currentIndex()
            text = self.ap_text.text()
            p = Path(name)
            stem = p.stem
            ext = p.suffix
            if act == 0:
                return text + stem + ext
            if act == 1:
                if stem.startswith(text):
                    return stem[len(text):] + ext
                return name
            if act == 2:
                return stem + text + ext
            if act == 3:
                if stem.endswith(text):
                    return stem[:-len(text)] + ext
                return name

        return name

    def _update_preview(self):
        """Recompute (original, renamed) pairs for all files and reload the preview table.

        Manages update preview operations and coordinates related state changes for the component.
        """
        self._previews = []
        for i, p in enumerate(self._originals):
            name = Path(p).name
            new_name = self._rename_for_mode(name, i)
            if not new_name:
                new_name = name
            self._previews.append((name, new_name))
        self._preview_model.set_data(self._previews)

    def _apply(self):
        """Rename all files per the current mode, recording undo entries.

        Skips targets that already exist (collected as errors) and keeps
        going on per-file OSError. Shows a warning summarizing errors when
        any occurred, then closes the dialog.
        """
        from PySide6.QtWidgets import QMessageBox
        folder = Path(self._originals[0]).parent if self._originals else None
        if not folder:
            return
        # Access undo stack from parent ExplorerWidget if available
        undo_stack = getattr(self.parent(), '_undo_manager', None)
        errors: list[str] = []
        renamed = 0
        for i, orig_path in enumerate(self._originals):
            old_name = Path(orig_path).name
            new_name = self._rename_for_mode(old_name, i)
            if new_name and new_name != old_name:
                new_path = folder / new_name
                try:
                    if new_path.exists():
                        errors.append(f"{old_name} -> {new_name}: destination already exists")
                        continue
                    if undo_stack:
                        undo_stack.record_rename(str(orig_path), str(new_path))
                    Path(orig_path).rename(new_path)
                    renamed += 1
                except OSError as exc:
                    errors.append(f"{old_name} -> {new_name}: {exc}")
        if errors:
            QMessageBox.warning(
                self,
                "Bulk Rename",
                f"Renamed {renamed} file(s).\n\n{len(errors)} error(s):\n"
                + "\n".join(errors[:20]),
            )
        self.close()


class SearchDialog(QWidget):
    """Searchdialog.

    Manages SearchDialog operations and coordinates related state changes for the component.
    """

    def __init__(self, engine: Engine, start_path: str, parent=None):
        """Build the search window: pattern input, scope combo, results table.

        Args:
            engine: shared Engine used to spawn the search process.
            start_path: directory the search is rooted at for the
                "Current folder" scopes.
        """
        super().__init__(parent)
        self.setWindowTitle("Search Files")
        self.setMinimumSize(680, 520)
        self.setWindowFlags(Qt.WindowType.Dialog)
        self._engine = engine
        self._start_path = start_path
        self._proc: QProcess | None = None
        self._results: list[dict] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        # Search input row
        row = QHBoxLayout()
        row.addWidget(QLabel("Search:"))
        self.input = QLineEdit()
        self.input.setPlaceholderText("e.g. *.pdf, report*, or filename substring")
        self.input.returnPressed.connect(self._start_search)
        row.addWidget(self.input, 1)

        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["Current folder", "Current folder (recursive)", "All drives"])
        row.addWidget(self.scope_combo)
        lay.addLayout(row)

        # Status row
        status_row = QHBoxLayout()
        self.status_label = QLabel("Type a pattern and press Enter")
        status_row.addWidget(self.status_label, 1)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setIcon(_fluent_action("close", size=16))
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_search)
        status_row.addWidget(self.cancel_btn)
        lay.addLayout(status_row)

        # Results table
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Name", "Path", "Size", "Modified"])
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self._open_result)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        lay.addWidget(self.table, 1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        open_btn = QPushButton("Open")
        open_btn.setIcon(_fluent_action("folder", size=16))
        open_btn.clicked.connect(self._open_selected)
        btn_row.addWidget(open_btn)
        close_btn = QPushButton("Close")
        close_btn.setIcon(_fluent_action("close", size=16))
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)

    def _start_search(self):
        """Launch an engine search for the typed pattern for the scope combo.

        Cancels any in-flight search first and disables the input while
        running. Scopes 0 and 1 both search the start folder identically
        (the recursive flag is computed but never forwarded to the
        engine); scope 2 joins every existing drive root into one search.
        """
        query = self.input.text().strip()
        if not query:
            return
        self._cancel_search()
        self._results.clear()
        self.model.removeRows(0, self.model.rowCount())
        self.status_label.setText("Searching\u2026")
        self.cancel_btn.setEnabled(True)
        self.input.setEnabled(False)

        scope = self.scope_combo.currentIndex()
        if scope == 0:
            root = self._start_path
            recursive = False
        elif scope == 1:
            root = self._start_path
            recursive = True
        else:
            import string
            root = ";".join(
                f"{d}:\\" for d in string.ascii_uppercase
                if os.path.isdir(f"{d}:\\")
            )
            recursive = True

        self._proc = self._engine.search(root, query, self._on_search_done)

    def _cancel_search(self):
        """Kill a running search process, if any, and re-enable the input field.

        Manages cancel search operations and coordinates related state changes for the component.
        """
        if self._proc and self._proc.state() == QProcess.ProcessState.Running:
            self._proc.kill()
        self._proc = None
        self.cancel_btn.setEnabled(False)
        self.input.setEnabled(True)

    def _on_search_done(self, code, rows):
        """Replace the results table with the completed search's rows.

        Each row dict is stored on the first item's UserRole so it can be
        retrieved when opened. Updates the status label with the result count.
        """
        self._results = rows
        self.model.removeRows(0, self.model.rowCount())
        for row in rows:
            items = [
                QStandardItem(row.get("name", "")),
                QStandardItem(row.get("path", "")),
                QStandardItem(human(row.get("size", 0)) if not row.get("isDir") else ""),
                QStandardItem(fmt_ms(int(row.get("modifiedMs", 0) or 0))),
            ]
            items[0].setData(row, Qt.ItemDataRole.UserRole)
            for item in items:
                item.setEditable(False)
            self.model.appendRow(items)
        self.status_label.setText(f"{len(rows)} result(s) found")
        self.cancel_btn.setEnabled(False)
        self.input.setEnabled(True)
        self.table.resizeColumnsToContents()

    def _open_result(self, idx):
        """Open one result row: navigate for folders, os.startfile for files.

        Retrieve the row dict from UserRole; closes the dialog after opening.
        """
        row = self.model.itemFromIndex(idx.sibling(idx.row(), 0))
        if row:
            data = row.data(Qt.ItemDataRole.UserRole)
            if data:
                path = data.get("path", "")
                if data.get("isDir"):
                    self.parent().navigate(path) if hasattr(self.parent(), 'navigate') else None
                else:
                    os.startfile(path)
                self.close()

    def _open_selected(self):
        """Open every currently selected result row (see :meth:`_open_result`).

        Manages open selected operations and coordinates related state changes for the component.
        """
        for idx in self.table.selectionModel().selectedRows():
            self._open_result(idx)


class GoToPathDialog(QDialog):
    """Simple dialog to navigate to a typed path (Ctrl+G).

    Only environment variables (%TEMP%, %USERPROFILE%), ~, and plain
    filesystem paths resolve: the shell-folder GUID lookup never matches
    a registry value, so shell:... entries fall through and are rejected.
    """

    _SHELL_FOLDERS = {
        "shell:recyclebinfolder": "::{645FF040-5081-101B-9F08-00AA002F954E}",
        "shell:downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
        "shell:desktop": "::{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
        "shell:mydocuments": "mydocuments",
        "shell:mypictures": "mypictures",
        "shell:mymusic": "mymusic",
        "shell:myvideo": "myvideo",
    }

    def __init__(self, current_path: str, parent=None):
        """Build the dialog with the path input pre-filled with ``current_path``.

        Initializes the instance and configures internal state.

        Args:
            current_path (str): Filesystem path to the target file or directory.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setWindowTitle("Go to Path")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setMinimumWidth(480)
        self._result_path: str = ""

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        lbl = QLabel("Type a path, environment variable, or shell folder:")
        lbl.setStyleSheet("color: #AAAAAA; font-size: 9pt;")
        lay.addWidget(lbl)

        self.path_input = QLineEdit(current_path)
        self.path_input.setPlaceholderText("e.g. %TEMP%, shell:Downloads, C:\\Users")
        self.path_input.returnPressed.connect(self._go)
        lay.addWidget(self.path_input)

        hint = QLabel("Examples: %USERPROFILE%, %TEMP%, shell:RecycleBinFolder")
        hint.setStyleSheet("color: #555555; font-size: 8pt;")
        lay.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_go = QPushButton("Go")
        self.btn_go.setObjectName("accent")
        self.btn_go.clicked.connect(self._go)
        btn_row.addWidget(self.btn_go)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

        self.path_input.setFocus()
        self.path_input.selectAll()

    def _go(self):
        """Resolve the typed text and accept the dialog if it points somewhere.

        Accepts directories directly; for files, accepts with the file's
        parent directory. On failure, highlights the input border in red.
        """
        raw = self.path_input.text().strip()
        if not raw:
            return
        resolved = self._resolve(raw)
        if resolved and os.path.isdir(resolved):
            self._result_path = resolved
            self.accept()
        elif resolved and os.path.isfile(resolved):
            self._result_path = os.path.dirname(resolved)
            self.accept()
        else:
            self.path_input.setStyleSheet(
                "border: 1px solid #EF5350; background: rgba(39,39,39,220);")

    def _resolve(self, text: str) -> str:
        """Resolve shell-folder names, env vars, and ~ into an absolute path.

        Shell folders (e.g. shell:Downloads) are looked up in the user's
        registry Shell Folders key; otherwise the text is passed through
        ``os.path.expandvars`` + ``expanduser`` + ``normpath``.
        """
        lower = text.lower().strip()
        if lower in self._SHELL_FOLDERS:
            special = self._SHELL_FOLDERS[lower]
            try:
                import winreg
                key_path = (
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer"
                    r"\Shell Folders"
                )
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    val, _ = winreg.QueryValueEx(key, special)
                    return val
            except (OSError, FileNotFoundError):
                pass
        expanded = os.path.expandvars(text)
        expanded = os.path.expanduser(expanded)
        return os.path.normpath(expanded)

    def result_path(self) -> str:
        """Return the accepted destination directory (empty if rejected).

        Manages result path operations and coordinates related state changes for the component.

        Returns:
            str: Formatted string or path.
        """
        return self._result_path


class _RenamePreviewModel(QAbstractTableModel):
    """Renamepreviewmodel.

    Manages RenamePreviewModel operations and coordinates related state changes for the component.
    """
    HEADERS = ["Original", "Renamed"]

    def __init__(self):
        """Create the model with an empty preview list.

        Initializes the instance and configures internal state.
        """
        super().__init__()
        self._data: list[tuple[str, str]] = []

    def set_data(self, data):
        """Replace the preview rows (original, renamed) with a full model reset.

        Manages set data operations and coordinates related state changes for the component.

        Args:
            data: The data parameter.
        """
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        """Rowcount.

        Manages rowCount operations and coordinates related state changes for the component.

        Args:
            parent: Parent window or shell controller instance.
        """
        return 0 if parent.isValid() else len(self._data)

    def columnCount(self, parent=QModelIndex()):
        """Columncount.

        Manages columnCount operations and coordinates related state changes for the component.

        Args:
            parent: Parent window or shell controller instance.
        """
        return 2

    def data(self, idx, role=Qt.ItemDataRole.DisplayRole):
        """Data.

        Manages data operations and coordinates related state changes for the component.

        Args:
            idx: The idx parameter.
            role: The role parameter.
        """
        if not idx.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return self._data[idx.row()][idx.column()]
        if role == Qt.ItemDataRole.ForegroundRole:
            if idx.column() == 1 and self._data[idx.row()][0] != self._data[idx.row()][1]:
                return QColor("#22d3ee")
        return None

    def headerData(self, sec, orient, role=Qt.ItemDataRole.DisplayRole):
        """Headerdata.

        Manages headerData operations and coordinates related state changes for the component.

        Args:
            sec: The sec parameter.
            orient: The orient parameter.
            role: The role parameter.
        """
        if role == Qt.ItemDataRole.DisplayRole and orient == Qt.Orientation.Horizontal:
            return self.HEADERS[sec]
        return None


# ═════════════════════════════════════════════════════════════════════════════
# Module-level QThread subclasses (MUST be here — local classes get GC'd)
# ═════════════════════════════════════════════════════════════════════════════
class _FolderSizeWorker(QThread):
    """Foldersizeworker.

    Manages FolderSizeWorker operations and coordinates related state changes for the component.
    """
    sizes_done = Signal(str, object)

    def __init__(self, path: str):
        """Store the directory path whose total size will be computed.

        Initializes the instance and configures internal state.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        super().__init__()
        self._path = path

    def run(self):
        """Walk the tree iteratively and emit sizes_done(path, total_bytes).

        Uses an explicit stack with os.scandir (symlinks not followed) so
        deep trees cannot recurse; unreadable entries are skipped. Emit
        failures during shutdown are logged, not raised.
        """
        total = 0
        stack = [self._path]
        try:
            while stack:
                current = stack.pop()
                try:
                    for entry in os.scandir(current):
                        try:
                            if entry.is_file(follow_symlinks=False):
                                total += entry.stat(follow_symlinks=False).st_size
                            elif entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
                        except (PermissionError, OSError):
                            continue
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError, ValueError):
            log.exception("folder-size worker failed for %s", self._path)
        try:
            self.sizes_done.emit(self._path, total)
        except RuntimeError:
            if not _SHUTTING_DOWN.is_set():
                log.warning("sizes_done emit failed for %s", self._path)


class _TextPreviewReader(QThread):
    """Textpreviewreader.

    Manages TextPreviewReader operations and coordinates related state changes for the component.
    """
    text_ready = Signal(str)

    def __init__(self, path: str, max_lines: int = 60):
        """Store the file path and the line cap for the preview read.

        Initializes the instance and configures internal state.

        Args:
            path (str): Filesystem path to the target file or directory.
            max_lines (int): The max lines parameter.
        """
        super().__init__()
        self._path = path
        self._max_lines = max_lines

    def run(self):
        """Read up to ``_max_lines`` lines (8MB files max) and emit them as text.

        Files larger than 8MB or with read/decode errors emit an empty
        string; decode errors are replaced rather than fatal (UTF-8 with
        errors="replace").
        """
        text = ""
        try:
            if os.path.getsize(self._path) <= 8 * 1024 * 1024:
                lines: list[str] = []
                with open(self._path, "r", encoding="utf-8",
                          errors="replace") as f:
                    while len(lines) < self._max_lines:
                        line = f.readline()
                        if not line:
                            break
                        lines.append(line)
                text = "".join(lines)
        except (OSError, UnicodeDecodeError):
            log.exception("text preview failed for %s", self._path)
            text = ""
        try:
            self.text_ready.emit(text)
        except RuntimeError:
            if not _SHUTTING_DOWN.is_set():
                log.warning("text_ready emit failed for %s", self._path)


class _ExtractArchiveWorker(QThread):
    """Extractarchiveworker.

    Manages ExtractArchiveWorker operations and coordinates related state changes for the component.
    """
    progress_update = Signal(int, str, int, int)  # percent, file, count, size
    finished_with_result = Signal(bool, str)

    def __init__(self, tasks):
        """Store the list of (archive_path, dest_dir) extraction tasks.

        Initializes the instance and configures internal state.

        Args:
            tasks: The tasks parameter.
        """
        super().__init__()
        self._tasks = tasks

    def run(self):
        """Extract each archive with 7z, parsing stdout for live progress.

        Runs ``7z x <archive> -o<dest> -aoa -mmt=on -bsp1 -bso0`` and reads
        stdout byte-by-byte, parsing percent lines into progress_update
        signals. Stops at the first failure (non-zero/one exit code) and
        emits finished_with_result(False, stderr/exception snippet);
        otherwise emits (True, "N files extracted") after all tasks.
        """
        from nexus_archive import _find_7z
        import re
        progress_re = re.compile(r"^\s*(\d+)%")
        file_count = 0

        for archive_path, dest_dir in self._tasks:
            os.makedirs(dest_dir, exist_ok=True)
            exe = _find_7z()
            if not exe:
                self.finished_with_result.emit(False, "7z.exe not found")
                return

            cmd = [exe, "x", archive_path, f"-o{dest_dir}", "-aoa", "-mmt=on", "-bsp1", "-bso0"]
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                buf = b""
                while True:
                    ch = proc.stdout.read(1)
                    if not ch:
                        break
                    if ch in (b"\r", b"\n"):
                        if buf.strip():
                            line = buf.decode("utf-8", errors="replace").strip()
                            m = progress_re.search(line)
                            if m:
                                pct = int(m.group(1))
                                fname = ""
                                parts = line.split(" - ", 1)
                                if len(parts) > 1:
                                    fname = parts[1].strip()
                                file_count += 1
                                self.progress_update.emit(pct, fname, file_count, 0)
                        buf = b""
                    else:
                        buf += ch

                proc.wait()
                success = proc.returncode in (0, 1)
                if not success:
                    err = proc.stderr.read().decode("utf-8", errors="replace").strip()
                    self.finished_with_result.emit(False, err[:200])
                    return
            except Exception as e:
                self.finished_with_result.emit(False, str(e)[:200])
                return

        self.finished_with_result.emit(True, f"{file_count} files extracted")


class _ExtractEntryWorker(QThread):
    """Extractentryworker.

    Manages ExtractEntryWorker operations and coordinates related state changes for the component.
    """
    progress_update = Signal(int, str, int, int)
    finished_with_result = Signal(bool, str)

    def __init__(self, archive_path, entries, dest_dir, password):
        """Store archive path, entry names, destination, and optional password.

        Initializes the instance and configures internal state.

        Args:
            archive_path: Filesystem path to the target file or directory.
            entries: Collection of items or entries to process.
            dest_dir: The dest dir parameter.
            password: The password parameter.
        """
        super().__init__()
        self._archive_path = archive_path
        self._entries = entries
        self._dest_dir = dest_dir
        self._password = password

    def run(self):
        """Extract each named entry with 7z, reporting overall progress.

        Spawns one 7z process per entry (with ``-p<password>`` when set) and
        combines each entry's parsed percent into an overall percent across
        all entries. Emits finished_with_result(False, ...) and stops on the
        first error; otherwise (True, "N entries extracted").
        """
        from nexus_archive import _find_7z
        import re
        progress_re = re.compile(r"^\s*(\d+)%")
        done = 0
        total = len(self._entries)

        for ep in self._entries:
            done += 1
            pct = int(done / total * 100) if total else 0
            self.progress_update.emit(pct, ep, done, 0)

            exe = _find_7z()
            if not exe:
                self.finished_with_result.emit(False, "7z.exe not found")
                return

            cmd = [exe, "x", self._archive_path, f"-o{self._dest_dir}",
                   "-aoa", "-mmt=on", "-bsp1", "-bso0", ep]
            if self._password:
                cmd.insert(1, f"-p{self._password}")

            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                buf = b""
                while True:
                    ch = proc.stdout.read(1)
                    if not ch:
                        break
                    if ch in (b"\r", b"\n"):
                        if buf.strip():
                            line = buf.decode("utf-8", errors="replace").strip()
                            m = progress_re.search(line)
                            if m:
                                p = int(m.group(1))
                                sub_pct = int((done - 1 + p / 100) / total * 100) if total else 0
                                self.progress_update.emit(sub_pct, ep, done, 0)
                        buf = b""
                    else:
                        buf += ch
                proc.wait()
            except Exception as e:
                self.finished_with_result.emit(False, str(e)[:200])
                return

        self.finished_with_result.emit(True, f"{done} entries extracted")


class _CompressWorker(QThread):
    """Compressworker.

    Manages CompressWorker operations and coordinates related state changes for the component.
    """
    progress_update = Signal(int, str, int, int)
    finished_with_result = Signal(bool, str)

    def __init__(self, cmd, name):
        """Store the fully-built 7z command line and the archive display name.

        Initializes the instance and configures internal state.

        Args:
            cmd: The cmd parameter.
            name: The name parameter.
        """
        super().__init__()
        self._cmd = cmd
        self._name = name

    def run(self):
        """Run the 7z command, parsing stdout percents into progress signals.

        Splits "pct% + filename" lines to report each added file. Emits
        finished_with_result with (True, "Created <name>") on exit codes
        0/1, else a failure message; exceptions emit (False, error text).
        """
        import re
        progress_re = re.compile(r"^\s*(\d+)%")
        try:
            proc = subprocess.Popen(self._cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            buf = b""
            count = 0
            while True:
                ch = proc.stdout.read(1)
                if not ch:
                    break
                if ch in (b"\r", b"\n"):
                    if buf.strip():
                        line = buf.decode("utf-8", errors="replace").strip()
                        m = progress_re.search(line)
                        if m:
                            pct = int(m.group(1))
                            fname = ""
                            parts = line.split(" + ", 1)
                            if len(parts) > 1:
                                fname = parts[1].strip()
                            count += 1
                            self.progress_update.emit(pct, fname, count, 0)
                    buf = b""
                else:
                    buf += ch
            proc.wait()
            ok = proc.returncode in (0, 1)
            self.finished_with_result.emit(
                ok, f"Created {self._name}" if ok else "Compression failed")
        except Exception as e:
            self.finished_with_result.emit(False, str(e)[:200])


# ═════════════════════════════════════════════════════════════════════════════
# FolderSizeCalculator — background thread for folder sizes
# ═════════════════════════════════════════════════════════════════════════════
class FolderSizeCalculator:
    """Foldersizecalculator.

    Manages FolderSizeCalculator operations and coordinates related state changes for the component.
    """

    def __init__(self):
        """Create an empty size cache and work queue; no worker thread yet.

        Initializes the instance and configures internal state.
        """
        self._cache: dict[str, int] = {}
        self._queue: deque = deque()
        self._thread = None
        self._pending = 0

    def get_size(self, path: str) -> int | None:
        """Return the cached total bytes for a path (None if unknown yet).

        Manages get size operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.

        Returns:
            int | None: Result of the operation.
        """
        return self._cache.get(path)

    def calculate(self, path: str, callback):
        """Request a folder size, invoking callback(path, size) when ready.

        Cached paths fire the callback synchronously; otherwise the request
        is queued and a _FolderSizeWorker is started if none is running.
        """
        if path in self._cache:
            callback(path, self._cache[path])
            return
        self._queue.append((path, callback))
        self._pending += 1
        if self._thread is None or not self._thread.isRunning():
            self._process_next()

    def _process_next(self):
        """Pop the next queued request and start a worker for it.

        Cached entries are answered immediately and the queue keeps
        draining; only one worker thread runs at a time.
        """
        if not self._queue:
            return
        path, cb = self._queue.popleft()
        if path in self._cache:
            cb(path, self._cache[path])
            self._process_next()
            return

        self._thread = _FolderSizeWorker(path)
        self._thread.sizes_done.connect(lambda p, s: self._on_done(p, s, cb))
        self._thread.finished.connect(self._on_thread_done)
        self._thread.start()

    def _on_done(self, path, size, callback):
        """Cache a computed size and deliver it to the waiting callback.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            path: Filesystem path to the target file or directory.
            size: Integer number of bytes to format or process.
            callback: The callback parameter.
        """
        self._cache[path] = size
        callback(path, size)

    def _on_thread_done(self):
        """Discard the finished worker thread and kick off the next queued request.

        Receives the completed data from the thread background worker, populates the view with results, and restores button states.
        """
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None
        if self._queue:
            self._process_next()

    def clear_queue(self):
        """Cancel pending calculations (e.g. on navigate away).

        Manages clear queue operations and coordinates related state changes for the component.
        """
        self._queue.clear()
        self._pending = 0

    def stop(self):
        """Stop active background operations.

        Manages worker thread execution states, signaling termination flags or initializing scheduled execution timers.
        """
        self._queue.clear()
        self._pending = 0
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)


# ═════════════════════════════════════════════════════════════════════════════
# ColorTagManager — color-coded tags for files
# ═════════════════════════════════════════════════════════════════════════════
class ColorTagManager:
    """Colortagmanager.

    Manages ColorTagManager operations and coordinates related state changes for the component.
    """

    TAG_COLORS = {
        "red": "#ef4444", "orange": "#f97316", "yellow": "#eab308",
        "green": "#22c55e", "blue": "#90CAF9", "purple": "#a855f7",
        "pink": "#ec4899",
    }

    def __init__(self):
        """Load previously saved tags from the NexusExplorer QSettings scope.

        Initializes the instance and configures internal state.
        """
        self._settings = QSettings("Nexus", "NexusExplorer")
        self._tags: dict[str, str] = {}
        saved = self._settings.value("colorTags", {})
        if saved and isinstance(saved, dict):
            self._tags = saved

    def get_tag(self, path: str) -> str | None:
        """Return the color name tagged on a path, or None.

        Manages get tag operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.

        Returns:
            str | None: Formatted string or path.
        """
        return self._tags.get(path)

    def set_tag(self, path: str, color: str | None):
        """Assign (or remove, when color is None) a tag and persist immediately.

        Manages set tag operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
            color (str | None): The color parameter.
        """
        if color:
            self._tags[path] = color
        else:
            self._tags.pop(path, None)
        self._save()

    def get_all_tags(self) -> dict[str, str]:
        """Return a copy of the path -> color-name mapping.

        Manages get all tags operations and coordinates related state changes for the component.

        Returns:
            dict[str, str]: Dictionary mapping identifiers to status or values.
        """
        return dict(self._tags)

    def _save(self):
        """Save configuration settings or analysis reports to persistent storage.

        Serializes current user preferences or generated report data to disk with integrity validation.
        """
        self._settings.setValue("colorTags", self._tags)


# ═════════════════════════════════════════════════════════════════════════════
# SmartFolderManager — saved search folders
# ═════════════════════════════════════════════════════════════════════════════
class SmartFolderManager:
    """Smartfoldermanager.

    Manages SmartFolderManager operations and coordinates related state changes for the component.
    """

    def __init__(self):
        """Load previously saved smart folders from QSettings.

        Initializes the instance and configures internal state.
        """
        self._settings = QSettings("Nexus", "NexusExplorer")
        self._folders: list[dict] = []
        saved = self._settings.value("smartFolders", [])
        if saved and isinstance(saved, list):
            self._folders = saved

    def add(self, name: str, root: str, pattern: str, ext_filter: str = ""):
        """Add.

        Manages add operations and coordinates related state changes for the component.

        Args:
            name (str): The name parameter.
            root (str): Filesystem path to the target file or directory.
            pattern (str): The pattern parameter.
            ext_filter (str): The ext filter parameter.
        """
        self._folders.append({
            "name": name, "root": root,
            "pattern": pattern, "ext": ext_filter,
        })
        self._save()

    def remove(self, index: int):
        """Remove.

        Manages remove operations and coordinates related state changes for the component.

        Args:
            index (int): The index parameter.
        """
        if 0 <= index < len(self._folders):
            self._folders.pop(index)
            self._save()

    def list_all(self) -> list[dict]:
        """Return a copy of all saved smart-folder definitions.

        Manages list all operations and coordinates related state changes for the component.

        Returns:
            list[dict]: List of processed items or identifiers.
        """
        return list(self._folders)

    def _save(self):
        """Save configuration settings or analysis reports to persistent storage.

        Serializes current user preferences or generated report data to disk with integrity validation.
        """
        self._settings.setValue("smartFolders", self._folders)


# ═════════════════════════════════════════════════════════════════════════════
# DuplicateFinderDialog — find and remove duplicate files
# ═════════════════════════════════════════════════════════════════════════════
class _DupScanWorker(QThread):
    """Dupscanworker.

    Manages DupScanWorker operations and coordinates related state changes for the component.
    """

    progress = Signal(int, str)
    scan_done = Signal(list)

    def __init__(self, root: str):
        """Store the scan root directory and mark the worker as running.

        Initializes the instance and configures internal state.

        Args:
            root (str): Filesystem path to the target file or directory.
        """
        super().__init__()
        self._root = root
        self._running = True

    def stop(self):
        """Stop active background operations.

        Manages worker thread execution states, signaling termination flags or initializing scheduled execution timers.
        """
        self._running = False

    def run(self):
        """Run the scan and emit scan_done with the duplicate groups.

        Failures log an exception and emit whatever groups (if any) were
        collected; emit RuntimeErrors during shutdown are swallowed.
    """
        groups: list = []
        try:
            groups = self._scan()
        except (OSError, PermissionError, ValueError):
            log.exception("duplicate scan failed for %s", self._root)
        try:
            self.scan_done.emit(groups)
        except RuntimeError:
            if not _SHUTTING_DOWN.is_set():
                log.warning("scan_done emit failed for %s", self._root)

    def _scan(self) -> list:
        """Find duplicate files: size pre-filter, then MD5 hashing.

        Returns a list of groups (lists of file dicts sharing one hash),
        sorted by recoverable size (total minus the oldest file in each
        group) descending. Emits progress(percent, filename) while
        hashing. Returns None if stopped mid-scan; empty files are skipped
        and unreadable entries ignored.
        """
        size_map: dict[int, list[dict]] = {}
        file_count = 0

        root = Path(self._root)
        for dirpath, _, filenames in os.walk(root):
            if not self._running:
                return
            for fname in filenames:
                if not self._running:
                    return
                fpath = Path(dirpath) / fname
                try:
                    st = fpath.stat()
                    sz = st.st_size
                    if sz == 0:
                        continue
                    size_map.setdefault(sz, []).append({
                        "name": fname,
                        "size": sz,
                        "path": str(fpath),
                        "mtime": st.st_mtime,
                    })
                    file_count += 1
                except (OSError, PermissionError):
                    continue

        candidates = {s: fl for s, fl in size_map.items() if len(fl) > 1}
        total_to_hash = sum(len(fl) for fl in candidates.values())
        hash_map: dict[str, list[dict]] = {}
        hashed = 0

        for _, fl in candidates.items():
            if not self._running:
                return
            for fi in fl:
                if not self._running:
                    return
                try:
                    h = hashlib.md5()
                    with open(fi["path"], "rb") as fh:
                        while chunk := fh.read(65536):
                            h.update(chunk)
                    fi["hash"] = h.hexdigest()
                    hash_map.setdefault(fi["hash"], []).append(fi)
                except (OSError, PermissionError):
                    continue
                hashed += 1
                if total_to_hash > 0:
                    pct = int(hashed * 100 / total_to_hash)
                    self.progress.emit(pct, fi["name"])

        groups = [g for g in hash_map.values() if len(g) > 1]
        groups.sort(key=lambda g: sum(f["size"] for f in g[1:]), reverse=True)
        return groups


class _DuplicateModel(QAbstractTableModel):
    """Duplicatemodel.

    Manages DuplicateModel operations and coordinates related state changes for the component.
    """

    HEADERS = ["", "Filename", "Size", "Path"]

    def __init__(self):
        """Create the model with no result rows yet.

        Initializes the instance and configures internal state.
        """
        super().__init__()
        self._rows: list[dict] = []

    def set_groups(self, groups: list[list[dict]]):
        """Load duplicate groups as flat, checkable rows (model reset).

        Within each group files are sorted oldest-first so the first row
        is the "original" candidate for auto-select.
        """
        self.beginResetModel()
        self._rows = []
        for gi, group in enumerate(groups):
            if len(group) < 2:
                continue
            for fi in sorted(group, key=lambda f: f["mtime"]):
                self._rows.append({
                    "group": gi,
                    "name": fi["name"],
                    "size": fi["size"],
                    "path": fi["path"],
                    "hash": fi["hash"],
                    "mtime": fi["mtime"],
                    "selected": False,
                })
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        """Rowcount.

        Manages rowCount operations and coordinates related state changes for the component.

        Args:
            parent: Parent window or shell controller instance.
        """
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        """Columncount.

        Manages columnCount operations and coordinates related state changes for the component.

        Args:
            parent: Parent window or shell controller instance.
        """
        return 4

    def data(self, idx, role=Qt.ItemDataRole.DisplayRole):
        """Provide per-cell data for all table roles.

        Renders 30px rows, alternating group background colors, red text
        for selected rows, a checkbox in column 0, filename/size/path text,
        and a hash+path tooltip.
        """
        row = self._rows[idx.row()]
        col = idx.column()

        if role == Qt.ItemDataRole.SizeHintRole:
            return QSize(0, 30)

        if role == Qt.ItemDataRole.BackgroundRole:
            return QColor("#181818") if row["group"] % 2 == 0 else QColor("#121212")

        if role == Qt.ItemDataRole.ForegroundRole and row["selected"]:
            return QColor("#ef4444")

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return ""
            if col == 1:
                return row["name"]
            if col == 2:
                return human(row["size"])
            if col == 3:
                return row["path"]

        if role == Qt.ItemDataRole.CheckStateRole and col == 0:
            return (Qt.CheckState.Checked if row["selected"]
                    else Qt.CheckState.Unchecked)

        if role == Qt.ItemDataRole.ToolTipRole:
            return f"Hash: {row['hash']}\n{row['path']}"

        return None

    def headerData(self, sec, orient, role=Qt.ItemDataRole.DisplayRole):
        """Headerdata.

        Manages headerData operations and coordinates related state changes for the component.

        Args:
            sec: The sec parameter.
            orient: The orient parameter.
            role: The role parameter.
        """
        if (role == Qt.ItemDataRole.DisplayRole
                and orient == Qt.Orientation.Horizontal):
            return self.HEADERS[sec]
        return None

    def flags(self, idx):
        """Flags.

        Manages flags operations and coordinates related state changes for the component.

        Args:
            idx: The idx parameter.
        """
        if idx.column() == 0:
            return (Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsUserCheckable)
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def toggle_selected(self, idx):
        """Flip one row's deletion checkbox and notify check-state changed.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.

        Args:
            idx: The idx parameter.
        """
        row = self._rows[idx.row()]
        row["selected"] = not row["selected"]
        self.dataChanged.emit(
            idx, idx,
            [Qt.ItemDataRole.CheckStateRole, Qt.ItemDataRole.ForegroundRole],
        )

    def auto_select_duplicates(self):
        """Check every duplicate except the oldest file in each group.

        Relies on set_groups having sorted each group oldest-first, so the
        first row per group is kept. Notifies a full-model data change.
        """
        groups: dict[int, list[dict]] = {}
        for row in self._rows:
            groups.setdefault(row["group"], []).append(row)
        for rows in groups.values():
            if len(rows) < 2:
                continue
            oldest = min(rows, key=lambda r: r.get("mtime", 0))
            for row in rows:
                row["selected"] = row is not oldest
        if self._rows:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._rows) - 1, self.columnCount() - 1),
                [Qt.ItemDataRole.CheckStateRole, Qt.ItemDataRole.ForegroundRole],
            )

    def get_selected_rows(self) -> list[dict]:
        """Return the row dicts currently checked for deletion.

        Manages get selected rows operations and coordinates related state changes for the component.

        Returns:
            list[dict]: List of processed items or identifiers.
        """
        return [r for r in self._rows if r["selected"]]

    def total_recoverable(self) -> int:
        """Return total bytes across all checked rows.

        Manages total recoverable operations and coordinates related state changes for the component.

        Returns:
            int: Result of the operation.
        """
        return sum(r["size"] for r in self._rows if r["selected"])


class DuplicateFinderDialog(QDialog):
    """Duplicatefinderdialog.

    Manages DuplicateFinderDialog operations and coordinates related state changes for the component.
    """

    def __init__(self, initial_path: str = "", parent=None):
        """Build the dialog: directory picker, progress bar, results table.

        Args:
            initial_path: directory pre-filled into the scan input.
        """
        super().__init__(parent)
        self.setObjectName("DuplicateFinder")
        self.setWindowTitle("Duplicate Finder")
        self.setMinimumSize(780, 540)
        self._thread: _DupScanWorker | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        # ── directory picker ──
        drow = QHBoxLayout()
        drow.setSpacing(6)
        self.dir_input = QLineEdit(initial_path)
        self.dir_input.setPlaceholderText("Select directory to scan\u2026")
        drow.addWidget(self.dir_input, 1)
        btn_browse = QPushButton("Browse\u2026")
        btn_browse.setIcon(_fluent_action("folder", size=16))
        btn_browse.setFixedWidth(80)
        btn_browse.clicked.connect(self._browse)
        drow.addWidget(btn_browse)
        lay.addLayout(drow)

        # ── progress ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Ready")
        lay.addWidget(self.progress_bar)

        self.status_label = QLabel(
            "Select a directory and click Scan to find duplicates.")
        self.status_label.setObjectName("DupStatusLabel")
        lay.addWidget(self.status_label)

        # ── table ──
        self.table = QTableView()
        self._model = _DuplicateModel()
        self.table.setModel(self._model)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(
            QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QTableView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setShowGrid(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.resizeSection(0, 32)
        hh.resizeSection(2, 90)
        self.table.clicked.connect(self._on_click)
        lay.addWidget(self.table, 1)

        # ── bottom bar ──
        brow = QHBoxLayout()
        self.space_label = QLabel("")
        self.space_label.setObjectName("DupSpaceLabel")
        brow.addWidget(self.space_label)
        brow.addStretch(1)

        self.btn_scan = QPushButton("Scan")
        self.btn_scan.setIcon(_fluent_action("search", size=16))
        self.btn_scan.setObjectName("accent")
        self.btn_scan.clicked.connect(self._start_scan)
        brow.addWidget(self.btn_scan)

        self.btn_select = QPushButton("Select Duplicates")
        self.btn_select.setIcon(_fluent_action("check", size=16))
        self.btn_select.setEnabled(False)
        self.btn_select.clicked.connect(self._auto_select)
        brow.addWidget(self.btn_select)

        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.setIcon(_fluent_action("delete", size=16))
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._delete_selected)
        brow.addWidget(self.btn_delete)

        lay.addLayout(brow)

    def set_directory(self, path: str):
        """Pre-fill the scan directory input.

        Manages set directory operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        self.dir_input.setText(path)

    def _browse(self):
        """Prompt the user to select a filesystem directory or file.

        Launches a native file dialog and populates the selected path into the corresponding target input widget.
        """
        d = QFileDialog.getExistingDirectory(
            self, "Scan for duplicates", self.dir_input.text())
        if d:
            self.dir_input.setText(d)

    def _start_scan(self):
        """Validate the directory and launch a _DupScanWorker.

        Disables all action buttons and resets the progress bar/table for
        the run. Any previous worker is stopped and awaited (up to 2s)
        first. Invalid paths only update the status label.
        """
        path = self.dir_input.text().strip()
        if not path or not os.path.isdir(path):
            self.status_label.setText("Please select a valid directory.")
            return
        if self._thread and self._thread.isRunning():
            self._thread.stop()
            self._thread.wait(2000)

        self.btn_scan.setEnabled(False)
        self.btn_select.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.space_label.setText("")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Scanning\u2026")
        self.status_label.setText("Building file index\u2026")
        self._model.set_groups([])

        self._thread = _DupScanWorker(path)
        self._thread.progress.connect(self._on_progress)
        self._thread.scan_done.connect(self._on_done)
        self._thread.start()

    def _on_progress(self, pct: int, name: str):
        """Mirror worker hashing progress into the bar and status label.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            pct (int): The pct parameter.
            name (str): The name parameter.
        """
        self.progress_bar.setValue(pct)
        self.progress_bar.setFormat(f"Hashing\u2026 {pct}%")
        self.status_label.setText(f"Hashing: {name}")

    def _on_done(self, groups: list):
        """Handle scan completion: summarize results and populate the table.

        Reports group count, total duplicate files, and recoverable bytes
        (all but the first file of each group); enables Select/Delete only
        when duplicates were found.
        """
        self.btn_scan.setEnabled(True)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Done")

        n_files = sum(len(g) for g in groups)
        n_groups = len(groups)
        rec = sum(sum(f["size"] for f in g[1:]) for g in groups)

        if n_groups == 0:
            self.status_label.setText("No duplicates found.")
        else:
            self.status_label.setText(
                f"Found {n_groups} duplicate group(s), "
                f"{n_files} files, {human(rec)} recoverable.")

        self._model.set_groups(groups)
        self.btn_select.setEnabled(n_groups > 0)
        self._update_space()

    def _auto_select(self):
        """Check all duplicates (keeping the oldest of each group) via the model.

        Manages auto select operations and coordinates related state changes for the component.
        """
        self._model.auto_select_duplicates()
        self._update_space()

    def _update_space(self):
        """Refresh the recoverable-space label and the Delete button's enabled state.

        Manages update space operations and coordinates related state changes for the component.
        """
        rec = self._model.total_recoverable()
        self.space_label.setText(f"{human(rec)} recoverable" if rec else "")
        self.btn_delete.setEnabled(rec > 0)

    def _on_click(self, idx):
        """Toggle a row's checkbox when column 0 is clicked.

        Manages on click operations and coordinates related state changes for the component.

        Args:
            idx: The idx parameter.
        """
        if idx.column() == 0:
            self._model.toggle_selected(idx)
            self._update_space()

    def _delete_selected(self):
        """Permanently delete all checked duplicates, then rescan.

        Asks for confirmation first; individual os.remove failures are
        silently skipped, and the reported count reflects actual deletions.
        """
        rows = self._model.get_selected_rows()
        if not rows:
            return
        paths = [r["path"] for r in rows]
        r = QMessageBox.question(
            self, "Delete duplicates",
            f"Permanently delete {len(paths)} duplicate file(s)?\n"
            "This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if r != QMessageBox.StandardButton.Yes:
            return
        deleted = 0
        for p in paths:
            try:
                os.remove(p)
                deleted += 1
            except OSError:
                pass
        self.status_label.setText(
            f"Deleted {deleted} file(s). Re-scanning\u2026")
        self._start_scan()

    def closeEvent(self, ev):
        """Handle the window or widget close event.

        Performs graceful shutdown, releases active workers and system hooks, persists window geometry, and accepts the close event.

        Args:
            ev: The Qt event object.
        """
        if self._thread and self._thread.isRunning():
            self._thread.stop()
            self._thread.wait(2000)
        super().closeEvent(ev)


# ═════════════════════════════════════════════════════════════════════════════
# NexusClipboard — shared clipboard with MIME data & live update signals
# ═════════════════════════════════════════════════════════════════════════════
class NexusClipboard(QObject):
    """Nexusclipboard.

    Manages NexusClipboard operations and coordinates related state changes for the component.
    """

    changed = Signal(str, list)  # (mode, [paths])

    MODE_CUT = "cut"
    MODE_COPY = "copy"

    def __init__(self, parent=None):
        """Initialize empty clipboard state and a 150ms debounce timer.

        Also hooks the system clipboard's dataChanged signal (lazily, on
        first successful QApplication access) for two-way sync.
        """
        super().__init__(parent)
        self._mode: str | None = None
        self._paths: list[str] = []
        self._syncing: bool = False
        self._connected: bool = False
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(150)
        self._debounce_timer.timeout.connect(self._do_external_change)
        self._get_clipboard()

    def _get_clipboard(self):
        """Return the system clipboard, connecting dataChanged once.

        Returns None (never raises) if QApplication is unavailable; the
        dataChanged hook is only connected the first time.
        """
        try:
            app = QApplication.instance()
            if app is None:
                return None
            clip = QApplication.clipboard()
            if clip is not None and not self._connected:
                clip.dataChanged.connect(self._on_data_changed)
                self._connected = True
            return clip
        except Exception:
            return None

    def cut(self, paths: list[str]):
        """Cut.

        Manages cut operations and coordinates related state changes for the component.

        Args:
            paths (list[str]): Filesystem path to the target file or directory.
        """
        self._mode = self.MODE_CUT
        self._paths = list(paths)
        self._sync_to_system_clipboard()
        self.changed.emit(self._mode, list(self._paths))

    def copy(self, paths: list[str]):
        """Copy.

        Manages copy operations and coordinates related state changes for the component.

        Args:
            paths (list[str]): Filesystem path to the target file or directory.
        """
        self._mode = self.MODE_COPY
        self._paths = list(paths)
        self._sync_to_system_clipboard()
        self.changed.emit(self._mode, list(self._paths))

    def paste(self) -> tuple[str, list[str]] | None:
        """Paste.

        Manages paste operations and coordinates related state changes for the component.

        Returns:
            tuple[str, list[str]] | None: List of processed items or identifiers.
        """
        if not self._mode or not self._paths:
            return None
        return (self._mode, list(self._paths))

    def clear(self):
        """Clear.

        Manages clear operations and coordinates related state changes for the component.
        """
        self._mode = None
        self._paths = []
        self.changed.emit("", [])

    @property
    def has_data(self) -> bool:
        """Return True when a mode and at least one path are set.

        Manages has data operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return bool(self._mode and self._paths)

    def _sync_to_system_clipboard(self):
        """Mirror the current cut/copy set into the system clipboard.

        Guards against feedback loops with ``_syncing`` and is skipped when
        no QApplication exists.
        """
        if self._syncing:
            return
        self._syncing = True
        try:
            clip = self._get_clipboard()
            if clip is not None:
                mime = QMimeData()
                urls = [QUrl.fromLocalFile(p) for p in self._paths if os.path.exists(p)]
                mime.setUrls(urls)
                mime.setText("\n".join(self._paths))
                clip.setMimeData(mime)
        except Exception:
            pass
        finally:
            self._syncing = False

    def _on_data_changed(self):
        """Debounce system-clipboard changes (150ms) before importing them.

        Manages on data changed operations and coordinates related state changes for the component.
        """
        if self._syncing:
            return
        self._debounce_timer.start()

    def _do_external_change(self):
        """Import an externally-copied file set from the system clipboard.

        Accepts URL lists directly, or newline-separated text whose lines
        are existing paths. Imported data always becomes MODE_COPY and
        emits changed() only when the path list actually differs.
        """
        if self._syncing:
            return
        try:
            clip = self._get_clipboard()
            if clip is None:
                return
            mime = clip.mimeData()
            if mime is None:
                return
            if mime.hasUrls():
                new_paths = [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]
                if new_paths and new_paths != self._paths:
                    self._paths = new_paths
                    self._mode = self.MODE_COPY
                    self.changed.emit(self._mode, list(self._paths))
            elif mime.hasText():
                text = mime.text().strip()
                if text:
                    new_paths = [p for p in text.splitlines() if os.path.exists(p.strip())]
                    if new_paths and new_paths != self._paths:
                        self._paths = new_paths
                        self._mode = self.MODE_COPY
                        self.changed.emit(self._mode, list(self._paths))
        except Exception:
            pass


# Singleton shared clipboard
_nexus_clipboard = NexusClipboard()


# ═════════════════════════════════════════════════════════════════════════════
# StagingShelfWidget — Interactive Drop Shelf & Clipboard Dock
# ═════════════════════════════════════════════════════════════════════════════
class StagedItemRow(QWidget):
    """Stageditemrow.

    Manages StagedItemRow operations and coordinates related state changes for the component.
    """

    remove_clicked = Signal(str)

    def __init__(self, path: str, icons: IconThumbs | None = None, parent=None):
        """Build a 30px staged row: icon, filename, size, and remove button.

        Initializes the instance and configures internal state.

        Args:
            path (str): Filesystem path to the target file or directory.
            icons (IconThumbs | None): The icons parameter.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.path = path
        self.setFixedHeight(30)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._drag_start_pos = None
        p = Path(path)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 2, 8, 2)
        lay.setSpacing(8)

        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(18, 18)
        self.icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        is_dir = p.is_dir() if p.exists() else False
        try:
            ico = None
            if icons is not None:
                if is_dir and hasattr(icons, "dir_icon"):
                    ico = icons.dir_icon(p.name)
                elif not is_dir and hasattr(icons, "ext_icon"):
                    ico = icons.ext_icon(p.suffix)
            if ico is None or ico.isNull():
                ico = _fluent_action("folder" if is_dir else "file", size=16)
            if ico is not None and not ico.isNull():
                self.icon_lbl.setPixmap(ico.pixmap(18, 18))
        except Exception:
            pass

        # Clear, bright, highly legible text
        self.name_lbl = QLabel(p.name or path)
        self.name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.name_lbl.setStyleSheet(
            "color: #FFFFFF; font-size: 8.5pt; font-weight: 600; background: transparent;"
        )
        self.name_lbl.setToolTip(f"{path}\nType: {'Folder' if is_dir else 'File'}")

        size_text = human(p.stat().st_size) if p.is_file() and p.exists() else ("Folder" if is_dir else "")
        self.size_lbl = QLabel(size_text)
        self.size_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.size_lbl.setStyleSheet(
            "color: #94A3B8; font-size: 7.5pt; font-weight: 500; background: transparent;"
        )

        self.btn_del = QToolButton()
        self.btn_del.setText("✕")
        self.btn_del.setFixedSize(18, 18)
        self.btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del.setToolTip("Remove from shelf")
        self.btn_del.setStyleSheet(
            "QToolButton { color: #94A3B8; background: transparent; border: none; font-size: 8.5pt; font-weight: bold; border-radius: 3px; }"
            "QToolButton:hover { color: #EF4444; background: rgba(239, 68, 68, 0.2); }"
        )
        self.btn_del.clicked.connect(lambda: self.remove_clicked.emit(self.path))

        lay.addWidget(self.icon_lbl)
        lay.addWidget(self.name_lbl, 1)
        lay.addWidget(self.size_lbl)
        lay.addWidget(self.btn_del)

    def mousePressEvent(self, ev):
        """Handle mouse mousePress interaction events.

        Tracks cursor coordinates, button states, drag-and-drop actions, or item selection changes within the widget.

        Args:
            ev: The Qt event object.
        """
        if ev.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = ev.pos()
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        """Handle mouse mouseMove interaction events.

        Tracks cursor coordinates, button states, drag-and-drop actions, or item selection changes within the widget.

        Args:
            ev: The Qt event object.
        """
        if not (ev.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_start_pos is not None:
            dist = (ev.pos() - self._drag_start_pos).manhattanLength()
            if dist < QApplication.startDragDistance():
                return
        if os.path.exists(self.path):
            drag = QDrag(self)
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(self.path)])
            mime.setText(self.path)
            drag.setMimeData(mime)
            try:
                pix = self.grab()
                drag.setPixmap(pix)
                drag.setHotSpot(ev.pos())
            except Exception:
                pass
            drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)


class StagingListWidget(QListWidget):
    """Staginglistwidget.

    Manages StagingListWidget operations and coordinates related state changes for the component.
    """

    def __init__(self, shelf, parent=None):
        """Create the drag-enabled staged-files list bound to its shelf.

        Initializes the instance and configures internal state.

        Args:
            shelf: The shelf parameter.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.shelf = shelf
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self._drag_start_pos = None

    def mousePressEvent(self, ev):
        """Handle mouse mousePress interaction events.

        Tracks cursor coordinates, button states, drag-and-drop actions, or item selection changes within the widget.

        Args:
            ev: The Qt event object.
        """
        if ev.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = ev.pos()
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        """Handle mouse mouseMove interaction events.

        Tracks cursor coordinates, button states, drag-and-drop actions, or item selection changes within the widget.

        Args:
            ev: The Qt event object.
        """
        if not (ev.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_start_pos is not None:
            dist = (ev.pos() - self._drag_start_pos).manhattanLength()
            if dist < QApplication.startDragDistance():
                return
        item = self.itemAt(self._drag_start_pos or ev.pos())
        paths = []
        if item is not None:
            row_widget = self.itemWidget(item)
            if row_widget and hasattr(row_widget, "path"):
                paths = [row_widget.path]
        if not paths and hasattr(self.shelf, "_staged_paths"):
            paths = list(self.shelf._staged_paths)
        valid_paths = [p for p in paths if os.path.exists(p)]
        if valid_paths:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(p) for p in valid_paths])
            mime.setText("\n".join(valid_paths))
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)


class StagingShelfWidget(QFrame):
    """Spacious, interactive Drop Shelf & Clipboard Dock.

    Occupies the lower half of the Preview Window:
    - Active Drag & Drop target for multi-source file accumulation
    - Draggable items: drag items OUT of the shelf to any destination
    - Live synchronization with NexusClipboard (Ctrl+C / Ctrl+X)
    - Persistent across folder navigation with dynamic destination targeting
    - One-click '⚡ Paste Here' / '⚡ Move Here' batch transfers
    - Mode toggle between COPY and MOVE
    """

    paste_requested = Signal(str, list, str)  # (mode, paths, dest_dir)
    staging_changed = Signal(list, str)       # (paths, mode)
    add_selected_requested = Signal()

    def __init__(self, icons: IconThumbs | None = None, parent=None):
        """Build the staging shelf: header, staged list, empty card, paste button.

        Initializes the instance and configures internal state.

        Args:
            icons (IconThumbs | None): The icons parameter.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setObjectName("StagingShelf")
        self.setAcceptDrops(True)
        self._icons = icons or IconThumbs()
        self._mode: str = "copy"
        self._staged_paths: list[str] = []
        self._current_dir: str = ""
        self._is_drag_over: bool = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        # 1. Header Bar
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        self.mode_btn = QPushButton("COPY")
        self.mode_btn.setToolTip("Click to toggle between COPY and MOVE")
        self.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_btn.setFixedHeight(22)
        self.mode_btn.setStyleSheet(
            "QPushButton { background: #0284c7; color: #ffffff; font-size: 7.5pt; font-weight: 700; "
            "border-radius: 4px; padding: 2px 8px; border: none; }"
            "QPushButton:hover { background: #0369a1; }"
        )
        self.mode_btn.clicked.connect(self._toggle_mode)

        self.title_lbl = QLabel("Staging Shelf")
        self.title_lbl.setStyleSheet("color: #F8FAFC; font-size: 9pt; font-weight: 700;")

        self.count_lbl = QLabel("(0)")
        self.count_lbl.setStyleSheet("color: #38BDF8; font-size: 8pt; font-weight: 600;")

        self.btn_add_sel = QToolButton()
        self.btn_add_sel.setText("➕")
        self.btn_add_sel.setToolTip("Stage selected files from table")
        self.btn_add_sel.setFixedSize(22, 22)
        self.btn_add_sel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_sel.setStyleSheet(
            "QToolButton { color: #94A3B8; background: transparent; border: none; font-size: 8.5pt; border-radius: 3px; }"
            "QToolButton:hover { color: #38BDF8; background: rgba(56, 189, 248, 0.15); }"
        )
        self.btn_add_sel.clicked.connect(self.add_selected_requested.emit)

        self.btn_clear = QToolButton()
        self.btn_clear.setText("🧹")
        self.btn_clear.setToolTip("Clear all staged files")
        self.btn_clear.setFixedSize(22, 22)
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setStyleSheet(
            "QToolButton { color: #94A3B8; background: transparent; border: none; font-size: 9pt; border-radius: 3px; }"
            "QToolButton:hover { color: #F1F5F9; background: rgba(255, 255, 255, 0.1); }"
        )
        self.btn_clear.clicked.connect(self.clear_staged)

        header.addWidget(self.mode_btn)
        header.addWidget(self.title_lbl)
        header.addWidget(self.count_lbl)
        header.addStretch(1)
        header.addWidget(self.btn_add_sel)
        header.addWidget(self.btn_clear)
        lay.addLayout(header)

        # 2. Middle Items List / Empty Card Stack
        self.list_widget = StagingListWidget(self)
        self.list_widget.setObjectName("StagingList")
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setMinimumHeight(150)
        self.list_widget.setMaximumHeight(260)
        self.list_widget.setStyleSheet(
            "QListWidget#StagingList { background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 255, 255, 0.1); "
            "border-radius: 6px; padding: 2px; } "
            "QListWidget#StagingList::item { background: transparent; border-bottom: 1px solid rgba(255, 255, 255, 0.04); }"
            "QListWidget#StagingList::item:hover { background: rgba(56, 189, 248, 0.08); border-radius: 4px; }"
        )

        # Spacious, informative empty card
        self.empty_card = QFrame()
        self.empty_card.setObjectName("EmptyDropCard")
        self.empty_card.setMinimumHeight(140)
        self.empty_card.setStyleSheet(
            "QFrame#EmptyDropCard { background: rgba(15, 23, 42, 0.45); border: 2px dashed rgba(56, 189, 248, 0.35); "
            "border-radius: 8px; padding: 12px; } "
            "QFrame#EmptyDropCard:hover { border-color: rgba(56, 189, 248, 0.7); background: rgba(14, 40, 65, 0.5); }"
        )
        card_lay = QVBoxLayout(self.empty_card)
        card_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_lay.setSpacing(4)

        icon_lbl = QLabel("📥")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 20pt; color: #38bdf8; background: transparent;")

        title_lbl = QLabel("Drag & Drop Files Here")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet("color: #E2E8F0; font-size: 8.5pt; font-weight: 700; background: transparent;")

        sub_lbl = QLabel("Drop files from table or press Ctrl+C to stage across folders")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 7.5pt; background: transparent;")

        card_lay.addWidget(icon_lbl)
        card_lay.addWidget(title_lbl)
        card_lay.addWidget(sub_lbl)

        self.stack_layout = QVBoxLayout()
        self.stack_layout.setContentsMargins(0, 0, 0, 0)
        self.stack_layout.addWidget(self.list_widget)
        self.stack_layout.addWidget(self.empty_card)
        lay.addLayout(self.stack_layout)

        # 3. Dynamic Paste Button
        self.btn_paste = QPushButton("⚡ Paste Here")
        self.btn_paste.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_paste.setFixedHeight(34)
        self.btn_paste.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #0369a1); "
            "color: #FFFFFF; font-weight: 700; font-size: 8.5pt; border-radius: 6px; border: none; padding: 4px 12px; } "
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #0284c7); } "
            "QPushButton:disabled { background: rgba(255, 255, 255, 0.05); color: #475569; }"
        )
        self.btn_paste.clicked.connect(self._on_paste_clicked)
        self.btn_paste.setEnabled(False)
        lay.addWidget(self.btn_paste)

        self._update_style()
        self._update_ui_state()

        # Connect to clipboard singleton
        _nexus_clipboard.changed.connect(self.set_staged)

    def _update_style(self):
        """Swap the shelf frame style to highlight an active drag-over.

        Manages update style operations and coordinates related state changes for the component.
        """
        if self._is_drag_over:
            self.setStyleSheet(
                "QFrame#StagingShelf { background: rgba(14, 40, 65, 0.95); border: 2px dashed #38bdf8; border-radius: 8px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame#StagingShelf { background: rgba(24, 24, 28, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; }"
            )

    def _update_ui_state(self):
        """Refresh count label, list/empty-card visibility, and paste/mode buttons.

        Manages update ui state operations and coordinates related state changes for the component.
        """
        count = len(self._staged_paths)
        self.count_lbl.setText(f"({count})")
        has_items = count > 0

        self.list_widget.setVisible(has_items)
        self.empty_card.setVisible(not has_items)
        self.btn_paste.setEnabled(has_items)

        # Update mode button appearance
        if self._mode == "cut":
            self.mode_btn.setText("MOVE")
            self.mode_btn.setStyleSheet(
                "QPushButton { background: #d97706; color: #ffffff; font-size: 7.5pt; font-weight: 700; "
                "border-radius: 4px; padding: 2px 8px; border: none; }"
                "QPushButton:hover { background: #b45309; }"
            )
        else:
            self.mode_btn.setText("COPY")
            self.mode_btn.setStyleSheet(
                "QPushButton { background: #0284c7; color: #ffffff; font-size: 7.5pt; font-weight: 700; "
                "border-radius: 4px; padding: 2px 8px; border: none; }"
                "QPushButton:hover { background: #0369a1; }"
            )

        # Update paste button text
        dest_name = Path(self._current_dir).name or self._current_dir
        if not dest_name:
            dest_name = "Current Folder"
        action_word = "Move" if self._mode == "cut" else "Paste"
        if has_items:
            self.btn_paste.setText(f"⚡ {action_word} {count} item{'s' if count != 1 else ''} to: {dest_name}")
        else:
            self.btn_paste.setText(f"⚡ {action_word} Here")

    def _norm(self, p: str) -> str:
        """Norm.

        Manages norm operations and coordinates related state changes for the component.

        Args:
            p (str): The p parameter.

        Returns:
            str: Formatted string or path.
        """
        return os.path.normpath(str(p)).replace("\\", "/")

    def set_current_folder(self, path: str):
        """Update active destination directory for the staging shelf.

        Manages set current folder operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        self._current_dir = str(path)
        self._update_ui_state()

    def set_staged(self, mode: str, paths: list[str]):
        """Set staged paths from clipboard or external event.

        Manages set staged operations and coordinates related state changes for the component.

        Args:
            mode (str): The mode parameter.
            paths (list[str]): Filesystem path to the target file or directory.
        """
        self._mode = "cut" if mode == "cut" else "copy"
        # Deduplicate & filter
        seen = set()
        clean = []
        for p in paths:
            if p:
                np = self._norm(p)
                if np not in seen:
                    seen.add(np)
                    clean.append(np)
        self._staged_paths = clean
        self._rebuild_list()
        self._update_ui_state()
        self.staging_changed.emit(list(self._staged_paths), self._mode)

    def add_paths(self, paths: list[str], mode: str | None = None):
        """Accumulate new paths into the staging shelf.

        Manages add paths operations and coordinates related state changes for the component.

        Args:
            paths (list[str]): Filesystem path to the target file or directory.
            mode (str | None): The mode parameter.
        """
        if mode:
            self._mode = "cut" if mode == "cut" else "copy"
        existing = set(self._staged_paths)
        for p in paths:
            if p:
                np = self._norm(p)
                if np not in existing:
                    self._staged_paths.append(np)
                    existing.add(np)
        self._rebuild_list()
        self._update_ui_state()
        # Keep clipboard in sync
        if self._mode == "cut":
            _nexus_clipboard.cut(self._staged_paths)
        else:
            _nexus_clipboard.copy(self._staged_paths)
        self.staging_changed.emit(list(self._staged_paths), self._mode)

    def remove_path(self, path: str):
        """Remove an individual path from staging.

        Manages remove path operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        target = self._norm(path)
        self._staged_paths = [p for p in self._staged_paths if p != target]
        self._rebuild_list()
        self._update_ui_state()
        if self._staged_paths:
            if self._mode == "cut":
                _nexus_clipboard.cut(self._staged_paths)
            else:
                _nexus_clipboard.copy(self._staged_paths)
        else:
            _nexus_clipboard.clear()
        self.staging_changed.emit(list(self._staged_paths), self._mode)

    def clear_staged(self):
        """Clear all staged items.

        Manages clear staged operations and coordinates related state changes for the component.
        """
        self._staged_paths = []
        self._rebuild_list()
        self._update_ui_state()
        _nexus_clipboard.clear()
        self.staging_changed.emit([], self._mode)

    def _toggle_mode(self):
        """Flip the shelf between copy and move, syncing the clipboard.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        self._mode = "copy" if self._mode == "cut" else "cut"
        if self._staged_paths:
            if self._mode == "cut":
                _nexus_clipboard.cut(self._staged_paths)
            else:
                _nexus_clipboard.copy(self._staged_paths)
        self._update_ui_state()
        self.staging_changed.emit(list(self._staged_paths), self._mode)

    def _rebuild_list(self):
        """Rebuild staged rows from _staged_paths, wiring remove buttons.

        Manages rebuild list operations and coordinates related state changes for the component.
        """
        self.list_widget.clear()
        for path in self._staged_paths:
            row = StagedItemRow(path, self._icons)
            row.remove_clicked.connect(self.remove_path)
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(row.sizeHint())
            self.list_widget.setItemWidget(item, row)

    def _on_paste_clicked(self):
        """Emit paste_requested for the staged paths in the current mode.

        Manages on paste clicked operations and coordinates related state changes for the component.
        """
        if self._staged_paths:
            self.paste_requested.emit(self._mode, list(self._staged_paths), self._current_dir)

    # ── Drag & Drop Events ──────────────────────────────────────────
    def dragEnterEvent(self, ev: QDragEnterEvent):
        """Dragenterevent.

        Manages dragEnterEvent operations and coordinates related state changes for the component.

        Args:
            ev (QDragEnterEvent): The Qt event object.
        """
        if ev.mimeData().hasUrls() or ev.mimeData().hasText():
            ev.acceptProposedAction()
            self._is_drag_over = True
            self._update_style()
        else:
            ev.ignore()

    def dragMoveEvent(self, ev: QDragMoveEvent):
        """Dragmoveevent.

        Manages dragMoveEvent operations and coordinates related state changes for the component.

        Args:
            ev (QDragMoveEvent): The Qt event object.
        """
        if ev.mimeData().hasUrls() or ev.mimeData().hasText():
            ev.acceptProposedAction()
        else:
            ev.ignore()

    def dragLeaveEvent(self, ev):
        """Dragleaveevent.

        Manages dragLeaveEvent operations and coordinates related state changes for the component.

        Args:
            ev: The Qt event object.
        """
        self._is_drag_over = False
        self._update_style()

    def dropEvent(self, ev):
        """Dropevent.

        Manages dropEvent operations and coordinates related state changes for the component.

        Args:
            ev: The Qt event object.
        """
        self._is_drag_over = False
        self._update_style()
        paths = []
        if ev.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in ev.mimeData().urls() if u.isLocalFile()]
        elif ev.mimeData().hasText():
            text = ev.mimeData().text().strip()
            paths = [p.strip() for p in text.splitlines() if os.path.exists(p.strip())]

        if paths:
            self.add_paths(paths, mode=self._mode)
            ev.acceptProposedAction()


# ═════════════════════════════════════════════════════════════════════════════
# TransferStatusDock — Embedded Live Transfer Monitor for Preview Pane
# ═════════════════════════════════════════════════════════════════════════════
class TransferStatusDock(QFrame):
    """Transferstatusdock.

    Manages TransferStatusDock operations and coordinates related state changes for the component.
    """

    open_monitor_requested = Signal()

    def __init__(self, icons: IconThumbs | None = None, parent=None):
        """Build the embedded transfer monitor dock with badge, bar, and stats.

        Initializes the instance and configures internal state.

        Args:
            icons (IconThumbs | None): The icons parameter.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setObjectName("TransferStatusDock")
        self._icons = icons or IconThumbs()
        self._tq = None
        self._current_job_id: str | None = None
        self._is_paused = False
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(3500)
        self._hide_timer.timeout.connect(self._auto_hide)

        self.setStyleSheet("""
            QFrame#TransferStatusDock {
                background: #11141C;
                border: 1px solid rgba(0, 229, 255, 0.4);
                border-radius: 9px;
            }
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        # Header Row: Badge, Title, Control Buttons
        hdr = QHBoxLayout()
        hdr.setSpacing(8)

        self.badge_lbl = QLabel("COPY")
        self.badge_lbl.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E5FF, stop:1 #0284C7);
            color: #050B14;
            font-weight: 800;
            font-size: 8.5pt;
            padding: 3px 8px;
            border-radius: 4px;
            letter-spacing: 0.5px;
        """)
        hdr.addWidget(self.badge_lbl)

        self.title_lbl = QLabel("Transferring…")
        self.title_lbl.setStyleSheet("color: #FFFFFF; font-weight: 700; font-size: 9.5pt;")
        hdr.addWidget(self.title_lbl, 1)

        # Pause button
        self.btn_pause = QToolButton()
        self.btn_pause.setIcon(_fluent_action("pause", size=13))
        self.btn_pause.setToolTip("Pause / Resume")
        self.btn_pause.setFixedSize(24, 24)
        self.btn_pause.setCursor(Qt.PointingHandCursor)
        self.btn_pause.setStyleSheet("QToolButton{background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.1);border-radius:5px;} QToolButton:hover{background:rgba(255,255,255,0.18);}")
        self.btn_pause.clicked.connect(self._toggle_pause)
        hdr.addWidget(self.btn_pause)

        # Cancel button
        self.btn_cancel = QToolButton()
        self.btn_cancel.setIcon(_fluent_action("close", size=13))
        self.btn_cancel.setToolTip("Cancel Transfer")
        self.btn_cancel.setFixedSize(24, 24)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet("QToolButton{background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.1);border-radius:5px;} QToolButton:hover{background:#EF4444;border-color:#EF4444;}")
        self.btn_cancel.clicked.connect(self._on_cancel)
        hdr.addWidget(self.btn_cancel)

        lay.addLayout(hdr)

        # Current Item Label (e.g. "file.mp4 -> dest")
        self.file_lbl = QLabel("")
        self.file_lbl.setStyleSheet("color: #F1F5F9; font-size: 9pt; font-weight: 500;")
        self.file_lbl.setWordWrap(False)
        lay.addWidget(self.file_lbl)

        # Progress bar
        self.bar = QProgressBar()
        self.bar.setFixedHeight(7)
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E5FF, stop:1 #3B82F6);
                border-radius: 3px;
            }
        """)
        lay.addWidget(self.bar)

        # Stats Row (e.g. "32% · 52.3 MB/s · ETA 34s")
        self.stats_lbl = QLabel("0% · 0 B/s")
        self.stats_lbl.setStyleSheet("font-size: 8.5pt; color: #CBD5E1;")
        lay.addWidget(self.stats_lbl)

        self.setVisible(False)

    def bind_queue(self, tq):
        """Attach a transfer queue, wiring its job signals to this dock.

        Manages bind queue operations and coordinates related state changes for the component.

        Args:
            tq: The tq parameter.
        """
        self._tq = tq
        if not tq:
            return
        tq.job_added.connect(self._on_job_added)
        tq.job_started.connect(self._on_job_started)
        tq.job_progress.connect(self._on_job_progress)
        tq.job_completed.connect(self._on_job_completed)
        tq.job_cancelled.connect(self._on_job_cancelled)

    def _on_job_added(self, job_id: str):
        """Show the dock for a new job and reset badge, title, and bar.

        Manages on job added operations and coordinates related state changes for the component.

        Args:
            job_id (str): The job id parameter.
        """
        self._hide_timer.stop()
        self._current_job_id = job_id
        self._is_paused = False
        self.btn_pause.setIcon(_fluent_action("pause", size=13))
        if self._tq:
            job = self._tq.get_job(job_id)
            if job:
                self.badge_lbl.setText(job.kind.upper())
                dest_name = Path(job.dest).name or job.dest
                self.title_lbl.setText(f"{job.kind.capitalize()}ing to {dest_name}")
                self.file_lbl.setText("<span style='color:#94A3B8;'>Starting transfer…</span>")
        self.bar.setValue(0)
        self.setVisible(True)

    def _on_job_started(self, job_id: str):
        """Reveal the dock and track a started job, stopping auto-hide.

        Manages on job started operations and coordinates related state changes for the component.

        Args:
            job_id (str): The job id parameter.
        """
        self._hide_timer.stop()
        self._current_job_id = job_id
        self.setVisible(True)

    def _on_job_progress(self, job_id: str, percent: int, text: str):
        """Update bar, current-file label, and speed/ETA stats for a job.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            job_id (str): The job id parameter.
            percent (int): The percent parameter.
            text (str): Display text string.
        """
        self._hide_timer.stop()
        self._current_job_id = job_id
        self.setVisible(True)
        self.bar.setValue(percent)

        job = self._tq.get_job(job_id) if self._tq else None
        if job:
            self.badge_lbl.setText(job.kind.upper())
            if job.current_file:
                dest_name = Path(job.dest).name if job.dest else ""
                arrow = f" <span style='color:#00E5FF;'>→</span> <span style='color:#94A3B8;'>{dest_name}</span>" if dest_name else ""
                self.file_lbl.setText(f"<b style='color:#FFFFFF;'>{job.current_file}</b>{arrow}")

        # Clean text by stripping redundant "kind: " prefix
        clean = text
        if job and clean.lower().startswith(f"{job.kind.lower()}:"):
            clean = clean.split(":", 1)[1].strip()

        parts = [p.strip() for p in clean.split("·") if p.strip()]
        formatted_parts = []
        for p in parts:
            if "ETA" in p:
                formatted_parts.append(f"<span style='color:#FBBF24; font-weight:600;'>{p}</span>")
            elif "/s" in p or "B/s" in p:
                formatted_parts.append(f"<span style='color:#38BDF8; font-weight:600;'>{p}</span>")
            elif "/" in p:
                formatted_parts.append(f"<span style='color:#FFFFFF; font-weight:600;'>{p}</span>")
            else:
                formatted_parts.append(f"<span style='color:#E2E8F0; font-weight:500;'>{p}</span>")

        stats_text = " &nbsp;·&nbsp; ".join(formatted_parts) if formatted_parts else clean
        self.stats_lbl.setText(
            f"<b style='color:#00E5FF; font-size:9.5pt;'>{percent}%</b> &nbsp;·&nbsp; {stats_text}"
        )

    def _on_job_completed(self, job_id: str, success: bool, msg: str):
        """Show DONE/ERROR state for a finished job and schedule auto-hide.

        Manages on job completed operations and coordinates related state changes for the component.

        Args:
            job_id (str): The job id parameter.
            success (bool): The success parameter.
            msg (str): Informational or progress status message.
        """
        if success:
            self.badge_lbl.setText("DONE")
            self.badge_lbl.setStyleSheet("""
                background: #10B981;
                color: #FFFFFF;
                font-weight: 800;
                font-size: 8.5pt;
                padding: 3px 8px;
                border-radius: 4px;
            """)
            self.title_lbl.setText("Transfer Completed")
            self.bar.setValue(100)
            self.file_lbl.setText("<span style='color:#10B981; font-weight:600;'>✓ All files transferred successfully</span>")
            self.stats_lbl.setText("<span style='color:#94A3B8;'>100% completed</span>")
        else:
            self.badge_lbl.setText("ERROR")
            self.badge_lbl.setStyleSheet("""
                background: #EF4444;
                color: #FFFFFF;
                font-weight: 800;
                font-size: 8.5pt;
                padding: 3px 8px;
                border-radius: 4px;
            """)
            self.title_lbl.setText("Transfer Notice")
            self.file_lbl.setText(f"<span style='color:#EF4444;'>{msg[:70] if msg else 'Transfer error'}</span>")
            self.stats_lbl.setText("<span style='color:#F87171;'>Completed with errors</span>")
        self._hide_timer.start()

    def _on_job_cancelled(self, job_id: str):
        """Show the CANCELLED state and schedule auto-hide.

        Manages on job cancelled operations and coordinates related state changes for the component.

        Args:
            job_id (str): The job id parameter.
        """
        self.badge_lbl.setText("CANCELLED")
        self.badge_lbl.setStyleSheet("""
            background: #64748B;
            color: #FFFFFF;
            font-weight: 800;
            font-size: 8.5pt;
            padding: 3px 8px;
            border-radius: 4px;
        """)
        self.title_lbl.setText("Transfer Cancelled")
        self.file_lbl.setText("<span style='color:#FBBF24;'>Transfer cancelled by user</span>")
        self.stats_lbl.setText("<span style='color:#94A3B8;'>Stopped &bull; Click ✕ to close</span>")
        self.btn_pause.setEnabled(False)
        self._hide_timer.start()

    def _auto_hide(self):
        """Hide the dock once idle unless a transfer is still busy.

        Manages auto hide operations and coordinates related state changes for the component.
        """
        try:
            if self._tq and getattr(self._tq, "is_busy", bool(getattr(self._tq, "_active", []))):
                return
        except Exception:
            pass
        self.setVisible(False)

    def _toggle_pause(self):
        """Pause or resume the tracked job and swap the pause/play icon.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        if not self._tq or not self._current_job_id:
            return
        if self._is_paused:
            self._tq.resume(self._current_job_id)
            self._is_paused = False
            self.btn_pause.setIcon(_fluent_action("pause", size=13))
            self.btn_pause.setToolTip("Pause")
        else:
            self._tq.pause(self._current_job_id)
            self._is_paused = True
            self.btn_pause.setIcon(_fluent_action("play", size=13))
            self.btn_pause.setToolTip("Resume")

    def _on_cancel(self):
        """Cancel the running job, or hide the dock when already idle.

        Manages on cancel operations and coordinates related state changes for the component.
        """
        if self._tq and self._current_job_id:
            job = self._tq.get_job(self._current_job_id)
            if job and job.state.name in ("RUNNING", "PAUSED", "QUEUED"):
                self._tq.cancel(self._current_job_id)
                return
        self._hide_timer.stop()
        self.setVisible(False)


# ═════════════════════════════════════════════════════════════════════════════
# PreviewPane — Right-side preview + Transfer Monitor + Staging Shelf
# ═════════════════════════════════════════════════════════════════════════════
class PreviewPane(QWidget):
    """Previewpane.

    Manages PreviewPane operations and coordinates related state changes for the component.
    """

    TEXT_EXTS = {".txt", ".md", ".py", ".js", ".ts", ".json", ".xml", ".html",
                 ".css", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".log",
                 ".csv", ".rs", ".go", ".c", ".cpp", ".h", ".hpp", ".java",
                 ".sh", ".bat", ".ps1", ".sql", ".rb", ".php"}

    IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico",
                  ".webp", ".svg", ".tiff", ".tif"}

    def __init__(self, icons: IconThumbs | None = None, parent=None):
        """Build the preview pane: icon, metadata, actions, dock, and shelf.

        Initializes the instance and configures internal state.

        Args:
            icons (IconThumbs | None): The icons parameter.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setObjectName("Preview")
        self.setFixedWidth(_scaled(330))
        self._icons = icons or IconThumbs()
        self._preview_proc: QProcess | None = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        self.icon_lbl = QLabel()
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setFixedHeight(120)
        self.icon_lbl.setStyleSheet(
            "background: rgba(30,30,30,220); border-radius: 10px; border: 1px solid rgba(255,255,255,0.08);")

        self.name_lbl = QLabel("No selection")
        self.name_lbl.setObjectName("PreviewName")
        self.name_lbl.setWordWrap(True)

        self.meta_lbl = QLabel("")
        self.meta_lbl.setObjectName("PreviewMeta")
        self.meta_lbl.setWordWrap(True)

        self.path_lbl = QLabel("")
        self.path_lbl.setObjectName("PreviewMeta")
        self.path_lbl.setWordWrap(True)
        self.path_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path_lbl.setStyleSheet("color: #777777; font-size: 7.5pt;")

        self._actions_widget = QWidget()
        self._actions_widget.setObjectName("PreviewActions")
        actions_lay = QVBoxLayout(self._actions_widget)
        actions_lay.setContentsMargins(0, 0, 0, 0)
        actions_lay.setSpacing(4)
        self._btn_open = QPushButton("Open")
        self._btn_open.setIcon(_fluent_action("folder", size=16))
        self._btn_open.clicked.connect(self._on_open)
        self._btn_open_with = QPushButton("Open with\u2026")
        self._btn_open_with.setIcon(_fluent_action("expand_right", size=16))
        self._btn_open_with.clicked.connect(self._on_open_with)
        self._btn_copy_path = QPushButton("Copy path")
        self._btn_copy_path.setIcon(_fluent_action("copy", size=16))
        self._btn_copy_path.clicked.connect(self._on_copy_path)
        self._btn_hash = QPushButton("Checksums\u2026")
        self._btn_hash.setIcon(_fluent_action("info", size=16))
        self._btn_hash.clicked.connect(self._on_checksums)
        actions_lay.addWidget(self._btn_open)
        actions_lay.addWidget(self._btn_open_with)
        actions_lay.addWidget(self._btn_copy_path)
        actions_lay.addWidget(self._btn_hash)

        self._hash_lbl = QLabel("")
        self._hash_lbl.setObjectName("PreviewMeta")
        self._hash_lbl.setStyleSheet("color: #777777; font-size: 7pt;")
        self._hash_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)

        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setMaximumHeight(160)
        self.text_view.setStyleSheet(
            "background: rgba(30,30,30,220); border: 1px solid rgba(255,255,255,0.08); border-radius: 6px;"
            " font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 7.5pt;"
            " color: #AAAAAA; padding: 6px;")
        self.text_view.setVisible(False)

        lay.addWidget(self.icon_lbl)
        lay.addWidget(self.name_lbl)
        lay.addWidget(self.meta_lbl)
        lay.addWidget(self.path_lbl)
        lay.addWidget(self._actions_widget)
        lay.addWidget(self._hash_lbl)
        lay.addWidget(self.text_view)
        lay.addStretch(1)

        # Embedded Live Transfer Monitor Dock
        self.transfer_dock = TransferStatusDock(self._icons, self)
        lay.addWidget(self.transfer_dock)

        # Staging Shelf / Clipboard Dock in lower half
        self.staging_shelf = StagingShelfWidget(self._icons, self)
        lay.addWidget(self.staging_shelf)

        self._current_path = None
        self._actions_widget.setVisible(False)
        self._hash_lbl.setVisible(False)

    def set_transfer_queue(self, tq):
        """Bind live transfer queue to the embedded transfer dock.

        Manages set transfer queue operations and coordinates related state changes for the component.

        Args:
            tq: The tq parameter.
        """
        self.transfer_dock.bind_queue(tq)

    def set_current_folder(self, path: str):
        """Update active destination directory for the staging shelf.

        Manages set current folder operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        self.staging_shelf.set_current_folder(path)

    def sync_clipboard(self, mode: str, paths: list[str]):
        """Update staging shelf when clipboard changes.

        Manages sync clipboard operations and coordinates related state changes for the component.

        Args:
            mode (str): The mode parameter.
            paths (list[str]): Filesystem path to the target file or directory.
        """
        self.staging_shelf.set_staged(mode, paths)

    def show_entry(self, row: dict | None) -> None:
        """Display icon/image, metadata, and text preview for a row dict.

        Manages show entry operations and coordinates related state changes for the component.

        Args:
            row (dict | None): Table row index or list of row indices.
        """
        from PySide6.QtGui import QImageReader, QPixmap

        if not row:
            self.icon_lbl.clear()
            self.name_lbl.setText("No selection")
            self.meta_lbl.setText("")
            self.path_lbl.setText("")
            self.text_view.setVisible(False)
            self._actions_widget.setVisible(False)
            self._hash_lbl.setVisible(False)
            return

        path = row.get("path", "")
        if not isinstance(path, str) or not path:
            self.icon_lbl.setPixmap(self._big_icon(row))
            return
        self._current_path = path
        name = row.get("name", "")
        is_dir = row.get("isDir", False)
        size = "" if is_dir else human(row.get("size", 0))
        ext = (row.get("ext") or "").upper()
        kind = "Folder" if is_dir else (ext or "FILE")
        mod = ""
        ms = int(row.get("modifiedMs", 0) or 0)
        if ms:
            from datetime import datetime
            mod = _safe_ts(ms)

        meta_parts = [f"{kind}"]
        if size:
            meta_parts.append(size)
        if mod:
            meta_parts.append(f"Modified: {mod}")
        if is_dir and row.get("folderSize") is not None:
            meta_parts.append(f"Size: {human(row['folderSize'])}")

        # Storage attribute badges (Cloud, Junction, Compact)
        if path:
            try:
                from cortex_unified.engine.winattrs import (
                    attrs_of, tag_of, is_dehydrated, is_cloud, is_junction, on_disk_size, size_may_be_misleading,
                    describe,
                    FILE_ATTRIBUTE_COMPRESSED, FILE_ATTRIBUTE_SPARSE_FILE, IO_REPARSE_TAG_SYMLINK
                )
                import os
                st = os.stat(path, follow_symlinks=False)
                a = attrs_of(st)
                t = tag_of(st)
                if is_dehydrated(a):
                    meta_parts.append("[☁️ Cloud: Online-Only]")
                elif is_cloud(a, t):
                    meta_parts.append("[☁️ Cloud Synced]")
                if is_junction(t):
                    meta_parts.append("[🔗 Junction]")
                elif t == IO_REPARSE_TAG_SYMLINK:
                    meta_parts.append("[🔗 Symlink]")
                if a & FILE_ATTRIBUTE_COMPRESSED:
                    meta_parts.append("[📦 Compact (NTFS)]")
                elif a & FILE_ATTRIBUTE_SPARSE_FILE:
                    meta_parts.append("[📦 Compact (Sparse)]")
                if not is_dir and size_may_be_misleading(a):
                    alloc = on_disk_size(path, row.get("size", 0))
                    if alloc is not None and alloc != row.get("size", 0):
                        meta_parts.append(f"On-Disk: {human(alloc)}")
                desc = describe(a, t)
                if desc:
                    meta_parts.append(f"Storage: {desc}")
            except Exception:
                pass
        self.name_lbl.setText(name)
        self.meta_lbl.setText("\n".join(meta_parts))
        self.path_lbl.setText(path)
        self._actions_widget.setVisible(not is_dir)
        self._hash_lbl.setVisible(False)

        self.text_view.setVisible(False)
        ext_l = "." + (row.get("ext") or "").lower()

        # Image preview (skip files >50MB)
        if not is_dir and ext_l in self.IMAGE_EXTS and Path(path).is_file():
            try:
                if Path(path).stat().st_size > 50 * 1024 * 1024:
                    self.icon_lbl.setPixmap(self._big_icon(row))
                    return
            except OSError:
                pass
            r = QImageReader(path)
            r.setAutoTransform(True)
            img_size = r.size()
            orig_w, orig_h = (img_size.width(), img_size.height()) if img_size.isValid() else (0, 0)
            r.setScaledSize(QSize(256, 256))
            img = r.read()
            if not img.isNull():
                if orig_w and orig_h:
                    meta_parts.append(f"{orig_w} \u00d7 {orig_h} px")
                    self.meta_lbl.setText("\n".join(meta_parts))
                max_w = 240
                scaled = img.scaled(
                    max_w, 10000,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.icon_lbl.setPixmap(QPixmap.fromImage(scaled))
                return

        # Text preview — read in background to avoid UI freeze
        if not is_dir and ext_l in self.TEXT_EXTS and Path(path).is_file():
            self.text_view.setPlainText("")
            self.text_view.setVisible(True)
            self._load_text_preview(path)

        self.icon_lbl.setPixmap(self._big_icon(row))

    def _on_open(self):
        """Open the previewed file with its default Windows handler.

        Manages on open operations and coordinates related state changes for the component.
        """
        if self._current_path and os.path.isfile(self._current_path):
            os.startfile(self._current_path)

    def _on_open_with(self):
        """Open the previewed file using the explicit 'open' verb.

        Manages on open with operations and coordinates related state changes for the component.
        """
        if self._current_path and os.path.isfile(self._current_path):
            os.startfile(self._current_path, "open")

    def _on_copy_path(self):
        """Copy the previewed path to the clipboard.

        Manages on copy path operations and coordinates related state changes for the component.
        """
        if self._current_path:
            QApplication.clipboard().setText(self._current_path)

    def _on_checksums(self):
        """Open the checksum dialog for the previewed file.

        Manages on checksums operations and coordinates related state changes for the component.
        """
        if self._current_path and os.path.isfile(self._current_path):
            FileChecksumDialog(self._current_path, self).exec()

    def _load_text_preview(self, path: str):
        """Read first 60 lines in a background thread.

        Manages load text preview operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        if hasattr(self, '_text_thread') and self._text_thread:
            if self._text_thread.isRunning():
                self._text_thread.quit()
                self._text_thread.wait(1000)
            try:
                self._text_thread.text_ready.disconnect(self._on_text_ready)
            except RuntimeError:
                pass

        self._text_thread = _TextPreviewReader(path)
        self._text_thread.text_ready.connect(self._on_text_ready)
        self._text_thread.start()

    def _on_text_ready(self, text: str):
        """Fill the text preview with content from the background reader.

        Manages on text ready operations and coordinates related state changes for the component.

        Args:
            text (str): Display text string.
        """
        self.text_view.setPlainText(text)

    def _big_icon(self, row: dict):
        """Return a 96px icon pixmap for a row via the icon cache.

        Manages big icon operations and coordinates related state changes for the component.

        Args:
            row (dict): Table row index or list of row indices.
        """
        ico = self._icons.icon_for(row)
        return ico.pixmap(96, 96)


# ═════════════════════════════════════════════════════════════════════════════
# CommandPalette — Ctrl+Shift+P command palette
# ═════════════════════════════════════════════════════════════════════════════
class CommandPalette(QDialog):
    """Commandpalette.

    Manages CommandPalette operations and coordinates related state changes for the component.
    """

    def __init__(self, parent=None):
        """Build the frameless fuzzy command palette dialog.

        Initializes the instance and configures internal state.

        Args:
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setObjectName("CommandPalette")
        self.setWindowTitle("Command Palette")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFixedWidth(520)
        self.setFixedHeight(400)
        self._actions: list[tuple[str, str, callable]] = []
        self._filtered: list[int] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Type a command\u2026")
        self.search.setObjectName("PaletteSearch")
        self.search.textChanged.connect(self._filter)
        self.search.returnPressed.connect(self._execute_selected)
        lay.addWidget(self.search)

        self.list = QListWidget()
        self.list.setObjectName("PaletteList")
        self.list.itemDoubleClicked.connect(lambda _: self._execute_selected())
        lay.addWidget(self.list, 1)

    def register(self, name: str, shortcut: str, callback):
        """Register.

        Manages register operations and coordinates related state changes for the component.

        Args:
            name (str): The name parameter.
            shortcut (str): The shortcut parameter.
            callback: The callback parameter.
        """
        self._actions.append((name, shortcut, callback))

    def toggle(self):
        """Hide the palette if visible, else open it centered on its parent.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        if self.isVisible():
            self.hide()
        else:
            self.open_palette()

    def open_palette(self):
        """Reset the search, center over the parent, and focus the input.

        Manages open palette operations and coordinates related state changes for the component.
        """
        self.search.clear()
        self._filter("")
        if self.parent():
            parent_global = self.parent().mapToGlobal(self.parent().rect().topLeft())
            x = parent_global.x() + (self.parent().width() - self.width()) // 2
            y = parent_global.y() + 60
            self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        self.search.setFocus()

    def _filter(self, text: str):
        """Filter.

        Manages filter operations and coordinates related state changes for the component.

        Args:
            text (str): Display text string.
        """
        self.list.clear()
        self._filtered = []
        text_lower = text.lower()
        for i, (name, shortcut, _) in enumerate(self._actions):
            if not text_lower or self._fuzzy_match(text_lower, name.lower()):
                self._filtered.append(i)
                display = f"{name}    {shortcut}" if shortcut else name
                self.list.addItem(display)
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    def _fuzzy_match(self, pattern: str, text: str) -> bool:
        """Return True when pattern chars appear in order within text.

        Manages fuzzy match operations and coordinates related state changes for the component.

        Args:
            pattern (str): The pattern parameter.
            text (str): Display text string.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        pi = 0
        for ch in text:
            if pi < len(pattern) and ch == pattern[pi]:
                pi += 1
        return pi == len(pattern)

    def _execute_selected(self):
        """Run the callback of the currently highlighted filtered command.

        Manages execute selected operations and coordinates related state changes for the component.
        """
        row = self.list.currentRow()
        if 0 <= row < len(self._filtered):
            idx = self._filtered[row]
            _, _, cb = self._actions[idx]
            self.hide()
            if cb:
                cb()

    def keyPressEvent(self, ev):
        """Handle keyboard press events for shortcuts and navigation.

        Processes key codes such as Return, Escape, or arrow keys to trigger associated commands or focus changes.

        Args:
            ev: The Qt event object.
        """
        if ev.key() == Qt.Key.Key_Escape:
            self.hide()
        elif ev.key() == Qt.Key.Key_Down:
            row = self.list.currentRow()
            if row < self.list.count() - 1:
                self.list.setCurrentRow(row + 1)
        elif ev.key() == Qt.Key.Key_Up:
            row = self.list.currentRow()
            if row > 0:
                self.list.setCurrentRow(row - 1)
        else:
            super().keyPressEvent(ev)


# ═════════════════════════════════════════════════════════════════════════════
# JobQueueWidget — overlay for copy/move/delete progress
# ═════════════════════════════════════════════════════════════════════════════
class JobQueueWidget(QWidget):
    """Jobqueuewidget.

    Manages JobQueueWidget operations and coordinates related state changes for the component.
    """

    def __init__(self, parent=None):
        """Build the floating jobs overlay, hidden until a job arrives.

        Initializes the instance and configures internal state.

        Args:
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setObjectName("JobQueueOverlay")
        self.setFixedWidth(_scaled(300))
        self._jobs: dict[int, dict] = {}
        self._next_id = 1
        self._collapsed = False

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(4)

        self.toggle_btn = QPushButton("Jobs")
        self.toggle_btn.setIcon(_fluent_action("transfer", size=14))
        self.toggle_btn.setObjectName("JobToggle")
        self.toggle_btn.setFixedHeight(24)
        self.toggle_btn.clicked.connect(self._toggle_collapse)
        self.main_layout.addWidget(self.toggle_btn)

        self.jobs_container = QWidget()
        self.jobs_layout = QVBoxLayout(self.jobs_container)
        self.jobs_layout.setContentsMargins(0, 0, 0, 0)
        self.jobs_layout.setSpacing(4)
        self.main_layout.addWidget(self.jobs_container)
        self.main_layout.addStretch(1)

        self.hide()

    def add_job(self, name: str, total: int) -> int:
        """Add a job row with progress bar; return its numeric job id.

        Manages add job operations and coordinates related state changes for the component.

        Args:
            name (str): The name parameter.
            total (int): The total parameter.

        Returns:
            int: Result of the operation.
        """
        job_id = self._next_id
        self._next_id += 1

        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(4, 4, 4, 4)
        vl.setSpacing(2)

        lbl = QLabel(f"{name} (0/{total})")
        lbl.setObjectName("JobLabel")

        bar = QProgressBar()
        bar.setMaximum(total)
        bar.setValue(0)
        bar.setFixedHeight(6)

        flbl = QLabel("")
        flbl.setObjectName("JobFileLabel")
        flbl.setMaximumWidth(280)

        vl.addWidget(lbl)
        vl.addWidget(bar)
        vl.addWidget(flbl)

        self.jobs_layout.addWidget(w)
        self._jobs[job_id] = {
            "widget": w, "label": lbl,
            "progress": bar, "file_label": flbl,
            "name": name, "total": total,
        }
        self._update_toggle_text()
        self.show()
        self._reposition()
        return job_id

    def update_job(self, job_id: int, current: int, filename: str = ""):
        """Update a job's bar, count label, and current filename.

        Manages update job operations and coordinates related state changes for the component.

        Args:
            job_id (int): The job id parameter.
            current (int): The current parameter.
            filename (str): The filename parameter.
        """
        job = self._jobs.get(job_id)
        if not job:
            return
        job["progress"].setValue(current)
        job["label"].setText(f"{job['name']} ({current}/{job['total']})")
        if filename:
            job["file_label"].setText(filename)

    def complete_job(self, job_id: int):
        """Remove a job's row; hide the overlay when no jobs remain.

        Manages complete job operations and coordinates related state changes for the component.

        Args:
            job_id (int): The job id parameter.
        """
        job = self._jobs.pop(job_id, None)
        if not job:
            return
        self.jobs_layout.removeWidget(job["widget"])
        job["widget"].deleteLater()
        self._update_toggle_text()
        if not self._jobs:
            self.hide()

    def _toggle_collapse(self):
        """Collapse or expand the jobs container and refresh the count.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        self._collapsed = not self._collapsed
        self.jobs_container.setVisible(not self._collapsed)
        self._update_toggle_text()

    def _update_toggle_text(self):
        """Refresh the toggle button with the live job count.

        Manages update toggle text operations and coordinates related state changes for the component.
        """
        self.toggle_btn.setText(f"Jobs ({len(self._jobs)})")

    def _reposition(self):
        """Reposition.

        Manages reposition operations and coordinates related state changes for the component.
        """
        parent = self.parent()
        if parent:
            w = self.width()
            h = self.height()
            self.move(parent.width() - w - 12, parent.height() - h - 12)


# ═════════════════════════════════════════════════════════════════════════════
# TerminalWidget — integrated terminal panel (bottom panel, Ctrl+` toggle)
# ═════════════════════════════════════════════════════════════════════════════
class TerminalWidget(QWidget):
    """Terminalwidget.

    Manages TerminalWidget operations and coordinates related state changes for the component.
    """

    def __init__(self, parent=None):
        """Build the terminal panel: header, output view, and input row.

        Initializes the instance and configures internal state.

        Args:
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setObjectName("TerminalPanel")
        self._process: QProcess | None = None
        self._cwd = os.path.expanduser("~")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── header bar ───────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("TerminalHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 4, 10, 4)
        hl.setSpacing(6)

        title = QLabel("Terminal")
        title.setStyleSheet(
            "color:#777777; font-weight:700; font-size:8pt; background:transparent;")
        hl.addWidget(title)
        hl.addStretch(1)

        btn_clear = QPushButton("Clear")
        btn_clear.setIcon(_fluent_action("delete", size=16))
        btn_clear.setFixedHeight(22)
        btn_clear.clicked.connect(self._clear_output)
        hl.addWidget(btn_clear)

        btn_copy = QPushButton("Copy")
        btn_copy.setIcon(_fluent_action("copy", size=16))
        btn_copy.setFixedHeight(22)
        btn_copy.clicked.connect(self._copy_output)
        hl.addWidget(btn_copy)

        lay.addWidget(header)

        # ── output area ──────────────────────────────────────────────────
        self.output = QTextEdit()
        self.output.setObjectName("TerminalOutput")
        self.output.setReadOnly(True)
        lay.addWidget(self.output, 1)

        # ── input row ────────────────────────────────────────────────────
        input_row = QWidget()
        il = QHBoxLayout(input_row)
        il.setContentsMargins(10, 4, 10, 4)
        il.setSpacing(6)

        prompt = QLabel(">")
        prompt.setStyleSheet(
            "color:#90CAF9; font-family:'Cascadia Code','Consolas',monospace;"
            " font-weight:700; background:transparent; font-size:9pt;")
        il.addWidget(prompt)

        self.input = QLineEdit()
        self.input.setObjectName("TerminalInput")
        self.input.setPlaceholderText("Type a command\u2026")
        self.input.returnPressed.connect(self._execute)
        il.addWidget(self.input)

        lay.addWidget(input_row)

    # ────────────────────────── process lifecycle ─────────────────────────
    def setVisible(self, visible: bool):
        """Setvisible.

        Manages setVisible operations and coordinates related state changes for the component.

        Args:
            visible (bool): The visible parameter.
        """
        super().setVisible(visible)
        if visible:
            self._ensure_process()
        else:
            self.shutdown()

    def _ensure_process(self):
        """Spawn cmd.exe via QProcess unless one is already running.

        Manages ensure process operations and coordinates related state changes for the component.
        """
        if self._process is not None and self._process.state() == QProcess.ProcessState.Running:
            return
        from nexus_core import _guarded

        self._process = QProcess(self)
        self._process.setProcessChannelMode(
            QProcess.ProcessChannelMode.MergedChannels)
        self._process.readyReadStandardOutput.connect(
            _guarded(self._on_output))
        self._process.setWorkingDirectory(self._cwd)
        self._process.start("cmd.exe")
        self.output.setHtml(
            f"<span style='color:#AAAAAA;'>Nexus Explorer Terminal &mdash; "
            f"{self._cwd}</span>")

    def _on_output(self):
        """Append HTML-escaped shell output and scroll to the bottom.

        Manages on output operations and coordinates related state changes for the component.
        """
        if self._process:
            try:
                data = bytes(self._process.readAllStandardOutput()).decode(
                    "utf-8", errors="replace")
            except RuntimeError:
                return
            if data:
                safe = (data.replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;"))
                self.output.append(
                    f"<span style='color:#E0E0E0;'>{safe}</span>")
                sb = self.output.verticalScrollBar()
                sb.setValue(sb.maximum())

    def shutdown(self):
        """Shutdown.

        Manages shutdown operations and coordinates related state changes for the component.
        """
        if self._process is not None:
            try:
                if self._process.state() == QProcess.ProcessState.Running:
                    self._process.kill()
                    self._process.waitForFinished(600)
            except Exception:
                pass
            self._process = None

    def closeEvent(self, event):
        """Handle the window or widget close event.

        Performs graceful shutdown, releases active workers and system hooks, persists window geometry, and accepts the close event.

        Args:
            event: The Qt event object.
        """
        self.shutdown()
        super().closeEvent(event)

    def __del__(self):
        """Del.

        Manages del operations and coordinates related state changes for the component.
        """
        self.shutdown()

    # ────────────────────────── command execution ─────────────────────────
    def _execute(self):
        """Execute.

        Manages execute operations and coordinates related state changes for the component.
        """
        cmd = self.input.text().strip()
        if not cmd:
            return
        self.input.clear()

        cwd_safe = self._cwd.replace("&", "&amp;").replace("<", "&lt;")
        cmd_safe = cmd.replace("&", "&amp;").replace("<", "&lt;")
        self.output.append(
            f"<span style='color:#90CAF9;'>{cwd_safe}&gt;</span> "
            f"<span style='color:#E0E0E0;'>{cmd_safe}</span>")

        if self._process and self._process.state() == QProcess.ProcessState.Running:
            self._process.write((cmd + "\n").encode("utf-8"))
            self._track_cd(cmd)

    def _track_cd(self, cmd: str):
        """Mirror cd commands into the panel's tracked working directory.

        Manages track cd operations and coordinates related state changes for the component.

        Args:
            cmd (str): The cmd parameter.
        """
        lower = cmd.lower().strip()
        if lower.startswith("cd ") and lower != "cd":
            target = cmd[3:].strip().strip('"').strip("'")
            self._resolve_cd(target)
        elif lower == "cd":
            pass  # cd alone prints cwd in output; no tracking change

    def _resolve_cd(self, target: str):
        """Resolve a cd target (.., root, absolute, relative) into _cwd.

        Manages resolve cd operations and coordinates related state changes for the component.

        Args:
            target (str): The target parameter.
        """
        cwd = Path(self._cwd)
        if target == "..":
            parent = cwd.parent
            self._cwd = str(parent) if parent != cwd else self._cwd
        elif target in ("\\", "/"):
            drive = cwd.drive
            self._cwd = f"{drive}\\" if drive else "\\"
        elif os.path.isabs(target):
            self._cwd = str(Path(target))
        else:
            self._cwd = str(cwd / target)

    # ────────────────────────── public API ────────────────────────────────
    def set_cwd(self, path: str):
        """Set the tracked cwd and the live shell's working directory.

        Manages set cwd operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        self._cwd = path
        if self._process and self._process.state() == QProcess.ProcessState.Running:
            self._process.setWorkingDirectory(path)

    def _clear_output(self):
        """Clear the terminal output view.

        Manages clear output operations and coordinates related state changes for the component.
        """
        self.output.clear()

    def _copy_output(self):
        """Copy the terminal's plain-text output to the clipboard.

        Manages copy output operations and coordinates related state changes for the component.
        """
        QApplication.clipboard().setText(self.output.toPlainText())


# ═════════════════════════════════════════════════════════════════════════════
# PropertiesDialog — file/folder properties with grid layout
# ═════════════════════════════════════════════════════════════════════════════
class PropertiesDialog(QDialog):
    """Propertiesdialog.

    Manages PropertiesDialog operations and coordinates related state changes for the component.
    """

    def __init__(self, row: dict, parent=None):
        """Build the properties grid (name, size, type, path, flags) from a row.

        Initializes the instance and configures internal state.

        Args:
            row (dict): Table row index or list of row indices.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setWindowTitle("Properties")
        self.setMinimumWidth(400)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)

        from datetime import datetime

        layout = QGridLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        name = row.get("name", "")
        path = row.get("path", "")
        is_dir = row.get("isDir", False)
        size = "Folder" if is_dir else human(row.get("size", 0))
        ms = int(row.get("modifiedMs", 0) or 0)
        mod = (_safe_ts(ms) + ":00") if ms else "N/A"
        hidden = os.path.basename(path).startswith(".")
        try:
            readonly = not os.access(path, os.W_OK)
        except OSError:
            readonly = False

        fields = [
            ("Name:", name),
            ("Size:", size),
            ("Type:", "Folder" if is_dir else (row.get("ext", "").upper() or "File")),
            ("Path:", path),
            ("Modified:", mod),
            ("Hidden:", "Yes" if hidden else "No"),
            ("Read-only:", "Yes" if readonly else "No"),
        ]

        for i, (label, value) in enumerate(fields):
            lbl = QLabel(label)
            lbl.setStyleSheet("font-weight: 600; color: #777777;")
            val = QLabel(value)
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            val.setWordWrap(True)
            val.setStyleSheet("color: #E0E0E0;")
            layout.addWidget(lbl, i, 0)
            layout.addWidget(val, i, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        if not is_dir and os.path.isfile(path):
            btn_hash = QPushButton("Checksums…")
            btn_hash.setIcon(_fluent_action("info", size=16))
            btn_hash.clicked.connect(lambda: FileChecksumDialog(path, self).exec())
            btn_row.addWidget(btn_hash)
        btn_close = QPushButton("Close")
        btn_close.setIcon(_fluent_action("close", size=16))
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row, len(fields), 0, 1, 2)


class _ChecksumWorkerThread(QThread):
    """Checksumworkerthread.

    Manages ChecksumWorkerThread operations and coordinates related state changes for the component.
    """
    progress = Signal(int)
    done = Signal(object)

    def __init__(self, path: str, parent=None):
        """Store the file path to hash when the thread runs.

        Initializes the instance and configures internal state.

        Args:
            path (str): Filesystem path to the target file or directory.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self._path = path

    def run(self):
        """Stream the file in chunks, emitting progress and final hashes.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        import hashlib
        try:
            sz = os.path.getsize(self._path)
        except Exception:
            sz = 0

        h_md5 = hashlib.md5()
        h_sha1 = hashlib.sha1()
        h_sha256 = hashlib.sha256()
        h_sha512 = hashlib.sha512()

        read_bytes = 0
        chunk_size = 1024 * 512
        try:
            with open(self._path, "rb") as f:
                while True:
                    if self.isInterruptionRequested():
                        return
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    h_md5.update(chunk)
                    h_sha1.update(chunk)
                    h_sha256.update(chunk)
                    h_sha512.update(chunk)
                    read_bytes += len(chunk)
                    if sz > 0:
                        pct = int(read_bytes * 100 / sz)
                        self.progress.emit(min(100, pct))
            self.done.emit({
                "MD5": h_md5.hexdigest(),
                "SHA-1": h_sha1.hexdigest(),
                "SHA-256": h_sha256.hexdigest(),
                "SHA-512": h_sha512.hexdigest(),
            })
        except Exception as exc:
            self.done.emit({"error": str(exc)})


class FileChecksumDialog(QDialog):
    """Filechecksumdialog.

    Manages FileChecksumDialog operations and coordinates related state changes for the component.
    """

    def __init__(self, file_path: str, parent=None):
        """Build the checksum dialog and start hashing the given file.

        Initializes the instance and configures internal state.

        Args:
            file_path (str): Filesystem path to the target file or directory.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setWindowTitle("File Checksums & Integrity")
        self.setMinimumWidth(560)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self._path = file_path
        self._hashes = {}

        self.setStyleSheet("""
            QDialog {
                background: #11141C;
                color: #FFFFFF;
            }
            QLabel {
                color: #E2E8F0;
            }
            QLineEdit {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 5px;
                color: #FFFFFF;
                padding: 5px 8px;
                font-family: 'Consolas', monospace;
            }
            QLineEdit:focus {
                border-color: #00E5FF;
            }
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px;
                color: #FFFFFF;
                padding: 5px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.16);
            }
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(12)

        # File info
        info_box = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(_fluent_action("info", size=24).pixmap(24, 24))
        info_box.addWidget(icon_lbl)

        p = Path(file_path)
        sz_text = human(os.path.getsize(file_path)) if p.is_file() else ""
        meta_text = f"<b style='font-size:10.5pt; color:#FFFFFF;'>{p.name}</b><br><span style='color:#94A3B8; font-size:8.5pt;'>{sz_text} &bull; {p}</span>"
        lbl_info = QLabel(meta_text)
        lbl_info.setTextFormat(Qt.TextFormat.RichText)
        info_box.addWidget(lbl_info, 1)
        lay.addLayout(info_box)

        # Progress bar
        self.prog = QProgressBar()
        self.prog.setFixedHeight(6)
        self.prog.setTextVisible(False)
        self.prog.setRange(0, 100)
        self.prog.setValue(0)
        self.prog.setStyleSheet("""
            QProgressBar { background: rgba(255,255,255,0.08); border-radius: 3px; border:none; }
            QProgressBar::chunk { background: #00E5FF; border-radius: 3px; }
        """)
        lay.addWidget(self.prog)

        # Hashes grid
        grid = QGridLayout()
        grid.setSpacing(8)
        self._algo_edits = {}

        algos = ["MD5", "SHA-1", "SHA-256", "SHA-512"]
        for row_idx, algo in enumerate(algos):
            lbl = QLabel(f"{algo}:")
            lbl.setStyleSheet("font-weight: 700; color: #38BDF8; font-size: 8.5pt;")
            edit = QLineEdit("Calculating…")
            edit.setReadOnly(True)
            btn_copy = QPushButton("Copy")
            btn_copy.setFixedWidth(60)
            btn_copy.clicked.connect(lambda _, e=edit: QApplication.clipboard().setText(e.text()))

            grid.addWidget(lbl, row_idx, 0)
            grid.addWidget(edit, row_idx, 1)
            grid.addWidget(btn_copy, row_idx, 2)
            self._algo_edits[algo] = edit

        lay.addLayout(grid)

        # Verification Box
        verify_box = QVBoxLayout()
        v_title = QLabel("Verify Checksum (Compare):")
        v_title.setStyleSheet("font-weight: 700; font-size: 9pt; color: #F1F5F9; margin-top: 6px;")
        verify_box.addWidget(v_title)

        self.verify_input = QLineEdit()
        self.verify_input.setPlaceholderText("Paste expected hash here to verify match…")
        self.verify_input.textChanged.connect(self._check_match)
        verify_box.addWidget(self.verify_input)

        self.match_lbl = QLabel("")
        self.match_lbl.setStyleSheet("font-size: 8.5pt; font-weight: 600;")
        verify_box.addWidget(self.match_lbl)
        lay.addLayout(verify_box)

        # Bottom buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)
        lay.addLayout(btn_box)

        # Start calculation
        self._worker = _ChecksumWorkerThread(file_path, self)
        self._worker.progress.connect(self.prog.setValue)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, hashes: dict):
        """Fill hash fields from the worker result and re-check any match.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            hashes (dict): The hashes parameter.
        """
        self.prog.setValue(100)
        self.prog.setVisible(False)
        self._hashes = hashes
        for algo, edit in self._algo_edits.items():
            if algo in hashes:
                edit.setText(hashes[algo])
            elif "error" in hashes:
                edit.setText(f"Error: {hashes['error']}")
        self._check_match()

    def _check_match(self):
        """Compare the verify input against computed hashes and label match.

        Manages check match operations and coordinates related state changes for the component.
        """
        text = self.verify_input.text().strip().lower()
        if not text:
            self.match_lbl.setText("")
            return
        matched_algo = None
        for algo, val in self._hashes.items():
            if val.lower() == text:
                matched_algo = algo
                break
        if matched_algo:
            self.match_lbl.setText(f"<span style='color:#10B981;'>✓ Checksum Matches ({matched_algo})</span>")
        else:
            self.match_lbl.setText("<span style='color:#EF4444;'>✗ No algorithm matches this hash</span>")

    def closeEvent(self, event):
        """Handle the window or widget close event.

        Performs graceful shutdown, releases active workers and system hooks, persists window geometry, and accepts the close event.

        Args:
            event: The Qt event object.
        """
        if self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(500)
        super().closeEvent(event)


# ═════════════════════════════════════════════════════════════════════════════
# ExtractionProgressWidget — live extraction progress panel
# ═════════════════════════════════════════════════════════════════════════════
class ExtractionProgressWidget(QFrame):
    """Frosted-glass extraction progress panel shown at the bottom of the file list.

    Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.
    """

    def __init__(self, parent=None):
        """Build the frosted-glass extraction progress panel.

        Initializes the instance and configures internal state.

        Args:
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setObjectName("ExtractionProgress")
        self.setFixedHeight(_scaled(80))
        self.setStyleSheet("""
            QFrame#ExtractionProgress {
                background: rgba(20, 20, 20, 230);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
            }
            QLabel { color: #E0E0E0; font-size: 12px; }
            QProgressBar {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 4px;
                height: 14px;
                text-align: center;
                color: #E0E0E0;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #2196F3, stop:0.5 #42A5F5, stop:1 #90CAF9);
                border-radius: 3px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        self._lbl_title = QLabel("Extracting...")
        self._lbl_title.setStyleSheet("font-weight: 600; color: #90CAF9;")
        top_row.addWidget(self._lbl_title)
        top_row.addStretch()
        self._lbl_file_count = QLabel("")
        self._lbl_file_count.setStyleSheet("color: #888; font-size: 11px;")
        top_row.addWidget(self._lbl_file_count)
        self._lbl_time = QLabel("0s elapsed")
        self._lbl_time.setStyleSheet("color: #888; font-size: 11px;")
        top_row.addWidget(self._lbl_time)
        layout.addLayout(top_row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        layout.addWidget(self._progress)

        bot_row = QHBoxLayout()
        self._lbl_file = QLabel("")
        self._lbl_file.setStyleSheet("color: #AAA; font-size: 11px;")
        bot_row.addWidget(self._lbl_file, 1)
        self._lbl_speed = QLabel("")
        self._lbl_speed.setStyleSheet("color: #888; font-size: 11px;")
        bot_row.addWidget(self._lbl_speed)
        self._lbl_eta = QLabel("")
        self._lbl_eta.setStyleSheet("color: #888; font-size: 11px;")
        bot_row.addWidget(self._lbl_eta)
        layout.addLayout(bot_row)

        self._start_time = 0.0
        self._total_files = 0
        self._processed_bytes = 0.0

    def start(self, archive_name: str, total_files: int = 0):
        """Start active background operations.

        Manages worker thread execution states, signaling termination flags or initializing scheduled execution timers.

        Args:
            archive_name (str): The archive name parameter.
            total_files (int): The total files parameter.
        """
        self._start_time = time.monotonic()
        self._total_files = total_files
        self._processed_bytes = 0.0
        self._lbl_title.setText(f"Extracting {archive_name}")
        self._progress.setValue(0)
        self._progress.setFormat("%p%")
        self._lbl_file.setText("Preparing...")
        self._lbl_speed.setText("")
        self._lbl_eta.setText("")
        if total_files:
            self._lbl_file_count.setText(f"0 / {total_files} files")
        else:
            self._lbl_file_count.setText("")
        self.show()

    def update_progress(self, percent: int, current_file: str = "", file_count: int = 0,
                        file_size: int = 0):
        """Update bar, file, speed, and ETA labels for an extraction.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            percent (int): The percent parameter.
            current_file (str): The current file parameter.
            file_count (int): The file count parameter.
            file_size (int): The file size parameter.
        """
        self._progress.setValue(percent)
        elapsed = time.monotonic() - self._start_time

        if file_size > 0:
            self._processed_bytes += file_size

        if current_file:
            name = Path(current_file).name
            if len(name) > 50:
                name = name[:25] + " ... " + name[-22:]
            self._lbl_file.setText(name)

        self._lbl_time.setText(_fmt_duration(elapsed) + " elapsed")

        if self._total_files and file_count:
            self._lbl_file_count.setText(f"{file_count} / {self._total_files} files")

        if percent > 0 and elapsed > 1:
            total_est = elapsed / (percent / 100.0)
            remaining = max(0, total_est - elapsed)
            self._lbl_eta.setText(_fmt_duration(remaining) + " left")

            if self._processed_bytes > 0:
                speed = self._processed_bytes / elapsed
                self._lbl_speed.setText(f"{_fmt_size(speed)}/s")
            elif file_count > 0:
                rate = file_count / elapsed
                self._lbl_speed.setText(f"{rate:.1f} files/s")

    def finish(self, success: bool, message: str = ""):
        """Finish.

        Manages finish operations and coordinates related state changes for the component.

        Args:
            success (bool): The success parameter.
            message (str): Informational or progress status message.
        """
        if success:
            self._progress.setValue(100)
            self._lbl_title.setText("Extraction complete")
            self._lbl_file.setText(message or "Done")
            self._lbl_file_count.setText("")
            self._lbl_speed.setText("")
            self._lbl_eta.setText("")
        else:
            self._lbl_title.setText("Extraction failed")
            self._lbl_file.setText(message or "Error occurred")
        QTimer.singleShot(3000, self.hide)


def _fmt_duration(seconds: float) -> str:
    """Format seconds as Xs, Xm SSs, or Xh MMm.

    Converts raw numeric values into formatted, localized, and human-readable string representations.

    Args:
        seconds (float): The seconds parameter.

    Returns:
        str: Formatted string or path.
    """
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m"


def _fmt_size(bps: float) -> str:
    """Format bytes-per-second as B/KB/MB/GB/TB(/PB) with one decimal.

    Converts raw numeric values into formatted, localized, and human-readable string representations.

    Args:
        bps (float): The bps parameter.

    Returns:
        str: Formatted string or path.
    """
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(bps) < 1024:
            return f"{bps:.1f} {unit}"
        bps /= 1024
    return f"{bps:.1f} PB"


# (NexusClipboard defined above StagingShelfWidget)


# ═════════════════════════════════════════════════════════════════════════════
# ArchiveBrowser — browse .zip files using Python's built-in zipfile module
# ═════════════════════════════════════════════════════════════════════════════
class _ZipEntry:
    """Zipentry.

    Manages ZipEntry operations and coordinates related state changes for the component.
    """

    def __init__(self, archive_path: str, name: str, is_dir: bool,
                 size: int, modified_ms: int):
        """Store an archive entry's identity, size, and modified time.

        Initializes the instance and configures internal state.

        Args:
            archive_path (str): Filesystem path to the target file or directory.
            name (str): The name parameter.
            is_dir (bool): The is dir parameter.
            size (int): Integer number of bytes to format or process.
            modified_ms (int): The modified ms parameter.
        """
        self.archive_path = archive_path
        self.name = name
        self.is_dir = is_dir
        self.size = size
        self.modified_ms = modified_ms


class ArchiveBrowser:
    """Browse .zip archives using Python's built-in zipfile module.

    Path format: "archive.zip!/inner/folder/" for navigation.
    Provides the same list_entries() / extract_entry() interface expected by
    ExplorerWidget's archive-browsing helpers.
    """

    def __init__(self):
        """Create a closed archive browser with no open zip.

        Initializes the instance and configures internal state.
        """
        self._zip_path: str = ""
        self._zip_file: zipfile.ZipFile | None = None

    def open(self, zip_path: str) -> bool:
        """Open.

        Manages open operations and coordinates related state changes for the component.

        Args:
            zip_path (str): Filesystem path to the target file or directory.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        self.close()
        try:
            self._zip_path = zip_path
            self._zip_file = zipfile.ZipFile(zip_path, "r")
            return True
        except (zipfile.BadZipFile, OSError):
            return False

    def close(self):
        """Close.

        Manages close operations and coordinates related state changes for the component.
        """
        if self._zip_file:
            try:
                self._zip_file.close()
            except OSError:
                pass
            self._zip_file = None
            self._zip_path = ""

    def list_entries(self, prefix: str = "") -> list[_ZipEntry]:
        """List first-level entries under prefix as _ZipEntry rows.

        Manages list entries operations and coordinates related state changes for the component.

        Args:
            prefix (str): The prefix parameter.

        Returns:
            list[_ZipEntry]: List of processed items or identifiers.
        """
        if not self._zip_file:
            return []

        entries: list[_ZipEntry] = []
        seen_dirs: set[str] = set()

        for info in self._zip_file.infolist():
            name = info.filename
            if not name:
                continue

            rel = name
            if prefix:
                if not name.startswith(prefix):
                    continue
                rel = name[len(prefix):]

            if not rel:
                continue

            modified_ms = 0
            try:
                modified_ms = int(
                    __import__("time").mktime(info.date_time + (0, 0, -1)) * 1000
                )
            except (TypeError, ValueError, OverflowError):
                pass

            parts = rel.rstrip("/").split("/")
            if len(parts) > 1:
                folder_name = parts[0]
                folder_path = prefix + folder_name + "/"
                if folder_path not in seen_dirs:
                    seen_dirs.add(folder_path)
                    entries.append(_ZipEntry(
                        archive_path=folder_path,
                        name=folder_name,
                        is_dir=True,
                        size=0,
                        modified_ms=modified_ms,
                    ))
            else:
                is_dir = rel.endswith("/")
                entries.append(_ZipEntry(
                    archive_path=name,
                    name=parts[0],
                    is_dir=is_dir,
                    size=info.file_size if not is_dir else 0,
                    modified_ms=modified_ms,
                ))

        return entries

    def extract_entry(self, entry_path: str, dest_dir: str) -> bool:
        """Extract one archive entry into dest_dir; True on success.

        Manages extract entry operations and coordinates related state changes for the component.

        Args:
            entry_path (str): Filesystem path to the target file or directory.
            dest_dir (str): The dest dir parameter.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        if not self._zip_file:
            return False
        try:
            self._zip_file.extract(entry_path, dest_dir)
            return True
        except (zipfile.BadZipFile, OSError):
            return False


# ═════════════════════════════════════════════════════════════════════════════
# UndoManager — undo/redo for file operations with QSettings persistence
# ═════════════════════════════════════════════════════════════════════════════
class UndoManager:
    """Tracks move, copy, delete, rename, new_folder operations.

    Max 20 operations; persists across sessions via QSettings.
    """

    MAX_HISTORY = 20

    def __init__(self):
        """Create undo/redo stacks backed by QSettings persistence.

        Initializes the instance and configures internal state.
        """
        self._settings = QSettings("Nexus", "NexusExplorer")
        self._undo_manager: list[dict] = []
        self._redo_stack: list[dict] = []
        self._load()

    def _load(self):
        """Load undo/redo history from QSettings.

        Note: distinct from ExplorerWidget._load(path) which lists a
        directory. Same name, different class/scope.
        """
        try:
            undo_raw = self._settings.value("undoManager/undo", [])
            redo_raw = self._settings.value("undoManager/redo", [])
            if isinstance(undo_raw, list):
                self._undo_manager = [op for op in undo_raw if isinstance(op, dict)]
            if isinstance(redo_raw, list):
                self._redo_stack = [op for op in redo_raw if isinstance(op, dict)]
        except (TypeError, ValueError):
            self._undo_manager = []
            self._redo_stack = []

    def _save(self):
        """Save configuration settings or analysis reports to persistent storage.

        Serializes current user preferences or generated report data to disk with integrity validation.
        """
        self._settings.setValue(
            "undoManager/undo", self._undo_manager[-self.MAX_HISTORY:])
        self._settings.setValue(
            "undoManager/redo", self._redo_stack[-self.MAX_HISTORY:])

    def record_move(self, src: str, dst: str):
        """Push a move operation onto the undo stack.

        Manages record move operations and coordinates related state changes for the component.

        Args:
            src (str): The src parameter.
            dst (str): The dst parameter.
        """
        self._push({"type": "move", "original": src,
                     "resulting": dst, "timestamp": time.time()})

    def record_copy(self, src: str, dst: str):
        """Push a copy operation onto the undo stack.

        Manages record copy operations and coordinates related state changes for the component.

        Args:
            src (str): The src parameter.
            dst (str): The dst parameter.
        """
        self._push({"type": "copy", "original": src,
                     "resulting": dst, "timestamp": time.time()})

    def record_delete(self, path: str):
        """Push a delete operation onto the undo stack.

        Manages record delete operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        self._push({"type": "delete", "original": path,
                     "resulting": "", "timestamp": time.time()})

    def record_rename(self, old: str, new: str):
        """Push a rename operation onto the undo stack.

        Manages record rename operations and coordinates related state changes for the component.

        Args:
            old (str): The old parameter.
            new (str): The new parameter.
        """
        self._push({"type": "rename", "original": old,
                     "resulting": new, "timestamp": time.time()})

    def record_new_folder(self, path: str, created_parents: list[str] | None = None):
        """Push a new-folder creation (plus created parents) for undo.

        Manages record new folder operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
            created_parents (list[str] | None): The created parents parameter.
        """
        self._push({"type": "new_folder", "original": path,
                     "resulting": path, "created_parents": created_parents or [], "timestamp": time.time()})

    def record_new_file(self, path: str, content: str = "", created_parents: list[str] | None = None):
        """Push a new-file creation (content, parents) for undo.

        Manages record new file operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
            content (str): The content parameter.
            created_parents (list[str] | None): The created parents parameter.
        """
        self._push({"type": "new_file", "original": path,
                     "resulting": path, "content": content,
                     "created_parents": created_parents or [], "timestamp": time.time()})

    def record_batch_create(self, created_files: list[tuple[str, str]], created_dirs: list[str], label: str = "Batch create"):
        """Push a batch file/dir creation under one label for undo.

        Manages record batch create operations and coordinates related state changes for the component.

        Args:
            created_files (list[tuple[str, str]]): The created files parameter.
            created_dirs (list[str]): The created dirs parameter.
            label (str): Display text string.
        """
        self._push({"type": "batch_create", "original": label,
                     "resulting": f"{len(created_files) + len(created_dirs)} items",
                     "created_files": created_files, "created_dirs": created_dirs, "timestamp": time.time()})

    def _push(self, op: dict):
        """Push.

        Manages push operations and coordinates related state changes for the component.

        Args:
            op (dict): The op parameter.
        """
        self._undo_manager.append(op)
        self._redo_stack.clear()
        if len(self._undo_manager) > self.MAX_HISTORY:
            self._undo_manager = self._undo_manager[-self.MAX_HISTORY:]
        self._save()

    def undo(self) -> str | None:
        """Undo.

        Manages undo operations and coordinates related state changes for the component.

        Returns:
            str | None: Formatted string or path.
        """
        if not self._undo_manager:
            return None
        op = self._undo_manager.pop()
        self._redo_stack.append(op)
        try:
            self._execute_undo(op)
            self._save()
            return f"Undid {op['type']}: {Path(op['original']).name}"
        except Exception as exc:
            log.warning("undo failed for %s: %s", op.get("original"), exc)
            self._undo_manager.append(op)
            self._redo_stack.pop()
            self._save()
            return None

    def redo(self) -> str | None:
        """Redo.

        Manages redo operations and coordinates related state changes for the component.

        Returns:
            str | None: Formatted string or path.
        """
        if not self._redo_stack:
            return None
        op = self._redo_stack.pop()
        self._undo_manager.append(op)
        try:
            self._execute_redo(op)
            self._save()
            return f"Redid {op['type']}: {Path(op['original']).name}"
        except Exception as exc:
            log.warning("redo failed for %s: %s", op.get("original"), exc)
            self._redo_stack.append(op)
            self._undo_manager.pop()
            self._save()
            return None

    def _execute_undo(self, op: dict):
        """Apply the inverse filesystem change for one recorded op.

        Manages execute undo operations and coordinates related state changes for the component.

        Args:
            op (dict): The op parameter.
        """
        op_type = op["type"]
        original = op["original"]
        resulting = op["resulting"]
        if op_type == "move":
            if os.path.exists(resulting):
                Path(original).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(resulting, original)
        elif op_type == "copy":
            if os.path.isdir(resulting):
                shutil.rmtree(resulting)
            elif os.path.exists(resulting):
                os.remove(resulting)
        elif op_type == "delete":
            log.warning("Cannot undo delete: %s", original)
        elif op_type == "rename":
            if os.path.exists(resulting):
                Path(original).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(resulting, original)
        elif op_type == "new_folder":
            if os.path.isdir(original):
                shutil.rmtree(original)
            for p_str in reversed(op.get("created_parents", [])):
                try:
                    p = Path(p_str)
                    if p.is_dir() and not any(p.iterdir()):
                        p.rmdir()
                except OSError:
                    pass
        elif op_type == "new_file":
            p = Path(original)
            if p.is_file():
                p.unlink(missing_ok=True)
            for p_str in reversed(op.get("created_parents", [])):
                try:
                    p = Path(p_str)
                    if p.is_dir() and not any(p.iterdir()):
                        p.rmdir()
                except OSError:
                    pass
        elif op_type == "batch_create":
            for file_path, _ in reversed(op.get("created_files", [])):
                try:
                    p = Path(file_path)
                    if p.is_file():
                        p.unlink(missing_ok=True)
                except OSError:
                    pass
            for dir_path in reversed(op.get("created_dirs", [])):
                try:
                    p = Path(dir_path)
                    if p.is_dir() and not any(p.iterdir()):
                        p.rmdir()
                except OSError:
                    pass

    def _execute_redo(self, op: dict):
        """Re-apply the forward filesystem change for one recorded op.

        Manages execute redo operations and coordinates related state changes for the component.

        Args:
            op (dict): The op parameter.
        """
        op_type = op["type"]
        original = op["original"]
        resulting = op["resulting"]
        if op_type == "move":
            if os.path.exists(original):
                Path(resulting).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(original, resulting)
        elif op_type == "copy":
            if os.path.isdir(original):
                shutil.copytree(original, resulting)
            elif os.path.exists(original):
                shutil.copy2(original, resulting)
        elif op_type == "delete":
            if os.path.isdir(original):
                shutil.rmtree(original)
            elif os.path.exists(original):
                os.remove(original)
        elif op_type == "rename":
            if os.path.exists(original):
                Path(resulting).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(original, resulting)
        elif op_type == "new_folder":
            Path(original).mkdir(parents=True, exist_ok=True)
        elif op_type == "new_file":
            p = Path(original)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(op.get("content", ""), encoding="utf-8")
        elif op_type == "batch_create":
            for dir_path in op.get("created_dirs", []):
                Path(dir_path).mkdir(parents=True, exist_ok=True)
            for file_path, content in op.get("created_files", []):
                p = Path(file_path)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")

    def can_undo(self) -> bool:
        """Return True when the undo stack is non-empty.

        Manages can undo operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return len(self._undo_manager) > 0

    def can_redo(self) -> bool:
        """Return True when the redo stack is non-empty.

        Manages can redo operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return len(self._redo_stack) > 0

    def undo_description(self) -> str | None:
        """Describe the top undo op, or None when the stack is empty.

        Manages undo description operations and coordinates related state changes for the component.

        Returns:
            str | None: Formatted string or path.
        """
        if not self._undo_manager:
            return None
        op = self._undo_manager[-1]
        return f"Undo {op['type']}: {Path(op['original']).name}"

    def redo_description(self) -> str | None:
        """Describe the top redo op, or None when the stack is empty.

        Manages redo description operations and coordinates related state changes for the component.

        Returns:
            str | None: Formatted string or path.
        """
        if not self._redo_stack:
            return None
        op = self._redo_stack[-1]
        return f"Redo {op['type']}: {Path(op['original']).name}"


# ═════════════════════════════════════════════════════════════════════════════
# ShortcutsDialog — keyboard shortcuts reference
# ═════════════════════════════════════════════════════════════════════════════
class ShortcutsDialog(QDialog):
    """Shortcutsdialog.

    Manages ShortcutsDialog operations and coordinates related state changes for the component.
    """

    _SHORTCUTS = [
        ("Navigation", [
            ("Alt + \u2190", "Back"),
            ("Alt + \u2192", "Forward"),
            ("Alt + \u2191 / Backspace", "Go Up"),
            ("Ctrl + L", "Edit Address"),
            ("Ctrl + G", "Go to Path"),
            ("Ctrl + 1\u20139", "Quick Bookmarks"),
        ]),
        ("View & Panels", [
            ("Ctrl + H", "Toggle Sidebar"),
            ("Ctrl + D", "Toggle Dual Pane"),
            ("Ctrl + `", "Toggle Integrated Terminal"),
            ("F12", "Debug Overlay"),
            ("F1 / Shift + ?", "Keyboard Shortcuts Help"),
        ]),
        ("File Creation & Scaffolding", [
            ("Ctrl + Shift + N / F7", "New Folder"),
            ("Ctrl + Alt + N", "Create Deep Nested Folders"),
            ("Ctrl + N", "New File"),
            ("Ctrl + Alt + F", "Create Deep Nested File"),
            ("Ctrl + Shift + B", "Batch Scaffold Project / Tree"),
        ]),
        ("File Operations", [
            ("F2", "Inline Rename"),
            ("Ctrl + Shift + R", "Bulk Rename (5 Modes)"),
            ("Ctrl + C", "Copy to Staging Shelf"),
            ("Ctrl + X", "Cut to Staging Shelf"),
            ("Ctrl + V", "Paste Staged Items Here"),
            ("F8 / Delete", "Move to Recycle Bin"),
            ("Shift + Delete", "Permanently Delete"),
            ("Ctrl + A", "Select All"),
        ]),
        ("Search & Power Tools", [
            ("Ctrl + F / F3", "Instant Search / Filter"),
            ("Ctrl + Shift + F", "Find Bit-for-Bit Duplicates"),
            ("Ctrl + Shift + P", "Command Palette"),
            ("Space", "Quick Look File Preview"),
        ]),
        ("Tabs & History", [
            ("Ctrl + T", "Open New Tab"),
            ("Ctrl + W", "Close Current Tab"),
            ("Ctrl + Z", "Undo Last Action"),
            ("Ctrl + Y / Ctrl+Shift+Z", "Redo Action"),
            ("F5 / Shift + F5", "Refresh Current Directory"),
        ]),
    ]

    def __init__(self, parent=None):
        """Build the shortcuts table dialog from _SHORTCUTS categories.

        Initializes the instance and configures internal state.

        Args:
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setObjectName("ShortcutsDialog")
        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumSize(520, 480)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        title = QLabel("Keyboard Shortcuts")
        title.setStyleSheet("font-size: 13pt; font-weight: 700; color: #FFFFFF;")
        lay.addWidget(title)

        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Shortcut", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().resizeSection(0, 180)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)

        total = sum(len(items) for _, items in self._SHORTCUTS)
        self.table.setRowCount(total)

        row = 0
        for category, shortcuts in self._SHORTCUTS:
            for i, (key, desc) in enumerate(shortcuts):
                key_item = QTableWidgetItem(key)
                key_item.setForeground(QColor("#90CAF9"))
                key_font = QFont()
                key_font.setBold(True)
                key_item.setFont(key_font)
                desc_item = QTableWidgetItem(desc)
                self.table.setItem(row, 0, key_item)
                self.table.setItem(row, 1, desc_item)
                row += 1

        self.table.verticalHeader().setDefaultSectionSize(32)
        lay.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        lay.addLayout(btn_row)


# ═════════════════════════════════════════════════════════════════════════════
# Creation Dialogs: Nested Folders, Nested Files, and Batch Scaffolding
# ═════════════════════════════════════════════════════════════════════════════

class NestedFolderDialog(QDialog):
    """Nestedfolderdialog.

    Manages NestedFolderDialog operations and coordinates related state changes for the component.
    """

    def __init__(self, current_dir: Path, parent=None):
        """Build the nested-folder dialog with presets and live preview.

        Initializes the instance and configures internal state.

        Args:
            current_dir (Path): The current dir parameter.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setWindowTitle("Create Nested Folders")
        self.setMinimumWidth(540)
        self.current_dir = current_dir

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Create Nested Folder Structure")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #60cdff;")
        lay.addWidget(title)

        desc = QLabel(
            f"Enter a folder name or multi-level path to create under: "
            f"<b>{current_dir.name}</b><br>"
            f"<span style='color: #888; font-size: 11px;'>Paths with forward or backslashes "
            f"(e.g. <code>src/api/v1/endpoints</code>) will automatically create all missing parent folders.</span>"
        )
        desc.setWordWrap(True)
        lay.addWidget(desc)

        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("e.g. components/ui/modals or feature_branch")
        self.input_path.setStyleSheet("padding: 8px 12px; font-size: 13px; border-radius: 6px;")
        self.input_path.textChanged.connect(self._update_preview)
        lay.addWidget(self.input_path)

        # Quick presets row
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(6)
        presets_lbl = QLabel("Quick Paths:")
        presets_lbl.setStyleSheet("color: #888; font-size: 11px;")
        presets_layout.addWidget(presets_lbl)

        for p_name, p_val in [
            ("components/ui", "components/ui"),
            ("api/v1/routes", "api/v1/routes"),
            ("tests/unit", "tests/unit"),
            ("docs/assets", "docs/assets"),
        ]:
            btn = QPushButton(p_name)
            btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
            btn.clicked.connect(lambda _c=False, v=p_val: self.input_path.setText(v))
            presets_layout.addWidget(btn)
        presets_layout.addStretch(1)
        lay.addLayout(presets_layout)

        # Target path preview
        self.preview_lbl = QLabel()
        self.preview_lbl.setStyleSheet(
            "color: #38bdf8; font-family: monospace; font-size: 12px; padding: 8px; "
            "background: rgba(0,0,0,0.25); border-radius: 6px;"
        )
        self.preview_lbl.setWordWrap(True)
        lay.addWidget(self.preview_lbl)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_create = QPushButton("Create Folders")
        self.btn_create.setDefault(True)
        self.btn_create.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_create)
        lay.addLayout(btn_box)

        self._update_preview()

    def _update_preview(self):
        """Preview the resolved target folder and gate the Create button.

        Manages update preview operations and coordinates related state changes for the component.
        """
        txt = self.input_path.text().strip().lstrip("/\\")
        if txt:
            target = (self.current_dir / txt).resolve()
            self.preview_lbl.setText(f"Target: {target}")
            self.btn_create.setEnabled(True)
        else:
            self.preview_lbl.setText(f"Target: {self.current_dir}")
            self.btn_create.setEnabled(False)

    def get_target_path(self) -> str:
        """Return the typed relative folder path.

        Manages get target path operations and coordinates related state changes for the component.

        Returns:
            str: Formatted string or path.
        """
        return self.input_path.text().strip()


class NestedFileDialog(QDialog):
    """Nestedfiledialog.

    Manages NestedFileDialog operations and coordinates related state changes for the component.
    """

    def __init__(self, current_dir: Path, parent=None):
        """Build the nested-file dialog with templates and live preview.

        Initializes the instance and configures internal state.

        Args:
            current_dir (Path): The current dir parameter.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setWindowTitle("Create New File in Nested Path")
        self.setMinimumWidth(580)
        self.current_dir = current_dir

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Create New File & Nested Directories")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #60cdff;")
        lay.addWidget(title)

        desc = QLabel(
            f"Enter a relative file path (e.g. <code>src/controllers/auth.py</code> "
            f"or <code>components/Button.tsx</code>).<br><span style='color: #888; font-size: 11px;'>"
            f"Any missing intermediate directories will be automatically created.</span>"
        )
        desc.setWordWrap(True)
        lay.addWidget(desc)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("e.g. src/utils/helpers.py")
        self.input_path.setStyleSheet("padding: 8px 12px; font-size: 13px; border-radius: 6px;")
        self.input_path.textChanged.connect(self._on_path_changed)
        path_row.addWidget(self.input_path, stretch=1)
        lay.addLayout(path_row)

        # Template selector
        tpl_row = QHBoxLayout()
        tpl_row.setSpacing(8)
        tpl_lbl = QLabel("Template:")
        tpl_row.addWidget(tpl_lbl)

        self.combo_template = QComboBox()
        self.combo_template.addItem("Blank File", "")
        for ext, info in FILE_TEMPLATES.items():
            self.combo_template.addItem(f"{info['label']}", ext)
        self.combo_template.currentIndexChanged.connect(self._on_template_selected)
        tpl_row.addWidget(self.combo_template, stretch=1)
        lay.addLayout(tpl_row)

        # Initial file content editor
        content_lbl = QLabel("Initial File Content (Optional):")
        content_lbl.setStyleSheet("color: #888; font-size: 11px;")
        lay.addWidget(content_lbl)

        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Leave blank or customize starter code...")
        self.content_edit.setMaximumHeight(130)
        self.content_edit.setStyleSheet(
            "font-family: monospace; font-size: 12px; background: rgba(0,0,0,0.25); "
            "border-radius: 6px; padding: 6px;"
        )
        lay.addWidget(self.content_edit)

        # Target path preview
        self.preview_lbl = QLabel()
        self.preview_lbl.setStyleSheet(
            "color: #38bdf8; font-family: monospace; font-size: 12px; padding: 8px; "
            "background: rgba(0,0,0,0.25); border-radius: 6px;"
        )
        self.preview_lbl.setWordWrap(True)
        lay.addWidget(self.preview_lbl)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_create = QPushButton("Create File")
        self.btn_create.setDefault(True)
        self.btn_create.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_create)
        lay.addLayout(btn_box)

        self._update_preview()

    def _on_path_changed(self, text: str):
        """Auto-select the template matching the typed extension.

        Manages on path changed operations and coordinates related state changes for the component.

        Args:
            text (str): Display text string.
        """
        ext = Path(text).suffix.lower()
        if ext in FILE_TEMPLATES:
            idx = self.combo_template.findData(ext)
            if idx >= 0:
                self.combo_template.blockSignals(True)
                self.combo_template.setCurrentIndex(idx)
                self.combo_template.blockSignals(False)
                if not self.content_edit.toPlainText().strip():
                    self.content_edit.setPlainText(FILE_TEMPLATES[ext]["content"])
        self._update_preview()

    def _on_template_selected(self, index: int):
        """Load template content and append its extension when missing.

        Manages on template selected operations and coordinates related state changes for the component.

        Args:
            index (int): The index parameter.
        """
        ext = self.combo_template.currentData()
        if ext and ext in FILE_TEMPLATES:
            self.content_edit.setPlainText(FILE_TEMPLATES[ext]["content"])
            curr_txt = self.input_path.text().strip()
            if curr_txt and not Path(curr_txt).suffix:
                self.input_path.setText(curr_txt + ext)
        elif not ext:
            self.content_edit.clear()

    def _update_preview(self):
        """Preview the resolved target file and gate the Create button.

        Manages update preview operations and coordinates related state changes for the component.
        """
        txt = self.input_path.text().strip().lstrip("/\\")
        if txt:
            target = (self.current_dir / txt).resolve()
            self.preview_lbl.setText(f"Creating: {target}")
            self.btn_create.setEnabled(True)
        else:
            self.preview_lbl.setText("Enter a file path above...")
            self.btn_create.setEnabled(False)

    def get_result(self) -> tuple[str, str]:
        """Return the typed path plus the editor's initial content.

        Manages get result operations and coordinates related state changes for the component.

        Returns:
            tuple[str, str]: Formatted string or path.
        """
        return self.input_path.text().strip(), self.content_edit.toPlainText()


class BatchScaffoldDialog(QDialog):
    """Batchscaffolddialog.

    Manages BatchScaffoldDialog operations and coordinates related state changes for the component.
    """

    def __init__(self, current_dir: Path, parent=None):
        """Build the batch scaffold dialog with presets and spec editor.

        Initializes the instance and configures internal state.

        Args:
            current_dir (Path): The current dir parameter.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setWindowTitle("Batch Scaffold Project / Directory Hierarchy")
        self.setMinimumWidth(660)
        self.setMinimumHeight(540)
        self.current_dir = current_dir

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Batch Directory & File Hierarchy Scaffolder")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #60cdff;")
        lay.addWidget(title)

        desc = QLabel(
            "Type or paste an indented directory tree or a list of slash-separated paths. "
            "All folders and starter template files will be scaffolded atomically."
        )
        desc.setWordWrap(True)
        lay.addWidget(desc)

        # Preset selection
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        preset_lbl = QLabel("Load Project Preset:")
        preset_row.addWidget(preset_lbl)

        self.combo_presets = QComboBox()
        self.combo_presets.addItem("Custom Structure...", "")
        for name in PROJECT_SCAFFOLD_PRESETS.keys():
            self.combo_presets.addItem(name, name)
        self.combo_presets.currentIndexChanged.connect(self._on_preset_selected)
        preset_row.addWidget(self.combo_presets, stretch=1)
        lay.addLayout(preset_row)

        # Text editor for specification
        self.spec_edit = QTextEdit()
        self.spec_edit.setStyleSheet(
            "font-family: monospace; font-size: 12px; background: rgba(0,0,0,0.3); "
            "border-radius: 6px; padding: 8px;"
        )
        self.spec_edit.setPlaceholderText(
            "Example 1 (Indented tree):\n"
            "src/\n"
            "  components/\n"
            "    Button.tsx\n"
            "    Modal.tsx\n"
            "  utils/\n"
            "    formatters.ts\n"
            "  index.ts\n"
            "README.md\n\n"
            "Example 2 (Path list):\n"
            "app/api/v1/auth.py\n"
            "app/core/config.py\n"
            "requirements.txt\n"
        )
        lay.addWidget(self.spec_edit, stretch=1)

        # Buttons
        btn_box = QHBoxLayout()
        self.status_lbl = QLabel(f"Target root: <b>{self.current_dir.name}</b>")
        self.status_lbl.setStyleSheet("color: #888; font-size: 11px;")
        btn_box.addWidget(self.status_lbl, stretch=1)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_create = QPushButton("Scaffold Hierarchy")
        self.btn_create.setDefault(True)
        self.btn_create.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_create)
        lay.addLayout(btn_box)

    def _on_preset_selected(self, index: int):
        """Load the chosen project preset text into the spec editor.

        Manages on preset selected operations and coordinates related state changes for the component.

        Args:
            index (int): The index parameter.
        """
        preset_name = self.combo_presets.currentData()
        if preset_name and preset_name in PROJECT_SCAFFOLD_PRESETS:
            self.spec_edit.setPlainText(PROJECT_SCAFFOLD_PRESETS[preset_name])

    def get_spec_text(self) -> str:
        """Return the scaffold specification text.

        Manages get spec text operations and coordinates related state changes for the component.

        Returns:
            str: Formatted string or path.
        """
        return self.spec_edit.toPlainText()


# ═════════════════════════════════════════════════════════════════════════════
# ExplorerWidget — the complete file explorer
# ═════════════════════════════════════════════════════════════════════════════
class ExplorerWidget(QWidget):
    """Explorerwidget.

    Manages ExplorerWidget operations and coordinates related state changes for the component.
    """

    def __init__(self, start_path: str = "", parent=None, root: str = ""):
        """Build the full explorer: tabs, views, panels, queues, and managers.

        Initializes the instance and configures internal state.

        Args:
            start_path (str): Filesystem path to the target file or directory.
            parent: Parent window or shell controller instance.
            root (str): Filesystem path to the target file or directory.
        """
        super().__init__(parent)
        self.setObjectName("NexusRoot")
        self.engine = Engine()
        # Monotonic token guarding against stale async listings (e.g. the
        # initial default-tab load racing a session restore).
        self._load_seq = 0
        if root and not start_path:
            start_path = root
        self.icons = IconThumbs()
        self.icons.set_fluent_ext_icon(_fluent_ext_icon)
        self.model = FileTableModel(self.icons)
        self.proxy = SortProxy()
        self.proxy.setSourceModel(self.model)
        self._tabs: list[dict] = []
        self._current_tab = -1
        self._sidebar_visible = True
        self._debug_visible = False
        self._dual_pane = False
        self._pending_view_mode: str | None = None
        self._debug = DebugOverlay()
        self._drag_paths: list[str] = []
        self.setMouseTracking(True)

        # Status bar click-cycle mode (0=items, 1=selected, 2=disk free)
        self._status_mode = 0
        self._status_disk_text = ""

        # Sort state for F6/Shift+F6 cycling
        self._sort_cycle_col = 0
        self._SORT_COLUMNS = [
            ("Name", 0),
            ("Modified", 1),
            ("Type", 2),
            ("Size", 3),
        ]

        # Archive browsing state
        self._archive_mode = False
        self._archive_path: str = ""
        self._archive_reader = None
        self._archive_current_prefix: str = ""

        # Second pane state (for dual pane mode)
        self._right_model = FileTableModel(self.icons)
        self._right_proxy = SortProxy()
        self._right_proxy.setSourceModel(self._right_model)
        self._right_tabs: list[dict] = []
        self._right_current_tab = -1

        # Phase 1 features
        self._quicklook = QuickLookPopup(self.icons)
        self._folder_sizes = FolderSizeCalculator()
        self._color_tags = ColorTagManager()
        self._smart_folders = SmartFolderManager()
        self._undo_manager = UndoManager()
        self._zip_browser = ArchiveBrowser()

        # Bookmarks (Ctrl+1-9 quick paths)
        self._bookmarks: list[str] = []
        self._load_bookmarks()

        # Connect color tags to model for visual indicators
        self.model.set_tags_manager(self._color_tags)

        # Transfer queue for serialized operations (FFI-first, CLI fallback)
        from nexus_transfer_monitor import TransferMonitorDialog
        from nexus_transfer_queue import TransferQueue
        self._transfer_queue = TransferQueue(self.engine, self)
        self._transfer_queue.job_started.connect(self._on_transfer_started)
        self._transfer_queue.job_progress.connect(self._on_transfer_progress)
        self._transfer_queue.job_completed.connect(self._on_transfer_completed)
        self._transfer_queue.job_cancelled.connect(self._on_transfer_cancelled)
        self._transfer_queue.queue_empty.connect(self._on_transfer_queue_empty)
        self._transfer_queue.job_added.connect(self._on_transfer_added)
        self._transfer_monitor: TransferMonitorDialog | None = None

        self.setStyleSheet(DARK_QSS)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ═════════════════════════════════════════════════════════════════════
        # ── TIER 1: WINDOWS 11 MODERN TAB BAR ROW ───────────────────────────
        # ═════════════════════════════════════════════════════════════════════
        self.tab_container = QWidget()
        self.tab_container.setObjectName("TabBarContainer")
        tab_layout = QHBoxLayout(self.tab_container)
        tab_layout.setContentsMargins(4, 2, 4, 0)
        tab_layout.setSpacing(4)

        self.tabbar = QTabBar()
        self.tabbar.setObjectName("TabBar")
        self.tabbar.setTabsClosable(True)
        self.tabbar.setExpanding(False)
        self.tabbar.setMovable(True)
        self.tabbar.tabCloseRequested.connect(self._close_tab)
        self.tabbar.currentChanged.connect(self._switch_tab)
        self.tabbar.tabMoved.connect(self._on_tab_moved)
        tab_layout.addWidget(self.tabbar)

        self.btn_newtab = QToolButton()
        self.btn_newtab.setObjectName("NewTabBtn")
        self.btn_newtab.setIcon(_fluent_action("plus", size=_scaled(13)))
        self.btn_newtab.setToolTip("New tab (Ctrl+T)")
        self.btn_newtab.clicked.connect(lambda: self.add_tab(os.path.expanduser("~")))
        tab_layout.addWidget(self.btn_newtab)
        tab_layout.addStretch(1)
        main_layout.addWidget(self.tab_container)

        # ═════════════════════════════════════════════════════════════════════
        # ── TIER 2: NAVIGATION & FULL-WIDTH ADDRESS & SEARCH BAR ────────────
        # ═════════════════════════════════════════════════════════════════════
        nav_addr_container = QWidget()
        nav_addr_container.setObjectName("NavAddressContainer")
        nav_addr_layout = QHBoxLayout(nav_addr_container)
        nav_addr_layout.setContentsMargins(8, 4, 8, 4)
        nav_addr_layout.setSpacing(6)

        def nav_btn(icon_name, tip, slot):
            """Create a 30x28 navigation tool button with icon and tooltip.

            Manages nav btn operations and coordinates related state changes for the component.

            Args:
                icon_name: The icon name parameter.
                tip: The tip parameter.
                slot: The slot parameter.
            """
            b = QToolButton()
            b.setIcon(_fluent_icon(icon_name, _scaled(18), _FLUENT_DEFAULT))
            b.setToolTip(tip)
            b.clicked.connect(slot)
            b.setFixedSize(_scaled(30), _scaled(28))
            return b

        def action_btn(icon_name, tip, slot, accent: bool = False) -> QToolButton:
            """Create a 30x28 command-bar button, optionally accented.

            Manages action btn operations and coordinates related state changes for the component.

            Args:
                icon_name: The icon name parameter.
                tip: The tip parameter.
                slot: The slot parameter.
                accent (bool): Whether to apply the primary accent styling.

            Returns:
                QToolButton: Result of the operation.
            """
            b = QToolButton()
            b.setIcon(_fluent_action(icon_name, accent=accent, size=_scaled(18)))
            b.setToolTip(tip)
            b.clicked.connect(slot)
            b.setFixedSize(_scaled(30), _scaled(28))
            b.setIconSize(QSize(_scaled(18), _scaled(18)))
            return b

        def sep() -> QFrame:
            """Sep.

            Manages sep operations and coordinates related state changes for the component.

            Returns:
                QFrame: Result of the operation.
            """
            s = QFrame()
            s.setFrameShape(QFrame.Shape.VLine)
            s.setFrameShadow(QFrame.Shadow.Sunken)
            s.setFixedHeight(_scaled(20))
            s.setStyleSheet("color: rgba(255,255,255,0.12); max-width: 1px; margin: 0 4px;")
            return s

        # Nav Buttons (Back, Forward, Up, Refresh)
        self.btn_back = nav_btn("back", "Back (Alt+←)", self.go_back)
        self.btn_fwd = nav_btn("forward", "Forward (Alt+→)", self.go_forward)
        self.btn_up = nav_btn("up", "Up (Backspace)", self.go_up)
        self.btn_refresh = nav_btn("refresh", "Refresh (Shift+F5)", self._reload_current)
        nav_addr_layout.addWidget(self.btn_back)
        nav_addr_layout.addWidget(self.btn_fwd)
        nav_addr_layout.addWidget(self.btn_up)
        nav_addr_layout.addWidget(self.btn_refresh)

        # Full-Width Breadcrumb / Address Bar
        addr_box = QWidget()
        addr_box.setObjectName("AddressBarBox")
        addr_box_lay = QHBoxLayout(addr_box)
        addr_box_lay.setContentsMargins(4, 0, 4, 0)
        addr_box_lay.setSpacing(0)

        self.crumbs = CrumbBar()
        self.crumbs.navigate.connect(self.navigate)
        self.crumbs.editRequested.connect(self._start_edit_path)
        self.addr = QLineEdit()
        self.addr.setObjectName("AddrBar")
        self.addr.hide()
        self.addr.returnPressed.connect(self._commit_edit_path)
        self.addr.editingFinished.connect(self._on_addr_editing_finished)
        self.addr.setMinimumHeight(28)

        addr_box_lay.addWidget(self.crumbs, 1)
        addr_box_lay.addWidget(self.addr, 1)
        nav_addr_layout.addWidget(addr_box, 1)

        # Search Bar
        search_box = QWidget()
        search_box.setObjectName("SearchBoxContainer")
        search_box_lay = QHBoxLayout(search_box)
        search_box_lay.setContentsMargins(0, 0, 0, 0)
        search_box_lay.setSpacing(0)

        self.filter = QLineEdit()
        self.filter.setObjectName("SearchInput")
        self.filter.setPlaceholderText("Search current folder…")
        self.filter.setMinimumWidth(200)
        self.filter.setMaximumWidth(320)
        self.filter.setFixedHeight(28)
        self.filter.textChanged.connect(self.proxy.setFilterFixedString)
        self.filter.returnPressed.connect(self._search)
        search_box_lay.addWidget(self.filter)
        nav_addr_layout.addWidget(search_box)

        main_layout.addWidget(nav_addr_container)

        # ═════════════════════════════════════════════════════════════════════
        # ── TIER 3: WINDOWS 11 FLUENT COMMAND BAR ────────────────────────────
        # ═════════════════════════════════════════════════════════════════════
        command_container = QWidget()
        command_container.setObjectName("CommandBarContainer")
        cmd_layout = QHBoxLayout(command_container)
        cmd_layout.setContentsMargins(8, 3, 8, 3)
        cmd_layout.setSpacing(4)

        # + New Dropdown Button
        self.btn_new = QToolButton()
        self.btn_new.setObjectName("NewItemBtn")
        self.btn_new.setText(" New")
        self.btn_new.setIcon(_fluent_action("new_folder", size=_scaled(18)))
        self.btn_new.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_new.setToolTip("New item / folder / file (Ctrl+Shift+N)")
        self.btn_new.setMinimumHeight(28)
        self.btn_new.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.btn_new.clicked.connect(self._new_folder)

        new_menu = QMenu(self.btn_new)
        act_new_folder = new_menu.addAction("New Folder\tCtrl+Shift+N")
        if hasattr(act_new_folder, "setIcon"):
            act_new_folder.setIcon(_fluent_action("new_folder", size=16))
        act_new_folder.triggered.connect(self._new_folder)

        act_new_nested_folder = new_menu.addAction("New Nested Folders…\tCtrl+Alt+N")
        if hasattr(act_new_nested_folder, "setIcon"):
            act_new_nested_folder.setIcon(_fluent_action("folder", size=16))
        act_new_nested_folder.triggered.connect(self._new_nested_folder)

        new_menu.addSeparator()
        act_new_file = new_menu.addAction("New File…\tCtrl+N")
        if hasattr(act_new_file, "setIcon"):
            act_new_file.setIcon(_fluent_action("new_file", size=16))
        act_new_file.triggered.connect(self._new_file)

        act_new_nested_file = new_menu.addAction("New File in Nested Path…\tCtrl+Alt+F")
        if hasattr(act_new_nested_file, "setIcon"):
            act_new_nested_file.setIcon(_fluent_action("new_file", size=16))
        act_new_nested_file.triggered.connect(self._new_nested_file)

        new_menu.addSeparator()
        act_batch_scaffold = new_menu.addAction("Batch Scaffold Project / Tree…\tCtrl+Shift+B")
        if hasattr(act_batch_scaffold, "setIcon"):
            act_batch_scaffold.setIcon(_fluent_action("copy", size=16))
        act_batch_scaffold.triggered.connect(self._batch_scaffold)

        self.btn_new.setMenu(new_menu)
        self.btn_newfolder = self.btn_new  # backward compat alias
        cmd_layout.addWidget(self.btn_new)

        cmd_layout.addWidget(sep())

        # Operations: Cut / Copy / Paste / Rename / Delete
        self.btn_cut = action_btn("cut", "Cut (Ctrl+X)", lambda: self._clip("cut"))
        self.btn_copy = action_btn("copy", "Copy (Ctrl+C)", lambda: self._clip("copy"))
        self.btn_paste = action_btn("paste", "Paste (Ctrl+V)", self._paste)
        self.btn_rename = action_btn("rename", "Rename (F2)", self._rename)
        self.btn_delete = action_btn("delete", "Delete (Del)", self._delete)
        for b in (self.btn_cut, self.btn_copy, self.btn_paste, self.btn_rename, self.btn_delete):
            cmd_layout.addWidget(b)

        cmd_layout.addWidget(sep())

        # Sort Dropdown
        self.btn_sort = QToolButton()
        self.btn_sort.setObjectName("SortBtn")
        self.btn_sort.setText(" Sort")
        self.btn_sort.setIcon(_fluent_action("sort", size=_scaled(16)))
        self.btn_sort.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_sort.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        sort_menu = QMenu(self.btn_sort)
        for label, col_idx in [
            ("Name", 0),
            ("Date modified", 1),
            ("Type", 2),
            ("Size", 3),
        ]:
            sub = sort_menu.addMenu(label)
            asc = sub.addAction("Ascending")
            asc.triggered.connect(lambda _c=False, c=col_idx: self.proxy.sort(c, Qt.SortOrder.AscendingOrder))
            desc = sub.addAction("Descending")
            desc.triggered.connect(lambda _c=False, c=col_idx: self.proxy.sort(c, Qt.SortOrder.DescendingOrder))
        self.btn_sort.setMenu(sort_menu)
        cmd_layout.addWidget(self.btn_sort)

        # View Dropdown
        self.btn_view = QToolButton()
        self.btn_view.setObjectName("ViewBtn")
        self.btn_view.setText(" View")
        self.btn_view.setIcon(_fluent_action("view_icon", size=_scaled(16)))
        self.btn_view.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_view.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        view_menu = QMenu(self.btn_view)
        act_details = view_menu.addAction("Details view")
        act_details.triggered.connect(lambda: self._set_view_mode("table"))
        act_icons = view_menu.addAction("Large icons view")
        act_icons.triggered.connect(lambda: self._set_view_mode("icons"))
        view_menu.addSeparator()
        act_dual_toggle = view_menu.addAction("Toggle Dual Pane")
        act_dual_toggle.triggered.connect(self._toggle_dual_pane)
        self.btn_view.setMenu(view_menu)
        self.view_toggle = self.btn_view  # backward compat alias
        cmd_layout.addWidget(self.btn_view)

        cmd_layout.addWidget(sep())

        # Dual Pane button
        self.btn_dual = action_btn("dual_pane", "Dual pane (Ctrl+D)", self._toggle_dual_pane)
        self.btn_dual.setCheckable(True)
        cmd_layout.addWidget(self.btn_dual)

        # Quick Look button
        self.btn_quicklook = action_btn("quicklook", "Quick Look (Space)", self._quick_look)
        cmd_layout.addWidget(self.btn_quicklook)

        # Transfers button
        self.btn_transfers = action_btn(
            "transfer", "Transfers (progress, pause, resume, cancel)", self.open_transfer_monitor
        )
        cmd_layout.addWidget(self.btn_transfers)

        # ··· More Options button
        self.btn_more = QToolButton()
        self.btn_more.setObjectName("MoreBtn")
        self.btn_more.setText(" ···")
        self.btn_more.setToolTip("More options")
        self.btn_more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more_menu = QMenu(self.btn_more)
        more_menu.addAction("Find Duplicates (Ctrl+Shift+F)", self._open_duplicate_finder)
        more_menu.addAction("Bulk Rename… (Ctrl+B)", self._bulk_rename)
        more_menu.addAction("Save as Smart Folder", self._add_current_as_smart_folder)
        more_menu.addAction("Open Terminal (Ctrl+`)", self._toggle_terminal)
        more_menu.addAction("Keyboard Shortcuts (Shift+?)", self._show_shortcuts)
        self.btn_more.setMenu(more_menu)
        cmd_layout.addWidget(self.btn_more)

        cmd_layout.addStretch(1)

        # Right Side: Navigation Pane & Details / Preview Pane toggle
        self.btn_sidebar = action_btn("sidebar", "Toggle Navigation Pane (Ctrl+H)", self._toggle_sidebar)
        self.btn_sidebar.setCheckable(True)
        self.btn_sidebar.setChecked(True)
        cmd_layout.addWidget(self.btn_sidebar)

        self.btn_preview = QToolButton()
        self.btn_preview.setObjectName("DetailsBtn")
        self.btn_preview.setText(" Details")
        self.btn_preview.setIcon(_fluent_action("preview", size=_scaled(16)))
        self.btn_preview.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_preview.setToolTip("Toggle preview / details pane")
        self.btn_preview.setCheckable(True)
        self.btn_preview.setChecked(True)
        self.btn_preview.clicked.connect(self._toggle_preview)
        cmd_layout.addWidget(self.btn_preview)

        main_layout.addWidget(command_container)

        # ── center: sidebar | views | preview ─────────────────────────────
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(2)
        self.splitter.setChildrenCollapsible(False)

        # sidebar
        self.side = QWidget()
        self.side.setObjectName("SidePanel")
        self.side.setMinimumWidth(160)
        self.side.setMaximumWidth(260)
        sv = QVBoxLayout(self.side)
        sv.setContentsMargins(0, 6, 0, 6)
        sv.setSpacing(2)

        t1 = QLabel("QUICK ACCESS")
        t1.setObjectName("SideTitle")
        sv.addWidget(t1)
        self.quick_list = QListWidget()
        for label, target, icon_name in QUICK_FOLDERS:
            it = QListWidgetItem(_fluent_sidebar(icon_name, _scaled(16)), label)
            it.setData(Qt.ItemDataRole.UserRole, os.path.expanduser(target))
            self.quick_list.addItem(it)
        self.quick_list.itemClicked.connect(
            lambda it: self.navigate(it.data(Qt.ItemDataRole.UserRole)))
        sv.addWidget(self.quick_list, 2)

        t2 = QLabel("FOLDERS")
        t2.setObjectName("SideTitle")
        sv.addWidget(t2)

        # Replace flat drive list with folder tree
        try:
            from nexus_folder_tree import FolderTreeWidget
            self.folder_tree = FolderTreeWidget()
            self.folder_tree.navigate_to.connect(self.navigate)
            sv.addWidget(self.folder_tree, 5)
        except ImportError:
            log.warning("nexus_folder_tree not available; sidebar folder tree disabled")
            self.folder_tree = None

        t3 = QLabel("SMART FOLDERS")
        t3.setObjectName("SideTitle")
        sv.addWidget(t3)
        self.smart_list = QListWidget()
        self.smart_list.itemClicked.connect(
            lambda it: self._open_smart_folder(it.data(Qt.ItemDataRole.UserRole)))
        self.smart_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.smart_list.customContextMenuRequested.connect(self._smart_folder_context_menu)
        sv.addWidget(self.smart_list, 2)
        self._refresh_smart_folders()
        self.splitter.addWidget(self.side)

        # views (table + icon)
        self.stack = QStackedWidget()
        self._view_mode = "table"
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(_scaled(28))
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c, w in ((1, 150), (2, 90), (3, 90)):
            self.table.setColumnWidth(c, _scaled(w))
        self.table.doubleClicked.connect(self._activate)
        self.table.clicked.connect(self._on_table_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.selectionModel().selectionChanged.connect(
            lambda *_: self._update_status(self.table))
        self.table.selectionModel().currentChanged.connect(
            self._on_current_changed)
        self.table.setShowGrid(False)
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDropIndicatorShown(True)
        self.table.setDragDropMode(QTableView.DragDropMode.DragDrop)
        self.stack.addWidget(self.table)

        self.icon_list = QListWidget()
        self.icon_list.setObjectName("icons")
        self.icon_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.icon_list.setIconSize(QSize(_scaled(96), _scaled(96)))
        self.icon_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.icon_list.setWordWrap(True)
        self.icon_list.setSpacing(4)
        self.icon_list.setDragEnabled(True)
        self.icon_list.setAcceptDrops(True)
        self.icon_list.setDropIndicatorShown(True)
        self.icon_list.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.icon_list.itemDoubleClicked.connect(
            lambda it: self._activate_path(it.data(Qt.ItemDataRole.UserRole)))
        self.icon_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.icon_list.customContextMenuRequested.connect(self._context_menu)
        self.icon_list.itemSelectionChanged.connect(
            lambda: self._update_status(self.icon_list))
        self.stack.addWidget(self.icon_list)

        # Empty state widget
        self._empty_state = QWidget()
        self._empty_state.setObjectName("EmptyState")
        empty_lay = QVBoxLayout(self._empty_state)
        empty_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon = QLabel()
        _fi = _fluent_icon("folder", _scaled(64), "#555555")
        empty_icon.setPixmap(_fi.pixmap(_scaled(64), _scaled(64)))
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title = QLabel("This folder is empty")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title.setStyleSheet("font-size: 14pt; font-weight: 600; color: #AAAAAA;")
        empty_desc = QLabel("Drop files here or create a new folder")
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_desc.setStyleSheet("font-size: 9pt; color: #777777;")
        empty_lay.addStretch(1)
        empty_lay.addWidget(empty_icon)
        empty_lay.addSpacing(8)
        empty_lay.addWidget(empty_title)
        empty_lay.addSpacing(4)
        empty_lay.addWidget(empty_desc)
        empty_lay.addStretch(1)
        self.stack.addWidget(self._empty_state)

        self.splitter.addWidget(self.stack)

        # Right pane (hidden until dual pane mode)
        self._right_stack = QStackedWidget()
        self._right_table = QTableView()
        self._right_table.setModel(self._right_proxy)
        self._right_table.setSortingEnabled(True)
        self._right_table.setAlternatingRowColors(True)
        self._right_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._right_table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self._right_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._right_table.verticalHeader().setVisible(False)
        self._right_table.verticalHeader().setDefaultSectionSize(_scaled(28))
        rhh = self._right_table.horizontalHeader()
        rhh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c, w in ((1, 90), (2, 90), (3, 150)):
            self._right_table.setColumnWidth(c, _scaled(w))
        self._right_table.doubleClicked.connect(self._activate_right)
        self._right_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._right_table.customContextMenuRequested.connect(self._context_menu)
        self._right_table.selectionModel().selectionChanged.connect(
            lambda *_: self._update_status(self._right_table))
        self._right_table.setShowGrid(False)
        self._right_stack.addWidget(self._right_table)

        self._right_icon_list = QListWidget()
        self._right_icon_list.setObjectName("icons")
        self._right_icon_list.setViewMode(QListWidget.ViewMode.IconMode)
        self._right_icon_list.setIconSize(QSize(_scaled(96), _scaled(96)))
        self._right_icon_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._right_icon_list.setWordWrap(True)
        self._right_icon_list.setSpacing(4)
        self._right_icon_list.itemDoubleClicked.connect(
            lambda it: self._activate_path(it.data(Qt.ItemDataRole.UserRole)))
        self._right_icon_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._right_icon_list.customContextMenuRequested.connect(self._context_menu)
        self._right_icon_list.itemSelectionChanged.connect(
            lambda: self._update_status(self._right_icon_list))
        self._right_stack.addWidget(self._right_icon_list)

        self.splitter.addWidget(self._right_stack)
        self._right_stack.hide()  # hidden until dual pane mode

        # preview
        self.preview = PreviewPane(self.icons)
        self.preview.set_transfer_queue(self._transfer_queue)
        self.preview.staging_shelf.paste_requested.connect(self._on_staging_paste)
        self.preview.staging_shelf.add_selected_requested.connect(self._on_stage_selected)
        self.preview.transfer_dock.open_monitor_requested.connect(self.open_transfer_monitor)
        self.splitter.addWidget(self.preview)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        self.splitter.setSizes([_scaled(210), _scaled(620), _scaled(270)])

        # ── terminal panel ──────────────────────────────────────────────
        self.terminal_panel = TerminalWidget()
        self.terminal_panel.hide()

        self.vsplitter = QSplitter(Qt.Orientation.Vertical)
        self.vsplitter.setHandleWidth(2)
        self.vsplitter.addWidget(self.splitter)
        self.vsplitter.addWidget(self.terminal_panel)
        self.vsplitter.setStretchFactor(0, 1)
        self.vsplitter.setStretchFactor(1, 0)
        self.vsplitter.setSizes([_scaled(600), _scaled(200)])
        main_layout.addWidget(self.vsplitter, 1)

        # ── extraction progress panel (hidden until needed) ────────────────
        self._extract_progress = ExtractionProgressWidget()
        self._extract_progress.hide()
        main_layout.addWidget(self._extract_progress)

        # ── status bar ────────────────────────────────────────────────────
        srow = QHBoxLayout()
        srow.setContentsMargins(12, 4, 12, 4)
        self.status_items = QLabel("0 items")
        self.status_sel = QLabel("")
        self.status_sel.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.status_transfer = QLabel("")
        self.status_transfer.setObjectName("StatusTransfer")
        self.status_transfer.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.status_transfer.hide()
        self.status_undo = QLabel("")
        self.status_undo.setStyleSheet("color: #90CAF9; font-size: 8pt;")
        self.status_undo.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.status_items.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_items.mousePressEvent = lambda _: self._cycle_status_mode()
        srow.addWidget(self.status_items)
        srow.addStretch(1)
        srow.addWidget(self.status_undo)
        srow.addWidget(self.status_transfer)
        srow.addWidget(self.status_sel)
        statusw = QWidget()
        statusw.setObjectName("Status")
        statusw.setFixedHeight(_scaled(28))
        statusw.setLayout(srow)
        main_layout.addWidget(statusw)

        # ── watcher ───────────────────────────────────────────────────────
        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(self._on_fs_change)
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(250)
        self._reload_timer.timeout.connect(self._reload_current)

        # ── Command Palette ────────────────────────────────────────────────
        self._palette = CommandPalette(self)
        self._register_palette_actions()

        # ── Shortcuts Dialog ──────────────────────────────────────────────
        self._shortcuts_dialog = ShortcutsDialog(self)

        # ── Job Queue Overlay ──────────────────────────────────────────────
        self._job_queue = JobQueueWidget(self)

        self._bind_shortcuts()
        self._load_drives()
        self.add_tab(start_path or os.path.expanduser("~"))

        # FPS timer for debug overlay
        self._fps_timer = QTimer(self)
        self._fps_timer.setInterval(500)
        self._fps_timer.timeout.connect(self._debug.tick_fps)
        self._fps_timer.start()

        # Session persistence (audit finding A8): save on application quit,
        # guarded so it works both standalone and embedded in a host app.
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._on_about_to_quit)

        # Restore LAST, after the default tab above already kicked off its
        # async load: restore_session supersedes it via the _load_seq guard.
        self._install_mouse_side_buttons()
        self.restore_session()

    def mount_tabs_to_window(self, win) -> None:
        """Mount the TabBarContainer directly into the top window title bar row.

        Manages mount tabs to window operations and coordinates related state changes for the component.

        Args:
            win: Parent window or shell controller instance.
        """
        if hasattr(win, "set_titlebar_tab_widget") and hasattr(self, "tab_container"):
            self.tab_container.setParent(None)
            win.set_titlebar_tab_widget(self.tab_container)

    def _on_about_to_quit(self) -> None:
        """Persist the session before the application quits.

        Manages on about to quit operations and coordinates related state changes for the component.
        """
        self.save_session(force=True)

    def save_session(self, force=False):
        """Persist UI session (schema v1) to QSettings. Never raises.

        Manages save session operations and coordinates related state changes for the component.

        Args:
            force: The force parameter.
        """
        try:
            s = QSettings("Nexus", "NexusExplorer")
            s.setValue("lastPath", self._tab()["path"])
            s.setValue("sidebarVisible", self._sidebar_visible)
            s.setValue("debugVisible", self._debug_visible)
            s.setValue("session/tabs",
                       json.dumps([t.get("path", "") for t in self._tabs]))
            s.setValue("session/activeTab", int(self._current_tab))
            s.setValue("session/viewMode",
                       "icons" if self.stack.currentIndex() == 1 else "details")
            s.setValue("session/dualPane", bool(self._dual_pane))
            s.setValue("session/splitterSizes",
                       json.dumps(self.splitter.sizes()))
        except (OSError, TypeError, ValueError):
            log.debug("save_session failed", exc_info=True)

    def restore_session(self):
        """Restore last session (schema v1). Defensive: bad/missing values
        fall back to the already-initialized state; never raises."""
        try:
            s = QSettings("Nexus", "NexusExplorer")
            last = s.value("lastPath", "")
            tabs_raw = s.value("session/tabs", "")
            paths: list[str] = []
            if isinstance(tabs_raw, str) and tabs_raw:
                try:
                    paths = [p for p in json.loads(tabs_raw)
                             if isinstance(p, str)]
                except (ValueError, TypeError):
                    paths = []
            paths = [p for p in paths if p and os.path.isdir(p)]

            if paths:
                target = paths[0] if os.path.isdir(paths[0]) else (
                    last if last and os.path.isdir(last) else None)
                if target:
                    self.navigate(target)
                for p in paths[1:]:
                    self.add_tab(p)
                try:
                    active = int(s.value("session/activeTab", 0))
                except (TypeError, ValueError):
                    active = 0
                active = max(0, min(active, self.tabbar.count() - 1))
                if self.tabbar.count() > 1:
                    self.tabbar.setCurrentIndex(active)
            elif last and os.path.isdir(last):
                self.navigate(last)

            want_icons = s.value("session/viewMode", "details") == "icons"
            if want_icons:
                self._pending_view_mode = "icons"
            elif self.stack.currentIndex() == 1:
                self._toggle_view()

            if s.value("session/dualPane", False) in (True, "true") \
                    and not self._dual_pane:
                self._toggle_dual_pane()

            side_val = s.value("sidebarVisible", None)
            if side_val is not None:
                want_side = side_val in (True, "true")
                if want_side != self._sidebar_visible:
                    self._toggle_sidebar()

            try:
                sizes = json.loads(s.value("session/splitterSizes", "[]"))
                if (isinstance(sizes, list) and sizes
                        and len(sizes) == len(self.splitter.sizes())
                        and all(isinstance(x, int) for x in sizes)):
                    self.splitter.setSizes(sizes)
            except (ValueError, TypeError):
                pass
        except (OSError, TypeError, ValueError):
            log.debug("restore_session failed", exc_info=True)

    # ────────────────────────── shortcuts ─────────────────────────────────
    def _bind_shortcuts(self):
        """Register global shortcuts, skipping text inputs where unsafe.

        Manages bind shortcuts operations and coordinates related state changes for the component.
        """
        def _text_input_focused():
            """Return True when focus sits in a line/text edit.

            Manages text input focused operations and coordinates related state changes for the component.
            """
            from PySide6.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit
            w = QApplication.focusWidget()
            return isinstance(w, (QLineEdit, QTextEdit, QPlainTextEdit))

        def _wrap(fn, allow_in_text=False):
            """Wrap.

            Manages wrap operations and coordinates related state changes for the component.

            Args:
                fn: The fn parameter.
                allow_in_text: The allow in text parameter.
            """
            def _handler():
                """Handler.

                Manages handler operations and coordinates related state changes for the component.
                """
                if not allow_in_text and _text_input_focused():
                    return
                fn()
            return _handler

        binds = [
            ("Alt+Left", self.go_back), ("Alt+Right", self.go_forward),
            ("Backspace", self.go_up),
            ("F5", lambda: (self._clip("copy"), self._paste())),
            ("F7", self._new_folder),
            ("Ctrl+Shift+N", self._new_folder),
            ("Ctrl+Alt+N", self._new_nested_folder),
            ("Ctrl+N", self._new_file),
            ("Ctrl+Alt+F", self._new_nested_file),
            ("Ctrl+Shift+B", self._batch_scaffold),
            ("F8", self._delete),
            ("Delete", self._delete),
            ("Shift+Delete", lambda: self._delete(permanent=True)),
            ("F2", self._rename),
            ("Ctrl+C", lambda: self._clip("copy")),
            ("Ctrl+X", lambda: self._clip("cut")),
            ("Ctrl+V", self._paste), ("Ctrl+A", self._select_all),
            ("Ctrl+Z", self._undo), ("Ctrl+Y", self._redo),
            ("Ctrl+Shift+Z", self._redo),
            ("Ctrl+T", lambda: self.add_tab(os.path.expanduser("~"))),
            ("Ctrl+W", self._close_current_tab),
            ("Ctrl+F", self.filter.setFocus),
            ("Ctrl+D", self._toggle_dual_pane),
            ("F12", self._toggle_debug),
            ("Shift+F5", self._reload_current),
            ("Ctrl+L", self._start_edit_path),
            ("Space", self._quick_look),
            ("Ctrl+B", self._bulk_rename),
            ("Ctrl+Shift+P", self._palette.toggle),
            ("Ctrl+`", self._toggle_terminal),
            ("Ctrl+Shift+F", self._open_duplicate_finder),
            ("Ctrl+H", self._toggle_sidebar),
            ("Ctrl+1", lambda: self._go_bookmark(0)),
            ("Ctrl+2", lambda: self._go_bookmark(1)),
            ("Ctrl+3", lambda: self._go_bookmark(2)),
            ("Ctrl+4", lambda: self._go_bookmark(3)),
            ("Ctrl+5", lambda: self._go_bookmark(4)),
            ("Ctrl+6", lambda: self._go_bookmark(5)),
            ("Ctrl+7", lambda: self._go_bookmark(6)),
            ("Ctrl+8", lambda: self._go_bookmark(7)),
            ("Ctrl+9", lambda: self._go_bookmark(8)),
            ("Ctrl+0", lambda: self._go_bookmark(9)),
            ("Shift+/", self._show_shortcuts),
            ("F1", self._show_shortcuts),
            ("Ctrl+?", self._show_shortcuts),
            ("Ctrl+G", self._go_to_path),
            ("F6", self._sort_cycle_column),
            ("Shift+F6", self._sort_toggle_order),
            ("Ctrl+Shift+F", self.toggle_flat_branch_view),
        ]
        for seq, fn in binds:
            sc = QShortcut(QKeySequence(seq), self)
            sc.activated.connect(_wrap(fn))

    def _register_palette_actions(self):
        """Register explorer commands (nav, view, create) in the palette.

        Manages register palette actions operations and coordinates related state changes for the component.
        """
        p = self._palette
        p.register("Navigate Back", "Alt+\u2190", self.go_back)
        p.register("Navigate Forward", "Alt+\u2192", self.go_forward)
        p.register("Go Up", "Backspace", self.go_up)
        p.register("Go Home", "", lambda: self.navigate(os.path.expanduser("~")))
        p.register("Toggle View", "", self._toggle_view)
        p.register("Toggle Flat Branch View", "Ctrl+Shift+F", self.toggle_flat_branch_view)
        p.register("Toggle Dual Pane", "Ctrl+D", self._toggle_dual_pane)
        p.register("Quick Look", "Space", self._quick_look)
        p.register("Bulk Rename", "Ctrl+B", self._bulk_rename)
        p.register("New Folder", "F7 / Ctrl+Shift+N", self._new_folder)
        p.register("New Nested Folders", "Ctrl+Alt+N", self._new_nested_folder)
        p.register("New File", "Ctrl+N", self._new_file)
        p.register("New File in Nested Path", "Ctrl+Alt+F", self._new_nested_file)
        p.register("Batch Scaffold Project / Tree", "Ctrl+Shift+B", self._batch_scaffold)
        p.register("Delete", "F8/Delete", self._delete)
        p.register("Rename", "F2", self._rename)
        p.register("Copy Here", "F5", lambda: (self._clip("copy"), self._paste()))
        p.register("Move Here", "F6", lambda: (self._clip("cut"), self._paste()))
        p.register("Copy", "Ctrl+C", lambda: self._clip("copy"))
        p.register("Cut", "Ctrl+X", lambda: self._clip("cut"))
        p.register("Paste", "Ctrl+V", self._paste)
        p.register("Undo", "Ctrl+Z", self._undo)
        p.register("Redo", "Ctrl+Y", self._redo)
        p.register("Select All", "Ctrl+A", self._select_all)
        p.register("Toggle Sidebar", "Ctrl+H", self._toggle_sidebar)
        p.register("Toggle Debug Overlay", "F12", self._toggle_debug)
        p.register("Refresh", "Shift+F5", self._reload_current)
        p.register("New Tab", "Ctrl+T", lambda: self.add_tab(os.path.expanduser("~")))
        p.register("Close Tab", "Ctrl+W", self._close_current_tab)
        p.register("Toggle Terminal", "Ctrl+`", self._toggle_terminal)
        p.register("Find Duplicates", "Ctrl+Shift+F", self._open_duplicate_finder)
        p.register("Search Files", "Ctrl+Shift+S", self._search)
        p.register("Add Bookmark", "", self._add_bookmark)
        p.register("Go to Path", "Ctrl+G", self._go_to_path)

    # ────────────────────────── debug ─────────────────────────────────────
    def _toggle_debug(self):
        """Show or hide the F12 debug overlay on the explorer.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        self._debug_visible = not self._debug_visible
        if self._debug_visible:
            self._debug.setParent(self)
            self._debug.move(10, 10)
            self._debug.show()
            self._debug.raise_()
            self._debug.log_event("Debug overlay ON — F12 to hide")
        else:
            self._debug.hide()

    def _show_shortcuts(self):
        """Raise the shortcuts dialog, showing it if hidden.

        Manages show shortcuts operations and coordinates related state changes for the component.
        """
        if self._shortcuts_dialog.isVisible():
            self._shortcuts_dialog.raise_()
            self._shortcuts_dialog.activateWindow()
        else:
            self._shortcuts_dialog.show()
            self._shortcuts_dialog.raise_()

    def _go_to_path(self):
        """Open Go-to-Path and navigate to the accepted directory.

        Manages go to path operations and coordinates related state changes for the component.
        """
        dlg = GoToPathDialog(self._tab()["path"], self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            path = dlg.result_path()
            if path:
                self.navigate(path)

    def _sort_cycle_column(self):
        """F6: cycle sort column (Name -> Modified -> Type -> Size -> Name).

        Manages sort cycle column operations and coordinates related state changes for the component.
        """
        col_names = [c[0] for c in self._SORT_COLUMNS]
        col_indices = [c[1] for c in self._SORT_COLUMNS]
        current = self.proxy.sortColumn()
        try:
            idx = col_indices.index(current)
        except ValueError:
            idx = -1
        next_idx = (idx + 1) % len(col_indices)
        self.proxy.sort(col_indices[next_idx], self.proxy.sortOrder())
        self.status_items.setText(f"Sort by: {col_names[next_idx]}")
        QTimer.singleShot(1200, self._update_status)

    def _sort_toggle_order(self):
        """Shift+F6: toggle ascending/descending.

        Manages sort toggle order operations and coordinates related state changes for the component.
        """
        new_order = (
            Qt.SortOrder.DescendingOrder
            if self.proxy.sortOrder() == Qt.SortOrder.AscendingOrder
            else Qt.SortOrder.AscendingOrder
        )
        self.proxy.sort(self.proxy.sortColumn(), new_order)
        label = "Ascending" if new_order == Qt.SortOrder.AscendingOrder else "Descending"
        self.status_items.setText(f"Sort order: {label}")
        QTimer.singleShot(1200, self._update_status)

    def _toggle_terminal(self):
        """Show or hide the terminal panel and focus its input.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        vis = not self.terminal_panel.isVisible()
        self.terminal_panel.setVisible(vis)
        if vis:
            total = self.vsplitter.height()
            self.vsplitter.setSizes([int(total * 0.7), int(total * 0.3)])
            self.terminal_panel.input.setFocus()

    def resizeEvent(self, ev):
        """Resizeevent.

        Manages resizeEvent operations and coordinates related state changes for the component.

        Args:
            ev: The Qt event object.
        """
        super().resizeEvent(ev)
        if hasattr(self, '_job_queue') and self._job_queue.isVisible():
            w = self._job_queue.width()
            h = self._job_queue.height()
            self._job_queue.move(self.width() - w - 12, self.height() - h - 12)

    def closeEvent(self, ev):
        """Handle the window or widget close event.

        Performs graceful shutdown, releases active workers and system hooks, persists window geometry, and accepts the close event.

        Args:
            ev: The Qt event object.
        """
        if hasattr(self, "terminal_panel") and self.terminal_panel is not None:
            self.terminal_panel.shutdown()
        super().closeEvent(ev)

    def _log(self, event: str):
        """Log.

        Manages log operations and coordinates related state changes for the component.

        Args:
            event (str): The Qt event object.
        """
        self._debug.log_event(event)
        log.debug(event)

    # ────────────────────────── tabs ──────────────────────────────────────
    def add_tab(self, path: str) -> None:
        """Append a tab entry with history and its closable tab-bar tab.

        Manages add tab operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        self._tabs.append({"path": path, "history": [path], "hindex": 0})
        idx = self.tabbar.addTab(_fluent_action("folder", size=14), Path(path).name or path)
        close_btn = QToolButton(self.tabbar)
        close_btn.setIcon(_fluent_action("close", size=12))
        close_btn.setStyleSheet(
            "QToolButton{background:transparent;border:none;border-radius:4px;padding:2px;}"
            "QToolButton:hover{background:#EF5350;}"
        )
        close_btn.setFixedSize(18, 18)
        close_btn.setCursor(Qt.PointingHandCursor)

        def _on_close_btn():
            """Close the tab whose close button emitted the click.

            Manages on close btn operations and coordinates related state changes for the component.
            """
            sender_btn = self.sender()
            for i in range(self.tabbar.count()):
                if self.tabbar.tabButton(i, QTabBar.RightSide) == sender_btn or self.tabbar.tabButton(i, QTabBar.LeftSide) == sender_btn:
                    self._close_tab(i)
                    break

        close_btn.clicked.connect(_on_close_btn)
        self.tabbar.setTabButton(idx, QTabBar.RightSide, close_btn)
        self.tabbar.setCurrentIndex(idx)
        self._log(f"Tab added: {path}")

    def _close_tab(self, idx: int) -> None:
        """Remove a tab, refusing when only one tab remains.

        Manages close tab operations and coordinates related state changes for the component.

        Args:
            idx (int): The idx parameter.
        """
        if self.tabbar.count() <= 1 or idx < 0 or idx >= len(self._tabs):
            return
        self._tabs.pop(idx)
        self.tabbar.removeTab(idx)
        new_idx = max(0, min(idx, self.tabbar.count() - 1))
        self.tabbar.setCurrentIndex(new_idx)
        self._switch_tab(new_idx)

    def _on_tab_moved(self, from_pos: int, to_pos: int) -> None:
        """Mirror a tab-bar drag reorder into the tabs list.

        Manages on tab moved operations and coordinates related state changes for the component.

        Args:
            from_pos (int): The from pos parameter.
            to_pos (int): The to pos parameter.
        """
        if 0 <= from_pos < len(self._tabs) and 0 <= to_pos < len(self._tabs):
            tab = self._tabs.pop(from_pos)
            self._tabs.insert(to_pos, tab)
            if self._current_tab == from_pos:
                self._current_tab = to_pos
            elif from_pos < self._current_tab <= to_pos:
                self._current_tab -= 1
            elif from_pos > self._current_tab >= to_pos:
                self._current_tab += 1

    def _close_current_tab(self) -> None:
        """Close the currently selected tab.

        Manages close current tab operations and coordinates related state changes for the component.
        """
        if self._current_tab >= 0:
            self._close_tab(self._current_tab)

    def _switch_tab(self, idx: int) -> None:
        """Activate a tab: clear the filter and load its path.

        Manages switch tab operations and coordinates related state changes for the component.

        Args:
            idx (int): The idx parameter.
        """
        if idx < 0 or idx >= len(self._tabs):
            return
        self._current_tab = idx
        self.filter.clear()
        tab = self._tabs[idx]
        self._load(tab["path"])

    def _tab(self) -> dict:
        """Tab.

        Manages tab operations and coordinates related state changes for the component.

        Returns:
            dict: Dictionary mapping identifiers to status or values.
        """
        if self._current_tab < 0 or self._current_tab >= len(self._tabs):
            return {"path": os.path.expanduser("~"), "history": [os.path.expanduser("~")], "hindex": 0}
        return self._tabs[self._current_tab]

    # ────────────────────────── navigation ────────────────────────────────
    def navigate(self, path: str, push: bool = True) -> None:
        """Navigate.

        Manages navigate operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
            push (bool): The push parameter.
        """
        path = os.path.normpath(os.path.expanduser(path))
        if not os.path.isdir(path):
            self.status_items.setText(f"Not a folder: {path}")
            self._log(f"Navigate FAIL: {path} not a directory")
            return
        tab = self._tab()
        if push:
            tab["history"] = tab["history"][: tab["hindex"] + 1]
            tab["history"].append(path)
            tab["hindex"] = len(tab["history"]) - 1
        tab["path"] = path
        self.tabbar.setTabText(self._current_tab, Path(path).name or path)
        self._log(f"Navigate: {path}")
        # Sync folder tree selection
        if self.folder_tree is not None:
            self.folder_tree.select_path(path)
        self._load(path)

    def _load(self, path: str) -> None:
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        self.status_items.setText("Loading\u2026")
        self.crumbs.setPath(path)
        self.preview.set_current_folder(path)
        folder_name = Path(path).name or path
        self.filter.setPlaceholderText(f"Search {folder_name}")
        self.terminal_panel.set_cwd(path)
        if self.addr.isVisible():
            self.addr.setText(path)
        self.watcher.blockSignals(True)
        if self.watcher.directories():
            self.watcher.removePaths(self.watcher.directories())
        self.watcher.addPath(path)
        self.watcher.blockSignals(False)
        self._folder_sizes.clear_queue()
        self._load_seq += 1
        seq = self._load_seq

        def _deliver(code: int, rows: list[dict], _seq: int = seq) -> None:
            """Deliver.

            Manages deliver operations and coordinates related state changes for the component.

            Args:
                code (int): The code parameter.
                rows (list[dict]): Table row index or list of row indices.
                _seq (int): The  seq parameter.
            """
            if _seq == self._load_seq:
                self._on_rows(code, rows)

        self.engine.list_dir(path, _deliver)

    def _on_rows(self, code: int, rows: list[dict]) -> None:
        """Push engine rows into the model and refresh status and view.

        Manages on rows operations and coordinates related state changes for the component.

        Args:
            code (int): The code parameter.
            rows (list[dict]): Table row index or list of row indices.
        """
        self.model.update_rows(rows)
        self._update_status()
        self._log(f"Loaded {len(rows)} items (code={code})")
        pending = getattr(self, "_pending_view_mode", None)
        if pending == "icons":
            self._pending_view_mode = None
            if self.stack.currentIndex() != 1:
                self._toggle_view()
            if rows:
                self._fill_icon_view(rows)
            return
        if len(rows) == 0:
            if self.stack.currentIndex() != 1:
                self.stack.setCurrentIndex(2)  # empty_state
        elif self.stack.currentIndex() == 1:
            self._fill_icon_view(rows)
        else:
            self.stack.setCurrentIndex(0)  # table
        # Trigger background folder size calculation for all directories
        self._calc_folder_sizes(rows)

    def _reload_current(self) -> None:
        """Reload the active tab's current path.

        Manages reload current operations and coordinates related state changes for the component.
        """
        self._load(self._tab()["path"])

    # ────────────────────────── bookmarks ────────────────────────────────
    def _load_bookmarks(self):
        """Load bookmarks from settings.

        Manages load bookmarks operations and coordinates related state changes for the component.
        """
        settings = QSettings("Nexus", "NexusExplorer")
        saved = settings.value("bookmarks", [], type=list)
        if isinstance(saved, list):
            self._bookmarks = [str(p) for p in saved if p]
        else:
            self._bookmarks = []

    def _save_bookmarks(self):
        """Persist bookmarks to settings.

        Manages save bookmarks operations and coordinates related state changes for the component.
        """
        settings = QSettings("Nexus", "NexusExplorer")
        settings.setValue("bookmarks", self._bookmarks)

    def _go_bookmark(self, index: int):
        """Navigate to bookmark at index (Ctrl+1-9).

        Manages go bookmark operations and coordinates related state changes for the component.

        Args:
            index (int): The index parameter.
        """
        if 0 <= index < len(self._bookmarks):
            path = self._bookmarks[index]
            if os.path.isdir(path):
                self.navigate(path)
            else:
                self.status_items.setText(f"Bookmark path not found: {path}")
        elif index < 10:
            self.status_items.setText(f"Bookmark {index + 1} not set")

    def _add_bookmark(self):
        """Add current directory to bookmarks.

        Manages add bookmark operations and coordinates related state changes for the component.
        """
        path = self._tab()["path"]
        if path in self._bookmarks:
            self._bookmarks.remove(path)
            self._bookmarks.insert(0, path)
        else:
            if len(self._bookmarks) >= 10:
                self._bookmarks.pop()
            self._bookmarks.insert(0, path)
        self._save_bookmarks()
        self.status_items.setText(f"Bookmarked: {path}")

    def _calc_folder_sizes(self, rows: list[dict]) -> None:
        """Calculate sizes for all directories in the current listing.

        Manages calc folder sizes operations and coordinates related state changes for the component.

        Args:
            rows (list[dict]): Table row index or list of row indices.
        """
        dirs = [r for r in rows if r.get("isDir") and r.get("path")]
        for d in dirs:
            path = d["path"]
            cached = self._folder_sizes.get_size(path)
            if cached is not None:
                d["folderSize"] = cached
            else:
                self._folder_sizes.calculate(path, self._on_folder_size_done)

    def _on_folder_size_done(self, path: str, size: int) -> None:
        """Callback when folder size calculation completes.

        Receives the completed data from the folder size background worker, populates the view with results, and restores button states.

        Args:
            path (str): Filesystem path to the target file or directory.
            size (int): Integer number of bytes to format or process.
        """
        for row in self.model.rows:
            if row.get("path") == path:
                row["folderSize"] = size
                break
        idx = self.model.index(0, 0)
        for i, row in enumerate(self.model.rows):
            if row.get("path") == path:
                self.model.dataChanged.emit(
                    self.model.index(i, 1), self.model.index(i, 1)
                )
                break

    def _on_fs_change(self, _path: str) -> None:
        """Debounce a filesystem-watcher change into a reload.

        Manages on fs change operations and coordinates related state changes for the component.

        Args:
            _path (str): Filesystem path to the target file or directory.
        """
        self._reload_timer.start()

    def go_back(self):
        """Step back in the active tab's history without pushing.

        Manages go back operations and coordinates related state changes for the component.
        """
        t = self._tab()
        if t["hindex"] > 0:
            t["hindex"] -= 1
            self.navigate(t["history"][t["hindex"]], push=False)

    def go_forward(self):
        """Step forward in the active tab's history without pushing.

        Manages go forward operations and coordinates related state changes for the component.
        """
        t = self._tab()
        if t["hindex"] < len(t["history"]) - 1:
            t["hindex"] += 1
            self.navigate(t["history"][t["hindex"]], push=False)

    # ── right-pane history (mouse side-buttons route here when over it) ──
    def _right_go_back(self):
        """Step back in the right pane's history without pushing.

        Manages right go back operations and coordinates related state changes for the component.
        """
        t = self._right_tab()
        if t["hindex"] > 0:
            t["hindex"] -= 1
            self._right_navigate(t["history"][t["hindex"]], push=False)

    def _right_go_forward(self):
        """Step forward in the right pane's history without pushing.

        Manages right go forward operations and coordinates related state changes for the component.
        """
        t = self._right_tab()
        if t["hindex"] < len(t["history"]) - 1:
            t["hindex"] += 1
            self._right_navigate(t["history"][t["hindex"]], push=False)

    def _install_mouse_side_buttons(self):
        """Route mouse XButton1/XButton2 and drag-drops across all file viewports.

        Initiates the package or update installation workflow in the background, monitoring execution progress.
        """
        self.setAcceptDrops(True)
        self.installEventFilter(self)
        views = [self]
        if hasattr(self, "stack") and self.stack is not None:
            views.append(self.stack)
            self.stack.setAcceptDrops(True)
        if hasattr(self, "_empty_state") and self._empty_state is not None:
            views.append(self._empty_state)
            self._empty_state.setAcceptDrops(True)
            for ch in self._empty_state.findChildren(QWidget):
                views.append(ch)
                ch.setAcceptDrops(True)
        if hasattr(self, "splitter") and self.splitter is not None:
            views.append(self.splitter)
            self.splitter.setAcceptDrops(True)

        for attr in ("table", "icon_list", "_right_table", "_right_icon_list", "quick_list", "smart_list"):
            v = getattr(self, attr, None)
            if v is not None:
                views.append(v)
                v.setAcceptDrops(True)
                vp = v.viewport()
                if vp is not None:
                    views.append(vp)
                    vp.setAcceptDrops(True)
        if hasattr(self, "folder_tree") and self.folder_tree is not None:
            views.append(self.folder_tree)
            self.folder_tree.setAcceptDrops(True)
            tree = getattr(self.folder_tree, "tree", None)
            if tree is not None:
                views.append(tree)
                tree.setAcceptDrops(True)
                vp = tree.viewport()
                if vp is not None:
                    views.append(vp)
                    vp.setAcceptDrops(True)
        for vp in set(views):
            vp.installEventFilter(self)

    def eventFilter(self, obj, ev):  # noqa: N802
        """Filter monitored Qt events for target child widgets.

        Intercepts specific mouse, keyboard, or focus events to provide custom interactive behaviors before standard event dispatch.

        Args:
            obj: The obj parameter.
            ev: The Qt event object.
        """
        from PySide6.QtCore import QEvent

        # 1. Route drag & drop events on all file viewports & trees
        if ev.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
            try:
                self._update_drop_hint(obj, ev)
            except Exception:
                pass
            ev.acceptProposedAction()
            return True
        elif ev.type() == QEvent.Type.DragLeave:
            try:
                self._update_status()
            except Exception:
                pass
            return False
        elif ev.type() == QEvent.Type.Drop:
            if self._handle_viewport_drop(obj, ev):
                return True

        # 2. Route mouse XButton1/XButton2
        if ev.type() == QEvent.Type.MouseButtonPress:
            btn = ev.button()
            if btn in (Qt.MouseButton.BackButton, Qt.MouseButton.ForwardButton):
                right_vps = set()
                for attr in ("_right_table", "_right_icon_list"):
                    v = getattr(self, attr, None)
                    if v is not None:
                        right_vps.add(v.viewport())
                over_right = obj in right_vps
                if btn == Qt.MouseButton.BackButton:
                    self._right_go_back() if over_right else self.go_back()
                else:
                    self._right_go_forward() if over_right else self.go_forward()
                return True
        return super().eventFilter(obj, ev)

    def _handle_viewport_drop(self, obj, ev) -> bool:
        """Enqueue a copy/move transfer for viewport-dropped paths.

        Manages handle viewport drop operations and coordinates related state changes for the component.

        Args:
            obj: The obj parameter.
            ev: The Qt event object.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        mime = ev.mimeData()
        if not mime:
            return False

        source_paths = []
        if mime.hasUrls():
            source_paths = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]
        elif mime.hasText():
            source_paths = [p.strip() for p in mime.text().splitlines() if os.path.exists(p.strip())]

        if not source_paths and hasattr(self, "preview") and hasattr(self.preview, "staging_shelf"):
            source_paths = list(self.preview.staging_shelf._staged_paths)

        if not source_paths:
            source_paths = self._selected_paths()

        if not source_paths:
            return False

        # Target directory defaults to current active tab
        dest_dir = self._tab()["path"]

        # Check if dropped onto specific folder row/item in the active table/list
        pos = ev.position().toPoint() if hasattr(ev, "position") else ev.pos()
        if hasattr(self, "table") and (obj == self.table or obj == self.table.viewport()):
            idx = self.table.indexAt(pos)
            if idx.isValid():
                row_data = self.proxy.index(idx.row(), 0).data(Qt.ItemDataRole.UserRole)
                if row_data and row_data.get("isDir"):
                    dest_dir = row_data.get("path", dest_dir)
        elif hasattr(self, "icon_list") and (obj == self.icon_list or obj == self.icon_list.viewport()):
            item = self.icon_list.itemAt(pos)
            if item is not None:
                path_val = item.data(Qt.ItemDataRole.UserRole)
                if path_val and os.path.isdir(path_val):
                    dest_dir = path_val
        elif hasattr(self, "_right_table") and (obj == self._right_table or obj == self._right_table.viewport()):
            dest_dir = getattr(self, "_right_path", dest_dir)
            idx = self._right_table.indexAt(pos)
            if idx.isValid():
                row_data = self._right_proxy.index(idx.row(), 0).data(Qt.ItemDataRole.UserRole)
                if row_data and row_data.get("isDir"):
                    dest_dir = row_data.get("path", dest_dir)
        elif hasattr(self, "quick_list") and (obj == self.quick_list or obj == self.quick_list.viewport()):
            item = self.quick_list.itemAt(pos)
            if item is not None:
                path_val = item.data(Qt.ItemDataRole.UserRole)
                if path_val and os.path.isdir(path_val):
                    dest_dir = path_val
        elif hasattr(self, "folder_tree") and self.folder_tree is not None:
            tree = getattr(self.folder_tree, "tree", None)
            if tree is not None and (obj == self.folder_tree or obj == tree or obj == tree.viewport()):
                idx = tree.indexAt(pos)
                if idx.isValid():
                    target_p = idx.data(Qt.ItemDataRole.UserRole)
                    if target_p and os.path.isdir(target_p):
                        dest_dir = target_p

        valid_sources = [p for p in source_paths if os.path.exists(p)]
        if not valid_sources:
            ev.acceptProposedAction()
            return True

        modifiers = ev.modifiers() if hasattr(ev, "modifiers") else ev.keyboardModifiers()
        is_move = bool(modifiers & Qt.KeyboardModifier.ShiftModifier) or (_nexus_clipboard._mode == "cut")
        if hasattr(self, "preview") and hasattr(self.preview, "staging_shelf"):
            if self.preview.staging_shelf._mode == "cut":
                is_move = True
        action_name = "move" if is_move else "copy"

        # Prevent moving file directly onto itself
        if is_move:
            valid_sources = [
                p for p in valid_sources
                if os.path.normpath(p) != os.path.normpath(str(Path(dest_dir) / Path(p).name))
            ]
        if not valid_sources:
            ev.acceptProposedAction()
            return True

        for p in valid_sources:
            dst = str(Path(dest_dir) / Path(p).name)
            if action_name == "copy":
                self._undo_manager.record_copy(p, dst)
            else:
                self._undo_manager.record_move(p, dst)

        self._log(f"Drag-Drop {action_name.capitalize()}: {len(valid_sources)} items -> {dest_dir}")
        self._transfer_queue.enqueue(
            kind=action_name,
            sources=valid_sources,
            dest=dest_dir,
        )

        if is_move:
            if hasattr(self, "preview") and hasattr(self.preview, "staging_shelf"):
                self.preview.staging_shelf.clear_staged()
            _nexus_clipboard.clear()

        self.status_items.setText(f"{action_name.capitalize()}ing {len(valid_sources)} item(s) to {Path(dest_dir).name or dest_dir}")
        ev.acceptProposedAction()
        return True

    def _update_drop_hint(self, obj, ev) -> None:
        """Show a drop-target hint in the status bar during drag-move.

        Best-effort only: never raises, writes only to status_sel (items
        count in status_items is untouched), and moves the details-table
        current index onto the hovered folder to highlight the drop target.
        """
        try:
            mime = ev.mimeData()
            if not mime:
                return
            if mime.hasUrls():
                count = len([u for u in mime.urls() if u.isLocalFile()])
            elif mime.hasText():
                count = len([p for p in mime.text().splitlines() if p.strip()])
            else:
                return
            if count <= 0:
                return
            pos = ev.position().toPoint() if hasattr(ev, "position") else ev.pos()
            target_name = None
            if hasattr(self, "table") and (obj == self.table or obj == self.table.viewport()):
                idx = self.table.indexAt(pos)
                if idx.isValid():
                    row = self.proxy.index(idx.row(), 0).data(Qt.ItemDataRole.UserRole)
                    if row and row.get("isDir"):
                        target_name = row.get("name") or row.get("path")
                        self.table.setCurrentIndex(idx)
            elif hasattr(self, "icon_list") and (obj == self.icon_list or obj == self.icon_list.viewport()):
                item = self.icon_list.itemAt(pos)
                if item is not None:
                    path_val = item.data(Qt.ItemDataRole.UserRole)
                    if path_val and os.path.isdir(path_val):
                        target_name = Path(path_val).name or path_val
            if target_name and hasattr(self, "status_sel"):
                self.status_sel.setText(f"Drop {count} item(s) into {target_name}")
        except Exception:
            pass

    def go_up(self):
        """Navigate to the parent folder (or out of archive mode).

        Manages go up operations and coordinates related state changes for the component.
        """
        if self._archive_mode:
            self._archive_go_up()
            return
        parent = os.path.dirname(self._tab()["path"].rstrip("\\/"))
        if parent and parent != self._tab()["path"]:
            self.navigate(parent)

    def _start_edit_path(self):
        """Swap breadcrumbs for the address editor with the path selected.

        Manages start edit path operations and coordinates related state changes for the component.
        """
        self.addr.setText(self._tab()["path"])
        self.crumbs.hide()
        self.addr.show()
        self.addr.setFocus()
        self.addr.selectAll()

    def _commit_edit_path(self):
        """Navigate to the edited address when it is a directory.

        Manages commit edit path operations and coordinates related state changes for the component.
        """
        p = self.addr.text().strip()
        if len(p) == 2 and p[1] == ":":
            p += "\\"
        self.addr.hide()
        self.crumbs.show()
        if os.path.isdir(p):
            self.navigate(p)

    def _on_addr_editing_finished(self):
        """Restore breadcrumbs when address editing finishes.

        Manages on addr editing finished operations and coordinates related state changes for the component.
        """
        self.addr.hide()
        self.crumbs.show()

    # ────────────────────────── sidebar ───────────────────────────────────
    def _toggle_sidebar(self):
        """Show or hide the sidebar and sync its toggle button.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        self._sidebar_visible = not self._sidebar_visible
        if self._sidebar_visible:
            self.side.show()
            self.btn_sidebar.setChecked(True)
        else:
            self.side.hide()
            self.btn_sidebar.setChecked(False)

    # ────────────────────────── dual pane ─────────────────────────────────
    def _toggle_dual_pane(self):
        """Toggle dual pane mode (Ctrl+D).

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        self._dual_pane = not self._dual_pane
        self.btn_dual.setChecked(self._dual_pane)
        if self._dual_pane:
            self._right_stack.show()
            self.splitter.setSizes([_scaled(210), _scaled(400), _scaled(400), _scaled(270)])
            if not self._right_tabs:
                self._right_add_tab(os.path.expanduser("~"))
            self._log("Dual pane ON")
        else:
            self._right_stack.hide()
            self.splitter.setSizes([_scaled(210), _scaled(620), _scaled(270)])
            self._log("Dual pane OFF")

    # ────────────────────────── archive browsing ──────────────────────────
    def _open_archive(self, archive_path: str):
        """Open an archive file, showing its contents in the file table.

        Manages open archive operations and coordinates related state changes for the component.

        Args:
            archive_path (str): Filesystem path to the target file or directory.
        """
        if archive_path.lower().endswith(".zip"):
            if self._zip_browser.open(archive_path):
                self._archive_mode = True
                self._archive_path = archive_path
                self._archive_reader = self._zip_browser
                self._archive_current_prefix = ""
                self._load_archive_entries("")
                self._log(f"Archive (zipfile): {archive_path}")
                return
        from nexus_archive import open_archive
        reader = open_archive(archive_path)
        if not reader:
            # Fallback to system default
            os.startfile(archive_path)
            return
        self._archive_mode = True
        self._archive_path = archive_path
        self._archive_reader = reader
        self._archive_current_prefix = ""
        self._load_archive_entries("")
        self._log(f"Archive: {archive_path}")

    def _load_archive_entries(self, prefix: str):
        """Load archive entries matching a directory prefix into the table.

        Manages load archive entries operations and coordinates related state changes for the component.

        Args:
            prefix (str): The prefix parameter.
        """
        self._archive_current_prefix = prefix
        entries = self._archive_reader.list_entries()
        rows = []
        for e in entries:
            # Match entries directly inside this prefix
            rel = e.archive_path
            if prefix:
                if not rel.startswith(prefix):
                    continue
                rel = rel[len(prefix):]
            # Skip empty
            if not rel:
                continue
            # Determine if this is a direct child or nested
            parts = rel.replace("\\", "/").strip("/").split("/")
            if len(parts) > 1:
                # It's a subfolder — show as folder once
                folder_name = parts[0]
                folder_path = prefix + folder_name + "/"
                # Avoid duplicates
                if any(r.get("path") == folder_path for r in rows):
                    continue
                rows.append({
                    "name": folder_name,
                    "path": folder_path,
                    "isDir": True,
                    "size": 0,
                    "modifiedMs": 0,
                    "ext": "",
                    "is_archive_entry": True,
                })
            else:
                # Direct file
                rows.append({
                    "name": parts[0],
                    "path": e.archive_path,
                    "isDir": e.is_dir,
                    "size": e.size,
                    "modifiedMs": e.modified_ms,
                    "ext": Path(parts[0]).suffix.lstrip(".").lower(),
                    "is_archive_entry": True,
                })
        self.model.set_rows(rows)
        # Update breadcrumb to show archive path
        self.crumbs.setPath(f"{self._archive_path} > {prefix or '(root)'}")

    def _archive_activate(self, path: str):
        """Handle click inside archive — navigate or extract.

        Manages archive activate operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        if path.endswith("/"):
            # Subfolder — navigate into it
            self._load_archive_entries(path)
        else:
            # File — extract to temp and open
            self._extract_and_open(path)

    def _extract_and_open(self, entry_path: str):
        """Extract a single archive entry and open it.

        Manages extract and open operations and coordinates related state changes for the component.

        Args:
            entry_path (str): Filesystem path to the target file or directory.
        """
        import tempfile
        tmp_dir = tempfile.mkdtemp(prefix="nexus_")
        if hasattr(self._archive_reader, "extract_entry"):
            ok = self._archive_reader.extract_entry(entry_path, tmp_dir)
        else:
            from nexus_archive import SevenZipCLIReader
            reader = SevenZipCLIReader(self._archive_path,
                                       getattr(self, "_archive_password", ""))
            ok = reader.extract_entry(entry_path, tmp_dir)
            reader.close()
        if ok:
            extracted = Path(tmp_dir) / entry_path.replace("\\", "/")
            if extracted.is_file():
                os.startfile(str(extracted))  # noqa: S606
            else:
                self._log(f"Extract failed: {entry_path}")

    def _archive_go_up(self):
        """Go up one level in archive hierarchy.

        Manages archive go up operations and coordinates related state changes for the component.
        """
        if not self._archive_current_prefix:
            return  # Already at root
        parts = self._archive_current_prefix.rstrip("/").split("/")
        if len(parts) <= 1:
            self._load_archive_entries("")
        else:
            parent = "/".join(parts[:-1]) + "/"
            self._load_archive_entries(parent)

    def _extract_archives_here(self, archive_paths: list[str]):
        """Extract selected archive files to their parent directory (background).

        Manages extract archives here operations and coordinates related state changes for the component.

        Args:
            archive_paths (list[str]): Filesystem path to the target file or directory.
        """
        self._extract_archives_to_dir(
            archive_paths,
            {ap: str(Path(ap).parent / Path(ap).stem) for ap in archive_paths},
        )

    def _extract_archives_to(self, archive_paths: list[str]):
        """Extract selected archive files to a user-chosen directory.

        Manages extract archives to operations and coordinates related state changes for the component.

        Args:
            archive_paths (list[str]): Filesystem path to the target file or directory.
        """
        dest = QFileDialog.getExistingDirectory(self, "Extract to")
        if not dest:
            return
        dirs = {ap: str(Path(dest) / Path(ap).stem) for ap in archive_paths}
        self._extract_archives_to_dir(archive_paths, dirs)

    def _extract_archives_to_dir(self, archive_paths: list[str], dirs: dict):
        """Run extraction with live progress using QProcess + -bsp1.

        Manages extract archives to dir operations and coordinates related state changes for the component.

        Args:
            archive_paths (list[str]): Filesystem path to the target file or directory.
            dirs (dict): The dirs parameter.
        """
        from nexus_archive import _find_7z, _run_7z

        tasks = [(ap, dirs[ap]) for ap in archive_paths]
        if not tasks:
            return

        total_files = 0
        for ap, _ in tasks:
            rc, out, _ = _run_7z(["l", "-slt", ap], timeout=60)
            if rc in (0, 1):
                total_files += sum(1 for line in out.splitlines() if line.startswith("Path = "))

        self._extract_progress.start(Path(tasks[0][0]).name, total_files)

        self._extract_worker = _ExtractArchiveWorker(tasks)
        self._extract_worker.progress_update.connect(
            lambda pct, f, c, s: self._extract_progress.update_progress(pct, f, c, s)
        )
        self._extract_worker.finished_with_result.connect(self._on_extract_done)
        self._extract_worker.start()

    def _on_extract_done(self, success: bool, message: str = ""):
        """Finish the extraction panel and reload the current folder.

        Receives the completed data from the extract background worker, populates the view with results, and restores button states.

        Args:
            success (bool): The success parameter.
            message (str): Informational or progress status message.
        """
        if hasattr(self, "_extract_progress"):
            self._extract_progress.finish(success, message)
        self._reload_current()

    def _extract_entries_here(self, entry_paths: list[str]):
        """Extract entries from current archive to the archive's parent dir (async).

        Manages extract entries here operations and coordinates related state changes for the component.

        Args:
            entry_paths (list[str]): Filesystem path to the target file or directory.
        """
        if not self._archive_mode or not self._archive_reader:
            return
        dest = str(Path(self._archive_path).parent)
        self._extract_archive_entries(entry_paths, dest)

    def _extract_entries_to(self, entry_paths: list[str]):
        """Extract entries from current archive to a user-chosen directory (async).

        Manages extract entries to operations and coordinates related state changes for the component.

        Args:
            entry_paths (list[str]): Filesystem path to the target file or directory.
        """
        if not self._archive_mode or not self._archive_reader:
            return
        dest = QFileDialog.getExistingDirectory(self, "Extract to")
        if not dest:
            return
        self._extract_archive_entries(entry_paths, dest)

    def _extract_archive_entries(self, entry_paths: list[str], dest_dir: str):
        """Run entry extraction in background with progress panel.

        Manages extract archive entries operations and coordinates related state changes for the component.

        Args:
            entry_paths (list[str]): Filesystem path to the target file or directory.
            dest_dir (str): The dest dir parameter.
        """
        from nexus_archive import _find_7z

        if not entry_paths:
            return

        self._extract_progress.start(Path(self._archive_path).name, len(entry_paths))

        archive_path = self._archive_path
        password = getattr(self, "_archive_password", "")

        self._extract_worker = _ExtractEntryWorker(archive_path, entry_paths, dest_dir, password)
        self._extract_worker.progress_update.connect(
            lambda pct, f, c, s: self._extract_progress.update_progress(pct, f, c, s)
        )
        self._extract_worker.finished_with_result.connect(self._on_extract_done)
        self._extract_worker.start()

    def _exit_archive_mode(self):
        """Exit archive browsing, return to normal file browsing.

        Manages exit archive mode operations and coordinates related state changes for the component.
        """
        self._archive_mode = False
        self._archive_path = ""
        if self._archive_reader:
            self._archive_reader.close()
            self._archive_reader = None
        self._archive_current_prefix = ""
        self._reload_current()

    def _toggle_preview(self):
        """Toggle preview pane visibility.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        vis = not self.preview.isVisible()
        self.preview.setVisible(vis)
        self.btn_preview.setChecked(vis)
        if vis:
            self.splitter.setSizes([_scaled(210), _scaled(620), _scaled(270)])
        else:
            self.splitter.setSizes([_scaled(210), _scaled(890)])
        self._log(f"Preview pane {'ON' if vis else 'OFF'}")

    def _newfolder(self):
        """Newfolder.

        Manages newfolder operations and coordinates related state changes for the component.
        """
        self._new_folder()

    def _right_add_tab(self, path: str) -> None:
        """Append a right-pane tab and load its path.

        Manages right add tab operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        self._right_tabs.append({"path": path, "history": [path], "hindex": 0})
        if self._right_current_tab < 0:
            self._right_current_tab = 0
        self._right_load(path)

    def _right_tab(self) -> dict:
        """Return the active right-pane tab, defaulting to Home.

        Manages right tab operations and coordinates related state changes for the component.

        Returns:
            dict: Dictionary mapping identifiers to status or values.
        """
        if self._right_current_tab < 0 or self._right_current_tab >= len(self._right_tabs):
            return {"path": os.path.expanduser("~"), "history": [os.path.expanduser("~")], "hindex": 0}
        return self._right_tabs[self._right_current_tab]

    def _right_navigate(self, path: str, push: bool = True) -> None:
        """Load a folder into the right pane, pushing its history.

        Manages right navigate operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
            push (bool): The push parameter.
        """
        path = os.path.normpath(os.path.expanduser(path))
        if not os.path.isdir(path):
            return
        tab = self._right_tab()
        if push:
            tab["history"] = tab["history"][: tab["hindex"] + 1]
            tab["history"].append(path)
            tab["hindex"] = len(tab["history"]) - 1
        tab["path"] = path
        self._right_load(path)

    def _right_load(self, path: str) -> None:
        """List a path into the right pane via the engine.

        Manages right load operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        self.engine.list_dir(path, self._right_on_rows)

    def _right_on_rows(self, code: int, rows: list[dict]) -> None:
        """Push engine rows into the right-pane model and icon view.

        Manages right on rows operations and coordinates related state changes for the component.

        Args:
            code (int): The code parameter.
            rows (list[dict]): Table row index or list of row indices.
        """
        self._right_model.update_rows(rows)
        if self._right_stack.currentIndex() == 1:
            self._fill_right_icon_view(rows)

    def _fill_right_icon_view(self, rows: list[dict]):
        """Rebuild right-pane icon items from engine row dicts.

        Refreshes table or tree items with formatted values, tooltips, and status indicators based on the provided dataset.

        Args:
            rows (list[dict]): Table row index or list of row indices.
        """
        self._right_icon_list.blockSignals(True)
        self._right_icon_list.clear()
        for row in rows:
            it = QListWidgetItem(self.icons.icon_for(row), row.get("name", ""))
            it.setData(Qt.ItemDataRole.UserRole, row)
            it.setToolTip(row.get("path", ""))
            self._right_icon_list.addItem(it)
        self._right_icon_list.blockSignals(False)

    def _activate_right(self, idx):
        """Open a right-pane row: navigate dirs, launch files.

        Manages activate right operations and coordinates related state changes for the component.

        Args:
            idx: The idx parameter.
        """
        row = self._right_proxy.index(idx.row(), 0).data(Qt.ItemDataRole.UserRole)
        if row.get("isDir"):
            self._right_navigate(row.get("path", ""))
        elif row.get("path") and os.path.isfile(row["path"]):
            os.startfile(row["path"])  # noqa: S606

    # ────────────────────────── Quick Look (Space) ────────────────────────
    def _quick_look(self):
        """Show Quick Look popup for selected file.

        Manages quick look operations and coordinates related state changes for the component.
        """
        sel = self._selected_rows()
        if sel:
            pos = None
            if self.stack.currentIndex() == 0:
                idx = self.table.currentIndex()
                if idx.isValid():
                    pos = self.table.viewport().mapToGlobal(
                        self.table.visualRect(idx).center())
            else:
                item = self.icon_list.currentItem()
                if item:
                    pos = self.icon_list.viewport().mapToGlobal(
                        self.icon_list.visualItemRect(item).center())
            self._quicklook.show_file(sel[-1], pos)

    # ────────────────────────── Bulk Rename (Ctrl+B) ──────────────────────
    def _bulk_rename(self):
        """Open bulk rename dialog for selected files.

        Manages bulk rename operations and coordinates related state changes for the component.
        """
        sel = self._selected_paths()
        if len(sel) < 2:
            return
        self._bulk_rename_dlg = BulkRenameDialog(sel, self)
        self._bulk_rename_dlg.exec()

    # ────────────────────────── Duplicate Finder ────────────────────────────
    def _open_duplicate_finder(self):
        """Open the Duplicate Finder dialog for the current directory.

        Manages open duplicate finder operations and coordinates related state changes for the component.
        """
        path = self._tab()["path"]
        if not hasattr(self, '_dup_finder') or self._dup_finder is None:
            self._dup_finder = DuplicateFinderDialog(path, self)
        else:
            self._dup_finder.set_directory(path)
        self._dup_finder.show()
        self._dup_finder.raise_()
        self._dup_finder.activateWindow()

    # ────────────────────────── Color Tags ────────────────────────────────
    def _set_color_tag(self, color: str | None):
        """Set color tag on selected files.

        Manages set color tag operations and coordinates related state changes for the component.

        Args:
            color (str | None): The color parameter.
        """
        for path in self._selected_paths():
            self._color_tags.set_tag(path, color)
        self._update_status()

    def _get_color_tag(self, path: str) -> str | None:
        """Return the stored color tag for a path, if any.

        Manages get color tag operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.

        Returns:
            str | None: Formatted string or path.
        """
        return self._color_tags.get_tag(path)

    # ────────────────────────── Smart Folders ─────────────────────────────
    def _refresh_smart_folders(self):
        """Refresh the smart folders list in sidebar.

        Manages refresh smart folders operations and coordinates related state changes for the component.
        """
        self.smart_list.clear()
        for i, sf in enumerate(self._smart_folders.list_all()):
            it = QListWidgetItem(_fluent_action("star", size=16), sf.get("name", f"Smart {i}"))
            it.setData(Qt.ItemDataRole.UserRole, i)
            self.smart_list.addItem(it)

    def _open_smart_folder(self, index: int):
        """Open a smart folder by index.

        Manages open smart folder operations and coordinates related state changes for the component.

        Args:
            index (int): The index parameter.
        """
        folders = self._smart_folders.list_all()
        if 0 <= index < len(folders):
            sf = folders[index]
            root = sf.get("root", os.path.expanduser("~"))
            pattern = sf.get("pattern", "*")
            self.navigate(root)
            self.filter.setText(pattern)

    def _add_current_as_smart_folder(self):
        """Save current directory + filter as a smart folder.

        Manages add current as smart folder operations and coordinates related state changes for the component.
        """
        path = self._tab()["path"]
        pattern = self.filter.text()
        name = f"{Path(path).name} ({pattern})" if pattern else Path(path).name
        self._smart_folders.add(name, path, pattern)
        self._refresh_smart_folders()

    def _smart_folder_context_menu(self, pos):
        """Right-click menu for smart folders.

        Manages smart folder context menu operations and coordinates related state changes for the component.

        Args:
            pos: The pos parameter.
        """
        menu = QMenu(self)
        item = self.smart_list.itemAt(pos)
        if item:
            idx = item.data(Qt.ItemDataRole.UserRole)
            a = QAction(_fluent_action("folder", size=16), "Open", self)
            a.triggered.connect(lambda: self._open_smart_folder(idx))
            menu.addAction(a)
            a = QAction(_fluent_action("delete", size=16), "Remove", self)
            a.triggered.connect(lambda: self._remove_smart_folder(idx))
            menu.addAction(a)
        else:
            a = QAction(_fluent_action("new_folder", size=16), "Add current folder", self)
            a.triggered.connect(self._add_current_as_smart_folder)
            menu.addAction(a)
        menu.exec(self.smart_list.viewport().mapToGlobal(pos))

    def _remove_smart_folder(self, index: int):
        """Remove a smart folder.

        Manages remove smart folder operations and coordinates related state changes for the component.

        Args:
            index (int): The index parameter.
        """
        self._smart_folders.remove(index)
        self._refresh_smart_folders()

    # ────────────────────────── views ─────────────────────────────────────
    def _set_view_mode(self, mode: str):
        """Switch details/icons view and sync the view-toggle icon.

        Manages set view mode operations and coordinates related state changes for the component.

        Args:
            mode (str): The mode parameter.
        """
        if mode == "icons":
            self.stack.setCurrentIndex(1)
            self._view_mode = "icons"
            self.view_toggle.setIcon(_fluent_action("view_detail", size=_scaled(16)))
            self._fill_icon_view(self.model.rows)
        else:
            self.stack.setCurrentIndex(0)
            self._view_mode = "table"
            self.view_toggle.setIcon(_fluent_action("view_icon", size=_scaled(16)))

    def _toggle_view(self):
        """Flip between details and icons view modes.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        if self.stack.currentIndex() == 0:
            self._set_view_mode("icons")
        else:
            self._set_view_mode("table")

    def toggle_flat_branch_view(self):
        """Toggle Total Commander-style Flat Branch View (recursive listing of all subfolder files).

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        self._flat_branch_mode = not getattr(self, "_flat_branch_mode", False)
        current_path = self._tab()["path"]
        if self._flat_branch_mode:
            self.status_items.setText("Loading Flat Branch View…")
            self._log(f"Flat Branch View ON: {current_path}")
            self.engine.list_flat_branch(current_path, lambda code, rows: self._on_rows(code, rows))
        else:
            self._log(f"Flat Branch View OFF: {current_path}")
            self._load(current_path)

    def _fill_icon_view(self, rows: list[dict]):
        """Fill icon view with signal blocking to avoid UI freeze on large directories.

        Refreshes table or tree items with formatted values, tooltips, and status indicators based on the provided dataset.

        Args:
            rows (list[dict]): Table row index or list of row indices.
        """
        self.icon_list.blockSignals(True)
        self.icon_list.clear()
        for row in rows:
            it = QListWidgetItem(self.icons.icon_for(row), row.get("name", ""))
            it.setData(Qt.ItemDataRole.UserRole, row)
            it.setToolTip(row.get("path", ""))
            self.icon_list.addItem(it)
        self.icon_list.blockSignals(False)

    # ────────────────────────── selection ─────────────────────────────────
    def _selected_rows(self, sender=None) -> list[dict]:
        """Collect selected row dicts from the active (or sender's) view.

        Manages selected rows operations and coordinates related state changes for the component.

        Args:
            sender: Widget or object originating the action.

        Returns:
            list[dict]: List of processed items or identifiers.
        """
        rows: list[dict] = []
        src = sender or self.sender()
        if src in (self._right_table, self._right_icon_list):
            if self._right_stack.currentIndex() == 0:
                for i in self._right_table.selectionModel().selectedRows():
                    rows.append(self._right_proxy.index(i.row(), 0)
                                .data(Qt.ItemDataRole.UserRole))
            else:
                for it in self._right_icon_list.selectedItems():
                    rows.append(it.data(Qt.ItemDataRole.UserRole))
        elif self.stack.currentIndex() == 0:
            for i in self.table.selectionModel().selectedRows():
                rows.append(self.proxy.index(i.row(), 0)
                            .data(Qt.ItemDataRole.UserRole))
        else:
            for it in self.icon_list.selectedItems():
                rows.append(it.data(Qt.ItemDataRole.UserRole))
        return rows

    def _selected_paths(self, sender=None) -> list[str]:
        """Collect selected filesystem paths from the active view.

        Manages selected paths operations and coordinates related state changes for the component.

        Args:
            sender: Widget or object originating the action.

        Returns:
            list[str]: List of processed items or identifiers.
        """
        return [r.get("path", "") for r in self._selected_rows(sender) if r.get("path")]

    def _activate(self, idx):
        """Activate.

        Manages activate operations and coordinates related state changes for the component.

        Args:
            idx: The idx parameter.
        """
        row = self.proxy.index(idx.row(), 0).data(Qt.ItemDataRole.UserRole)
        self._activate_path(row)

    def _activate_path(self, row_or_path):
        """Open a row: dirs navigate, archives browse, files launch.

        Manages activate path operations and coordinates related state changes for the component.

        Args:
            row_or_path: Filesystem path to the target file or directory.
        """
        row = row_or_path if isinstance(row_or_path, dict) else {"path": str(row_or_path)}
        p = row.get("path", "")
        if self._archive_mode:
            # Inside an archive — navigate or extract
            self._archive_activate(p)
            return
        if row.get("isDir"):
            self.navigate(p)
        elif p and os.path.isfile(p):
            # Open archives inside our explorer, not Windows
            from nexus_archive import is_archive
            if is_archive(p):
                self._open_archive(p)
            else:
                os.startfile(p)  # noqa: S606

    def _update_status(self, sender=None, *_):
        """Refresh item counts, selection size, and undo hints.

        Manages update status operations and coordinates related state changes for the component.

        Args:
            sender: Widget or object originating the action.
        """
        total = self.proxy.rowCount()
        folders = sum(1 for r in self.model.rows if r.get("isDir"))
        files = total - folders
        items_text = f"{total} items ({folders} folders, {files} files)"

        sel = self._selected_rows(sender)
        if not sel:
            sel_text = ""
        else:
            sel_size = sum(int(r.get("size", 0) or 0) for r in sel if not r.get("isDir"))
            sel_text = f"{len(sel)} selected ({human(sel_size)})"

        self.status_items.setText(items_text)
        self.status_sel.setText(sel_text)

        if not sel:
            self.preview.show_entry(None)
        else:
            self.preview.show_entry(sel[-1])

        if self._status_mode == 1 and sel:
            self.status_items.setText(f"{items_text}  |  Selected: {sel_text}")
        elif self._status_mode == 2:
            self.status_items.setText(self._status_disk_text or items_text)

    def _cycle_status_mode(self):
        """Cycle the status bar through items/selected/disk-free modes.

        Manages cycle status mode operations and coordinates related state changes for the component.
        """
        self._status_mode = (self._status_mode + 1) % 3
        if self._status_mode == 2:
            path = self._tab().get("path", "")
            drive = os.path.splitdrive(path)[0]
            if drive:
                try:
                    usage = shutil.disk_usage(drive + "\\")
                    free_text = (
                        f"{drive}\\  Free: {human(usage.free)}  "
                        f"Total: {human(usage.total)}"
                    )
                except OSError:
                    free_text = f"{drive}\\  Disk info unavailable"
            else:
                free_text = "Disk info unavailable"
            self._status_disk_text = free_text
        self._update_status()

    def _on_transfer_started(self, job_id: str):
        """Note an active transfer id in the status bar.

        Manages on transfer started operations and coordinates related state changes for the component.

        Args:
            job_id (str): The job id parameter.
        """
        if hasattr(self, "status_items"):
            self.status_items.setText(f"Transfer active ({job_id[:8]}…)")

    def _on_transfer_added(self, job_id: str):
        """Job added to transfer queue (tracked live by preview pane dock).

        The dock updates itself from the queue's own ``job_added`` signal
        (see ``TransferStatusDock.bind_queue``); no manual refresh is needed.
        """
        return

    def open_transfer_monitor(self):
        """Lazily open the transfer monitor dialog for the queue.

        Manages open transfer monitor operations and coordinates related state changes for the component.
        """
        if self._transfer_monitor is None:
            from nexus_transfer_monitor import TransferMonitorDialog

            self._transfer_monitor = TransferMonitorDialog(
                self._transfer_queue, self)
        self._transfer_monitor.open_for()

    def _on_transfer_progress(self, job_id: str, percent: int, text: str):
        """Show live transfer percent and text in the status bar.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            job_id (str): The job id parameter.
            percent (int): The percent parameter.
            text (str): Display text string.
        """
        if hasattr(self, "status_items"):
            self.status_items.setText(f"Transfer {percent}% — {text}")

    def _on_transfer_cancelled(self, job_id: str):
        """Note cancellation in the status bar and reload.

        Manages on transfer cancelled operations and coordinates related state changes for the component.

        Args:
            job_id (str): The job id parameter.
        """
        if hasattr(self, "status_items"):
            self.status_items.setText("Transfer cancelled")
        self._reload_current()

    def _on_transfer_completed(self, job_id: str, success: bool, message: str):
        """Reload the current folder after a transfer finishes.

        Manages on transfer completed operations and coordinates related state changes for the component.

        Args:
            job_id (str): The job id parameter.
            success (bool): The success parameter.
            message (str): Informational or progress status message.
        """
        self._reload_current()

    def _on_transfer_queue_empty(self):
        """Reload the current folder once the transfer queue drains.

        Manages on transfer queue empty operations and coordinates related state changes for the component.
        """
        self._reload_current()
    # ────────────────────────── operations ────────────────────────────────
    def _unique_name(self, base: str) -> str:
        """Return a collision-free name by appending a (2), (3), ... suffix.

        Manages unique name operations and coordinates related state changes for the component.

        Args:
            base (str): The base parameter.

        Returns:
            str: Formatted string or path.
        """
        existing = {r.get("name", "").lower() for r in self.model.rows}
        name, i = base, 2
        while name.lower() in existing:
            name = f"{base} ({i})"
            i += 1
        return name

    def _new_folder(self):
        """Create a new folder in the current directory.

        Manages new folder operations and coordinates related state changes for the component.
        """
        curr_path = Path(self._tab()["path"])
        name = self._unique_name("New Folder")
        dest, created_parents = create_nested_folder(curr_path, name)
        self._undo_manager.record_new_folder(str(dest), created_parents=created_parents)
        self._reload_current()
        self._log(f"New folder: {dest.name}")

    def _new_nested_folder(self):
        """Open dialog to create single or deep nested folder paths (e.g. 'src/components/ui').

        Manages new nested folder operations and coordinates related state changes for the component.
        """
        curr_path = Path(self._tab()["path"])
        dlg = NestedFolderDialog(curr_path, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            target_path_str = dlg.get_target_path()
            if not target_path_str:
                return
            try:
                target, created_parents = create_nested_folder(curr_path, target_path_str)
                self._undo_manager.record_new_folder(str(target), created_parents=created_parents)
                self._reload_current()
                self._log(f"Created nested folder: {target_path_str}")
            except Exception as exc:
                QMessageBox.critical(self, "Error Creating Folder", f"Could not create folder:\n{exc}")

    def _new_file(self, template_ext: str = ""):
        """Create a new file in the current directory with optional template extension.

        Manages new file operations and coordinates related state changes for the component.

        Args:
            template_ext (str): The template ext parameter.
        """
        curr_path = Path(self._tab()["path"])
        ext = template_ext if template_ext.startswith(".") else ""
        base_name = f"New Document{ext}" if ext else "New Document.txt"
        name = self._unique_name(base_name)
        content = FILE_TEMPLATES.get(ext, {}).get("content", "")
        target, created_parents = create_nested_file(curr_path, name, content=content)
        self._undo_manager.record_new_file(str(target), content=content, created_parents=created_parents)
        self._reload_current()
        self._log(f"New file created: {name}")

    def _new_nested_file(self):
        """Open dialog to create a file inside a nested path with template selection.

        Manages new nested file operations and coordinates related state changes for the component.
        """
        curr_path = Path(self._tab()["path"])
        dlg = NestedFileDialog(curr_path, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            rel_path, content = dlg.get_result()
            if not rel_path:
                return
            try:
                target, created_parents = create_nested_file(curr_path, rel_path, content=content)
                self._undo_manager.record_new_file(str(target), content=content, created_parents=created_parents)
                self._reload_current()
                self._log(f"Created nested file: {rel_path}")
            except Exception as exc:
                QMessageBox.critical(self, "Error Creating File", f"Could not create file:\n{exc}")

    def _batch_scaffold(self):
        """Open dialog to scaffold entire project or directory hierarchies.

        Manages batch scaffold operations and coordinates related state changes for the component.
        """
        curr_path = Path(self._tab()["path"])
        dlg = BatchScaffoldDialog(curr_path, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            spec_text = dlg.get_spec_text()
            if not spec_text.strip():
                return
            try:
                result = scaffold_hierarchy(curr_path, spec_text)
                created_files = result.get("created_files", [])
                created_dirs = result.get("created_dirs", [])
                errors = result.get("errors", [])

                if created_files or created_dirs:
                    self._undo_manager.record_batch_create(
                        created_files=created_files,
                        created_dirs=created_dirs,
                        label=f"Scaffold {len(created_files) + len(created_dirs)} items",
                    )
                    self._reload_current()
                    total = len(created_files) + len(created_dirs)
                    self._log(f"Scaffolded {total} items ({len(created_dirs)} folders, {len(created_files)} files)")

                if errors:
                    QMessageBox.warning(
                        self,
                        "Scaffold Warnings",
                        "Some items could not be created:\n" + "\n".join(errors[:10]),
                    )
            except Exception as exc:
                QMessageBox.critical(self, "Error Scaffolding Hierarchy", f"Could not scaffold hierarchy:\n{exc}")

    def _new_folder_with_selection(self):
        """Create a new folder and move all selected items into it.

        Manages new folder with selection operations and coordinates related state changes for the component.
        """
        sel = self._selected_paths()
        if not sel:
            return
        base = Path(sel[0]).stem
        name = self._unique_name(base)
        dest_dir = Path(self._tab()["path"]) / name
        os.makedirs(dest_dir, exist_ok=True)
        self._transfer_queue.enqueue(kind="move", sources=sel, dest=str(dest_dir))
        self._log(f"Moved {len(sel)} items to {name}/")

    def _compress_to(self, fmt: str):
        """Compress selected files/folders into an archive.

        Manages compress to operations and coordinates related state changes for the component.

        Args:
            fmt (str): The fmt parameter.
        """
        sel = self._selected_paths()
        if not sel:
            return
        from nexus_archive import _find_7z, _run_7z

        ext_map = {
            "ZIP": (".zip", "-tzip"),
            "7z": (".7z", "-t7z"),
            "TAR.GZ": (".tar.gz", "-ttar"),
        }
        ext, flag = ext_map.get(fmt, (".zip", "-tzip"))

        # Default archive name based on first item
        first = Path(sel[0])
        if len(sel) == 1:
            default_name = first.stem + ext
        else:
            default_name = first.parent.name + ext

        name, ok = QInputDialog.getText(self, "Compress", "Archive name:",
                                        text=default_name)
        if not ok or not name:
            return
        if not name.endswith(ext):
            name += ext

        archive_path = str(Path(self._tab()["path"]) / name)

        # Show progress
        if not hasattr(self, "_extract_progress"):
            self._extract_progress = ExtractionProgressWidget()
        self._extract_progress.start(f"Creating {name}")

        exe = _find_7z()
        if not exe:
            self._extract_progress.finish(False, "7z.exe not found")
            return

        # Build file list via temp file for many files
        import tempfile
        filelist = tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                               delete=False, encoding="utf-8")
        try:
            for sp in sel:
                filelist.write(sp + "\n")
            filelist.close()

            cmd = [exe, "a", flag, archive_path, f"@{filelist.name}",
                   "-mmt=on", "-bsp1", "-bso0"]

            self._compress_worker = _CompressWorker(cmd, name)
            self._compress_worker.progress_update.connect(
                lambda pct, f, c, s: self._extract_progress.update_progress(pct, f, c, s))
            self._compress_worker.finished_with_result.connect(
                lambda ok, msg: (self._extract_progress.finish(ok, msg),
                                 self._reload_current()))
            self._compress_worker.start()
        finally:
            try:
                os.unlink(filelist.name)
            except OSError:
                pass

    def _move_to_folder(self):
        """Move selected items to a user-chosen folder.

        Manages move to folder operations and coordinates related state changes for the component.
        """
        sel = self._selected_paths()
        if not sel:
            return
        dest = QFileDialog.getExistingDirectory(self, "Move to")
        if not dest:
            return
        self._transfer_queue.enqueue(kind="move", sources=sel, dest=dest)

    def _rename(self):
        """Rename.

        Manages rename operations and coordinates related state changes for the component.
        """
        sel = self._selected_paths()
        if len(sel) != 1:
            return
        old = sel[0]
        old_name = Path(old).name
        new, ok = QInputDialog.getText(self, "Rename", "New name:", text=old_name)
        if not ok or not new or new.strip() == old_name:
            return
        new = new.strip()
        invalid_chars = r'\/:*?"<>|'
        if any(c in new for c in invalid_chars):
            QMessageBox.warning(self, "Invalid Name", f"A file name cannot contain any of the following characters:\n{invalid_chars}")
            return
        new_path = str(Path(old).parent / new)
        if Path(new_path).exists() and Path(new_path).resolve() != Path(old).resolve():
            QMessageBox.warning(self, "Item Exists", f"An item named '{new}' already exists in this folder.")
            return
        try:
            self._undo_manager.record_rename(old, new_path)
            self.engine.simple(["rename", old, new], lambda ok2, out, err: self._reload_current())
            self._log(f"Rename: {old_name} -> {new}")
            self.status_items.setText(f"Renamed to '{new}'")
        except Exception as exc:
            QMessageBox.critical(self, "Rename Failed", f"Could not rename item:\n{exc}")

    def _clip(self, mode: str):
        """Clip.

        Manages clip operations and coordinates related state changes for the component.

        Args:
            mode (str): The mode parameter.
        """
        sel = self._selected_paths()
        if sel:
            if mode == "cut":
                _nexus_clipboard.cut(sel)
            else:
                _nexus_clipboard.copy(sel)
            self.status_items.setText(f"{mode} {len(sel)} item(s)")
            self._log(f"Clipboard: {mode} {len(sel)} items")

    def _paste(self, target_dest: str | None = None):
        """Paste.

        Manages paste operations and coordinates related state changes for the component.

        Args:
            target_dest (str | None): The target dest parameter.
        """
        data = _nexus_clipboard.paste()
        if not data and hasattr(self, "preview") and hasattr(self.preview, "staging_shelf"):
            shelf = self.preview.staging_shelf
            if shelf._staged_paths:
                data = (shelf._mode, list(shelf._staged_paths))
        if not data:
            self.status_items.setText("Nothing to paste")
            return
        mode, paths = data
        dest = target_dest or self._tab()["path"]
        # Filter out non-existent files (may have been deleted)
        paths = [p for p in paths if os.path.exists(p)]
        if not paths:
            _nexus_clipboard.clear()
            if hasattr(self, "preview") and hasattr(self.preview, "staging_shelf"):
                self.preview.staging_shelf.clear_staged()
            self.status_items.setText("Source files no longer exist")
            return
        for p in paths:
            dst = str(Path(dest) / Path(p).name)
            if mode == "copy":
                self._undo_manager.record_copy(p, dst)
            else:
                self._undo_manager.record_move(p, dst)
        self._log(f"Paste: {mode} {len(paths)} -> {dest}")
        # Use transfer queue for serialized execution
        self._transfer_queue.enqueue(
            kind="copy" if mode == "copy" else "move",
            sources=paths,
            dest=dest,
        )
        # Clear clipboard after cut (move)
        if mode == "cut":
            _nexus_clipboard.clear()
            if hasattr(self, "preview") and hasattr(self.preview, "staging_shelf"):
                self.preview.staging_shelf.clear_staged()
        self.status_items.setText(f"{mode.capitalize()}ing {len(paths)} item(s) to {Path(dest).name or dest}")

    def _on_staging_paste(self, mode: str, paths: list[str], target_dir: str):
        """Enqueue a queued transfer for shelf paste requests.

        Manages on staging paste operations and coordinates related state changes for the component.

        Args:
            mode (str): The mode parameter.
            paths (list[str]): Filesystem path to the target file or directory.
            target_dir (str): The target dir parameter.
        """
        dest = target_dir or self._tab()["path"]
        valid_paths = [p for p in paths if os.path.exists(p)]
        if not valid_paths or not dest:
            self.preview.staging_shelf.clear_staged()
            self.status_items.setText("Source files no longer exist")
            return
        for p in valid_paths:
            dst = str(Path(dest) / Path(p).name)
            if mode == "copy":
                self._undo_manager.record_copy(p, dst)
            else:
                self._undo_manager.record_move(p, dst)
        self._log(f"Staging Transfer: {mode} {len(valid_paths)} -> {dest}")
        self._transfer_queue.enqueue(
            kind="copy" if mode == "copy" else "move",
            sources=valid_paths,
            dest=dest,
        )
        if mode == "cut":
            self.preview.staging_shelf.clear_staged()
            _nexus_clipboard.clear()
        self.status_items.setText(f"{mode.capitalize()}ing {len(valid_paths)} item(s) to {Path(dest).name or dest}")

    def _on_stage_selected(self):
        """Stage the current selection onto the shelf.

        Manages on stage selected operations and coordinates related state changes for the component.
        """
        sel = self._selected_paths()
        if sel:
            self.preview.staging_shelf.add_paths(sel, mode=_nexus_clipboard._mode or "copy")
            self.status_items.setText(f"Staged {len(sel)} item(s) to shelf")

    def _delete(self, permanent: bool = False):
        """Delete.

        Manages delete operations and coordinates related state changes for the component.

        Args:
            permanent (bool): The permanent parameter.
        """
        sel = self._selected_paths()
        if not sel:
            return
        if permanent:
            r = QMessageBox.question(
                self, "Delete permanently",
                f"Permanently delete {len(sel)} item(s)?\nThis cannot be undone.")
            if r != QMessageBox.StandardButton.Yes:
                return
        self._log(f"Delete ({'permanent' if permanent else 'recycle'}): {len(sel)} items")
        # Record in undo stack before executing
        for p in sel:
            self._undo_manager.record_delete(p)
        # Use transfer queue for serialized execution
        self._transfer_queue.enqueue(
            kind="delete",
            sources=sel,
            permanent=permanent,
        )

    def _undo(self):
        """Undo.

        Manages undo operations and coordinates related state changes for the component.
        """
        msg = self._undo_manager.undo()
        if msg:
            self._log(msg)
            self.status_items.setText(msg)
            self.status_undo.setText(self._undo_manager.undo_description() or "")
            self._reload_current()
        else:
            self.status_items.setText("Nothing to undo")

    def _redo(self):
        """Redo.

        Manages redo operations and coordinates related state changes for the component.
        """
        msg = self._undo_manager.redo()
        if msg:
            self._log(msg)
            self.status_items.setText(msg)
            self.status_undo.setText(self._undo_manager.redo_description() or "")
            self._reload_current()
        else:
            self.status_items.setText("Nothing to redo")

    def _select_all(self):
        """Select all items in the active details or icons view.

        Manages select all operations and coordinates related state changes for the component.
        """
        if self.stack.currentIndex() == 0:
            self.table.selectAll()
        else:
            self.icon_list.selectAll()

    def _on_table_clicked(self, idx):
        """Preview the clicked details row.

        Manages on table clicked operations and coordinates related state changes for the component.

        Args:
            idx: The idx parameter.
        """
        row = self.proxy.index(idx.row(), 0).data(Qt.ItemDataRole.UserRole)
        if row:
            self.preview.show_entry(row)

    def _on_current_changed(self, current: QModelIndex, _prev: QModelIndex):
        """Preview the newly current details row.

        Manages on current changed operations and coordinates related state changes for the component.

        Args:
            current (QModelIndex): The current parameter.
            _prev (QModelIndex): The  prev parameter.
        """
        if current.isValid():
            row = self.proxy.index(current.row(), 0).data(Qt.ItemDataRole.UserRole)
            if row:
                self.preview.show_entry(row)

    # ────────────────────────── drag and drop ─────────────────────────────
    def dragEnterEvent(self, ev: QDragEnterEvent):
        """Dragenterevent.

        Manages dragEnterEvent operations and coordinates related state changes for the component.

        Args:
            ev (QDragEnterEvent): The Qt event object.
        """
        ev.acceptProposedAction()

    def dragMoveEvent(self, ev: QDragMoveEvent):
        """Dragmoveevent.

        Manages dragMoveEvent operations and coordinates related state changes for the component.

        Args:
            ev (QDragMoveEvent): The Qt event object.
        """
        ev.acceptProposedAction()
        try:
            pos = ev.position().toPoint() if hasattr(ev, "position") else ev.pos()
            vp_pos = self.table.viewport().mapFrom(self, pos)
            idx = self.table.indexAt(vp_pos)
            if idx.isValid():
                row = self.proxy.index(idx.row(), 0).data(Qt.ItemDataRole.UserRole)
                if row and row.get("isDir"):
                    self.table.setCurrentIndex(idx)
                    mime = ev.mimeData()
                    if mime is not None and hasattr(self, "status_sel"):
                        if mime.hasUrls():
                            n = len(mime.urls())
                        elif mime.hasText():
                            n = len([p for p in mime.text().splitlines() if p.strip()])
                        else:
                            n = 0
                        if n > 0:
                            self.status_sel.setText(
                                f"Drop {n} item(s) into {row.get('name') or row.get('path')}")
        except Exception:
            pass

    def dragLeaveEvent(self, ev):
        """Dragleaveevent.

        Manages dragLeaveEvent operations and coordinates related state changes for the component.

        Args:
            ev: The Qt event object.
        """
        try:
            self._update_status()
        except Exception:
            pass

    def dropEvent(self, ev):
        """Dropevent.

        Manages dropEvent operations and coordinates related state changes for the component.

        Args:
            ev: The Qt event object.
        """
        if not self._handle_viewport_drop(self, ev):
            ev.ignore()

    def startDrag(self, actions: Qt.DropAction):
        """Startdrag.

        Manages startDrag operations and coordinates related state changes for the component.

        Args:
            actions (Qt.DropAction): The actions parameter.
        """
        sel = self._selected_paths()
        if not sel:
            return
        mime = QMimeData()
        urls = [QUrl.fromLocalFile(p) for p in sel if os.path.exists(p)]
        mime.setUrls(urls)
        mime.setText("\n".join(sel))

        drag = QDrag(self)
        drag.setMimeData(mime)
        # Use the first file's icon as drag pixmap
        if sel:
            pix = self.icons.icon_for({"path": sel[0], "isDir": os.path.isdir(sel[0])})
            if pix and not pix.isNull():
                drag.setPixmap(pix.pixmap(_scaled(32), _scaled(32)))

        drag.exec(actions)

    def _search(self):
        """Search.

        Manages search operations and coordinates related state changes for the component.
        """
        dlg = SearchDialog(self.engine, self._tab()["path"], self)
        dlg.show()

    # ────────────────────────── context menu ──────────────────────────────
    def _context_menu(self, pos):
        """Build and show the selection/background context menu.

        Manages context menu operations and coordinates related state changes for the component.

        Args:
            pos: The pos parameter.
        """
        from nexus_archive import is_archive as _is_archive
        menu = QMenu(self)
        sender = self.sender()

        # Check if the right-click actually landed on an item
        if sender is not None:
            if hasattr(self, "table") and (sender == self.table or (hasattr(self.table, "viewport") and sender == self.table.viewport())):
                idx = self.table.indexAt(pos)
                if idx.isValid():
                    selected_rows = {i.row() for i in self.table.selectionModel().selectedRows()}
                    if idx.row() not in selected_rows:
                        self.table.selectRow(idx.row())
                else:
                    self.table.clearSelection()
            elif hasattr(self, "icon_list") and (sender == self.icon_list or (hasattr(self.icon_list, "viewport") and sender == self.icon_list.viewport())):
                it = self.icon_list.itemAt(pos)
                if it is not None:
                    if not it.isSelected():
                        self.icon_list.setCurrentItem(it)
                else:
                    self.icon_list.clearSelection()
            elif hasattr(self, "_right_table") and (sender == self._right_table or sender == getattr(self._right_table, "viewport", lambda: None)()):
                idx = self._right_table.indexAt(pos)
                if idx.isValid():
                    selected_rows = {i.row() for i in self._right_table.selectionModel().selectedRows()}
                    if idx.row() not in selected_rows:
                        self._right_table.selectRow(idx.row())
                else:
                    self._right_table.clearSelection()
            elif hasattr(self, "_right_icon_list") and (sender == self._right_icon_list or sender == getattr(self._right_icon_list, "viewport", lambda: None)()):
                it = self._right_icon_list.itemAt(pos)
                if it is not None:
                    if not it.isSelected():
                        self._right_icon_list.setCurrentItem(it)
                else:
                    self._right_icon_list.clearSelection()

        sel = self._selected_rows(sender)
        paths = [r.get("path", "") for r in sel if r.get("path")]

        # Determine clipboard / staging shelf contents
        has_clip = _nexus_clipboard.has_data or (
            hasattr(self, "preview") and hasattr(self.preview, "staging_shelf") and bool(self.preview.staging_shelf._staged_paths)
        )
        clip_mode = _nexus_clipboard._mode or (
            self.preview.staging_shelf._mode if hasattr(self, "preview") and hasattr(self.preview, "staging_shelf") else "copy"
        )
        paste_text = "Move Here" if clip_mode == "cut" else "Paste"

        # Archive mode context menu
        if self._archive_mode:
            def _open_all_archive():
                """Open every selected archive path in archive mode.

                Manages open all archive operations and coordinates related state changes for the component.
                """
                for p in paths:
                    self._archive_activate(p)
            menu.addAction("Open", _open_all_archive)
            menu.addSeparator()
            archive_files = [p for p in paths if not p.endswith("/")]
            if archive_files:
                menu.addAction("Extract Here", lambda: self._extract_entries_here(archive_files))
                menu.addAction("Extract to\u2026", lambda: self._extract_entries_to(archive_files))
                menu.addSeparator()
            menu.addAction("Exit Archive", self._exit_archive_mode)
            menu.addAction("Select All", self._select_all)
            pos_global = sender.viewport().mapToGlobal(pos) if hasattr(sender, "viewport") else self.mapToGlobal(pos)
            menu.exec(pos_global)
            return

        if sel:
            def _mi(icon_name, text, slot, accent=False):
                """Mi.

                Manages mi operations and coordinates related state changes for the component.

                Args:
                    icon_name: The icon name parameter.
                    text: Display text string.
                    slot: The slot parameter.
                    accent: Whether to apply the primary accent styling.
                """
                a = QAction(_fluent_action(icon_name, accent=accent, size=_scaled(16)), text, self)
                a.triggered.connect(slot)
                menu.addAction(a)
                return a

            def _open_all_sel():
                """Activate every selected row.

                Manages open all sel operations and coordinates related state changes for the component.
                """
                for r in sel:
                    self._activate_path(r)

            _mi("folder", "Open", _open_all_sel)
            _mi("new_file", "Open in New Tab", self._open_in_new_tab)
            menu.addSeparator()

            _mi("cut", "Cut", lambda: self._clip("cut"))
            _mi("copy", "Copy", lambda: self._clip("copy"))

            # Paste option when items are selected
            act_paste = _mi("paste", paste_text, lambda: self._paste())
            act_paste.setEnabled(has_clip)

            # If right-clicked on a directory, provide dedicated "Paste into folder"
            if len(paths) == 1 and os.path.isdir(paths[0]):
                folder_name = Path(paths[0]).name or paths[0]
                act_into = _mi("folder", f"Paste into '{folder_name}'", lambda p=paths[0]: self._paste(p))
                act_into.setEnabled(has_clip)

            _mi("copy", "Copy Path", lambda: QApplication.clipboard().setText("\n".join(paths)))
            _mi("copy", "Copy Filename", lambda: QApplication.clipboard().setText("\n".join(Path(p).name for p in paths)))
            menu.addSeparator()

            if len(paths) == 1:
                _mi("rename", "Rename\u2026", self._rename)
            _mi("delete", "Delete", self._delete)
            _mi("delete", "Delete permanently", lambda: self._delete(True), accent=True)
            menu.addSeparator()

            if len(paths) >= 2:
                _mi("rename", "Bulk rename\u2026 (Ctrl+B)", self._bulk_rename)
                _mi("new_folder", "New folder with selection", self._new_folder_with_selection)
                _mi("folder", "Move to folder\u2026", self._move_to_folder)

            # Compress submenu
            compress_menu = menu.addMenu("Compress")
            compress_menu.addAction("ZIP (.zip)", lambda: self._compress_to("ZIP"))
            compress_menu.addAction("7z (.7z)", lambda: self._compress_to("7z"))
            compress_menu.addAction("TAR.GZ (.tar.gz)", lambda: self._compress_to("TAR.GZ"))
            menu.addSeparator()

            # Archive-specific actions for .zip/.rar/.7z etc.
            archive_paths = [p for p in paths if _is_archive(p)]
            if archive_paths:
                _mi("folder", "Open Archive", lambda: [self._open_archive(p) for p in archive_paths])
                _mi("folder", "Extract Here", lambda: self._extract_archives_here(archive_paths))
                _mi("folder", "Extract to\u2026", lambda: self._extract_archives_to(archive_paths))
                menu.addSeparator()

            tag_menu = menu.addMenu("Color tag")
            for color_name, color_hex in ColorTagManager.TAG_COLORS.items():
                tag_menu.addAction(color_name.capitalize(),
                                    lambda c=color_name: self._set_color_tag(c))
            tag_menu.addSeparator()
            tag_menu.addAction("Remove tag", lambda: self._set_color_tag(None))
            menu.addSeparator()
            menu.addAction("Select All", self._select_all)
            menu.addAction("Invert Selection", self._invert_selection)
            if len(paths) == 1:
                _mi("info", "Properties", lambda: self._show_properties(paths[0]))
                if os.path.isfile(paths[0]):
                    _mi("info", "Calculate Checksums\u2026", lambda: self._calculate_file_hashes(paths[0]))
            if len(paths) == 1 and os.path.isfile(paths[0]):
                _mi("expand_right", "Open with\u2026", lambda: self._open_with(paths[0]))
        else:
            def _mi_bg(icon_name, text, slot):
                """Create a fluent-icon background-menu action for empty space.

                Manages mi bg operations and coordinates related state changes for the component.

                Args:
                    icon_name: The icon name parameter.
                    text: Display text string.
                    slot: The slot parameter.
                """
                a = QAction(_fluent_action(icon_name, size=_scaled(16)), text, self)
                a.triggered.connect(slot)
                menu.addAction(a)
                return a

            _mi_bg("new_folder", "New folder", self._new_folder)

            new_sub = menu.addMenu("New")
            if hasattr(new_sub, "setIcon"):
                new_sub.setIcon(_fluent_action("new_folder", size=_scaled(16)))

            act_folder = new_sub.addAction("Folder\tCtrl+Shift+N", self._new_folder)
            if hasattr(act_folder, "setIcon"):
                act_folder.setIcon(_fluent_action("new_folder", size=_scaled(16)))

            act_nested_f = new_sub.addAction("Nested Folders…\tCtrl+Alt+N", self._new_nested_folder)
            if hasattr(act_nested_f, "setIcon"):
                act_nested_f.setIcon(_fluent_action("folder", size=_scaled(16)))

            new_sub.addSeparator()
            act_file = new_sub.addAction("File…\tCtrl+N", self._new_file)
            if hasattr(act_file, "setIcon"):
                act_file.setIcon(_fluent_action("new_file", size=_scaled(16)))

            act_nested_file = new_sub.addAction("File in Nested Path…\tCtrl+Alt+F", self._new_nested_file)
            if hasattr(act_nested_file, "setIcon"):
                act_nested_file.setIcon(_fluent_action("new_file", size=_scaled(16)))

            new_sub.addSeparator()
            act_scaffold = new_sub.addAction("Batch Scaffold Project / Tree…\tCtrl+Shift+B", self._batch_scaffold)
            if hasattr(act_scaffold, "setIcon"):
                act_scaffold.setIcon(_fluent_action("copy", size=_scaled(16)))

            new_sub.addSeparator()
            tpl_sub = new_sub.addMenu("Templates")
            for ext, info in FILE_TEMPLATES.items():
                tpl_act = tpl_sub.addAction(info["label"], lambda _c=False, e=ext: self._new_file(e))
                if hasattr(tpl_act, "setIcon"):
                    tpl_act.setIcon(_fluent_action("new_file", size=_scaled(16)))

            menu.addSeparator()
            act_paste_bg = _mi_bg("paste", paste_text, self._paste)
            act_paste_bg.setEnabled(has_clip)

            menu.addSeparator()
            _mi_bg("refresh", "Refresh", self._reload_current)
            _mi_bg("star", "Save as smart folder", self._add_current_as_smart_folder)
            menu.addSeparator()
            menu.addAction("Select All", self._select_all)
            menu.addSeparator()
            _mi_bg("copy", "Find Duplicates (Ctrl+Shift+F)", self._open_duplicate_finder)

            sort_menu = menu.addMenu("Sort By")
            for col_name, col_idx in self._SORT_COLUMNS:
                sub = sort_menu.addMenu(col_name)
                asc = QAction(f"{col_name} \u2191 Ascending", self)
                asc.triggered.connect(
                    lambda checked=False, c=col_idx: self.proxy.sort(c, Qt.SortOrder.AscendingOrder))
                sub.addAction(asc)
                desc = QAction(f"{col_name} \u2193 Descending", self)
                desc.triggered.connect(
                    lambda checked=False, c=col_idx: self.proxy.sort(c, Qt.SortOrder.DescendingOrder))
                sub.addAction(desc)

        pos_global = sender.viewport().mapToGlobal(pos) if (sender is not None and hasattr(sender, "viewport")) else self.mapToGlobal(pos)
        menu.exec(pos_global)

    def _open_in_new_tab(self):
        """Open selected folder (or file's parent) in a new tab.

        Manages open in new tab operations and coordinates related state changes for the component.
        """
        for path in self._selected_paths():
            if os.path.isdir(path):
                self.add_tab(path)
            elif os.path.isfile(path):
                self.add_tab(os.path.dirname(path))

    def _open_in_terminal(self):
        """Show terminal panel and cd to selected path.

        Manages open in terminal operations and coordinates related state changes for the component.
        """
        if not self.terminal_panel.isVisible():
            self._toggle_terminal()
        paths = self._selected_paths()
        if paths:
            target = paths[0]
            if os.path.isfile(target):
                target = os.path.dirname(target)
            self.terminal_panel.set_cwd(target)
            self.terminal_panel.input.setFocus()

    def _invert_selection(self):
        """Invert the current selection.

        Manages invert selection operations and coordinates related state changes for the component.
        """
        if self.stack.currentIndex() == 0:
            model = self.proxy
            sel_model = self.table.selectionModel()
            all_rows = set(range(model.rowCount()))
            current = {idx.row() for idx in sel_model.selectedRows()}
            to_select = all_rows - current
            sel_model.clearSelection()
            for row in to_select:
                idx = model.index(row, 0)
                sel_model.select(idx, sel_model.SelectFlag.Select | sel_model.SelectFlag.Rows)
        else:
            items = [self.icon_list.item(i) for i in range(self.icon_list.count())]
            current = set(self.icon_list.selectedItems())
            for it in items:
                if it in current:
                    it.setSelected(False)
                else:
                    it.setSelected(True)

    def _show_properties(self, path_or_row):
        """Show Properties dialog for a single file/folder.

        Manages show properties operations and coordinates related state changes for the component.

        Args:
            path_or_row: Filesystem path to the target file or directory.
        """
        if isinstance(path_or_row, dict):
            row = dict(path_or_row)
        else:
            path = str(path_or_row)
            row = None
            for r in self.model.rows:
                if r.get("path") == path:
                    row = r
                    break
            if not row:
                row = {"name": Path(path).name, "path": path,
                       "isDir": os.path.isdir(path)}
        dlg = PropertiesDialog(row, self)
        dlg.exec()

    def _calculate_file_hashes(self, path_or_row):
        """Show File Checksums dialog for a file.

        Manages calculate file hashes operations and coordinates related state changes for the component.

        Args:
            path_or_row: Filesystem path to the target file or directory.
        """
        if isinstance(path_or_row, dict):
            path = path_or_row.get("path", "")
        else:
            path = str(path_or_row)
        if path and os.path.isfile(path):
            dlg = FileChecksumDialog(path, self)
            dlg.exec()

    def _open_with(self, path: str):
        """Prompt for an .exe and launch the path with it.

        Manages open with operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
        start_dir = str(Path(path).parent) if os.path.isfile(path) else ""
        exe, _ = QFileDialog.getOpenFileName(self, "Open with\u2026",
                                             start_dir,
                                             "Programs (*.exe)")
        if exe:
            # Safety: shell=False (default) prevents command injection via
            # user-selected exe or file paths. exe is validated by
            # QFileDialog.getOpenFileName returning a user-chosen .exe.
            subprocess.Popen([exe, path])

    def closeEvent(self, ev):
        """Handle the window or widget close event.

        Performs graceful shutdown, releases active workers and system hooks, persists window geometry, and accepts the close event.

        Args:
            ev: The Qt event object.
        """
        # Stop extract/compress workers
        for attr in ('_extract_worker', '_compress_worker'):
            worker = getattr(self, attr, None)
            if worker is not None and worker.isRunning():
                worker.terminate()
                worker.wait(2000)
        # Close duplicate finder if open
        dup = getattr(self, '_dup_finder', None)
        if dup is not None:
            dup.close()
        try:
            eng = getattr(self, "engine", None)
            if eng is not None and hasattr(eng, "shutdown"):
                eng.shutdown()
        except RuntimeError:
            log.debug("engine shutdown failed", exc_info=True)
        try:
            self._folder_sizes.stop()
        except (RuntimeError, OSError):
            log.debug("folder_sizes stop failed", exc_info=True)
        try:
            if hasattr(self, 'preview') and hasattr(self.preview, '_text_thread'):
                t = self.preview._text_thread
                if t and t.isRunning():
                    t.quit()
                    t.wait(2000)
        except RuntimeError:
            log.debug("text thread cleanup failed", exc_info=True)
        try:
            if hasattr(self, '_transfer_queue'):
                self._transfer_queue.stop()
        except RuntimeError:
            log.debug("transfer queue stop failed", exc_info=True)
        super().closeEvent(ev)

    # ────────────────────────── sidebar drives ────────────────────────────
    def _load_drives(self):
        """Load drive roots via FFI/CLI and refresh the folder tree.

        Manages load drives operations and coordinates related state changes for the component.
        """
        from PySide6.QtCore import QRunnable, QThreadPool

        engine = getattr(self, "engine", None)

        def _finish(count: int) -> None:
            """Finish.

            Manages finish operations and coordinates related state changes for the component.

            Args:
                count (int): The count parameter.
            """
            if self.folder_tree is not None:
                self.folder_tree.refresh()
            self._log(f"Drives: {count} found")

        marshal = _get_marshal()

        if engine is not None and getattr(engine, "ffi", None) is not None:
            ffi = engine.ffi
            job_done = {"n": 0}

            class _DriveJob(QRunnable):
                """Drivejob.

                Manages DriveJob operations and coordinates related state changes for the component.
                """
                def run(self_inner):
                    """Count FFI drives and marshal the result back to the UI thread.

                    Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.

                    Args:
                        self_inner: The self inner parameter.
                    """
                    try:
                        job_done["n"] = len(ffi.get_drives())
                    except (RuntimeError, OSError) as exc:
                        log.warning("get_drives failed: %s", exc)
                        job_done["n"] = 0
                    n = job_done["n"]
                    try:
                        if marshal is not None:
                            marshal.invoke.emit(
                                lambda code=0, rows=[n]: _finish(rows[0]), 0, [n]
                            )
                        else:
                            QTimer.singleShot(0, lambda count=n: _finish(count))
                    except Exception:
                        QTimer.singleShot(0, lambda count=n: _finish(count))

            QThreadPool.globalInstance().start(_DriveJob())
            return

        import json as _json
        from nexus_core import _guarded

        proc = QProcess()

        def done():
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.
            """
            raw = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
            try:
                drives = _json.loads(raw)
            except _json.JSONDecodeError:
                return
            _finish(len(drives))

        proc.finished.connect(_guarded(lambda *_: done()))
        self._drive_proc = proc
        proc.start(self.engine.cli, ["drives", "--json"])
