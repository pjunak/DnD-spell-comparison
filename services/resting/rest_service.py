"""Utilities for applying D&D rest mechanics to character sheets."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Protocol

from character_sheet import CharacterSheet


class RestType(str, Enum):
	"""Rest categories supported by the engine."""

	SHORT_REST = "short_rest"
	LONG_REST = "long_rest"

	@classmethod
	def from_value(cls, value: RestType | str) -> RestType:
		if isinstance(value, RestType):
			return value
		text = str(value or "").lower()
		return cls.SHORT_REST if text.startswith("short") else cls.LONG_REST


class RestHandler(Protocol):
	"""Protocol for components that mutate a character on rest."""

	def apply(self, sheet: CharacterSheet, rest_type: RestType) -> None: ...


@dataclass
class SpellSlotRestHandler:
	"""Rest handler that refreshes spell slot state based on rest type."""

	def apply(self, sheet: CharacterSheet, rest_type: RestType) -> None:  # pragma: no cover - thin adapter
		if not sheet or not sheet.spellcasting:
			return
		sheet.spellcasting.reset_slots(rest_type.value)
		sheet.spellcasting.sync_slot_schedule()


class RestManager:
	"""Coordinator that applies rest logic to one or more characters."""

	def __init__(self, handlers: Iterable[RestHandler] | None = None) -> None:
		self._handlers: List[RestHandler] = list(handlers or [SpellSlotRestHandler()])

	def add_handler(self, handler: RestHandler) -> None:
		"""Register an additional handler that runs for each rest."""

		self._handlers.append(handler)

	def rest(self, characters: Iterable[CharacterSheet], rest_type: RestType | str) -> None:
		"""Apply a rest to every character in *characters*."""

		rest_kind = RestType.from_value(rest_type)
		for sheet in characters:
			self._apply_handlers(sheet, rest_kind)

	def rest_one(self, sheet: CharacterSheet, rest_type: RestType | str) -> None:
		"""Apply a rest to a single character."""

		self._apply_handlers(sheet, RestType.from_value(rest_type))

	def _apply_handlers(self, sheet: CharacterSheet, rest_type: RestType) -> None:
		for handler in self._handlers:
			handler.apply(sheet, rest_type)