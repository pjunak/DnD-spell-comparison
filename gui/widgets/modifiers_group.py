"""Widget for displaying modifier checkbox categories."""

from __future__ import annotations

from typing import Dict, Iterable, List

from PySide6.QtWidgets import QCheckBox, QGroupBox, QVBoxLayout, QWidget


class ModifiersGroup(QWidget):
	"""Arranges modifier definitions into grouped checkbox sections."""

	def __init__(self, definitions: Iterable[dict], initial_states: Dict[str, bool], parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._checks: Dict[str, QCheckBox] = {}
		self._definitions = [definition for definition in definitions if definition.get("name")]
		self._initial_states = dict(initial_states)

		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(8)

		grouped = self._group_by_category(self._definitions)
		for category_key in self._sorted_categories(grouped.keys()):
			group_box = QGroupBox(self._format_category_label(category_key))
			group_layout = QVBoxLayout(group_box)
			group_layout.setContentsMargins(8, 12, 8, 8)
			for definition in sorted(grouped[category_key], key=lambda d: str(d.get("name", "")).lower()):
				checkbox = QCheckBox(definition["name"])
				checkbox.setChecked(self._initial_state_for(definition))
				if definition.get("description"):
					checkbox.setToolTip(str(definition.get("description")))
				self._checks[definition["name"]] = checkbox
				group_layout.addWidget(checkbox)
			group_layout.addStretch()
			layout.addWidget(group_box)

		layout.addStretch()

	def states(self) -> Dict[str, bool]:
		return {name: checkbox.isChecked() for name, checkbox in self._checks.items()}

	def _initial_state_for(self, definition: dict) -> bool:
		name = definition["name"]
		if name in self._initial_states:
			return bool(self._initial_states[name])
		return bool(definition.get("default_enabled", False))

	@staticmethod
	def _group_by_category(definitions: Iterable[dict]) -> Dict[str, List[dict]]:
		grouped: Dict[str, List[dict]] = {}
		for definition in definitions:
			category = ModifiersGroup._normalise_category(definition.get("category"))
			grouped.setdefault(category, []).append(definition)
		return grouped

	@staticmethod
	def _normalise_category(value) -> str:
		text = str((value or "")).strip().lower()
		return text or "misc"

	@staticmethod
	def _sorted_categories(keys: Iterable[str]) -> List[str]:
		return sorted(keys)

	@staticmethod
	def _format_category_label(category: str) -> str:
		return category.title()


__all__ = ["ModifiersGroup"]
