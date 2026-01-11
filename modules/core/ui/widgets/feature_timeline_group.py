"""Read-only feature timeline widget."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QToolButton, QVBoxLayout, QWidget

from modules.character_sheet.model import ClassProgression
from modules.dnd24_mechanics.character_rules import CharacterRuleSnapshot


def _normalise(text: str | None) -> str:
    return (text or "").strip().lower()


class FeatureTimelineGroup(QWidget):
    """Shows unlocked class/subclass features grouped by class level.

    This is intentionally read-only; edits happen via the option pickers elsewhere.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)

    def clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None:
                widget.setParent(None)

    def set_timeline(self, snapshot: CharacterRuleSnapshot | None, classes: Iterable[ClassProgression]) -> None:
        self.clear()
        if not snapshot:
            label = QLabel("No features to display yet.")
            label.setStyleSheet("color: #5f6b7c;")
            self._layout.addWidget(label)
            return

        class_entries = [entry for entry in classes if (entry.name or "").strip() and int(entry.level or 0) > 0]
        if not class_entries:
            label = QLabel("Add a class to see its feature timeline.")
            label.setStyleSheet("color: #5f6b7c;")
            self._layout.addWidget(label)
            return

        # Group active features by (class_name, subclass_name, min_level)
        by_key: Dict[Tuple[str, str], Dict[int, List[str]]] = defaultdict(lambda: defaultdict(list))
        for rule in snapshot.features:
            class_key = _normalise(rule.class_name)
            subclass_key = _normalise(rule.subclass_name)
            min_level = max(1, int(rule.min_level or 1))
            label = (rule.label or "").strip()
            if not label:
                continue
            by_key[(class_key, subclass_key)][min_level].append(label)

        for entry in class_entries:
            class_key = _normalise(entry.name)
            subclass_key = _normalise(entry.subclass)
            level_cap = max(1, int(entry.level))

            header_text = f"{entry.name.strip()} {level_cap}"
            subclass_text = (entry.subclass or "").strip()
            if subclass_text:
                header_text += f" ({subclass_text})"

            header = QToolButton()
            header.setText(header_text)
            header.setCheckable(True)
            header.setChecked(False)
            header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            header.setArrowType(Qt.ArrowType.RightArrow)

            body = QWidget()
            body_layout = QVBoxLayout(body)
            body_layout.setContentsMargins(12, 0, 0, 0)
            body_layout.setSpacing(4)
            body.setVisible(False)

            def toggle(checked: bool, *, btn=header, panel=body) -> None:
                panel.setVisible(checked)
                btn.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)

            header.toggled.connect(toggle)

            # Prefer subclass-specific buckets, but also include base-class buckets.
            buckets: Dict[int, List[str]] = defaultdict(list)
            for lvl, labels in by_key.get((class_key, ""), {}).items():
                buckets[lvl].extend(labels)
            if subclass_key:
                for lvl, labels in by_key.get((class_key, subclass_key), {}).items():
                    buckets[lvl].extend(labels)

            any_rows = False
            for lvl in range(1, level_cap + 1):
                labels = sorted(set(buckets.get(lvl, [])), key=lambda value: value.lower())
                if not labels:
                    continue
                any_rows = True
                row = QLabel(f"Level {lvl}: " + ", ".join(labels))
                row.setWordWrap(True)
                body_layout.addWidget(row)

            if not any_rows:
                empty = QLabel("No unlocked features recorded for this class yet.")
                empty.setStyleSheet("color: #5f6b7c;")
                empty.setWordWrap(True)
                body_layout.addWidget(empty)

            self._layout.addWidget(header)
            self._layout.addWidget(body)

        self._layout.addStretch(1)


__all__ = ["FeatureTimelineGroup"]
