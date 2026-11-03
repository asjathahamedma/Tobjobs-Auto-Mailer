import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from bs4 import BeautifulSoup
from fastapi import HTTPException

from src import scraper
from src.resume_profiles import build_resume_profile
from src.web_engine import run_topjobs_search
from web_backend.app.auth import require_user
from web_backend.app.content import generate_application_content
from web_backend.app.schemas import SettingsUpdate


class WebFeatureTests(unittest.TestCase):
    def test_resume_profile_extracts_skill_keywords(self):
        profile = build_resume_profile(
            "Frontend developer with React, TypeScript, responsive design and Redux experience.",
            "frontend_resume.pdf",
        )
        self.assertIn("react", [keyword.lower() for keyword in profile["title_keywords"] + profile["description_keywords"]])
        self.assertTrue(profile["label"])
        self.assertTrue(profile["summary"])

    def test_settings_only_allow_topjobs_applicant_categories(self):
        settings = SettingsUpdate(category_urls=[
            "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=HNS&jst=OPEN",
        ])
        self.assertEqual(len(settings.category_urls), 1)
        with self.assertRaises(ValueError):
            SettingsUpdate(category_urls=["https://example.com/applicant/jobs"])

    def test_email_and_cover_letter_are_job_specific(self):
        content = generate_application_content(
            job_title="Frontend Developer",
            company="Example Ltd",
            applicant_name="Taylor Example",
            profile_summary="Frontend engineer experienced in React.",
            matched_keywords=["React", "TypeScript"],
            contact={"phone": "555-0100"},
        )
        self.assertIn("Frontend Developer", content.subject)
        self.assertIn("Example Ltd", content.cover_letter)
        self.assertIn("React", content.email)
        self.assertIn("555-0100", content.email)

    @patch("web_backend.app.auth.requests.get")
    @patch("web_backend.app.auth.get_settings")
    def test_authentication_forwards_the_supplied_bearer_token(self, get_settings, get):
        get_settings.return_value = SimpleNamespace(
            supabase_url="https://example.supabase.co",
            supabase_anon_key="public-key",
        )
        get.return_value = SimpleNamespace(
            status_code=200,
            json=lambda: {"id": "user-123", "email": "user@example.com"},
        )
        user = require_user("Bearer example-session-token")
        self.assertEqual(user.id, "user-123")
        self.assertEqual(user.access_token, "example-session-token")
        self.assertEqual(
            get.call_args.kwargs["headers"]["Authorization"],
            "Bearer example-session-token",
        )

    @patch("src.web_engine.time.sleep")
    @patch.object(scraper, "analyze_job_fit")
    @patch.object(scraper, "should_run_ocr", return_value=False)
    @patch.object(scraper, "extract_ad_image_urls", return_value=[])
    @patch.object(scraper, "extract_visible_page_text", return_value="React and TypeScript")
    @patch.object(scraper, "extract_company_email", return_value="jobs@example.com")
    @patch.object(scraper, "fetch_job_page", return_value=BeautifulSoup("", "html.parser"))
    @patch.object(scraper, "load_job_listing_page")
    def test_search_persists_matching_job_through_callback(
        self,
        load_category,
        _fetch,
        _email,
        _text,
        _images,
        _ocr,
        analyze,
        _sleep,
    ):
        load_category.return_value = [{
            "url": "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?rid=123",
            "title": "Frontend Developer",
            "date": date.today(),
        }]
        analyze.return_value = {
            "is_match": True,
            "profile_key": "resume-1",
            "fit_score": 8,
            "fit_feedback": "React skills matched",
            "matched_title_keywords": "Frontend",
            "matched_description_keywords": "React, TypeScript",
        }
        saved = []
        updates = []
        counts = run_topjobs_search(
            {
                "category_urls": ["https://www.topjobs.lk/applicant/jobs"],
                "recent_job_window_days": 2,
                "minimum_fit_score": 4,
                "require_remote": False,
            },
            [{"id": "resume-1", "label": "Frontend", "title_keywords": ["Frontend"], "description_keywords": ["React"]}],
            set(),
            saved.append,
            updates.append,
        )
        self.assertEqual(counts["matched"], 1)
        self.assertEqual(saved[0]["source_job_id"], "123")
        self.assertEqual(saved[0]["company_email"], "jobs@example.com")
        self.assertTrue(updates)

    def test_missing_authentication_is_rejected(self):
        with patch("web_backend.app.auth.get_settings", return_value=SimpleNamespace(
            supabase_url="https://example.supabase.co",
            supabase_anon_key="public-key",
        )):
            with self.assertRaises(HTTPException) as error:
                require_user(None)
        self.assertEqual(error.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
