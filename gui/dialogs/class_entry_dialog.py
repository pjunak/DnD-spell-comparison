"""Modal dialog for adding or editing a single class progression entry."""

from __future__ import annotations

from typing import Dict, List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QMessageBox,
    QPushButton,
    QWidget,
)

from modules.characters.model import ClassProgression
from services.class_options import CLASS_NAME_OPTIONS, subclass_options_for
from modules.compendium.service import Compendium


def _load_compendium() -> Compendium | None:
    try:
        return Compendium.load()
    except Exception:
        return None


def _class_name_options(compendium: Compendium | None) -> List[str]:
    if not compendium:
        return list(CLASS_NAME_OPTIONS)
    names: List[str] = []
    for record in compendium.records("classes"):
        name = record.get("name") if isinstance(record, dict) else None
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    if names:
        return sorted(dict.fromkeys(names), key=lambda value: value.lower())
    return list(CLASS_NAME_OPTIONS)


def _subclass_name_options(compendium: Compendium | None, class_name: str) -> List[str]:
    if not compendium:
        return subclass_options_for(class_name)
    klass = compendium.class_record(class_name)
    if not klass:
        return subclass_options_for(class_name)
    subs = klass.get("subclasses")
    if not isinstance(subs, list):
        return subclass_options_for(class_name)
    result: List[str] = []
    for entry in subs:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if isinstance(name, str) and name.strip():
            result.append(name.strip())
    if result:
        return sorted(dict.fromkeys(result), key=lambda value: value.lower())
    return subclass_options_for(class_name)


class ClassEntryDialog(QDialog):
    """Dialog that captures class, subclass, and level values with guided inputs."""

    def __init__(
        self,
        existing: ClassProgression | None = None,
        max_assignable_level: int = 20,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Class Entry")
        self.resize(520, 360)
        self._suppress_subclass_popup = True
        self._max_assignable_level = max(1, int(max_assignable_level or 1))
        initial_level = existing.level if existing else 1
        self._selected_level = max(1, min(self._max_assignable_level, initial_level))
        self._level_group = QButtonGroup(self)
        self._level_group.setExclusive(True)
        self._level_buttons: Dict[int, QPushButton] = {}

        layout = QFormLayout(self)
        layout.setHorizontalSpacing(16)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self._compendium = _load_compendium()

        self.class_combo = QComboBox()
        self._configure_combo(self.class_combo, allow_blank=False)
        self.class_combo.addItems(_class_name_options(self._compendium))
        if existing:
            self.class_combo.setCurrentText(existing.name)
        layout.addRow("Class", self.class_combo)

        self.subclass_combo = QComboBox()
        self._configure_combo(self.subclass_combo, allow_blank=True)
        layout.addRow("Subclass", self.subclass_combo)
        self._populate_subclasses(self.class_combo.currentText())
        if existing and existing.subclass:
            self.subclass_combo.setCurrentText(existing.subclass)
        self.class_combo.currentTextChanged.connect(self._on_class_changed)

        level_box = self._build_level_selector()
        layout.addRow("Level", level_box)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
        self._suppress_subclass_popup = False
        self._update_level_buttons()

    def _configure_combo(self, combo: QComboBox, *, allow_blank: bool) -> None:
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        completer = combo.completer()
        if completer:
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
        line_edit = combo.lineEdit()
        if line_edit:
            line_edit.editingFinished.connect(
                lambda combo=combo, allow_blank=allow_blank: self._enforce_combo_value(combo, allow_blank)
            )

    def _on_class_changed(self, text: str) -> None:
        previous = self.subclass_combo.currentText().strip()
        options = self._populate_subclasses(text)
        if previous and previous in options:
            self.subclass_combo.setCurrentText(previous)
        else:
            self.subclass_combo.setCurrentIndex(0)
        self._maybe_open_subclass_popup(options)

    def _populate_subclasses(self, class_name: str) -> list[str]:
        choices = [""] + _subclass_name_options(self._compendium, class_name)
        self.subclass_combo.blockSignals(True)
        self.subclass_combo.clear()
        self.subclass_combo.addItems(choices)
        self.subclass_combo.blockSignals(False)
        return choices

    def _maybe_open_subclass_popup(self, options: list[str]) -> None:
        if self._suppress_subclass_popup:
            return
        if len(options) <= 1:
            return
        if not self.isVisible():
            return
        QTimer.singleShot(0, self.subclass_combo.showPopup)

    def _build_level_selector(self) -> QGroupBox:
        box = QGroupBox("Select Level")
        grid = QGridLayout(box)
        grid.setSpacing(6)
        for level in range(1, self._max_assignable_level + 1):
            button = QPushButton(str(level), box)
            button.setCheckable(True)
            button.clicked.connect(lambda _checked, value=level: self._set_selected_level(value))
            self._level_group.addButton(button, level)
            self._level_buttons[level] = button
            row = (level - 1) // 5
            column = (level - 1) % 5
            grid.addWidget(button, row, column)
        return box

    def _set_selected_level(self, level: int) -> None:
        if level > self._max_assignable_level:
            return
        self._selected_level = level
        self._update_level_buttons()

    def _update_level_buttons(self) -> None:
        allowed = max(1, self._max_assignable_level)
        if self._selected_level > allowed:
            self._selected_level = allowed
        for level, button in self._level_buttons.items():
            button.blockSignals(True)
            button.setEnabled(level <= allowed)
            button.setChecked(level == self._selected_level)
            button.blockSignals(False)

    def _enforce_combo_value(self, combo: QComboBox, allow_blank: bool) -> None:
        text = combo.currentText().strip().lower()
        for index in range(combo.count()):
            candidate = combo.itemText(index).strip().lower()
            if candidate == text:
                combo.setCurrentIndex(index)
                return
        if allow_blank and combo.count():
            combo.setCurrentIndex(0)
        elif combo.count():
            combo.setCurrentIndex(0)

    def _validate_and_accept(self) -> None:
        if not self._value_in_combo(self.class_combo):
            QMessageBox.warning(self, "Missing Class", "Please choose a class from the list.")
            return
        self.accept()

    @staticmethod
    def _value_in_combo(combo: QComboBox) -> bool:
        needle = combo.currentText().strip().lower()
        for index in range(combo.count()):
            if combo.itemText(index).strip().lower() == needle:
                return True
        return False

    def to_progression(self) -> ClassProgression:
        return ClassProgression(
            name=self.class_combo.currentText().strip(),
            level=self._selected_level,
            subclass=self.subclass_combo.currentText().strip() or None,
        )


__all__ = ["ClassEntryDialog"]
