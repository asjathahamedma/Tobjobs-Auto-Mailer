import json
import os
import sqlite3
from datetime import datetime

import pandas as pd

from src.config import APP_STATE_DB, FEEDBACK_DIR


class AppDatabase:
    """Stores runs, jobs, applications, and UI activity for the desktop app."""

    def __init__(self, db_path=APP_STATE_DB):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    summary_json TEXT
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    url TEXT PRIMARY KEY,
                    title TEXT,
                    date_posted TEXT,
                    company_email TEXT,
                    profile_label TEXT,
                    fit_score INTEGER,
                    fit_feedback TEXT,
                    resume_path TEXT,
                    status TEXT,
                    note TEXT,
                    last_run_id INTEGER,
                    last_seen_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    job_url TEXT,
                    title TEXT,
                    profile TEXT,
                    recipient_email TEXT,
                    status TEXT,
                    note TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )

    def create_run(self, mode):
        started_at = datetime.now().isoformat(timespec="seconds")
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO runs (mode, status, started_at) VALUES (?, ?, ?)",
                (mode, "running", started_at),
            )
            return cursor.lastrowid, started_at

    def complete_run(self, run_id, summary):
        ended_at = datetime.now().isoformat(timespec="seconds")
        with self._connect() as connection:
            connection.execute(
                "UPDATE runs SET status = ?, ended_at = ?, summary_json = ? WHERE id = ?",
                (
                    summary.get("status", "completed"),
                    ended_at,
                    json.dumps(summary),
                    run_id,
                ),
            )

    def add_event(self, run_id, level, message):
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO events (run_id, level, message, created_at) VALUES (?, ?, ?, ?)",
                (
                    run_id,
                    level,
                    message,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )

    def get_latest_run_summary(self):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT summary_json FROM runs ORDER BY id DESC LIMIT 1"
            ).fetchone()

        if not row or not row["summary_json"]:
            return {}

        try:
            return json.loads(row["summary_json"])
        except json.JSONDecodeError:
            return {}

    def get_recent_events(self, limit=100):
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT created_at, level, message FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    def get_jobs(self, limit=500):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT title, profile_label, fit_score, company_email, status, note, date_posted, url
                FROM jobs
                ORDER BY last_seen_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    def get_applications(self, limit=500):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT title, profile, recipient_email, status, note, created_at, job_url
                FROM applications
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    def sync_run_artifacts(self, run_id, run_started_at):
        leads_file = self._find_latest_file(os.path.join("data", "leads"), "topjobs_leads_")
        feedback_file = self._find_latest_file(FEEDBACK_DIR, "application_feedback_")

        latest_feedback = {}
        if feedback_file and self._is_recent_enough(feedback_file, run_started_at):
            feedback_df = pd.read_csv(feedback_file)
            for _, row in feedback_df.iterrows():
                url = self._safe_text(row.get("url"))
                if not url:
                    continue
                latest_feedback[url] = {
                    "status": self._safe_text(row.get("status")),
                    "note": self._safe_text(row.get("note")),
                    "title": self._safe_text(row.get("title")),
                    "profile": self._safe_text(row.get("profile")),
                    "email": self._safe_text(row.get("email")),
                }
                self._insert_application(
                    run_id=run_id,
                    job_url=url,
                    title=self._safe_text(row.get("title")),
                    profile=self._safe_text(row.get("profile")),
                    recipient_email=self._safe_text(row.get("email")),
                    status=self._safe_text(row.get("status")),
                    note=self._safe_text(row.get("note")),
                )

        if leads_file and self._is_recent_enough(leads_file, run_started_at):
            leads_df = pd.read_csv(leads_file)
            for _, row in leads_df.iterrows():
                url = self._safe_text(row.get("url"))
                if not url:
                    continue

                feedback = latest_feedback.get(url, {})
                self._upsert_job(
                    url=url,
                    title=self._safe_text(row.get("title")),
                    date_posted=self._safe_text(row.get("date_posted")),
                    company_email=self._safe_text(row.get("email")),
                    profile_label=self._safe_text(row.get("profile_label")),
                    fit_score=self._safe_int(row.get("fit_score")),
                    fit_feedback=self._safe_text(row.get("fit_feedback")),
                    resume_path=self._safe_text(row.get("resume_path")),
                    status=feedback.get("status") or "matched",
                    note=feedback.get("note", ""),
                    run_id=run_id,
                )

    def _upsert_job(
        self,
        *,
        url,
        title,
        date_posted,
        company_email,
        profile_label,
        fit_score,
        fit_feedback,
        resume_path,
        status,
        note,
        run_id,
    ):
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    url, title, date_posted, company_email, profile_label, fit_score,
                    fit_feedback, resume_path, status, note, last_run_id, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title = excluded.title,
                    date_posted = excluded.date_posted,
                    company_email = excluded.company_email,
                    profile_label = excluded.profile_label,
                    fit_score = excluded.fit_score,
                    fit_feedback = excluded.fit_feedback,
                    resume_path = excluded.resume_path,
                    status = excluded.status,
                    note = excluded.note,
                    last_run_id = excluded.last_run_id,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    url,
                    title,
                    date_posted,
                    company_email,
                    profile_label,
                    fit_score,
                    fit_feedback,
                    resume_path,
                    status,
                    note,
                    run_id,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )

    def _insert_application(self, *, run_id, job_url, title, profile, recipient_email, status, note):
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO applications (
                    run_id, job_url, title, profile, recipient_email, status, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    job_url,
                    title,
                    profile,
                    recipient_email,
                    status,
                    note,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )

    @staticmethod
    def _find_latest_file(folder, prefix):
        if not os.path.exists(folder):
            return ""

        candidates = [
            os.path.join(folder, name)
            for name in os.listdir(folder)
            if name.startswith(prefix) and name.endswith(".csv")
        ]
        if not candidates:
            return ""
        return max(candidates, key=os.path.getctime)

    @staticmethod
    def _is_recent_enough(path, run_started_at):
        if not path:
            return False
        return os.path.getctime(path) >= datetime.fromisoformat(run_started_at).timestamp() - 5

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
