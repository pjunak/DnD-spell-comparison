"""Probability helpers shared by all presentation layers."""

from __future__ import annotations

from typing import Dict, Iterable

from .dices import combination_distribution


def _die_faces(die_value: int, constant_per_die: int) -> Iterable[int]:
    """Yield each die face after applying a per-die constant."""

    return (face + constant_per_die for face in range(1, die_value + 1))


def chain_spell_distribution(
    start_rolls: int,
    add_rolls: int,
    initial_dice_value: int,
    additional_dice_value: int,
    *,
    modifier: int = 0,
    levels: int = 1,
    constant_per_die: int = 0,
) -> Dict[int, float]:
    """Return the normalized outcome distribution for a spell across the requested levels."""

    initial_faces = list(_die_faces(initial_dice_value, constant_per_die))
    distribution = combination_distribution(initial_faces, start_rolls, modifier)

    additional_faces = list(_die_faces(additional_dice_value, constant_per_die))
    for _ in range(max(levels - 1, 0)):
        new_distribution: Dict[int, float] = {}
        extra_rolls = combination_distribution(additional_faces, add_rolls, 0)
        for current_total, current_prob in distribution.items():
            for added_total, added_prob in extra_rolls.items():
                total = current_total + added_total
                new_distribution[total] = new_distribution.get(total, 0.0) + current_prob * added_prob
        distribution = new_distribution

    total_probability = sum(distribution.values())
    if total_probability:
        distribution = {outcome: prob / total_probability for outcome, prob in distribution.items()}

    return distribution
