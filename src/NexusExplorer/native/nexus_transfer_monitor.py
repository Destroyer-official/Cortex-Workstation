"""Transfer Monitor — non-modal window showing the live transfer queue.

Per job: kind badge, source → destination, progress bar, percent,
speed, ETA, current file, and Pause/Resume/Cancel controls.
Opens automatically when a job is enqueued; can be reopened from the
toolbar/status button at any time.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from nexus_transfer_queue import JobState, TransferQueue, fmt_eta, human_bytes
from nexus_icons import action_icon as _fluent_action

log = logging.getLogger("nexus.transfer.monitor")

_KIND_BADGE = {"copy": "COPY", "move": "MOVE", "delete": "DELETE"}


class _JobRow(QWidget):
    """Jobrow.

    Manages JobRow operations and coordinates related state changes for the component.
    """

    def __init__(self, job_id: str, queue: TransferQueue, parent=None):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            job_id (str): The job id parameter.
            queue (TransferQueue): The queue parameter.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.job_id = job_id
        self.queue = queue
        job = queue.get_job(job_id)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(4)

        top = QHBoxLayout()
        kind = (job.kind if job else "job").upper()
        _kind_icon = {"COPY": "copy", "MOVE": "transfer", "DELETE": "delete"}.get(kind, "transfer")
        self.badge = QLabel(kind)
        self.badge.setObjectName("TransferBadge")
        self.badge.setFixedWidth(64)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_icon = _fluent_action(_kind_icon, size=14)
        if not badge_icon.isNull():
            self.badge.setPixmap(badge_icon.pixmap(14, 14))
            self.badge.setText("")
        top.addWidget(self.badge)

        self.title = QLabel(self._describe(job))
        self.title.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        f = self.title.font()
        f.setBold(True)
        self.title.setFont(f)
        top.addWidget(self.title, 1)

        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setIcon(_fluent_action("expand_down", size=14))
        self.btn_pause.setFixedWidth(72)
        self.btn_pause.clicked.connect(self._toggle_pause)
        top.addWidget(self.btn_pause)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setIcon(_fluent_action("close", size=14))
        self.btn_cancel.setFixedWidth(72)
        self.btn_cancel.clicked.connect(self._cancel)
        top.addWidget(self.btn_cancel)
        root.addLayout(top)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(job.progress if job else 0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(10)
        root.addWidget(self.bar)

        self.detail = QLabel("")
        self.detail.setStyleSheet("color:#8b949e;")
        root.addWidget(self.detail)

        self._last_progress = job.progress if job else -1
        self._last_file = job.current_file if job else ""

        self._refresh(job)

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _describe(job) -> str:
        """Describe.

        Manages describe operations and coordinates related state changes for the component.

        Args:
            job: The job parameter.

        Returns:
            str: Formatted string or path.
        """
        if job is None:
            return "Transfer"
        if job.kind == "delete":
            n = len(job.sources)
            first = Path(job.sources[0]).name if job.sources else ""
            return f"Deleting {n} item(s)" + (f"  ·  {first}…" if n == 1 else "")
        src = Path(job.sources[0]).name if job.sources else "?"
        more = f"  +{len(job.sources) - 1} more" if len(job.sources) > 1 else ""
        return f"{src}{more}   →   {Path(job.dest).name or job.dest}"

    def _refresh(self, job):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.

        Args:
            job: The job parameter.
        """
        if job is None:
            return
        new_progress = job.progress
        if new_progress != self._last_progress:
            self.bar.setValue(new_progress)
            self._last_progress = new_progress
        bits = [f"{new_progress}%"]
        if job.speed_bps > 0 and job.state is JobState.RUNNING:
            bits.append(f"{human_bytes(job.speed_bps)}/s")
        if job.eta_secs > 0 and job.state is JobState.RUNNING:
            bits.append(f"ETA {fmt_eta(job.eta_secs)}")
        if job.current_file:
            bits.append(job.current_file)
        if job.state is JobState.PAUSED:
            bits.append("PAUSED")
        elif job.state is JobState.COMPLETED:
            bits.append("Completed")
        elif job.state is JobState.FAILED:
            bits.append(f"Failed: {job.error[:120]}")
        elif job.state is JobState.CANCELLED:
            bits.append("Cancelled")
        self.detail.setText("   ·   ".join(bits))

        running = job.state is JobState.RUNNING
        paused = job.state is JobState.PAUSED
        if paused:
            self.btn_pause.setText("Resume")
            self.btn_pause.setIcon(_fluent_action("expand_right", size=14))
        else:
            self.btn_pause.setText("Pause")
            self.btn_pause.setIcon(_fluent_action("expand_down", size=14))
        self.btn_pause.setEnabled(running or paused)
        self.btn_cancel.setEnabled(job.state in (
            JobState.QUEUED, JobState.RUNNING, JobState.PAUSED))
        if job.state in (JobState.COMPLETED, JobState.CANCELLED):
            self.bar.setStyleSheet("")
            self.btn_pause.hide()
            self.btn_cancel.hide()
        if job.state is JobState.FAILED:
            self.badge.setStyleSheet(
                "color:#f85149; font-weight:700;")

    # ------------------------------------------------------------ handlers
    def _toggle_pause(self):
        """_toggle_pause.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        job = self.queue.get_job(self.job_id)
        if job is None:
            return
        if job.state is JobState.RUNNING:
            self.queue.pause(self.job_id)
        elif job.state is JobState.PAUSED:
            self.queue.resume(self.job_id)
        self._refresh(self.queue.get_job(self.job_id))

    def _cancel(self):
        """Cancel.

        Manages cancel operations and coordinates related state changes for the component.
        """
        self.queue.cancel(self.job_id)
        self._refresh(self.queue.get_job(self.job_id))


class TransferMonitorDialog(QDialog):
    """Transfermonitordialog.

    Manages TransferMonitorDialog operations and coordinates related state changes for the component.
    """

    def __init__(self, queue: TransferQueue, parent=None):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            queue (TransferQueue): The queue parameter.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.setWindowTitle("Nexus Transfers")
        self.setModal(False)
        self.setMinimumSize(560, 220)
        self.resize(640, 320)

        self._queue = queue
        self._rows: dict[str, _JobRow] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(self.scroll, 1)

        holder = QWidget()
        self.list_lay = QVBoxLayout(holder)
        self.list_lay.setContentsMargins(4, 4, 4, 4)
        self.list_lay.setSpacing(6)
        self.list_lay.addStretch(1)
        self.scroll.setWidget(holder)

        bottom = QHBoxLayout()
        self.summary = QLabel("No active transfers")
        self.summary.setStyleSheet("color:#8b949e;")
        bottom.addWidget(self.summary, 1)
        btn_clear = QPushButton("Clear finished")
        btn_clear.setIcon(_fluent_action("delete", size=14))
        btn_clear.clicked.connect(self._clear_finished)
        bottom.addWidget(btn_clear)
        btn_close = QPushButton("Close")
        btn_close.setIcon(_fluent_action("close", size=14))
        btn_close.clicked.connect(self.hide)
        bottom.addWidget(btn_close)
        outer.addLayout(bottom)

        queue.job_added.connect(self._on_job_added)
        queue.job_progress.connect(self._on_progress)
        queue.job_completed.connect(self._on_progress)
        queue.job_cancelled.connect(self._on_progress)
        queue.job_started.connect(self._on_job_added)

        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ------------------------------------------------------------- slots
    def _on_job_added(self, job_id: str):
        """_on_job_added.

        Manages on job added operations and coordinates related state changes for the component.

        Args:
            job_id (str): The job id parameter.
        """
        if job_id in self._rows:
            return
        row = _JobRow(job_id, self._queue)
        self._rows[job_id] = row
        self.list_lay.insertWidget(self.list_lay.count() - 1, row)
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_progress(self, job_id: str, *_a):
        """_on_progress.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            job_id (str): The job id parameter.
        """
        row = self._rows.get(job_id)
        if row is not None:
            row._refresh(self._queue.get_job(job_id))
        self._update_summary()

    def _tick(self):
        """Handle recurring timer events for real-time metric updates.

        Samples live system performance statistics, advances animation counters, and updates graphical meters.
        """
        for jid, row in list(self._rows.items()):
            job = self._queue.get_job(jid)
            if job is not None and job.state is JobState.RUNNING:
                row._refresh(job)
        self._update_summary()

    def _update_summary(self):
        """_update_summary.

        Manages update summary operations and coordinates related state changes for the component.
        """
        jobs = self._queue.get_all_jobs()
        active = [j for j in jobs if j.state in (
            JobState.QUEUED, JobState.RUNNING, JobState.PAUSED)]
        done = [j for j in jobs if j.state is JobState.COMPLETED]
        if active:
            agg = sum(j.progress for j in active) / len(active)
            self.summary.setText(
                f"{len(active)} active  ·  {agg:.0f}% overall  ·  "
                f"{len(done)} completed")
        elif jobs:
            self.summary.setText(f"{len(done)} completed  ·  queue idle")
        else:
            self.summary.setText("No active transfers")

    def _clear_finished(self):
        """_clear_finished.

        Manages clear finished operations and coordinates related state changes for the component.
        """
        n = self._queue.clear_finished()
        for jid, row in list(self._rows.items()):
            job = self._queue.get_job(jid)
            if job is None:
                row.setParent(None)
                row.deleteLater()
                self._rows.pop(jid, None)
        log.debug("cleared %d finished jobs", n)

    def open_for(self) -> None:
        """open_for.

        Manages open for operations and coordinates related state changes for the component.
        """
        self.show()
        self.raise_()
        self.activateWindow()

    def cleanup(self) -> None:
        """Stop timers and release all row widgets.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.
        """
        self._timer.stop()
        for row in self._rows.values():
            row.setParent(None)
            row.deleteLater()
        self._rows.clear()

    def closeEvent(self, event) -> None:
        """Handle the window or widget close event.

        Performs graceful shutdown, releases active workers and system hooks, persists window geometry, and accepts the close event.

        Args:
            event: The Qt event object.
        """
        self.cleanup()
        super().closeEvent(event)
