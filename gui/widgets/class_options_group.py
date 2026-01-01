"""Widget for selecting class-specific option groups (invocations, boons, etc.)."""

from __future__ import annotations

from typing import Dict, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from services.class_options.models import ClassOptionGroup, ClassOptionSnapshot


class ClassOptionsGroup(QGroupBox):
    """Displays checkbox lists for each available class option group."""

    selectionChanged = Signal(str, list)

    # requestPick is emitted for picker-based groups (e.g. invocations).
    requestPick = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__("Class Options", parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(12)

        self._container = QFrame()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(10)
        layout.addWidget(self._container)
        layout.addStretch()

        self._group_widgets: Dict[str, QListWidget] = {}
        self._group_status_labels: Dict[str, QLabel] = {}
        self._group_defs: Dict[str, ClassOptionGroup] = {}
        self._snapshot: ClassOptionSnapshot | None = None

        self._picker_value_labels: Dict[str, QLabel] = {}
        self._picker_limits: Dict[str, int] = {}

    def set_snapshot(self, snapshot: ClassOptionSnapshot | None) -> None:
        self._snapshot = snapshot
        self._group_defs = {group.key: group for group in snapshot.groups} if snapshot else {}
        self._rebuild(snapshot)

    def current_selections(self) -> Dict[str, List[str]]:
        selections: Dict[str, List[str]] = {}
        for key, widget in self._group_widgets.items():
            values = self._checked_values(widget)
            if values:
                selections[key] = values
        if self._snapshot:
            for key, values in self._snapshot.selections.items():
                selections.setdefault(key, list(values))
        return selections

    def set_group_selection(self, key: str, values: List[str]) -> None:
        """Update a group's selected values (used by picker-driven groups)."""

        if not self._snapshot:
            return
        limit = max(0, int(self._picker_limits.get(key, 0)))
        filtered = [value for value in values if value]
        if limit:
            filtered = filtered[:limit]
        self._snapshot = ClassOptionSnapshot(groups=self._snapshot.groups, selections={**self._snapshot.selections, key: filtered})
        label = self._picker_value_labels.get(key)
        if label is not None:
            label.setText(", ".join(filtered) if filtered else "None")
        self._update_group_status(key)
        self.selectionChanged.emit(key, list(filtered))

    # --- Internal helpers ---------------------------------------------
    def _rebuild(self, snapshot: ClassOptionSnapshot | None) -> None:
        self._clear_layout(self._container_layout)
        self._group_widgets.clear()
        self._group_status_labels.clear()
        self._picker_value_labels.clear()
        self._picker_limits.clear()
        if not snapshot or not snapshot.groups:
            placeholder = QLabel("No class-specific options are currently available.")
            placeholder.setWordWrap(True)
            placeholder.setStyleSheet("color: #777777;")
            self._container_layout.addWidget(placeholder)
            self._container_layout.addStretch()
            return
        for group in snapshot.groups:
            frame = self._build_group_widget(group, snapshot)
            self._container_layout.addWidget(frame)
        self._container_layout.addStretch()

    def _build_group_widget(self, group: ClassOptionGroup, snapshot: ClassOptionSnapshot) -> QFrame:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title = QLabel(f"{group.label} (pick {group.max_choices})")
        title.setWordWrap(True)
        layout.addWidget(title)

        helper_lines: List[str] = []
        if group.helper_text:
            helper_lines.append(group.helper_text)
        helper_lines.append(f"Minimum Level: {group.min_level}")
        helper = QLabel("\n".join(helper_lines))
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #7a7a7a;")
        layout.addWidget(helper)

        status = QLabel()
        status.setStyleSheet("color: #5f6b7c;")
        layout.addWidget(status)
        self._group_status_labels[group.key] = status
        self._group_defs[group.key] = group

        # Invocations can be a very long list; use a searchable picker UX.
        if "invocation" in group.key.lower():
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            value_label = QLabel()
            value_label.setWordWrap(True)
            value_label.setStyleSheet("color: #0f172a;")
            stored = snapshot.selections.get(group.key, []) or []
            value_label.setText(", ".join(stored) if stored else "None")
            button = QPushButton("Choose…")
            button.clicked.connect(lambda _checked=False, key=group.key: self.requestPick.emit(key))
            row.addWidget(value_label, 1)
            row.addWidget(button)
            layout.addLayout(row)
            self._picker_value_labels[group.key] = value_label
            self._picker_limits[group.key] = int(group.max_choices)
            self._update_group_status(group.key)
            return frame

        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        stored = snapshot.selections.get(group.key, [])
        for choice in group.choices:
            item = QListWidgetItem(choice.label)
            item.setData(Qt.ItemDataRole.UserRole, choice.value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if choice.description:
                item.setToolTip(choice.description)
            checked = choice.value in stored
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            list_widget.addItem(item)
        list_widget.itemChanged.connect(
            lambda item, key=group.key, widget=list_widget, limit=group.max_choices: self._on_item_changed(
                key, widget, limit, item
            )
        )
        self._group_widgets[group.key] = list_widget
        self._update_group_status(group.key)
        layout.addWidget(list_widget)
        return frame

    def _on_item_changed(
        self,
        key: str,
        widget: QListWidget,
        max_choices: int,
        item: QListWidgetItem,
    ) -> None:
        max_allowed = max(0, max_choices)
        if max_allowed == 0:
            widget.blockSignals(True)
            item.setCheckState(Qt.CheckState.Unchecked)
            widget.blockSignals(False)
            return
        values = self._checked_values(widget)
        if len(values) > max_allowed:
            widget.blockSignals(True)
            item.setCheckState(Qt.CheckState.Unchecked)
            widget.blockSignals(False)
            return
        self._update_group_status(key)
        self.selectionChanged.emit(key, values)

    def selection_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for key, widget in self._group_widgets.items():
            counts[key] = len(self._checked_values(widget))
        return counts

    def _update_group_status(self, key: str) -> None:
        label = self._group_status_labels.get(key)
        group = self._group_defs.get(key)
        if not label or not group:
            return
        if key in self._picker_value_labels and self._snapshot:
            count = len(self._snapshot.selections.get(key, []) or [])
            label.setText(f"Selected {count} / {group.max_choices}")
            return
        widget = self._group_widgets.get(key)
        if not widget:
            return
        count = len(self._checked_values(widget))
        label.setText(f"Selected {count} / {group.max_choices}")

    @staticmethod
    def _checked_values(widget: QListWidget) -> List[str]:
        values: List[str] = []
        for index in range(widget.count()):
            item = widget.item(index)
            if item.checkState() != Qt.CheckState.Checked:
                continue
            value = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(value, str) and value not in values:
                values.append(value)
        return values

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            child = layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.deleteLater()
            nested = child.layout()
            if nested:
                ClassOptionsGroup._clear_layout(nested)  # type: ignore[arg-type]


__all__ = ["ClassOptionsGroup"]
