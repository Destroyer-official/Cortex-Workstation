"""A reusable model/view foundation for the data-dense tables.

Why this exists
---------------
Every table in the app was a ``QTableWidget``, which is *item based*: it
allocates a ``QTableWidgetItem`` object per cell, for every row, whether or not
that row is on screen. Measured consequences in this codebase:

* **Secrets Scanner** had no row cap at all - the CLI trims its output to 100
  findings, but the GUI built one item per cell for *every* finding, so a large
  repository produced thousands of rows in one synchronous loop.
* **Task Manager** rebuilt ~150-500 rows x 8 columns every 2 seconds while
  "Live" was checked - up to ~4,000 object allocations per tick.

``QAbstractTableModel`` inverts that: the view asks for data only for the rows
it is actually painting, so cost scales with the viewport rather than the result
set. Sorting and filtering move to :class:`QSortFilterProxyModel`, which also
removes the "sort by display string" bug class (``"9 MB" > "10 MB"``).

Design
------
:class:`Column` declares one column - its header, how to read a display value
from a record, and optionally a typed sort key, icon, tooltip and alignment.
:class:`RecordTableModel` renders any sequence of records (dataclass, dict or
object) through those columns, so pages describe their table instead of
imperatively filling it.

Sorting note
------------
``sort_key`` matters. Without it, sorting compares the *display* text, so a
"Memory" column reading ``"9.0 MB"`` and ``"10.0 MB"`` sorts wrongly. Pass a
callable returning the underlying number and the proxy sorts on that.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
)
from PySide6.QtGui import QBrush, QColor

#: Role carrying the typed sort value, so the proxy never sorts display strings.
SORT_ROLE = Qt.ItemDataRole.UserRole + 1

#: Role exposing the whole record for a row, for selection and actions.
RECORD_ROLE = Qt.ItemDataRole.UserRole + 2


def _read(record: Any, name: str) -> Any:
    """Read *name* from a dict-like or attribute-like record."""
    if isinstance(record, dict):
        return record.get(name)
    return getattr(record, name, None)


@dataclass(frozen=True, slots=True)
class Column:
    """Declarative description of one table column.

    ``value`` may be a field name or a callable taking the record. Everything
    else is optional, so the common case stays a one-liner::

        Column("PID", "pid", sort_key=lambda p: p["pid"])
    """

    header: str
    value: str | Callable[[Any], Any]
    sort_key: Callable[[Any], Any] | None = None
    align: Qt.AlignmentFlag | None = None
    icon: Callable[[Any], Any] | None = None
    tooltip: Callable[[Any], str] | None = None
    #: Per-row text colour. Returns anything ``QBrush``/``QColor`` accepts (a
    #: token hex string is fine) or ``None`` to leave the theme default.
    #:
    #: Needed for the risk-signalling tables: network connections paint external
    #: remotes red, and a browser extension asking for broad permissions is shown
    #: red too. Without this hook those tables had to stay item-based, because
    #: migrating them would have silently dropped the colour.
    #:
    #: Colour must never be the *only* cue - pair it with ``icon`` or ``tooltip``
    #: so the meaning survives for colour-blind users and screen readers.
    foreground: Callable[[Any], Any] | None = None
    #: Give this column the remaining horizontal space.
    stretch: bool = False
    #: Include this column when the filter text is matched.
    searchable: bool = True

    def display(self, record: Any) -> str:
        """Format a record's raw value as display text (empty string when None)."""
        raw = self.value(record) if callable(self.value) else _read(record, self.value)
        return "" if raw is None else str(raw)

    def sort_value(self, record: Any) -> Any:
        """Typed sort key for a record: sort_key if given, else the raw value."""
        if self.sort_key is not None:
            return self.sort_key(record)
        raw = self.value(record) if callable(self.value) else _read(record, self.value)
        return "" if raw is None else raw


class RecordTableModel(QAbstractTableModel):
    """Renders a sequence of records through a list of :class:`Column`.

    Only the cells the view paints are ever queried, so a 10,000-row result set
    costs the same to display as a 50-row one.
    """

    def __init__(self, columns: Sequence[Column], parent: QObject | None = None):
        """Store the column definitions and start with zero records."""
        super().__init__(parent)
        self._columns: tuple[Column, ...] = tuple(columns)
        self._records: list[Any] = []

    # -- population ---------------------------------------------------------

    def set_records(self, records: Sequence[Any]) -> None:
        """Replace every row in one reset - no per-cell allocation."""
        self.beginResetModel()
        self._records = list(records)
        self.endResetModel()

    def clear(self) -> None:
        """Remove all rows via a model reset."""
        self.set_records([])

    @property
    def records(self) -> tuple[Any, ...]:
        """Snapshot of the current row records as a tuple."""
        return tuple(self._records)

    def record_at(self, row: int) -> Any | None:
        """The record behind *row*, or ``None`` when out of range."""
        if 0 <= row < len(self._records):
            return self._records[row]
        return None

    @property
    def columns(self) -> tuple[Column, ...]:
        """The model's column definitions."""
        return self._columns

    # -- QAbstractTableModel ------------------------------------------------

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        """Number of rows; 0 for any valid parent index (flat model)."""
        if parent is not None and parent.isValid():
            return 0
        return len(self._records)

    def columnCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        """Number of columns; 0 for any valid parent index (flat model)."""
        if parent is not None and parent.isValid():
            return 0
        return len(self._columns)

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Return header data."""
        if (orientation is Qt.Orientation.Horizontal
                and role == Qt.ItemDataRole.DisplayRole
                and 0 <= section < len(self._columns)):
            return self._columns[section].header
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Serve display, sort, record, icon, tooltip, alignment and foreground roles per column."""
        if not index.isValid():
            return None
        record = self.record_at(index.row())
        if record is None:
            return None
        if index.column() >= len(self._columns):
            return None
        column = self._columns[index.column()]

        if role == Qt.ItemDataRole.DisplayRole:
            return column.display(record)
        if role == SORT_ROLE:
            return column.sort_value(record)
        if role == RECORD_ROLE:
            return record
        if role == Qt.ItemDataRole.DecorationRole and column.icon is not None:
            return column.icon(record)
        if role == Qt.ItemDataRole.ToolTipRole and column.tooltip is not None:
            return column.tooltip(record)
        if role == Qt.ItemDataRole.TextAlignmentRole and column.align is not None:
            return int(column.align)
        if role == Qt.ItemDataRole.ForegroundRole and column.foreground is not None:
            colour = column.foreground(record)
            if colour is None:
                return None
            # Accept a QBrush/QColor as-is, and a token hex string for
            # convenience so pages can pass ``self.p.danger`` directly.
            if isinstance(colour, (QBrush, QColor)):
                return colour
            return QBrush(QColor(colour))
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Read-only enabled+selectable flags for valid indexes."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        # Read-only: these tables report system state; edits happen through
        # explicit actions, never by typing into a cell.
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable


class RecordFilterProxy(QSortFilterProxyModel):
    """Sorts on :data:`SORT_ROLE` and filters across searchable columns.

    Sorting on the typed role rather than the display string is what makes a
    "Memory" or "CPU %" column order correctly.
    """

    def __init__(self, parent: QObject | None = None):
        """Sort on SORT_ROLE with dynamic sort/filter and an empty filter term."""
        super().__init__(parent)
        self.setSortRole(SORT_ROLE)
        self.setDynamicSortFilter(True)
        self._term = ""

    def set_filter_text(self, text: str) -> None:
        """Set the case-folded filter term, keeping selection stable across the change."""
        term = (text or "").strip().casefold()
        if term == self._term:
            return
        # Qt 6.11 deprecates both ``invalidateFilter`` and
        # ``invalidateRowsFilter`` in favour of an explicit begin/end pair, which
        # lets the proxy keep the current selection stable across the change.
        # Older Qt builds fall back to the previous call.
        begin = getattr(self, "beginFilterChange", None)
        end = getattr(self, "endFilterChange", None)
        if callable(begin) and callable(end):
            begin()
            self._term = term
            end(QSortFilterProxyModel.Direction.Rows)
            return
        self._term = term  # pragma: no cover - Qt without begin/endFilterChange
        self.invalidateFilter()

    @property
    def filter_text(self) -> str:
        """The active case-folded filter term."""
        return self._term

    def filterAcceptsRow(  # noqa: N802
        self, source_row: int, source_parent: QModelIndex
    ) -> bool:
        """Filter accepts row."""
        if not self._term:
            return True
        model = self.sourceModel()
        if not isinstance(model, RecordTableModel):
            return True
        record = model.record_at(source_row)
        if record is None:
            return False
        for column_index, column in enumerate(model.columns):
            if not column.searchable:
                continue
            index = model.index(source_row, column_index, source_parent)
            text = model.data(index, Qt.ItemDataRole.DisplayRole)
            if text and self._term in str(text).casefold():
                return True
        return False

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:  # noqa: N802
        """Compare typed sort-role values, falling back to string comparison on TypeError."""
        model = self.sourceModel()
        if not isinstance(model, RecordTableModel):
            return super().lessThan(left, right)
        left_val = model.data(left, self.sortRole())
        right_val = model.data(right, self.sortRole())
        if left_val is None and right_val is None:
            return False
        if left_val is None:
            return True
        if right_val is None:
            return False
        try:
            return bool(left_val < right_val)
        except TypeError:
            return str(left_val) < str(right_val)


@dataclass(slots=True)
class TableBinding:
    """The objects created by :func:`bind_table`, kept together.

    Pages must retain this: dropping the model or proxy would leave the view
    showing nothing, because Qt does not take ownership of either.
    """

    view: Any
    model: RecordTableModel
    proxy: RecordFilterProxy
    columns: tuple[Column, ...] = field(default_factory=tuple)

    def set_records(self, records: Sequence[Any]) -> None:
        """Replace the underlying model's rows."""
        self.model.set_records(records)

    def set_filter_text(self, text: str) -> None:
        """Apply filter text to the proxy."""
        self.proxy.set_filter_text(text)

    @property
    def visible_count(self) -> int:
        """Rows passing the current filter."""
        return self.proxy.rowCount()

    def selected_record(self) -> Any | None:
        """The record behind the current selection, sort-order safe.

        Resolved by mapping the proxy index back to the source model, so it
        stays correct when the user sorts or filters - unlike indexing a python
        list by the view's row number.
        """
        indexes = self.view.selectionModel().selectedRows()
        if not indexes:
            indexes = self.view.selectionModel().selectedIndexes()
        if not indexes:
            return None
        return self.proxy.data(indexes[0], RECORD_ROLE)

    def select_where(self, predicate: Callable[[Any], bool]) -> bool:
        """Re-select the row whose record satisfies *predicate*.

        Used to keep a selection stable across a live refresh, keyed on identity
        (a PID, an IP) rather than a row number.
        """
        for proxy_row in range(self.proxy.rowCount()):
            index = self.proxy.index(proxy_row, 0)
            record = self.proxy.data(index, RECORD_ROLE)
            if record is not None and predicate(record):
                self.view.selectRow(proxy_row)
                return True
        return False


def bind_table(
    view: Any,
    columns: Sequence[Column],
    *,
    sort_column: int | None = None,
    sort_order: Qt.SortOrder = Qt.SortOrder.DescendingOrder,
    sortable: bool = True,
) -> TableBinding:
    """Wire *view* to a model + proxy built from *columns*.

    Applies the presentation defaults these tables share (row selection, single
    selection, read-only, alternating rows, hidden vertical header) and the
    per-column stretch declared on :class:`Column`.
    """
    from PySide6.QtWidgets import QAbstractItemView, QHeaderView

    model = RecordTableModel(columns, parent=view)
    proxy = RecordFilterProxy(parent=view)
    proxy.setSourceModel(model)
    view.setModel(proxy)

    view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    view.setAlternatingRowColors(True)
    view.verticalHeader().setVisible(False)
    view.setSortingEnabled(sortable)
    # Uniform row heights let Qt skip per-row size queries while scrolling.
    view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
    view.setWordWrap(False)

    header = view.horizontalHeader()
    for position, column in enumerate(columns):
        if column.stretch:
            header.setSectionResizeMode(position, QHeaderView.ResizeMode.Stretch)

    if sortable and sort_column is not None:
        view.sortByColumn(sort_column, sort_order)

    return TableBinding(view=view, model=model, proxy=proxy,
                        columns=tuple(columns))


__all__ = [
    "Column",
    "RECORD_ROLE",
    "RecordFilterProxy",
    "RecordTableModel",
    "SORT_ROLE",
    "TableBinding",
    "bind_table",
]
