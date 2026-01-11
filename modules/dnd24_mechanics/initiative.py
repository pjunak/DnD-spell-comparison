"""Initiative derivation.

Minimal implementation:
- Initiative bonus = DEX modifier + flat bonuses (equipment/other)

This is intentionally small and reusable across UI, exports, and future combat tooling.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InitiativeBreakdown:
	dex_modifier: int
	equipment_bonus: int
	other_bonus: int
	total: int


def derive_initiative_bonus(
	*,
	dex_modifier: int,
	equipment_bonus: int = 0,
	other_bonus: int = 0,
) -> InitiativeBreakdown:
	dex = int(dex_modifier or 0)
	eq = int(equipment_bonus or 0)
	other = int(other_bonus or 0)
	total = dex + eq + other
	return InitiativeBreakdown(dex_modifier=dex, equipment_bonus=eq, other_bonus=other, total=total)


__all__ = ["InitiativeBreakdown", "derive_initiative_bonus"]
