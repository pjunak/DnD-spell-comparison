"""Derived damage resistances.

Minimal, structured (non-text-parsing) support for damage resistances granted by
species/subtype.

Data source:
- `species.grants.resistances`: list[str]
- `species.subtypes[].grants.resistances`: list[str]

This is currently intended for read-only display (and future combat logic).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Set, Tuple

from services.compendium import Compendium


@dataclass(frozen=True)
class ResistancesBreakdown:
	resistances: Set[str]

	def formatted(self) -> str:
		if not self.resistances:
			return "None"
		def _title(s: str) -> str:
			text = str(s).strip()
			return text[:1].upper() + text[1:] if text else text
		return ", ".join(_title(r) for r in sorted(self.resistances, key=lambda s: s.lower()))


def derive_resistances(
	*,
	compendium: Compendium | None,
	species_name: str | None,
	species_subtype_name: str | None = None,
) -> ResistancesBreakdown:
	record, subtype = _find_species_record(compendium, species_name, species_subtype_name)
	merged: Set[str] = set()
	for block in (record, subtype):
		if not block:
			continue
		grants = block.get("grants")
		if not isinstance(grants, Mapping):
			continue
		resistances = grants.get("resistances")
		if not isinstance(resistances, list):
			continue
		for entry in resistances:
			name = str(entry or "").strip().lower()
			if name:
				merged.add(name)
	return ResistancesBreakdown(resistances=merged)


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


__all__ = ["ResistancesBreakdown", "derive_resistances"]
