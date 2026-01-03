"""Equipment window for browsing and viewing items."""

from __future__ import annotations

from typing import List, Mapping, Optional
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
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
    QCheckBox,
    QLineEdit
)

from services.compendium import Compendium
from gui.widgets.compendium_equipment_table import EquipmentTableView
from gui.utils.compendium_formatting import render_markdown_with_links, as_text, get_summary_md
from gui.utils.stat_blocks import render_equipment_stat_block
from ..resources import get_app_icon
from ..widgets import FramelessWindow

class EquipmentWindow(FramelessWindow):
    """Standalone window for browsing Equipment and Magic Items."""

    item_selected = Signal(dict)

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

    def __init__(self, parent: QWidget | None = None, selection_mode: bool = False) -> None:
        super().__init__(parent)
        self._selection_mode = selection_mode
        self.setWindowTitle("Select Equipment" if selection_mode else "Equipment Manager")
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

        # -- Search Bar --
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search items...")
        self._search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #5d5d5d;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: #2b2b2b;
                color: #ffffff;
            }
        """)
        self._search_input.textChanged.connect(self._apply_filters)
        left_layout.addWidget(self._search_input)

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

        # Dev mode button
        self._open_source_btn = QPushButton("Open Source File")
        self._open_source_btn.setVisible(False)
        self._open_source_btn.clicked.connect(self._on_open_source_clicked)
        self._open_source_btn.setStyleSheet("text-align: left; padding: 5px; background-color: #4a4a4a; color: #ffffff; border: none;")
        right_layout.addWidget(self._open_source_btn)

        self._details = QTextBrowser()
        self._details.setOpenExternalLinks(False)
        self._details.setPlaceholderText("Select an item to view details.")
        right_layout.addWidget(self._details)

        split.addWidget(right_widget)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        
        # Set fixed width for details pane
        right_widget.setFixedWidth(400)

        # Selector Buttons
        if self._selection_mode:
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0, 10, 0, 0)
            btn_layout.addStretch()
            
            self._cancel_btn = QPushButton("Cancel")
            self._cancel_btn.clicked.connect(self.close)
            self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._cancel_btn.setFixedWidth(100)
            self._cancel_btn.setStyleSheet("""
                QPushButton { background-color: #4a4a4a; color: white; border-radius: 4px; padding: 6px; }
                QPushButton:hover { background-color: #5a5a5a; }
            """)
            btn_layout.addWidget(self._cancel_btn)
            
            self._select_btn = QPushButton("Select")
            self._select_btn.clicked.connect(self._confirm_selection)
            self._select_btn.setEnabled(False)
            self._select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._select_btn.setFixedWidth(100)
            self._select_btn.setStyleSheet("""
                QPushButton { background-color: #27ae60; color: white; border-radius: 4px; padding: 6px; font-weight: bold; }
                QPushButton:hover { background-color: #2ecc71; }
                QPushButton:disabled { background-color: #2c3e50; color: #7f8c8d; }
            """)
            btn_layout.addWidget(self._select_btn)
            
            root.addLayout(btn_layout)

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

    def _on_open_source_clicked(self) -> None:
        item = self._table.get_selected_item()
        if not item:
            return
            
        path_str = item.get("_meta_source_path")
        if not path_str:
            return

        path = Path(path_str)
        if not path.exists():
            return
            
        url = QUrl.fromLocalFile(str(path.resolve()))
        QDesktopServices.openUrl(url)

    def _confirm_selection(self) -> None:
        item = self._table.get_selected_item()
        if item:
            self.item_selected.emit(dict(item))
            self.close()

    def _apply_filters(self):
        # Gather active filters
        group = self._group_combo.currentText()
        allowed_types = self._EQUIPMENT_GROUPS.get(group, [])
        
        active_rarities = []
        for btn in self._rarity_buttons.buttons():
                active_rarities.append(btn.toolTip().lower())
                
        require_attunement = self._attunement_check.isChecked()
        query = self._search_input.text().strip().lower()

        filtered = []
        for item in self._items:
            # Name Filter
            if query and query not in item.get("name", "").lower():
                continue
            
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
        item = self._table.get_selected_item()
        if not item:
            self._details.clear()
            self._open_source_btn.setVisible(False)
            return
            
        # Update dev button visibility
        # Update dev button visibility
        has_source = bool(item.get("_meta_source_path"))
        self._open_source_btn.setVisible(has_source)

        # Update select button
        if self._selection_mode and hasattr(self, '_select_btn'):
            self._select_btn.setEnabled(bool(item))
            
        # Render
        md = render_equipment_stat_block(item)
        
        def _resolve_id(rid: str) -> str:
            if self._compendium:
                return self._compendium.display_for_id(rid)
            return rid

        html = render_markdown_with_links(md, label_for_id=_resolve_id)
        self._details.setHtml(html)
