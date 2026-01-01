"""Derived senses.

Minimal, structured (non-text-parsing) support for senses granted by species/subtype.

Data source:
- `species.grants.senses`: mapping of sense name -> range (feet)
- `species.subtypes[].grants.senses`: same

This is intentionally read-only/derived and is primarily used for display.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Tuple

from services.compendium import Compendium


@dataclass(frozen=True)
class SensesBreakdown:
	senses_ft: Dict[str, int]

	def formatted(self) -> str:
		if not self.senses_ft:
			return "None"
		parts = []
		for name, feet in sorted(self.senses_ft.items(), key=lambda kv: kv[0].lower()):
			label = str(name).strip()
			try:
				dist = int(feet)
			except (TypeError, ValueError):
				dist = 0
			if dist > 0:
				parts.append(f"{label} {dist} ft")
			else:
				parts.append(label)
		return ", ".join(parts) if parts else "None"


def derive_senses(
	*,
	compendium: Compendium | None,
	species_name: str | None,
	species_subtype_name: str | None = None,
) -> SensesBreakdown:
	record, subtype = _find_species_record(compendium, species_name, species_subtype_name)
	merged: Dict[str, int] = {}
	for block in (record, subtype):
		if not block:
			continue
		grants = block.get("grants")
		if not isinstance(grants, Mapping):
			continue
		senses = grants.get("senses")
		if not isinstance(senses, Mapping):
			continue
		for key, value in senses.items():
			name = str(key or "").strip()
			if not name:
				continue
			try:
				feet = int(value)
			except (TypeError, ValueError):
				feet = 0
			merged[name] = max(merged.get(name, 0), max(0, feet))
	return SensesBreakdown(senses_ft=merged)


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


__all__ = ["SensesBreakdown", "derive_senses"]
