# Living Scroll – D&D 2024 Rules + Character + Spell Math Toolkit

Living Scroll is a modular PySide6 desktop app that serves as a modern companion for D&D 2024. It unifies rule browsing, character building, and spell probability analysis into a single, cohesive experience.

## Features

- **Modular Architecture** – Organized into distinct feature modules (`core`, `compendium`, `character_sheet`, `spell_grapher`, etc.).
- **Filesystem Compendium (target architecture)** – Rules content is stored as a nested folder tree of Markdown files using YAML frontmatter under `modules/compendium/data/dnd_2024/`. version control.
- **Character Sheet** – A clear, read-only view of your character's derived stats and features, powered by a streamlined progression engine.
- **Spell Grapher** – Analyze spell usage, damage probabilities, and effect distributions.
- **Unified Build System** – single python script (`builder/build.py`) handles cross-platform building and distribution.

## Quick Start

### 1. Install Dependencies
This project uses `pyproject.toml` for dependency management.

```bash
pip install .
# OR for development (editable mode)
pip install -e .
```

### 2. Run the Application
Launch the application directly from the source:

```bash
python main.py
# OR
python -m .
```

### 3. Build Executable
Create a standalone executable for your platform (Windows/Linux/macOS):

```bash
python builder/build.py
```
The output will be located in `builder/output/LivingScroll`.

## Project Structure

The codebase follows a strict modular design:

- **`modules/`**: Contains all feature logic.
    - **`core/`**: Shared services (Logging, Settings, Theme) and UI widgets.
    - **`compendium/`**: Rules loading and data management.
    - **`character_sheet/`**: Character management and sheet UI.
    - **`spell_grapher/`**: Spell analysis tools.
- **`database/`**: Stores local data.
    - **`compendium/`**: The Markdown/JSON dataset.
- **`builder/`**: Build scripts and output artifacts.
- **`tests/`**: Unit tests.

## Development

### Running Tests
Run the test suite using `unittest` or `pytest`:

```bash
python -m unittest discover tests
```

### Adding Content
See `docs/COMPENDIUM_GUIDE.md` for details on how to add new rules, spells, or classes using Markdown files.

## License

This project is provided as-is for educational and personal use.
