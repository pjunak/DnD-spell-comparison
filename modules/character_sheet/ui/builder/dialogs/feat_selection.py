"""
Feat Selection Dialog - Searchable list of feats from the Compendium.
"""

from __future__ import annotations

import re
from typing import Optional, List, Dict, Any, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QListWidget, QListWidgetItem, QPushButton, QTextBrowser, QSplitter, QWidget
)
from PySide6.QtCore import Qt

from modules.compendium.service import Compendium
from modules.core.ui.utils.compendium_formatting import convert_to_html_doc


def _parse_prerequisite_from_text(text: str) -> Tuple[str, int]:
    """
    Parse prerequisite from markdown text like '*Prerequisite: Level 19+*' or 
    '*Prerequisite: Level 4+, Charisma 13+*'.
    Returns (prerequisite_string, min_level) where min_level is 0 if not found.
    """
    # Look for *Prerequisite: ...* pattern
    match = re.search(r'\*Prerequisite:\s*([^*]+)\*', text, re.IGNORECASE)
    if not match:
        return "", 0
    
    prereq_str = match.group(1).strip()
    
    # Extract level requirement (e.g., "Level 19+" -> 19)
    level_match = re.search(r'Level\s*(\d+)\+?', prereq_str, re.IGNORECASE)
    min_level = int(level_match.group(1)) if level_match else 0
    
    return prereq_str, min_level


class FeatSelectionDialog(QDialog):
    def __init__(
        self, 
        parent: QWidget | None = None, 
        current_selection: str = "",
        character_level: int = 1
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select a Feat")
        self.resize(700, 500)
        
        self._compendium = Compendium.load()
        self._feats: List[Dict[str, Any]] = []
        self._selected_feat: Optional[str] = current_selection
        self._character_level = character_level
        
        self._layout_ui()
        self._load_feats()
        
        # Pre-select current if exists
        if current_selection:
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole) == current_selection:
                    self.list_widget.setCurrentItem(item)
                    break
    
    def _layout_ui(self):
        layout = QVBoxLayout(self)
        
        # Search
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type to filter feats...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)
        
        # Splitter: List | Details
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        splitter.addWidget(self.list_widget)
        
        # Details
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(8, 0, 0, 0)
        
        self.desc_text = QTextBrowser()
        self.desc_text.setOpenExternalLinks(False)
        self.desc_text.setPlaceholderText("Select a feat to view details.")
        details_layout.addWidget(self.desc_text)
        
        splitter.addWidget(details_widget)
        splitter.setSizes([250, 450])
        
        layout.addWidget(splitter)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_select = QPushButton("Select Feat")
        self.btn_select.setEnabled(False)
        self.btn_select.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_select)
        layout.addLayout(btn_layout)
    
    def _load_feats(self):
        self._feats = [r for r in self._compendium.records("feats") if isinstance(r, dict)]
        self._feats.sort(key=lambda x: str(x.get("name", "")))
        self._populate_list()
    
    def _populate_list(self, filter_text: str = ""):
        self.list_widget.clear()
        filter_lower = filter_text.lower()
        
        for feat in self._feats:
            name = str(feat.get("name", ""))
            if filter_text and filter_lower not in name.lower():
                continue
            
            # Skip fighting styles - they are granted by class features, not selectable as feats
            category = feat.get("category", "")
            if category == "fighting_style":
                continue
            
            # Get prerequisite from YAML field (now properly populated)
            prereq_str = feat.get("prerequisite") or ""
            
            # Extract level requirement from prerequisite string (e.g., "Level 19+")
            min_level = 0
            if prereq_str:
                level_match = re.search(r'Level\s*(\d+)\+?', prereq_str, re.IGNORECASE)
                if level_match:
                    min_level = int(level_match.group(1))
            
            # Filter out feats that require higher level than character
            if min_level > 0 and min_level > self._character_level:
                continue
            
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setData(Qt.ItemDataRole.UserRole + 1, feat)
            self.list_widget.addItem(item)
    
    def _on_search_changed(self, text: str):
        self._populate_list(text)
    
    def _on_selection_changed(self):
        items = self.list_widget.selectedItems()
        if not items:
            self._selected_feat = None
            self.btn_select.setEnabled(False)
            self.desc_text.clear()
            return
        
        item = items[0]
        name = item.data(Qt.ItemDataRole.UserRole)
        feat = item.data(Qt.ItemDataRole.UserRole + 1)
        
        self._selected_feat = name
        self.btn_select.setEnabled(True)
        
        # Get description - this contains the prerequisite in markdown format
        text_data = feat.get("text", {})
        if isinstance(text_data, dict):
            desc = text_data.get("full", text_data.get("summary", ""))
        elif isinstance(text_data, str):
            desc = text_data
        else:
            desc = str(feat.get("description", ""))
        
        # Prepend feat name as header if not already present
        if desc and not desc.strip().startswith("# "):
            desc = f"# {name}\n\n{desc}"
        
        # Render as styled HTML using the global markdown stylesheet
        html = convert_to_html_doc(desc)
        self.desc_text.setHtml(html)
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        self._selected_feat = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
    
    def get_selected_feat(self) -> Optional[str]:
        return self._selected_feat
