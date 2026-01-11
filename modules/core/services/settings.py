from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set

from PySide6.QtCore import QSettings

# Constants
KEY_RULESET = "compendium/ruleset"
KEY_MODULES = "compendium/modules"
KEY_DEV_MODE = "app/dev_mode"
KEY_MINIMIZE_TO_TRAY = "app/minimize_to_tray"

DEFAULT_RULESET = "dnd_2024"
REQUIRED_MODULES = {"players_handbook"}

class Settings:
    """Simple wrapper around QSettings for application-wide preferences."""

    def __init__(self) -> None:
        self._settings = QSettings("LivingScroll", "LivingScroll")

    @property
    def ruleset(self) -> str:
        return str(self._settings.value(KEY_RULESET, DEFAULT_RULESET))

    @ruleset.setter
    def ruleset(self, value: str) -> None:
        self._settings.setValue(KEY_RULESET, value)

    @property
    def active_modules(self) -> Set[str]:
        val = self._settings.value(KEY_MODULES)
        modules = set()
        if val is None:
            # Default to all available modules if not configured
            modules = set(self.available_modules(self.ruleset))
        elif isinstance(val, list):
            modules = set(str(v) for v in val)
        elif val:
            modules = {str(val)}
            
        # Always include required modules
        modules.update(REQUIRED_MODULES)
        return modules

    @active_modules.setter
    def active_modules(self, modules: Set[str]) -> None:
        # Ensure required modules are always present
        modules.update(REQUIRED_MODULES)
        self._settings.setValue(KEY_MODULES, list(modules))

    @property
    def dev_mode(self) -> bool:
        return bool(self._settings.value(KEY_DEV_MODE, False, type=bool))

    @dev_mode.setter
    def dev_mode(self, enabled: bool) -> None:
        self._settings.setValue(KEY_DEV_MODE, enabled)

    @property
    def minimize_to_tray(self) -> bool:
        return bool(self._settings.value(KEY_MINIMIZE_TO_TRAY, True, type=bool))

    @minimize_to_tray.setter
    def minimize_to_tray(self, enabled: bool) -> None:
        self._settings.setValue(KEY_MINIMIZE_TO_TRAY, enabled)

    def _get_compendium_root(self) -> Path:
        """Resolve the root directory of the compendium data."""
        # Check for frozen (PyInstaller)
        import sys
        if getattr(sys, "frozen", False):
            # In one-dir mode, this usually points to _internal
            # But we should rely on sys.executable logic for onedir if _MEIPASS is tricky
            # Standard PyInstaller: sys._MEIPASS exists in both onefile and onedir
            base_path = Path(sys._MEIPASS)
        else:
            # Dev mode: modules/core/services/settings.py -> up to root -> modules
            # We want modules/compendium/data
            base_path = Path(__file__).resolve().parent.parent.parent.parent
            
        return base_path / "modules" / "compendium" / "data"

    def available_rulesets(self) -> List[str]:
        """Scan modules/compendium/data for available ruleset folders."""
        root = self._get_compendium_root()
        if not root.exists():
            return []
        return [d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith("_") and not d.name == "__pycache__"]

    def available_modules(self, ruleset: str) -> List[str]:
        """Scan the ruleset folder for available modules."""
        root = self._get_compendium_root() / ruleset
        if not root.exists():
            return []
        return [d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith("_") and not d.name == "__pycache__"]

    def get_module_metadata(self, ruleset: str, module: str) -> Dict[str, Any]:
        """Retrieve metadata for a specific module."""
        path = self._get_compendium_root() / ruleset / module / "metadata.json"
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def get_module_path(self, ruleset: str, module: str) -> Path | None:
        """Resolve the absolute filesystem path for a module."""
        path = self._get_compendium_root() / ruleset / module
        if path.exists() and path.is_dir():
            return path
        return None

_instance = None

def get_settings() -> Settings:
    global _instance
    if _instance is None:
        _instance = Settings()
    return _instance
