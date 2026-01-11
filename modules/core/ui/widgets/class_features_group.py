"""Widget summarising active class/subclass features and related options."""

from __future__ import annotations

from typing import Dict, Mapping

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QLabel,
    QToolButton,
    QVBoxLayout,
)

from modules.dnd24_mechanics.character_rules import CharacterRuleSnapshot, FeatureOptionGroup


class ClassFeaturesGroup(QGroupBox):
    """Displays derived class features and creates controls for feature options."""

    selectionChanged = Signal(str, str)
    sectionCollapsed = Signal(str)
    sectionExpanded = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__("Class & Subclass Features", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(12)

        self._feature_frame = QFrame()
        self._feature_layout = QVBoxLayout(self._feature_frame)
        self._feature_layout.setContentsMargins(0, 0, 0, 0)
        self._feature_layout.setSpacing(4)
        layout.addWidget(self._feature_frame)

        self._options_frame = QFrame()
        self._options_layout = QVBoxLayout(self._options_frame)
        self._options_layout.setContentsMargins(0, 0, 0, 0)
        self._options_layout.setSpacing(8)
        layout.addWidget(self._options_frame)

        layout.addStretch()
        self._option_controls: Dict[str, QComboBox] = {}
        self._snapshot: CharacterRuleSnapshot | None = None
        self._collapse_states: Dict[str, bool] = {}

    def set_snapshot(self, snapshot: CharacterRuleSnapshot) -> None:
        self._snapshot = snapshot
        self._rebuild_feature_section(snapshot)
        self._rebuild_options(snapshot)

    def set_collapse_states(self, states: Mapping[str, bool]) -> None:
        self._collapse_states = {str(key): bool(value) for key, value in states.items() if key}
        if self._snapshot:
            self._rebuild_feature_section(self._snapshot)

    def collapse_states(self) -> Dict[str, bool]:
        return dict(self._collapse_states)

    def current_selections(self) -> Dict[str, str]:
        selections: Dict[str, str] = {}
        for key, combo in self._option_controls.items():
            value = combo.currentData()
            selections[key] = str(value if value is not None else combo.currentText())
        if self._snapshot:
            selections.update(
                {key: value for key, value in self._snapshot.selections.items() if key not in selections}
            )
        return selections

    # --- Private helpers -------------------------------------------------
    def _rebuild_feature_section(self, snapshot: CharacterRuleSnapshot) -> None:
        self._clear_layout(self._feature_layout)
        features = snapshot.features
        if not features:
            placeholder = QLabel("No class or subclass features are currently active.")
            placeholder.setWordWrap(True)
            self._feature_layout.addWidget(placeholder)
            self._feature_layout.addStretch()
            return
        for feature in features:
            self._feature_layout.addWidget(self._build_feature_panel(feature))
        self._feature_layout.addStretch()

    def _build_feature_panel(self, feature) -> QFrame:
        container = QFrame()
        inner_layout = QVBoxLayout(container)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(4)

        header = QToolButton()
        header.setCheckable(True)
        key = getattr(feature, "key", feature.label)
        is_expanded = self._collapse_states.get(key, True)
        header.setChecked(is_expanded)
        header.setText(feature.label)
        header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        header.setArrowType(Qt.ArrowType.DownArrow if is_expanded else Qt.ArrowType.RightArrow)
        header.clicked.connect(lambda _checked, key=key, btn=header: self._toggle_feature_section(key, btn))
        inner_layout.addWidget(header)

        description = QLabel(feature.description)
        description.setWordWrap(True)
        description.setStyleSheet("color: #c7c7c7;")
        description.setVisible(is_expanded)
        inner_layout.addWidget(description)

        container.setProperty("feature_key", key)
        container.setProperty("feature_desc", description)
        container.setProperty("feature_button", header)
        container.setProperty("is_expanded", is_expanded)
        return container

    def _toggle_feature_section(self, key: str, button: QToolButton) -> None:
        description = None
        container = None
        for index in range(self._feature_layout.count()):
            item = self._feature_layout.itemAt(index)
            widget = item.widget()
            if widget and widget.property("feature_key") == key:
                description = widget.property("feature_desc")
                container = widget
                break
        is_checked = button.isChecked()
        button.setArrowType(Qt.ArrowType.DownArrow if is_checked else Qt.ArrowType.RightArrow)
        if description:
            description.setVisible(is_checked)
        if container:
            container.setProperty("is_expanded", is_checked)
        self._collapse_states[key] = is_checked
        if is_checked:
            self.sectionExpanded.emit(key)
        else:
            self.sectionCollapsed.emit(key)

    def _rebuild_options(self, snapshot: CharacterRuleSnapshot) -> None:
        self._clear_layout(self._options_layout)
        self._option_controls.clear()
        option_groups = snapshot.option_groups
        if not option_groups:
            placeholder = QLabel("No configurable options for current features.")
            placeholder.setWordWrap(True)
            self._options_layout.addWidget(placeholder)
            self._options_layout.addStretch()
            return
        for group in option_groups:
            self._options_layout.addWidget(self._build_option_control(group, snapshot))
        self._options_layout.addStretch()

    def _build_option_control(self, group: FeatureOptionGroup, snapshot: CharacterRuleSnapshot) -> QFrame:
        container = QFrame()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label = QLabel(group.label)
        label.setWordWrap(True)
        layout.addWidget(label)
        if group.description:
            desc = QLabel(group.description)
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #909090;")
            layout.addWidget(desc)

        combo = QComboBox()
        for choice in group.choices:
            combo.addItem(choice.label, choice.value)
        selection = snapshot.selections.get(group.key)
        if selection is not None:
            index = combo.findData(selection)
            if index >= 0:
                combo.setCurrentIndex(index)
        combo.currentIndexChanged.connect(lambda _index, key=group.key: self._on_option_changed(key))
        layout.addWidget(combo)
        self._option_controls[group.key] = combo
        return container

    def _on_option_changed(self, key: str) -> None:
        combo = self._option_controls.get(key)
        if not combo:
            return
        value = combo.currentData()
        selection = str(value if value is not None else combo.currentText())
        self.selectionChanged.emit(key, selection)

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            child_layout = item.layout()
            if child_layout:
                ClassFeaturesGroup._clear_layout(child_layout)  # type: ignore[arg-type]
