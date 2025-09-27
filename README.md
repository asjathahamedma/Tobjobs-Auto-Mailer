# **TopJobs.lk Automated Job Scraper & Applier**

This project is a comprehensive automation tool designed to streamline the job search process on TopJobs.lk. It automates the entire workflow: finding relevant job listings based on highly specific criteria, extracting contact information, and sending personalized email applications with a CV attached.

The system is built to be run on a schedule (e.g., once a day), saving significant time and effort while ensuring you never miss a relevant opportunity.

## **Key Features**

* **Multi-Category Scraping:** Scans multiple IT-related categories on TopJobs.lk to gather a wide range of listings.  
* **Advanced Combination Filtering:** Filters jobs with high precision by requiring a match from **both** an experience level keyword (e.g., "Junior", "Intern") AND a technical role keyword (e.g., "Cyber Security", "Network Engineer").  
* **Intelligent Memory:** Keeps track of jobs it has already processed in data/processed\_jobs.csv. It won't re-apply for the same job, but it will catch any matching jobs posted within the last 5 days that it might have missed.  
* **Dynamic Email Generation:** Avoids sending generic, repetitive emails. It dynamically constructs a unique, professional email for each application by mixing different phrases and sentences.  
* **Resume-Infused Content:** Automatically includes a professional summary and a full signature with contact details and portfolio links in every email.  
* **Detailed Logging & Summary:** Provides real-time feedback in the terminal and saves a detailed log file in the /logs directory. A complete summary is displayed after every run.  
* **Secure & Professional Structure:** Follows best practices by separating source code, data, and logs, and uses a .env file to keep credentials safe and out of the main codebase.

## **Project in Action**

Here is a live demo of the script running. It identifies new/missed jobs, extracts the contact details, sends personalized emails, and provides a final summary.

## **How It Works: The Automation Workflow**

The system is orchestrated by the run\_automation.py script, which executes a two-step process:

1. **Scrape (scraper.py):**  
   * Scans the target URLs from src/config.py.  
   * Gathers all jobs posted in the last 5 days.  
   * Filters these jobs against the keyword lists in src/config.py.  
   * Checks its "memory" (processed\_jobs.csv) to discard jobs it has already seen.  
   * Extracts the email address for new, matching jobs.  
   * Saves the results to a new timestamped CSV file in /data/leads/.  
2. **Apply (mailer.py):**  
   * Finds the most recent leads file created by the scraper.  
   * Loads your credentials securely from the .env file.  
   * For each job, it generates a unique email, attaches your CV, and sends the application.  
   * Updates the memory file (processed\_jobs.csv) with the jobs it just processed.

## **Project Structure**

For the script to work correctly, your project folder must be set up as follows. The setup guide below will help you create the missing files.

/JOB\_AUTO/  
├── assets/  
│   └── demo.gif  
├── data/  
│   └── leads/  
├── logs/  
├── src/  
│   ├── \_\_init\_\_.py  
│   ├── config.py  
│   ├── scraper.py  
│   ├── mailer.py  
│   └── utils.py  
├── .env  
├── Asjath-Ahamed-Mohamed-Aazath.pdf  
├── requirements.txt  
└── run\_automation.py

## **Setup and Installation Guide**

Follow these steps carefully to set up and run the project for the first time.

### **Prerequisites**

* [Python](https://www.python.org/downloads/) (version 3.9 or higher)  
* [Git](https://git-scm.com/downloads/)

### **Step 1: Clone the Repository**

Open your terminal or command prompt and run the following command to download the project:

git clone \[https://github.com/asjathahamedma/Tobjobs-Auto-Mailer.git\](https://github.com/asjathahamedma/Tobjobs-Auto-Mailer.git)  
cd Tobjobs-Auto-Mailer

### **Step 2: Create the Environment File (.env)**

This file will store your secret email credentials.

1. Create the file in the main project directory.  
   * In your terminal: touch .env (macOS/Linux) or echo. \> .env (Windows)  
2. Open the .env file and add the following content, replacing the placeholders with your information.  
   **IMPORTANT:** For Gmail, you must generate a 16-digit **App Password**. Your regular Google account password will not work and will result in an authentication error.  
   * Go to your Google Account \-\> Security \-\> 2-Step Verification (must be ON) \-\> App passwords.

\# Enter your Gmail address and your 16-digit Google App Password  
EMAIL\_ADDRESS="your-email@gmail.com"  
EMAIL\_PASSWORD="your-16-digit-app-password"

### **Step 3: Place Your CV**

Make sure your resume PDF file (e.g., Asjath-Ahamed-Mohamed-Aazath.pdf) is placed in the main project directory. If your filename is different, update it in src/config.py.

### **Step 4: Install Dependencies**

Install all the required Python packages by running:

pip install \-r requirements.txt

### **Step 5: Configure Your Search (Optional)**

Open **src/config.py**. This is your central control panel. You can easily edit the LEVEL\_KEYWORDS, ROLE\_KEYWORDS, your name, and your portfolio links to customize the automation for your needs without touching the core logic.

## **Usage**

To run the entire automation workflow, execute the master script from the main project directory:

python run\_automation.py

The script will:

* Automatically create the data/leads/ and logs/ folders if they don't exist.  
* Provide detailed real-time updates in your terminal.  
* Save a comprehensive log file to the /logs folder.  
* Display a final summary of its actions upon completion.

### **A Note on Security**

This project includes a .gitignore file to ensure that your sensitive information (.env file) and data/log files are **never** uploaded to a public GitHub repository. This is a critical security and best-practice measure.