import re

from src.config import get_profile_templates


COMMON_KEYWORDS = [
    "python", "javascript", "typescript", "react", "nextjs", "next js", "nodejs", "node js",
    "express", "mongodb", "mysql", "postgresql", "api", "rest api", "graphql", "java",
    "php", "laravel", "c#", ".net", "docker", "aws", "azure", "linux", "git", "figma", "ui ux",
    "html", "css", "tailwind", "redux", "vue", "angular", "svelte", "vite", "webpack",
    "nestjs", "fastapi", "django", "flask", "spring boot", "spring", "ruby", "rails",
    "go", "golang", "rust", "kotlin", "swift", "dart", "flutter", "react native",
    "c++", "c", "asp.net", "blazor", "wordpress", "drupal", "shopify", "webflow",
    "sql", "sqlite", "oracle", "mariadb", "redis", "elasticsearch", "dynamodb", "firebase",
    "supabase", "snowflake", "bigquery", "redshift", "databricks", "hadoop", "spark",
    "pandas", "numpy", "scikit learn", "tensorflow", "pytorch", "keras", "machine learning",
    "deep learning", "natural language processing", "nlp", "computer vision", "data science",
    "data analysis", "data analytics", "data visualization", "power bi", "tableau", "excel",
    "statistics", "etl", "data warehouse", "data modeling", "generative ai", "large language models",
    "llm", "prompt engineering", "openai", "langchain", "airflow",
    "google cloud", "gcp", "vercel", "netlify", "heroku", "kubernetes", "terraform",
    "ansible", "jenkins", "github actions", "ci cd", "devops", "serverless", "cloud computing",
    "cloudformation", "prometheus", "grafana", "nginx", "apache", "bash", "powershell",
    "networking", "tcp ip", "dns", "vpn", "firewall", "active directory", "windows server",
    "cybersecurity", "penetration testing", "owasp", "siem", "splunk", "incident response",
    "vulnerability assessment", "burp suite", "wireshark", "nmap", "soc", "ccna",
    "selenium", "playwright", "cypress", "jest", "pytest", "junit", "testing",
    "test automation", "quality assurance", "manual testing", "postman", "robot framework",
    "agile", "scrum", "kanban", "jira", "project management", "product management",
    "business analysis", "requirements gathering", "stakeholder management", "leadership",
    "communication", "customer service", "sales", "marketing", "seo", "content writing",
    "financial analysis", "accounting", "bookkeeping", "human resources", "recruitment",
    "figma", "adobe xd", "adobe photoshop", "adobe illustrator", "user experience",
    "user interface", "wireframing", "prototyping", "responsive design", "accessibility",
    "graphic design", "visual design", "usability testing", "design systems",
    "microservices", "distributed systems", "system design", "object oriented programming",
    "oop", "data structures", "algorithms", "authentication", "authorization", "oauth",
    "jwt", "rest", "soap", "websocket", "graphql api", "api integration", "mobile development",
    "ios", "android", "embedded systems", "internet of things", "iot", "blockchain",
    "solidity", "ethereum", "technical support", "it support", "troubleshooting",
    "customer relationship management", "crm", "salesforce", "sap", "erp",
]

ADDITIONAL_TITLE_KEYWORDS = [
    "software engineer", "software developer", "web developer", "web designer",
    "frontend developer", "front end developer", "backend developer", "back end developer",
    "full stack developer", "fullstack developer", "mobile app developer",
    "application developer", "python developer", "java developer", "react developer",
    "devops engineer", "cloud engineer", "site reliability engineer", "platform engineer",
    "data engineer", "data analyst", "business intelligence analyst", "data scientist",
    "machine learning engineer", "ai engineer", "qa engineer", "qa analyst", "test engineer",
    "automation tester", "security analyst", "cybersecurity analyst", "security engineer",
    "network engineer", "system administrator", "it support engineer", "technical support",
    "ui designer", "ux designer", "product designer", "graphic designer",
    "project manager", "product manager", "business analyst", "scrum master",
    "technical writer", "digital marketer", "marketing executive", "sales executive",
    "accountant", "finance analyst", "hr executive", "recruiter", "customer success manager",
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


def _ranked_hits(text: str, keywords: list[str]) -> list[str]:
    normalized_text = f" {normalize_text(text)} "
    unique_keywords = list(dict.fromkeys(keywords))
    positions = {keyword: index for index, keyword in enumerate(unique_keywords)}
    counts = {
        keyword: normalized_text.count(f" {normalized} ")
        for keyword in unique_keywords
        if (normalized := normalize_text(keyword)) and f" {normalized} " in normalized_text
    }
    return sorted(counts, key=lambda keyword: (-counts[keyword], positions[keyword]))


def _infer_years_experience(text: str) -> int:
    matches = re.findall(r"(\d{1,2})\s*(?:\+\s*)?years?", text.lower())
    if matches:
        years = max(int(value) for value in matches)
        return years
    return 0


def _infer_seniority_level(text: str, years_experience: int) -> str:
    if "manager" in text.lower() or "director" in text.lower():
        return "manager/director"
    if "lead" in text.lower() or "principal" in text.lower():
        return "lead/principal"
    if years_experience >= 8:
        return "senior"
    if years_experience >= 4:
        return "mid"
    if years_experience >= 2:
        return "junior/entry"
    return "intern/trainee"


def _infer_target_roles(text: str, title_keywords: list[str]) -> list[str]:
    found: list[str] = []
    for keyword in ADDITIONAL_TITLE_KEYWORDS:
        if keyword.lower() in text.lower() and keyword not in found:
            found.append(keyword)
    for keyword in title_keywords:
        if keyword not in found:
            found.append(keyword)
    return found[:5]


def _infer_domains(text: str, description_keywords: list[str]) -> list[str]:
    domains = []
    lowered = text.lower()
    if any(term in lowered for term in ["react", "frontend", "ui", "ux", "css", "html", "javascript", "typescript"]):
        domains.append("frontend")
    if any(term in lowered for term in ["python", "node", "api", "backend", "database", "sql", "fastapi", "django", "express"]):
        domains.append("backend")
    if any(term in lowered for term in ["data", "sql", "pandas", "spark", "warehouse", "etl", "analytics", "machine learning"]):
        domains.append("data")
    if any(term in lowered for term in ["aws", "azure", "gcp", "kubernetes", "docker", "terraform", "devops"]):
        domains.append("cloud/devops")
    if not domains:
        domains = list(dict.fromkeys(description_keywords[:3]))
    return domains[:5]


def build_resume_profile(text: str, file_name: str) -> dict:
    templates = get_profile_templates()
    vocabulary: list[str] = list(COMMON_KEYWORDS)
    title_vocabulary = list(ADDITIONAL_TITLE_KEYWORDS)
    ranked_templates = []
    for key, template in templates.items():
        titles = template.get("title_keywords", [])
        descriptions = template.get("description_keywords", [])
        title_vocabulary.extend(titles)
        vocabulary.extend(descriptions)
        score = 3 * len(find_hits(text, titles)) + len(find_hits(text, descriptions))
        ranked_templates.append((score, key, template))

    description_keywords = _ranked_hits(text, vocabulary)[:60]
    title_keywords = _ranked_hits(text, title_vocabulary)[:30]
    score, _, template = max(ranked_templates, default=(0, "", {}))
    name = re.sub(r"[_-]+", " ", file_name.rsplit(".", 1)[0]).strip().title()
    detected_keywords = title_keywords + description_keywords
    summary = template.get("summary", "") if score else ""
    if not summary:
        summary = f"Resume profile based on the detected skills: {', '.join(detected_keywords[:4]) or name}."

    years_experience = _infer_years_experience(text)
    seniority_level = _infer_seniority_level(text, years_experience)
    target_roles = _infer_target_roles(text, title_keywords)
    core_skills = list(dict.fromkeys(description_keywords[:8]))
    domains = _infer_domains(text, description_keywords)
    return {
        "label": template.get("label") if score else name or "Resume profile",
        "summary": summary,
        "title_keywords": title_keywords or template.get("title_keywords", [])[:10],
        "description_keywords": description_keywords,
        "target_roles": target_roles,
        "seniority_level": seniority_level,
        "years_experience": years_experience,
        "core_skills": core_skills,
        "domains": domains,
        "include_keywords": list(dict.fromkeys(title_keywords[:12] + description_keywords[:12])),
        "exclude_keywords": [],
        "preferred_locations": [],
        "remote_preference": False,
        "min_match_score": 4,
        "daily_apply_cap": 5,
        "active": True,
    }
