from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, 
    QPushButton, QHBoxLayout, QMessageBox, QGroupBox, QWidget
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QBrush

from modules.character_sheet.model import CharacterSheet
from modules.compendium.service import Compendium
from modules.dnd24_mechanics.character_rules.service import CharacterRulesService

class ClassSelectionDialog(QDialog):
    def __init__(self, sheet: CharacterSheet, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Class Level")
        self.resize(400, 500)
        
        self._sheet = sheet
        self._compendium = Compendium.load()
        self._rules_service = CharacterRulesService()
        self._selected_class: Optional[str] = None
        
        self._layout_ui()
        self._populate_classes()
        
    def _layout_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        lbl = QLabel("Select a class to gain a level in.\nYou must meet the Ability Score prerequisites for both your current classes\nand the new class if you are multiclassing.")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(32, 32))
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)
        
        # Info Area
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #d95c5c; font-style: italic;")
        layout.addWidget(self.info_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_select = QPushButton("Add Level")
        self.btn_select.setEnabled(False)
        self.btn_select.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_select)
        layout.addLayout(btn_layout)

    def _populate_classes(self):
        # 1. Existing Classes
        existing_names = {c.name.lower(): c for c in self._sheet.identity.classes}
        
        # 2. All Classes from Compendium
        all_classes_raw = self._compendium.records("classes")
        # Deduplicate and sort
        all_classes = sorted(
            [c for c in all_classes_raw if isinstance(c, dict)], 
            key=lambda x: str(x.get("name", ""))
        )
        
        for record in all_classes:
            name = str(record.get("name", ""))
            if not name: continue
            
            existing = existing_names.get(name.lower())
            
            # Check validation
            failures = self._rules_service.validate_multiclass_requirements(self._sheet, name)
            is_valid = len(failures) == 0
            
            display_text = name
            if existing:
                display_text += f" (Current Level: {existing.level})"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setData(Qt.ItemDataRole.UserRole + 1, is_valid)
            item.setData(Qt.ItemDataRole.UserRole + 2, failures)
            
            if not is_valid:
                item.setForeground(QBrush(QColor("#808080"))) # Grey out
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable) # Make unselectable? Or selectable but show error?
                # Let's make it selectable to show WHY it's invalid
            else:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                
            self.list_widget.addItem(item)

    def _on_selection_changed(self):
        items = self.list_widget.selectedItems()
        if not items:
            self._selected_class = None
            self.btn_select.setEnabled(False)
            self.info_label.setText("")
            return
            
        item = items[0]
        name = item.data(Qt.ItemDataRole.UserRole)
        is_valid = item.data(Qt.ItemDataRole.UserRole + 1)
        failures = item.data(Qt.ItemDataRole.UserRole + 2)
        
        if is_valid:
            self._selected_class = name
            self.btn_select.setEnabled(True)
            self.info_label.setText("")
        else:
            self._selected_class = None
            self.btn_select.setEnabled(False)
            reason = "\n".join(failures)
            self.info_label.setText(f"Prerequisities not met:\n{reason}")

    def get_selected_class(self) -> Optional[str]:
        return self._selected_class
