"""Cortex Cleaner Production Debugging & Diagnostics Engine.

Provides deep structural, algorithmic, runtime, and UI diagnostics across all
components of the Cortex Cleaner application suite.
"""

from __future__ import annotations

from .runner import DiagnosticReport, DiagnosticRunner, run_all_diagnostics

__all__ = [
    "DiagnosticRunner",
    "DiagnosticReport",
    "run_all_diagnostics",
]
