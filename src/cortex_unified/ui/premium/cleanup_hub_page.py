"""Cleanup Hub: unified Storage Sense-style view of all cleanup categories.

Groups every engine/categories.py CleanupCategory as a card with
RiskLevel + Reversible badges (reuse CleanupCategory.risk/reversible:30),
a live reclaimed estimate (via _get_dir_size / CleanerService scan), and a
"Select D:\\code" shortcut that points the log/project-cache sweeps at the
secondary drive where manual hits (21.9GB target, 7.6GB logs) hid.

Cards are grouped like Windows Storage Sense so users recognize the layout,
and each card links directly to its underlying cleaner (temp, browser, AI
recordings, Docker FS cache, cargo registry, scoop, WSL compact, etc.).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cortex_unified.engine import CleanerService, RiskLevel
from cortex_unified.engine.categories import CleanupCategory, default_categories, _get_dir_size

from .states import StatePanel
from .widgets import Card, StatCard, status_note, title_block
from .window import _Page, fmt_bytes

IS_WINDOWS = sys.platform == "win32"


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------

class HubScanWorker(QObject):
    """Scans all cleanup categories via CleanerService.

    Emits ``finished`` with a CleanupReport, ``progress`` with status text,
    or ``failed`` with an error message.
    """
    finished = Signal(object)  # CleanupReport
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, max_risk: str = "medium", include_disabled: bool = True):
        """Store max-risk level, disabled-category flag, and a cancel event."""
        super().__init__()
        self._max_risk = max_risk
        self._include_disabled = include_disabled
        import threading
        self._cancel = threading.Event()

    def cancel(self):
        """Request cooperative cancellation of the running scan."""
        self._cancel.set()

    def run(self):
        """Run the category scan and emit the report or a failure."""
        try:
            report = CleanerService().scan_categories(
                max_risk=RiskLevel(self._max_risk),
                include_disabled=self._include_disabled,
                progress=self.progress.emit,
                cancel_event=self._cancel,
            )
            self.finished.emit(report)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

# Risk -> badge color / label
_RISK_STYLE = {
    RiskLevel.LOW: ("LOW", "#34D399"),
    RiskLevel.MEDIUM: ("MEDIUM", "#FBBF24"),
    RiskLevel.HIGH: ("HIGH", "#FB7185"),
}


def _risk_label(risk: RiskLevel) -> str:
    """Return the display label ("LOW"/"MEDIUM"/"HIGH") for a risk level."""
    return _RISK_STYLE[risk][0]


def _risk_color(risk: RiskLevel) -> str:
    """Return the badge hex color for a risk level."""
    return _RISK_STYLE[risk][1]


class CleanupHubPage(_Page):
    """Storage Sense-style hub: every CleanupCategory as a card with estimates."""

    def __init__(self, win):
        """Build the Cleanup Hub: scan controls, summary cards, and a card grid."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Cleanup Hub",
            "Unified storage optimizer for system temp, browser caches, developer "
            "runtimes, application caches, and storage sense categories with "
            "live safety indicators and reclaim estimates."
        ))

        # --- top controls ---------------------------------------------------
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)

        self.scan_btn = QPushButton("Scan All Caches")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.clicked.connect(self._scan)
        ctrl.addWidget(self.scan_btn)

        self.btn_select_dir = QPushButton("Select Directory")
        self.btn_select_dir.setObjectName("Ghost")
        self.btn_select_dir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_dir.setToolTip("Add any custom drive or directory to the cleanup scan.")
        self.btn_select_dir.clicked.connect(self._pick_custom_folder)
        ctrl.addWidget(self.btn_select_dir)

        self.btn_select_file = QPushButton("Select File Location")
        self.btn_select_file.setObjectName("Ghost")
        self.btn_select_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_file.setToolTip("Select a file to add its parent folder to the cleanup scan.")
        self.btn_select_file.clicked.connect(self._pick_custom_file)
        ctrl.addWidget(self.btn_select_file)

        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.setObjectName("Ghost")
        self.btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_all.clicked.connect(lambda: self._select_all_cards(True))
        ctrl.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_deselect_all.setObjectName("Ghost")
        self.btn_deselect_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deselect_all.clicked.connect(lambda: self._select_all_cards(False))
        ctrl.addWidget(self.btn_deselect_all)

        ctrl.addStretch(1)

        self.include_disabled_chk = QCheckBox("Include opt-in (HIGH)")
        self.include_disabled_chk.setToolTip("Also scan HIGH-risk / disabled categories (rustup toolchains, WSL vhdx).")
        self.include_disabled_chk.setCursor(Qt.CursorShape.PointingHandCursor)
        ctrl.addWidget(self.include_disabled_chk)

        self.v.addLayout(ctrl)

        # Roots summary bar
        roots_row = QHBoxLayout()
        roots_row.setSpacing(8)
        self.target_roots_label = QLabel("Active Scan Roots: Default System Partitions")
        self.target_roots_label.setObjectName("Muted")
        roots_row.addWidget(self.target_roots_label)

        self.btn_clear_roots = QPushButton("Reset Roots")
        self.btn_clear_roots.setObjectName("Ghost")
        self.btn_clear_roots.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_roots.setVisible(False)
        self.btn_clear_roots.clicked.connect(self._clear_custom_roots)
        roots_row.addWidget(self.btn_clear_roots)
        roots_row.addStretch(1)
        self.v.addLayout(roots_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.scan_status = QLabel("")
        self.scan_status.setObjectName("Muted")
        self.v.addWidget(self.scan_status)

        # --- summary cards --------------------------------------------------
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)
        self.card_total = StatCard(self.p, "Reclaimable", "—")
        self.card_files = StatCard(self.p, "Files", "—")
        self.card_cats = StatCard(self.p, "Categories", "—")
        for c in (self.card_total, self.card_files, self.card_cats):
            summary_row.addWidget(c)
        self.v.addLayout(summary_row)

        # --- scrollable card grid ------------------------------------------
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        holder = QWidget()
        self.grid = QGridLayout(holder)
        self.grid.setContentsMargins(4, 8, 4, 8)
        self.grid.setSpacing(12)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(holder)
        self.attach_single_scroll(self.scroll)
        self.v.addWidget(self.scroll, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.scroll)
        self.v.addWidget(self.state, 1)

        # --- action row -----------------------------------------------------
        self._selected: dict[str, bool] = {}
        self._card_checkboxes: dict[str, QCheckBox] = {}
        self._report = None
        self._scan_map: dict[str, object] = {}  # id -> CategoryScan

        action_row = QHBoxLayout()
        self.clean_btn = QPushButton("Clean Selected")
        self.clean_btn.setObjectName("Danger")
        self.clean_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clean_btn.setEnabled(False)
        self.clean_btn.clicked.connect(self._clean)
        action_row.addWidget(self.clean_btn)
        action_row.addStretch(1)
        hint = QLabel("LOW = regenerable • MEDIUM = re-download • HIGH = confirm. "
                      "Reversible = safe undo (Recycle Bin / pull).")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        action_row.addWidget(hint, 1)
        self.v.addLayout(action_row)

        # Custom sweep roots chosen dynamically
        self._custom_roots: list[Path] = []

        self._worker = None
        self._loaded = False
        self._autoload = self._scan

    # -- scan ---------------------------------------------------------------

    def _scan(self):
        """Disable buttons and start a HubScanWorker (risk level from opt-in checkbox)."""
        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.state.show_loading("Scanning categories…")
        self.progress.setVisible(True)
        self.scan_status.setText("Scanning…")
        risk = "high" if self.include_disabled_chk.isChecked() else "medium"
        w = HubScanWorker(max_risk=risk, include_disabled=True)
        self._worker = w
        self.win.run_worker(w, self._on_scanned, self._fail, on_progress=self._on_progress)

    def _on_progress(self, msg: str):
        """Show worker progress text in the scan status label."""
        self.scan_status.setText(msg)

    def _on_scanned(self, report):
        """Update summary cards and rebuild the category card grid from the scan report."""
        self._worker = None
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.scan_btn.setEnabled(True)
        self._report = report
        self._scan_map = {s.category.id: s for s in report.scans}
        # Summary
        self.card_total.set_value(fmt_bytes(report.total_reclaimable_bytes), animate=True)
        self.card_files.set_value(f"{report.total_files:,}", animate=True)
        self.card_cats.set_value(str(len(report.scans)), animate=True)

        cats = default_categories()
        all_by_id = {c.id: c for c in cats}
        ids_sorted = sorted(all_by_id.keys(), key=lambda cid: (all_by_id[cid].risk.rank, cid))

        # Clear grid
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._selected = {}
        self._card_checkboxes = {}

        cols = 2
        if report.scans:
            self.state.clear()
        else:
            self.state.show_empty("No reclaimable files found under the scanned categories.")

        total = 0
        for idx, cid in enumerate(ids_sorted):
            cat = all_by_id[cid]
            scan = self._scan_map.get(cid)
            est_bytes = scan.total_bytes if scan else 0
            est_files = scan.file_count if scan else 0
            if est_bytes == 0 and cat.existing_paths():
                for p in cat.existing_paths():
                    try:
                        est_bytes += _get_dir_size(p)
                    except OSError:
                        continue
            card = self._make_card(cat, est_bytes, est_files)
            r, c = divmod(idx, cols)
            self.grid.addWidget(card, r, c)
            total += est_bytes

        self.win.statusBar().showMessage(
            f"Scanned {len(ids_sorted)} categories, {report.total_files:,} files, {fmt_bytes(report.total_reclaimable_bytes)} reclaimable", 5000)
        self._update_clean_enabled()

    def _make_card(self, cat: CleanupCategory, est_bytes: int, est_files: int) -> Card:
        """Build one category card: risk/reversible badges, paths, globs, estimate, and select checkbox."""
        card = Card(self.p)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)

        title_row = QHBoxLayout()
        title = QLabel(f"<b>{cat.label}</b>")
        title.setTextFormat(Qt.TextFormat.RichText)
        title_row.addWidget(title)
        title_row.addStretch(1)
        # Risk badge
        risk_txt, risk_col = _risk_label(cat.risk), _risk_color(cat.risk)
        risk_lbl = QLabel(f"<span style='background:{risk_col}; color:#111; padding:2px 6px; border-radius:6px; font-size:11px'><b>{risk_txt}</b></span>")
        risk_lbl.setTextFormat(Qt.TextFormat.RichText)
        risk_lbl.setToolTip(f"Risk: {cat.risk.value} — {cat.description}")
        title_row.addWidget(risk_lbl)
        # Reversible badge
        rev = QLabel(f"<span style='border:1px solid #6b7280; padding:1px 6px; border-radius:6px; font-size:11px'>{'↩ Reversible' if cat.reversible else 'Irreversible'}</span>")
        rev.setTextFormat(Qt.TextFormat.RichText)
        rev.setToolTip("Reversible = safe to undo (cache regenerates or goes to Recycle Bin)" if cat.reversible else "Irreversible = manual re-download / reinstall")
        title_row.addWidget(rev)
        lay.addLayout(title_row)

        desc = QLabel(cat.description)
        desc.setObjectName("Muted")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        # Paths line (first existing, else first declared)
        paths = cat.existing_paths()
        path_text = str(paths[0]) if paths else (str(cat.paths[0]) if cat.paths else "—")
        if len(cat.paths) > 1:
            path_text += f"  (+{len(cat.paths)-1} more)"
        path_lbl = QLabel(path_text)
        path_lbl.setObjectName("Muted")
        path_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(path_lbl)

        # Globs
        if cat.globs != ("*",):
            globs_lbl = QLabel(f"Matches: {', '.join(cat.globs)}")
            globs_lbl.setObjectName("Muted")
            lay.addWidget(globs_lbl)

        # Estimate
        est_row = QHBoxLayout()
        est_row.addWidget(QLabel(f"<b>{fmt_bytes(est_bytes)}</b> &middot; {est_files:,} file(s)" if est_bytes or est_files else "<span style='color:#888'>No files found</span>"))
        est_row.addStretch(1)
        chk = QCheckBox("Select")
        chk.setCursor(Qt.CursorShape.PointingHandCursor)
        chk.setChecked(est_bytes > 0 and cat.default_enabled)
        cid = cat.id
        self._selected[cid] = chk.isChecked()
        self._card_checkboxes[cid] = chk

        def _on_toggled(checked, _cid=cid):
            """Record the card's selection state and refresh the Clean button."""
            self._selected[_cid] = checked
            self._update_clean_enabled()
        chk.toggled.connect(_on_toggled)
        est_row.addWidget(chk)
        lay.addLayout(est_row)

        return card

    def _select_all_cards(self, state: bool):
        """Check or uncheck every category card checkbox at once."""
        for cid, chk in self._card_checkboxes.items():
            chk.setChecked(state)
            self._selected[cid] = state
        self._update_clean_enabled()

    def _update_clean_enabled(self):
        """Enable the Clean button only when something is selected and a scan has files."""
        any_sel = any(self._selected.values())
        report_ok = self._report is not None and self._report.total_files > 0
        self.clean_btn.setEnabled(any_sel and report_ok)

    def _fail(self, msg: str):
        """Reset UI state after a failed scan/clean and offer retry."""
        self._worker = None
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.scan_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._scan)

    # -- pickers ------------------------------------------------------------

    def _pick_custom_folder(self):
        """Add a chosen directory to the scan roots and rescan."""
        folder = QFileDialog.getExistingDirectory(self, "Select Directory to Add to Cleanup Sweep", str(Path.home()))
        if folder:
            p = Path(folder)
            if p not in self._custom_roots:
                self._custom_roots.append(p)
            self._update_roots_status()
            self._scan()

    def _pick_custom_file(self):
        """Add the parent folder of a chosen file to the scan roots and rescan."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Add Parent Location", str(Path.home()))
        if file_path:
            p = Path(file_path).parent
            if p not in self._custom_roots:
                self._custom_roots.append(p)
            self._update_roots_status()
            self._scan()

    def _clear_custom_roots(self):
        """Remove all custom scan roots (back to system defaults) and rescan."""
        self._custom_roots.clear()
        self._update_roots_status()
        self._scan()

    def _update_roots_status(self):
        """Refresh the active-scan-roots label and Reset Roots button visibility."""
        if self._custom_roots:
            roots_str = ", ".join(str(r) for r in self._custom_roots)
            self.target_roots_label.setText(f"Active Scan Roots: System Defaults + {roots_str}")
            self.btn_clear_roots.setVisible(True)
        else:
            self.target_roots_label.setText("Active Scan Roots: Default System Partitions (C:\\, Temp, AppData)")
            self.btn_clear_roots.setVisible(False)

    # -- clean --------------------------------------------------------------

    def _clean(self):
        """Confirm selection, then run CleanWorker on the selected categories (Recycle-Bin-safe delete)."""
        if self._report is None:
            return
        selected_ids = [cid for cid, on in self._selected.items() if on]
        if not selected_ids:
            QMessageBox.information(self, "Nothing selected", "Tick at least one category card first.")
            return
        # Filter report to selected categories only
        from cortex_unified.engine.service import CleanupReport
        filtered = CleanupReport(
            scans=[s for s in self._report.scans if s.category.id in selected_ids],
            duration_seconds=self._report.duration_seconds,
        )
        total = filtered.total_reclaimable_bytes
        confirm = QMessageBox.question(
            self, "Confirm cleanup",
            f"Clean {len(filtered.scans)} category(ies), {filtered.total_files:,} file(s), "
            f"{fmt_bytes(total)}?\n\nFiles go to the Recycle Bin where possible (reversible). "
            "HIGH-risk items are excluded unless you included them.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        from cortex_unified.engine import DeletionMethod
        self.clean_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.scan_status.setText("Cleaning selected categories…")
        from .workers import CleanWorker
        # Use DELETE (goes to recycle via SecureDeleter probe) for safety; user can pick SHRED elsewhere
        w = CleanWorker(filtered, DeletionMethod.DELETE.value)
        self.win.run_worker(w, self._on_cleaned, self._fail, on_progress=self._on_progress)

    def _on_cleaned(self, freed: int, items: int, skipped: int):
        """Report freed bytes and item counts after cleanup finishes."""
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        extra = f" {skipped} blocked/skipped." if skipped else ""
        QMessageBox.information(self, "Cleanup done", f"Freed {fmt_bytes(freed)} across {items} item(s).{extra}")
        self.win.statusBar().showMessage(f"Cleanup done: {fmt_bytes(freed)} freed", 6000)
        self._scan()
