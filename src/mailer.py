import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import pandas as pd
import os
from dotenv import load_dotenv
import glob
import time
import random
import logging
from src.config import YOUR_NAME, CV_PATH, CONTACT_INFO, RESUME_SUMMARY

logger = logging.getLogger('JobAutomation')

def find_latest_leads_csv():
    """Finds the most recently created 'topjobs_leads_*.csv' file in the leads folder."""
    list_of_files = glob.glob(os.path.join("data", "leads", 'topjobs_leads_*.csv'))
    if not list_of_files:
        return None
    return max(list_of_files, key=os.path.getctime)

def generate_email_content(job_title):
    """Generates a semi-randomized, professional email body and subject."""
    openings = [
        "I am writing to express my keen interest in the",
        "I was excited to see the opening for the",
        "I am writing to apply for the recently advertised"
    ]
    alignments = [
        "With my hands-on experience in network engineering and a strong foundation in cybersecurity, I am confident that my skills align perfectly with the requirements of this role.",
        "My background in network configuration, security protocols, and system administration, as detailed in my resume, makes me a strong candidate for this position.",
        "Given my practical skills in automation with Python and ongoing studies in Data Science, I am eager to apply my technical and analytical abilities to this role."
    ]
    subject = f"Application for the {job_title} Position - {YOUR_NAME}"
    body = f"""
Dear Hiring Manager,

{random.choice(openings)} {job_title} position I saw advertised on TopJobs.lk.

{RESUME_SUMMARY} {random.choice(alignments)}

My resume, which is attached for your review, provides further detail on my qualifications and projects. I am particularly drawn to this opportunity and am eager to discuss how I can contribute to your team.

Thank you for your time and consideration.

Sincerely,

{YOUR_NAME}
{CONTACT_INFO['phone']} | {CONTACT_INFO['email']}
Portfolio: {CONTACT_INFO['portfolio']}
LinkedIn: {CONTACT_INFO['linkedin']}
GitHub: {CONTACT_INFO['github']}
"""
    return subject, body.strip()

def send_email(smtp_server, port, sender_email, password, receiver_email, subject, body, attachment_path):
    """Connects to the SMTP server and sends a single email with an attachment."""
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            message = MIMEMultipart()
            message["From"] = f"{YOUR_NAME} <{sender_email}>"
            message["To"] = receiver_email
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {os.path.basename(attachment_path)}")
            message.attach(part)
            server.sendmail(sender_email, receiver_email, message.as_string())
            logger.info(f" -> SUCCESS: Email sent to {receiver_email}")
            time.sleep(5)
            return True
    except FileNotFoundError:
        logger.error(f" -> ERROR: Attachment file not found at '{attachment_path}'.")
        return False
    except smtplib.SMTPAuthenticationError:
        logger.error(" -> ERROR: SMTP Authentication Failed. Check your .env file.")
        logger.error("    (Hint: For Gmail, you must use a 16-digit 'App Password'.)")
        return False
    except Exception as e:
        logger.error(f" -> ERROR: An unexpected error occurred: {e}")
        return False

def main():
    """Main function to read leads and send emails."""
    summary = {"emails_sent": 0, "errors": 0}
    load_dotenv()
    sender_email = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    
    if not sender_email or not password:
        logger.critical("CRITICAL: EMAIL_ADDRESS or EMAIL_PASSWORD not found in .env file.")
        summary["errors"] += 1
        return summary
        
    leads_csv_file = find_latest_leads_csv()
    if not leads_csv_file:
        logger.warning("No new 'topjobs_leads_*.csv' file found to process.")
        return summary
        
    logger.info(f"Found leads file to process: {leads_csv_file}")
    
    try:
        df = pd.read_csv(leads_csv_file)
        df_valid = df[df['email'].str.contains('@', na=False)].copy()
    except Exception as e:
        logger.error(f"Could not read or process CSV '{leads_csv_file}': {e}")
        summary["errors"] += 1
        return summary
        
    if df_valid.empty:
        logger.info("The leads file does not contain any valid emails to process.")
        return summary

    smtp_server = "smtp.gmail.com"
    port = 465

    for index, row in df_valid.iterrows():
        job_title = row['title']
        receiver_email = row['email']
        logger.info(f"\nProcessing application for: '{job_title}'")
        subject, body = generate_email_content(job_title)
        
        if send_email(smtp_server, port, sender_email, password, receiver_email, subject, body, CV_PATH):
            summary["emails_sent"] += 1
        else:
            summary["errors"] += 1
            
    return summary

