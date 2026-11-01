import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path

from src.config import absolute_in_app_home


PASSWORD_ITERATIONS = 310_000
PASSWORD_MIN_LENGTH = 10
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AccountService:
    """Stores a local app account for first-run registration and later sign-in."""

    def __init__(self):
        self.path = Path(absolute_in_app_home(os.path.join("data", "account.json")))

    def status(self):
        account = self._read_account()
        return {"registered": bool(account), "email": account.get("email", "") if account else ""}

    def register(self, email, password):
        normalized_email = (email or "").strip().lower()
        if not EMAIL_PATTERN.fullmatch(normalized_email):
            raise ValueError("Enter a valid email address.")
        if len(password or "") < PASSWORD_MIN_LENGTH:
            raise ValueError(f"Choose a password with at least {PASSWORD_MIN_LENGTH} characters.")
        if self._read_account():
            raise ValueError("An account already exists on this computer. Sign in instead.")

        salt = secrets.token_bytes(16)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(
                {
                    "email": normalized_email,
                    "salt": salt.hex(),
                    "password_hash": password_hash.hex(),
                    "iterations": PASSWORD_ITERATIONS,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(temporary_path, self.path)
        return {"registered": True, "email": normalized_email}

    def login(self, email, password):
        account = self._read_account()
        if not account:
            raise ValueError("No account is registered on this computer. Create one first.")

        submitted_email = (email or "").strip().lower()
        try:
            salt = bytes.fromhex(account["salt"])
            expected_hash = bytes.fromhex(account["password_hash"])
            iterations = int(account["iterations"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("The local account file is invalid. Contact support before continuing.") from error

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256", (password or "").encode("utf-8"), salt, iterations
        )
        if not hmac.compare_digest(submitted_email, account.get("email", "")) or not hmac.compare_digest(
            actual_hash, expected_hash
        ):
            raise ValueError("Email or password is incorrect.")
        return {"registered": True, "email": account["email"]}

    def _read_account(self):
        if not self.path.exists():
            return None
        try:
            account = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("Could not read the local account file.") from error
        if not isinstance(account, dict):
            raise ValueError("The local account file is invalid.")
        return account
