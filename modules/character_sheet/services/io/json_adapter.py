"""Import/export helpers for character sheet JSON payloads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from modules.character_sheet.model import (
    CharacterSheet,
    character_sheet_from_dict,
    character_sheet_to_dict,
)


@dataclass
class CharacterPackage:
    """Bundle of a sheet and modifier states."""

    sheet: CharacterSheet
    modifiers: Dict[str, bool]


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _ensure_path(path_like) -> Path:
    path = Path(path_like)
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def load_character_package(path_like) -> CharacterPackage:
    """Load a character sheet + modifier state from JSON."""

    path = _ensure_path(path_like)
    payload = _read_json(path)

    if isinstance(payload, dict) and "character_sheet" in payload:
        sheet_payload = payload.get("character_sheet", {}) or {}
        modifiers_payload = payload.get("modifiers", {}) or {}
    else:
        sheet_payload = payload or {}
        modifiers_payload = {}

    sheet = character_sheet_from_dict(sheet_payload)

    modifiers: Dict[str, bool] = {}
    if isinstance(modifiers_payload, dict):
        for name, enabled in modifiers_payload.items():
            modifiers[str(name)] = bool(enabled)

    return CharacterPackage(sheet=sheet, modifiers=modifiers)


def save_character_package(path_like, sheet: CharacterSheet, modifiers: Dict[str, bool]) -> Path:
    """Persist a character and its modifier states to JSON."""

    path = Path(path_like)
    payload = {
        "character_sheet": character_sheet_to_dict(sheet),
        "modifiers": dict(modifiers),
    }

    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    return path


__all__ = [
    "CharacterPackage",
    "load_character_package",
    "save_character_package",
]
