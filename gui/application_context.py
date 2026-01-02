"""Shared state container for coordinating launcher modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict

from character_sheet import CharacterSheet
from services.character_library import CharacterLibrary
from services.modifiers import ModifierStateSnapshot

if TYPE_CHECKING:
    from services.compendium import Compendium


@dataclass
class ApplicationContext:
    """Lightweight hub for sharing sheet/modifier state across modules."""

    character_sheet: CharacterSheet | None = None
    modifier_snapshot: ModifierStateSnapshot | None = None
    modifier_states: Dict[str, bool] = field(default_factory=dict)
    character_library: CharacterLibrary | None = None
    active_character_id: str | None = None
    _compendium: "Compendium | None" = field(default=None, repr=False)

    def clone(self) -> "ApplicationContext":
        """Return a shallow clone pointing at the same underlying state."""

        return ApplicationContext(
            character_sheet=self.character_sheet,
            modifier_snapshot=self.modifier_snapshot,
            modifier_states=dict(self.modifier_states),
            character_library=self.character_library.clone() if self.character_library else None,
            active_character_id=self.active_character_id,
            _compendium=self._compendium,
        )

    def ensure_library(self) -> CharacterLibrary:
        """Ensure callers always get a loaded CharacterLibrary instance."""

        if not self.character_library:
            self.character_library = CharacterLibrary.load_default()
        if self.character_library.active_id != self.active_character_id:
            self.active_character_id = self.character_library.active_id
        return self.character_library

    def ensure_compendium(self) -> "Compendium":
        """Lazily load and cache the compendium instance."""
        if self._compendium is None:
            from services.compendium import Compendium
            self._compendium = Compendium.load()
        return self._compendium

    def invalidate_compendium(self) -> None:
        """Clear cached compendium (e.g. after settings change)."""
        self._compendium = None


__all__ = ["ApplicationContext"]

