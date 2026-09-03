"""Windows RAM Standby List & Working Set Kernel Purger Page.

Studio for real-time memory monitoring, purging the Windows NT Standby List,
and emptying process working sets using native NtSetSystemInformation system calls.
"""

from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import Qt, QObject, Signal, QThread, QTimer
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cortex_unified.system_tools.memory_standby_purger import (
    MemorySnapshot,
    MemoryStandbyPurger,
    PurgeResult,
)
from .widgets import Card, CircularGauge, StatCard, status_note, title_block
from .window import _Page, fmt_bytes


class MemoryStandbyPurgerPage(_Page):
    """UI studio for Standby List and working set kernel optimization."""

    def __init__(self, win) -> None:
        """__init__."""
        super().__init__(win)
        self.purger = MemoryStandbyPurger()

        hdr = title_block(
            "RAM Standby List & Working Set Purger",
            "Flush Windows NT Standby List caches and process working sets via native NtSetSystemInformation (Class 80).",
        )
        self.v.addWidget(hdr)

        # Stat cards row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.stat_phys_total = StatCard(self.p, "Physical RAM", "0 GB")
        self.stat_phys_used = StatCard(self.p, "Used Memory", "0 GB")
        self.stat_phys_avail = StatCard(self.p, "Available RAM", "0 GB")
        self.stat_load = StatCard(self.p, "Memory Load", "0%")
        stats_row.addWidget(self.stat_phys_total)
        stats_row.addWidget(self.stat_phys_used)
        stats_row.addWidget(self.stat_phys_avail)
        stats_row.addWidget(self.stat_load)
        self.v.addLayout(stats_row)

        # Action cards row
        action_card = Card(self.p)
        action_lay = QVBoxLayout(action_card)
        action_lay.setContentsMargins(18, 16, 18, 16)
        action_lay.setSpacing(12)

        lbl_actions = QLabel("<b>Kernel Optimization Commands:</b>")
        action_lay.addWidget(lbl_actions)

        btn_grid = QGridLayout()
        btn_grid.setSpacing(12)

        self.btn_purge_standby = QPushButton("Purge Standby List (Command 4)")
        self.btn_purge_standby.setObjectName("AccentButton")
        self.btn_purge_standby.setToolTip("Flushes pages in the standby list to free up uncommitted RAM.")
        self.btn_purge_standby.clicked.connect(self._on_purge_standby)
        btn_grid.addWidget(self.btn_purge_standby, 0, 0)

        self.btn_empty_working_sets = QPushButton("Empty Working Sets (Command 2)")
        self.btn_empty_working_sets.setToolTip("Forces all running processes to trim their private working sets.")
        self.btn_empty_working_sets.clicked.connect(self._on_empty_working_sets)
        btn_grid.addWidget(self.btn_empty_working_sets, 0, 1)

        self.btn_purge_modified = QPushButton("Flush Modified Page List (Command 3)")
        self.btn_purge_modified.setToolTip("Writes dirty modified pages directly to disk before clearing.")
        self.btn_purge_modified.clicked.connect(self._on_purge_modified)
        btn_grid.addWidget(self.btn_purge_modified, 1, 0)

        self.btn_purge_all = QPushButton("1-Click Complete Kernel Purge")
        self.btn_purge_all.setToolTip("Executes complete memory compaction and standby purge.")
        self.btn_purge_all.clicked.connect(self._on_purge_all)
        btn_grid.addWidget(self.btn_purge_all, 1, 1)

        action_lay.addLayout(btn_grid)

        # Status note
        self.note = status_note(
            self.p,
            "info",
            "Note: Purging the Standby List requires SeProfileSingleProcessPrivilege. "
            "If not running as Administrator, Windows NT will return STATUS_PRIVILEGE_NOT_HELD.",
        )
        action_lay.addWidget(self.note)
        self.v.addWidget(action_card)

        # Timer to update stats periodically
        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self._refresh_stats)
        self._timer.start()
        self._refresh_stats()

    def _refresh_stats(self) -> None:
        """_refresh_stats."""
        snap = self.purger.get_memory_snapshot()
        self.stat_phys_total.set_value(fmt_bytes(snap.total_phys_bytes))
        self.stat_phys_used.set_value(fmt_bytes(snap.used_phys_bytes))
        self.stat_phys_avail.set_value(fmt_bytes(snap.avail_phys_bytes))
        self.stat_load.set_value(f"{snap.memory_load_percent}%")

    def _on_purge_standby(self) -> None:
        """_on_purge_standby."""
        res = self.purger.purge_standby_list()
        self._handle_result(res)

    def _on_empty_working_sets(self) -> None:
        """_on_empty_working_sets."""
        res = self.purger.purge_working_sets()
        self._handle_result(res)

    def _on_purge_modified(self) -> None:
        """_on_purge_modified."""
        res = self.purger.purge_modified_page_list()
        self._handle_result(res)

    def _on_purge_all(self) -> None:
        """_on_purge_all."""
        r1 = self.purger.purge_working_sets()
        r2 = self.purger.purge_modified_page_list()
        r3 = self.purger.purge_standby_list()
        self._refresh_stats()
        if r3.success:
            QMessageBox.information(
                self,
                "Memory Compaction Succeeded",
                f"Flushed working sets, written modified pages, and purged standby list.\n"
                f"Reclaimed approximately {fmt_bytes(r3.reclaimed_bytes_approx)} of physical RAM.",
            )
        else:
            QMessageBox.warning(self, "Memory Action Notice", r3.message)

    def _handle_result(self, res: PurgeResult) -> None:
        """_handle_result."""
        self._refresh_stats()
        if res.success:
            msg = f"{res.message}\nReclaimed: {fmt_bytes(res.reclaimed_bytes_approx)}." if res.reclaimed_bytes_approx > 0 else res.message
            QMessageBox.information(self, "Command Succeeded", msg)
        else:
            QMessageBox.warning(self, "Command Status", res.message)
