import re
import time
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

from src import scraper


def _source_job_id(url):
    query = parse_qs(urlparse(url).query)
    return (query.get("rid") or [url])[0]


def _profile_map(profiles):
    output = {}
    for profile in profiles:
        key = str(profile.get("id") or profile.get("profile_key") or profile.get("label") or "")
        if not key:
            continue
        output[key] = {
            "label": profile.get("label", "Resume profile"),
            "resume_path": "",
            "summary": profile.get("summary", ""),
            "title_keywords": profile.get("title_keywords") or [],
            "description_keywords": profile.get("description_keywords") or [],
        }
    return output


def run_topjobs_search(settings, profiles, previously_applied, on_job, on_progress):
    """Runs the existing TopJobs parser/matcher and persists each discovered item via callbacks."""
    categories = settings["category_urls"]
    for category in categories:
        parsed = urlparse(category)
        if parsed.scheme != "https" or parsed.hostname not in {"topjobs.lk", "www.topjobs.lk"}:
            raise ValueError("Only HTTPS TopJobs category URLs are supported.")

    profile_map = _profile_map(profiles)
    if not profile_map and settings.get("preferred_titles"):
        profile_map["preferences"] = {
            "label": "Job preferences",
            "resume_path": "",
            "summary": "",
            "title_keywords": settings["preferred_titles"],
            "description_keywords": [],
        }

    collected = {}
    category_errors = 0
    for index, category_url in enumerate(categories, start=1):
        on_progress(
            {
                "stage": "categories",
                "detail": f"Fetching TopJobs category {index} of {len(categories)}.",
                "current": index - 1,
                "total": len(categories),
                "percent": int((index - 1) / max(len(categories), 1) * 10),
            }
        )
        category_jobs = scraper.load_job_listing_page(category_url)
        if category_jobs is None:
            category_errors += 1
            continue
        for job in category_jobs:
            collected.setdefault(job["url"], job)
        time.sleep(1)

    today = datetime.now().date()
    start_date = today - timedelta(days=max(settings["recent_job_window_days"] - 1, 0))
    recent_jobs = [
        job for job in collected.values()
        if start_date <= job["date"] <= today
    ]
    pending = [
        job for job in recent_jobs
        if job["url"] not in previously_applied
    ]
    counts = {
        "total_found": len(recent_jobs),
        "jobs_reviewed": 0,
        "matched": 0,
        "skipped": 0,
        "errors": category_errors,
        "category_errors": category_errors,
    }

    for index, job in enumerate(pending, start=1):
        on_progress(
            {
                "stage": "job_details",
                "detail": f"Reviewing job {index} of {len(pending)}.",
                "current": index - 1,
                "total": len(pending),
                "percent": 10 + int((index - 1) / max(len(pending), 1) * 80),
            }
        )
        try:
            soup = scraper.fetch_job_page(job["url"])
            company_email = scraper.extract_company_email(soup)
            visible_text = scraper.extract_visible_page_text(soup)
            company_tag = soup.find(id="employer")
            company = company_tag.get_text(" ", strip=True) if company_tag else ""
            image_urls = scraper.extract_ad_image_urls(soup, job["url"])
            ocr_text = ""
            if scraper.should_run_ocr(
                job["title"], visible_text, image_urls,
                enabled=settings.get("enable_ocr_for_ad_images", False),
            ):
                ocr_text = scraper.ocr_ad_images(
                    image_urls,
                    enabled=settings.get("enable_ocr_for_ad_images", False),
                )
            match = scraper.analyze_job_fit(
                job["title"],
                visible_text,
                ocr_text,
                profiles=profile_map,
                minimum_fit_score=settings["minimum_fit_score"],
                require_remote=settings.get("require_remote", False),
            )
            record = {
                "source": "topjobs.lk",
                "source_job_id": _source_job_id(job["url"]),
                "source_url": job["url"],
                "title": job["title"],
                "company": company,
                "location": "",
                "description": visible_text,
                "company_email": "" if company_email == "Not Found" else company_email,
                "posted_at": job["date"].isoformat(),
                "match": match,
            }
        except Exception as exc:
            counts["errors"] += 1
            on_progress(
                {
                    "stage": "job_error",
                    "level": "warning",
                    "detail": f"Could not process one TopJobs listing ({type(exc).__name__}).",
                }
            )
            time.sleep(1)
            continue
        on_job(record)
        counts["jobs_reviewed"] += 1
        counts["matched"] += bool(match.get("is_match"))
        counts["skipped"] += not bool(match.get("is_match"))
        time.sleep(1)

    return counts
