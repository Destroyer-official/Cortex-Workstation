"""WSL Cleaner page: list distros + compact ext4.vhdx.

Surfaces the 1.37GB AppData\\Local\\wsl hit that Storage Sense never showed:
each WSL2 distro owns an ext4.vhdx that only shrinks after
``wsl --shutdown`` + diskpart compact. Uses the new
:class:`WslCleaner` + :class:`VhdxManager` path.

Read-only until the user explicitly confirms shutdown/compact.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .states import StatePanel
from .widgets import Card, title_block, status_note
from .window import _Page, fmt_bytes

IS_WINDOWS = sys.platform == "win32"


class _WslListWorker(QObject):
    """_WslListWorker class."""
    finished = Signal(list)
    failed = Signal(str)
    def run(self):
        """run."""
        try:
            from cortex_unified.system_tools.wsl_cleaner import WslCleaner
            self.finished.emit([d for d in WslCleaner().list_distros()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _WslShutdownWorker(QObject):
    """_WslShutdownWorker class."""
    finished = Signal(bool, str)
    failed = Signal(str)
    def run(self):
        """run."""
        try:
            from cortex_unified.system_tools.wsl_cleaner import WslCleaner
            ok, msg = WslCleaner().shutdown()
            self.finished.emit(ok, msg)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class WslPage(_Page):
    """List WSL distros, show ext4.vhdx sizes, shutdown + compact."""

    def __init__(self, win):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "WSL Cleaner",
            "WSL2 distros keep an ext4.vhdx that never shrinks on its own "
            "(1.37GB hit). Stop WSL, then compact the disk — Windows will "
            "return the freed blocks to the host."
        ))
        if not IS_WINDOWS:
            self.v.addWidget(status_note(self.p, "info", "WSL is only available on Windows."))
            self.v.addStretch(1)
            return

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("List Distros")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.shutdown_btn = QPushButton("Stop WSL (wsl --shutdown)")
        self.shutdown_btn.setToolTip("Stops all distros + Docker WSL backend so disks can be compacted.")
        self.shutdown_btn.clicked.connect(self._shutdown)
        row.addWidget(self.shutdown_btn)
        self.compact_btn = QPushButton("Compact Selected")
        self.compact_btn.setObjectName("Primary")
        self.compact_btn.setEnabled(False)
        self.compact_btn.clicked.connect(self._compact)
        row.addWidget(self.compact_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.info = QLabel("No data yet.")
        self.info.setObjectName("Muted")
        self.info.setWordWrap(True)
        self.v.addWidget(self.info)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["Distro", "State", "Path", "Size (on disk)", "Size (logical)"])
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.itemSelectionChanged.connect(lambda: self.compact_btn.setEnabled(bool(self.tbl.selectedIndexes())))
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._autoload = self._load
        self._loaded = False

    def _load(self):
        """_load."""
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Listing WSL distros…")
        from cortex_unified.system_tools.wsl_cleaner import WslCleaner
        if not WslCleaner().is_wsl_available():
            self.refresh_btn.setEnabled(True)
            self.state.show_empty("WSL not installed on this PC (no distros found).")
            self.info.setText("WSL is not installed, or no distro has been created yet.")
            return
        self.win.run_worker(_WslListWorker(), self._on_list, self._fail)

    def _on_list(self, distros):
        """_on_list."""
        self.refresh_btn.setEnabled(True)
        if not distros:
            self.state.show_empty("No WSL distros found.")
            self.info.setText("No WSL distros detected (try wsl --list --verbose in a terminal).")
        else:
            self.state.clear()
            total = sum(getattr(d, "vhdx_on_disk_bytes", 0) for d in distros)
            total_logical = sum(getattr(d, "vhdx_bytes", 0) for d in distros)
            self.info.setText(f"{len(distros)} distro(s), {fmt_bytes(total)} on disk ({fmt_bytes(total_logical)} logical). "
                              "Stop WSL before compacting - compacting an attached disk risks corruption.")
        self.tbl.setRowCount(len(distros))
        for r, d in enumerate(distros):
            # d may be WslDistro or already dict from test
            if isinstance(d, dict):
                name = d.get("name", "?")
                state = d.get("state", "?")
                path = d.get("vhdx_path") or "—"
                ondisk = d.get("vhdx_on_disk_bytes", 0)
                logical = d.get("vhdx_bytes", 0)
            else:
                name = getattr(d, "name", "?")
                state = getattr(d, "state", "?")
                path = str(getattr(d, "vhdx_path", "—") or "—")
                ondisk = getattr(d, "vhdx_on_disk_bytes", 0)
                logical = getattr(d, "vhdx_bytes", 0)
            self.tbl.setItem(r, 0, QTableWidgetItem(str(name)))
            self.tbl.setItem(r, 1, QTableWidgetItem(str(state)))
            p_item = QTableWidgetItem(str(path))
            p_item.setToolTip(str(path))
            self.tbl.setItem(r, 2, p_item)
            self.tbl.setItem(r, 3, QTableWidgetItem(fmt_bytes(ondisk) if ondisk else "—"))
            self.tbl.setItem(r, 4, QTableWidgetItem(fmt_bytes(logical) if logical else "—"))

    def _shutdown(self):
        """_shutdown."""
        confirm = QMessageBox.question(
            self, "Stop WSL?",
            "This stops ALL WSL distros and Docker Desktop's WSL backend.\n\n"
            "Unsaved work inside a distro will be lost (like a hard stop). Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.shutdown_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.statusBar().showMessage("Stopping WSL…")
        self.win.run_worker(_WslShutdownWorker(), self._on_shutdown, self._fail)

    def _on_shutdown(self, ok: bool, msg: str):
        """_on_shutdown."""
        self.shutdown_btn.setEnabled(True)
        self.progress.setVisible(False)
        if ok:
            QMessageBox.information(self, "WSL stopped", msg)
        else:
            QMessageBox.warning(self, "WSL shutdown", msg)
        self.win.statusBar().showMessage(msg, 5000)
        self._load()

    def _compact(self):
        """_compact."""
        sel = self.tbl.selectedIndexes()
        if not sel:
            return
        rows = sorted({i.row() for i in sel})
        paths = []
        for r in rows:
            item = self.tbl.item(r, 2)
            if item and item.text() and item.text() != "—":
                p = Path(item.text())
                if p.exists():
                    paths.append(p)
        if not paths:
            QMessageBox.information(self, "No disk", "Selected distro has no ext4.vhdx file.")
            return
        names = ", ".join(p.name for p in paths)
        confirm = QMessageBox.question(
            self, "Compact vhdx?",
            f"Compact {len(paths)} disk(s): {names}\n\n"
            "This compacts the virtual disk read-only (diskpart). "
            "It can take several minutes for large disks. Proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.compact_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.statusBar().showMessage(f"Compacting {names}…")
        # Reuse VhdxCompactWorker via inline worker
        from PySide6.QtCore import QObject as _QO, Signal as _Sig

        class _Compact(QObject):
            """_Compact class."""
            finished = Signal(list)
            failed = Signal(str)
            def __init__(self, paths):
                """__init__."""
                super().__init__()
                self._paths = paths
            def run(self):
                """run."""
                try:
                    from cortex_unified.system_tools.wsl_cleaner import WslCleaner
                    results = []
                    for vp in self._paths:
                        results.append(WslCleaner().compact_vhdx(vp))
                    self.finished.emit(results)
                except Exception as exc:  # noqa: BLE001
                    self.failed.emit(str(exc))
        w = _Compact(paths)
        self.win.run_worker(w, self._on_compact, self._fail)

    def _on_compact(self, results):
        """_on_compact."""
        self.compact_btn.setEnabled(True)
        self.progress.setVisible(False)
        if not results:
            return
        freed = sum(r.get("freed_bytes", 0) for r in results)
        ok = sum(1 for r in results if r.get("success"))
        msgs = "\n".join(f"{Path(r.get('detail','')).name or 'disk'}: {r.get('message','')}" for r in results)
        QMessageBox.information(self, "Compaction done",
                                f"Compacted {ok}/{len(results)} disk(s), freed {fmt_bytes(freed)}.\n\n{msgs}")
        self.win.statusBar().showMessage(f"Compacted {ok}/{len(results)}, freed {fmt_bytes(freed)}", 6000)
        self._load()

    def _fail(self, msg: str):
        """_fail."""
        self.refresh_btn.setEnabled(True)
        self.shutdown_btn.setEnabled(True)
        self.compact_btn.setEnabled(bool(self.tbl.selectedIndexes()))
        self.progress.setVisible(False)
        self.state.show_error(msg, on_retry=self._load)
