"""Utilities for loading and tracking modifier definitions/states."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Tuple

from services.compendium import Compendium

from .defaults import get_default_modifier_definitions

EXCLUDED_MODIFIER_NAMES = {
	"Magic Item: Wand of the War Mage (+1)",
	"Subclass: Abjurer",
	"Subclass: Evoker",
	"Subclass: Life Domain",
	"Subclass: Fiend Patron",
}


class ModifierServiceError(RuntimeError):
	"""Base exception for modifier service failures."""


class ModifierLoadError(ModifierServiceError):
	"""Raised when modifier definitions fail to load from persistence."""


@dataclass
class ModifierStateSnapshot:
	"""Immutable snapshot of modifier definitions and resolved states."""

	definitions: List[dict]
	states: Dict[str, bool]


class ModifierStateService:
	"""Centralized helper that loads modifier definitions and resolves states."""

	def __init__(
		self,
		loader: Callable[[], List[dict]] | None = None,
		saver: Callable[[Iterable[dict]], None] | None = None,
		defaults_provider: Callable[[], List[dict]] | None = None,
	) -> None:
		self._loader = loader or _load_modifiers_from_compendium
		self._saver = saver
		self._defaults_provider = defaults_provider or get_default_modifier_definitions
		self._definitions: List[dict] = []
		self._states: Dict[str, bool] = {}

	@property
	def definitions(self) -> List[dict]:
		return list(self._definitions)

	@property
	def states(self) -> Dict[str, bool]:
		return dict(self._states)

	def refresh(self, existing_states: Dict[str, bool] | None = None) -> ModifierStateSnapshot:
		"""Reload definitions from backing storage and resolve states."""

		defaults = self._defaults_provider() or []
		definitions = self._load_with_defaults(defaults)
		definitions = self._filter_excluded_definitions(definitions)
		definitions = self._sort_definitions(definitions)
		resolved_states = self._merge_states(definitions, existing_states or {})

		self._definitions = definitions
		self._states = resolved_states
		return ModifierStateSnapshot(self.definitions, self.states)

	def update_states(self, states: Dict[str, bool]) -> None:
		"""Persist a new in-memory snapshot of modifier states."""

		self._states = self._merge_states(self._definitions, states)

	def _load_with_defaults(self, defaults: List[dict]) -> List[dict]:
		try:
			definitions = self._loader()
		except Exception as exc:  # pragma: no cover - database error propagation
			raise ModifierLoadError("Failed to load modifiers from storage") from exc

		return definitions or list(defaults)

	def _safe_load(self, fallback: List[dict]) -> List[dict]:
		try:
			return self._loader()
		except Exception:
			return list(fallback)

	def _filter_excluded_definitions(self, definitions: Iterable[dict]) -> List[dict]:
		if not EXCLUDED_MODIFIER_NAMES:
			return list(definitions)
		filtered: List[dict] = []
		for definition in definitions:
			name = str(definition.get("name") or "")
			if name in EXCLUDED_MODIFIER_NAMES:
				continue
			filtered.append(definition)
		return filtered

	@staticmethod
	def _merge_states(definitions: Iterable[dict], states: Dict[str, bool]) -> Dict[str, bool]:
		resolved: Dict[str, bool] = {}
		for definition in definitions:
			name = definition.get("name")
			if not name:
				continue
			default_state = bool(definition.get("default_enabled", False))
			resolved[name] = bool(states.get(name, default_state))
		return resolved

	@staticmethod
	def _sort_definitions(definitions: Iterable[dict]) -> List[dict]:
		return sorted(
			definitions,
			key=lambda entry: (str(entry.get("scope") or "spell").lower(), str(entry.get("name", "")).lower()),
		)



def _load_modifiers_from_compendium() -> List[dict]:
	compendium = Compendium.load()
	records = compendium.records("modifiers")
	return [dict(entry) for entry in records if isinstance(entry, dict)]
__all__ = [
	"ModifierLoadError",
	"ModifierServiceError",
	"ModifierStateService",
	"ModifierStateSnapshot",
]
