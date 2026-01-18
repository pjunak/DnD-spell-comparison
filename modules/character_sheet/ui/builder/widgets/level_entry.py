from __future__ import annotations

from typing import List, Optional, Callable
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QToolButton, QComboBox, QPushButton
)

class LevelEntry(QWidget):
    """
    Represents a single level step in the builder (e.g. "Wizard Level 3").
    Contains:
    - Automatically granted features (read-only).
    - Choice widgets (Subclass, ASI, Options).
    """
    
    # Signals for when choices are made (group_key, value)
    choiceChanged = Signal(str, str)
    # Signal when remove button is clicked
    removeClicked = Signal(int)  # level number
    
    def __init__(
        self, 
        level: int, 
        class_name: str, 
        features: List[dict],
        parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.level = level
        self.class_name = class_name
        self.features = features
        
        # Main container with border
        self.setObjectName("LevelEntryContainer")
        self.setStyleSheet("""
            #LevelEntryContainer {
                border: 1px solid #555;
                border-radius: 6px;
                background-color: rgba(40, 40, 45, 0.8);
                margin: 4px 0;
            }
        """)
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 8)
        
        # Header with remove button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self._header = QToolButton()
        self._header.setText(f"Level {level}: {class_name}")
        self._header.setCheckable(True)
        self._header.setChecked(True) # Expanded by default
        self._header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._header.setArrowType(Qt.ArrowType.DownArrow)
        self._header.setStyleSheet("font-weight: bold; background: none; border: none; text-align: left;")
        self._header.toggled.connect(self._toggle_body)
        header_layout.addWidget(self._header)
        
        header_layout.addStretch()
        
        # Remove button
        self._remove_btn = QPushButton("✕")
        self._remove_btn.setFixedSize(24, 24)
        self._remove_btn.setToolTip(f"Remove Level {level}")
        self._remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #666;
                border-radius: 4px;
                color: #888;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e74c3c;
                color: white;
                border-color: #e74c3c;
            }
        """)
        self._remove_btn.clicked.connect(lambda: self.removeClicked.emit(self.level))
        header_layout.addWidget(self._remove_btn)
        
        self._layout.addWidget(header_widget)
        
        # Body
        self._body = QFrame()
        self._body.setObjectName("LevelEntryBody")
        self._body.setStyleSheet("#LevelEntryBody { border-left: 2px solid #444; margin-left: 10px; padding-left: 10px; }")
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 4, 0, 8)
        self._layout.addWidget(self._body)
        
        # Dynamic options container (for feat-specific choices)
        self._dynamic_options_container = QVBoxLayout()
        self._body_layout.addLayout(self._dynamic_options_container)
        
        self._populate_features()
        
    def _toggle_body(self, checked: bool):
        self._body.setVisible(checked)
        self._header.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        
    def _populate_features(self):
        # 1. Static Features
        for feat in self.features:
            name = feat.get("name", "Unknown Feature")
            desc = feat.get("description", "")
            
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0,0,0,0)
            
            lbl = QLabel(f"• {name}")
            lbl.setStyleSheet("font-weight: 500;")
            h.addWidget(lbl)
            
            # If complex description, maybe tooltip or expander?
            # For now, simplistic
            
            self._body_layout.addWidget(row)
            
    def set_options(self, options: List['FeatureOptionGroup'], current_selections: Dict[str, str]):
        """Populate choice widgets for this level."""
        from modules.character_sheet.ui.builder.widgets.feature_selector import FeatureSelector
        
        # Compute exclude values for proficiency-type groups (skill_1, skill_2, etc.)
        # Group keys that share a pattern should exclude each other's selections
        def get_group_base(key: str) -> str:
            # Extract base pattern: "wizard_skill_1" -> "wizard_skill"
            parts = key.rsplit("_", 1)
            if len(parts) == 2 and parts[1].isdigit():
                return parts[0]
            return ""
        
        # Build exclude map: base_pattern -> list of selected values from sibling groups
        exclude_map: Dict[str, List[str]] = {}
        for group in options:
            base = get_group_base(group.key)
            if base:
                if base not in exclude_map:
                    exclude_map[base] = []
                # Add all sibling selections
                for g2 in options:
                    if get_group_base(g2.key) == base and g2.key != group.key:
                        val = current_selections.get(g2.key, "")
                        if val:
                            exclude_map[base].append(val)
        
        for group in options:
            current = current_selections.get(group.key)
            base = get_group_base(group.key)
            exclude_values = exclude_map.get(base, []) if base else []
            
            selector = FeatureSelector(group, current, exclude_values=exclude_values, parent=self)
            selector.selectionChanged.connect(self.choiceChanged.emit)
            self._body_layout.addWidget(selector)
            
    def add_choice_widget(self, widget: QWidget):
        """External caller adds choice widgets (Subclass selector, etc) here."""
        self._body_layout.addWidget(widget)
    
    def clear_dynamic_options(self):
        """Remove all dynamic option widgets."""
        while self._dynamic_options_container.count():
            item = self._dynamic_options_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def add_dynamic_option(self, label: str, options: List[any], current: str, key: str, exclude: List[str] = None, width: int = None):
        """
        Add a dynamic dropdown for feat-specific options (attribute choice, skill, etc).
        
        Args:
            label: Display label (e.g., "Choose Attribute")
            options: List of available choices (strings or FeatureOptionChoice objects)
            current: Currently selected value
            key: Unique key for this option
            exclude: Values to exclude from options
            width: Optional fixed width for the combobox
        """
        from PySide6.QtWidgets import QComboBox
        
        if exclude is None:
            exclude = []
        
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(20, 4, 0, 4)  # Indented to show it's a sub-option
        
        lbl = QLabel(f"  ↳ {label}:")
        lbl.setStyleSheet("color: #888; font-style: italic;")
        h.addWidget(lbl)
        
        combo = QComboBox()
        if width:
            combo.setFixedWidth(width)
        else:
            combo.setMinimumWidth(150)
        combo.addItem("(Select...)", "")
        
        for opt in options:
            if hasattr(opt, 'label') and hasattr(opt, 'value'):
                val = opt.value
                txt = opt.label
                enabled = getattr(opt, 'enabled', True)
            else:
                val = str(opt)
                txt = str(opt)
                enabled = True
                
            if val in exclude and val != current:
                continue
                
            combo.addItem(txt, val)
            
            # handle disabled state
            if not enabled:
                idx = combo.count() - 1
                combo.model().item(idx).setEnabled(False)
                
                # Set Color (Gray)
                from PySide6.QtCore import Qt
                from PySide6.QtGui import QColor, QBrush
                combo.setItemData(idx, QBrush(QColor("gray")), Qt.ForegroundRole)
            
            if val == current:
                combo.setCurrentIndex(combo.count() - 1)
        
        combo.currentTextChanged.connect(
            lambda text: self.choiceChanged.emit(key, combo.currentData())
        )
        
        self.add_choice_widget(row)
        self._dynamic_options_container.addWidget(row)
