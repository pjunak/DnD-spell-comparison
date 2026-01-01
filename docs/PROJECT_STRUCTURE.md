# Project Structure

This document provides a comprehensive overview of the SpellGraphix codebase architecture, explaining the purpose of each module and how they interact.

---

## Overview

SpellGraphix follows a layered architecture separating concerns across four primary layers:

1. **Data Layer** — Persistent storage for characters and game content.
2. **Service Layer** — Business logic, rules engine, and data loading.
3. **Presentation Layer** — PySide6-based graphical user interface.
4. **Utility Layer** — Mathematical computations, dice logic, and plotting.

---

## Directory Structure

```
SpellGraphix/
├── Assets/                  # Application icons and static resources
├── character_sheet/         # Character data model and I/O
├── database/                # Persistent data storage
│   ├── characters/          # User character files (JSON)
│   └── compendium/          # Game content (Markdown + YAML)
├── docs/                    # Project documentation
├── gui/                     # PySide6 user interface
│   ├── dialogs/             # Modal dialog windows
│   ├── resources/           # UI resources (stylesheets)
│   ├── utils/               # UI helper functions
│   ├── widgets/             # Reusable UI components
│   └── windows/             # Top-level application windows
├── scripts/                 # Build and maintenance scripts
├── services/                # Business logic and rules engine
│   └── spellcasting/        # Spellcasting subsystem
├── spell_graphs/            # Dice math and visualization
│   └── spells/              # Spell parsing utilities
└── tests/                   # Unit test suite
```

---

## Module Descriptions

### Data Layer

#### `database/`
Contains all persistent application data.

| Subdirectory | Purpose |
|--------------|---------|
| `characters/` | Stores user-created characters as individual JSON files. |
| `compendium/` | Contains the game content library. See [COMPENDIUM_GUIDE.md](COMPENDIUM_GUIDE.md). |

#### `character_sheet/`
Defines the in-memory representation of a character.

| File | Purpose |
|------|---------|
| `model.py` | The `Character` class — the canonical data structure for a character's state. |
| `io.py` | Serialization and deserialization of characters to/from JSON. |
| `spell_profile.py` | Spell-related character data (prepared spells, spell slots). |

---

### Service Layer

#### `services/`
The core business logic layer. Services consume data from the character model and compendium, then compute derived statistics according to D&D 2024 rules.

| File | Purpose |
|------|---------|
| `compendium.py` | Loads and queries the compendium dataset (spells, items, classes, rules). |
| `character_library.py` | Manages the collection of saved characters. |
| `logger.py` | Application-wide logging infrastructure. |

**Stat Calculators:**

| File | Computed Statistic |
|------|--------------------|
| `armor_class.py` | Armor Class (AC) from equipment, Dexterity, and features. |
| `hit_points.py` | Maximum and current hit points. |
| `initiative.py` | Initiative bonus. |
| `speed.py` | Movement speeds (walking, flying, swimming). |
| `senses.py` | Darkvision, blindsight, and other senses. |
| `passive_scores.py` | Passive Perception, Investigation, Insight. |
| `resistances.py` | Damage resistances, vulnerabilities, and immunities. |
| `condition_immunities.py` | Condition immunities granted by species/class/items. |

#### `services/spellcasting/`
Handles all spellcasting-related computations.

| File | Purpose |
|------|---------|
| `slots.py` | Spell slot progression and multiclass slot calculation. |
| `preparation.py` | Number of prepared spells, known spells limits. |
| `dc_attack.py` | Spell save DC and spell attack modifier. |

---

### Presentation Layer

#### `gui/`
The graphical user interface, built with PySide6 (Qt 6).

| File | Purpose |
|------|---------|
| `app.py` | Application entry point. Initializes Qt, applies themes, handles global exceptions. |
| `application_context.py` | Shared state accessible across windows (current character, compendium). |
| `resources.py` | Icon loading, theme constants, and the dark mode stylesheet. |

#### `gui/windows/`
Top-level application windows.

| File | Purpose |
|------|---------|
| `launcher_window.py` | The main hub with tiles for each module. |
| `main_window.py` | The character sheet view. |
| `compendium_window.py` | Rules browser (Classes, Species, Backgrounds, Rules). |
| `spell_window.py` | Spell browser with level and school filters. |
| `monster_window.py` | Monster Manual browser with CR/Type/Size filters. |
| `equipment_window.py` | Equipment and magic item browser. |

#### `gui/dialogs/`
Modal dialogs for user input.

| File | Purpose |
|------|---------|
| `class_entry_dialog.py` | Add or modify class levels. |
| `spell_source_dialog.py` | Manage spell sources (class, feat, item). |
| `character_creation_dialog.py` | Create a new character. |

#### `gui/widgets/`
Reusable UI components.

| File | Purpose |
|------|---------|
| `stat_block.py` | Displays a single ability score with modifier. |
| `compendium_spells_table.py` | Filterable table of spells. |
| `compendium_equipment_table.py` | Filterable table of equipment. |
| `frameless_window.py` | Base class for custom-styled borderless windows. |

#### `gui/resources/`
Static UI resources.

| Subdirectory | Purpose |
|--------------|---------|
| `styles/` | CSS stylesheets for the compendium HTML renderer. |

---

### Utility Layer

#### `spell_graphs/`
Mathematical backend for dice probability and visualization.

| File | Purpose |
|------|---------|
| `dices.py` | Dice notation parser (e.g., `2d6+3`) and probability distributions. |
| `calculations.py` | Mathematical utilities for expected values and comparisons. |
| `plotting.py` | Matplotlib-based graph generation for spell damage analysis. |

#### `spell_graphs/spells/`
Spell-specific parsing and filtering utilities.

---

### Build & Maintenance

#### `scripts/`
Utility scripts for building and maintaining the project.

| File | Purpose |
|------|---------|
| `build_linux.sh` | PyInstaller build script for Linux. |
| `build_windows.ps1` | PyInstaller build script for Windows. |
| `compendium_audit.py` | Audits compendium files for completeness. |

---

## Entry Points

| Command | Description |
|---------|-------------|
| `python -m gui.app` | Launch the GUI application. |
| `python __main__.py` | Alternative entry point (same as above). |
| `python -m unittest discover` | Run the test suite. |

---

## Related Documentation

- [COMPENDIUM_GUIDE.md](COMPENDIUM_GUIDE.md) — Compendium structure and data schema.
- [README.md](../README.md) — Project overview and quick start guide.
