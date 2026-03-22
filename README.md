# AcadoreSkills — SAP ABAP Job Scraper
### Phase 1: Auto-scrape Google Jobs → Google Sheet

Runs automatically every day at **7:00 AM IST** on GitHub's free servers.
Zero cost. Zero maintenance after setup.

---

## What this does

```
Every morning at 7 AM IST:
GitHub Actions → runs scrape_jobs.py → searches Google Jobs
→ finds SAP ABAP roles → saves to your Google Sheet
```

Your Google Sheet becomes the master database.
Your website reads from that sheet live (Phase 3).

---

## Files in this project

```
acadore-scraper/
├── .github/
│   └── workflows/
│       └── scrape-jobs.yml     ← GitHub Actions schedule
├── scraper/
│   └── scrape_jobs.py          ← Main Python scraper
├── requirements.txt            ← Python packages needed
└── README.md                   ← This file
```

---

## SETUP GUIDE — Do these steps once

---

### STEP 1 — Create a GitHub account & repository

1. Go to https://github.com and sign up (free)
2. Click **"New repository"**
3. Name it: `acadore-jobs-scraper`
4. Set to **Private** (so your credentials stay safe)
5. Click **"Create repository"**
6. Upload all these files by dragging them into GitHub

---

### STEP 2 — Create a Google Sheet

1. Go to https://sheets.google.com
2. Create a new sheet
3. Name it exactly: **`AcadoreSkills Jobs`**
4. Leave it empty — the scraper will add headers automatically

Your sheet will look like this after first run:

| ID | Title | Company | Location | Work Type | Level | Salary | Tags | Description | Apply URL | Source | Date Posted | Date Added | Status | Featured |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ABAP-00001 | SAP ABAP Developer | Infosys | Hyderabad | Hybrid | Mid-level | ₹8.0–14.0 LPA | ABAP OOP, BAPIs | ... | https://... | Google Jobs | 2026-03-20 | 2026-03-22 | Active | No |

---

### STEP 3 — Create Google Service Account (free)

This lets the Python script write to your Google Sheet.

1. Go to https://console.cloud.google.com
2. Create a new project (name it anything, e.g. "acadore-scraper")
3. Click **"APIs & Services"** → **"Enable APIs"**
4. Search and enable:
   - **Google Sheets API** ✅
   - **Google Drive API** ✅
5. Go to **"APIs & Services"** → **"Credentials"**
6. Click **"Create Credentials"** → **"Service Account"**
7. Name: `acadore-scraper` → Click **Create**
8. Skip optional steps → Click **Done**
9. Click on your new service account → **"Keys"** tab
10. **"Add Key"** → **"Create new key"** → **JSON** → Download
11. Open the downloaded JSON file — you'll need it in Step 4

---

### STEP 4 — Share your Google Sheet with the service account

1. Open the JSON file you downloaded
2. Find the `"client_email"` field — it looks like:
   `acadore-scraper@your-project.iam.gserviceaccount.com`
3. Open your **AcadoreSkills Jobs** Google Sheet
4. Click **Share** (top right)
5. Paste that email address
6. Set permission to **Editor**
7. Click **Send**

---

### STEP 5 — Add credentials to GitHub Secrets

This is how the scraper gets permission to write to your sheet — safely, without exposing credentials in your code.

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Name: `GOOGLE_CREDENTIALS`
5. Value: Open your downloaded JSON file → **select ALL text** → paste it here
6. Click **"Add secret"**

That's it! Your credentials are now safely stored.

---

### STEP 6 — Test it manually

1. Go to your GitHub repository
2. Click **"Actions"** tab
3. Click **"Scrape SAP ABAP Jobs Daily"**
4. Click **"Run workflow"** → **"Run workflow"** (green button)
5. Watch it run (takes ~2–3 minutes)
6. Open your Google Sheet — you should see jobs appearing!

---

### STEP 7 — It now runs automatically

Every day at **7:00 AM IST**, GitHub will:
1. Start a free Linux server
2. Install Python and dependencies
3. Run your scraper
4. Add new jobs to your Google Sheet
5. Shut down

You don't need to do anything. Just check your sheet each morning.

---

## Customising the scraper

Open `scraper/scrape_jobs.py` and edit the `CONFIG` section at the top:

```python
CONFIG = {
    # Add or remove search terms here
    "search_terms": [
        "SAP ABAP Developer",
        "SAP ABAP Consultant",
        "SAP ABAP Fresher",    # ← Great for your audience
        "ABAP HANA Developer",
        "SAP Fiori ABAP",
    ],

    # Change location
    "location": "India",       # or "Hyderabad" for local focus

    # Results per search term
    "results_per_term": 15,    # Max ~20 to stay polite

    # Sheet name (must match exactly)
    "sheet_name": "AcadoreSkills Jobs",
}
```

---

## Managing jobs manually in the sheet

You can add LinkedIn/Naukri/Recruiter jobs directly in the sheet.
Just add a new row with the same column format.

For manually added jobs, set:
- **Source** column → `LinkedIn` or `Naukri` or `Recruiter`
- **Status** column → `Active`
- **Featured** column → `Yes` (to highlight on your website)

---

## Troubleshooting

**"GOOGLE_CREDENTIALS environment variable not set"**
→ You haven't added the GitHub Secret yet. See Step 5.

**"Google Sheet not found"**
→ The sheet name doesn't match exactly. It must be: `AcadoreSkills Jobs`

**"No results found"**
→ Normal sometimes. Google Jobs rate-limits occasionally. Try again next day.

**GitHub Actions not running**
→ Check the Actions tab for error logs.
→ Make sure the YAML file is in `.github/workflows/` folder.

---

## What's next — Phase 2 & 3

- **Phase 2** — Set up the Google Sheet properly with dropdowns, formatting
- **Phase 3** — Connect your website to read from the sheet live

---

## Cost breakdown

| Service | Cost |
|---|---|
| GitHub Actions (2000 min/month free) | $0 |
| Google Sheets API | $0 |
| Google Cloud Service Account | $0 |
| JobSpy (open source) | $0 |
| **Total** | **$0** |

---

Built for AcadoreSkills · acadoreskillsconsulting.com
