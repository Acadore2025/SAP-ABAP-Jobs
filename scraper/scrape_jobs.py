"""
============================================================
AcadoreSkills — SAP ABAP Job Scraper
============================================================
Scrapes SAP ABAP jobs from Google Jobs using JobSpy
and saves them to Google Sheets automatically.

Runs daily via GitHub Actions at 7:00 AM IST.
Cost: $0

SETUP INSTRUCTIONS:
See README.md for full step-by-step guide.
============================================================
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

# ── Third-party (installed via requirements.txt) ──────────
try:
    import gspread
    from google.oauth2.service_account import Credentials
    from jobspy import scrape_jobs
    import pandas as pd
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)


# ============================================================
# ✅ CONFIG — edit these to customise your scraper
# ============================================================
CONFIG = {
    # Search terms — JobSpy searches these on Google Jobs
    "search_terms": [
        "SAP ABAP Developer",
        "SAP ABAP Consultant",
        "SAP ABAP Fresher",
        "SAP ABAP Senior",
        "ABAP HANA Developer",
        "SAP Fiori ABAP",
    ],

    # Location to search in
    "location": "India",

    # How many results to fetch per search term
    "results_per_term": 15,

    # Only scrape Google Jobs (safest, legal, no ToS issues)
    "sources": ["google"],

    # Your Google Sheet name (must match exactly)
    "sheet_name": "AcadoreSkills Jobs",

    # Worksheet/tab name inside the sheet
    "worksheet_name": "Jobs",

    # How many days old a job can be before we skip it
    "max_age_days": 30,
}
# ============================================================


def get_google_sheet():
    """
    Connect to Google Sheets using service account credentials.
    Credentials come from GitHub Secrets (GOOGLE_CREDENTIALS env var).
    """
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise EnvironmentError(
            "❌ GOOGLE_CREDENTIALS environment variable not set.\n"
            "Add it as a GitHub Secret. See README.md for instructions."
        )

    creds_dict = json.loads(creds_json)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)

    try:
        sheet = client.open(CONFIG["sheet_name"])
    except gspread.SpreadsheetNotFound:
        raise ValueError(
            f"❌ Google Sheet '{CONFIG['sheet_name']}' not found.\n"
            "Make sure you:\n"
            "1. Created a sheet with that exact name\n"
            "2. Shared it with your service account email"
        )

    try:
        worksheet = sheet.worksheet(CONFIG["worksheet_name"])
    except gspread.WorksheetNotFound:
        print(f"⚠️  Worksheet '{CONFIG['worksheet_name']}' not found — creating it...")
        worksheet = sheet.add_worksheet(
            title=CONFIG["worksheet_name"], rows=1000, cols=20
        )

    return worksheet


def ensure_headers(worksheet):
    """
    Make sure the sheet has the correct column headers.
    Only writes headers if row 1 is empty.
    """
    headers = [
        "ID",
        "Title",
        "Company",
        "Location",
        "Work Type",
        "Level",
        "Salary",
        "Tags",
        "Description (Short)",
        "Apply URL",
        "Source",
        "Date Posted",
        "Date Added",
        "Status",
        "Featured",
    ]
    first_row = worksheet.row_values(1)
    if not first_row or first_row[0] != "ID":
        print("📋 Writing headers to sheet...")
        worksheet.insert_row(headers, index=1)
        # Bold the header row
        worksheet.format("A1:O1", {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.17, "green": 0.11, "blue": 0.41},
        })
    return headers


def get_existing_urls(worksheet):
    """
    Fetch all Apply URLs already in the sheet to avoid duplicates.
    """
    try:
        all_values = worksheet.get_all_values()
        if len(all_values) <= 1:
            return set()
        # Apply URL is column 10 (index 9)
        return {row[9] for row in all_values[1:] if len(row) > 9 and row[9]}
    except Exception as e:
        print(f"⚠️  Could not fetch existing URLs: {e}")
        return set()


def derive_work_type(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    if any(w in text for w in ["remote", "work from home", "wfh", "anywhere"]):
        return "Remote"
    if "hybrid" in text:
        return "Hybrid"
    return "On-site"


def derive_level(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    if any(w in text for w in ["fresher", "trainee", "entry level", "graduate", "0-1", "0 to 1"]):
        return "Fresher"
    if any(w in text for w in ["senior", "lead", "principal", "architect", "manager", "head"]):
        return "Senior"
    if any(w in text for w in ["junior", "1-3", "1 to 3"]):
        return "Junior"
    return "Mid-level"


def derive_tags(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    known = [
        "ABAP OOP", "Fiori", "UI5", "OData", "BAPI", "BADI",
        "CDS Views", "S/4HANA", "ALV", "SmartForms", "BDC",
        "Module Pool", "RFC", "IDocs", "AMDP", "BTP",
        "SAP PI", "SAP PO", "RAP", "Enhancement Framework",
    ]
    matched = [tag for tag in known if tag.lower() in text]
    return ", ".join(matched[:6]) if matched else "SAP ABAP"


def format_salary(row) -> str:
    min_sal = getattr(row, "min_amount", None)
    max_sal = getattr(row, "max_amount", None)
    currency = getattr(row, "currency", "INR") or "INR"

    if pd.isna(min_sal) and pd.isna(max_sal):
        return "Not disclosed"

    symbol = "₹" if currency in ["INR", "Rs"] else currency + " "

    def fmt(n):
        if pd.isna(n):
            return None
        n = float(n)
        if currency == "INR":
            lpa = n / 100000
            return f"{symbol}{lpa:.1f} LPA"
        return f"{symbol}{n:,.0f}"

    if not pd.isna(min_sal) and not pd.isna(max_sal):
        return f"{fmt(min_sal)} – {fmt(max_sal)}"
    if not pd.isna(min_sal):
        return f"From {fmt(min_sal)}"
    return f"Up to {fmt(max_sal)}"


def clean_text(text, max_len=300) -> str:
    if not text or (isinstance(text, float)):
        return ""
    text = str(text).strip()
    text = re.sub(r'\s+', ' ', text)
    return text[:max_len] + "..." if len(text) > max_len else text


def scrape_all_terms(existing_urls: set) -> list:
    """
    Loop through each search term, scrape Google Jobs,
    and return cleaned job rows ready for the sheet.
    """
    all_rows = []
    seen_urls = set(existing_urls)

    for term in CONFIG["search_terms"]:
        print(f"\n🔍 Searching: '{term}' in {CONFIG['location']}...")
        try:
            jobs_df = scrape_jobs(
                site_name=CONFIG["sources"],
                search_term=term,
                location=CONFIG["location"],
                results_wanted=CONFIG["results_per_term"],
                hours_old=CONFIG["max_age_days"] * 24,
                country_indeed="India",
            )

            if jobs_df is None or jobs_df.empty:
                print(f"   ⚠️  No results for '{term}'")
                continue

            print(f"   ✅ Found {len(jobs_df)} jobs")

            for _, row in jobs_df.iterrows():
                apply_url = str(getattr(row, "job_url", "") or "")

                # Skip duplicates
                if apply_url in seen_urls or not apply_url:
                    continue
                seen_urls.add(apply_url)

                title       = clean_text(getattr(row, "title", "SAP ABAP Developer"))
                company     = clean_text(getattr(row, "company", ""), 100)
                location    = clean_text(getattr(row, "location", CONFIG["location"]), 100)
                description = clean_text(getattr(row, "description", ""), 300)
                date_posted = str(getattr(row, "date_posted", ""))[:10]

                work_type = derive_work_type(title, description)
                level     = derive_level(title, description)
                tags      = derive_tags(title, description)
                salary    = format_salary(row)
                job_id    = f"ABAP-{abs(hash(apply_url)) % 100000:05d}"
                now       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

                all_rows.append([
                    job_id,        # ID
                    title,         # Title
                    company,       # Company
                    location,      # Location
                    work_type,     # Work Type
                    level,         # Level
                    salary,        # Salary
                    tags,          # Tags
                    description,   # Description (Short)
                    apply_url,     # Apply URL
                    "Google Jobs", # Source
                    date_posted,   # Date Posted
                    now,           # Date Added
                    "Active",      # Status
                    "No",          # Featured
                ])

        except Exception as e:
            print(f"   ❌ Error scraping '{term}': {e}")
            continue

    return all_rows


def write_to_sheet(worksheet, rows: list):
    """
    Append new job rows to the Google Sheet.
    """
    if not rows:
        print("\n📭 No new jobs to add.")
        return 0

    print(f"\n📝 Writing {len(rows)} new jobs to Google Sheet...")
    worksheet.append_rows(rows, value_input_option="RAW")
    print(f"✅ Successfully added {len(rows)} jobs!")
    return len(rows)


def run():
    print("=" * 55)
    print("  AcadoreSkills — SAP ABAP Job Scraper")
    print(f"  Run time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    # 1. Connect to Google Sheet
    print("\n📊 Connecting to Google Sheet...")
    worksheet = get_google_sheet()
    ensure_headers(worksheet)
    print(f"   ✅ Connected to '{CONFIG['sheet_name']}'")

    # 2. Get existing URLs to avoid duplicates
    existing_urls = get_existing_urls(worksheet)
    print(f"   📋 {len(existing_urls)} existing jobs in sheet")

    # 3. Scrape jobs
    new_rows = scrape_all_terms(existing_urls)
    print(f"\n🎯 Total new unique jobs found: {len(new_rows)}")

    # 4. Write to sheet
    added = write_to_sheet(worksheet, new_rows)

    # 5. Summary
    print("\n" + "=" * 55)
    print(f"  ✅ Done! {added} new jobs added to your sheet.")
    print(f"  📊 Open: https://docs.google.com/spreadsheets")
    print("=" * 55)


if __name__ == "__main__":
    run()

