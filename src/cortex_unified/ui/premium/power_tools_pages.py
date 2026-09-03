"""Premium GUI pages for Enterprise Power Tools & System Maintainers.

Contains full-featured interactive pages for:
- HashVerifierPage (Checksum & Manifest Validator)
- BatchRenamerPage (Regex & EXIF Multi-Renamer)
- FolderSyncPage (Directory Comparison & Synchronization)
- FileSplitterPage (File Splitter and Joiner)
- FileUnlockerPage (Windows Restart Manager Process Unlocker)
- AdsManagerPage (NTFS Alternate Data Streams & Zone.Identifier)
- EventLogCleanerPage (Windows Event Log Sweeper)
- SystemCacheRebuilderPage (Font & Icon Cache Rebuilder)
- NetworkOptimizerPage (DNS & Network Stack Optimizer)
- CrashDumpCleanerPage (Windows Memory & WER Crash Dump Cleaner)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QObject, Signal, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import icons
from .states import StatePanel
from .widgets import Card, StatCard, status_note, title_block
from .window import _Page, fmt_bytes

IS_WINDOWS = sys.platform == "win32"


# ===========================================================================
# 1. Checksum & Hash Verifier Page
# ===========================================================================

class HashVerifierPage(_Page):
    """File checksum calculator and manifest validator."""

    def __init__(self, win):
        """Build the Hash Verifier page with file picker, digests table, and manifest actions."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Checksum & Hash Verifier",
            "Calculate MD5, SHA-1, SHA-256, SHA-512, and CRC32 or verify checksum manifests.",
        ))

        picker_card = Card(self.p, "Card")
        p_lay = QHBoxLayout(picker_card)
        pick_btn = QPushButton("Select File…")
        pick_btn.setObjectName("Secondary")
        pick_btn.clicked.connect(self._pick_file)
        self.path_lbl = QLabel("No file selected")
        self.path_lbl.setObjectName("Muted")
        p_lay.addWidget(pick_btn)
        p_lay.addWidget(self.path_lbl, 1)

        self.calc_btn = QPushButton("Compute Hashes")
        self.calc_btn.setObjectName("Primary")
        self.calc_btn.setEnabled(False)
        self.calc_btn.clicked.connect(self._compute_hashes)
        p_lay.addWidget(self.calc_btn)
        self.v.addWidget(picker_card)

        # Hash Results Table
        table_card = Card(self.p, "Card")
        t_lay = QVBoxLayout(table_card)
        self.table = QTableWidget(5, 3)
        self.table.setHorizontalHeaderLabels(["Algorithm", "Checksum / Digest", "Action"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)

        algos = ["MD5", "SHA-1", "SHA-256", "SHA-512", "CRC32"]
        for row, algo in enumerate(algos):
            self.table.setItem(row, 0, QTableWidgetItem(algo))
            self.table.setItem(row, 1, QTableWidgetItem("—"))

        t_lay.addWidget(self.table)
        self.add_scrolling_list(table_card, stretch=1)

        # Manifest actions
        act_card = Card(self.p, "Card")
        a_lay = QHBoxLayout(act_card)
        self.verify_btn = QPushButton("Verify Manifest (.sfv / .sha256)…")
        self.verify_btn.setObjectName("Secondary")
        self.verify_btn.clicked.connect(self._verify_manifest)
        a_lay.addWidget(self.verify_btn)
        a_lay.addStretch(1)
        self.v.addWidget(act_card)

        self._current_file: Optional[Path] = None

    def _pick_file(self):
        """Pick a file to hash and enable computation."""
        fn, _ = QFileDialog.getOpenFileName(self, "Select File to Hash", str(Path.home()))
        if fn:
            self._current_file = Path(fn)
            self.path_lbl.setText(f"{self._current_file.name} ({fmt_bytes(self._current_file.stat().st_size)})")
            self.path_lbl.setObjectName("")
            self.path_lbl.setStyleSheet("color: inherit;")
            self.calc_btn.setEnabled(True)

    def _compute_hashes(self):
        """Compute MD5, SHA-1, SHA-256, SHA-512, and CRC32 for the chosen file."""
        if not self._current_file or not self._current_file.is_file():
            return
        from NexusExplorer.native.nexus_hash_tool import HashTool, HashAlgorithm
        res = HashTool.compute_all_hashes(self._current_file)

        mapping = {
            0: res.get(HashAlgorithm.MD5),
            1: res.get(HashAlgorithm.SHA1),
            2: res.get(HashAlgorithm.SHA256),
            3: res.get(HashAlgorithm.SHA512),
            4: res.get(HashAlgorithm.CRC32),
        }
        for row, h_res in mapping.items():
            if h_res and h_res.digest:
                self.table.setItem(row, 1, QTableWidgetItem(h_res.digest))
                copy_btn = QPushButton("Copy")
                copy_btn.setObjectName("Secondary")
                digest = h_res.digest
                copy_btn.clicked.connect(lambda _, d=digest: self._copy_to_clip(d))
                self.table.setCellWidget(row, 2, copy_btn)

    def _copy_to_clip(self, text: str):
        """Copy a checksum digest to the clipboard and confirm."""
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Checksum copied to clipboard.")

    def _verify_manifest(self):
        """Verify a .sfv/.md5/.sha256/.sha512 manifest and summarize match results."""
        fn, _ = QFileDialog.getOpenFileName(self, "Open Checksum Manifest", str(Path.home()), "Manifests (*.sfv *.md5 *.sha256 *.sha512);;All Files (*.*)")
        if not fn:
            return
        from NexusExplorer.native.nexus_hash_tool import HashTool
        results = HashTool.verify_manifest(fn)
        if not results:
            QMessageBox.warning(self, "Verify Manifest", "No valid checksum entries found in manifest.")
            return

        matches = sum(1 for r in results if r.status == "MATCH")
        mismatches = sum(1 for r in results if r.status == "MISMATCH")
        missing = sum(1 for r in results if r.status == "MISSING")

        msg = f"Verified {len(results)} file(s):\n• {matches} OK (Match)\n• {mismatches} Corrupted (Mismatch)\n• {missing} Missing"
        if mismatches == 0 and missing == 0:
            QMessageBox.information(self, "Manifest Verification Passed", msg)
        else:
            QMessageBox.warning(self, "Manifest Verification Issues Found", msg)


# ===========================================================================
# 2. Enterprise Batch Multi-Renamer Page
# ===========================================================================

class BatchRenamerPage(_Page):
    """Regex, token template, and EXIF batch multi-renamer."""

    def __init__(self, win):
        """Build the Batch Renamer page with pattern form, preview table, and apply/undo buttons."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Batch Multi-Renamer",
            "Batch rename multiple files with regex pattern replacement, counters, and EXIF/ID3 metadata.",
        ))

        # Controls Card
        ctrl_card = Card(self.p, "Card")
        c_lay = QVBoxLayout(ctrl_card)

        row1 = QHBoxLayout()
        pick_btn = QPushButton("Select Files…")
        pick_btn.setObjectName("Secondary")
        pick_btn.clicked.connect(self._pick_files)
        self.count_lbl = QLabel("0 files loaded")
        self.count_lbl.setObjectName("Muted")
        row1.addWidget(pick_btn)
        row1.addWidget(self.count_lbl)
        row1.addStretch(1)
        c_lay.addLayout(row1)

        form = QFormLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search string or regex pattern...")
        self.search_edit.textChanged.connect(self._update_preview)
        form.addRow("Search:", self.search_edit)

        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("Tokens: <counter:001>, <folder>, <date>, <artist>, <title>, <camera>, <dimensions>...")
        self.replace_edit.textChanged.connect(self._update_preview)
        form.addRow("Replace:", self.replace_edit)

        opt_row = QHBoxLayout()
        self.regex_chk = QCheckBox("Use Regular Expressions")
        self.regex_chk.toggled.connect(self._update_preview)
        opt_row.addWidget(self.regex_chk)

        self.case_combo = QComboBox()
        self.case_combo.addItems(["None", "UPPERCASE", "lowercase", "Title Case", "camelCase", "snake_case", "kebab-case"])
        self.case_combo.currentIndexChanged.connect(self._update_preview)
        opt_row.addWidget(QLabel("Case:"))
        opt_row.addWidget(self.case_combo)
        opt_row.addStretch(1)
        form.addRow("Options:", opt_row)

        c_lay.addLayout(form)
        self.v.addWidget(ctrl_card)

        # Preview Table
        table_card = Card(self.p, "Card")
        t_lay = QVBoxLayout(table_card)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Original Name", "New Name", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        t_lay.addWidget(self.table)
        self.add_scrolling_list(table_card, stretch=1)

        # Action Buttons
        act_row = QHBoxLayout()
        self.apply_btn = QPushButton("Apply Rename")
        self.apply_btn.setObjectName("Primary")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply_rename)
        self.undo_btn = QPushButton("Undo Last Rename")
        self.undo_btn.setObjectName("Secondary")
        self.undo_btn.clicked.connect(self._undo_rename)
        act_row.addWidget(self.apply_btn)
        act_row.addWidget(self.undo_btn)
        act_row.addStretch(1)
        self.v.addLayout(act_row)

        self._files: List[Path] = []
        from NexusExplorer.native.nexus_batch_renamer import BatchRenamer
        self._renamer = BatchRenamer()
        self._current_plan = []

    def _pick_files(self):
        """Pick files to rename and refresh the preview."""
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Rename", str(Path.home()))
        if files:
            self._files = [Path(f) for f in files]
            self.count_lbl.setText(f"{len(self._files)} file(s) selected")
            self._update_preview()

    def _update_preview(self):
        """Recompute the rename plan and show per-file status in the table."""
        if not self._files:
            return
        from NexusExplorer.native.nexus_batch_renamer import CaseTransformation

        case_map = {
            0: CaseTransformation.NONE,
            1: CaseTransformation.UPPERCASE,
            2: CaseTransformation.LOWERCASE,
            3: CaseTransformation.TITLE_CASE,
            4: CaseTransformation.CAMEL_CASE,
            5: CaseTransformation.SNAKE_CASE,
            6: CaseTransformation.KEBAB_CASE,
        }
        case_t = case_map.get(self.case_combo.currentIndex(), CaseTransformation.NONE)

        self._current_plan = self._renamer.preview_rename(
            file_paths=self._files,
            search_pattern=self.search_edit.text(),
            replace_pattern=self.replace_edit.text(),
            use_regex=self.regex_chk.isChecked(),
            case_transform=case_t,
        )

        self.table.setRowCount(len(self._current_plan))
        has_valid_changes = False

        for row, item in enumerate(self._current_plan):
            self.table.setItem(row, 0, QTableWidgetItem(item.original_name))
            self.table.setItem(row, 1, QTableWidgetItem(item.new_name))

            status_txt = "Ready" if (item.is_valid and item.is_changed) else ("Unchanged" if not item.is_changed else item.error_message)
            st_item = QTableWidgetItem(status_txt)
            if not item.is_valid:
                st_item.setForeground(Qt.GlobalColor.red)
            elif item.is_changed:
                st_item.setForeground(Qt.GlobalColor.green)
                has_valid_changes = True
            self.table.setItem(row, 2, st_item)

        self.apply_btn.setEnabled(has_valid_changes)

    def _apply_rename(self):
        """Execute the previewed rename plan and report the outcome."""
        if not self._current_plan:
            return
        count, err_count, errs = self._renamer.execute_rename(self._current_plan)
        if err_count > 0:
            QMessageBox.warning(self, "Rename Complete with Errors", f"Renamed {count} file(s). Errors: {err_count}\n" + "\n".join(errs[:5]))
        else:
            QMessageBox.information(self, "Rename Complete", f"Successfully renamed {count} file(s).")
        self._files = [Path(item.new_path) for item in self._current_plan if item.is_valid and item.is_changed]
        self._update_preview()

    def _undo_rename(self):
        """Revert the last executed rename."""
        count, errs = self._renamer.undo_last()
        if errs and count == 0:
            QMessageBox.warning(self, "Undo", "\n".join(errs))
        else:
            QMessageBox.information(self, "Undo Success", f"Reverted {count} file rename(s).")
            self._update_preview()


# ===========================================================================
# 3. Directory Diff & Folder Synchronization Page
# ===========================================================================

class FolderSyncPage(_Page):
    """Side-by-side folder comparison matrix and 1-click sync engine."""

    def __init__(self, win):
        """Build the Folder Sync page with folder pickers, compare controls, diff table, and sync mode."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Folder Compare & Sync",
            "Compare two folders by size, date, or content hash and synchronize missing or modified files.",
        ))

        # Folder Pickers
        pick_card = Card(self.p, "Card")
        p_lay = QVBoxLayout(pick_card)

        left_row = QHBoxLayout()
        l_btn = QPushButton("Left Folder…")
        l_btn.setObjectName("Secondary")
        l_btn.clicked.connect(self._pick_left)
        self.left_lbl = QLabel("No folder selected")
        self.left_lbl.setObjectName("Muted")
        left_row.addWidget(l_btn)
        left_row.addWidget(self.left_lbl, 1)
        p_lay.addLayout(left_row)

        right_row = QHBoxLayout()
        r_btn = QPushButton("Right Folder…")
        r_btn.setObjectName("Secondary")
        r_btn.clicked.connect(self._pick_right)
        self.right_lbl = QLabel("No folder selected")
        self.right_lbl.setObjectName("Muted")
        right_row.addWidget(r_btn)
        right_row.addWidget(self.right_lbl, 1)
        p_lay.addLayout(right_row)

        act_row = QHBoxLayout()
        self.deep_chk = QCheckBox("Deep Content Hash Check (SHA-256)")
        self.cmp_btn = QPushButton("Compare Folders")
        self.cmp_btn.setObjectName("Primary")
        self.cmp_btn.clicked.connect(self._run_compare)
        act_row.addWidget(self.deep_chk)
        act_row.addStretch(1)
        act_row.addWidget(self.cmp_btn)
        p_lay.addLayout(act_row)
        self.v.addWidget(pick_card)

        # Diff Table
        table_card = Card(self.p, "Card")
        t_lay = QVBoxLayout(table_card)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Relative Path", "Left Size / Date", "Status", "Right Size / Date"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        t_lay.addWidget(self.table)
        self.add_scrolling_list(table_card, stretch=1)

        # Sync Action Card
        sync_card = Card(self.p, "Card")
        s_lay = QHBoxLayout(sync_card)
        s_lay.addWidget(QLabel("Sync Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Mirror Left -> Right",
            "Mirror Right -> Left",
            "Two-Way Bidirectional Merge",
            "Update Newer Files Only",
        ])
        s_lay.addWidget(self.mode_combo)
        self.sync_btn = QPushButton("Synchronize Now")
        self.sync_btn.setObjectName("Primary")
        self.sync_btn.setEnabled(False)
        self.sync_btn.clicked.connect(self._run_sync)
        s_lay.addWidget(self.sync_btn)
        s_lay.addStretch(1)
        self.v.addWidget(sync_card)

        self._left_dir: Optional[Path] = None
        self._right_dir: Optional[Path] = None
        self._diff_list = []

    def _pick_left(self):
        """Pick the left folder to compare."""
        d = QFileDialog.getExistingDirectory(self, "Select Left Folder", str(Path.home()))
        if d:
            self._left_dir = Path(d)
            self.left_lbl.setText(str(self._left_dir))
            self.left_lbl.setObjectName("")
            self.left_lbl.setStyleSheet("color: inherit;")

    def _pick_right(self):
        """Pick the right folder to compare."""
        d = QFileDialog.getExistingDirectory(self, "Select Right Folder", str(Path.home()))
        if d:
            self._right_dir = Path(d)
            self.right_lbl.setText(str(self._right_dir))
            self.right_lbl.setObjectName("")
            self.right_lbl.setStyleSheet("color: inherit;")

    def _run_compare(self):
        """Compare the two folders and fill the diff table; enable sync."""
        if not self._left_dir or not self._right_dir:
            QMessageBox.warning(self, "Compare", "Please select both Left and Right folders first.")
            return

        from NexusExplorer.native.nexus_dir_diff import DirectoryDiffEngine, DiffStatus
        self._diff_list = DirectoryDiffEngine.compare_directories(
            self._left_dir,
            self._right_dir,
            compare_content_hash=self.deep_chk.isChecked(),
        )

        self.table.setRowCount(len(self._diff_list))
        for row, entry in enumerate(self._diff_list):
            self.table.setItem(row, 0, QTableWidgetItem(entry.relative_path))

            l_txt = fmt_bytes(entry.left_size) if entry.left_path else "—"
            r_txt = fmt_bytes(entry.right_size) if entry.right_path else "—"
            self.table.setItem(row, 1, QTableWidgetItem(l_txt))
            self.table.setItem(row, 3, QTableWidgetItem(r_txt))

            st_item = QTableWidgetItem(entry.status.value)
            if entry.status == DiffStatus.IDENTICAL:
                st_item.setForeground(Qt.GlobalColor.gray)
            elif entry.status in (DiffStatus.LEFT_ONLY, DiffStatus.RIGHT_ONLY):
                st_item.setForeground(Qt.GlobalColor.cyan)
            else:
                st_item.setForeground(Qt.GlobalColor.yellow)
            self.table.setItem(row, 2, st_item)

        self.sync_btn.setEnabled(len(self._diff_list) > 0)

    def _run_sync(self):
        """Confirm and execute the selected sync mode, then re-compare."""
        if not self._diff_list or not self._left_dir or not self._right_dir:
            return
        from NexusExplorer.native.nexus_dir_diff import DirectoryDiffEngine, SyncMode

        modes = [
            SyncMode.MIRROR_LEFT_TO_RIGHT,
            SyncMode.MIRROR_RIGHT_TO_LEFT,
            SyncMode.TWO_WAY_MERGE,
            SyncMode.UPDATE_NEWER,
        ]
        chosen_mode = modes[self.mode_combo.currentIndex()]

        confirm = QMessageBox.question(
            self,
            "Confirm Sync",
            f"Are you sure you want to perform '{chosen_mode.value}'?\nThis will modify files in the target directory.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        stats = DirectoryDiffEngine.execute_sync(self._diff_list, self._left_dir, self._right_dir, chosen_mode)
        QMessageBox.information(
            self,
            "Sync Complete",
            f"Synchronization finished:\n• Copied: {stats.copied}\n• Updated: {stats.updated}\n• Deleted: {stats.deleted}\n• Data: {fmt_bytes(stats.bytes_transferred)}",
        )
        self._run_compare()


# ===========================================================================
# 4. File Splitter & Joiner Page
# ===========================================================================

class FileSplitterPage(_Page):
    """File chunk splitter and reconstructor with SHA256 integrity check."""

    def __init__(self, win):
        """Build the Splitter/Joiner page with split and join tabs."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "File Splitter & Joiner",
            "Split large files into sequential chunk segments with checksum manifests or join them back.",
        ))

        tabs = QTabWidget()

        # --- Split Tab ---
        split_widget = QWidget()
        s_lay = QVBoxLayout(split_widget)

        s_form = QFormLayout()
        s_pick_row = QHBoxLayout()
        s_btn = QPushButton("Select File…")
        s_btn.setObjectName("Secondary")
        s_btn.clicked.connect(self._pick_split_src)
        self.s_path_lbl = QLabel("No file selected")
        self.s_path_lbl.setObjectName("Muted")
        s_pick_row.addWidget(s_btn)
        s_pick_row.addWidget(self.s_path_lbl, 1)
        s_form.addRow("Source File:", s_pick_row)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "10 MB",
            "50 MB",
            "100 MB",
            "700 MB (CD-R)",
            "3.99 GB (FAT32 Limit)",
            "4.37 GB (DVD Single Layer)",
        ])
        s_form.addRow("Chunk Size:", self.preset_combo)

        s_lay.addLayout(s_form)
        self.do_split_btn = QPushButton("Split File Now")
        self.do_split_btn.setObjectName("Primary")
        self.do_split_btn.setEnabled(False)
        self.do_split_btn.clicked.connect(self._execute_split)
        s_lay.addWidget(self.do_split_btn)
        s_lay.addStretch(1)
        tabs.addTab(split_widget, "Split File")

        # --- Join Tab ---
        join_widget = QWidget()
        j_lay = QVBoxLayout(join_widget)

        j_form = QFormLayout()
        j_pick_row = QHBoxLayout()
        j_btn = QPushButton("Select Part (.001 / .split.json)…")
        j_btn.setObjectName("Secondary")
        j_btn.clicked.connect(self._pick_join_src)
        self.j_path_lbl = QLabel("No part selected")
        self.j_path_lbl.setObjectName("Muted")
        j_pick_row.addWidget(j_btn)
        j_pick_row.addWidget(self.j_path_lbl, 1)
        j_form.addRow("Input Part:", j_pick_row)

        j_lay.addLayout(j_form)
        self.do_join_btn = QPushButton("Join Files Now")
        self.do_join_btn.setObjectName("Primary")
        self.do_join_btn.setEnabled(False)
        self.do_join_btn.clicked.connect(self._execute_join)
        j_lay.addWidget(self.do_join_btn)
        j_lay.addStretch(1)
        tabs.addTab(join_widget, "Join Files")

        self.v.addWidget(tabs)
        self._split_src: Optional[Path] = None
        self._join_src: Optional[Path] = None

    def _pick_split_src(self):
        """Pick the file to split and enable the split button."""
        f, _ = QFileDialog.getOpenFileName(self, "Select File to Split", str(Path.home()))
        if f:
            self._split_src = Path(f)
            self.s_path_lbl.setText(f"{self._split_src.name} ({fmt_bytes(self._split_src.stat().st_size)})")
            self.s_path_lbl.setObjectName("")
            self.s_path_lbl.setStyleSheet("color: inherit;")
            self.do_split_btn.setEnabled(True)

    def _execute_split(self):
        """Split the source file into preset-sized chunks with a manifest."""
        if not self._split_src:
            return
        from NexusExplorer.native.nexus_file_splitter import FileSplitterJoiner, SplitPreset, PRESET_BYTES

        presets = [
            SplitPreset.MB_10,
            SplitPreset.MB_50,
            SplitPreset.MB_100,
            SplitPreset.CD_700MB,
            SplitPreset.FAT32_4GB,
            SplitPreset.DVD_4_3GB,
        ]
        chunk_bytes = PRESET_BYTES[presets[self.preset_combo.currentIndex()]]

        res = FileSplitterJoiner.split_file(self._split_src, chunk_bytes)
        if res.success:
            QMessageBox.information(
                self,
                "Split Complete",
                f"File split into {len(res.parts_created)} chunk parts.\nManifest saved to:\n{res.manifest_path}",
            )
        else:
            QMessageBox.warning(self, "Split Failed", f"Error: {res.error}")

    def _pick_join_src(self):
        """Pick the first part or manifest to join and enable the join button."""
        f, _ = QFileDialog.getOpenFileName(self, "Select First Part or Manifest", str(Path.home()), "Split Parts (*.001 *.json);;All Files (*.*)")
        if f:
            self._join_src = Path(f)
            self.j_path_lbl.setText(self._join_src.name)
            self.j_path_lbl.setObjectName("")
            self.j_path_lbl.setStyleSheet("color: inherit;")
            self.do_join_btn.setEnabled(True)

    def _execute_join(self):
        """Reassemble the split parts into the original file."""
        if not self._join_src:
            return
        from NexusExplorer.native.nexus_file_splitter import FileSplitterJoiner
        res = FileSplitterJoiner.join_files(self._join_src)
        if res.success:
            ver_text = "Verified byte-for-byte with SHA-256" if res.hash_verified else "Assembled successfully"
            QMessageBox.information(
                self,
                "Join Complete",
                f"Reconstructed file: {Path(res.output_path).name}\nSize: {fmt_bytes(res.total_bytes)}\nStatus: {ver_text}",
            )
        else:
            QMessageBox.warning(self, "Join Failed", f"Error: {res.error}")


# ===========================================================================
# 5. Windows Restart Manager Process Unlocker Page
# ===========================================================================

class FileUnlockerPage(_Page):
    """File handle inspector and process unlocker."""

    def __init__(self, win):
        """Build the File Unlocker page with a picker, lock table, and per-process kill actions."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "File Unlocker & Handle Inspector",
            "Identify which processes hold open locks on files or folders and terminate them to release locks.",
        ))

        # Picker Card
        p_card = Card(self.p, "Card")
        p_lay = QHBoxLayout(p_card)
        pick_btn = QPushButton("Select Locked File…")
        pick_btn.setObjectName("Secondary")
        pick_btn.clicked.connect(self._pick_file)
        self.path_lbl = QLabel("No file selected")
        self.path_lbl.setObjectName("Muted")
        p_lay.addWidget(pick_btn)
        p_lay.addWidget(self.path_lbl, 1)
        self.scan_btn = QPushButton("Inspect Locks")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self._inspect_locks)
        p_lay.addWidget(self.scan_btn)
        self.v.addWidget(p_card)

        # Process Table
        table_card = Card(self.p, "Card")
        t_lay = QVBoxLayout(table_card)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["PID", "Process Name", "Executable Path", "Memory", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        t_lay.addWidget(self.table)
        self.add_scrolling_list(table_card, stretch=1)

        self._current_file: Optional[Path] = None
        self._locking_procs = []

    def _pick_file(self):
        """Pick the locked file and immediately inspect its locks."""
        f, _ = QFileDialog.getOpenFileName(self, "Select Locked File", str(Path.home()))
        if f:
            self._current_file = Path(f)
            self.path_lbl.setText(self._current_file.name)
            self.path_lbl.setObjectName("")
            self.path_lbl.setStyleSheet("color: inherit;")
            self.scan_btn.setEnabled(True)
            self._inspect_locks()

    def _inspect_locks(self):
        """List processes holding locks on the chosen file."""
        if not self._current_file:
            return
        from NexusExplorer.native.nexus_unlocker import FileUnlocker
        self._locking_procs = FileUnlocker.get_locking_processes(self._current_file)
        self.table.setRowCount(len(self._locking_procs))

        if not self._locking_procs:
            QMessageBox.information(self, "No Locks Found", "The file is not locked by any active process.")
            return

        for row, p in enumerate(self._locking_procs):
            self.table.setItem(row, 0, QTableWidgetItem(str(p.pid)))
            self.table.setItem(row, 1, QTableWidgetItem(p.name))
            self.table.setItem(row, 2, QTableWidgetItem(p.executable_path or "—"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{p.memory_mb} MB"))

            kill_btn = QPushButton("Kill Process")
            kill_btn.setObjectName("Danger")
            pid = p.pid
            kill_btn.clicked.connect(lambda _, pid=pid: self._terminate_proc(pid))
            self.table.setCellWidget(row, 4, kill_btn)

    def _terminate_proc(self, pid: int):
        """Force-terminate a locking process, then re-inspect locks."""
        from NexusExplorer.native.nexus_unlocker import FileUnlocker
        ok, msg = FileUnlocker.unlock_and_terminate(pid, force=True)
        if ok:
            QMessageBox.information(self, "Unlocked", msg)
        else:
            QMessageBox.warning(self, "Unlock Failed", msg)
        self._inspect_locks()


# ===========================================================================
# 6. NTFS Alternate Data Streams (ADS) & Zone.Identifier Manager Page
# ===========================================================================

class AdsManagerPage(_Page):
    """NTFS Alternate Data Stream inspector and Zone.Identifier unblocker."""

    def __init__(self, win):
        """Build the ADS Manager page with a file picker, unblock button, and streams table."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "NTFS Alternate Data Streams",
            "Enumerate hidden streams, strip Zone.Identifier 'Mark-of-the-Web' download blocks, and inspect stream contents.",
        ))

        p_card = Card(self.p, "Card")
        p_lay = QHBoxLayout(p_card)
        pick_btn = QPushButton("Select File…")
        pick_btn.setObjectName("Secondary")
        pick_btn.clicked.connect(self._pick_file)
        self.path_lbl = QLabel("No file selected")
        self.path_lbl.setObjectName("Muted")
        p_lay.addWidget(pick_btn)
        p_lay.addWidget(self.path_lbl, 1)
        self.unblock_btn = QPushButton("Unblock File (Remove Zone.Id)")
        self.unblock_btn.setObjectName("Primary")
        self.unblock_btn.setEnabled(False)
        self.unblock_btn.clicked.connect(self._unblock_file)
        p_lay.addWidget(self.unblock_btn)
        self.v.addWidget(p_card)

        # Streams Table
        table_card = Card(self.p, "Card")
        t_lay = QVBoxLayout(table_card)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Stream Name", "Type", "Size", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        t_lay.addWidget(self.table)
        self.add_scrolling_list(table_card, stretch=1)

        self._current_file: Optional[Path] = None

    def _pick_file(self):
        """Pick a file and list its alternate data streams."""
        f, _ = QFileDialog.getOpenFileName(self, "Select File with Streams", str(Path.home()))
        if f:
            self._current_file = Path(f)
            self.path_lbl.setText(self._current_file.name)
            self.path_lbl.setObjectName("")
            self.path_lbl.setStyleSheet("color: inherit;")
            self._refresh_streams()

    def _refresh_streams(self):
        """List the file's NTFS streams and enable unblocking when a Zone.Identifier exists."""
        if not self._current_file:
            return
        from NexusExplorer.native.nexus_ads_manager import AlternateDataStreamsManager
        streams = AlternateDataStreamsManager.list_streams(self._current_file)
        self.table.setRowCount(len(streams))
        has_zone_id = any(s.is_zone_identifier for s in streams)
        self.unblock_btn.setEnabled(has_zone_id)

        for row, s in enumerate(streams):
            self.table.setItem(row, 0, QTableWidgetItem(s.stream_name))
            self.table.setItem(row, 1, QTableWidgetItem(s.stream_type))
            self.table.setItem(row, 2, QTableWidgetItem(fmt_bytes(s.size_bytes)))

            del_btn = QPushButton("Delete Stream")
            del_btn.setObjectName("Danger")
            name = s.stream_name
            del_btn.clicked.connect(lambda _, n=name: self._delete_stream(n))
            self.table.setCellWidget(row, 3, del_btn)

    def _unblock_file(self):
        """Remove the Zone.Identifier stream to unblock the file."""
        if not self._current_file:
            return
        from NexusExplorer.native.nexus_ads_manager import AlternateDataStreamsManager
        ok, msg = AlternateDataStreamsManager.unblock_file(self._current_file)
        if ok:
            QMessageBox.information(self, "Unblocked", "Zone.Identifier stream removed. File is now unblocked.")
        else:
            QMessageBox.warning(self, "Error", msg)
        self._refresh_streams()

    def _delete_stream(self, stream_name: str):
        """Delete the named alternate data stream, then refresh."""
        if not self._current_file:
            return
        from NexusExplorer.native.nexus_ads_manager import AlternateDataStreamsManager
        ok, msg = AlternateDataStreamsManager.delete_stream(self._current_file, stream_name)
        if ok:
            QMessageBox.information(self, "Stream Deleted", msg)
        else:
            QMessageBox.warning(self, "Error", msg)
        self._refresh_streams()


# ===========================================================================
# 7. Windows Event Log Sweeper Page
# ===========================================================================

class EventLogCleanerPage(_Page):
    """Windows Event Log manager and cleaner."""

    def __init__(self, win):
        """Build the Event Log page with stat cards, log table, and refresh/clear actions."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Windows Event Log Sweeper",
            "Inspect and clean Windows Event Logs (Application, System, Security, PowerShell, Diagnostics).",
        ))

        # Stats Card
        stat_row = QHBoxLayout()
        self.stat_channels = StatCard(self.p, "0", "Log Channels")
        self.stat_records = StatCard(self.p, "0", "Total Records")
        self.stat_size = StatCard(self.p, "0 B", "Disk Usage")
        stat_row.addWidget(self.stat_channels)
        stat_row.addWidget(self.stat_records)
        stat_row.addWidget(self.stat_size)
        self.v.addLayout(stat_row)

        # Log Table
        table_card = Card(self.p, "Card")
        t_lay = QVBoxLayout(table_card)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Log Channel", "Records", "Size on Disk", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        t_lay.addWidget(self.table)
        self.add_scrolling_list(table_card, stretch=1)

        # Actions
        act_card = Card(self.p, "Card")
        a_lay = QHBoxLayout(act_card)
        self.refresh_btn = QPushButton("Refresh Logs")
        self.refresh_btn.setObjectName("Secondary")
        self.refresh_btn.clicked.connect(self._load_logs)
        a_lay.addWidget(self.refresh_btn)

        self.clean_all_btn = QPushButton("Clear All Event Logs")
        self.clean_all_btn.setObjectName("Danger")
        self.clean_all_btn.clicked.connect(self._clear_all_logs)
        a_lay.addWidget(self.clean_all_btn)
        a_lay.addStretch(1)
        self.v.addWidget(act_card)

        self._logs = []
        QTimer.singleShot(100, self._load_logs)

    def _load_logs(self):
        """Load all event log channels into the table and stat cards."""
        from cortex_unified.system_tools.event_log_cleaner import EventLogCleaner
        self._logs = EventLogCleaner.list_all_logs()

        self.table.setRowCount(len(self._logs))
        total_records = sum(l.record_count for l in self._logs)
        total_size = sum(l.size_bytes for l in self._logs)

        self.stat_channels.set_value(str(len(self._logs)))
        self.stat_records.set_value(f"{total_records:,}")
        self.stat_size.set_value(fmt_bytes(total_size))

        for row, log in enumerate(self._logs):
            self.table.setItem(row, 0, QTableWidgetItem(log.name))
            self.table.setItem(row, 1, QTableWidgetItem(f"{log.record_count:,}"))
            self.table.setItem(row, 2, QTableWidgetItem(fmt_bytes(log.size_bytes)))
            self.table.setItem(row, 3, QTableWidgetItem("Active" if log.is_enabled else "Disabled"))

    def _clear_all_logs(self):
        """Confirm and clear every event log channel, then reload."""
        confirm = QMessageBox.question(
            self,
            "Clear Event Logs",
            "Are you sure you want to clear Windows Event Logs? (Requires Administrator privileges).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        from cortex_unified.system_tools.event_log_cleaner import EventLogCleaner
        ok_count, freed, _ = EventLogCleaner.clear_all_logs()
        QMessageBox.information(self, "Logs Cleared", f"Cleared {ok_count} log channels.\nFreed: {fmt_bytes(freed)}")
        self._load_logs()


# ===========================================================================
# 8. Font & Icon Cache Rebuilder Page
# ===========================================================================

class SystemCacheRebuilderPage(_Page):
    """Font, Icon, and Thumbnail cache rebuilder and Shell restarter."""

    def __init__(self, win):
        """Build the Cache Rebuilder page with restart-shell option and rebuild button."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "System Cache & Icon Rebuilder",
            "Repair corrupted desktop icons, broken thumbnails, missing font glyphs, and reload Windows Explorer.",
        ))

        card = Card(self.p, "Card")
        c_lay = QVBoxLayout(card)

        desc = QLabel(
            "If your desktop icons display blank white sheets, thumbnail previews fail to load, "
            "or fonts render improperly, rebuilding the system caches will resolve the issue."
        )
        desc.setWordWrap(True)
        c_lay.addWidget(desc)

        self.restart_shell_chk = QCheckBox("Restart Windows Explorer immediately after rebuild")
        self.restart_shell_chk.setChecked(True)
        c_lay.addWidget(self.restart_shell_chk)

        self.rebuild_btn = QPushButton("Rebuild Font & Icon Caches Now")
        self.rebuild_btn.setObjectName("Primary")
        self.rebuild_btn.clicked.connect(self._execute_rebuild)
        c_lay.addWidget(self.rebuild_btn)

        self.v.addWidget(card)
        self.v.addStretch(1)

    def _execute_rebuild(self):
        """Rebuild font and icon caches and report the outcome."""
        from cortex_unified.system_tools.system_cache_rebuilder import SystemCacheRebuilder
        report = SystemCacheRebuilder.execute_full_cache_rebuild(restart_shell=self.restart_shell_chk.isChecked())
        QMessageBox.information(
            self,
            "Rebuild Complete",
            f"Cache rebuild finished:\n• Font Cache: {'Rebuilt' if report.font_cache_rebuilt else 'Skipped'}\n• Icon/Thumbnail Cache: {'Rebuilt' if report.icon_cache_rebuilt else 'Skipped'}\n• Cache Files Deleted: {report.files_deleted}\n• Freed: {fmt_bytes(report.bytes_freed)}",
        )


# ===========================================================================
# 9. Network Stack & DNS Optimizer Page
# ===========================================================================

class NetworkOptimizerPage(_Page):
    """DNS Resolver and TCP/IP stack tuning toolkit."""

    def __init__(self, win):
        """Build the Network Optimizer page with TCP status form, tuning buttons, and repair actions."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Network Stack & DNS Optimizer",
            "Flush DNS resolver cache, purge ARP tables, reset Winsock and TCP/IP stack, and optimize TCP autotuning.",
        ))

        # Status & Tuning Card
        card = Card(self.p, "Card")
        c_lay = QVBoxLayout(card)

        form = QFormLayout()
        self.autotuning_lbl = QLabel("Checking...")
        self.rss_lbl = QLabel("Checking...")
        self.ecn_lbl = QLabel("Checking...")
        form.addRow("TCP Auto-Tuning Level:", self.autotuning_lbl)
        form.addRow("Receive-Side Scaling (RSS):", self.rss_lbl)
        form.addRow("ECN Congestion Notification:", self.ecn_lbl)
        c_lay.addLayout(form)

        tune_row = QHBoxLayout()
        self.tune_normal_btn = QPushButton("Set TCP Normal (Default)")
        self.tune_normal_btn.setObjectName("Secondary")
        self.tune_normal_btn.clicked.connect(lambda: self._set_autotuning("normal"))
        self.tune_exp_btn = QPushButton("Set TCP Experimental (Gaming/High Throughput)")
        self.tune_exp_btn.setObjectName("Secondary")
        self.tune_exp_btn.clicked.connect(lambda: self._set_autotuning("experimental"))
        tune_row.addWidget(self.tune_normal_btn)
        tune_row.addWidget(self.tune_exp_btn)
        tune_row.addStretch(1)
        c_lay.addLayout(tune_row)

        self.v.addWidget(card)

        # 1-Click Reset Card
        reset_card = Card(self.p, "Card")
        r_lay = QVBoxLayout(reset_card)
        r_lay.addWidget(QLabel("<b>Network Repair Actions:</b>"))

        btn_grid = QHBoxLayout()
        dns_btn = QPushButton("Flush DNS Cache")
        dns_btn.setObjectName("Secondary")
        dns_btn.clicked.connect(self._flush_dns)
        btn_grid.addWidget(dns_btn)

        arp_btn = QPushButton("Clear ARP Cache")
        arp_btn.setObjectName("Secondary")
        arp_btn.clicked.connect(self._clear_arp)
        btn_grid.addWidget(arp_btn)

        winsock_btn = QPushButton("Reset Winsock")
        winsock_btn.setObjectName("Secondary")
        winsock_btn.clicked.connect(self._reset_winsock)
        btn_grid.addWidget(winsock_btn)

        repair_all_btn = QPushButton("Complete 1-Click Repair")
        repair_all_btn.setObjectName("Primary")
        repair_all_btn.clicked.connect(self._repair_all)
        btn_grid.addWidget(repair_all_btn)

        r_lay.addLayout(btn_grid)
        self.v.addWidget(reset_card)
        self.v.addStretch(1)

        QTimer.singleShot(100, self._load_tcp_status)

    def _load_tcp_status(self):
        """Show current TCP autotuning, RSS, and ECN status."""
        from cortex_unified.system_tools.network_stack_optimizer import NetworkStackOptimizer
        st = NetworkStackOptimizer.get_tcp_settings()
        self.autotuning_lbl.setText(st.autotuning_level)
        self.rss_lbl.setText(st.receive_side_scaling)
        self.ecn_lbl.setText(st.ecn_capability)

    def _set_autotuning(self, level: str):
        """Set the TCP autotuning level, then refresh status."""
        from cortex_unified.system_tools.network_stack_optimizer import NetworkStackOptimizer
        ok, msg = NetworkStackOptimizer.set_tcp_autotuning(level)
        QMessageBox.information(self, "TCP Auto-Tuning", msg)
        self._load_tcp_status()

    def _flush_dns(self):
        """Flush the DNS resolver cache and report."""
        from cortex_unified.system_tools.network_stack_optimizer import NetworkStackOptimizer
        ok, msg = NetworkStackOptimizer.flush_dns()
        QMessageBox.information(self, "DNS", msg)

    def _clear_arp(self):
        """Clear the ARP cache and report."""
        from cortex_unified.system_tools.network_stack_optimizer import NetworkStackOptimizer
        ok, msg = NetworkStackOptimizer.clear_arp_cache()
        QMessageBox.information(self, "ARP", msg)

    def _reset_winsock(self):
        """Reset the Winsock catalog and report."""
        from cortex_unified.system_tools.network_stack_optimizer import NetworkStackOptimizer
        ok, msg = NetworkStackOptimizer.reset_winsock()
        QMessageBox.information(self, "Winsock", msg)

    def _repair_all(self):
        """Run the complete network repair sequence, then refresh status."""
        from cortex_unified.system_tools.network_stack_optimizer import NetworkStackOptimizer
        report = NetworkStackOptimizer.execute_complete_network_repair()
        QMessageBox.information(self, "Network Repair", "\n".join(report.output_messages))
        self._load_tcp_status()


# ===========================================================================
# 10. Windows Crash Dump & WER Cleaner Page
# ===========================================================================

class CrashDumpCleanerPage(_Page):
    """Windows Kernel & User Memory Dump and WER Sanitizer."""

    def __init__(self, win):
        """Build the Crash Dump page with stat cards, dumps table, and scan/clean actions."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Crash Dumps & Error Reports",
            "Sanitize stale Windows Kernel Memory Dumps (MEMORY.DMP), Minidumps, and Windows Error Reporting (WER) logs.",
        ))

        # Stats Card
        stat_row = QHBoxLayout()
        self.stat_count = StatCard(self.p, "0", "Dump Files")
        self.stat_size = StatCard(self.p, "0 B", "Reclaimable")
        stat_row.addWidget(self.stat_count)
        stat_row.addWidget(self.stat_size)
        self.v.addLayout(stat_row)

        # Dumps Table
        table_card = Card(self.p, "Card")
        t_lay = QVBoxLayout(table_card)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Filename", "Category", "Size"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        t_lay.addWidget(self.table)
        self.add_scrolling_list(table_card, stretch=1)

        # Action Card
        act_card = Card(self.p, "Card")
        a_lay = QHBoxLayout(act_card)
        self.scan_btn = QPushButton("Scan Crash Dumps")
        self.scan_btn.setObjectName("Secondary")
        self.scan_btn.clicked.connect(self._scan_dumps)
        a_lay.addWidget(self.scan_btn)

        self.clean_btn = QPushButton("Clean All Crash Dumps")
        self.clean_btn.setObjectName("Danger")
        self.clean_btn.setEnabled(False)
        self.clean_btn.clicked.connect(self._clean_dumps)
        a_lay.addWidget(self.clean_btn)
        a_lay.addStretch(1)
        self.v.addWidget(act_card)

        self._dumps = []
        QTimer.singleShot(100, self._scan_dumps)

    def _scan_dumps(self):
        """Scan crash dumps and WER reports, updating table and stat cards."""
        from cortex_unified.system_tools.crash_dump_cleaner import CrashDumpCleaner
        self._dumps = CrashDumpCleaner.scan_dumps()

        self.table.setRowCount(len(self._dumps))
        total_size = sum(d.size_bytes for d in self._dumps)

        self.stat_count.set_value(str(len(self._dumps)))
        self.stat_size.set_value(fmt_bytes(total_size))
        self.clean_btn.setEnabled(len(self._dumps) > 0)

        for row, d in enumerate(self._dumps):
            self.table.setItem(row, 0, QTableWidgetItem(d.filename))
            self.table.setItem(row, 1, QTableWidgetItem(d.category))
            self.table.setItem(row, 2, QTableWidgetItem(fmt_bytes(d.size_bytes)))

    def _clean_dumps(self):
        """Delete all discovered crash dumps, then rescan."""
        if not self._dumps:
            return
        from cortex_unified.system_tools.crash_dump_cleaner import CrashDumpCleaner
        report = CrashDumpCleaner.clean_dumps(self._dumps)
        QMessageBox.information(
            self,
            "Clean Complete",
            f"Removed {report.files_deleted} crash dump file(s).\nReclaimed: {fmt_bytes(report.bytes_freed)}",
        )
        self._scan_dumps()
