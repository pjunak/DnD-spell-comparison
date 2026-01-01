"""Access helpers for compendium-backed rule data (advancement, point-buy, etc.)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Mapping, Optional

from .compendium import Compendium

_DEFAULT_MAX_CHARACTER_LEVEL = 20


@dataclass(frozen=True)
class PointBuyRules:
    pool: int
    min_score: int
    max_score: int
    costs: Dict[int, int]
    asi_levels: List[int]
    asi_or_feat_choice: bool


def max_character_level() -> int:
    """Return the maximum supported character level from the rules payload."""

    block = _advancement_rules()
    value = block.get("max_level")
    if isinstance(value, int) and value >= 1:
        return value
    return _DEFAULT_MAX_CHARACTER_LEVEL


@lru_cache(maxsize=1)
def point_buy_rules() -> Optional[PointBuyRules]:
    """Return structured point-buy rules if available in the compendium."""

    block = _point_buy_rules()
    if not block:
        return None

    try:
        pool = int(block.get("pool", 0) or 0)
        min_score = int(block.get("min_score", 8) or 8)
        max_score = int(block.get("max_score", 15) or 15)
    except (TypeError, ValueError):
        return None

    raw_costs = block.get("costs", {}) or {}
    costs: Dict[int, int] = {}
    for key, value in raw_costs.items():
        try:
            score = int(key)
            cost = int(value)
        except (TypeError, ValueError):
            continue
        if cost < 0:
            continue
        costs[score] = cost

    if not costs:
        return None

    levels = [
        level
        for level in block.get("ability_score_increase_levels", []) or []
        if isinstance(level, int) and level > 0
    ]
    levels.sort()
    asi_or_feat = bool(block.get("asi_or_feat_choice", False))

    return PointBuyRules(
        pool=max(pool, 0),
        min_score=min_score,
        max_score=max(max_score, min_score),
        costs=costs,
        asi_levels=levels,
        asi_or_feat_choice=asi_or_feat,
    )


@lru_cache(maxsize=1)
def _rules_payload() -> Mapping[str, Any]:
    try:
        compendium = Compendium.load()
    except FileNotFoundError:
        return {}
    rules = compendium.payload.get("rules", {})
    return rules if isinstance(rules, Mapping) else {}


def _advancement_rules() -> Mapping[str, Any]:
    rules = _rules_payload()
    block = rules.get("advancement") if isinstance(rules, Mapping) else None
    return block if isinstance(block, Mapping) else {}


def _point_buy_rules() -> Mapping[str, Any]:
    rules = _rules_payload()
    block = rules.get("character_creation/point_buy") if isinstance(rules, Mapping) else None
    if not isinstance(block, Mapping):
        block = rules.get("point_buy") if isinstance(rules, Mapping) else None
    return block if isinstance(block, Mapping) else {}


__all__ = ["max_character_level", "point_buy_rules", "PointBuyRules"]
