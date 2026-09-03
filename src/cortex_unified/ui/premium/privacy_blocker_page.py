"""Privacy & Telemetry Blocker page — profile-based telemetry control.

Research: O&O ShutUp10++ 2.0 (2025), windows-telemetry-guard, TelemetrySlayer,
Windows-Privacy-Toolkit, RegiLattice (7,718 tweaks). IFEO persistence on
CompatTelRunner.exe survives feature updates; timestamped rollback before
every change.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .states import StatePanel
from .widgets import Card, title_block
from .window import _Page

# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------


class _PrivacyWorker(QObject):
    """Apply or revert privacy tweaks on a background thread."""

    finished = Signal(list)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(
        self, mode: str, profile: str | None = None, tweak_ids: list[str] | None = None
    ):
        """Initialize worker."""
        super().__init__()
        self._mode = mode  # "apply" | "revert"
        self._profile = profile
        self._tweak_ids = tweak_ids or []
        import threading

        self._cancel = threading.Event()

    def cancel(self):
        """cancel."""
        self._cancel.set()

    def run(self):
        """run."""
        try:
            from cortex_unified.system_tools.privacy_blocker import (
                PrivacyBlocker,
            )

            pb = PrivacyBlocker(
                create_restore_point=True,
                progress_callback=lambda msg: self.progress.emit(str(msg)),
                cancel_event=self._cancel,
            )

            if self._mode == "apply" and self._profile:
                results = pb.apply_profile(self._profile)
            elif self._mode == "revert":
                all_ids = list(pb.tweaks.keys())
                results = pb.remove(all_ids)
            else:
                results = {}

            rows = []
            for tid, ok in results.items():
                tweak = pb.tweaks.get(tid)
                name = tweak.name if tweak else tid
                cat = tweak.category if tweak else ""
                desc = tweak.description if tweak else ""
                status = "Applied" if ok else "Failed"
                rows.append((name, cat, status, desc))

            self.finished.emit(rows)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

_PROFILES = ["Minimal", "Moderate", "Aggressive", "Gaming", "Custom"]

_PROFILE_MAP = {
    "Minimal": "minimal",
    "Moderate": "business",
    "Aggressive": "privacy",
    "Gaming": "gaming",
    "Custom": "privacy",
}


class PrivacyBlockerPage(_Page):
    """Block Windows telemetry via profiles and per-category tweak control."""

    def __init__(self, win):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(
            title_block(
                "Privacy Blocker",
                "Profile-based telemetry control — blocks Windows data collection "
                "with IFEO persistence, firewall rules, and timestamped rollback. "
                "A restore point is created before every change.",
            )
        )

        # -- Profile picker + action buttons --------------------------------
        card = Card(self.p)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(16, 14, 16, 14)
        card_lay.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(10)

        row.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(_PROFILES)
        self.profile_combo.setMinimumWidth(140)
        row.addWidget(self.profile_combo)

        row.addStretch(1)

        self.apply_btn = QPushButton("Apply Selected")
        self.apply_btn.setObjectName("Primary")
        self.apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_btn.clicked.connect(self._apply)
        row.addWidget(self.apply_btn)

        self.revert_btn = QPushButton("Revert All")
        self.revert_btn.setObjectName("Ghost")
        self.revert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.revert_btn.clicked.connect(self._revert)
        row.addWidget(self.revert_btn)

        card_lay.addLayout(row)

        # Backup reminder
        backup_label = QLabel(
            "A system restore point and registry backups are created "
            "automatically before any change. You can revert from the "
            "Backups & Restore page at any time."
        )
        backup_label.setObjectName("Muted")
        backup_label.setWordWrap(True)
        card_lay.addWidget(backup_label)

        self.v.addWidget(card)

        # -- Category checkboxes --------------------------------------------
        cat_card = Card(self.p)
        cat_lay = QVBoxLayout(cat_card)
        cat_lay.setContentsMargins(16, 14, 16, 14)
        cat_lay.setSpacing(8)

        cat_header = QLabel("Tweak Categories")
        cat_header.setObjectName("SectionTitle")
        cat_lay.addWidget(cat_header)

        self._cat_checks: dict[str, QCheckBox] = {}
        categories = self._discover_categories()
        for cat in sorted(categories):
            cb = QCheckBox(cat.capitalize())
            cb.setChecked(True)
            self._cat_checks[cat] = cb
            cat_lay.addWidget(cb)

        self.v.addWidget(cat_card)

        # -- Progress + status ----------------------------------------------
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.v.addWidget(self.status)

        # -- Results table --------------------------------------------------
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(
            ["Tweak Name", "Category", "Status", "Description"]
        )
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.v.addWidget(self.tbl, 1)

        # -- State panel ----------------------------------------------------
        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._worker = None

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _discover_categories() -> list[str]:
        """Extract unique categories from the tweak catalog."""
        from cortex_unified.system_tools.privacy_blocker import TELEMETRY_TWEAKS

        return sorted({t.category for t in TELEMETRY_TWEAKS if t.category})

    def _selected_tweak_ids(self) -> list[str]:
        """Return tweak IDs matching the chosen profile and checked categories."""
        from cortex_unified.system_tools.privacy_blocker import TELEMETRY_TWEAKS

        profile_key = _PROFILE_MAP.get(self.profile_combo.currentText(), "privacy")
        checked = {cat for cat, cb in self._cat_checks.items() if cb.isChecked()}
        return [
            t.id
            for t in TELEMETRY_TWEAKS
            if profile_key in t.profiles and t.category in checked
        ]

    # -- apply / revert ----------------------------------------------------

    def _apply(self):
        """_apply."""
        profile = self.profile_combo.currentText()
        ids = self._selected_tweak_ids()
        if not ids:
            self.state.show_empty(
                "No tweaks match the selected profile and categories. "
                "Adjust the profile or check more categories."
            )
            return
        self._set_busy(True)
        self.state.show_loading(f"Applying '{profile}' profile ({len(ids)} tweaks)…")
        self.status.setText(f"Applying profile '{profile}'…")
        self.tbl.setRowCount(0)
        w = _PrivacyWorker("apply", profile=profile, tweak_ids=ids)
        self._worker = w
        self.win.run_worker(w, self._on_done, self._fail, on_progress=self._on_progress)

    def _revert(self):
        """_revert."""
        self._set_busy(True)
        self.state.show_loading("Reverting all tweaks…")
        self.status.setText("Reverting all applied tweaks…")
        self.tbl.setRowCount(0)
        w = _PrivacyWorker("revert")
        self._worker = w
        self.win.run_worker(w, self._on_done, self._fail, on_progress=self._on_progress)

    def _set_busy(self, busy: bool):
        """_set_busy."""
        self.apply_btn.setEnabled(not busy)
        self.revert_btn.setEnabled(not busy)
        self.profile_combo.setEnabled(not busy)
        self.progress.setVisible(busy)

    # -- callbacks ---------------------------------------------------------

    def _on_progress(self, msg: str):
        """_on_progress."""
        self.status.setText(msg)

    def _on_done(self, rows: list):
        """_on_done."""
        self._worker = None
        self._set_busy(False)
        if not rows:
            self.state.show_empty(
                "No tweaks were modified. Check that the selected profile "
                "has matching categories."
            )
            self.status.setText("No changes applied.")
            self.win.statusBar().showMessage("No privacy changes", 5000)
            return
        self.state.clear()
        self.tbl.setRowCount(len(rows))
        for r, (name, cat, status, desc) in enumerate(rows):
            self.tbl.setItem(r, 0, QTableWidgetItem(name))
            self.tbl.setItem(r, 1, QTableWidgetItem(cat.capitalize()))
            self.tbl.setItem(r, 2, QTableWidgetItem(status))
            self.tbl.setItem(r, 3, QTableWidgetItem(desc))
        ok = sum(1 for _, _, s, _ in rows if s == "Applied")
        fail = len(rows) - ok
        summary = f"{ok} applied, {fail} failed" if fail else f"{ok} tweaks applied"
        self.status.setText(summary)
        self.win.statusBar().showMessage(summary, 5000)

    def _fail(self, msg: str):
        """_fail."""
        self._worker = None
        self._set_busy(False)
        self.state.show_error(msg, on_retry=self._apply)
