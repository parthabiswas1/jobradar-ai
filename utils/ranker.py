"""
AI ranking layer using Claude to evaluate job matches.
"""
import json
import anthropic
from utils.db import get_config, get_resume, get_filters, add_log


def rank_jobs_with_ai(jobs: list) -> list:
    """
    Takes a list of job dicts (already filter-passed).
    Returns same list enriched with ai_score and ai_reason.
    """
    config = get_config()
    api_key = config.get("anthropic_api_key", "")
    if not api_key:
        add_log("warning", "No Anthropic API key set. Skipping AI ranking.", "ai_ranker")
        for job in jobs:
            job["ai_score"] = 50
            job["ai_reason"] = "AI ranking skipped (no API key)"
        return jobs

    resume = get_resume()
    filters = get_filters()

    client = anthropic.Anthropic(api_key=api_key)

    ranked = []
    for job in jobs:
        try:
            prompt = f"""You are an expert career advisor. Evaluate how well this job matches the candidate.

CANDIDATE RESUME / BACKGROUND:
{resume or "Not provided – use job filter preferences instead."}

JOB PREFERENCES:
- Titles of interest: {', '.join(filters.get('titles', [])) or 'Any'}
- Preferred locations: {', '.join(filters.get('locations', [])) or 'Any'}
- Seniority levels: {', '.join(filters.get('seniority', [])) or 'Any'}
- Remote only: {filters.get('remote_only', False)}
- Keywords to include: {', '.join(filters.get('keywords_include', [])) or 'None'}
- Keywords to exclude: {', '.join(filters.get('keywords_exclude', [])) or 'None'}

JOB TO EVALUATE:
Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}
Remote: {job.get('remote', False)}
Seniority: {job.get('seniority', '')}
Description (excerpt): {job.get('description', '')[:1500]}

Respond ONLY with a JSON object, no markdown:
{{
  "score": <integer 0-100>,
  "reason": "<2-3 sentence explanation of the match quality>",
  "highlights": ["<strength 1>", "<strength 2>"],
  "concerns": ["<concern 1>"]
}}"""

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            text = message.content[0].text.strip()
            # Strip markdown fences if present
            text = text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)
            job["ai_score"] = result.get("score", 50)
            job["ai_reason"] = result.get("reason", "")
            job["ai_highlights"] = result.get("highlights", [])
            job["ai_concerns"] = result.get("concerns", [])
        except Exception as e:
            add_log("error", f"AI ranking failed for '{job.get('title')}': {e}", "ai_ranker")
            job["ai_score"] = 50
            job["ai_reason"] = f"AI ranking error: {str(e)[:100]}"
            job["ai_highlights"] = []
            job["ai_concerns"] = []
        ranked.append(job)

    ranked.sort(key=lambda x: x.get("ai_score", 0), reverse=True)
    add_log("info", f"AI ranked {len(ranked)} jobs", "ai_ranker")
    return ranked


def apply_rule_filters(jobs: list) -> list:
    """Apply rule-based filters. Returns (passed, failed) lists."""
    filters = get_filters()
    titles = [t.lower() for t in filters.get("titles", [])]
    locations = [l.lower() for l in filters.get("locations", [])]
    seniority = [s.lower() for s in filters.get("seniority", [])]
    remote_only = filters.get("remote_only", False)
    include_kw = [k.lower() for k in filters.get("keywords_include", [])]
    exclude_kw = [k.lower() for k in filters.get("keywords_exclude", [])]

    passed, failed = [], []
    for job in jobs:
        text = f"{job.get('title','')} {job.get('description','')} {job.get('location','')}".lower()
        title = job.get("title", "").lower()
        job_location = job.get("location", "").lower()
        job_remote = job.get("remote", False)
        job_seniority = job.get("seniority", "").lower()

        reasons = []

        # Title filter
        if titles and not any(t in title for t in titles):
            reasons.append(f"Title '{job.get('title')}' doesn't match: {titles}")

        # Location filter
        if locations and not job_remote and not any(l in job_location for l in locations):
            reasons.append(f"Location '{job.get('location')}' not in: {locations}")

        # Remote filter
        if remote_only and not job_remote:
            reasons.append("Not remote")

        # Seniority filter
        if seniority and job_seniority and not any(s in job_seniority for s in seniority):
            reasons.append(f"Seniority '{job.get('seniority')}' not in: {seniority}")

        # Keyword include
        if include_kw and not any(k in text for k in include_kw):
            reasons.append(f"Missing required keywords: {include_kw}")

        # Keyword exclude
        matched_excludes = [k for k in exclude_kw if k in text]
        if matched_excludes:
            reasons.append(f"Contains excluded keywords: {matched_excludes}")

        job["filter_passed"] = len(reasons) == 0
        job["filter_reasons"] = reasons
        if job["filter_passed"]:
            passed.append(job)
        else:
            failed.append(job)

    add_log("info", f"Filter: {len(passed)} passed, {len(failed)} failed", "filter")
    return passed, failed
