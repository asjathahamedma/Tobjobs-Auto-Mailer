import unittest
from collections import Counter

from desktop_app.history_service import ArtifactHistoryService


class HistoryAnalyticsTests(unittest.TestCase):
    def test_calculates_match_rate_and_reports_reviewed_jobs_without_fallback(self):
        service = ArtifactHistoryService(".")
        run = {
            "started_at": "2000-01-01T00:00:00",
            "total_found": 10,
            "matching_criteria": 4,
            "jobs_reviewed_by_scraper": 3,
            "emails_sent": 0,
        }

        summary = service._build_summary([run], [], [], 30)

        self.assertEqual(summary["match_rate"], 40)
        self.assertEqual(summary["reviewed"], 3)

    def test_today_skipped_total_counts_recorded_reasons_not_all_unapplied_jobs(self):
        service = ArtifactHistoryService(".")
        today = service._build_today_summary([], [], "2026-11-01")

        self.assertEqual(today["skipped"], 0)


if __name__ == "__main__":
    unittest.main()
