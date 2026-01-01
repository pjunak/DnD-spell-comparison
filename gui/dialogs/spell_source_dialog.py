"""Dialog dedicated to capturing spell sources for automatic spell access."""

from __future__ import annotations

from typing import Iterable, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from character_sheet import SpellAccessEntry

SPELL_SOURCE_CHOICES = [
    ("Class", "class"),
    ("Subclass", "subclass"),
    ("Feat", "feat"),
    ("Heritage", "heritage"),
    ("Background", "background"),
    ("Invocation", "invocation"),
    ("Pact Boon", "pact"),
    ("Magic Item", "item"),
    ("Patron", "patron"),
    ("Custom Source", "custom_source"),
    ("Other", "other"),
]

SPELL_CATEGORY_OPTIONS = [
    "Damage",
    "Control",
    "Utility",
    "Healing",
    "Defense",
    "Support",
    "Summoning",
    "Detection",
    "Other",
]


class SpellSourceDialog(QDialog):
    """Dialog for registering spell sources (manual or custom)."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        initial_source: dict | None = None,
        initial_spells: Iterable[str] | None = None,
        title: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title or "Add Spell Source")
        self._initial_source = dict(initial_source or {})
        self._initial_spells = list(initial_spells or [])
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        layout.addLayout(form)

        self.source_type_combo = QComboBox()
        for label, value in SPELL_SOURCE_CHOICES:
            self.source_type_combo.addItem(label, value)
        self.source_type_combo.currentIndexChanged.connect(self._update_source_hint)
        form.addRow("Source Type", self.source_type_combo)

        self.source_name_edit = QLineEdit()
        form.addRow("Source Name", self.source_name_edit)

        self.source_category_combo = self._build_combo([""] + SPELL_CATEGORY_OPTIONS)
        form.addRow("Category", self.source_category_combo)

        self.source_ability_combo = self._build_combo(["", "STR", "DEX", "CON", "INT", "WIS", "CHA"])
        form.addRow("Ability Override", self.source_ability_combo)

        self.prepared_check = QCheckBox("Mark spells from this source as prepared")
        form.addRow("Prepared", self.prepared_check)

        self.source_hint_label = QLabel()
        self.source_hint_label.setWordWrap(True)
        self.source_hint_label.setStyleSheet("color: #777; font-size: 11px;")
        form.addRow(self.source_hint_label)

        self.source_spells_edit = QPlainTextEdit()
        self.source_spells_edit.setPlaceholderText("One spell per line")
        form.addRow("Spells", self.source_spells_edit)

        self._update_source_hint()
        self._apply_initial_state()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _build_combo(self, options: Iterable[str]) -> QComboBox:
        combo = QComboBox()
        combo.addItems(list(options))
        combo.setEditable(True)
        return combo

    def _selected_source_type(self) -> str:
        index = self.source_type_combo.currentIndex()
        value = self.source_type_combo.itemData(index, Qt.ItemDataRole.UserRole)
        if isinstance(value, str) and value:
            return value
        return self.source_type_combo.currentText().strip().lower()

    def _update_source_hint(self) -> None:
        source_type = self._selected_source_type()
        is_custom = source_type == "custom_source"
        if is_custom:
            self.source_hint_label.setText(
                "Custom sources capture homebrew or temporary effects. List every spell granted below."
            )
        else:
            self.source_hint_label.setText(
                "Standard sources should list the spells they grant. Future builds will auto-fill "
                "official sources based on this metadata."
            )
        self.source_spells_edit.setEnabled(True)

    def _validate_and_accept(self) -> None:
        source_name = self.source_name_edit.text().strip()
        if not source_name:
            QMessageBox.warning(self, "Missing Source", "Please enter the name of the source granting these spells.")
            return
        if not self._collect_source_spells():
            QMessageBox.warning(self, "Missing Spells", "Please list at least one spell provided by the source.")
            return
        self.accept()

    def _collect_source_spells(self) -> List[str]:
        return [line.strip() for line in self.source_spells_edit.toPlainText().splitlines() if line.strip()]

    def to_entries(self) -> List[SpellAccessEntry]:
        spells = self._collect_source_spells()
        category = self.source_category_combo.currentText().strip()
        ability = self.source_ability_combo.currentText().strip().upper() or None
        source_type_value = self._selected_source_type() or self.source_type_combo.currentText().strip()
        source_name = self.source_name_edit.text().strip()
        source_label = f"{self.source_type_combo.currentText().strip()} - {source_name}".strip()
        prepared_flag = self.prepared_check.isChecked()
        return [
            SpellAccessEntry(
                spell_name=name,
                source=source_label,
                category=category,
                prepared=prepared_flag,
                source_type=source_type_value,
                source_id=source_name,
                ability=ability,
            )
            for name in spells
        ]

    def descriptor(self) -> dict:
        source_type_value = self._selected_source_type() or self.source_type_combo.currentText().strip()
        source_name = self.source_name_edit.text().strip()
        display_label = self.source_type_combo.currentText().strip()
        return {
            "source_type": source_type_value,
            "source_name": source_name,
            "label": f"{display_label} - {source_name}".strip(),
            "ability": self.source_ability_combo.currentText().strip().upper() or None,
            "category": self.source_category_combo.currentText().strip(),
            "prepared": self.prepared_check.isChecked(),
        }

    def _apply_initial_state(self) -> None:
        if not self._initial_source:
            if self._initial_spells:
                self.source_spells_edit.setPlainText("\n".join(self._initial_spells))
            return
        source_type = self._initial_source.get("source_type")
        if source_type:
            index = self.source_type_combo.findData(source_type)
            if index >= 0:
                self.source_type_combo.setCurrentIndex(index)
            else:
                self.source_type_combo.setEditText(source_type.title())
        source_name = self._initial_source.get("source_name") or self._initial_source.get("source_id")
        if source_name:
            self.source_name_edit.setText(str(source_name))
        ability = self._initial_source.get("ability")
        if ability:
            index = self.source_ability_combo.findText(str(ability).upper())
            if index >= 0:
                self.source_ability_combo.setCurrentIndex(index)
            else:
                self.source_ability_combo.setEditText(str(ability).upper())
        category = self._initial_source.get("category")
        if category:
            index = self.source_category_combo.findText(str(category))
            if index >= 0:
                self.source_category_combo.setCurrentIndex(index)
            else:
                self.source_category_combo.setEditText(str(category))
        prepared = self._initial_source.get("prepared")
        if prepared is not None:
            self.prepared_check.setChecked(bool(prepared))
        spells = self._initial_spells or self._initial_source.get("spells")
        if spells:
            self.source_spells_edit.setPlainText("\n".join(spells))


__all__ = ["SpellSourceDialog"]
