import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src import mailer


class MailerContentTests(unittest.TestCase):
    def test_email_is_professional_and_does_not_claim_unverified_experience(self):
        with patch.object(mailer, "YOUR_NAME", "Taylor Example"), patch.object(
            mailer,
            "CONTACT_INFO",
            {
                "phone": "",
                "email": "taylor@example.com",
                "portfolio": "",
                "linkedin": "",
                "github": "",
            },
        ):
            subject, body = mailer.generate_email_content(
                {
                    "title": "Junior Software Developer",
                    "profile_summary": "Targets software development opportunities.",
                    "matched_title_keywords": "software developer",
                    "matched_description_keywords": "Python, APIs",
                }
            )

        self.assertEqual(subject, "Application for Junior Software Developer - Taylor Example")
        self.assertIn("Dear Hiring Team,", body)
        self.assertIn("Kind regards,\n\nTaylor Example", body)
        self.assertIn("Python, APIs", body)
        self.assertNotIn("hands-on work", body)
        self.assertNotIn("Portfolio:", body)

    def test_smtp_sends_resume_and_cover_letter_as_attachments(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            resume_path = Path(temp_dir) / "resume.pdf"
            cover_path = Path(temp_dir) / "cover-letter.pdf"
            resume_path.write_bytes(b"resume")
            cover_path.write_bytes(b"cover letter")
            smtp = MagicMock()
            with patch("src.mailer.smtplib.SMTP_SSL", return_value=smtp):
                sent, note = mailer.send_email(
                    "smtp.gmail.com",
                    465,
                    "sender@example.com",
                    "app-password",
                    "jobs@example.com",
                    "Application",
                    "Please see the attached documents.",
                    str(resume_path),
                    extra_attachments=[str(cover_path)],
                )

        self.assertTrue(sent)
        self.assertEqual(note, "Email sent successfully.")
        smtp.__enter__.return_value.login.assert_called_once_with(
            "sender@example.com", "app-password"
        )
        sent_message = smtp.__enter__.return_value.sendmail.call_args.args[2]
        self.assertIn("resume.pdf", sent_message)
        self.assertIn("cover-letter.pdf", sent_message)


if __name__ == "__main__":
    unittest.main()
