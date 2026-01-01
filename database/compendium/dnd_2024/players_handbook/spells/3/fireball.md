---
name: Fireball
type: spell
level: 3
school: Evocation
ritual: false
casting_time: "1 action"
range: "150 feet"
components: [V, S, M]
material: "A ball of bat guano and sulfur"
duration: "Instantaneous"
concentration: false
classes: [Sorcerer, Wizard]

# Automation Data
actions:
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
