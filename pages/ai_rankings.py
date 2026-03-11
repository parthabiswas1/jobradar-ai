import streamlit as st
from utils.db import get_jobs, save_jobs, get_config, add_log
from utils.ranker import rank_jobs_with_ai


def show():
    st.markdown('<div class="main-header">🤖 AI-Ranked Jobs</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Jobs ranked by AI based on your resume and preferences</div>', unsafe_allow_html=True)

    jobs = get_jobs()
    config = get_config()
    passed = [j for j in jobs if j.get("filter_passed")]
    ranked = [j for j in passed if j.get("ai_score") is not None]
    unranked = [j for j in passed if j.get("ai_score") is None]

    # Controls
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🤖 Rank Unranked Jobs", type="primary", disabled=not unranked):
            if not config.get("anthropic_api_key"):
                st.error("Set your Anthropic API key in the Email/Config page first.")
            else:
                with st.spinner(f"Ranking {len(unranked)} jobs with AI..."):
                    result = rank_jobs_with_ai(unranked)
                    # Merge back
                    ranked_ids = {j["id"]: j for j in result}
                    updated = []
                    for j in jobs:
                        if j["id"] in ranked_ids:
                            updated.append(ranked_ids[j["id"]])
                        else:
                            updated.append(j)
                    save_jobs(updated)
                st.success(f"✅ Ranked {len(result)} jobs!")
                st.rerun()
    with col2:
        if st.button("🔄 Re-rank All Jobs"):
            if not config.get("anthropic_api_key"):
                st.error("Set your Anthropic API key first.")
            else:
                with st.spinner(f"Re-ranking {len(passed)} jobs..."):
                    result = rank_jobs_with_ai(passed)
                    ranked_ids = {j["id"]: j for j in result}
                    updated = []
                    for j in jobs:
                        if j["id"] in ranked_ids:
                            updated.append(ranked_ids[j["id"]])
                        else:
                            updated.append(j)
                    save_jobs(updated)
                st.success(f"✅ Re-ranked {len(result)} jobs!")
                st.rerun()
    with col3:
        min_score = st.slider("Min Score to Show", 0, 100,
                              value=config.get("min_ai_score", 60), step=5)

    st.markdown("---")

    # Stats
    if ranked:
        m1, m2, m3, m4 = st.columns(4)
        scores = [j.get("ai_score", 0) for j in ranked]
        m1.metric("Total Ranked", len(ranked))
        m2.metric("🟢 Strong (75+)", len([s for s in scores if s >= 75]))
        m3.metric("🟡 Good (50-74)", len([s for s in scores if 50 <= s < 75]))
        m4.metric("🔴 Weak (<50)", len([s for s in scores if s < 50]))
    
    if unranked:
        st.info(f"⚠️ {len(unranked)} filter-passed jobs haven't been ranked yet. Click 'Rank Unranked Jobs'.")

    if not ranked:
        st.info("No ranked jobs yet. Make sure you have filter-passed jobs and an Anthropic API key set.")
        return

    # Sort and filter
    show_jobs = sorted(ranked, key=lambda x: x.get("ai_score", 0), reverse=True)
    show_jobs = [j for j in show_jobs if j.get("ai_score", 0) >= min_score]

    st.subheader(f"📊 {len(show_jobs)} Jobs (score ≥ {min_score})")

    for job in show_jobs:
        score = job.get("ai_score", 0)
        color = "🟢" if score >= 75 else ("🟡" if score >= 50 else "🔴")
        
        # Build header
        header = f"{color} **{score}/100** · **{job.get('title')}** @ {job.get('company')} · {job.get('location', '')}"
        if job.get("remote"):
            header += " · 🌐"
        
        with st.expander(header):
            col_l, col_r = st.columns([3, 1])
            with col_l:
                # Score bar
                st.progress(score / 100)
                
                if job.get("ai_reason"):
                    st.write(f"**💡 Why it matches:** {job.get('ai_reason')}")
                
                highlights = job.get("ai_highlights", [])
                concerns = job.get("ai_concerns", [])
                
                if highlights:
                    with st.container():
                        st.write("**✅ Strengths:**")
                        for h in highlights:
                            st.write(f"  - {h}")
                
                if concerns:
                    with st.container():
                        st.write("**⚠️ Concerns:**")
                        for c in concerns:
                            st.write(f"  - {c}")
                
                st.caption(f"Seniority: {job.get('seniority','N/A')} · Found: {job.get('found_at','')[:10]}")
            
            with col_r:
                st.metric("Match Score", f"{score}/100")
                if job.get("url"):
                    st.markdown(f"[🔗 View Job]({job.get('url')})")
                
                status = job.get("status", "new")
                new_status = st.selectbox(
                    "Track as",
                    ["new", "viewed", "applied", "dismissed"],
                    index=["new", "viewed", "applied", "dismissed"].index(status),
                    key=f"rank_status_{job['id']}"
                )
                if new_status != status:
                    from utils.db import update_job
                    update_job(job["id"], status=new_status)
                    st.rerun()
