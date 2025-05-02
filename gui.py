import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QLabel,
    QCheckBox, QSplitter, QGroupBox, QFormLayout, QSpinBox, QListWidget,
    QListWidgetItem, QCompleter, QFrame, QMessageBox, QPlainTextEdit
)
from PySide6.QtCore import Qt, QStringListModel, Signal
from PySide6.QtGui import QBrush, QColor
import db  # load spells from database
import json
import plotting  # integrate plotting functions
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

# --- Custom Widget for Filter Input with Auto-Completion and Active Filters ---
class FilterInputWidget(QWidget):
    # Signal emitted when a new filter is added; carries tuple (label, value)
    filterAdded = Signal(str, str)
    filterRemoved = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.available_labels = {
            "level": [str(i) for i in range(1, 10)],
            "components": ["V", "S", "M"]  # Example values; extend as needed.
        }
        self.current_phase = "label"  # "label" or "value"
        self.current_label = ""  # stores the chosen label
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        # Input field for typing filter text
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Type filter (e.g., level: 3)")
        layout.addWidget(self.input_line)

        # Active filters area
        self.active_filters_frame = QFrame()
        self.active_filters_frame.setFrameShape(QFrame.StyledPanel)
        self.active_filters_layout = QHBoxLayout(self.active_filters_frame)
        self.active_filters_layout.addStretch()  # To push chips to left
        layout.addWidget(self.active_filters_frame)

        # Set up completer
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.input_line.setCompleter(self.completer)
        self.model = QStringListModel()
        self.completer.setModel(self.model)

        # Connect signals
        self.input_line.textEdited.connect(self.on_text_edited)
        self.input_line.returnPressed.connect(self.on_return_pressed)
        self.completer.activated.connect(self.on_completer_activated)

    def on_text_edited(self, text):
        # Determine phase based on whether ':' is present.
        if ':' in text:
            # Assume format: label: value...
            parts = text.split(':', 1)
            label_part = parts[0].strip()
            value_part = parts[1].strip()
            if label_part in self.available_labels:
                self.current_phase = "value"
                self.current_label = label_part
                suggestions = self.available_labels[label_part]
                # Filter suggestions based on current value text.
                filtered = [s for s in suggestions if s.lower().startswith(value_part.lower())]
                # Auto-select if only one suggestion.
                if len(filtered) == 1 and value_part != filtered[0]:
                    # Complete the text automatically.
                    self.input_line.setText(f"{label_part}: {filtered[0]}")
                    self.input_line.setCursorPosition(len(self.input_line.text()))
                self.update_completer(filtered)
            else:
                # Unrecognized label; revert to label phase.
                self.current_phase = "label"
                self.update_completer(list(self.available_labels.keys()))
        else:
            # In label phase.
            self.current_phase = "label"
            filtered = [lbl for lbl in self.available_labels.keys() if lbl.lower().startswith(text.lower())]
            # Auto-select if only one possibility and text is nonempty.
            if len(filtered) == 1 and text.lower() != filtered[0].lower():
                self.input_line.setText(f"{filtered[0]}: ")
                self.input_line.setCursorPosition(len(self.input_line.text()))
                self.current_phase = "value"
                self.current_label = filtered[0]
                self.update_completer(self.available_labels[filtered[0]])
            else:
                self.update_completer(filtered)

    def update_completer(self, suggestions):
        self.model.setStringList(suggestions)
        self.completer.complete()

    def on_completer_activated(self, text):
        # When a suggestion is selected, complete the field accordingly.
        current = self.input_line.text()
        if self.current_phase == "label":
            # Replace text with chosen label and add colon.
            self.input_line.setText(f"{text}: ")
            self.current_label = text
            self.current_phase = "value"
            self.update_completer(self.available_labels.get(text, []))
        elif self.current_phase == "value":
            # In value phase, complete the value.
            label_part = self.current_label
            self.input_line.setText(f"{label_part}: {text}")
            # Optionally, move cursor to end.
            self.input_line.setCursorPosition(len(self.input_line.text()))

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
                self.update_completer(list(self.available_labels.keys()))

    def add_filter_chip(self, label, value):
        chip_text = f"{label}: {value}"
        chip = QPushButton(chip_text)
        chip.label = label
        chip.value = value
        chip.setCheckable(False)
        chip.setStyleSheet("QPushButton {border: 1px solid gray; border-radius: 5px; padding: 2px; background-color: lightgray;}")
        # When chip is clicked, remove it.
        chip.clicked.connect(lambda: self.remove_chip(chip))
        # Insert the chip before the stretch spacer.
        self.active_filters_layout.insertWidget(self.active_filters_layout.count()-1, chip)

    def remove_chip(self, chip):
        label = chip.label
        value = chip.value
        chip.deleteLater()
        self.filterRemoved.emit(label, value)

# --- Main Window Prototype with Filtering and Spell Tables ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DnD Spell Plotter")
        self.resize(1000, 650)
        
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)
        
        # Top: Filter Input Widget
        self.filter_input_widget = FilterInputWidget()
        self._active_filters = {}
        self.filter_input_widget.filterAdded.connect(self.on_filter_added)
        self.filter_input_widget.filterRemoved.connect(self.on_filter_removed)
        main_layout.addWidget(self.filter_input_widget)
        
        # Add Clear Filters button
        clear_filters_button = QPushButton("Clear Filters")
        clear_filters_button.clicked.connect(self.clear_filters)
        button_layout = QHBoxLayout()
        button_layout.addWidget(clear_filters_button)
        button_layout.addStretch()
        main_layout.insertLayout(1, button_layout)
        
        # Search box for spell names
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name...")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        main_layout.insertWidget(2, self.search_input)
        
        # Main area split into two: Left for spells table, Right for settings and selected spells
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left Pane: Available Spells Table
        self.available_spells_table = QTableWidget()
        # 7 columns: Name, Level, School, Range, Casting Time, Duration, Components
        self.available_spells_table.setColumnCount(7)
        self.available_spells_table.setHorizontalHeaderLabels([
            "Name", "Level", "School", "Range", "Casting Time", "Duration", "Components"
        ])
        self.available_spells_table.setSortingEnabled(True)

        # Load spells from database with error handling
        try:
            self.available_spells = db.load_spells()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load spells: {e}")
            self.available_spells = []

        self.selected_spells = []  # list of spell objects selected for comparison

        # Populate Available Spells Table from database with actual columns
        self.available_spells_table.setRowCount(len(self.available_spells))
        for row, spell in enumerate(self.available_spells):
            name = spell.get('name', 'Unknown')
            level = str(spell.get('level', ''))
            school = spell.get('school', '')
            rng = spell.get('range', '')
            casting = spell.get('casting_time', '')
            duration = spell.get('duration', '')
            comps = spell.get('components', [])
            comp_str = ', '.join(comps) if isinstance(comps, list) else str(comps)
            self.available_spells_table.setItem(row, 0, QTableWidgetItem(name))
            self.available_spells_table.setItem(row, 1, QTableWidgetItem(level))
            self.available_spells_table.setItem(row, 2, QTableWidgetItem(school))
            self.available_spells_table.setItem(row, 3, QTableWidgetItem(rng))
            self.available_spells_table.setItem(row, 4, QTableWidgetItem(casting))
            self.available_spells_table.setItem(row, 5, QTableWidgetItem(duration))
            self.available_spells_table.setItem(row, 6, QTableWidgetItem(comp_str))
        self.available_spells_table.resizeColumnsToContents()

        # Configure filter widget with appropriate labels and values
        unique_levels = sorted({str(sp.get('level', '')) for sp in self.available_spells})
        unique_schools = sorted({sp.get('school', '') for sp in self.available_spells})
        # Gather distinct component flags across spells
        comp_set = set()
        for sp in self.available_spells:
            comps = sp.get('components', [])
            if isinstance(comps, list):
                comp_set.update(comps)
        unique_components = sorted(comp_set)
        self.filter_input_widget.available_labels = {
            'level': unique_levels,
            'school': unique_schools,
            'components': unique_components
        }
        self.filter_input_widget.current_phase = 'label'
        self.filter_input_widget.update_completer(list(self.filter_input_widget.available_labels.keys()))

        splitter.addWidget(self.available_spells_table)
        
        # Right Pane: Spellcasting Configuration, Modifiers, and Selected Spells
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Spellcasting Configuration Group
        spellcasting_config_group = QGroupBox("Spellcasting Configuration")
        spellcasting_layout = QFormLayout()
        self.ability_value_spin = QSpinBox()
        self.ability_value_spin.setRange(1, 30)
        self.ability_value_spin.setValue(10)
        spellcasting_layout.addRow("Ability Value:", self.ability_value_spin)
        
        self.additional_bonus_spin = QSpinBox()
        self.additional_bonus_spin.setRange(-10, 10)
        self.additional_bonus_spin.setValue(0)
        spellcasting_layout.addRow("Additional Bonus:", self.additional_bonus_spin)
        
        self.saving_throw_proficiency_spin = QSpinBox()
        self.saving_throw_proficiency_spin.setRange(0, 10)
        self.saving_throw_proficiency_spin.setValue(2)
        spellcasting_layout.addRow("Saving Throw Proficiency:", self.saving_throw_proficiency_spin)
        
        self.saving_throw_bonus_spin = QSpinBox()
        self.saving_throw_bonus_spin.setRange(-10, 10)
        self.saving_throw_bonus_spin.setValue(0)
        spellcasting_layout.addRow("Saving Throw Bonus:", self.saving_throw_bonus_spin)
        
        spellcasting_config_group.setLayout(spellcasting_layout)
        right_layout.addWidget(spellcasting_config_group)
        
        # Modifiers Panel
        modifiers_group = QGroupBox("Modifiers (Feats, Subclasses, etc.)")
        modifiers_layout = QVBoxLayout()
        modifiers_layout.addWidget(QCheckBox("Feat: Elemental Adept"))
        modifiers_layout.addWidget(QCheckBox("Subclass: Evoker"))
        modifiers_layout.addWidget(QCheckBox("Feat: Spell Sniper"))
        modifiers_layout.addWidget(QCheckBox("Subclass: Abjurer"))
        modifiers_group.setLayout(modifiers_layout)
        right_layout.addWidget(modifiers_group)
        
        # Selected Spells Panel (Table)
        selected_label = QLabel("Selected Spells for Comparison:")
        right_layout.addWidget(selected_label)
        self.selected_spells_table = QTableWidget()
        self.selected_spells_table.setColumnCount(7)
        self.selected_spells_table.setHorizontalHeaderLabels([
            "Name", "Level", "School", "Range", "Casting Time", "Duration", "Components"
        ])
        self.selected_spells_table.resizeColumnsToContents()
        right_layout.addWidget(self.selected_spells_table)
        
        # Add Clear Selections button above selected spells
        clear_selection_btn = QPushButton("Clear Selections")
        clear_selection_btn.clicked.connect(self.clear_selections)
        right_layout.insertWidget(right_layout.indexOf(self.selected_spells_table)-1, clear_selection_btn)
        
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
        
        # Plot display area
        self.plot_widget = QWidget()
        self.plot_layout = QVBoxLayout(self.plot_widget)
        self.plot_canvas = None
        self.nav_toolbar = None
        main_layout.addWidget(self.plot_widget)
        
        # Signal Connections:
        self.available_spells_table.cellDoubleClicked.connect(self.add_spell_to_selection)
        self.available_spells_table.cellClicked.connect(self.on_available_spell_clicked)
        self.selected_spells_table.cellDoubleClicked.connect(self.remove_spell_from_selection)
        self.generate_button.clicked.connect(self.on_generate)  # handle generate graph
        
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
        for row in range(table.rowCount()):
            visible = True
            for key, vals in self._active_filters.items():
                # Map filter label to table column index
                if key == "level":
                    col = 1
                elif key == "school":
                    col = 2
                elif key == "components":
                    col = 6
                else:
                    continue
                item = table.item(row, col)
                if not item or item.text() not in vals:
                    visible = False
                    break
            table.setRowHidden(row, not visible)
        
    def add_spell_to_selection(self, row, column):
        # Add selected spell object and populate table
        spell = self.available_spells[row]
        # Avoid duplicates based on spell id
        if any(s.get('id') == spell.get('id') for s in self.selected_spells):
            return
        # Append to internal list
        self.selected_spells.append(spell)
        # Insert into selected spells table
        row_position = self.selected_spells_table.rowCount()
        self.selected_spells_table.insertRow(row_position)
        # Map keys to columns
        cols = ['name', 'level', 'school', 'range', 'casting_time', 'duration', 'components']
        for col, key in enumerate(cols):
            val = spell.get(key, '')
            if key == 'components' and isinstance(val, list):
                val = ', '.join(val)
            self.selected_spells_table.setItem(row_position, col, QTableWidgetItem(str(val)))
        self.selected_spells_table.resizeColumnsToContents()
        
        # Highlight the selected row in available spells table
        for col_idx in range(self.available_spells_table.columnCount()):
            item = self.available_spells_table.item(row, col_idx)
            if item:
                item.setBackground(QBrush(QColor("lightblue")))
        
    def remove_spell_from_selection(self, row, column):
        # Identify and remove spell
        removed_spell = self.selected_spells[row]
        self.selected_spells_table.removeRow(row)
        self.selected_spells.pop(row)
        # Un-highlight the corresponding row in available spells table
        for avail_row, spell in enumerate(self.available_spells):
            if spell.get('id') == removed_spell.get('id'):
                for col_idx in range(self.available_spells_table.columnCount()):
                    item = self.available_spells_table.item(avail_row, col_idx)
                    if item:
                        item.setBackground(QBrush(QColor("white")))
                break
        
    def on_generate(self):
        """Generate and display the graph for selected spells within the GUI."""
        # compute modifier
        mod_val = (self.ability_value_spin.value() - 10) // 2 + self.additional_bonus_spin.value()
        count = len(self.selected_spells)
        if count == 0:
            QMessageBox.warning(self, "No Spells Selected", "Please select at least one spell to plot.")
            return
        # Generate figure
        if count == 1:
            fig = plotting.plot_spell(self.selected_spells[0], mod_val, self.selected_spells[0].get("name", "Spell"))
        elif count in (2, 3):
            fig = plotting.compare_spells(self.selected_spells, mod_val)
        else:
            QMessageBox.warning(self, "Too Many Spells", "Please select up to 3 spells for comparison.")
            return
        if not fig:
            return
        # Clear previous canvas
        if self.plot_canvas:
            self.plot_layout.removeWidget(self.nav_toolbar)
            self.nav_toolbar.deleteLater()
            self.plot_layout.removeWidget(self.plot_canvas)
            self.plot_canvas.deleteLater()
        # Create and add toolbar
        self.nav_toolbar = NavigationToolbar(FigureCanvas(fig), self)
        self.plot_layout.addWidget(self.nav_toolbar)
        # Create and add canvas
        self.plot_canvas = FigureCanvas(fig)
        self.plot_layout.addWidget(self.plot_canvas)
        self.plot_canvas.draw()
        
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
        # Clear search input as well
        if hasattr(self, 'search_input'):
            self.search_input.clear()
        # Re-apply filters to show all rows
        self._apply_filters()
        
    def clear_selections(self):
        """Clear all selected spells and reset highlights."""
        self.selected_spells_table.setRowCount(0)
        self.selected_spells.clear()
        for row in range(self.available_spells_table.rowCount()):
            for col_idx in range(self.available_spells_table.columnCount()):
                item = self.available_spells_table.item(row, col_idx)
                if item:
                    item.setBackground(QBrush(QColor("white")))
        
    def on_search_text_changed(self, text):
        """Filter available spells table by name search and active filters."""
        text = text.strip().lower()
        # First apply other active filters
        self._apply_filters()
        # Then apply search filter on name column
        for row in range(self.available_spells_table.rowCount()):
            if not text:
                continue
            item = self.available_spells_table.item(row, 0)
            if item and text not in item.text().lower():
                self.available_spells_table.setRowHidden(row, True)
        
    def on_available_spell_clicked(self, row, column):
        """Display details of the clicked available spell."""
        if row < 0 or row >= len(self.available_spells):
            return
        spell = self.available_spells[row]
        # Prepare details text
        details = {
            'Name': spell.get('name'),
            'Level': spell.get('level'),
            'School': spell.get('school'),
            'Casting Time': spell.get('casting_time'),
            'Range': spell.get('range'),
            'Duration': spell.get('duration'),
            'Components': spell.get('components'),
            'Bonus Options': spell.get('bonus_options'),
            'Effects': spell.get('effects')
        }
        self.details_text.setPlainText(json.dumps(details, indent=2))
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
