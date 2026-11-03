import re
from collections import Counter

from src.config import get_profile_templates


COMMON_KEYWORDS = [
    "python", "javascript", "typescript", "react", "nextjs", "next js", "nodejs", "node js",
    "express", "mongodb", "mysql", "postgresql", "api", "rest api", "graphql", "java",
    "php", "laravel", "c#", ".net", "docker", "aws", "azure", "linux", "git", "figma", "ui ux",
]


def normalize_text(text: str) -> str:
    lowered = (text or "").lower()
    lowered = re.sub(r"[^a-z0-9+#.]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def find_hits(text: str, keywords: list[str]) -> list[str]:
    normalized_text = f" {normalize_text(text)} "
    return [
        keyword
        for keyword in keywords
        if (normalized := normalize_text(keyword)) and f" {normalized} " in normalized_text
    ]


def build_resume_profile(text: str, file_name: str) -> dict:
    templates = get_profile_templates()
    ranked_templates = []
    vocabulary: list[str] = list(COMMON_KEYWORDS)
    for key, template in templates.items():
        titles = template.get("title_keywords", [])
        descriptions = template.get("description_keywords", [])
        vocabulary.extend(titles)
        vocabulary.extend(descriptions)
        score = 3 * len(find_hits(text, titles)) + len(find_hits(text, descriptions))
        ranked_templates.append((score, key, template))

    keyword_counts = Counter(find_hits(text, list(dict.fromkeys(vocabulary))))
    keywords = [keyword for keyword, _ in keyword_counts.most_common()]
    score, _, template = max(ranked_templates, default=(0, "", {}))
    name = re.sub(r"[_-]+", " ", file_name.rsplit(".", 1)[0]).strip().title()
    summary = template.get("summary", "") if score else ""
    if not summary:
        summary = f"Resume profile based on the detected skills: {', '.join(keywords[:4]) or name}."
    return {
        "label": template.get("label") if score else name or "Resume profile",
        "summary": summary,
        "title_keywords": keywords[:10] or template.get("title_keywords", [])[:10],
        "description_keywords": keywords[10:22] or template.get("description_keywords", [])[:12],
    }
