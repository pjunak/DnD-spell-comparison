"""Widget summarizing derived proficiency, attack, and save bonuses."""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class ProficiencySummaryGroup(QGroupBox):
	"""Displays derived bonus labels.

	This is intentionally read-only: edits must happen at the source of truth
	(ability scores, classes, equipment, feats), not via ad-hoc overrides.
	"""

	values_changed = Signal()

	_METRIC_CONFIG = {
		"proficiency": {"label": "Proficiency Bonus"},
		"attack": {"label": "Spell Attack Bonus"},
		"save": {"label": "Spell Save DC"},
	}

	def __init__(self, initial_extras: Dict[str, int], parent: QWidget | None = None) -> None:
		super().__init__("Spellcasting Bonuses", parent)
		self._labels: Dict[str, QLabel] = {}

		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(6)
		for key, config in self._METRIC_CONFIG.items():
			row = QWidget()
			row_layout = QHBoxLayout(row)
			row_layout.setContentsMargins(0, 0, 0, 0)
			row_layout.setSpacing(8)

			static_label = QLabel(config["label"])
			static_label.setMinimumWidth(150)

			display_label = QLabel()
			display_label.setMinimumWidth(120)

			row_layout.addWidget(static_label)
			row_layout.addWidget(display_label)
			row_layout.addStretch()

			layout.addWidget(row)
			self._labels[key] = display_label

	def extra_value(self, metric: str) -> int:
		return 0

	def set_display_text(self, metric: str, text: str) -> None:
		label = self._labels.get(metric)
		if label:
			label.setText(text)

	def extras(self) -> Dict[str, int]:
		return {}


__all__ = ["ProficiencySummaryGroup"]