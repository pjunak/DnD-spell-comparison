"""Species-derived grants.

This module provides minimal, structured (non-text-parsing) grants derived from
selected species and species subtype records in the compendium.

Initial scope:
- Granting skill proficiencies (rank map 0/1/2) such as Elf "Keen Senses".

Design notes:
- We only apply grants when the sheet is using a rank-map representation for
  `sheet.proficiencies.skills` (0/1/2) or when it is empty.
- If the sheet stores skills as already-final bonuses, we leave it untouched.
"""

from __future__ import annotations

from typing import Dict, Mapping, Tuple

from modules.compendium.service import Compendium


def derive_species_skill_ranks(
	*,
	compendium: Compendium | None,
	species_name: str | None,
	species_subtype_name: str | None = None,
) -> Dict[str, int]:
	"""Return a map of skill -> minimum rank granted by species/subtype."""
	record, subtype = _find_species_record(compendium, species_name, species_subtype_name)
	grants: Dict[str, int] = {}
	for block in (record, subtype):
		if not block:
			continue
		block_grants = block.get("grants")
		if not isinstance(block_grants, Mapping):
			continue
		skills = block_grants.get("skills")
		if isinstance(skills, Mapping):
			for key, value in skills.items():
				name = str(key or "").strip()
				if not name:
					continue
				try:
					rank = int(value)
				except (TypeError, ValueError):
					rank = 1
				grants[name] = max(grants.get(name, 0), max(0, min(rank, 2)))
		elif isinstance(skills, list):
			for entry in skills:
				name = str(entry or "").strip()
				if not name:
					continue
				grants[name] = max(grants.get(name, 0), 1)
	return grants


def apply_species_skill_grants(
	*,
	current_skill_map: Dict[str, int] | None,
	granted_skill_ranks: Dict[str, int] | None,
) -> Tuple[Dict[str, int], bool]:
	"""Apply grants to an existing rank-map, returning (new_map, changed)."""
	base = dict(current_skill_map or {})
	grants = dict(granted_skill_ranks or {})
	changed = False
	for skill, min_rank in grants.items():
		try:
			target = int(min_rank)
		except (TypeError, ValueError):
			target = 1
		target = max(0, min(target, 2))
		try:
			current = int(base.get(skill, 0) or 0)
		except (TypeError, ValueError):
			current = 0
		if current < target:
			base[skill] = target
			changed = True
	return base, changed


def _find_species_record(
	compendium: Compendium | None,
	species_name: str | None,
	species_subtype_name: str | None,
) -> Tuple[Mapping[str, object] | None, Mapping[str, object] | None]:
	if not (compendium and (species_name or "").strip()):
		return None, None
	name_key = (species_name or "").strip().lower()
	subtype_key = (species_subtype_name or "").strip().lower()
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


__all__ = ["apply_species_skill_grants", "derive_species_skill_ranks"]
