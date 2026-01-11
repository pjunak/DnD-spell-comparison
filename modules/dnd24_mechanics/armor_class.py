"""Armor Class derivation.

This module keeps AC derived (read-only) by computing it from sources of truth.

Implemented sources:
- Equipment: armor / shields / flat bonuses
- Ability scores: DEX modifier (and optional CON/WIS for unarmored defense)
- Class-based feature formulas (minimal, structured): Unarmored Defense
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Tuple

from modules.character_sheet.model import EquipmentItem
from modules.compendium.service import Compendium


@dataclass(frozen=True)
class ArmorClassBreakdown:
	base: int
	dex_modifier_used: int
	armor_name: str | None
	shield_name: str | None
	item_bonus: int
	feature_bonus: int = 0
	formula: str | None = None

	@property
	def total(self) -> int:
		return self.base + self.dex_modifier_used + self.item_bonus + self.feature_bonus


def derive_armor_class(
	*,
	compendium: Compendium | None,
	equipment: Iterable[EquipmentItem] | None,
	dex_modifier: int,
	class_names: Iterable[str] | None = None,
	con_modifier: int | None = None,
	wis_modifier: int | None = None,
	species_name: str | None = None,
	species_subtype_name: str | None = None,
	ability_modifiers: Mapping[str, int] | None = None,
	ac_formula_candidates: Iterable[Mapping[str, object]] | None = None,
	flat_ac_bonus: int | None = None,
) -> ArmorClassBreakdown:
	"""Derive AC from armor/shield and DEX modifier.

	Rules implemented (minimal):
	- No armor: 10 + DEX
	- Light/medium armor: armor_class + min(DEX, dex_cap) where dex_cap can be "full" or int
	- Heavy armor: armor_class (no DEX)
	- Shield: adds its armor_class value as a bonus
	- Flat bonuses: equipment item bonuses keys {"ac", "armor_class"}

	Notes:
	- This assumes any armor/shield present in equipment is worn/used.
	- Feature formulas are applied only when no armor is worn.
	"""

	dex_mod = int(dex_modifier)
	con_mod = int(con_modifier or 0)
	wis_mod = int(wis_modifier or 0)
	mods = {str(k).strip().upper(): int(v) for k, v in (ability_modifiers or {}).items() if str(k).strip()}
	mods.setdefault("DEX", dex_mod)
	mods.setdefault("CON", con_mod)
	mods.setdefault("WIS", wis_mod)
	classes = {str(name or "").strip().lower() for name in (class_names or []) if str(name or "").strip()}
	items = list(equipment or [])
	armor_index = _build_armor_index(compendium)

	best_armor_total = 10 + dex_mod
	best_armor_base = 10
	best_armor_dex_used = dex_mod
	best_armor_name: str | None = None

	best_shield_bonus = 0
	best_shield_name: str | None = None

	for item in items:
		name = (item.name or "").strip()
		if not name:
			continue
		record = armor_index.get(name.lower())
		if not record:
			continue
		armor_type = str(record.get("armor_type") or "").strip().lower()
		raw_ac = record.get("armor_class")
		if isinstance(raw_ac, bool):
			ac_value = 0
		elif isinstance(raw_ac, (int, float)):
			ac_value = int(raw_ac)
		elif isinstance(raw_ac, str):
			try:
				ac_value = int(raw_ac.strip())
			except (TypeError, ValueError):
				ac_value = 0
		else:
			ac_value = 0
		if armor_type == "shield":
			if ac_value > best_shield_bonus:
				best_shield_bonus = ac_value
				best_shield_name = name
			continue

		dex_used = 0
		dex_cap = record.get("dex_cap")
		if isinstance(dex_cap, str) and dex_cap.strip().lower() == "full":
			dex_used = dex_mod
		elif isinstance(dex_cap, int):
			dex_used = min(dex_mod, dex_cap)
		elif isinstance(dex_cap, str):
			try:
				dex_used = min(dex_mod, int(dex_cap.strip()))
			except (TypeError, ValueError):
				dex_used = 0
		else:
			# Heavy (or unknown) armor: no dex.
			dex_used = 0
		candidate_total = ac_value + dex_used
		if candidate_total > best_armor_total:
			best_armor_total = candidate_total
			best_armor_base = ac_value
			best_armor_dex_used = dex_used
			best_armor_name = name

	item_bonus = int(flat_ac_bonus) if flat_ac_bonus is not None else _sum_item_bonus(items, keys={"ac", "armor_class"})
	base_with_shield = best_armor_base + best_shield_bonus

	feature_bonus = 0
	formula: str | None = None
	# Feature-based formulas: only when not wearing armor.
	# Prefer structured formula candidates passed in from a modifier-source pipeline.
	# Fallbacks exist for backwards compatibility.
	if best_armor_name is None:
		best_total = base_with_shield + best_armor_dex_used + item_bonus
		candidates = list(ac_formula_candidates or [])
		# Back-compat: if no candidates provided, include species natural armor and built-in class formulas.
		if not candidates:
			species_formula = _species_armor_class_formula(compendium, species_name, species_subtype_name)
			if isinstance(species_formula, Mapping):
				candidates.append(species_formula)
			if "barbarian" in classes:
				candidates.append({"type": "unarmored_defense", "base": 10, "add": ["DEX", "CON"], "allow_shield": True})
			if "monk" in classes:
				candidates.append({"type": "unarmored_defense", "base": 10, "add": ["DEX", "WIS"], "allow_shield": False})

		for candidate_formula in candidates:
			if not isinstance(candidate_formula, Mapping):
				continue
			candidate = _evaluate_ac_formula(
				candidate_formula,
				mods,
				shield_bonus=best_shield_bonus,
				item_bonus=item_bonus,
			)
			if candidate is None:
				continue
			candidate_total, candidate_base, candidate_dex_used, candidate_feature_bonus, candidate_key = candidate
			if candidate_total > best_total:
				best_total = candidate_total
				base_with_shield = candidate_base
				best_armor_dex_used = candidate_dex_used
				feature_bonus = candidate_feature_bonus
				formula = candidate_key

	return ArmorClassBreakdown(
		base=base_with_shield,
		dex_modifier_used=best_armor_dex_used,
		armor_name=best_armor_name,
		shield_name=best_shield_name,
		item_bonus=item_bonus,
		feature_bonus=feature_bonus,
		formula=formula,
	)


def _sum_item_bonus(items: Iterable[EquipmentItem], *, keys: set[str]) -> int:
	total = 0
	key_set = {k.lower() for k in keys}
	for item in items:
		for key, value in (item.bonuses or {}).items():
			if str(key).strip().lower() not in key_set:
				continue
			try:
				total += int(value)
			except (TypeError, ValueError):
				continue
	return total


def _build_armor_index(compendium: Compendium | None) -> dict[str, Mapping[str, object]]:
	if not compendium:
		return {}
	# equipment category stores blocks (armor/weapons/gear/packs). We only care about the armor block.
	for block in compendium.records("equipment"):
		if not isinstance(block, Mapping):
			continue
		if str(block.get("category") or "").strip().lower() != "armor":
			continue
		items = block.get("items")
		if not isinstance(items, list):
			continue
		index: dict[str, Mapping[str, object]] = {}
		for entry in items:
			if not isinstance(entry, Mapping):
				continue
			name = entry.get("name")
			if not isinstance(name, str):
				continue
			index[name.strip().lower()] = entry
		return index
	return {}


def _species_armor_class_formula(
	compendium: Compendium | None,
	species_name: str | None,
	species_subtype_name: str | None,
) -> Mapping[str, object] | None:
	if not (compendium and (species_name or "").strip()):
		return None
	name_key = (species_name or "").strip().lower()
	subtype_key = (species_subtype_name or "").strip().lower()
	for entry in compendium.records("species"):
		if not isinstance(entry, Mapping):
			continue
		name = entry.get("name")
		if not isinstance(name, str) or name.strip().lower() != name_key:
			continue
		# Subtype overrides (if present)
		if subtype_key:
			raw_subtypes = entry.get("subtypes")
			if isinstance(raw_subtypes, list):
				for subtype in raw_subtypes:
					if not isinstance(subtype, Mapping):
						continue
					st_name = subtype.get("name")
					if isinstance(st_name, str) and st_name.strip().lower() == subtype_key:
						formula = _extract_ac_formula_from_grants(subtype)
						if formula is not None:
							return formula
		# Fall back to base species
		return _extract_ac_formula_from_grants(entry)
	return None


def _extract_ac_formula_from_grants(block: Mapping[str, object]) -> Mapping[str, object] | None:
	grants = block.get("grants")
	if not isinstance(grants, Mapping):
		return None
	formula = grants.get("armor_class_formula")
	if isinstance(formula, Mapping):
		return formula
	return None


def _evaluate_ac_formula(
	formula: Mapping[str, object],
	ability_mods: Mapping[str, int],
	*,
	shield_bonus: int,
	item_bonus: int,
) -> Tuple[int, int, int, int, str] | None:
	"""Return (total, base, dex_used, feature_bonus, formula_key) or None."""
	formula_type = str(formula.get("type") or "").strip().lower()
	if formula_type not in {"natural_armor", "unarmored_defense"}:
		return None
	base_raw = formula.get("base")
	if isinstance(base_raw, bool):
		base_value = 10
	elif isinstance(base_raw, (int, float)):
		base_value = int(base_raw)
	elif isinstance(base_raw, str):
		try:
			base_value = int(base_raw.strip())
		except (TypeError, ValueError):
			base_value = 10
	else:
		base_value = 10
	allow_shield_raw = formula.get("allow_shield")
	allow_shield = True if allow_shield_raw is None else bool(allow_shield_raw)
	if not allow_shield and int(shield_bonus or 0) > 0:
		return None
	add_list = formula.get("add")
	if not isinstance(add_list, list) or not add_list:
		add_list = ["DEX"]
	add_mod_total = 0
	dex_used = 0
	feature_bonus = 0
	# Optional dex cap for formulas that add DEX.
	dex_cap = formula.get("dex_cap")
	cap_value: int | None = None
	if isinstance(dex_cap, str) and dex_cap.strip().lower() == "full":
		cap_value = None
	elif isinstance(dex_cap, int):
		cap_value = int(dex_cap)
	elif isinstance(dex_cap, str):
		try:
			cap_value = int(dex_cap.strip())
		except (TypeError, ValueError):
			cap_value = None

	for ability in add_list:
		key = str(ability or "").strip().upper()
		if not key:
			continue
		mod = int(ability_mods.get(key, 0) or 0)
		if key == "DEX":
			if cap_value is not None:
				mod = min(mod, cap_value)
			dex_used = mod
			add_mod_total += mod
			continue
		add_mod_total += mod
		feature_bonus += mod

	base_with_shield = base_value + (int(shield_bonus or 0) if allow_shield else 0)
	total = base_with_shield + add_mod_total + int(item_bonus or 0)
	key = "natural_armor" if formula_type == "natural_armor" else "unarmored_defense"
	return total, base_with_shield, dex_used, feature_bonus, key


__all__ = ["ArmorClassBreakdown", "derive_armor_class"]
