import streamlit as st
from datetime import datetime
from utils.db import get_jobs, get_companies, save_companies, update_job, save_jobs, add_log, get_config
from utils.scraper import scrape_company
from utils.ranker import apply_rule_filters


def show():
    st.markdown('<div class="main-header">📋 Matched Jobs</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Jobs that passed your filter rules</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1, 1])

    # ── Run Scan ───────────────────────────────────────────────────────────
    with col1:
        if st.button("🔄 Run Scan Now", type="primary"):
            companies = get_companies()
            active    = [c for c in companies if c.get("status") == "active"]
            if not active:
                st.warning("No active companies to scan. Add companies first.")
            else:
                all_new_jobs  = []
                existing_urls = {j.get("url") for j in get_jobs()}
                progress      = st.progress(0)
                status_text   = st.empty()

                for i, company in enumerate(active):
                    status_text.write(f"🔍 Scanning {company['name']}...")
                    try:
                        scraped = scrape_company(company)
                        new     = [j for j in scraped if j.get("url") not in existing_urls]
                        for j in new:
                            j["company"] = company["name"]
                        all_new_jobs.extend(new)
                        existing_urls.update(j.get("url") for j in new)
                        # Update company scan metadata
                        for c in companies:
                            if c["id"] == company["id"]:
                                c["jobs_found"]  = c.get("jobs_found", 0) + len(scraped)
                                c["last_scanned"] = datetime.now().isoformat()
                        save_companies(companies)
                    except Exception as e:
                        add_log("error", f"Scan failed for {company['name']}: {e}", "scanner")
                    progress.progress((i + 1) / len(active))

                progress.empty()
                status_text.empty()

                if all_new_jobs:
                    passed, _ = apply_rule_filters(all_new_jobs)
                    existing  = get_jobs()
                    save_jobs(all_new_jobs + existing)
                    st.success(f"✅ Found {len(all_new_jobs)} new jobs · {len(passed)} passed filters")
                    add_log("info", f"Scan: {len(all_new_jobs)} new, {len(passed)} passed filter", "scanner")
                else:
                    st.info("No new jobs found this scan.")
                    add_log("info", "Scan complete: no new jobs found", "scanner")
                st.rerun()

    # ── Re-run Filters ────────────────────────────────────────────────────
    with col2:
        if st.button("♻️ Re-run Filters"):
            jobs = get_jobs()
            if not jobs:
                st.warning("No jobs to filter.")
            else:
                passed, failed = apply_rule_filters(jobs)
                save_jobs(jobs)
                st.success(f"Re-filtered: {len(passed)} passed, {len(failed)} failed")
                add_log("info", f"Re-ran filters: {len(passed)} passed", "filter")
                st.rerun()

    with col3:
        if st.button("🗑 Clear All Jobs"):
            save_jobs([])
            add_log("info", "Cleared all jobs", "matched_jobs")
            st.rerun()

    # ── Filters / display ─────────────────────────────────────────────────
    jobs = get_jobs()

    col_a, col_b, col_c, col_d = st.columns(4)
    total    = len(jobs)
    passed   = len([j for j in jobs if j.get("filter_passed")])
    new_jobs = len([j for j in jobs if j.get("status") == "new"])
    applied  = len([j for j in jobs if j.get("status") == "applied"])
    col_a.metric("Total Jobs",   total)
    col_b.metric("Passed Filter", passed)
    col_c.metric("New / Unseen", new_jobs)
    col_d.metric("Applied",      applied)

    if not jobs:
        st.info("No jobs yet. Click 'Run Scan Now' to start.")
        return

    # ── Display controls ──────────────────────────────────────────────────
    st.markdown("---")
    f1, f2, f3 = st.columns([2, 2, 2])
    with f1:
        show_filter = st.selectbox("Show", ["All Jobs", "Passed Filter Only", "New Only", "Applied"], key="mj_show")
    with f2:
        company_list = ["All"] + sorted({j.get("company","") for j in jobs if j.get("company")})
        filter_company = st.selectbox("Company", company_list, key="mj_company")
    with f3:
        sort_by = st.selectbox("Sort by", ["Newest First", "Score High→Low", "Company"], key="mj_sort")

    # Apply filters
    display = jobs[:]
    if show_filter == "Passed Filter Only": display = [j for j in display if j.get("filter_passed")]
    elif show_filter == "New Only":         display = [j for j in display if j.get("status") == "new"]
    elif show_filter == "Applied":          display = [j for j in display if j.get("status") == "applied"]
    if filter_company != "All":             display = [j for j in display if j.get("company") == filter_company]

    if sort_by == "Score High→Low":   display.sort(key=lambda j: j.get("ai_score", 0), reverse=True)
    elif sort_by == "Company":        display.sort(key=lambda j: j.get("company", ""))

    st.markdown(f"**Showing {len(display)} jobs**")

    for job in display:
        score  = job.get("ai_score", 0)
        passed = job.get("filter_passed", False)
        status = job.get("status", "new")

        badge  = "🟢" if passed else "🔴"
        s_col  = "#4ade80" if score >= 75 else "#fbbf24" if score >= 50 else "#f87171"

        with st.expander(f"{badge} **{job.get('title','')}** — {job.get('company','')} · {job.get('location','')}"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{job.get('title','')}** at **{job.get('company','')}**")
                st.caption(f"📍 {job.get('location','')} · 👔 {job.get('seniority','')} · {'🌐 Remote' if job.get('remote') else '🏢 On-site'}")
                if job.get("url"):
                    st.markdown(f"[🔗 View Job]({job['url']})")
                desc = job.get("description","")
                if desc:
                    st.markdown(desc[:400] + ("..." if len(desc) > 400 else ""))
            with c2:
                if score:
                    st.markdown(f"<div style='text-align:center;font-size:28px;font-weight:800;color:{s_col}'>{score}</div><div style='text-align:center;font-size:11px;color:gray'>AI Score</div>", unsafe_allow_html=True)
                st.markdown(f"**Filter:** {'✅ Passed' if passed else '❌ Failed'}")
                new_status = st.selectbox("Status", ["new","viewed","applied","dismissed"],
                                          index=["new","viewed","applied","dismissed"].index(status) if status in ["new","viewed","applied","dismissed"] else 0,
                                          key=f"status_{job.get('id','')}")
                if new_status != status:
                    update_job(job["id"], status=new_status)
                    st.rerun()
                if job.get("filter_reason"):
                    st.caption(f"Filter: {job['filter_reason']}")
