from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set

from PySide6.QtCore import QSettings

# Constants
KEY_RULESET = "compendium/ruleset"
KEY_MODULES = "compendium/modules"
KEY_DEV_MODE = "app/dev_mode"

DEFAULT_RULESET = "dnd_2024"
REQUIRED_MODULES = {"players_handbook"}

class Settings:
    """Simple wrapper around QSettings for application-wide preferences."""

    def __init__(self) -> None:
        self._settings = QSettings("SpellGraphix", "SpellGraphix")

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

    def available_rulesets(self) -> List[str]:
        """Scan database/compendium for available ruleset folders."""
        root = Path(__file__).resolve().parents[1] / "database" / "compendium"
        if not root.exists():
            return []
        return [d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith("_") and not d.name == "__pycache__"]

    def available_modules(self, ruleset: str) -> List[str]:
        """Scan the ruleset folder for available modules."""
        root = Path(__file__).resolve().parents[1] / "database" / "compendium" / ruleset
        if not root.exists():
            return []
        return [d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith("_") and not d.name == "__pycache__"]

    def get_module_metadata(self, ruleset: str, module: str) -> Dict[str, Any]:
        """Retrieve metadata for a specific module."""
        path = Path(__file__).resolve().parents[1] / "database" / "compendium" / ruleset / module / "metadata.json"
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

_instance = None

def get_settings() -> Settings:
    global _instance
    if _instance is None:
        _instance = Settings()
    return _instance
