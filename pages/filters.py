import streamlit as st
from utils.db import get_filters, save_filters, get_resume, save_resume


def show():
    st.markdown('<div class="main-header">🔍 Job Filters & Preferences</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Define what jobs to keep and what to skip</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🎛 Filter Rules", "📄 Resume & Background"])

    with tab1:
        filters = get_filters()

        st.subheader("Job Title Matching")
        st.caption("Jobs matching ANY of these titles will pass. Leave empty to allow all titles.")
        titles_input = st.text_area(
            "Target Job Titles (one per line)",
            value="\n".join(filters.get("titles", [])),
            placeholder="Software Engineer\nSenior Backend Engineer\nStaff Engineer\nPrincipal Engineer",
            height=120
        )

        st.markdown("---")
        st.subheader("📍 Location")
        col1, col2 = st.columns(2)
        with col1:
            locations_input = st.text_area(
                "Preferred Locations (one per line)",
                value="\n".join(filters.get("locations", [])),
                placeholder="San Francisco\nNew York\nRemote\nSeattle",
                height=100
            )
        with col2:
            remote_only = st.checkbox("🌐 Remote Only", value=filters.get("remote_only", False))
            st.caption("If checked, only remote jobs will pass regardless of location filter.")

        st.markdown("---")
        st.subheader("💼 Seniority Level")
        seniority_options = ["Intern", "Junior", "Mid", "Senior", "Director+"]
        selected_seniority = st.multiselect(
            "Target Seniority Levels",
            seniority_options,
            default=filters.get("seniority", [])
        )

        st.markdown("---")
        st.subheader("🔑 Keywords")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**✅ Must Include** (at least one)")
            include_input = st.text_area(
                "Include Keywords (one per line)",
                value="\n".join(filters.get("keywords_include", [])),
                placeholder="python\nkubernetes\nmachine learning",
                height=100,
                label_visibility="collapsed"
            )
        with col2:
            st.write("**❌ Must Exclude** (none of these)")
            exclude_input = st.text_area(
                "Exclude Keywords (one per line)",
                value="\n".join(filters.get("keywords_exclude", [])),
                placeholder="manager\ndirector\nclearance required",
                height=100,
                label_visibility="collapsed"
            )

        st.markdown("---")
        st.subheader("💰 Salary Range (Optional)")
        col1, col2 = st.columns(2)
        with col1:
            min_salary = st.number_input("Min Salary ($)", min_value=0, step=10000,
                                          value=filters.get("min_salary") or 0)
        with col2:
            max_salary = st.number_input("Max Salary ($)", min_value=0, step=10000,
                                          value=filters.get("max_salary") or 0)

        st.markdown("---")
        if st.button("💾 Save Filters", type="primary", use_container_width=True):
            new_filters = {
                "titles": [t.strip() for t in titles_input.split("\n") if t.strip()],
                "locations": [l.strip() for l in locations_input.split("\n") if l.strip()],
                "seniority": selected_seniority,
                "remote_only": remote_only,
                "keywords_include": [k.strip() for k in include_input.split("\n") if k.strip()],
                "keywords_exclude": [k.strip() for k in exclude_input.split("\n") if k.strip()],
                "min_salary": min_salary if min_salary > 0 else None,
                "max_salary": max_salary if max_salary > 0 else None,
            }
            save_filters(new_filters)
            st.success("✅ Filters saved successfully!")

        # Preview
        with st.expander("👁 Preview Current Filters"):
            current = get_filters()
            st.json(current)

    with tab2:
        st.subheader("📄 Resume / Background")
        st.write("Paste your resume or background summary. The AI will use this to rank job matches.")
        
        resume_text = get_resume()
        
        new_resume = st.text_area(
            "Resume / Background",
            value=resume_text,
            height=400,
            placeholder="""Paste your resume here, or write a background summary like:

5 years of backend engineering experience with Python, Go, and Kubernetes.
Strong background in distributed systems, microservices, and cloud infrastructure (AWS, GCP).
Previously at Stripe and Cloudflare. 
Currently targeting senior IC roles at high-growth startups.
Prefer remote or San Francisco Bay Area positions.
Interested in: fintech, developer tools, AI infrastructure.
Not interested in: sales engineering, management roles, government/defense.
"""
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Resume", type="primary", use_container_width=True):
                save_resume(new_resume)
                st.success("✅ Resume saved!")
        with col2:
            if st.button("🗑 Clear Resume", use_container_width=True):
                save_resume("")
                st.rerun()
        
        if resume_text:
            st.caption(f"📊 Resume length: {len(resume_text)} characters / ~{len(resume_text.split())} words")
