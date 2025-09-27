import os
import time
from src import scraper, mailer, utils

def main():
    """
    Runs the complete job application workflow:
    1. Sets up necessary folders and logging.
    2. Scrapes for new jobs.
    3. Sends emails for the jobs found.
    4. Prints a final summary.
    """
    # Create necessary directories if they don't exist
    os.makedirs("data/leads", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Setup logging to file and console
    logger = utils.setup_logging()
    
    summary = {
        "total_found": 0,
        "matching_criteria": 0,
        "new_leads_found": 0,
        "emails_sent": 0,
        "errors": 0
    }

    logger.info("=================================================")
    logger.info("===          AUTOMATION WORKFLOW START        ===")
    logger.info("=================================================")

    try:
        # --- STEP 1: RUN THE SCRAPER ---
        logger.info("\nSTEP 1: Starting the job scraper...")
        scraper_summary = scraper.main()
        summary.update(scraper_summary)
        logger.info("STEP 1: Job scraper has finished.")
        time.sleep(1)

        # --- STEP 2: RUN THE MAILER ---
        if summary.get("new_leads_found", 0) > 0:
            logger.info("\nSTEP 2: New leads were found. Starting the emailer...")
            mailer_summary = mailer.main()
            summary.update(mailer_summary)
            logger.info("STEP 2: Emailer has finished.")
        else:
            logger.info("\nSTEP 2: No new job leads were found by the scraper. Emailer skipped.")

    except Exception as e:
        logger.error(f"A critical error occurred in the main workflow: {e}")
        summary["errors"] += 1

    # --- FINAL SUMMARY ---
    logger.info("\n=================================================")
    logger.info("===         AUTOMATION WORKFLOW SUMMARY       ===")
    logger.info("=================================================")
    logger.info(f"  > Total Unique Jobs Scanned: {summary.get('total_found', 0)}")
    logger.info(f"  > Jobs Matching Your Profile: {summary.get('matching_criteria', 0)}")
    logger.info(f"  > New/Missed Leads Found: {summary.get('new_leads_found', 0)}")
    logger.info(f"  > Emails Successfully Sent: {summary.get('emails_sent', 0)}")
    logger.info(f"  > Errors Encountered: {summary.get('errors', 0)}")
    logger.info("=================================================")
    logger.info("===         WORKFLOW COMPLETE               ===")
    logger.info("=================================================")

if __name__ == "__main__":
    main()

