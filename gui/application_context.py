"""Shared state container for coordinating launcher modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from character_sheet import CharacterSheet
from services.character_library import CharacterLibrary
from services.modifiers import ModifierStateSnapshot


@dataclass
class ApplicationContext:
    """Lightweight hub for sharing sheet/modifier state across modules."""

    character_sheet: CharacterSheet | None = None
    modifier_snapshot: ModifierStateSnapshot | None = None
    modifier_states: Dict[str, bool] = field(default_factory=dict)
    character_library: CharacterLibrary | None = None
    active_character_id: str | None = None

    def clone(self) -> "ApplicationContext":
        """Return a shallow clone pointing at the same underlying state."""

        return ApplicationContext(
            character_sheet=self.character_sheet,
            modifier_snapshot=self.modifier_snapshot,
            modifier_states=dict(self.modifier_states),
            character_library=self.character_library.clone() if self.character_library else None,
            active_character_id=self.active_character_id,
        )

    def ensure_library(self) -> CharacterLibrary:
        """Ensure callers always get a loaded CharacterLibrary instance."""

        if not self.character_library:
            self.character_library = CharacterLibrary.load_default()
        if self.character_library.active_id != self.active_character_id:
            self.active_character_id = self.character_library.active_id
        return self.character_library


__all__ = ["ApplicationContext"]
