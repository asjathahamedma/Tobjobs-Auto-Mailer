import copy


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




def get_profile_templates():
    return copy.deepcopy(_profile_templates())


LEVEL_KEYWORDS = ["intern", "associate", "junior", "entry level", "fresher", "assistant", "trainee"]
EXCLUDED_TITLE_KEYWORDS = [
    "it support", "technical support", "help desk", "service desk", "desktop support",
    "customer support", "support engineer", "support executive", "it executive",
]
EXCLUDED_SENIORITY_KEYWORDS = ["senior", "lead", "manager", "head", "principal", "director", "architect"]
RECENT_JOB_WINDOW_DAYS = 2
REQUIRE_REMOTE = False
ENABLE_OCR_FOR_AD_IMAGES = False
OCR_LANGUAGES = ["en"]
MINIMUM_FIT_SCORE = 4
CATEGORY_URLS = [
    "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=HNS&jst=OPEN",
    "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=SDQ&jst=OPEN",
]
JOB_PROFILES = {}
DEFAULT_RESUME_PATH = ""
TRACKING_FILE = ""
