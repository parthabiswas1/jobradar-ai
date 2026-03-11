"""
Background scheduler for automated scanning and email digests.
Run this separately: python scheduler.py
"""
import time
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger("scheduler")

# Add project root to path
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from utils.db import get_config, get_companies, get_jobs, save_jobs, add_log, update_job
from utils.scraper import scrape_company
from utils.ranker import apply_rule_filters, rank_jobs_with_ai
from utils.mailer import send_digest


def run_scan():
    config = get_config()
    if not config.get("scan_enabled", True):
        log.info("Scanning disabled. Skipping.")
        return
    
    companies = get_companies()
    active = [c for c in companies if c.get("status") == "active"]
    log.info(f"Starting scan for {len(active)} companies")
    add_log("info", f"Scheduled scan started for {len(active)} companies", "scheduler")

    existing_jobs = get_jobs()
    existing_urls = {j.get("url") for j in existing_jobs}
    all_new = []

    for company in active:
        try:
            scraped = scrape_company(company)
            new = [j for j in scraped if j.get("url") not in existing_urls]
            for j in new:
                j["company"] = company["name"]
            all_new.extend(new)
            log.info(f"{company['name']}: {len(scraped)} jobs, {len(new)} new")
            
            # Update last_scanned
            from utils.db import get_companies, save_companies
            all_c = get_companies()
            for c in all_c:
                if c["id"] == company["id"]:
                    c["last_scanned"] = datetime.now().isoformat()
                    c["jobs_found"] = c.get("jobs_found", 0) + len(scraped)
            save_companies(all_c)
        except Exception as e:
            log.error(f"Scan failed for {company['name']}: {e}")
            add_log("error", f"Scan failed for {company['name']}: {e}", "scheduler")

    if all_new:
        passed, failed = apply_rule_filters(all_new)
        
        if passed and config.get("anthropic_api_key"):
            passed = rank_jobs_with_ai(passed)
        
        # Update failed filter status
        failed_ids = {j["id"] for j in failed}
        all_new_merged = {j["id"]: j for j in passed}
        all_new_merged.update({j["id"]: j for j in failed})
        
        save_jobs(list(all_new_merged.values()) + existing_jobs)
        
        log.info(f"Scan complete: {len(all_new)} new, {len(passed)} passed, {len(failed)} filtered")
        add_log("info", f"Scan complete: {len(all_new)} new jobs, {len(passed)} passed filter", "scheduler")
    else:
        log.info("No new jobs found.")
        add_log("info", "Scheduled scan: no new jobs found", "scheduler")


def run_digest():
    config = get_config()
    if not config.get("digest_enabled", True):
        log.info("Digest disabled. Skipping.")
        return
    log.info("Sending scheduled digest")
    add_log("info", "Sending scheduled digest", "scheduler")
    send_digest()


def main():
    scheduler = BlockingScheduler()
    config = get_config()
    
    # Scan job
    scan_hours = config.get("scan_interval_hours", 6)
    scheduler.add_job(run_scan, IntervalTrigger(hours=scan_hours), id="scan",
                      name=f"Scan every {scan_hours}h", replace_existing=True)
    
    # Digest jobs
    for t in config.get("digest_times", ["08:00", "18:00"]):
        h, m = t.split(":")
        scheduler.add_job(run_digest, CronTrigger(hour=int(h), minute=int(m)),
                          id=f"digest_{t}", name=f"Digest at {t}", replace_existing=True)
    
    log.info(f"Scheduler started. Scan every {scan_hours}h. Digests at {config.get('digest_times')}")
    add_log("info", "Background scheduler started", "scheduler")
    
    # Run an initial scan immediately
    run_scan()
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
