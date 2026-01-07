"""Monster Manual window for browsing and viewing monster stat blocks."""

from __future__ import annotations

import yaml
from typing import Any, List, Mapping, Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QPushButton,
    QButtonGroup,
)

from modules.compendium.service import Compendium
from gui.utils.compendium_formatting import display_name, render_markdown_with_links
from gui.utils.stat_blocks import render_monster_stat_block
from gui.resources import get_app_icon
from gui.widgets import FramelessWindow

class MonsterWindow(FramelessWindow):
    """Standalone window for browsing the Monster Manual."""

    _CR_VALUES = [
        "All CR", "0", "1/8", "1/4", "1/2", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
        "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24",
        "25", "26", "27", "28", "29", "30"
    ]
    
    _CREATURE_TYPES = [
        "All Types", "Aberration", "Beast", "Celestial", "Construct", "Dragon", "Elemental", "Fey",
        "Fiend", "Giant", "Humanoid", "Monstrosity", "Ooze", "Plant", "Undead"
    ]
    
    _SIZES = [
        "All Sizes", "Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Bestiary")
        self.setWindowIcon(get_app_icon())
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.resize(1200, 800)

        self._compendium: Compendium | None = None
        self._monsters: List[dict] = []
        self._filtered_monsters: List[dict] = []

        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # --- Title Bar ---
        title_label = QLabel("Bestiary")
        title_label.setProperty("class", "HeaderLabel")
        self.set_title_bar_center_widget(title_label)

        # --- Main Layout ---
        split = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(split, 1)

        # Left Pane: List and Filters
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # Search
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search monsters...")
        self._search.textChanged.connect(self._apply_filters)
        left_layout.addWidget(self._search)

        # Filters
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(4)
        
        self._cr_combo = QComboBox()
        self._cr_combo.addItems(self._CR_VALUES)
        self._cr_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._cr_combo, 1)
        
        self._type_combo = QComboBox()
        self._type_combo.addItems(self._CREATURE_TYPES)
        self._type_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._type_combo, 1)
        
        self._size_combo = QComboBox()
        self._size_combo.addItems(self._SIZES)
        self._size_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._size_combo, 1)
        
        left_layout.addLayout(filter_layout)

        # List
        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self._list)
        
        # Status Count
        self._status_label = QLabel("0 monsters")
        self._status_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        left_layout.addWidget(self._status_label)

        split.addWidget(left_widget)

        # Right Pane: Stat Block
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._details = QTextBrowser()
        self._details.setOpenExternalLinks(False)
        self._details.setPlaceholderText("Select a monster to view stats.")
        right_layout.addWidget(self._details)
        
        # Open source button (dev)
        # self._open_source_btn = QPushButton("Open Source")
        # right_layout.addWidget(self._open_source_btn)

        split.addWidget(right_widget)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 3)

        self.setCentralWidget(central)
        self._load_data()

    def _load_data(self):
        try:
            self._compendium = Compendium.load()
            # Fetch all monsters from the expected path or logical group
            # Assuming 'monsters' logical group exists or we scan for them
            # Since we just added them to 'players_handbook/monsters', they should be under 'monsters' if logic permits,
            # OR we need to ensure Compendium service knows about 'monsters'.
            # Looking at previous steps, we added files to database/compendium/dnd_2024/players_handbook/monsters/
            # The compendium service likely scans recursively. We need to check how it names keys.
            # Usually it's by folder name if not configured.
             
            raw_records = self._compendium.records("monsters")
            self._monsters = [dict(r) for r in raw_records if isinstance(r, Mapping) and r.get("name")]
            self._monsters.sort(key=lambda m: str(m.get("name", "")).lower())
            
            self._apply_filters()
            
        except Exception as e:
            self._details.setText(f"Error loading monsters: {e}")

    def _apply_filters(self):
        query = self._search.text().lower().strip()
        
        cr_filter = self._cr_combo.currentText()
        if cr_filter == "All CR": cr_filter = None
        
        type_filter = self._type_combo.currentText().lower()
        if type_filter == "all types": type_filter = None
        
        size_filter = self._size_combo.currentText().lower()
        if size_filter == "all sizes": size_filter = None

        self._filtered_monsters = []
        
        self._list.clear()
        
        for m in self._monsters:
            # 1. Text Search
            name = str(m.get("name", "")).lower()
            if query and query not in name:
                continue
            
            # 2. CR Filter
            # Note: stored CR might be string "1/4" or int/float. Convert to str for comparison.
            if cr_filter:
                m_cr = str(m.get("cr", "")).strip()
                if m_cr != cr_filter:
                    continue
            
            # 3. Type Filter
            if type_filter:
                m_type = str(m.get("type", "")).lower()
                # Check if filter is substring (e.g. "Humanoid" matches "Humanoid (Elf)")
                if type_filter not in m_type:
                    continue
                    
            # 4. Size Filter
            if size_filter:
                m_size = str(m.get("size", "")).lower()
                if size_filter not in m_size:
                     continue
            
            self._filtered_monsters.append(m)
            item = QListWidgetItem(m.get("name", "Unknown"))
            item.setData(Qt.ItemDataRole.UserRole, m)
            self._list.addItem(item)
            
        self._status_label.setText(f"{len(self._filtered_monsters)} monsters found")

    def _on_selection_changed(self):
        items = self._list.selectedItems()
        if not items:
            self._details.clear()
            return
            
        record = items[0].data(Qt.ItemDataRole.UserRole)
        self._render_monster(record)

    def _render_monster(self, record: dict):
        md = render_monster_stat_block(record)
        # We need to pass a lambda for label lookup if we want robust linking, 
        # or just pass the record itself if render_markdown_with_links handles it.
        # Looking at compendium_formatting.py: render_markdown_with_links(text, *, label_for_id)
        
        # We don't have a sophisticated label_for_id here without the compendium instance handy
        # But we do have self._compendium if loaded.
        
        def _resolve_id(rid: str) -> str:
            if self._compendium:
                return self._compendium.display_for_id(rid)
            return rid

        html = render_markdown_with_links(md, label_for_id=_resolve_id)
        self._details.setHtml(html)

