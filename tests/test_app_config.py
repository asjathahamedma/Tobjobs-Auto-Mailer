import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import config


class AppConfigTests(unittest.TestCase):
    def test_new_install_starts_unconfigured_and_does_not_auto_run(self):
        defaults = config.get_default_app_config()

        self.assertFalse(defaults["app"]["onboarding_completed"])
        self.assertFalse(defaults["app"]["auto_run_on_launch"])
        self.assertEqual(defaults["profiles"], {})

    def test_existing_config_is_not_forced_through_first_run_setup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "app_config.json"
            env_path = Path(temp_dir) / ".env"
            config_path.write_text(json.dumps({"mailer": {"your_name": "Existing user"}}), encoding="utf-8")
            with patch.object(config, "APP_CONFIG_FILE", str(config_path)), patch.object(
                config, "ENV_FILE", str(env_path)
            ):
                loaded = config.load_app_config()

        self.assertTrue(loaded["app"]["onboarding_completed"])
        self.assertEqual(loaded["mailer"]["your_name"], "Existing user")


if __name__ == "__main__":
    unittest.main()
