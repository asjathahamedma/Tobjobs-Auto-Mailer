import re
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


ApplicationStatus = Literal[
    "discovered",
    "shortlisted",
    "awaiting_review",
    "ready_to_apply",
    "applied",
    "interview",
    "rejected",
    "withdrawn",
    "failed",
]


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(default="", max_length=120)
    preferred_titles: list[str] = Field(default_factory=list, max_length=30)
    preferred_locations: list[str] = Field(default_factory=list, max_length=20)
    employment_preferences: list[str] = Field(default_factory=list, max_length=8)
    recent_job_window_days: int = Field(default=2, ge=1, le=30)
    minimum_fit_score: int = Field(default=4, ge=0, le=100)
    require_remote: bool = False
    enable_ocr_for_ad_images: bool = False
    auto_apply_enabled: bool = False
    enable_ai_features: bool = True
    ai_feature_toggles: dict[str, bool] = Field(
        default_factory=lambda: {
            "resume_analysis": True,
            "job_tuning": True,
            "application_drafts": True,
        }
    )
    category_urls: list[str] = Field(
        default_factory=lambda: [
            "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=HNS&jst=OPEN",
            "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=SDQ&jst=OPEN",
        ],
        max_length=10,
    )
    selected_resume_id: str | None = None
    your_name: str = Field(default="", max_length=120)
    contact_email: str = Field(default="", max_length=254)
    phone: str = Field(default="", max_length=40)
    portfolio: str = Field(default="", max_length=300)
    linkedin: str = Field(default="", max_length=300)
    github: str = Field(default="", max_length=300)

    @field_validator("preferred_titles", "preferred_locations", "employment_preferences")
    @classmethod
    def clean_string_lists(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        if any(len(value) > 120 for value in cleaned):
            raise ValueError("Each preference must be 120 characters or fewer.")
        return list(dict.fromkeys(cleaned))

    @field_validator("category_urls")
    @classmethod
    def validate_category_urls(cls, values: list[str]) -> list[str]:
        checked = []
        for value in values:
            if len(value) > 2048:
                raise ValueError("Category URLs must be 2048 characters or fewer.")
            parsed = urlparse(value)
            if (
                parsed.scheme != "https"
                or parsed.hostname not in {"topjobs.lk", "www.topjobs.lk"}
                or not parsed.path.startswith("/applicant/")
                or parsed.username
                or parsed.password
            ):
                raise ValueError("Only TopJobs.lk applicant category URLs are supported.")
            checked.append(value)
        if not checked:
            raise ValueError("Choose at least one TopJobs category.")
        return list(dict.fromkeys(checked))


class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resume_id: str | None = None


class ApplicationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    notes: str | None = Field(default=None, max_length=5000)
    generated_subject: str | None = Field(default=None, max_length=300)
    generated_email: str | None = Field(default=None, max_length=20000)
    cover_letter: str | None = Field(default=None, max_length=30000)


class ApprovedSend(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved: Literal[True]


class MailerCredentialUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sender_email: str = Field(min_length=3, max_length=254)
    app_password: str = Field(min_length=8, max_length=128)

    @field_validator("sender_email")
    @classmethod
    def validate_sender_email(cls, value: str) -> str:
        cleaned = value.strip()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", cleaned):
            raise ValueError("Enter a valid sender email address.")
        return cleaned

    @field_validator("app_password")
    @classmethod
    def validate_app_password(cls, value: str) -> str:
        if len("".join(value.split())) < 8:
            raise ValueError("Enter the Gmail App Password without relying on spaces.")
        return value


class ResumeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str | None = Field(default=None, min_length=1, max_length=120)
    summary: str | None = Field(default=None, max_length=2000)
    title_keywords: list[str] | None = Field(default=None, max_length=30)
    description_keywords: list[str] | None = Field(default=None, max_length=60)

    @field_validator("title_keywords", "description_keywords")
    @classmethod
    def clean_resume_keywords(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        cleaned = [value.strip() for value in values if value.strip()]
        if any(len(value) > 100 for value in cleaned):
            raise ValueError("Each resume keyword must be 100 characters or fewer.")
        return list(dict.fromkeys(cleaned))


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(default="", max_length=120)
    headline: str = Field(default="", max_length=200)
    summary: str = Field(default="", max_length=5000)
    target_roles: list[str] = Field(default_factory=list)
    seniority_level: str = Field(default="mid", max_length=40)
    years_experience: int = Field(default=0, ge=0, le=60)
    domains: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    remote_preference: bool = False
    daily_apply_cap: int = Field(default=5, ge=1, le=50)
    active: bool = True
    strengths: list[str] = Field(default_factory=list)

    @field_validator("target_roles", "domains", "preferred_locations", "strengths")
    @classmethod
    def clean_profile_lists(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(cleaned))


class AnswerBankEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str | None = None
    question: str = Field(min_length=3, max_length=500)
    answer: str = Field(min_length=1, max_length=8000)
    tags: list[str] = Field(default_factory=list)
    is_default: bool = False

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(cleaned))
