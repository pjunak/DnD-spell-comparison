"""Read-only summary of derived saving throws and skill bonuses."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QWidget

from modules.character_sheet.model import ABILITY_NAMES, CharacterSheet


_SKILL_TO_ABILITY: Tuple[Tuple[str, str], ...] = (
	("Acrobatics", "DEX"),
	("Animal Handling", "WIS"),
	("Arcana", "INT"),
	("Athletics", "STR"),
	("Deception", "CHA"),
	("History", "INT"),
	("Insight", "WIS"),
	("Intimidation", "CHA"),
	("Investigation", "INT"),
	("Medicine", "WIS"),
	("Nature", "INT"),
	("Perception", "WIS"),
	("Performance", "CHA"),
	("Persuasion", "CHA"),
	("Religion", "INT"),
	("Sleight of Hand", "DEX"),
	("Stealth", "DEX"),
	("Survival", "WIS"),
)


def _format_bonus(value: int) -> str:
	return f"{value:+d}"


def _normalise_name(name: str) -> str:
	return (name or "").strip().lower()


class SavesSkillsSummaryGroup(QGroupBox):
	"""Displays derived saving throw and skill bonuses.

	This widget is intentionally read-only: the user should change the granting
	source (background/class/feat/item) rather than editing derived values.
	"""

	def __init__(self, sheet: CharacterSheet, parent: QWidget | None = None) -> None:
		super().__init__("Saving Throws & Skills", parent)
		self._sheet = sheet
		self._ability_score_bonuses: Dict[str, int] = {}
		self._value_labels: Dict[str, QLabel] = {}

		layout = QGridLayout(self)
		layout.setContentsMargins(8, 8, 8, 8)
		layout.setHorizontalSpacing(16)
		layout.setVerticalSpacing(4)

		layout.addWidget(QLabel("Saving Throws"), 0, 0)
		layout.addWidget(QLabel("Bonus"), 0, 1)
		layout.addWidget(QLabel("Skills"), 0, 2)
		layout.addWidget(QLabel("Bonus"), 0, 3)

		save_row = 1
		for ability in ABILITY_NAMES:
			name = f"{ability} Save"
			layout.addWidget(QLabel(name), save_row, 0)
			value = QLabel("+0")
			layout.addWidget(value, save_row, 1)
			self._value_labels[f"save::{ability}"] = value
			save_row += 1

		skill_row = 1
		for skill, ability in _SKILL_TO_ABILITY:
			layout.addWidget(QLabel(f"{skill} ({ability})"), skill_row, 2)
			value = QLabel("+0")
			layout.addWidget(value, skill_row, 3)
			self._value_labels[f"skill::{skill}"] = value
			skill_row += 1

		self.refresh()

	def set_sheet(self, sheet: CharacterSheet) -> None:
		self._sheet = sheet
		self.refresh()

	def set_ability_score_bonuses(self, bonuses: Dict[str, int] | None) -> None:
		"""Apply derived +score bonuses without mutating the sheet.

		Used for ASIs so derived saves/skills reflect the increased ability scores.
		"""

		incoming = bonuses or {}
		self._ability_score_bonuses = {str(k).upper(): int(v) for k, v in incoming.items() if str(k).strip()}
		self.refresh()

	def refresh(self) -> None:
		sheet = self._sheet
		prof_bonus = int(getattr(sheet.proficiencies, "proficiency_bonus", 0) or 0)
		bonuses = self._ability_score_bonuses

		def effective_ability_mod(ability: str) -> int:
			key = str(ability).upper()
			block = sheet.get_ability(key)
			if block.modifier is not None:
				return int(block.modifier)
			score = int(block.score) + int(bonuses.get(key, 0) or 0)
			return (score - 10) // 2

		# Saving throws: use AbilityBlock rules.
		for ability in ABILITY_NAMES:
			block = sheet.get_ability(ability)
			base = effective_ability_mod(ability)
			if block.save_proficient:
				base += prof_bonus
			base += int(block.save_bonus or 0)
			bonus = int(base)
			label = self._value_labels.get(f"save::{ability}")
			if label:
				label.setText(_format_bonus(bonus))

		# Skills: interpret proficiencies.skills as either rank map (0/1/2) or direct bonus map.
		skill_map = dict(sheet.proficiencies.skills or {})
		values: Iterable[object] = skill_map.values()
		is_rank_map = True
		for value in values:
			try:
				numeric = int(value)
			except (TypeError, ValueError):
				is_rank_map = False
				break
			if numeric not in (0, 1, 2):
				is_rank_map = False
				break

		if is_rank_map:
			ranks = {_normalise_name(name): int(value) for name, value in skill_map.items()}
			for skill, ability in _SKILL_TO_ABILITY:
				ability_mod = effective_ability_mod(ability)
				rank = ranks.get(_normalise_name(skill), 0)
				bonus = int(ability_mod + prof_bonus * max(0, min(rank, 2)))
				suffix = ""
				if rank == 1:
					suffix = " (P)"
				elif rank == 2:
					suffix = " (E)"
				label = self._value_labels.get(f"skill::{skill}")
				if label:
					label.setText(_format_bonus(bonus) + suffix)
		else:
			# Treat stored values as already-final bonuses.
			bonuses = {_normalise_name(name): int(value) for name, value in skill_map.items() if str(name).strip()}
			for skill, _ability in _SKILL_TO_ABILITY:
				value = bonuses.get(_normalise_name(skill))
				label = self._value_labels.get(f"skill::{skill}")
				if label:
					label.setText(_format_bonus(int(value)) if value is not None else "")


__all__ = ["SavesSkillsSummaryGroup"]
