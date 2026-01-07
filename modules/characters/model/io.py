"""Import/export helpers for interacting with the PHB 2024 PDF form."""

from __future__ import annotations

import re
from typing import Iterable, Mapping, MutableMapping, Optional

from .model import (
    ABILITY_NAMES,
    AbilityBlock,
    CharacterSheet,
    ClassProgression,
    EquipmentItem,
    FeatureEntry,
    ResourcePool,
    SpellAccessEntry,
)

# Default field names inferred from the official PDF. The mapping can be
# overridden by consumers if Wizards updates the sheet again.
PDF_FIELD_MAP: Mapping[str, str] = {
    "CharacterName": "identity.name",
    "ClassLevel": "identity.classes",
    "Background": "identity.background",
    "Ancestry": "identity.ancestry",
    "PlayerName": "identity.player",
    "Alignment": "identity.alignment",
    "ExperiencePoints": "identity.experience",
    "ArmorClass": "combat.armor_class",
    "Initiative": "combat.initiative_bonus",
    "Speed": "combat.speed_ft",
    "MaxHP": "combat.max_hp",
    "CurrentHP": "combat.current_hp",
    "TempHP": "combat.temp_hp",
    "HitDice": "combat.hit_dice",
    "DeathSaveSuccesses": "combat.death_save_successes",
    "DeathSaveFailures": "combat.death_save_failures",
    "ProficiencyBonus": "proficiencies.proficiency_bonus",
    "SpellcastingAbility": "spellcasting.spellcasting_ability",
    "SpellAttackBonus": "spellcasting.attack_bonus",
    "SpellSaveDC": "spellcasting.save_dc",
}

for ability in ABILITY_NAMES:
    PDF_FIELD_MAP |= {
        f"{ability}Score": f"abilities.{ability}.score",
        f"{ability}Modifier": f"abilities.{ability}.modifier",
        f"{ability}SaveProf": f"abilities.{ability}.save_proficient",
        f"{ability}SaveBonus": f"abilities.{ability}.save_bonus",
    }


CLASS_SPLIT_PATTERN = re.compile(r"[,/]+")


def parse_class_summary(summary: str) -> Iterable[ClassProgression]:
    entries: list[ClassProgression] = []
    for chunk in CLASS_SPLIT_PATTERN.split(summary or ""):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split()
        if len(parts) < 2:
            continue
        try:
            level = int(parts[-1])
        except ValueError:
            level = 0
        name = " ".join(parts[:-1])
        entries.append(ClassProgression(name=name, level=level))
    return entries


def format_class_summary(classes: Iterable[ClassProgression]) -> str:
    return " / ".join(f"{entry.name} {entry.level}" for entry in classes if entry.level)


class CharacterSheetParser:
    def __init__(self, field_map: Optional[Mapping[str, str]] = None) -> None:
        self.field_map = dict(field_map or PDF_FIELD_MAP)

    def parse(self, fields: Mapping[str, str]) -> CharacterSheet:
        sheet = CharacterSheet()
        for key, value in fields.items():
            attr_path = self.field_map.get(key)
            if not attr_path:
                continue
            self._apply(sheet, attr_path, value)
        return sheet

    def _apply(self, sheet: CharacterSheet, path: str, raw_value: str) -> None:
        parts = path.split(".")
        target = sheet
        for segment in parts[:-1]:
            if segment == "identity.classes":
                raise ValueError("classes path cannot be intermediate")
            target = getattr(target, segment)
        leaf = parts[-1]
        if path == "identity.classes":
            target.classes = list(parse_class_summary(raw_value))
            return
        existing = getattr(target, leaf)
        if isinstance(existing, bool):
            value = raw_value.lower() in {"true", "1", "yes", "on"}
        elif isinstance(existing, int):
            try:
                value = int(raw_value)
            except ValueError:
                value = existing
        elif isinstance(existing, float):
            try:
                value = float(raw_value)
            except ValueError:
                value = existing
        else:
            value = raw_value
        setattr(target, leaf, value)


class CharacterSheetSerializer:
    def __init__(self, field_map: Optional[Mapping[str, str]] = None) -> None:
        self.field_map = dict(field_map or PDF_FIELD_MAP)

    def serialise(self, sheet: CharacterSheet) -> MutableMapping[str, str]:
        payload: MutableMapping[str, str] = {}
        for form_field, path in self.field_map.items():
            payload[form_field] = self._extract(sheet, path)
        return payload

    def _extract(self, sheet: CharacterSheet, path: str) -> str:
        if path == "identity.classes":
            return format_class_summary(sheet.identity.classes)
        parts = path.split(".")
        value = sheet
        for segment in parts:
            value = getattr(value, segment)
        if isinstance(value, bool):
            return "Yes" if value else ""
        return str(value)


__all__ = [
    "CharacterSheetParser",
    "CharacterSheetSerializer",
    "PDF_FIELD_MAP",
    "parse_class_summary",
    "format_class_summary",
    "AbilityBlock",
    "EquipmentItem",
    "FeatureEntry",
    "ResourcePool",
    "SpellAccessEntry",
]
