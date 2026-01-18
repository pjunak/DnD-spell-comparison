from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QGroupBox, QSizePolicy, QHBoxLayout
)

from modules.dnd24_mechanics.character_rules import FeatureOptionGroup

class FeatureSelector(QWidget):
    """
    Renders a selection control for a FeatureOptionGroup.
    """
    selectionChanged = Signal(str, str) # group_key, value

    def __init__(
        self,
        group: FeatureOptionGroup,
        current_selection: str | None = None,
        exclude_values: list | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.group = group
        self._exclude_values = set(exclude_values or [])
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        
        # Label
        self.label = QLabel(group.label)
        self.label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.label)
        
        if group.description:
            desc = QLabel(group.description)
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #888; font-size: 0.9em;")
            layout.addWidget(desc)
            
        # ComboBox
        self.combo = QComboBox()
        if group.width:
            self.combo.setFixedWidth(group.width)
        else:
            self.combo.setMinimumWidth(150)
            
        # Add "Clear" or "Select" option if not required?
        if not group.required:
            self.combo.addItem("(None)", "")
            
        index_to_select = 0
        actual_index = 0
        for i, choice in enumerate(group.choices):
            # Add item
            self.combo.addItem(choice.label, choice.value)
            
            # Use QStandardItemModel to disable items if not enabled
            if not choice.enabled:
                 idx = self.combo.count() - 1
                 # Disable item
                 self.combo.model().item(idx).setEnabled(False)
                 
                 # Set Color (Gray)
                 from PySide6.QtCore import Qt
                 from PySide6.QtGui import QColor, QBrush
                 # Using standard palette color or fixed gray
                 self.combo.setItemData(idx, QBrush(QColor("gray")), Qt.ForegroundRole)
            
            # Check selection
            if current_selection and choice.value == current_selection:
                # offset by 1 if we added (None)
                if not group.required:
                    index_to_select = actual_index + 1
                else:
                    index_to_select = actual_index
            actual_index += 1
                    
        self.combo.setCurrentIndex(index_to_select)
        self.combo.currentIndexChanged.connect(self._on_changed)
        
        # Limit width: use minimum size hint + padding, don't expand
        self.combo.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.combo.setMaximumWidth(350)
        
        # Wrap in horizontal layout to prevent full-width spanning
        combo_row = QHBoxLayout()
        combo_row.setContentsMargins(0, 0, 0, 0)
        combo_row.addWidget(self.combo)
        combo_row.addStretch()
        layout.addLayout(combo_row)
        
    def _on_changed(self, index: int):
        val = self.combo.itemData(index)
        self.selectionChanged.emit(self.group.key, str(val))
