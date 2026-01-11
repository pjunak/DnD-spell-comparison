"""Collect structured modifiers from all active sources.

Goal: keep rule data human-readable and modifiable by storing mechanics in a
consistent `grants` schema in compendium records (species/classes/subclasses/…)
and then aggregating those effects for derivation services.

This module is intentionally small at first; it can grow into a full effects
pipeline as more subsystems are migrated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Set, Tuple

from modules.character_sheet.model import EquipmentItem

from modules.compendium.service import Compendium


def collect_ac_formula_candidates(
	*,
	compendium: Compendium | None,
	species_name: str | None,
	species_subtype_name: str | None,
	class_names: Iterable[str] | None,
) -> List[Mapping[str, object]]:
	"""Collect AC formula candidate dicts from active sources.

Sources (initial):
	- Species / species subtype: `grants.armor_class_formula` (single) or
	  `grants.armor_class_formulas` (list)
	- Class records: `grants.armor_class_formulas` (list) or `grants.armor_class_formula` (single)

The returned dicts are passed into AC derivation; they must be structured and
contain enough info to evaluate conditions like shield allowance.
"""
	candidates: List[Mapping[str, object]] = []
	if compendium is None:
		return candidates

	# Species.
	species_record, subtype_record = _find_species_record(compendium, species_name, species_subtype_name)
	for block in (species_record, subtype_record):
		candidates.extend(_extract_ac_formulas(block))

	# Classes.
	for class_name in class_names or []:
		name = (class_name or "").strip()
		if not name:
			continue
		record = compendium.class_record(name)
		candidates.extend(_extract_ac_formulas(record))

	return candidates


@dataclass(frozen=True)
class BonusBundle:
	"""Aggregated bonuses from all active sources.

	`flat` uses canonical keys:
	- ac
	- speed_ft
	- initiative
	- max_hp
	- max_hp_per_level
	- spell_attack
	- spell_save_dc
	
	`spell_slots` maps spell level -> additional slots.
	"""

	flat: Dict[str, int]
	spell_slots: Dict[int, int]

	def get(self, key: str, default: int = 0) -> int:
		return int(self.flat.get(key, default) or 0)


_BONUS_KEY_ALIASES: Dict[str, str] = {
	# AC
	"ac": "ac",
	"armor_class": "ac",
	# Speed
	"speed": "speed_ft",
	"speed_ft": "speed_ft",
	"walk_speed": "speed_ft",
	# Initiative
	"initiative": "initiative",
	"initiative_bonus": "initiative",
	"init": "initiative",
	# HP
	"max_hp": "max_hp",
	"hp_max": "max_hp",
	"maxhp": "max_hp",
	"max_hp_per_level": "max_hp_per_level",
	"hp_per_level": "max_hp_per_level",
	"maxhp_per_level": "max_hp_per_level",
	# Spellcasting
	"spell_attack": "spell_attack",
	"spell_attack_bonus": "spell_attack",
	# Historical shorthand used in UI: treat as spell attack.
	"attack": "spell_attack",
	"spell_save": "spell_save_dc",
	"spell_save_dc": "spell_save_dc",
	"save_dc": "spell_save_dc",
}


def collect_bonus_bundle(
	*,
	compendium: Compendium | None,
	species_name: str | None,
	species_subtype_name: str | None,
	background_name: str | None = None,
	class_progression: Iterable[object] | None,
	feat_names: Iterable[str] | None = None,
	equipment: Iterable[EquipmentItem] | None,
) -> BonusBundle:
	"""Collect standardized bonuses from all active sources.

	`class_progression` should be an iterable of objects with at least `.name` and
	optional `.subclass` attributes (matches `ClassProgression`).
	"""
	flat: Dict[str, int] = {}
	slots: Dict[int, int] = {}

	_eq_flat, _eq_slots = _collect_equipment_bonuses(equipment or [])
	_merge_flat(flat, _eq_flat)
	_merge_slots(slots, _eq_slots)

	_comp_flat, _comp_slots = _collect_compendium_bonuses(
		compendium=compendium,
		species_name=species_name,
		species_subtype_name=species_subtype_name,
		background_name=background_name,
		class_progression=class_progression,
		feat_names=feat_names,
	)
	_merge_flat(flat, _comp_flat)
	_merge_slots(slots, _comp_slots)

	return BonusBundle(flat=flat, spell_slots=slots)


def _merge_flat(target: Dict[str, int], incoming: Dict[str, int]) -> None:
	for key, value in incoming.items():
		if not key:
			continue
		target[key] = int(target.get(key, 0) or 0) + int(value or 0)


def _merge_slots(target: Dict[int, int], incoming: Dict[int, int]) -> None:
	for level, value in incoming.items():
		try:
			lvl = int(level)
		except (TypeError, ValueError):
			continue
		if lvl <= 0:
			continue
		target[lvl] = int(target.get(lvl, 0) or 0) + int(value or 0)


def _collect_equipment_bonuses(items: Iterable[EquipmentItem]) -> Tuple[Dict[str, int], Dict[int, int]]:
	flat: Dict[str, int] = {}
	slots: Dict[int, int] = {}
	for item in items:
		for raw_key, raw_value in (item.bonuses or {}).items():
			key = str(raw_key or "").strip().lower()
			if not key:
				continue
			try:
				value = int(raw_value)
			except (TypeError, ValueError):
				continue

			# Spell slot bonuses.
			level = _parse_spell_slot_level(key)
			if level is not None:
				slots[level] = int(slots.get(level, 0) or 0) + value
				continue

			canonical = _BONUS_KEY_ALIASES.get(key)
			if not canonical:
				continue
			flat[canonical] = int(flat.get(canonical, 0) or 0) + value
	return flat, slots


@dataclass(frozen=True)
class TraitBundle:
	"""Non-numeric grants that are best represented as sets/maps."""

	senses_ft: Dict[str, int]
	resistances: Set[str]
	condition_immunities: Set[str]

	def senses_formatted(self) -> str:
		if not self.senses_ft:
			return "None"
		parts: List[str] = []
		for name, feet in sorted(self.senses_ft.items(), key=lambda kv: kv[0].lower()):
			label = str(name).strip()
			try:
				dist = int(feet)
			except (TypeError, ValueError):
				dist = 0
			parts.append(f"{label} {dist} ft" if dist > 0 else label)
		return ", ".join(parts) if parts else "None"

	def resistances_formatted(self) -> str:
		return _format_title_list(self.resistances)

	def condition_immunities_formatted(self) -> str:
		return _format_title_list(self.condition_immunities)


def _format_title_list(values: Iterable[str]) -> str:
	items = [str(v).strip() for v in values if str(v).strip()]
	if not items:
		return "None"
	items = sorted(set(items), key=lambda s: s.lower())
	def _title(s: str) -> str:
		return s[:1].upper() + s[1:] if s else s
	return ", ".join(_title(s) for s in items)


def collect_trait_bundle(
	*,
	compendium: Compendium | None,
	species_name: str | None,
	species_subtype_name: str | None,
	background_name: str | None = None,
	class_progression: Iterable[object] | None,
	feat_names: Iterable[str] | None = None,
) -> TraitBundle:
	"""Collect merged senses/resistances/condition immunities from all sources."""
	senses: Dict[str, int] = {}
	resistances: Set[str] = set()
	immunities: Set[str] = set()
	if compendium is None:
		return TraitBundle(senses_ft=senses, resistances=resistances, condition_immunities=immunities)

	# Species and subtype.
	species_record, subtype_record = _find_species_record(compendium, species_name, species_subtype_name)
	for record in (species_record, subtype_record):
		_apply_trait_grants_from_record(record, senses, resistances, immunities)

	# Background.
	_apply_trait_grants_from_record(_find_background_record(compendium, background_name), senses, resistances, immunities)

	# Classes and subclasses.
	for entry in class_progression or []:
		class_name = str(getattr(entry, "name", "") or "").strip()
		if not class_name:
			continue
		_apply_trait_grants_from_record(compendium.class_record(class_name), senses, resistances, immunities)
		subclass_name = str(getattr(entry, "subclass", "") or "").strip()
		if subclass_name:
			_apply_trait_grants_from_record(
				compendium.subclass_record(class_name, subclass_name),
				senses,
				resistances,
				immunities,
			)

	# Feats.
	for feat_name in feat_names or []:
		name = str(feat_name or "").strip()
		if not name:
			continue
		_apply_trait_grants_from_record(compendium.feat_record(name), senses, resistances, immunities)

	return TraitBundle(senses_ft=senses, resistances=resistances, condition_immunities=immunities)


def collect_unquantifiable_modifiers(
	*,
	compendium: Compendium | None,
	species_name: str | None,
	species_subtype_name: str | None,
	background_name: str | None = None,
	class_progression: Iterable[object] | None,
	feat_names: Iterable[str] | None,
) -> List[str]:
	"""Collect non-quantifiable mechanics notes from active sources.

	This is intended for features like feats whose mechanical impact can't be
	expressed as numeric modifiers or simple structured grants.

	Schema (canonical):
	- `grants.unquantifiable_modifiers`: list[str]
	
	Back-compat / tolerated aliases (single string or list):
	- `grants.unquantifiable_modifier`
	- `grants.unqualifiable_modifier` (common typo)

	Merging rule: concatenate unique, non-empty strings.
	"""
	if compendium is None:
		return []

	out: List[str] = []
	seen: Set[str] = set()

	def _ingest(record: Mapping[str, object] | None) -> None:
		for note in _extract_unquantifiable_modifiers(record):
			key = note.strip().lower()
			if not key or key in seen:
				continue
			seen.add(key)
			out.append(note)

	# Species and subtype.
	species_record, subtype_record = _find_species_record(compendium, species_name, species_subtype_name)
	_ingest(species_record)
	_ingest(subtype_record)

	# Background.
	_ingest(_find_background_record(compendium, background_name))

	# Classes and subclasses.
	for entry in class_progression or []:
		class_name = str(getattr(entry, "name", "") or "").strip()
		if not class_name:
			continue
		_ingest(compendium.class_record(class_name))
		subclass_name = str(getattr(entry, "subclass", "") or "").strip()
		if subclass_name:
			_ingest(compendium.subclass_record(class_name, subclass_name))

	# Feats.
	for feat_name in feat_names or []:
		name = str(feat_name or "").strip()
		if not name:
			continue
		_ingest(compendium.feat_record(name))

	return out


def _apply_trait_grants_from_record(
	record: Mapping[str, object] | None,
	senses_out: Dict[str, int],
	resistances_out: Set[str],
	immunities_out: Set[str],
) -> None:
	if not isinstance(record, Mapping):
		return
	grants = record.get("grants")
	if not isinstance(grants, Mapping):
		return

	# Senses.
	raw_senses = grants.get("senses")
	if isinstance(raw_senses, Mapping):
		for key, value in raw_senses.items():
			name = str(key or "").strip()
			if not name:
				continue
			try:
				feet = int(value)
			except (TypeError, ValueError):
				feet = 0
			senses_out[name] = max(int(senses_out.get(name, 0) or 0), max(0, feet))

	# Resistances.
	raw_resist = grants.get("resistances")
	if isinstance(raw_resist, list):
		for entry in raw_resist:
			name = str(entry or "").strip().lower()
			if name:
				resistances_out.add(name)

	# Condition immunities.
	raw_imm = grants.get("condition_immunities")
	if isinstance(raw_imm, list):
		for entry in raw_imm:
			name = str(entry or "").strip().lower()
			if name:
				immunities_out.add(name)


def collect_speed_base_ft(
	*,
	compendium: Compendium | None,
	species_name: str | None,
	species_subtype_name: str | None,
	default_base_ft: int = 30,
) -> int:
	"""Collect the best/active base walking speed (override), before flat bonuses."""
	default_base = int(default_base_ft)
	if not (compendium and (species_name or "").strip()):
		return default_base
	species_record, subtype_record = _find_species_record(compendium, species_name, species_subtype_name)
	# Prefer subtype override, then species.
	for record in (subtype_record, species_record):
		if not isinstance(record, Mapping):
			continue
		# Prefer structured grants override if present.
		grants = record.get("grants")
		if isinstance(grants, Mapping):
			for key in ("speed_base_ft", "speed_override_ft"):
				value = grants.get(key)
				if isinstance(value, (int, float)):
					return int(value)
				if isinstance(value, str):
					try:
						return int(value.strip())
					except (TypeError, ValueError):
						pass
		# Legacy/top-level fields.
		raw = record.get("speed")
		if isinstance(raw, (int, float)):
			return int(raw)
		if isinstance(raw, str):
			try:
				return int(raw.strip())
			except (TypeError, ValueError):
				pass
		# Optional legacy additive bonus.
		raw_bonus = record.get("speed_bonus")
		if isinstance(raw_bonus, (int, float)):
			# Add to default unless we have a concrete base elsewhere.
			return int(default_base + int(raw_bonus))
		if isinstance(raw_bonus, str):
			try:
				return int(default_base + int(raw_bonus.strip()))
			except (TypeError, ValueError):
				pass
	return default_base


def _extract_unquantifiable_modifiers(record: Mapping[str, object] | None) -> List[str]:
	if not isinstance(record, Mapping):
		return []
	grants = record.get("grants")
	if not isinstance(grants, Mapping):
		return []

	def _as_list(value: object) -> List[str]:
		if value is None:
			return []
		if isinstance(value, str):
			note = value.strip()
			return [note] if note else []
		if isinstance(value, list):
			result: List[str] = []
			for entry in value:
				if isinstance(entry, str) and entry.strip():
					result.append(entry.strip())
			return result
		return []

	# Canonical + aliases.
	values: List[str] = []
	values.extend(_as_list(grants.get("unquantifiable_modifiers")))
	values.extend(_as_list(grants.get("unquantifiable_modifier")))
	values.extend(_as_list(grants.get("unqualifiable_modifier")))
	# De-dupe but preserve order.
	seen: Set[str] = set()
	out: List[str] = []
	for note in values:
		key = note.strip().lower()
		if not key or key in seen:
			continue
		seen.add(key)
		out.append(note.strip())
	return out


def collect_skill_rank_grants(
	*,
	compendium: Compendium | None,
	species_name: str | None,
	species_subtype_name: str | None,
	background_name: str | None = None,
	class_progression: Iterable[object] | None,
	feat_names: Iterable[str] | None = None,
) -> Dict[str, int]:
	"""Collect skill-rank (0/1/2) grants from all active sources.

	Schema (current): `grants.skills` can be either:
	- mapping: {"Perception": 1}
	- list: ["Perception", "Stealth"] (treated as rank 1)

	Merging rule: take max rank for each skill across sources.
	"""
	grants: Dict[str, int] = {}
	if compendium is None:
		return grants

	# Species and subtype.
	species_record, subtype_record = _find_species_record(compendium, species_name, species_subtype_name)
	for record in (species_record, subtype_record):
		_merge_skill_grants(grants, _extract_skill_ranks(record))

	# Background.
	_merge_skill_grants(grants, _extract_skill_ranks(_find_background_record(compendium, background_name)))

	# Classes and subclasses (future-friendly).
	for entry in class_progression or []:
		class_name = str(getattr(entry, "name", "") or "").strip()
		if not class_name:
			continue
		_merge_skill_grants(grants, _extract_skill_ranks(compendium.class_record(class_name)))
		subclass_name = str(getattr(entry, "subclass", "") or "").strip()
		if subclass_name:
			_merge_skill_grants(grants, _extract_skill_ranks(compendium.subclass_record(class_name, subclass_name)))

	# Feats.
	for feat_name in feat_names or []:
		name = str(feat_name or "").strip()
		if not name:
			continue
		_merge_skill_grants(grants, _extract_skill_ranks(compendium.feat_record(name)))

	return grants


def _merge_skill_grants(target: Dict[str, int], incoming: Dict[str, int]) -> None:
	for name, rank in (incoming or {}).items():
		label = str(name or "").strip()
		if not label:
			continue
		try:
			value = int(rank)
		except (TypeError, ValueError):
			value = 1
		value = max(0, min(value, 2))
		current = int(target.get(label, 0) or 0)
		if value > current:
			target[label] = value


def _extract_skill_ranks(record: Mapping[str, object] | None) -> Dict[str, int]:
	result: Dict[str, int] = {}
	if not isinstance(record, Mapping):
		return result
	grants = record.get("grants")
	if not isinstance(grants, Mapping):
		return result
	skills = grants.get("skills")
	if isinstance(skills, Mapping):
		for key, value in skills.items():
			name = str(key or "").strip()
			if not name:
				continue
			try:
				rank = int(value)
			except (TypeError, ValueError):
				rank = 1
			result[name] = max(result.get(name, 0), max(0, min(rank, 2)))
		return result
	if isinstance(skills, list):
		for entry in skills:
			name = str(entry or "").strip()
			if name:
				result[name] = max(result.get(name, 0), 1)
	return result


def _parse_spell_slot_level(key: str) -> int | None:
	# Accepted historical key patterns used by the UI.
	prefixes = (
		"spell_slot_",
		"spell_slots_",
		"slot_",
		"slots_",
		"slot_level_",
	)
	for prefix in prefixes:
		if not key.startswith(prefix):
			continue
		suffix = key[len(prefix) :].strip()
		try:
			level = int(suffix)
		except (TypeError, ValueError):
			return None
		return level if level > 0 else None
	return None


def _collect_compendium_bonuses(
	*,
	compendium: Compendium | None,
	species_name: str | None,
	species_subtype_name: str | None,
	background_name: str | None,
	class_progression: Iterable[object] | None,
	feat_names: Iterable[str] | None,
) -> Tuple[Dict[str, int], Dict[int, int]]:
	flat: Dict[str, int] = {}
	slots: Dict[int, int] = {}
	if compendium is None:
		return flat, slots

	# Species and subtype.
	species_record, subtype_record = _find_species_record(compendium, species_name, species_subtype_name)
	for record in (species_record, subtype_record):
		_rec_flat, _rec_slots = _extract_bonus_blocks(record)
		_merge_flat(flat, _rec_flat)
		_merge_slots(slots, _rec_slots)

	# Background.
	_rec_flat, _rec_slots = _extract_bonus_blocks(_find_background_record(compendium, background_name))
	_merge_flat(flat, _rec_flat)
	_merge_slots(slots, _rec_slots)

	# Classes + subclasses.
	for entry in class_progression or []:
		class_name = str(getattr(entry, "name", "") or "").strip()
		if not class_name:
			continue
		class_record = compendium.class_record(class_name)
		_rec_flat, _rec_slots = _extract_bonus_blocks(class_record)
		_merge_flat(flat, _rec_flat)
		_merge_slots(slots, _rec_slots)

		subclass_name = str(getattr(entry, "subclass", "") or "").strip()
		if subclass_name:
			sub_record = compendium.subclass_record(class_name, subclass_name)
			_rec_flat, _rec_slots = _extract_bonus_blocks(sub_record)
			_merge_flat(flat, _rec_flat)
			_merge_slots(slots, _rec_slots)

	# Feats.
	for feat_name in feat_names or []:
		name = str(feat_name or "").strip()
		if not name:
			continue
		_rec_flat, _rec_slots = _extract_bonus_blocks(compendium.feat_record(name))
		_merge_flat(flat, _rec_flat)
		_merge_slots(slots, _rec_slots)

	return flat, slots


def _extract_bonus_blocks(record: Mapping[str, object] | None) -> Tuple[Dict[str, int], Dict[int, int]]:
	flat: Dict[str, int] = {}
	slots: Dict[int, int] = {}
	if not isinstance(record, Mapping):
		return flat, slots
	grants = record.get("grants")
	if not isinstance(grants, Mapping):
		return flat, slots

	bonuses = grants.get("bonuses")
	if isinstance(bonuses, Mapping):
		for raw_key, raw_value in bonuses.items():
			key = str(raw_key or "").strip().lower()
			if not key:
				continue
			try:
				value = int(raw_value)
			except (TypeError, ValueError):
				continue
			canonical = _BONUS_KEY_ALIASES.get(key)
			if canonical:
				flat[canonical] = int(flat.get(canonical, 0) or 0) + value

	slot_bonuses = grants.get("spell_slots")
	if isinstance(slot_bonuses, Mapping):
		for raw_level, raw_value in slot_bonuses.items():
			try:
				lvl = int(str(raw_level).strip())
			except (TypeError, ValueError):
				continue
			if lvl <= 0:
				continue
			try:
				value = int(raw_value)
			except (TypeError, ValueError):
				continue
			slots[lvl] = int(slots.get(lvl, 0) or 0) + value

	return flat, slots


def _extract_ac_formulas(record: Mapping[str, object] | None) -> List[Mapping[str, object]]:
	if not isinstance(record, Mapping):
		return []
	grants = record.get("grants")
	if not isinstance(grants, Mapping):
		return []
	formulas = grants.get("armor_class_formulas")
	if isinstance(formulas, list):
		return [f for f in formulas if isinstance(f, Mapping)]
	formula = grants.get("armor_class_formula")
	if isinstance(formula, Mapping):
		return [formula]
	return []


def _find_species_record(
	compendium: Compendium,
	species_name: str | None,
	species_subtype_name: str | None,
) -> tuple[Mapping[str, object] | None, Mapping[str, object] | None]:
	name_key = (species_name or "").strip().lower()
	subtype_key = (species_subtype_name or "").strip().lower()
	if not name_key:
		return None, None
	for entry in compendium.records("species"):
		if not isinstance(entry, Mapping):
			continue
		name = entry.get("name")
		if not isinstance(name, str) or name.strip().lower() != name_key:
			continue
		if not subtype_key:
			return entry, None
		raw_subtypes = entry.get("subtypes")
		if isinstance(raw_subtypes, list):
			for subtype in raw_subtypes:
				if not isinstance(subtype, Mapping):
					continue
				st_name = subtype.get("name")
				if isinstance(st_name, str) and st_name.strip().lower() == subtype_key:
					return entry, subtype
		return entry, None
	return None, None


def _find_background_record(compendium: Compendium | None, background_name: str | None) -> Mapping[str, object] | None:
	if not (compendium and (background_name or "").strip()):
		return None
	name_key = (background_name or "").strip().lower()
	for entry in compendium.records("backgrounds"):
		if not isinstance(entry, Mapping):
			continue
		name = entry.get("name")
		if isinstance(name, str) and name.strip().lower() == name_key:
			return entry
	return None


__all__ = [
	"BonusBundle",
	"TraitBundle",
	"collect_ac_formula_candidates",
	"collect_bonus_bundle",
	"collect_trait_bundle",
	"collect_unquantifiable_modifiers",
	"collect_speed_base_ft",
	"collect_skill_rank_grants",
]
