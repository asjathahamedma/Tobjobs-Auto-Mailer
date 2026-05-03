import glob
import logging
import os
import random
import smtplib
import ssl
import time
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
from dotenv import load_dotenv

from src import utils
from src.config import CONTACT_INFO, ENV_FILE, FEEDBACK_DIR, MAILER_AUTH, TRACKING_FILE, YOUR_NAME, resolve_existing_path

logger = logging.getLogger("JobAutomation")


def safe_text(value):
    """Converts CSV values into a clean string."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def find_latest_leads_csv():
    """Finds the most recently created leads CSV file."""
    list_of_files = glob.glob(os.path.join("data", "leads", "topjobs_leads_*.csv"))
    if not list_of_files:
        return None
    return max(list_of_files, key=os.path.getctime)


def build_keyword_snippet(row):
    """Turns matched keywords into a short sentence fragment."""
    raw_keywords = [
        keyword.strip()
        for keyword in (
            safe_text(row.get("matched_title_keywords")).split(",")
            + safe_text(row.get("matched_description_keywords")).split(",")
        )
        if keyword.strip()
    ]

    unique_keywords = list(dict.fromkeys(raw_keywords))
    if not unique_keywords:
        return "the responsibilities highlighted in the job description"

    if len(unique_keywords) == 1:
        return unique_keywords[0]

    return ", ".join(unique_keywords[:3])


def generate_email_content(row):
    """Generates a professional email body and subject based on the matched profile."""
    job_title = safe_text(row.get("title"))
    profile_summary = safe_text(row.get("profile_summary"))
    keyword_snippet = build_keyword_snippet(row)

    openings = [
        "I am writing to express my interest in the",
        "I was excited to come across the",
        "I am writing to apply for the",
    ]
    closings = [
        "I would welcome the chance to discuss how I can contribute to your team.",
        "I would be glad to discuss how my background can support this opportunity.",
        "I would appreciate the opportunity to speak further about how I can add value to your team.",
    ]

    subject = f"Application for {job_title} - {YOUR_NAME}"
    body = f"""
Dear Hiring Manager,

{random.choice(openings)} {job_title} role advertised on TopJobs.lk.

{profile_summary} This opportunity stands out to me because it aligns closely with my hands-on work in {keyword_snippet}.

My resume is attached for your review, and I would be happy to provide any additional information if needed. {random.choice(closings)}

Thank you for your time and consideration.

Sincerely,

{YOUR_NAME}
{CONTACT_INFO['phone']} | {CONTACT_INFO['email']}
Portfolio: {CONTACT_INFO['portfolio']}
LinkedIn: {CONTACT_INFO['linkedin']}
GitHub: {CONTACT_INFO['github']}
"""
    return subject, body.strip()


def send_email(smtp_server, port, sender_email, password, receiver_email, subject, body, attachment_path):
    """Connects to the SMTP server and sends a single email with an attachment."""
    resolved_attachment_path = resolve_existing_path(attachment_path)
    if not os.path.exists(resolved_attachment_path):
        return False, f"Attachment file was not found: {resolved_attachment_path}"

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            message = MIMEMultipart()
            message["From"] = f"{YOUR_NAME} <{sender_email}>"
            message["To"] = receiver_email
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))

            with open(resolved_attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())

            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(attachment_path)}",
            )
            message.attach(part)
            server.sendmail(sender_email, receiver_email, message.as_string())
            time.sleep(5)
            return True, "Email sent successfully."
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed. Check EMAIL_ADDRESS and Gmail App Password."
    except Exception as exc:
        return False, f"Unexpected send error: {exc}"


def save_feedback_report(rows):
    """Writes a timestamped feedback report for the run."""
    if not rows:
        return ""

    os.makedirs(FEEDBACK_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    report_path = os.path.join(FEEDBACK_DIR, f"application_feedback_{timestamp}.csv")
    pd.DataFrame(rows).to_csv(report_path, index=False, encoding="utf-8")
    return report_path


def main(progress_callback=None):
    """Reads the latest leads file and sends matching emails."""
    summary = {
        "emails_sent": 0,
        "errors": 0,
        "jobs_reviewed": 0,
        "skipped_already_applied": 0,
        "skipped_missing_email": 0,
        "skipped_missing_resume": 0,
    }

    load_dotenv(dotenv_path=ENV_FILE)
    sender_email = MAILER_AUTH.get("sender_email") or os.getenv("EMAIL_ADDRESS")
    password = MAILER_AUTH.get("app_password") or os.getenv("EMAIL_PASSWORD")
    if progress_callback:
        progress_callback(
            {
                "percent": 74,
                "stage": "mailer",
                "detail": "Checking email credentials and loading the latest leads file.",
            }
        )

    if not sender_email or not password:
        logger.critical("CRITICAL: EMAIL_ADDRESS or EMAIL_PASSWORD not found in .env file.")
        summary["errors"] += 1
        return summary

    leads_csv_file = find_latest_leads_csv()
    if not leads_csv_file:
        logger.warning("No new 'topjobs_leads_*.csv' file found to process.")
        return summary

    logger.info(f"Found leads file to process: {leads_csv_file}")

    try:
        df = pd.read_csv(leads_csv_file)
    except Exception as exc:
        logger.error(f"Could not read leads CSV '{leads_csv_file}': {exc}")
        summary["errors"] += 1
        return summary

    if df.empty:
        logger.info("The leads file is empty. Nothing to process.")
        return summary

    smtp_server = "smtp.gmail.com"
    port = 465
    processed_urls = utils.load_processed_jobs(TRACKING_FILE)
    newly_processed_urls = set()
    feedback_rows = []
    total_rows = len(df.index)

    for index, (_, row) in enumerate(df.iterrows(), start=1):
        title = safe_text(row.get("title"))
        receiver_email = safe_text(row.get("email"))
        resume_path = safe_text(row.get("resume_path"))
        profile_label = safe_text(row.get("profile_label"))
        fit_feedback = safe_text(row.get("fit_feedback"))
        job_url = safe_text(row.get("url"))
        if progress_callback:
            progress_callback(
                {
                    "percent": 74 + int(index / max(total_rows, 1) * 24),
                    "stage": "mailer",
                    "detail": f"Processing application {index} of {total_rows}: {title}",
                    "current": index,
                    "total": total_rows,
                }
            )

        if job_url and job_url in processed_urls:
            summary["skipped_already_applied"] += 1
            feedback_rows.append(
                {
                    "title": title,
                    "profile": profile_label,
                    "fit_score": safe_text(row.get("fit_score")),
                    "fit_feedback": fit_feedback,
                    "status": "skipped_already_applied",
                    "note": "Skipped because this job URL already exists in processed_jobs.csv.",
                    "email": receiver_email,
                    "resume_path": resume_path,
                    "url": job_url,
                }
            )
            continue

        summary["jobs_reviewed"] += 1
        logger.info(f"\nProcessing application for: '{title}'")
        logger.debug(f" -> Fit review: {profile_label} | {fit_feedback}")

        status = ""
        note = ""

        if "@" not in receiver_email:
            status = "skipped_missing_email"
            note = "No company email address was available on the TopJobs ad."
            summary["skipped_missing_email"] += 1
            logger.info(f" -> Skipped. {note}")
        elif not resume_path:
            status = "skipped_missing_resume"
            note = f"No resume is configured yet for the {profile_label} profile."
            summary["skipped_missing_resume"] += 1
            logger.info(f" -> Skipped. {note}")
        elif not os.path.exists(resume_path):
            status = "skipped_missing_resume_file"
            note = f"The configured resume file does not exist: {resume_path}"
            summary["skipped_missing_resume"] += 1
            logger.info(f" -> Skipped. {note}")
        else:
            subject, body = generate_email_content(row)
            sent, send_note = send_email(
                smtp_server,
                port,
                sender_email,
                password,
                receiver_email,
                subject,
                body,
                resume_path,
            )

            if sent:
                status = "sent"
                note = send_note
                summary["emails_sent"] += 1
                if job_url:
                    newly_processed_urls.add(job_url)
                logger.info(f" -> SUCCESS: Email sent to {receiver_email}")
            else:
                status = "send_failed"
                note = send_note
                summary["errors"] += 1
                logger.error(f" -> ERROR: {send_note}")

        feedback_rows.append(
            {
                "title": title,
                "profile": profile_label,
                "fit_score": safe_text(row.get("fit_score")),
                "fit_feedback": fit_feedback,
                "status": status,
                "note": note,
                "email": receiver_email,
                "resume_path": resume_path,
                "url": job_url,
            }
        )

    if newly_processed_urls:
        updated_urls = processed_urls.union(newly_processed_urls)
        utils.save_processed_jobs(TRACKING_FILE, updated_urls)
        logger.info(
            f"\nUpdated '{TRACKING_FILE}' with {len(newly_processed_urls)} newly applied jobs."
        )

    report_path = save_feedback_report(feedback_rows)
    if report_path:
        summary["feedback_report"] = report_path
        logger.info(f"Saved application feedback report to '{report_path}'")
    if progress_callback:
        progress_callback(
            {
                "percent": 99,
                "stage": "mailer",
                "detail": "Mailer finished. Saving feedback report and processed jobs.",
                "current": total_rows,
                "total": total_rows,
            }
        )

    return summary
