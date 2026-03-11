import streamlit as st
from utils.db import get_companies, get_jobs, get_logs, get_config


def show():
    st.markdown('<div class="ph"><h1>Dashboard</h1><p>Your job hunt at a glance</p></div>', unsafe_allow_html=True)

    companies = get_companies()
    jobs      = get_jobs()
    config    = get_config()
    logs      = get_logs()

    passed   = [j for j in jobs if j.get("filter_passed")]
    ranked   = [j for j in jobs if j.get("ai_score") is not None]
    top      = [j for j in ranked if j.get("ai_score", 0) >= 75]
    new_jobs = [j for j in jobs if j.get("status") == "new"]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🏢 Companies",     len(companies), f"{len([c for c in companies if c.get('status')=='active'])} active")
    c2.metric("📋 Total Jobs",    len(jobs))
    c3.metric("✅ Filter Passed", len(passed))
    c4.metric("🤖 Strong (75+)", len(top))
    c5.metric("🆕 Unseen",        len(new_jobs))

    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown('<div class="info-card"><h3>🏆 Top AI-Ranked Matches</h3>', unsafe_allow_html=True)
        top_jobs = sorted(ranked, key=lambda x: x.get("ai_score", 0), reverse=True)[:6]
        if not top_jobs:
            st.info("No ranked jobs yet — add companies and run a scan.")
        else:
            for job in top_jobs:
                score = job.get("ai_score", 0)
                cls   = "score-hi" if score >= 75 else ("score-md" if score >= 50 else "score-lo")
                remote_tag = '<span class="pill pill-indigo">Remote</span>' if job.get("remote") else ""
                new_tag    = '<span class="pill pill-green">New</span>' if job.get("status") == "new" else ""
                link = f"<a href='{job.get('url','')}' target='_blank' style='font-size:11px;color:#6366f1;text-decoration:none;white-space:nowrap;'>View →</a>" if job.get('url') else ""
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:14px;padding:13px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                  <div style="min-width:44px;text-align:center;"><span class="{cls}">{score}</span></div>
                  <div style="flex:1;min-width:0;">
                    <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:14px;color:#fff;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{job.get('title','')}</div>
                    <div style="font-size:12px;color:rgba(255,255,255,0.36);margin-top:2px;">{job.get('company','')} &nbsp;·&nbsp; {job.get('location','')} &nbsp;{remote_tag}{new_tag}</div>
                  </div>
                  {link}
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_r:
        api_ok   = bool(config.get("anthropic_api_key"))
        email_ok = bool(config.get("email_to") and config.get("smtp_password"))
        n_active = len([c for c in companies if c.get("status") == "active"])
        def dot(ok): return '<span class="dot-green"></span>' if ok else '<span class="dot-red"></span>'

        st.markdown(f"""
        <div class="info-card">
          <h3>⚙️ System Status</h3>
          <div style="display:flex;flex-direction:column;gap:10px;font-size:13px;color:rgba(255,255,255,0.62);">
            <div>{dot(api_ok)} API Key &nbsp;{'<span class="pill pill-green">Set</span>' if api_ok else '<span class="pill pill-red">Missing</span>'}</div>
            <div>{dot(email_ok)} Email &nbsp;{'<span class="pill pill-green">Configured</span>' if email_ok else '<span class="pill pill-red">Not set</span>'}</div>
            <div>{dot(n_active>0)} Companies &nbsp;<span class="pill pill-indigo">{n_active} active</span></div>
            <div>{dot(True)} Scan &nbsp;<span class="pill pill-green">{'Enabled' if config.get('scan_enabled',True) else 'Paused'}</span></div>
            <div>{dot(True)} Digest &nbsp;<span class="pill pill-green">{'Enabled' if config.get('digest_enabled',True) else 'Paused'}</span></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        times    = config.get("digest_times", ["08:00", "18:00"])
        interval = config.get("scan_interval_hours", 6)
        st.markdown(f"""
        <div class="info-card">
          <h3>📅 Schedule</h3>
          <div style="font-size:13px;color:rgba(255,255,255,0.45);line-height:2.2;">
            <div>🔄 Scan every <strong style="color:#a5b4fc">{interval}h</strong></div>
            <div>📧 Digests at <strong style="color:#a5b4fc">{' &amp; '.join(times)}</strong></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="info-card"><h3>📝 Recent Activity</h3>', unsafe_allow_html=True)
        if not logs:
            st.markdown('<p style="font-size:12px;color:rgba(255,255,255,0.22);">No activity yet.</p>', unsafe_allow_html=True)
        for log in logs[:5]:
            ts    = log.get("timestamp","")[:16].replace("T"," ")
            level = log.get("level","info")
            icon  = "🔴" if level=="error" else ("🟡" if level=="warning" else "🔵")
            st.markdown(f'<div style="font-size:11.5px;color:rgba(255,255,255,0.38);padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);">{icon} <span style="color:rgba(255,255,255,0.2);">{ts}</span> — {log.get("message","")}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if jobs:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="info-card"><h3>📊 Job Pipeline</h3>', unsafe_allow_html=True)
        stages = [("Scraped", len(jobs)), ("Filter Passed", len(passed)), ("AI Ranked", len(ranked)), ("Strong (75+)", len(top)), ("Applied", len([j for j in jobs if j.get("status")=="applied"]))]
        cols = st.columns(len(stages))
        for col, (label, count) in zip(cols, stages):
            col.metric(label, count)
        st.markdown('</div>', unsafe_allow_html=True)
