"""Window classes used by the GUI."""

try:
	from .character_sheet_hub import CharacterSheetHubWindow
	from .compendium_window import CompendiumWindow
	from .graph_window import GraphWindow
	from .launcher_window import LauncherWindow
	from .main_window import MainWindow
except ModuleNotFoundError:
	# Optional dependency (PySide6) may be absent in minimal environments.
	CharacterSheetHubWindow = None  # type: ignore[assignment]
	CompendiumWindow = None  # type: ignore[assignment]
	GraphWindow = None  # type: ignore[assignment]
	LauncherWindow = None  # type: ignore[assignment]
	MainWindow = None  # type: ignore[assignment]

__all__ = [
	"CharacterSheetHubWindow",
	"CompendiumWindow",
	"GraphWindow",
	"LauncherWindow",
	"MainWindow",
]
