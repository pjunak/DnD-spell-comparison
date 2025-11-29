"""Database helpers for schema management, imports, exports, and lookups."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from . import schema
from .schema import DatasetSpec, FieldSpec


def ensure_database() -> None:
    """Create the database file and apply the current schema if needed."""

    schema.DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(schema.DB_FILE)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        current_version = _get_user_version(conn)
        if current_version == schema.SCHEMA_VERSION:
            return
        if current_version not in (0, schema.SCHEMA_VERSION):
            raise RuntimeError(
                "Unsupported spellBook schema version "
                f"{current_version}; please re-import your spell data."
            )
        _apply_schema(conn)


def load_spells() -> List[dict]:
    """Return all spells and cantrips with resolved modifier details."""

    ensure_database()

    with closing(sqlite3.connect(schema.DB_FILE)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        raw_modifier_entries = _fetch_dataset_entries(conn, schema.DATASET_SPECS["modifiers"])
        modifier_entries = [_prepare_modifier_runtime_entry(entry) for entry in raw_modifier_entries]
        modifier_map = {
            entry["name"]: entry
            for entry in modifier_entries
            if entry.get("scope", "spell").lower() != "character"
        }

        spell_entries = _fetch_dataset_entries(conn, schema.DATASET_SPECS["spells"])
        cantrip_entries = _fetch_dataset_entries(conn, schema.DATASET_SPECS["cantrips"])

        records = [_spell_runtime(entry, modifier_map) for entry in spell_entries]
        records.extend(_cantrip_runtime(entry, modifier_map) for entry in cantrip_entries)
        records.sort(key=lambda item: (item.get("level", 0), item["name"].lower()))
        return records


def load_modifiers(*, scope: Optional[str] = None) -> List[dict]:
    """Return modifiers filtered by optional *scope* (e.g. "character")."""

    ensure_database()

    with closing(sqlite3.connect(schema.DB_FILE)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        raw_entries = _fetch_dataset_entries(conn, schema.DATASET_SPECS["modifiers"])
        prepared = [_prepare_modifier_runtime_entry(entry) for entry in raw_entries]
        if scope is None:
            return prepared
        scope_lower = scope.lower()
        return [entry for entry in prepared if entry.get("scope", "").lower() == scope_lower]


def upsert_modifiers(entries: Iterable[dict]) -> int:
    """Insert or replace modifier definitions.

    Returns the number of entries written to the database.
    """

    ensure_database()

    spec = schema.DATASET_SPECS["modifiers"]
    column_names = spec.column_names()
    column_list = ", ".join(column_names)
    placeholders = ", ".join("?" for _ in column_names)

    with closing(sqlite3.connect(schema.DB_FILE)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        inserted = 0
        for entry in entries:
            prepared_entry = _prepare_entry_for_dataset(entry, "modifiers")
            normalised = _normalise_entry(prepared_entry, spec)
            conn.execute(
                f"REPLACE INTO {spec.table} ({column_list}) VALUES ({placeholders})",
                [normalised[name] for name in column_names],
            )
            inserted += 1
        conn.commit()
    return inserted


def import_dataset(json_path: Path | str) -> Dict[str, int]:
    """Replace database contents using a dataset stored in *json_path*."""

    payload = _modernise_dataset_payload(_load_json_dataset(Path(json_path)))
    ensure_database()

    with closing(sqlite3.connect(schema.DB_FILE)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        counts: Dict[str, int] = {}
        for name in schema.DATASET_ORDER:
            spec = schema.DATASET_SPECS[name]
            entries = payload.get(name, []) or []
            entries = [_prepare_entry_for_dataset(entry, name) for entry in entries]
            conn.execute(f"DELETE FROM {spec.table}")
            inserted = 0
            for entry in entries:
                normalised = _normalise_entry(entry, spec)
                _insert_row(conn, spec, normalised)
                inserted += 1
            counts[name] = inserted
        conn.commit()
    return counts


def export_dataset() -> Dict[str, Any]:
    """Dump the current database contents in JSON-serialisable form."""

    ensure_database()

    with closing(sqlite3.connect(schema.DB_FILE)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        exported: Dict[str, Any] = {}
        for name in schema.DATASET_ORDER:
            spec = schema.DATASET_SPECS[name]
            rows = _fetch_dataset_entries(conn, spec)
            if name == "modifiers":
                for row in rows:
                    row["default_enabled"] = bool(row.get("default_enabled", 0))
                exported[name] = _group_modifiers_for_export(rows)
            else:
                exported[name] = rows
        return exported


def export_dataset_to_json(json_path: Path | str) -> Dict[str, int]:
    """Write the dataset to *json_path* on disk and return row counts."""

    data = export_dataset()
    path = Path(json_path)
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    counts: Dict[str, int] = {}
    for name, rows in data.items():
        if name == "modifiers" and isinstance(rows, dict):
            counts[name] = sum(len(items) for items in rows.values())
        elif isinstance(rows, list):
            counts[name] = len(rows)
        else:
            counts[name] = 0
    return counts


def fill_database_from_json(json_path: Path | str) -> Dict[str, int]:
    """Compatibility alias for :func:`import_dataset`."""

    return import_dataset(json_path)


def export_database_to_json(json_path: Path | str) -> Dict[str, int]:
    """Compatibility alias for :func:`export_dataset_to_json`."""

    return export_dataset_to_json(json_path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _apply_schema(conn: sqlite3.Connection) -> None:
    script = schema.SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    conn.executescript(script)
    conn.execute(f"PRAGMA user_version = {schema.SCHEMA_VERSION}")
    conn.commit()


def _get_user_version(conn: sqlite3.Connection) -> int:
    cur = conn.execute("PRAGMA user_version")
    row = cur.fetchone()
    return int(row[0]) if row else 0


def _load_json_dataset(path: Path) -> Dict[str, list]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Dataset root must be a JSON object containing spell lists.")
    return data  # type: ignore[return-value]


def _modernise_dataset_payload(payload: Dict[str, list]) -> Dict[str, list]:
    if "bonuses" in payload and "modifiers" not in payload:
        payload["modifiers"] = payload.pop("bonuses")
    modifiers = payload.get("modifiers")
    if isinstance(modifiers, dict):
        flattened: List[dict] = []
        for category_key, entries in modifiers.items():
            if not isinstance(entries, list):
                continue
            base_category = _normalise_modifier_category(category_key)
            for entry in entries:
                record = dict(entry) if isinstance(entry, dict) else {}
                if not record.get("category"):
                    record["category"] = base_category
                else:
                    record["category"] = _normalise_modifier_category(record.get("category"))
                flattened.append(record)
        payload["modifiers"] = flattened
    return payload


def _prepare_entry_for_dataset(entry: dict, dataset_name: str) -> dict:
    prepared = dict(entry)
    name_lower = dataset_name.lower()

    if name_lower in {"spells", "cantrips"}:
        if "modifiers" not in prepared and "bonus" in prepared:
            prepared["modifiers"] = prepared.pop("bonus")

    if name_lower == "modifiers":
        scope = prepared.get("scope")
        if not scope:
            prepared["scope"] = "spell"
        else:
            prepared["scope"] = str(scope)
        category = prepared.get("category")
        if category not in (None, ""):
            prepared["category"] = _normalise_modifier_category(category)
        default_enabled = prepared.get("default_enabled", 0)
        prepared["default_enabled"] = 1 if bool(default_enabled) else 0

    return prepared


def _insert_row(conn: sqlite3.Connection, spec: DatasetSpec, values: Dict[str, object]) -> None:
    columns = spec.column_names()
    placeholders = ", ".join("?" for _ in columns)
    column_list = ", ".join(columns)
    conn.execute(
        f"INSERT INTO {spec.table} ({column_list}) VALUES ({placeholders})",
        [values.get(name) for name in columns],
    )


def _normalise_entry(entry: dict, spec: DatasetSpec) -> Dict[str, object]:
    field_map = spec.field_map()
    normalised: Dict[str, object] = {}
    for field in spec.fields:
        value = entry.get(field.key, None)
        if value in (None, ""):
            value = schema.default_for(field)
            if value is None and field.required:
                raise ValueError(f"Field '{field.key}' is required for '{spec.name}'.")
        converted = _coerce_to_db(field, value)
        normalised[field.column_name] = converted
    return normalised


def _coerce_to_db(field: FieldSpec, value) -> object:
    kind = field.kind
    if kind == "string":
        if value in (None, ""):
            return None
        return str(value)
    if kind == "int":
        if value in (None, ""):
            if field.required:
                raise ValueError(f"Field '{field.key}' requires an integer value.")
            return None
        return int(value)
    if kind == "json":
        if value in (None, ""):
            return None
        if isinstance(value, str):
            return value
        return json.dumps(value)
    if kind == "list[str]":
        items = _normalise_string_list(value)
        return json.dumps(items)
    if kind == "list[int]":
        items = _normalise_int_list(value, field)
        return json.dumps(items)
    raise ValueError(f"Unsupported field kind '{kind}' for '{field.key}'.")


def _normalise_string_list(value) -> List[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        items: List[str] = []
        for item in value:
            text = str(item).strip()
            if text and text not in items:
                items.append(text)
        return items
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
        return [part for part in parts if part]
    raise ValueError("List field expects an array or comma-separated text value.")


def _normalise_int_list(value, field: FieldSpec) -> List[int]:
    if value in (None, ""):
        default_value = schema.default_for(field)
        return [int(item) for item in default_value] if default_value else []
    if isinstance(value, list):
        return [int(item) for item in value]
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",") if part.strip()]
        return [int(part) for part in parts]
    raise ValueError("List field expects an array or comma-separated numbers.")


def _fetch_dataset_entries(conn: sqlite3.Connection, spec: DatasetSpec) -> List[dict]:
    columns = ", ".join(spec.column_names())
    order_clause = f" ORDER BY {', '.join(spec.order_by)}" if spec.order_by else ""
    cur = conn.execute(f"SELECT {columns} FROM {spec.table}{order_clause}")
    rows = cur.fetchall()
    return [_row_to_dataset_entry(row, spec) for row in rows]


def _row_to_dataset_entry(row: sqlite3.Row, spec: DatasetSpec) -> dict:
    data: Dict[str, object] = {}
    for field in spec.fields:
        raw_value = row[field.column_name]
        converted = _coerce_from_db(field, raw_value)
        if field.omit_if_empty and _is_empty(converted):
            continue
        if converted is None and not field.required:
            continue
        data[field.key] = converted
    return data


def _coerce_from_db(field: FieldSpec, value) -> object:
    kind = field.kind
    if kind == "string":
        if value in (None, ""):
            default_value = schema.default_for(field)
            return default_value if default_value is not None else None
        return str(value)
    if kind == "int":
        if value is None:
            default_value = schema.default_for(field)
            return int(default_value) if default_value is not None else None
        return int(value)
    if kind == "json":
        if value in (None, ""):
            return schema.default_for(field)
        return _parse_json(value, schema.default_for(field))
    if kind == "list[str]":
        return _parse_string_list(value, schema.default_for(field) or [])
    if kind == "list[int]":
        return _parse_int_list(value, schema.default_for(field) or [])
    raise ValueError(f"Unsupported field kind '{kind}' for '{field.key}'.")


def _parse_json(raw_value, default):
    if raw_value in (None, ""):
        return default
    try:
        return json.loads(raw_value)
    except (TypeError, ValueError):
        return default


def _parse_string_list(raw_value, default: Iterable[str]) -> List[str]:
    parsed = _parse_json(raw_value, None)
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    if isinstance(raw_value, str):
        parts = [part.strip() for part in raw_value.split(",")]
        return [part for part in parts if part]
    return list(default)


def _parse_int_list(raw_value, default: Iterable[int]) -> List[int]:
    parsed = _parse_json(raw_value, None)
    if isinstance(parsed, list):
        result: List[int] = []
        for item in parsed:
            try:
                result.append(int(item))
            except (TypeError, ValueError):
                continue
        return result
    if isinstance(raw_value, str):
        parts = [part.strip() for part in raw_value.split(",") if part.strip()]
        result: List[int] = []
        for part in parts:
            try:
                result.append(int(part))
            except ValueError:
                continue
        return result
    return list(default)


def _is_empty(value) -> bool:
    return value in (None, "", [], {}, ())


def _prepare_modifier_runtime_entry(entry: dict) -> dict:
    data = dict(entry)
    scope = data.get("scope") or "spell"
    data["scope"] = str(scope)
    if data.get("category"):
        data["category"] = _normalise_modifier_category(data.get("category"))
    data["default_enabled"] = bool(data.get("default_enabled", 0))
    return data


def _spell_runtime(entry: dict, modifier_map: Dict[str, dict]) -> dict:
    data = dict(entry)
    modifier_names = data.pop("modifiers", data.pop("bonus", []))
    modifiers = _resolve_modifier_details(modifier_names, modifier_map)
    effects = _build_effects(data.pop("primary_effect", None), data.pop("secondary_effect", None))

    record = {
        "name": data.get("name"),
        "level": data.get("level", 0),
        "school": data.get("school"),
        "casting_time": data.get("casting_time"),
        "range": data.get("range"),
        "duration": data.get("duration"),
        "components": data.get("components", []),
        "effects": effects,
        "modifiers": modifiers,
    }
    return record


def _cantrip_runtime(entry: dict, modifier_map: Dict[str, dict]) -> dict:
    data = dict(entry)
    modifier_names = data.pop("modifiers", data.pop("bonus", []))
    modifiers = _resolve_modifier_details(modifier_names, modifier_map)
    effects = _build_effects(data.pop("primary_effect", None), data.pop("secondary_effect", None))

    record = {
        "name": data.get("name"),
        "level": 0,
        "school": data.get("school"),
        "casting_time": data.get("casting_time"),
        "range": data.get("range"),
        "duration": data.get("duration"),
        "components": data.get("components", []),
        "effects": effects,
        "modifiers": modifiers,
        "scaling_levels": data.get("scaling_levels", schema.DEFAULT_CANTRIP_LEVELS),
    }
    return record


def _resolve_modifier_details(modifier_names: Iterable[str], modifier_map: Dict[str, dict]) -> List[dict]:
    resolved: List[dict] = []
    for name in modifier_names:
        modifier = modifier_map.get(name)
        if modifier:
            resolved.append(modifier)
    return resolved


def _build_effects(primary, secondary) -> List[dict]:
    effects: List[dict] = []
    primary_effect = _clone_effect(primary, default_type="primary")
    if primary_effect is not None:
        effects.append(primary_effect)
    secondary_effect = _clone_effect(secondary, default_type="secondary")
    if secondary_effect is not None:
        effects.append(secondary_effect)
    return effects


def _clone_effect(effect, *, default_type: str) -> dict | None:
    if effect in (None, ""):
        if default_type == "primary":
            return {"effect_type": "primary"}
        return None
    if isinstance(effect, dict):
        clone = dict(effect)
    else:
        clone = _parse_json(effect, {})
        if not isinstance(clone, dict):
            clone = {}
    clone.setdefault("effect_type", default_type)
    return clone


def _normalise_modifier_category(value, *, default: str = "misc") -> str:
    if isinstance(value, dict):
        value = value.get("category")
    text = str(value or "").strip().lower()
    if not text:
        return default
    aliases = {
        "feat": "feat",
        "feats": "feat",
        "invocation": "invocation",
        "invocations": "invocation",
        "subclass": "subclass",
        "subclasses": "subclass",
        "specialization": "specialization",
        "specializations": "specialization",
        "specialisation": "specialization",
        "specialisations": "specialization",
        "boon": "boon",
        "boons": "boon",
        "general": "general",
        "misc": "misc",
    }
    if text in aliases:
        return aliases[text]
    if text.endswith("es"):
        singular = text[:-2]
    elif text.endswith("s"):
        singular = text[:-1]
    else:
        singular = text
    return singular or default


def _group_modifiers_for_export(entries: List[dict]) -> Dict[str, List[dict]]:
    grouped: Dict[str, List[dict]] = {}
    category_lookup: Dict[str, str] = {}
    for entry in entries:
        base_category = _normalise_modifier_category(entry.get("category"))
        label = _export_category_label(base_category)
        category_lookup[label] = base_category
        grouped.setdefault(label, []).append(entry)

    ordered_labels = sorted(
        grouped.keys(),
        key=lambda label: (
            _category_export_order(category_lookup.get(label, "misc")),
            label,
        ),
    )

    ordered: Dict[str, List[dict]] = {}
    for label in ordered_labels:
        ordered[label] = sorted(grouped[label], key=lambda item: str(item.get("name", "")).lower())
    return ordered


def _export_category_label(base_category: str) -> str:
    base = (base_category or "misc").strip().lower()
    labels = {
        "feat": "feats",
        "invocation": "invocations",
        "subclass": "subclasses",
        "specialization": "specializations",
        "boon": "boons",
        "general": "general",
        "misc": "misc",
    }
    if base in labels:
        return labels[base]
    if base.endswith("s"):
        return base
    return f"{base}s" if base else "misc"


def _category_export_order(base_category: str) -> int:
    base = (base_category or "misc").strip().lower()
    ordering = {
        "feat": 10,
        "invocation": 20,
        "subclass": 30,
        "specialization": 40,
        "boon": 50,
        "general": 60,
        "misc": 70,
    }
    return ordering.get(base, 65)


__all__ = [
    "ensure_database",
    "load_spells",
    "load_modifiers",
    "upsert_modifiers",
    "import_dataset",
    "export_dataset",
    "export_dataset_to_json",
    "fill_database_from_json",
    "export_database_to_json",
]
