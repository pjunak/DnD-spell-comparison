"""Built-in modifier definitions.

These are shipped with the app and act as a fallback when the user modifier
store is empty.
"""

from __future__ import annotations

from typing import List


def get_default_modifier_definitions() -> List[dict]:
	"""Return the built-in list of modifier definitions."""
	return [
		{
			"name": "Agonizing Blast",
			"category": "invocation",
			"scope": "spell",
			"description": "Eldritch invocation that adds the caster's ability modifier to Eldritch Blast damage.",
			"default_enabled": False,
			"applies_to": [
				{
					"scope": "spell",
					"effect_type": "multi_beam",
				},
				{
					"spell_names": ["Eldritch Blast"],
				},
			],
			"effect_data": {
				"ability_modifier": "charisma",
				"apply_per_beam": True,
			},
		},
		{
			"name": "Feat: Elemental Adept",
			"category": "feat",
			"scope": "character",
			"description": "Ignore resistance when casting spells of your chosen element.",
			"default_enabled": False,
			"applies_to": [
				{
					"scope": "character",
					"element_choice": ["acid", "cold", "fire", "lightning", "thunder"],
				}
			],
			"effect_data": {
				"ignore_resistance": True,
				"minimum_damage_die": 2,
			},
		},
		{
			"name": "Feat: Spell Sniper",
			"category": "feat",
			"scope": "character",
			"description": "Doubles spell attack range and ignores cover bonuses.",
			"default_enabled": False,
			"applies_to": [
				{
					"scope": "spell",
					"requires_attack_roll": True,
				}
			],
			"effect_data": {
				"range_multiplier": 2,
				"ignore_cover": True,
			},
		},
		{
			"name": "Feat: War Caster",
			"category": "feat",
			"scope": "character",
			"description": "Maintain focus amidst battle; gain advantage on concentration checks and broaden casting reactions.",
			"default_enabled": False,
			"applies_to": [
				{
					"scope": "character",
					"advantages": ["concentration_checks"],
				},
				{
					"scope": "spell",
					"allows_opportunity_casting": True,
				},
			],
			"effect_data": {
				"concentration_advantage": True,
				"opportunity_spell_casting": True,
				"somatic_with_weapons": True,
			},
		},
		{
			"name": "Feat: Resilient (Constitution)",
			"category": "feat",
			"scope": "character",
			"description": "Bolster your Constitution saves with proficiency and a hardened constitution.",
			"default_enabled": False,
			"applies_to": [
				{
					"scope": "character",
					"ability_focus": "Constitution",
				}
			],
			"effect_data": {
				"saving_throw_bonus": 1,
				"grant_proficiency_in_save": "CON",
			},
		},
		{
			"name": "Flame Mastery",
			"category": "specialization",
			"scope": "spell",
			"description": "Enhances the effectiveness of fire-based spells like Fireball.",
			"default_enabled": False,
			"applies_to": [
				{
					"scope": "spell",
					"element_type": "fire",
					"effect_role": "primary",
				},
				{
					"spell_names": ["Fireball", "Burning Hands"],
				},
			],
			"effect_data": {
				"damage_bonus": {
					"dice": 1,
					"die": 6,
				},
				"ignore_resistance": True,
			},
		},
		{
			"name": "Metamagic: Empowered Spell",
			"category": "specialization",
			"scope": "spell",
			"description": "Reroll a limited number of damage dice when casting a spell.",
			"default_enabled": False,
			"applies_to": [
				{
					"scope": "spell",
					"requires_damage_roll": True,
				}
			],
			"effect_data": {
				"reroll_damage_dice": 3,
				"requires_sorcery_points": 1,
			},
		},
		{
			"name": "Metamagic: Quickened Spell",
			"category": "specialization",
			"scope": "spell",
			"description": "Transform a spell with casting time of 1 action into a bonus action.",
			"default_enabled": False,
			"applies_to": [
				{
					"scope": "spell",
					"casting_time": "1 Action",
				}
			],
			"effect_data": {
				"new_casting_time": "1 Bonus Action",
				"requires_sorcery_points": 2,
			},
		},
		{
			"name": "Storm Channeling",
			"category": "specialization",
			"scope": "spell",
			"description": "Focuses lightning-based spells into devastating lines of energy.",
			"default_enabled": False,
			"applies_to": [
				{
					"scope": "spell",
					"element_type": "lightning",
				},
				{
					"spell_names": ["Lightning Bolt"],
				},
			],
			"effect_data": {
				"damage_bonus": {
					"dice": 1,
					"die": 6,
				},
				"save_dc_bonus": 1,
			},
		},
		{
			"name": "Grasp of Hadar",
			"category": "invocation",
			"scope": "spell",
			"description": "Each beam of Eldritch Blast can pull a creature closer to you.",
			"default_enabled": False,
			"applies_to": [
				{
					"scope": "spell",
					"spell_names": ["Eldritch Blast"],
				}
			],
			"effect_data": {
				"pull_distance": 10,
				"apply_per_beam": True,
			},
		},
		{
			"name": "Repelling Blast",
			"category": "invocation",
			"scope": "spell",
			"description": "Eldritch Blast pushes creatures away when it hits.",
			"default_enabled": False,
			"applies_to": [
				{
					"scope": "spell",
					"spell_names": ["Eldritch Blast"],
				}
			],
			"effect_data": {
				"push_distance": 10,
				"apply_per_beam": True,
			},
		},
		{
			"name": "Boon: Blessing of the Archmage",
			"category": "boon",
			"scope": "character",
			"description": "A rare boon that heightens spell potency and resilience.",
			"default_enabled": False,
			"applies_to": [
				{
					"scope": "character",
					"spell_save_dc": True,
				}
			],
			"effect_data": {
				"spell_save_dc_bonus": 1,
				"resistance_to_damage_types": ["fire", "cold"],
			},
		},
	]


__all__ = ["get_default_modifier_definitions"]
