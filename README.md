# 🎯 AI Job Hunter

An AI-powered job monitoring and ranking system built with Streamlit. Monitors company career pages, filters jobs by your criteria, ranks them with Claude AI, and sends email digests.

## Features

- **6-page Streamlit dashboard** — Companies, Filters, Matched Jobs, AI Rankings, Email Digest, Logs
- **ATS support** — Greenhouse, Lever, Workday, Ashby, and generic career pages
- **Rule-based filtering** — Title, location, seniority, remote, keywords
- **AI ranking** — Claude scores each job 0–100 with a reason why it matches
- **Email digest** — HTML digest sent on a schedule with top-ranked jobs
- **Background scheduler** — Auto-scan and auto-digest via APScheduler

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Streamlit app
```bash
streamlit run app.py
```

### 3. Run the background scheduler (separate terminal)
```bash
python scheduler.py
```

### 4. Configure in the UI
1. Go to **📧 Email Digest** → set your Anthropic API key
2. Go to **🏢 Target Companies** → add companies
3. Go to **🔍 Job Filters** → set your preferences and paste your resume
4. Click **🔄 Run Scan Now** from any page
5. Click **🤖 Rank Unranked Jobs** in AI Rankings

---

## Free Hosting Options

### Option 1: Streamlit Community Cloud (Recommended — 100% Free)
**Best for: sharing with others, always-on**
1. Push your code to a GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo → deploy
4. Add secrets in the Streamlit Cloud dashboard (API keys, etc.)
- ✅ Free forever, HTTPS, custom subdomain
- ⚠️ Sleeps after 7 days of inactivity (free tier)
- ⚠️ No persistent background scheduler (run scans manually or use cron)

**Add secrets** in Streamlit Cloud → App Settings → Secrets:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
EMAIL_PASSWORD = "your-app-password"
```

### Option 2: Railway (Free tier, $5/mo after)
**Best for: always-on with scheduler**
1. Sign up at [railway.app](https://railway.app)
2. `railway init` → `railway up`
3. Add env vars in Railway dashboard
- ✅ Runs the scheduler continuously
- ✅ Persistent storage
- Free tier: 500 hours/month

### Option 3: Render (Free tier)
**Best for: lightweight, no credit card**
1. Sign up at [render.com](https://render.com)
2. Create a new Web Service → connect GitHub
3. Build command: `pip install -r requirements.txt`
4. Start command: `streamlit run app.py --server.port $PORT`
- ✅ Free tier available
- ⚠️ Spins down on inactivity (free tier)

### Option 4: Hugging Face Spaces (Free)
**Best for: ML/AI projects**
1. Create a Space at [huggingface.co/spaces](https://huggingface.co/spaces)
2. Select Streamlit as the SDK
3. Push your code
- ✅ Free, persistent
- ⚠️ Public by default unless using Pro

### Option 5: Local + ngrok (Free, for personal use)
**Best for: running on your own machine**
```bash
# Terminal 1: run app
streamlit run app.py

# Terminal 2: expose publicly
ngrok http 8501
```
- ✅ Free, full control
- ⚠️ Only online when your computer is on

### Option 6: Google Cloud Run (Free tier)
**Best for: production-grade**
```bash
gcloud run deploy job-hunter \
  --source . \
  --platform managed \
  --allow-unauthenticated
```
- ✅ Free tier: 2M requests/month
- ✅ Auto-scales to zero

---

## Project Structure

```
job_hunter/
├── app.py              # Main Streamlit app
├── scheduler.py        # Background scan + digest scheduler
├── requirements.txt
├── pages/
│   ├── dashboard.py
│   ├── companies.py
│   ├── filters.py
│   ├── matched_jobs.py
│   ├── ai_rankings.py
│   ├── email_digest.py
│   └── logs.py
├── utils/
│   ├── db.py           # JSON-based data store
│   ├── scraper.py      # Greenhouse, Lever, generic scrapers
│   ├── ranker.py       # Rule filter + AI ranking
│   └── mailer.py       # Email digest sender
└── data/               # Auto-created, stores all state
    ├── companies.json
    ├── filters.json
    ├── jobs.json
    ├── config.json
    ├── logs.json
    └── resume.txt
```

---

## Gmail Setup

1. Enable 2-Factor Authentication on your Google account
2. Go to: myaccount.google.com → Security → App Passwords
3. Create an App Password for "Mail"
4. Use that 16-character password in the Email Setup page

---

## Upgrading the Database

The default storage uses JSON files — perfect for personal use.
To scale up, replace `utils/db.py` with SQLite:
```bash
pip install sqlalchemy
```
Or PostgreSQL for production.
