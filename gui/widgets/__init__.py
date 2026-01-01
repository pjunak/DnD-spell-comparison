"""Reusable widgets for the SpellGraphix GUI."""

try:
	from .ability_scores_group import AbilityScoresGroup
	from .class_progression_table import ClassProgressionTable
	from .class_features_group import ClassFeaturesGroup
	from .class_options_group import ClassOptionsGroup
	from .equipment_table import EquipmentBonusesTable
	from .feature_timeline_group import FeatureTimelineGroup
	from .feats_table import FeatsTable
	from .filter_input import FilterInputWidget
	from .modifiers_group import ModifiersGroup
	from .proficiency_summary_group import ProficiencySummaryGroup
	from .saves_skills_summary_group import SavesSkillsSummaryGroup
	from .spell_slot_adjustments_group import SpellSlotAdjustmentsGroup
	from .spell_access_table import SpellAccessTable, build_spell_source_key
except ModuleNotFoundError:
	# Optional dependency (PySide6) may be absent in minimal environments.
	AbilityScoresGroup = None  # type: ignore[assignment]
	ClassProgressionTable = None  # type: ignore[assignment]
	ClassFeaturesGroup = None  # type: ignore[assignment]
	ClassOptionsGroup = None  # type: ignore[assignment]
	EquipmentBonusesTable = None  # type: ignore[assignment]
	FeatureTimelineGroup = None  # type: ignore[assignment]
	FeatsTable = None  # type: ignore[assignment]
	FilterInputWidget = None  # type: ignore[assignment]
	ModifiersGroup = None  # type: ignore[assignment]
	ProficiencySummaryGroup = None  # type: ignore[assignment]
	SavesSkillsSummaryGroup = None  # type: ignore[assignment]
	SpellSlotAdjustmentsGroup = None  # type: ignore[assignment]
	SpellAccessTable = None  # type: ignore[assignment]
	def build_spell_source_key(*args, **kwargs):  # type: ignore[no-untyped-def]
		raise ModuleNotFoundError("Optional dependency 'PySide6' is required for GUI widgets")

__all__ = [
	"AbilityScoresGroup",
	"ClassProgressionTable",
	"ClassFeaturesGroup",
	"ClassOptionsGroup",
	"EquipmentBonusesTable",
	"FeatureTimelineGroup",
	"FeatsTable",
	"FilterInputWidget",
	"ModifiersGroup",
	"ProficiencySummaryGroup",
	"SavesSkillsSummaryGroup",
	"SpellSlotAdjustmentsGroup",
	"SpellAccessTable",
	"build_spell_source_key",
]
from .frameless_window import FramelessWindow
