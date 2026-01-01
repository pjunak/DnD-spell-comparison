"""Hit point derivation helpers.

Design rules:
- Max HP is derived (class hit die + CON modifier, plus any configured bonuses).
- Current HP is a freely editable state value and should not be overwritten by derivation.
"""

from __future__ import annotations

from typing import Iterable

from character_sheet.model import ClassProgression
from services.compendium import Compendium


def average_hp_per_level(hit_die: int) -> int:
	"""Return the deterministic per-level HP gain for a hit die.

	Uses the common 5e-style average: floor(d/2) + 1.
	Examples: d6->4, d8->5, d10->6, d12->7.
	"""

	die = max(1, int(hit_die))
	return die // 2 + 1


def class_hit_die(compendium: Compendium | None, class_name: str) -> int:
	# Try to load from python module first
	try:
		# TODO: Make this dynamic based on active ruleset
		if class_name.lower() == "fighter":
			from database.compendium.dnd_2024.players_handbook.classes.fighter.base import HIT_DIE
			return HIT_DIE
	except ImportError:
		pass

	if not compendium:
		return 8
	record = compendium.class_record(class_name)
	if not record:
		return 8
	value = record.get("hit_die", 8)
	try:
		return max(1, int(value))
	except (TypeError, ValueError):
		return 8


def derive_max_hp(
	classes: Iterable[ClassProgression],
	*,
	con_modifier: int,
	compendium: Compendium | None = None,
	equipment_bonus: int = 0,
	per_level_bonus: int = 0,
) -> int:
	entries = [entry for entry in classes if (entry.name or "").strip() and int(entry.level or 0) > 0]
	if not entries:
		return 0

	con_mod = int(con_modifier)
	total_level = sum(max(0, int(entry.level)) for entry in entries)
	if total_level <= 0:
		return 0

	total = 0
	first = entries[0]
	first_die = class_hit_die(compendium, first.name)
	first_levels = max(0, int(first.level))
	if first_levels:
		total += first_die
		if first_levels > 1:
			total += average_hp_per_level(first_die) * (first_levels - 1)

	for entry in entries[1:]:
		hit_die = class_hit_die(compendium, entry.name)
		levels = max(0, int(entry.level))
		if levels:
			total += average_hp_per_level(hit_die) * levels

	total += con_mod * total_level
	total += int(equipment_bonus)
	try:
		per_level = int(per_level_bonus)
	except (TypeError, ValueError):
		per_level = 0
	if per_level:
		total += int(per_level) * int(total_level)
	return max(1, int(total))
