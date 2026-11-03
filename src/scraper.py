import logging
import re
import time
import warnings
from datetime import datetime
from urllib.parse import urljoin

import cv2
import numpy as np
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config import (
    DEFAULT_RESUME_PATH,
    ENABLE_OCR_FOR_AD_IMAGES,
    EXCLUDED_SENIORITY_KEYWORDS,
    EXCLUDED_TITLE_KEYWORDS,
    JOB_PROFILES,
    LEVEL_KEYWORDS,
    MINIMUM_FIT_SCORE,
    OCR_LANGUAGES,
    REQUIRE_REMOTE,
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

_HTTP_SESSION = requests.Session()
_HTTP_SESSION.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=3,
            connect=3,
            read=2,
            status=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )
    ),
)

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


def get_ocr_reader(enabled=None):
    """Lazily loads the OCR reader only when it is needed."""
    global _OCR_READER

    if not (ENABLE_OCR_FOR_AD_IMAGES if enabled is None else enabled):
        return None

    if _OCR_READER is False:
        return None

    if _OCR_READER is None:
        try:
            import easyocr

            logger.info("Initializing OCR reader for image-based TopJobs ads...")
            _OCR_READER = easyocr.Reader(OCR_LANGUAGES, gpu=False, verbose=False)
        except ImportError as exc:
            _OCR_READER = False
            raise RuntimeError(
                "Image OCR is enabled, but EasyOCR is not installed on this API service."
            ) from exc
        except Exception as exc:
            _OCR_READER = False
            raise RuntimeError("Image OCR could not be initialized on this API service.") from exc

    return None if _OCR_READER is False else _OCR_READER


def load_job_listing_page(category_url):
    """Downloads a job category page and returns parsed rows, or None if unreachable."""
    logger.info(f"Fetching job links from: {category_url}")
    job_details = []

    try:
        response = _HTTP_SESSION.get(category_url, headers=HEADERS, timeout=20)
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
    response = _HTTP_SESSION.get(job_url, headers=HEADERS, timeout=30)
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


def ocr_ad_images(image_urls, enabled=None):
    """Runs OCR on the image-based job advert, if OCR is available."""
    reader = get_ocr_reader(enabled=enabled)
    if not reader or not image_urls:
        return ""

    extracted_chunks = []
    for image_url in image_urls:
        try:
            response = _HTTP_SESSION.get(image_url, headers=HEADERS, timeout=30)
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


def analyze_job_fit(
    job_title,
    visible_text,
    ocr_text,
    *,
    profiles=None,
    minimum_fit_score=None,
    require_remote=None,
    excluded_title_keywords=None,
    excluded_seniority_keywords=None,
    level_keywords=None,
):
    """Scores a job against your profiles using title and ad content."""
    normalized_title = normalize_text(job_title)

    if (REQUIRE_REMOTE if require_remote is None else require_remote) and " remote " not in f" {normalized_title} ":
        return {
            "is_match": False,
            "skip_reason": "remote_required",
            "fit_feedback": "Skipped because remote-only mode is enabled.",
        }

    excluded_hits = find_keyword_hits(
        job_title,
        EXCLUDED_TITLE_KEYWORDS if excluded_title_keywords is None else excluded_title_keywords,
    )
    if excluded_hits:
        return {
            "is_match": False,
            "skip_reason": "excluded_role",
            "fit_feedback": f"Skipped because the title matched excluded roles: {', '.join(excluded_hits)}.",
        }

    seniority_hits = find_keyword_hits(
        job_title,
        EXCLUDED_SENIORITY_KEYWORDS if excluded_seniority_keywords is None else excluded_seniority_keywords,
    )
    if seniority_hits:
        return {
            "is_match": False,
            "skip_reason": "senior_role",
            "fit_feedback": f"Skipped because the title looks too senior: {', '.join(seniority_hits)}.",
        }

    combined_text = " ".join(part for part in [job_title, visible_text, ocr_text] if part).strip()
    level_hits = find_keyword_hits(
        job_title,
        LEVEL_KEYWORDS if level_keywords is None else level_keywords,
    )

    best_match = None
    active_profiles = JOB_PROFILES if profiles is None else profiles
    for profile_key, profile in active_profiles.items():
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

    threshold = MINIMUM_FIT_SCORE if minimum_fit_score is None else minimum_fit_score
    if not best_match or best_match["fit_score"] < threshold:
        return {
            "is_match": False,
            "skip_reason": "low_fit",
            "fit_feedback": "Skipped because the job did not score as a strong fit.",
        }

    best_match["is_match"] = True
    best_match["skip_reason"] = ""
    return best_match


def should_run_ocr(job_title, visible_text, image_urls, enabled=None):
    """Runs OCR whenever the advert content is image-based."""
    return bool(image_urls) and (
        ENABLE_OCR_FOR_AD_IMAGES if enabled is None else enabled
    )
