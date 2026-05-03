import re
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

from src.config import get_profile_templates, load_app_config, save_app_config


COMMON_KEYWORDS = [
    "python",
    "javascript",
    "typescript",
    "react",
    "nextjs",
    "next js",
    "nodejs",
    "node js",
    "express",
    "mongodb",
    "mysql",
    "postgresql",
    "api",
    "rest api",
    "graphql",
    "java",
    "php",
    "laravel",
    "c#",
    ".net",
    "docker",
    "aws",
    "azure",
    "linux",
    "git",
    "figma",
    "ui ux",
]


def normalize_text(text):
    lowered = (text or "").lower()
    lowered = re.sub(r"[^a-z0-9+#.]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def slugify(value):
    normalized = normalize_text(value)
    slug = normalized.replace(" ", "_").strip("_")
    return slug or "resume_profile"


def extract_resume_text(pdf_path):
    reader = PdfReader(str(pdf_path))
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def keyword_vocabulary():
    templates = get_profile_templates()
    ordered = []
    for template in templates.values():
        ordered.extend(template.get("title_keywords", []))
        ordered.extend(template.get("description_keywords", []))
    ordered.extend(COMMON_KEYWORDS)
    unique = []
    seen = set()
    for keyword in ordered:
        normalized = normalize_text(keyword)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(keyword)
    return unique


def find_hits(text, keywords):
    normalized_text = f" {normalize_text(text)} "
    hits = []
    for keyword in keywords:
        normalized_keyword = normalize_text(keyword)
        if normalized_keyword and f" {normalized_keyword} " in normalized_text:
            hits.append(keyword)
    return hits


def infer_profile_template(text):
    templates = get_profile_templates()
    best_key = ""
    best_score = -1
    for profile_key, template in templates.items():
        title_hits = find_hits(text, template.get("title_keywords", []))
        description_hits = find_hits(text, template.get("description_keywords", []))
        score = (len(title_hits) * 3) + len(description_hits)
        if score > best_score:
            best_key = profile_key
            best_score = score
    return best_key if best_score > 0 else ""


def extract_ranked_keywords(text):
    vocabulary = keyword_vocabulary()
    hits = find_hits(text, vocabulary)
    weights = Counter()
    for keyword in hits:
        weights[keyword] += max(1, len(keyword.split()))
    ranked = [keyword for keyword, _ in weights.most_common()]
    return ranked


def normalize_keywords(values):
    normalized_values = []
    seen = set()
    for value in values or []:
        cleaned = " ".join(str(value).strip().split())
        normalized = normalize_text(cleaned)
        if not cleaned or not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_values.append(cleaned)
    return normalized_values


def build_profile_definition(pdf_path, overrides=None):
    overrides = overrides or {}
    text = extract_resume_text(pdf_path)
    ranked_keywords = extract_ranked_keywords(text)
    inferred_template_key = infer_profile_template(text)
    templates = get_profile_templates()
    template = templates.get(inferred_template_key, {})

    override_title_keywords = normalize_keywords(overrides.get("title_keywords", []))
    override_description_keywords = normalize_keywords(overrides.get("description_keywords", []))

    title_keywords = (
        override_title_keywords
        or ranked_keywords[:10]
        or template.get("title_keywords", [])[:10]
    )
    description_keywords = (
        override_description_keywords
        or ranked_keywords[10:22]
        or template.get("description_keywords", [])[:12]
    )

    readable_name = pdf_path.stem.replace("_", " ").replace("-", " ").strip()
    override_label = " ".join(str(overrides.get("label", "")).strip().split())
    override_summary = " ".join(str(overrides.get("summary", "")).strip().split())

    label = override_label or template.get("label") or readable_name.title()
    summary_keywords = ", ".join((title_keywords + description_keywords)[:4])
    summary = (
        override_summary
        or template.get("summary")
        or f"Imported resume profile based on the detected skills in {summary_keywords or readable_name}."
    )

    return {
        "label": label,
        "resume_path": str(Path("resumes") / pdf_path.name).replace("/", "\\"),
        "summary": summary,
        "title_keywords": title_keywords,
        "description_keywords": description_keywords,
        "inferred_template_key": inferred_template_key,
        "extracted_text_length": len(text),
    }


def preview_profile_for_resume(pdf_path, overrides=None):
    profile_definition = build_profile_definition(pdf_path, overrides=overrides)
    return {
        "draft": {
            "label": profile_definition["label"],
            "summary": profile_definition["summary"],
            "title_keywords": profile_definition["title_keywords"],
            "description_keywords": profile_definition["description_keywords"],
        },
        "meta": {
            "resume_file_name": pdf_path.name,
            "resume_path": str(pdf_path),
            "inferred_template_key": profile_definition["inferred_template_key"],
            "extracted_text_length": profile_definition["extracted_text_length"],
        },
    }


def create_or_update_profile_for_resume(pdf_path, overrides=None):
    overrides = overrides or {}
    config = load_app_config()
    profile_definition = build_profile_definition(pdf_path, overrides=overrides)
    preferred_key = " ".join(str(overrides.get("profile_key", "")).strip().split())
    base_key = slugify(preferred_key or profile_definition["label"])
    profile_key = base_key
    index = 2

    existing_profiles = config.setdefault("profiles", {})
    while profile_key in existing_profiles:
        existing_resume = existing_profiles[profile_key].get("resume_path", "")
        if normalize_text(existing_resume) == normalize_text(profile_definition["resume_path"]):
            break
        profile_key = f"{base_key}_{index}"
        index += 1

    existing_profiles[profile_key] = {
        "label": profile_definition["label"],
        "resume_path": profile_definition["resume_path"],
        "summary": profile_definition["summary"],
        "title_keywords": profile_definition["title_keywords"],
        "description_keywords": profile_definition["description_keywords"],
    }
    save_app_config(config)

    return {
        "profile_key": profile_key,
        "profile": existing_profiles[profile_key],
        "meta": {
            "inferred_template_key": profile_definition["inferred_template_key"],
            "extracted_text_length": profile_definition["extracted_text_length"],
        },
    }
