"""Rule compendium loader for the modular 2024 D&D SRD data."""

from __future__ import annotations

import json
import re
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set

import sys
from modules.core.services.settings import get_settings

def _get_default_data_path() -> Path:
    # Use settings logic or replicate it safely
    # If frozen, use MEIPASS/modules/compendium/data
    if getattr(sys, "frozen", False):
         # OneDir: app/LivingScroll.exe vs _internal/modules...
         # Spec puts data at _internal/modules/compendium/data
         # sys._MEIPASS points to _internal
         base = Path(sys._MEIPASS)
    else:
         # Dev: modules/compendium/service.py -> up 2 -> modules
         base = Path(__file__).resolve().parent.parent.parent

    return base / "modules" / "compendium" / "data"

DEFAULT_COMPENDIUM_PATH = _get_default_data_path() / "dnd_2024"

# Module-level cache for Compendium instances to avoid redundant disk I/O
_COMPENDIUM_CACHE: Dict[tuple, "Compendium"] = {}


def clear_compendium_cache() -> None:
    """Clear the cached compendium instances (e.g. after settings change)."""
    _COMPENDIUM_CACHE.clear()


@dataclass
class SpellGrant:
    spell: str
    always_prepared: bool = False


@dataclass
class GrantedSpellList:
    level: int
    spells: List[str]
    always_prepared: bool = False


class Compendium:
    """Lightweight accessor around the static JSON rule data."""

    def __init__(self, payload: Mapping[str, object]) -> None:
        self._payload = payload
        self._classes = _index_by_name(_record_iterable_from(payload.get("classes")))
        self._feats = _index_by_name(_record_iterable_from(payload.get("feats")))
        self._invocations = _index_by_name(_record_iterable_from(payload.get("invocations")))
        self.point_buy = payload.get("point_buy", {})
        self._by_id: Dict[str, object] = {}
        self._display_by_id: Dict[str, str] = {}
        self._rebuild_id_index()

    @classmethod
    def load(cls, ruleset: str | None = None, modules: Iterable[str] | None = None) -> "Compendium":
        settings = get_settings()

        # Use provided ruleset or fall back to settings
        target_ruleset = ruleset or settings.ruleset
        
        # Use simple path construction relative to known data root
        target = _get_default_data_path() / target_ruleset
        
        if not target.exists():
            # Fallback to default path if specific ruleset not found (or if it was a full path passed in legacy code)
            if ruleset and Path(ruleset).exists():
                target = Path(ruleset)
            else:
                target = DEFAULT_COMPENDIUM_PATH

        if not target.exists():
            raise FileNotFoundError(f"Unable to locate compendium data at {target}")
            
        # Use provided modules or fall back to settings
        # Note: If modules is explicitly an empty list, we respect that (loading nothing/base).
        # If it is None, we use settings.
        active_modules = set(modules) if modules is not None else settings.active_modules
        
        # Check cache before loading from disk
        modules_key = frozenset(active_modules) if active_modules else frozenset()
        cache_key = (str(target), modules_key)
        
        if cache_key in _COMPENDIUM_CACHE:
            return _COMPENDIUM_CACHE[cache_key]
        
        payload = _load_payload(target, active_modules)
        instance = cls(payload)
        _COMPENDIUM_CACHE[cache_key] = instance
        return instance

    @property
    def payload(self) -> Mapping[str, object]:
        """Expose the raw payload so non-UI systems can reason over the data."""

        return self._payload

    def records(self, category: str) -> List[dict]:
        """Return a best-effort list of records for an arbitrary category (e.g. feats)."""

        records = self._payload.get(category, [])
        if isinstance(records, list):
            return list(records)
        return []

    def record_by_id(self, record_id: str) -> Optional[object]:
        """Resolve a stable id to its underlying record payload."""

        key = (record_id or "").strip()
        if not key:
            return None
        return self._by_id.get(key)

    def display_for_id(self, record_id: str) -> str:
        """Best-effort display label for an id (used for link rendering)."""

        key = (record_id or "").strip()
        if not key:
            return ""
        return self._display_by_id.get(key, key)

    # --- Internal ----------------------------------------------------
    def _rebuild_id_index(self) -> None:
        by_id: Dict[str, object] = {}
        display: Dict[str, str] = {}

        def _ingest_record(record: Mapping[str, object], *, fallback: str) -> None:
            record_id = record.get("id")
            record_id = record_id if isinstance(record_id, str) else ""
            record_id = record_id.strip() or fallback
            if not record_id:
                return
            by_id.setdefault(record_id, dict(record))
            name = record.get("name")
            title = record.get("title")
            label = name if isinstance(name, str) and name.strip() else (title if isinstance(title, str) and title.strip() else record_id)
            display.setdefault(record_id, str(label))

        # Index top-level list categories.
        for category in ("spells", "feats", "backgrounds", "species", "equipment", "invocations", "classes", "modifiers"):
            items = self._payload.get(category)
            if isinstance(items, list):
                for entry in items:
                    if isinstance(entry, Mapping):
                        name = entry.get("name")
                        name = name if isinstance(name, str) else ""
                        fallback = f"{category}:{_key(name)}" if name else ""
                        _ingest_record(entry, fallback=fallback)

        # Index nested class components (subclasses/options/features) if present.
        classes = self._payload.get("classes")
        if isinstance(classes, list):
            for klass in classes:
                if not isinstance(klass, Mapping):
                    continue
                klass_name = klass.get("name")
                klass_name = klass_name if isinstance(klass_name, str) else ""
                klass_key = _key(klass_name)
                for subclass in (klass.get("subclasses") or []) if isinstance(klass.get("subclasses"), list) else []:
                    if not isinstance(subclass, Mapping):
                        continue
                    sub_name = subclass.get("name")
                    sub_name = sub_name if isinstance(sub_name, str) else ""
                    fallback = f"subclass:{klass_key}:{_key(sub_name)}" if klass_key and sub_name else ""
                    _ingest_record(subclass, fallback=fallback)

        # Index rules blocks as synthetic ids.
        rules = self._payload.get("rules")
        if isinstance(rules, Mapping):
            for key, value in rules.items():
                if not isinstance(key, str):
                    continue
                synthetic_id = f"rules:{key}"
                by_id.setdefault(synthetic_id, value)
                display.setdefault(synthetic_id, key)

        self._by_id = by_id
        self._display_by_id = display

    def class_record(self, name: str) -> Optional[dict]:
        return self._classes.get(_key(name))

    def subclass_record(self, class_name: str, subclass_name: str) -> Optional[dict]:
        klass = self.class_record(class_name)
        if not klass:
            return None
        return _index_by_name(klass.get("subclasses", [])).get(_key(subclass_name))

    def feat_record(self, name: str) -> Optional[dict]:
        return self._feats.get(_key(name))

    def invocation_record(self, name: str) -> Optional[dict]:
        return self._invocations.get(_key(name))

    def invocations(self) -> List[dict]:
        """Return all invocation records defined in the compendium."""

        return list(self._invocations.values())

    def invocations_for_class(
        self,
        class_name: str,
        *,
        class_level: int,
        known_spells: Iterable[str] | None = None,
        known_features: Iterable[str] | None = None,
    ) -> List[dict]:
        """Filter invocations by class prerequisites and auxiliary requirements."""

        class_key = _key(class_name)
        spell_keys = _lowered_set(known_spells)
        feature_keys = _lowered_set(known_features)
        level = max(0, int(class_level))
        matches: List[dict] = []
        for record in self._invocations.values():
            if _invocation_matches(record, class_key, level, spell_keys, feature_keys):
                matches.append(record)
        return matches

    def spellcasting_ability_for(self, class_name: str, subclass_name: str | None = None) -> Optional[str]:
        subclass = self.subclass_record(class_name, subclass_name) if subclass_name else None
        if subclass:
            spellcasting = subclass.get("spellcasting")
            if isinstance(spellcasting, Mapping):
                ability = spellcasting.get("ability")
                if isinstance(ability, str):
                    return ability.upper()
        klass = self.class_record(class_name)
        if not klass:
            return None
        spellcasting = klass.get("spellcasting")
        if isinstance(spellcasting, Mapping):
            ability = spellcasting.get("ability")
            if isinstance(ability, str):
                return ability.upper()
        return None

    def subclasses_with_granted_spells(self, class_name: str) -> List[dict]:
        klass = self.class_record(class_name)
        if not klass:
            return []
        result: List[dict] = []
        for record in klass.get("subclasses", []) or []:
            if record.get("granted_spells"):
                result.append(record)
        return result

    def feats_with_spell_grants(self) -> List[dict]:
        return [feat for feat in self._feats.values() if feat.get("granted_spells")]


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower()).strip("_")


def _index_by_name(records: Iterable[Mapping[str, object]]) -> Dict[str, dict]:
    index: Dict[str, dict] = {}
    for record in records or []:
        name = record.get("name") if isinstance(record, Mapping) else None
        if not isinstance(name, str):
            continue
        index[_key(name)] = dict(record)
    return index


def _load_payload(target: Path, active_modules: Set[str] | None = None) -> Dict[str, Any]:
    if target.is_file():
        return json.loads(target.read_text(encoding="utf-8"))
    if not target.is_dir():
        raise FileNotFoundError(f"Unsupported compendium path: {target}")

    # Otherwise, treat as a container of modules
    combined_payload: Dict[str, Any] = {}
    
    # Sort directories to ensure deterministic load order (e.g. players_handbook first if named appropriately, 
    # or we can rely on a manifest later. For now, alphabetical is a reasonable default).
    for module_dir in sorted(target.iterdir()):
        if not module_dir.is_dir() or module_dir.name.startswith("_"):
            continue
        
        # Filter by active_modules if provided
        if active_modules is not None and module_dir.name not in active_modules:
            continue
        
        module_payload = _load_dataset_directory(module_dir)
        combined_payload = _merge_payloads(combined_payload, module_payload)
        
    return combined_payload


def _merge_payloads(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two compendium payloads, with overlay taking precedence."""
    merged = dict(base)
    
    # Merge lists of named records (classes, feats, spells, etc.)
    for category in ("classes", "feats", "backgrounds", "species", "equipment", "spells", "modifiers", "invocations", "monsters"):
        base_list = base.get(category)
        overlay_list = overlay.get(category)
        
        if not base_list and not overlay_list:
            continue
            
        # Ensure they are lists of dicts
        base_items = base_list if isinstance(base_list, list) else []
        overlay_items = overlay_list if isinstance(overlay_list, list) else []
        
        # Use _merge_named_records logic to combine them by name/id
        merged[category] = _merge_named_records(base_items, overlay_items)

    # Merge rules (dict of dicts)
    base_rules = base.get("rules")
    overlay_rules = overlay.get("rules")
    if base_rules or overlay_rules:
        merged_rules = dict(base_rules) if isinstance(base_rules, dict) else {}
        if isinstance(overlay_rules, dict):
            merged_rules.update(overlay_rules)
        merged["rules"] = merged_rules
        
    # Merge point_buy (simple dict update)
    base_pb = base.get("point_buy")
    overlay_pb = overlay.get("point_buy")
    if base_pb or overlay_pb:
        merged_pb = dict(base_pb) if isinstance(base_pb, dict) else {}
        if isinstance(overlay_pb, dict):
            merged_pb.update(overlay_pb)
        merged["point_buy"] = merged_pb

    return merged


def _load_dataset_directory(root: Path) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}

    metadata_file = root / "metadata.json"
    if metadata_file.exists():
        payload["metadata"] = _read_json(metadata_file)

    classes_dir = root / "classes"
    class_records = _collect_class_records(classes_dir)
    if class_records:
        payload["classes"] = class_records

    # Spells - Strict loading
    spells_dir = root / "spells"
    if spells_dir.exists():
        payload["spells"] = _collect_spells(spells_dir)

    # Other categories - Strict loading
    for category in ("feats", "backgrounds", "species", "equipment", "modifiers", "monsters"):
        directory = root / category
        records = _collect_record_list(directory)
        if records:
            payload[category] = records

    invocation_records = _collect_invocation_records(root)
    if invocation_records:
        payload["invocations"] = invocation_records

    rules_dir = root / "rules"
    rules = _collect_rule_blocks(rules_dir)
    if rules:
        payload["rules"] = rules
        point_buy = rules.get("point_buy")
        if not isinstance(point_buy, Mapping):
            point_buy = rules.get("character_creation/point_buy")
        if isinstance(point_buy, Mapping):
            payload.setdefault("point_buy", point_buy)

    return payload


def _collect_spells(directory: Path) -> List[dict]:
    if not directory.exists():
        return []
    
    records = []
    # Iterate 0-9 directories
    for level_dir in sorted(directory.iterdir()):
        if not level_dir.is_dir() or not level_dir.name.isdigit():
            continue
            
        level = int(level_dir.name)
        
        for file_path in sorted(list(level_dir.glob("*.json")) + list(level_dir.glob("*.md"))):
            if file_path.name.startswith("_"): continue
            
            try:
                if file_path.suffix.lower() == ".json":
                    data = _read_json(file_path)
                else:
                    data = _read_markdown_rule(file_path)
            except Exception as e:
                raise ValueError(f"Invalid data in spell file {file_path}: {e}")

            if not isinstance(data, dict):
                raise ValueError(f"Spell file {file_path} must contain a JSON object or YAML frontmatter")
                
            # Auto-generate ID for MD files if missing
            if "id" not in data and file_path.suffix.lower() == ".md":
                data["id"] = f"spell:{file_path.stem}"

            # Strict Validation
            if "id" not in data:
                raise ValueError(f"Spell {file_path} missing required field 'id'")
            if "name" not in data:
                raise ValueError(f"Spell {file_path} missing required field 'name'")
            if "level" not in data:
                raise ValueError(f"Spell {file_path} missing required field 'level'")
            if data["level"] != level:
                raise ValueError(f"Spell {file_path} has level {data['level']} but is in folder {level}")
            if "school" not in data:
                raise ValueError(f"Spell {file_path} missing required field 'school'")
            if "components" not in data or not isinstance(data["components"], list):
                raise ValueError(f"Spell {file_path} missing or invalid 'components' (must be a list of strings)")
            if "text" not in data or not isinstance(data["text"], dict):
                raise ValueError(f"Spell {file_path} missing or invalid 'text' (must be a dict)")
                
            data["_meta_source_path"] = str(file_path)
            records.append(data)
            
    return records


def _collect_record_list(directory: Path) -> List[dict]:
    if not directory.exists():
        return []
    
    records: List[dict] = []
    
    # Strict: Only load individual JSON/MD files, no bulk lists.
    files = sorted(list(directory.rglob("*.json")) + list(directory.rglob("*.md")), key=lambda p: (len(p.parts), p.name))
    
    for file_path in files:
        if not file_path.is_file():
            continue
        if file_path.name.startswith("_"):
            continue
            
        try:
            if file_path.suffix.lower() == ".json":
                data = _read_json(file_path)
            else:
                data = _read_markdown_rule(file_path)
        except Exception as e:
            raise ValueError(f"Invalid data in file {file_path}: {e}")

        if isinstance(data, list):
            # Disallow bulk files
            raise ValueError(f"Bulk list files are no longer supported. Found list in {file_path}")
        elif isinstance(data, dict):
            # Auto-generate ID if missing for MD files
            if "id" not in data:
                if file_path.suffix.lower() == ".md":
                    # e.g. spells/3/fireball.md -> spell:fireball
                    # This is a heuristic; ideally ID is in frontmatter
                    # For now, we require ID or infer it from filename if possible
                    # But for spells, the ID is usually "spell:name"
                    # Let's try to infer a reasonable ID if missing
                    pass
                
                # If still missing, we can't index it properly
                if "id" not in data:
                     # Fallback: use filename as ID (e.g. "fireball")
                     data["id"] = file_path.stem

            data["_meta_source_path"] = str(file_path)
            records.append(data)
        else:
            raise ValueError(f"File {file_path} must contain a JSON object or YAML frontmatter")
            
    return records


def _collect_class_records(directory: Path) -> List[dict]:
    if not directory.exists():
        return []
    records: List[dict] = []
    for entry in sorted(directory.iterdir(), key=lambda path: path.name.lower()):
        # Handle standalone files
        if entry.is_file():
            if entry.name.startswith("_"): continue
            
            data = None
            if entry.suffix.lower() == ".json":
                data = _read_json(entry)
            elif entry.suffix.lower() == ".md":
                data = _read_markdown_rule(entry)
            
            if isinstance(data, dict):
                if "id" not in data:
                    data["id"] = entry.stem
                data["_meta_source_path"] = str(entry)
                records.append(data)
            continue

        # Handle class directories (e.g. classes/bard/)
        if not entry.is_dir():
            continue
            
        # Look for base.md or base.json
        base_file = entry / "base.md"
        if not base_file.exists():
            base_file = entry / "base.json"
            
        if not base_file.exists():
            continue
            
        if base_file.suffix.lower() == ".json":
            base_record = _read_json(base_file)
        else:
            base_record = _read_markdown_rule(base_file)

        if not isinstance(base_record, dict):
            continue # Skip invalid
        
        if "id" not in base_record:
            base_record["id"] = entry.name # e.g. "bard"

        base_record["_meta_source_path"] = str(base_file)
        record = dict(base_record)
        
        # Collect subclasses
        subclass_dir = entry / "subclasses"
        if subclass_dir.exists():
            subclasses = _collect_record_list(subclass_dir)
            if subclasses:
                record["subclasses"] = _merge_named_records(record.get("subclasses"), subclasses)

        # Collect options
        option_dir = entry / "options"
        if option_dir.exists():
            option_groups = _collect_record_list(option_dir)
            if option_groups:
                record["options"] = _merge_option_groups(record.get("options"), option_groups)
        records.append(record)
    return records


def _merge_named_records(
    existing: Iterable[Mapping[str, Any]] | None,
    additions: Iterable[Mapping[str, Any]] | None,
) -> List[dict]:
    combined: Dict[str, dict] = {}
    ordered_keys: List[str] = []

    def _ingest(items: Iterable[Mapping[str, Any]] | None) -> None:
        if not items:
            return
        for entry in items:
            if not isinstance(entry, Mapping):
                continue
            name = entry.get("name")
            if not isinstance(name, str):
                continue
            key = _key(name)
            if key not in combined:
                ordered_keys.append(key)
            combined[key] = dict(entry)

    _ingest(existing)
    _ingest(additions)
    return [combined[key] for key in ordered_keys]


def _merge_option_groups(
    existing: Iterable[Mapping[str, Any]] | None,
    additions: Iterable[Mapping[str, Any]] | None,
) -> List[dict]:
    combined: Dict[str, dict] = {}
    ordered_keys: List[str] = []

    def _ingest(items: Iterable[Mapping[str, Any]] | None) -> None:
        if not items:
            return
        for entry in items:
            if not isinstance(entry, Mapping):
                continue
            key_value = entry.get("key") or entry.get("name")
            if not isinstance(key_value, str):
                continue
            key = _key(key_value)
            if key not in combined:
                ordered_keys.append(key)
            combined[key] = dict(entry)

    _ingest(existing)
    _ingest(additions)
    return [combined[key] for key in ordered_keys]


def _collect_invocation_records(root: Path) -> List[dict]:
    records: List[dict] = []
    records.extend(_collect_record_list(root / "invocations"))

    classes_dir = root / "classes"
    if classes_dir.exists():
        for inv_dir in classes_dir.glob("**/invocations"):
            if inv_dir.is_dir():
                records.extend(_collect_record_list(inv_dir))
    return records


def _collect_rule_blocks(directory: Path) -> Dict[str, object]:
    if not directory.exists():
        return {}
    blocks: Dict[str, object] = {}
    
    # JSON files (Legacy)
    for file_path in sorted(directory.rglob("*.json")):
        if not file_path.is_file():
            continue
        key = file_path.relative_to(directory).with_suffix("").as_posix()
        data = _read_json(file_path)
        if isinstance(data, dict):
            data["_meta_source_path"] = str(file_path)
        blocks[key] = data

    # Markdown files (New)
    for file_path in sorted(directory.rglob("*.md")):
        if not file_path.is_file():
            continue
        key = file_path.relative_to(directory).with_suffix("").as_posix()
        data = _read_markdown_rule(file_path)
        if isinstance(data, dict):
            data["_meta_source_path"] = str(file_path)
        blocks[key] = data
        
    return blocks


def _read_markdown_rule(path: Path) -> Dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    
    # YAML frontmatter parser
    if content.startswith("---"):
        try:
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                body = parts[2]
                
                data = yaml.safe_load(frontmatter) or {}
                
                # Ensure basic fields exist
                if "title" not in data:
                    data["title"] = path.stem.replace("_", " ").title()
                
                # Store the body text
                # We keep the legacy structure for now to avoid breaking existing UI
                if "text" not in data:
                    data["text"] = {"full": body.strip()}
                elif isinstance(data["text"], dict) and "full" not in data["text"]:
                    data["text"]["full"] = body.strip()
                
                return data
        except Exception:
            # Fallback if parsing fails, treat as plain text
            pass
            # Fallback if parsing fails, treat as plain text
            pass
            
    # Fallback for plain markdown without frontmatter
    return {
        "title": path.stem.replace("_", " ").title(),
        "text": {
            "full": content.strip()
        }
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _record_iterable_from(value: Any) -> Iterable[Mapping[str, object]]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _lowered_set(values: Iterable[str] | None) -> Set[str]:
    return {_key(value) for value in (values or []) if value}


def _invocation_matches(
    record: Mapping[str, Any],
    class_key: str,
    class_level: int,
    known_spells: Set[str],
    known_features: Set[str],
) -> bool:
    prereqs = record.get("prerequisites") or []
    for requirement in prereqs:
        if not isinstance(requirement, Mapping):
            return False
        req_type = _key(str(requirement.get("type", "")))
        value = _key(str(requirement.get("value", "")))
        if req_type == "class":
            required_class = value
            if required_class and required_class != class_key:
                return False
            required_level = int(requirement.get("level", 1) or 1)
            if class_level < required_level:
                return False
        elif req_type == "spell":
            if value not in known_spells:
                return False
        elif req_type == "feature":
            if value not in known_features:
                return False
        else:
            return False
    return True



def get_module_metrics(module_path: Path) -> Dict[str, int]:
    """Analyze a module directory and return counts of its content types."""
    if not module_path.exists():
        return {}

    metrics = {}
    
    # Classes & Subclasses
    classes = _collect_class_records(module_path / "classes")
    if classes:
        metrics["Classes"] = len(classes)
        subclasses = sum(len(c.get("subclasses", [])) for c in classes)
        if subclasses:
            metrics["Subclasses"] = subclasses

    # Spells
    spells = _collect_spells(module_path / "spells")
    if spells:
        metrics["Spells"] = len(spells)

    # Simple Lists
    for category_key, display_name in [
        ("feats", "Feats"),
        ("backgrounds", "Backgrounds"),
        ("species", "Species"),
        ("equipment", "Items"),
        ("monsters", "Monsters"),
        ("invocations", "Invocations"),
    ]:
        # Special check for invocations as they can be scattered
        if category_key == "invocations":
             records = _collect_invocation_records(module_path)
        else:
             records = _collect_record_list(module_path / category_key)
             
        if records:
            metrics[display_name] = len(records)

    return metrics


__all__ = ["Compendium", "DEFAULT_COMPENDIUM_PATH", "clear_compendium_cache", "get_module_metrics"]
