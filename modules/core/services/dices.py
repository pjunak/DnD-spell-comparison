"""Small helpers for probability distributions over custom dice."""

from __future__ import annotations

from typing import Dict, Iterable


def combination_distribution(dice: Iterable[int], rolls: int, modifier: int = 0) -> Dict[int, float]:
    """Return the probability distribution for *rolls* dice picked from *dice* faces."""

    faces = list(dice)
    if not faces or rolls <= 0:
        return {}

    dist: Dict[int, float] = {}
    for outcome in faces:
        total = outcome + modifier
        dist[total] = dist.get(total, 0.0) + 1.0
    for _ in range(rolls - 1):
        new_dist: Dict[int, float] = {}
        for current_sum, count in dist.items():
            for outcome in faces:
                new_total = current_sum + outcome
                new_dist[new_total] = new_dist.get(new_total, 0.0) + count
        dist = new_dist
    total_outcomes = float(len(faces) ** rolls)
    for key in dist:
        dist[key] /= total_outcomes
    return dist
