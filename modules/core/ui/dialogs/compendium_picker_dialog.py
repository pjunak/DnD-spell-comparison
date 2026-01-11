"""Searchable selection dialog with details side panel.

Used for choosing feats and invocations while letting the user preview details.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
	QDialog,
	QDialogButtonBox,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QListWidget,
	QListWidgetItem,
	QPlainTextEdit,
	QVBoxLayout,
)


@dataclass(frozen=True)
class PickerItem:
	value: str
	label: str
	details: str


class CompendiumPickerDialog(QDialog):
	"""Dialog that supports search + preview + single/multi selection."""

	def __init__(
		self,
		*,
		title: str,
		items: Sequence[PickerItem],
		initial_selection: Iterable[str] = (),
		max_choices: int = 1,
		parent=None,
	) -> None:
		super().__init__(parent)
		self.setWindowTitle(title)
		self.resize(820, 520)
		self._items = list(items)
		self._max_choices = max(1, int(max_choices))
		self._selected: List[str] = []
		self._initial_set = {str(v) for v in initial_selection if str(v)}

		root = QVBoxLayout(self)
		root.setContentsMargins(12, 12, 12, 12)
		root.setSpacing(10)

		search = QLineEdit()
		search.setPlaceholderText("Search…")
		search.textChanged.connect(self._rebuild_list)
		self._search = search
		root.addWidget(search)

		split = QHBoxLayout()
		split.setContentsMargins(0, 0, 0, 0)
		split.setSpacing(12)
		root.addLayout(split, 1)

		left = QVBoxLayout()
		left.setContentsMargins(0, 0, 0, 0)
		left.setSpacing(6)
		split.addLayout(left, 1)

		list_widget = QListWidget()
		list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
		list_widget.itemSelectionChanged.connect(self._on_selection_changed)
		list_widget.itemChanged.connect(self._on_item_check_changed)
		self._list = list_widget
		left.addWidget(list_widget, 1)

		status = QLabel()
		status.setStyleSheet("color: #5f6b7c;")
		self._status = status
		left.addWidget(status)

		details = QPlainTextEdit()
		details.setReadOnly(True)
		details.setPlaceholderText("Select an item to preview details.")
		self._details = details
		split.addWidget(details, 1)

		buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
		buttons.accepted.connect(self._validate_and_accept)
		buttons.rejected.connect(self.reject)
		root.addWidget(buttons)

		self._rebuild_list()
		self._update_status()

	def selected_values(self) -> List[str]:
		return list(self._selected)

	# --- Internal ------------------------------------------------------
	def _filtered_items(self) -> List[PickerItem]:
		query = (self._search.text() or "").strip().lower()
		if not query:
			return list(self._items)
		return [
			item
			for item in self._items
			if query in item.label.lower() or query in item.value.lower()
		]

	def _rebuild_list(self) -> None:
		items = self._filtered_items()
		self._list.blockSignals(True)
		self._list.clear()
		for entry in items:
			item = QListWidgetItem(entry.label)
			item.setData(Qt.ItemDataRole.UserRole, entry.value)
			item.setToolTip(entry.details[:500] if entry.details else "")
			if self._max_choices > 1:
				item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
				checked = entry.value in self._initial_set or entry.value in self._selected
				item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
			self._list.addItem(item)
		self._list.blockSignals(False)

		# Seed initial selection.
		if self._max_choices == 1:
			for idx in range(self._list.count()):
				value = self._list.item(idx).data(Qt.ItemDataRole.UserRole)
				if value in self._initial_set:
					self._list.setCurrentRow(idx)
					break
		self._update_status()

	def _update_status(self) -> None:
		if self._max_choices <= 1:
			self._status.setText("Select one item.")
			return
		count = len(self._selected) or len(self._initial_set)
		self._status.setText(f"Selected {count} / {self._max_choices}")

	def _on_selection_changed(self) -> None:
		item = self._list.currentItem()
		if not item:
			self._details.setPlainText("")
			return
		value = str(item.data(Qt.ItemDataRole.UserRole) or "")
		match = next((entry for entry in self._items if entry.value == value), None)
		self._details.setPlainText(match.details if match else "")
		if self._max_choices == 1 and value:
			self._selected = [value]

	def _on_item_check_changed(self, item: QListWidgetItem) -> None:
		if self._max_choices <= 1:
			return
		value = str(item.data(Qt.ItemDataRole.UserRole) or "")
		if not value:
			return
		selected = set(self._selected or self._initial_set)
		if item.checkState() == Qt.CheckState.Checked:
			if value not in selected and len(selected) >= self._max_choices:
				self._list.blockSignals(True)
				item.setCheckState(Qt.CheckState.Unchecked)
				self._list.blockSignals(False)
				return
			selected.add(value)
		else:
			selected.discard(value)
		self._selected = list(selected)
		self._update_status()
		# Show details for convenience.
		self._list.setCurrentItem(item)

	def _validate_and_accept(self) -> None:
		values = self.selected_values() if self._selected else list(self._initial_set)
		values = [v for v in values if str(v).strip()]
		if self._max_choices == 1 and not values:
			return
		if self._max_choices > 1 and len(values) > self._max_choices:
			return
		self._selected = values
		self.accept()


def build_picker_items(
	records: Sequence[dict],
	*,
	name_key: str = "name",
	detail_formatter: Callable[[dict], str] | None = None,
) -> List[PickerItem]:
	items: List[PickerItem] = []
	for record in records:
		name = record.get(name_key)
		if not isinstance(name, str) or not name.strip():
			continue
		details = detail_formatter(record) if detail_formatter else ""
		items.append(PickerItem(value=name.strip(), label=name.strip(), details=details or ""))
	items.sort(key=lambda item: item.label.lower())
	return items


__all__ = ["PickerItem", "CompendiumPickerDialog", "build_picker_items"]
