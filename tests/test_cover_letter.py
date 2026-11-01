import os
import tempfile
import unittest
from unittest.mock import patch

from src import mailer


class CoverLetterTests(unittest.TestCase):
    def test_cover_letter_uses_job_and_profile_context_without_inventing_experience(self):
        with patch.object(mailer, "YOUR_NAME", "Taylor Example"):
            paragraphs = mailer.generate_cover_letter_content(
                {
                    "title": "Software Developer",
                    "profile_summary": "Targets software development opportunities.",
                    "matched_title_keywords": "software developer",
                    "matched_description_keywords": "Python, APIs",
                }
            )

        content = "\n".join(paragraphs)
        self.assertIn("Software Developer", content)
        self.assertIn("Python, APIs", content)
        self.assertIn("Taylor Example", content)
        self.assertNotIn("years of experience", content.lower())

    def test_generates_pdf_cover_letter(self):
        with tempfile.TemporaryDirectory() as output_dir:
            old_directory = os.getcwd()
            try:
                os.chdir(output_dir)
                path = os.path.abspath(
                    mailer.create_cover_letter_pdf({"title": "Software Developer"})
                )
            finally:
                os.chdir(old_directory)

            with open(path, "rb") as letter_file:
                self.assertTrue(letter_file.read(5).startswith(b"%PDF-"))


if __name__ == "__main__":
    unittest.main()
