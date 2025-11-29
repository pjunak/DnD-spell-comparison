import json
import tempfile
import unittest
from pathlib import Path

from database import management, schema


def build_sample_dataset():
    return {
        "spells": [
            {
                "name": "Scorching Ray",
                "level": 2,
                "school": "Evocation",
                "casting_time": "1 action",
                "range": "120 feet",
                "duration": "Instantaneous",
                "components": ["V", "S"],
                "primary_effect": {
                    "effect_type": "primary",
                    "effect_data": {
                        "damage": {
                            "type": "fire",
                            "base": {"dice": 2, "die": 6},
                            "scaling": {"dice_per_slot": 1, "die": 6},
                            "use_modifier": True,
                            "constant": 0,
                        }
                    },
                },
                "modifiers": ["Agonizing Blast"],
            }
        ],
        "cantrips": [
            {
                "name": "Frostbite",
                "school": "Evocation",
                "casting_time": "1 action",
                "range": "60 feet",
                "duration": "Instantaneous",
                "components": ["V", "S"],
                "primary_effect": {
                    "effect_type": "primary",
                    "effect_data": {
                        "damage": {
                            "type": "cold",
                            "base": {"dice": 1, "die": 8},
                            "scaling": {"dice_per_slot": 0, "die": 8},
                            "use_modifier": False,
                            "constant": 0,
                        }
                    },
                },
                "scaling_levels": [1, 5, 11, 17],
                "modifiers": [],
            }
        ],
        "modifiers": [
            {
                "name": "Agonizing Blast",
                "category": "invocation",
                "scope": "spell",
                "description": "Adds the caster's ability modifier to damage.",
                "effect_data": {"damage_bonus": {"flat": 1}},
                "default_enabled": 0,
            },
            {
                "name": "War Caster",
                "category": "feat",
                "scope": "character",
                "description": "Improves concentration on spells.",
                "effect_data": {"concentration_advantage": True},
                "default_enabled": 0,
            },
        ],
    }


class DatabaseManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self._original_db_path = schema.DB_PATH
        self._original_db_file = schema.DB_FILE
        self.test_db_path = Path(self.temp_dir.name) / "spellBook.db"
        schema.DB_PATH = self.test_db_path
        schema.DB_FILE = str(self.test_db_path)
        management.schema.DB_PATH = self.test_db_path
        management.schema.DB_FILE = str(self.test_db_path)
        self.dataset_path = Path(self.temp_dir.name) / "dataset.json"

    def tearDown(self):
        schema.DB_PATH = self._original_db_path
        schema.DB_FILE = self._original_db_file
        management.schema.DB_PATH = self._original_db_path
        management.schema.DB_FILE = self._original_db_file

    def _write_dataset(self, payload=None):
        payload = payload or build_sample_dataset()
        self.dataset_path.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    def test_import_and_load_spells(self):
        payload = self._write_dataset()
        counts = management.import_dataset(self.dataset_path)
        self.assertEqual(counts["spells"], len(payload["spells"]))
        self.assertEqual(counts["cantrips"], len(payload["cantrips"]))
        self.assertEqual(counts["modifiers"], len(payload["modifiers"]))

        spells = management.load_spells()
        self.assertEqual(len(spells), 2)
        frostbite, scorching_ray = spells
        self.assertEqual(frostbite["level"], 0)
        self.assertEqual(scorching_ray["level"], 2)
        self.assertEqual(scorching_ray["modifiers"][0]["name"], "Agonizing Blast")
        damage_block = scorching_ray["effects"][0]["effect_data"]["damage"]
        self.assertEqual(damage_block["base"]["dice"], 2)

    def test_export_dataset_to_json_reports_counts(self):
        self._write_dataset()
        management.import_dataset(self.dataset_path)

        export_path = Path(self.temp_dir.name) / "export.json"
        counts = management.export_dataset_to_json(export_path)
        self.assertTrue(export_path.exists())
        self.assertEqual(counts["spells"], 1)
        self.assertEqual(counts["cantrips"], 1)
        # Modifiers are grouped by category counts.
        self.assertEqual(counts["modifiers"], 2)

    def test_load_modifiers_scope_filter(self):
        self._write_dataset()
        management.import_dataset(self.dataset_path)

        spell_modifiers = management.load_modifiers(scope="spell")
        self.assertEqual(len(spell_modifiers), 1)
        self.assertEqual(spell_modifiers[0]["name"], "Agonizing Blast")

        all_modifiers = management.load_modifiers()
        self.assertEqual(len(all_modifiers), 2)


if __name__ == "__main__":
    unittest.main()
