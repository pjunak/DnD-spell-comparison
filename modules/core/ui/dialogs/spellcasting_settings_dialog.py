"""Enhanced spellcasting configuration dialog for SpellGraphix."""

from __future__ import annotations

import copy
from typing import Dict, Iterable, List, Mapping, Set, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
	QCheckBox,
	QComboBox,
	QDialog,
	QDialogButtonBox,
	QFormLayout,
	QGroupBox,
	QHBoxLayout,
	QLabel,
	QLayout,
	QLineEdit,
	QListWidget,
	QListWidgetItem,
	QMessageBox,
	QPlainTextEdit,
	QPushButton,
	QFrame,
	QScrollArea,
	QSpinBox,
	QTabWidget,
	QToolButton,
	QVBoxLayout,
	QVBoxLayout,
	QWidget,
    QFileDialog,
)
from PySide6.QtGui import QPixmap
import shutil
from pathlib import Path
from modules.character_sheet.services.library import DEFAULT_LIBRARY_PATH

from modules.character_sheet.model import (
	ABILITY_NAMES,
	BackgroundSelection,
	CharacterSheet,
	ClassProgression,
	FeatureEntry,
	SpellAccessEntry,
	SpellSourceRecord,
    EquipmentItem,
)
from modules.dnd24_mechanics.class_options import normalise_class_name, normalise_subclass_name
from modules.dnd24_mechanics.character_rules import CharacterRuleSnapshot, CharacterRulesService
from modules.dnd24_mechanics.class_options import ClassOptionSnapshot, ClassOptionsService
from modules.dnd24_mechanics.armor_class import derive_armor_class
from modules.compendium.service import Compendium
from modules.dnd24_mechanics.hit_points import derive_max_hp
from modules.dnd24_mechanics.initiative import derive_initiative_bonus
from modules.compendium.modifiers.state import ModifierStateSnapshot
from modules.dnd24_mechanics.speed import derive_speed_ft
from modules.dnd24_mechanics.passive_scores import derive_passive_scores
from modules.dnd24_mechanics.species_grants import apply_species_skill_grants
from modules.dnd24_mechanics.senses import derive_senses
from modules.dnd24_mechanics.resistances import derive_resistances
from modules.dnd24_mechanics.condition_immunities import derive_condition_immunities
from modules.compendium.mechanics import (
	BonusBundle,
	TraitBundle,
	collect_ac_formula_candidates,
	collect_bonus_bundle,
	collect_skill_rank_grants,
	collect_speed_base_ft,
	collect_trait_bundle,
)
from modules.dnd24_mechanics.rules_config import max_character_level, point_buy_rules
from modules.dnd24_mechanics.spellcasting import DerivedSpellcastingProfile, derive_spellcasting_profile

from .compendium_picker_dialog import CompendiumPickerDialog, PickerItem, build_picker_items
from .class_entry_dialog import ClassEntryDialog
from .equipment_entry_dialog import EquipmentEntryDialog
from modules.equipment.ui.window import EquipmentWindow
from .spell_source_dialog import SpellSourceDialog
from ..widgets import (
	AbilityScoresGroup,
	ClassFeaturesGroup,
	ClassOptionsGroup,
	ClassProgressionTable,
	EquipmentBonusesTable,
	FeatureTimelineGroup,
	FeatsTable,
	ModifiersGroup,
	SavesSkillsSummaryGroup,
	SpellAccessTable,
	build_spell_source_key,
)


FULL_CASTER_CLASSES = {
	"bard",
	"cleric",
	"druid",
	"sorcerer",
	"wizard",
}

HALF_CASTER_CLASSES = {
	"paladin",
	"ranger",
	"artificer",
}

THIRD_CASTER_SUBCLASSES = {
	"eldritch knight",
	"arcane trickster",
}

MULTICLASS_SLOT_TABLE: Dict[int, Dict[int, int]] = {
	0: {},
	1: {1: 2},
	2: {1: 3},
	3: {1: 4, 2: 2},
	4: {1: 4, 2: 3},
	5: {1: 4, 2: 3, 3: 2},
	6: {1: 4, 2: 3, 3: 3},
	7: {1: 4, 2: 3, 3: 3, 4: 1},
	8: {1: 4, 2: 3, 3: 3, 4: 2},
	9: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
	10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
	11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
	12: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
	13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
	14: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
	15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
	16: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
	17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
	18: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 1, 7: 1, 8: 1, 9: 1},
	19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 1, 8: 1, 9: 1},
	20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1},
}

WARLOCK_PACT_SLOT_TABLE: Dict[int, Dict[int, int]] = {
	0: {},
	1: {1: 1},
	2: {1: 2},
	3: {2: 2},
	4: {2: 2},
	5: {3: 2},
	6: {3: 2},
	7: {4: 2},
	8: {4: 2},
	9: {5: 2},
	10: {5: 2},
	11: {5: 3},
	12: {5: 3},
	13: {5: 3},
	14: {5: 3},
	15: {5: 3},
	16: {5: 3},
	17: {5: 4},
	18: {5: 4},
	19: {5: 4},
	20: {5: 4},
}

_CUSTOM_BACKGROUND_KEY = "__custom_background__"


def _normalise_class_name(name: str) -> str:
	text = name.lower().strip()
	if "(" in text:
		text = text.split("(", 1)[0].strip()
	return text


def _normalise_background_key(name: str) -> str:
	return (name or "").strip().lower()


def _equivalent_caster_level(classes: Iterable[ClassProgression]) -> int:
	total = 0
	for entry in classes:
		name = _normalise_class_name(entry.name)
		subclass = (entry.subclass or "").strip().lower()
		if name == "warlock":
			continue
		if name in FULL_CASTER_CLASSES:
			total += entry.level
		elif name in HALF_CASTER_CLASSES:
			total += entry.level // 2
		elif subclass in THIRD_CASTER_SUBCLASSES or any(keyword in name for keyword in THIRD_CASTER_SUBCLASSES):
			total += entry.level // 3
	return max(0, min(total, 20))


def _derived_slot_buckets(classes: Iterable[ClassProgression]) -> Tuple[Dict[int, int], Dict[int, int]]:
	long_rest = dict(MULTICLASS_SLOT_TABLE.get(_equivalent_caster_level(classes), {}))
	short_rest = _warlock_pact_slots_for_classes(classes)
	return long_rest, short_rest


def _derived_spell_slots_for_classes(classes: Iterable[ClassProgression]) -> Dict[int, int]:
	long_rest, short_rest = _derived_slot_buckets(classes)
	return _combine_slot_buckets(long_rest, short_rest)


def _warlock_pact_slots_for_classes(classes: Iterable[ClassProgression]) -> Dict[int, int]:
	level = sum(entry.level for entry in classes if _normalise_class_name(entry.name) == "warlock")
	if level <= 0:
		return {}
	level = min(level, max(WARLOCK_PACT_SLOT_TABLE))
	return dict(WARLOCK_PACT_SLOT_TABLE.get(level, {}))


def _combine_slot_buckets(long_rest: Dict[int, int], short_rest: Dict[int, int]) -> Dict[int, int]:
	combined: Dict[int, int] = dict(long_rest)
	for level, amount in short_rest.items():
		combined[level] = combined.get(level, 0) + amount
	return {level: count for level, count in combined.items() if count > 0}


def _derived_proficiency_from_level(level: int) -> int:
	if level >= 17:
		return 6
	if level >= 13:
		return 5
	if level >= 9:
		return 4
	if level >= 5:
		return 3
	if level >= 1:
		return 2
	return 2


class SpellcastingSettingsDialog(QDialog):
	"""Multi-tab character sheet dialog that drives spellcasting configuration."""

	def __init__(
		self,
		sheet: CharacterSheet,
		modifier_snapshot: ModifierStateSnapshot | None,
		parent: QWidget | None = None,
	) -> None:
		super().__init__(parent)
		self.setWindowTitle("Character Sheet")
		self._sheet = copy.deepcopy(sheet)
		self._max_character_level = max(1, max_character_level())
		self._modifier_snapshot = modifier_snapshot or ModifierStateSnapshot([], {})
		self._modifier_definitions = list(self._modifier_snapshot.definitions)
		self._modifier_states = dict(self._modifier_snapshot.states)
		self._point_buy_rules = point_buy_rules()
		self._point_buy_error_message: str | None = None
		self._asi_missing_levels: List[int] = []

		self.ability_group: AbilityScoresGroup | None = None
		self.point_buy_toggle: QCheckBox | None = None
		self.point_buy_summary_label: QLabel | None = None
		self.point_buy_error_label: QLabel | None = None
		self._builder_spell_bonuses_label: QLabel | None = None
		self._builder_spell_slots_label: QLabel | None = None
		self.modifiers_group: ModifiersGroup | None = None
		self.class_features_group: ClassFeaturesGroup | None = None
		self.class_options_group: ClassOptionsGroup | None = None
		self.feature_timeline_group: FeatureTimelineGroup | None = None
		self.class_table: ClassProgressionTable | None = None
		self.level_total_label: QLabel | None = None
		self.feats_table: FeatsTable | None = None
		self.asi_group: QGroupBox | None = None
		self.asi_status_label: QLabel | None = None
		self.spell_table = SpellAccessTable(self)
		self.spell_source_list: QListWidget | None = None
		self.equipment_table = EquipmentBonusesTable(self)
		self._spell_table_ready = False
		self._equipment_table_ready = False
		self._cached_proficiency_base = 0
		self._cached_attack_base = 0
		self._cached_save_base = 0
		self._cached_slot_base: Dict[int, int] = {}
		self._cached_long_rest_slots: Dict[int, int] = {}
		self._cached_short_rest_slots: Dict[int, int] = {}
		self._cached_asi_score_bonuses: Dict[str, int] = {}

		self._compendium = self._load_compendium()
		self._background_records: Dict[str, Mapping[str, object]] = self._load_background_records()
		self._available_feat_names: List[str] = self._load_feat_names()
		self._feat_records: Dict[str, Mapping[str, object]] = self._load_feat_records()
		self._background_combo: QComboBox | None = None
		self._background_custom_edit: QLineEdit | None = None
		self._background_summary_label: QLabel | None = None
		self._background_feature_title: QLabel | None = None
		self._background_feature_text: QPlainTextEdit | None = None
		self._background_notes_label: QLabel | None = None
		self._background_choice_layout: QFormLayout | None = None
		self._background_error_label: QLabel | None = None
		self._background_error_message: str | None = None
		self._background_ability_inputs: List[QComboBox] = []
		self._background_language_inputs: List[QComboBox] = []
		self._background_tool_inputs: List[QLineEdit] = []
		self._background_feat_combo: QComboBox | None = None
		self._selected_background_key: str | None = self._match_background_key(self._sheet.identity.background)
		self._background_fallback_edit: QLineEdit | None = None
		self._background_header_button: QToolButton | None = None
		self._background_body_widget: QWidget | None = None
		self._proficiency_overview_label: QLabel | None = None
		self._saves_skills_group: SavesSkillsSummaryGroup | None = None
		self._builder_tab_index: int | None = None
		self._overview_name_label: QLabel | None = None
		self._overview_identity_label: QLabel | None = None
		self._overview_abilities_label: QLabel | None = None
		self._overview_spellcasting_label: QLabel | None = None
		self._overview_spell_slots_label: QLabel | None = None
		self._overview_current_hp_spin: QSpinBox | None = None
		self._overview_max_hp_label: QLabel | None = None
		self._overview_ac_label: QLabel | None = None
		self._overview_speed_label: QLabel | None = None
		self._overview_initiative_label: QLabel | None = None
		self._overview_senses_label: QLabel | None = None
		self._overview_resistances_label: QLabel | None = None
		self._overview_condition_immunities_label: QLabel | None = None
		self._overview_passive_perception_label: QLabel | None = None
		self._overview_passive_investigation_label: QLabel | None = None
		self._overview_passive_insight_label: QLabel | None = None
		self._species_combo: QComboBox | None = None
		self._species_subtype_combo: QComboBox | None = None
		self._default_tab_text_colors: Dict[int, QColor] = {}
		self._cached_bonus_bundle: BonusBundle | None = None
		self._cached_trait_bundle: TraitBundle | None = None

		self._rules_service = CharacterRulesService()
		self._class_options_service = ClassOptionsService()
		self._feature_selections: Dict[str, str] = dict(self._sheet.feature_options or {})
		self._class_option_selections: Dict[str, List[str]] = {
			key: list(values)
			for key, values in (self._sheet.class_options or {}).items()
		}
		self._feature_collapse_states: Dict[str, bool] = {}
		self._rule_snapshot: CharacterRuleSnapshot | None = None
		self._class_option_snapshot: ClassOptionSnapshot | None = None
		self._derived_spell_profile: DerivedSpellcastingProfile | None = None
		self._derived_spell_ability = (self._sheet.spellcasting.spellcasting_ability or "INT").upper()
		self._active_spell_source_key: str | None = None
		self._spell_sources: Dict[str, SpellSourceRecord] = {}
		self._asi_choice_inputs: Dict[int, QComboBox] = {}
		self._asi_ability_inputs: Dict[int, Tuple[QComboBox, QComboBox]] = {}
		self._asi_feat_labels: Dict[int, QLabel] = {}
		self._asi_feat_buttons: Dict[int, QPushButton] = {}
		self._asi_detail_widgets: Dict[int, Tuple[QWidget, QWidget]] = {}
		self._asi_row_widgets: Dict[int, Tuple[QWidget, QWidget]] = {}
		self.asi_placeholder_label: QLabel | None = None
		self._bootstrap_spell_sources()

		layout = QVBoxLayout(self)
		self.tabs = QTabWidget()
		layout.addWidget(self.tabs)

		self._build_overview_tab()
		self._build_spells_tab()
		self._build_equipment_tab()
		self._build_builder_tab()
		self._default_tab_text_colors = {
			idx: self.tabs.tabBar().tabTextColor(idx)
			for idx in range(self.tabs.count())
		}

		# Bring the working copy into a consistent initial state and refresh derived displays.
		self._refresh_level_summary()
		self._refresh_level_dependent_fields()
		self._refresh_feature_rules()
		self._refresh_class_options()
		self._apply_point_buy_bounds()
		self._update_point_buy_summary()
		self._refresh_asi_choice_state()
		self._refresh_overview_panels()
		self._update_tab_highlights()

		button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
		button_box.accepted.connect(self._accept)
		button_box.rejected.connect(self.reject)
		layout.addWidget(button_box)

		self._apply_initial_geometry()

	def _build_overview_tab(self) -> None:
		tab = QWidget()
		root = QVBoxLayout(tab)
		root.setContentsMargins(0, 0, 0, 0)
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.Shape.NoFrame)
		content = QWidget()
		layout = QVBoxLayout(content)
		layout.setContentsMargins(8, 8, 8, 8)
		layout.setSpacing(10)
		scroll.setWidget(content)
		root.addWidget(scroll)

		# --- Portrait Section ---
		portrait_layout = QHBoxLayout()
		self._portrait_label = QLabel()
		self._portrait_label.setFixedSize(100, 100)
		self._portrait_label.setStyleSheet("background-color: #2d2d30; border: 1px solid #3e3e42; border-radius: 4px;")
		self._portrait_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		
		portrait_btn_layout = QVBoxLayout()
		portrait_btn = QPushButton("Change Portrait...")
		portrait_btn.clicked.connect(self._on_select_portrait)
		portrait_btn_layout.addWidget(portrait_btn)
		portrait_btn_layout.addStretch()

		portrait_layout.addWidget(self._portrait_label)
		portrait_layout.addLayout(portrait_btn_layout)
		portrait_layout.addStretch()
		layout.addLayout(portrait_layout)

		self._refresh_portrait_preview()
		# ------------------------

		name = QLabel()
		name.setStyleSheet("font-weight: 700; font-size: 16px;")
		self._overview_name_label = name
		layout.addWidget(name)

		identity = QLabel()
		identity.setWordWrap(True)
		identity.setStyleSheet("color: #5f6b7c;")
		self._overview_identity_label = identity
		layout.addWidget(identity)

		abilities_box = QGroupBox("Abilities")
		abilities_layout = QVBoxLayout(abilities_box)
		abilities_layout.setContentsMargins(8, 8, 8, 8)
		abilities_layout.setSpacing(6)
		abilities_label = QLabel()
		abilities_label.setWordWrap(True)
		self._overview_abilities_label = abilities_label
		abilities_layout.addWidget(abilities_label)
		layout.addWidget(abilities_box)

		spellcasting_box = QGroupBox("Spellcasting")
		spellcasting_layout = QVBoxLayout(spellcasting_box)
		spellcasting_layout.setContentsMargins(8, 8, 8, 8)
		spellcasting_layout.setSpacing(6)
		spellcasting_label = QLabel()
		slots_label = QLabel()

		combat_box = QGroupBox("Hit Points")
		combat_layout = QFormLayout(combat_box)
		combat_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
		combat_layout.setContentsMargins(8, 8, 8, 8)
		combat_layout.setSpacing(6)
		current_spin = QSpinBox()
		current_spin.setRange(0, 999)
		current_spin.setValue(max(0, int(self._sheet.combat.current_hp or 0)))
		current_spin.valueChanged.connect(self._on_current_hp_changed)
		self._overview_current_hp_spin = current_spin
		max_label = QLabel("0")
		max_label.setStyleSheet("color: #5f6b7c;")
		self._overview_max_hp_label = max_label
		ac_label = QLabel("10")
		ac_label.setStyleSheet("color: #5f6b7c;")
		self._overview_ac_label = ac_label
		combat_layout.addRow("Current HP", current_spin)
		combat_layout.addRow("Max HP", max_label)
		combat_layout.addRow("Armor Class", ac_label)
		speed_label = QLabel("30")
		speed_label.setStyleSheet("color: #5f6b7c;")
		self._overview_speed_label = speed_label
		combat_layout.addRow("Speed", speed_label)
		initiative_label = QLabel("+0")
		initiative_label.setStyleSheet("color: #5f6b7c;")
		self._overview_initiative_label = initiative_label
		combat_layout.addRow("Initiative", initiative_label)
		senses_label = QLabel("None")
		senses_label.setStyleSheet("color: #5f6b7c;")
		senses_label.setWordWrap(True)
		self._overview_senses_label = senses_label
		combat_layout.addRow("Senses", senses_label)
		resistances_label = QLabel("None")
		resistances_label.setStyleSheet("color: #5f6b7c;")
		resistances_label.setWordWrap(True)
		self._overview_resistances_label = resistances_label
		combat_layout.addRow("Resistances", resistances_label)
		condition_immunities_label = QLabel("None")
		condition_immunities_label.setStyleSheet("color: #5f6b7c;")
		condition_immunities_label.setWordWrap(True)
		self._overview_condition_immunities_label = condition_immunities_label
		combat_layout.addRow("Condition Immunities", condition_immunities_label)
		passive_perception_label = QLabel("10")
		passive_perception_label.setStyleSheet("color: #5f6b7c;")
		self._overview_passive_perception_label = passive_perception_label
		combat_layout.addRow("Passive Perception", passive_perception_label)
		passive_investigation_label = QLabel("10")
		passive_investigation_label.setStyleSheet("color: #5f6b7c;")
		self._overview_passive_investigation_label = passive_investigation_label
		combat_layout.addRow("Passive Investigation", passive_investigation_label)
		passive_insight_label = QLabel("10")
		passive_insight_label.setStyleSheet("color: #5f6b7c;")
		self._overview_passive_insight_label = passive_insight_label
		combat_layout.addRow("Passive Insight", passive_insight_label)
		spellcasting_label.setWordWrap(True)
		self._overview_spellcasting_label = spellcasting_label
		spellcasting_layout.addWidget(spellcasting_label)
		slots_label.setWordWrap(True)
		slots_label.setStyleSheet("color: #5f6b7c;")
		self._overview_spell_slots_label = slots_label
		spellcasting_layout.addWidget(slots_label)
		layout.addWidget(spellcasting_box)
		layout.addWidget(combat_box)

		saves_skills = SavesSkillsSummaryGroup(self._sheet)
		self._saves_skills_group = saves_skills
		layout.addWidget(saves_skills)

		go = QPushButton("Go to Builder")
		go.clicked.connect(self._go_to_builder_tab)
		layout.addWidget(go)
		layout.addStretch()

		self.tabs.addTab(tab, "Overview")

	def _refresh_portrait_preview(self) -> None:
		path_str = self._sheet.identity.portrait_path
		if path_str:
			# Resovle path
			if Path(path_str).is_absolute():
				p_path = Path(path_str)
			else:
				p_path = DEFAULT_LIBRARY_PATH / "portraits" / path_str
			
			if p_path.exists():
				pix = QPixmap(str(p_path))
				self._portrait_label.setPixmap(pix.scaled(self._portrait_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
				self._portrait_label.setText("")
			else:
				self._portrait_label.setPixmap(QPixmap())
				self._portrait_label.setText("Missing")
		else:
			self._portrait_label.setPixmap(QPixmap())
			self._portrait_label.setText("No Image")

	def _on_select_portrait(self) -> None:
		file_path, _ = QFileDialog.getOpenFileName(
			self, "Select Portrait", "", "Images (*.png *.jpg *.jpeg *.bmp)"
		)
		if not file_path:
			return

		src_path = Path(file_path)
		char_name = self._sheet.identity.name or "unnamed"
		
		# Sanitize filename
		safe_name = "".join(c for c in char_name if c.isalnum() or c in (' ', '-', '_')).strip()
		safe_name = safe_name.replace(' ', '_')
		if not safe_name: safe_name = "character"
		
		ext = src_path.suffix.lower()
		dest_filename = f"{safe_name}{ext}"
		
		dest_dir = DEFAULT_LIBRARY_PATH / "portraits"
		dest_dir.mkdir(parents=True, exist_ok=True)
		dest_path = dest_dir / dest_filename
		
		# Handle collision (append index)
		counter = 1
		while dest_path.exists():
			dest_filename = f"{safe_name}_{counter}{ext}"
			dest_path = dest_dir / dest_filename
			counter += 1
			
		try:
			shutil.copy2(src_path, dest_path)
			self._sheet.identity.portrait_path = dest_filename
			self._refresh_portrait_preview()
		except Exception as e:
			QMessageBox.critical(self, "Error", f"Failed to save portrait: {e}")

	def _on_current_hp_changed(self, value: int) -> None:
		self._sheet.combat.current_hp = max(0, int(value))

	def _go_to_builder_tab(self) -> None:
		if self._builder_tab_index is None:
			# Builder is always the last tab by design.
			self._builder_tab_index = max(0, self.tabs.count() - 1)
		self.tabs.setCurrentIndex(self._builder_tab_index)

	def _refresh_overview_panels(self) -> None:
		name = (self._sheet.identity.name or "").strip() or "(Unnamed Character)"
		if self._overview_name_label:
			self._overview_name_label.setText(name)
		classes = self._current_class_progression()
		class_text = " / ".join(f"{c.name} {c.level}" + (f" ({c.subclass})" if c.subclass else "") for c in classes if c.name and c.level)
		background = (self._current_background_name() or "").strip() or "None"
		level = self._sum_class_levels(classes)
		if self._overview_identity_label:
			self._overview_identity_label.setText(f"Level {level} • Background: {background}\n{class_text}".strip())
		if self._overview_abilities_label:
			if self.ability_group:
				scores = self.ability_group.scores()
				parts = []
				for ability in ABILITY_NAMES:
					base_score = int(scores.get(ability, 10))
					bonus = int(self._cached_asi_score_bonuses.get(ability, 0) or 0)
					score = base_score + bonus
					mod = (score - 10) // 2
					parts.append(f"{ability} {score} ({mod:+d})")
				self._overview_abilities_label.setText(" • ".join(parts))
			else:
				parts = []
				for ability in ABILITY_NAMES:
					block = self._sheet.get_ability(ability)
					bonus = int(self._cached_asi_score_bonuses.get(ability, 0) or 0)
					score = int(block.score) + bonus
					mod = block.modifier if block.modifier is not None else (score - 10) // 2
					parts.append(f"{ability} {score} ({int(mod):+d})")
				self._overview_abilities_label.setText(" • ".join(parts))
		if self._overview_spellcasting_label:
			ability = (self._derived_spell_ability or self._sheet.spellcasting.spellcasting_ability or "INT").upper()
			effective_prof = self._cached_proficiency_base
			attack_final = self._cached_attack_base
			save_final = self._cached_save_base
			attack_text = f"{attack_final:+d}"
			save_text = f"{save_final:d}"
			self._overview_spellcasting_label.setText(
				f"Ability: {ability}\nProficiency Bonus: {effective_prof:+d}\nSpell Attack: {attack_text}\nSave DC: {save_text}".strip()
			)
		if self._overview_spell_slots_label:
			parts: List[str] = []
			for level_num in range(1, 10):
				count = int(self._cached_slot_base.get(level_num, 0) or 0)
				if count <= 0:
					continue
				parts.append(f"{level_num}: {count}")
			self._overview_spell_slots_label.setText(
				"Slots by level: " + (", ".join(parts) if parts else "None")
			)
		if self._overview_ac_label:
			self._overview_ac_label.setText(str(int(self._sheet.combat.armor_class or 10)))
		if self._overview_speed_label:
			self._overview_speed_label.setText(str(int(self._sheet.combat.speed_ft or 30)))
		if self._overview_initiative_label:
			value = int(self._sheet.combat.initiative_bonus or 0)
			self._overview_initiative_label.setText(f"{value:+d}")
		if self._overview_senses_label:
			if self._cached_trait_bundle is not None:
				self._overview_senses_label.setText(self._cached_trait_bundle.senses_formatted())
			else:
				breakdown = derive_senses(
					compendium=self._compendium,
					species_name=self._sheet.identity.ancestry,
					species_subtype_name=getattr(self._sheet.identity, "ancestry_subtype", "") or "",
				)
				self._overview_senses_label.setText(breakdown.formatted())
		if self._overview_resistances_label:
			if self._cached_trait_bundle is not None:
				self._overview_resistances_label.setText(self._cached_trait_bundle.resistances_formatted())
			else:
				breakdown = derive_resistances(
					compendium=self._compendium,
					species_name=self._sheet.identity.ancestry,
					species_subtype_name=getattr(self._sheet.identity, "ancestry_subtype", "") or "",
				)
				self._overview_resistances_label.setText(breakdown.formatted())
		if self._overview_condition_immunities_label:
			if self._cached_trait_bundle is not None:
				self._overview_condition_immunities_label.setText(self._cached_trait_bundle.condition_immunities_formatted())
			else:
				breakdown = derive_condition_immunities(
					compendium=self._compendium,
					species_name=self._sheet.identity.ancestry,
					species_subtype_name=getattr(self._sheet.identity, "ancestry_subtype", "") or "",
				)
				self._overview_condition_immunities_label.setText(breakdown.formatted())
		if (
			self._overview_passive_perception_label
			or self._overview_passive_investigation_label
			or self._overview_passive_insight_label
		):
			passives = derive_passive_scores(self._sheet, ability_score_bonuses=self._cached_asi_score_bonuses)
			if self._overview_passive_perception_label:
				self._overview_passive_perception_label.setText(str(int(passives.perception)))
			if self._overview_passive_investigation_label:
				self._overview_passive_investigation_label.setText(str(int(passives.investigation)))
			if self._overview_passive_insight_label:
				self._overview_passive_insight_label.setText(str(int(passives.insight)))
		if self._overview_max_hp_label or self._overview_current_hp_spin:
			max_hp = max(0, int(self._sheet.combat.max_hp or 0))
			if self._overview_max_hp_label:
				self._overview_max_hp_label.setText(str(max_hp))
			if self._overview_current_hp_spin:
				spin = self._overview_current_hp_spin
				spin.setMaximum(max_hp if max_hp > 0 else 999)
				if not spin.hasFocus():
					spin.blockSignals(True)
					spin.setValue(max(0, min(int(self._sheet.combat.current_hp or 0), spin.maximum())))
					spin.blockSignals(False)
		if self._saves_skills_group:
			self._saves_skills_group.set_sheet(self._sheet)

	def _refresh_hit_points(
		self,
		classes: Sequence[ClassProgression],
		*,
		max_hp_bonus: int = 0,
		max_hp_per_level_bonus: int = 0,
	) -> None:
		con_mod = self._ability_modifier_value("CON") if self.ability_group else self._sheet.get_ability("CON").effective_modifier()
		max_hp = derive_max_hp(
			classes,
			con_modifier=con_mod,
			compendium=self._compendium,
			equipment_bonus=int(max_hp_bonus),
			per_level_bonus=int(max_hp_per_level_bonus),
		)
		previous_max = max(0, int(self._sheet.combat.max_hp or 0))
		self._sheet.combat.max_hp = max_hp

		# Clamp current HP into the valid range, but never auto-edit it otherwise.
		current = max(0, int(self._sheet.combat.current_hp or 0))
		if max_hp > 0:
			self._sheet.combat.current_hp = min(current, max_hp)
		# Bootstrap new characters (or incomplete imports): if both values are unset, start at full.
		if previous_max == 0 and current == 0 and max_hp > 0:
			self._sheet.combat.current_hp = max_hp

	def _build_background_controls(self, form: QFormLayout) -> None:
		# Species selection (sources of truth for derived speed and some traits).
		if self._compendium:
			combo = QComboBox()
			species_records = [r for r in self._compendium.records("species") if isinstance(r, Mapping)]
			names = sorted(
				[str(r.get("name")) for r in species_records if isinstance(r.get("name"), str)],
				key=lambda s: s.lower(),
			)
			combo.addItem("(None)", "")
			for name in names:
				combo.addItem(name, name)
			current = (self._sheet.identity.ancestry or "").strip()
			if current:
				combo.setCurrentText(current)
			combo.currentIndexChanged.connect(self._on_species_changed)
			form.addRow("Species", combo)
			self._species_combo = combo

			subtype_combo = QComboBox()
			subtype_combo.addItem("(None)", "")
			subtype_combo.setEnabled(False)
			subtype_combo.currentIndexChanged.connect(self._on_species_subtype_changed)
			form.addRow("Species Subtype", subtype_combo)
			self._species_subtype_combo = subtype_combo
			self._refresh_species_subtype_options()

		section = QWidget()
		section_layout = QVBoxLayout(section)
		section_layout.setContentsMargins(0, 0, 0, 0)
		section_layout.setSpacing(6)

		header = QToolButton()
		header.setCheckable(True)
		header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
		header.clicked.connect(self._on_background_section_toggled)
		self._background_header_button = header
		section_layout.addWidget(header)

		body = QWidget()
		body_layout = QVBoxLayout(body)
		body_layout.setContentsMargins(0, 0, 0, 0)
		body_layout.setSpacing(6)
		self._background_body_widget = body
		section_layout.addWidget(body)

		if not self._background_records:
			edit = QLineEdit(self._sheet.identity.background)
			edit.setPlaceholderText("Enter background name")
			edit.textChanged.connect(lambda _text: self._update_background_header())
			edit.textChanged.connect(lambda _text: self._refresh_overview_panels())
			self._background_fallback_edit = edit
			body_layout.addWidget(edit)
			form.addRow(section)
			self._update_background_header()
			self._set_background_section_expanded(not bool(self._sheet.identity.background.strip()))
			return

		group = QGroupBox()
		group_layout = QVBoxLayout(group)
		group_layout.setContentsMargins(8, 6, 8, 6)
		group_layout.setSpacing(6)
		body_layout.addWidget(group)

		combo = QComboBox()
		combo.addItem("No Background Selected", "")
		for key, record in sorted(
			self._background_records.items(),
			key=lambda item: str(item[1].get("name", "")).lower(),
		):
			name = str(record.get("name", "Background")) or "Background"
			combo.addItem(name, key)
		combo.addItem("Custom / Homebrew", _CUSTOM_BACKGROUND_KEY)
		combo.currentIndexChanged.connect(self._on_background_changed)
		self._background_combo = combo
		group_layout.addWidget(combo)

		custom_text = self._sheet.identity.background if not self._selected_background_key else ""
		custom_edit = QLineEdit(custom_text)
		custom_edit.setPlaceholderText("Custom background name")
		custom_edit.textChanged.connect(lambda _text: self._update_background_header())
		custom_edit.textChanged.connect(lambda _text: self._refresh_overview_panels())
		custom_edit.hide()
		self._background_custom_edit = custom_edit
		group_layout.addWidget(custom_edit)

		summary = QLabel("Select a background to review its benefits.")
		summary.setWordWrap(True)
		summary.setStyleSheet("color: #1f2937;")
		self._background_summary_label = summary
		group_layout.addWidget(summary)

		feature_title = QLabel()
		feature_title.setStyleSheet("font-weight: 600;")
		self._background_feature_title = feature_title
		group_layout.addWidget(feature_title)

		feature_text = QPlainTextEdit()
		feature_text.setReadOnly(True)
		feature_text.setMaximumHeight(100)
		feature_text.hide()
		self._background_feature_text = feature_text
		group_layout.addWidget(feature_text)

		notes_label = QLabel()
		notes_label.setWordWrap(True)
		notes_label.setStyleSheet("color: #5f6b7c; font-style: italic;")
		notes_label.hide()
		self._background_notes_label = notes_label
		group_layout.addWidget(notes_label)

		choices_widget = QWidget()
		choice_layout = QFormLayout(choices_widget)
		choice_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
		choice_layout.setHorizontalSpacing(12)
		self._background_choice_layout = choice_layout
		group_layout.addWidget(choices_widget)

		error_label = QLabel()
		error_label.setStyleSheet("color: #d95c5c;")
		error_label.hide()
		self._background_error_label = error_label
		group_layout.addWidget(error_label)

		form.addRow(section)

		initial_index = 0
		if self._selected_background_key:
			index = combo.findData(self._selected_background_key)
			if index >= 0:
				initial_index = index
		elif self._sheet.identity.background:
			index = combo.findData(_CUSTOM_BACKGROUND_KEY)
			if index >= 0:
				initial_index = index
		combo.setCurrentIndex(initial_index)
		self._on_background_changed(combo.currentIndex())
		self._update_background_header()
		self._set_background_section_expanded(not bool(self._current_background_name().strip()))

	def _on_background_section_toggled(self, checked: bool) -> None:
		self._set_background_section_expanded(bool(checked))

	def _set_background_section_expanded(self, expanded: bool) -> None:
		if not self._background_header_button or not self._background_body_widget:
			return
		self._background_body_widget.setVisible(expanded)
		self._background_header_button.blockSignals(True)
		self._background_header_button.setChecked(expanded)
		self._background_header_button.blockSignals(False)
		self._background_header_button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
		self._update_background_header()

	def _update_background_header(self) -> None:
		if not self._background_header_button:
			return
		name = self._current_background_name().strip()
		if not name:
			name = "No Background Selected"
		self._background_header_button.setText(f"Background: {name}")

	def _on_background_changed(self, _index: int) -> None:
		if not self._background_combo:
			return
		previous_record = self._current_background_record()
		data = self._background_combo.currentData(Qt.ItemDataRole.UserRole)
		key = str(data or "").strip().lower()
		if not key:
			self._selected_background_key = None
			self._show_background_custom_input(False)
			self._render_background_summary(None)
			self._rebuild_background_dynamic_fields(None)
			self._background_error_message = None
			if self._background_error_label:
				self._background_error_label.hide()
			self._update_background_header()
			self._refresh_overview_panels()
			return
		if key == _CUSTOM_BACKGROUND_KEY:
			self._selected_background_key = None
			prefill = self._sheet.identity.background.strip()
			if previous_record:
				name_value = previous_record.get("name")
				if isinstance(name_value, str) and name_value.strip():
					prefill = name_value.strip()
			self._show_background_custom_input(True, prefill)
			self._render_background_summary(None)
			self._rebuild_background_dynamic_fields(None)
			self._background_error_message = None
			if self._background_error_label:
				self._background_error_label.hide()
			self._update_background_header()
			self._refresh_overview_panels()
			return
		record = self._background_records.get(key)
		self._selected_background_key = key if record else None
		self._show_background_custom_input(False)
		self._render_background_summary(record)
		self._rebuild_background_dynamic_fields(record if record else None)
		self._validate_background_choices()
		self._update_background_header()
		self._refresh_overview_panels()

	def _update_proficiency_overview(self) -> None:
		if not self._proficiency_overview_label:
			return
		prof = self._sheet.proficiencies
		lines: List[str] = []
		if prof.armor:
			lines.append(f"Armor: {', '.join(prof.armor)}")
		if prof.weapons:
			lines.append(f"Weapons: {', '.join(prof.weapons)}")
		if prof.tools:
			lines.append(f"Tools: {', '.join(prof.tools)}")
		if prof.languages:
			lines.append(f"Languages: {', '.join(prof.languages)}")
		skills = prof.skills or {}
		if skills:
			values = list(skills.values())
			if values and all(isinstance(v, (int, float)) for v in values):
				items = sorted(((name, int(value)) for name, value in skills.items()), key=lambda item: item[0].lower())
				lines.append("Skills: " + ", ".join(f"{name} {value:+d}" for name, value in items))
			else:
				names = sorted((str(name) for name in skills.keys() if name), key=lambda value: value.lower())
				lines.append("Skills: " + ", ".join(names))
		if not lines:
			lines.append("No proficiencies recorded yet.")
		self._proficiency_overview_label.setText("\n".join(lines))

	def _show_background_custom_input(self, visible: bool, prefill: str | None = None) -> None:
		if not self._background_custom_edit:
			return
		self._background_custom_edit.setVisible(visible)
		if not visible:
			return
		if self._background_custom_edit.text().strip():
			return
		fallback = (prefill or self._sheet.identity.background).strip()
		if fallback:
			self._background_custom_edit.setText(fallback)

	def _render_background_summary(self, record: Mapping[str, object] | None) -> None:
		if not self._background_summary_label:
			return
		if not record:
			self._background_summary_label.setText("Select a background to review its benefits.")
			if self._background_feature_title:
				self._background_feature_title.setText("")
			if self._background_feature_text:
				self._background_feature_text.hide()
			if self._background_notes_label:
				self._background_notes_label.hide()
			return
		summary_lines: List[str] = []
		skills = [str(value) for value in (record.get("skill_proficiencies") or []) if value]
		if skills:
			summary_lines.append(f"Skills: {', '.join(skills)}")
		tools = [str(value) for value in (record.get("tool_proficiencies") or []) if value]
		if tools:
			summary_lines.append(f"Tools: {', '.join(tools)}")
		languages = record.get("languages") or {}
		try:
			language_count = int(languages.get("count", 0) or 0)
		except (TypeError, ValueError):
			language_count = 0
		if language_count > 0:
			descriptor = languages.get("choices", "any")
			summary_lines.append(f"Languages: {language_count} ({descriptor})")
		vehicles = [str(value) for value in (record.get("vehicle_proficiencies") or []) if value]
		if vehicles:
			summary_lines.append(f"Vehicles: {', '.join(vehicles)}")
		weapons = [str(value) for value in (record.get("weapon_proficiencies") or []) if value]
		if weapons:
			summary_lines.append(f"Weapons: {', '.join(weapons)}")
		feat = str(record.get("starting_feat", "") or "").strip()
		if feat:
			summary_lines.append(f"Feat: {feat}")
		equipment = [str(value) for value in (record.get("equipment") or []) if value]
		if equipment:
			summary_lines.append(f"Equipment: {', '.join(equipment)}")
		self._background_summary_label.setText("\n".join(summary_lines))
		feature = record.get("feature") or {}
		feature_name = str(feature.get("name", "") or "").strip()
		feature_description = str(feature.get("description", "") or "").strip()
		if self._background_feature_title:
			self._background_feature_title.setText(f"Feature: {feature_name}" if feature_name else "")
		if self._background_feature_text:
			if feature_description:
				self._background_feature_text.setPlainText(feature_description)
				self._background_feature_text.show()
			else:
				self._background_feature_text.hide()
		notes = str(record.get("notes", "") or "").strip()
		if self._background_notes_label:
			if notes:
				self._background_notes_label.setText(notes)
				self._background_notes_label.show()
			else:
				self._background_notes_label.hide()

	def _rebuild_background_dynamic_fields(self, record: Mapping[str, object] | None) -> None:
		layout = self._background_choice_layout
		if not layout:
			return
		self._clear_layout(layout)
		self._background_ability_inputs = []
		self._background_language_inputs = []
		self._background_tool_inputs = []
		self._background_feat_combo = None
		if not record:
			return
		selection = self._stored_background_selection()
		ability_options = record.get("ability_bonus_options") or {}
		try:
			required_ability_choices = int(ability_options.get("choose", 0) or 0)
		except (TypeError, ValueError):
			required_ability_choices = 0
		amount = int(ability_options.get("amount", 1) or 1)
		allowed_abilities = [str(value).upper() for value in (ability_options.get("abilities") or ABILITY_NAMES)]
		if required_ability_choices > 0:
			help_label = QLabel(f"Assign {required_ability_choices} ability bonus{'es' if required_ability_choices != 1 else ''} (+{amount}).")
			help_label.setStyleSheet("color: #5f6b7c;")
			layout.addRow("", help_label)
			stored = list(selection.ability_choices or [])
			for index in range(required_ability_choices):
				combo = QComboBox()
				combo.addItem("Select ability", "")
				for ability in allowed_abilities:
					combo.addItem(ability, ability)
				if index < len(stored):
					stored_value = (stored[index] or "").upper()
					stored_index = combo.findData(stored_value)
					if stored_index >= 0:
						combo.setCurrentIndex(stored_index)
				combo.currentIndexChanged.connect(self._validate_background_choices)
				layout.addRow(QLabel(f"Ability Bonus {index + 1}"), combo)
				self._background_ability_inputs.append(combo)
		language_config = record.get("languages") or {}
		try:
			language_count = int(language_config.get("count", 0) or 0)
		except (TypeError, ValueError):
			language_count = 0
		if language_count > 0:
			stored_languages = list(selection.language_choices or [])
			options = language_config.get("choices")
			choice_list = list(options) if isinstance(options, (list, tuple)) else []
			descriptor = options if isinstance(options, str) else "any"
			for index in range(language_count):
				combo = QComboBox()
				combo.setEditable(True)
				combo.addItem("", "")
				for entry in choice_list:
					label = str(entry)
					combo.addItem(label, label)
				stored_value = str(stored_languages[index]).strip() if index < len(stored_languages) else ""
				if stored_value:
					combo.setCurrentText(stored_value)
				line_edit = combo.lineEdit()
				if line_edit:
					placeholder = f"{descriptor} language" if isinstance(descriptor, str) else "Language"
					line_edit.setPlaceholderText(placeholder)
				combo.currentTextChanged.connect(self._validate_background_choices)
				layout.addRow(QLabel(f"Language {index + 1}"), combo)
				self._background_language_inputs.append(combo)
		tools = [str(value) for value in (record.get("tool_proficiencies") or []) if value]
		stored_tools = list(selection.tool_choices or [])
		for index, entry in enumerate(tools):
			edit = QLineEdit()
			stored_value = str(stored_tools[index]).strip() if index < len(stored_tools) else ""
			requires_choice = any(keyword in entry.lower() for keyword in ("choice", "choose"))
			if stored_value:
				edit.setText(stored_value)
			elif requires_choice:
				edit.setPlaceholderText(entry)
			else:
				edit.setText(entry)
			edit.textChanged.connect(self._validate_background_choices)
			layout.addRow(QLabel(f"Tool {index + 1}"), edit)
			self._background_tool_inputs.append(edit)
		feat_name = str(record.get("starting_feat", "") or "").strip()
		combo = QComboBox()
		combo.setEditable(True)
		combo.addItem("", "")
		seen_feats = set()
		if feat_name:
			combo.addItem(feat_name, feat_name)
			seen_feats.add(feat_name.lower())
		for feat in self._available_feat_names:
			key = feat.lower()
			if key in seen_feats:
				continue
			combo.addItem(feat, feat)
			seen_feats.add(key)
		stored_feat = selection.feat_choice.strip() or feat_name
		if stored_feat:
			combo.setCurrentText(stored_feat)
		combo.currentTextChanged.connect(self._validate_background_choices)
		layout.addRow(QLabel("Starting Feat"), combo)
		self._background_feat_combo = combo

	def _stored_background_selection(self) -> BackgroundSelection:
		selection = getattr(self._sheet.identity, "background_choices", None)
		if isinstance(selection, BackgroundSelection):
			return selection
		selection = BackgroundSelection()
		self._sheet.identity.background_choices = selection
		return selection

	def _validate_background_choices(self) -> None:
		record = self._current_background_record()
		if not record:
			self._background_error_message = None
			if self._background_error_label:
				self._background_error_label.hide()
			self._update_tab_highlights()
			return
		message: str | None = None
		ability_options = record.get("ability_bonus_options") or {}
		try:
			required = int(ability_options.get("choose", 0) or 0)
		except (TypeError, ValueError):
			required = 0
		allow_duplicates = bool(ability_options.get("allow_same_target", False))
		if required:
			selected = [str(combo.currentData(Qt.ItemDataRole.UserRole) or "").upper() for combo in self._background_ability_inputs]
			filled = [value for value in selected if value]
			if len(filled) < required:
				message = f"Select {required} ability bonus{'es' if required != 1 else ''}."
			elif not allow_duplicates and len(set(filled)) != len(filled):
				message = "Each ability bonus must target a different ability."
		if not message:
			language_config = record.get("languages") or {}
			try:
				language_count = int(language_config.get("count", 0) or 0)
			except (TypeError, ValueError):
				language_count = 0
			if language_count:
				for index, combo in enumerate(self._background_language_inputs):
					if not combo.currentText().strip():
						message = f"Specify language {index + 1}."
						break
		if not message and record.get("starting_feat") and self._background_feat_combo:
			if not self._background_feat_combo.currentText().strip():
				message = "Select the granted feat or enter a custom one."
		self._background_error_message = message
		if not self._background_error_label:
			return
		if message:
			self._background_error_label.setText(message)
			self._background_error_label.show()
		else:
			self._background_error_label.hide()
		self._update_tab_highlights()

	def _current_background_record(self) -> Mapping[str, object] | None:
		if not self._selected_background_key:
			return None
		return self._background_records.get(self._selected_background_key)

	def _current_background_name(self) -> str:
		if self._background_combo:
			data = self._background_combo.currentData(Qt.ItemDataRole.UserRole)
			key = str(data or "").strip().lower()
			if key == _CUSTOM_BACKGROUND_KEY:
				if self._background_custom_edit:
					return self._background_custom_edit.text().strip()
				return self._sheet.identity.background
			if key:
				record = self._background_records.get(key)
				if record:
					name = record.get("name")
					if isinstance(name, str):
						return name
		if self._background_fallback_edit:
			return self._background_fallback_edit.text().strip()
		return self._sheet.identity.background

	def _gather_background_ability_choices(self) -> List[str]:
		choices: List[str] = []
		for combo in self._background_ability_inputs:
			value = str(combo.currentData(Qt.ItemDataRole.UserRole) or "").upper()
			if value:
				choices.append(value)
		return choices

	def _gather_background_language_choices(self) -> List[str]:
		choices: List[str] = []
		for combo in self._background_language_inputs:
			text = combo.currentText().strip()
			if text:
				choices.append(text)
		return choices

	def _gather_background_tool_choices(self) -> List[str]:
		choices: List[str] = []
		for edit in self._background_tool_inputs:
			text = edit.text().strip()
			if text:
				choices.append(text)
		return choices

	def _gather_background_feat_choice(self) -> str:
		if self._background_feat_combo:
			return self._background_feat_combo.currentText().strip()
		selection = self._stored_background_selection()
		return selection.feat_choice.strip()

	def _match_background_key(self, name: str | None) -> str | None:
		key = _normalise_background_key(name or "")
		if key and key in self._background_records:
			return key
		return None

	def _load_compendium(self) -> Compendium | None:
		try:
			return Compendium.load()
		except Exception:
			return None

	def _load_background_records(self) -> Dict[str, Mapping[str, object]]:
		if not self._compendium:
			return {}
		index: Dict[str, Mapping[str, object]] = {}
		for record in self._compendium.records("backgrounds"):
			if not isinstance(record, Mapping):
				continue
			name = record.get("name")
			if not isinstance(name, str):
				continue
			index[_normalise_background_key(name)] = record
		return index

	def _load_feat_names(self) -> List[str]:
		if not self._compendium:
			return []
		names: List[str] = []
		for record in self._compendium.records("feats"):
			if not isinstance(record, Mapping):
				continue
			name = record.get("name")
			if isinstance(name, str) and name.strip():
				names.append(name.strip())
		return sorted(dict.fromkeys(names), key=lambda value: value.lower())

	def _load_feat_records(self) -> Dict[str, Mapping[str, object]]:
		if not self._compendium:
			return {}
		index: Dict[str, Mapping[str, object]] = {}
		for record in self._compendium.records("feats"):
			if not isinstance(record, Mapping):
				continue
			name = record.get("name")
			if not isinstance(name, str) or not name.strip():
				continue
			index[name.strip().lower()] = record
		return index

	def _format_feat_details(self, record: Mapping[str, object]) -> str:
		lines: List[str] = []
		level = record.get("level")
		if isinstance(level, int):
			lines.append(f"Level: {level}")
		prereq = record.get("prerequisites")
		if isinstance(prereq, list) and prereq:
			parts: List[str] = []
			for item in prereq:
				if isinstance(item, str) and item.strip():
					parts.append(item.strip())
				elif isinstance(item, Mapping):
					text = item.get("text")
					if isinstance(text, str) and text.strip():
						parts.append(text.strip())
			if parts:
				lines.append("Prerequisites: " + ", ".join(parts))
		ability_bonus = record.get("ability_bonus_options")
		if isinstance(ability_bonus, Mapping):
			choose = ability_bonus.get("choose")
			amount = ability_bonus.get("amount")
			abilities = ability_bonus.get("abilities")
			if isinstance(choose, int) and isinstance(amount, int) and isinstance(abilities, list) and abilities:
				opts = ", ".join(str(a) for a in abilities)
				lines.append(f"Ability Bonus: Choose {choose} ability(+{amount}) from {opts}")
		features = record.get("features")
		if isinstance(features, list) and features:
			lines.append("")
			for feat in features:
				if not isinstance(feat, Mapping):
					continue
				name = feat.get("name")
				desc = feat.get("description")
				if isinstance(name, str) and name.strip():
					lines.append(name.strip())
				if isinstance(desc, str) and desc.strip():
					lines.append(desc.strip())
				lines.append("")
		text = "\n".join(lines).strip()
		return text

	@staticmethod
	def _clear_layout(layout: QLayout) -> None:
		while layout.count():
			item = layout.takeAt(0)
			widget = item.widget()
			if widget:
				widget.deleteLater()
				continue
			sub_layout = item.layout()
			if sub_layout:
				SpellcastingSettingsDialog._clear_layout(sub_layout)

	def _build_ability_generation_controls(self, form: QFormLayout) -> None:
		stored_mode = (self._sheet.identity.ability_generation or "manual").lower()
		if self._point_buy_rules:
			label = f"Use Point Buy ({self._point_buy_rules.pool} pts)"
			toggle = QCheckBox(label)
			toggle.setChecked(stored_mode == "point_buy")
			toggle.toggled.connect(self._on_ability_generation_changed)
			self.point_buy_toggle = toggle
			form.addRow("Ability Method", toggle)
		else:
			info = QLabel("Manual ability scores only (point-buy rules unavailable).")
			info.setStyleSheet("color: #5f6b7c;")
			form.addRow("Ability Method", info)

		summary = QLabel()
		summary.setStyleSheet("color: #5f6b7c;")
		self.point_buy_summary_label = summary
		form.addRow("", summary)

		error_label = QLabel()
		error_label.setStyleSheet("color: #d95c5c;")
		error_label.hide()
		self.point_buy_error_label = error_label
		form.addRow("", error_label)

	def _build_asi_controls(self, form: QFormLayout) -> None:
		if not self._point_buy_rules or not self._point_buy_rules.asi_levels:
			return
		group = QGroupBox("ASI or Feat Choices")
		layout = QFormLayout(group)
		stored = dict(self._sheet.identity.asi_choices or {})
		self._asi_choice_inputs = {}
		self._asi_ability_inputs = {}
		self._asi_feat_labels = {}
		self._asi_feat_buttons = {}
		self._asi_detail_widgets = {}
		self._asi_row_widgets = {}
		for level in self._point_buy_rules.asi_levels:
			label_widget = QLabel(f"Level {level}")
			row = QWidget()
			row_layout = QVBoxLayout(row)
			row_layout.setContentsMargins(0, 0, 0, 0)
			row_layout.setSpacing(6)

			mode_combo = QComboBox()
			mode_combo.addItem("Undecided", "")
			mode_combo.addItem("Ability Score Increase", "asi")
			if self._point_buy_rules.asi_or_feat_choice:
				mode_combo.addItem("Feat Selection", "feat")
			mode_combo.currentIndexChanged.connect(self._on_asi_inputs_changed)
			row_layout.addWidget(mode_combo)

			asi_row = QWidget()
			asi_layout = QHBoxLayout(asi_row)
			asi_layout.setContentsMargins(0, 0, 0, 0)
			asi_layout.setSpacing(8)
			ability_1 = QComboBox()
			ability_2 = QComboBox()
			ability_1.addItem("Ability 1", "")
			ability_2.addItem("Ability 2", "")
			for ability in ABILITY_NAMES:
				ability_1.addItem(ability, ability)
				ability_2.addItem(ability, ability)
			ability_1.currentIndexChanged.connect(self._on_asi_inputs_changed)
			ability_2.currentIndexChanged.connect(self._on_asi_inputs_changed)
			asi_layout.addWidget(ability_1)
			asi_layout.addWidget(ability_2)
			asi_layout.addStretch()
			row_layout.addWidget(asi_row)

			feat_row = QWidget()
			feat_layout = QHBoxLayout(feat_row)
			feat_layout.setContentsMargins(0, 0, 0, 0)
			feat_layout.setSpacing(8)
			feat_label = QLabel("None")
			feat_label.setWordWrap(True)
			feat_button = QPushButton("Choose Feat…")
			feat_button.clicked.connect(lambda _checked=False, lvl=level: self._choose_asi_feat(lvl))
			feat_layout.addWidget(feat_label, 1)
			feat_layout.addWidget(feat_button)
			row_layout.addWidget(feat_row)

			mode, feat_name, abilities = self._parse_asi_choice(stored.get(level, ""))
			if mode:
				idx = mode_combo.findData(mode)
				if idx >= 0:
					mode_combo.setCurrentIndex(idx)
			if abilities:
				if len(abilities) >= 1 and abilities[0]:
					idx = ability_1.findData(abilities[0])
					if idx >= 0:
						ability_1.setCurrentIndex(idx)
				if len(abilities) >= 2 and abilities[1]:
					idx = ability_2.findData(abilities[1])
					if idx >= 0:
						ability_2.setCurrentIndex(idx)
			if feat_name:
				feat_label.setText(feat_name)

			layout.addRow(label_widget, row)
			self._asi_choice_inputs[level] = mode_combo
			self._asi_ability_inputs[level] = (ability_1, ability_2)
			self._asi_feat_labels[level] = feat_label
			self._asi_feat_buttons[level] = feat_button
			self._asi_detail_widgets[level] = (asi_row, feat_row)
			self._asi_row_widgets[level] = (label_widget, row)
		placeholder = QLabel()
		placeholder.setStyleSheet("color: #5f6b7c; font-style: italic;")
		placeholder.setWordWrap(True)
		placeholder.hide()
		layout.addRow("", placeholder)
		self.asi_placeholder_label = placeholder
		status = QLabel()
		status.setStyleSheet("color: #d95c5c;")
		self.asi_status_label = status
		layout.addRow("", status)
		self.asi_group = group
		form.addRow(group)
		self._refresh_asi_visibility()
		self._refresh_asi_choice_state()

	def _on_asi_inputs_changed(self, *_args: object) -> None:
		"""UI handler for ASI widgets.

		Updates missing-level validation and recomputes derived stats that depend on
		ability modifiers (spellcasting, HP, saves/skills).
		"""

		self._refresh_asi_choice_state()
		self._refresh_level_dependent_fields()

	def _parse_asi_choice(self, value: object) -> Tuple[str, str, List[str]]:
		text = str(value or "").strip()
		if not text:
			return "", "", []
		lower = text.lower()
		if lower.startswith("feat:"):
			return "feat", text.split(":", 1)[1].strip(), []
		if lower.startswith("asi:"):
			payload = text.split(":", 1)[1]
			parts = [part.strip().upper() for part in payload.split(",") if part.strip()]
			return "asi", "", parts[:2]
		# Legacy encoding: only tracks the mode.
		if lower in {"ability", "asi"}:
			return "asi", "", []
		if lower == "feat":
			return "feat", "", []
		return "", "", []

	def _encode_asi_choice(self, level: int) -> str:
		mode_combo = self._asi_choice_inputs.get(level)
		mode = str(mode_combo.currentData() or "").strip() if mode_combo else ""
		if mode == "asi":
			inputs = self._asi_ability_inputs.get(level)
			if not inputs:
				return ""
			a1 = str(inputs[0].currentData() or "").strip().upper()
			a2 = str(inputs[1].currentData() or "").strip().upper()
			if not (a1 and a2):
				return ""
			return f"asi:{a1},{a2}"
		if mode == "feat":
			label = self._asi_feat_labels.get(level)
			name = (label.text() if label else "").strip()
			if not name or name.lower() == "none":
				return ""
			return f"feat:{name}"
		return ""

	def _choose_asi_feat(self, level: int) -> None:
		initial = ""
		label = self._asi_feat_labels.get(level)
		if label:
			initial = label.text().strip()
		name = self._pick_feat(initial=initial)
		if not name:
			return
		if label:
			label.setText(name)
		self._on_asi_inputs_changed()

	def _current_ability_generation_mode(self) -> str:
		if self.point_buy_toggle and self.point_buy_toggle.isChecked():
			return "point_buy"
		return "manual"

	def _point_buy_enabled(self) -> bool:
		return bool(self._point_buy_rules and self.point_buy_toggle and self.point_buy_toggle.isChecked())

	def _apply_point_buy_bounds(self) -> None:
		if not self.ability_group:
			return
		if self._point_buy_enabled():
			rules = self._point_buy_rules
			if rules:
				self.ability_group.set_score_bounds(rules.min_score, rules.max_score)
		else:
			self.ability_group.set_score_bounds(1, 30)

	def _on_ability_generation_changed(self, _checked: bool) -> None:
		self._apply_point_buy_bounds()
		self._update_point_buy_summary()

	def _calculate_point_buy_cost(self) -> Tuple[int, str | None]:
		if not self.ability_group or not self._point_buy_rules:
			return 0, None
		total = 0
		rules = self._point_buy_rules
		for ability, value in self.ability_group.scores().items():
			if value < rules.min_score or value > rules.max_score:
				return total, f"{ability} score must be between {rules.min_score} and {rules.max_score}."
			cost = rules.costs.get(value)
			if cost is None:
				return total, f"No point-buy cost defined for score {value}."
			total += cost
		return total, None

	def _update_point_buy_summary(self) -> None:
		if not self.point_buy_summary_label:
			return
		if not self._point_buy_rules:
			self.point_buy_summary_label.setText("Point-buy rules unavailable for this dataset.")
			if self.point_buy_error_label:
				self.point_buy_error_label.hide()
			self._point_buy_error_message = None
			self._update_tab_highlights()
			return
		if not self._point_buy_enabled():
			self.point_buy_summary_label.setText("Manual ability scores enabled.")
			if self.point_buy_error_label:
				self.point_buy_error_label.hide()
			self._point_buy_error_message = None
			self._update_tab_highlights()
			return
		total, error = self._calculate_point_buy_cost()
		remaining = self._point_buy_rules.pool - total
		self.point_buy_summary_label.setText(
			f"Point Buy: {max(remaining, 0)} pts remaining (spent {total}/{self._point_buy_rules.pool})."
		)
		if error:
			if self.point_buy_error_label:
				self.point_buy_error_label.setText(error)
				self.point_buy_error_label.show()
			self._point_buy_error_message = error
			self._update_tab_highlights()
			return
		if remaining < 0:
			message = f"Over budget by {abs(remaining)} point(s)."
			if self.point_buy_error_label:
				self.point_buy_error_label.setText(message)
				self.point_buy_error_label.show()
			self._point_buy_error_message = message
			self._update_tab_highlights()
			return
		if self.point_buy_error_label:
			self.point_buy_error_label.hide()
		self._point_buy_error_message = None
		self._update_tab_highlights()

	def _refresh_asi_choice_state(self) -> None:
		if not self._asi_choice_inputs:
			self._asi_missing_levels = []
			self._refresh_asi_visibility()
			self._update_tab_highlights()
			return
		classes = self._current_class_progression()
		current_level = self._sum_class_levels(classes)
		missing: List[int] = []
		for level, combo in self._asi_choice_inputs.items():
			if level > current_level:
				continue
			mode = str(combo.currentData() or "").strip()
			asi_row, feat_row = self._asi_detail_widgets.get(level, (None, None))
			if asi_row is not None:
				asi_row.setVisible(mode == "asi")
			if feat_row is not None:
				feat_row.setVisible(mode == "feat")
			if not mode:
				missing.append(level)
				continue
			if mode == "asi":
				inputs = self._asi_ability_inputs.get(level)
				a1 = str(inputs[0].currentData() or "").strip() if inputs else ""
				a2 = str(inputs[1].currentData() or "").strip() if inputs else ""
				if not (a1 and a2):
					missing.append(level)
				continue
			if mode == "feat":
				label = self._asi_feat_labels.get(level)
				feat_name = (label.text() if label else "").strip()
				if not feat_name or feat_name.lower() == "none":
					missing.append(level)
		if self.asi_status_label:
			if missing:
				levels_text = ", ".join(str(level) for level in missing)
				self.asi_status_label.setText(f"Select ASI or Feat for levels: {levels_text}.")
			else:
				self.asi_status_label.setText("")
		self._asi_missing_levels = missing
		self._refresh_asi_score_bonuses(current_level=current_level)
		self._refresh_asi_visibility()
		# Do not call _refresh_level_dependent_fields() from here; that method
		# triggers ASI validation and would recurse.
		self._refresh_overview_panels()
		self._update_tab_highlights()

	def _refresh_asi_visibility(self) -> None:
		if not self._asi_row_widgets:
			if self.asi_placeholder_label:
				self.asi_placeholder_label.hide()
			return
		current_level = self._current_total_level()
		visible_any = False
		for level, widgets in self._asi_row_widgets.items():
			visible = level <= current_level
			for widget in widgets:
				widget.setVisible(visible)
			if visible:
				visible_any = True
		if not self.asi_placeholder_label:
			return
		if visible_any:
			self.asi_placeholder_label.hide()
			return
		next_levels = sorted(level for level in self._asi_row_widgets if level > current_level)
		if next_levels:
			next_level = next_levels[0]
			message = f"Ability Score Improvements unlock at level {next_level}. Reach that level to choose an ASI or feat."
		else:
			message = "All Ability Score Improvements have been assigned."
		self.asi_placeholder_label.setText(message)
		self.asi_placeholder_label.show()

	def _refresh_asi_score_bonuses(self, *, current_level: int | None = None) -> None:
		"""Recompute +1 bonuses granted by ASI selections.

		We intentionally do not mutate base ability scores. Instead we apply these bonuses
		when computing derived modifiers and Overview displays.
		"""

		bonuses: Dict[str, int] = {ability: 0 for ability in ABILITY_NAMES}
		current_level = int(current_level) if current_level is not None else self._current_total_level()
		choices = self._gather_asi_choices(current_level=current_level)
		for level, encoded in (choices or {}).items():
			try:
				lvl = int(level)
			except (TypeError, ValueError):
				continue
			if lvl <= 0 or lvl > current_level:
				continue
			mode, _feat_name, abilities = self._parse_asi_choice(encoded)
			if mode != "asi":
				continue
			for ability in abilities:
				ab = str(ability or "").strip().upper()
				if ab in bonuses:
					bonuses[ab] += 1
		self._cached_asi_score_bonuses = bonuses
		if self._saves_skills_group:
			self._saves_skills_group.set_ability_score_bonuses(bonuses)

	def _gather_asi_choices(self, *, current_level: int | None = None) -> Dict[int, str]:
		if not self._asi_choice_inputs:
			return {}
		choices: Dict[int, str] = {}
		current_level = int(current_level) if current_level is not None else self._current_total_level()
		for level in self._asi_choice_inputs:
			if level > current_level:
				continue
			encoded = self._encode_asi_choice(level)
			if encoded:
				choices[level] = encoded
		return choices

	def _validate_before_accept(self) -> bool:
		# Non-blocking: allow saving even when incomplete; visually warn via tab highlight.
		self._update_tab_highlights()
		return True

	def _collect_validation_issues(self) -> List[str]:
		issues: List[str] = []
		if self._point_buy_enabled() and self._point_buy_error_message:
			issues.append(self._point_buy_error_message)
		if self._asi_missing_levels:
			issues.append("Missing ASI/Feat selections")
		if self._background_error_message:
			issues.append(self._background_error_message)
		if self.class_options_group and self._class_option_snapshot:
			current = self.class_options_group.current_selections()
			for group in self._class_option_snapshot.groups:
				required = max(0, group.max_choices)
				if required <= 0:
					continue
				selected = len([value for value in current.get(group.key, []) if value])
				if selected < required:
					issues.append(f"Incomplete class options: {group.label}")
					break
		if self._current_total_level() > self._max_character_level:
			issues.append("Character level exceeds maximum")
		return issues

	def _update_tab_highlights(self) -> None:
		if not hasattr(self, "tabs") or not self.tabs:
			return
		tab_bar = self.tabs.tabBar()
		if not self._default_tab_text_colors:
			self._default_tab_text_colors = {idx: tab_bar.tabTextColor(idx) for idx in range(self.tabs.count())}
		for idx in range(self.tabs.count()):
			default = self._default_tab_text_colors.get(idx)
			if default is not None:
				tab_bar.setTabTextColor(idx, default)
		issues = self._collect_validation_issues()
		if not issues:
			return
		builder_idx = self._builder_tab_index
		if builder_idx is None:
			builder_idx = max(0, self.tabs.count() - 1)
		tab_bar.setTabTextColor(builder_idx, QColor(Qt.GlobalColor.red))
	def _build_builder_tab(self) -> None:
		tab = QWidget(objectName="builder_tab")
		root = QVBoxLayout(tab)
		root.setContentsMargins(0, 0, 0, 0)
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.Shape.NoFrame)
		content = QWidget()
		outer = QVBoxLayout(content)
		outer.setContentsMargins(8, 8, 8, 8)
		outer.setSpacing(10)
		scroll.setWidget(content)
		root.addWidget(scroll)

		def add_collapsible(title: str, expanded: bool = True) -> QWidget:
			header = QToolButton()
			header.setText(title)
			header.setCheckable(True)
			header.setChecked(expanded)
			header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
			header.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
			body = QWidget()
			body.setVisible(expanded)

			def toggle(checked: bool) -> None:
				body.setVisible(checked)
				header.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
			header.toggled.connect(toggle)

			outer.addWidget(header)
			outer.addWidget(body)
			return body

		# Character name (always visible, at the very top)
		name_widget = QWidget()
		name_form = QFormLayout(name_widget)
		name_form.setHorizontalSpacing(16)
		name_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
		self.name_edit = QLineEdit(self._sheet.identity.name)
		self.name_edit.textChanged.connect(self._on_name_text_changed)
		name_form.addRow("Character Name", self.name_edit)
		outer.addWidget(name_widget)

		# Starting Stats
		starting_body = add_collapsible("Starting Stats", expanded=False)
		starting_form = QFormLayout(starting_body)
		starting_form.setHorizontalSpacing(16)
		starting_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
		self._build_ability_generation_controls(starting_form)
		initial_scores = {ability: self._sheet.get_ability(ability).score for ability in ABILITY_NAMES}
		initial_modifiers = {ability: self._sheet.get_ability(ability).effective_modifier() for ability in ABILITY_NAMES}
		self.ability_group = AbilityScoresGroup(
			ability_names=ABILITY_NAMES,
			initial_scores=initial_scores,
			initial_modifiers=initial_modifiers,
			modifier_formatter=self._format_modifier,
		)
		self.ability_group.score_changed.connect(self._on_ability_score_changed)
		starting_form.addRow(self.ability_group)

		# Identity & Background
		identity_body = add_collapsible("Identity & Background", expanded=False)
		identity_form = QFormLayout(identity_body)
		identity_form.setHorizontalSpacing(16)
		identity_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
		self._build_background_controls(identity_form)

		# Classes, Features, Options
		classes_body = add_collapsible("Classes & Features", expanded=False)
		classes_layout = QVBoxLayout(classes_body)
		classes_layout.setContentsMargins(0, 0, 0, 0)
		classes_layout.setSpacing(10)

		class_group = QGroupBox("Class Levels")
		class_layout = QVBoxLayout(class_group)
		self.class_table = ClassProgressionTable()
		self.class_table.setMinimumHeight(160)
		class_layout.addWidget(self.class_table)
		controls = QHBoxLayout()
		add_btn = QPushButton("Add")
		add_btn.clicked.connect(self._add_class_entry)
		edit_btn = QPushButton("Edit")
		edit_btn.clicked.connect(self._edit_selected_class_entry)
		remove_btn = QPushButton("Remove")
		remove_btn.clicked.connect(self._remove_selected_class_entry)
		controls.addWidget(add_btn)
		controls.addWidget(edit_btn)
		controls.addWidget(remove_btn)
		controls.addStretch()
		class_layout.addLayout(controls)

		self.class_features_group = ClassFeaturesGroup(self)
		self.class_features_group.setMinimumWidth(320)
		self.class_features_group.selectionChanged.connect(self._on_feature_option_changed)
		self.class_features_group.sectionCollapsed.connect(self._on_feature_section_collapsed)
		self.class_features_group.sectionExpanded.connect(self._on_feature_section_expanded)
		self.class_options_group = ClassOptionsGroup(self)
		self.class_options_group.setMinimumWidth(280)
		self.class_options_group.selectionChanged.connect(self._on_class_option_changed)
		self.class_options_group.requestPick.connect(self._on_class_option_picker_requested)

		class_row = QWidget()
		class_row_layout = QHBoxLayout(class_row)
		class_row_layout.setContentsMargins(0, 0, 0, 0)
		class_row_layout.setSpacing(12)
		class_group.setMinimumWidth(420)
		class_row_layout.addWidget(class_group, 3)
		class_row_layout.addWidget(self.class_features_group, 2)
		class_row_layout.addWidget(self.class_options_group, 2)
		classes_layout.addWidget(class_row)

		self.feature_timeline_group = FeatureTimelineGroup(self)
		classes_layout.addWidget(self.feature_timeline_group)

		self.class_table.populate(self._sheet.identity.classes)
		self.class_table.progressions_changed.connect(self._on_class_progressions_changed)

		# ASI / Feat choice controls
		asi_body = add_collapsible("Ability Score Improvements", expanded=False)
		asi_form = QFormLayout(asi_body)
		asi_form.setHorizontalSpacing(16)
		asi_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
		self._build_asi_controls(asi_form)

		# Feats
		feats_body = add_collapsible("Feats", expanded=False)
		feats_layout = QVBoxLayout(feats_body)
		feats_layout.setContentsMargins(0, 0, 0, 0)
		feats_layout.setSpacing(8)
		self.feats_table = FeatsTable(self)
		self.feats_table.populate(self._sheet.features)
		feats_layout.addWidget(self.feats_table)
		feats_controls = QHBoxLayout()
		add_feat_btn = QPushButton("Add")
		add_feat_btn.clicked.connect(self._add_feat_entry)
		edit_feat_btn = QPushButton("Edit")
		edit_feat_btn.clicked.connect(self._edit_selected_feat_entry)
		remove_feat_btn = QPushButton("Remove")
		remove_feat_btn.clicked.connect(self._remove_selected_feat_entry)
		feats_controls.addWidget(add_feat_btn)
		feats_controls.addWidget(edit_feat_btn)
		feats_controls.addWidget(remove_feat_btn)
		feats_controls.addStretch()
		feats_layout.addLayout(feats_controls)

		# Modifiers
		mods_body = add_collapsible("Modifiers", expanded=False)
		mods_layout = QVBoxLayout(mods_body)
		mods_layout.setContentsMargins(0, 0, 0, 0)
		self.modifiers_group = ModifiersGroup(self._modifier_definitions, self._modifier_states, parent=self)
		mods_layout.addWidget(self.modifiers_group)

		outer.addStretch()
		self._builder_tab_index = self.tabs.addTab(tab, "Builder")
		self._update_tab_highlights()

	def _pick_feat(self, *, initial: str = "") -> str | None:
		if not self._compendium:
			return None
		records = [record for record in self._compendium.records("feats") if isinstance(record, dict)]
		items = build_picker_items(records, detail_formatter=self._format_feat_details)
		dialog = CompendiumPickerDialog(
			title="Choose Feat",
			items=items,
			initial_selection=[initial] if initial and initial.lower() != "none" else [],
			max_choices=1,
			parent=self,
		)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return None
		values = dialog.selected_values()
		return values[0] if values else None

	def _add_feat_entry(self) -> None:
		if not self.feats_table:
			return
		name = self._pick_feat()
		if not name:
			return
		record = self._feat_records.get(name.lower(), {})
		source_id = record.get("source_id") if isinstance(record, Mapping) else None
		source = str(source_id).strip() if isinstance(source_id, str) and source_id.strip() else "Feat"
		details = self._format_feat_details(record) if isinstance(record, Mapping) else ""
		self.feats_table.append_entry(FeatureEntry(title=name, source=source, description=details))

	def _edit_selected_feat_entry(self) -> None:
		if not self.feats_table:
			return
		row = self.feats_table.selected_row()
		if row < 0:
			return
		existing = self.feats_table.entry_at(row)
		name = self._pick_feat(initial=existing.title if existing else "")
		if not name:
			return
		record = self._feat_records.get(name.lower(), {})
		source_id = record.get("source_id") if isinstance(record, Mapping) else None
		source = str(source_id).strip() if isinstance(source_id, str) and source_id.strip() else (existing.source if existing else "Feat")
		details = self._format_feat_details(record) if isinstance(record, Mapping) else (existing.description if existing else "")
		self.feats_table.replace_entry(row, FeatureEntry(title=name, source=source, description=details))

	def _remove_selected_feat_entry(self) -> None:
		if self.feats_table:
			self.feats_table.remove_selected_row()

	def _build_spells_tab(self) -> None:
		tab = QWidget()
		root = QVBoxLayout(tab)
		root.setContentsMargins(0, 0, 0, 0)
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.Shape.NoFrame)
		content = QWidget()
		layout = QVBoxLayout(content)
		layout.setContentsMargins(8, 8, 8, 8)
		layout.setSpacing(8)
		scroll.setWidget(content)
		root.addWidget(scroll)

		split_layout = QHBoxLayout()
		split_layout.setContentsMargins(0, 0, 0, 0)
		split_layout.setSpacing(12)

		source_panel = QVBoxLayout()
		source_panel.setContentsMargins(0, 0, 0, 0)
		source_panel.setSpacing(6)
		source_label = QLabel("Spell Sources")
		source_label.setStyleSheet("font-weight: 600;")
		source_panel.addWidget(source_label)
		self.spell_source_list = QListWidget()
		self.spell_source_list.itemSelectionChanged.connect(self._on_spell_source_selection_changed)
		self.spell_source_list.itemDoubleClicked.connect(self._on_spell_source_double_clicked)
		source_panel.addWidget(self.spell_source_list)
		source_controls = QHBoxLayout()
		add_source_button = QPushButton("Add Spell Source…")
		add_source_button.clicked.connect(self._add_spell_source)
		add_missing_button = QPushButton("Add Missing Sources")
		add_missing_button.clicked.connect(self._add_missing_spell_sources)
		remove_source_button = QPushButton("Remove Selected Source")
		remove_source_button.clicked.connect(self._remove_selected_spell_source)
		source_controls.addWidget(add_source_button)
		source_controls.addWidget(add_missing_button)
		source_controls.addWidget(remove_source_button)
		source_controls.addStretch()
		source_panel.addLayout(source_controls)
		split_layout.addLayout(source_panel, 1)

		spell_panel = QVBoxLayout()
		spell_panel.setContentsMargins(0, 0, 0, 0)
		spell_panel.setSpacing(8)
		self.spell_table.setParent(content)
		self.spell_table.setMinimumHeight(240)
		spell_panel.addWidget(self.spell_table)

		controls = QHBoxLayout()
		remove_button = QPushButton("Remove Selected Spells")
		remove_button.clicked.connect(self._remove_selected_spells)
		controls.addWidget(remove_button)
		controls.addStretch()
		spell_panel.addLayout(controls)
		split_layout.addLayout(spell_panel, 3)

		layout.addLayout(split_layout)

		for entry in self._sheet.spellcasting.known_spells:
			self.spell_table.append_entry(entry)
		self._spell_table_ready = True
		self._sync_spell_entry_abilities()
		self._rebuild_spell_source_list()
		self._apply_spell_source_filter()
		self._on_known_spells_updated()

		self.tabs.addTab(tab, "Spells")

	def _build_equipment_tab(self) -> None:
		tab = QWidget()
		root = QVBoxLayout(tab)
		root.setContentsMargins(0, 0, 0, 0)
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setFrameShape(QFrame.Shape.NoFrame)
		content = QWidget()
		layout = QVBoxLayout(content)
		layout.setContentsMargins(8, 8, 8, 8)
		layout.setSpacing(8)
		scroll.setWidget(content)
		root.addWidget(scroll)

		self.equipment_table.setParent(content)
		self.equipment_table.setMinimumHeight(200)
		layout.addWidget(self.equipment_table)

		controls = QHBoxLayout()
		add_button = QPushButton("Add from Ruleset")
		add_button.clicked.connect(self._add_equipment_entry)
		add_custom_button = QPushButton("Add Custom")
		add_custom_button.clicked.connect(self._on_add_custom_item)
		remove_button = QPushButton("Remove Selected")
		remove_button.clicked.connect(self._remove_selected_equipment)
		controls.addWidget(add_button)
		controls.addWidget(add_custom_button)
		controls.addWidget(remove_button)
		controls.addStretch()
		layout.addLayout(controls)

		for item in self._sheet.equipment:
			self.equipment_table.append_entry(item)
		self._equipment_table_ready = True

		self.tabs.addTab(tab, "Items")

	# Modifiers are now part of the Builder tab.

	def _apply_initial_geometry(self) -> None:
		"""Ensure the dialog opens wider than the default size hint."""

		hint = self.sizeHint()
		if not hint.isValid():
			return
		new_width = int(hint.width() * 2)
		self.resize(new_width, hint.height())

	def _on_ability_score_changed(self, _ability: str, _value: int) -> None:
		# Keep working sheet updated so derived displays (e.g., saves/skills) stay consistent.
		try:
			block = self._sheet.get_ability(_ability)
			block.score = int(_value)
		except Exception:
			pass
		self._refresh_level_dependent_fields()
		self._update_point_buy_summary()
		self._refresh_overview_panels()
		if self._saves_skills_group:
			self._saves_skills_group.set_sheet(self._sheet)

	def _on_name_text_changed(self, _text: str) -> None:
		self._sheet.identity.name = _text
		self._refresh_overview_panels()

	def _on_species_changed(self, _index: int) -> None:
		if not self._species_combo:
			return
		value = self._species_combo.currentData(Qt.ItemDataRole.UserRole)
		self._sheet.identity.ancestry = str(value or "").strip()
		self._refresh_species_subtype_options()
		self._refresh_level_dependent_fields()

	def _on_species_subtype_changed(self, _index: int) -> None:
		if not self._species_subtype_combo:
			return
		value = self._species_subtype_combo.currentData(Qt.ItemDataRole.UserRole)
		self._sheet.identity.ancestry_subtype = str(value or "").strip()
		self._refresh_level_dependent_fields()

	def _refresh_species_subtype_options(self) -> None:
		combo = self._species_subtype_combo
		if not (combo and self._compendium):
			return
		species_name = (self._sheet.identity.ancestry or "").strip()
		record: Mapping[str, object] | None = None
		for entry in self._compendium.records("species"):
			if not isinstance(entry, Mapping):
				continue
			name = entry.get("name")
			if isinstance(name, str) and name.strip() == species_name:
				record = entry
				break
		subtypes = []
		if record:
			raw = record.get("subtypes")
			if isinstance(raw, list):
				subtypes = [s for s in raw if isinstance(s, Mapping) and isinstance(s.get("name"), str)]
		combo.blockSignals(True)
		try:
			combo.clear()
			combo.addItem("(None)", "")
			if subtypes:
				for st in sorted(subtypes, key=lambda s: str(s.get("name", "")).lower()):
					st_name = str(st.get("name") or "").strip()
					combo.addItem(st_name, st_name)
				combo.setEnabled(True)
			else:
				combo.setEnabled(False)
			current = (self._sheet.identity.ancestry_subtype or "").strip()
			if current and any(str(st.get("name") or "").strip() == current for st in subtypes):
				combo.setCurrentText(current)
			else:
				self._sheet.identity.ancestry_subtype = ""
				combo.setCurrentIndex(0)
		finally:
			combo.blockSignals(False)

	def _on_class_progressions_changed(self) -> None:
		# Keep working sheet in sync for any read-only/derived displays.
		self._sheet.identity.classes = self._current_class_progression()
		self._refresh_level_dependent_fields()
		self._refresh_feature_rules()
		self._refresh_class_options()
		self._refresh_asi_choice_state()
		self._refresh_overview_panels()

	def _refresh_level_summary(self) -> None:
		if not self.level_total_label:
			return
		total = self._current_total_level()
		cap = self._max_character_level
		text = f"{total} / {cap}"
		if total > cap:
			self.level_total_label.setStyleSheet("font-weight: 600; color: #d95c5c;")
			text += " (exceeds maximum)"
		else:
			self.level_total_label.setStyleSheet("font-weight: 600;")
		self.level_total_label.setText(text)
		self._update_tab_highlights()

	def _current_class_progression(self) -> List[ClassProgression]:
		if not self.class_table:
			return list(self._sheet.identity.classes)
		classes = [entry for entry in self.class_table.current_progressions() if entry.name and entry.level > 0]
		return classes or list(self._sheet.identity.classes)

	def _current_total_level(self) -> int:
		return self._sum_class_levels(self._current_class_progression())

	@staticmethod
	def _sum_class_levels(entries: Iterable[ClassProgression]) -> int:
		return sum(max(0, entry.level) for entry in entries)

	def _current_level_cap(self) -> int:
		return self._max_character_level

	def _remaining_level_capacity(self, exclude_row: int | None = None) -> int:
		if not self.class_table:
			return self._current_level_cap()
		entries = self.class_table.current_progressions()
		if not entries:
			entries = list(self._sheet.identity.classes)
		total = 0
		for index, entry in enumerate(entries):
			if exclude_row is not None and index == exclude_row:
				continue
			total += max(0, entry.level)
		cap = self._current_level_cap()
		return max(0, cap - total)

	def _current_equipment_entries(self) -> List[EquipmentItem]:
		if not self._equipment_table_ready:
			return list(self._sheet.equipment)
		return self.equipment_table.current_items()

	def _current_feature_entries(self) -> List[FeatureEntry]:
		if not self.feats_table:
			return list(self._sheet.features)
		return [entry for entry in self.feats_table.entries() if entry.title or entry.source or entry.description]

	def _current_spell_entries(self) -> List[SpellAccessEntry]:
		if not self.spell_table or not self._spell_table_ready:
			return list(self._sheet.spellcasting.known_spells)
		return list(self.spell_table.iter_entries())

	def _refresh_level_dependent_fields(self) -> None:
		classes = self._current_class_progression()
		self._refresh_level_summary()
		# Ensure ASI bonuses are up to date before computing derived modifiers.
		level = self._sum_class_levels(classes)
		self._refresh_asi_score_bonuses(current_level=level)
		profile = derive_spellcasting_profile(classes, self._sheet.spellcasting.spellcasting_ability)
		self._derived_spell_profile = profile
		self._derived_spell_ability = profile.ability or "INT"
		self._sync_spell_entry_abilities()
		self._sync_spell_entry_prepared_flags()
		# level computed above
		self._cached_proficiency_base = _derived_proficiency_from_level(level)
		effective_prof = self._cached_proficiency_base
		self._sheet.proficiencies.proficiency_bonus = effective_prof

		# Unified modifier-source bonuses (equipment + compendium grants).
		feat_names = [entry.title for entry in self._current_feature_entries() if (entry.title or "").strip()]
		bonus_bundle = collect_bonus_bundle(
			compendium=self._compendium,
			species_name=self._sheet.identity.ancestry,
			species_subtype_name=getattr(self._sheet.identity, "ancestry_subtype", "") or "",
			background_name=self._sheet.identity.background,
			class_progression=classes,
			feat_names=feat_names,
			equipment=self._current_equipment_entries(),
		)
		self._cached_bonus_bundle = bonus_bundle
		self._cached_trait_bundle = collect_trait_bundle(
			compendium=self._compendium,
			species_name=self._sheet.identity.ancestry,
			species_subtype_name=getattr(self._sheet.identity, "ancestry_subtype", "") or "",
			background_name=self._sheet.identity.background,
			class_progression=classes,
			feat_names=feat_names,
		)

		# Apply structured skill-rank grants.
		# Only safe when using rank map (0/1/2) or empty.
		skill_map = dict(self._sheet.proficiencies.skills or {})
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
		if is_rank_map:
			grants = collect_skill_rank_grants(
				compendium=self._compendium,
				species_name=self._sheet.identity.ancestry,
				species_subtype_name=getattr(self._sheet.identity, "ancestry_subtype", "") or "",
				background_name=self._sheet.identity.background,
				class_progression=classes,
				feat_names=feat_names,
			)
			updated, changed = apply_species_skill_grants(current_skill_map=skill_map, granted_skill_ranks=grants)
			if changed:
				self._sheet.proficiencies.skills = updated

		ability = self._derived_spell_ability or "INT"
		ability_mod = self._ability_modifier_value(ability)
		attack_base = ability_mod + effective_prof + int(bonus_bundle.get("spell_attack"))
		self._cached_attack_base = attack_base
		attack_final = attack_base

		save_base = 8 + ability_mod + effective_prof + int(bonus_bundle.get("spell_save_dc"))
		self._cached_save_base = save_base
		save_final = save_base
		self._sheet.spellcasting.attack_bonus = attack_final
		self._sheet.spellcasting.save_dc = save_final

		long_slots, short_slots = _derived_slot_buckets(classes)
		for slot_level in range(1, 10):
			bonus = int(bonus_bundle.spell_slots.get(int(slot_level), 0) or 0)
			if bonus:
				long_slots[slot_level] = max(0, int(long_slots.get(slot_level, 0) or 0) + int(bonus))
		self._cached_long_rest_slots = long_slots
		self._cached_short_rest_slots = short_slots
		self._cached_slot_base = _combine_slot_buckets(long_slots, short_slots)
		self._refresh_slot_displays()
		self._refresh_hit_points(
			classes,
			max_hp_bonus=int(bonus_bundle.get("max_hp")),
			max_hp_per_level_bonus=int(bonus_bundle.get("max_hp_per_level")),
		)
		# Derived AC (equipment + dex + bonuses).
		ac_formulas = collect_ac_formula_candidates(
			compendium=self._compendium,
			species_name=self._sheet.identity.ancestry,
			species_subtype_name=getattr(self._sheet.identity, "ancestry_subtype", "") or "",
			class_names=[entry.name for entry in classes if entry.name],
		)
		ac = derive_armor_class(
			compendium=self._compendium,
			equipment=self._current_equipment_entries(),
			dex_modifier=self._ability_modifier_value("DEX"),
			class_names=[entry.name for entry in classes if entry.name],
			con_modifier=self._ability_modifier_value("CON"),
			wis_modifier=self._ability_modifier_value("WIS"),
			species_name=self._sheet.identity.ancestry,
			species_subtype_name=getattr(self._sheet.identity, "ancestry_subtype", "") or "",
			ac_formula_candidates=ac_formulas,
			flat_ac_bonus=int(bonus_bundle.get("ac")),
		)
		self._sheet.combat.armor_class = int(ac.total)
		# Derived speed (species + equipment bonuses).
		speed = derive_speed_ft(
			compendium=self._compendium,
			species_name=self._sheet.identity.ancestry,
			species_subtype_name=self._sheet.identity.ancestry_subtype,
			equipment=None,
			bonus_ft=int(bonus_bundle.get("speed_ft")),
			base_ft_override=collect_speed_base_ft(
				compendium=self._compendium,
				species_name=self._sheet.identity.ancestry,
				species_subtype_name=getattr(self._sheet.identity, "ancestry_subtype", "") or "",
				default_base_ft=30,
			),
		)
		self._sheet.combat.speed_ft = int(speed.total_ft)
		# Derived initiative (DEX + equipment bonuses).
		initiative = derive_initiative_bonus(
			dex_modifier=self._ability_modifier_value("DEX"),
			equipment_bonus=int(bonus_bundle.get("initiative")),
		)
		self._sheet.combat.initiative_bonus = int(initiative.total)
		if self._auto_add_granted_spells(classes):
			self._sync_spell_entry_abilities()
			self._sync_spell_entry_prepared_flags()
		if self._saves_skills_group:
			self._saves_skills_group.set_sheet(self._sheet)
		self._rebuild_spell_source_list()
		self._apply_spell_source_filter()
		# Keep ASI validation/visibility in sync with level changes.
		self._refresh_asi_choice_state()
		self._refresh_overview_panels()

	def _auto_add_granted_spells(self, classes: Sequence[ClassProgression]) -> bool:
		"""Seed the spell table with compendium-granted subclass spells.

		Adds missing spells only; it does not remove spells if the class/subclass level is reduced.
		Returns True if any new spell entries were added.
		"""

		if not (self._compendium and self.spell_table and self._spell_table_ready):
			return False
		if not classes:
			return False

		existing: set[tuple[str, str, str]] = set()
		for entry in self.spell_table.iter_entries():
			spell_name = (entry.spell_name or "").strip().lower()
			source_type = (entry.source_type or "").strip().lower()
			source_id = (entry.source_id or "").strip().lower()
			if spell_name and source_type and source_id:
				existing.add((source_type, source_id, spell_name))

		added = False
		for entry in classes:
			class_name = (entry.name or "").strip()
			subclass_name = (entry.subclass or "").strip()
			if not (class_name and subclass_name):
				continue
			if entry.level <= 0:
				continue
			sub_record = self._compendium.subclass_record(class_name, subclass_name)
			if not isinstance(sub_record, Mapping):
				continue
			granted_blocks = sub_record.get("granted_spells")
			if not isinstance(granted_blocks, list):
				continue

			for block in granted_blocks:
				if not isinstance(block, Mapping):
					continue
				try:
					required_level = int(block.get("level", 0) or 0)
				except (TypeError, ValueError):
					required_level = 0
				if required_level <= 0 or required_level > entry.level:
					continue
				spells = block.get("spells")
				if not isinstance(spells, list):
					continue
				always_prepared = bool(block.get("always_prepared", False))
				for spell in spells:
					if not isinstance(spell, str):
						continue
					spell_name = spell.strip()
					if not spell_name:
						continue
					key = ("subclass", subclass_name.lower(), spell_name.lower())
					if key in existing:
						continue
					source_label = f"Subclass - {subclass_name}".strip()
					new_entry = SpellAccessEntry(
						spell_name=spell_name,
						source=source_label,
						prepared=always_prepared,
						source_type="subclass",
						source_id=subclass_name,
						granted=True,
					)
					self._ensure_spell_source_from_entry(new_entry)
					self.spell_table.append_entry(new_entry)
					existing.add(key)
					added = True

		if added:
			self._persist_spell_sources()
			self._on_known_spells_updated()
		return added

	def _spellcasting_source_modes(self) -> Dict[str, str]:
		profile = self._derived_spell_profile
		if not profile:
			return {}
		modes: Dict[str, str] = {}
		for source in profile.sources.values():
			source_type = "subclass" if source.source_type == "subclass" else "class"
			source_id = source.subclass_name if source_type == "subclass" else source.class_name
			key = build_spell_source_key(source_type, source_id, source.label)
			if not key:
				continue
			modes[key.strip().lower()] = (source.mode or "").strip().lower()
		return modes

	def _sync_spell_entry_prepared_flags(self) -> None:
		if not self.spell_table or not self._spell_table_ready:
			return
		modes = self._spellcasting_source_modes()
		if not modes:
			return
		changed = self.spell_table.sync_prepared_modes(modes)
		if changed:
			self._on_known_spells_updated()

	def _sync_spell_entry_abilities(self) -> None:
		if not self.spell_table or not self._derived_spell_profile:
			return
		entries: List[SpellAccessEntry] = []
		changed = False
		for entry in self.spell_table.iter_entries():
			desired = self._ability_for_spell_entry(entry)
			current = (entry.ability or "").upper()
			if desired and desired != current:
				entry.ability = desired
				changed = True
			elif current:
				entry.ability = current
			entries.append(entry)
		if changed:
			self.spell_table.populate(entries)
			self._rebuild_spell_source_list()
			self._apply_spell_source_filter()

	def _ability_for_spell_entry(self, entry: SpellAccessEntry) -> str | None:
		profile = self._derived_spell_profile
		fallback = (entry.ability or "").upper() or None
		if not profile:
			return fallback
		source_type = (entry.source_type or "").strip().lower()
		source_id = (entry.source_id or "").strip()
		source_label = (entry.source or "").strip()
		candidates = profile.sources.values()
		if source_type == "class":
			target = normalise_class_name(source_id or source_label)
			for candidate in candidates:
				if candidate.source_type == "class" and normalise_class_name(candidate.class_name) == target:
					return candidate.ability
		elif source_type == "subclass":
			target = normalise_subclass_name(source_id or source_label)
			for candidate in candidates:
				if candidate.source_type == "subclass" and candidate.subclass_name and normalise_subclass_name(candidate.subclass_name) == target:
					return candidate.ability
		return fallback

	def _rebuild_spell_source_list(self) -> None:
		if not self.spell_source_list:
			return
		entries = list(self.spell_table.iter_entries()) if self.spell_table else []
		summary = self._group_spells_by_source(entries)
		previous = (self._active_spell_source_key or "").strip().lower()
		self.spell_source_list.blockSignals(True)
		self.spell_source_list.clear()
		all_item = QListWidgetItem("All Sources")
		all_item.setData(Qt.ItemDataRole.UserRole, "")
		self.spell_source_list.addItem(all_item)
		selection_row = 0
		for info in summary:
			item = QListWidgetItem(info["display"])
			item.setToolTip(info["tooltip"])
			item.setData(Qt.ItemDataRole.UserRole, info["key"])
			self.spell_source_list.addItem(item)
			if info["key"] == previous:
				selection_row = self.spell_source_list.count() - 1
		self.spell_source_list.blockSignals(False)
		self.spell_source_list.setCurrentRow(selection_row)
		self._on_spell_source_selection_changed()

	def _group_spells_by_source(self, entries: List[SpellAccessEntry]) -> List[Dict[str, str]]:
		summary: Dict[str, Dict[str, object]] = {}
		for key, record in self._spell_sources.items():
			summary[key] = {
				"key": key,
				"label": record.label or record.source_id or "Spell Source",
				"type": (record.source_type or "Other").title(),
				"ability": (record.ability or ""),
				"count": 0,
			}
		for entry in entries:
			key = build_spell_source_key(entry.source_type, entry.source_id, entry.source)
			if not key:
				continue
			title_type = (entry.source_type or "Other").title()
			bucket = summary.setdefault(
				key,
				{
					"key": key,
					"label": entry.source or entry.source_id or "Unknown Source",
					"type": title_type,
					"ability": entry.ability or "",
					"count": 0,
				},
			)
			current_count = bucket.get("count", 0)
			if isinstance(current_count, (int, float)):
				numeric = int(current_count)
			elif isinstance(current_count, str):
				try:
					numeric = int(current_count)
				except ValueError:
					numeric = 0
			else:
				numeric = 0
			bucket["count"] = numeric + 1
			if entry.source and not bucket.get("label"):
				bucket["label"] = entry.source
			if entry.ability and not bucket.get("ability"):
				bucket["ability"] = entry.ability
		ordered: List[Dict[str, str]] = []
		for bucket in sorted(summary.values(), key=lambda info: (str(info["type"]).lower(), str(info["label"]).lower())):
			label = str(bucket.get("label", "Unknown Source"))
			type_name = str(bucket.get("type", "Other"))
			ability_value = str(bucket.get("ability", ""))
			ability_text = f" • {ability_value}" if ability_value else ""
			count_value = bucket.get("count", 0)
			if isinstance(count_value, (int, float)):
				count = int(count_value)
			elif isinstance(count_value, str):
				try:
					count = int(count_value)
				except ValueError:
					count = 0
			else:
				count = 0
			display = f"{label} [{type_name}] {ability_text} ({count})"
			tooltip = f"{label}\nType: {type_name}\nSpells: {count}"
			if ability_value:
				tooltip += f"\nAbility: {ability_value}"
			ordered.append({
				"key": str(bucket.get("key", "")),
				"display": display.strip(),
				"tooltip": tooltip,
			})
		return ordered

	def _baseline_spell_sources(self) -> List[Dict[str, str]]:
		profile = self._derived_spell_profile
		if not profile:
			return []
		baseline: List[Dict[str, str]] = []
		for source in profile.sources.values():
			source_type = "subclass" if source.source_type == "subclass" else "class"
			source_id = source.subclass_name if source_type == "subclass" else source.class_name
			label = source.label or source_id or "Spell Source"
			key = build_spell_source_key(source_type, source_id, label)
			if not key:
				continue
			ability = (source.ability or "").upper()
			baseline.append(
				{
					"key": key,
					"label": label,
					"type": source_type.title(),
					"ability": ability,
					"source_type": source_type,
					"source_id": source_id or "",
				}
			)
		return baseline

	def _on_spell_source_selection_changed(self) -> None:
		if not self.spell_source_list:
			return
		item = self.spell_source_list.currentItem()
		key = ""
		if item:
			value = item.data(Qt.ItemDataRole.UserRole)
			if isinstance(value, str):
				key = value.strip().lower()
		self._active_spell_source_key = key or None
		self._apply_spell_source_filter()

	def _apply_spell_source_filter(self) -> None:
		if not self.spell_table:
			return
		self.spell_table.apply_source_filter(self._active_spell_source_key)

	def _on_known_spells_updated(self) -> None:
		self._refresh_class_options()

	def _refresh_feature_rules(self) -> None:
		if not self.class_features_group:
			return
		snapshot = self._evaluate_feature_rules()
		active_keys = {group.key for group in snapshot.option_groups}
		filtered_selections = {key: value for key, value in snapshot.selections.items() if key in active_keys}
		snapshot = CharacterRuleSnapshot(snapshot.features, snapshot.option_groups, filtered_selections)
		self._feature_selections = dict(filtered_selections)
		self._rule_snapshot = snapshot
		feature_keys = self._feature_keys_from_snapshot(snapshot)
		self._feature_collapse_states = {
			key: state for key, state in self._feature_collapse_states.items() if key in feature_keys
		}
		for key in feature_keys:
			self._feature_collapse_states.setdefault(key, True)
		self.class_features_group.set_collapse_states(self._feature_collapse_states)
		self.class_features_group.set_snapshot(snapshot)
		self._feature_collapse_states = self.class_features_group.collapse_states()
		if self.feature_timeline_group:
			self.feature_timeline_group.set_timeline(snapshot, self._current_class_progression())

	def _refresh_class_options(self) -> None:
		if not self.class_options_group:
			return
		snapshot = self._evaluate_class_options()
		active_keys = {group.key for group in snapshot.groups}
		filtered = {
			key: [value for value in values if value]
			for key, values in snapshot.selections.items()
			if key in active_keys
		}
		resolved = ClassOptionSnapshot(snapshot.groups, filtered)
		self._class_option_selections = dict(filtered)
		self._class_option_snapshot = resolved
		self.class_options_group.set_snapshot(resolved)
		self._update_tab_highlights()

	def _evaluate_feature_rules(self) -> CharacterRuleSnapshot:
		temp_sheet = copy.deepcopy(self._sheet)
		temp_sheet.identity.classes = list(self._current_class_progression())
		return self._rules_service.evaluate(temp_sheet, dict(self._feature_selections))

	def _evaluate_class_options(self) -> ClassOptionSnapshot:
		temp_sheet = copy.deepcopy(self._sheet)
		temp_sheet.identity.classes = list(self._current_class_progression())
		temp_sheet.spellcasting.known_spells = self._current_spell_entries()
		return self._class_options_service.build_snapshot(
			temp_sheet,
			{key: list(values) for key, values in self._class_option_selections.items()},
		)

	def _on_feature_option_changed(self, key: str, value: str) -> None:
		self._feature_selections[key] = value

	def _on_feature_section_collapsed(self, key: str) -> None:
		self._feature_collapse_states[key] = False

	def _on_feature_section_expanded(self, key: str) -> None:
		self._feature_collapse_states[key] = True

	@staticmethod
	def _feature_keys_from_snapshot(snapshot: CharacterRuleSnapshot) -> Set[str]:
		keys: Set[str] = set()
		for feature in snapshot.features:
			key = getattr(feature, "key", "") or getattr(feature, "label", "")
			if key:
				keys.add(str(key))
		return keys

	def _on_class_option_changed(self, key: str, values: List[str]) -> None:
		self._class_option_selections[key] = list(values)
		self._update_tab_highlights()

	def _on_class_option_picker_requested(self, key: str) -> None:
		if not self._class_option_snapshot or not self.class_options_group:
			return
		group = next((entry for entry in self._class_option_snapshot.groups if entry.key == key), None)
		if not group:
			return
		items = [
			PickerItem(
				value=choice.value,
				label=choice.label or choice.value,
				details=choice.description or "",
			)
			for choice in (group.choices or [])
			if choice.value
		]
		items.sort(key=lambda item: item.label.lower())
		initial = self._class_option_selections.get(key) or list(self._class_option_snapshot.selections.get(key, []) or [])
		dialog = CompendiumPickerDialog(
			title=f"Choose {group.label}",
			items=items,
			initial_selection=initial,
			max_choices=max(1, int(group.max_choices or 1)),
			parent=self,
		)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return
		selected = dialog.selected_values()
		self.class_options_group.set_group_selection(key, selected)

	def _refresh_slot_displays(self) -> None:
		if not self._builder_spell_slots_label:
			return
		parts: List[str] = []
		for level in range(1, 10):
			count = int(self._cached_slot_base.get(level, 0) or 0)
			if count <= 0:
				continue
			parts.append(f"{level}: {count}")
		self._builder_spell_slots_label.setText("Slots by level: " + (", ".join(parts) if parts else "None"))

	def _equipment_slot_bonus(self, spell_level: int) -> int:
		level = int(spell_level)
		keys = {
			f"spell_slot_{level}",
			f"spell_slots_{level}",
			f"slot_{level}",
			f"slots_{level}",
			f"slot_level_{level}",
		}
		return self._equipment_bonus(keys)

	def _ability_modifier_value(self, ability: str) -> int:
		key = (ability or "").strip().upper()
		bonus = int(self._cached_asi_score_bonuses.get(key, 0) or 0)
		if self.ability_group:
			score = int(self.ability_group.score_for(key)) + bonus
			return (score - 10) // 2
		try:
			block = self._sheet.get_ability(key)
		except Exception:
			return 0
		if block.modifier is not None:
			return int(block.modifier)
		score = int(block.score) + bonus
		return (score - 10) // 2

	def _equipment_bonus(self, keys: Iterable[str]) -> int:
		key_set = {key.lower() for key in keys}
		total = 0
		for item in self._current_equipment_entries():
			for key, value in (item.bonuses or {}).items():
				if str(key).lower() in key_set:
					try:
						total += int(value)
					except (TypeError, ValueError):
						continue
		return total

	def _add_class_entry(self) -> None:
		available = self._remaining_level_capacity()
		cap = self._current_level_cap()
		if available <= 0:
			QMessageBox.information(
				self,
				"Level Cap Reached",
				f"All {cap} character levels are allocated. Adjust existing entries before adding new ones.",
			)
			return
		dialog = ClassEntryDialog(max_assignable_level=available, parent=self)
		if dialog.exec() == QDialog.DialogCode.Accepted:
			self.class_table.insert_or_replace(dialog.to_progression())

	def _edit_selected_class_entry(self) -> None:
		row = self.class_table.selected_row()
		if row < 0:
			return
		existing = self.class_table.progression_at(row)
		available = self._remaining_level_capacity(row)
		dialog = ClassEntryDialog(existing=existing, max_assignable_level=max(1, available), parent=self)
		if dialog.exec() == QDialog.DialogCode.Accepted:
			self.class_table.insert_or_replace(dialog.to_progression(), row)

	def _remove_selected_class_entry(self) -> None:
		row = self.class_table.selected_row()
		if row < 0:
			return
		self.class_table.remove_row(row)

	def _add_spell_source(self) -> None:
		dialog = SpellSourceDialog(parent=self)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return
		entries = dialog.to_entries()
		if not entries:
			return
		descriptor = dialog.descriptor()
		key = self._register_spell_source_from_descriptor(descriptor)
		self._replace_spells_for_source(key, entries)
		self._persist_spell_sources()
		self._sync_spell_entry_abilities()
		self._rebuild_spell_source_list()
		self._apply_spell_source_filter()

	def _remove_selected_spells(self) -> None:
		self.spell_table.remove_selected_rows()
		self._persist_spell_sources()
		self._rebuild_spell_source_list()
		self._apply_spell_source_filter()
		self._on_known_spells_updated()

	def _remove_selected_spell_source(self) -> None:
		key = (self._active_spell_source_key or "").strip().lower()
		if not key:
			QMessageBox.information(self, "Select a Source", "Please select a spell source to remove.")
			return
		record = self._spell_sources.get(key)
		label = record.label if record else "Spell Source"
		attached_spells = self._spell_entries_for_source(key)
		if attached_spells:
			count = len(attached_spells)
			response = QMessageBox.question(
				self,
				"Remove Spell Source",
				f"{label} still has {count} spell{'s' if count != 1 else ''}. Removing the source will also delete them. Continue?",
			)
			if response != QMessageBox.StandardButton.Yes:
				return
			self.spell_table.remove_entries_for_source(key)
		self._spell_sources.pop(key, None)
		self._persist_spell_sources()
		self._active_spell_source_key = None
		self._rebuild_spell_source_list()
		self._apply_spell_source_filter()
		self._on_known_spells_updated()

	def _bootstrap_spell_sources(self) -> None:
		for record in self._sheet.spellcasting.spell_sources:
			self._register_spell_source(record)
		for entry in self._sheet.spellcasting.known_spells:
			self._ensure_spell_source_from_entry(entry)

	def _persist_spell_sources(self) -> None:
		self._sheet.spellcasting.spell_sources = list(self._spell_sources.values())

	def _register_spell_source_from_descriptor(
		self,
		descriptor: dict,
		existing_key: str | None = None,
	) -> str:
		record = SpellSourceRecord(
			source_type=descriptor.get("source_type", ""),
			source_id=descriptor.get("source_name", ""),
			label=descriptor.get("label", ""),
			ability=descriptor.get("ability"),
		)
		key = self._register_spell_source(record)
		if existing_key and existing_key != key and existing_key in self._spell_sources:
			self._spell_sources.pop(existing_key, None)
		return key

	def _register_spell_source(self, record: SpellSourceRecord) -> str:
		key = build_spell_source_key(record.source_type, record.source_id, record.label)
		if not key:
			return ""
		self._spell_sources[key] = SpellSourceRecord(
			source_type=record.source_type,
			source_id=record.source_id,
			label=record.label,
			ability=record.ability,
		)
		return key

	def _ensure_spell_source_from_entry(self, entry: SpellAccessEntry) -> None:
		key = build_spell_source_key(entry.source_type, entry.source_id, entry.source)
		if key and key not in self._spell_sources:
			self._spell_sources[key] = SpellSourceRecord(
				source_type=entry.source_type or "",
				source_id=entry.source_id or "",
				label=entry.source or entry.source_id or "Spell Source",
				ability=entry.ability,
			)

	def _replace_spells_for_source(self, source_key: str | None, entries: List[SpellAccessEntry]) -> None:
		if source_key:
			self.spell_table.remove_entries_for_source(source_key)
		for entry in entries:
			self.spell_table.append_entry(entry)
		self._on_known_spells_updated()

	def _spell_entries_for_source(self, source_key: str | None) -> List[SpellAccessEntry]:
		return list(self.spell_table.entries_for_source(source_key)) if self.spell_table else []

	def _source_descriptor_for_key(self, source_key: str | None) -> dict:
		record = self._spell_sources.get(source_key or "")
		entries = self._spell_entries_for_source(source_key)
		ability = record.ability if record else None
		category = entries[0].category if entries else ""
		prepared = entries[0].prepared if entries else False
		source_type = (record.source_type if record else (entries[0].source_type if entries else ""))
		source_id = (record.source_id if record else (entries[0].source_id if entries else ""))
		label = (record.label if record else (entries[0].source if entries else ""))
		return {
			"source_type": source_type,
			"source_name": source_id,
			"source_id": source_id,
			"label": label,
			"ability": ability,
			"category": category,
			"prepared": prepared,
			"spells": [entry.spell_name for entry in entries],
		}

	def _on_spell_source_double_clicked(self, item: QListWidgetItem | None) -> None:
		if not item:
			return
		value = item.data(Qt.ItemDataRole.UserRole)
		if not value:
			return
		self._edit_spell_source(str(value))

	def _edit_spell_source(self, source_key: str) -> None:
		descriptor = self._source_descriptor_for_key(source_key)
		initial_spells = descriptor.get("spells", [])
		dialog = SpellSourceDialog(
			parent=self,
			initial_source=descriptor,
			initial_spells=initial_spells,
			title="Edit Spell Source",
		)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return
		entries = dialog.to_entries()
		if not entries:
			return
		new_descriptor = dialog.descriptor()
		new_key = self._register_spell_source_from_descriptor(new_descriptor, existing_key=source_key)
		self._replace_spells_for_source(source_key, entries)
		self._persist_spell_sources()
		self._sync_spell_entry_abilities()
		self._rebuild_spell_source_list()
		self._active_spell_source_key = new_key or self._active_spell_source_key
		self._apply_spell_source_filter()

	def _add_missing_spell_sources(self) -> None:
		missing = 0
		for source in self._baseline_spell_sources():
			key = source.get("key")
			if key and key in self._spell_sources:
				continue
			record = SpellSourceRecord(
				source_type=source.get("source_type", ""),
				source_id=source.get("source_id", ""),
				label=source.get("label", ""),
				ability=source.get("ability"),
			)
			self._register_spell_source(record)
			missing += 1
		if missing == 0:
			QMessageBox.information(self, "Sources Up to Date", "All class-based spell sources are already tracked.")
		else:
			self._persist_spell_sources()
			self._rebuild_spell_source_list()
			self._apply_spell_source_filter()

	def _add_equipment_entry(self) -> None:
		# Use EquipmentWindow for selection
		self._equipment_window = EquipmentWindow(parent=self, selection_mode=True)
		self._equipment_window.items_selected.connect(self._on_items_selected_from_browser)
		self._equipment_window.item_selected.connect(self._on_single_item_selected_legacy) # Fallback
		self._equipment_window.show()

	def _on_single_item_selected_legacy(self, data: Dict[str, object]) -> None:
		# Compatibility wrapper
		self._on_items_selected_from_browser([(data, 1)])

	def _on_items_selected_from_browser(self, items: List[Tuple[Dict[str, object], int]]) -> None:
		for data, qty in items:
			name = str(data.get("name", "New Item"))
			
			weight_val = 0.0
			# Check compendium weight format
			w_raw = data.get("weight", "0")
			if isinstance(w_raw, (int, float)):
				weight_val = float(w_raw)
			elif isinstance(w_raw, str):
				try:
					weight_val = float(w_raw.lower().replace("lb.", "").strip())
				except ValueError:
					pass
			
			entry = EquipmentItem(
				name=name,
				quantity=max(1, qty),
				weight_lb=weight_val,
				attuned=bool(data.get("attunement", False)),
				equipped=False, # Default to not equipped? Or equipped? Default unequipped.
				notes="",
				compendium_id=str(data.get("id", "")),
				cost=str(data.get("cost", "")),
				rarity=str(data.get("rarity", "")),
			)
			self.equipment_table.append_entry(entry)

	def _on_add_custom_item(self) -> None:
		# Opens empty dialog
		dialog = EquipmentEntryDialog(parent=self)
		if dialog.exec() == QDialog.DialogCode.Accepted:
			item = dialog.get_item()
			if item.name:
				self.equipment_table.append_entry(item)

	def _on_edit_equipment_entry(self, item: EquipmentItem) -> None:
		dialog = EquipmentEntryDialog(parent=self, initial_item=item)
		if dialog.exec() != QDialog.DialogCode.Accepted:
			return
		new_item = dialog.get_item()
		if self.equipment_table.upsert_entry(
			new_item,
			slot=dialog.slot_type,
			bonus_type=dialog.bonus_type,
			bonus_value=dialog.bonus_value,
		):
			pass
		else:
			QMessageBox.information(
				self,
				"Equipment Updated",
				f"Updated existing entry for {item.name or 'item'}.",
			)
		self._refresh_level_dependent_fields()

	def _remove_selected_equipment(self) -> None:
		self.equipment_table.remove_selected_rows()
		self._refresh_level_dependent_fields()

	def _format_modifier(self, value: int) -> str:
		return f"{value:+d}"

	def _format_final_with_extra(self, final_value: int, base: int, extra: int) -> str:
		if extra == 0:
			return f"{final_value} (Base {base})"
		return f"{final_value} (Base {base} | Extra {extra:+d})"

	def _equipment_bonus_from_sheet(self, keys: Iterable[str]) -> int:
		key_set = {key.lower() for key in keys}
		total = 0
		for item in self._sheet.equipment:
			for key, value in (item.bonuses or {}).items():
				if str(key).lower() in key_set:
					try:
						total += int(value)
					except (TypeError, ValueError):
						continue
		return total

	def _scheduled_slot_totals(self) -> Dict[int, int]:
		schedule = self._sheet.spellcasting.slot_schedule or {}
		totals = _combine_slot_buckets(
			schedule.get("long_rest", {}),
			schedule.get("short_rest", {}),
		)
		return totals or dict(self._sheet.spellcasting.spell_slots)

	def _read_slot_adjustments(self) -> Dict[int, int]:
		return {}

	def _compute_final_slot_schedule(self, adjustments: Dict[int, int]) -> Dict[str, Dict[int, int]]:
		long_base = dict(self._cached_long_rest_slots)
		short_base = dict(self._cached_short_rest_slots)
		if not (long_base or short_base):
			long_base, short_base = _derived_slot_buckets(self._current_class_progression())

		final_long: Dict[int, int] = {}
		final_short: Dict[int, int] = {}
		for level in range(1, 10):
			base_long = long_base.get(level, 0)
			base_short = short_base.get(level, 0)
			total_base = base_long + base_short
			adjusted_total = max(0, total_base + adjustments.get(level, 0))
			short_value = min(base_short, adjusted_total)
			long_value = max(0, adjusted_total - short_value)
			if long_value:
				final_long[level] = long_value
			if short_value:
				final_short[level] = short_value

		return {"long_rest": final_long, "short_rest": final_short}

	# --- Accept / Result -------------------------------------------------
	def _accept(self) -> None:
		if not self._validate_before_accept():
			return
		self._apply_core_stats()
		self._apply_feats()
		self._apply_spells()
		self._apply_equipment()
		self._apply_modifiers()
		self.accept()

	def _apply_core_stats(self) -> None:
		self._sheet.identity.name = self.name_edit.text().strip()
		self._sheet.identity.background = self._current_background_name().strip()
		selection = self._stored_background_selection()
		selection.ability_choices = self._gather_background_ability_choices()
		selection.language_choices = self._gather_background_language_choices()
		selection.tool_choices = self._gather_background_tool_choices()
		selection.feat_choice = self._gather_background_feat_choice()
		self._sheet.identity.background_choices = selection
		classes = self._current_class_progression()
		self._sheet.identity.classes = classes
		total_level = self._sum_class_levels(classes)
		self._sheet.identity.level_cap = min(total_level, self._max_character_level)
		self._sheet.identity.ability_generation = self._current_ability_generation_mode()
		self._sheet.identity.asi_choices = self._gather_asi_choices()

		self._sheet.proficiencies.proficiency_bonus = self._cached_proficiency_base

		if self.ability_group:
			for ability, value in self.ability_group.scores().items():
				block = self._sheet.get_ability(ability)
				block.score = value
				block.modifier = None

		derived_ability = (self._derived_spell_ability or self._sheet.spellcasting.spellcasting_ability or "INT").upper()
		self._sheet.spellcasting.spellcasting_ability = derived_ability
		self._sheet.spellcasting.attack_bonus = self._cached_attack_base
		self._sheet.spellcasting.save_dc = self._cached_save_base

		slot_schedule = self._compute_final_slot_schedule({})
		self._sheet.spellcasting.slot_schedule = slot_schedule
		self._sheet.spellcasting.slot_state = {
			"long_rest": dict(slot_schedule.get("long_rest", {})),
			"short_rest": dict(slot_schedule.get("short_rest", {})),
		}
		self._sheet.spellcasting.sync_slot_schedule()

		# Derived max HP; current HP remains user-editable state.
		max_hp_bonus = 0
		if self._cached_bonus_bundle is not None:
			max_hp_bonus = int(self._cached_bonus_bundle.get("max_hp"))
		self._refresh_hit_points(classes, max_hp_bonus=max_hp_bonus)

		if self.class_features_group:
			self._feature_selections.update(self.class_features_group.current_selections())
		if self._rule_snapshot:
			active_keys = {group.key for group in self._rule_snapshot.option_groups}
			filtered_options = {key: value for key, value in self._feature_selections.items() if key in active_keys}
		else:
			filtered_options = dict(self._feature_selections)
		self._sheet.feature_options = filtered_options
		if self.class_options_group:
			self._class_option_selections.update(self.class_options_group.current_selections())
		if self._class_option_snapshot:
			active_option_keys = {group.key for group in self._class_option_snapshot.groups}
			filtered_class_options = {
				key: [value for value in values if value]
				for key, values in self._class_option_selections.items()
				if key in active_option_keys and values
			}
		else:
			filtered_class_options = {
				key: [value for value in values if value]
				for key, values in self._class_option_selections.items()
				if values
			}
		self._sheet.class_options = filtered_class_options

	def _apply_spells(self) -> None:
		entries = list(self.spell_table.iter_entries())
		prepared = [entry.spell_name for entry in entries if entry.prepared and entry.spell_name]
		self._sheet.spellcasting.known_spells = entries
		self._sheet.spellcasting.prepared_spells = prepared

	def _apply_feats(self) -> None:
		self._sheet.features = self._current_feature_entries()

	def _apply_equipment(self) -> None:
		self._sheet.equipment = self._current_equipment_entries()

	def _apply_modifiers(self) -> None:
		if self.modifiers_group:
			self._modifier_states = self.modifiers_group.states()

	def get_result(self) -> Tuple[CharacterSheet, Dict[str, bool]]:
		return copy.deepcopy(self._sheet), dict(self._modifier_states)

__all__ = ["SpellcastingSettingsDialog"]
