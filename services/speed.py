"""Speed derivation.

Keeps movement speed derived (read-only) by computing it from sources of truth
(species, equipment, and later features).

Current implementation:
- Base speed from selected species record ("speed"), default 30.
- Flat bonuses from equipment item bonuses keys {"speed", "speed_ft", "walk_speed"}.

Future:
- Armor-based penalties (if modeled in data)
- Feature-based adjustments (Fleet of Foot, etc.)
- Multiple movement types (fly, swim, climb)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from modules.characters.model import EquipmentItem
from modules.compendium.service import Compendium
from modules.compendium.mechanics import collect_bonus_bundle, collect_speed_base_ft


@dataclass(frozen=True)
class SpeedBreakdown:
	base_ft: int
	equipment_bonus_ft: int

	@property
	def total_ft(self) -> int:
		return max(0, int(self.base_ft) + int(self.equipment_bonus_ft))


def derive_speed_ft(
	*,
	compendium: Compendium | None,
	species_name: str | None,
	species_subtype_name: str | None = None,
	equipment: Iterable[EquipmentItem] | None,
	bonus_ft: int | None = None,
	base_ft_override: int | None = None,
	default_base_ft: int = 30,
) -> SpeedBreakdown:
	base = int(base_ft_override) if base_ft_override is not None else collect_speed_base_ft(
		compendium=compendium,
		species_name=species_name,
		species_subtype_name=species_subtype_name,
		default_base_ft=default_base_ft,
	)
	bonus = int(bonus_ft) if bonus_ft is not None else collect_bonus_bundle(
		compendium=None,
		species_name=None,
		species_subtype_name=None,
		class_progression=[],
		feat_names=None,
		equipment=equipment or [],
	).get("speed_ft")
	return SpeedBreakdown(base_ft=base, equipment_bonus_ft=bonus)


def _species_base_speed(
	compendium: Compendium | None,
	species_name: str | None,
	*,
	species_subtype_name: str | None,
	default_base_ft: int,
) -> int:
	name_key = (species_name or "").strip().lower()
	if not (compendium and name_key):
		return int(default_base_ft)
	for record in compendium.records("species"):
		if not isinstance(record, Mapping):
			continue
		name = record.get("name")
		if not isinstance(name, str):
			continue
		if name.strip().lower() != name_key:
			continue
		# Prefer structured subtype overrides if present.
		subtype_key = (species_subtype_name or "").strip().lower()
		if subtype_key:
			raw_subtypes = record.get("subtypes")
			if isinstance(raw_subtypes, list):
				for subtype in raw_subtypes:
					if not isinstance(subtype, Mapping):
						continue
					st_name = subtype.get("name")
					if not isinstance(st_name, str) or st_name.strip().lower() != subtype_key:
						continue
					st_speed = subtype.get("speed")
					if isinstance(st_speed, (int, float)):
						return int(st_speed)
					if isinstance(st_speed, str):
						try:
							return int(st_speed.strip())
						except (TypeError, ValueError):
							pass
					st_bonus = subtype.get("speed_bonus")
					if isinstance(st_bonus, (int, float)):
						# Fall back to base speed + bonus (computed below).
						base_speed = record.get("speed")
						base = int(base_speed) if isinstance(base_speed, (int, float)) else int(default_base_ft)
						return int(base + int(st_bonus))
					break

		speed = record.get("speed")
		if isinstance(speed, bool):
			return int(default_base_ft)
		if isinstance(speed, (int, float)):
			return int(speed)
		if isinstance(speed, str):
			try:
				return int(speed.strip())
			except (TypeError, ValueError):
				return int(default_base_ft)
		return int(default_base_ft)
	return int(default_base_ft)


def _sum_equipment_bonus(items: Iterable[EquipmentItem]) -> int:
	keys = {"speed", "speed_ft", "walk_speed"}
	total = 0
	for item in items:
		for key, value in (item.bonuses or {}).items():
			if str(key).strip().lower() not in keys:
				continue
			try:
				total += int(value)
			except (TypeError, ValueError):
				continue
	return total


__all__ = ["SpeedBreakdown", "derive_speed_ft"]
