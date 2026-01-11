"""Main Character Sheet View Window."""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QGridLayout,
    QProgressBar,
)

from modules.character_sheet.model import CharacterSheet, ABILITY_NAMES
from modules.character_sheet.services.library import CharacterRecord, CharacterLibrary
from modules.compendium.modifiers.state import ModifierStateSnapshot
from modules.core.application_context import ApplicationContext
from modules.core.ui.resources import get_app_icon
from modules.core.ui.widgets import FramelessWindow
from modules.core.ui.dialogs import SpellcastingSettingsDialog
from PySide6.QtWidgets import (
    QDialog,
    QMessageBox,
)
from PySide6.QtGui import QPixmap
from pathlib import Path
from modules.character_sheet.services.library import DEFAULT_LIBRARY_PATH

class CharacterSheetWindow(FramelessWindow):
    """
    A read-only (mostly) view of the character sheet, styled like a digital PDF.
    """

    def __init__(self, record: CharacterRecord, app_context: ApplicationContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{record.display_name} - Character Sheet")
        self.setWindowIcon(get_app_icon())
        self.resize(1280, 800)

        self._record = record
        self._sheet = record.sheet
        self._app_context = app_context
        # snapshot logic should be passed in or derived
        self._modifier_snapshot = ModifierStateSnapshot([], record.modifiers) 
        
        # Styles
        self._apply_styles()

        # Main Layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header Bar (Name, Back button, Edit button)
        self._build_header(main_layout)

        # 2. Ribbon (HP, AC, etc)
        self._build_ribbon(main_layout)

        # 3. Content Area (3 Columns)
        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(24)
        
        # Left Column: Abilities, Skills
        left_col = self._build_left_column()
        content_layout.addWidget(left_col, 1) # Stretch factor 1

        # Center Column: Combat, Features
        center_col = self._build_center_column()
        content_layout.addWidget(center_col, 2) # Stretch factor 2 (Wider)

        # Right Column: Spells, Inventory
        right_col = self._build_right_column()
        content_layout.addWidget(right_col, 1) # Stretch factor 1

        main_layout.addWidget(content_area, 1)

    def _apply_styles(self):
        # Global styles are applied by app.setStyleSheet(DARK_THEME_STYLESHEET)
        pass

    def _build_header(self, layout: QVBoxLayout):
        header = QFrame()
        header.setProperty("class", "SectionPanel")
        # header.setStyleSheet("background-color: #1e293b; border-bottom: 1px solid #334155;")

        header.setFixedHeight(80)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)
        

        
        h_layout.addStretch()
        
        # Portrait (if available)
        portrait_path_str = self._record.sheet.identity.portrait_path
        if portrait_path_str:
             if Path(portrait_path_str).is_absolute():
                 p_path = Path(portrait_path_str)
             else:
                 p_path = DEFAULT_LIBRARY_PATH / "portraits" / portrait_path_str
             
             if p_path.exists():
                 p_label = QLabel()
                 p_label.setFixedSize(64, 64)
                 p_label.setProperty("class", "CharacterPortrait")
                 # p_label.setStyleSheet("border-radius: 4px; border: 1px solid #334155;")

                 p_label.setScaledContents(True)
                 p_label.setPixmap(QPixmap(str(p_path)))
                 h_layout.addWidget(p_label)
                 h_layout.addSpacing(16)


        h_layout.addStretch()
        
        # Identity
        identity_layout = QVBoxLayout()
        identity_layout.setSpacing(4)
        name_label = QLabel(self._record.display_name)
        name_label.setProperty("class", "ValueLabel")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        sub_text = f"Level {self._record.level} {self._record.sheet.identity.ancestry} {self._record.class_summary}"
        sub_label = QLabel(sub_text)
        sub_label.setProperty("class", "DimLabel")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        
        identity_layout.addWidget(name_label)
        identity_layout.addWidget(sub_label)
        h_layout.addLayout(identity_layout)
        
        h_layout.addStretch()
        
        # Edit Button
        edit_btn = QPushButton("Edit")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setProperty("class", "PrimaryButton")

        # Connect to a signal or callback to open the editor
        # For now, we'll just emit a custom signal or handle in parent
        # But wait, this window can handle calling the dialog if we import it.
        # Ideally we emit a signal 'request_edit'
        edit_btn.clicked.connect(self._on_edit_clicked)
        h_layout.addWidget(edit_btn)

        layout.addWidget(header)

    def _on_edit_clicked(self):
        """Open the editor dialog."""
        # Ensure we have a defined modifier snapshot
        snapshot = self._modifier_snapshot 
        if not snapshot:
             # Fallback
             snapshot = ModifierStateSnapshot([], self._record.modifiers)

        dialog = SpellcastingSettingsDialog(self._sheet, snapshot, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
            
        # Save changes
        new_sheet, new_modifiers = dialog.get_result()
        
        # We need to update the record in the library
        library = self._app_context.ensure_library()
        try:
            library.update_record(self._record.identifier, new_sheet, new_modifiers)
            self._record = library.get(self._record.identifier)
            self._sheet = self._record.sheet
            self._modifier_snapshot = ModifierStateSnapshot(snapshot.definitions, new_modifiers)
            
            # Refresh UI
            self.close() # Close and reopen? Or refresh? 
            # Reopening is easier to ensure all UI rebuilds, or we can implement a _refresh_ui()
            # For now, let's just close and let user re-open, or better, implement basic refresh
            QMessageBox.information(self, "Updated", "Character updated. Re-opening to refresh view.")
            # Ideally we would just update the view, but since our view build is in __init__, 
            # we would need to extract it. For V1 rework, closing is acceptable or we try to re-init.
            self.close()
            
            # Re-open (this would need a signal to parent to re-open or we just close)
            # Let's just close for now, simulating "Save & Close" behavior often seen.
            # OR we can just update internal state and hope for the best, but visuals won't update without _init calls.
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save changes: {e}")

    def _build_ribbon(self, layout: QVBoxLayout):
        ribbon = QFrame()
        ribbon.setFixedHeight(80)
        # Apply darker background for ribbon specifically if needed, using CustomWidget style or inline if unique
        # ribbon.setStyleSheet("background-color: #0f172a; border-bottom: 1px solid #334155;")
        # Actually it matches main window background in old theme.
        # Let's use SectionPanel but maybe transparent?
        # User wanted standard theme.
        ribbon.setProperty("class", "SectionPanel") 

        r_layout = QHBoxLayout(ribbon)
        r_layout.setContentsMargins(24, 10, 24, 10)
        r_layout.setSpacing(40)
        r_layout.addStretch()
        
        # Stat Helpers
        def add_ribbon_stat(label, value, icon_char=None):
            container = QWidget()
            v_layout = QVBoxLayout(container)
            v_layout.setSpacing(2)
            v_layout.setContentsMargins(0,0,0,0)
            
            val_lbl = QLabel(str(value))
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_lbl.setProperty("class", "ValueLabel")
            
            lbl_lbl = QLabel(label)
            lbl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_lbl.setProperty("class", "LabelLabel")

            
            v_layout.addWidget(val_lbl)
            v_layout.addWidget(lbl_lbl)
            r_layout.addWidget(container)

        combat = self._sheet.combat
        
        add_ribbon_stat("Armor Class", combat.armor_class or 10)
        add_ribbon_stat("Initiative", f"{combat.initiative_bonus:+d}" if combat.initiative_bonus else "+0")
        add_ribbon_stat("Speed", f"{combat.speed_ft or 30} ft.")
        add_ribbon_stat("Proficiency", f"+{self._get_proficiency()}")
        add_ribbon_stat("Max HP", combat.max_hp or 0)
        
        # Current HP with bar? Maybe just text for now
        
        r_layout.addStretch()
        layout.addWidget(ribbon)

    def _get_proficiency(self) -> int:
        # Simple calc based on level
        lvl = self._record.level
        if lvl >= 17: return 6
        if lvl >= 13: return 5
        if lvl >= 9: return 4
        if lvl >= 5: return 3
        return 2

    def _build_left_column(self) -> QWidget:
        col = QWidget()
        layout = QVBoxLayout(col)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(20)
        
        # Ability Scores
        abilities_frame = QFrame()
        abilities_frame.setProperty("class", "SectionPanel")

        ab_layout = QVBoxLayout(abilities_frame)
        
        title = QLabel("Ability Scores")
        title.setProperty("class", "SectionTitle")

        ab_layout.addWidget(title)
        
        for name in ABILITY_NAMES:
            row = QHBoxLayout()
            score_obj = self._sheet.get_ability(name)
            score = int(score_obj.score)
            mod = (score - 10) // 2
            
            lbl = QLabel(name)
            # lbl.setStyleSheet("font-weight: 700; color: #94a3b8; font-size: 16px;")
            lbl.setProperty("class", "DimLabel")
            lbl.setStyleSheet("font-weight: 700; font-size: 16px;")
            
            val = QLabel(f"{score}")
            val.setProperty("class", "DimLabel")
            val.setStyleSheet("font-size: 16px;")
            
            mod_lbl = QLabel(f"{mod:+d}")
            mod_lbl.setProperty("class", "ValueLabel")
            mod_lbl.setStyleSheet("font-size: 18px;")

            
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            row.addSpacing(16)
            row.addWidget(mod_lbl)
            ab_layout.addLayout(row)
            
        layout.addWidget(abilities_frame)
        
        # Skills (Placeholder for now, implementation depends on deeper logic)
        skills_frame = QFrame()
        skills_frame.setProperty("class", "SectionPanel")
        sk_layout = QVBoxLayout(skills_frame)
        sk_title = QLabel("Skills & Saves")
        sk_title.setProperty("class", "SectionTitle")
        sk_layout.addWidget(sk_title)
        
        sk_label = QLabel("Skill list would go here...")
        sk_label.setProperty("class", "DimLabel")
        sk_layout.addWidget(sk_label)
        
        layout.addWidget(skills_frame)
        
        layout.addStretch()
        return col

    def _build_center_column(self) -> QWidget:
        col = QWidget()
        layout = QVBoxLayout(col)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(20)
        
        # Attacks / Actions
        attacks_frame = QFrame()
        attacks_frame.setProperty("class", "SectionPanel")
        at_layout = QVBoxLayout(attacks_frame)
        at_title = QLabel("Attacks & Spellcasting")
        at_title.setProperty("class", "SectionTitle")
        at_layout.addWidget(at_title)
        
        # Simple list of equipped weapons?
        found_weapon = False
        for item in self._sheet.equipment:
            # Very naive check for now, real app has 'weapons' category
            if "sword" in item.name.lower() or "bow" in item.name.lower() or "dagger" in item.name.lower():
                found_weapon = True
                row = QHBoxLayout()
                name = QLabel(item.name)
                name.setStyleSheet("font-weight: 600; font-size: 15px;")
                row.addWidget(name)
                row.addStretch()
                bonus = QLabel("+? Hit") # Need calc logic
                bonus.setStyleSheet("color: #94a3b8;")
                row.addWidget(bonus)
                damage = QLabel("1d8+?") 
                damage.setStyleSheet("color: #cbd5e1;")
                row.addWidget(damage)
                at_layout.addLayout(row)
        
        if not found_weapon:
            lbl = QLabel("No weapons found.")
            lbl.setProperty("class", "DimLabel")
            at_layout.addWidget(lbl)

        layout.addWidget(attacks_frame)
        
        # Features & Traits
        features_frame = QFrame()
        features_frame.setProperty("class", "SectionPanel")
        ft_layout = QVBoxLayout(features_frame)
        ft_title = QLabel("Features & Traits")
        ft_title.setProperty("class", "SectionTitle")
        ft_layout.addWidget(ft_title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(0,0,0,0)
        c_layout.setSpacing(12)
        
        # Combine class features, race traits, feats
        for feature in (self._sheet.features or []):
            f_box = QWidget()
            f_layout = QVBoxLayout(f_box)
            f_layout.setContentsMargins(0,0,0,0)
            f_layout.setSpacing(2)
            
            f_name = QLabel(feature.title)
            # f_name.setStyleSheet("font-weight: 700; font-size: 14px; color: #e2e8f0;")
            f_name.setStyleSheet("font-weight: 700; font-size: 14px;") # Keep size/weight override? Or make a class?
            # It's basically a small header. Let's keep it clean or make a FeatureTitle class if reused.
            # Using bold default is fine or local override if specific.
            
            f_source = QLabel(feature.source)
            f_source.setProperty("class", "DimLabel")
            f_source.setStyleSheet("font-size: 11px;")
            
            f_desc = QLabel(feature.description)
            f_desc.setWordWrap(True)
            f_desc.setProperty("class", "DimLabel")
            f_desc.setStyleSheet("font-size: 13px;")
            
            f_layout.addWidget(f_name)
            f_layout.addWidget(f_source)
            f_layout.addWidget(f_desc)
            c_layout.addWidget(f_box)
            
            # Divider
            line = QFrame()
            line.setFixedHeight(1)
            line.setStyleSheet("background-color: #334155;")
            c_layout.addWidget(line)
            
        c_layout.addStretch()
        scroll.setWidget(content)
        ft_layout.addWidget(scroll)
        
        layout.addWidget(features_frame, 1) # This one expands
        return col

    def _build_right_column(self) -> QWidget:
        col = QWidget()
        layout = QVBoxLayout(col)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(20)

        # Spells
        spells_frame = QFrame()
        spells_frame.setProperty("class", "SectionPanel")
        sp_layout = QVBoxLayout(spells_frame)
        sp_title = QLabel("Magic")
        sp_title.setProperty("class", "SectionTitle")
        sp_layout.addWidget(sp_title)
        
        # Just a summary for now
        caster_level = self._record.level # Approx
        sp_label = QLabel(f"Spellcasting Ability: {self._sheet.spellcasting.spellcasting_ability or 'N/A'}")
        sp_layout.addWidget(sp_label)
        
        layout.addWidget(spells_frame)

        # Equipment
        eq_frame = QFrame()
        eq_frame.setProperty("class", "SectionPanel")
        eq_layout = QVBoxLayout(eq_frame)
        eq_title = QLabel("Inventory")
        eq_title.setProperty("class", "SectionTitle")
        eq_layout.addWidget(eq_title)
        
        # List items
        for item in (self._sheet.equipment or [])[:10]: # Limit for UI
            row = QHBoxLayout()
            name = QLabel(f"{item.quantity}x {item.name}")
            name.setStyleSheet("color: #cbd5e1;")
            row.addWidget(name)
            eq_layout.addLayout(row)
            
        if len(self._sheet.equipment) > 10:
             eq_layout.addWidget(QLabel(f"...and {len(self._sheet.equipment)-10} more"))

        layout.addWidget(eq_frame)
        layout.addStretch()

        return col
