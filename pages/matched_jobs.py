import streamlit as st
from datetime import datetime
from utils.db import get_jobs, get_companies, update_job, save_jobs, add_log, get_config
from utils.scraper import scrape_company
from utils.ranker import apply_rule_filters


def show():
    st.markdown('<div class="main-header">📋 Matched Jobs</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Jobs that passed your filter rules</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.button("🔄 Run Scan Now", type="primary"):
            _run_scan()
            st.rerun()
    with col2:
        if st.button("♻️ Re-run Filters"):
            _rerun_filters()
            st.rerun()
    with col3:
        if st.button("🗑 Clear All Jobs"):
            save_jobs([])
            st.success("All jobs cleared.")
            st.rerun()

    st.markdown("---")

    jobs = get_jobs()
    passed = [j for j in jobs if j.get("filter_passed")]
    failed = [j for j in jobs if j.get("filter_passed") is False]
    
    # Stats row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Scraped", len(jobs))
    m2.metric("✅ Passed Filter", len(passed))
    m3.metric("❌ Filtered Out", len(failed))
    m4.metric("🆕 New", len([j for j in passed if j.get("status") == "new"]))

    st.markdown("---")

    # Filters
    with st.expander("🎛 View/Filter Options"):
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.multiselect("Status", ["new", "viewed", "applied", "dismissed"],
                                           default=["new", "viewed"])
        with col2:
            company_filter = st.multiselect("Company",
                                            sorted(set(j.get("company", "") for j in passed)))
        with col3:
            remote_filter = st.selectbox("Remote", ["All", "Remote Only", "On-site Only"])

    # Apply view filters
    display_jobs = passed
    if status_filter:
        display_jobs = [j for j in display_jobs if j.get("status") in status_filter]
    if company_filter:
        display_jobs = [j for j in display_jobs if j.get("company") in company_filter]
    if remote_filter == "Remote Only":
        display_jobs = [j for j in display_jobs if j.get("remote")]
    elif remote_filter == "On-site Only":
        display_jobs = [j for j in display_jobs if not j.get("remote")]

    # Sort
    display_jobs = sorted(display_jobs, key=lambda x: x.get("found_at", ""), reverse=True)

    if not display_jobs:
        if not jobs:
            st.info("📭 No jobs yet. Click 'Run Scan Now' to find jobs from your target companies.")
        else:
            st.info("No jobs match the current view filters.")
        return

    st.subheader(f"Showing {len(display_jobs)} jobs")

    for job in display_jobs:
        status = job.get("status", "new")
        status_icon = {"new": "🆕", "viewed": "👁", "applied": "📤", "dismissed": "❌"}.get(status, "")
        ai_score = job.get("ai_score")
        score_str = f" · AI: {ai_score}" if ai_score is not None else ""
        remote_str = " · 🌐 Remote" if job.get("remote") else ""
        
        with st.expander(
            f"{status_icon} **{job.get('title')}** @ {job.get('company')}{score_str} · {job.get('location','')}{remote_str}"
        ):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Company:** {job.get('company')}")
                st.write(f"**Location:** {job.get('location')} {'(Remote)' if job.get('remote') else ''}")
                st.write(f"**Seniority:** {job.get('seniority', 'N/A')}")
                if job.get("salary"):
                    st.write(f"**Salary:** {job.get('salary')}")
                st.write(f"**Found:** {job.get('found_at','')[:16].replace('T',' ')}")
                if job.get("url"):
                    st.markdown(f"[🔗 Apply / View Full Posting]({job.get('url')})")
                if job.get("ai_reason"):
                    st.info(f"💡 **AI says:** {job.get('ai_reason')}")
                if job.get("description"):
                    with st.expander("📝 Job Description"):
                        st.write(job.get("description", "")[:3000])
            with col2:
                if ai_score is not None:
                    color = "🟢" if ai_score >= 75 else ("🟡" if ai_score >= 50 else "🔴")
                    st.markdown(f"### {color} {ai_score}/100")
                    st.caption("AI Match Score")
                
                new_status = st.selectbox(
                    "Status",
                    ["new", "viewed", "applied", "dismissed"],
                    index=["new", "viewed", "applied", "dismissed"].index(status),
                    key=f"status_{job['id']}"
                )
                if new_status != status:
                    update_job(job["id"], status=new_status)
                    st.rerun()

    # Show filtered out jobs
    if failed:
        with st.expander(f"🚫 {len(failed)} filtered-out jobs"):
            for job in failed[:20]:
                reasons = job.get("filter_reasons", [])
                st.markdown(f"- **{job.get('title')}** @ {job.get('company')} — _{', '.join(reasons)}_")


def _run_scan():
    companies = get_companies()
    active = [c for c in companies if c.get("status") == "active"]
    if not active:
        st.warning("No active companies to scan. Add companies first.")
        return

    all_new_jobs = []
    progress = st.progress(0)
    status_text = st.empty()

    existing_urls = {j.get("url") for j in get_jobs()}

    for i, company in enumerate(active):
        status_text.write(f"Scanning {company['name']}...")
        try:
            scraped = scrape_company(company)
            new = [j for j in scraped if j.get("url") not in existing_urls]
            for j in new:
                j["company"] = company["name"]
            all_new_jobs.extend(new)
            update_job_count(company, len(scraped))
        except Exception as e:
            add_log("error", f"Scan failed for {company['name']}: {e}", "scanner")
        progress.progress((i + 1) / len(active))

    progress.empty()
    status_text.empty()

    if all_new_jobs:
        passed, failed = apply_rule_filters(all_new_jobs)
        from utils.db import get_jobs, save_jobs
        existing = get_jobs()
        # Add new jobs to existing (prepend)
        save_jobs(all_new_jobs + existing)
        st.success(f"✅ Found {len(all_new_jobs)} new jobs · {len(passed)} passed filters")
        add_log("info", f"Scan complete: {len(all_new_jobs)} new jobs, {len(passed)} passed filter", "scanner")
    else:
        st.info("No new jobs found.")
        add_log("info", "Scan complete: no new jobs found", "scanner")


def update_job_count(company, count):
    from utils.db import get_companies, save_companies
    companies = get_companies()
    for c in companies:
        if c["id"] == company["id"]:
            c["jobs_found"] = c.get("jobs_found", 0) + count
            c["last_scanned"] = datetime.now().isoformat()
    save_companies(companies)


def _rerun_filters():
    jobs = get_jobs()
    if not jobs:
        st.warning("No jobs to filter.")
        return
    passed, failed = apply_rule_filters(jobs)
    save_jobs(jobs)  # filters update in-place
    st.success(f"Re-filtered: {len(passed)} passed, {len(failed)} failed")
    add_log("info", f"Re-ran filters: {len(passed)} passed, {len(failed)} failed", "filter")
