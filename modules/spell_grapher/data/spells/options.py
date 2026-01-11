"""Helpers for partitioning spell datasets and building filter metadata."""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

SpellRecord = Mapping[str, object]


def partition_spells(records: Iterable[SpellRecord]) -> Tuple[List[dict], List[dict]]:
    """Split spell records into leveled spells and cantrips."""

    spells: List[dict] = []
    cantrips: List[dict] = []
    for entry in records:
        level_value = entry.get("level", 0)
        target = cantrips if level_value in (None, "", 0) else spells
        target.append(entry)
    return spells, cantrips


def build_filter_labels(
    spells: Sequence[SpellRecord],
    *,
    include_levels: bool,
) -> Dict[str, List[str]]:
    """Generate distinct values for the filter widget labels."""

    unique_names = sorted({str(sp.get("name", "")) for sp in spells if sp.get("name")})
    unique_schools = sorted({str(sp.get("school", "")) for sp in spells if sp.get("school")})
    unique_ranges = sorted({str(sp.get("range", "")) for sp in spells if sp.get("range")})
    unique_casting = sorted({str(sp.get("casting_time", "")) for sp in spells if sp.get("casting_time")})
    unique_durations = sorted({str(sp.get("duration", "")) for sp in spells if sp.get("duration")})

    component_values = set()
    for spell in spells:
        components = spell.get("components") or []
        if isinstance(components, str):
            items = [part.strip() for part in components.split(",") if part.strip()]
        else:
            items = [str(part).strip() for part in components if str(part).strip()]
        component_values.update(items)
    unique_components = sorted(component_values)

    labels: Dict[str, List[str]] = {
        "name": unique_names,
        "school": unique_schools,
        "range": unique_ranges,
        "casting_time": unique_casting,
        "duration": unique_durations,
        "components": unique_components,
    }

    if include_levels:
        level_values = set()
        for spell in spells:
            raw_level = spell.get("level")
            if raw_level in (None, "", 0):
                continue
            level_values.add(str(raw_level))
        labels["level"] = sorted(level_values, key=lambda value: int(value) if value.isdigit() else value)

    return labels


__all__ = ["partition_spells", "build_filter_labels"]
