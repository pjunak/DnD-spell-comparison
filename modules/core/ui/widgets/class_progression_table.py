"""Table widget dedicated to displaying class progressions."""

from __future__ import annotations

from typing import Callable, Iterable, Iterator, List

from PySide6.QtCore import QModelIndex, QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
	QAbstractItemView,
	QComboBox,
	QStyledItemDelegate,
	QTableWidget,
	QTableWidgetItem,
	QWidget,
)

from modules.character_sheet.model import ClassProgression
from modules.dnd24_mechanics.class_options import CLASS_NAME_OPTIONS, subclass_options_for


class _ComboDelegate(QStyledItemDelegate):
	"""Delegate that swaps in a combo box with predefined options."""

	def __init__(
		self,
		options_provider: Callable[[QModelIndex], List[str]],
		*,
		allow_blank: bool,
		parent: QWidget | None = None,
	) -> None:
		super().__init__(parent)
		self._options_provider = options_provider
		self._allow_blank = allow_blank

	def createEditor(self, parent: QWidget, option, index: QModelIndex) -> QWidget:  # type: ignore[override]
		combo = QComboBox(parent)
		combo.setEditable(True)
		combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
		completer = combo.completer()
		if completer:
			completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
			completer.setFilterMode(Qt.MatchFlag.MatchContains)
		self._populate(combo, index)
		return combo

	def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:  # type: ignore[override]
		if isinstance(editor, QComboBox):
			self._populate(editor, index)
			text = (index.data(Qt.ItemDataRole.EditRole) or "").strip().lower()
			for pos in range(editor.count()):
				candidate = editor.itemText(pos).strip().lower()
				if candidate == text:
					editor.setCurrentIndex(pos)
					break
			else:
				if self._allow_blank:
					editor.setCurrentIndex(0)

	def setModelData(self, editor: QWidget, model, index: QModelIndex) -> None:  # type: ignore[override]
		if isinstance(editor, QComboBox):
			value = editor.currentText().strip()
			choices = [editor.itemText(i).strip() for i in range(editor.count())]
			if value:
				for choice in choices:
					if choice.lower() == value.lower():
						value = choice
						break
				else:
					value = choices[0] if choices else ""
			model.setData(index, value)
		else:
			super().setModelData(editor, model, index)

	def _populate(self, combo: QComboBox, index: QModelIndex) -> None:
		options = self._options_provider(index)
		combo.blockSignals(True)
		combo.clear()
		combo.addItems(options)
		combo.blockSignals(False)


def _class_options_provider(_: QModelIndex) -> List[str]:
	return list(CLASS_NAME_OPTIONS)


def _subclass_options_provider(index: QModelIndex) -> List[str]:
	model = index.model()
	class_index = model.index(index.row(), 0)
	class_name = class_index.data(Qt.ItemDataRole.DisplayRole)
	return [""] + subclass_options_for(class_name)


class ClassProgressionTable(QTableWidget):
	"""Encapsulates class progression editing with change notifications."""

	progressions_changed = Signal()

	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(0, 3, parent)
		self._populating = False
		self._reading_progressions = False
		self.setHorizontalHeaderLabels(["Class", "Subclass", "Level"])
		header = self.horizontalHeader()
		header.setStretchLastSection(False)
		self.setColumnWidth(0, 200)
		self.setColumnWidth(1, 200)
		self.setColumnWidth(2, 60)
		self.verticalHeader().setVisible(False)
		self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
		self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.setEditTriggers(
			QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.SelectedClicked
		)
		self.setItemDelegateForColumn(
			0,
			_ComboDelegate(_class_options_provider, allow_blank=False, parent=self),
		)
		self.setItemDelegateForColumn(
			1,
			_ComboDelegate(_subclass_options_provider, allow_blank=True, parent=self),
		)
		self.itemChanged.connect(self._on_item_changed)

	def populate(self, classes: Iterable[ClassProgression]) -> None:
		self._populating = True
		self.setRowCount(0)
		for progression in classes:
			self._append_row(progression)
		self._populating = False
		self.progressions_changed.emit()

	def insert_or_replace(self, progression: ClassProgression, row: int | None = None) -> int:
		if row is None or row < 0:
			row = self.rowCount()
			self.insertRow(row)
		self._set_row(row, progression)
		self.progressions_changed.emit()
		return row

	def remove_row(self, row: int) -> None:  # type: ignore[override]
		if row < 0 or row >= self.rowCount():
			return
		super().removeRow(row)
		self.progressions_changed.emit()

	def selected_row(self) -> int:
		return self.currentRow()

	def iter_progressions(self) -> Iterator[ClassProgression]:
		# Reading from the table while an editor is committing data can be re-entrant
		# (signals can fire while we're mid-read). Guard + block table signals.
		if self._reading_progressions:
			return
		self._reading_progressions = True
		blocker = QSignalBlocker(self)
		try:
			for row in range(self.rowCount()):
				yield self._row_to_progression(row)
		finally:
			# Ensure blocker is kept alive for the full scope.
			_ = blocker
			self._reading_progressions = False

	def current_progressions(self) -> List[ClassProgression]:
		# If called re-entrantly, return a safe empty list rather than recursing.
		if self._reading_progressions:
			return []
		return list(self.iter_progressions())

	def progression_at(self, row: int) -> ClassProgression | None:
		if row < 0 or row >= self.rowCount():
			return None
		if self._reading_progressions:
			return None
		blocker = QSignalBlocker(self)
		try:
			return self._row_to_progression(row)
		finally:
			_ = blocker

	def _append_row(self, progression: ClassProgression) -> None:
		row = self.rowCount()
		self.insertRow(row)
		self._set_row(row, progression)

	def _set_row(self, row: int, progression: ClassProgression) -> None:
		self._populating = True
		self.setItem(row, 0, QTableWidgetItem(progression.name))
		self.setItem(row, 1, QTableWidgetItem(progression.subclass or ""))
		self.setItem(row, 2, QTableWidgetItem(str(progression.level)))
		self._populating = False

	def _row_to_progression(self, row: int) -> ClassProgression:
		name = self._text(row, 0)
		subclass = self._text(row, 1) or None
		try:
			level = int(self._text(row, 2) or 0)
		except ValueError:
			level = 0
		return ClassProgression(name=name, level=max(level, 0), subclass=subclass)

	def _text(self, row: int, column: int) -> str:
		item = self.item(row, column)
		return item.text().strip() if item else ""

	def _on_item_changed(self, _item: QTableWidgetItem) -> None:
		if self._populating or self._reading_progressions:
			return
		self.progressions_changed.emit()


__all__ = ["ClassProgressionTable"]
