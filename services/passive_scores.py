"""Passive score derivation.

Computes passive scores (e.g., Passive Perception) from the character sheet.

This is designed to be reused by:
- the character sheet UI (read-only display)
- compendium/rules validation
- future combat/exploration helpers

Rules implemented (minimal):
- Passive score = 10 + relevant skill bonus

Skill bonus is derived from:
- relevant ability modifier (with optional +score bonuses applied non-destructively)
- proficiency bonus multiplied by rank (0/1/2) when `sheet.proficiencies.skills` is a rank map
- OR treated as already-final bonus when `sheet.proficiencies.skills` is not a rank map

Notes:
- This does not yet model temporary bonuses/penalties beyond what is represented on the sheet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from character_sheet import CharacterSheet


_SKILL_TO_ABILITY: Dict[str, str] = {
	"Perception": "WIS",
	"Investigation": "INT",
	"Insight": "WIS",
}


def _normalise_name(name: str) -> str:
	return (name or "").strip().lower()


@dataclass(frozen=True)
class PassiveScores:
	perception: int
	investigation: int
	insight: int


def derive_passive_scores(
	sheet: CharacterSheet,
	*,
	ability_score_bonuses: Dict[str, int] | None = None,
) -> PassiveScores:
	bonuses = {str(k).upper(): int(v) for k, v in (ability_score_bonuses or {}).items() if str(k).strip()}
	prof_bonus = int(getattr(sheet.proficiencies, "proficiency_bonus", 0) or 0)

	def effective_ability_mod(ability: str) -> int:
		key = str(ability).upper()
		block = sheet.get_ability(key)
		if block.modifier is not None:
			return int(block.modifier)
		score = int(block.score) + int(bonuses.get(key, 0) or 0)
		return (score - 10) // 2

	skill_map = dict(sheet.proficiencies.skills or {})
	is_rank_map = True
	for value in skill_map.values():
		try:
			numeric = int(value)
		except (TypeError, ValueError):
			is_rank_map = False
			break
		if numeric not in (0, 1, 2):
			is_rank_map = False
			break

	def skill_bonus(skill: str) -> int:
		ability = _SKILL_TO_ABILITY.get(skill)
		if not ability:
			return 0
		ability_mod = effective_ability_mod(ability)
		if is_rank_map:
			rank = int(skill_map.get(skill, skill_map.get(_normalise_name(skill), 0)) or 0)
			rank = max(0, min(rank, 2))
			return int(ability_mod + prof_bonus * rank)
		# already-final bonus map
		value = skill_map.get(skill)
		if value is None:
			value = skill_map.get(_normalise_name(skill))
		if value is None:
			return int(ability_mod)
		try:
			return int(value)
		except (TypeError, ValueError):
			return int(ability_mod)

	per = 10 + skill_bonus("Perception")
	inv = 10 + skill_bonus("Investigation")
	ins = 10 + skill_bonus("Insight")
	return PassiveScores(perception=int(per), investigation=int(inv), insight=int(ins))


__all__ = ["PassiveScores", "derive_passive_scores"]
