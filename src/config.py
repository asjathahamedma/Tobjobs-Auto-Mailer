# --- scraper.py CONFIGURATION ---

# Experience levels to search for
LEVEL_KEYWORDS = [
    'intern', 'associate', 'junior', 'entry level', 'fresher', 'assistant', 'trainee'
]

# Roles and skills based on your resume
ROLE_KEYWORDS = [
    'cyber security', 'network engineer', 'it administrator', 'system administrator', 
    'it support', 'security analyst', 'penetration tester', 'network security', 
    'devops', 'python', 'firewall', 'active directory', 'it executive','techops', 'technical support','cloud','frontend','nextjs','software'
]

# Roles that should be accepted regardless of the experience level mentioned
ROLES_WITHOUT_LEVEL_CHECK = [
    'it support',
    'it executive',
    'technical support'
]

# Set to True to only find jobs with "remote" in the title
REQUIRE_REMOTE = False

# Job category URLs to scrape
CATEGORY_URLS = [
    "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=HNS&jst=OPEN",
    "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=SDQ&jst=OPEN"
]

# File to track already processed jobs
TRACKING_FILE = 'data/processed_jobs.csv'


# --- mailer.py CONFIGURATION ---

# Your full name for the email signature
YOUR_NAME = "Asjath Ahamed Mohamed Aazath"

# Path to your resume file (relative to the main project folder)
CV_PATH = "Asjath-Ahamed-Mohamed-Aazath.pdf"

# Your contact and professional links for the signature
CONTACT_INFO = {
    "phone": "+94758218880",
    "email": "asjathahamedma@gmail.com",
    "portfolio": "https://asjath.xyz/",
    "linkedin": "https://www.linkedin.com/in/asjathahamedma",
    "github": "https://github.com/asjathahamedma"
}

# Short summary from your resume's profile section
RESUME_SUMMARY = "A dedicated Network Engineer with hands-on experience in configuring, securing, and optimizing network infrastructures, complemented by expertise in cybersecurity. Proficient in routing, switching, firewall management, and automation using Python and PowerShell."

