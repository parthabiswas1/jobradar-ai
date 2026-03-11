"""
State management using JSON files as a simple database.
In production, swap with SQLite or PostgreSQL.
"""
import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

COMPANIES_FILE = DATA_DIR / "companies.json"
FILTERS_FILE = DATA_DIR / "filters.json"
JOBS_FILE = DATA_DIR / "jobs.json"
LOGS_FILE = DATA_DIR / "logs.json"
CONFIG_FILE = DATA_DIR / "config.json"
RESUME_FILE = DATA_DIR / "resume.txt"


def _load(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return default
    return default


def _save(path, data):
    path.write_text(json.dumps(data, indent=2, default=str))


# ── Companies ────────────────────────────────────────────────────────────────

def get_companies():
    return _load(COMPANIES_FILE, [])


def save_companies(companies):
    _save(COMPANIES_FILE, companies)


def add_company(name, url, career_url="", ats_type="", status="active", notes=""):
    companies = get_companies()
    company = {
        "id": datetime.now().isoformat(),
        "name": name,
        "url": url,
        "career_url": career_url,
        "ats_type": ats_type,
        "status": status,
        "notes": notes,
        "added_at": datetime.now().isoformat(),
        "last_scanned": None,
        "jobs_found": 0,
    }
    companies.append(company)
    save_companies(companies)
    return company


def update_company(company_id, **kwargs):
    companies = get_companies()
    for c in companies:
        if c["id"] == company_id:
            c.update(kwargs)
    save_companies(companies)


def delete_company(company_id):
    companies = [c for c in get_companies() if c["id"] != company_id]
    save_companies(companies)


# ── Filters ──────────────────────────────────────────────────────────────────

def get_filters():
    return _load(FILTERS_FILE, {
        "titles": [],
        "locations": [],
        "seniority": [],
        "remote_only": False,
        "keywords_include": [],
        "keywords_exclude": [],
        "min_salary": None,
        "max_salary": None,
    })


def save_filters(filters):
    _save(FILTERS_FILE, filters)


# ── Jobs ─────────────────────────────────────────────────────────────────────

def get_jobs():
    return _load(JOBS_FILE, [])


def save_jobs(jobs):
    _save(JOBS_FILE, jobs)


def add_job(title, company, location, url, description, remote=False,
            seniority="", salary="", source="scraped"):
    jobs = get_jobs()
    job = {
        "id": datetime.now().isoformat() + f"_{len(jobs)}",
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "description": description,
        "remote": remote,
        "seniority": seniority,
        "salary": salary,
        "source": source,
        "found_at": datetime.now().isoformat(),
        "filter_passed": None,
        "ai_score": None,
        "ai_reason": "",
        "status": "new",   # new | viewed | applied | dismissed
    }
    jobs.insert(0, job)
    save_jobs(jobs)
    return job


def update_job(job_id, **kwargs):
    jobs = get_jobs()
    for j in jobs:
        if j["id"] == job_id:
            j.update(kwargs)
    save_jobs(jobs)


# ── Config ───────────────────────────────────────────────────────────────────

def get_config():
    return _load(CONFIG_FILE, {
        "anthropic_api_key": "",
        "email_to": "",
        "email_from": "",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_password": "",
        "digest_times": ["08:00", "18:00"],
        "digest_enabled": True,
        "scan_interval_hours": 6,
        "scan_enabled": True,
        "min_ai_score": 60,
    })


def save_config(config):
    _save(CONFIG_FILE, config)


# ── Resume ───────────────────────────────────────────────────────────────────

def get_resume():
    if RESUME_FILE.exists():
        return RESUME_FILE.read_text()
    return ""


def save_resume(text):
    RESUME_FILE.write_text(text)


# ── Logs ─────────────────────────────────────────────────────────────────────

def get_logs():
    return _load(LOGS_FILE, [])


def add_log(level, message, source="system"):
    logs = get_logs()
    log = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "source": source,
        "message": message,
    }
    logs.insert(0, log)
    # Keep last 500 logs
    logs = logs[:500]
    _save(LOGS_FILE, logs)


def clear_logs():
    _save(LOGS_FILE, [])
