"""Static collection of class and subclass feature rules."""

from __future__ import annotations

from .models import ClassFeatureRule


CLASS_FEATURE_RULES = [
    ClassFeatureRule(
        key="wizard_school_abjuration",
        label="Arcane Ward",
        class_name="Wizard",
        subclass_name="School of Abjuration",
        min_level=3,
        description="Abjuration spells raise a protective ward granting temporary hit points.",
        effect_data={
            "temporary_hit_points": {
                "dice": 1,
                "die": 6,
            }
        },
    ),
    ClassFeatureRule(
        key="wizard_school_evocation",
        label="Potent Cantrip",
        class_name="Wizard",
        subclass_name="School of Evocation",
        min_level=3,
        description="Evocation spells gain a consistent damage bonus.",
        effect_data={
            "damage_bonus": {
                "flat": 2,
            }
        },
    ),
    ClassFeatureRule(
        key="cleric_life_domain",
        label="Disciple of Life",
        class_name="Cleric",
        subclass_name="Life Domain",
        min_level=1,
        description="Healing spells restore additional hit points and empower Preserve Life.",
        effect_data={
            "healing_bonus": {
                "flat": 2,
                "per_die": True,
            },
            "preserve_life_channel": True,
        },
    ),
    ClassFeatureRule(
        key="warlock_fiend_patron",
        label="Dark One's Blessing",
        class_name="Warlock",
        subclass_name="The Fiend",
        min_level=3,
        description="Felling foes with spells grants temporary hit points from your fiendish patron.",
        effect_data={
            "temporary_hit_points": {
                "dice": 1,
                "die": 10,
                "modifier": "charisma",
            }
        },
    ),
]


__all__ = ["CLASS_FEATURE_RULES"]
