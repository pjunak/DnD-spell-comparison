"""Group box widget that manages ability score inputs and modifier labels."""

from __future__ import annotations

from typing import Callable, Dict, Iterable, Mapping

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QGroupBox, QHBoxLayout, QLabel, QSpinBox, QWidget


def _default_modifier_formatter(value: int) -> str:
	return f"{value:+d}"


class AbilityScoresGroup(QGroupBox):
	"""Displays ability score inputs with derived modifier labels."""

	score_changed = Signal(str, int)

	def __init__(
		self,
		ability_names: Iterable[str],
		initial_scores: Dict[str, int],
		initial_modifiers: Dict[str, int] | None = None,
		modifier_formatter: Callable[[int], str] | None = None,
		title: str = "Ability Scores",
		parent: QWidget | None = None,
	) -> None:
		super().__init__(title, parent)
		self._spins: Dict[str, QSpinBox] = {}
		self._labels: Dict[str, QLabel] = {}
		self._formatter = modifier_formatter or _default_modifier_formatter
		self._initial_scores = dict(initial_scores)
		self._initial_modifiers = dict(initial_modifiers or {})

		layout = QFormLayout(self)
		for ability in ability_names:
			row_widget = QWidget()
			row_layout = QHBoxLayout(row_widget)
			row_layout.setContentsMargins(0, 0, 0, 0)

			spin = QSpinBox()
			spin.setRange(1, 30)
			spin.setValue(self._initial_scores.get(ability, 10))
			spin.valueChanged.connect(lambda value, ab=ability: self._on_spin_changed(ab, value))

			label = QLabel(self._formatted_modifier_for(ability, spin.value()))
			label.setFixedWidth(40)

			row_layout.addWidget(spin)
			row_layout.addWidget(label)
			row_layout.addStretch()

			layout.addRow(f"{ability}", row_widget)
			self._spins[ability] = spin
			self._labels[ability] = label

	def score_for(self, ability: str) -> int:
		spin = self._spins.get(ability)
		return spin.value() if spin else 0

	def modifier_for(self, ability: str) -> int:
		return (self.score_for(ability) - 10) // 2

	def scores(self) -> Dict[str, int]:
		return {ability: spin.value() for ability, spin in self._spins.items()}

	def set_scores(self, values: Mapping[str, int]) -> None:
		"""Apply the provided ability scores without breaking signal wiring."""

		for ability, value in values.items():
			spin = self._spins.get(ability)
			if not spin:
				continue
			try:
				numeric = int(value)
			except (TypeError, ValueError):
				continue
			spin.setValue(numeric)

	def set_score_bounds(self, minimum: int, maximum: int) -> None:
		"""Clamp all ability spin boxes to the provided range."""

		minimum = int(minimum)
		maximum = max(int(maximum), minimum)
		for spin in self._spins.values():
			spin.setRange(minimum, maximum)

	def _formatted_modifier_for(self, ability: str, score: int) -> str:
		if ability in self._initial_modifiers:
			return self._formatter(self._initial_modifiers[ability])
		return self._formatter((score - 10) // 2)

	def _on_spin_changed(self, ability: str, value: int) -> None:
		self._labels[ability].setText(self._formatter((value - 10) // 2))
		self.score_changed.emit(ability, value)


__all__ = ["AbilityScoresGroup"]
