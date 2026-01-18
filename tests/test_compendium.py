import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path
from modules.compendium.service import Compendium, _load_payload

class TestCompendium(unittest.TestCase):
    def setUp(self):
        self.sample_payload = {
            "spells": [{
                "id": "spell:fireball",
                "name": "Fireball",
                "type": "spell",
                "level": 3,
                "school": "Evocation"
            }],
            "classes": [{
                "id": "class:wizard",
                "name": "Wizard",
                "type": "class",
                "hit_die": "d6"
            }],
            "equipment": [{
                "id": "item:sword",
                "name": "Sword",
                "type": "item",
                "cost": "10gp"
            }]
        }
        self.compendium = Compendium(self.sample_payload)

    def test_record_by_id(self):
        # Direct hit
        rec = self.compendium.record_by_id("spell:fireball")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["name"], "Fireball")

        # Miss
        rec = self.compendium.record_by_id("spell:nada")
        self.assertIsNone(rec)

    def test_filter_by_type(self):
        # Use public API records()
        spells = self.compendium.records("spells")
        self.assertEqual(len(spells), 1)
        self.assertEqual(spells[0]["name"], "Fireball")

        items = self.compendium.records("equipment")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "Sword")

    def test_filter_by_custom_predicate(self):
        # Manual filter on records
        all_spells = self.compendium.records("spells")
        results = [s for s in all_spells if s.get("name", "").startswith("F")]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Fireball")


class TestCompendiumLoading(unittest.TestCase):
    @patch("modules.compendium.service.Path")
    @patch("modules.compendium.service._load_dataset_directory")
    def test_load_payload_iterates_modules(self, mock_load_dir, mock_path_cls):
        # Setup mocks
        mock_root = MagicMock()
        mock_path_cls.return_value = mock_root
        
        # Determine behavior of the root path
        mock_root.is_file.return_value = False
        mock_root.is_dir.return_value = True
        
        # Create mock module directories
        mod_1 = MagicMock()
        mod_1.is_dir.return_value = True
        mod_1.name = "core_rules"
        # Make comparable for sorted()
        mod_1.__lt__ = lambda self, other: self.name < other.name
        
        mod_2 = MagicMock()
        mod_2.is_dir.return_value = True
        mod_2.name = "expansion"
        mod_2.__lt__ = lambda self, other: self.name < other.name
        
        mock_root.iterdir.return_value = [mod_1, mod_2]
        
        # Mock payload returns - must use valid keys like 'spells'
        mock_load_dir.side_effect = [
            {"spells": [{"name": "S1", "id": "s1"}]}, 
            {"spells": [{"name": "S2", "id": "s2"}]}
        ]
        
        # Test 1: Load all
        result = _load_payload(mock_root)
        self.assertEqual(len(result["spells"]), 2)
        
        # Test 2: Filter modules
        mock_load_dir.reset_mock()
        mock_load_dir.side_effect = [{"spells": [{"name": "S1", "id": "s1"}]}] # Called once
        
        result_filtered = _load_payload(mock_root, active_modules={"core_rules"})
        self.assertEqual(len(result_filtered["spells"]), 1)

if __name__ == "__main__":
    unittest.main()
