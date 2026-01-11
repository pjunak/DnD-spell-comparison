"""Table widget dedicated to displaying and editing feats/features."""

from __future__ import annotations

from typing import Iterable, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QTableWidget, QTableWidgetItem, QWidget

from modules.character_sheet.model import FeatureEntry


class FeatsTable(QTableWidget):
    """Simple three-column table storing FeatureEntry rows."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, 3, parent)
        self.setHorizontalHeaderLabels(["Feat / Feature", "Source", "Notes"])
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

    def populate(self, entries: Iterable[FeatureEntry]) -> None:
        self.setRowCount(0)
        for entry in entries:
            self.append_entry(entry)

    def append_entry(self, entry: FeatureEntry) -> None:
        row = self.rowCount()
        self.insertRow(row)
        self._set_row(row, entry)

    def replace_entry(self, row: int, entry: FeatureEntry) -> None:
        if 0 <= row < self.rowCount():
            self._set_row(row, entry)

    def selected_row(self) -> int:
        indexes = self.selectionModel().selectedRows() if self.selectionModel() else []
        return indexes[0].row() if indexes else -1

    def remove_selected_row(self) -> None:
        row = self.selected_row()
        if row >= 0:
            self.removeRow(row)

    def entries(self) -> List[FeatureEntry]:
        return [self.entry_at(row) for row in range(self.rowCount())]

    def entry_at(self, row: int) -> FeatureEntry:
        if row < 0 or row >= self.rowCount():
            return FeatureEntry(title="", source="", description="")
        return FeatureEntry(
            title=self._text(row, 0),
            source=self._text(row, 1),
            description=self._text(row, 2),
        )

    def _set_row(self, row: int, entry: FeatureEntry) -> None:
        self.setItem(row, 0, QTableWidgetItem(entry.title or ""))
        self.setItem(row, 1, QTableWidgetItem(entry.source or ""))
        self.setItem(row, 2, QTableWidgetItem(entry.description or ""))

    def _text(self, row: int, column: int) -> str:
        item = self.item(row, column)
        return item.text().strip() if item else ""


__all__ = ["FeatsTable"]
