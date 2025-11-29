
# SpellGraphix – Plotting D&D 5e Spells

This project lets you visualize the probability distributions of D&D spells and cantrips as a function of spell (or effective) level. The modern UI is entirely PySide6-based and focuses on browsing spells, curating selections, and producing interactive matplotlib plots.

## Features

- **Single Spell Plotting** – Inspect the probability distribution for a chosen spell (or cantrip) across its available levels. Hover over a point to see percentile-style summaries.
- **Comparison Mode** – Compare up to 3 spells (or cantrips) from the same category. Levels and spells receive distinct colors/linestyles, and clicking legends isolates the series you care about.
- **Filterable Spell Browser** – Search by name, level, school, casting time, duration, or components with quick chips and auto-complete.
- **JSON Import/Export from the Toolbar** – Bring in homebrew content or back up the current database without leaving the GUI. Standard file dialogs keep the workflow familiar.
- **Backend Probability Engine** – Dice math, scaling logic, and plotting primitives live in the `backend/` package so they can be reused or tested independently of the GUI.

## Quick Start

1. **Install dependencies** (Python 3.10+ recommended):

   ```bash
   pip install -r requirements.txt
   ```

2. **Launch SpellGraphix**:

   ```bash
   python gui.py
   ```

   Running `python __main__.py` is also supported and simply forwards to the SpellGraphix launcher.

3. **Select spells and plot** – Double-click rows in the left table to curate selections. Use the "Generate Graph" button to open interactive matplotlib windows.

## Building Standalone Apps

PyInstaller is used to create distributable builds. The repository ships with helper scripts that ensure the packaged app starts with an empty database, forcing end users to import `spellbook.json` (or another dataset) on first launch.

- **Linux:**

   ```bash
   ./scripts/build_linux.sh
   ```

- **Windows (PowerShell):**

   ```powershell
   pwsh -File scripts/build_windows.ps1
   ```

Both scripts temporarily remove `database/spellBook.db` before invoking PyInstaller so the resulting bundle contains no preloaded data. Once the build finishes, the original database file is restored. PyInstaller’s temporary folders are deleted, and the final artifact is moved into `build/SpellGraphix`, making it easy to add the entire `build/` directory to `.gitignore`.

## Testing

- Automated tests live in the `tests/` package and cover the dice math, plotting helpers, and database import/export pipeline.
- Run the full suite with:

   ```bash
   python -m unittest discover
   ```

   The test package forces matplotlib to use the `Agg` backend and sets `QT_QPA_PLATFORM=offscreen`, so everything runs headlessly in CI.

## Usage Guide

### Spell Browser & Filters

- The left pane lists spells (or cantrips) depending on the selected dataset toggle in the toolbar.
- Use the filter input to type queries such as `school: evocation` or `level: 3`. Press Enter to add chips and narrow the table instantly.
- The "Options" menu contains quick actions (clear filters, clear selections, allow inline editing, toggle non-damaging spells).

### Plotting

- Select one spell to render a level-by-level distribution window.
- Select 2–3 spells to compare them; shared levels receive unique linestyles and markers.
- Legends are interactive—click to isolate spells or levels. Hovering reveals exact probabilities and cumulative ratios.

### Dataset Import/Export

- The "Database" toolbar menu hosts **Import Dataset** and **Export Dataset**.
- Import expects a JSON file that matches the schema used by the bundled SQLite database.
- Export writes the current database contents to JSON so you can share or version-control your tweaks externally.

## Architecture Overview

- **GUI (`gui.py`)** – Houses the PySide6 widgets, dialogs, and plotting triggers. The module now exposes a `main()` helper used both by `python gui.py` and by the repository's `__main__.py` entry point.
- **Backend (`backend/`)** – Contains the probability calculations (`calculations.py`), dice helpers (`dices.py`), and matplotlib plotting functions (`plotting.py`). The legacy root modules are thin compatibility shims that re-export the backend implementations.
- **Database utilities (`database/`)** – Manage SQLite schema creation, spell/modifier loading, and JSON import/export routines shared by the GUI.

If you need the historical CLI workflow, refer to commits prior to the GUI-only refactor. All new development happens in the GUI and backend packages described above.

## Requirements

- Python 3.x
- matplotlib
- PySide6

Install required packages (if not already installed):

```bash
pip install -r requirements.txt
```

## Database & Dataset Workflow

- The SQLite schema is stored in `database/schema.sql`. Update this file when you need to add or modify tables/columns.
- Structured metadata that maps tables to JSON payloads lives in `database/schema.py`. It defines each dataset section, field defaults, and export ordering. Adjust these descriptors to keep the runtime import/export code stable across schema changes.
- Runtime helpers (`database/management.py`) enforce the schema, load spells for the app, and handle JSON import/export. Because they consume the metadata from `schema.py`, they typically do not need changes when the schema evolves.
- The GUI calls into `database.management`, so database logic stays consolidated even without the CLI.

## License

This project is provided as-is for educational and personal use.
