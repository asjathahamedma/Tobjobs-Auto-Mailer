import json
import tempfile
import unittest
from pathlib import Path

from desktop_app.account_service import AccountService


class AccountServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.service = AccountService()
        self.service.path = Path(self.temp_dir.name) / "account.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_registers_and_signs_in_with_a_hashed_password(self):
        account = self.service.register("User@example.com", "a sufficiently long password")

        self.assertEqual(account, {"registered": True, "email": "user@example.com"})
        stored_account = json.loads(self.service.path.read_text(encoding="utf-8"))
        self.assertNotIn("password", stored_account)
        self.assertNotIn("a sufficiently long password", self.service.path.read_text(encoding="utf-8"))
        self.assertEqual(
            self.service.login("USER@example.com", "a sufficiently long password"),
            account,
        )

    def test_rejects_short_passwords_and_invalid_credentials(self):
        with self.assertRaisesRegex(ValueError, "at least 10 characters"):
            self.service.register("user@example.com", "short")

        self.service.register("user@example.com", "a sufficiently long password")
        with self.assertRaisesRegex(ValueError, "incorrect"):
            self.service.login("user@example.com", "incorrect password")

    def test_reports_unregistered_account(self):
        self.assertEqual(self.service.status(), {"registered": False, "email": ""})


if __name__ == "__main__":
    unittest.main()
