"""Dialog widgets for the SpellGraphix GUI."""

try:
	from .feat_entry_dialog import FeatEntryDialog
	from .global_settings_dialog import GlobalSettingsDialog
	from .spellcasting_settings_dialog import SpellcastingSettingsDialog
except ModuleNotFoundError:
	# Optional dependency (PySide6) may be absent in minimal environments.
	FeatEntryDialog = None  # type: ignore[assignment]
	GlobalSettingsDialog = None  # type: ignore[assignment]
	SpellcastingSettingsDialog = None  # type: ignore[assignment]

__all__ = ["SpellcastingSettingsDialog", "GlobalSettingsDialog", "FeatEntryDialog"]
