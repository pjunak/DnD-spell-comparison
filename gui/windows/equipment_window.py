"""Equipment window for browsing and viewing items."""

from __future__ import annotations

from typing import List, Mapping, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QPushButton,
    QButtonGroup,
    QCheckBox
)

from services.compendium import Compendium
from gui.widgets.compendium_equipment_table import EquipmentTableView
from gui.utils.compendium_formatting import render_markdown_with_links, as_text, get_summary_md
from gui.utils.stat_blocks import render_equipment_stat_block
from ..resources import get_app_icon
from ..widgets import FramelessWindow

class EquipmentWindow(FramelessWindow):
    """Standalone window for browsing Equipment and Magic Items."""

    _EQUIPMENT_GROUPS = {
        "All": [],
        "Armor & Clothing": ["Armor", "Shield", "Clothing", "Boots", "Head", "Hands", "Jewelry", "Ring", "Cloak"],
        "Weapons": ["Simple Weapon", "Martial Weapon", "Staff", "Wand", "Rod"],
        "Consumables": ["Potion", "Scroll", "Poison", "Food"],
        "Vehicles & Mounts": ["Mount", "Land Vehicle", "Water Vehicle", "Air Vehicle"],
        "Miscellaneous": ["Tool", "Container", "Instrument", "Focus", "Other"]
    }
    
    _RARITY_FILTERS = [
        "Common", "Uncommon", "Rare", "Very Rare", "Legendary", "Artifact"
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Equipment Manager")
        self.setWindowIcon(get_app_icon())
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.resize(1300, 800)

        self._compendium: Compendium | None = None
        self._items: List[dict] = []

        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # --- Title Bar ---
        title_label = QLabel("Equipment & Magic Items")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ecf0f1;")
        self.set_title_bar_center_widget(title_label)

        # --- Main Layout ---
        split = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(split, 1)

        # Left Pane: Filters + Table
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # -- Filter Toolbar --
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(8)

        # Search/Group
        filter_layout.addWidget(QLabel("Group:"))
        self._group_combo = QComboBox()
        self._group_combo.addItems(list(self._EQUIPMENT_GROUPS.keys()))
        self._group_combo.currentTextChanged.connect(self._on_group_changed)
        filter_layout.addWidget(self._group_combo)

        # Rarity
        filter_layout.addWidget(QLabel("Rarity:"))
        self._rarity_buttons = QButtonGroup(self)
        self._rarity_buttons.setExclusive(False)
        
        rarity_colors = {
            "Common": "#95a5a6",
            "Uncommon": "#2ecc71",
            "Rare": "#3498db",
            "Very Rare": "#9b59b6",
            "Legendary": "#f1c40f",
            "Artifact": "#e74c3c"
        }
        
        for i, rarity in enumerate(self._RARITY_FILTERS):
            btn = QPushButton(rarity[0])
            btn.setToolTip(rarity)
            btn.setCheckable(True)
            btn.setFixedWidth(30)
            color = rarity_colors.get(rarity, "#7f8c8d")
            btn.setStyleSheet(f"QPushButton {{ color: {color}; font-weight: bold; }} QPushButton:checked {{ background-color: {color}; color: white; }}")
            btn.toggled.connect(self._apply_filters)
            self._rarity_buttons.addButton(btn, i)
            filter_layout.addWidget(btn)

        # Attunement
        self._attunement_check = QCheckBox("Attunement")
        self._attunement_check.toggled.connect(self._apply_filters)
        filter_layout.addWidget(self._attunement_check)

        # Clear
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(clear_btn)
        
        filter_layout.addStretch()
        left_layout.addWidget(filter_widget)

        # -- Table --
        self._table = EquipmentTableView()
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self._table)

        split.addWidget(left_widget)

        # Right Pane: Details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._details = QTextBrowser()
        self._details.setOpenExternalLinks(False)
        self._details.setPlaceholderText("Select an item to view details.")
        right_layout.addWidget(self._details)

        split.addWidget(right_widget)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 1)

        self.setCentralWidget(central)
        self._load_data()

    def _load_data(self):
        try:
            self._compendium = Compendium.load()
            raw = self._compendium.records("equipment")
            self._items = [dict(r) for r in raw if isinstance(r, Mapping) and r.get("name")]
            self._apply_filters()
        except Exception as e:
            self._details.setText(f"Error loading equipment: {e}")

    def _on_group_changed(self, group_name: str):
        self._apply_filters()

    def _apply_filters(self):
        # Gather active filters
        group = self._group_combo.currentText()
        allowed_types = self._EQUIPMENT_GROUPS.get(group, [])
        
        active_rarities = []
        for btn in self._rarity_buttons.buttons():
            if btn.isChecked():
                active_rarities.append(btn.toolTip().lower())
                
        require_attunement = self._attunement_check.isChecked()

        filtered = []
        for item in self._items:
            # Type Filter
            if allowed_types:
                item_type = str(item.get("type", "")).lower()
                # Simple substring match
                if not any(t.lower() in item_type for t in allowed_types):
                    # Also check tags if available
                    tags = [str(t).lower() for t in item.get("tags", [])]
                    if not any(t.lower() in tag for t in allowed_types for tag in tags):
                        continue
            
            # Rarity Filter
            if active_rarities:
                item_rarity = str(item.get("rarity", "Common")).lower()
                if not any(r in item_rarity for r in active_rarities):
                    continue
                    
            # Attunement Filter
            if require_attunement:
                att = item.get("attunement")
                if not att or str(att).lower() == "false" or str(att).lower() == "no":
                    continue

            filtered.append(item)
            
        self._table.set_items(filtered)

    def _clear_filters(self):
        self._group_combo.setCurrentIndex(0)
        for btn in self._rarity_buttons.buttons():
            btn.setChecked(False)
        self._attunement_check.setChecked(False)
        self._apply_filters()

    def _on_selection_changed(self):
        item = self._table.selected_item()
        if not item:
            self._details.clear()
            return
            
        # Render
        md = render_equipment_stat_block(item)
        
        def _resolve_id(rid: str) -> str:
            if self._compendium:
                return self._compendium.display_for_id(rid)
            return rid

        html = render_markdown_with_links(md, label_for_id=_resolve_id)
        self._details.setHtml(html)
