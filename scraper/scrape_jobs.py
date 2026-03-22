import os
import json
import gspread
import requests
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials

print("=======================================================")
print("  AcadoreSkills — SAP ABAP Job Scraper")
print(f"  Run time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=======================================================\n")

# ── Google Sheet connection ──────────────────────────────────────────────────
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SHEET_NAME = "AcadoreSkills Jobs"
HEADERS = ["ID","Title","Company","Location","Work Type","Level","Salary",
           "Tags","Description","Apply URL","Source","Date Posted","Date Added","Status","Featured"]

def connect_sheet():
    print("📊 Connecting to Google Sheet...")
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise Exception("GOOGLE_CREDENTIALS secret not found!")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).worksheet("Jobs")
    print(f"   ✅ Connected to '{SHEET_NAME}'")
    return sheet

# ── Scrape from Remotive (free, no auth, SAP-friendly) ──────────────────────
def fetch_remotive():
    print("\n🔍 Searching Remotive API for SAP ABAP jobs...")
    jobs = []
    try:
        url = "https://remotive.com/api/remote-jobs?search=SAP+ABAP&limit=20"
        r = requests.get(url, timeout=15)
        data = r.json()
        for j in data.get("jobs", []):
            title = j.get("title", "")
            if not any(k in title.upper() for k in ["SAP", "ABAP"]):
                continue
            jobs.append({
                "title": title,
                "company": j.get("company_name", ""),
                "location": j.get("candidate_required_location", "Worldwide"),
                "work_type": "Remote",
                "level": guess_level(title),
                "salary": j.get("salary", ""),
                "tags": ", ".join(j.get("tags", [])[:5]),
                "description": clean_text(j.get("description", ""))[:300],
                "apply_url": j.get("url", ""),
                "source": "Remotive",
                "date_posted": j.get("publication_date", "")[:10],
            })
        print(f"   ✅ Found {len(jobs)} SAP ABAP jobs on Remotive")
    except Exception as e:
        print(f"   ⚠️  Remotive error: {e}")
    return jobs

# ── Scrape from Jobicy (free, no auth) ──────────────────────────────────────
def fetch_jobicy():
    print("\n🔍 Searching Jobicy API for SAP jobs...")
    jobs = []
    try:
        url = "https://jobicy.com/api/v2/remote-jobs?tag=sap&count=20"
        r = requests.get(url, timeout=15)
        data = r.json()
        for j in data.get("jobs", []):
            title = j.get("jobTitle", "")
            jobs.append({
                "title": title,
                "company": j.get("companyName", ""),
                "location": j.get("jobGeo", "Remote"),
                "work_type": "Remote",
                "level": guess_level(title),
                "salary": j.get("annualSalaryMin", ""),
                "tags": ", ".join(j.get("jobIndustry", [])[:3]),
                "description": clean_text(j.get("jobExcerpt", ""))[:300],
                "apply_url": j.get("url", ""),
                "source": "Jobicy",
                "date_posted": j.get("pubDate", "")[:10],
            })
        print(f"   ✅ Found {len(jobs)} SAP jobs on Jobicy")
    except Exception as e:
        print(f"   ⚠️  Jobicy error: {e}")
    return jobs

# ── Adzuna API (free tier) ───────────────────────────────────────────────────
def fetch_adzuna():
    print("\n🔍 Searching Adzuna for SAP ABAP jobs in India...")
    jobs = []
    APP_ID  = os.environ.get("ADZUNA_APP_ID", "")
    APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
    if not APP_ID or not APP_KEY:
        print("   ⚠️  Adzuna keys not set — skipping")
        return jobs
    try:
        url = (f"https://api.adzuna.com/v1/api/jobs/in/search/1"
               f"?app_id={APP_ID}&app_key={APP_KEY}"
               f"&results_per_page=20&what=SAP+ABAP&content-type=application/json")
        r = requests.get(url, timeout=15)
        data = r.json()
        for j in data.get("results", []):
            jobs.append({
                "title": j.get("title", ""),
                "company": j.get("company", {}).get("display_name", ""),
                "location": j.get("location", {}).get("display_name", "India"),
                "work_type": "On-site",
                "level": guess_level(j.get("title", "")),
                "salary": format_salary(j.get("salary_min"), j.get("salary_max")),
                "tags": "SAP, ABAP",
                "description": j.get("description", "")[:300],
                "apply_url": j.get("redirect_url", ""),
                "source": "Adzuna",
                "date_posted": j.get("created", "")[:10],
            })
        print(f"   ✅ Found {len(jobs)} jobs on Adzuna")
    except Exception as e:
        print(f"   ⚠️  Adzuna error: {e}")
    return jobs

# ── Helpers ──────────────────────────────────────────────────────────────────
def guess_level(title):
    t = title.upper()
    if any(w in t for w in ["FRESHER","JUNIOR","TRAINEE","ENTRY","GRADUATE"]): return "Fresher"
    if any(w in t for w in ["SENIOR","SR.","LEAD","PRINCIPAL","ARCHITECT"]): return "Senior"
    if any(w in t for w in ["MID","MIDDLE"]): return "Mid-level"
    return "Mid-level"

def format_salary(mn, mx):
    if mn and mx:
        return f"₹{int(mn):,} - ₹{int(mx):,}"
    if mn: return f"₹{int(mn):,}+"
    return ""

def clean_text(html):
    import re
    return re.sub(r'<[^>]+>', '', str(html)).strip()

def make_id(title, company):
    import hashlib
    return hashlib.md5(f"{title}{company}".encode()).hexdigest()[:8].upper()

# ── Write to sheet ───────────────────────────────────────────────────────────
def write_to_sheet(sheet, all_jobs):
    existing = sheet.get_all_values()
    if len(existing) <= 1:
        sheet.clear()
        sheet.append_row(HEADERS)
        existing_ids = set()
    else:
        existing_ids = set(row[0] for row in existing[1:] if row)

    today = datetime.now().strftime("%Y-%m-%d")
    new_count = 0

    for j in all_jobs:
        jid = make_id(j["title"], j["company"])
        if jid in existing_ids:
            continue
        row = [
            jid,
            j.get("title",""),
            j.get("company",""),
            j.get("location",""),
            j.get("work_type","Remote"),
            j.get("level","Mid-level"),
            j.get("salary",""),
            j.get("tags","SAP, ABAP"),
            j.get("description",""),
            j.get("apply_url",""),
            j.get("source",""),
            j.get("date_posted", today),
            today,
            "Active",
            "No"
        ]
        sheet.append_row(row)
        existing_ids.add(jid)
        new_count += 1
        print(f"   ➕ Added: {j['title']} @ {j['company']}")

    return new_count

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    sheet = connect_sheet()
    existing = sheet.get_all_values()
    print(f"   📋 {max(0, len(existing)-1)} existing jobs in sheet\n")

    all_jobs = []
    all_jobs += fetch_remotive()
    all_jobs += fetch_jobicy()
    all_jobs += fetch_adzuna()

    print(f"\n🎯 Total jobs found across all sources: {len(all_jobs)}")

    if not all_jobs:
        print("\n📭 No jobs found. Will try again tomorrow.")
    else:
        count = write_to_sheet(sheet, all_jobs)
        print(f"\n{'='*55}")
        print(f"  ✅ Done! {count} new jobs added to your sheet.")
        print(f"  📊 Open: https://docs.google.com/spreadsheets")
        print(f"{'='*55}")

if __name__ == "__main__":
    main()
