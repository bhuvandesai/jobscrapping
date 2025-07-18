import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import sync_playwright
import time
import json
import os
from datetime import datetime, timedelta
import re

"""
Config file format (config.json):
{
    "max_jobs": 50,
    "linkedin_email": "your_email@example.com",
    "linkedin_password": "your_password"
}
"""

def normalize_link(link):
    # Normalize job link for deduplication
    return link.rstrip('/').strip().lower() if link else ''

def is_within_24_hours(time_text, source="linkedin"):
    """Check if job posting is within 24 hours for different sources"""
    if not time_text:
        if source == "linkedin":
            return True
        return False
    time_text = time_text.lower()
    if source == "linkedin":
        if any(x in time_text for x in ['hour', 'hr', 'h']):
            hours_match = re.search(r'(\d+)\s*(?:hour|hr|h)', time_text)
            if hours_match:
                hours = int(hours_match.group(1))
                return hours <= 24
        if any(x in time_text for x in ['today', 'yesterday', 'posted', 'recent']):
            return True
        return True
    if source == "remoterocketship":
        if any(x in time_text for x in ['yesterday', 'today', 'recent', 'new']):
            return True
        if any(x in time_text for x in ['posted', 'ago', 'recent']):
            return True
        return True
    return False

# === Script Start ===
print("=== Starting Comprehensive Job Scraper ===")
print(f"Start time: {datetime.now()}")

# --- Load configuration from config.json ---
config_path = "config.json"
default_max_jobs = 50
max_jobs = default_max_jobs
linkedin_credentials = {}
if os.path.exists(config_path):
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            max_jobs = int(config.get("max_jobs", default_max_jobs))
            linkedin_credentials = {
                "email": config.get("linkedin_email", ""),
                "password": config.get("linkedin_password", "")
            }
    except Exception as e:
        print(f"Warning: Could not read config.json, using default max_jobs={default_max_jobs}. Error: {e}")

# --- Set up Google Sheets connection ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("cryptic-arc-288217-002de23e8527.json", scope)
client = gspread.authorize(creds)

SHEET_ID = "1xxgA9XrpkvhNEoq5YWo52VNXAN4UXzmDkw1bBCTnH3U"
SHEET_NAME = "Sheet1"

# Open the target worksheet
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# --- Load previously seen job links to avoid duplicates ---
seen_links_path = "seen_links.txt"
seen_links = set()
if os.path.exists(seen_links_path):
    try:
        with open(seen_links_path, 'r') as f:
            for line in f:
                seen_links.add(line.strip())
    except Exception as e:
        seen_links = set()

# --- Scraper for RemoteRocketship jobs ---
def scrape_remoterocketship():
    jobs = []
    page_num = 1
    max_pages = 5
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        while len(jobs) < max_jobs and page_num <= max_pages:
            # Build URL for each page of Product Manager jobs in India
            url = f"https://www.remoterocketship.com/country/india/jobs/product-manager?page={page_num}&sort=DateAdded&jobTitle=Product+Manager&locations=India"
            try:
                page.goto(url, timeout=30000)
                # Wait for job cards to load using multiple possible selectors
                try:
                    page.wait_for_selector('div.relative.cursor-pointer', timeout=10000)
                except:
                    try:
                        page.wait_for_selector('[data-testid="job-card"]', timeout=5000)
                    except:
                        try:
                            page.wait_for_selector('.job-card', timeout=5000)
                        except:
                            break
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                # Detect login wall and stop if encountered
                login_form = soup.find("form", {"action": lambda x: x and "login" in x.lower()})
                login_button = soup.find("button", string=lambda x: x and "log in" in x.lower())
                signup_button = soup.find("button", string=lambda x: x and "sign up" in x.lower())
                login_input = soup.find("input", {"type": "password"})
                login_page_indicators = [
                    soup.find("h1", string=lambda x: x and "log in" in x.lower()),
                    soup.find("h1", string=lambda x: x and "sign in" in x.lower()),
                    soup.find("div", {"class": "login-form"}),
                    soup.find("div", {"id": "login"}),
                    soup.find("div", {"class": "auth-form"}),
                    "vercel security checkpoint" in html.lower(),
                    "please log in to continue" in html.lower(),
                    "sign in to continue" in html.lower(),
                    "login to view" in html.lower(),
                    "sign up to view" in html.lower(),
                    "authentication required" in html.lower(),
                    "please authenticate" in html.lower()
                ]
                if (login_form or login_button or signup_button or login_input or 
                    any(login_page_indicators)):
                    print("RemoteRocketship: Login/Signup page detected. Stopping scraping.")
                    break
                # Find all job cards using multiple selectors
                cards = soup.find_all("div", class_="relative cursor-pointer")
                if not cards:
                    cards = soup.find_all("div", attrs={"data-testid": "job-card"})
                if not cards:
                    cards = soup.find_all("div", class_="job-card")
                if not cards:
                    cards = soup.find_all("div", class_="cursor-pointer")
                if not cards:
                    break
                for card in cards:
                    # Extract job title and link from card
                    title = ""
                    link = ""
                    h3 = card.find("h3", class_="text-lg")
                    if h3:
                        a_tag = h3.find("a", href=True)
                        if a_tag:
                            title = a_tag.get_text(strip=True)
                            link = a_tag["href"]
                    if not title or not link:
                        h3_alt = card.find("h3")
                        if h3_alt:
                            a_tag = h3_alt.find("a", href=True)
                            if a_tag:
                                title = a_tag.get_text(strip=True)
                                link = a_tag["href"]
                    if not title or not link:
                        a_tag = card.find("a", href=True)
                        if a_tag:
                            title = a_tag.get_text(strip=True)
                            link = a_tag["href"]
                    if link and not link.startswith("http"):
                        link = "https://www.remoterocketship.com" + link
                    # Extract company name
                    company = ""
                    h4 = card.find("h4", class_="text-md")
                    if h4:
                        company_a = h4.find("a")
                        if company_a:
                            company = company_a.get_text(strip=True)
                    if not company:
                        company_elem = card.find("div", class_="text-sm") or card.find("span", class_="text-sm")
                        if company_elem:
                            company = company_elem.get_text(strip=True)
                    # Extract posting time
                    time_elem = card.find("p", class_="text-sm")
                    posting_time = time_elem.get_text(strip=True) if time_elem else ""
                    norm_link = normalize_link(link)
                    # Add job if not seen and within 24 hours
                    if title and company and link and norm_link not in seen_links:
                        if is_within_24_hours(posting_time, "remoterocketship"):
                            jobs.append([title, company, link, "RemoteRocketship", posting_time])
                            seen_links.add(norm_link)
                            if len(jobs) >= max_jobs:
                                break
                    page_num += 1
                    time.sleep(3)
            except Exception as e:
                break
        browser.close()
    return jobs

# --- Scraper for LinkedIn jobs (requires login) ---
def scrape_linkedin():
    jobs = []
    # Skip if credentials are not provided
    if not linkedin_credentials.get("email") or not linkedin_credentials.get("password"):
        print("LinkedIn credentials not provided in config.json. Skipping LinkedIn scraping.")
        return jobs
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # Log in to LinkedIn
            page.goto("https://www.linkedin.com/login", timeout=60000)
            page.fill("#username", linkedin_credentials["email"])
            page.fill("#password", linkedin_credentials["password"])
            page.click("button[type='submit']")
            try:
                page.wait_for_load_state("networkidle", timeout=30000)
                # Check for successful login
                if page.query_selector(".global-nav") or page.query_selector("[data-test-id='nav-logo']"):
                    pass
                else:
                    error_elem = page.query_selector(".alert-error, .error, [data-test-id='login-error']")
                    if error_elem:
                        error_text = error_elem.inner_text()
                        print(f"LinkedIn - Login error: {error_text}")
                        return jobs
            except Exception as e:
                pass
            # Go to LinkedIn job search page for Product Manager, Remote, last 24 hours
            search_url = "https://www.linkedin.com/jobs/search/?keywords=product%20manager&location=Remote&f_TPR=r86400&f_WT=2"
            try:
                page.goto(search_url, timeout=60000)
                # Try multiple selectors to find job cards
                job_cards_found = False
                selectors_to_try = [
                    ".job-search-card",
                    "[data-job-id]",
                    ".job-card-container",
                    ".job-card",
                    ".jobs-search__results-list li",
                    ".jobs-search-results__list-item"
                ]
                for selector in selectors_to_try:
                    try:
                        page.wait_for_selector(selector, timeout=10000)
                        job_cards_found = True
                        break
                    except:
                        continue
                if not job_cards_found:
                    return jobs
                # Scroll to load more jobs
                for scroll_num in range(5):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                # Extract job cards from the page
                job_cards = []
                for selector in selectors_to_try:
                    job_cards = page.query_selector_all(selector)
                    if job_cards:
                        break
                if not job_cards:
                    return jobs
                for card in job_cards:
                    # Extract job title
                    title_selectors = [
                        ".job-search-card__title",
                        ".job-card-container__link",
                        ".job-card-container__title",
                        "h3",
                        "a[data-control-name='job_card_click']",
                        ".job-card-list__title"
                    ]
                    # Extract company name
                    company_selectors = [
                        ".job-search-card__subtitle",
                        ".job-card-container__company-name",
                        ".job-card-container__subtitle",
                        "[data-test-id='job-card-company-name']",
                        ".job-search-card__company-name",
                        ".job-card-list__company-name"
                    ]
                    # Extract posting time
                    time_selectors = [
                        ".job-search-card__listdate",
                        ".job-card-container__listdate",
                        ".job-card-list__date",
                        ".job-search-card__time-badge",
                        ".job-card-container__time-badge",
                        ".job-card-list__time-badge",
                        "[data-test-id='job-card-posted-time']",
                        ".job-search-card__time",
                        ".job-card-container__time"
                    ]
                    title = ""
                    for selector in title_selectors:
                        title_elem = card.query_selector(selector)
                        if title_elem:
                            title = title_elem.inner_text().strip()
                            if title:
                                break
                    company = ""
                    for selector in company_selectors:
                        company_elem = card.query_selector(selector)
                        if company_elem:
                            company = company_elem.inner_text().strip()
                            if company:
                                break
                    link_elem = card.query_selector("a")
                    link = link_elem.get_attribute("href") if link_elem else ""
                    posting_time = ""
                    for selector in time_selectors:
                        time_elem = card.query_selector(selector)
                        if time_elem:
                            posting_time = time_elem.inner_text().strip()
                            if posting_time:
                                break
                    # Fallback: try to extract company from job URL if not found
                    if not company and link:
                        if "at-" in link:
                            url_parts = link.split("at-")
                            if len(url_parts) > 1:
                                company_from_url = url_parts[1].split("?")[0].split("-")[0]
                                if company_from_url:
                                    company = company_from_url.title()
                    if link and not link.startswith("http"):
                        link = "https://www.linkedin.com" + link
                    norm_link = normalize_link(link)
                    # Add job if not seen and within 24 hours
                    if title and company and link and norm_link not in seen_links:
                        if is_within_24_hours(posting_time, "linkedin"):
                            jobs.append([title, company, link, "LinkedIn", posting_time])
                            seen_links.add(norm_link)
                            if len(jobs) >= max_jobs:
                                break
                    else:
                        if norm_link in seen_links:
                            pass
                        else:
                            pass
            except Exception as e:
                pass
        except Exception as e:
            pass
        browser.close()
    return jobs

# --- Main scraping logic ---
all_jobs = []

# Scrape jobs from RemoteRocketship
print("Scraping RemoteRocketship...")
start_time = time.time()
remoterocketship_jobs = scrape_remoterocketship()
remoterocketship_time = time.time() - start_time
all_jobs.extend(remoterocketship_jobs)
print(f"Found {len(remoterocketship_jobs)} jobs from RemoteRocketship (took {remoterocketship_time:.2f} seconds)")

# Scrape jobs from LinkedIn
print("Scraping LinkedIn...")
start_time = time.time()
linkedin_jobs = scrape_linkedin()
linkedin_time = time.time() - start_time
all_jobs.extend(linkedin_jobs)
print(f"Found {len(linkedin_jobs)} jobs from LinkedIn (took {linkedin_time:.2f} seconds)")

# Limit each source to max_jobs to prevent any single source from dominating
if len(remoterocketship_jobs) > max_jobs:
    remoterocketship_jobs = remoterocketship_jobs[:max_jobs]
if len(linkedin_jobs) > max_jobs:
    linkedin_jobs = linkedin_jobs[:max_jobs]

# Combine jobs from both sources
all_jobs = remoterocketship_jobs + linkedin_jobs

# --- Upload jobs to Google Sheets and update seen links ---
if all_jobs:
    # Ensure header exists in the sheet
    existing_rows = sheet.get_all_values()
    if not existing_rows or existing_rows[0] != ['Title', 'Company', 'Apply Link', 'Source', 'Posted']:
        sheet.clear()
        sheet.append_row(['Title', 'Company', 'Apply Link', 'Source', 'Posted'])
    # Append all new jobs
    sheet.append_rows(all_jobs)
    try:
        with open(seen_links_path, 'a') as f:
            for job in all_jobs:
                f.write(normalize_link(job[2]) + '\n')
    except Exception as e:
        print(f"Error updating seen links file: {e}")

# --- Final summary output ---
print(f"Appended {len(all_jobs)} new jobs to Google Sheet: {SHEET_NAME}")
print(f"Total jobs scraped: {len(all_jobs)}")
print(f"  - RemoteRocketship: {len(remoterocketship_jobs)} (took {remoterocketship_time:.2f}s)")
print(f"  - LinkedIn: {len(linkedin_jobs)} (took {linkedin_time:.2f}s)")
print(f"Total execution time: {time.time() - start_time:.2f} seconds")
print(f"End time: {datetime.now()}")
print("=== Comprehensive Job Scraper Completed ===") 