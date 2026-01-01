"""Helpers for distilling a CharacterSheet into spellcasting data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .model import CharacterSheet, SpellAccessEntry


@dataclass
class SpellcastingProfile:
    character_name: str
    level: int
    proficiency_bonus: int
    spellcasting_ability: str
    spell_attack_bonus: int
    spell_save_dc: int
    ability_modifier: int
    known_spells: List[SpellAccessEntry] = field(default_factory=list)
    spell_slots: dict[int, int] = field(default_factory=dict)


def build_spellcasting_profile(sheet: CharacterSheet) -> SpellcastingProfile:
    ability = sheet.spellcasting.spellcasting_ability.upper()
    ability_block = sheet.get_ability(ability)
    ability_mod = ability_block.effective_modifier()
    proficiency_bonus = sheet.proficiency_bonus()
    attack_bonus = sheet.spellcasting.attack_bonus
    save_dc = sheet.spellcasting.save_dc

    if attack_bonus is None:
        attack_bonus = ability_mod + proficiency_bonus
    if save_dc is None:
        save_dc = 8 + ability_mod + proficiency_bonus

    return SpellcastingProfile(
        character_name=sheet.identity.name or "Unnamed Adventurer",
        level=sheet.identity.level,
        proficiency_bonus=proficiency_bonus,
        spellcasting_ability=ability,
        spell_attack_bonus=attack_bonus,
        spell_save_dc=save_dc,
        ability_modifier=ability_mod,
        known_spells=list(sheet.spellcasting.known_spells),
        spell_slots=dict(sheet.spellcasting.spell_slots),
    )


__all__ = ["SpellcastingProfile", "build_spellcasting_profile"]
