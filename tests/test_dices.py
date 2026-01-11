import unittest

from modules.core.services.dices import combination_distribution


class CombinationDistributionTests(unittest.TestCase):
    def test_single_roll_with_modifier(self):
        distribution = combination_distribution([1, 2], 1, modifier=3)
        self.assertEqual(distribution[4], 0.5)
        self.assertEqual(distribution[5], 0.5)
        self.assertAlmostEqual(sum(distribution.values()), 1.0)

    def test_multiple_rolls_distribution(self):
        distribution = combination_distribution([1, 2], 2)
        expected = {2: 0.25, 3: 0.5, 4: 0.25}
        self.assertEqual(distribution, expected)
        self.assertAlmostEqual(sum(distribution.values()), 1.0)


if __name__ == "__main__":
    unittest.main()
