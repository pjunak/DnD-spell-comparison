import unittest

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from backend import plotting


def make_spell(
    name="Test Spell",
    level=1,
    base_dice=2,
    base_die=6,
    scaling_dice=1,
    scaling_die=6,
    constant=0,
):
    return {
        "name": name,
        "level": level,
        "effects": [
            {
                "effect_type": "primary",
                "effect_data": {
                    "damage": {
                        "type": "fire",
                        "base": {"dice": base_dice, "die": base_die},
                        "scaling": {"dice_per_slot": scaling_dice, "die": scaling_die},
                        "use_modifier": False,
                        "constant": constant,
                    }
                },
            }
        ],
    }


class ExtractEffectParamsTests(unittest.TestCase):
    def test_extract_effect_params_returns_expected_fields(self):
        spell = make_spell()
        params = plotting.extract_effect_params(spell)
        self.assertIsNotNone(params)
        params = params or {}
        self.assertEqual(params["start_rolls"], 2)
        self.assertEqual(params["initial_dice_value"], 6)

    def test_extract_effect_params_handles_absent_damage(self):
        spell = {"effects": [{"effect_type": "primary", "effect_data": {}}]}
        params = plotting.extract_effect_params(spell)
        self.assertIsNone(params)


class PlotSpellTests(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def test_plot_spell_creates_figure(self):
        spell = make_spell(level=3)
        fig = plotting.plot_spell(spell, mod=2, spell_full_name="Test Spell")
        self.assertIsNotNone(fig)
        self.assertTrue(fig.axes)
        self.assertGreater(len(fig.axes[0].lines), 0)

    def test_plot_spell_without_damage_raises(self):
        spell = {"name": "Empty", "level": 1, "effects": []}
        with self.assertRaises(ValueError):
            plotting.plot_spell(spell, mod=0, spell_full_name="Empty")


class CompareSpellsTests(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def test_compare_spells_requires_uniform_types(self):
        leveled = make_spell(name="Fireball", level=3)
        cantrip = make_spell(name="Ray", level=0)
        with self.assertRaises(ValueError):
            plotting.compare_spells([leveled, cantrip], mod=0)

    def test_compare_spells_requires_valid_count(self):
        spell = make_spell()
        with self.assertRaises(ValueError):
            plotting.compare_spells([spell], mod=0)
        too_many = [make_spell(name=f"Spell {i}") for i in range(plotting.MAX_COMPARE_SPELLS + 1)]
        with self.assertRaises(ValueError):
            plotting.compare_spells(too_many, mod=0)

    def test_compare_spells_returns_figure(self):
        fireball = make_spell(name="Fireball", level=3)
        lightning = make_spell(name="Lightning", level=3)
        fig = plotting.compare_spells([fireball, lightning], mod=3)
        self.assertTrue(fig.axes)
        self.assertGreater(len(fig.axes[0].lines), 0)


if __name__ == "__main__":
    unittest.main()
