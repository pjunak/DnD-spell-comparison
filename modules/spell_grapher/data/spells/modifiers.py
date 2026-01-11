"""Functions for computing modifier adjustments."""

from __future__ import annotations

from typing import Iterable

from modules.character_sheet.model import CharacterSheet


def equipment_damage_bonus(sheet: CharacterSheet) -> int:
    bonus = 0
    equipment = getattr(sheet, "equipment", []) or []
    for item in equipment:
        bonuses = getattr(item, "bonuses", {}) or {}
        for key, value in bonuses.items():
            key_name = str(key).lower()
            if key_name in {"spell_damage", "damage", "damage_bonus"}:
                try:
                    bonus += int(value)
                except (TypeError, ValueError):
                    continue
    return bonus


__all__ = ["equipment_damage_bonus"]
