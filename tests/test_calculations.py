import unittest

from backend.calculations import chain_spell_distribution


class ChainSpellDistributionTests(unittest.TestCase):
    def test_constant_per_die_applies_shift(self):
        distribution = chain_spell_distribution(
            start_rolls=1,
            add_rolls=0,
            initial_dice_value=4,
            additional_dice_value=4,
            modifier=0,
            levels=1,
            constant_per_die=2,
        )
        self.assertEqual(sorted(distribution.keys()), [3, 4, 5, 6])
        self.assertAlmostEqual(distribution[3], 0.25)

    def test_distribution_normalized_and_levels_stack(self):
        distribution = chain_spell_distribution(
            start_rolls=1,
            add_rolls=1,
            initial_dice_value=4,
            additional_dice_value=6,
            modifier=2,
            levels=2,
            constant_per_die=1,
        )
        self.assertAlmostEqual(sum(distribution.values()), 1.0)
        # Minimum possible roll occurs when both dice show 1 before constants/modifier.
        min_total = min(distribution.keys())
        max_total = max(distribution.keys())
        self.assertGreaterEqual(min_total, 4)
        self.assertGreater(max_total, min_total)


if __name__ == "__main__":
    unittest.main()
