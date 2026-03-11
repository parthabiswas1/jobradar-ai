import streamlit as st
from datetime import datetime
from utils.db import get_companies, get_jobs, get_logs, get_config


def show():
    st.markdown('<div class="main-header">🏠 Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Overview of your AI job hunting system</div>', unsafe_allow_html=True)

    companies = get_companies()
    jobs = get_jobs()
    config = get_config()
    logs = get_logs()

    # ── Top metrics ──────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("🏢 Companies", len(companies),
                  delta=f"{len([c for c in companies if c.get('status')=='active'])} active")
    with c2:
        st.metric("📋 Total Jobs", len(jobs))
    with c3:
        passed = [j for j in jobs if j.get("filter_passed")]
        st.metric("✅ Filter Passed", len(passed))
    with c4:
        ranked = [j for j in jobs if j.get("ai_score") is not None]
        top = [j for j in ranked if j.get("ai_score", 0) >= 75]
        st.metric("🤖 Strong Matches", len(top))
    with c5:
        new_jobs = [j for j in jobs if j.get("status") == "new"]
        st.metric("🆕 New (Unseen)", len(new_jobs))

    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🏆 Top AI-Ranked Jobs")
        top_jobs = sorted(
            [j for j in jobs if j.get("ai_score") is not None],
            key=lambda x: x.get("ai_score", 0), reverse=True
        )[:8]

        if not top_jobs:
            st.info("No ranked jobs yet. Run a scan to find jobs!")
        else:
            for job in top_jobs:
                score = job.get("ai_score", 0)
                color = "🟢" if score >= 75 else ("🟡" if score >= 50 else "🔴")
                with st.expander(f"{color} **{job.get('title')}** @ {job.get('company')} — Score: {score}"):
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"📍 {job.get('location', 'N/A')}")
                    c2.write(f"💼 {job.get('seniority', 'N/A')}")
                    c3.write(f"🌐 {'Remote' if job.get('remote') else 'On-site'}")
                    if job.get("ai_reason"):
                        st.write(f"💡 {job.get('ai_reason')}")
                    if job.get("url"):
                        st.markdown(f"[🔗 View Job Posting]({job.get('url')})")

    with col2:
        st.subheader("⚙️ System Status")

        api_key = config.get("anthropic_api_key", "")
        email = config.get("email_to", "")
        n_active = len([c for c in companies if c.get("status") == "active"])

        statuses = [
            ("API Key", "✅ Set" if api_key else "❌ Not set", bool(api_key)),
            ("Email", "✅ Set" if email else "❌ Not set", bool(email)),
            ("Companies", f"✅ {n_active} active" if n_active else "❌ None added", n_active > 0),
            ("Scan", "✅ Enabled" if config.get("scan_enabled") else "⏸ Disabled", True),
            ("Digest", "✅ Enabled" if config.get("digest_enabled") else "⏸ Disabled", True),
        ]
        for name, label, ok in statuses:
            st.markdown(f"**{name}**: {label}")

        st.markdown("---")
        st.subheader("📅 Next Scan")
        interval = config.get("scan_interval_hours", 6)
        st.write(f"Every {interval} hours")
        
        times = config.get("digest_times", ["08:00", "18:00"])
        st.subheader("📧 Digest Times")
        st.write(", ".join(times))

        st.markdown("---")
        st.subheader("📝 Recent Logs")
        for log in logs[:5]:
            ts = log.get("timestamp", "")[:16].replace("T", " ")
            level = log.get("level", "info")
            icon = "🔴" if level == "error" else ("🟡" if level == "warning" else "🔵")
            st.markdown(f"<small>{icon} {ts} — {log.get('message','')}</small>", unsafe_allow_html=True)

    # ── Jobs found by company ─────────────────────────────────────────────
    if companies:
        st.markdown("---")
        st.subheader("📊 Jobs by Company")
        cols = st.columns(min(len(companies), 4))
        for i, company in enumerate(companies[:8]):
            company_jobs = [j for j in jobs if j.get("company") == company["name"]]
            with cols[i % 4]:
                st.metric(
                    company["name"][:20],
                    len(company_jobs),
                    delta=f"{len([j for j in company_jobs if j.get('filter_passed')])} matched"
                )
