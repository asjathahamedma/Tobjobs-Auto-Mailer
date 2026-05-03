import argparse
import importlib
import os
import time

from src import config as app_config
from src import mailer, scraper, utils
from src.config import FEEDBACK_DIR, STARTUP_STATE_FILE


def parse_args():
    parser = argparse.ArgumentParser(description="Run the TopJobs automation workflow.")
    parser.add_argument(
        "--startup",
        action="store_true",
        help="Run in startup mode and skip if the automation already ran today.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable console logging and only write logs to file.",
    )
    return parser.parse_args()


def reload_runtime_modules():
    """Reloads config-sensitive modules so the latest app settings are used every run."""
    importlib.reload(app_config)
    importlib.reload(scraper)
    importlib.reload(mailer)


def emit_progress(progress_callback, percent, stage, detail, current=None, total=None):
    """Sends a normalized progress update to any attached UI callback."""
    if not progress_callback:
        return

    payload = {
        "percent": max(0, min(int(percent), 100)),
        "stage": stage,
        "detail": detail,
    }
    if current is not None:
        payload["current"] = current
    if total is not None:
        payload["total"] = total
    progress_callback(payload)


def run_workflow(startup=False, use_console=True, extra_handlers=None, progress_callback=None):
    """
    Runs the complete job application workflow and returns a structured summary.
    """
    reload_runtime_modules()

    os.makedirs("data/leads", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs(FEEDBACK_DIR, exist_ok=True)

    logger = utils.setup_logging(use_console=use_console, extra_handlers=extra_handlers)

    if startup and utils.has_startup_run_today(STARTUP_STATE_FILE):
        logger.info("Startup mode detected: the automation already ran today, so this run is skipped.")
        return {
            "status": "skipped_startup_already_ran",
            "total_found": 0,
            "matching_criteria": 0,
            "new_leads_found": 0,
            "jobs_reviewed_by_scraper": 0,
            "jobs_reviewed": 0,
            "emails_sent": 0,
            "skipped_already_applied": 0,
            "skipped_missing_email": 0,
            "skipped_missing_resume": 0,
            "skipped_low_fit": 0,
            "skipped_senior_role": 0,
            "skipped_excluded_role": 0,
            "skipped_remote_required": 0,
            "errors": 0,
            "source_reachable": False,
        }

    summary = {
        "status": "completed",
        "total_found": 0,
        "matching_criteria": 0,
        "new_leads_found": 0,
        "jobs_reviewed_by_scraper": 0,
        "jobs_reviewed": 0,
        "emails_sent": 0,
        "skipped_already_applied": 0,
        "skipped_missing_email": 0,
        "skipped_missing_resume": 0,
        "skipped_low_fit": 0,
        "skipped_senior_role": 0,
        "skipped_excluded_role": 0,
        "skipped_remote_required": 0,
        "errors": 0,
        "source_reachable": False,
    }

    logger.info("=================================================")
    logger.info("===          AUTOMATION WORKFLOW START        ===")
    logger.info("=================================================")
    emit_progress(
        progress_callback,
        2,
        "starting",
        "Preparing folders, configuration, and runtime services.",
    )

    try:
        logger.info("\nSTEP 1: Starting the job scraper...")
        emit_progress(progress_callback, 5, "scraper", "Starting TopJobs scraping.")
        scraper_summary = scraper.main(progress_callback=progress_callback)
        summary.update(scraper_summary)
        logger.info("STEP 1: Job scraper has finished.")
        emit_progress(progress_callback, 68, "scraper", "Scraping complete. Preparing application stage.")
        time.sleep(1)

        scan_only_mode = app_config.APP_SETTINGS.get("scan_only_mode", False)
        if scan_only_mode:
            logger.info("\nSTEP 2: Scan-only mode is enabled. Emailer skipped.")
            emit_progress(
                progress_callback,
                100,
                "complete",
                "Scan-only mode finished. No application emails were sent.",
            )
        elif summary.get("new_leads_found", 0) > 0:
            logger.info("\nSTEP 2: Candidate leads were found. Starting the emailer...")
            emit_progress(
                progress_callback,
                72,
                "mailer",
                "Matched jobs found. Starting application emails.",
            )
            mailer_summary = mailer.main(progress_callback=progress_callback)
            summary.update(mailer_summary)
            logger.info("STEP 2: Emailer has finished.")
            emit_progress(progress_callback, 100, "complete", "Workflow finished successfully.")
        else:
            logger.info("\nSTEP 2: No candidate leads were found by the scraper. Emailer skipped.")
            emit_progress(
                progress_callback,
                100,
                "complete",
                "No candidate leads were found. Workflow finished.",
            )
    except Exception as exc:
        logger.error(f"A critical error occurred in the main workflow: {exc}")
        summary["errors"] += 1
        summary["status"] = "failed"
        emit_progress(
            progress_callback,
            100,
            "failed",
            f"Workflow stopped because of an error: {exc}",
        )
    finally:
        if startup:
            if summary.get("source_reachable"):
                utils.record_startup_run(STARTUP_STATE_FILE, status="completed", summary=summary)
            else:
                logger.info(
                    "Startup mode: TopJobs was not reachable, so today's startup run was not recorded."
                )

    logger.info("\n=================================================")
    logger.info("===         AUTOMATION WORKFLOW SUMMARY       ===")
    logger.info("=================================================")
    logger.info(f"  > Total Unique Jobs Scanned: {summary.get('total_found', 0)}")
    logger.info(f"  > Jobs Reviewed By Scraper: {summary.get('jobs_reviewed_by_scraper', 0)}")
    logger.info(f"  > Jobs Matching Your Profiles: {summary.get('matching_criteria', 0)}")
    logger.info(f"  > Candidate Leads Saved: {summary.get('new_leads_found', 0)}")
    logger.info(f"  > Jobs Reviewed By Mailer: {summary.get('jobs_reviewed', 0)}")
    logger.info(f"  > Emails Successfully Sent: {summary.get('emails_sent', 0)}")
    logger.info(f"  > Skipped (Already Applied): {summary.get('skipped_already_applied', 0)}")
    logger.info(f"  > Skipped (Missing Email): {summary.get('skipped_missing_email', 0)}")
    logger.info(f"  > Skipped (Missing Resume): {summary.get('skipped_missing_resume', 0)}")
    logger.info(f"  > Skipped (Low Fit): {summary.get('skipped_low_fit', 0)}")
    logger.info(f"  > Skipped (Senior Role): {summary.get('skipped_senior_role', 0)}")
    logger.info(f"  > Skipped (Excluded Role): {summary.get('skipped_excluded_role', 0)}")
    logger.info(f"  > Skipped (Remote Required): {summary.get('skipped_remote_required', 0)}")
    logger.info(f"  > Errors Encountered: {summary.get('errors', 0)}")
    logger.info("=================================================")
    logger.info("===         WORKFLOW COMPLETE               ===")
    logger.info("=================================================")

    return summary


def main():
    args = parse_args()
    run_workflow(startup=args.startup, use_console=not args.quiet)


if __name__ == "__main__":
    main()
