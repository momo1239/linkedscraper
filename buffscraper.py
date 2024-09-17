#!/usr/bin/env python3

import os
import json
import time
import random
import logging
import argparse
from urllib.parse import unquote
from playwright.sync_api import sync_playwright

# Get LinkedIn credentials from environment variables
USER = os.getenv("LINKEDIN_USER")
PASS = os.getenv("LINKEDIN_PASS")

# Set the max number of scrolls and profiles per scroll
MAX_SCROLLS = 900
PROFILES_PER_SCROLL = 12

def scrape_linkedin(company, output_file=None):
    # Check if credentials are set
    if not USER or not PASS:
        logging.error("Credentials missing. Set LINKEDIN_USER and LINKEDIN_PASS environment variables.")
        return

    # Launch browser and login
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Login to LinkedIn
            page.goto("https://www.linkedin.com/login")
            page.fill("#username", USER)
            page.fill("#password", PASS)
            page.click("button[type=submit]")
            page.wait_for_url("**/feed/", timeout=60000)

            # Navigate to the company people page
            page.goto(f"https://www.linkedin.com/company/{company}/people")
            time.sleep(3)

        except Exception as e:
            logging.error(f"Login failed: {e}")
            browser.close()
            return

        # Scroll and collect profiles
        for scroll in range(0, MAX_SCROLLS, PROFILES_PER_SCROLL):
            logging.info(f"Scrolling... {scroll}/{MAX_SCROLLS}")
            page.keyboard.press("End")
            time.sleep(random.uniform(10, 15))

        # Extract names and profile URLs
        profiles = page.evaluate("""
            [...document.querySelectorAll('.org-people-profile-card__profile-info a')]
            .map(el => [el.innerText, el.href])
            .filter(entry => entry[0] !== "")
        """)

        browser.close()

    if not profiles:
        logging.error("No profiles found.")
        return

    # Process and format the data
    employees = [
        {"name": name, "profile_id": unquote(url.split('/in/')[1].split('/')[0].split('?')[0])}
        for name, url in profiles
    ]

    # Prepare the output
    result = {
        "company": company,
        "employees": employees
    }

    # Save to file or print output
    if output_file:
        with open(output_file, 'w') as file:
            json.dump(result, file, indent=2)
        logging.info(f"Results saved to {output_file}")
    else:
        print(json.dumps(result, indent=2))

def main():
    # Command-line argument parser
    parser = argparse.ArgumentParser(description="LinkedIn Company People Scraper")
    parser.add_argument('company', help="LinkedIn company identifier")
    parser.add_argument('-o', '--output', help="Optional output file for saving results")
    args = parser.parse_args()

    # Start scraping
    scrape_linkedin(args.company, args.output)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
