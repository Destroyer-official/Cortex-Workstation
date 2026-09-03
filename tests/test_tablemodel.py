"""Contracts for the model/view table foundation.

The data-dense tables were all ``QTableWidget``, which allocates a
``QTableWidgetItem`` per cell for every row whether or not it is visible.
Measured in this codebase: a Task Manager tick rebuilt ~500 rows x 8 columns
every 2 seconds, and the Secrets Scanner had no row cap at all.

Two properties matter and are pinned here:

1. **Virtualisation** - the model must supply only what the view paints.
2. **Typed sorting** - item tables compare display strings, which is why
   ``"9 MB"`` sorted above ``"10 MB"``. Sorting must use the real value.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QTableView  # noqa: E402

from cortex_unified.ui.premium.tablemodel import (  # noqa: E402
    RECORD_ROLE,
    SORT_ROLE,
    Column,
    RecordTableModel,
    bind_table,
)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _records(count=6):
    return [
        {"pid": pid, "name": f"proc{pid}", "rss": pid * 1_048_576, "cpu": pid / 2}
        for pid in (9, 10, 2, 100, 33, 1)[:count]
    ]


def _columns():
    return [
        Column("PID", "pid", sort_key=lambda r: r["pid"]),
        Column("Name", "name", stretch=True),
        Column(
            "Memory",
            lambda r: f"{r['rss'] / 1_048_576:.1f} MB",
            sort_key=lambda r: r["rss"],
            searchable=False,
        ),
    ]


@pytest.fixture
def binding(app):
    view = QTableView()
    bound = bind_table(
        view, _columns(), sort_column=0, sort_order=Qt.SortOrder.AscendingOrder
    )
    bound.set_records(_records())
    return bound


# --- shape and content -----------------------------------------------------


def test_model_reports_shape_from_records_and_columns(binding):
    assert binding.proxy.rowCount() == 6
    assert binding.proxy.columnCount() == 3
    model = binding.model
    assert (
        model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        == "PID"
    )


def test_display_supports_field_names_and_callables(binding):
    model = binding.model
    row = 0
    assert model.data(model.index(row, 0), Qt.ItemDataRole.DisplayRole) == "9"
    assert model.data(model.index(row, 1), Qt.ItemDataRole.DisplayRole) == "proc9"
    assert model.data(model.index(row, 2), Qt.ItemDataRole.DisplayRole) == "9.0 MB"


def test_missing_field_renders_empty_not_none(app):
    model = RecordTableModel([Column("Nope", "absent")])
    model.set_records([{"present": 1}])
    assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == ""


def test_cells_are_read_only(binding):
    flags = binding.model.flags(binding.model.index(0, 0))
    assert not (flags & Qt.ItemFlag.ItemIsEditable)
    assert flags & Qt.ItemFlag.ItemIsSelectable


# --- the sorting bug this replaces -----------------------------------------


def test_sorting_uses_the_typed_key_not_the_display_string(binding):
    """``"9.0 MB"`` must not sort above ``"100.0 MB"``."""
    binding.view.sortByColumn(2, Qt.SortOrder.DescendingOrder)
    proxy = binding.proxy
    order = [proxy.data(proxy.index(r, 0)) for r in range(proxy.rowCount())]
    assert order == ["100", "33", "10", "9", "2", "1"]
    # A display-string sort would have produced 9 before 100.
    assert order[0] == "100"


def test_sort_role_exposes_the_raw_value(binding):
    model = binding.model
    raw = model.data(model.index(0, 2), SORT_ROLE)
    assert isinstance(raw, int) and raw == 9 * 1_048_576


# --- filtering -------------------------------------------------------------


def test_filter_matches_searchable_columns_only(binding):
    binding.set_filter_text("proc1")
    visible = {
        binding.proxy.data(binding.proxy.index(r, 1))
        for r in range(binding.proxy.rowCount())
    }
    assert visible == {"proc1", "proc10", "proc100"}
    # Memory is searchable=False, so its digits must not match.
    binding.set_filter_text("MB")
    assert binding.proxy.rowCount() == 0


def test_filter_is_case_insensitive_and_clearable(binding):
    binding.set_filter_text("PROC2")
    assert binding.proxy.rowCount() == 1
    binding.set_filter_text("")
    assert binding.proxy.rowCount() == 6


def test_filtering_does_not_discard_the_records(binding):
    binding.set_filter_text("nothing-matches-this")
    assert binding.proxy.rowCount() == 0
    assert len(binding.model.records) == 6, "source data must be preserved"


# --- selection safety ------------------------------------------------------


def test_selected_record_is_correct_under_sorting(binding):
    """The bug this design prevents: indexing a list by the view's row."""
    binding.view.sortByColumn(0, Qt.SortOrder.DescendingOrder)
    binding.view.selectRow(0)
    record = binding.selected_record()
    assert record is not None
    # Row 0 under PID-descending is pid 100, not the first record supplied.
    assert record["pid"] == 100
    assert binding.model.records[0]["pid"] == 9


def test_selected_record_is_none_without_selection(binding):
    binding.view.clearSelection()
    assert binding.selected_record() is None


def test_select_where_reselects_by_identity(binding):
    assert binding.select_where(lambda r: r["pid"] == 33)
    assert binding.selected_record()["pid"] == 33
    # Survives a records swap, which is how a live refresh keeps its selection.
    binding.set_records(list(reversed(_records())))
    assert binding.select_where(lambda r: r["pid"] == 33)
    assert binding.selected_record()["pid"] == 33


def test_select_where_returns_false_when_absent(binding):
    assert binding.select_where(lambda r: r["pid"] == 999999) is False


def test_record_role_returns_the_object_itself(binding):
    model = binding.model
    record = model.data(model.index(0, 0), RECORD_ROLE)
    assert record is model.records[0]


# --- population ------------------------------------------------------------


def test_set_records_replaces_everything(binding):
    binding.set_records([{"pid": 7, "name": "solo", "rss": 1, "cpu": 0.0}])
    assert binding.proxy.rowCount() == 1
    assert binding.proxy.data(binding.proxy.index(0, 1)) == "solo"


def test_clear_empties_the_model(binding):
    binding.model.clear()
    assert binding.proxy.rowCount() == 0
    assert binding.selected_record() is None


def test_record_at_is_bounds_safe(binding):
    assert binding.model.record_at(0) is not None
    assert binding.model.record_at(999) is None
    assert binding.model.record_at(-1) is None


def test_works_with_attribute_records_not_just_dicts(app):
    class Device:
        def __init__(self, ip):
            self.ip = ip

    model = RecordTableModel([Column("IP", "ip")])
    model.set_records([Device("10.0.0.1")])
    assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == "10.0.0.1"


# --- virtualisation --------------------------------------------------------


def test_large_result_set_costs_no_per_cell_objects(binding):
    """10,000 rows must be accepted without building 30,000 cell objects."""
    import time

    big = [{"pid": i, "name": f"p{i}", "rss": i, "cpu": 0.0} for i in range(10_000)]
    start = time.perf_counter()
    binding.set_records(big)
    elapsed = time.perf_counter() - start
    assert binding.proxy.rowCount() == 10_000
    # The point is that this is a list assignment plus a model reset, not
    # 30,000 widget-item allocations (QTableWidget-style costs 10s+ here).
    # Bound generously so a loaded CI box doesn't flake it.
    assert elapsed < 10.0, f"set_records took {elapsed:.2f}s"
