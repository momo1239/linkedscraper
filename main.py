#!/usr/bin/env python3

import os
import json
import time
import random
import logging
import argparse

from urllib.parse import unquote
from typing import List, Tuple, Optional

from pydantic import BaseModel
from playwright.sync_api import sync_playwright


USERNAME = os.environ.get("FACELIFT_USER")
PASSWORD = os.environ.get("FACELIFT_PASS")


VOYAGER_API_MAX = 900
VOYAGER_API_DEFAULT_COUNT = 12


class VoyagerSearchResult(BaseModel):
  firstName: Optional[str]
  lastName: Optional[str]
  occupation: Optional[str]
  objectUrn: Optional[str]
  entityUrn: Optional[str]
  publicIdentifier: Optional[str]


def main():
  logging.basicConfig(level='INFO')
  parser = argparse.ArgumentParser(description='performs scraping of LinkedIn users')
  parser.add_argument('company', help="the target LinkedIn identifier")
  parser.add_argument('-o', '--output', required=False, help="optional output file")
  parser.add_argument('--noheadless', required=False, default=True, action='store_false', help='if set, will run with GUI')
  args = vars(parser.parse_args())

  company = args['company']
  people = []

  if not USERNAME or not PASSWORD:
    logging.fatal("Username/password not configured correctly. See README.")
    exit(1)

  with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=args['noheadless'])
    page = browser.new_page()

    try:
      # Go to login page
      page.goto("https://www.linkedin.com/login")
      # Input credentials
      page.type("#username", USERNAME)
      page.type("#password", PASSWORD)
      # Click to trigger login
      page.click("button[type=submit]")
      # Wait for navigation to home page
      page.wait_for_url("**/feed/", timeout=60000)
      page.goto(f"https://www.linkedin.com/company/{args['company']}/people")
    except Exception:
      logging.fatal("Could not authenticate to LinkedIn. Try running with --noheadless")
      exit(1)

    # Grab all of the data
    company_name = page.text_content('h1.org-top-card-summary__title').strip()
    logging.info(f"Company name: {company_name}")

    # Scroll down until you reach the max
    for i in range(0, VOYAGER_API_MAX, VOYAGER_API_DEFAULT_COUNT):
      logging.info("%d/%d" % (i, VOYAGER_API_MAX))
      page.keyboard.down('End')
      time.sleep(random.randint(10,15))

    data = page.evaluate('[...document.querySelectorAll(".org-people-profile-card__profile-info a")].map(e => [e.innerText, e.href]).filter(e => e[0] != "")')
    page.close()
    browser.close()

  if len(data) == 0:
    logging.fatal("Failed to collect any results. Try running with --noheadless")

  people = []
  for entry in data:
    name, url = entry
    publicIdentifier = unquote(url.split('https://www.linkedin.com/in/')[1].split('/')[0].split('?')[0])
    people.append(
      VoyagerSearchResult(
        firstName=name, 
        publicIdentifier=publicIdentifier
      )
    )

  output = json.dumps({
    "company": company_name,
    "profiles": [person.dict() for person in people],
    "facets": {}, # for backward compatibility with 1.0
    "numEmployees": 0, # for backward compatibility with 1.0
  })

  if args['output']:
    with open(args['output'], 'w') as handle:
      handle.write(output)
    logging.info(f"Wrote results to: {args['output']}")
  else:
    print(output)


if __name__ == '__main__':
  main()
