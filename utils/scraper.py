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
    Returns a deduplicated list of candidates.
    """
    slug = re.sub(r"[^a-z0-9]", "", company_name.lower())
    candidates = [
        f"https://www.{slug}.com",
        f"https://{slug}.com",
        f"https://www.{slug}.io",
        f"https://{slug}.io",
        f"https://www.{slug}.co",
    ]
    valid = []
    seen_final_urls = set()
    for url in candidates:
        try:
            r = requests.head(url, headers=HEADERS, timeout=6, allow_redirects=True)
            final_url = r.url.rstrip("/")
            if r.status_code < 400 and final_url not in seen_final_urls:
                seen_final_urls.add(final_url)
                valid.append({"url": r.url, "status": r.status_code})
        except Exception:
            pass
    return valid


def ai_find_career_url(company_url: str, company_name: str = "", api_key: str = "") -> dict:
    """
    AI-powered career page finder.
    Step 1: Scrape the homepage and collect all links.
    Step 2: Ask Claude to identify which link is most likely the careers page.
    Step 3: Follow that link, check for ATS redirects.
    Returns {'career_url': ..., 'ats_type': ..., 'confidence': ..., 'method': 'ai'}
    """
    import anthropic

    base = company_url.rstrip("/")
    add_log("info", f"AI career finder starting for {company_name or base}", "ai_finder")

    # ── Step 1: scrape homepage for all links + page text ──────────────────
    try:
        r = requests.get(base, headers=HEADERS, timeout=12, allow_redirects=True)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        add_log("error", f"Could not fetch homepage {base}: {e}", "ai_finder")
        return {"career_url": "", "ats_type": "unknown", "confidence": "low", "method": "ai"}

    # Collect all links with their anchor text
    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(strip=True)
        if not href or href.startswith("#") or href.startswith("mailto:"):
            continue
        full = urljoin(base, href)
        # Only keep links on the same domain or known ATS domains
        parsed = urlparse(full)
        base_domain = urlparse(base).netloc.replace("www.", "")
        is_same_domain = base_domain in parsed.netloc
        is_ats = any(ats in parsed.netloc for ats in [
            "greenhouse.io", "lever.co", "workday.com", "ashbyhq.com",
            "smartrecruiters.com", "jobvite.com", "icims.com", "myworkdayjobs.com"
        ])
        if (is_same_domain or is_ats) and full not in seen:
            seen.add(full)
            links.append({"url": full, "text": text[:80]})

    if not links:
        add_log("warning", f"No links found on homepage of {base}", "ai_finder")
        return {"career_url": "", "ats_type": "unknown", "confidence": "low", "method": "ai"}

    # Also grab nav/footer text for context
    page_text = ""
    for tag in soup.find_all(["nav", "footer", "header"]):
        page_text += tag.get_text(separator=" ", strip=True)[:500]

    # ── Step 2: Ask Claude ─────────────────────────────────────────────────
    if not api_key:
        # Fall back to keyword matching if no API key
        add_log("warning", "No API key for AI finder, using keyword fallback", "ai_finder")
        return _keyword_career_finder(base, links)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        links_text = "\n".join(
            f"- {l['url']}  [{l['text']}]" for l in links[:80]
        )
        prompt = f"""You are helping find the careers/jobs page for a company.

Company: {company_name or base}
Homepage: {base}

Here are all the links found on their homepage:
{links_text}

Page context (nav/footer text):
{page_text[:800]}

Task: Identify the single best URL that leads to their careers, jobs, or hiring page.
The page might be called: Careers, Jobs, Work With Us, Join Us, Join the Team, We're Hiring, Open Roles, Opportunities, Team, etc.
It could also be an external ATS like Greenhouse, Lever, Workday, Ashby.

Respond ONLY with a JSON object, no markdown:
{{
  "career_url": "<the best URL or empty string if none found>",
  "confidence": "high|medium|low",
  "page_name": "<what the link was called>",
  "reasoning": "<one sentence>"
}}"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        text = message.content[0].text.strip().replace("```json","").replace("```","").strip()
        result = json.loads(text)
        career_url = result.get("career_url", "")
        confidence = result.get("confidence", "medium")
        reasoning  = result.get("reasoning", "")
        page_name  = result.get("page_name", "")

        add_log("info", f"AI found career page: {career_url} ({page_name}) — {reasoning}", "ai_finder")

        if not career_url:
            return {"career_url": "", "ats_type": "unknown", "confidence": "low", "method": "ai"}

        # ── Step 3: follow the URL and detect ATS ─────────────────────────
        try:
            r2 = requests.get(career_url, headers=HEADERS, timeout=10, allow_redirects=True)
            final_url = r2.url
            ats = detect_ats(final_url)
            # If redirected to ATS, use that
            if ats != "generic":
                career_url = final_url
        except Exception:
            ats = detect_ats(career_url)

        return {
            "career_url": career_url,
            "ats_type": ats,
            "confidence": confidence,
            "page_name": page_name,
            "reasoning": reasoning,
            "method": "ai",
        }

    except Exception as e:
        add_log("error", f"AI career finder failed: {e}", "ai_finder")
        return _keyword_career_finder(base, links)


def _keyword_career_finder(base: str, links: list) -> dict:
    """Fallback: keyword-based link scoring."""
    CAREER_KEYWORDS = [
        "career", "careers", "jobs", "job", "hiring", "work-with-us",
        "join-us", "join", "work with us", "we're hiring", "opportunities",
        "open roles", "positions", "vacancies", "talent", "team"
    ]
    best_url, best_score, best_text = "", 0, ""
    for link in links:
        url_lower  = link["url"].lower()
        text_lower = link["text"].lower()
        score = 0
        for kw in CAREER_KEYWORDS:
            if kw in url_lower:  score += 3
            if kw in text_lower: score += 2
        # Bonus for ATS domains
        if any(ats in url_lower for ats in ["greenhouse","lever","workday","ashby"]):
            score += 5
        if score > best_score:
            best_score, best_url, best_text = score, link["url"], link["text"]

    if best_url:
        ats = detect_ats(best_url)
        confidence = "high" if best_score >= 5 else "medium" if best_score >= 2 else "low"
        add_log("info", f"Keyword finder: {best_url} (score {best_score})", "ai_finder")
        return {"career_url": best_url, "ats_type": ats, "confidence": confidence, "method": "keyword"}

    return {"career_url": "", "ats_type": "unknown", "confidence": "low", "method": "keyword"}
