"""
Ability Score Improvement Dialog - Choose how to allocate ASI points.
D&D 2024: +2 to one ability OR +1 to two different abilities.
"""

from __future__ import annotations

from typing import Optional, Dict, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QWidget, QRadioButton, QButtonGroup, QComboBox, QGroupBox
)
from PySide6.QtCore import Qt

from modules.character_sheet.model import ABILITY_NAMES


class ASISelectionDialog(QDialog):
    def __init__(
        self, 
        parent: QWidget | None = None, 
        current_selection: str = "",
        current_scores: Dict[str, int] | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ability Score Improvement")
        self.resize(400, 300)
        
        self._current_scores = current_scores or {}
        self._selection: Optional[str] = None
        
        self._layout_ui()
        
        # Parse existing selection if any
        if current_selection and current_selection != "_ASI_":
            self._parse_selection(current_selection)
    
    def _layout_ui(self):
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Choose how to improve your ability scores:\n"
            "• +2 to one ability score\n"
            "• +1 to two different ability scores"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Mode Selection
        mode_group = QGroupBox("Improvement Type")
        mode_layout = QVBoxLayout(mode_group)
        
        self._mode_group = QButtonGroup(self)
        
        self._radio_plus2 = QRadioButton("+2 to one ability")
        self._radio_plus1x2 = QRadioButton("+1 to two abilities")
        self._radio_plus2.setChecked(True)
        
        self._mode_group.addButton(self._radio_plus2, 0)
        self._mode_group.addButton(self._radio_plus1x2, 1)
        
        self._radio_plus2.toggled.connect(self._on_mode_changed)
        
        mode_layout.addWidget(self._radio_plus2)
        mode_layout.addWidget(self._radio_plus1x2)
        layout.addWidget(mode_group)
        
        # Ability Selection
        selection_group = QGroupBox("Select Abilities")
        selection_layout = QVBoxLayout(selection_group)
        
        # +2 ability
        plus2_row = QHBoxLayout()
        plus2_row.addWidget(QLabel("+2 to:"))
        self._combo_plus2 = QComboBox()
        for ability in ABILITY_NAMES:
            score = self._current_scores.get(ability, 10)
            self._combo_plus2.addItem(f"{ability} ({score})", ability)
        plus2_row.addWidget(self._combo_plus2)
        plus2_row.addStretch()
        selection_layout.addLayout(plus2_row)
        
        # +1 abilities (hidden initially)
        self._plus1_widget = QWidget()
        plus1_layout = QVBoxLayout(self._plus1_widget)
        plus1_layout.setContentsMargins(0, 0, 0, 0)
        
        plus1_row1 = QHBoxLayout()
        plus1_row1.addWidget(QLabel("+1 to:"))
        self._combo_plus1_a = QComboBox()
        for ability in ABILITY_NAMES:
            score = self._current_scores.get(ability, 10)
            self._combo_plus1_a.addItem(f"{ability} ({score})", ability)
        plus1_row1.addWidget(self._combo_plus1_a)
        plus1_row1.addStretch()
        plus1_layout.addLayout(plus1_row1)
        
        plus1_row2 = QHBoxLayout()
        plus1_row2.addWidget(QLabel("+1 to:"))
        self._combo_plus1_b = QComboBox()
        for ability in ABILITY_NAMES:
            score = self._current_scores.get(ability, 10)
            self._combo_plus1_b.addItem(f"{ability} ({score})", ability)
        self._combo_plus1_b.setCurrentIndex(1)  # Default to different ability
        plus1_row2.addWidget(self._combo_plus1_b)
        plus1_row2.addStretch()
        plus1_layout.addLayout(plus1_row2)
        
        self._plus1_widget.hide()  # Hidden by default
        selection_layout.addWidget(self._plus1_widget)
        
        layout.addWidget(selection_group)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_apply = QPushButton("Apply")
        btn_apply.clicked.connect(self._on_apply)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_apply)
        layout.addLayout(btn_layout)
    
    def _on_mode_changed(self, checked: bool):
        if self._radio_plus2.isChecked():
            self._combo_plus2.setVisible(True)
            self._plus1_widget.hide()
        else:
            self._combo_plus2.setVisible(False)
            self._plus1_widget.show()
    
    def _parse_selection(self, selection: str):
        """Parse existing selection like 'ASI:STR+2' or 'ASI:DEX+1,WIS+1'."""
        if not selection.startswith("ASI:"):
            return
        parts = selection[4:].split(",")
        if len(parts) == 1 and "+2" in parts[0]:
            # +2 mode
            ability = parts[0].replace("+2", "")
            idx = self._combo_plus2.findData(ability)
            if idx >= 0:
                self._combo_plus2.setCurrentIndex(idx)
        elif len(parts) == 2:
            # +1+1 mode
            self._radio_plus1x2.setChecked(True)
            for i, part in enumerate(parts):
                ability = part.replace("+1", "")
                combo = self._combo_plus1_a if i == 0 else self._combo_plus1_b
                idx = combo.findData(ability)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
    
    def _on_apply(self):
        if self._radio_plus2.isChecked():
            ability = self._combo_plus2.currentData()
            self._selection = f"ASI:{ability}+2"
        else:
            ability_a = self._combo_plus1_a.currentData()
            ability_b = self._combo_plus1_b.currentData()
            if ability_a == ability_b:
                # Same ability selected - warn or just accept
                pass
            self._selection = f"ASI:{ability_a}+1,{ability_b}+1"
        self.accept()
    
    def get_selection(self) -> Optional[str]:
        return self._selection
