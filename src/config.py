import copy
import json
import os
from pathlib import Path

from dotenv import dotenv_values


APP_CONFIG_FILE = "data/app_config.json"
TRACKING_FILE = "data/processed_jobs.csv"
STARTUP_STATE_FILE = "data/startup_state.json"
SCRAPER_STATE_FILE = "data/scraper_state.json"
FEEDBACK_DIR = "data/application_feedback"
APP_STATE_DB = "data/app_state.db"
ENV_FILE = ".env"


def get_code_root():
    env_root = os.environ.get("TOPJOBS_RESOURCE_DIR")
    if env_root:
        return Path(env_root)
    return Path.cwd()


def get_app_home():
    env_home = os.environ.get("TOPJOBS_APP_HOME")
    if env_home:
        return Path(env_home)
    return Path.cwd()


def absolute_in_app_home(relative_path):
    return str((get_app_home() / relative_path).resolve())


def resolve_existing_path(path_value):
    raw_value = (path_value or "").strip()
    if not raw_value:
        return ""

    candidate = Path(raw_value)
    if candidate.is_absolute():
        return str(candidate)

    app_path = get_app_home() / raw_value
    if app_path.exists():
        return str(app_path)

    code_path = get_code_root() / raw_value
    if code_path.exists():
        return str(code_path)

    return str(app_path)


def _profile_templates():
    return {
        "security": {
            "label": "Cybersecurity",
            "resume_path": "",
            "summary": (
                "This profile targets cybersecurity, network hardening, vulnerability assessment, "
                "and practical security operations roles."
            ),
            "title_keywords": [
                "cybersecurity",
                "cyber security",
                "penetration tester",
                "penetration testing",
                "pentester",
                "pentest",
                "security analyst",
                "soc analyst",
                "security engineer",
                "information security",
                "network security",
                "ethical hacker",
                "vapt",
                "security operations",
            ],
            "description_keywords": [
                "vulnerability assessment",
                "penetration testing",
                "owasp",
                "burp suite",
                "nmap",
                "wireshark",
                "incident response",
                "threat hunting",
                "siem",
                "splunk",
                "soc",
                "firewall",
                "ids",
                "ips",
                "kali linux",
                "security monitoring",
                "security controls",
            ],
        },
        "network": {
            "label": "Network Engineering",
            "resume_path": "",
            "summary": (
                "This profile targets network administration, infrastructure support, routing, "
                "switching, firewall configuration, and system reliability roles."
            ),
            "title_keywords": [
                "network engineer",
                "network administrator",
                "network operations",
                "noc engineer",
                "infrastructure engineer",
                "system administrator",
                "systems engineer",
                "network operations engineer",
            ],
            "description_keywords": [
                "routing",
                "switching",
                "cisco",
                "mikrotik",
                "tcp ip",
                "vpn",
                "dns",
                "dhcp",
                "lan",
                "wan",
                "fortigate",
                "juniper",
                "active directory",
                "windows server",
                "network troubleshooting",
                "ccna",
            ],
        },
        "frontend": {
            "label": "Frontend Development",
            "resume_path": "",
            "summary": (
                "This profile targets responsive frontend engineering, component-driven UI work, "
                "and modern JavaScript product development roles."
            ),
            "title_keywords": [
                "frontend",
                "front end",
                "frontend developer",
                "front end developer",
                "nextjs",
                "next js",
                "react",
                "reactjs",
                "ui developer",
                "ui engineer",
            ],
            "description_keywords": [
                "javascript",
                "typescript",
                "html",
                "css",
                "tailwind",
                "responsive design",
                "react",
                "next js",
                "nextjs",
                "ui ux",
                "component",
                "redux",
                "web performance",
                "accessibility",
            ],
        },
        "full_stack": {
            "label": "Full Stack / Backend Development",
            "resume_path": "",
            "summary": (
                "This profile targets full stack and backend development roles across APIs, "
                "databases, server-side services, and JavaScript-based web applications."
            ),
            "title_keywords": [
                "full stack",
                "fullstack",
                "backend",
                "back end",
                "backend developer",
                "back end developer",
                "full stack developer",
                "fullstack developer",
                "software engineer",
                "software developer",
                "web application developer",
                "mern",
                "node js",
                "nodejs",
                "api developer",
            ],
            "description_keywords": [
                "node",
                "express",
                "nestjs",
                "rest api",
                "graphql",
                "mongodb",
                "mysql",
                "postgresql",
                "sequelize",
                "prisma",
                "jwt",
                "authentication",
                "server side",
                "backend services",
                "microservices",
                "react",
                "next js",
                "nextjs",
                "full stack",
                "api integration",
            ],
        },
        "data_ai": {
            "label": "Data Science / AI-ML",
            "resume_path": "",
            "summary": (
                "This profile targets data science and AI/ML roles involving Python analysis, "
                "model development, machine learning, and practical data workflows."
            ),
            "title_keywords": [
                "data scientist",
                "data science",
                "machine learning",
                "ml engineer",
                "ai engineer",
                "ai ml developer",
                "artificial intelligence",
                "data analyst",
                "ai developer",
            ],
            "description_keywords": [
                "python",
                "pandas",
                "numpy",
                "scikit learn",
                "tensorflow",
                "pytorch",
                "machine learning",
                "deep learning",
                "nlp",
                "computer vision",
                "feature engineering",
                "model training",
                "data visualization",
                "power bi",
                "sql",
            ],
        },
    }


def _default_config():
    return {
        "scraper": {
            "level_keywords": [
                "intern",
                "associate",
                "junior",
                "entry level",
                "fresher",
                "assistant",
                "trainee",
            ],
            "excluded_title_keywords": [
                "it support",
                "technical support",
                "help desk",
                "service desk",
                "desktop support",
                "customer support",
                "support engineer",
                "support executive",
                "it executive",
            ],
            "excluded_seniority_keywords": [
                "senior",
                "lead",
                "manager",
                "head",
                "principal",
                "director",
                "architect",
            ],
            "recent_job_window_days": 2,
            "require_remote": False,
            "enable_ocr_for_ad_images": True,
            "ocr_languages": ["en"],
            "minimum_fit_score": 4,
            "category_urls": [
                "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=HNS&jst=OPEN",
                "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=SDQ&jst=OPEN",
            ],
        },
        "profiles": {},
        "mailer": {
            "your_name": "",
            "default_resume_path": "",
            "auth": {
                "sender_email": "",
                "app_password": "",
            },
            "contact_info": {
                "phone": "",
                "email": "",
                "portfolio": "",
                "linkedin": "",
                "github": "",
            },
        },
        "app": {
            "run_at_startup": False,
            "auto_run_on_launch": True,
            "start_minimized": False,
            "scan_only_mode": False,
            "startup_delay_seconds": 30,
            "theme": "ember-light",
        },
    }


def _deep_merge(base, override):
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def get_default_app_config():
    return copy.deepcopy(_default_config())


def get_profile_templates():
    return copy.deepcopy(_profile_templates())


def load_app_config():
    config = get_default_app_config()
    if not os.path.exists(APP_CONFIG_FILE):
        env_values = dotenv_values(ENV_FILE)
        config["mailer"]["auth"]["sender_email"] = env_values.get("EMAIL_ADDRESS", "") or ""
        config["mailer"]["auth"]["app_password"] = env_values.get("EMAIL_PASSWORD", "") or ""
        return config

    try:
        with open(APP_CONFIG_FILE, "r", encoding="utf-8") as file:
            user_config = json.load(file)
    except (OSError, json.JSONDecodeError):
        env_values = dotenv_values(ENV_FILE)
        config["mailer"]["auth"]["sender_email"] = env_values.get("EMAIL_ADDRESS", "") or ""
        config["mailer"]["auth"]["app_password"] = env_values.get("EMAIL_PASSWORD", "") or ""
        return config

    merged = _deep_merge(config, user_config)
    if merged["scraper"].get("recent_job_window_days") in (3, 5):
        merged["scraper"]["recent_job_window_days"] = 2
    env_values = dotenv_values(ENV_FILE)
    merged["mailer"]["auth"]["sender_email"] = (
        merged["mailer"]["auth"].get("sender_email")
        or env_values.get("EMAIL_ADDRESS", "")
        or ""
    )
    merged["mailer"]["auth"]["app_password"] = (
        merged["mailer"]["auth"].get("app_password")
        or env_values.get("EMAIL_PASSWORD", "")
        or ""
    )
    return merged


def save_app_config(config):
    os.makedirs(os.path.dirname(APP_CONFIG_FILE), exist_ok=True)
    with open(APP_CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=2)


_CONFIG = load_app_config()

LEVEL_KEYWORDS = _CONFIG["scraper"]["level_keywords"]
EXCLUDED_TITLE_KEYWORDS = _CONFIG["scraper"]["excluded_title_keywords"]
EXCLUDED_SENIORITY_KEYWORDS = _CONFIG["scraper"]["excluded_seniority_keywords"]
RECENT_JOB_WINDOW_DAYS = _CONFIG["scraper"]["recent_job_window_days"]
REQUIRE_REMOTE = _CONFIG["scraper"]["require_remote"]
ENABLE_OCR_FOR_AD_IMAGES = _CONFIG["scraper"]["enable_ocr_for_ad_images"]
OCR_LANGUAGES = _CONFIG["scraper"]["ocr_languages"]
MINIMUM_FIT_SCORE = _CONFIG["scraper"]["minimum_fit_score"]
CATEGORY_URLS = _CONFIG["scraper"]["category_urls"]

JOB_PROFILES = _CONFIG["profiles"]
PROFILE_TEMPLATES = get_profile_templates()
YOUR_NAME = _CONFIG["mailer"]["your_name"]
DEFAULT_RESUME_PATH = _CONFIG["mailer"]["default_resume_path"]
MAILER_AUTH = _CONFIG["mailer"].get("auth", {})
CONTACT_INFO = _CONFIG["mailer"]["contact_info"]

APP_SETTINGS = _CONFIG["app"]
