"""Workspace window dedicated to character sheet management."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from character_sheet import CharacterSheet
from services.character_io import (
    load_character_package,
    load_character_pdf,
    save_character_package,
    save_character_pdf,
)
from services.character_library import CharacterLibrary, CharacterRecord
from services.modifiers import ModifierLoadError, ModifierStateService, ModifierStateSnapshot

from ..application_context import ApplicationContext
from ..dialogs import SpellcastingSettingsDialog
from ..resources import PROJECT_ROOT, get_app_icon
from ..widgets import FramelessWindow


class CharacterSheetHubWindow(FramelessWindow):
    """Provides centralized actions for managing multiple characters."""

    def __init__(self, app_context: ApplicationContext | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Character Sheet Workspace")
        self.setWindowIcon(get_app_icon())
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.resize(920, 640)

        self._app_context = app_context or ApplicationContext()
        self._modifier_service = ModifierStateService()
        self._library: CharacterLibrary = self._app_context.ensure_library()
        self._selected_character_id: str | None = None

        self._tile_container: QWidget | None = None
        self._tile_layout: QGridLayout | None = None
        self._selection_label: QLabel | None = None

        self._initialise_library_state()

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        header = QLabel("Manage each adventurer in one place")
        header.setStyleSheet("font-size: 26px; font-weight: 600;")
        layout.addWidget(header)

        body = QLabel(
            "Create new characters, import existing sheets, and switch between them with one click. "
            "The highlighted tile represents the character shared with other workspaces (spell graphs, etc.)."
        )
        body.setWordWrap(True)
        body.setStyleSheet("font-size: 14px; color: #475569;")
        layout.addWidget(body)

        controls = QHBoxLayout()
        controls.setSpacing(12)
        new_button = QPushButton("New Character…")
        new_button.clicked.connect(self._create_character)
        controls.addWidget(new_button)

        import_button = QPushButton("Import Character File…")
        import_button.clicked.connect(self._import_new_character)
        controls.addWidget(import_button)

        controls.addStretch()
        layout.addLayout(controls)

        self._tile_container = QWidget()
        self._tile_layout = QGridLayout(self._tile_container)
        self._tile_layout.setContentsMargins(0, 0, 0, 0)
        self._tile_layout.setHorizontalSpacing(20)
        self._tile_layout.setVerticalSpacing(20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self._tile_container)
        layout.addWidget(scroll, 1)

        self._selection_label = QLabel()
        self._selection_label.setWordWrap(True)
        self._selection_label.setStyleSheet(
            "font-size: 15px; color: #0f172a; background: #eef2ff; border-radius: 12px; padding: 14px; line-height: 1.6;"
        )
        layout.addWidget(self._selection_label)

        close_button = QPushButton("Close Workspace")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)

        self.setCentralWidget(central)
        self._refresh_tiles()

    def _initialise_library_state(self) -> None:
        records = self._library.list_records()
        if not records:
            self._selected_character_id = None
            self._library.set_active(None)
            self._clear_context_selection()
            return

        active_id = self._library.active_id or records[0].identifier
        self._set_active_record(active_id, broadcast=False, refresh_tiles=False)

    def _clear_context_selection(self) -> None:
        self._app_context.active_character_id = None
        self._app_context.character_sheet = None
        self._app_context.modifier_states = {}
        self._app_context.modifier_snapshot = None

    def _ensure_modifier_snapshot(self, states: Dict[str, bool]) -> ModifierStateSnapshot:
        try:
            if not self._modifier_service.definitions:
                return self._modifier_service.refresh(states)
            self._modifier_service.update_states(states)
            return ModifierStateSnapshot(self._modifier_service.definitions, self._modifier_service.states)
        except ModifierLoadError:
            return ModifierStateSnapshot([], dict(states))

    def _refresh_tiles(self) -> None:
        if not self._tile_layout or not self._tile_container:
            return
        while self._tile_layout.count():
            item = self._tile_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        records = self._library.list_records()
        if not records:
            self._selected_character_id = None
            placeholder = QLabel("No characters yet. Create or import one to get started.")
            placeholder.setStyleSheet("color: #475569; font-style: italic; padding: 24px;")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._tile_layout.addWidget(placeholder, 0, 0)
            self._update_selection_summary(None)
            return

        columns = 2 if len(records) > 1 else 1
        for index, record in enumerate(records):
            tile = _CharacterTile(record, selected=(record.identifier == self._selected_character_id))
            tile.request_select.connect(self._select_character)
            tile.request_edit.connect(self._edit_character)
            tile.request_import.connect(self._import_into_character)
            tile.request_export.connect(self._export_character)
            tile.request_delete.connect(self._delete_character)
            row = index // columns
            column = index % columns
            self._tile_layout.addWidget(tile, row, column)

        self._tile_layout.setRowStretch(self._tile_layout.rowCount(), 1)
        active = self._library.get(self._selected_character_id)
        self._update_selection_summary(active)

    def _update_selection_summary(self, record: CharacterRecord | None) -> None:
        if not self._selection_label:
            return
        if not record:
            self._selection_label.setText(
                "No active character selected. Create or import a character to power other workspaces."
            )
            return
        class_text = record.class_summary or "No class levels"
        text = (
            f"<b>Active Character:</b> {record.display_name}<br>"
            f"<b>Level:</b> {record.level} &nbsp;•&nbsp; <b>Classes:</b> {class_text}"
        )
        self._selection_label.setText(text)

    def _select_character(self, identifier: str) -> None:
        self._set_active_record(identifier, broadcast=True, refresh_tiles=True)

    def _set_active_record(self, identifier: str | None, *, broadcast: bool = False, refresh_tiles: bool = False) -> None:
        if not identifier:
            self._library.set_active(None)
            self._selected_character_id = None
            self._clear_context_selection()
            if refresh_tiles:
                self._refresh_tiles()
            else:
                self._update_selection_summary(None)
            if broadcast:
                self._notify_character_updated()
            return
        record = self._library.get(identifier)
        if not record:
            return
        self._library.set_active(identifier)
        self._selected_character_id = identifier
        self._app_context.active_character_id = identifier
        snapshot = self._ensure_modifier_snapshot(record.modifiers)
        self._app_context.character_sheet = record.sheet
        self._app_context.modifier_states = dict(snapshot.states)
        self._app_context.modifier_snapshot = snapshot
        if refresh_tiles:
            self._refresh_tiles()
        else:
            self._update_selection_summary(record)
        if broadcast:
            self._notify_character_updated()

    def _notify_character_updated(self) -> None:
        launcher = self.parent()
        callback = getattr(launcher, "notify_character_updated", None)
        if callable(callback):
            callback()

    def _create_character(self) -> None:
        snapshot = self._ensure_modifier_snapshot({})
        dialog = SpellcastingSettingsDialog(CharacterSheet(), snapshot, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        sheet, modifiers = dialog.get_result()
        record = self._library.create_record(sheet, modifiers)
        self._set_active_record(record.identifier, broadcast=True, refresh_tiles=True)
        QMessageBox.information(self, "Character Created", f"Added {record.display_name} to the roster.")

    def _edit_character(self, identifier: str | None = None) -> None:
        record = self._library.get(identifier or self._selected_character_id)
        if not record:
            return
        snapshot = self._ensure_modifier_snapshot(record.modifiers)
        dialog = SpellcastingSettingsDialog(record.sheet, snapshot, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        sheet, modifiers = dialog.get_result()
        self._library.update_record(record.identifier, sheet, modifiers)
        if record.identifier == self._selected_character_id:
            self._set_active_record(record.identifier, broadcast=True, refresh_tiles=True)
        else:
            self._refresh_tiles()
        QMessageBox.information(self, "Character Updated", f"Saved changes to {sheet.identity.name or 'Unnamed Adventurer'}.")

    def _import_new_character(self) -> None:
        self._import_character_from_file(target_record_id=None, create_new=True)

    def _import_into_character(self, identifier: str) -> None:
        self._import_character_from_file(target_record_id=identifier, create_new=False)

    def _import_character_from_file(self, *, target_record_id: str | None, create_new: bool) -> None:
        start_dir = str(PROJECT_ROOT)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Character Sheet",
            start_dir,
            "Character Files (*.json *.pdf);;JSON Files (*.json);;PDF Files (*.pdf);;All Files (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        try:
            if path.suffix.lower() == ".pdf":
                package = load_character_pdf(path)
            else:
                package = load_character_package(path)
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", f"Could not load character file:\n{exc}")
            return

        if create_new or not target_record_id:
            record = self._library.create_record(package.sheet, package.modifiers or {})
            self._set_active_record(record.identifier, broadcast=True, refresh_tiles=True)
            name = record.display_name
            QMessageBox.information(self, "Character Imported", f"Loaded {name} as a new entry.")
        else:
            record = self._library.get(target_record_id)
            if not record:
                return
            self._library.update_record(record.identifier, package.sheet, package.modifiers or {})
            if record.identifier == self._selected_character_id:
                self._set_active_record(record.identifier, broadcast=True, refresh_tiles=True)
            else:
                self._refresh_tiles()
            name = package.sheet.identity.name or "Unnamed Adventurer"
            QMessageBox.information(self, "Character Imported", f"Updated {name} from {path.name}.")

    def _export_character(self, identifier: str | None = None) -> None:
        record = self._library.get(identifier or self._selected_character_id)
        if not record:
            return
        start_dir = str(PROJECT_ROOT)
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Character Sheet",
            start_dir,
            "Character PDF (*.pdf);;Character JSON (*.json);;All Files (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        suffix = path.suffix.lower()
        if not suffix:
            if selected_filter and "pdf" in selected_filter.lower():
                path = path.with_suffix(".pdf")
            else:
                path = path.with_suffix(".json")
        elif suffix not in {".json", ".pdf"}:
            path = path.with_suffix(".json")

        if path.exists():
            response = QMessageBox.question(
                self,
                "Overwrite File?",
                f"{path} already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if response != QMessageBox.StandardButton.Yes:
                return

        try:
            if path.suffix.lower() == ".pdf":
                save_character_pdf(path, record.sheet, record.modifiers)
            else:
                save_character_package(path, record.sheet, record.modifiers)
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not write character file:\n{exc}")
            return

        QMessageBox.information(self, "Character Exported", f"Saved {record.display_name} to {path.name}.")

    def _delete_character(self, identifier: str) -> None:
        record = self._library.get(identifier)
        if not record:
            return
        response = QMessageBox.question(
            self,
            "Remove Character?",
            f"Delete {record.display_name}? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return

        self._library.delete_record(identifier)
        records = self._library.list_records()
        if not records:
            self._set_active_record(None, broadcast=True, refresh_tiles=True)
            QMessageBox.information(self, "Character Removed", f"Deleted {record.display_name} from the roster.")
            return

        new_active = self._library.active_id or records[0].identifier
        self._set_active_record(new_active, broadcast=True, refresh_tiles=True)
        QMessageBox.information(self, "Character Removed", f"Deleted {record.display_name} from the roster.")

    def on_character_data_updated(self) -> None:
        if not self._selected_character_id:
            return
        record = self._library.get(self._selected_character_id)
        if not record:
            return
        record.sheet = self._app_context.character_sheet
        record.modifiers = dict(self._app_context.modifier_states)
        self._library.save()
        self._refresh_tiles()


class _CharacterTile(QFrame):
    """Clickable card summarizing a single character."""

    request_select = Signal(str)
    request_edit = Signal(str)
    request_import = Signal(str)
    request_export = Signal(str)
    request_delete = Signal(str)

    def __init__(self, record: CharacterRecord, *, selected: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._record_id = record.identifier
        self.setObjectName("CharacterTile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(160)
        self.setStyleSheet(
            "#CharacterTile {"
            "  background-color: #f8fafc;"
            "  border: 2px solid transparent;"
            "  border-radius: 20px;"
            "  padding: 20px;"
            "}"
            "#CharacterTile[isSelected='true'] {"
            "  border-color: #2563eb;"
            "  background-color: #dbeafe;"
            "}"
        )
        self.setProperty("isSelected", bool(selected))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        name_label = QLabel(record.display_name)
        name_label.setStyleSheet("font-size: 20px; font-weight: 600; color: #0f172a;")
        layout.addWidget(name_label)

        level_label = QLabel(f"Level {record.level}")
        level_label.setStyleSheet("color: #475569; font-size: 14px;")
        layout.addWidget(level_label)

        class_label = QLabel(record.class_summary or "No class levels yet")
        class_label.setWordWrap(True)
        class_label.setStyleSheet("color: #334155; font-size: 13px;")
        layout.addWidget(class_label)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        for text, handler in (
            ("Import…", self.request_import),
            ("Export…", self.request_export),
            ("Delete", self.request_delete),
        ):
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, sig=handler: self._emit_action(sig))
            button_row.addWidget(btn)
        button_row.addStretch()
        layout.addLayout(button_row)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("isSelected", bool(selected))
        self.style().unpolish(self)
        self.style().polish(self)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.request_select.emit(self._record_id)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            # Double click opens the character editor.
            self.request_select.emit(self._record_id)
            self.request_edit.emit(self._record_id)
            return
        super().mouseDoubleClickEvent(event)

    def _emit_action(self, signal_obj) -> None:
        self.request_select.emit(self._record_id)
        signal_obj.emit(self._record_id)
