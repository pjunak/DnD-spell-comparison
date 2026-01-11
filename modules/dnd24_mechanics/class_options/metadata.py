"""Canonical class metadata for UI choices and spellcasting rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

CLASS_SUBCLASS_OPTIONS: Dict[str, List[str]] = {
    "Artificer": ["Alchemist", "Armorer", "Artillerist", "Battle Smith"],
    "Barbarian": [
        "Path of the Berserker",
        "Path of the Wild Heart",
        "Path of the World Tree",
        "Path of the Zealot",
    ],
    "Bard": ["College of Dance", "College of Glamour", "College of Lore", "College of Valor"],
    "Cleric": ["Life Domain", "Light Domain", "Trickery Domain", "War Domain"],
    "Druid": ["Circle of the Land", "Circle of the Moon", "Circle of the Sea", "Circle of the Stars"],
    "Fighter": ["Battle Master", "Champion", "Eldritch Knight", "Psi Warrior"],
    "Monk": [
        "Way of the Open Hand",
        "Way of Shadow",
        "Way of the Elements",
        "Way of Mercy",
    ],
    "Paladin": ["Oath of Devotion", "Oath of Glory", "Oath of the Ancients", "Oath of Vengeance"],
    "Ranger": ["Beast Master", "Fey Wanderer", "Gloom Stalker", "Hunter"],
    "Rogue": ["Arcane Trickster", "Assassin", "Swashbuckler", "Thief"],
    "Sorcerer": ["Aberrant Mind", "Clockwork Soul", "Draconic Bloodline", "Wild Magic"],
    "Warlock": ["The Archfey", "The Celestial", "The Fiend", "The Great Old One", "The Hexblade"],
    "Wizard": [
        "School of Abjuration",
        "School of Divination",
        "School of Evocation",
        "School of Illusion",
    ],
}

CLASS_NAME_OPTIONS: List[str] = list(CLASS_SUBCLASS_OPTIONS.keys())


@dataclass(frozen=True)
class SpellcastingDefinition:
    ability: Optional[str]
    mode: str  # "prepared", "known", "none"

    def is_caster(self) -> bool:
        return bool(self.ability)


SPELLCASTING_NONE = SpellcastingDefinition(None, "none")

CLASS_SPELLCASTING: Dict[str, SpellcastingDefinition] = {
    "artificer": SpellcastingDefinition("INT", "prepared"),
    "bard": SpellcastingDefinition("CHA", "known"),
    "cleric": SpellcastingDefinition("WIS", "prepared"),
    "druid": SpellcastingDefinition("WIS", "prepared"),
    "paladin": SpellcastingDefinition("CHA", "prepared"),
    "ranger": SpellcastingDefinition("WIS", "prepared"),
    "sorcerer": SpellcastingDefinition("CHA", "known"),
    "warlock": SpellcastingDefinition("CHA", "known"),
    "wizard": SpellcastingDefinition("INT", "prepared"),
}

# Martial subclasses that gain spellcasting use subclass-specific abilities.
SUBCLASS_SPELLCASTING: Dict[Tuple[str, str], SpellcastingDefinition] = {
    ("fighter", "eldritch knight"): SpellcastingDefinition("INT", "known"),
    ("rogue", "arcane trickster"): SpellcastingDefinition("INT", "known"),
}


def normalise_class_name(name: str | None) -> str:
    return (name or "").strip().lower()


def normalise_subclass_name(name: str | None) -> str:
    return (name or "").strip().lower()


def subclass_options_for(class_name: str | None) -> List[str]:
    key = normalise_class_name(class_name)
    for name, subclasses in CLASS_SUBCLASS_OPTIONS.items():
        if name.lower() == key:
            return list(subclasses)
    return []


def class_spellcasting_definition(class_name: str | None) -> SpellcastingDefinition:
    return CLASS_SPELLCASTING.get(normalise_class_name(class_name), SPELLCASTING_NONE)


def subclass_spellcasting_definition(class_name: str | None, subclass_name: str | None) -> SpellcastingDefinition:
    key = (normalise_class_name(class_name), normalise_subclass_name(subclass_name))
    return SUBCLASS_SPELLCASTING.get(key, SPELLCASTING_NONE)


def resolve_spellcasting_definition(class_name: str | None, subclass_name: str | None = None) -> SpellcastingDefinition:
    subclass_def = subclass_spellcasting_definition(class_name, subclass_name)
    if subclass_def.is_caster():
        return subclass_def
    return class_spellcasting_definition(class_name)


__all__ = [
    "CLASS_SUBCLASS_OPTIONS",
    "CLASS_NAME_OPTIONS",
    "SpellcastingDefinition",
    "class_spellcasting_definition",
    "subclass_spellcasting_definition",
    "resolve_spellcasting_definition",
    "subclass_options_for",
    "normalise_class_name",
    "normalise_subclass_name",
]
