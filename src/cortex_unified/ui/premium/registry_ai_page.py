"""AI Registry Cleaner page — ML-powered risk scoring for registry cleanup.

Research: Microsoft KB 2563254 explicitly recommends against registry cleaners.
Modern ML approach (Saha et al., COMNETS 2020; Soltaniani & Ghafari, 2026)
shows context-aware models achieve 89% F1 for detecting safe-to-remove keys.
Auslogics/Wise use rule-based categories; this page adds learned safety
on top: key path + value + surrounding keys = context vector -> risk score.

Risk thresholds:
  - risk < 0.3:  remove (high confidence orphan)
  - 0.3 <= risk < 0.6:  review (uncertain)
  - risk >= 0.6:  keep (likely system/active)
"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from .widgets import title_block
from .window import _Page, fmt_bytes
from .states import StatePanel
from cortex_unified.analyzers.registry_cleaner_ai import AIRegistryCleaner, ScanResult


class _RegistryWorker(QObject):
    """Registryworker.

    Manages RegistryWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(object)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        root: str,
        categories: list[str],
        risk_threshold: float,
        create_restore_point: bool = True,
    ):
        """Initialize worker.

        Initializes the instance and configures internal state.

        Args:
            root (str): Filesystem path to the target file or directory.
            categories (list[str]): The categories parameter.
            risk_threshold (float): The risk threshold parameter.
            create_restore_point (bool): The create restore point parameter.
        """
        super().__init__()
        self._root = root
        self._categories = categories
        self._risk_threshold = risk_threshold
        self._create_restore_point = create_restore_point
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
            cleaner = AIRegistryCleaner(
                create_restore_point=False,
                progress_callback=lambda msg, *_: self.progress.emit(str(msg)),
                cancel_event=self._cancel,
            )
            result: ScanResult = cleaner.scan(categories=self._categories)
            # Filter by risk threshold for display
            filtered = [
                i
                for i in result.issues
                if i.risk_score < self._risk_threshold or i.recommendation != "keep"
            ]
            self.finished.emit(
                {
                    "issues": filtered,
                    "all_issues": result.issues,
                    "scan_time": result.scan_time,
                    "categories_scanned": result.categories_scanned,
                    "model_version": result.model_version,
                }
            )
        except Exception as exc:
            self.failed.emit(str(exc))


class RegistryAICleanerPage(_Page):
    """Registryaicleanerpage.

    Manages RegistryAICleanerPage operations and coordinates related state changes for the component.
    """

    _DEFAULT_ROOT = r"HKLM\Software\Microsoft\Windows\CurrentVersion"

    def __init__(self, win):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(
            title_block(
                "AI Registry Cleaner",
                "ML-powered risk scoring (ONNX + heuristic fallback) — scans "
                "App Paths, Uninstall, SharedDLLs, Fonts, Services, Run keys, MRU. "
                "Risk < 0.3 = remove, 0.3–0.6 = review, ≥ 0.6 = keep.",
            )
        )

        from PySide6.QtWidgets import (
            QFileDialog,
            QProgressBar,
            QPushButton,
            QSpinBox,
        )

        picker = QHBoxLayout()
        pick_btn = QPushButton("Choose Registry Root…")
        self.path_label = QLabel(self._DEFAULT_ROOT)
        self.run_btn = QPushButton("Scan")
        self.run_btn.setObjectName("Primary")
        self.risk_spin = QDoubleSpinBox()
        self.risk_spin.setRange(0.0, 1.0)
        self.risk_spin.setSingleStep(0.05)
        self.risk_spin.setValue(0.3)
        self.risk_spin.setToolTip(
            "Risk threshold: <0.3 = remove, 0.3-0.6 = review, >=0.6 = keep"
        )
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(
            [
                "All Categories",
                "App Paths Only",
                "Uninstall Only",
                "SharedDLLs Only",
                "Fonts Only",
                "Services Only",
                "Run/RunOnce Only",
                "MRU Only",
            ]
        )
        pick_btn.clicked.connect(self._pick)
        self.run_btn.clicked.connect(self._run)
        picker.addWidget(pick_btn)
        picker.addWidget(self.path_label, 1)
        picker.addWidget(QLabel("Risk:"))
        picker.addWidget(self.risk_spin)
        picker.addWidget(QLabel("Categories:"))
        picker.addWidget(self.cat_combo)
        picker.addWidget(self.run_btn)
        self.v.addLayout(picker)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.v.addWidget(self.status)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(
            ["Key Path", "Value Name", "Category", "Risk Score", "Recommendation"]
        )
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._folder = self._DEFAULT_ROOT
        self._worker = None

    def _pick(self):
        """Prompt the user to select a filesystem directory or file.

        Launches a native file dialog and populates the selected path into the corresponding target input widget.
        """
        from PySide6.QtWidgets import QFileDialog

        folder = QFileDialog.getExistingDirectory(self, "Select folder", self._folder)
        if folder:
            self._folder = folder
            self.path_label.setText(folder)

    def _run(self):
        """Run.

        Manages run operations and coordinates related state changes for the component.
        """
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Scanning registry (AI risk scoring)…")
        self.status.setText(f"Scanning {self._folder}…")
        self.tbl.setRowCount(0)

        cat_map = {
            0: None,
            1: ["unused_file_extension", "missing_application_path"],
            2: ["orphaned_uninstall"],
            3: ["invalid_shared_dll"],
            4: ["orphaned_font"],
            5: ["orphaned_service_driver"],
            6: ["orphaned_path_value"],
            7: ["stale_mru_cache"],
        }
        cats = cat_map[self.cat_combo.currentIndex()]

        w = _RegistryWorker(
            self._folder,
            categories=cats or list(self._all_categories()),
            risk_threshold=self.risk_spin.value(),
        )
        self._worker = w
        self.win.run_worker(w, self._on_done, self._fail, on_progress=self._on_progress)

    def _all_categories(self):
        """_all_categories.

        Manages all categories operations and coordinates related state changes for the component.
        """
        from cortex_unified.analyzers.registry_cleaner_ai import _CATEGORY_DEFS

        return _CATEGORY_DEFS.keys()

    def _on_progress(self, msg: str):
        """_on_progress.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            msg (str): Informational or progress status message.
        """
        self.status.setText(msg)

    def _on_done(self, data: dict):
        """_on_done.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            data (dict): The data parameter.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)

        issues = data.get("issues", [])
        all_issues = data.get("all_issues", [])
        if not issues:
            self.state.show_empty(
                "No registry issues above the risk threshold. "
                "Lower the threshold or scan more categories."
            )
            self.status.setText("No issues found above threshold.")
            self.win.statusBar().showMessage("No registry issues found", 5000)
            return

        self.state.clear()
        self.tbl.setRowCount(len(issues))
        for r, issue in enumerate(issues):
            self.tbl.setItem(r, 0, QTableWidgetItem(issue.key_path))
            self.tbl.setItem(r, 1, QTableWidgetItem(issue.value_name))
            self.tbl.setItem(r, 2, QTableWidgetItem(issue.category))
            risk_item = QTableWidgetItem(f"{issue.risk_score:.2f}")
            risk_item.setToolTip(f"Confidence: {issue.confidence:.0%}")
            self.tbl.setItem(r, 3, risk_item)
            rec_item = QTableWidgetItem(issue.recommendation.upper())
            self.tbl.setItem(r, 4, rec_item)

        total = 0
        for issue in issues:
            try:
                total += Path(issue.value_data).stat().st_size
            except OSError:
                pass

        self.status.setText(
            f"{len(issues)} issues to review ({len(all_issues)} total scanned), "
            f"{fmt_bytes(total)} potential reclaim"
        )
        self.win.statusBar().showMessage(
            f"{len(issues)} registry issues ({len(all_issues)} scanned)", 5000
        )

    def _fail(self, msg):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg: Informational or progress status message.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._run)
