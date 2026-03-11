import streamlit as st
from utils.db import get_companies, save_companies, add_company, update_company, delete_company, add_log, get_config
from utils.scraper import ai_find_career_url, search_company_url, detect_ats


def show():
    st.markdown('<div class="ph"><h1>Target Companies</h1><p>Manage companies to monitor for job openings</p></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["➕ Add Company", "📋 Manage Companies", "🔍 Find Company URL"])

    # ── Tab 1: Add Company ────────────────────────────────────────────────
    with tab1:
        st.subheader("Add a New Target Company")
        st.info("💡 Just enter the company name and website URL — the AI will automatically find their careers page, even if it has an unusual name.")

        with st.form("add_company_form"):
            col1, col2 = st.columns(2)
            with col1:
                name      = st.text_input("Company Name *", placeholder="e.g. Parloa")
                url       = st.text_input("Company Website URL *", placeholder="https://parloa.com")
                career_url= st.text_input("Career Page URL (leave blank — AI will find it)", placeholder="Auto-detected")
            with col2:
                ats_type  = st.selectbox("ATS Type", ["auto-detect", "greenhouse", "lever", "workday",
                                                        "ashby", "smartrecruiters", "jobvite", "generic"])
                status    = st.selectbox("Status", ["active", "paused"])
                notes     = st.text_area("Notes", placeholder="Any notes...", height=80)

            submitted = st.form_submit_button("➕ Add Company", type="primary")
            if submitted:
                if not name:
                    st.error("Company name is required.")
                elif not url:
                    st.error("Company website URL is required.")
                else:
                    config  = get_config()
                    api_key = config.get("anthropic_api_key", "")

                    # AI-powered career page detection
                    if not career_url:
                        with st.spinner(f"🤖 AI is finding {name}'s career page..."):
                            result     = ai_find_career_url(url, name, api_key)
                            career_url = result.get("career_url", "")
                            confidence = result.get("confidence", "low")
                            page_name  = result.get("page_name", "")
                            reasoning  = result.get("reasoning", "")
                            method     = result.get("method", "")
                            if ats_type == "auto-detect":
                                ats_type = result.get("ats_type", "generic")

                        if career_url:
                            label = f'"{page_name}"' if page_name else "career page"
                            st.success(f"✅ Found {label}: {career_url} (confidence: {confidence})")
                            if reasoning:
                                st.caption(f"💡 {reasoning}")
                        else:
                            st.warning("⚠️ Could not auto-detect career page. You can add it manually later in Manage Companies.")

                    if ats_type == "auto-detect":
                        ats_type = detect_ats(career_url) if career_url else "generic"

                    add_company(name, url, career_url, ats_type, status, notes)
                    add_log("info", f"Added company: {name} — career: {career_url}", "companies")
                    st.success(f"✅ {name} added!")
                    st.rerun()

    # ── Tab 2: Manage Companies ───────────────────────────────────────────
    with tab2:
        companies = get_companies()
        if not companies:
            st.info("No companies added yet. Use the 'Add Company' tab to get started.")
        else:
            active = len([c for c in companies if c.get("status") == "active"])
            st.markdown(f"**{len(companies)} companies** · {active} active · {len(companies)-active} paused")

            search = st.text_input("🔍 Search companies", placeholder="Filter by name...")
            filtered = [c for c in companies if search.lower() in c.get("name","").lower()] if search else companies

            for company in filtered:
                with st.expander(f"{'🟢' if company.get('status')=='active' else '⏸'} **{company['name']}**  |  {company.get('ats_type','?').upper()}  |  Jobs: {company.get('jobs_found',0)}"):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        new_name   = st.text_input("Name",       value=company.get("name",""),       key=f"name_{company['id']}")
                        new_url    = st.text_input("Website",    value=company.get("url",""),        key=f"url_{company['id']}")
                        new_career = st.text_input("Career URL", value=company.get("career_url",""), key=f"career_{company['id']}")
                        new_notes  = st.text_area("Notes",       value=company.get("notes",""),      key=f"notes_{company['id']}", height=60)
                    with col2:
                        ats_opts = ["greenhouse","lever","workday","ashby","smartrecruiters","jobvite","generic"]
                        cur_ats  = company.get("ats_type","generic")
                        cur_ats  = cur_ats if cur_ats in ats_opts else "generic"
                        new_ats  = st.selectbox("ATS", ats_opts, index=ats_opts.index(cur_ats), key=f"ats_{company['id']}")
                        new_status = st.selectbox("Status", ["active","paused"],
                                                  index=0 if company.get("status")=="active" else 1,
                                                  key=f"status_{company['id']}")
                        if company.get("last_scanned"):
                            st.caption(f"Last scanned: {company['last_scanned'][:16].replace('T',' ')}")

                        b1, b2 = st.columns(2)
                        with b1:
                            if st.button("💾 Save", key=f"save_{company['id']}", use_container_width=True):
                                update_company(company["id"], name=new_name, url=new_url,
                                               career_url=new_career, ats_type=new_ats,
                                               status=new_status, notes=new_notes)
                                st.success("Saved!")
                                st.rerun()
                        with b2:
                            if st.button("🗑 Delete", key=f"del_{company['id']}", use_container_width=True):
                                delete_company(company["id"])
                                add_log("info", f"Deleted: {company['name']}", "companies")
                                st.rerun()

                    # AI re-detect button
                    if st.button("🤖 Re-detect Career Page with AI", key=f"redetect_{company['id']}"):
                        if company.get("url"):
                            config  = get_config()
                            api_key = config.get("anthropic_api_key", "")
                            with st.spinner("🤖 AI searching for career page..."):
                                result = ai_find_career_url(company["url"], company["name"], api_key)
                            if result.get("career_url"):
                                update_company(company["id"],
                                               career_url=result["career_url"],
                                               ats_type=result.get("ats_type","generic"))
                                st.success(f"✅ Found: {result['career_url']} ({result.get('confidence','?')} confidence)")
                                if result.get("reasoning"):
                                    st.caption(f"💡 {result['reasoning']}")
                                st.rerun()
                            else:
                                st.warning("Could not find career page. Try entering it manually.")

    # ── Tab 3: Find Company URL ───────────────────────────────────────────
    with tab3:
        st.subheader("🔍 Find Company Website by Name")
        st.write("Don't know a company's URL? Enter the name and we'll try to find it.")

        search_name = st.text_input("Company Name", placeholder="e.g. Figma, Notion, Linear", key="company_search_input")
        if st.button("🔍 Search", type="primary") and search_name:
            with st.spinner(f"Searching for {search_name}..."):
                raw = search_company_url(search_name)
            seen, unique = set(), []
            for c in raw:
                if c['url'].rstrip("/") not in seen:
                    seen.add(c['url'].rstrip("/"))
                    unique.append(c)
            st.session_state["search_candidates"] = unique
            st.session_state["search_name"] = search_name

        if st.session_state.get("search_candidates"):
            unique = st.session_state["search_candidates"]
            sname  = st.session_state.get("search_name", "")
            st.success(f"Found {len(unique)} candidate(s):")
            for i, c in enumerate(unique):
                col1, col2 = st.columns([3, 1])
                col1.write(f"🌐 {c['url']}")
                if col2.button("➕ Add This", key=f"cbtn_{i}_{abs(hash(c['url']))%99999}"):
                    st.session_state["prefill_url"]  = c["url"]
                    st.session_state["prefill_name"] = sname
                    st.session_state["search_candidates"] = []
                    st.info(f"✅ Go to 'Add Company' tab — URL pre-noted: {c['url']}")
        elif "search_candidates" in st.session_state:
            st.warning("No candidates found automatically.")
            if st.session_state.get("search_name"):
                q = st.session_state["search_name"].replace(" ", "+")
                st.markdown(f"Try: [Google Search](https://google.com/search?q={q}+careers+site)")
