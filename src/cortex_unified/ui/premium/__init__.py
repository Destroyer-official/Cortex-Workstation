"""Cortex Cleaner - premium GUI.

A modern, cohesive PySide6 interface built on a real design system (QSS design
tokens + custom-painted widgets + elevation) rather than ad-hoc per-widget CSS.
It is engine-backed: every action runs against the safe, storage-aware
``cortex_unified.engine`` on a background thread, so the UI never freezes.

Entry point: ``cortex_unified.ui.premium.app:main`` (installed as ``cortex-gui``).
"""

from .theme import Palette, THEMES, apply_theme, build_stylesheet

__all__ = ["Palette", "THEMES", "apply_theme", "build_stylesheet"]
