"""Widget showing derived spell slot totals."""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QGroupBox, QHBoxLayout, QLabel, QWidget


class SpellSlotAdjustmentsGroup(QGroupBox):
	"""Displays final slot labels.

	This is intentionally read-only: slot changes must come from the source of truth
	(classes, features, equipment), not manual per-level overrides.
	"""

	adjustments_changed = Signal()

	def __init__(self, initial_adjustments: Dict[int, int], parent: QWidget | None = None) -> None:
		super().__init__("Maximum Spell Slots", parent)
		self._labels: Dict[int, QLabel] = {}

		layout = QFormLayout(self)
		for level in range(1, 10):
			row_widget = QWidget()
			row_layout = QHBoxLayout(row_widget)
			row_layout.setContentsMargins(0, 0, 0, 0)
			row_layout.setSpacing(8)

			final_label = QLabel("0")

			row_layout.addWidget(QLabel("Final:"))
			row_layout.addWidget(final_label)
			row_layout.addStretch()

			layout.addRow(f"Level {level}", row_widget)
			self._labels[level] = final_label

	def set_level_text(self, level: int, text: str) -> None:
		label = self._labels.get(level)
		if label:
			label.setText(text)

	def adjustments(self) -> Dict[int, int]:
		return {}

	def extra_value(self, level: int) -> int:
		return 0


__all__ = ["SpellSlotAdjustmentsGroup"]