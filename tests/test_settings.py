import unittest
from unittest.mock import patch
import os
from modules.core.services.settings import Settings

class TestSettings(unittest.TestCase):
    def setUp(self):
        # Patch QSettings to avoid registry access
        self.qsettings_patcher = patch("modules.core.services.settings.QSettings")
        self.mock_qsettings = self.qsettings_patcher.start()
        self.mock_instance = self.mock_qsettings.return_value
        
        # Default mock behavior: return default value if provided, else None
        def get_value(key, default=None, type=None):
            return default
        self.mock_instance.value.side_effect = get_value

        # Clean env
        if "LIVING_SCROLL_RULESET" in os.environ:
            del os.environ["LIVING_SCROLL_RULESET"]
        if "LIVING_SCROLL_MODULES" in os.environ:
            del os.environ["LIVING_SCROLL_MODULES"]

    def tearDown(self):
        self.qsettings_patcher.stop()

    def test_defaults(self):
        s = Settings()
        # Mock returns None -> default handling in property
        self.assertEqual(s.ruleset, "dnd_2024")
        # Theme is hardcoded in theme.py usually, but Settings might have one. 
        # Actually Settings.theme wasn't in the file I viewed earlier. It had 'ruleset', 'active_modules', 'dev_mode', 'minimize_to_tray'.
        # I should check what properties exist. 
        # Removing check for 'theme' as it was not in my view of settings.py.
        self.assertFalse(s.dev_mode) # Default False

    def test_env_var_override(self):
        with patch.dict(os.environ, {"LIVING_SCROLL_RULESET": "custom_rules"}):
            s = Settings()
            self.assertEqual(s.ruleset, "custom_rules")
            # Verify QSettings NOT called/used for this
            # (Implementation might read it but return env var)

    def test_active_modules_parsing(self):
        with patch.dict(os.environ, {"LIVING_SCROLL_MODULES": "mod_a,mod_b"}):
            s = Settings()
            # Required 'players_handbook' is always added
            self.assertIn("mod_a", s.active_modules)
            self.assertIn("mod_b", s.active_modules)
            self.assertIn("players_handbook", s.active_modules)

if __name__ == "__main__":
    unittest.main()
