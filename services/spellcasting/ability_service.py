"""Derive spellcasting abilities from class and subclass progressions."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Mapping, Sequence

from modules.characters.model import ClassProgression
from services.class_options import normalise_class_name, normalise_subclass_name
from modules.compendium.service import Compendium


@dataclass(frozen=True)
class SpellcastingSourceInfo:
    key: str
    source_type: str  # "class" or "subclass"
    label: str
    ability: str
    mode: str
    class_name: str
    subclass_name: str | None
    level: int


@dataclass(frozen=True)
class DerivedSpellcastingProfile:
    ability: str
    primary_source: SpellcastingSourceInfo | None
    sources: Dict[str, SpellcastingSourceInfo]

    @property
    def has_prepared_source(self) -> bool:
        return any(source.mode == "prepared" for source in self.sources.values())


def derive_spellcasting_profile(
    classes: Sequence[ClassProgression],
    fallback_ability: str | None = None,
) -> DerivedSpellcastingProfile:
    fallback = (fallback_ability or "INT").upper()
    aggregated: Dict[str, SpellcastingSourceInfo] = {}
    mutable_levels: Dict[str, int] = {}

    for entry in classes:
        class_name = entry.name or ""
        subclass_name = entry.subclass or ""
        source_type, spellcasting = _spellcasting_for_entry(class_name, subclass_name)
        ability = str(spellcasting.get("ability", "") or "").upper()
        if not ability:
            continue
        prepared = bool(spellcasting.get("prepared", False))
        mode = "prepared" if prepared else "known"
        class_key = normalise_class_name(class_name)
        if source_type == "subclass":
            sub_key = normalise_subclass_name(subclass_name)
            key = f"subclass:{class_key}:{sub_key}"
            label = f"{subclass_name or ''} ({class_name})".strip()
        else:
            key = f"class:{class_key}"
            label = class_name
        mutable_levels[key] = mutable_levels.get(key, 0) + max(0, int(entry.level))
        aggregated[key] = SpellcastingSourceInfo(
            key=key,
            source_type=source_type,
            label=label or class_name or "Unknown Source",
            ability=ability,
            mode=mode,
            class_name=class_name,
            subclass_name=subclass_name or None,
            level=mutable_levels[key],
        )

    primary = _select_primary_source(aggregated)
    ability = (primary.ability if primary else fallback).upper()
    return DerivedSpellcastingProfile(ability=ability, primary_source=primary, sources=aggregated)


@lru_cache(maxsize=1)
def _compendium() -> Compendium | None:
    try:
        return Compendium.load()
    except Exception:
        return None


def _spellcasting_mapping(record: Mapping[str, object] | None) -> Mapping[str, object]:
    if not record:
        return {}
    spellcasting = record.get("spellcasting")
    return spellcasting if isinstance(spellcasting, Mapping) else {}


def _spellcasting_for_entry(class_name: str, subclass_name: str | None) -> tuple[str, Mapping[str, object]]:
    compendium = _compendium()
    if compendium:
        if subclass_name:
            subclass = compendium.subclass_record(class_name, subclass_name)
            mapping = _spellcasting_mapping(subclass)
            if mapping.get("ability"):
                return "subclass", mapping
        klass = compendium.class_record(class_name)
        mapping = _spellcasting_mapping(klass)
        if mapping.get("ability"):
            return "class", mapping
    return "class", {}


def _select_primary_source(sources: Dict[str, SpellcastingSourceInfo]) -> SpellcastingSourceInfo | None:
    priority = {"prepared": 2, "known": 1, "none": 0}
    best: SpellcastingSourceInfo | None = None
    for source in sources.values():
        if not best:
            best = source
            continue
        if source.level > best.level:
            best = source
            continue
        if source.level == best.level:
            if priority.get(source.mode, 0) > priority.get(best.mode, 0):
                best = source
    return best


__all__ = [
    "DerivedSpellcastingProfile",
    "SpellcastingSourceInfo",
    "derive_spellcasting_profile",
]
