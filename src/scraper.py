import logging
import os
import re
import time
import warnings
from datetime import datetime, timedelta
from urllib.parse import urljoin

import cv2
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

from src import utils
from src.config import (
    CATEGORY_URLS,
    DEFAULT_RESUME_PATH,
    ENABLE_OCR_FOR_AD_IMAGES,
    EXCLUDED_SENIORITY_KEYWORDS,
    EXCLUDED_TITLE_KEYWORDS,
    JOB_PROFILES,
    LEVEL_KEYWORDS,
    MINIMUM_FIT_SCORE,
    OCR_LANGUAGES,
    RECENT_JOB_WINDOW_DAYS,
    REQUIRE_REMOTE,
    TRACKING_FILE,
)

logger = logging.getLogger("JobAutomation")
warnings.filterwarnings("ignore", message=".*pin_memory.*", category=UserWarning)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}

_OCR_READER = None


def normalize_text(text):
    """Lowercases and normalizes text for keyword matching."""
    lowered = (text or "").lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def find_keyword_hits(text, keywords):
    """Returns every keyword that appears as a normalized phrase match."""
    normalized_text = f" {normalize_text(text)} "
    hits = []

    for keyword in keywords:
        normalized_keyword = normalize_text(keyword)
        if normalized_keyword and f" {normalized_keyword} " in normalized_text:
            hits.append(keyword)

    return hits


def get_ocr_reader():
    """Lazily loads the OCR reader only when it is needed."""
    global _OCR_READER

    if not ENABLE_OCR_FOR_AD_IMAGES:
        return None

    if _OCR_READER is False:
        return None

    if _OCR_READER is None:
        try:
            import easyocr

            logger.info("Initializing OCR reader for image-based TopJobs ads...")
            _OCR_READER = easyocr.Reader(OCR_LANGUAGES, gpu=False, verbose=False)
        except ImportError:
            logger.warning(
                "easyocr is not installed. Falling back to title/page-text-only matching."
            )
            _OCR_READER = False
        except Exception as exc:
            logger.warning(f"OCR initialization failed: {exc}")
            _OCR_READER = False

    return None if _OCR_READER is False else _OCR_READER


def load_job_listing_page(category_url):
    """Downloads a job category page and returns parsed rows, or None if unreachable."""
    logger.info(f"Fetching job links from: {category_url}")
    job_details = []

    try:
        response = requests.get(category_url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        job_rows = soup.find_all("tr", id=re.compile(r"^tr\d+"))
        if not job_rows:
            logger.info(" -> No job rows found in this category.")
            return []

        for row in job_rows:
            onclick_attr = row.get("onclick")
            cells = row.find_all("td")
            if not onclick_attr or len(cells) < 5:
                continue

            date_str = cells[4].get_text(strip=True)
            try:
                post_date = datetime.strptime(date_str, "%a %b %d %Y").date()
            except ValueError:
                continue

            match = re.search(
                r"createAlert\('(\d+)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'",
                onclick_attr,
            )
            if not match:
                continue

            rid, ac, jc, ec = match.groups()
            job_url = (
                "https://www.topjobs.lk/employer/JobAdvertismentServlet"
                f"?rid={rid}&ac={ac}&jc={jc}&ec={ec}"
            )
            title_tag = row.find("h2")
            job_title = title_tag.get_text(" ", strip=True) if title_tag else "No Title"
            job_details.append({"title": job_title, "url": job_url, "date": post_date})

        logger.info(f" -> Found {len(job_details)} jobs in this category.")
        return job_details
    except requests.exceptions.RequestException as exc:
        logger.error(f"Error fetching category page: {exc}")
        return None


def fetch_job_page(job_url):
    """Downloads and parses a single TopJobs ad page."""
    response = requests.get(job_url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extract_company_email(soup):
    """Extracts the company email from the ad page if available."""
    email_input_tag = soup.find("input", id="txtAVECompanyEmail")
    if email_input_tag and email_input_tag.get("value"):
        return email_input_tag["value"].strip()
    return "Not Found"


def extract_visible_page_text(soup):
    """Extracts any plain text that exists on the ad page itself."""
    text_parts = []
    for element_id in ("position", "employer", "remark"):
        tag = soup.find(id=element_id)
        if tag:
            text_parts.append(tag.get_text(" ", strip=True))

    return " ".join(part for part in text_parts if part).strip()


def extract_ad_image_urls(soup, job_url):
    """Finds the main ad images used inside the TopJobs job description block."""
    remark_block = soup.find(id="remark")
    if not remark_block:
        return []

    image_urls = []
    for image_tag in remark_block.find_all("img"):
        src = image_tag.get("src")
        if not src:
            continue
        image_urls.append(urljoin(job_url, src))

    return list(dict.fromkeys(image_urls))


def ocr_ad_images(image_urls):
    """Runs OCR on the image-based job advert, if OCR is available."""
    reader = get_ocr_reader()
    if not reader or not image_urls:
        return ""

    extracted_chunks = []
    for image_url in image_urls:
        try:
            response = requests.get(image_url, headers=HEADERS, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            logger.debug(f" -> Could not download ad image for OCR: {exc}")
            continue

        content_type = response.headers.get("Content-Type", "").lower()
        if content_type and not content_type.startswith("image/"):
            logger.debug(f" -> OCR skipped non-image ad asset: {image_url}")
            continue

        image_buffer = np.frombuffer(response.content, dtype=np.uint8)
        image_array = cv2.imdecode(image_buffer, cv2.IMREAD_COLOR)
        if image_array is None:
            logger.debug(f" -> OCR skipped unreadable image asset: {image_url}")
            continue

        try:
            ocr_lines = reader.readtext(image_array, detail=0, paragraph=True)
            extracted_text = " ".join(line.strip() for line in ocr_lines if line.strip())
            if extracted_text:
                extracted_chunks.append(extracted_text)
        except Exception as exc:
            logger.debug(f" -> OCR failed for {image_url}: {exc}")

    return "\n".join(extracted_chunks).strip()


def analyze_job_fit(job_title, visible_text, ocr_text):
    """Scores a job against your profiles using title and ad content."""
    normalized_title = normalize_text(job_title)

    if REQUIRE_REMOTE and " remote " not in f" {normalized_title} ":
        return {
            "is_match": False,
            "skip_reason": "remote_required",
            "fit_feedback": "Skipped because remote-only mode is enabled.",
        }

    excluded_hits = find_keyword_hits(job_title, EXCLUDED_TITLE_KEYWORDS)
    if excluded_hits:
        return {
            "is_match": False,
            "skip_reason": "excluded_role",
            "fit_feedback": f"Skipped because the title matched excluded roles: {', '.join(excluded_hits)}.",
        }

    seniority_hits = find_keyword_hits(job_title, EXCLUDED_SENIORITY_KEYWORDS)
    if seniority_hits:
        return {
            "is_match": False,
            "skip_reason": "senior_role",
            "fit_feedback": f"Skipped because the title looks too senior: {', '.join(seniority_hits)}.",
        }

    combined_text = " ".join(part for part in [job_title, visible_text, ocr_text] if part).strip()
    level_hits = find_keyword_hits(job_title, LEVEL_KEYWORDS)

    best_match = None
    for profile_key, profile in JOB_PROFILES.items():
        title_hits = find_keyword_hits(job_title, profile["title_keywords"])
        all_profile_hits = find_keyword_hits(combined_text, profile["title_keywords"])
        description_hits = find_keyword_hits(combined_text, profile["description_keywords"])

        extra_content_hits = [hit for hit in all_profile_hits if hit not in title_hits]
        score = (len(title_hits) * 4) + (len(extra_content_hits) * 2) + (len(description_hits) * 2)
        if level_hits:
            score += 1

        feedback_parts = []
        if title_hits:
            feedback_parts.append(f"title: {', '.join(title_hits[:3])}")
        if extra_content_hits:
            feedback_parts.append(f"ad text: {', '.join(extra_content_hits[:3])}")
        if description_hits:
            feedback_parts.append(f"description: {', '.join(description_hits[:4])}")
        if level_hits:
            feedback_parts.append(f"level hint: {', '.join(level_hits[:2])}")

        resume_path = (profile.get("resume_path") or DEFAULT_RESUME_PATH).strip()
        match_result = {
            "profile_key": profile_key,
            "profile_label": profile["label"],
            "profile_summary": profile["summary"],
            "resume_path": resume_path,
            "resume_configured": bool(resume_path),
            "fit_score": score,
            "matched_title_keywords": ", ".join(title_hits),
            "matched_description_keywords": ", ".join(description_hits),
            "fit_feedback": (
                "; ".join(feedback_parts)
                if feedback_parts
                else "No strong profile evidence found."
            ),
        }

        if best_match is None or match_result["fit_score"] > best_match["fit_score"]:
            best_match = match_result

    if not best_match or best_match["fit_score"] < MINIMUM_FIT_SCORE:
        return {
            "is_match": False,
            "skip_reason": "low_fit",
            "fit_feedback": "Skipped because the job did not score as a strong fit.",
        }

    best_match["is_match"] = True
    best_match["skip_reason"] = ""
    return best_match


def should_run_ocr(job_title, visible_text, image_urls):
    """Runs OCR whenever the advert content is image-based."""
    return bool(image_urls) and ENABLE_OCR_FOR_AD_IMAGES


def build_candidate_row(job, analysis, company_email):
    """Creates the CSV row used by the mailer."""
    return {
        "title": job["title"],
        "email": company_email,
        "url": job["url"],
        "date_posted": job["date"].isoformat(),
        "profile_key": analysis["profile_key"],
        "profile_label": analysis["profile_label"],
        "profile_summary": analysis["profile_summary"],
        "resume_path": analysis["resume_path"],
        "fit_score": analysis["fit_score"],
        "fit_feedback": analysis["fit_feedback"],
        "matched_title_keywords": analysis["matched_title_keywords"],
        "matched_description_keywords": analysis["matched_description_keywords"],
    }


def main(progress_callback=None):
    """Main function to run the scraper module."""
    summary = {
        "total_found": 0,
        "matching_criteria": 0,
        "new_leads_found": 0,
        "jobs_reviewed_by_scraper": 0,
        "skipped_low_fit": 0,
        "skipped_senior_role": 0,
        "skipped_excluded_role": 0,
        "skipped_remote_required": 0,
        "errors": 0,
        "category_fetch_successes": 0,
        "source_reachable": False,
    }
    processed_urls = utils.load_processed_jobs(TRACKING_FILE)
    logger.info(f"Loaded {len(processed_urls)} previously applied jobs from '{TRACKING_FILE}'.")
    if progress_callback:
        progress_callback(
            {
                "percent": 8,
                "stage": "scraper",
                "detail": "Loading job categories and previously applied jobs.",
            }
        )

    all_jobs_details = []
    unique_urls = set()
    total_categories = max(len(CATEGORY_URLS), 1)
    for index, url in enumerate(CATEGORY_URLS, start=1):
        if progress_callback:
            progress_callback(
                {
                    "percent": 8 + int((index - 1) / total_categories * 12),
                    "stage": "scraper",
                    "detail": f"Fetching category {index} of {total_categories}.",
                    "current": index,
                    "total": total_categories,
                }
            )
        jobs_from_category = load_job_listing_page(url)
        if jobs_from_category is None:
            time.sleep(1)
            continue

        summary["category_fetch_successes"] += 1
        for job in jobs_from_category:
            if job["url"] not in unique_urls:
                all_jobs_details.append(job)
                unique_urls.add(job["url"])
        time.sleep(1)

    summary["source_reachable"] = summary["category_fetch_successes"] > 0

    today = datetime.now().date()
    start_date = today - timedelta(days=max(RECENT_JOB_WINDOW_DAYS - 1, 0))
    recent_jobs = [
        job
        for job in all_jobs_details
        if start_date <= job["date"] <= today
    ]
    jobs_to_review = [
        job
        for job in recent_jobs
        if job["url"] not in processed_urls
    ]

    summary["total_found"] = len(recent_jobs)
    logger.info("-" * 50)
    logger.info(
        f"Collected {len(all_jobs_details)} visible jobs. "
        f"Reviewing {len(jobs_to_review)} unprocessed jobs from the last {RECENT_JOB_WINDOW_DAYS} days."
    )
    if progress_callback:
        progress_callback(
            {
                "percent": 20,
                "stage": "scraper",
                "detail": (
                    f"Found {summary['total_found']} jobs from the last "
                    f"{RECENT_JOB_WINDOW_DAYS} days. Evaluating new matches."
                ),
            }
        )

    if not jobs_to_review:
        logger.info(
            f"No unprocessed jobs found inside the last {RECENT_JOB_WINDOW_DAYS} days."
        )
        if progress_callback:
            progress_callback(
                {
                    "percent": 65,
                    "stage": "scraper",
                    "detail": f"No new jobs were found in the last {RECENT_JOB_WINDOW_DAYS} days.",
                    "current": 0,
                    "total": 0,
                }
            )
        return summary

    candidate_rows = []
    total_jobs_to_review = len(jobs_to_review)
    summary["jobs_reviewed_by_scraper"] = total_jobs_to_review
    for index, job in enumerate(jobs_to_review, start=1):
        logger.debug(f"Reviewing ({index}/{len(jobs_to_review)}): {job['title']}")
        if progress_callback:
            progress_callback(
                {
                    "percent": 20 + int(index / total_jobs_to_review * 42),
                    "stage": "scraper",
                    "detail": f"Reviewing job {index} of {total_jobs_to_review}: {job['title']}",
                    "current": index,
                    "total": total_jobs_to_review,
                }
            )

        try:
            soup = fetch_job_page(job["url"])
            company_email = extract_company_email(soup)
            visible_text = extract_visible_page_text(soup)
            image_urls = extract_ad_image_urls(soup, job["url"])

            ocr_text = ""
            if should_run_ocr(job["title"], visible_text, image_urls):
                ocr_text = ocr_ad_images(image_urls)

            analysis = analyze_job_fit(job["title"], visible_text, ocr_text)
        except Exception as exc:
            logger.error(f" -> Failed to analyze job page: {exc}")
            summary["errors"] += 1
            continue

        if not analysis.get("is_match"):
            skip_reason = analysis.get("skip_reason", "")
            if skip_reason == "low_fit":
                summary["skipped_low_fit"] += 1
            elif skip_reason == "senior_role":
                summary["skipped_senior_role"] += 1
            elif skip_reason == "excluded_role":
                summary["skipped_excluded_role"] += 1
            elif skip_reason == "remote_required":
                summary["skipped_remote_required"] += 1
            logger.debug(f" -> Skipped. {analysis.get('fit_feedback')}")
            time.sleep(1)
            continue

        summary["matching_criteria"] += 1
        logger.info(
            f" -> Match: {analysis['profile_label']} ({analysis['fit_score']} pts) | "
            f"{analysis['fit_feedback']}"
        )

        if company_email == "Not Found":
            logger.debug(" -> Company email was not found. The job will still be saved for review.")

        if not analysis["resume_configured"]:
            logger.debug(
                f" -> No resume is configured yet for {analysis['profile_label']}. "
                "The job will be saved but skipped by the mailer."
            )

        candidate_rows.append(build_candidate_row(job, analysis, company_email))
        time.sleep(1)

    summary["new_leads_found"] = len(candidate_rows)
    if not candidate_rows:
        logger.info("No jobs met the profile-based fit threshold.")
        return summary

    leads_dir = os.path.join("data", "leads")
    os.makedirs(leads_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = os.path.join(leads_dir, f"topjobs_leads_{timestamp}.csv")

    df = pd.DataFrame(candidate_rows)
    df.to_csv(filename, index=False, encoding="utf-8")
    logger.info(f"\nSaved {len(df)} candidate leads to '{filename}'")
    if progress_callback:
        progress_callback(
            {
                "percent": 65,
                "stage": "scraper",
                "detail": f"Scraping finished. Saved {len(df)} candidate leads.",
                "current": len(df),
                "total": total_jobs_to_review,
            }
        )

    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    main()
