"""Dialog for adding or editing character feats and narrative features."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QPlainTextEdit, QWidget

from character_sheet import FeatureEntry


class FeatEntryDialog(QDialog):
    """Collects feat metadata including name, source, and notes."""

    def __init__(self, parent: QWidget | None = None, *, existing: FeatureEntry | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Feat" if existing else "Add Feat")
        self.resize(420, 320)
        self._existing = existing

        layout = QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.name_edit = QLineEdit(existing.title if existing else "")
        layout.addRow("Feat / Feature", self.name_edit)

        self.source_edit = QLineEdit(existing.source if existing else "")
        layout.addRow("Source", self.source_edit)

        self.notes_edit = QPlainTextEdit(existing.description if existing else "")
        self.notes_edit.setPlaceholderText("Notes, benefits, requirements …")
        self.notes_edit.setMinimumHeight(120)
        layout.addRow("Notes", self.notes_edit)

        helper = QLabel("Name is required; source/notes help you remember prerequisites and benefits.")
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #5f6b7c; font-size: 12px;")
        layout.addRow(helper)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _validate_and_accept(self) -> None:
        if not self.name_edit.text().strip():
            self.name_edit.setFocus()
            self.name_edit.selectAll()
            return
        self.accept()

    def to_entry(self) -> FeatureEntry:
        return FeatureEntry(
            title=self.name_edit.text().strip(),
            source=self.source_edit.text().strip(),
            description=self.notes_edit.toPlainText().strip(),
        )


__all__ = ["FeatEntryDialog"]
