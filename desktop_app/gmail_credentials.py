import keyring


KEYRING_SERVICE = "com.asjath.topjobsautomailer"
GMAIL_PASSWORD_KEY = "gmail-app-password"


class GmailCredentialStore:
    """Stores Gmail app passwords in the operating system credential store."""

    def get_password(self, fallback=""):
        password = keyring.get_password(KEYRING_SERVICE, GMAIL_PASSWORD_KEY)
        if password:
            return password
        if fallback:
            self.set_password(fallback)
            return self.normalize(fallback)
        return ""

    def set_password(self, password):
        normalized = self.normalize(password)
        if not normalized:
            raise ValueError("Gmail app password cannot be empty.")
        keyring.set_password(KEYRING_SERVICE, GMAIL_PASSWORD_KEY, normalized)

    def is_configured(self):
        return bool(keyring.get_password(KEYRING_SERVICE, GMAIL_PASSWORD_KEY))

    def clear_legacy_oauth_token(self):
        legacy_key = "gmail-oauth-token"
        if keyring.get_password(KEYRING_SERVICE, legacy_key):
            keyring.delete_password(KEYRING_SERVICE, legacy_key)

    @staticmethod
    def normalize(password):
        return "".join((password or "").split())
