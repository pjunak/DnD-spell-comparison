"""Derived condition immunities.

Structured (non-text-parsing) support for condition immunities granted by
species/subtype.

Data source:
- `species.grants.condition_immunities`: list[str]
- `species.subtypes[].grants.condition_immunities`: list[str]

Currently used for read-only display; intended for future combat logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Set, Tuple

from modules.compendium.service import Compendium


@dataclass(frozen=True)
class ConditionImmunitiesBreakdown:
	immunities: Set[str]

	def formatted(self) -> str:
		if not self.immunities:
			return "None"
		def _title(s: str) -> str:
			text = str(s).strip()
			return text[:1].upper() + text[1:] if text else text
		return ", ".join(_title(i) for i in sorted(self.immunities, key=lambda s: s.lower()))


def derive_condition_immunities(
	*,
	compendium: Compendium | None,
	species_name: str | None,
	species_subtype_name: str | None = None,
) -> ConditionImmunitiesBreakdown:
	record, subtype = _find_species_record(compendium, species_name, species_subtype_name)
	merged: Set[str] = set()
	for block in (record, subtype):
		if not block:
			continue
		grants = block.get("grants")
		if not isinstance(grants, Mapping):
			continue
		items = grants.get("condition_immunities")
		if not isinstance(items, list):
			continue
		for entry in items:
			name = str(entry or "").strip().lower()
			if name:
				merged.add(name)
	return ConditionImmunitiesBreakdown(immunities=merged)


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


__all__ = ["ConditionImmunitiesBreakdown", "derive_condition_immunities"]
