"""Dialog for entering custom equipment modifiers."""

from __future__ import annotations

from typing import List

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QSpinBox,
    QWidget,
)

from modules.characters.model import EquipmentItem

ITEM_SLOT_OPTIONS: List[str] = [
    "Arcane Focus",
    "Weapon",
    "Armor",
    "Shield",
    "Ring",
    "Amulet",
    "Wand",
    "Staff",
    "Rod",
    "Consumable",
    "Other",
]

ITEM_BONUS_OPTIONS: List[str] = [
    "spell_attack",
    "spell_save_dc",
    "spell_damage",
    "attack",
    "save_dc",
    "damage",
    "initiative",
    "other",
]


class EquipmentEntryDialog(QDialog):
    """Modal dialog that captures a single equipment record."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Equipment")
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        layout.addRow("Item Name", self.name_edit)

        self.slot_combo = QComboBox()
        self.slot_combo.addItems(ITEM_SLOT_OPTIONS)
        self.slot_combo.setEditable(True)
        layout.addRow("Slot / Type", self.slot_combo)

        self.bonus_type_combo = QComboBox()
        self.bonus_type_combo.addItems(ITEM_BONUS_OPTIONS)
        self.bonus_type_combo.setEditable(True)
        layout.addRow("Bonus Type", self.bonus_type_combo)

        self.bonus_value_spin = QSpinBox()
        self.bonus_value_spin.setRange(-10, 10)
        layout.addRow("Bonus Value", self.bonus_value_spin)

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Optional notes")
        layout.addRow("Notes", self.notes_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _validate_and_accept(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Missing Item Name", "Please enter an item name.")
            return
        self.accept()

    @property
    def slot_type(self) -> str:
        return self.slot_combo.currentText().strip()

    @property
    def bonus_type(self) -> str:
        return self.bonus_type_combo.currentText().strip().lower()

    @property
    def bonus_value(self) -> int:
        return self.bonus_value_spin.value()

    def to_item(self) -> EquipmentItem:
        bonuses = {self.bonus_type: self.bonus_value} if self.bonus_type else {}
        return EquipmentItem(
            self.name_edit.text().strip(),
            1,
            0.0,
            False,
            self.notes_edit.toPlainText().strip(),
            bonuses,
        )


__all__ = ["EquipmentEntryDialog"]
