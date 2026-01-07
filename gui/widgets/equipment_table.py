"""Equipment bonuses table widget."""

from __future__ import annotations

from typing import Iterable, Iterator, List

from PySide6.QtWidgets import QAbstractItemView, QTableWidget, QTableWidgetItem, QWidget

from modules.characters.model import EquipmentItem


class EquipmentBonusesTable(QTableWidget):
    """Table widget encapsulating equipment bonus entry management."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, 5, parent)
        self.setHorizontalHeaderLabels(["Item", "Slot/Type", "Bonus Type", "Bonus Value", "Notes"])
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

    def populate(self, items: Iterable[EquipmentItem]) -> None:
        self.setRowCount(0)
        for item in items:
            self.append_entry(item)

    def append_entry(
        self,
        item: EquipmentItem,
        slot: str = "",
        bonus_type: str | None = None,
        bonus_value: int | None = None,
    ) -> None:
        row = self.rowCount()
        self.insertRow(row)
        self._set_row(row, item, slot, bonus_type, bonus_value)

    def upsert_entry(
        self,
        item: EquipmentItem,
        slot: str,
        bonus_type: str,
        bonus_value: int,
    ) -> bool:
        row = self._find_row(item.name, slot)
        if row is None:
            self.append_entry(item, slot=slot, bonus_type=bonus_type, bonus_value=bonus_value)
            return True
        self._set_row(row, item, slot, bonus_type, bonus_value)
        return False

    def remove_selected_rows(self) -> None:
        rows = sorted({index.row() for index in self.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            self.removeRow(row)

    def iter_items(self) -> Iterator[EquipmentItem]:
        for row in range(self.rowCount()):
            name = self._text(row, 0)
            if not name:
                continue
            notes = self._text(row, 4)
            bonus_type = self._text(row, 2).lower()
            bonus_value = self._int_value(row, 3)
            bonuses = {bonus_type: bonus_value} if bonus_type else {}
            yield EquipmentItem(name=name, quantity=1, weight_lb=0.0, attuned=False, notes=notes, bonuses=bonuses)

    def current_items(self) -> List[EquipmentItem]:
        return list(self.iter_items())

    def _set_row(
        self,
        row: int,
        item: EquipmentItem,
        slot: str,
        bonus_type: str | None,
        bonus_value: int | None,
    ) -> None:
        self.setItem(row, 0, QTableWidgetItem(item.name))
        self.setItem(row, 1, QTableWidgetItem(slot))
        bonus_key = bonus_type or next(iter(item.bonuses.keys()), "")
        bonus_val = bonus_value if bonus_value is not None else (item.bonuses.get(bonus_key, 0) if bonus_key else 0)
        self.setItem(row, 2, QTableWidgetItem(bonus_key))
        self.setItem(row, 3, QTableWidgetItem(str(bonus_val)))
        self.setItem(row, 4, QTableWidgetItem(item.notes))

    def _find_row(self, name: str | None, slot: str | None) -> int | None:
        needle_name = (name or "").strip().lower()
        needle_slot = (slot or "").strip().lower()
        if not needle_name:
            return None
        for row in range(self.rowCount()):
            row_name = self._text(row, 0).lower()
            row_slot = self._text(row, 1).lower()
            if row_name == needle_name and row_slot == needle_slot:
                return row
        return None

    def _text(self, row: int, column: int) -> str:
        item = self.item(row, column)
        return item.text().strip() if item else ""

    def _int_value(self, row: int, column: int) -> int:
        text = self._text(row, column)
        try:
            return int(text)
        except ValueError:
            return 0


__all__ = ["EquipmentBonusesTable"]
