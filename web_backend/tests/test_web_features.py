import unittest
from datetime import date
from email import policy
from email.parser import BytesParser
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup
from fastapi import HTTPException

from src import scraper
from src.resume_profiles import build_resume_profile
from src.web_engine import run_topjobs_search
from web_backend.app.auth import AuthenticatedUser, require_user
from web_backend.app.content import generate_application_content
from web_backend.app.schemas import ApprovedSend, SettingsUpdate
from web_backend.app import main as api_main


class WebFeatureTests(unittest.TestCase):
    def test_resume_profile_extracts_skill_keywords(self):
        profile = build_resume_profile(
            "Frontend developer with React, TypeScript, responsive design and Redux experience.",
            "frontend_resume.pdf",
        )
        self.assertIn("react", [keyword.lower() for keyword in profile["title_keywords"] + profile["description_keywords"]])
        self.assertTrue(profile["label"])
        self.assertTrue(profile["summary"])

    def test_resume_profile_extracts_a_broader_ranked_keyword_set(self):
        profile = build_resume_profile(
            "Data engineer: Python SQL PostgreSQL AWS Docker Kubernetes Airflow Spark "
            "Snowflake BigQuery ETL data modeling data warehouse Git Linux Terraform "
            "Tableau pandas numpy Excel Power BI data analysis machine learning deep learning "
            "TensorFlow PyTorch scikit learn data visualization statistics computer vision NLP "
            "Python Python",
            "data_resume.pdf",
        )
        keywords = profile["title_keywords"] + profile["description_keywords"]
        self.assertGreater(len(keywords), 22)
        self.assertIn("data engineer", profile["title_keywords"])
        self.assertIn("python", profile["description_keywords"])
        self.assertLess(profile["description_keywords"].index("python"), profile["description_keywords"].index("sql"))
        self.assertLessEqual(len(profile["title_keywords"]), 30)
        self.assertLessEqual(len(profile["description_keywords"]), 60)

    def test_resume_preview_is_private_and_scoped_to_the_current_user(self):
        class FakeDatabase:
            def request(self, method, table, *, params=None, **kwargs):
                self.params = params
                return [{"storage_path": "user-1/resume.pdf", "file_name": "resume.pdf"}]

            def storage_request(self, method, path):
                self.storage_request_args = (method, path)
                return SimpleNamespace(content=b"%PDF-1.4 private resume")

        database = FakeDatabase()
        response = api_main.preview_resume(
            "resume-1",
            AuthenticatedUser("user-1", "user@example.com", "access-token"),
            database,
        )
        self.assertEqual(database.params["user_id"], "eq.user-1")
        self.assertEqual(database.storage_request_args[0], "GET")
        self.assertEqual(response.body, b"%PDF-1.4 private resume")
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertTrue(response.headers["content-disposition"].startswith("inline;"))

    def test_resume_keyword_reextraction_updates_only_keyword_fields(self):
        existing_profile = {
            "id": "resume-1",
            "file_name": "resume.pdf",
            "label": "My edited profile",
            "summary": "My edited summary",
            "title_keywords": ["Data Engineer"],
            "description_keywords": ["Python"],
        }

        class FakeDatabase:
            def request(self, method, table, *, params=None, body=None, **kwargs):
                if method == "GET":
                    self.params = params
                    return [{"storage_path": "user-1/resume.pdf", "file_name": "resume.pdf"}]
                self.body = body
                return [existing_profile]

            def storage_request(self, method, path):
                return SimpleNamespace(content=b"%PDF-1.4 private resume")

        database = FakeDatabase()
        with patch.object(api_main, "_extract_resume_text", return_value="Data engineer with Python and AWS"):
            updated = api_main.extract_resume_keywords(
                "resume-1",
                AuthenticatedUser("user-1", "user@example.com", "access-token"),
                database,
            )
        expected = build_resume_profile("Data engineer with Python and AWS", "resume.pdf")
        self.assertEqual(database.params["user_id"], "eq.user-1")
        self.assertEqual(database.body["title_keywords"], expected["title_keywords"])
        self.assertEqual(database.body["description_keywords"], expected["description_keywords"])
        self.assertGreater(database.body["extracted_text_length"], 0)
        self.assertNotIn("label", database.body)
        self.assertNotIn("summary", database.body)
        self.assertEqual(updated["label"], "My edited profile")
        self.assertEqual(updated["summary"], "My edited summary")

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

    def test_approved_email_sends_resume_attachment_and_updates_status(self):
        application = {
            "id": "application-1",
            "job_id": "job-1",
            "status": "awaiting_review",
            "generated_subject": "Application",
            "generated_email": "Please review my application.",
            "job_listings": {
                "title": "Developer",
                "company_email": "jobs@example.com",
                "source_url": "https://example.com/job",
            },
        }

        class FakeDatabase:
            def request(self, method, table, *, params=None, **kwargs):
                if method == "GET" and table == "applications":
                    return [application]
                if method == "GET" and table == "job_matches":
                    return [{"resumes": {"storage_path": "user-1/resume.pdf", "file_name": "resume.pdf"}}]
                if method == "GET" and table == "mailer_credentials":
                    return [{"sender_email": "applicant@example.com", "encrypted_app_password": "encrypted"}]
                if method == "GET" and table == "user_settings":
                    return []
                if method == "PATCH" and table == "applications":
                    if params["status"] == "eq.sending":
                        return [{"id": "application-1", "status": "applied"}]
                    return [{"id": "application-1"}]
                raise AssertionError(f"Unexpected database request: {method} {table}")

            def storage_request(self, method, path):
                if method != "GET" or "private-resumes/user-1/resume.pdf" not in path:
                    raise AssertionError(f"Unexpected storage request: {method} {path}")
                return SimpleNamespace(content=b"%PDF-1.4 test resume")

        database = FakeDatabase()
        smtp = MagicMock()
        smtp.__enter__.return_value = smtp
        smtp.sendmail.return_value = {}

        with (
            patch.object(api_main.smtplib, "SMTP_SSL", return_value=smtp) as smtp_ssl,
            patch.object(
                api_main,
                "_require_encryption",
                return_value=SimpleNamespace(decrypt=lambda _: b"gmail-app-password"),
            ),
        ):
            result = api_main.send_approved_email(
                "application-1",
                ApprovedSend(approved=True),
                AuthenticatedUser("user-1", "applicant@example.com", "access-token"),
                database,
                SimpleNamespace(state=SimpleNamespace(request_id="request-test")),
            )

        self.assertEqual(result["status"], "applied")
        smtp_ssl.assert_called_once()
        smtp.login.assert_called_once_with("applicant@example.com", "gmail-app-password")
        smtp.sendmail.assert_called_once()
        self.assertEqual(smtp.sendmail.call_args.args[0], "applicant@example.com")
        self.assertEqual(smtp.sendmail.call_args.args[1], "jobs@example.com")
        parsed_message = BytesParser(policy=policy.default).parsebytes(
            smtp.sendmail.call_args.args[2].encode()
        )
        self.assertEqual(parsed_message["Subject"], "Application")
        self.assertEqual(parsed_message.get_body(preferencelist=("plain",)).get_content().strip(), "Please review my application.")
        self.assertEqual(parsed_message.get_payload()[1].get_content_type(), "application/pdf")
        self.assertEqual(parsed_message.get_payload()[1].get_filename(), "resume.pdf")

    def test_sending_application_cannot_be_submitted_twice(self):
        class FakeDatabase:
            def request(self, method, table, *, params=None, **kwargs):
                if method == "GET" and table == "applications":
                    return [{
                        "id": "application-1",
                        "status": "sending",
                    }]
                raise AssertionError(f"Unexpected database request: {method} {table}")

        with patch.object(api_main.smtplib, "SMTP_SSL") as smtp_ssl:
            with self.assertRaises(HTTPException) as error:
                api_main.send_approved_email(
                    "application-1",
                    ApprovedSend(approved=True),
                    AuthenticatedUser("user-1", "applicant@example.com", "access-token"),
                    FakeDatabase(),
                    SimpleNamespace(state=SimpleNamespace(request_id="request-test")),
                )
        self.assertEqual(error.exception.status_code, 409)
        self.assertIn("Check Gmail Sent", error.exception.detail)
        smtp_ssl.assert_not_called()

    def test_gmail_authentication_failure_has_clear_error_and_marks_failed(self):
        application = {
            "id": "application-1",
            "job_id": "job-1",
            "status": "awaiting_review",
            "generated_subject": "Application",
            "generated_email": "Please review my application.",
            "job_listings": {"company_email": "jobs@example.com"},
        }

        class FakeDatabase:
            def __init__(self):
                self.status_updates = []

            def request(self, method, table, *, params=None, body=None, **kwargs):
                if method == "GET" and table == "applications":
                    return [application]
                if method == "GET" and table == "job_matches":
                    return [{"resumes": {"storage_path": "user-1/resume.pdf", "file_name": "resume.pdf"}}]
                if method == "GET" and table == "mailer_credentials":
                    return [{"sender_email": "applicant@example.com", "encrypted_app_password": "encrypted"}]
                if method == "GET" and table == "user_settings":
                    return []
                if method == "PATCH" and table == "applications":
                    self.status_updates.append(body)
                    return [{"id": "application-1"}]
                raise AssertionError(f"Unexpected database request: {method} {table}")

            def storage_request(self, method, path):
                return SimpleNamespace(content=b"%PDF-1.4 test resume")

        database = FakeDatabase()
        smtp = MagicMock()
        smtp.__enter__.return_value = smtp
        smtp.login.side_effect = api_main.smtplib.SMTPAuthenticationError(535, b"Authentication failed")
        with (
            patch.object(api_main.smtplib, "SMTP_SSL", return_value=smtp),
            patch.object(api_main, "_require_encryption", return_value=SimpleNamespace(
                decrypt=lambda _: b"gmail-app-password",
            )),
        ):
            with self.assertLogs("topjobs_web_api", level="ERROR"):
                with self.assertRaises(HTTPException) as error:
                    api_main.send_approved_email(
                        "application-1",
                        ApprovedSend(approved=True),
                        AuthenticatedUser("user-1", "applicant@example.com", "access-token"),
                        database,
                        SimpleNamespace(state=SimpleNamespace(request_id="request-test")),
                    )

        self.assertEqual(error.exception.status_code, 502)
        self.assertIn("Gmail rejected the sign-in", error.exception.detail)
        self.assertEqual(database.status_updates[-1]["status"], "failed")
        smtp.sendmail.assert_not_called()


if __name__ == "__main__":
    unittest.main()
