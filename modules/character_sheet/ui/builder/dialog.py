"""
Main container for the redesign Character Builder experience.
Migrating from SpellcastingSettingsDialog to a split Creation/Leveling tab approach.
"""

from __future__ import annotations

import copy
from typing import Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
    QTabWidget,
    QWidget,
)

from modules.character_sheet.model import CharacterSheet
from modules.compendium.modifiers.state import ModifierStateSnapshot
from modules.character_sheet.ui.builder.tabs.creation import CreationTab
from modules.character_sheet.ui.builder.tabs.leveling import LevelingTab


class CharacterBuilderDialog(QDialog):
    """
    The new Character Builder.
    Tabs:
      1. Creation: Base identity, species, class (level 1), background, initial stats.
      2. Leveling: Post-creation progression management (1-20).
    """

    def __init__(
        self,
        sheet: CharacterSheet,
        modifier_snapshot: ModifierStateSnapshot | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Character Builder")
        self.resize(1024, 768)

        # Working copies
        self._sheet = copy.deepcopy(sheet)
        self._modifier_snapshot = modifier_snapshot or ModifierStateSnapshot([], {})
        
        # Layout
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 1. Creation Tab
        self.creation_tab = CreationTab(self._sheet, self._modifier_snapshot, parent=self)
        self.tabs.addTab(self.creation_tab, "Creation")

        # 2. Leveling Tab
        self.leveling_tab = LevelingTab(self._sheet, self._modifier_snapshot, parent=self)
        self.tabs.addTab(self.leveling_tab, "Leveling")

        # Connect signals for cross-tab updates?
        # e.g., if Name changes in Creation, title might change.
        # e.g., if Class changes in Creation, Leveling tab needs rebuild.
        self.creation_tab.dataChanged.connect(self._on_creation_data_changed)

        # Dialog Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_creation_data_changed(self):
        """Called when base creation data (Identity, Class Lvl 1) changes."""
        # Signal Leveling tab to refresh its base assumptions
        self.leveling_tab.refresh_from_sheet()

    def get_result(self) -> Tuple[CharacterSheet, dict]:
        """Return the modified sheet and modifier states."""
        # Finalize data from tabs if needed
        return self._sheet, self._modifier_snapshot.states
