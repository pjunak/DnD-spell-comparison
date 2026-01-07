"""Structured representation of the D&D 2024 character sheet."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Mapping, Optional

ABILITY_NAMES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


@dataclass
class AbilityBlock:
    score: int = 10
    modifier: Optional[int] = None
    save_proficient: bool = False
    save_bonus: int = 0

    def effective_modifier(self) -> int:
        if self.modifier is not None:
            return self.modifier
        return (self.score - 10) // 2

    def save_modifier(self, proficiency_bonus: int) -> int:
        base = self.effective_modifier()
        if self.save_proficient:
            base += proficiency_bonus
        return base + self.save_bonus


@dataclass
class ClassProgression:
    name: str
    level: int
    subclass: Optional[str] = None


@dataclass
class BackgroundSelection:
    ability_choices: List[str] = field(default_factory=list)
    skill_choices: List[str] = field(default_factory=list)
    tool_choices: List[str] = field(default_factory=list)
    language_choices: List[str] = field(default_factory=list)
    feat_choice: str = ""


@dataclass
class CharacterIdentity:
    name: str = ""
    ancestry: str = ""
    ancestry_subtype: str = ""
    background: str = ""
    background_choices: BackgroundSelection = field(default_factory=BackgroundSelection)
    player: str = ""
    alignment: str = ""
    experience: int = 0
    classes: List[ClassProgression] = field(default_factory=list)
    level_cap: int = 0
    ability_generation: str = "manual"
    asi_choices: Dict[int, str] = field(default_factory=dict)
    portrait_path: str = ""

    @property
    def level(self) -> int:
        return sum(entry.level for entry in self.classes) or 0

    @property
    def effective_level_cap(self) -> int:
        base = self.level_cap or self.level or 1
        return max(1, base)


@dataclass
class CombatStats:
    armor_class: int = 10
    initiative_bonus: int = 0
    speed_ft: int = 30
    max_hp: int = 0
    current_hp: int = 0
    temp_hp: int = 0
    hit_dice: str = ""
    death_save_successes: int = 0
    death_save_failures: int = 0


@dataclass
class ProficiencySet:
    proficiency_bonus: int = 2
    armor: List[str] = field(default_factory=list)
    weapons: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    skills: Dict[str, int] = field(default_factory=dict)


@dataclass
class EquipmentItem:
    name: str
    quantity: int = 1
    weight_lb: float = 0.0
    attuned: bool = False
    notes: str = ""
@dataclass
class EquipmentItem:
    name: str
    quantity: int = 1
    weight_lb: float = 0.0
    attuned: bool = False
    notes: str = ""
    bonuses: Dict[str, int] = field(default_factory=dict)
    compendium_id: str = ""
    cost: str = ""
    rarity: str = ""


@dataclass
class FeatureEntry:
    title: str
    source: str
@dataclass
class FeatureEntry:
    title: str
    source: str
    description: str = ""
    compendium_id: str = ""


@dataclass
class ResourcePool:
    name: str
    max_uses: int
    current_uses: int
    refreshes_on: str


@dataclass
class SpellAccessEntry:
    spell_name: str
    source: str
    prepared: bool = False
    category: str = ""
    source_type: str = ""
    source_id: str = ""
    ability: Optional[str] = None
    granted: bool = False


@dataclass
class SpellSourceRecord:
    source_type: str
    source_id: str
    label: str = ""
    ability: Optional[str] = None


def _default_slot_schedule() -> Dict[str, Dict[int, int]]:
    return {"long_rest": {}, "short_rest": {}}


def _normalise_slot_dict(entries: Mapping[str, Any] | Dict[int, Any]) -> Dict[int, int]:
    result: Dict[int, int] = {}
    for level, amount in (entries or {}).items():
        try:
            lvl = int(level)
            amt = int(amount)
        except (TypeError, ValueError):
            continue
        if lvl <= 0 or amt <= 0:
            continue
        result[lvl] = amt
    return result


def _aggregate_slot_schedule(schedule: Mapping[str, Dict[int, int]]) -> Dict[int, int]:
    combined: Dict[int, int] = {}
    for pool in (schedule or {}).values():
        for level, amount in (pool or {}).items():
            if amount <= 0:
                continue
            combined[level] = combined.get(level, 0) + amount
    return combined


def _copy_slot_pools(pools: Mapping[int, int]) -> Dict[int, int]:
    return {level: amount for level, amount in pools.items() if amount > 0}


@dataclass
class SpellcastingData:
    spellcasting_ability: str = "INT"
    attack_bonus: Optional[int] = None
    save_dc: Optional[int] = None
    known_spells: List[SpellAccessEntry] = field(default_factory=list)
    spell_sources: List[SpellSourceRecord] = field(default_factory=list)
    slot_schedule: Dict[str, Dict[int, int]] = field(default_factory=_default_slot_schedule)
    slot_state: Dict[str, Dict[int, int]] = field(default_factory=_default_slot_schedule)
    spell_slots: Dict[int, int] = field(default_factory=dict)
    prepared_spells: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.sync_slot_schedule()

    def sync_slot_schedule(self) -> None:
        """Keep aggregated spell slots and rest-based pools aligned."""

        raw_schedule = self.slot_schedule or {}
        schedule = {
            "long_rest": _normalise_slot_dict(raw_schedule.get("long_rest", {})),
            "short_rest": _normalise_slot_dict(raw_schedule.get("short_rest", {})),
        }
        if not any(schedule.values()):
            if self.spell_slots:
                schedule["long_rest"] = _normalise_slot_dict(self.spell_slots)
            else:
                schedule = _default_slot_schedule()

        raw_state = self.slot_state or {}
        state: Dict[str, Dict[int, int]] = {}
        for rest_key, pool in schedule.items():
            state_pool = _normalise_slot_dict(raw_state.get(rest_key, pool))
            clamped: Dict[int, int] = {}
            for level, maximum in pool.items():
                value = state_pool.get(level, maximum)
                clamped[level] = max(0, min(value, maximum))
            state[rest_key] = clamped

        self.slot_schedule = schedule
        self.slot_state = state
        self.spell_slots = _aggregate_slot_schedule(self.slot_state)

    def reset_slots(self, rest_type: str) -> None:
        """Restore slot state according to the requested rest type."""

        rest_key = str(rest_type or "").lower()
        if rest_key not in {"short", "short_rest", "long", "long_rest"}:
            rest_key = "long_rest"
        if rest_key.startswith("short"):
            current_long = _copy_slot_pools(self.slot_state.get("long_rest", self.slot_schedule.get("long_rest", {})))
            self.slot_state["short_rest"] = _copy_slot_pools(self.slot_schedule.get("short_rest", {}))
            self.slot_state["long_rest"] = current_long
        else:
            self.slot_state = {
                "long_rest": _copy_slot_pools(self.slot_schedule.get("long_rest", {})),
                "short_rest": _copy_slot_pools(self.slot_schedule.get("short_rest", {})),
            }
        self.spell_slots = _aggregate_slot_schedule(self.slot_state)


@dataclass
class CharacterSheet:
    identity: CharacterIdentity = field(default_factory=CharacterIdentity)
    abilities: Dict[str, AbilityBlock] = field(
        default_factory=lambda: {name: AbilityBlock() for name in ABILITY_NAMES}
    )
    combat: CombatStats = field(default_factory=CombatStats)
    proficiencies: ProficiencySet = field(default_factory=ProficiencySet)
    equipment: List[EquipmentItem] = field(default_factory=list)
    features: List[FeatureEntry] = field(default_factory=list)
    resources: List[ResourcePool] = field(default_factory=list)
    spellcasting: SpellcastingData = field(default_factory=SpellcastingData)
    feature_options: Dict[str, str] = field(default_factory=dict)
    class_options: Dict[str, List[str]] = field(default_factory=dict)
    notes: Dict[str, str] = field(default_factory=dict)

    def get_ability(self, name: str) -> AbilityBlock:
        key = name.upper()
        if key not in self.abilities:
            raise KeyError(f"Unknown ability: {name}")
        return self.abilities[key]

    def proficiency_bonus(self) -> int:
        return self.proficiencies.proficiency_bonus


def character_sheet_to_dict(sheet: CharacterSheet, compendium: Any = None) -> Dict[str, Any]:
    data = asdict(sheet)
    
    # Minify equipment if compendium is available
    if compendium and "equipment" in data:
        minified_equipment = []
        for item in sheet.equipment:
            entry = {
                "name": item.name,
                "quantity": item.quantity,
                "attuned": item.attuned,
            }
            if item.compendium_id:
                entry["compendium_id"] = item.compendium_id
            
            # If we have a compendium match, we can omit static data if it matches
            # For now, we simple-save: if compendium_id exists, we omit weight/cost/bonuses
            # This relies on the hydrator to restore them.
            
            if not item.compendium_id:
                # Full save
                entry["weight_lb"] = item.weight_lb
                entry["notes"] = item.notes
                entry["bonuses"] = item.bonuses
                entry["cost"] = item.cost
                entry["rarity"] = item.rarity
            else:
                # Partial save: keep notes, drop statics
                if item.notes:
                    entry["notes"] = item.notes
                # We could check if weight differs from default, but for now let's strict-reference
            
            minified_equipment.append(entry)
        data["equipment"] = minified_equipment

    return data


def _build_ability_block(data: Mapping[str, Any]) -> AbilityBlock:
    return AbilityBlock(
        score=int(data.get("score", 10) or 10),
        modifier=data.get("modifier"),
        save_proficient=bool(data.get("save_proficient", False)),
        save_bonus=int(data.get("save_bonus", 0) or 0),
    )


def _build_classes(entries: Iterable[Mapping[str, Any]]) -> List[ClassProgression]:
    result: List[ClassProgression] = []
    for entry in entries:
        name = str(entry.get("name", ""))
        level = int(entry.get("level", 0) or 0)
        subclass = entry.get("subclass")
        result.append(ClassProgression(name=name, level=level, subclass=subclass or None))
    return result


def _build_equipment(entries: Iterable[Mapping[str, Any]], compendium: Any = None) -> List[EquipmentItem]:
    items: List[EquipmentItem] = []
    for entry in entries:
        compendium_id = str(entry.get("compendium_id", "") or "")
        name = str(entry.get("name", ""))
        
        # Defaults
        weight_lb = float(entry.get("weight_lb", 0.0) or 0.0)
        cost = str(entry.get("cost", ""))
        rarity = str(entry.get("rarity", ""))
        bonuses = entry.get("bonuses") or {}
        
        # Hydrate from compendium if possible
        if compendium and (compendium_id or name):
            # Try ID first, then name
            record = None
            if compendium_id:
                record = compendium.record_by_id(compendium_id)
            
            if not record and name:
                 # Fallback search by name if ID missing (migration)
                 # Note: Ideally we want a robust lookup. 
                 # For now, we rely on checking equipment list if we implement a `find_item`
                 pass

            if record:
                # Hydrate missing/static fields
                compendium_id = record.get("id", compendium_id)
                if not name: name = record.get("name", name)
                
                # Check for weight string in compendium (e.g. "65 lb.") and parse if local is 0.0
                if weight_lb == 0.0:
                    w_str = str(record.get("weight", "")).lower().replace("lb.", "").strip()
                    try:
                        weight_lb = float(w_str)
                    except ValueError:
                        pass
                
                if not cost: cost = str(record.get("cost", ""))
                if not rarity: rarity = str(record.get("rarity", ""))
                
                # Merge bonuses: Compendium modifiers -> bonuses
                # Note: The model calls them 'bonuses', the compendium 'modifiers'.
                # We need to map them if we want them effective. 
                # Currently model.EquipmentItem.bonuses seems to be a simple dict, 
                # while compendium uses a list of modifier objects.
                # For this refactor, we won't fully reimplement the modifier engine here,
                # but we should ensure we don't LOSE data.
                pass
        
        items.append(
            EquipmentItem(
                name=name,
                quantity=int(entry.get("quantity", 1) or 1),
                weight_lb=weight_lb,
                attuned=bool(entry.get("attuned", False)),
                notes=str(entry.get("notes", "")),
                bonuses={str(key): int(value) for key, value in bonuses.items()},
                compendium_id=compendium_id,
                cost=cost,
                rarity=rarity,
            )
        )
    return items


def _build_features(entries: Iterable[Mapping[str, Any]], compendium: Any = None) -> List[FeatureEntry]:
    features = []
    for entry in entries:
        compendium_id = str(entry.get("compendium_id", "") or "")
        description = str(entry.get("description", ""))
        
        if compendium and compendium_id:
             record = compendium.record_by_id(compendium_id)
             if record:
                  # Hydrate
                  # Note: Compendium text might be in 'text' object or direct description
                  if not description:
                        text_val = record.get("text")
                        if isinstance(text_val, dict):
                            description = text_val.get("full", "")
                        elif isinstance(text_val, str):
                            description = text_val
                  
        features.append(FeatureEntry(
            title=str(entry.get("title", "")),
            source=str(entry.get("source", "")),
            description=description,
            compendium_id=compendium_id,
        ))
    return features


def _build_resources(entries: Iterable[Mapping[str, Any]]) -> List[ResourcePool]:
    return [
        ResourcePool(
            name=str(entry.get("name", "")),
            max_uses=int(entry.get("max_uses", 0) or 0),
            current_uses=int(entry.get("current_uses", 0) or 0),
            refreshes_on=str(entry.get("refreshes_on", "")),
        )
        for entry in entries
    ]


def _build_spell_entries(entries: Iterable[Mapping[str, Any]]) -> List[SpellAccessEntry]:
    result: List[SpellAccessEntry] = []
    for entry in entries:
        result.append(
            SpellAccessEntry(
                spell_name=str(entry.get("spell_name", "")),
                source=str(entry.get("source", "")),
                prepared=bool(entry.get("prepared", False)),
                category=str(entry.get("category", "")),
                source_type=str(entry.get("source_type", "")),
                source_id=str(entry.get("source_id", "")),
                ability=entry.get("ability"),
                granted=bool(entry.get("granted", False)),
            )
        )
    return result


def _build_spell_sources(entries: Iterable[Mapping[str, Any]]) -> List[SpellSourceRecord]:
    result: List[SpellSourceRecord] = []
    for entry in entries:
        result.append(
            SpellSourceRecord(
                source_type=str(entry.get("source_type", "")),
                source_id=str(entry.get("source_id", "")),
                label=str(entry.get("label", "")),
                ability=entry.get("ability"),
            )
        )
    return result


def character_sheet_from_dict(data: Mapping[str, Any], compendium: Any = None) -> CharacterSheet:
    identity_data = data.get("identity", {}) or {}
    classes = _build_classes(identity_data.get("classes", []) or [])
    asi_choices_raw = identity_data.get("asi_choices", {}) or {}
    asi_choices: Dict[int, str] = {}
    for key, value in asi_choices_raw.items():
        try:
            level = int(key)
        except (TypeError, ValueError):
            continue
        text = str(value or "").strip()
        if not text:
            continue
        asi_choices[level] = text

    raw_background_choices = identity_data.get("background_choices", {}) or {}
    background_choice_data = raw_background_choices if isinstance(raw_background_choices, Mapping) else {}
    background_choices = BackgroundSelection(
        ability_choices=list(background_choice_data.get("ability_choices", []) or []),
        skill_choices=list(background_choice_data.get("skill_choices", []) or []),
        tool_choices=list(background_choice_data.get("tool_choices", []) or []),
        language_choices=list(background_choice_data.get("language_choices", []) or []),
        feat_choice=str(background_choice_data.get("feat_choice", "") or ""),
    )

    identity = CharacterIdentity(
        name=str(identity_data.get("name", "")),
        ancestry=str(identity_data.get("ancestry", "")),
        ancestry_subtype=str(identity_data.get("ancestry_subtype", "") or ""),
        background=str(identity_data.get("background", "")),
        background_choices=background_choices,
        player=str(identity_data.get("player", "")),
        alignment=str(identity_data.get("alignment", "")),
        experience=int(identity_data.get("experience", 0) or 0),
        classes=classes,
        level_cap=int(identity_data.get("level_cap", 0) or 0),
        ability_generation=str(identity_data.get("ability_generation", "manual") or "manual"),
        asi_choices=asi_choices,
        portrait_path=str(identity_data.get("portrait_path", "")),
    )

    abilities_data = data.get("abilities", {}) or {}
    abilities = {
        name: _build_ability_block(abilities_data.get(name, {}) or {})
        for name in ABILITY_NAMES
    }

    combat_data = data.get("combat", {}) or {}
    combat = CombatStats(
        armor_class=int(combat_data.get("armor_class", 10) or 10),
        initiative_bonus=int(combat_data.get("initiative_bonus", 0) or 0),
        speed_ft=int(combat_data.get("speed_ft", 30) or 30),
        max_hp=int(combat_data.get("max_hp", 0) or 0),
        current_hp=int(combat_data.get("current_hp", 0) or 0),
        temp_hp=int(combat_data.get("temp_hp", 0) or 0),
        hit_dice=str(combat_data.get("hit_dice", "")),
        death_save_successes=int(combat_data.get("death_save_successes", 0) or 0),
        death_save_failures=int(combat_data.get("death_save_failures", 0) or 0),
    )

    prof_data = data.get("proficiencies", {}) or {}
    proficiencies = ProficiencySet(
        proficiency_bonus=int(prof_data.get("proficiency_bonus", 2) or 2),
        armor=list(prof_data.get("armor", []) or []),
        weapons=list(prof_data.get("weapons", []) or []),
        tools=list(prof_data.get("tools", []) or []),
        languages=list(prof_data.get("languages", []) or []),
        skills=dict(prof_data.get("skills", {}) or {}),
    )

    equipment = _build_equipment(data.get("equipment", []) or [], compendium=compendium)
    features = _build_features(data.get("features", []) or [], compendium=compendium)
    resources = _build_resources(data.get("resources", []) or [])

    spell_data = data.get("spellcasting", {}) or {}
    slot_schedule_data: Dict[str, Dict[int, int]] = {}
    for rest_key, pool in (spell_data.get("slot_schedule", {}) or {}).items():
        slot_schedule_data[str(rest_key)] = _normalise_slot_dict(pool or {})

    slot_state_data: Dict[str, Dict[int, int]] = {}
    for rest_key, pool in (spell_data.get("slot_state", {}) or {}).items():
        slot_state_data[str(rest_key)] = _normalise_slot_dict(pool or {})

    spellcasting = SpellcastingData(
        spellcasting_ability=str(spell_data.get("spellcasting_ability", "INT") or "INT"),
        attack_bonus=spell_data.get("attack_bonus"),
        save_dc=spell_data.get("save_dc"),
        known_spells=_build_spell_entries(spell_data.get("known_spells", []) or []),
        spell_sources=_build_spell_sources(spell_data.get("spell_sources", []) or []),
        slot_schedule=slot_schedule_data,
        slot_state=slot_state_data,
        spell_slots={int(level): int(amount) for level, amount in (spell_data.get("spell_slots", {}) or {}).items()},
        prepared_spells=list(spell_data.get("prepared_spells", []) or []),
    )

    raw_class_options = data.get("class_options", {}) or {}
    class_options: Dict[str, List[str]] = {}
    for key, values in raw_class_options.items():
        if not key:
            continue
        if isinstance(values, (list, tuple)):
            cleaned = [str(value).strip() for value in values if str(value).strip()]
        else:
            string_value = str(values).strip()
            cleaned = [string_value] if string_value else []
        if cleaned:
            unique = list(dict.fromkeys(cleaned))
            class_options[str(key)] = unique

    sheet = CharacterSheet(
        identity=identity,
        abilities=abilities,
        combat=combat,
        proficiencies=proficiencies,
        equipment=equipment,
        features=features,
        resources=resources,
        spellcasting=spellcasting,
        feature_options=dict(data.get("feature_options", {}) or {}),
        class_options=class_options,
        notes=dict(data.get("notes", {}) or {}),
    )
    return sheet


__all__ = [
    "ABILITY_NAMES",
    "AbilityBlock",
    "CharacterIdentity",
    "ClassProgression",
    "BackgroundSelection",
    "CombatStats",
    "ProficiencySet",
    "EquipmentItem",
    "FeatureEntry",
    "ResourcePool",
    "SpellAccessEntry",
    "SpellSourceRecord",
    "SpellcastingData",
    "CharacterSheet",
    "character_sheet_to_dict",
    "character_sheet_from_dict",
]