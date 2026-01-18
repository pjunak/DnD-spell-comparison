import unittest
from modules.character_sheet.model.model import (
    AbilityBlock,
    CharacterIdentity,
    ClassProgression,
    SpellcastingData,
    _default_slot_schedule,
    CharacterSheet,
    character_sheet_to_dict,
    character_sheet_from_dict
)

class TestAbilityBlock(unittest.TestCase):
    def test_effective_modifier_standard(self):
        # Score 10 -> +0
        ab = AbilityBlock(score=10)
        self.assertEqual(ab.effective_modifier(), 0)
        
        # Score 20 -> +5
        ab = AbilityBlock(score=20)
        self.assertEqual(ab.effective_modifier(), 5)
        
        # Score 1 -> -5
        ab = AbilityBlock(score=1)
        self.assertEqual(ab.effective_modifier(), -5)

    def test_effective_modifier_override(self):
        # Override takes precedence over score
        ab = AbilityBlock(score=10, modifier=5)
        self.assertEqual(ab.effective_modifier(), 5)

    def test_save_modifier(self):
        prof_bonus = 3
        # No proficiency: +1 from score 12
        ab = AbilityBlock(score=12, save_proficient=False)
        self.assertEqual(ab.save_modifier(prof_bonus), 1)

        # With proficiency: +1 + 3 = 4
        ab.save_proficient = True
        self.assertEqual(ab.save_modifier(prof_bonus), 4)
        
        # With extra bonus item/feature: +1 + 3 + 2 = 6
        ab.save_bonus = 2
        self.assertEqual(ab.save_modifier(prof_bonus), 6)


class TestCharacterIdentity(unittest.TestCase):
    def test_level_calculation(self):
        ident = CharacterIdentity()
        self.assertEqual(ident.level, 0)
        
        ident.classes.append(ClassProgression(name="Wizard", level=3))
        self.assertEqual(ident.level, 3)
        
        ident.classes.append(ClassProgression(name="Fighter", level=2))
        self.assertEqual(ident.level, 5)


class TestSpellcastingData(unittest.TestCase):
    def test_sync_slot_schedule_initializes_empty(self):
        sd = SpellcastingData()
        self.assertEqual(sd.spell_slots, {})

    def test_sync_slot_schedule_aggregates_slots(self):
        sd = SpellcastingData()
        # Simulate setup
        sd.slot_schedule = {
            "long_rest": {1: 4, 2: 2},
            "short_rest": {1: 2} # Warlock style
        }
        # Force sync (usually runs in post_init or manual call)
        sd.sync_slot_schedule()
        
        # Should sum long and short rest slots: Lvl 1: 4+2=6, Lvl 2: 2
        self.assertEqual(sd.spell_slots[1], 6)
        self.assertEqual(sd.spell_slots[2], 2)
        
        # State should be initialized to max if empty
        self.assertEqual(sd.slot_state["long_rest"][1], 4)
        self.assertEqual(sd.slot_state["short_rest"][1], 2)

    def test_reset_slots_long_rest(self):
        sd = SpellcastingData()
        sd.slot_schedule = {"long_rest": {1: 4}, "short_rest": {}}
        sd.sync_slot_schedule()
        
        # Spend a slot
        sd.slot_state["long_rest"][1] = 0
        sd.spell_slots = {1: 0}
        
        # Reset Long Rest
        sd.reset_slots("long_rest")
        self.assertEqual(sd.slot_state["long_rest"][1], 4)
        self.assertEqual(sd.spell_slots[1], 4)

    def test_reset_slots_short_rest(self):
        sd = SpellcastingData()
        sd.slot_schedule = {"long_rest": {1: 4}, "short_rest": {2: 2}}
        sd.sync_slot_schedule()
        
        # Spend slots
        sd.slot_state["long_rest"][1] = 0
        sd.slot_state["short_rest"][2] = 0
        
        sd.reset_slots("short_rest")
        self.assertEqual(sd.slot_state["long_rest"].get(1, 0), 0)
        self.assertEqual(sd.slot_state["short_rest"][2], 2)
        # Total slots should reflect this (0 + 2 = 2)
        self.assertEqual(sd.spell_slots.get(1, 0), 0)
        self.assertEqual(sd.spell_slots[2], 2)


class TestSerialization(unittest.TestCase):
    def test_round_trip(self):
        sheet = CharacterSheet()
        sheet.identity.name = "Test Hero"
        sheet.abilities["STR"].score = 18
        sheet.identity.classes.append(ClassProgression(name="Rogue", level=5))
        
        data = character_sheet_to_dict(sheet)
        self.assertEqual(data["identity"]["name"], "Test Hero")
        self.assertEqual(data["abilities"]["STR"]["score"], 18)
        
        loaded = character_sheet_from_dict(data)
        self.assertEqual(loaded.identity.name, "Test Hero")
        self.assertEqual(loaded.abilities["STR"].score, 18)
        self.assertEqual(len(loaded.identity.classes), 1)
        self.assertEqual(loaded.identity.classes[0].name, "Rogue")

if __name__ == "__main__":
    unittest.main()
