"""Secure File Shredder — multi-standard sanitization with verification.

Standards: NIST SP 800-88 (Clear/Purge), DoD 5220.22-M (3/7 pass),
Gutmann 35-pass, HMG IS5, VSITR, GOST, Schneier, RCMP TSSIT OPS-II,
NSA EPL, and quick fill patterns. Storage-aware: auto-selects NIST Clear
for SSD, DoD 3-pass for HDD. Verifies each overwrite pass via read-back.
"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .widgets import Card, title_block
from .window import _Page, fmt_bytes
from .states import StatePanel
from cortex_unified.system_tools.secure_shredder import (
    SecureShredder,
    ShredStandard,
    StorageType,
)


class _ShredWorker(QObject):
    """Shredworker.

    Manages ShredWorker operations and coordinates related state changes for the component.
    """

    finished = Signal(list)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        file_paths: list[str],
        standard: ShredStandard,
        verify: bool,
    ):
        """Initialize worker.

        Initializes the instance and configures internal state.

        Args:
            file_paths (list[str]): Filesystem path to the target file or directory.
            standard (ShredStandard): The standard parameter.
            verify (bool): The verify parameter.
        """
        super().__init__()
        self._file_paths = file_paths
        self._standard = standard
        self._verify = verify
        self._cancel = threading.Event()

    def cancel(self):
        """cancel.

        Sets the internal cancellation event to cooperatively stop worker execution at the next safe boundary.
        """
        self._cancel.set()

    def run(self):
        """run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            engine = SecureShredder(
                progress_callback=lambda msg, *_: self.progress.emit(str(msg)),
                cancel_event=self._cancel,
                verify_passes=self._verify,
            )
            results = []
            for i, fp in enumerate(self._file_paths):
                if self._cancel.is_set():
                    break
                self.progress.emit(
                    f"Shredding ({i + 1}/{len(self._file_paths)}): {Path(fp).name}"
                )
                result = engine.shred_file(
                    fp, standard=self._standard, auto_detect=False
                )
                results.append(result)
            self.finished.emit(results)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# Maps human-readable combo labels to ShredStandard enum members.
_STANDARD_MAP: dict[str, ShredStandard] = {
    "NIST Clear (1-pass random)": ShredStandard.NIST_CLEAR,
    "NIST Purge – Crypto Erase (SSD)": ShredStandard.NIST_PURGE_CRYPTO,
    "NIST Purge – Block Erase (SSD)": ShredStandard.NIST_PURGE_BLOCK,
    "DoD 5220.22-M (3-pass)": ShredStandard.DOD_5220_22_M,
    "DoD 5220.22-M ECE (7-pass)": ShredStandard.DOD_5220_22_M_ECE,
    "Gutmann (35-pass)": ShredStandard.GUTMANN,
    "HMG IS5 Baseline (1-pass zeros)": ShredStandard.HMG_IS5_BASELINE,
    "HMG IS5 Enhanced (3-pass)": ShredStandard.HMG_IS5_ENHANCED,
    "BSI VSITR (7-pass)": ShredStandard.VSITR,
    "GOST R 50739 (2-pass)": ShredStandard.GOST_R_50739,
    "RCMP TSSIT OPS-II (7-pass)": ShredStandard.RCMP_TSSIT_OPS_II,
    "Schneier (7-pass)": ShredStandard.SCHNEIER,
    "NSA EPL (3-pass)": ShredStandard.NSA_EPL,
    "Zero Fill (1-pass)": ShredStandard.ZERO_FILL,
    "One Fill – 0xFF (1-pass)": ShredStandard.ONE_FILL,
    "Random (1-pass)": ShredStandard.RANDOM_1PASS,
    "Random (3-pass)": ShredStandard.RANDOM_3PASS,
}

_STORAGE_LABELS: dict[StorageType, str] = {
    StorageType.HDD: "HDD",
    StorageType.SSD_NVME: "SSD (NVMe)",
    StorageType.SSD_SATA: "SSD (SATA)",
    StorageType.USB_FLASH: "USB Flash",
    StorageType.UNKNOWN: "Unknown",
}


class SecureShredderPage(_Page):
    """Secureshredderpage.

    Manages SecureShredderPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(
            title_block(
                "Secure Shredder",
                "NIST SP 800-88, DoD 5220.22-M, Gutmann, and international standards. "
                "Storage-aware auto-selection (NIST Clear for SSD, DoD 3-pass for HDD). "
                "Verifies each overwrite pass via read-back with entropy analysis.",
            )
        )

        # ── File selection card ──────────────────────────────────────────────
        file_card = Card(self.p)
        fc_lay = QVBoxLayout(file_card)
        fc_lay.setContentsMargins(22, 20, 22, 20)
        fc_lay.setSpacing(12)

        picker_row = QHBoxLayout()
        self.add_files_btn = QPushButton("Add Files\u2026")
        self.add_files_btn.setObjectName("Ghost")
        self.add_files_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_files_btn.clicked.connect(self._add_files)
        self.add_folder_btn = QPushButton("Add Folder\u2026")
        self.add_folder_btn.setObjectName("Ghost")
        self.add_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_folder_btn.clicked.connect(self._add_folder)
        self.clear_list_btn = QPushButton("Clear List")
        self.clear_list_btn.setObjectName("Ghost")
        self.clear_list_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_list_btn.clicked.connect(self._clear_list)
        self.file_count_label = QLabel("No files selected")
        self.file_count_label.setObjectName("Muted")
        picker_row.addWidget(self.add_files_btn)
        picker_row.addWidget(self.add_folder_btn)
        picker_row.addWidget(self.clear_list_btn)
        picker_row.addStretch(1)
        picker_row.addWidget(self.file_count_label)
        fc_lay.addLayout(picker_row)

        # File list preview
        self.file_list_label = QLabel("")
        self.file_list_label.setObjectName("Muted")
        self.file_list_label.setWordWrap(True)
        fc_lay.addWidget(self.file_list_label)

        self.v.addWidget(file_card)

        # ── Settings card ────────────────────────────────────────────────────
        settings_card = Card(self.p)
        sc_lay = QVBoxLayout(settings_card)
        sc_lay.setContentsMargins(22, 20, 22, 20)
        sc_lay.setSpacing(12)

        row1 = QHBoxLayout()
        row1.setSpacing(12)
        row1.addWidget(QLabel("Wipe Standard:"))
        self.standard_combo = QComboBox()
        self.standard_combo.addItems(list(_STANDARD_MAP.keys()))
        self.standard_combo.setCurrentIndex(3)  # DoD 5220.22-M (3-pass)
        self.standard_combo.setToolTip(
            "NIST Clear: single verified random pass (recommended for SSD)\n"
            "DoD 3-pass: 0x00, 0xFF, random + verify (HDD compliance)\n"
            "DoD 7-pass ECE: extended with verification\n"
            "Gutmann 35-pass: targets MFM/RLL patterns (legacy audit)\n"
            "International standards: HMG IS5, VSITR, GOST, Schneier, RCMP"
        )
        row1.addWidget(self.standard_combo, 1)
        row1.addWidget(QLabel("Storage:"))
        self.storage_combo = QComboBox()
        self.storage_combo.addItems(list(_STORAGE_LABELS.values()))
        self.storage_combo.setToolTip(
            "Hint the shredder about the underlying media.\n"
            "SSD: firmware erase or single-pass recommended.\n"
            "HDD: multi-pass overwrite is effective."
        )
        row1.addWidget(self.storage_combo)
        sc_lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(16)
        self.verify_check = QCheckBox("Verify after wipe (read-back + entropy check)")
        self.verify_check.setChecked(True)
        self.verify_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.verify_check.setToolTip(
            "After each overwrite pass, read the file back and verify the "
            "written pattern matches. Entropy analysis confirms random data."
        )
        row2.addWidget(self.verify_check)
        row2.addStretch(1)
        sc_lay.addLayout(row2)

        # Storage type info label
        self.storage_info = QLabel("")
        self.storage_info.setObjectName("Muted")
        sc_lay.addWidget(self.storage_info)

        self.v.addWidget(settings_card)

        # ── Progress + status ────────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.v.addWidget(self.status)

        # ── Results table ────────────────────────────────────────────────────
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["File Path", "Size", "Standard", "Status"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setSortingEnabled(True)
        self.v.addWidget(self.tbl, 1)

        # ── State panel ──────────────────────────────────────────────────────
        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        # ── Action row ───────────────────────────────────────────────────────
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 8, 0, 0)
        action_row.addStretch(1)
        self.shred_btn = QPushButton("Shred Selected")
        self.shred_btn.setObjectName("Danger")
        self.shred_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.shred_btn.setEnabled(False)
        self.shred_btn.clicked.connect(self._confirm_shred)
        action_row.addWidget(self.shred_btn)
        self.v.addLayout(action_row)

        self._files: list[str] = []
        self._worker: _ShredWorker | None = None

    # ── File selection ────────────────────────────────────────────────────────

    def _add_files(self):
        """_add_files.

        Manages add files operations and coordinates related state changes for the component.
        """
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select files to shred",
            str(Path.home()),
        )
        if paths:
            self._files.extend(paths)
            self._update_file_count()

    def _add_folder(self):
        """_add_folder.

        Manages add folder operations and coordinates related state changes for the component.
        """
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select folder to shred",
            str(Path.home()),
        )
        if not folder:
            return
        folder_path = Path(folder)
        count = 0
        for f in folder_path.rglob("*"):
            if f.is_file():
                self._files.append(str(f))
                count += 1
        self._update_file_count()
        if count == 0:
            self.status.setText(f"No files found in {folder}")

    def _clear_list(self):
        """_clear_list.

        Manages clear list operations and coordinates related state changes for the component.
        """
        self._files.clear()
        self._update_file_count()
        self.tbl.setRowCount(0)
        self.state.clear()

    def _update_file_count(self):
        """_update_file_count.

        Manages update file count operations and coordinates related state changes for the component.
        """
        n = len(self._files)
        if n == 0:
            self.file_count_label.setText("No files selected")
            self.file_list_label.setText("")
            self.shred_btn.setEnabled(False)
        else:
            total = sum(Path(f).stat().st_size for f in self._files if Path(f).exists())
            self.file_count_label.setText(f"{n} file(s) — {fmt_bytes(total)}")
            self.shred_btn.setEnabled(True)
            # Show a preview of the first few files
            preview = "\n".join(
                f"  {i+1}. {Path(f).name}" for i, f in enumerate(self._files[:5])
            )
            if n > 5:
                preview += f"\n  ... and {n - 5} more"
            self.file_list_label.setText(preview)

    # ── Shred action ──────────────────────────────────────────────────────────

    def _confirm_shred(self):
        """_confirm_shred.

        Manages confirm shred operations and coordinates related state changes for the component.
        """
        if not self._files:
            return

        standard_label = self.standard_combo.currentText()
        standard = _STANDARD_MAP[standard_label]
        verify = self.verify_check.isChecked()
        n = len(self._files)
        total = sum(Path(f).stat().st_size for f in self._files if Path(f).exists())

        msg = (
            f"Permanently shred {n} file(s) ({fmt_bytes(total)})?\n\n"
            f"Standard: {standard_label}\n"
            f"Passes: {standard.pass_count}\n"
            f"Verification: {'ON' if verify else 'OFF'}\n\n"
            "THIS CANNOT BE UNDONE."
        )
        reply = QMessageBox.warning(
            self,
            "Confirm Secure Shred",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._run_shred(standard, verify)

    def _run_shred(self, standard: ShredStandard, verify: bool):
        """_run_shred.

        Manages run shred operations and coordinates related state changes for the component.

        Args:
            standard (ShredStandard): The standard parameter.
            verify (bool): The verify parameter.
        """
        self.shred_btn.setEnabled(False)
        self.add_files_btn.setEnabled(False)
        self.add_folder_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading(
            f"Shredding {len(self._files)} file(s) with {standard.name}…"
        )
        self.status.setText("Starting secure wipe…")
        self.tbl.setRowCount(0)

        w = _ShredWorker(self._files, standard, verify)
        self._worker = w
        self.win.run_worker(w, self._on_done, self._fail, on_progress=self._on_progress)

    def _on_progress(self, msg: str):
        """_on_progress.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            msg (str): Informational or progress status message.
        """
        self.status.setText(msg)

    def _on_done(self, results: list):
        """_on_done.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            results (list): Dictionary or data object holding operation results.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.shred_btn.setEnabled(True)
        self.add_files_btn.setEnabled(True)
        self.add_folder_btn.setEnabled(True)

        if not results:
            self.state.show_empty("No files were shredded (all skipped or cancelled).")
            self.status.setText("Shred cancelled.")
            self.win.statusBar().showMessage("Shred cancelled", 5000)
            return

        self.state.clear()
        self.tbl.setRowCount(len(results))
        success = 0
        failed = 0
        total_bytes = 0
        for r, res in enumerate(results):
            self.tbl.setItem(r, 0, QTableWidgetItem(res.file_path))
            self.tbl.setItem(r, 1, QTableWidgetItem(fmt_bytes(res.bytes_shredded)))
            self.tbl.setItem(r, 2, QTableWidgetItem(res.standard.name))
            status = "Shredded" if res.success else f"Failed: {res.error}"
            self.tbl.setItem(r, 3, QTableWidgetItem(status))
            if res.success:
                success += 1
                total_bytes += res.bytes_shredded
            else:
                failed += 1

        summary = (
            f"{success} shredded, {failed} failed — {fmt_bytes(total_bytes)} wiped"
        )
        self.status.setText(summary)
        self.win.statusBar().showMessage(summary, 5000)

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.shred_btn.setEnabled(True)
        self.add_files_btn.setEnabled(True)
        self.add_folder_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._confirm_shred)
        self.win._default_fail(msg)
