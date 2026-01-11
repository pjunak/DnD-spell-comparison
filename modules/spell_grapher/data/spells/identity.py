"""Helpers to uniquely identify spells."""

from __future__ import annotations

from typing import Dict


def spell_identity(spell: Dict) -> str:
    spell_id = spell.get("id")
    if spell_id is not None:
        return f"id:{spell_id}"
    name = spell.get("name", "")
    level = spell.get("level", "")
    school = spell.get("school", "")
    return f"name:{name}|level:{level}|school:{school}"


__all__ = ["spell_identity"]
