"""Formatting helpers for presenting spell details."""

from __future__ import annotations

import json
from typing import Dict, List


def _stringify_value(value) -> str:
    if value in (None, ""):
        return "None"
    if isinstance(value, (list, dict)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)
    return str(value)


def _format_damage_block(payload) -> str:
    if not isinstance(payload, dict):
        return _stringify_value(payload)
    parts: List[str] = []
    base = payload.get("base") or {}
    dice = base.get("dice")
    die = base.get("die")
    if dice and die:
        parts.append(f"{dice}d{die}")
    scaling = payload.get("scaling") or {}
    add_dice = scaling.get("dice_per_slot")
    add_die = scaling.get("die")
    if add_dice and add_die:
        parts.append(f"+ {add_dice}d{add_die} per slot")
    constant = payload.get("constant")
    if isinstance(constant, (int, float)) and constant:
        parts.append(f"+ {constant}")
    add_constant = scaling.get("constant_per_slot")
    if isinstance(add_constant, (int, float)) and add_constant:
        parts.append(f"+ {add_constant} per slot")
    if payload.get("use_modifier"):
        parts.append("+ ability modifier")
    damage_type = payload.get("type")
    summary = " ".join(parts) if parts else _stringify_value({k: v for k, v in payload.items() if k not in {"type"}})
    if damage_type:
        return f"{str(damage_type).title()} ({summary})" if summary else str(damage_type).title()
    return summary


def _summarise_effect_data(effect_data: Dict, *, indent: str = "") -> List[str]:
    lines: List[str] = []
    if not effect_data:
        return lines
    damage = effect_data.get("damage")
    if damage:
        lines.append(f"{indent}Damage: {_format_damage_block(damage)}")
    healing = effect_data.get("healing")
    if healing:
        lines.append(f"{indent}Healing: {_format_damage_block(healing)}")
    for key, value in effect_data.items():
        if key in {"damage", "healing"}:
            continue
        label = key.replace("_", " ").title()
        lines.append(f"{indent}{label}: {_stringify_value(value)}")
    return lines


def format_spell_details(spell: Dict) -> str:
    lines: List[str] = []
    name = spell.get("name", "Unknown")
    level_value = spell.get("level")
    level_text = "Cantrip" if not level_value else f"Level {level_value}"
    school = spell.get("school") or ""
    lines.append(f"Name: {name}")
    lines.append(f"Level: {level_text}")
    if school:
        lines.append(f"School: {school}")
    casting = spell.get("casting_time") or "Unknown"
    lines.append(f"Casting Time: {casting}")
    rng = spell.get("range") or "Unknown"
    lines.append(f"Range: {rng}")
    duration = spell.get("duration") or "Unknown"
    lines.append(f"Duration: {duration}")
    components = spell.get("components")
    if isinstance(components, list):
        comp_text = ", ".join(components) if components else "None"
    elif components:
        comp_text = str(components)
    else:
        comp_text = "None"
    lines.append(f"Components: {comp_text}")

    modifiers = spell.get("modifiers") or []
    lines.append("")
    lines.append("Modifiers:")
    if not modifiers:
        lines.append("  None")
    else:
        for modifier in modifiers:
            label = modifier.get("name", "Unnamed Modifier")
            category = modifier.get("category")
            scope = modifier.get("scope")
            suffix_bits = []
            if category:
                suffix_bits.append(str(category).title())
            if scope and str(scope).lower() != "spell":
                suffix_bits.append(str(scope).title())
            suffix = f" ({', '.join(suffix_bits)})" if suffix_bits else ""
            lines.append(f"  - {label}{suffix}")

    effects = spell.get("effects") or []
    lines.append("")
    lines.append("Effects:")
    if not effects:
        lines.append("  None")
    else:
        for effect in effects:
            effect_type = str(effect.get("effect_type", "Effect")).replace("_", " ").title()
            lines.append(f"  {effect_type}:")
            description = effect.get("description")
            if description:
                lines.append(f"    {description}")
            effect_data = effect.get("effect_data") or {}
            lines.extend(_summarise_effect_data(effect_data, indent="    "))
            resolution = effect.get("resolution")
            if resolution:
                lines.append(f"    Resolution: {_stringify_value(resolution)}")
            repeat = effect.get("repeat")
            if repeat:
                lines.append(f"    Repeat: {_stringify_value(repeat)}")

    return "\n".join(line for line in lines if line is not None).strip()


__all__ = ["format_spell_details"]
