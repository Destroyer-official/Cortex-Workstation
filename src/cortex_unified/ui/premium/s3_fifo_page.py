"""S3-FIFO cache policy demo – FIFO queues are all you need (SOSP'23).

Research: Yang et al., SOSP'23 – three static FIFO queues (Small 10 %,
Main 90 %, Ghost) with 2-bit frequency, quick demotion of one-hit wonders,
6× throughput over LRU. This page visualises the policy and lets the user
benchmark it on a synthetic trace, complementing the cleaner’s own cache
management.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
)

from .states import StatePanel
from .widgets import title_block
from .window import _Page


class _BenchWorker(QObject):
    """Benchworker.

    Manages BenchWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, capacity: int, trace_len: int = 5000):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            capacity (int): The capacity parameter.
            trace_len (int): The trace len parameter.
        """
        super().__init__()
        self._cap = capacity
        self._n = trace_len

    def run(self):
        """run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.s3_fifo import S3FIFO
            import random

            rnd = random.Random(0xC0FFEE)
            # Zipf-like trace: 80 % of requests hit 20 % of keys
            hot = [f"hot{i}" for i in range(20)]
            cold = [f"cold{i}" for i in range(200)]
            trace = [
                rnd.choice(hot) if rnd.random() < 0.8 else rnd.choice(cold)
                for _ in range(self._n)
            ]
            cache = S3FIFO(capacity=self._cap)
            for k in trace:
                if cache.get(k) is None:
                    cache.put(k, k)
            stats = cache.stats()
            # Compare with simple LRU simulation (OrderedDict)
            from collections import OrderedDict

            lru: OrderedDict[str, str] = OrderedDict()
            hits = 0
            for k in trace:
                if k in lru:
                    lru.move_to_end(k)
                    hits += 1
                else:
                    lru[k] = k
                    if len(lru) > self._cap:
                        lru.popitem(last=False)
            stats["lru_hits"] = hits
            stats["lru_hit_ratio"] = hits / len(trace) if trace else 0
            stats["trace_len"] = len(trace)
            self.finished.emit(stats)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class S3FifoPage(_Page):
    """S3fifopage.

    Manages S3FifoPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "S3-FIFO Cache (SOSP'23)",
            "FIFO Queues Are All You Need – three static FIFO queues (Small 10 % + "
            "Main 90 % + Ghost) with 2-bit frequency and quick demotion. This demo "
            "benchmarks the policy on a synthetic Zipf trace versus LRU.",
        ))

        picker = QHBoxLayout()
        picker.addWidget(QLabel("Capacity:"))
        self.cap_spin = QSpinBox()
        self.cap_spin.setRange(10, 10000)
        self.cap_spin.setValue(256)
        self.cap_spin.setSingleStep(10)
        picker.addWidget(self.cap_spin)
        self.run_btn = QPushButton("Run Benchmark")
        self.run_btn.setObjectName("Primary")
        self.run_btn.clicked.connect(self._run)
        picker.addWidget(self.run_btn)
        picker.addStretch(1)
        self.v.addLayout(picker)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.v.addWidget(self.status)

        self.tbl = QTableWidget(0, 2)
        self.tbl.setHorizontalHeaderLabels(["Metric", "Value"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        note = QLabel(
            "S3-FIFO is the policy backing the cleaner’s model/HF cache management. "
            "Quick demotion evicts one-hit wonders early; Ghost remembers S-evicted "
            "keys so a second access promotes directly to Main."
        )
        note.setObjectName("Muted")
        note.setWordWrap(True)
        self.v.addWidget(note)

    def _run(self):
        """Run.

        Manages run operations and coordinates related state changes for the component.
        """
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Benchmarking S3-FIFO vs LRU…")
        w = _BenchWorker(capacity=int(self.cap_spin.value()))
        self.win.run_worker(w, self._on_done, self._fail)

    def _on_done(self, stats: dict):
        """_on_done.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            stats (dict): The stats parameter.
        """
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        self.state.clear()
        rows = [
            ("Trace length", str(stats.get("trace_len", ""))),
            ("S3-FIFO hit ratio", f"{stats.get('hit_ratio', 0):.2%}"),
            ("S3-FIFO hits", str(stats.get("hits", ""))),
            ("S3-FIFO misses", str(stats.get("misses", ""))),
            ("Ghost hits (promotions)", str(stats.get("ghost_hits", ""))),
            ("Evictions", str(stats.get("evictions", ""))),
            ("Small→Main", str(stats.get("small_to_main", ""))),
            ("Small→Ghost", str(stats.get("small_to_ghost", ""))),
            ("Main reinsertions", str(stats.get("main_reinsertions", ""))),
            ("LRU hit ratio", f"{stats.get('lru_hit_ratio', 0):.2%}"),
            ("LRU hits", str(stats.get("lru_hits", ""))),
        ]
        self.tbl.setRowCount(len(rows))
        for r, (k, v) in enumerate(rows):
            self.tbl.setItem(r, 0, QTableWidgetItem(k))
            self.tbl.setItem(r, 1, QTableWidgetItem(v))
        better = stats.get("hit_ratio", 0) > stats.get("lru_hit_ratio", 0)
        self.status.setText(
            "S3-FIFO beats LRU on this trace" if better else "LRU slightly ahead on this trace"
        )
        self.win.statusBar().showMessage("S3-FIFO benchmark complete", 5000)

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._run)
