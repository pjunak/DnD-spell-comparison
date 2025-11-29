"""PySide6 GUI for browsing and plotting D&D spell damage distributions."""

import sys
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QCheckBox,
    QSplitter,
    QGroupBox,
    QSizePolicy,
    QFormLayout,
    QSpinBox,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QMessageBox,
    QPlainTextEdit,
    QToolBar,
    QToolButton,
    QMenu,
    QDialog,
    QDialogButtonBox,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QAction, QActionGroup, QBrush, QColor, QIcon
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set, Iterable
from database import (
    export_dataset_to_json,
    import_dataset,
    load_modifiers,
    load_spells,
    upsert_modifiers,
)
from database.defaults import get_default_modifier_definitions
import json
from backend import plotting  # integrate plotting functions
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar

PROJECT_ROOT = Path(__file__).resolve().parent
APP_ICON_PATH = PROJECT_ROOT / "Assets" / "app-icon.svg"
_APP_ICON_CACHE: Optional[QIcon] = None


def get_app_icon() -> QIcon:
    global _APP_ICON_CACHE
    if _APP_ICON_CACHE is not None:
        return _APP_ICON_CACHE

    icon = QIcon()
    if APP_ICON_PATH.exists():
        icon = QIcon(str(APP_ICON_PATH))

    if icon.isNull():
        fallback = QIcon.fromTheme("applications-games")
        if not fallback.isNull():
            icon = fallback

    _APP_ICON_CACHE = icon
    return _APP_ICON_CACHE

# --- Custom Widget for Filter Input with Auto-Completion and Active Filters ---
class FilterInputWidget(QWidget):
    """Lightweight filter builder with chip UI and manual auto-complete."""

    # Signal emitted when a new filter is added; carries tuple (label, value)
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
        self.current_phase = "label"  # "label" or "value"
        self.current_label = ""  # stores the chosen label
        self.init_ui()

    def init_ui(self):
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

        # Active filters area
        self.active_filters_frame = QFrame()
        self.active_filters_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.active_filters_layout = QHBoxLayout(self.active_filters_frame)
        self.active_filters_layout.addStretch()  # To push chips to left
        layout.addWidget(self.active_filters_frame)

        # Manual suggestion tracking (no popup)
        self._current_suggestions: List[str] = []
        self.input_line.installEventFilter(self)

        # Connect signals
        self.input_line.textEdited.connect(self.on_text_edited)
        self.input_line.returnPressed.connect(self.on_return_pressed)
        self._process_input_text(self.input_line.text())

    def on_text_edited(self, text):
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

    def update_completer(self, suggestions):
        self._current_suggestions = suggestions

    def eventFilter(self, obj, event):
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

        # Value phase handling
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

    def on_return_pressed(self):
        text = self.input_line.text().strip()
        # Expecting format "label: value"
        if ':' in text:
            label, value = text.split(':', 1)
            label = label.strip()
            value = value.strip()
            if label and value:
                # Emit filter and add chip.
                self.add_filter_chip(label, value)
                self.filterAdded.emit(label, value)
                # Clear input field and reset phase.
                self.input_line.clear()
                self.current_phase = "label"
                self.current_label = ""
                self._process_input_text("")

    def add_filter_chip(self, label, value):
        chip_text = f"{label}: {value}"
        chip = QPushButton(chip_text)
        chip.setProperty("filter_label", label)
        chip.setProperty("filter_value", value)
        chip.setCheckable(False)
        chip.setStyleSheet("QPushButton {border: 1px solid gray; border-radius: 5px; padding: 2px; background-color: lightgray;}")
        # When chip is clicked, remove it.
        chip.clicked.connect(lambda: self.remove_chip(chip))
        # Insert the chip before the stretch spacer.
        self.active_filters_layout.insertWidget(self.active_filters_layout.count()-1, chip)

    def remove_chip(self, chip):
        label = chip.property("filter_label")
        value = chip.property("filter_value")
        chip.deleteLater()
        self.filterRemoved.emit(label, value)


class CharacterDialog(QDialog):
    def __init__(self, settings: dict, modifier_states: dict, modifier_definitions: List[dict], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Character Settings")
        self._initial_settings = dict(settings)
        self._modifier_definitions = list(modifier_definitions)
        initial_states: Dict[str, bool] = {}
        for definition in self._modifier_definitions:
            label = definition.get("name")
            if not label:
                continue
            default_state = bool(modifier_states.get(label, definition.get("default_enabled", False)))
            initial_states[label] = default_state
        self._initial_modifiers = initial_states
        self._result_settings: Optional[Dict[str, int]] = None
        self._result_modifiers: Optional[Dict[str, bool]] = None

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.ability_spin = QSpinBox()
        self.ability_spin.setRange(1, 30)
        self.ability_spin.setValue(settings.get("ability_value", 10))
        form_layout.addRow("Ability Value:", self.ability_spin)

        self.additional_bonus_spin = QSpinBox()
        self.additional_bonus_spin.setRange(-10, 10)
        self.additional_bonus_spin.setValue(settings.get("additional_bonus", 0))
        form_layout.addRow("Additional Bonus:", self.additional_bonus_spin)

        self.proficiency_spin = QSpinBox()
        self.proficiency_spin.setRange(0, 10)
        self.proficiency_spin.setValue(settings.get("saving_throw_proficiency", 2))
        form_layout.addRow("Saving Throw Proficiency:", self.proficiency_spin)

        self.saving_bonus_spin = QSpinBox()
        self.saving_bonus_spin.setRange(-10, 10)
        self.saving_bonus_spin.setValue(settings.get("saving_throw_bonus", 0))
        form_layout.addRow("Saving Throw Bonus:", self.saving_bonus_spin)

        layout.addLayout(form_layout)

        modifiers_group = QGroupBox("Modifiers (Feats, Subclasses, etc.)")
        modifiers_layout = QVBoxLayout()
        self._modifier_checkboxes: Dict[str, QCheckBox] = {}

        grouped_definitions: Dict[str, List[dict]] = {}
        for definition in self._modifier_definitions:
            category_key = self._normalise_category(definition.get("category"))
            grouped_definitions.setdefault(category_key, []).append(definition)

        for category_key in self._sorted_categories(grouped_definitions.keys()):
            category_label = self._format_category_label(category_key)
            category_box = QGroupBox(category_label)
            category_box_layout = QVBoxLayout()
            definitions = sorted(
                grouped_definitions[category_key],
                key=lambda item: (
                    self._format_scope_label(str(item.get("scope") or "spell")),
                    str(item.get("name", "")).lower(),
                ),
            )
            for definition in definitions:
                label = definition.get("name")
                if not label:
                    continue
                checkbox = QCheckBox(label)
                checkbox.setChecked(self._initial_modifiers.get(label, False))
                scope_suffix = self._format_scope_label(str(definition.get("scope") or "spell"))
                checkbox.setAccessibleName(f"{label} ({scope_suffix})")
                tooltip = self._build_modifier_tooltip(definition)
                if tooltip:
                    checkbox.setToolTip(tooltip)
                category_box_layout.addWidget(checkbox)
                self._modifier_checkboxes[label] = checkbox
            category_box_layout.addStretch()
            category_box.setLayout(category_box_layout)
            modifiers_layout.addWidget(category_box)

        modifiers_layout.addStretch()
        modifiers_group.setLayout(modifiers_layout)
        layout.addWidget(modifiers_group)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        apply_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        apply_button.setText("Apply")
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self._on_apply)
        layout.addWidget(button_box)

    def _on_apply(self) -> None:
        self._result_settings = {
            "ability_value": self.ability_spin.value(),
            "additional_bonus": self.additional_bonus_spin.value(),
            "saving_throw_proficiency": self.proficiency_spin.value(),
            "saving_throw_bonus": self.saving_bonus_spin.value(),
        }
        self._result_modifiers = {
            label: checkbox.isChecked()
            for label, checkbox in self._modifier_checkboxes.items()
        }
        self.accept()

    def get_values(self) -> Tuple[Dict[str, int], Dict[str, bool]]:
        if self._result_settings is None or self._result_modifiers is None:
            return dict(self._initial_settings), dict(self._initial_modifiers)
        return dict(self._result_settings), dict(self._result_modifiers)

    @staticmethod
    def _format_scope_label(scope: str) -> str:
        scope_lower = scope.lower()
        if scope_lower == "spell":
            return "Spell Modifiers"
        if scope_lower == "character":
            return "Character Modifiers"
        return f"{scope_lower.title()} Modifiers"

    @staticmethod
    def _build_modifier_tooltip(definition: dict) -> str:
        lines: List[str] = []
        description = definition.get("description")
        if description:
            lines.append(str(description))
        applies_to = definition.get("applies_to") or []
        if applies_to:
            lines.append("Applies to:")
            for entry in applies_to:
                lines.append(f"  - {json.dumps(entry, ensure_ascii=False)}")
        effect_data = definition.get("effect_data")
        if effect_data:
            lines.append("Effect:")
            lines.append(json.dumps(effect_data, ensure_ascii=False, indent=2))
        return "\n".join(lines).strip()

    @staticmethod
    def _normalise_category(value) -> str:
        text = str((value or "")).strip().lower()
        if not text:
            return "misc"
        aliases = {
            "feat": "feat",
            "feats": "feat",
            "invocation": "invocation",
            "invocations": "invocation",
            "subclass": "subclass",
            "subclasses": "subclass",
            "specialization": "specialization",
            "specializations": "specialization",
            "specialisation": "specialization",
            "specialisations": "specialization",
            "boon": "boon",
            "boons": "boon",
            "general": "general",
            "misc": "misc",
        }
        if text in aliases:
            return aliases[text]
        if text.endswith("es"):
            return text[:-2] or "misc"
        if text.endswith("s"):
            return text[:-1] or "misc"
        return text

    @staticmethod
    def _format_category_label(category: str) -> str:
        labels = {
            "feat": "Feats",
            "invocation": "Invocations",
            "subclass": "Subclasses",
            "specialization": "Specializations",
            "boon": "Boons",
            "general": "General Enhancements",
            "misc": "Miscellaneous",
        }
        return labels.get(category, category.title())

    @staticmethod
    def _sorted_categories(keys: Iterable[str]) -> List[str]:
        order = {
            "feat": 10,
            "invocation": 20,
            "subclass": 30,
            "specialization": 40,
            "general": 50,
            "boon": 60,
            "misc": 70,
        }
        return sorted(keys, key=lambda key: (order.get(key, 999), key))


class GraphWindow(QMainWindow):
    """Wrapper window that embeds a matplotlib figure with toolbar controls."""

    def __init__(self, figure, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(get_app_icon())
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        central = QWidget()
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        self.canvas = FigureCanvas(figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        self.canvas.draw()

# --- Main Window Prototype with Filtering and Spell Tables ---
class MainWindow(QMainWindow):
    """Primary application window that hosts filters, tables, and plotting actions."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SpellGraphix")
        self.setWindowIcon(get_app_icon())
        self.resize(1300, 750)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        self.allow_edit_action: Optional[QAction] = None
        self._default_edit_triggers: Dict[str, QAbstractItemView.EditTrigger] = {}

        # Top: Filter Input Widget (embedded with the left table so it shares width)
        self.filter_input_widget = FilterInputWidget()
        self._active_filters = {}
        self.filter_input_widget.filterAdded.connect(self.on_filter_added)
        self.filter_input_widget.filterRemoved.connect(self.on_filter_removed)
        filter_size_policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.filter_input_widget.setSizePolicy(filter_size_policy)

        # Add dataset toolbar
        self._build_toolbar()

        # Main area split into two: Left for spells table, Right for settings and selected spells
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Left pane holds the filter widget and available spells stacked vertically
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        left_layout.addWidget(self.filter_input_widget)

        # Left Pane: Available Spells Table
        self.available_spells_table = QTableWidget()
        # 7 columns: Name, Level, School, Range, Casting Time, Duration, Components
        self.available_spells_table.setColumnCount(7)
        self.available_spells_table.setHorizontalHeaderLabels([
            "Name", "Level", "School", "Range", "Casting Time", "Duration", "Components"
        ])
        self.available_spells_table.setSortingEnabled(True)
        self.available_spells_table.horizontalHeader().setStretchLastSection(True)
        self.available_spells: List[dict] = []
        self.selected_spells: List[dict] = []
        self._selected_spell_keys: Set[str] = set()

        self.available_spells_table.setAlternatingRowColors(False)
        self.available_spells_table.setStyleSheet(
            "QTableWidget {"
            "background-color: #1b1f27;"
            "color: #f0f0f0;"
            "gridline-color: #2c313c;"
            "selection-background-color: #2d4f7c;"
            "selection-color: #ffffff;"
            "}"
        )

        self.selected_spells_table_style = (
            "QTableWidget {"
            "background-color: #1b1f27;"
            "color: #f0f0f0;"
            "gridline-color: #2c313c;"
            "selection-background-color: #2d4f7c;"
            "selection-color: #ffffff;"
            "}"
        )

        self._available_row_colors = {
            "even": QColor("#1b1f27"),
            "odd": QColor("#222733"),
            "highlight": QColor("#2d4f7c"),
            "text": QColor("#f0f0f0"),
        }
        self._selected_row_colors = {
            "even": QColor("#1b1f27"),
            "odd": QColor("#222733"),
            "highlight": QColor("#2d4f7c"),
            "text": QColor("#f0f0f0"),
        }

        self.character_settings = {
            "ability_value": 10,
            "additional_bonus": 0,
            "saving_throw_proficiency": 2,
            "saving_throw_bonus": 0,
        }
        self._character_modifier_definitions: List[dict] = []
        self.character_modifiers: Dict[str, bool] = {}
        self._graph_windows: List[GraphWindow] = []
        self._dataset_mode = "spells"
        self._spells_only: List[dict] = []
        self._cantrips_only: List[dict] = []
        self._show_non_damage_spells = False

        left_layout.addWidget(self.available_spells_table, stretch=1)
        left_layout.setStretch(0, 0)
        left_layout.setStretch(1, 1)
        splitter.addWidget(left_widget)
        
        # Right Pane: Spellcasting Configuration, Modifiers, and Selected Spells
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Selected Spells Panel (Table)
        selected_label = QLabel("Selected Spells for Comparison:")
        right_layout.addWidget(selected_label)
        self.selected_spells_table = QTableWidget()
        self.selected_spells_table.setColumnCount(7)
        self.selected_spells_table.setHorizontalHeaderLabels([
            "Name", "Level", "School", "Range", "Casting Time", "Duration", "Components"
        ])
        self.selected_spells_table.setAlternatingRowColors(False)
        self.selected_spells_table.setStyleSheet(self.selected_spells_table_style)
        self.selected_spells_table.horizontalHeader().setStretchLastSection(True)
        self.selected_spells_table.resizeColumnsToContents()
        right_layout.addWidget(self.selected_spells_table)
        self._apply_table_edit_state()
        
        # Spell Details Panel
        details_group = QGroupBox("Spell Details")
        details_layout = QVBoxLayout()
        self.details_text = QPlainTextEdit()
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        details_group.setLayout(details_layout)
        right_layout.addWidget(details_group)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        
        # Bottom: Generate Graph Button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.generate_button = QPushButton("Generate Graph")
        bottom_layout.addWidget(self.generate_button)
        main_layout.addLayout(bottom_layout)
        
        # Load data
        self._reload_spells(show_errors=True)

        # Signal Connections:
        self.available_spells_table.cellDoubleClicked.connect(self.add_spell_to_selection)
        self.available_spells_table.cellClicked.connect(self.on_available_spell_clicked)
        self.selected_spells_table.cellDoubleClicked.connect(self.remove_spell_from_selection)
        self.generate_button.clicked.connect(self.on_generate)  # handle generate graph

    def _build_toolbar(self) -> None:
        """Constructs the main toolbar with Character, Options, and Database menus."""
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Character menu hosts configuration dialogs
        character_menu = QMenu("Character", self)
        configure_character_action = QAction("Configure Spellcasting...", self)
        configure_character_action.triggered.connect(self._open_character_dialog)
        character_menu.addAction(configure_character_action)

        character_button = QToolButton()
        character_button.setText("Character")
        character_button.setMenu(character_menu)
        character_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        character_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        toolbar.addWidget(character_button)

        toolbar.addSeparator()

        # Options menu (currently holds quick actions, future-safe for more entries)
        options_menu = QMenu("Options", self)

        dataset_group = QActionGroup(self)
        dataset_group.setExclusive(True)

        self.show_spells_action = QAction("Show Spells", self)
        self.show_spells_action.setCheckable(True)
        self.show_spells_action.setChecked(True)
        self.show_spells_action.triggered.connect(
            lambda checked, mode="spells": checked and self._set_dataset_mode(mode)
        )
        dataset_group.addAction(self.show_spells_action)
        options_menu.addAction(self.show_spells_action)

        self.show_cantrips_action = QAction("Show Cantrips", self)
        self.show_cantrips_action.setCheckable(True)
        self.show_cantrips_action.triggered.connect(
            lambda checked, mode="cantrips": checked and self._set_dataset_mode(mode)
        )
        dataset_group.addAction(self.show_cantrips_action)
        options_menu.addAction(self.show_cantrips_action)

        options_menu.addSeparator()

        self.show_non_damage_action = QAction("Show Non-Damaging Spells", self)
        self.show_non_damage_action.setCheckable(True)
        self.show_non_damage_action.setToolTip("Toggle visibility of spells without damage distributions")
        self.show_non_damage_action.toggled.connect(self._toggle_non_damage_visibility)
        options_menu.addAction(self.show_non_damage_action)

        options_menu.addSeparator()

        self.allow_edit_action = QAction("Allow Data Modification", self)
        self.allow_edit_action.setCheckable(True)
        self.allow_edit_action.setChecked(False)
        self.allow_edit_action.setToolTip("Toggle whether spell tables can be edited.")
        self.allow_edit_action.toggled.connect(self._apply_table_edit_state)
        options_menu.addAction(self.allow_edit_action)

        options_menu.addSeparator()

        clear_filters_action = QAction("Clear Filters", self)
        clear_filters_action.triggered.connect(self.clear_filters)
        options_menu.addAction(clear_filters_action)

        clear_selection_action = QAction("Clear Selections", self)
        clear_selection_action.triggered.connect(self.clear_selections)
        options_menu.addAction(clear_selection_action)

        options_button = QToolButton()
        options_button.setText("Options")
        options_button.setMenu(options_menu)
        options_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        options_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        toolbar.addWidget(options_button)

        # Database menu groups import/export actions for future expansion
        database_menu = QMenu("Database", self)

        import_action = QAction("Import Dataset", self)
        import_action.triggered.connect(self._action_import_dataset)
        database_menu.addAction(import_action)

        export_action = QAction("Export Dataset", self)
        export_action.triggered.connect(self._action_export_dataset)
        database_menu.addAction(export_action)

        database_button = QToolButton()
        database_button.setText("Database")
        database_button.setMenu(database_menu)
        database_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        database_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        toolbar.addWidget(database_button)

        self.main_toolbar = toolbar

    def _apply_table_edit_state(self, checked: bool | None = None) -> None:
        if not hasattr(self, "available_spells_table") or not hasattr(self, "selected_spells_table"):
            return
        if not self._default_edit_triggers:
            self._default_edit_triggers = {
                "available": self.available_spells_table.editTriggers(),
                "selected": self.selected_spells_table.editTriggers(),
            }
        allow_edits = bool(self.allow_edit_action and self.allow_edit_action.isChecked())
        if allow_edits:
            available_triggers = self._default_edit_triggers.get(
                "available", QAbstractItemView.EditTrigger.AllEditTriggers
            )
            selected_triggers = self._default_edit_triggers.get(
                "selected", QAbstractItemView.EditTrigger.AllEditTriggers
            )
        else:
            available_triggers = QAbstractItemView.EditTrigger.NoEditTriggers
            selected_triggers = QAbstractItemView.EditTrigger.NoEditTriggers
        self.available_spells_table.setEditTriggers(available_triggers)
        self.selected_spells_table.setEditTriggers(selected_triggers)

    def _open_character_dialog(self) -> None:
        """Opens the character configuration dialog and applies changes if accepted."""
        dialog = CharacterDialog(
            self.character_settings,
            self.character_modifiers,
            self._character_modifier_definitions,
            self,
        )
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            settings, modifiers = dialog.get_values()
            self.character_settings = settings
            self.character_modifiers = modifiers

    def _register_graph_window(self, window: GraphWindow) -> None:
        self._graph_windows.append(window)

        def _cleanup(_: object = None, *, ref=window) -> None:
            if ref in self._graph_windows:
                self._graph_windows.remove(ref)

        window.destroyed.connect(_cleanup)

    def _set_dataset_mode(self, mode: str, *, force: bool = False) -> None:
        """
        Switches between 'spells' and 'cantrips' datasets.

        Args:
            mode: 'spells' or 'cantrips'.
            force: If True, reloads even if mode hasn't changed.
        """
        if mode not in {"spells", "cantrips"}:
            return

        data_changed = force or mode != self._dataset_mode
        self._dataset_mode = mode

        if mode == "spells":
            dataset = list(self._spells_only)
            hide_level = False
        else:
            dataset = list(self._cantrips_only)
            hide_level = True

        if not data_changed and dataset == getattr(self, "available_spells", []):
            return

        self.available_spells = dataset

        if hasattr(self, "available_spells_table"):
            self.available_spells_table.setColumnHidden(1, hide_level)
        if hasattr(self, "selected_spells_table"):
            self.selected_spells_table.setColumnHidden(1, hide_level)

        self._populate_available_spells_table()
        self._reset_filter_options()
        self.filter_input_widget.input_line.clear()
        self.filter_input_widget.completion_hint.clear()
        self.clear_filters()
        self.clear_selections()
        self.details_text.clear()

        action = getattr(self, "show_spells_action", None)
        if action is not None:
            action.blockSignals(True)
            action.setChecked(mode == "spells")
            action.blockSignals(False)
        action = getattr(self, "show_cantrips_action", None)
        if action is not None:
            action.blockSignals(True)
            action.setChecked(mode == "cantrips")
            action.blockSignals(False)

    def _reload_spells(self, *, show_errors: bool) -> None:
        """Loads spells from the database and partitions them into spells and cantrips."""
        try:
            records = load_spells()
        except Exception as exc:
            if show_errors:
                QMessageBox.critical(self, "Database Error", f"Failed to load spells: {exc}")
            records = []

        spells_only = []
        cantrips_only = []
        for entry in records:
            level_value = entry.get("level", 0)
            if level_value in (None, "", 0):
                cantrips_only.append(entry)
            else:
                spells_only.append(entry)

        self._spells_only = spells_only
        self._cantrips_only = cantrips_only

        target_mode = self._dataset_mode if self._dataset_mode in {"spells", "cantrips"} else "spells"
        if target_mode == "spells" and not spells_only and cantrips_only:
            target_mode = "cantrips"
        self._set_dataset_mode(target_mode, force=True)
        self._refresh_character_modifiers()

    def _refresh_character_modifiers(self) -> None:
        """Loads character modifiers from DB, seeding defaults if necessary."""
        defaults = get_default_modifier_definitions()

        try:
            definitions = load_modifiers()
        except Exception as exc:
            QMessageBox.warning(self, "Modifier Load Failed", f"Could not load modifiers: {exc}")
            definitions = []

        if not definitions:
            try:
                if defaults:
                    upsert_modifiers(defaults)
                    definitions = load_modifiers()
            except Exception:
                definitions = []

        # Ensure the database stays in sync with the shipped defaults so new
        # modifiers/categories appear even on existing installations.
        if defaults:
            if self._sync_default_modifiers(definitions, defaults):
                try:
                    definitions = load_modifiers()
                except Exception:
                    # Fall back to defaults if reload fails after seeding.
                    definitions = list(defaults)

        if not definitions:
            definitions = list(defaults)

        definitions = sorted(
            definitions,
            key=lambda entry: (str(entry.get("scope") or "spell").lower(), str(entry.get("name", "")).lower()),
        )

        existing_states = dict(getattr(self, "character_modifiers", {}))
        resolved_states: Dict[str, bool] = {}
        for definition in definitions:
            name = definition.get("name")
            if not name:
                continue
            default_state = bool(definition.get("default_enabled", False))
            resolved_states[name] = existing_states.get(name, default_state)

        self._character_modifier_definitions = definitions
        self.character_modifiers = resolved_states

    def _toggle_non_damage_visibility(self, checked: bool) -> None:
        self._show_non_damage_spells = bool(checked)
        if not checked:
            self._remove_non_damage_from_selection()
        self._populate_available_spells_table()
        self.details_text.clear()

    def _remove_non_damage_from_selection(self) -> None:
        for row in range(len(self.selected_spells) - 1, -1, -1):
            spell = self.selected_spells[row]
            if plotting.extract_effect_params(spell) is None:
                self.remove_spell_from_selection(row, 0)

    @staticmethod
    def _sync_default_modifiers(existing: List[dict], defaults: List[dict]) -> bool:
        """Ensure missing or outdated default modifiers are written to the DB."""

        existing_map = {
            record.get("name"): record
            for record in existing
            if record.get("name")
        }

        to_upsert: List[dict] = []
        comparison_keys = (
            "category",
            "scope",
            "description",
            "applies_to",
            "effect_data",
            "default_enabled",
        )

        for default in defaults:
            name = default.get("name")
            if not name:
                continue
            current = existing_map.get(name)
            if current is None:
                to_upsert.append(default)
                continue

            if any(
                MainWindow._normalise_modifier_field(current.get(key))
                != MainWindow._normalise_modifier_field(default.get(key))
                for key in comparison_keys
            ):
                to_upsert.append(default)

        if not to_upsert:
            return False

        try:
            upsert_modifiers(to_upsert)
        except Exception:
            return False
        return True

    @staticmethod
    def _normalise_modifier_field(value) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if value in (None, ""):
            return ""
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            return str(value)

    def _populate_available_spells_table(self) -> None:
        table = self.available_spells_table
        header = table.horizontalHeader()
        sort_section = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()

        table.setSortingEnabled(False)
        table.setRowCount(0)
        table.clearContents()

        filtered_spells: List[dict] = []
        for spell in self.available_spells:
            has_damage = plotting.extract_effect_params(spell) is not None
            if not self._show_non_damage_spells and not has_damage:
                continue
            filtered_spells.append(spell)

        table.setRowCount(len(filtered_spells))
        for row, spell in enumerate(filtered_spells):
            name = spell.get("name", "Unknown")
            level_value = spell.get("level", "")
            if self._dataset_mode == "cantrips" or level_value in (None, "", 0):
                level = ""
            else:
                level = str(level_value)
            school = spell.get("school", "")
            rng = spell.get("range", "")
            casting = spell.get("casting_time", "")
            duration = spell.get("duration", "")
            comps = spell.get("components", [])
            comp_str = ", ".join(comps) if isinstance(comps, list) else str(comps)

            name_item = QTableWidgetItem(str(name))
            name_item.setData(Qt.ItemDataRole.UserRole, spell)
            table.setItem(row, 0, name_item)
            table.setItem(row, 1, QTableWidgetItem(str(level)))
            table.setItem(row, 2, QTableWidgetItem(str(school)))
            table.setItem(row, 3, QTableWidgetItem(str(rng)))
            table.setItem(row, 4, QTableWidgetItem(str(casting)))
            table.setItem(row, 5, QTableWidgetItem(str(duration)))
            table.setItem(row, 6, QTableWidgetItem(comp_str))
            self._style_available_row(row)

        table.setSortingEnabled(True)
        if filtered_spells and sort_section >= 0:
            table.sortItems(sort_section, sort_order)
        table.resizeColumnsToContents()
        self._apply_filters()
        self._refresh_selection_highlights()

    def _reset_filter_options(self) -> None:
        unique_names = sorted({sp.get("name", "") for sp in self.available_spells if sp.get("name")})
        unique_schools = sorted({sp.get("school", "") for sp in self.available_spells if sp.get("school")})
        unique_ranges = sorted({sp.get("range", "") for sp in self.available_spells if sp.get("range")})
        unique_casting_times = sorted({sp.get("casting_time", "") for sp in self.available_spells if sp.get("casting_time")})
        unique_durations = sorted({sp.get("duration", "") for sp in self.available_spells if sp.get("duration")})
        comp_set = set()
        for spell in self.available_spells:
            comps = spell.get("components", [])
            if isinstance(comps, list):
                comp_set.update(comps)
            elif isinstance(comps, str) and comps:
                comp_set.update(part.strip() for part in comps.split(','))
        unique_components = sorted({comp.strip() for comp in comp_set if comp})

        labels: Dict[str, List[str]] = {
            "name": unique_names,
        }
        if self._dataset_mode != "cantrips":
            level_values = set()
            for spell in self.available_spells:
                raw_level = spell.get("level")
                if raw_level in (None, "", 0):
                    continue
                level_values.add(str(raw_level))
            unique_levels = sorted(level_values, key=lambda value: int(value) if value.isdigit() else value)
            if unique_levels:
                labels["level"] = unique_levels
        labels.update(
            {
                "school": unique_schools,
                "range": unique_ranges,
                "casting_time": unique_casting_times,
                "duration": unique_durations,
                "components": unique_components,
            }
        )

        self.filter_input_widget.available_labels = labels
        self.filter_input_widget.current_phase = "label"
        self.filter_input_widget.current_label = ""
        self.filter_input_widget.update_completer(list(self.filter_input_widget.available_labels.keys()))

    def _action_import_dataset(self) -> None:
        start_dir = str(PROJECT_ROOT)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Spell Dataset",
            start_dir,
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        try:
            counts = import_dataset(path)
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", f"Could not import dataset:\n{exc}")
            return

        self._reload_spells(show_errors=True)
        QMessageBox.information(
            self,
            "Import Complete",
            (
                f"Imported dataset from {path.name}:\n"
                f"Spells: {counts.get('spells', 0)}\n"
                f"Cantrips: {counts.get('cantrips', 0)}\n"
                f"Modifiers: {counts.get('modifiers', 0)}"
            ),
        )

    def _action_export_dataset(self) -> None:
        start_dir = str(PROJECT_ROOT)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Spell Dataset",
            start_dir,
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        if path.suffix.lower() != ".json":
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
            counts = export_dataset_to_json(path)
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not export dataset:\n{exc}")
            return

        QMessageBox.information(
            self,
            "Export Complete",
            (
                f"Exported dataset to {path.name}:\n"
                f"Spells: {counts.get('spells', 0)}\n"
                f"Cantrips: {counts.get('cantrips', 0)}\n"
                f"Modifiers: {counts.get('modifiers', 0)}"
            ),
        )
        
    def on_filter_added(self, label, value):
        self._active_filters.setdefault(label, set()).add(value)
        self._apply_filters()

    def on_filter_removed(self, label, value):
        vals = self._active_filters.get(label)
        if vals and value in vals:
            vals.remove(value)
            if not vals:
                del self._active_filters[label]
        self._apply_filters()

    def _apply_filters(self):
        table = self.available_spells_table
        column_map = {
            "name": 0,
            "level": 1,
            "school": 2,
            "range": 3,
            "casting_time": 4,
            "duration": 5,
            "components": 6,
        }
        for row in range(table.rowCount()):
            visible = True
            for key, vals in self._active_filters.items():
                if key not in column_map or not vals:
                    continue
                item = table.item(row, column_map[key])
                if not item:
                    visible = False
                    break
                cell_text = item.text() or ""
                if key == "level":
                    if str(cell_text) not in vals:
                        visible = False
                        break
                elif key == "components":
                    components = [part.strip().lower() for part in cell_text.split(',') if part.strip()]
                    if not any(value.lower() in components for value in vals):
                        visible = False
                        break
                else:
                    cell_lower = cell_text.lower()
                    if not any(value.lower() in cell_lower for value in vals):
                        visible = False
                        break
            table.setRowHidden(row, not visible)

    def _style_available_row(self, row: int, *, highlight: bool = False) -> None:
        table = self.available_spells_table
        if row < 0 or row >= table.rowCount():
            return
        if highlight:
            background = self._available_row_colors["highlight"]
        else:
            key = "even" if row % 2 == 0 else "odd"
            background = self._available_row_colors[key]
        text_color = self._available_row_colors["text"]
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if not item:
                continue
            item.setBackground(QBrush(background))
            item.setForeground(QBrush(text_color))

    def _style_selected_row(self, row: int) -> None:
        table = self.selected_spells_table
        if row < 0 or row >= table.rowCount():
            return
        key = "even" if row % 2 == 0 else "odd"
        background = self._selected_row_colors[key]
        text_color = self._selected_row_colors["text"]
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if not item:
                continue
            item.setBackground(QBrush(background))
            item.setForeground(QBrush(text_color))

    def _refresh_selection_highlights(self) -> None:
        table = self.available_spells_table
        selected_keys = self._selected_spell_keys
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            spell = item.data(Qt.ItemDataRole.UserRole) if item else None
            highlight = bool(spell) and self._spell_identity(spell) in selected_keys
            self._style_available_row(row, highlight=highlight)

    def _spell_identity(self, spell: Dict) -> str:
        spell_id = spell.get("id")
        if spell_id is not None:
            return f"id:{spell_id}"
        name = spell.get("name", "")
        level = spell.get("level", "")
        school = spell.get("school", "")
        return f"name:{name}|level:{level}|school:{school}"
        
    def add_spell_to_selection(self, row, column):
        table = self.available_spells_table
        item = table.item(row, 0)
        if not item:
            return
        spell = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(spell, dict):
            return

        key = self._spell_identity(spell)
        if key in self._selected_spell_keys:
            return

        self.selected_spells.append(spell)
        self._selected_spell_keys.add(key)

        row_position = self.selected_spells_table.rowCount()
        self.selected_spells_table.insertRow(row_position)
        cols = ['name', 'level', 'school', 'range', 'casting_time', 'duration', 'components']
        for col, field in enumerate(cols):
            val = spell.get(field, '')
            if field == 'components' and isinstance(val, list):
                val = ', '.join(val)
            self.selected_spells_table.setItem(row_position, col, QTableWidgetItem(str(val)))
        self._style_selected_row(row_position)
        self.selected_spells_table.resizeColumnsToContents()

        self._refresh_selection_highlights()
        
    def remove_spell_from_selection(self, row, column):
        # Identify and remove spell
        removed_spell = self.selected_spells[row]
        removed_key = self._spell_identity(removed_spell)
        self.selected_spells_table.removeRow(row)
        self.selected_spells.pop(row)
        self._selected_spell_keys.discard(removed_key)
        for idx in range(self.selected_spells_table.rowCount()):
            self._style_selected_row(idx)
        self._refresh_selection_highlights()
        
    def on_generate(self):
        """Generate and display the graph for selected spells within separate windows."""
        settings = self.character_settings
        ability = settings.get("ability_value", 10)
        additional = settings.get("additional_bonus", 0)
        mod_val = (ability - 10) // 2 + additional

        count = len(self.selected_spells)
        if count == 0:
            QMessageBox.warning(self, "No Spells Selected", "Please select at least one spell to plot.")
            return

        try:
            if count == 1:
                spell = self.selected_spells[0]
                spell_name = spell.get("name", "Spell")
                fig = plotting.plot_spell(spell, mod_val, spell_name)
                window_title = f"Spell Graph: {spell_name}"
            elif 2 <= count <= plotting.MAX_COMPARE_SPELLS:
                fig = plotting.compare_spells(self.selected_spells, mod_val)
                joined_names = ", ".join(spell.get("name", "Spell") for spell in self.selected_spells)
                window_title = f"Spell Comparison: {joined_names}"
            else:
                QMessageBox.warning(
                    self,
                    "Too Many Spells",
                    f"Please select up to {plotting.MAX_COMPARE_SPELLS} spells for comparison.",
                )
                return
        except ValueError as exc:
            QMessageBox.information(self, "Unable to Plot", str(exc))
            return

        if not fig:
            return

        graph_window = GraphWindow(fig, title=window_title, parent=self)
        graph_window.show()
        self._register_graph_window(graph_window)
        
    def clear_filters(self):
        """Clear all active filters."""
        self._active_filters.clear()
        # Remove all filter chips from UI
        layout = self.filter_input_widget.active_filters_layout
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            widget = item.widget() if item else None
            # Remove chip buttons only
            if widget and isinstance(widget, QPushButton):
                widget.deleteLater()
        # Re-apply filters to show all rows
        self._apply_filters()
        self._refresh_selection_highlights()
        
    def clear_selections(self):
        """Clear all selected spells and reset highlights."""
        self.selected_spells_table.setRowCount(0)
        self.selected_spells.clear()
        self._selected_spell_keys.clear()
        self._refresh_selection_highlights()
        
    def on_available_spell_clicked(self, row, column):
        """Display details of the clicked available spell."""
        table = self.available_spells_table
        if row < 0 or row >= table.rowCount():
            return
        item = table.item(row, 0)
        if not item:
            return
        spell = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(spell, dict):
            return
        self.details_text.setPlainText(self._format_spell_details(spell))

    def _format_spell_details(self, spell: Dict) -> str:
        lines: List[str] = []
        name = spell.get("name", "Unknown")
        level_value = spell.get("level")
        level_text = "Cantrip" if not level_value else f"Level {level_value}"
        school = spell.get("school") or ""
        lines.append(f"Name: {name}")
        lines.append(f"Level: {level_text}")
        if school:
            lines.append(f"School: {school}")
        casting = spell.get("casting_time") or "Unknown"
        lines.append(f"Casting Time: {casting}")
        rng = spell.get("range") or "Unknown"
        lines.append(f"Range: {rng}")
        duration = spell.get("duration") or "Unknown"
        lines.append(f"Duration: {duration}")
        components = spell.get("components")
        if isinstance(components, list):
            comp_text = ", ".join(components) if components else "None"
        elif components:
            comp_text = str(components)
        else:
            comp_text = "None"
        lines.append(f"Components: {comp_text}")

        modifiers = spell.get("modifiers") or []
        lines.append("")
        lines.append("Modifiers:")
        if not modifiers:
            lines.append("  None")
        else:
            for modifier in modifiers:
                label = modifier.get("name", "Unnamed Modifier")
                category = modifier.get("category")
                scope = modifier.get("scope")
                suffix_bits = []
                if category:
                    suffix_bits.append(str(category).title())
                if scope and str(scope).lower() != "spell":
                    suffix_bits.append(str(scope).title())
                suffix = f" ({', '.join(suffix_bits)})" if suffix_bits else ""
                lines.append(f"  - {label}{suffix}")

        effects = spell.get("effects") or []
        lines.append("")
        lines.append("Effects:")
        if not effects:
            lines.append("  None")
        else:
            for effect in effects:
                effect_type = str(effect.get("effect_type", "Effect")).replace("_", " ").title()
                lines.append(f"  {effect_type}:")
                description = effect.get("description")
                if description:
                    lines.append(f"    {description}")
                effect_data = effect.get("effect_data") or {}
                lines.extend(self._summarise_effect_data(effect_data, indent="    "))
                resolution = effect.get("resolution")
                if resolution:
                    lines.append(f"    Resolution: {self._stringify_value(resolution)}")
                repeat = effect.get("repeat")
                if repeat:
                    lines.append(f"    Repeat: {self._stringify_value(repeat)}")

        return "\n".join(line for line in lines if line is not None).strip()

    def _summarise_effect_data(self, effect_data: Dict, *, indent: str = "") -> List[str]:
        lines: List[str] = []
        if not effect_data:
            return lines
        damage = effect_data.get("damage")
        if damage:
            lines.append(f"{indent}Damage: {self._format_damage_block(damage)}")
        healing = effect_data.get("healing")
        if healing:
            lines.append(f"{indent}Healing: {self._format_damage_block(healing)}")
        for key, value in effect_data.items():
            if key in {"damage", "healing"}:
                continue
            label = key.replace("_", " ").title()
            lines.append(f"{indent}{label}: {self._stringify_value(value)}")
        return lines

    def _format_damage_block(self, payload) -> str:
        if not isinstance(payload, dict):
            return self._stringify_value(payload)
        parts: List[str] = []
        base = payload.get("base") or {}
        dice = base.get("dice")
        die = base.get("die")
        if dice and die:
            parts.append(f"{dice}d{die}")
        scaling = payload.get("scaling") or {}
        add_dice = scaling.get("dice_per_slot")
        add_die = scaling.get("die")
        if add_dice and add_die:
            parts.append(f"+ {add_dice}d{add_die} per slot")
        constant = payload.get("constant")
        if isinstance(constant, (int, float)) and constant:
            parts.append(f"+ {constant}")
        add_constant = scaling.get("constant_per_slot")
        if isinstance(add_constant, (int, float)) and add_constant:
            parts.append(f"+ {add_constant} per slot")
        if payload.get("use_modifier"):
            parts.append("+ ability modifier")
        damage_type = payload.get("type")
        summary = " ".join(parts) if parts else self._stringify_value({k: v for k, v in payload.items() if k not in {"type"}})
        if damage_type:
            return f"{str(damage_type).title()} ({summary})" if summary else str(damage_type).title()
        return summary

    def _stringify_value(self, value) -> str:
        if value in (None, ""):
            return "None"
        if isinstance(value, (list, dict)):
            try:
                return json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError):
                return str(value)
        return str(value)
        
def main() -> int:
    """Launch the PySide6 GUI and return the application's exit code."""

    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
    app_icon = get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    window = MainWindow()
    window.show()

    if owns_app:
        return app.exec()

    # If an application already exists, don't quit it—just start the window.
    return 0


if __name__ == "__main__":
    sys.exit(main())
