# Living Scroll – D&D 2024 Rules + Character + Spell Math Toolkit

Living Scroll is a PySide6 desktop app that aims to unify three things under one consistent data model:

- A **rule compendium** you can browse in-app.
- A **character builder/sheet** where most fields are derived and read-only.
- A **spell math + plotting** toolkit that can evaluate spell effects under character modifiers and compare outcomes.

The project is actively migrating toward a single source of truth: a **filesystem-based compendium** (nested folders + small JSON files). Legacy database-era code still exists in the repository, but the target architecture removes runtime databases entirely.

## Features

- **Modular Launcher** – A hub window launches workspaces (Spell Grapher, Character Sheet, Compendium, and future modules).
- **Filesystem Compendium (target architecture)** – Rules content is stored as a nested folder tree of Markdown files using YAML frontmatter under `database/compendium/dnd_2024/`.
- **Character Sheet: derived-first** – Builder choices are sources-of-truth; displayed sheet stats are derived and read-only.
- **Spell Math + Plotting** – A reusable dice/probability backend.

## Quick Start

1. **Install dependencies** (Python 3.10+ recommended):

   ```bash
   pip install -r requirements.txt
   ```

2. **Launch Living Scroll**:

   ```bash
   python -m gui.app
   ```

   (Or `python __main__.py`)

3. **Select spells and plot** – Double-click rows in the left table to curate selections.

## Compendium Dataset Layout
 
The dataset is a tree of Markdown files (`.md`) with YAML frontmatter. The loader ingests `database/compendium/dnd_2024/` recursively.

Example:

```
database/compendium/dnd_2024/
   players_handbook/
      metadata.json
      classes/
         wizard/
            base.md
            subclasses/
               evoker.md
      spells/
         fireball.md
      rules/
         combat.md
   eberron_forge_of_the_artificer/
      classes/
         artificer/
            base.md
```

Each record can include:

- **Human-readable text** for compendium browsing.
- An optional **short description** suitable for the character sheet when mechanics aren’t fully captured by stats.
- Optional **structured grants/modifiers** (to derive character stats and validate choices).
- For spells and other active mechanics: optional **math definitions** that the backend can evaluate under modifiers.

## Content Sourcing & Licensing (Important)

This project is intended for **personal/local use only**.

The working plan for this repo is that a local compendium dataset may include rules text sourced from sites like `dnd2024.wikidot.com` to make the in-app compendium readable.

Important: I’m not a lawyer, and “personal use” does not automatically grant redistribution rights. Treat any third‑party rules text as **local-only**:

- Do not distribute builds or datasets that embed third‑party text unless you have explicit permission.
- Prefer keeping generated datasets out of version control.

## Building Standalone Apps

PyInstaller is used to create distributable builds.

The long-term goal is: packaged apps ship only code + UI assets, while the compendium dataset is provided separately (or generated/imported by the user), keeping licensing boundaries clear.

- **Linux:**

   ```bash
   ./scripts/build_linux.sh
   ```

- **Windows (PowerShell):**

   ```powershell
   pwsh -File scripts/build_windows.ps1
   ```

Both scripts clean PyInstaller’s working directories and move the final artifact into `build/LivingScroll`, making it easy to add the entire `build/` directory to `.gitignore`.

## Testing

- Automated tests live in the `tests/` package and cover the dice math, plotting helpers, and core services.
- Run the full suite with:

   ```bash
   python -m unittest discover
   ```

   The test package forces matplotlib to use the `Agg` backend and sets `QT_QPA_PLATFORM=offscreen`, so everything runs headlessly in CI.

## Usage Guide

### Launcher & Workspaces

- The entry window presents large tiles for each workspace.
- **Spell Grapher** focuses on spell selection and probability visualizations.
- **Character Sheet** focuses on choosing sources-of-truth and inspecting derived results.

### Spell Browser & Filters

- Use the filter input to narrow spells quickly (syntax depends on the current filter implementation).

### Plotting

- Select one spell to render a distribution window.
- Select 2–3 spells to compare them.

## Architecture Overview

- **GUI (`gui/`)** – PySide6 widgets, dialogs, and windows.
- **Backend (`backend/`)** – Dice math, probability calculations, and plotting.
- **Compendium services (`services/compendium.py`)** – Loads the filesystem dataset and exposes query helpers.
- **Rules/derivation services (`services/`, `character_sheet/`)** – Apply grants/modifiers and compute derived stats.

If you need the historical CLI workflow, refer to commits prior to the GUI-only refactor. All new development happens in the GUI and backend packages described above.

## Requirements

- Python 3.x
- matplotlib
- PySide6

Install required packages (if not already installed):

```bash
pip install -r requirements.txt
```

## Status Note (Migration In Progress)

Some parts of the codebase still reflect the earlier SQLite-centric implementation. The roadmap is to remove these in favor of:

- Compendium files as the only rules dataset.
- A single grants/modifiers pipeline driving derivations.
- Optional local tooling to generate datasets (kept out of version control unless redistributable).

## License

This project is provided as-is for educational and personal use.
