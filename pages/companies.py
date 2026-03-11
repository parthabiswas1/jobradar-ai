import streamlit as st
from utils.db import get_companies, save_companies, add_company, update_company, delete_company, add_log
from utils.scraper import find_career_url, search_company_url, detect_ats


def show():
    st.markdown('<div class="main-header">🏢 Target Companies</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Manage companies to monitor for job openings</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["➕ Add Company", "📋 Manage Companies", "🔍 Find Company URL"])

    # ── Tab 1: Add Company ────────────────────────────────────────────────
    with tab1:
        st.subheader("Add a New Target Company")
        with st.form("add_company_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Company Name *", placeholder="e.g. Stripe")
                url = st.text_input("Company Website URL", placeholder="https://stripe.com")
                career_url = st.text_input("Career Page URL (optional)", placeholder="https://stripe.com/jobs")
            with col2:
                ats_type = st.selectbox("ATS Type", ["auto-detect", "greenhouse", "lever", "workday",
                                                      "ashby", "smartrecruiters", "jobvite", "generic"])
                status = st.selectbox("Status", ["active", "paused"])
                notes = st.text_area("Notes", placeholder="Any notes about this company...", height=80)
            
            submitted = st.form_submit_button("➕ Add Company", type="primary")
            if submitted:
                if not name:
                    st.error("Company name is required.")
                else:
                    # Auto-detect career URL if not provided
                    if url and not career_url:
                        with st.spinner("Detecting career page..."):
                            result = find_career_url(url, name)
                            career_url = result.get("career_url", "")
                            if ats_type == "auto-detect":
                                ats_type = result.get("ats_type", "generic")
                            if career_url:
                                st.success(f"✅ Found career page: {career_url} ({ats_type})")
                    
                    if ats_type == "auto-detect":
                        ats_type = detect_ats(career_url) if career_url else "generic"
                    
                    add_company(name, url, career_url, ats_type, status, notes)
                    add_log("info", f"Added company: {name}", "companies")
                    st.success(f"✅ {name} added successfully!")
                    st.rerun()

    # ── Tab 2: Manage Companies ───────────────────────────────────────────
    with tab2:
        companies = get_companies()
        if not companies:
            st.info("No companies added yet. Use the 'Add Company' tab to get started.")
        else:
            # Quick stats
            active = len([c for c in companies if c.get("status") == "active"])
            st.markdown(f"**{len(companies)} companies** · {active} active · {len(companies)-active} paused")
            
            search = st.text_input("🔍 Search companies", placeholder="Filter by name...")
            
            filtered = companies
            if search:
                filtered = [c for c in companies if search.lower() in c.get("name", "").lower()]
            
            for company in filtered:
                with st.expander(f"{'🟢' if company.get('status')=='active' else '⏸'} **{company['name']}**  |  {company.get('ats_type','?').upper()}  |  Jobs found: {company.get('jobs_found',0)}"):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        new_name = st.text_input("Name", value=company.get("name", ""), key=f"name_{company['id']}")
                        new_url = st.text_input("Website", value=company.get("url", ""), key=f"url_{company['id']}")
                        new_career = st.text_input("Career URL", value=company.get("career_url", ""), key=f"career_{company['id']}")
                        new_notes = st.text_area("Notes", value=company.get("notes", ""), key=f"notes_{company['id']}", height=60)
                    with col2:
                        new_ats = st.selectbox("ATS", ["greenhouse", "lever", "workday", "ashby",
                                                        "smartrecruiters", "jobvite", "generic"],
                                               index=["greenhouse","lever","workday","ashby",
                                                       "smartrecruiters","jobvite","generic"].index(
                                                   company.get("ats_type","generic") if company.get("ats_type","generic") in
                                                   ["greenhouse","lever","workday","ashby","smartrecruiters","jobvite","generic"] else "generic"),
                                               key=f"ats_{company['id']}")
                        new_status = st.selectbox("Status", ["active", "paused"],
                                                  index=0 if company.get("status") == "active" else 1,
                                                  key=f"status_{company['id']}")
                        
                        if company.get("last_scanned"):
                            st.caption(f"Last scanned: {company['last_scanned'][:16].replace('T',' ')}")
                        
                        btn1, btn2 = st.columns(2)
                        with btn1:
                            if st.button("💾 Save", key=f"save_{company['id']}", use_container_width=True):
                                update_company(company["id"], name=new_name, url=new_url,
                                               career_url=new_career, ats_type=new_ats,
                                               status=new_status, notes=new_notes)
                                st.success("Saved!")
                                st.rerun()
                        with btn2:
                            if st.button("🗑 Delete", key=f"del_{company['id']}", use_container_width=True, type="secondary"):
                                delete_company(company["id"])
                                add_log("info", f"Deleted company: {company['name']}", "companies")
                                st.rerun()
                    
                    # Re-detect career URL button
                    if st.button("🔄 Re-detect Career URL", key=f"redetect_{company['id']}"):
                        if company.get("url"):
                            with st.spinner("Detecting..."):
                                result = find_career_url(company["url"], company["name"])
                                if result.get("career_url"):
                                    update_company(company["id"],
                                                   career_url=result["career_url"],
                                                   ats_type=result.get("ats_type", "generic"))
                                    st.success(f"Found: {result['career_url']}")
                                    st.rerun()
                                else:
                                    st.warning("Could not auto-detect career page. Please enter it manually.")

    # ── Tab 3: Find Company URL ──────────────────────────────────────────
    with tab3:
        st.subheader("🔍 Find Company Website by Name")
        st.write("Don't know a company's URL? Enter the name and we'll try to find it.")
        
        search_name = st.text_input("Company Name", placeholder="e.g. Figma, Notion, Linear")
        if st.button("🔍 Search", type="primary") and search_name:
            with st.spinner(f"Searching for {search_name}..."):
                candidates = search_company_url(search_name)
            
            if candidates:
                # Deduplicate by URL
                seen_urls = set()
                unique_candidates = []
                for c in candidates:
                    if c['url'] not in seen_urls:
                        seen_urls.add(c['url'])
                        unique_candidates.append(c)
                
                st.success(f"Found {len(unique_candidates)} candidate(s):")
                for i, c in enumerate(unique_candidates):
                    col1, col2 = st.columns([3, 1])
                    col1.write(f"🌐 {c['url']}")
                    if col2.button("➕ Add This", key=f"add_{i}_{c['url'][-20:]}"):
                        st.session_state["prefill_url"] = c["url"]
                        st.session_state["prefill_name"] = search_name
                        st.info(f"Go to 'Add Company' tab and use URL: {c['url']}")
            else:
                st.warning("No candidates found automatically. Try searching manually.")
                st.markdown(f"Try: [Google Search](https://google.com/search?q={search_name.replace(' ','+')}+careers+site)")
