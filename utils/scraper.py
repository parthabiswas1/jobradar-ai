"""
Job scraper: handles Greenhouse, Lever, Workday, and generic career pages.
"""
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from utils.db import add_log


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JobHunterBot/1.0)"
}


def detect_ats(url: str) -> str:
    """Detect ATS type from URL."""
    url = url.lower()
    if "greenhouse.io" in url or "boards.greenhouse" in url:
        return "greenhouse"
    if "lever.co" in url:
        return "lever"
    if "workday.com" in url or "myworkdayjobs" in url:
        return "workday"
    if "ashbyhq.com" in url:
        return "ashby"
    if "smartrecruiters.com" in url:
        return "smartrecruiters"
    if "jobvite.com" in url:
        return "jobvite"
    if "icims.com" in url:
        return "icims"
    return "generic"


def find_career_url(company_url: str, company_name: str = "") -> dict:
    """
    Attempt to find the career page for a company.
    Returns {'career_url': ..., 'ats_type': ..., 'confidence': ...}
    """
    candidates = []
    base = company_url.rstrip("/")
    
    # Common career page paths
    paths = ["/careers", "/jobs", "/work-with-us", "/join-us",
             "/about/careers", "/company/careers", "/en/careers"]
    
    for path in paths:
        candidates.append(base + path)
    
    # Try to find via homepage scrape
    try:
        r = requests.get(base, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            text = a.get_text().lower()
            if any(k in href or k in text for k in ["career", "jobs", "hiring", "work with us", "join"]):
                full = urljoin(base, a["href"])
                if full not in candidates:
                    candidates.insert(0, full)  # prioritize found links
    except Exception as e:
        add_log("warning", f"Could not scrape homepage {base}: {e}", "scraper")
    
    # Try each candidate
    for url in candidates[:6]:
        try:
            r = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
            if r.status_code == 200:
                ats = detect_ats(r.url)
                return {
                    "career_url": r.url,
                    "ats_type": ats,
                    "confidence": "high" if ats != "generic" else "medium"
                }
        except Exception:
            continue
    
    return {"career_url": "", "ats_type": "unknown", "confidence": "low"}


def scrape_greenhouse(career_url: str) -> list:
    """Scrape jobs from Greenhouse board."""
    jobs = []
    # Extract board token from URL
    match = re.search(r"greenhouse\.io/([^/\?]+)", career_url)
    if not match:
        return jobs
    token = match.group(1)
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    try:
        r = requests.get(api_url, headers=HEADERS, timeout=15)
        data = r.json()
        for job in data.get("jobs", []):
            jobs.append({
                "title": job.get("title", ""),
                "location": job.get("location", {}).get("name", ""),
                "url": job.get("absolute_url", ""),
                "description": BeautifulSoup(job.get("content", ""), "html.parser").get_text()[:2000],
                "remote": "remote" in job.get("location", {}).get("name", "").lower(),
                "seniority": _infer_seniority(job.get("title", "")),
                "salary": "",
                "source": "greenhouse",
            })
    except Exception as e:
        add_log("error", f"Greenhouse scrape failed for {career_url}: {e}", "scraper")
    return jobs


def scrape_lever(career_url: str) -> list:
    """Scrape jobs from Lever."""
    jobs = []
    match = re.search(r"lever\.co/([^/\?]+)", career_url)
    if not match:
        return jobs
    token = match.group(1)
    api_url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    try:
        r = requests.get(api_url, headers=HEADERS, timeout=15)
        data = r.json()
        for job in data:
            desc = " ".join(
                block.get("content", "") if isinstance(block, dict) else ""
                for block in job.get("descriptionBody", {}).get("blocks", [])
            )
            jobs.append({
                "title": job.get("text", ""),
                "location": job.get("categories", {}).get("location", ""),
                "url": job.get("hostedUrl", ""),
                "description": BeautifulSoup(desc, "html.parser").get_text()[:2000],
                "remote": "remote" in job.get("categories", {}).get("location", "").lower(),
                "seniority": _infer_seniority(job.get("text", "")),
                "salary": "",
                "source": "lever",
            })
    except Exception as e:
        add_log("error", f"Lever scrape failed for {career_url}: {e}", "scraper")
    return jobs


def scrape_generic(career_url: str) -> list:
    """Generic scraper for unknown career pages."""
    jobs = []
    try:
        r = requests.get(career_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Look for job listing patterns
        job_containers = (
            soup.find_all(class_=re.compile(r"job|position|opening|role", re.I)) or
            soup.find_all("li", class_=re.compile(r"job|position", re.I))
        )
        
        seen = set()
        for el in job_containers[:50]:
            link = el.find("a", href=True)
            if not link:
                continue
            title = link.get_text(strip=True)
            href = urljoin(career_url, link["href"])
            if not title or href in seen or len(title) < 4:
                continue
            seen.add(href)
            
            # Try to get location
            loc_el = el.find(class_=re.compile(r"location|city|place", re.I))
            location = loc_el.get_text(strip=True) if loc_el else ""
            
            jobs.append({
                "title": title,
                "location": location,
                "url": href,
                "description": el.get_text(separator=" ", strip=True)[:1000],
                "remote": "remote" in el.get_text().lower(),
                "seniority": _infer_seniority(title),
                "salary": "",
                "source": "generic",
            })
    except Exception as e:
        add_log("error", f"Generic scrape failed for {career_url}: {e}", "scraper")
    return jobs


def scrape_company(company: dict) -> list:
    """Main entry point: scrape a company's career page."""
    career_url = company.get("career_url", "")
    if not career_url:
        add_log("warning", f"No career URL for {company['name']}", "scraper")
        return []
    
    ats = company.get("ats_type", detect_ats(career_url))
    add_log("info", f"Scanning {company['name']} ({ats}): {career_url}", "scraper")
    
    if ats == "greenhouse":
        jobs = scrape_greenhouse(career_url)
    elif ats == "lever":
        jobs = scrape_lever(career_url)
    else:
        jobs = scrape_generic(career_url)
    
    add_log("info", f"Found {len(jobs)} jobs at {company['name']}", "scraper")
    return jobs


def _infer_seniority(title: str) -> str:
    title = title.lower()
    if any(k in title for k in ["vp ", "vice president", "director", "head of", "chief"]):
        return "Director+"
    if any(k in title for k in ["senior", "sr.", "sr ", "lead", "principal", "staff"]):
        return "Senior"
    if any(k in title for k in ["junior", "jr.", "jr ", "associate", "entry"]):
        return "Junior"
    if any(k in title for k in ["intern", "internship"]):
        return "Intern"
    return "Mid"


def search_company_url(company_name: str) -> list:
    """
    Use a simple web search heuristic to guess company URL.
    Returns a list of candidates.
    """
    # Build plausible domains
    slug = re.sub(r"[^a-z0-9]", "", company_name.lower())
    candidates = [
        f"https://www.{slug}.com",
        f"https://{slug}.com",
        f"https://www.{slug}.io",
        f"https://{slug}.io",
        f"https://www.{slug}.co",
    ]
    valid = []
    for url in candidates:
        try:
            r = requests.head(url, headers=HEADERS, timeout=6, allow_redirects=True)
            if r.status_code < 400:
                valid.append({"url": r.url, "status": r.status_code})
        except Exception:
            pass
    return valid
