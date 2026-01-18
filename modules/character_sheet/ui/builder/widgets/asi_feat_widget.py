"""
ASI/Feat Choice Widget - Two buttons for choosing between ASI and Feat.
"""

from __future__ import annotations

from typing import Optional, Dict
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel
)
from PySide6.QtCore import Signal

from modules.character_sheet.ui.builder.dialogs.feat_selection import FeatSelectionDialog
from modules.character_sheet.ui.builder.dialogs.asi_selection import ASISelectionDialog


class ASIFeatWidget(QWidget):
    """
    Widget with two buttons:
    - Choose Feat: Opens FeatSelectionDialog
    - Ability Score Improvement: Opens ASISelectionDialog
    
    Emits choiceChanged(key, value) when a selection is made.
    Emits featSelected(feat_name) when a feat is selected (for showing inline options).
    """
    
    choiceChanged = Signal(str, str)  # group_key, value
    featSelected = Signal(str)  # feat_name (so parent can show inline options)
    
    def __init__(
        self, 
        group_key: str,
        level: int,
        current_selection: str = "",
        current_scores: Dict[str, int] | None = None,
        character_level: int = 1,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        
        self._group_key = group_key
        self._level = level
        self._current_selection = current_selection
        self._current_scores = current_scores or {}
        self._character_level = character_level
        
        self._layout_ui()
        self._update_display()
    
    def _layout_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 8)
        
        # Set minimum height to prevent layout shifts when selection changes
        self.setMinimumHeight(90)
        
        # Header
        header = QLabel(f"Level {self._level}: Ability Score Improvement or Feat")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)
        
        # Current selection display
        self._selection_label = QLabel("")
        self._selection_label.setStyleSheet("color: #4ec9b0; font-style: italic;")
        layout.addWidget(self._selection_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self._btn_asi = QPushButton("Ability Score Improvement")
        self._btn_asi.clicked.connect(self._on_asi_clicked)
        btn_layout.addWidget(self._btn_asi)
        
        self._btn_feat = QPushButton("Choose Feat")
        self._btn_feat.clicked.connect(self._on_feat_clicked)
        btn_layout.addWidget(self._btn_feat)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def _update_display(self):
        if not self._current_selection:
            self._selection_label.setText("No selection made")
        elif self._current_selection.startswith("ASI:"):
            self._selection_label.setText(f"Selected: {self._current_selection}")
        else:
            self._selection_label.setText(f"Selected Feat: {self._current_selection}")
    
    def _on_asi_clicked(self):
        dialog = ASISelectionDialog(
            parent=self,
            current_selection=self._current_selection if self._current_selection.startswith("ASI:") else "",
            current_scores=self._current_scores
        )
        if dialog.exec():
            selection = dialog.get_selection()
            if selection:
                self._current_selection = selection
                self._update_display()
                self.choiceChanged.emit(self._group_key, selection)
    
    def _on_feat_clicked(self):
        current_feat = self._current_selection if not self._current_selection.startswith("ASI:") else ""
        dialog = FeatSelectionDialog(
            parent=self, 
            current_selection=current_feat,
            character_level=self._character_level
        )
        if dialog.exec():
            selection = dialog.get_selected_feat()
            if selection:
                self._current_selection = selection
                self._update_display()
                self.choiceChanged.emit(self._group_key, selection)
                self.featSelected.emit(selection)
    
    def set_selection(self, value: str):
        self._current_selection = value
        self._update_display()
