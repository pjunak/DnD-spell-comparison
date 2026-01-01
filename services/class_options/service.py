"""Service that derives class option slots (invocations, pacts, etc.) from the compendium."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence

from character_sheet import CharacterSheet, ClassProgression
from services.compendium import Compendium

from .models import ClassOptionChoice, ClassOptionGroup, ClassOptionSnapshot


class ClassOptionsService:
    """Computes dynamic class options (e.g., invocations) for a sheet."""

    def __init__(self, compendium: Compendium | None = None) -> None:
        self._compendium = compendium or Compendium.load()

    def build_snapshot(
        self,
        sheet: CharacterSheet,
        selections: Dict[str, List[str]] | None = None,
    ) -> ClassOptionSnapshot:
        classes = tuple(sheet.identity.classes or [])
        option_groups: Dict[str, ClassOptionGroup] = {}
        order: List[str] = []

        def _append_group(group: ClassOptionGroup | None) -> None:
            if not group:
                return
            if group.key not in option_groups:
                order.append(group.key)
            option_groups[group.key] = group

        for group in self._class_defined_option_groups(classes):
            _append_group(group)

        _append_group(self._warlock_invocation_group(classes, sheet))

        ordered_groups = [option_groups[key] for key in order]

        resolved = self._resolve_selections(ordered_groups, selections or {})
        return ClassOptionSnapshot(ordered_groups, resolved)

    # --- Private helpers -------------------------------------------------
    def _class_defined_option_groups(
        self,
        classes: Sequence[ClassProgression],
    ) -> List[ClassOptionGroup]:
        groups: List[ClassOptionGroup] = []
        for entry in classes:
            class_record = self._compendium.class_record(entry.name)
            if not class_record:
                continue
            raw_options = class_record.get("options")
            if not isinstance(raw_options, list):
                continue
            for option_data in raw_options:
                group = self._group_from_record(option_data, entry.name)
                if not group:
                    continue
                if entry.level < max(1, group.min_level):
                    continue
                groups.append(group)
        return groups

    def _group_from_record(self, data: Any, class_name: str) -> ClassOptionGroup | None:
        if not isinstance(data, dict):
            return None
        key = str(data.get("key", "")).strip()
        if not key:
            return None
        label = str(data.get("label") or key.replace("_", " ").title()).strip()
        min_level = max(1, int(data.get("min_level", 1) or 1))
        max_choices = max(1, int(data.get("max_choices", 1) or 1))
        helper_text = str(data.get("helper_text", "")).strip()
        choices_data = data.get("choices") or []
        choices: List[ClassOptionChoice] = []
        for choice in choices_data:
            if not isinstance(choice, dict):
                continue
            value = str(choice.get("value", "")).strip()
            label_text = str(choice.get("label", value)).strip()
            if not value or not label_text:
                continue
            description = str(choice.get("description", "")).strip()
            metadata_raw = choice.get("metadata") or {}
            metadata: Dict[str, str] = {}
            if isinstance(metadata_raw, dict):
                for meta_key, meta_value in metadata_raw.items():
                    if meta_key is None:
                        continue
                    metadata[str(meta_key)] = str(meta_value)
            choices.append(
                ClassOptionChoice(
                    value=value,
                    label=label_text,
                    description=description,
                    metadata=metadata,
                )
            )
        if not choices:
            return None
        return ClassOptionGroup(
            key=key,
            label=label,
            class_name=class_name,
            min_level=min_level,
            max_choices=max_choices,
            choices=choices,
            helper_text=helper_text,
        )

    def _warlock_invocation_group(
        self,
        classes: Sequence[ClassProgression],
        sheet: CharacterSheet,
    ) -> ClassOptionGroup | None:
        warlock_level = _class_level(classes, "warlock")
        if warlock_level < 2:
            return None
        class_record = self._compendium.class_record("warlock") or {}
        table = class_record.get("spellcasting", {}).get("invocations_known_table", {})
        max_choices = _lookup_progression_value(table, warlock_level)
        if max_choices <= 0:
            return None

        available_names: Iterable[str] = class_record.get("invocations_available", []) or []
        known_spells = {
            (entry.spell_name or "").strip().lower()
            for entry in sheet.spellcasting.known_spells
            if (entry.spell_name or "").strip()
        }
        known_features = {
            (entry.title or "").strip().lower()
            for entry in sheet.features
            if (entry.title or "").strip()
        }
        invocations = self._compendium.invocations_for_class(
            "warlock",
            class_level=warlock_level,
            known_spells=known_spells,
            known_features=known_features,
        )

        # Filter by listed availability if provided on the class record.
        allowed_set = {name.strip().lower() for name in available_names if name}
        choices: List[ClassOptionChoice] = []
        for record in invocations:
            name = record.get("name")
            if not isinstance(name, str) or not name:
                continue
            if allowed_set and name.strip().lower() not in allowed_set:
                continue
            description = ""
            features = record.get("features")
            if isinstance(features, list) and features:
                first = features[0]
                if isinstance(first, dict):
                    description = str(first.get("description", ""))
            choices.append(
                ClassOptionChoice(
                    value=name,
                    label=name,
                    description=description,
                )
            )
        if not choices:
            return None
        choices.sort(key=lambda choice: choice.label.lower())
        helper = "Select the Eldritch Invocations you currently know."
        return ClassOptionGroup(
            key="warlock_invocations",
            label="Eldritch Invocations",
            class_name="Warlock",
            min_level=2,
            max_choices=max_choices,
            choices=choices,
            helper_text=helper,
        )

    @staticmethod
    def _resolve_selections(
        groups: Sequence[ClassOptionGroup],
        selections: Dict[str, List[str]],
    ) -> Dict[str, List[str]]:
        resolved: Dict[str, List[str]] = {}
        for group in groups:
            requested = selections.get(group.key, []) or []
            filtered: List[str] = []
            allowed_values = {choice.value.lower(): choice.value for choice in group.choices}
            for value in requested:
                lower = (value or "").strip().lower()
                if not lower:
                    continue
                canonical = allowed_values.get(lower)
                if not canonical:
                    continue
                if canonical in filtered:
                    continue
                filtered.append(canonical)
                if len(filtered) >= group.max_choices:
                    break
            resolved[group.key] = filtered
        return resolved


def _class_level(classes: Sequence[ClassProgression], class_name: str) -> int:
    target = (class_name or "").strip().lower()
    total = 0
    for entry in classes:
        if (entry.name or "").strip().lower() != target:
            continue
        total += max(0, int(entry.level))
    return total


def _lookup_progression_value(table: dict, level: int) -> int:
    try:
        return int(table.get(str(level), 0) or 0)
    except (AttributeError, ValueError, TypeError):
        return 0


__all__ = ["ClassOptionsService"]
