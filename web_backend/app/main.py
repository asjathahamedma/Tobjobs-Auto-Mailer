import asyncio
import logging
import os
import re
import smtplib
import ssl
import uuid
from datetime import datetime, timedelta, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from io import BytesIO
from typing import Annotated, Any
from urllib.parse import quote

from cryptography.fernet import Fernet, InvalidToken
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pypdf import PdfReader

from src.web_engine import run_topjobs_search
from web_backend.app.auth import AuthenticatedUser, require_user, supabase_for_user
from web_backend.app.content import generate_application_content
from web_backend.app.schemas import (
    ApplicationStatus,
    ApplicationUpdate,
    ApprovedSend,
    MailerCredentialUpdate,
    ResumeUpdate,
    RunCreate,
    SettingsUpdate,
)
from web_backend.app.settings import get_settings
from web_backend.app.search_queue import SearchJob, enqueue_search_job
from web_backend.app.supabase_rest import SupabaseRest
from src.resume_profiles import build_resume_profile

logger = logging.getLogger("topjobs_web_api")


class SearchFailedPermanently(Exception):
    pass


app = FastAPI(title="TopJobs Auto Mailer API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def _one(rows: Any, message: str):
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=404, detail=message)
    return rows[0]


def _user_filter(user: AuthenticatedUser):
    return {"user_id": f"eq.{user.id}"}


def _extract_resume_text(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
        extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read text from this PDF.") from exc
    if not extracted.strip():
        raise HTTPException(
            status_code=422,
            detail="This PDF has no extractable text. Scanned-image resumes are not supported yet.",
        )
    return extracted


def _read_user_settings(db: SupabaseRest, user: AuthenticatedUser) -> dict[str, Any]:
    rows = db.request("GET", "user_settings", params={**_user_filter(user), "select": "settings"})
    if not rows:
        return {}
    settings = rows[0].get("settings")
    return settings if isinstance(settings, dict) else {}


def _settings_defaults() -> dict[str, Any]:
    return {
        "display_name": "",
        "preferred_titles": [],
        "preferred_locations": [],
        "employment_preferences": [],
        "recent_job_window_days": 2,
        "minimum_fit_score": 4,
        "require_remote": False,
        "enable_ocr_for_ad_images": False,
        "auto_apply_enabled": False,
        "category_urls": [
            "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=HNS&jst=OPEN",
            "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=SDQ&jst=OPEN",
        ],
        "selected_resume_id": None,
        "your_name": "",
        "contact_email": "",
        "phone": "",
        "portfolio": "",
        "linkedin": "",
        "github": "",
    }


def _require_encryption() -> Fernet:
    key = get_settings().app_credentials_encryption_key
    if not key:
        raise HTTPException(status_code=503, detail="Mailer credential encryption is not configured.")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=503, detail="Mailer credential encryption key is invalid.") from exc


def _persist_progress(db: SupabaseRest, user: AuthenticatedUser, run_id: str, progress: dict):
    db.request(
        "PATCH",
        "search_runs",
        params={"id": f"eq.{run_id}", **_user_filter(user)},
        body={"progress": progress},
        prefer="return=minimal",
    )


def _add_run_event(db: SupabaseRest, user: AuthenticatedUser, run_id: str, level: str, message: str):
    db.request(
        "POST",
        "search_run_events",
        body={
            "user_id": user.id,
            "search_run_id": run_id,
            "level": level,
            "message": message[:1000],
        },
        prefer="return=minimal",
    )


def _execute_search(
    user_id: str,
    run_id: str,
    requested_resume_id: str | None,
    *,
    access_token: str | None = None,
    service_role: bool = False,
    delivery_attempt: int = 1,
    max_attempts: int = 1,
):
    settings = get_settings()
    user = AuthenticatedUser(id=user_id, email="", access_token=access_token or "")
    if service_role:
        db = SupabaseRest(settings.supabase_service_role_key, user_id, service_role=True)
    else:
        if not access_token:
            raise ValueError("A user access token is required for a local search.")
        db = SupabaseRest(access_token, user_id)
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        run_rows = db.request(
            "GET",
            "search_runs",
            params={"id": f"eq.{run_id}", **_user_filter(user), "select": "status"},
        )
        run = _one(run_rows, "Search run not found.")
        if run["status"] in {"completed", "partially_completed", "failed", "cancelled"}:
            return

        listing_db = SupabaseRest(
            settings.supabase_service_role_key,
            service_role=True,
        )
        db.request(
            "PATCH",
            "search_runs",
            params={"id": f"eq.{run_id}", **_user_filter(user)},
            body={"status": "running", "started_at": started_at, "progress": {
                "stage": "starting", "percent": 0, "detail": "Starting a TopJobs search."
            }},
            prefer="return=minimal",
        )
        settings = {**_settings_defaults(), **_read_user_settings(db, user)}
        resumes = db.request(
            "GET",
            "resumes",
            params={**_user_filter(user), "select": "id,label,summary,title_keywords,description_keywords"},
        )
        resume_id = requested_resume_id or settings.get("selected_resume_id")
        if resume_id:
            resumes = [resume for resume in resumes if resume["id"] == resume_id]
            if not resumes:
                raise ValueError("Selected resume was not found for this account.")
        if not resumes and not settings.get("preferred_titles"):
            raise ValueError("Add a resume profile or preferred job titles before starting a search.")

        applied = db.request(
            "GET",
            "applications",
            params={
                **_user_filter(user),
                "select": "job_listings(source_url)",
                "status": "eq.applied",
            },
        )
        already_applied = {
            entry["job_listings"]["source_url"]
            for entry in applied
            if isinstance(entry.get("job_listings"), dict) and entry["job_listings"].get("source_url")
        }
        counts = {"total_found": 0, "jobs_reviewed": 0, "matched": 0, "skipped": 0, "errors": 0}
        last_progress = {"stage": "starting", "percent": 0, "detail": "Starting a TopJobs search."}

        def persist_job(record: dict):
            listing = {
                key: value for key, value in record.items()
                if key in {
                    "source", "source_job_id", "source_url", "title", "company",
                    "location", "description", "company_email", "posted_at",
                }
            }
            jobs = listing_db.request(
                "POST",
                "job_listings",
                params={"on_conflict": "source,source_job_id", "select": "id"},
                body=listing,
                prefer="resolution=merge-duplicates,return=representation",
            )
            job_id = _one(jobs, "Could not save discovered job.")["id"]
            match = record.get("match") or {}
            if match.get("is_match"):
                profile_key = match.get("profile_key")
                matched_resume = next((resume for resume in resumes if resume["id"] == profile_key), None)
                matched_title_keywords = [
                    value.strip()
                    for value in str(match.get("matched_title_keywords", "")).split(",")
                    if value.strip()
                ]
                matched_description_keywords = [
                    value.strip()
                    for value in str(match.get("matched_description_keywords", "")).split(",")
                    if value.strip()
                ]
                match_details = str(match.get("fit_feedback", "")).strip()
                if match.get("profile_label"):
                    match_details = f"Matched with the {match['profile_label']} profile. {match_details}".strip()
                db.request(
                    "POST",
                    "job_matches",
                    params={"on_conflict": "user_id,job_id", "select": "id"},
                    body={
                        "user_id": user.id,
                        "job_id": job_id,
                        "resume_id": matched_resume["id"] if matched_resume else None,
                        "search_run_id": run_id,
                        "match_score": int(match.get("fit_score", 0)),
                        "match_explanation": match_details,
                        "matched_title_keywords": matched_title_keywords,
                        "matched_description_keywords": matched_description_keywords,
                        "status": "awaiting_review",
                    },
                    prefer="resolution=ignore-duplicates,return=minimal",
                )
                db.request(
                    "PATCH",
                    "job_matches",
                    params={**_user_filter(user), "job_id": f"eq.{job_id}"},
                    body={
                        "resume_id": matched_resume["id"] if matched_resume else None,
                        "search_run_id": run_id,
                        "match_score": int(match.get("fit_score", 0)),
                        "match_explanation": match_details,
                        "matched_title_keywords": matched_title_keywords,
                        "matched_description_keywords": matched_description_keywords,
                        "last_seen_at": datetime.now(timezone.utc).isoformat(),
                    },
                    prefer="return=minimal",
                )
                matched_keywords = list(dict.fromkeys(matched_title_keywords + matched_description_keywords))
                contact = {
                    "phone": settings.get("phone", ""),
                    "contact_email": settings.get("contact_email", ""),
                    "linkedin": settings.get("linkedin", ""),
                    "github": settings.get("github", ""),
                    "portfolio": settings.get("portfolio", ""),
                }
                content = generate_application_content(
                    job_title=record.get("title", ""),
                    company=record.get("company", ""),
                    applicant_name=settings.get("your_name") or settings.get("display_name", ""),
                    profile_summary=(matched_resume or {}).get("summary", ""),
                    matched_keywords=matched_keywords,
                    contact=contact,
                )
                new_applications = db.request(
                    "POST",
                    "applications",
                    params={"on_conflict": "user_id,job_id", "select": "id"},
                    body={
                        "user_id": user.id,
                        "job_id": job_id,
                        "status": "awaiting_review",
                        "generated_subject": content.subject,
                        "generated_email": content.email,
                        "cover_letter": content.cover_letter,
                    },
                    prefer="resolution=ignore-duplicates,return=representation",
                )
                if settings.get("auto_apply_enabled") and new_applications:
                    application_id = new_applications[0]["id"]
                    try:
                        _send_application_email(
                            application_id,
                            user,
                            db,
                            request_id=f"search-{run_id}",
                            automatic=True,
                        )
                        _add_run_event(
                            db,
                            user,
                            run_id,
                            "info",
                            f"Automatically sent an application email for {record.get('title', 'a matched job')}.",
                        )
                    except HTTPException as exc:
                        logger.warning(
                            "Automatic application email %s was not sent: %s",
                            application_id,
                            exc.detail,
                        )
                        db.request(
                            "PATCH",
                            "applications",
                            params={
                                **_user_filter(user),
                                "id": f"eq.{application_id}",
                                "status": "in.(awaiting_review,failed)",
                            },
                            body={"last_error": str(exc.detail)[:1000]},
                            prefer="return=minimal",
                        )
                        _add_run_event(
                            db,
                            user,
                            run_id,
                            "warning",
                            f"Automatic application email was not sent: {exc.detail}",
                        )
            counts["jobs_reviewed"] += 1
            counts["matched"] += int(bool(match.get("is_match")))
            counts["skipped"] += int(not bool(match.get("is_match")))
            last_progress.update(
                {
                    "current": counts["jobs_reviewed"],
                    "total": max(counts["total_found"], counts["jobs_reviewed"]),
                    "jobs_found": counts["jobs_reviewed"],
                    "matched": counts["matched"],
                }
            )
            _persist_progress(db, user, run_id, last_progress)

        def progress(update: dict):
            last_progress.update(update)
            level = update.get("level", "info")
            if update.get("detail"):
                _add_run_event(db, user, run_id, level, update["detail"])
            _persist_progress(db, user, run_id, last_progress)

        progress({"stage": "discovery", "percent": 0, "detail": "Loading TopJobs listings."})
        counts = run_topjobs_search(
            settings,
            resumes,
            already_applied,
            persist_job,
            progress,
        )
        status = "partially_completed" if counts["errors"] else "completed"
        db.request(
            "PATCH",
            "search_runs",
            params={"id": f"eq.{run_id}", **_user_filter(user)},
            body={
                "status": status,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "jobs_found": counts["jobs_reviewed"],
                "progress": {
                    "stage": "complete",
                    "percent": 100,
                    "detail": "Search completed." if not counts["errors"] else "Search completed with some source errors.",
                    **counts,
                },
                "error_summary": f"{counts['errors']} listing/category errors" if counts["errors"] else "",
            },
            prefer="return=minimal",
        )
        _add_run_event(db, user, run_id, "info", "Search run completed.")
    except Exception as exc:
        logger.exception("Search run %s failed", run_id)
        try:
            is_final_attempt = delivery_attempt >= max_attempts
            db.request(
                "PATCH",
                "search_runs",
                params={"id": f"eq.{run_id}", **_user_filter(user)},
                body={
                    "status": "failed" if is_final_attempt else "queued",
                    "completed_at": datetime.now(timezone.utc).isoformat() if is_final_attempt else None,
                    "error_summary": str(exc)[:1000],
                    "progress": {
                        "stage": "failed" if is_final_attempt else "retrying",
                        "percent": 100 if is_final_attempt else 0,
                        "detail": (
                            "Search failed after repeated attempts. Previously saved results were retained."
                            if is_final_attempt
                            else "A temporary error interrupted this attempt. The search will be retried."
                        ),
                    },
                },
                prefer="return=minimal",
            )
            _add_run_event(
                db,
                user,
                run_id,
                "error" if is_final_attempt else "warning",
                f"Search attempt {delivery_attempt} failed: {type(exc).__name__}.",
            )
        except Exception:
            logger.exception("Could not save failed search state for run %s", run_id)
            raise
        if is_final_attempt:
            raise SearchFailedPermanently(str(exc)) from exc
        raise


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/settings")
def get_user_settings(
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
):
    rows = db.request("GET", "profiles", params={"id": f"eq.{user.id}", "select": "display_name,email"})
    return {
        **_settings_defaults(),
        **_read_user_settings(db, user),
        "profile": rows[0] if rows else {"email": user.email, "display_name": ""},
        "mailer_configured": bool(
            db.request(
                "GET",
                "mailer_credentials",
                params={**_user_filter(user), "select": "sender_email"},
            )
        ),
    }


@app.get("/api/analytics")
def get_analytics(
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
):
    base = _user_filter(user)
    total_matches = db.count("job_matches", params=base)
    total_applications = db.count("applications", params=base)
    sent_applications = db.count("applications", params={**base, "status": "eq.applied"})
    runs = db.request(
        "GET",
        "search_runs",
        params={**base, "select": "progress,status", "order": "created_at.desc", "limit": 1000},
    )
    reviewed = sum(
        int((run.get("progress") or {}).get("jobs_reviewed", 0))
        for run in runs
        if run.get("status") in {"completed", "partially_completed"}
    )
    return {
        "matched_jobs": total_matches,
        "applications": total_applications,
        "sent_applications": sent_applications,
        "jobs_reviewed_recent_runs": reviewed,
        "match_rate_recent_runs": round(
            sum(
                int((run.get("progress") or {}).get("matched", 0))
                for run in runs
                if run.get("status") in {"completed", "partially_completed"}
            ) / reviewed * 100
        ) if reviewed else 0,
        "runs": runs,
    }


@app.patch("/api/settings")
def update_user_settings(
    payload: SettingsUpdate,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
):
    if payload.selected_resume_id:
        selected = db.request(
            "GET",
            "resumes",
            params={
                **_user_filter(user),
                "id": f"eq.{payload.selected_resume_id}",
                "select": "id",
            },
        )
        if not selected:
            raise HTTPException(status_code=422, detail="Choose a resume profile from your account.")
    if payload.auto_apply_enabled:
        credentials = db.request(
            "GET",
            "mailer_credentials",
            params={**_user_filter(user), "select": "sender_email"},
        )
        resumes = db.request(
            "GET",
            "resumes",
            params={**_user_filter(user), "select": "id", "limit": 1},
        )
        if not credentials:
            raise HTTPException(
                status_code=422,
                detail="Save a Gmail App Password in Settings before enabling automatic applications.",
            )
        if not resumes:
            raise HTTPException(
                status_code=422,
                detail="Upload a resume profile before enabling automatic applications.",
            )
    settings = payload.model_dump()
    db.request(
        "PATCH",
        "profiles",
        params={"id": f"eq.{user.id}"},
        body={"display_name": payload.display_name, "email": user.email},
        prefer="return=minimal",
    )
    db.request(
        "POST",
        "user_settings",
        params={"on_conflict": "user_id"},
        body={"user_id": user.id, "settings": settings},
        prefer="resolution=merge-duplicates,return=minimal",
    )
    return {"ok": True, **settings}


@app.put("/api/mailer-credentials")
def save_mailer_credentials(
    payload: MailerCredentialUpdate,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
):
    cipher = _require_encryption()
    encrypted = cipher.encrypt("".join(payload.app_password.split()).encode()).decode()
    db.request(
        "POST",
        "mailer_credentials",
        params={"on_conflict": "user_id"},
        body={
            "user_id": user.id,
            "sender_email": payload.sender_email,
            "encrypted_app_password": encrypted,
        },
        prefer="resolution=merge-duplicates,return=minimal",
    )
    return {"ok": True, "configured": True, "sender_email": payload.sender_email}


@app.get("/api/resumes")
def list_resumes(
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
):
    return db.request(
        "GET",
        "resumes",
        params={**_user_filter(user), "select": "id,file_name,label,summary,title_keywords,description_keywords,created_at", "order": "created_at.desc"},
    )


@app.post("/api/resumes", status_code=201)
async def upload_resume(
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
    file: UploadFile = File(...),
):
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", file.filename or "resume.pdf")[:120]
    if not filename.lower().endswith(".pdf") or file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Upload a PDF resume.")
    content = await file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Resume files must be 10 MB or smaller.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")
    extracted = _extract_resume_text(content)
    profile = build_resume_profile(extracted, filename)
    resume_id = str(uuid.uuid4())
    storage_path = f"{user.id}/{resume_id}-{filename}"
    db.storage_request(
        "POST",
        f"object/private-resumes/{quote(storage_path, safe='/')}",
        content=content,
        content_type="application/pdf",
        extra_headers={"x-upsert": "false"},
    )
    payload = {
        "id": resume_id,
        "user_id": user.id,
        "storage_path": storage_path,
        "file_name": filename,
        **profile,
        "extracted_text_length": len(extracted),
    }
    rows = db.request("POST", "resumes", body=payload, prefer="return=representation")
    return _one(rows, "Could not save resume profile.")


@app.get("/api/resumes/{resume_id}/file")
def preview_resume(
    resume_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
):
    rows = db.request(
        "GET",
        "resumes",
        params={
            **_user_filter(user),
            "id": f"eq.{resume_id}",
            "select": "storage_path,file_name",
        },
    )
    resume = _one(rows, "Resume profile not found.")
    content = db.storage_request(
        "GET",
        f"object/private-resumes/{quote(resume['storage_path'], safe='/')}",
    ).content
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", resume.get("file_name") or "resume.pdf")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.post("/api/resumes/{resume_id}/extract-keywords")
def extract_resume_keywords(
    resume_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
):
    rows = db.request(
        "GET",
        "resumes",
        params={
            **_user_filter(user),
            "id": f"eq.{resume_id}",
            "select": "storage_path,file_name",
        },
    )
    resume = _one(rows, "Resume profile not found.")
    content = db.storage_request(
        "GET",
        f"object/private-resumes/{quote(resume['storage_path'], safe='/')}",
    ).content
    extracted = _extract_resume_text(content)
    profile = build_resume_profile(extracted, resume.get("file_name") or "resume.pdf")
    updated = db.request(
        "PATCH",
        "resumes",
        params={
            **_user_filter(user),
            "id": f"eq.{resume_id}",
            "select": "id,file_name,label,summary,title_keywords,description_keywords,created_at",
        },
        body={
            "title_keywords": profile["title_keywords"],
            "description_keywords": profile["description_keywords"],
            "extracted_text_length": len(extracted),
        },
        prefer="return=representation",
    )
    return _one(updated, "Resume profile not found.")


@app.patch("/api/resumes/{resume_id}")
def update_resume(
    resume_id: str,
    payload: ResumeUpdate,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Provide at least one profile field to update.")
    rows = db.request(
        "PATCH",
        "resumes",
        params={
            **_user_filter(user),
            "id": f"eq.{resume_id}",
            "select": "id,file_name,label,summary,title_keywords,description_keywords,created_at",
        },
        body=changes,
        prefer="return=representation",
    )
    return _one(rows, "Resume profile not found.")


@app.delete("/api/resumes/{resume_id}")
def delete_resume(
    resume_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
):
    resume = _one(
        db.request(
            "GET",
            "resumes",
            params={
                **_user_filter(user),
                "id": f"eq.{resume_id}",
                "select": "id,storage_path",
            },
        ),
        "Resume profile not found.",
    )
    remaining = db.request(
        "GET",
        "resumes",
        params={
            **_user_filter(user),
            "id": f"neq.{resume_id}",
            "select": "id",
            "order": "created_at.desc",
            "limit": 1,
        },
    )
    replacement_id = remaining[0]["id"] if remaining else None
    settings = _read_user_settings(db, user)
    selection_changed = settings.get("selected_resume_id") == resume_id
    selected_resume_id = settings.get("selected_resume_id")
    if selection_changed:
        settings["selected_resume_id"] = replacement_id
        selected_resume_id = replacement_id

    db.request(
        "PATCH",
        "job_matches",
        params={**_user_filter(user), "resume_id": f"eq.{resume_id}"},
        body={"resume_id": None},
        prefer="return=minimal",
    )
    if selection_changed:
        db.request(
            "POST",
            "user_settings",
            params={"on_conflict": "user_id"},
            body={"user_id": user.id, "settings": settings},
            prefer="resolution=merge-duplicates,return=minimal",
        )
    deleted = db.request(
        "DELETE",
        "resumes",
        params={**_user_filter(user), "id": f"eq.{resume_id}", "select": "id"},
        prefer="return=representation",
    )
    _one(deleted, "Resume profile was not deleted.")
    db.storage_request(
        "DELETE",
        f"object/private-resumes/{quote(resume['storage_path'], safe='/')}",
    )
    return {"ok": True, "selected_resume_id": selected_resume_id}


@app.get("/api/jobs")
def list_jobs(
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status: ApplicationStatus | None = None,
    search: str | None = Query(default=None, max_length=100),
):
    params: dict[str, Any] = {
        **_user_filter(user),
        "select": "id,match_score,match_explanation,matched_title_keywords,matched_description_keywords,status,last_seen_at,job_listings(id,title,company,location,description,company_email,source_url,posted_at,discovered_at),resumes(id,label,file_name)",
        "order": "last_seen_at.desc",
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }
    if status:
        params["status"] = f"eq.{status}"
    if search:
        term = re.sub(r"[^A-Za-z0-9 ._-]", " ", search).strip()
        if term:
            params["job_listings.title"] = f"ilike.*{term}*"
    jobs = db.request("GET", "job_matches", params=params)
    return {"items": jobs, "page": page, "page_size": page_size}


@app.post("/api/search-runs", status_code=202)
def create_search_run(
    payload: RunCreate,
    background_tasks: BackgroundTasks,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
):
    if os.getenv("VERCEL_ENV") == "preview":
        raise HTTPException(
            status_code=503,
            detail="Search runs are enabled on the production deployment only.",
        )
    settings = {**_settings_defaults(), **_read_user_settings(db, user)}
    resume_id = payload.resume_id or settings.get("selected_resume_id")
    if resume_id and not db.request(
        "GET",
        "resumes",
        params={**_user_filter(user), "id": f"eq.{resume_id}", "select": "id"},
    ):
        raise HTTPException(status_code=422, detail="Choose a resume profile from your account.")
    if not resume_id and not settings.get("preferred_titles") and not db.request(
        "GET",
        "resumes",
        params={**_user_filter(user), "select": "id", "limit": 1},
    ):
        raise HTTPException(status_code=422, detail="Add a resume profile or preferred job titles before searching.")
    active_runs = db.request(
        "GET",
        "search_runs",
        params={
            **_user_filter(user),
            "status": "in.(queued,running)",
            "select": "id,status,updated_at",
            "limit": 5,
        },
    )
    stale_before = (datetime.now(timezone.utc) - timedelta(days=8)).timestamp()
    still_active = []
    for active_run in active_runs:
        try:
            last_update = datetime.fromisoformat(
                active_run["updated_at"].replace("Z", "+00:00")
            ).timestamp()
        except (KeyError, TypeError, ValueError):
            last_update = datetime.now(timezone.utc).timestamp()
        if last_update < stale_before:
            db.request(
                "PATCH",
                "search_runs",
                params={**_user_filter(user), "id": f"eq.{active_run['id']}", "status": f"eq.{active_run['status']}"},
                body={
                    "status": "failed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "error_summary": "Run stopped reporting progress; it may have been interrupted by a service restart.",
                    "progress": {
                        "stage": "failed",
                        "percent": 100,
                        "detail": "Search was interrupted and saved results were kept.",
                    },
                },
                prefer="return=minimal",
            )
        else:
            still_active.append(active_run)
    if still_active:
        raise HTTPException(status_code=409, detail="A search is already running for your account.")
    rows = db.request(
        "POST",
        "search_runs",
        body={
            "user_id": user.id,
            "status": "queued",
            "search_parameters": {
                "resume_id": resume_id,
                "category_urls": settings["category_urls"],
            },
            "progress": {"stage": "queued", "percent": 0, "detail": "Search queued."},
        },
        prefer="return=representation",
    )
    run = _one(rows, "Could not create search run.")
    if get_settings().search_queue_backend == "vercel":
        try:
            asyncio.run(
                enqueue_search_job(
                    get_settings().vercel_queue_region,
                    SearchJob(user_id=user.id, run_id=run["id"], resume_id=resume_id),
                )
            )
        except Exception as exc:
            logger.exception("Could not enqueue search run %s", run["id"])
            try:
                db.request(
                    "PATCH",
                    "search_runs",
                    params={"id": f"eq.{run['id']}", **_user_filter(user)},
                    body={
                        "status": "failed",
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "error_summary": "The search queue is unavailable. Please try again.",
                        "progress": {
                            "stage": "failed",
                            "percent": 100,
                            "detail": "The search could not be queued. Please try again.",
                        },
                    },
                    prefer="return=minimal",
                )
            except Exception:
                logger.exception("Could not record queue failure for search run %s", run["id"])
            raise HTTPException(
                status_code=503,
                detail="The search queue is unavailable. Please try again.",
            ) from exc
    else:
        background_tasks.add_task(
            _execute_search,
            user.id,
            run["id"],
            resume_id,
            access_token=user.access_token,
        )
    return run


@app.get("/api/search-runs")
def list_search_runs(
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    runs = db.request(
        "GET",
        "search_runs",
        params={**_user_filter(user), "select": "*", "order": "created_at.desc", "limit": page_size, "offset": (page - 1) * page_size},
    )
    return {"items": runs, "page": page, "page_size": page_size}


@app.get("/api/search-runs/{run_id}")
def get_search_run(
    run_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
):
    run = _one(
        db.request("GET", "search_runs", params={**_user_filter(user), "id": f"eq.{run_id}", "select": "*"}),
        "Search run not found.",
    )
    events = db.request(
        "GET",
        "search_run_events",
        params={**_user_filter(user), "search_run_id": f"eq.{run_id}", "select": "level,message,created_at", "order": "created_at.desc", "limit": 50},
    )
    return {**run, "events": events}


@app.get("/api/applications")
def list_applications(
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status: ApplicationStatus | None = None,
):
    params: dict[str, Any] = {
        **_user_filter(user),
        "select": "id,status,generated_subject,generated_email,cover_letter,notes,submitted_at,last_error,created_at,updated_at,job_listings(id,title,company,location,description,company_email,source_url),",
        "order": "updated_at.desc",
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }
    params["select"] = params["select"].rstrip(",")
    if status:
        params["status"] = f"eq.{status}"
    return {"items": db.request("GET", "applications", params=params), "page": page, "page_size": page_size}


@app.patch("/api/applications/{application_id}")
def update_application(
    application_id: str,
    payload: ApplicationUpdate,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Provide at least one field to update.")
    rows = db.request(
        "PATCH",
        "applications",
        params={**_user_filter(user), "id": f"eq.{application_id}", "select": "id,status,notes,generated_subject,generated_email,cover_letter,updated_at"},
        body=changes,
        prefer="return=representation",
    )
    return _one(rows, "Application not found.")


@app.post("/api/applications/{application_id}/generate-content")
def generate_content(
    application_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
):
    app_row = _one(
        db.request(
            "GET",
            "applications",
            params={**_user_filter(user), "id": f"eq.{application_id}", "select": "id,job_id,status,job_listings(title,company)"},
        ),
        "Application not found.",
    )
    job = app_row.get("job_listings") or {}
    match_rows = db.request(
    "GET",
    "job_matches",
    params={
        **_user_filter(user),
        "job_id": f"eq.{app_row['job_id']}",
        "select": "match_explanation,matched_title_keywords,matched_description_keywords,resumes(summary)",
    },
    )
    match = match_rows[0] if match_rows else {}
    resume = match.get("resumes") or {}
    settings = {**_settings_defaults(), **_read_user_settings(db, user)}
    keywords = (match.get("matched_title_keywords") or []) + (match.get("matched_description_keywords") or [])
    contact = {
        "phone": settings["phone"],
        "contact_email": settings["contact_email"],
        "linkedin": settings["linkedin"],
        "github": settings["github"],
        "portfolio": settings["portfolio"],
    }
    content = generate_application_content(
        job_title=job.get("title", ""),
        company=job.get("company", ""),
        applicant_name=settings.get("your_name") or settings.get("display_name", ""),
        profile_summary=resume.get("summary", ""),
        matched_keywords=keywords,
        contact=contact,
    )
    rows = db.request(
        "PATCH",
        "applications",
        params={**_user_filter(user), "id": f"eq.{application_id}", "select": "id,status,generated_subject,generated_email,cover_letter"},
        body={
            "generated_subject": content.subject,
            "generated_email": content.email,
            "cover_letter": content.cover_letter,
            "status": "awaiting_review",
        },
        prefer="return=representation",
    )
    return _one(rows, "Could not save application draft.")


def _send_application_email(
    application_id: str,
    user: AuthenticatedUser,
    db: SupabaseRest,
    *,
    request_id: str,
    automatic: bool,
):
    app_row = _one(
        db.request(
            "GET",
            "applications",
            params={**_user_filter(user), "id": f"eq.{application_id}", "select": "id,job_id,status,generated_subject,generated_email,job_listings(title,company_email,source_url)"},
        ),
        "Application not found.",
    )
    if app_row["status"] == "applied":
        raise HTTPException(status_code=409, detail="This application has already been sent.")
    if app_row["status"] == "sending":
        raise HTTPException(
            status_code=409,
            detail="This email is already being sent or its outcome is still being confirmed. Check Gmail Sent before taking further action.",
        )
    allowed_statuses = {"awaiting_review"} if automatic else {"awaiting_review", "ready_to_apply", "failed"}
    if app_row["status"] not in allowed_statuses:
        raise HTTPException(status_code=409, detail="This application is not in a sendable state.")
    job = app_row.get("job_listings") or {}
    recipient = (job.get("company_email") or "").strip()
    if not recipient or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient):
        raise HTTPException(status_code=422, detail="The listing does not have a valid application email.")
    if not app_row.get("generated_subject") or not app_row.get("generated_email"):
        raise HTTPException(status_code=409, detail="Generate and review the application email first.")
    if "\r" in app_row["generated_subject"] or "\n" in app_row["generated_subject"]:
        raise HTTPException(status_code=422, detail="The email subject contains invalid line breaks. Edit and save the subject before sending.")
    match_rows = db.request(
        "GET",
        "job_matches",
        params={
            **_user_filter(user),
            "job_id": f"eq.{app_row['job_id']}",
            "select": "resume_id,resumes(storage_path,file_name)",
        },
    )
    resume = match_rows[0].get("resumes") if match_rows else None
    if not isinstance(resume, dict) or not resume.get("storage_path"):
        raise HTTPException(status_code=422, detail="Add a resume profile to this job match before sending.")
    credential = _one(
        db.request("GET", "mailer_credentials", params={**_user_filter(user), "select": "sender_email,encrypted_app_password"}),
        "Set up your Gmail App Password in Settings before sending.",
    )
    try:
        password = _require_encryption().decrypt(
            credential["encrypted_app_password"].encode()
        ).decode()
    except (InvalidToken, KeyError, ValueError) as exc:
        logger.exception("Could not decrypt mailer credentials for user %s", user.id)
        raise HTTPException(status_code=503, detail="Saved mailer credentials cannot be decrypted; please save them again.") from exc

    message = MIMEMultipart()
    settings = {**_settings_defaults(), **_read_user_settings(db, user)}
    message["From"] = formataddr((settings.get("your_name") or settings.get("display_name", ""), credential["sender_email"]))
    message["To"] = recipient
    message["Subject"] = app_row["generated_subject"]
    message.attach(MIMEText(app_row["generated_email"], "plain", "utf-8"))
    attachment = db.storage_request(
        "GET",
        f"object/private-resumes/{quote(resume['storage_path'], safe='/')}",
    )
    attached_pdf = MIMEBase("application", "pdf")
    attached_pdf.set_payload(attachment.content)
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", resume.get("file_name") or "resume.pdf")[:120]
    attached_pdf.add_header(
        "Content-Disposition",
        "attachment",
        filename=filename,
    )
    encoders.encode_base64(attached_pdf)
    message.attach(attached_pdf)

    claimed = db.request(
        "PATCH",
        "applications",
        params={
            **_user_filter(user),
            "id": f"eq.{application_id}",
            "status": "eq.awaiting_review" if automatic else "in.(awaiting_review,ready_to_apply,failed)",
            "select": "id",
        },
        body={"status": "sending", "last_error": ""},
        prefer="return=representation",
    )
    if not claimed:
        raise HTTPException(status_code=409, detail="This application is already being sent or is not ready to send.")
    submission_started = False
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=30) as server:
            server.login(credential["sender_email"], password)
            serialized_message = message.as_string()
            submission_started = True
            refused = server.sendmail(credential["sender_email"], recipient, serialized_message)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)
    except (smtplib.SMTPAuthenticationError, smtplib.SMTPRecipientsRefused, smtplib.SMTPDataError) as exc:
        logger.exception(
            "Gmail rejected application email %s (request %s)",
            application_id,
            request_id,
        )
        db.request(
            "PATCH",
            "applications",
            params={**_user_filter(user), "id": f"eq.{application_id}", "status": "eq.sending"},
            body={"status": "failed", "last_error": "SMTP send failed. Verify the address and App Password, then retry."},
            prefer="return=minimal",
        )
        if isinstance(exc, smtplib.SMTPAuthenticationError):
            detail = "Gmail rejected the sign-in. Verify the sender address and its Google App Password in Settings."
        else:
            detail = "Gmail rejected the recipient or message. Verify the recipient address and reviewed email."
        raise HTTPException(status_code=502, detail=detail) from exc
    except (smtplib.SMTPException, OSError) as exc:
        logger.exception(
            "SMTP transport failed for application %s (request %s)",
            application_id,
            request_id,
        )
        if submission_started:
            db.request(
                "PATCH",
                "applications",
                params={**_user_filter(user), "id": f"eq.{application_id}", "status": "eq.sending"},
                body={
                    "last_error": "Email submission outcome is uncertain. Check Gmail Sent before attempting another send."
                },
                prefer="return=minimal",
            )
            raise HTTPException(
                status_code=502,
                detail="The connection ended during email submission, so Gmail's acceptance could not be confirmed. Check Gmail Sent before retrying; this application is locked to prevent duplicate email.",
            ) from exc
        db.request(
            "PATCH",
            "applications",
            params={**_user_filter(user), "id": f"eq.{application_id}", "status": "eq.sending"},
            body={"status": "failed", "last_error": "Could not connect to Gmail. Verify mailer settings and retry."},
            prefer="return=minimal",
        )
        raise HTTPException(
            status_code=502,
            detail="Could not connect to Gmail before submitting the email. Check the sender address and App Password, then retry.",
        ) from exc

    completed_at = datetime.now(timezone.utc).isoformat()
    completion = {
        "status": "applied",
        "approved_at": None if automatic else completed_at,
        "submitted_at": completed_at,
        "submission_reference": (
            "Automatically authorized in account settings; Gmail SMTP accepted the message. Delivery is not confirmed."
            if automatic
            else "Gmail SMTP accepted the message; delivery is not confirmed."
        ),
        "last_error": "",
    }
    rows = db.request(
        "PATCH",
        "applications",
        params={**_user_filter(user), "id": f"eq.{application_id}", "status": "eq.sending", "select": "id,status,submitted_at,submission_reference"},
        body=completion,
        prefer="return=representation",
    )
    if not rows:
        logger.error(
            "Gmail accepted application email %s but status update returned no row (request %s)",
            application_id,
            request_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Gmail accepted the email, but the application status could not be updated. Do not retry; check Gmail Sent and refresh the application.",
        )
    return _one(rows, "Email was accepted, but application status could not be updated.")


@app.post("/api/applications/{application_id}/send")
def send_approved_email(
    application_id: str,
    approval: ApprovedSend,
    user: Annotated[AuthenticatedUser, Depends(require_user)],
    db: Annotated[SupabaseRest, Depends(supabase_for_user)],
    request: Request,
):
    return _send_application_email(
        application_id,
        user,
        db,
        request_id=request.state.request_id,
        automatic=False,
    )
