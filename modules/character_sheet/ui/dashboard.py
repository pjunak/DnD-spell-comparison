"""Redesigned Character Dashboard."""

from __future__ import annotations

from typing import Dict, List, Optional
from pathlib import Path

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QPainter, QColor, QPen, QBrush, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QGridLayout,
    QGridLayout,
    QDialog,
    QToolTip,
    QStackedWidget,
    QMessageBox,
)

from modules.core.ui.dialogs.spellcasting_settings_dialog import SpellcastingSettingsDialog

from modules.character_sheet.model import CharacterSheet, ABILITY_NAMES, EquipmentItem
from modules.character_sheet.services.library import CharacterRecord, DEFAULT_LIBRARY_PATH
from modules.compendium.modifiers.state import ModifierStateSnapshot
from modules.equipment.ui.window import EquipmentWindow
from modules.core.ui.dialogs.equipment_entry_dialog import EquipmentEntryDialog
from modules.core.application_context import ApplicationContext
from modules.core.ui.resources import get_app_icon
from modules.core.ui.theme import COLORS

# --- Local Styling Constants (The "Dashboard Theme") ---
DASH_COLORS = {
    "bg_base": "#121212",
    "bg_card": "#1e1e20",
    "bg_hero": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2b1029, stop:1 #121212)", # Subtle purple fade
    "accent": "#9b59b6",
    "accent_dim": "rgba(155, 89, 182, 0.3)",
    "text_main": "#e0e0e0",
    "text_dim": "#a0a0a0",
    "border": "#333333",
    "success": "#2ecc71",
    "danger": "#e74c3c",
}


class _StatHex(QWidget):
    """Custom painted hexagonal stat widget."""
    def __init__(self, label: str, value: int, modifier: int, parent=None):
        super().__init__(parent)
        self._label = label
        self._value = value
        self._modifier = modifier
        self.setFixedSize(60, 70)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw Hexagon-like shape (or just a nice rounded panel for now)
        # Using rounded rect for simplicity unless hex strictly required
        rect = self.rect().adjusted(2, 2, -2, -2)
        
        # Background
        painter.setBrush(QBrush(QColor(DASH_COLORS["bg_card"])))
        painter.setPen(QPen(QColor(DASH_COLORS["border"]), 1))
        painter.drawRoundedRect(rect, 12, 12)

        # Text
        painter.setPen(QColor(DASH_COLORS["accent"]))
        font = painter.font()
        font.setPixelSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect.adjusted(0, 5, 0, 0), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, self._label)

        # Modifier (Big)
        painter.setPen(QColor(DASH_COLORS["text_main"]))
        font.setPixelSize(22)
        font.setBold(True)
        painter.setFont(font)
        mod_str = f"{self._modifier:+d}"
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, mod_str)

        # Score (Small bubble at bottom)
        score_rect = rect.adjusted(10, rect.height() - 20, -10, -2)
        painter.setBrush(QBrush(QColor(DASH_COLORS["bg_base"])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(score_rect, 8, 8)
        
        painter.setPen(QColor(DASH_COLORS["text_dim"]))
        font.setPixelSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(score_rect, Qt.AlignmentFlag.AlignCenter, str(self._value))


class CharacterDashboard(QWidget):
    """
    The new 'Golden Standard' Character Sheet.
    Features: Dashboard layout, 'Equipped' toggle, collapsible drawers.
    """

    def __init__(self, record: CharacterRecord, app_context: ApplicationContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._record = record
        self._sheet = record.sheet
        self._app_context = app_context
        # Placeholder for modifier snapshot
        self._modifier_snapshot = ModifierStateSnapshot([], record.modifiers)
        
        # Helper map for spellcasting
        self._class_casting_map = {
            "Wizard": "INT", "Artificer": "INT",
            "Cleric": "WIS", "Druid": "WIS", "Ranger": "WIS", "Monk": "WIS",
            "Bard": "CHA", "Paladin": "CHA", "Sorcerer": "CHA", "Warlock": "CHA"
        }

        self._init_ui()

    def _init_ui(self):
        # Main Layout
        self.setLayout(QHBoxLayout())
        main_layout = self.layout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setStyleSheet(f"background-color: {DASH_COLORS['bg_base']}; color: {DASH_COLORS['text_main']}; font-family: 'Segoe UI';")

        # --- Sidebar ---
        self._sidebar = self._build_sidebar()
        main_layout.addWidget(self._sidebar)

        # --- Center Stage (Vitals + Split Area) ---
        center_stage = QWidget()
        center_layout = QVBoxLayout(center_stage)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)

        # 1. Header (Identity + Vitals)
        self._header = self._build_header_section()
        center_layout.addWidget(self._header)

        # 2. Main Split Area
        main_split = QSplitter(Qt.Orientation.Horizontal)
        main_split.setHandleWidth(1)
        main_split.setStyleSheet(f"QSplitter::handle {{ background: {DASH_COLORS['border']}; }}")
        
        # 1. Column 1: Quick Stats (Skills, Feats, Traits)
        left_panel = self._build_left_panel()
        main_split.addWidget(left_panel)

        # 2. Column 2: Main Workspace (Tabs)
        center_panel = QWidget()
        center_panel_layout = QVBoxLayout(center_panel)
        center_panel_layout.setContentsMargins(0, 0, 0, 0)
        center_panel_layout.setSpacing(0)
        
        # Navigation Bar
        self._nav_bar = self._build_nav_bar()
        center_panel_layout.addWidget(self._nav_bar)
        
         # Stacked Content
        self._stack = QStackedWidget()
        
        # Page 0: Overview
        self._overview_page = self._build_overview_page()
        self._stack.addWidget(self._overview_page)
        
        # Page 1: Backpack
        self._inventory_page = InventoryPage(self._record, self._app_context, self)
        self._stack.addWidget(self._inventory_page)
        
        # Page 2+: Placeholders
        self._grimoire_page = QLabel("Grimoire (Coming Soon)")
        self._grimoire_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stack.addWidget(self._grimoire_page)
        
        center_panel_layout.addWidget(self._stack)
        main_split.addWidget(center_panel)

        # 3. Column 3: The Inspector
        self._inspector_panel = self._build_inspector_panel()
        main_split.addWidget(self._inspector_panel)
        
        # Set Split Ratios (20%, 50%, 30%)
        main_split.setStretchFactor(0, 2)
        main_split.setStretchFactor(1, 5)
        main_split.setStretchFactor(2, 3)

        center_layout.addWidget(main_split, 1)
        
        main_layout.addWidget(center_stage, 1)
        
        # Refresh on tab change
        self._stack.currentChanged.connect(self._on_tab_changed)

    def _build_overview_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header is now global, no need to include locally
        
        # Action Area
        self._action_area = self._build_action_area()
        layout.addWidget(self._action_area, 1)
        
        return page

    def _rebuild_ui(self):
        # Legacy hook, might not need full rebuild anymore with tabs.
        # Just refresh current view.
        self._refresh_ui()

    def _on_tab_changed(self, index):
        # Refresh the page we just switched to
        if index == 0:
             self._refresh_overview()
        elif index == 1:
             self._inventory_page.refresh()
            
    def _refresh_overview(self):
        # We need to refresh the Equipped items list
        # Check if the layout exists to update it
        if hasattr(self, '_action_content_layout'):
             # Clear layout
             layout = self._action_content_layout
             while layout.count():
                 child = layout.takeAt(0)
                 if child.widget(): child.widget().deleteLater()
                 
             # Rebuild
             equipped_items = [i for i in self._sheet.equipment if i.equipped]
             
             if not equipped_items:
                  empty = QLabel("No items equipped. Open Backpack to equip weapons or armor.")
                  empty.setStyleSheet(f"color: {DASH_COLORS['text_dim']}; font-style: italic; padding: 20px;")
                  empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                  layout.addWidget(empty)
             else:
                  for item in equipped_items:
                      card = self._create_item_card(item)
                      layout.addWidget(card)
                      
             layout.addStretch()

    def _refresh_ui(self):
        # Global refresh
        self._refresh_overview()
        if hasattr(self, '_inventory_page'):
            self._inventory_page.refresh()


    def _refresh_ui(self):
        self._rebuild_ui()

    def _drawer_closed(self):
        self._refresh_ui()


    def _build_sidebar(self) -> QWidget:
        container = QFrame()
        container.setFixedWidth(90)
        container.setStyleSheet(f"background-color: {DASH_COLORS['bg_card']}; border-right: 1px solid {DASH_COLORS['border']};")
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(15)

        for name in ABILITY_NAMES:
            score_obj = self._sheet.get_ability(name)
            score = int(score_obj.score)
            mod = (score - 10) // 2
            
            hex_widget = _StatHex(name, score, mod)
            hex_widget.setToolTip(f"{name} Score: {score}\nModifier: {mod:+d}\nSaving Throw: {score_obj.save_modifier(self._sheet.proficiency_bonus()):+d}")
            layout.addWidget(hex_widget, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch()
        
        # Edit Button (Moved from Header)
        edit_btn = QPushButton("✎")
        edit_btn.setToolTip("Edit Character")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {DASH_COLORS['text_dim']};
                border: 1px solid {DASH_COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                font-weight: 700;
                font-size: 16px;
            }}
            QPushButton:hover {{
                color: {DASH_COLORS['accent']};
                border-color: {DASH_COLORS['accent']};
                background-color: rgba(155, 89, 182, 0.1);
            }}
        """)
        edit_btn.clicked.connect(self._open_editor)
        layout.addWidget(edit_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        return container

    def _build_header_section(self) -> QWidget:
        container = QFrame()
        container.setStyleSheet(f"background: {DASH_COLORS['bg_hero']}; border-radius: 12px; border: 1px solid {DASH_COLORS['border']};")
        container.setFixedHeight(140)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Left: Portrait + Name
        # Check portrait
        portrait_widget = QLabel()
        portrait_widget.setFixedSize(100, 100)
        portrait_widget.setStyleSheet(f"background-color: {DASH_COLORS['bg_base']}; border-radius: 8px; border: 1px solid {DASH_COLORS['accent']};")
        portrait_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        p_path = self._record.sheet.identity.portrait_path
        if p_path:
             if not Path(p_path).is_absolute():
                  full_p = DEFAULT_LIBRARY_PATH / "portraits" / p_path
             else:
                  full_p = Path(p_path)
             
             if full_p.exists():
                 pix = QPixmap(str(full_p))
                 portrait_widget.setPixmap(pix.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        
        layout.addWidget(portrait_widget)

        # Identity
        id_layout = QVBoxLayout()
        id_layout.setSpacing(4)
        name_lbl = QLabel(self._record.display_name)
        name_lbl.setStyleSheet("font-size: 24px; font-weight: 800; color: white;")
        
        sub_lbl = QLabel(f"Level {self._record.level} {self._record.sheet.identity.ancestry} {self._record.class_summary}")
        sub_lbl.setStyleSheet(f"color: {DASH_COLORS['text_dim']}; font-size: 14px;")
        
        id_layout.addWidget(name_lbl)
        id_layout.addWidget(sub_lbl)
        id_layout.addStretch()
        layout.addLayout(id_layout)

        layout.addStretch()

        layout.addStretch()
        # Edit button removed from here
        # layout.addWidget(edit_btn)
        # layout.addSpacing(20)

        # Vitals (AC, HP, Init)
        # Using a grid for tight packing
        vitals_grid = QGridLayout()
        vitals_grid.setHorizontalSpacing(30)
        vitals_grid.setVerticalSpacing(5)

        # AC
        ac_val = QLabel(str(self._sheet.combat.armor_class))
        ac_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ac_val.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        ac_lbl = QLabel("ARMOR")
        ac_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ac_lbl.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {DASH_COLORS['text_dim']};")
        
        vitals_grid.addWidget(ac_val, 0, 0)
        vitals_grid.addWidget(ac_lbl, 1, 0)

        # HP (Simple text for now, bar later)
        hp_str = f"{self._sheet.combat.current_hp} / {self._sheet.combat.max_hp}"
        hp_val = QLabel(hp_str)
        hp_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hp_val.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {DASH_COLORS['success']};")
        hp_lbl = QLabel("HIT POINTS")
        hp_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hp_lbl.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {DASH_COLORS['text_dim']};")

        vitals_grid.addWidget(hp_val, 0, 1)
        vitals_grid.addWidget(hp_lbl, 1, 1)
        
        # Initiative
        init_bonus = self._sheet.combat.initiative_bonus
        init_val = QLabel(f"{init_bonus:+d}")
        init_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        init_val.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        init_lbl = QLabel("INITIATIVE")
        init_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        init_lbl.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {DASH_COLORS['text_dim']};")
        
        vitals_grid.addWidget(init_val, 0, 2)
        vitals_grid.addWidget(init_lbl, 1, 2)

        # Proficiency
        prof_val = QLabel(f"{self._sheet.proficiency_bonus():+d}")
        prof_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prof_val.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        prof_lbl = QLabel("PROF.")
        prof_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prof_lbl.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {DASH_COLORS['text_dim']};")
        
        vitals_grid.addWidget(prof_val, 0, 3)
        vitals_grid.addWidget(prof_lbl, 1, 3)

        # Spell Stats (Conditional)
        cast_ability = self._get_primary_spellcasting_ability()
        
        if cast_ability:
            try:
                ability_obj = self._sheet.get_ability(cast_ability)
                mod = ability_obj.effective_modifier()
                prof = self._sheet.proficiency_bonus()
                
                dc = 8 + prof + mod
                atk = prof + mod
                
                # DC
                dc_val = QLabel(str(dc))
                dc_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
                dc_val.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {DASH_COLORS['accent']};")
                dc_lbl = QLabel(f"SAVE DC ({cast_ability})")
                dc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                dc_lbl.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {DASH_COLORS['text_dim']};")
                
                vitals_grid.addWidget(dc_val, 0, 4)
                vitals_grid.addWidget(dc_lbl, 1, 4)

                # Attack
                atk_val = QLabel(f"{atk:+d}")
                atk_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
                atk_val.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
                atk_lbl = QLabel("SPELL ATK")
                atk_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                atk_lbl.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {DASH_COLORS['text_dim']};")
                
                vitals_grid.addWidget(atk_val, 0, 5)
                vitals_grid.addWidget(atk_lbl, 1, 5)
                
            except KeyError:
                pass # Should not happen with valid map

        layout.addLayout(vitals_grid)

        return container
        
    def _get_primary_spellcasting_ability(self) -> str | None:
        """Determines primary spellcasting ability based on classes."""
        # TODO: Handle multi-classing more robustly (currently takes highest level caster)
        best_ability = None
        highest_level = -1
        
        for cls_entry in self._sheet.identity.classes:
            name = cls_entry.name
            level = cls_entry.level
            
            # Simple substring match for "Eldritch Knight" or "Arcane Trickster" could follow later
            # For now direct map
            ability = self._class_casting_map.get(name)
            if ability:
                if level > highest_level:
                     highest_level = level
                     best_ability = ability
        
        return best_ability

    def _build_action_area(self) -> QWidget:
        area = QWidget()
        layout = QVBoxLayout(area)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Section Title
        title_row = QHBoxLayout()
        lbl = QLabel("Equipped & Ready")
        lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {DASH_COLORS['accent']}; text-transform: uppercase; letter-spacing: 1px;")
        title_row.addWidget(lbl)
        title_row.addStretch()
        layout.addLayout(title_row)

        # Scroll for items
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        self._action_content_layout = QVBoxLayout(content)
        self._action_content_layout.setContentsMargins(0, 10, 0, 10)
        self._action_content_layout.setSpacing(10)

        # Initial Population
        self._refresh_overview()

        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return area
        
    def _build_left_panel(self) -> QWidget:
        """Passive Stats, Skills, Feats, Traits List"""
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {DASH_COLORS['bg_card']}; border-right: 1px solid {DASH_COLORS['border']};")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        
        lbl = QLabel("TRAITS & FEATS")
        lbl.setStyleSheet(f"font-weight: bold; color: {DASH_COLORS['text_dim']}; font-size: 12px; letter-spacing: 1px;")
        layout.addWidget(lbl)
        
        # Placeholder List
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setSpacing(5)
        
        # Example Traits & Features
        # Currently model stores everything in 'features'. 
        # We can try to distinguish by source if needed, or simply list all for now.
        
        for feature in self._sheet.features:
             # Simple logic: if source contains "Feat", style differently?
             # For now just list them.
             text = f"• {feature.title}"
             if "Feat" in feature.source:
                 text = f"★ {feature.title}"
                 
             f_lbl = QLabel(text)
             f_lbl.setWordWrap(True)
             if "Feat" in feature.source:
                 f_lbl.setStyleSheet(f"color: {DASH_COLORS['accent']}; font-weight: bold;")
                 
             f_lbl.setToolTip(f"{feature.source}\n{feature.description}")
             c_layout.addWidget(f_lbl)

        c_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return panel

    def _build_inspector_panel(self) -> QWidget:
        """Right-most panel for contextual details."""
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {DASH_COLORS['bg_base']}; border-left: 1px solid {DASH_COLORS['border']};")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header for Inspector
        self._inspector_title = QLabel("NOTES")
        self._inspector_title.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {DASH_COLORS['accent']};")
        layout.addWidget(self._inspector_title)
        
        # Content
        self._inspector_content = QLabel("Select an item, spell, or feature to view details.")
        self._inspector_content.setWordWrap(True)
        self._inspector_content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._inspector_content, 1) # Expand
        
        return panel

    def _create_item_card(self, item) -> QWidget:
        card = QFrame()
        card.setFixedHeight(40) # Thinner
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {DASH_COLORS['bg_card']};
                border-radius: 4px;
                border: 1px solid {DASH_COLORS['border']};
            }}
            QFrame:hover {{
                border-color: {DASH_COLORS['accent']};
            }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(10, 2, 10, 2)        
        name = QLabel(item.name)
        name.setStyleSheet("font-weight: bold; font-size: 14px; border: none; background: transparent;")
        layout.addWidget(name)
        layout.addStretch()
        
        # Read-only Overview (No Un-equip here)
        
        return card

    def _save_changes(self):
        library = self._app_context.ensure_library()
        try:
            library.update_record(self._record.identifier, self._sheet, self._record.modifiers)
        except Exception:
            pass # Handle error gracefully

    def _refresh_ui(self):
        # Brute force refresh: delete layout and rebuild
        # In a real app we'd use signals or cleaner wiring
        # For this prototype, let's close and reopen or just accept the flicker if we rebuild layout?
        # Rebuilding 'action_area' specifically is better.
        pass # To be implemented or rely on parent reload

    def _open_editor(self):
        # reuse SpellcastingSettingsDialog logic
        snapshot = self._modifier_snapshot
        if not snapshot:
             snapshot = ModifierStateSnapshot([], self._record.modifiers)

        dialog = SpellcastingSettingsDialog(self._sheet, snapshot, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
            
        # Save changes
        new_sheet, new_modifiers = dialog.get_result()
        
        library = self._app_context.ensure_library()
        try:
            library.update_record(self._record.identifier, new_sheet, new_modifiers)
            self._record = library.get(self._record.identifier)
            self._sheet = self._record.sheet
            self._modifier_snapshot = ModifierStateSnapshot(snapshot.definitions, new_modifiers)
            
            # Legacy refresh trigger (might need to update Dashboard vars)
            self._refresh_ui()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save changes: {e}")

    def _build_nav_bar(self) -> QWidget:
        # Replaces _build_dock
        nav = QFrame()
        nav.setFixedHeight(40)
        nav.setStyleSheet(f"background-color: {DASH_COLORS['bg_card']}; border-bottom: 1px solid {DASH_COLORS['border']};")
        
        layout = QHBoxLayout(nav)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        
        def add_tab_btn(label, index):
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFlat(True)
            # Add basic checkable style logic if time permits, for now simple buttons
            btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 13px; 
                    font-weight: 700; 
                    color: {DASH_COLORS['text_dim']}; 
                    border: none;
                    padding: 5px 10px;
                }}
                QPushButton:hover {{
                    color: {DASH_COLORS['accent']};
                    background-color: rgba(255, 255, 255, 0.05);
                    border-radius: 4px;
                }}
            """)
            btn.clicked.connect(lambda: self._stack.setCurrentIndex(index))
            layout.addWidget(btn)
            
        add_tab_btn("OVERVIEW", 0)
        add_tab_btn("BACKPACK", 1) # Renamed
        add_tab_btn("GRIMOIRE", 2)
        add_tab_btn("FEATURES", 3)
        add_tab_btn("NOTES", 4)
        
        layout.addStretch()
        return nav

class InventoryPage(QWidget):
    """
    Full page inventory view.
    """
    def __init__(self, record: CharacterRecord, app_context: ApplicationContext, dashboard: CharacterDashboard):
        super().__init__()
        self._record = record
        self._sheet = record.sheet
        self._app_context = app_context
        self._dashboard = dashboard # Back reference for saving
        
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Controls
        controls = QHBoxLayout()
        
        title = QLabel("Backpack")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {DASH_COLORS['text_main']};")
        controls.addWidget(title)
        
        controls.addStretch()
        
        browse_btn = QPushButton("+ Add from Ruleset")
        browse_btn.setProperty("class", "PrimaryButton")
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._open_ruleset_browser)
        
        custom_btn = QPushButton("+ Create Custom")
        custom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        custom_btn.clicked.connect(self._open_custom_dialog)
        
        controls.addWidget(browse_btn)
        controls.addWidget(custom_btn)
        
        layout.addLayout(controls)
        
        # Item List
        # Using a QScrollArea with a VBoxLayout for now to match style
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")
        
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(8)
        
        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll)
        
        self.refresh()

    def refresh(self):
        # Rebuild list
        # Clear
        while self._content_layout.count():
             child = self._content_layout.takeAt(0)
             if child.widget(): child.widget().deleteLater()
             
        for item in self._sheet.equipment:
            card = self._create_item_row(item)
            self._content_layout.addWidget(card)
            
        self._content_layout.addStretch()

    def _create_item_row(self, item: EquipmentItem) -> QWidget:
        row = QFrame()
        row.setStyleSheet(f"""
            QFrame {{
                background-color: {DASH_COLORS['bg_card']};
                border-radius: 6px;
                border: 1px solid {DASH_COLORS['border']};
            }}
            QFrame:hover {{
                border-color: {DASH_COLORS['accent']};
            }}
        """)
        row.setFixedHeight(40)
        l = QHBoxLayout(row)
        l.setContentsMargins(10, 2, 10, 2)
        
        # Icon/Type indicator?
        
        name_txt = item.name
        if item.attuned: name_txt += " [A]"
        name = QLabel(name_txt)
        name.setStyleSheet("font-weight: bold; font-size: 13px; border: none; background: transparent;")
        l.addWidget(name)
        
        l.addStretch()
        
        qty = QLabel(f"x{item.quantity}")
        qty.setStyleSheet(f"color: {DASH_COLORS['text_dim']}; border: none; background: transparent;")
        l.addWidget(qty)
        
        l.addSpacing(20)
        
        equip_btn = QPushButton("Unequip" if item.equipped else "Equip")
        equip_style = f"""
            QPushButton {{
                background-color: {DASH_COLORS['accent'] if item.equipped else 'transparent'};
                border: 1px solid {DASH_COLORS['accent']};
                color: {'white' if item.equipped else DASH_COLORS['accent']};
                border-radius: 4px;
                padding: 2px 8px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {DASH_COLORS['accent']};
                color: white;
            }}
        """
        equip_btn.setStyleSheet(equip_style)
        equip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        equip_btn.clicked.connect(lambda _, i=item: self._toggle_equip(i))
        l.addWidget(equip_btn)
        
        # Remove/Delete?
        
        return row

    def _toggle_equip(self, item):
        item.equipped = not item.equipped
        self._dashboard._save_changes()
        self.refresh()

    def _open_ruleset_browser(self):
        # Open EquipmentWindow
        self._eq_window = EquipmentWindow(parent=self.window(), selection_mode=True)
        self._eq_window.setWindowFlags(Qt.WindowType.Window)
        self._eq_window.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._eq_window.items_selected.connect(self._on_items_added)
        self._eq_window.show()

    def _open_custom_dialog(self):
        dialog = EquipmentEntryDialog(parent=self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
             item = dialog.get_item()
             if item.name:
                 self._on_items_added([(dict(name=item.name, weight=item.weight_lb, cost=item.cost, rarity=item.rarity), item.quantity)]) 
                 # Wait, logic mismatch. _on_items_added expects list of tuples. 
                 # Should adapt. 
                 self._add_to_sheet([item])

    def _on_items_added(self, items_data):
        new_items = []
        for data, qty in items_data:
             entry = EquipmentItem(
                name=str(data.get("name", "New Item")),
                quantity=max(1, qty),
                weight_lb=float(data.get("weight", 0.0) or 0.0),
                attuned=bool(data.get("attunement", False)),
                equipped=False,
                compendium_id=str(data.get("id", "")),
                rarity=str(data.get("rarity", "")),
            )
             new_items.append(entry)
        self._add_to_sheet(new_items)

    def _add_to_sheet(self, items):
        self._sheet.equipment.extend(items)
        self._dashboard._save_changes()
        self.refresh()





