# Compendium Guide

This document defines the organization, data format, and schema specifications for the Living Scroll game content compendium.

---

## Table of Contents

1. [Overview](#overview)
2. [Directory Structure](#directory-structure)
3. [Module Status](#module-status)
4. [File Format Specification](#file-format-specification)
5. [Schema Reference](#schema-reference)
6. [Formula Syntax](#formula-syntax)

---

## Overview

The compendium is a filesystem-based database of D&D 2024 game content. All content is stored as **Markdown files with YAML frontmatter**, enabling both machine-readable structured data and human-readable documentation in a single file.

### Design Principles

| Principle | Description |
|-----------|-------------|
| **Single Source of Truth** | One file per game entity (spell, item, class, monster, rule). |
| **Separation of Concerns** | YAML frontmatter contains structured data; Markdown body contains prose. |
| **Human-Readable** | Files can be read and edited with any text editor. |
| **Extensible** | New content types can be added by defining new frontmatter schemas. |

---

## Directory Structure

```
database/compendium/dnd_2024/
├── players_handbook/           # Core rulebook content
│   ├── metadata.json           # Module metadata
│   ├── classes/                # Class definitions
│   │   └── {class_name}/
│   │       ├── base.md         # Base class features
│   │       └── subclasses/     # Subclass definitions
│   ├── equipment/              # Items, weapons, armor, tools
│   ├── monsters/               # Monster stat blocks
│   ├── rules/                  # Gameplay rules
│   ├── species/                # Playable species
│   └── spells/                 # Spell definitions
│
└── eberron_forge_of_the_artificer/  # Expansion module
    └── classes/artificer/
        ├── base.md
        └── subclasses/
```

---

## Module Status

| Module | Status | Description |
|--------|--------|-------------|
| `players_handbook/` | **Functional** | Core D&D 2024 content including all classes, equipment, monsters, rules, species, and spells from the Player's Handbook and Basic Rules. |
| `eberron_forge_of_the_artificer/` | **Complete** | Full Artificer class with five subclasses: Alchemist, Armorer, Artillerist, Battle Smith, Cartographer. |
| `astarion_s_book_of_hungers/` | Planned | Reserved for vampire-themed content. |
| `forgotten_realms_heroes_of_faerun/` | Planned | Reserved for Forgotten Realms content. |
| `lorwyn_first_light/` | Planned | Reserved for Magic: The Gathering crossover content. |

---

## File Format Specification

### General Structure

Every compendium file follows this format:

```markdown
---
# YAML Frontmatter (structured data)
name: "Entity Name"
type: entity_type
# ... additional fields
---

# Entity Name

Markdown body with human-readable description, rules text, and flavor.
```

### Common Fields

These fields are available on all entity types:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | **Yes** | Display name shown in the UI. |
| `id` | string | No | Unique identifier. Defaults to filename (without extension). |
| `source` | string | No | Source book reference (e.g., `"PHB 2024"`). |
| `tags` | array | No | Searchable tags for filtering. |

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Filenames | `snake_case.md` | `cure_wounds.md`, `plate_armor.md` |
| Directory names | `snake_case/` | `players_handbook/`, `subclasses/` |
| IDs | `type:name` | `spell:fireball`, `class:wizard` |

---

## Schema Reference

### Spells

Spell files define both the mechanical properties and descriptive text.

```md
---
name: Fireball
type: spell
level: 3
school: Evocation
ritual: false
casting_time: "1 action"
range: "150 feet"
components: [V, S, M]
material: "A tiny ball of bat guano and sulfur"
material_price: ""
duration: "Instantaneous"
concentration: false
classes: [Sorcerer, Wizard]
actions: # Optional: Automation data for the rules engine
  - type: save
    ability: dex
    on_pass: "half"
    on_fail: "full"
    damage:
      - formula: "8d6"
        type: fire
        scaling: "1d6"
---
# Fireball
*Level 3 Evocation (Sorcerer, Wizard)*
**Casting Time:** Action
**Range:** 150 feet
**Components:** V, S, M (a ball of bat guano and sulfur)
**Duration:** Instantaneous
A bright streak flashes from you to a point you choose within range and then blossoms with a low roar into a fiery explosion. Each creature in a 20-foot-radius Sphere centered on that point makes a Dexterity saving throw, taking **8d6 Fire damage** on a failed save or half as much damage on a successful one.
Flammable objects in the area that aren’t being worn or carried start burning.
**Using a Higher-Level Spell Slot.** The damage increases by 1d6 for each spell slot level above 3.
```

#### Spell-Specific Fields

| Field | Type | Description |
|-------|------|-------------|
| `level` | integer | Spell level (0–9). |
| `school` | string | Abjuration, Conjuration, Divination, Enchantment, Evocation, Illusion, Necromancy, Transmutation. |
| `ritual` | boolean | Whether the spell can be cast as a ritual. |
| `casting_time` | string | Time required to cast. |
| `range` | string | Casting range. |
| `components` | array | Components required: `V` (verbal), `S` (somatic), `M` (material). |
| `material` | string | Material component description (if applicable). |
| `duration` | string | How long the spell lasts. |
| `concentration` | boolean | Whether the spell requires concentration. |
| `classes` | array | Classes that have access to this spell. |

---

### Equipment (Items)

Equipment files use the **modifier system** to apply effects to character statistics.

```yaml
---
name: Plate Armor
type: item
item_type: armor
armor_category: heavy
cost: "1,500 gp"
weight: "65 lb."
stealth_disadvantage: true
strength_requirement: 15

modifiers:
  - target: "attributes.ac.calculation"
    mode: "override"
    formula: "18"
---

# Plate Armor

Plate consists of shaped, interlocking metal plates...
```

#### Equipment-Specific Fields

| Field | Type | Description |
|-------|------|-------------|
| `item_type` | string | `weapon`, `armor`, `tool`, `gear`, `magic_item`. |
| `armor_category` | string | `light`, `medium`, `heavy`, `shield`. |
| `weapon_category` | string | `simple`, `martial`. |
| `cost` | string | Purchase price. |
| `weight` | string | Item weight. |
| `rarity` | string | For magic items: `common`, `uncommon`, `rare`, `very_rare`, `legendary`. |

#### Modifier System

Modifiers alter character statistics when the item is equipped.

| Field | Description |
|-------|-------------|
| `target` | The stat path to modify (e.g., `attributes.ac.calculation`). |
| `mode` | How to apply: `add`, `multiply`, `override`, `min`, `max`. |
| `formula` | The value or formula to apply. |

---

### Monsters

Monster files contain stat blocks for the Monster Manual browser.

```yaml
---
name: Goblin
type: Humanoid
size: Small
alignment: Neutral Evil
ac: 15
hp: "7 (2d6)"
speed: "30 ft."
cr: "1/4"

stats:
  str: 8
  dex: 14
  con: 10
  int: 10
  wis: 8
  cha: 8

traits:
  - name: Nimble Escape
    description: "The goblin can take the Disengage or Hide action as a bonus action."

actions:
  - name: Scimitar
    description: "Melee Weapon Attack: +4 to hit, reach 5 ft. Hit: 5 (1d6 + 2) slashing damage."
---
```

#### Monster-Specific Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Creature type: Aberration, Beast, Celestial, Construct, Dragon, Elemental, Fey, Fiend, Giant, Humanoid, Monstrosity, Ooze, Plant, Undead. |
| `size` | string | Tiny, Small, Medium, Large, Huge, Gargantuan. |
| `alignment` | string | Creature alignment. |
| `ac` | integer | Armor Class. |
| `hp` | string | Hit points with hit dice formula. |
| `speed` | string | Movement speeds. |
| `cr` | string | Challenge Rating. |
| `stats` | object | Ability scores (`str`, `dex`, `con`, `int`, `wis`, `cha`). |
| `traits` | array | Special traits (name + description). |
| `actions` | array | Actions (name + description). |

---

### Classes

Class files define level progression and features.

```yaml
---
name: Wizard
type: class
hit_die: d6
primary_ability: Intelligence
saves: [Intelligence, Wisdom]
proficiencies:
  armor: []
  weapons: [Daggers, Darts, Slings, Quarterstaffs, Light Crossbows]
  tools: []
  skills:
    choose: 2
    from: [Arcana, History, Insight, Investigation, Medicine, Religion]

progression:
  - level: 1
    features: [Spellcasting, Arcane Recovery]
    spell_slots: [2, 0, 0, 0, 0, 0, 0, 0, 0]
  - level: 2
    features: [Arcane Tradition]
    spell_slots: [3, 0, 0, 0, 0, 0, 0, 0, 0]
---
```

---

### Rules

Rule section files for the compendium browser.

```yaml
---
name: "Making an Attack"
type: rule_section
category: combat
---

# Making an Attack

Whether you're striking with a melee weapon, firing a ranged weapon...
```

---

## Formula Syntax

Formulas are used in automation fields (`damage.formula`, `modifiers.formula`, etc.) and are evaluated by the rules engine.

### Dice Notation

| Syntax | Description | Example |
|--------|-------------|---------|
| `XdY` | Roll X dice with Y sides | `2d6`, `1d20` |
| `XdY+Z` | Roll and add modifier | `1d8+3` |
| `XdY-Z` | Roll and subtract | `2d6-1` |

### Variables

| Variable | Description |
|----------|-------------|
| `@level` | Total character level. |
| `@class_level` | Level in the relevant class. |
| `@mod` | Spellcasting ability modifier. |
| `@str`, `@dex`, `@con`, `@int`, `@wis`, `@cha` | Ability score modifiers. |
| `@prof` | Proficiency bonus. |

### Operators

| Operator | Description |
|----------|-------------|
| `+`, `-`, `*`, `/` | Arithmetic operations. |
| `//` | Integer division (floor). |
| `min(a, b)`, `max(a, b)` | Minimum/maximum functions. |

---

## Related Documentation

- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) — Codebase architecture overview.
- [README.md](../README.md) — Project overview and quick start.
