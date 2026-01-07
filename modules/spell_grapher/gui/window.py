"""Primary application window implementation for Living Scroll."""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)
from spell_graphs import plotting
from modules.characters.model import (
    CharacterSheet,
    build_spellcasting_profile,
)
from spell_graphs.spells import (
    build_filter_labels,
    equipment_damage_bonus,
    partition_spells,
    spell_identity,
    spell_matches_filters,
)
from modules.compendium.service import Compendium
from modules.compendium.modifiers.state import ModifierLoadError, ModifierStateService, ModifierStateSnapshot
from gui.application_context import ApplicationContext
from gui.resources import get_app_icon
from gui.widgets import FilterInputWidget, FramelessWindow
from .graph_widget import GraphWindow



class MainWindow(FramelessWindow):
    """Primary application window that hosts filters, tables, and plotting actions."""

    @staticmethod
    def _spell_record_from_compendium(payload: dict) -> dict:
        """Convert a filesystem compendium spell record into the runtime shape used by the UI."""

        record = dict(payload or {})

        effects: List[dict] = []

        runtime: dict = {
            "id": record.get("id"),
            "name": record.get("name"),
            "level": record.get("level", 0),
            "school": record.get("school"),
            "casting_time": record.get("casting_time"),
            "range": record.get("range"),
            "duration": record.get("duration"),
            "components": record.get("components", []),
            "effects": effects,
            "modifiers": [],
        }

        scaling_levels = legacy.get("scaling_levels")
        if isinstance(scaling_levels, list):
            runtime["scaling_levels"] = list(scaling_levels)

        return runtime

    def __init__(self, app_context: ApplicationContext | None = None):
        super().__init__()
        self.setWindowTitle("Spell Grapher")
        self.setWindowIcon(get_app_icon())
        self.resize(1300, 750)
        self._app_context = app_context

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

        self.character_modifiers: Dict[str, bool]
        self._context_sheet_linked = bool(app_context and app_context.character_sheet)
        if app_context and app_context.character_sheet:
            self.character_sheet = app_context.character_sheet
            self.character_modifiers = dict(app_context.modifier_states)
            self._modifier_snapshot = app_context.modifier_snapshot
        else:
            self.character_sheet = CharacterSheet()
            self.character_modifiers = {}
            self._modifier_snapshot = None
        self._modifier_service = ModifierStateService()
        self._spellcasting_profile = None
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
        selected_label = QLabel("Selected Spells for Comparison")
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
        self.selected_spells_table.cellDoubleClicked.connect(self.remove_spell_from_selection)
        self.generate_button.clicked.connect(self.on_generate)  # handle generate graph

    def _build_toolbar(self) -> None:
        """Constructs the main toolbar with Character and Options menus."""
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

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
        """Loads spells from the filesystem compendium and partitions them into spells and cantrips."""
        try:
            compendium = Compendium.load()
            raw_records = compendium.records("spells")
            records = [self._spell_record_from_compendium(entry) for entry in raw_records if isinstance(entry, dict)]
            records.sort(key=lambda item: (item.get("level", 0), str(item.get("name", "")).lower()))
        except Exception as exc:
            if show_errors:
                QMessageBox.critical(self, "Compendium Error", f"Failed to load spells: {exc}")
            records = []

        spells_only, cantrips_only = partition_spells(records)
        self._spells_only = spells_only
        self._cantrips_only = cantrips_only

        target_mode = self._dataset_mode if self._dataset_mode in {"spells", "cantrips"} else "spells"
        if target_mode == "spells" and not spells_only and cantrips_only:
            target_mode = "cantrips"
        self._set_dataset_mode(target_mode, force=True)
        self._refresh_character_modifiers()

    def _refresh_character_modifiers(self) -> None:
        """Reload modifier definitions/states via the service and refresh caches."""
        existing_states = dict(self.character_modifiers)
        try:
            snapshot = self._modifier_service.refresh(existing_states)
        except ModifierLoadError as exc:
            QMessageBox.warning(self, "Modifier Load Failed", str(exc))
            snapshot = ModifierStateSnapshot(self._modifier_service.definitions, existing_states)
        self.character_modifiers = snapshot.states
        self._modifier_snapshot = snapshot
        self._update_spellcasting_profile()
        self._sync_context()

    def _sync_context(self) -> None:
        if not self._app_context or not self._context_sheet_linked:
            return
        self._app_context.character_sheet = self.character_sheet
        self._app_context.modifier_states = dict(self.character_modifiers)
        self._app_context.modifier_snapshot = self._modifier_snapshot

    def on_character_data_updated(self) -> None:
        if not self._app_context:
            return
        sheet = self._app_context.character_sheet
        self._context_sheet_linked = bool(sheet)
        self.character_sheet = sheet if sheet else CharacterSheet()
        self.character_modifiers = dict(self._app_context.modifier_states) if sheet else {}
        self._modifier_snapshot = self._app_context.modifier_snapshot if sheet else None
        self._refresh_character_modifiers()

    def _update_spellcasting_profile(self) -> None:
        try:
            self._spellcasting_profile = build_spellcasting_profile(self.character_sheet)
        except Exception:
            self._spellcasting_profile = None

    def _toggle_non_damage_visibility(self, checked: bool) -> None:
        self._show_non_damage_spells = bool(checked)
        if not checked:
            self._remove_non_damage_from_selection()
        self._populate_available_spells_table()

    def _remove_non_damage_from_selection(self) -> None:
        for row in range(len(self.selected_spells) - 1, -1, -1):
            spell = self.selected_spells[row]
            if plotting.extract_effect_params(spell) is None:
                self.remove_spell_from_selection(row, 0)

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
        include_levels = self._dataset_mode != "cantrips"
        labels = build_filter_labels(self.available_spells, include_levels=include_levels)
        self.filter_input_widget.available_labels = labels
        self.filter_input_widget.current_phase = "label"
        self.filter_input_widget.current_label = ""
        self.filter_input_widget.update_completer(list(self.filter_input_widget.available_labels.keys()))

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
        has_filters = bool(self._active_filters)
        for row in range(table.rowCount()):
            spell = self._spell_from_table_row(row)
            if not spell:
                visible = not has_filters
            else:
                visible = spell_matches_filters(spell, self._active_filters)
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

    def _spell_from_table_row(self, row: int) -> Optional[Dict]:
        if row < 0 or row >= self.available_spells_table.rowCount():
            return None
        item = self.available_spells_table.item(row, 0)
        if not item:
            return None
        spell = item.data(Qt.ItemDataRole.UserRole)
        return spell if isinstance(spell, dict) else None

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
            spell = self._spell_from_table_row(row)
            highlight = bool(spell) and spell_identity(spell) in selected_keys
            self._style_available_row(row, highlight=highlight)
        
    def add_spell_to_selection(self, row, column):
        table = self.available_spells_table
        item = table.item(row, 0)
        if not item:
            return
        spell = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(spell, dict):
            return

        key = spell_identity(spell)
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
        removed_key = spell_identity(removed_spell)
        self.selected_spells_table.removeRow(row)
        self.selected_spells.pop(row)
        self._selected_spell_keys.discard(removed_key)
        for idx in range(self.selected_spells_table.rowCount()):
            self._style_selected_row(idx)
        self._refresh_selection_highlights()
        
    def on_generate(self):
        """Generate and display the graph for selected spells within separate windows."""
        profile = self._spellcasting_profile or build_spellcasting_profile(self.character_sheet)
        mod_val = profile.ability_modifier + equipment_damage_bonus(self.character_sheet)

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
