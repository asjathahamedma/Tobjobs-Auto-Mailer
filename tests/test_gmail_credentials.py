import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop_app.gmail_credentials import (
    GMAIL_PASSWORD_KEY,
    KEYRING_SERVICE,
    GmailCredentialStore,
)
from tauri_bridge import cli


class GmailCredentialTests(unittest.TestCase):
    def test_password_is_normalized_and_kept_in_the_credential_store(self):
        stored = {}

        with patch("desktop_app.gmail_credentials.keyring.set_password") as set_password, patch(
            "desktop_app.gmail_credentials.keyring.get_password",
            side_effect=lambda service, key: stored.get((service, key)),
        ):
            set_password.side_effect = lambda service, key, value: stored.update(
                {(service, key): value}
            )
            credential_store = GmailCredentialStore()
            credential_store.set_password("abcd efgh ijkl mnop")

            self.assertEqual(
                credential_store.get_password(),
                "abcdefghijklmnop",
            )

        set_password.assert_called_once_with(
            KEYRING_SERVICE,
            GMAIL_PASSWORD_KEY,
            "abcdefghijklmnop",
        )

    def test_config_read_migrates_legacy_password_and_hides_it(self):
        stored = {}

        class FakeConfigStore:
            def __init__(self):
                self.config = {
                    "mailer": {
                        "auth": {
                            "sender_email": "person@example.com",
                            "app_password": "abcd efgh ijkl mnop",
                        }
                    }
                }

            def snapshot(self):
                return self.config

            def save(self, config):
                self.config = config

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("desktop_app.gmail_credentials.keyring.get_password",
                       side_effect=lambda service, key: stored.get((service, key))), patch(
                "desktop_app.gmail_credentials.keyring.set_password",
                side_effect=lambda service, key, value: stored.update(
                    {(service, key): value}
                ),
            ), patch("desktop_app.gmail_credentials.keyring.delete_password"), patch.object(
                cli, "app_home", return_value=Path(temp_dir)
            ):
                store = FakeConfigStore()
                config = cli.load_config_for_ui(store)

            self.assertEqual(config["mailer"]["auth"]["app_password"], "")
            self.assertTrue(config["mailer"]["auth"]["app_password_configured"])
            self.assertEqual(
                stored[(KEYRING_SERVICE, GMAIL_PASSWORD_KEY)],
                "abcdefghijklmnop",
            )
            self.assertEqual(store.config["mailer"]["auth"]["app_password"], "")
            self.assertEqual(
                (Path(temp_dir) / ".env").read_text(encoding="utf-8"),
                'EMAIL_ADDRESS="person@example.com"\n',
            )

    def test_config_read_removes_stale_plaintext_env_password(self):
        stored = {(KEYRING_SERVICE, GMAIL_PASSWORD_KEY): "saved-password"}

        class FakeConfigStore:
            config = {
                "mailer": {
                    "auth": {
                        "sender_email": "person@example.com",
                        "app_password": "",
                    }
                }
            }

            def snapshot(self):
                return self.config

            def save(self, config):
                self.config = config

        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                'EMAIL_ADDRESS="person@example.com"\nEMAIL_PASSWORD="old-password"\n',
                encoding="utf-8",
            )
            with patch("desktop_app.gmail_credentials.keyring.get_password",
                       side_effect=lambda service, key: stored.get((service, key))), patch(
                "desktop_app.gmail_credentials.keyring.set_password"
            ) as set_password, patch(
                "desktop_app.gmail_credentials.keyring.delete_password"
            ), patch.object(cli, "app_home", return_value=Path(temp_dir)):
                store = FakeConfigStore()
                config = cli.load_config_for_ui(store)

            set_password.assert_not_called()
            self.assertTrue(config["mailer"]["auth"]["app_password_configured"])
            self.assertEqual(
                env_path.read_text(encoding="utf-8"),
                'EMAIL_ADDRESS="person@example.com"\n',
            )


if __name__ == "__main__":
    unittest.main()
