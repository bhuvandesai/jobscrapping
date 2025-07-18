# Comprehensive Job Scraper

A Python-based job scraping tool that collects Product Manager job postings (change the URL for different roles) from RemoteRocketship and LinkedIn, and uploads them to a Google Sheet for easy tracking and analysis.

## Features
- Scrapes Product Manager jobs from:
  - [RemoteRocketship](https://www.remoterocketship.com/)
  - [LinkedIn](https://www.linkedin.com/jobs/)
- Only collects jobs posted within the last 24 hours
- Avoids duplicate entries using a local seen-links file
- Uploads results directly to a specified Google Sheet
- Highly configurable via a simple `config.json` file

## Technologies Used
- Python 3
- [Playwright](https://playwright.dev/python/) (for browser automation)
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) (for HTML parsing)
- [gspread](https://gspread.readthedocs.io/) (for Google Sheets API)
- [oauth2client](https://github.com/googleapis/oauth2client) (for Google API authentication)

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name
```

### 2. Install Dependencies
It is recommended to use a virtual environment.
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Google Sheets API Credentials
- Create a Google Cloud project and enable the Google Sheets API and Google Drive API.
- Download your service account JSON key and place it in the project root (e.g., `cryptic-arc-288217-002de23e8527.json`).
- Share your target Google Sheet with the service account email.

### 4. Configuration
Edit `config.json` with your preferences:
```json
{
    "max_jobs": 10,
    "linkedin_email": "your_email@example.com",
    "linkedin_password": "your_password"
}
```
- **max_jobs**: Maximum jobs to fetch per source.
- **linkedin_email/password**: Your LinkedIn credentials (see Security Notes below).

### 5. Usage
Run the scraper:
```bash
python comprehensive_job_scraper.py
```
- The script will scrape jobs and append new ones to your Google Sheet.
- Duplicate jobs are avoided using `seen_links.txt`.

## Security Notes
- **Never commit your real LinkedIn credentials or Google API keys to a public repository!**
- Use environment variables or a `.env` file for sensitive data in production.
- This project is for educational/demo purposes only. Automated scraping of LinkedIn or other sites may violate their terms of service.

## Customization
- You can adjust the scraping logic or add new job sources by editing `comprehensive_job_scraper.py`.
- The script is currently set up for Product Manager jobs in India, but can be modified for other roles/locations.

## Contributing
Pull requests and suggestions are welcome! Please open an issue to discuss your ideas or report bugs.


## Disclaimer
This tool is for educational and demonstration purposes only. Use responsibly and respect the terms of service of the sites you scrape. 
