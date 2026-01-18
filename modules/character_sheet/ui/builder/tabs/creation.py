from __future__ import annotations

from typing import Dict, List, Mapping, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox, 
    QGroupBox, QPushButton, QLabel, QScrollArea, QFrame, QToolButton, QFileDialog
)
from PySide6.QtGui import QPixmap
from pathlib import Path
import shutil

from modules.character_sheet.model import CharacterSheet, ABILITY_NAMES
from modules.compendium.modifiers.state import ModifierStateSnapshot
from modules.compendium.service import Compendium
from modules.character_sheet.services.library import DEFAULT_LIBRARY_PATH
from modules.core.ui.widgets.ability_scores_group import AbilityScoresGroup
from modules.dnd24_mechanics.rules_config import point_buy_rules

class CreationTab(QWidget):
    """
    Handles Character Creation decisions:
    - Identity (Name, Portrait)
    - Species & Subtype
    - Class (Level 1) & Subclass (if Lvl 1)
    - Background (Origin)
    - Ability Scores
    """
    dataChanged = Signal()

    def __init__(
        self,
        sheet: CharacterSheet,
        modifier_snapshot: ModifierStateSnapshot,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._sheet = sheet
        self._modifier_snapshot = modifier_snapshot
        self._compendium = Compendium.load()
        
        # UI State
        self._portrait_label: QLabel | None = None
        self._species_combo: QComboBox | None = None
        self._subtype_combo: QComboBox | None = None
        self._background_combo: QComboBox | None = None
        self.ability_group: AbilityScoresGroup | None = None
        
        self._layout_ui()
        self._load_data()

    def _layout_ui(self):
        layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self.form_layout = QVBoxLayout(content)
        self.form_layout.setSpacing(20)
        
        # 1. Identity Group
        self.form_layout.addWidget(self._build_identity_section())
        
        # 2. Race & Class Group
        self.form_layout.addWidget(self._build_origin_section())
        
        # 3. Background Group
        self.form_layout.addWidget(self._build_background_section())
        
        # 4. Ability Scores Group
        self.form_layout.addWidget(self._build_ability_scores_section())
        
        self.form_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _build_identity_section(self) -> QWidget:
        group = QGroupBox("Identity")
        layout = QHBoxLayout(group)
        
        # Portrait
        portrait_layout = QVBoxLayout()
        self._portrait_label = QLabel()
        self._portrait_label.setFixedSize(100, 100)
        self._portrait_label.setStyleSheet("background-color: #2d2d30; border: 1px solid #3e3e42; border-radius: 4px;")
        self._portrait_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn = QPushButton("Select Portrait...")
        btn.clicked.connect(self._on_select_portrait)
        
        portrait_layout.addWidget(self._portrait_label)
        portrait_layout.addWidget(btn)
        layout.addLayout(portrait_layout)
        
        # Name
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Character Name")
        self.name_edit.textChanged.connect(self._on_name_changed)
        form.addRow("Name:", self.name_edit)
        
        layout.addLayout(form, 1)
        return group

    def _build_origin_section(self) -> QWidget:
        group = QGroupBox("Ancestry")
        form = QFormLayout(group)
        
        # Species
        self._species_combo = QComboBox()
        self._species_combo.addItem("(Select Species)", "")
        self._species_combo.currentIndexChanged.connect(self._on_species_changed)
        form.addRow("Species:", self._species_combo)
        
        self._subtype_combo = QComboBox()
        self._subtype_combo.setEnabled(False)
        self._subtype_combo.currentIndexChanged.connect(self._on_subtype_changed)
        form.addRow("Subtype:", self._subtype_combo)
        
        return group

    def _build_background_section(self) -> QWidget:
        group = QGroupBox("Background")
        form = QFormLayout(group)
        
        self._background_combo = QComboBox()
        self._background_combo.addItem("(Select Background)", "")
        self._background_combo.currentIndexChanged.connect(self._on_background_changed)
        form.addRow("Origins:", self._background_combo)
        
        # TODO: Add Origin Feat / Proficiency selection based on background
        
        return group

    def _build_ability_scores_section(self) -> QWidget:
        group = QGroupBox("Ability Scores")
        layout = QVBoxLayout(group)
        
        # 1. Method Selection
        self._point_buy_rules = point_buy_rules()
        self._gen_method_combo = QComboBox()
        self._gen_method_combo.addItem("Manual Entry", "manual")
        
        if self._point_buy_rules:
            self._gen_method_combo.addItem("Point Buy", "point_buy")
            
        self._gen_method_combo.currentIndexChanged.connect(self._on_gen_method_changed)
        
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Generation Method:"))
        method_layout.addWidget(self._gen_method_combo)
        method_layout.addStretch()
        layout.addLayout(method_layout)
        
        # 2. Point Buy Summary (Hidden by default)
        self._pb_summary_label = QLabel()
        self._pb_summary_label.setStyleSheet("font-weight: bold; color: #4ec9b0;")
        self._pb_summary_label.hide()
        layout.addWidget(self._pb_summary_label)
        
        # 3. Scores Group
        initial_scores = {abil: self._sheet.get_ability(abil).score for abil in ABILITY_NAMES}
        initial_modifiers = {abil: self._sheet.get_ability(abil).effective_modifier() for abil in ABILITY_NAMES}
        
        self.ability_group = AbilityScoresGroup(
            ability_names=ABILITY_NAMES,
            initial_scores=initial_scores,
            initial_modifiers=initial_modifiers,
            modifier_formatter=lambda m: f"{m:+d}"
        )
        self.ability_group.score_changed.connect(self._on_score_changed)
        
        layout.addWidget(self.ability_group)
        return group

    def _on_gen_method_changed(self):
        method = self._gen_method_combo.currentData()
        self._sheet.identity.ability_generation = method or "manual"
        
        if method == "point_buy" and self._point_buy_rules:
            self._pb_summary_label.show()
            # Enforce bounds
            self.ability_group.set_score_bounds(
                self._point_buy_rules.min_score,
                self._point_buy_rules.max_score
            )
            self._recalc_point_buy()
        else:
            self._pb_summary_label.hide()
            # Relax bounds
            self.ability_group.set_score_bounds(1, 30)

    def _recalc_point_buy(self):
        if not self._point_buy_rules:
            return
            
        total_cost = 0
        valid = True
        
        # We need current raw scores from the widget
        current_scores = self.ability_group.scores()
        
        for score in current_scores.values():
            cost = self._point_buy_rules.costs.get(score)
            if cost is None:
                valid = False # Score out of cost table (should be prevented by bounds, but check anyway)
                continue
            total_cost += cost
            
        remaining = self._point_buy_rules.pool - total_cost
        
        if not valid:
             self._pb_summary_label.setText("Invalid score detected for Point Buy.")
             self._pb_summary_label.setStyleSheet("color: #d95c5c;")
             return
             
        self._pb_summary_label.setText(f"Points Remaining: {remaining} / {self._point_buy_rules.pool}")
        if remaining < 0:
            self._pb_summary_label.setStyleSheet("color: #d95c5c; font-weight: bold;")
        else:
            self._pb_summary_label.setStyleSheet("color: #4ec9b0; font-weight: bold;")



    def _load_data(self):
        # Identity
        self.name_edit.setText(self._sheet.identity.name)
        self._refresh_portrait_preview()
        
        # Species
        species_records = [r for r in self._compendium.records("species") if isinstance(r, Mapping)]
        sorted_species = sorted(species_records, key=lambda x: str(x.get("name", "")))
        for r in sorted_species:
            self._species_combo.addItem(str(r.get("name")), r)
            
        current_species = self._sheet.identity.ancestry
        if current_species:
            self._species_combo.setCurrentText(current_species)
            # Also restore subtype if it was saved
            current_subtype = self._sheet.identity.ancestry_subtype
            if current_subtype:
                # Trick: Species change will populate subtypes, then we set the text
                # Need to do this AFTER species is set so subtypes are populated
                pass  # Will be handled in _on_species_changed
            
        # Backgrounds
        backgrounds = sorted([r for r in self._compendium.records("backgrounds") if isinstance(r, Mapping)], key=lambda x: str(x.get("name", "")))
        for b in backgrounds:
            self._background_combo.addItem(str(b.get("name")), b)
            
        current_bg = self._sheet.identity.background
        if current_bg:
            self._background_combo.setCurrentText(current_bg)
        
        # Restore Ability Generation Method
        saved_method = self._sheet.identity.ability_generation
        if saved_method:
            idx = self._gen_method_combo.findData(saved_method)
            if idx >= 0:
                self._gen_method_combo.setCurrentIndex(idx)
                self._on_gen_method_changed()  # Trigger UI update

    def _refresh_portrait_preview(self):
        path_str = self._sheet.identity.portrait_path
        if path_str:
            if Path(path_str).is_absolute():
                p_path = Path(path_str)
            else:
                p_path = DEFAULT_LIBRARY_PATH / "portraits" / path_str
            
            if p_path.exists():
                pix = QPixmap(str(p_path))
                self._portrait_label.setPixmap(pix.scaled(self._portrait_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                return
        self._portrait_label.setText("No Image")

    def _on_select_portrait(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Portrait", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not file_path:
            return
            
        src = Path(file_path)
        dest_dir = DEFAULT_LIBRARY_PATH / "portraits"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_name = f"{self._sheet.identity.name or 'char'}_{src.name}".replace(" ", "_")
        dest = dest_dir / dest_name
        
        try:
            shutil.copy2(src, dest)
            self._sheet.identity.portrait_path = dest_name
            self._refresh_portrait_preview()
            self.dataChanged.emit()
        except Exception:
            pass

    def _on_name_changed(self, text: str):
        self._sheet.identity.name = text
        self.dataChanged.emit()

    def _on_species_changed(self):
        data = self._species_combo.currentData()
        if not isinstance(data, dict):
            return
        
        name = str(data.get("name", ""))
        self._sheet.identity.ancestry = name
        
        # Store saved subtype before clearing
        saved_subtype = self._sheet.identity.ancestry_subtype
        
        # Block signals to prevent _on_subtype_changed from firing during population
        self._subtype_combo.blockSignals(True)
        
        # Update subtypes
        self._subtype_combo.clear()
        self._subtype_combo.addItem("(None)", "")
        subtypes = data.get("subtypes", [])
        if subtypes and isinstance(subtypes, list):
            self._subtype_combo.setEnabled(True)
            for s in subtypes:
                if isinstance(s, dict):
                    self._subtype_combo.addItem(str(s.get("name")), s)
            # Restore saved subtype if it exists
            if saved_subtype:
                idx = self._subtype_combo.findText(saved_subtype)
                if idx >= 0:
                    self._subtype_combo.setCurrentIndex(idx)
        else:
            self._subtype_combo.setEnabled(False)
        
        # Restore signals
        self._subtype_combo.blockSignals(False)
            
        self.dataChanged.emit()

    def _on_subtype_changed(self):
        data = self._subtype_combo.currentData()
        name = ""
        if isinstance(data, dict):
            name = str(data.get("name", ""))
        elif isinstance(data, str):
            name = data
        self._sheet.identity.ancestry_subtype = name
        self.dataChanged.emit()


    def _on_background_changed(self):
        data = self._background_combo.currentData()
        if not isinstance(data, dict):
            return
        
        name = str(data.get("name", ""))
        self._sheet.identity.background = name
        self.dataChanged.emit()
        
    def _on_score_changed(self, ability: str, value: int):
        self._sheet.get_ability(ability).score = value
        if self._gen_method_combo and self._gen_method_combo.currentData() == "point_buy":
            self._recalc_point_buy()
        self.dataChanged.emit()
