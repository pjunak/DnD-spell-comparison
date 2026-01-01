"""Utility functions for filtering spell records."""

from __future__ import annotations

from typing import Dict, Iterable, Mapping, Sequence, Set

FilterMap = Mapping[str, Set[str]]


_COMPONENT_KEYS = {"components"}
_LEVEL_KEYS = {"level"}


def _normalise(value: str) -> str:
    return (value or "").strip().lower()


def spell_matches_filters(spell: Mapping[str, object], filters: FilterMap) -> bool:
    """Return True when a spell dict satisfies all provided filters."""

    if not filters:
        return True

    for key, values in filters.items():
        if not values:
            continue
        key_lower = key.lower()
        if key_lower in _LEVEL_KEYS:
            spell_level = str(spell.get("level", ""))
            if spell_level not in values:
                return False
            continue
        if key_lower in _COMPONENT_KEYS:
            components = spell.get("components") or []
            if isinstance(components, str):
                items = {part.strip().lower() for part in components.split(',') if part.strip()}
            else:
                items = {str(part).strip().lower() for part in (components or [])}
            if not any(_normalise(value) in items for value in values):
                return False
            continue

        haystack = _normalise(str(spell.get(key) or spell.get(key_lower) or ""))
        if haystack:
            if any(_normalise(value) in haystack for value in values):
                continue
        return False

    return True


__all__ = ["spell_matches_filters"]
