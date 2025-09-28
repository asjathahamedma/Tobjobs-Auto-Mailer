import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import logging
from src.config import (
    CATEGORY_URLS,
    LEVEL_KEYWORDS,
    ROLE_KEYWORDS,
    ROLES_WITHOUT_LEVEL_CHECK,
    REQUIRE_REMOTE,
    TRACKING_FILE
)

# Get the logger instance configured in other parts of the project
# If running this file standalone, basic logging will be used.
logger = logging.getLogger('JobAutomation')

def load_processed_jobs(filename):
    """Loads the set of already processed job URLs from the tracking file."""
    if not os.path.exists(filename):
        return set()
    try:
        df = pd.read_csv(filename)
        return set(df['url'])
    except pd.errors.EmptyDataError:
        return set()

def save_processed_jobs(filename, url_set):
    """Saves the updated set of processed job URLs to the tracking file."""
    # Ensure the directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    df = pd.DataFrame(list(url_set), columns=['url'])
    df.to_csv(filename, index=False)

def get_job_links(category_url):
    """Scrapes a category page for job links, titles, and their posting dates."""
    logger.info(f"Fetching job links from: {category_url}")
    job_details = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(category_url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        job_rows = soup.find_all('tr', id=re.compile(r'^tr\d+'))
        if not job_rows:
            logger.info(f" -> No job rows found in this category.")
            return []

        for row in job_rows:
            onclick_attr = row.get('onclick')
            cells = row.find_all('td')
            if not onclick_attr or len(cells) < 5:
                continue

            date_str = cells[4].text.strip()
            try:
                post_date = datetime.strptime(date_str, '%a %b %d %Y').date()
            except ValueError:
                continue

            match = re.search(r"createAlert\('(\d+)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'", onclick_attr)
            if match:
                rid, ac, jc, ec = match.groups()
                base_url = "https://www.topjobs.lk"
                job_url = f"{base_url}/employer/JobAdvertismentServlet?rid={rid}&ac={ac}&jc={jc}&ec={ec}"
                title_tag = row.find('h2')
                job_title = title_tag.text.strip() if title_tag else "No Title"
                job_details.append({"title": job_title, "url": job_url, "date": post_date})
        
        logger.info(f" -> Found {len(job_details)} jobs in this category.")
        return job_details
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching category page: {e}")
        return []

def extract_info_from_ad(job_url):
    """Extracts email from a job page, primarily by looking for plain text."""
    try:
        response = requests.get(job_url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        email_input_tag = soup.find('input', id='txtAVECompanyEmail')
        if email_input_tag and email_input_tag.get('value'):
            email = email_input_tag['value']
            logger.info(f" -> SUCCESS: Found plain text email: {email}")
            return {"url": job_url, "email": email}
        
        logger.warning(" -> No plain text email found for this job.")
        return {"url": job_url, "email": "Not Found"}

    except Exception as e:
        logger.error(f" -> An unexpected error occurred while extracting info: {e}")
        return None

def main():
    """Main function to run the scraper module."""
    summary = {"total_found": 0, "matching_criteria": 0, "new_leads_found": 0, "errors": 0}
    processed_urls = load_processed_jobs(TRACKING_FILE)
    logger.info(f"Loaded {len(processed_urls)} previously processed jobs from '{TRACKING_FILE}'.")
    
    all_jobs_details = []
    unique_urls = set()
    for url in CATEGORY_URLS:
        jobs_from_category = get_job_links(url)
        for job in jobs_from_category:
            if job['url'] not in unique_urls:
                all_jobs_details.append(job)
                unique_urls.add(job['url'])
        time.sleep(1)
    
    summary["total_found"] = len(all_jobs_details)
    logger.info("-" * 50)
    logger.info(f"Collected {summary['total_found']} unique jobs. Applying filters...")

    today = datetime.now().date()
    start_date = today - timedelta(days=5)
    
    jobs_to_process = []
    for job in all_jobs_details:
        title_lower = job['title'].lower()
        
        is_match = False
        matched_role = None
        for role in ROLE_KEYWORDS:
            if role in title_lower:
                matched_role = role
                break
        
        if matched_role:
            is_exception = matched_role in ROLES_WITHOUT_LEVEL_CHECK
            has_level_keyword = any(level in title_lower for level in LEVEL_KEYWORDS)
            
            if is_exception or has_level_keyword:
                is_match = True
        
        if REQUIRE_REMOTE:
            is_match = is_match and 'remote' in title_lower

        if is_match:
            summary["matching_criteria"] += 1
            if start_date <= job['date'] <= today and job['url'] not in processed_urls:
                logger.info(f"  [MATCH FOUND] New job from {job['date']}: {job['title']}")
                jobs_to_process.append(job)

    summary["new_leads_found"] = len(jobs_to_process)
    if not jobs_to_process:
        logger.info("\nNo new jobs found within the last 5 days that match your criteria.")
        return summary
        
    # ⭐ THIS IS THE CORRECTED LINE ⭐
    logger.info(f"\nFound {summary['new_leads_found']} jobs to process. Starting extraction...")
    logger.info("-" * 50)

    final_job_data = []
    newly_processed_urls = set()
    for i, job in enumerate(jobs_to_process):
        logger.info(f"Processing ({i+1}/{len(jobs_to_process)}): {job['title']}")
        data = extract_info_from_ad(job['url'])
        if data:
            data['title'] = job['title']
            final_job_data.append(data)
            newly_processed_urls.add(job['url'])
        time.sleep(1)

    if final_job_data:
        leads_dir = os.path.join("data", "leads")
        os.makedirs(leads_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = os.path.join(leads_dir, f'topjobs_leads_{timestamp}.csv')
        
        df = pd.DataFrame(final_job_data)
        df = df[['title', 'email', 'url']] 
        df.to_csv(filename, index=False, encoding='utf-8')
        logger.info(f"\nSaved {len(df)} new job leads to '{filename}'")
        
        updated_processed_urls = processed_urls.union(newly_processed_urls)
        save_processed_jobs(TRACKING_FILE, updated_processed_urls)
        logger.info(f"Updated '{TRACKING_FILE}' with {len(newly_processed_urls)} new jobs.")
    
    return summary

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()