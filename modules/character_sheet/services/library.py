"""Persistent collection of character sheets shared across workspaces."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from modules.character_sheet.model import CharacterSheet, character_sheet_from_dict, character_sheet_to_dict
from modules.compendium.service import Compendium

DEFAULT_LIBRARY_PATH = Path(__file__).resolve().parents[1] / "database" / "characters"


@dataclass
class CharacterRecord:
    """Container pairing a character sheet with its modifier states."""

    identifier: str
    sheet: CharacterSheet = field(default_factory=CharacterSheet)
    modifiers: Dict[str, bool] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return self.sheet.identity.name or "Unnamed Adventurer"

    @property
    def level(self) -> int:
        return self.sheet.identity.level

    @property
    def class_summary(self) -> str:
        classes = self.sheet.identity.classes or []
        if not classes:
            return "No class levels"
        return ", ".join(f"{entry.name} {entry.level}" for entry in classes)


def _serialise_record(record: CharacterRecord, compendium: Compendium | None = None) -> dict:
    return {
        "id": record.identifier,
        "sheet": character_sheet_to_dict(record.sheet, compendium=compendium),
        "modifiers": dict(record.modifiers),
    }


def _deserialise_record(payload: dict, compendium: Compendium | None = None) -> CharacterRecord:
    identifier = str(payload.get("id") or uuid.uuid4())
    sheet_payload = payload.get("sheet", {}) or {}
    modifiers_payload = payload.get("modifiers", {}) or {}
    sheet = character_sheet_from_dict(sheet_payload, compendium=compendium) if sheet_payload else CharacterSheet()
    modifiers: Dict[str, bool] = {str(key): bool(value) for key, value in modifiers_payload.items()}
    return CharacterRecord(identifier=identifier, sheet=sheet, modifiers=modifiers)


class CharacterLibrary:
    """Simple JSON-backed registry of character sheets."""

    def __init__(
        self,
        records: Iterable[CharacterRecord] | None = None,
        *,
        active_id: Optional[str] = None,
        storage_path: Path | None = None,
    ) -> None:
        self._storage_path = Path(storage_path) if storage_path else DEFAULT_LIBRARY_PATH
        self._records: Dict[str, CharacterRecord] = {}
        self._order: List[str] = []
        for record in records or []:
            self._records[record.identifier] = record
            self._order.append(record.identifier)
        self._active_id = active_id if active_id in self._records else (self._order[0] if self._order else None)

    @property
    def storage_path(self) -> Path:
        return self._storage_path

    @property
    def active_id(self) -> Optional[str]:
        return self._active_id

    @classmethod
    def load(cls, path: Path | None = None) -> "CharacterLibrary":
        storage_path = Path(path) if path else DEFAULT_LIBRARY_PATH
        
        if not storage_path.exists():
            storage_path.mkdir(parents=True, exist_ok=True)
            return cls([], storage_path=storage_path)

        # Load from directory
        records = []
        active_id = None
        order = []
        
        # Load meta
        meta_path = storage_path / "_meta.json"
        if meta_path.exists():
            try:
                with meta_path.open("r", encoding="utf-8") as f:
                    meta = json.load(f)
                    active_id = meta.get("active_id")
                    order = meta.get("order", [])
            except Exception:
                pass

        # Try to load compendium once for batch operations
        try:
            compendium = Compendium.load()
        except Exception:
            compendium = None

        # Load characters
        for file_path in storage_path.glob("*.json"):
            if file_path.name == "_meta.json":
                continue
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    records.append(_deserialise_record(data, compendium=compendium))
            except Exception:
                continue
        
        # Reorder based on meta if possible
        if order:
            record_map = {r.identifier: r for r in records}
            ordered_records = []
            for uid in order:
                if uid in record_map:
                    ordered_records.append(record_map[uid])
            # Add any new/unknown records at the end
            for r in records:
                if r.identifier not in order:
                    ordered_records.append(r)
            records = ordered_records

        return cls(records, active_id=active_id, storage_path=storage_path)

    @classmethod
    def load_default(cls) -> "CharacterLibrary":
        return cls.load(DEFAULT_LIBRARY_PATH)

    def save(self) -> Path:
        self._storage_path.mkdir(parents=True, exist_ok=True)
        
        # Save meta
        meta = {
            "active_id": self._active_id,
            "order": self._order
        }
        with (self._storage_path / "_meta.json").open("w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # Save characters
        try:
            compendium = Compendium.load()
        except Exception:
            compendium = None

        current_ids = set()
        for identifier, record in self._records.items():
            current_ids.add(identifier)
            payload = _serialise_record(record, compendium=compendium)
            file_path = self._storage_path / f"{identifier}.json"
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        
        # Clean up deleted characters (files that exist but are not in records)
        for file_path in self._storage_path.glob("*.json"):
            if file_path.name == "_meta.json":
                continue
            # Assuming filename is {uuid}.json
            stem = file_path.stem
            if stem not in current_ids:
                # Only delete if it looks like a UUID to avoid deleting random user files
                try:
                    uuid.UUID(stem)
                    file_path.unlink()
                except ValueError:
                    pass
                    
        return self._storage_path

    def list_records(self) -> List[CharacterRecord]:
        return [self._records[identifier] for identifier in self._order]

    def get(self, identifier: str | None) -> Optional[CharacterRecord]:
        if not identifier:
            return None
        return self._records.get(identifier)

    def ensure_active(self) -> Optional[CharacterRecord]:
        if self._active_id and self._active_id in self._records:
            return self._records[self._active_id]
        if self._order:
            self._active_id = self._order[0]
            return self._records[self._active_id]
        return None

    def set_active(self, identifier: str | None) -> None:
        if identifier and identifier in self._records:
            self._active_id = identifier
        elif not self._order:
            self._active_id = None
        else:
            self._active_id = self._order[0]

    def create_record(self, sheet: CharacterSheet | None = None, modifiers: Dict[str, bool] | None = None) -> CharacterRecord:
        identifier = str(uuid.uuid4())
        record = CharacterRecord(identifier=identifier, sheet=sheet or CharacterSheet(), modifiers=dict(modifiers or {}))
        self._records[identifier] = record
        self._order.append(identifier)
        if not self._active_id:
            self._active_id = identifier
        self.save()
        return record

    def update_record(self, identifier: str, sheet: CharacterSheet, modifiers: Dict[str, bool]) -> None:
        if identifier not in self._records:
            raise KeyError(f"Unknown character id: {identifier}")
        self._records[identifier].sheet = sheet
        self._records[identifier].modifiers = dict(modifiers)
        self.save()

    def delete_record(self, identifier: str) -> None:
        if identifier not in self._records:
            return
        self._records.pop(identifier)
        if identifier in self._order:
            self._order.remove(identifier)
        if self._active_id == identifier:
            self._active_id = self._order[0] if self._order else None
        self.save()

    def replace_all(self, records: Iterable[CharacterRecord], *, active_id: Optional[str] = None) -> None:
        self._records = {}
        self._order = []
        for record in records:
            self._records[record.identifier] = record
            self._order.append(record.identifier)
        self._active_id = active_id if active_id in self._records else (self._order[0] if self._order else None)
        self.save()

    def clone(self) -> "CharacterLibrary":
        return CharacterLibrary(
            [CharacterRecord(identifier=record.identifier, sheet=record.sheet, modifiers=dict(record.modifiers)) for record in self.list_records()],
            active_id=self._active_id,
            storage_path=self._storage_path,
        )


__all__ = [
    "CharacterLibrary",
    "CharacterRecord",
    "DEFAULT_LIBRARY_PATH",
]
