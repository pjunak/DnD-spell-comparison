"""Spell Window for browsing and viewing spells."""

from __future__ import annotations

from typing import List, Mapping, Optional, Any
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
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

from modules.compendium.service import Compendium
from gui.widgets.compendium_spells_table import SpellsTableView
from gui.utils.compendium_formatting import render_markdown_with_links
from gui.utils.stat_blocks import render_spell_stat_block
from gui.resources import get_app_icon
from gui.widgets import FramelessWindow

class SpellWindow(FramelessWindow):
    """Standalone window for browsing Spells."""
    
    item_selected = Signal(dict)
    
    _SCHOOLS = [
        "All Schools", "Abjuration", "Conjuration", "Divination", 
        "Enchantment", "Evocation", "Illusion", "Necromancy", "Transmutation"
    ]

    def __init__(self, parent: QWidget | None = None, selection_mode: bool = False) -> None:
        super().__init__(parent)
        self._selection_mode = selection_mode
        self.setWindowTitle("Select Spell" if selection_mode else "Spell Browser")
        self.setWindowIcon(get_app_icon())
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.resize(1300, 800)

        self._compendium: Compendium | None = None
        self._spells: List[dict] = []
        self._current_payload: Mapping[str, Any] | None = None

        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # --- Title Bar ---
        title_label = QLabel("Grimoire")
        title_label.setProperty("class", "HeaderLabel")
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
        self._search_input.setPlaceholderText("Search spells...")
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search spells...")
        self._search_input.textChanged.connect(self._apply_filters)
        left_layout.addWidget(self._search_input)
        self._search_input.textChanged.connect(self._apply_filters)
        left_layout.addWidget(self._search_input)

        # -- Filter Toolbar --
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(8)
        
        # Level Buttons
        self._level_buttons = QButtonGroup(self)
        self._level_buttons.setExclusive(False)
        for i in range(10):
            label = str(i)
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedWidth(30)
            btn.setToolTip(f"Level {i}")
            btn.toggled.connect(self._apply_filters)
            self._level_buttons.addButton(btn, i)
            filter_layout.addWidget(btn)

        # School Buttons
        self._school_group = QButtonGroup(self)
        self._school_group.setExclusive(False)
        
        # School Colors (approximate 5e standard colors)
        school_colors = {
            "Abjuration": "#3498DB",    # Blue
            "Conjuration": "#E67E22",   # Orange
            "Divination": "#BDC3C7",    # Silver/Grey
            "Enchantment": "#E91E63",   # Pink/Magenta
            "Evocation": "#E74C3C",     # Red
            "Illusion": "#9B59B6",      # Purple
            "Necromancy": "#2ECC71",    # Green (often associated with acid/poison/undead glow) - or Black
            "Transmutation": "#F1C40F"  # Gold
        }

        # Header label for schools? Or just list them.
        # Let's add them directly.
        # Note: "All Schools" is implicit if none selected? Or explicit button?
        # User asked for buttons "like for levels". Levels are multiple selection.
        # So multiple school selection makes sense.
        
        for school, color in school_colors.items():
            # Use 3 letter abbreviation
            btn = QPushButton(school[:3]) 
            btn.setCheckable(True)
            btn.setToolTip(school)
            # Style: Color background when checked, colored border when unchecked?
            # Or always colored but brighter when checked?
            # Let's do a simple style sheet injection per button.
            
            # Base style
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: 2px solid {color};
                    color: {color};
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-weight: bold;
                }}
                QPushButton:checked {{
                    background-color: {color};
                    color: white;
                }}
                QPushButton:hover {{
                    background-color: {color}40; /* 25% opacity */
                }}
            """)
            
            btn.toggled.connect(self._apply_filters)
            self._school_group.addButton(btn)
            filter_layout.addWidget(btn)
        
        filter_layout.addStretch()
        left_layout.addWidget(filter_widget)

        # -- Table --
        self._table = SpellsTableView()
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self._table)

        # -- Status Bar --
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        left_layout.addWidget(self._status_label)

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
        self._details.setPlaceholderText("Select a spell to view details.")
        right_layout.addWidget(self._details)

        split.addWidget(right_widget)
        
        # Table pane: stretch to fill available space
        split.setStretchFactor(0, 1)
        # Details pane: fixed width, doesn't stretch
        split.setStretchFactor(1, 0)
        
        # Set fixed width for details pane
        right_widget.setFixedWidth(400)

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
            self._cancel_btn.setFixedWidth(100)
            # self._cancel_btn inherits default button styles
            btn_layout.addWidget(self._cancel_btn)
            
            self._select_btn = QPushButton("Select")
            self._select_btn.clicked.connect(self._confirm_selection)
            self._select_btn.setEnabled(False)
            self._select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._select_btn.setFixedWidth(100)
            self._select_btn.setFixedWidth(100)
            self._select_btn.setProperty("class", "PrimaryButton")
            btn_layout.addWidget(self._select_btn)
            
            root.addLayout(btn_layout)

        self.setCentralWidget(central)
        self._load_data()

    def _load_data(self):
        try:
            self._compendium = Compendium.load()
            # The table widget might expect rows or payload. 
            # Looking at source, SpellsTableView has set_spells(spells) or similar? 
            # Checked source previously: it has `set_spells` if it inherits from generic table, or we just pass the full list.
            # Actually, let's just use use apply_filters logic which seems to handle it if we look at CompendiumWindow usage.
            # CompendiumWindow usage: self._spells_table.apply_filters(level_ints, schools, query)
            # But we also need to load the data into it first.
            # CompendiumWindow had: self._spells_table.set_spells(spells) ? 
            # No, looking at previous views - SpellsTableView was instantiated with compendium?
            # Creating CompendiumWindow: self._spells_table = CompendiumSpellsTable(self._compendium) ?
            # Wait, SpellsTableView usage in CompendiumWindow was removed.
            # Let's check SpellsTableView implementation quickly if needed.
            
            raw = self._compendium.records("spells")
            self._spells = [dict(r) for r in raw if isinstance(r, Mapping) and r.get("name")]
            self._table.set_spells(self._spells)
            self._apply_filters()
            
        except Exception as e:
            self._details.setText(f"Error loading spells: {e}")

    def _update_status(self) -> None:
        """Update the status label with the current spell count."""
        visible = self._table.visible_count()
        total = len(self._spells)
        self._status_label.setText(f"Showing {visible} of {total} spells")

    def _apply_filters(self):
        # Gather levels
        levels = []
        for btn in self._level_buttons.buttons():
            if btn.isChecked():
                levels.append(int(btn.text()))
                
        # Gather school
        schools = []
        for btn in self._school_group.buttons():
            if btn.isChecked():
                # We used abbreviation for text, so use tooltip for full name
                schools.append(btn.toolTip())
            
        # Search text
        query = self._search_input.text().strip()
        
        self._table.apply_filters(levels if levels else [], schools, query)
        self._update_status()

    def _on_open_source_clicked(self) -> None:
        if not self._current_payload:
            return
            
        path_str = self._current_payload.get("_meta_source_path")
        if not path_str:
            return

        path = Path(path_str)
        if not path.exists():
            return
            
        url = QUrl.fromLocalFile(str(path.resolve()))
        url = QUrl.fromLocalFile(str(path.resolve()))
        QDesktopServices.openUrl(url)

    def _confirm_selection(self) -> None:
        if self._current_payload:
            self.item_selected.emit(self._current_payload)
            self.close()

    def _on_selection_changed(self):
        payload = self._table.get_selected_spell()
        self._current_payload = payload
        
        # Update dev button visibility
        has_source = bool(payload and payload.get("_meta_source_path"))
        self._open_source_btn.setVisible(has_source)

        # Update select button
        if self._selection_mode and hasattr(self, '_select_btn'):
            self._select_btn.setEnabled(bool(payload))

        if not payload:
            self._details.clear()
            return
            
        # Render
        md = render_spell_stat_block(payload)
        
        def _resolve_id(rid: str) -> str:
            if self._compendium:
                return self._compendium.display_for_id(rid)
            return rid

        html = render_markdown_with_links(md, label_for_id=_resolve_id)
        self._details.setHtml(html)
