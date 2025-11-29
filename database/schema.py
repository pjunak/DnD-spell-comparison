"""Static metadata describing the spell database and exportable dataset."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

DB_PATH = Path(__file__).resolve().parent / "spellBook.db"
DB_FILE = str(DB_PATH)
SCHEMA_SQL_PATH = Path(__file__).resolve().parent / "schema.sql"
SCHEMA_VERSION = 11
DEFAULT_CANTRIP_LEVELS = [1, 5, 11, 17]


@dataclass(frozen=True)
class FieldSpec:
    """Description of a single field in both the dataset and database."""

    key: str
    kind: str
    required: bool = False
    default: Any = None
    column: str | None = None
    omit_if_empty: bool = False

    @property
    def column_name(self) -> str:
        return self.column or self.key


@dataclass(frozen=True)
class DatasetSpec:
    """Description of one export/import section backed by a database table."""

    name: str
    table: str
    fields: Tuple[FieldSpec, ...]
    order_by: Tuple[str, ...] = ()

    def field_map(self) -> Dict[str, FieldSpec]:
        return {field.key: field for field in self.fields}

    def column_names(self) -> Tuple[str, ...]:
        return tuple(field.column_name for field in self.fields)


SPELL_FIELDS = (
    FieldSpec("name", "string", required=True),
    FieldSpec("level", "int", required=True),
    FieldSpec("school", "string", omit_if_empty=True),
    FieldSpec("casting_time", "string", omit_if_empty=True),
    FieldSpec("range", "string", omit_if_empty=True),
    FieldSpec("duration", "string", omit_if_empty=True),
    FieldSpec("components", "list[str]", default=[], omit_if_empty=True),
    FieldSpec("primary_effect", "json", required=True),
    FieldSpec("secondary_effect", "json", omit_if_empty=True),
    FieldSpec("modifiers", "list[str]", default=[], omit_if_empty=True),
)

CANTRIP_FIELDS = (
    FieldSpec("name", "string", required=True),
    FieldSpec("school", "string", omit_if_empty=True),
    FieldSpec("casting_time", "string", omit_if_empty=True),
    FieldSpec("range", "string", omit_if_empty=True),
    FieldSpec("duration", "string", omit_if_empty=True),
    FieldSpec("components", "list[str]", default=[], omit_if_empty=True),
    FieldSpec("primary_effect", "json", required=True),
    FieldSpec("secondary_effect", "json", omit_if_empty=True),
    FieldSpec("scaling_levels", "list[int]", default=DEFAULT_CANTRIP_LEVELS),
    FieldSpec("modifiers", "list[str]", default=[], omit_if_empty=True),
)

MODIFIER_FIELDS = (
    FieldSpec("name", "string", required=True),
    FieldSpec("category", "string", omit_if_empty=True),
    FieldSpec("scope", "string", default="spell"),
    FieldSpec("description", "string", omit_if_empty=True),
    FieldSpec("applies_to", "json", omit_if_empty=True),
    FieldSpec("effect_data", "json", omit_if_empty=True),
    FieldSpec("default_enabled", "int", default=0),
)

SPELL_DATASET = DatasetSpec(
    name="spells",
    table="spells",
    fields=SPELL_FIELDS,
    order_by=("level", "name COLLATE NOCASE"),
)

CANTRIP_DATASET = DatasetSpec(
    name="cantrips",
    table="cantrips",
    fields=CANTRIP_FIELDS,
    order_by=("name COLLATE NOCASE",),
)

MODIFIER_DATASET = DatasetSpec(
    name="modifiers",
    table="modifiers",
    fields=MODIFIER_FIELDS,
    order_by=("name COLLATE NOCASE",),
)

DATASET_SPECS: Dict[str, DatasetSpec] = {
    spec.name: spec
    for spec in (SPELL_DATASET, CANTRIP_DATASET, MODIFIER_DATASET)
}

DATASET_ORDER: Tuple[str, ...] = tuple(DATASET_SPECS.keys())
TABLE_NAMES: Tuple[str, ...] = tuple(spec.table for spec in DATASET_SPECS.values())


def default_for(field: FieldSpec) -> Any:
    """Return a copy of the default value configured for *field*."""

    value = field.default
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        return dict(value)
    return value


__all__ = [
    "DB_FILE",
    "DB_PATH",
    "SCHEMA_SQL_PATH",
    "SCHEMA_VERSION",
    "DEFAULT_CANTRIP_LEVELS",
    "FieldSpec",
    "DatasetSpec",
    "DATASET_SPECS",
    "DATASET_ORDER",
    "TABLE_NAMES",
    "default_for",
]
