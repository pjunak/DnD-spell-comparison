"""Reusable spell access table widget."""

from __future__ import annotations

from typing import Iterable, Iterator, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QTableWidget, QTableWidgetItem, QWidget

from modules.characters.model import SpellAccessEntry


def build_spell_source_key(source_type: str | None, source_id: str | None, source_label: str | None) -> str:
    """Normalise a source descriptor into a stable lookup key."""

    type_key = (source_type or "").strip().lower()
    id_key = (source_id or "").strip().lower()
    label_key = (source_label or "").strip().lower()
    if not id_key:
        id_key = label_key
    if not type_key:
        type_key = "label" if label_key else ""
    if not (type_key or id_key):
        return ""
    return f"{type_key}::{id_key}"


class SpellAccessTable(QTableWidget):
    """Table widget that manages spell access entries with prepared state."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, 5, parent)
        self.setHorizontalHeaderLabels(["Spell", "Source", "Ability", "Category", "Prepared"])
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

    def populate(self, entries: Iterable[SpellAccessEntry]) -> None:
        self.setRowCount(0)
        for entry in entries:
            self.append_entry(entry)

    def sync_prepared_modes(self, source_key_to_mode: dict[str, str]) -> bool:
        """Sync prepared checkbox state/editability for known vs prepared casters.

        Only rows whose computed source key exists in the mapping are affected.
        Returns True if any row state changed.
        """

        if not source_key_to_mode:
            return False
        changed = False
        for row in range(self.rowCount()):
            metadata = self._metadata(row)
            source_key = (metadata.get("source_key") or "").strip().lower()
            if not source_key:
                continue
            mode = (source_key_to_mode.get(source_key) or "").strip().lower()
            if not mode:
                continue
            prepared_item = self.item(row, 4)
            if not prepared_item:
                continue
            flags = prepared_item.flags()
            if mode == "known":
                if prepared_item.checkState() != Qt.CheckState.Unchecked:
                    prepared_item.setCheckState(Qt.CheckState.Unchecked)
                    changed = True
                new_flags = flags & ~Qt.ItemFlag.ItemIsUserCheckable
                new_flags = new_flags & ~Qt.ItemFlag.ItemIsEnabled
                if new_flags != flags:
                    prepared_item.setFlags(new_flags)
                    changed = True
            else:
                new_flags = flags | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
                if new_flags != flags:
                    prepared_item.setFlags(new_flags)
                    changed = True
        return changed

    def append_entry(self, entry: SpellAccessEntry) -> None:
        row = self.rowCount()
        self.insertRow(row)
        self._set_row(row, entry)

    def upsert_entry(self, entry: SpellAccessEntry) -> bool:
        row = self._find_row(entry.spell_name, entry.source)
        if row is None:
            self.append_entry(entry)
            return True
        self._set_row(row, entry)
        return False

    def remove_selected_rows(self) -> None:
        rows = sorted({index.row() for index in self.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            self.removeRow(row)

    def iter_entries(self) -> Iterator[SpellAccessEntry]:
        for row in range(self.rowCount()):
            spell_name = self._text(row, 0)
            source = self._text(row, 1)
            ability_text = self._text(row, 2)
            category = self._text(row, 3)
            prepared_item = self.item(row, 4)
            is_prepared = prepared_item.checkState() == Qt.CheckState.Checked if prepared_item else False
            metadata = self._metadata(row)
            yield SpellAccessEntry(
                spell_name=spell_name,
                source=source,
                category=category,
                prepared=is_prepared,
                source_type=metadata.get("source_type", ""),
                source_id=metadata.get("source_id", ""),
                ability=metadata.get("ability") or (ability_text.upper() if ability_text else None),
                granted=metadata.get("granted", False),
            )

    def _set_row(self, row: int, entry: SpellAccessEntry) -> None:
        self.setItem(row, 0, QTableWidgetItem(entry.spell_name or ""))
        self.setItem(row, 1, QTableWidgetItem(entry.source or ""))
        ability_item = QTableWidgetItem((entry.ability or "").upper())
        ability_item.setFlags(ability_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, 2, ability_item)
        self.setItem(row, 3, QTableWidgetItem(entry.category or ""))
        prepared_item = QTableWidgetItem()
        prepared_item.setFlags(prepared_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        prepared_item.setCheckState(Qt.CheckState.Checked if entry.prepared else Qt.CheckState.Unchecked)
        self.setItem(row, 4, prepared_item)
        self._store_metadata(
            row,
            {
                "source_type": entry.source_type or "",
                "source_id": entry.source_id or "",
                "ability": ((entry.ability or "").upper() or None),
                "granted": bool(entry.granted),
                "source_key": build_spell_source_key(entry.source_type, entry.source_id, entry.source),
            },
        )
        self.setRowHidden(row, False)

    def _find_row(self, spell_name: str | None, source: str | None) -> int | None:
        needle_name = (spell_name or "").strip().lower()
        needle_source = (source or "").strip().lower()
        if not needle_name:
            return None
        for row in range(self.rowCount()):
            row_name = self._text(row, 0).lower()
            row_source = self._text(row, 1).lower()
            if row_name == needle_name and row_source == needle_source:
                return row
        return None

    def _text(self, row: int, column: int) -> str:
        item = self.item(row, column)
        return item.text().strip() if item else ""

    def _metadata(self, row: int) -> dict:
        item = self.item(row, 0)
        if not item:
            return {}
        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            return data
        return {}

    def _store_metadata(self, row: int, payload: dict) -> None:
        item = self.item(row, 0)
        if not item:
            item = QTableWidgetItem()
            self.setItem(row, 0, item)
        item.setData(Qt.ItemDataRole.UserRole, dict(payload))

    def entries_for_source(self, source_key: str | None) -> List[SpellAccessEntry]:
        needle = (source_key or "").strip().lower()
        return [entry for entry in self.iter_entries() if (build_spell_source_key(entry.source_type, entry.source_id, entry.source).lower() == needle)]

    def remove_entries_for_source(self, source_key: str | None) -> None:
        needle = (source_key or "").strip().lower()
        if not needle:
            return
        rows_to_remove: List[int] = []
        for row in range(self.rowCount()):
            metadata = self._metadata(row)
            row_key = (metadata.get("source_key") or "").strip().lower()
            if row_key == needle:
                rows_to_remove.append(row)
        for row in reversed(rows_to_remove):
            self.removeRow(row)

    def apply_source_filter(self, source_key: str | None) -> None:
        needle = (source_key or "").strip().lower()
        for row in range(self.rowCount()):
            metadata = self._metadata(row)
            row_key = (metadata.get("source_key") or "").strip().lower()
            self.setRowHidden(row, bool(needle) and row_key != needle)


__all__ = ["SpellAccessTable"]
