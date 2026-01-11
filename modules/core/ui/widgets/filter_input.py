"""Filter builder widget with inline completion and chips."""

from __future__ import annotations

from typing import List

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class FilterInputWidget(QWidget):
    """Lightweight filter builder with chip UI and manual auto-complete."""

    filterAdded = Signal(str, str)
    filterRemoved = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.available_labels = {
            "name": [],
            "level": [str(i) for i in range(1, 10)],
            "school": [],
            "range": [],
            "casting_time": [],
            "duration": [],
            "components": ["V", "S", "M"],
        }
        self.current_phase = "label"
        self.current_label = ""
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        input_row = QHBoxLayout()
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Type filter (e.g., level: 3)")
        input_row.addWidget(self.input_line)
        self.completion_hint = QLabel()
        self.completion_hint.setObjectName("filterCompletionHint")
        self.completion_hint.setStyleSheet("color: #9aa0aa; font-style: italic;")
        input_row.addWidget(self.completion_hint)
        input_row.setStretch(0, 1)
        input_row.setStretch(1, 0)
        layout.addLayout(input_row)

        self.active_filters_frame = QFrame()
        self.active_filters_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.active_filters_layout = QHBoxLayout(self.active_filters_frame)
        self.active_filters_layout.addStretch()
        layout.addWidget(self.active_filters_frame)

        self._current_suggestions: List[str] = []
        self.input_line.installEventFilter(self)

        self.input_line.textEdited.connect(self.on_text_edited)
        self.input_line.returnPressed.connect(self.on_return_pressed)
        self._process_input_text(self.input_line.text())

    def on_text_edited(self, text: str) -> None:
        self._process_input_text(text)

    def _process_input_text(self, text: str) -> None:
        text = text or ""
        prefix = ""
        suggestions: List[str] = []
        if ':' in text:
            label_part, value_part = text.split(':', 1)
            label_part = label_part.strip()
            value_part = value_part.strip()
            if label_part in self.available_labels:
                self.current_phase = "value"
                self.current_label = label_part
                prefix = value_part
                if value_part:
                    options = self.available_labels[label_part]
                    suggestions = [
                        s for s in options if s.lower().startswith(value_part.lower())
                    ]
            else:
                self.current_phase = "label"
                self.current_label = ""
                prefix = label_part
                if label_part:
                    suggestions = [
                        lbl for lbl in self.available_labels.keys()
                        if lbl.lower().startswith(label_part.lower())
                    ]
        else:
            fragment = text.strip()
            self.current_phase = "label"
            self.current_label = ""
            prefix = fragment
            if fragment:
                suggestions = [
                    lbl for lbl in self.available_labels.keys()
                    if lbl.lower().startswith(fragment.lower())
                ]
        self.update_completer(suggestions)

        if suggestions:
            lcp = self._longest_common_prefix(suggestions)
            if self.current_phase == "value" and self.current_label:
                completion_base = lcp if lcp and len(lcp) >= len(prefix) else prefix
                preview = f"{self.current_label}: {completion_base or suggestions[0]}"
            else:
                completion_base = lcp if lcp and len(lcp) >= len(prefix) else (prefix or "")
                preview = completion_base or suggestions[0]
            self.completion_hint.setText(preview)
        else:
            self.completion_hint.clear()

    def update_completer(self, suggestions: List[str]) -> None:
        self._current_suggestions = suggestions

    def eventFilter(self, obj, event):  # noqa: N802  (Qt naming)
        if event.type() == QEvent.Type.KeyPress and obj is self.input_line:
            tab_keys = {Qt.Key.Key_Tab}
            alt_tab = getattr(Qt.Key, "Tab", None)
            if alt_tab is not None:
                tab_keys.add(alt_tab)
            if event.key() in tab_keys and not event.modifiers():
                if self._apply_tab_completion():
                    return True
        return super().eventFilter(obj, event)

    def _apply_tab_completion(self) -> bool:
        if not self._current_suggestions:
            return True

        text = self.input_line.text()
        suggestion_count = len(self._current_suggestions)
        lcp = self._longest_common_prefix(self._current_suggestions)

        if self.current_phase == "label":
            fragment = text.strip()
            if suggestion_count > 1 and lcp and fragment == lcp:
                return True

            if suggestion_count == 1:
                chosen = self._current_suggestions[0]
                new_text = f"{chosen}: "
                self.input_line.setText(new_text)
                self.input_line.setCursorPosition(len(new_text))
                self.current_phase = "value"
                self.current_label = chosen
                self._process_input_text(new_text)
                return True

            if not lcp:
                return True

            if fragment and lcp.lower().startswith(fragment.lower()) and fragment == lcp:
                return True

            new_text = lcp
            self.input_line.setText(new_text)
            self.input_line.setCursorPosition(len(new_text))
            self._process_input_text(new_text)
            return True

        label_part = self.current_label or text.split(':', 1)[0].strip()
        value_fragment = ""
        if ':' in text:
            value_fragment = text.split(':', 1)[1].strip()

        if suggestion_count > 1 and lcp and value_fragment == lcp:
            return True

        completion = self._current_suggestions[0] if suggestion_count == 1 else lcp
        if not completion:
            return True

        new_text = f"{label_part}: {completion}"
        self.input_line.setText(new_text)
        self.input_line.setCursorPosition(len(new_text))
        self._process_input_text(new_text)
        return True

    @staticmethod
    def _longest_common_prefix(entries: List[str]) -> str:
        if not entries:
            return ""
        prefix = entries[0]
        for entry in entries[1:]:
            while not entry.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    return ""
        return prefix

    def on_return_pressed(self) -> None:
        text = self.input_line.text().strip()
        if ':' in text:
            label, value = text.split(':', 1)
            label = label.strip()
            value = value.strip()
            if label and value:
                self.add_filter_chip(label, value)
                self.filterAdded.emit(label, value)
                self.input_line.clear()
                self.current_phase = "label"
                self.current_label = ""
                self._process_input_text("")

    def add_filter_chip(self, label: str, value: str) -> None:
        chip_text = f"{label}: {value}"
        chip = QPushButton(chip_text)
        chip.setProperty("filter_label", label)
        chip.setProperty("filter_value", value)
        chip.setCheckable(False)
        chip.setStyleSheet(
            "QPushButton {border: 1px solid gray; border-radius: 5px; padding: 2px; background-color: lightgray;}"
        )
        chip.clicked.connect(lambda: self.remove_chip(chip))
        self.active_filters_layout.insertWidget(self.active_filters_layout.count() - 1, chip)

    def remove_chip(self, chip: QPushButton) -> None:
        label = chip.property("filter_label")
        value = chip.property("filter_value")
        chip.deleteLater()
        self.filterRemoved.emit(label, value)


__all__ = ["FilterInputWidget"]
