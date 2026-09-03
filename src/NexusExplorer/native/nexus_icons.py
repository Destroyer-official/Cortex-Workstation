"""Fluent Design icon library for NexusExplorer.

All icons are defined as SVG path data in a 20x20 viewport with 1.5px stroke,
matching Windows 11's Fluent UI icon style. Rendered via QPainter onto QPixmap
at any requested size — no external assets required.
"""
from __future__ import annotations

__all__ = [
    "icon",
    "action_icon",
    "sidebar_icon",
    "folder_icon",
    "icon_for_ext",
]

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QLinearGradient,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray
from collections import OrderedDict

# ── colour palette ───────────────────────────────────────────────────────
_CLR_DEFAULT = "#AAAAAA"
_CLR_ACCENT  = "#90CAF9"
_CLR_WHITE   = "#E0E0E0"
_CLR_RED     = "#EF5350"
_CLR_GREEN   = "#66BB6A"
_CLR_ORANGE  = "#FFA726"
_CLR_CYAN    = "#4DD0E1"

# ── SVG path data (20×20 viewport, 1.5 px stroke, round cap/join) ──────
# Each entry: (path_d, viewBox)  viewBox is always (0,0,20,20) for Fluent.

_PATHS: dict[str, str] = {
    # ── navigation ──────────────────────────────────────────────────────
    "back": (
        "M13 4 L7 10 L13 16"
    ),
    "forward": (
        "M7 4 L13 10 L7 16"
    ),
    "up": (
        "M4 13 L10 7 L16 13"
    ),
    "down": (
        "M4 7 L10 13 L16 7"
    ),
    "refresh": (
        "M16 10 A6 6 0 1 1 10 4"
        "M10 4 L14 4 L14 1 L17 4 L14 7 L14 4"
    ),
    "home": (
        "M3 10.5 L10 4 L17 10.5"
        "M5 9.5 V16 H8.5 V12 H11.5 V16 H15 V9.5"
    ),

    # ── clipboard / file ops ────────────────────────────────────────────
    "cut": (
        "M6.5 5 A1.5 1.5 0 1 0 6.5 8 A1.5 1.5 0 1 0 6.5 5"
        "M13.5 5 A1.5 1.5 0 1 0 13.5 8 A1.5 1.5 0 1 0 13.5 5"
        "M7.5 8 L12 14.5"
        "M12.5 8 L8 14.5"
    ),
    "copy": (
        "M8 3 H5 A1.5 1.5 0 0 0 3.5 4.5 V14.5 A1.5 1.5 0 0 0 5 16 H13 A1.5 1.5 0 0 0 14.5 14.5 V12"
        "M12 3 H15 A1.5 1.5 0 0 1 16.5 4.5 V14.5 A1.5 1.5 0 0 1 15 16 H14"
    ),
    "paste": (
        "M12 3 H7 A1 1 0 0 0 6 4 V5 H5 A1.5 1.5 0 0 0 3.5 6.5 V15.5 A1.5 1.5 0 0 0 5 17 H13 A1.5 1.5 0 0 0 14.5 15.5 V6.5 A1.5 1.5 0 0 0 13 5 H12 V4 A1 1 0 0 0 11 3"
        "M8 9 H12 M8 12 H11"
    ),
    "rename": (
        "M14.5 3.5 L16.5 5.5"
        "M14 4 L5 13 V15 H7 L16 6 Z"
    ),
    "delete": (
        "M5 6 H15"
        "M6 6 V4.5 A1.5 1.5 0 0 1 7.5 3 H12.5 A1.5 1.5 0 0 1 14 4.5 V6"
        "M7 6 V16 A1 1 0 0 0 8 17 H12 A1 1 0 0 0 13 16 V6"
        "M9 9 V14 M11 9 V14"
    ),
    "new_folder": (
        "M3 5.5 V15 A1.5 1.5 0 0 0 4.5 16.5 H15.5 A1.5 1.5 0 0 0 17 15 V7 A1.5 1.5 0 0 0 15.5 5.5 H9 L7.5 3.5 H4.5 A1.5 1.5 0 0 0 3 5"
        "M10 10 V14 M8 12 H12"
    ),
    "new_file": (
        "M13 3 H6 A1.5 1.5 0 0 0 4.5 4.5 V15.5 A1.5 1.5 0 0 0 6 17 H14 A1.5 1.5 0 0 0 15.5 15.5 V6.5 L13 3"
        "M10 11 V7 M8 9 H12"
    ),
    "plus": "M10 4 V16 M4 10 H16",
    "add": "M10 4 V16 M4 10 H16",

    # ── view / layout ───────────────────────────────────────────────────
    "view_detail": (
        "M3 5 H17 M3 10 H17 M3 15 H17"
    ),
    "view_icon": (
        "M3 3 H8.5 V8.5 H3 Z"
        "M11.5 3 H17 V8.5 H11.5 Z"
        "M3 11.5 H8.5 V17 H3 Z"
        "M11.5 11.5 H17 V17 H11.5 Z"
    ),
    "sidebar": (
        "M3 4 H17 V16 H3 Z"
        "M8 4 V16"
    ),
    "dual_pane": (
        "M3 4 H17 V16 H3 Z M10 4 V16"
    ),
    "preview": (
        "M3 4 H17 V16 H3 Z"
        "M12 4 V16"
    ),
    "sort": (
        "M5 5 H15 M7 10 H13 M9 15 H11"
    ),
    "filter": (
        "M3 4 H17 L12 10.5 V16 L8 14 V10.5 Z"
    ),

    # ── misc toolbar ────────────────────────────────────────────────────
    "search": (
        "M9 3 A6 6 0 1 0 9 15 A6 6 0 1 0 9 3"
        "M13.5 13.5 L17 17"
    ),
    "transfer": (
        "M10 3 V17 M6 7 L10 3 L14 7"
        "M6 13 L10 17 L14 13"
    ),
    "quicklook": (
        "M10 4 A8 5 0 1 0 10 14 A8 5 0 1 0 10 4"
        "M10 7 A2.5 2.5 0 1 0 10 12 A2.5 2.5 0 1 0 10 7"
    ),
    "check": (
        "M4 10 L8 14 L16 6"
    ),
    "info": (
        "M10 3 A7 7 0 1 0 10 17 A7 7 0 1 0 10 3"
        "M10 9 V13 M10 6 V7"
    ),
    "warning": (
        "M10 3 L18 17 H2 Z"
        "M10 10 V13 M10 15 V15.5"
    ),
    "error": (
        "M10 3 A7 7 0 1 0 10 17 A7 7 0 1 0 10 3"
        "M7 7 L13 13 M13 7 L7 13"
    ),
    "more": (
        "M4 10 A1 1 0 1 0 4 10.01"
        "M10 10 A1 1 0 1 0 10 10.01"
        "M16 10 A1 1 0 1 0 16 10.01"
    ),
    "close": (
        "M5 5 L15 15 M15 5 L5 15"
    ),
    "expand_right": (
        "M8 5 L13 10 L8 15"
    ),
    "expand_down": (
        "M5 8 L10 13 L15 8"
    ),
    "pin": (
        "M12 2 L15 5 L12.5 7.5 L13 13 L10 13 L10 16 L9 16 L9 13 L6 13 L6.5 7.5 L4 5 L7 2 Z"
    ),
    "star": (
        "M10 2 L12.4 7.5 L18.5 8 L13.8 12 L15.3 18 L10 14.8 L4.7 18 L6.2 12 L1.5 8 L7.6 7.5 Z"
    ),
    "star_outline": (
        "M10 2 L12.4 7.5 L18.5 8 L13.8 12 L15.3 18 L10 14.8 L4.7 18 L6.2 12 L1.5 8 L7.6 7.5 Z"
    ),

    # ── sidebar / quick access ──────────────────────────────────────────
    "desktop": (
        "M3 4 H17 V12 H3 Z M8 14 H12 M10 12 V14"
    ),
    "downloads": (
        "M10 3 V13 M6 9 L10 13 L14 9"
        "M3 15 H17"
    ),
    "documents": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M7 10 H13 M7 13 H11"
    ),
    "pictures": (
        "M3 4.5 A1.5 1.5 0 0 1 4.5 3 H15.5 A1.5 1.5 0 0 1 17 4.5 V15.5 A1.5 1.5 0 0 1 15.5 17 H4.5 A1.5 1.5 0 0 1 3 15.5 Z"
        "M7 11 L9 8 L11 10 L13 7 L17 12"
        "M7 11 A1 1 0 1 1 7.01 11"
    ),
    "music": (
        "M8 3 V14 A3 3 0 1 1 5 11 V6 H14 V12 A3 3 0 1 1 11 9 V3"
    ),
    "videos": (
        "M3 5 A1.5 1.5 0 0 1 4.5 3.5 H15.5 A1.5 1.5 0 0 1 17 5 V15 A1.5 1.5 0 0 1 15.5 16.5 H4.5 A1.5 1.5 0 0 1 3 15 Z"
        "M8 7.5 V12.5 L13 10 Z"
    ),
    "drive": (
        "M3 7 H17 V14 A1.5 1.5 0 0 1 15.5 15.5 H4.5 A1.5 1.5 0 0 1 3 14 Z"
        "M3 7 L5 4 H15 L17 7"
        "M8 11 H12 A0.5 0.5 0 0 1 12 12 H8 A0.5 0.5 0 0 1 8 11"
    ),
    "network": (
        "M3 4 H8 V9 H3 Z M12 4 H17 V9 H12 Z"
        "M3 13 H8 V18 H3 Z M12 13 H17 V18 H12 Z"
        "M8 6.5 H12 M5.5 9 V13 M14.5 9 V13 M5.5 13 H14.5"
    ),
    "trash": (
        "M4 5 H16"
        "M6 5 V3.5 A1.5 1.5 0 0 1 7.5 2 H12.5 A1.5 1.5 0 0 1 14 3.5 V5"
        "M7 7 V16 A1 1 0 0 0 8 17 H12 A1 1 0 0 0 13 16 V7"
    ),

    # ── file type badges ────────────────────────────────────────────────
    "file_pdf": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M7 10 H13 M7 13 H10"
    ),
    "file_image": (
        "M3 4.5 A1.5 1.5 0 0 1 4.5 3 H15.5 A1.5 1.5 0 0 1 17 4.5 V15.5 A1.5 1.5 0 0 1 15.5 17 H4.5 A1.5 1.5 0 0 1 3 15.5 Z"
        "M7 11 L9 8 L11 10 L13 7 L17 12"
    ),
    "file_code": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M8 10 L6 12 L8 14 M12 10 L14 12 L12 14"
    ),
    "file_zip": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M9.5 10 H10.5 V11 H11.5 V12 H10.5 V13 H11.5 V14 H10.5 V15 H9.5 V14 H8.5 V13 H9.5 V12 H8.5 V11 H9.5 Z"
    ),
    "file_exe": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M8 10 L12 12.5 L8 15 Z"
    ),
    "file_text": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M7 10 H13 M7 12.5 H13 M7 15 H10"
    ),
    "file_audio": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M8 14 A2 2 0 1 0 8 10 A2 2 0 1 0 8 14 M10 10 V7.5"
    ),
    "file_video": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M8 10 V14 L12 12 Z"
    ),
    "folder": (
        "M3 5.5 V15 A1.5 1.5 0 0 0 4.5 16.5 H15.5 A1.5 1.5 0 0 0 17 15 V7 A1.5 1.5 0 0 0 15.5 5.5 H9 L7.5 3.5 H4.5 A1.5 1.5 0 0 0 3 5"
    ),

    # ── document types ───────────────────────────────────────────────────
    "file_doc": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M7 10 H13 M7 12.5 H13 M7 15 H11"
    ),
    "file_spread": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M7 10 H13 M7 12.5 H13 M7 15 H13"
        "M10 10 V15"
    ),
    "file_presentation": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M7 10 H13 V15 H7 Z"
    ),
    "file_note": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M7 10 H10 M7 13 H9"
    ),
    "file_email": (
        "M3 5.5 A1.5 1.5 0 0 1 4.5 4 H15.5 A1.5 1.5 0 0 1 17 5.5 V14.5 A1.5 1.5 0 0 1 15.5 16 H4.5 A1.5 1.5 0 0 1 3 14.5 Z"
        "M3 5.5 L10 10.5 L17 5.5"
    ),

    # ── development ──────────────────────────────────────────────────────
    "file_config": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M8 11 A1.5 1.5 0 1 0 8 11.01 M10.5 10 V12 H12 V10 Z"
    ),
    "file_script": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M10 10 L8 13 L10 16"
    ),
    "file_data": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M8 10 A2 1.5 0 1 0 8 13 A2 1.5 0 1 0 8 10"
        "M8 10 V9 M8 13 V14 M6 11.5 H10"
    ),
    "file_web": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M10 10 A3 3 0 1 1 10 16 A3 3 0 1 1 10 10"
        "M7 13 H13 M10 10 V16"
    ),
    "file_markdown": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M7 10 L9 14 L11 10 L13 14"
    ),

    # ── media ────────────────────────────────────────────────────────────
    "file_font": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M10 10 L8 15 M10 10 L12 15 M8.5 13 H11.5"
    ),
    "file_3d": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M8 10 L12 10 L14 13 L10 13 Z M12 10 L12 14 L14 13"
    ),
    "file_vector": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M8 14 Q10 9 12 14"
    ),
    "file_raw": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M8 11 A2 2 0 1 0 8 11.01 M12 11 A1 1 0 1 0 12 11.01"
    ),

    # ── system ───────────────────────────────────────────────────────────
    "file_disk": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M10 10 A2 2 0 1 0 10 14 A2 2 0 1 0 10 10"
    ),
    "file_log": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M7 10 H9 M7 12.5 H11 M7 15 H8"
    ),
    "file_key": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M9 10 A1.5 1.5 0 1 0 9 13 A1.5 1.5 0 1 0 9 10"
        "M10.5 12 L13 12 M12 11 L12 13"
    ),
    "file_link": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M8 12 L12 12 M10 10 L10 14"
    ),
    "file_backup": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M10 10 A3 3 0 1 1 13 13 M10 10 V10 M10 10 L12 10 M10 10 L10 12"
    ),
    "file_unknown": (
        "M5 3 H12 L16 7 V17 H5 A1.5 1.5 0 0 1 3.5 15.5 V4.5 A1.5 1.5 0 0 1 5 3"
        "M12 3 V7 H16"
        "M10 10 A1.5 1.5 0 0 1 10 13 M10 14.5 V14.51"
    ),
}

# extension → icon name mapping
_EXT_MAP: dict[str, str] = {
    # ── documents ────────────────────────────────────────────────────────
    ".pdf": "file_pdf",
    ".doc": "file_doc", ".docx": "file_doc", ".odt": "file_doc", ".rtf": "file_doc",
    ".wps": "file_doc", ".wpd": "file_doc", ".pages": "file_doc",
    ".xls": "file_spread", ".xlsx": "file_spread", ".ods": "file_spread",
    ".numbers": "file_spread", ".qpw": "file_spread", ".123": "file_spread",
    ".ppt": "file_presentation", ".pptx": "file_presentation",
    ".odp": "file_presentation", ".key": "file_presentation", ".pps": "file_presentation",
    ".note": "file_note", ".journal": "file_note", ".one": "file_note",
    ".eml": "file_email", ".msg": "file_email", ".mbox": "file_email",
    ".xps": "file_doc", ".oxps": "file_doc",

    # ── text / config ────────────────────────────────────────────────────
    ".txt": "file_text", ".text": "file_text", ".log": "file_log",
    ".csv": "file_text", ".tsv": "file_text", ".nfo": "file_text",
    ".readme": "file_text", ".license": "file_text", ".authors": "file_text",
    ".changelog": "file_text", ".credits": "file_text",
    ".ini": "file_config", ".cfg": "file_config", ".conf": "file_config",
    ".env": "file_config", ".properties": "file_config",
    ".editorconfig": "file_config", ".gitignore": "file_config",
    ".gitattributes": "file_config", ".gitmodules": "file_config",
    ".dockerignore": "file_config", ".dockerfile": "file_config",
    ".gitlab-ci.yml": "file_config", ".travis.yml": "file_config",
    ".appveyor.yml": "file_config", ".circleci": "file_config",

    # ── code ─────────────────────────────────────────────────────────────
    ".py": "file_code", ".pyw": "file_code", ".pyi": "file_code",
    ".js": "file_code", ".jsx": "file_code", ".mjs": "file_code", ".cjs": "file_code",
    ".ts": "file_code", ".tsx": "file_code",
    ".rs": "file_code", ".go": "file_code", ".java": "file_code",
    ".kt": "file_code", ".kts": "file_code", ".scala": "file_code",
    ".c": "file_code", ".cpp": "file_code", ".cc": "file_code",
    ".cxx": "file_code", ".h": "file_code", ".hpp": "file_code", ".hxx": "file_code",
    ".cs": "file_code", ".vb": "file_code", ".fs": "file_code", ".fsx": "file_code",
    ".rb": "file_code", ".php": "file_code",
    ".pl": "file_code", ".pm": "file_code", ".r": "file_code", ".R": "file_code",
    ".swift": "file_code", ".m": "file_code", ".mm": "file_code",
    ".zig": "file_code", ".nim": "file_code", ".cr": "file_code", ".jl": "file_code",
    ".lua": "file_code", ".ex": "file_code", ".exs": "file_code",
    ".erl": "file_code", ".hs": "file_code", ".ml": "file_code",
    ".elm": "file_code", ".clj": "file_code", ".lisp": "file_code", ".el": "file_code",
    ".dart": "file_code", ".coffee": "file_code", ".ts": "file_code",
    ".sol": "file_code", ".vy": "file_code",

    # ── web ──────────────────────────────────────────────────────────────
    ".html": "file_web", ".htm": "file_web", ".xhtml": "file_web",
    ".css": "file_code", ".scss": "file_code", ".sass": "file_code", ".less": "file_code",
    ".svg": "file_vector", ".vue": "file_code", ".svelte": "file_code",
    ".jsx": "file_code", ".tsx": "file_code",

    # ── data / structured ────────────────────────────────────────────────
    ".json": "file_data", ".jsonl": "file_data", ".json5": "file_data",
    ".geojson": "file_data", ".topojson": "file_data",
    ".yaml": "file_data", ".yml": "file_data",
    ".toml": "file_data", ".xml": "file_data",
    ".plist": "file_data", ".graphql": "file_data", ".gql": "file_data",
    ".sql": "file_data", ".db": "file_data", ".sqlite": "file_data",
    ".sqlite3": "file_data", ".mdb": "file_data", ".accdb": "file_data",
    ".parquet": "file_data", ".arrow": "file_data",
    ".hdf5": "file_data", ".h5": "file_data", ".fits": "file_data",

    # ── markdown / docs ──────────────────────────────────────────────────
    ".md": "file_markdown", ".mdx": "file_markdown",
    ".rst": "file_doc", ".asciidoc": "file_doc", ".adoc": "file_doc",
    ".wiki": "file_doc", ".textile": "file_doc",
    ".tex": "file_doc", ".latex": "file_doc", ".sty": "file_doc", ".cls": "file_doc",
    ".bib": "file_doc",

    # ── scripts ──────────────────────────────────────────────────────────
    ".sh": "file_script", ".bash": "file_script", ".zsh": "file_script",
    ".fish": "file_script", ".awk": "file_script", ".sed": "file_script",
    ".ps1": "file_script", ".psm1": "file_script", ".psd1": "file_script",
    ".bat": "file_script", ".cmd": "file_script", ".btm": "file_script",
    ".vbs": "file_script", ".vba": "file_script", ".jsl": "file_script",

    # ── images ───────────────────────────────────────────────────────────
    ".png": "file_image", ".jpg": "file_image", ".jpeg": "file_image",
    ".gif": "file_image", ".bmp": "file_image", ".webp": "file_image",
    ".ico": "file_image", ".tiff": "file_image", ".tif": "file_image",
    ".heic": "file_image", ".heif": "file_image", ".avif": "file_image",
    ".jxl": "file_image", ".pcx": "file_image", ".tga": "file_image",
    ".dds": "file_image", ".exr": "file_image", ".hdr": "file_image",
    ".psd": "file_image", ".xcf": "file_image", ".sketch": "file_image",
    ".fig": "file_image", ".pdn": "file_image",
    ".raw": "file_raw", ".cr2": "file_raw", ".cr3": "file_raw",
    ".nef": "file_raw", ".arw": "file_raw", ".dng": "file_raw",
    ".orf": "file_raw", ".rw2": "file_raw", ".pef": "file_raw",
    ".srw": "file_raw", ".raf": "file_raw", ".3fr": "file_raw",
    ".mef": "file_raw", ".mrw": "file_raw", ".nrw": "file_raw",
    ".rwl": "file_raw", ".sr2": "file_raw",
    ".ai": "file_vector", ".eps": "file_vector", ".ps": "file_vector",
    ".afdesign": "file_vector", ".afphoto": "file_image",

    # ── video ────────────────────────────────────────────────────────────
    ".mp4": "file_video", ".m4v": "file_video", ".avi": "file_video",
    ".mkv": "file_video", ".mov": "file_video", ".wmv": "file_video",
    ".flv": "file_video", ".webm": "file_video", ".mpg": "file_video",
    ".mpeg": "file_video", ".3gp": "file_video", ".ogv": "file_video",
    ".m2ts": "file_video", ".vob": "file_video",
    ".asf": "file_video", ".rm": "file_video", ".rmvb": "file_video",
    ".f4v": "file_video", ".divx": "file_video", ".xvid": "file_video",

    # ── audio ────────────────────────────────────────────────────────────
    ".mp3": "file_audio", ".wav": "file_audio", ".flac": "file_audio",
    ".ogg": "file_audio", ".aac": "file_audio", ".m4a": "file_audio",
    ".wma": "file_audio", ".opus": "file_audio", ".aiff": "file_audio",
    ".ape": "file_audio", ".alac": "file_audio",
    ".mid": "file_audio", ".midi": "file_audio", ".kar": "file_audio",
    ".amr": "file_audio", ".au": "file_audio", ".ra": "file_audio",

    # ── fonts ────────────────────────────────────────────────────────────
    ".ttf": "file_font", ".otf": "file_font", ".woff": "file_font",
    ".woff2": "file_font", ".eot": "file_font", ".fon": "file_font",
    ".fnt": "file_font", ".bdf": "file_font", ".pcf": "file_font",

    # ── 3D / CAD ─────────────────────────────────────────────────────────
    ".stl": "file_3d", ".obj": "file_3d", ".fbx": "file_3d",
    ".blend": "file_3d", ".3ds": "file_3d", ".dae": "file_3d",
    ".dwg": "file_3d", ".dxf": "file_3d",
    ".step": "file_3d", ".stp": "file_3d", ".iges": "file_3d", ".igs": "file_3d",
    ".3mf": "file_3d", ".off": "file_3d", ".ply": "file_3d",

    # ── archives / compressed ────────────────────────────────────────────
    ".zip": "file_zip", ".rar": "file_zip", ".7z": "file_zip",
    ".tar": "file_zip", ".gz": "file_zip", ".bz2": "file_zip",
    ".xz": "file_zip", ".lz": "file_zip", ".lzma": "file_zip",
    ".zst": "file_zip", ".cab": "file_zip", ".lzh": "file_zip",
    ".sit": "file_zip", ".sitx": "file_zip", ".ace": "file_zip",
    ".arj": "file_zip", ".tgz": "file_zip", ".tbz2": "file_zip",
    ".txz": "file_zip", ".tlz": "file_zip",

    # ── disk images / backups ────────────────────────────────────────────
    ".iso": "file_disk", ".img": "file_disk", ".vmdk": "file_disk",
    ".vhd": "file_disk", ".vhdx": "file_disk", ".qcow2": "file_disk",
    ".toast": "file_disk", ".dmg": "file_disk", ".sparseimage": "file_disk",
    ".wim": "file_disk", ".esd": "file_disk", ".swm": "file_disk",

    # ── executables / system ─────────────────────────────────────────────
    ".exe": "file_exe", ".dll": "file_exe", ".sys": "file_exe",
    ".drv": "file_exe", ".so": "file_exe", ".dylib": "file_exe",
    ".bundle": "file_exe", ".com": "file_exe", ".pif": "file_exe",
    ".msc": "file_exe", ".scr": "file_exe", ".cpl": "file_exe",
    ".msi": "file_exe", ".msix": "file_exe", ".appx": "file_exe",
    ".deb": "file_exe", ".rpm": "file_exe", ".apk": "file_exe",
    ".ipa": "file_exe", ".app": "file_exe",

    # ── keys / certificates ──────────────────────────────────────────────
    ".pem": "file_key", ".key": "file_key", ".crt": "file_key",
    ".cer": "file_key", ".p12": "file_key", ".pfx": "file_key",
    ".jks": "file_key", ".keystore": "file_key", ".gpg": "file_key",
    ".pgp": "file_key", ".pub": "file_key",

    # ── links / shortcuts ────────────────────────────────────────────────
    ".lnk": "file_link", ".url": "file_link", ".webloc": "file_link",
    ".desktop": "file_link", ".lnk": "file_link",

    # ── backups / temp ───────────────────────────────────────────────────
    ".bak": "file_backup", ".backup": "file_backup", ".orig": "file_backup",
    ".old": "file_backup", ".save": "file_backup",
    ".swp": "file_backup", ".swo": "file_backup", "~": "file_backup",
    ".tmp": "file_backup", ".temp": "file_backup",

    # ── subtitles ────────────────────────────────────────────────────────
    ".srt": "file_text", ".sub": "file_text", ".ssa": "file_text",
    ".ass": "file_text", ".vtt": "file_text", ".idx": "file_text",

    # ── misc ─────────────────────────────────────────────────────────────
    ".torrent": "file_data",
    ".ics": "file_note", ".vcs": "file_note",
    ".kml": "file_data", ".kmz": "file_data",
}

# ── rendering engine ────────────────────────────────────────────────────

_CANDIDATE_ICON_DIRS = (
    Path(__file__).resolve().parents[2] / "cortex_unified" / "resources" / "icons",
    Path(__file__).resolve().parents[3] / "src" / "cortex_unified" / "resources" / "icons",
    Path(__file__).resolve().parents[1] / "resources" / "icons",
    Path(__file__).resolve().parents[2] / "resources" / "icons",
)
_MATERIAL_DIR = next((p for p in _CANDIDATE_ICON_DIRS if p.is_dir()), _CANDIDATE_ICON_DIRS[0])


class _LRUCache:
    """Ordered-dict LRU cache mapping string keys to rendered QIcons,
    evicting the least recently used entry beyond maxsize."""
    def __init__(self, maxsize: int = 1000):
        """Create the OrderedDict store with the given capacity."""
        self._data: OrderedDict[str, QIcon] = OrderedDict()
        self._maxsize = maxsize
        """Create the OrderedDict store with the given capacity."""

    def get(self, key: str) -> QIcon | None:
        """Return the cached icon (refreshing LRU position) or None."""
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None
        """Return the cached icon (refreshing LRU position) or None."""

    def set(self, key: str, value: QIcon) -> None:
        """Insert/refresh an entry, evicting the oldest when the cache
        exceeds maxsize."""
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)
        """Insert/refresh an entry, evicting the oldest when the cache
        exceeds maxsize."""
    """Ordered-dict LRU cache mapping string keys to rendered QIcons,
    evicting the least recently used entry beyond maxsize."""

_SVG_CACHE = _LRUCache(1000)


_RENDERER_CACHE: dict[str, QSvgRenderer] = {}

def _render_svg(path_d: str, size: int, color: str,
                fill: str | None = None) -> QPixmap:
    """Render an inline SVG (20×20 viewBox, 1.5 px stroke, round joins)
    built from path_d into a transparent antialiased QPixmap of the
    requested size; renderers are cached per (path, colors) up to 200."""
    cache_key = f"{path_d}:{color}:{fill}"
    renderer = _RENDERER_CACHE.get(cache_key)
    if renderer is None:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 20 20" width="{size}" height="{size}">'
            f'<path d="{path_d}" '
            f'stroke="{color}" stroke-width="1.5" '
            f'fill="{"none" if fill is None else fill}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            f'</svg>'
        )
        renderer = QSvgRenderer(QByteArray(svg.encode()))
        if len(_RENDERER_CACHE) < 200:
            _RENDERER_CACHE[cache_key] = renderer
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer.render(painter)
    painter.end()
    return pixmap
    """Render an inline SVG (20×20 viewBox, 1.5 px stroke, round joins)
    built from path_d into a transparent antialiased QPixmap of the
    requested size; renderers are cached per (path, colors) up to 200."""


def _render_svg_file(svg_content: str, size: int, default_color: str = "#FFB900") -> QPixmap:
    """Render SVG content string to a crisp high-DPI QPixmap with currentColor substitution."""
    if "currentColor" in svg_content:
        svg_content = svg_content.replace("currentColor", default_color)
    renderer = QSvgRenderer(QByteArray(svg_content.encode("utf-8")))
    if not renderer.isValid():
        return QPixmap()
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer.render(painter)
    painter.end()
    return pixmap


_ICON_CACHE: dict[tuple, QIcon] = {}
_ICON_CACHE_MAX = 512


def icon(name: str, size: int = 20, color: str = _CLR_DEFAULT,
         fill: str | None = None) -> QIcon:
    """Return a Fluent icon by name at the requested size/color/fill,
    served from a bounded icon cache; unknown names fall back to
    file_unknown (ValueError when even that is missing)."""
    cache_key = (name, size, color, fill)
    cached = _ICON_CACHE.get(cache_key)
    if cached is not None:
        return cached
    path_d = _PATHS.get(name)
    if path_d is None:
        path_d = _PATHS.get("file_unknown", "")
        if not path_d:
            raise ValueError(f"Unknown icon: {name!r}")
    ico = QIcon(_render_svg(path_d, size, color, fill))
    if len(_ICON_CACHE) >= _ICON_CACHE_MAX:
        _ICON_CACHE.pop(next(iter(_ICON_CACHE)))
    _ICON_CACHE[cache_key] = ico
    return ico
    """Return a Fluent icon by name at the requested size/color/fill,
    served from a bounded icon cache; unknown names fall back to
    file_unknown (ValueError when even that is missing)."""


def _material_icon(material_name: str, size: int = 32, default_color: str = "#FFB900") -> QIcon:
    """Load a Material Design icon from disk by name (e.g. 'python', 'folder-desktop')."""
    cache_key = f"{material_name}:{size}:{default_color}"
    cached = _SVG_CACHE.get(cache_key)
    if cached is not None:
        return cached
    svg_file = _MATERIAL_DIR / f"{material_name}.svg"
    if not svg_file.exists():
        return QIcon()
    try:
        content = svg_file.read_text(encoding="utf-8")
        pixmap = _render_svg_file(content, size, default_color=default_color)
        if pixmap.isNull():
            return QIcon()
        ico = QIcon(pixmap)
        _SVG_CACHE.set(cache_key, ico)
        return ico
    except Exception:
        return QIcon()


# ── extension → Material icon name mapping ─────────────────────────────
# Maps file extensions to Material Icon Theme SVG filenames.
_MATERIAL_EXT_MAP: dict[str, str] = {
    # ── languages ────────────────────────────────────────────────────────
    ".py": "python", ".pyw": "python", ".pyi": "python",
    ".js": "javascript", ".jsx": "react", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "react",
    ".rs": "rust", ".go": "go", ".java": "java",
    ".c": "c", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
    ".h": "c", ".hpp": "cpp", ".hxx": "cpp",
    ".cs": "csharp", ".vb": "csharp",
    ".php": "php", ".rb": "ruby",
    ".swift": "swift", ".kt": "kotlin", ".kts": "kotlin",
    ".scala": "scala", ".dart": "dart",
    ".lua": "lua", ".r": "r", ".R": "r",
    ".pl": "perl", ".pm": "perl",
    ".hs": "haskell", ".lhs": "haskell",
    ".ex": "elixir", ".exs": "elixir",
    ".clj": "clojure", ".cljs": "clojure",
    ".groovy": "groovy", ".gradle": "gradle",
    ".zig": "zig", ".nim": "nim",
    ".jl": "julia",
    ".erl": "erlang",
    ".ml": "ocaml", ".mli": "ocaml",
    ".fs": "csharp", ".fsx": "csharp",
    ".coffee": "coffeescript",
    ".elm": "elm",
    ".lisp": "lisp", ".el": "lisp",
    ".scm": "scheme",
    ".fortran": "fortran", ".f90": "fortran", ".f95": "fortran",
    ".cob": "c", ".cbl": "c",
    ".asm": "assembly", ".s": "assembly",
    ".ada": "ada",
    ".abap": "abap",
    ".dart": "dart",
    ".sol": "javascript",  # Solidity
    ".vy": "python",  # Vyper

    # ── web ──────────────────────────────────────────────────────────────
    ".html": "html", ".htm": "html", ".xhtml": "html",
    ".css": "css", ".scss": "scss", ".sass": "sass", ".less": "less",
    ".vue": "vue", ".svelte": "svelte",
    ".astro": "astro",

    # ── config / data ────────────────────────────────────────────────────
    ".json": "json", ".jsonl": "json", ".json5": "json",
    ".geojson": "json", ".topojson": "json",
    ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".xml": "xml",
    ".plist": "xml",
    ".graphql": "graphql", ".gql": "graphql",

    # ── markup / docs ────────────────────────────────────────────────────
    ".md": "markdown", ".mdx": "markdown",
    ".rst": "readme", ".asciidoc": "readme", ".adoc": "readme",
    ".tex": "readme", ".latex": "readme",
    ".bib": "readme",

    # ── scripts ──────────────────────────────────────────────────────────
    ".sh": "terminal", ".bash": "terminal", ".zsh": "terminal", ".fish": "terminal",
    ".ps1": "powershell", ".psm1": "powershell", ".psd1": "powershell",
    ".bat": "terminal", ".cmd": "terminal", ".btm": "terminal",
    ".awk": "terminal", ".sed": "terminal",

    # ── images ───────────────────────────────────────────────────────────
    ".png": "image", ".jpg": "image", ".jpeg": "image",
    ".gif": "image", ".bmp": "image", ".webp": "image",
    ".ico": "image", ".tiff": "image", ".tif": "image",
    ".heic": "image", ".heif": "image", ".avif": "image",
    ".jxl": "image", ".pcx": "image", ".tga": "image",
    ".dds": "image", ".exr": "image", ".hdr": "image",
    ".psd": "photoshop", ".xcf": "image",
    ".ai": "illustrator", ".eps": "illustrator",
    ".svg": "svg", ".sketch": "figma", ".fig": "figma",
    ".afdesign": "figma", ".afphoto": "figma",
    ".raw": "image", ".cr2": "image", ".cr3": "image",
    ".nef": "image", ".arw": "image", ".dng": "image",
    ".orf": "image", ".rw2": "image", ".pef": "image",
    ".srw": "image", ".raf": "image",

    # ── video ────────────────────────────────────────────────────────────
    ".mp4": "video", ".m4v": "video", ".avi": "video",
    ".mkv": "video", ".mov": "video", ".wmv": "video",
    ".flv": "video", ".webm": "video", ".mpg": "video",
    ".mpeg": "video", ".3gp": "video", ".ogv": "video",
    ".m2ts": "video", ".vob": "video",

    # ── audio ────────────────────────────────────────────────────────────
    ".mp3": "audio", ".wav": "audio", ".flac": "audio",
    ".ogg": "audio", ".aac": "audio", ".m4a": "audio",
    ".wma": "audio", ".opus": "audio", ".aiff": "audio",
    ".mid": "audio", ".midi": "audio",

    # ── documents ────────────────────────────────────────────────────────
    ".pdf": "pdf",
    ".doc": "word", ".docx": "word", ".odt": "word", ".rtf": "word",
    ".xls": "excel", ".xlsx": "excel", ".ods": "excel", ".csv": "excel",
    ".ppt": "powerpoint", ".pptx": "powerpoint", ".odp": "powerpoint",
    ".key": "powerpoint",

    # ── archives / compressed ────────────────────────────────────────────
    ".zip": "zip", ".rar": "zip", ".7z": "zip",
    ".tar": "zip", ".gz": "zip", ".bz2": "zip",
    ".xz": "zip", ".zst": "zip",
    ".cab": "zip", ".tgz": "zip",

    # ── databases ────────────────────────────────────────────────────────
    ".sql": "sql", ".db": "database", ".sqlite": "sqlite",
    ".sqlite3": "sqlite", ".mdb": "database",

    # ── system / devops ──────────────────────────────────────────────────
    ".exe": "binary", ".dll": "binary", ".sys": "binary",
    ".msi": "binary", ".msix": "binary",
    ".so": "binary", ".dylib": "binary",
    ".log": "log", ".out": "log",
    ".lock": "lock",
    ".pem": "certificate", ".key": "certificate",
    ".crt": "certificate", ".cer": "certificate",
    ".p12": "certificate", ".pfx": "certificate",
    ".jks": "certificate", ".gpg": "key", ".pub": "key",
    ".lnk": "terminal", ".url": "terminal",

    # ── devtools ─────────────────────────────────────────────────────────
    ".dockerfile": "docker", ".dockerignore": "docker",
    ".gitignore": "gitignore", ".gitattributes": "git",
    ".editorconfig": "file",
    ".eslintrc": "eslint", ".eslintrc.js": "eslint",
    ".prettierrc": "prettier", ".prettierrc.js": "prettier",
    "webpack.config.js": "webpack", "vite.config.js": "vite",
    "Makefile": "makefile", "CMakeLists.txt": "cmake",
    "Cargo.toml": "cargo", "Cargo.lock": "cargo",
    "package.json": "npm", "package-lock.json": "npm",
    "yarn.lock": "yarn", "pnpm-lock.yaml": "pnpm",
    "Gemfile": "gem", "Gemfile.lock": "gem",
    "build.gradle": "gradle", "pom.xml": "maven",
    "nuget.config": "nuget",

    # ── misc ─────────────────────────────────────────────────────────────
    ".torrent": "binary",
    ".ics": "readme", ".vcs": "readme",
    ".kml": "xml", ".kmz": "zip",
    ".tmp": "binary", ".temp": "binary",
    ".bak": "binary", ".backup": "binary",
    ".swp": "binary", ".orig": "binary",

    # ── additional languages ──────────────────────────────────────────────
    ".as": "actionscript", ".as3": "actionscript",
    ". applescript": "applescript", ".scpt": "applescript",
    ".au3": "autohotkey",
    ".ballerina": "ballerina", ".bal": "ballerina",
    ".bazel": "bazel", ".bzl": "bazel",
    ".bbx": "bbx",
    ".beancount": "beancount", ".bean": "beancount",
    ".bicep": "bicep",
    ".blade": "laravel", ".blade.php": "laravel",
    ".bruno": "bruno",
    ".c3": "c3",
    ".cabal": "cabal",
    ".capnp": "capnp",
    ".cds": "cds",
    ".chess": "chess",
    ".circom": "architecture",
    ".cljc": "clojure", ".clj": "clojure", ".cljs": "clojure",
    ".cob": "cobol", ".cbl": "cobol",
    ".coconut": "coconut", ".coconut.py": "coconut",
    ".coldfusion": "coldfusion", ".cfm": "coldfusion",
    ".cr": "crystal", ".cr": "crystal",
    ".cuda": "cuda", ".cu": "cuda", ".cuh": "cuda",
    ".cue": "cue",
    ".dart": "dart",
    ".denizenscript": "denizenscript",
    ".dhall": "dhall",
    ".dinophp": "dinophp",
    ".dpr": "delphi", ".dpk": "delphi", ".pas": "delphi",
    ".duc": "duc",
    ".dune": "dune",
    ".ejs": "ejs",
    ".elm": "elm",
    ".ember": "ember",
    ".erl": "erlang", ".hrl": "erlang",
    ".ex": "elixir", ".exs": "elixir",
    ".flow": "flow",
    ".forth": "forth", ".fth": "forth",
    ".foxpro": "foxpro", ".prg": "foxpro",
    ".fql": "graphql",
    ".fs": "fsharp", ".fsx": "fsharp", ".fsi": "fsharp",
    ".fxml": "xml",  # javafx -> closest available
    ".game": "gamemaker", ".yy": "gamemaker", ".gml": "gamemaker",
    ".gleam": "gleam",
    ".glsl": "shader", ".vert": "shader", ".frag": "shader", ".geom": "shader",
    ".gnuplot": "gnuplot", ".plt": "gnuplot",
    ".gql": "graphql",
    ".groovy": "groovy", ".gvy": "groovy",
    ".hack": "hack", ".hh": "hack", ".hhi": "hack",
    ".haml": "haml",
    ".handlebars": "handlebars", ".hbs": "handlebars",
    ".hcl": "hcl", ".tf": "terraform", ".tfvars": "terraform",
    ".helm": "helm",
    ".hex": "hex", ".ihx": "hex",
    ".hip": "hip",
    ".hjson": "hjson",
    ".hlsl": "shader", ".fx": "shader", ".fxh": "shader",
    ".hpp": "cpp", ".hxx": "cpp",
    ".huff": "huff",
    ".hurl": "hurl",
    ".hx": "haxe", ".hxsl": "haxe",
    ".idr": "idris", ".ipkg": "idris",
    ".imba": "imba",
    ".ionic": "ionic",
    ".isp": "verilog", ".v": "verilog", ".vh": "verilog",
    ".jai": "haxe",  # jai -> closest available
    ".jav": "java",
    ".jl": "julia",
    ".jsconfig": "javascript",
    ".jsr": "javascript",  # jsr -> javascript
    ".jux": "jupyter",
    ".kcl": "kcl",
    ".kivy": "python",  # kivy -> python
    ".kl": "kl",
    ".lalrpop": "rust",
    ".lean": "lean",
    ".less": "less",
    ".liquid": "liquid",
    ".lisp": "lisp", ".el": "lisp", ".lsp": "lisp",
    ".livescript": "livescript",
    ".lolcode": "lolcode", ".lol": "lolcode",
    ".lua": "lua",
    ".luau": "lua",  # luau -> lua
    ".m": "c",  # objectivec -> objective-c
    ".m2ts": "video",
    ".macaulay2": "macaulay2",
    ".makefile": "makefile",
    ".mako": "python",
    ".markdoc": "markdoc",
    ".marko": "html",  # markojs -> html
    ".mathematica": "mathematica", ".nb": "mathematica",
    ".mcr": "terminal",  # maxscript -> batch (closest)
    ".mdsvex": "svelte",  # mdsvex -> svelte
    ".mermaid": "mermaid", ".mmd": "mermaid",
    ".meson": "meson", ".meson.build": "meson",
    ".mid": "audio",  # midi -> audio
    ".mjml": "html",  # mjml -> html
    ".mojo": "python",  # mojo -> python
    ".moon": "lua",  # moonscript -> lua
    ".nc": "binary",  # gcode -> binary (closest)
    ".neon": "php",
    ".nginx": "yaml",  # nginx -> yaml (closest)
    ".nimble": "nim", ".nim.cfg": "nim",
    ".nix": "hcl",  # nix -> hcl
    ".nunjucks": "html",  # nunjucks -> html
    ".odin": "zig",  # odin -> zig (closest)
    ".onnx": "python",  # onnx -> python
    ".opa": "go",  # opa -> go (closest)
    ".opam": "ocaml",
    ".openapi": "yaml",  # openapi -> yaml
    ".opentofu": "terraform",  # opentofu -> terraform
    ".oz": "erlang",  # oz -> erlang (closest)
    ".p": "prolog",  # prolog
    ".pan": "hcl",  # pan -> hcl (closest)
    ".pas": "pascal", ".pp": "pascal",
    ".pawn": "c",  # pawn -> c (closest)
    ".pd": "audio",  # puredata -> audio
    ".pegjs": "javascript",  # pegjs -> javascript
    ".php": "php",
    ".php-cs-fixer": "php",
    ".phpstan": "php",
    ".phpunit": "php",
    ".pkl": "python",  # pkl -> python
    ".pl": "perl", ".pm": "perl",
    ".plsql": "sql",  # oracle/plsql -> sql
    ".po": "i18n", ".pot": "i18n",
    ".postcss": "css",
    ".puppet": "ruby",  # puppet -> ruby (closest)
    ".purs": "haskell",  # purescript -> haskell
    ".pyi": "python",
    ".pyt": "python",
    ".q": "binary",  # kdb -> binary
    ".qasm": "binary",  # qasm -> binary
    ".qsharp": "csharp",  # qsharp -> csharp
    ".quarto": "markdown",  # quarto -> markdown
    ".quasar": "vue",  # quasar -> vue
    ".r": "r",
    ".raml": "yaml",  # raml -> yaml
    ".razor": "html",  # razor -> html
    ".reason": "ocaml",  # reason -> ocaml (closest)
    ".rego": "go",  # rego -> go
    ".res": "ocaml",  # rescript -> ocaml (closest)
    ".resi": "ocaml",
    ".restql": "sql",  # restql -> sql
    ".riot": "html",  # riot -> html
    ".robot": "python",  # robot -> python (closest)
    ".rojo": "lua",  # rojo -> lua (Roblox)
    ".rql": "sql",  # rql -> sql
    ".rs": "rust",
    ".rune": "rust",  # rune -> rust
    ".s": "assembly", ".asm": "assembly",
    ".sas": "binary",  # sas -> binary
    ".sbt": "scala",  # sbt -> scala
    ".sc": "haskell",  # supercollider -> haskell (closest)
    ".scd": "haskell",
    ".scala": "scala",
    ".scons": "python",  # scons -> python
    ".scss": "scss",
    ".sh": "terminal",
    ".shader": "shader",
    ".sieve": "ruby",  # sieve -> ruby (closest)
    ".slim": "html",  # slim -> html
    ".slint": "rust",  # slint -> rust
    ".sml": "ocaml",  # sml -> ocaml (closest)
    ".solidity": "javascript",  # solidity -> javascript
    ".spwn": "lua",  # spwn -> lua (closest)
    ".stan": "r",  # stan -> r (closest)
    ".star": "hcl",
    ".sty": "tex",
    ".svelte": "svelte",
    ".svg": "svg",
    ".swift": "swift",
    ".swig": "c",  # swig -> c
    ".systemd": "yaml",  # systemd -> yaml (closest)
    ".tcl": "tcl",
    ".teal": "lua",  # teal -> lua
    ".templ": "html",  # templ -> html
    ".tex": "tex", ".latex": "tex",
    ".tf": "terraform",
    ".tla": "binary",  # tla -> binary
    ".toml": "toml",
    ".tremor": "rust",  # tremor -> rust
    ".tscn": "godot", ".tres": "godot",
    ".twig": "html",  # twig -> html
    ".typ": "markdown",  # typst -> markdown
    ".uiua": "binary",  # uiua -> binary
    ".umt": "uml",
    ".vala": "c",  # vala -> c
    ".vapi": "c",
    ".vfl": "swift",  # vfl -> swift (closest)
    ".vim": "vim",
    ".vlang": "go",  # vlang -> go
    ".vue": "vue",
    ".wasm": "binary",  # webassembly -> binary
    ".wat": "binary",
    ".wgsl": "shader",
    ".wxml": "html",  # wechat -> html
    ".wxss": "css",
    ".xaml": "xml",
    ".xht": "html", ".xhtml": "html",
    ".xml": "xml",
    ".xq": "xml",  # xquery -> xml
    ".xquery": "xml",
    ".xsd": "xml", ".xsl": "xml", ".xslt": "xml",
    ".yaml": "yaml", ".yml": "yaml",
    ".yang": "yaml",  # yang -> yaml
    ".zig": "zig",
    ".zil": "lisp",  # zil -> lisp (closest)

    # ── config / tooling ──────────────────────────────────────────────────
    ".appveyor.yml": "travis",
    ".azure-pipelines.yml": "yaml",
    ".babelrc": "javascript",
    ".babel.config.js": "javascript",
    ".bithoundrc": "yaml",
    ".bowerrc": "json",
    ".browserslistrc": "markdown",
    ".buildkite.yml": "yaml",
    ".circleci.yml": "yaml",
    ".codecov.yml": "yaml",
    ".commitlintrc": "json",
    ".commitlint.config.js": "json",
    ".craco.config.js": "javascript",
    ".deepsource.toml": "toml",
    ".dependabot.yml": "yaml",
    ".drone.yml": "yaml",
    ".editorconfig": "markdown",
    ".eslintignore": "markdown",
    ".eslintrc.json": "json",
    ".eslintrc.yml": "yaml",
    ".fastlane": "ruby",
    ".firebase.json": "json",
    ".firebaserc": "json",
    ".flowconfig": "markdown",
    ".github.yml": "yaml",
    ".github": "git",
    ".gitpod.yml": "yaml",
    ".gradle.kts": "gradle",
    ".grit.yaml": "yaml",
    ".hadolint.yaml": "yaml",
    ".huskyrc": "json",
    ".husky": "terminal",
    ".istanbul.yml": "yaml",
    ".jest.config.js": "javascript", ".jest.config.ts": "typescript",
    ".jsdoc.json": "json",
    ".karma.conf.js": "javascript",
    ".knip.json": "json",
    ".lefthook.yml": "yaml",
    ".lint-staged.config.js": "javascript",
    ".markdownlint.json": "json",
    ".mocharc.yml": "yaml",
    ".modernizrrc": "json",
    ".nano-staged.json": "json",
    ".netlify.toml": "toml",
    ".nodemon.json": "json",
    ".nx.json": "json",
    ".parcelrc": "json",
    ".percy.yml": "yaml",
    ".php_cs.dist": "php",
    ".playwright.config.ts": "typescript",
    ".pm2.config.js": "json",
    ".postcss.config.js": "javascript",
    ".pre-commit-config.yaml": "yaml",
    ".prettierignore": "markdown",
    ".prettierrc.json": "json",
    ".prisma": "prisma",
    ".protractor.conf.js": "javascript",
    ".pylintrc": "python",
    ".pyproject.toml": "toml",
    ".remarkrc": "json",
    ".renovaterc": "json",
    ".replit": "markdown",
    ".rspec": "ruby",
    ".rubocop.yml": "yaml",
    ".ruff.toml": "toml",
    ".s3cfg": "python",
    ".sentryclirc": "markdown",
    ".snakemake.yaml": "yaml",
    ".snowpack.config.js": "javascript",
    ".snyk.json": "json",
    ".sonarcloud.properties": "markdown",
    ".storybook": "javascript",
    ".stryker.conf.js": "javascript",
    ".stylelintrc": "json",
    ".stylua.toml": "toml",
    ".svgo.config.js": "javascript",
    ".swcrc": "json",
    ".tailwind.config.js": "javascript",
    ".taze.config.js": "javascript",
    ".test.js": "javascript", ".test.ts": "typescript",
    ".spec.js": "javascript", ".spec.ts": "typescript",
    ".test.jsx": "javascript", ".test.tsx": "typescript",
    ".spec.jsx": "javascript", ".spec.tsx": "typescript",
    ".textlintrc": "json",
    ".tsconfig.json": "json",
    ".tsdoc.json": "json",
    ".typedoc.json": "json",
    ".unocss.config.js": "javascript",
    ".verdaccio.yaml": "yaml",
    ".vite.config.ts": "typescript",
    ".vitest.config.ts": "typescript",
    ".vscodeignore": "json",
    ".vscode": "json",
    ".wallaby.js": "javascript",
    ".webpack.config.js": "javascript",
    ".wintersmith.coffee": "coffeescript",
    ".wxml": "html",
    ".wrangler.toml": "toml",

    # ── docs / project files ──────────────────────────────────────────────
    ".authors": "markdown",
    ".changelog": "markdown",
    ".citation": "markdown",
    ".codeowners": "markdown",
    ".conduct": "markdown",
    ".contributing": "markdown",
    ".credits": "markdown",
    ".gemspec": "ruby",
    ".gemfile": "ruby",
    ".go.mod": "go", ".go.sum": "go",
    ".hosts": "xml",
    ".podspec": "ruby",
    ".roadmap": "markdown",
    ".todo": "markdown",
    ".unlicense": "markdown",

    # ── 3D / CAD ─────────────────────────────────────────────────────────
    ".blend": "blender", ".blend1": "blender",
    ".fbx": "blender", ".obj": "blender", ".stl": "blender",
    ".gltf": "blender", ".glb": "blender",
    ".3ds": "blender", ".dae": "blender",
    ".dwg": "blender", ".dxf": "blender",
    ".step": "blender", ".stp": "blender",

    # ── data / misc ───────────────────────────────────────────────────────
    ".bib": "markdown", ".bibtex": "markdown",
    ".csv": "excel", ".tsv": "excel",
    ".dbf": "database",
    ".dicom": "python", ".dcm": "python",  # medical -> closest available
    ".edf": "python",
    ".fits": "python",  # scientific -> closest available
    ".gcode": "binary",  # gcode -> binary
    ".grib": "python",
    ".hdf5": "python", ".h5": "python",
    ".he5": "python",
    ".ics": "markdown",
    ".ini": "markdown",
    ".proto": "binary",
    ".proto3": "binary",
    ".reg": "markdown",
    ".srt": "markdown", ".sub": "markdown", ".vtt": "markdown",
    ".usdz": "blender",
    ".vcf": "markdown",
    ".vcard": "markdown",
    ".webm": "video",
    ".wkt": "python",
    ".xlf": "xml", ".xliff": "xml",
    ".xlf2": "xml",
    ".po": "markdown", ".pot": "markdown",

    # ── extensions to existing icons ───────────────────────────────────────
    ".rmd": "r", ".rproj": "r",
    ".rda": "r", ".rds": "r",
    ".Rproj": "r",
    ".Rmd": "r",

    # ── game engines ───────────────────────────────────────────────────────
    ".tscn": "godot", ".tres": "godot",
    ".gd": "godot",
    ".unity": "unity", ".unitypackage": "unity",
    ".uproject": "unity",  # unreal -> unity (closest)
    ".roblox": "lua",

    # ── mobile / cross-platform ────────────────────────────────────────────
    ".xcodeproj": "swift", ".xcworkspace": "swift",
    ".pbxproj": "swift",
    ".plist": "xml",
    ".gradle.kts": "gradle",
    ".strings": "xml",

    # ── misc tools ─────────────────────────────────────────────────────────
    ".asciidoc": "markdown",
    ".adoc": "markdown",
    ".bib": "markdown",
    ".claude": "json",
    ".cline": "json",
    ".copilot": "json",
    ".drawio": "svg",
    ".excalidraw": "svg",
    ".figma": "svg",
    ".gemini": "json",
    ".gitpod": "yaml",
    ".grafana": "json",
    ".helm": "yaml",
    ".jupyter": "python", ".ipynb": "python",
    ".lottie": "json",
    ".mermaid": "markdown",
    ".obsidian": "markdown",
    ".opencode": "json",
    ".postman": "json",
    ".sketch": "svg",
    ".swagger": "yaml",
    ".tauri": "rust",
    ".tldraw": "svg",
    ".travis.yml": "yaml",

    # ── more file types ───────────────────────────────────────────────────
    ".appimage": "binary",
    ".apk": "binary",
    ".ipa": "binary",
    ".msix": "binary",
    ".msixbundle": "binary",
    ".appx": "binary",
    ".snap": "binary",
    ".deb": "binary",
    ".rpm": "binary",
    ".pkg": "binary",
    ".dmg": "binary",
    ".iso": "binary",
    ".img": "binary",
    ".vdi": "binary",
    ".vmdk": "binary",
    ".vhd": "binary",
    ".vhdx": "binary",
    ".ova": "binary",
    ".ovf": "binary",
}


def icon_for_ext(ext: str, size: int = 32,
                 color: str = _CLR_DEFAULT) -> QIcon:
    """Return a file-type icon for the given extension.

    Priority: Material icon from disk > inline Fluent SVG > OS shell icon.
    """
    # Try Material icon from disk first
    mat_name = _MATERIAL_EXT_MAP.get(ext.lower())
    if mat_name:
        ico = _material_icon(mat_name, size)
        if not ico.isNull():
            return ico
    # Fallback to inline Fluent SVG
    name = _EXT_MAP.get(ext.lower(), "file_text")
    return icon(name, size, color)


def action_icon(name: str, accent: bool = False, size: int = 20) -> QIcon:
    """Convenience: icon with default or accent colour."""
    color = _CLR_ACCENT if accent else _CLR_DEFAULT
    return icon(name, size, color)


# ── prebuilt icon sets for quick access sidebar ─────────────────────────

_FOLDER_ICON_MAP: dict[str, str] = {
    "desktop": "folder-desktop",
    "downloads": "folder-downloads",
    "download": "folder-downloads",
    "documents": "folder-documents",
    "docs": "folder-documents",
    "documentation": "folder-documents",
    "pictures": "folder-images",
    "images": "folder-images",
    "photos": "folder-images",
    "music": "folder-music",
    "audio": "folder-music",
    "videos": "folder-video",
    "video": "folder-video",
    "movies": "folder-video",
    "home": "folder-home",
    "~": "folder-home",
    "src": "folder-src",
    "source": "folder-src",
    "code": "folder-code",
    "test": "folder-test",
    "tests": "folder-test",
    "__tests__": "folder-test",
    "config": "folder-config",
    "settings": "folder-settings",
    "tools": "folder-tools",
    "utils": "folder-utils",
    "scripts": "folder-scripts",
    "lib": "folder-lib",
    "library": "folder-library",
    "dist": "folder-dist",
    "build": "folder-dist",
    "out": "folder-dist",
    "target": "folder-target",
    "bin": "folder-dist",
    "log": "folder-log",
    "logs": "folder-log",
    "temp": "folder-temp",
    "tmp": "folder-temp",
    "cache": "folder-temp",
    "node_modules": "folder-node",
    "npm": "folder-npm",
    "yarn": "folder-yarn",
    "pnpm": "folder-pnpm",
    "git": "folder-git",
    ".git": "folder-git",
    "github": "folder-github",
    ".github": "folder-github",
    "gitlab": "folder-gitlab",
    "docker": "folder-docker",
    "database": "folder-database",
    "db": "folder-database",
    "archive": "folder-zip",
    "archives": "folder-zip",
    "zip": "folder-zip",
    "backup": "folder-backup",
    "backups": "folder-backup",
    "android": "folder-android",
    "ios": "folder-ios",
    "linux": "folder-linux",
    "windows": "folder-windows",
    "python": "folder-python",
    "rust": "folder-rust",
    "react": "folder-react",
    "vue": "folder-vue",
    "angular": "folder-angular",
    "svelte": "folder-svelte",
    "public": "folder-public",
    "assets": "folder-resource",
    "resources": "folder-resource",
}


def folder_icon(name: str = "", size: int = 20, color: str = _CLR_DEFAULT) -> QIcon:
    """Return a rich vector folder icon.

    Tries specialized folder SVGs from disk first (e.g. 'folder-desktop', 'folder-src'),
    then generic golden folder, then inline Fluent fallback.
    """
    clean_name = name.lower().strip() if name else ""
    if clean_name in ("c:", "d:", "e:", "f:", "c:\\", "d:\\", "e:\\", "f:\\") or clean_name.endswith(":"):
        ico = _material_icon("folder-windows", size)
        if not ico.isNull():
            return ico
        ico = icon("drive", size, _CLR_WHITE)
        if not ico.isNull():
            return ico

    mat_name = _FOLDER_ICON_MAP.get(clean_name) if clean_name else None
    if mat_name:
        ico = _material_icon(mat_name, size)
        if not ico.isNull():
            return ico

    # Default to classic golden folder with warm amber tint
    ico = _material_icon("folder", size, default_color="#F1A80A")
    if not ico.isNull():
        return ico
    ico = _material_icon("folder-resource", size)
    if not ico.isNull():
        return ico

    return icon("folder", size, color or "#F1A80A")


def sidebar_icon(name: str, size: int = 16) -> QIcon:
    """Sidebar Quick Access icon at 16px — uses rich Material folder icons."""
    return folder_icon(name, size)
