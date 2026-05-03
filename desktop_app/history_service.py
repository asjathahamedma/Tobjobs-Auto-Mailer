import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import pandas as pd

from src.config import FEEDBACK_DIR


RUN_SUMMARY_FIELDS = {
    "Total Unique Jobs Scanned": "total_found",
    "Jobs Reviewed By Scraper": "jobs_reviewed_by_scraper",
    "Jobs Matching Your Profiles": "matching_criteria",
    "Candidate Leads Saved": "new_leads_found",
    "Jobs Reviewed By Mailer": "jobs_reviewed",
    "Emails Successfully Sent": "emails_sent",
    "Skipped (Already Applied)": "skipped_already_applied",
    "Skipped (Missing Email)": "skipped_missing_email",
    "Skipped (Missing Resume)": "skipped_missing_resume",
    "Skipped (Low Fit)": "skipped_low_fit",
    "Skipped (Senior Role)": "skipped_senior_role",
    "Skipped (Excluded Role)": "skipped_excluded_role",
    "Skipped (Remote Required)": "skipped_remote_required",
    "Errors Encountered": "errors",
}

LOG_LINE_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (?P<level>[A-Z]+) - (?P<message>.*)$"
)
REVIEW_COUNTER_PATTERN = re.compile(r"Reviewing \((?P<current>\d+)/(?P<total>\d+)\):")


class ArtifactHistoryService:
    """Builds a rolling snapshot from logs and CSV artifacts."""

    def __init__(self, project_dir):
        self.project_dir = os.path.abspath(project_dir)
        self.leads_dir = os.path.join(self.project_dir, "data", "leads")
        self.feedback_dir = os.path.join(self.project_dir, FEEDBACK_DIR)
        self.log_path = os.path.join(self.project_dir, "logs", "automation_log.log")

    def collect_snapshot(self, window_days=30):
        window_start = datetime.now() - timedelta(days=window_days)
        runs = self._parse_run_summaries(window_start)
        applications = self._load_feedback_rows(window_start)
        latest_feedback_by_url = self._latest_feedback_by_url(applications)
        jobs = self._load_jobs(window_start, latest_feedback_by_url)
        summary = self._build_summary(runs, jobs, applications, window_days)
        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "window_days": window_days,
            "summary": summary,
            "runs": runs,
            "jobs": jobs,
            "applications": applications,
        }

    def _build_summary(self, runs, jobs, applications, window_days):
        totals = Counter()
        for run in runs:
            for field_name in RUN_SUMMARY_FIELDS.values():
                totals[field_name] += int(run.get(field_name, 0) or 0)

        status_counts = Counter(row.get("status", "") for row in applications)
        profile_counts = Counter(job.get("profile_label", "") for job in jobs if job.get("profile_label"))
        daily_applications = Counter(
            row.get("created_at", "")[:10] for row in applications if row.get("created_at")
        )
        skip_reason_counts = self._build_skip_reason_counts(totals, status_counts)
        today_key = datetime.now().date().isoformat()
        today_summary = self._build_today_summary(runs, applications, today_key)
        profile_performance = self._build_profile_performance(jobs, applications)
        applied_count = status_counts.get("sent", 0)
        rejected_count = len(applications) - applied_count
        searched_total = totals.get("total_found", 0)
        matched_total = totals.get("matching_criteria", 0)
        reviewed_total = totals.get("jobs_reviewed_by_scraper", 0) or searched_total

        return {
            "window_days": window_days,
            "runs_count": len(runs),
            "latest_run_at": runs[0]["started_at"] if runs else "",
            "searched": searched_total,
            "filtered_out": max(searched_total - matched_total, 0),
            "matched": matched_total,
            "reviewed": reviewed_total,
            "applied": applied_count,
            "rejected": rejected_count,
            "unique_jobs": len(jobs),
            "leads_saved": totals.get("new_leads_found", 0),
            "errors": totals.get("errors", 0),
            "missing_email": status_counts.get("skipped_missing_email", 0),
            "already_applied": status_counts.get("skipped_already_applied", 0),
            "missing_resume": status_counts.get("skipped_missing_resume", 0),
            "status_counts": dict(status_counts),
            "profile_counts": dict(profile_counts),
            "daily_applications": dict(sorted(daily_applications.items(), reverse=True)),
            "skip_reason_counts": skip_reason_counts,
            "today_summary": today_summary,
            "profile_performance": profile_performance,
        }

    def _build_today_summary(self, runs, applications, today_key):
        today_totals = Counter()
        for run in runs:
            if not str(run.get("started_at", "")).startswith(today_key):
                continue
            for field_name in RUN_SUMMARY_FIELDS.values():
                today_totals[field_name] += int(run.get(field_name, 0) or 0)

        today_status_counts = Counter(
            row.get("status", "")
            for row in applications
            if str(row.get("created_at", "")).startswith(today_key)
        )
        skip_reason_counts = self._build_skip_reason_counts(today_totals, today_status_counts)
        scanned = today_totals.get("total_found", 0)
        reviewed = today_totals.get("jobs_reviewed_by_scraper", 0) or scanned
        applied = today_status_counts.get("sent", 0) or today_totals.get("emails_sent", 0)
        skipped = max(sum(skip_reason_counts.values()), scanned - applied, 0)
        return {
            "date": today_key,
            "scanned": scanned,
            "reviewed": reviewed,
            "matched": today_totals.get("matching_criteria", 0),
            "applied": applied,
            "skipped": skipped,
            "skip_reason_counts": skip_reason_counts,
        }

    @staticmethod
    def _build_skip_reason_counts(totals, status_counts):
        return {
            "No email": status_counts.get("skipped_missing_email", 0)
            or totals.get("skipped_missing_email", 0),
            "Already applied": status_counts.get("skipped_already_applied", 0)
            or totals.get("skipped_already_applied", 0),
            "Low fit": totals.get("skipped_low_fit", 0),
            "Senior role": totals.get("skipped_senior_role", 0),
            "Excluded role": totals.get("skipped_excluded_role", 0),
            "Remote required": totals.get("skipped_remote_required", 0),
            "Missing resume": (
                status_counts.get("skipped_missing_resume", 0)
                + status_counts.get("skipped_missing_resume_file", 0)
            )
            or totals.get("skipped_missing_resume", 0),
        }

    def _build_profile_performance(self, jobs, applications):
        performance = defaultdict(
            lambda: {
                "profile": "",
                "resume_name": "",
                "matches": 0,
                "applications": 0,
                "skipped": 0,
                "average_fit_score": 0,
                "_fit_score_total": 0,
                "_fit_score_count": 0,
            }
        )

        for job in jobs:
            profile = job.get("profile_label") or "Unassigned"
            row = performance[profile]
            row["profile"] = profile
            row["matches"] += 1
            row["resume_name"] = row["resume_name"] or os.path.basename(job.get("resume_path", ""))
            fit_score = self._safe_int(job.get("fit_score"))
            if fit_score:
                row["_fit_score_total"] += fit_score
                row["_fit_score_count"] += 1

        for application in applications:
            profile = application.get("profile") or "Unassigned"
            row = performance[profile]
            row["profile"] = profile
            if application.get("status") == "sent":
                row["applications"] += 1
            elif application.get("status"):
                row["skipped"] += 1

        rows = []
        for row in performance.values():
            fit_count = row.pop("_fit_score_count", 0)
            fit_total = row.pop("_fit_score_total", 0)
            row["average_fit_score"] = round(fit_total / fit_count, 1) if fit_count else 0
            rows.append(row)

        rows.sort(
            key=lambda item: (
                item.get("applications", 0),
                item.get("matches", 0),
                item.get("average_fit_score", 0),
            ),
            reverse=True,
        )
        return rows

    def _load_jobs(self, window_start, latest_feedback_by_url):
        jobs_by_url = {}
        for timestamp, file_path in self._find_artifact_files(self.leads_dir, "topjobs_leads_", window_start):
            try:
                dataframe = pd.read_csv(file_path)
            except Exception:
                continue

            for _, row in dataframe.iterrows():
                url = self._safe_text(row.get("url"))
                if not url:
                    continue

                existing = jobs_by_url.get(url)
                latest_feedback = latest_feedback_by_url.get(url, {})
                record = {
                    "title": self._safe_text(row.get("title")),
                    "profile_label": self._safe_text(row.get("profile_label")),
                    "fit_score": self._safe_int(row.get("fit_score")),
                    "company_email": self._safe_text(row.get("email")),
                    "resume_path": self._safe_text(row.get("resume_path")),
                    "status": latest_feedback.get("status") or "matched",
                    "note": latest_feedback.get("note", ""),
                    "date_posted": self._safe_text(row.get("date_posted")),
                    "url": url,
                    "last_seen_at": timestamp.isoformat(timespec="seconds"),
                    "matches_seen": 1,
                }

                if existing:
                    record["matches_seen"] = existing["matches_seen"] + 1
                    if existing["last_seen_at"] > record["last_seen_at"]:
                        existing["matches_seen"] = record["matches_seen"]
                        continue

                jobs_by_url[url] = record

        jobs = list(jobs_by_url.values())
        jobs.sort(key=lambda item: item.get("last_seen_at", ""), reverse=True)
        return jobs

    def _load_feedback_rows(self, window_start):
        rows = []
        for timestamp, file_path in self._find_artifact_files(
            self.feedback_dir, "application_feedback_", window_start
        ):
            try:
                dataframe = pd.read_csv(file_path)
            except Exception:
                continue

            for _, row in dataframe.iterrows():
                rows.append(
                    {
                        "created_at": timestamp.isoformat(timespec="seconds"),
                        "title": self._safe_text(row.get("title")),
                        "profile": self._safe_text(row.get("profile")),
                        "recipient_email": self._safe_text(row.get("email")),
                        "status": self._safe_text(row.get("status")),
                        "note": self._safe_text(row.get("note")),
                        "job_url": self._safe_text(row.get("url")),
                    }
                )

        rows.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return rows

    def _latest_feedback_by_url(self, applications):
        latest = {}
        for row in applications:
            url = row.get("job_url")
            if not url or url in latest:
                continue
            latest[url] = {
                "status": row.get("status", ""),
                "note": row.get("note", ""),
                "created_at": row.get("created_at", ""),
            }
        return latest

    def _parse_run_summaries(self, window_start):
        if not os.path.exists(self.log_path):
            return []

        runs = []
        current_run = None
        pending_runtime_metrics = Counter()

        with open(self.log_path, "r", encoding="utf-8", errors="ignore") as log_file:
            for raw_line in log_file:
                stripped_line = raw_line.rstrip("\n")
                if "STEP 1: Starting the job scraper" in stripped_line:
                    pending_runtime_metrics = Counter()

                match = LOG_LINE_PATTERN.match(stripped_line)
                if not match:
                    continue

                timestamp = datetime.strptime(match.group("timestamp"), "%Y-%m-%d %H:%M:%S")
                message = match.group("message")

                if timestamp >= window_start:
                    self._collect_runtime_metric(message, pending_runtime_metrics)

                if "===         AUTOMATION WORKFLOW SUMMARY" in message:
                    current_run = {
                        "started_at": timestamp.isoformat(timespec="seconds"),
                        "status": "completed",
                        **pending_runtime_metrics,
                    }
                    pending_runtime_metrics = Counter()
                    continue

                if current_run is None or timestamp < window_start:
                    continue

                for label, field_name in RUN_SUMMARY_FIELDS.items():
                    prefix = f"  > {label}:"
                    if message.startswith(prefix):
                        parsed_value = self._safe_int(message.split(":", 1)[1].strip())
                        current_run[field_name] = max(current_run.get(field_name, 0), parsed_value)
                        break

                if "===         WORKFLOW COMPLETE" in message:
                    for field_name in RUN_SUMMARY_FIELDS.values():
                        current_run.setdefault(field_name, 0)
                    runs.append(current_run)
                    current_run = None

        runs.sort(key=lambda item: item.get("started_at", ""), reverse=True)
        return runs

    @staticmethod
    def _collect_runtime_metric(message, metrics):
        review_match = REVIEW_COUNTER_PATTERN.search(message)
        if review_match:
            metrics["jobs_reviewed_by_scraper"] = max(
                metrics.get("jobs_reviewed_by_scraper", 0),
                ArtifactHistoryService._safe_int(review_match.group("current")),
            )

        if "Skipped because the job did not score as a strong fit" in message:
            metrics["skipped_low_fit"] += 1
        elif "Skipped because the title looks too senior" in message:
            metrics["skipped_senior_role"] += 1
        elif "Skipped because the title matched excluded roles" in message:
            metrics["skipped_excluded_role"] += 1
        elif "Skipped because remote-only mode is enabled" in message:
            metrics["skipped_remote_required"] += 1

    @staticmethod
    def _find_artifact_files(folder, prefix, window_start):
        if not os.path.exists(folder):
            return []

        files = []
        for name in os.listdir(folder):
            if not name.startswith(prefix) or not name.endswith(".csv"):
                continue
            timestamp = ArtifactHistoryService._parse_timestamp_from_name(name, prefix)
            if not timestamp or timestamp < window_start:
                continue
            files.append((timestamp, os.path.join(folder, name)))

        files.sort(key=lambda item: item[0], reverse=True)
        return files

    @staticmethod
    def _parse_timestamp_from_name(filename, prefix):
        try:
            timestamp_text = filename[len(prefix) : -4]
            return datetime.strptime(timestamp_text, "%Y-%m-%d_%H%M%S")
        except ValueError:
            return None

    @staticmethod
    def _safe_text(value):
        if pd.isna(value):
            return ""
        return str(value).strip()

    @staticmethod
    def _safe_int(value):
        try:
            if pd.isna(value):
                return 0
            return int(float(value))
        except (TypeError, ValueError):
            return 0
