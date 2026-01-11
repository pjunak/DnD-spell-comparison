# Project Structure

Living Scroll uses a modular architecture to separate concerns and improve maintainability. The codebase is organized primarily within the `modules/` directory, with top-level scripts handling entry points and build processes.

## Directory Layout

```
Living-scroll/
├── builder/                # Build system scripts and artifacts
│   ├── build.py            # Unified cross-platform build script
│   └── output/             # Final executable location (ignored by git)
├── database/               # Local data storage
│   └── compendium/         # Rule data (Markdown/YAML/JSON)
├── modules/                # Core application logic, split by domain
│   ├── core/               # Shared infrastructure
│   │   ├── services/       # Logging, Settings, Event Bus
│   │   └── ui/             # Common widgets, Theme, Resources
│   ├── compendium/         # Data loading and Compendium service
│   ├── character_sheet/    # Character management and Sheet UI
│   ├── spell_grapher/      # Spell plotting and mechanics
│   ├── dashboard/          # Main launcher/hub window
│   ├── rules_explorer/     # UI for browsing the compendium
│   └── ... (other feature modules)
├── tests/                  # Unit tests
├── docs/                   # Documentation
├── Assets/                 # Application icons and binary assets
├── main.py                 # Application Entry Point
├── pyproject.toml          # Project dependencies and configuration
└── LivingScroll.spec       # PyInstaller configuration
```

## Key Modules

### Core (`modules.core`)
The backbone of the application. It provides:
- **Services**: Singleton-like access to `Settings`, `Logger`.
- **UI**: A unified theme (`theme.py`), shared widgets (buttons, frameless windows), and dialogs.

### Compendium (`modules.compendium`)
Handles the loading of rule data from the filesystem. It parses Markdown files with YAML frontmatter into structured Python objects for use by other modules.

### Character Sheet (`modules.character_sheet`)
Manages the `CharacterSheet` data model and the UI for displaying it. It relies on `modules.core.services` for settings and `modules.compendium` for rule lookups.

### Dashboard (`modules.dashboard`)
The entry point UI (`LauncherWindow`) that allows users to select a workspace (Character, Spells, Admin, etc.).

## Build System (`builder/`)
The project uses a custom Python script (`builder/build.py`) that wraps `PyInstaller`.
- It cleans previous builds.
- It determines the OS and sets appropriate flags.
- It moves the final artifact to `builder/output/LivingScroll`.
