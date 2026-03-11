import re
import streamlit as st
from utils.db import get_companies, save_companies, add_company, update_company, delete_company, add_log, get_config
from utils.scraper import ai_find_career_url, detect_ats


def _name_from_url(url: str) -> str:
    """Extract a pretty company name from a URL."""
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc or url
        host = host.replace("www.", "").split(".")[0]
        return host.strip().title()
    except Exception:
        return ""


def show():
    st.markdown('<div class="ph"><h1>Target Companies</h1><p>Manage companies to monitor for job openings</p></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["➕ Add Company", "📋 Manage Companies", "🔍 Find Company URL"])

    # ── Tab 1: Add Company ────────────────────────────────────────────────
    with tab1:
        st.info("💡 Enter the website URL — company name is auto-filled. The AI will find their careers page automatically.")

        # ── URL input — drives everything ──────────────────────────────────
        # Read any prefilled values from Find URL tab
        prefill_url  = st.session_state.pop("prefill_url",  "")
        prefill_name = st.session_state.pop("prefill_name", "")

        url_input = st.text_input(
            "Company Website URL *",
            value=prefill_url,
            placeholder="https://parloa.com",
            key="add_url_input"
        )

        # Auto-suggest company name from URL
        suggested_name = prefill_name or (_name_from_url(url_input) if url_input else "")
        name_input = st.text_input(
            "Company Name *",
            value=suggested_name,
            key="add_name_input",
            help="Auto-filled from URL — edit if needed"
        )

        col1, col2 = st.columns(2)
        with col1:
            status_input = st.selectbox("Status", ["active", "paused"], key="add_status")
        with col2:
            notes_input = st.text_input("Notes (optional)", placeholder="e.g. Series B fintech startup", key="add_notes")

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("➕ Add Company & Find Career Page", type="primary", use_container_width=True):
            url  = url_input.strip()
            name = name_input.strip()

            if not url:
                st.error("Please enter a website URL.")
            elif not name:
                st.error("Please enter a company name.")
            else:
                # Normalise URL
                if not url.startswith("http"):
                    url = "https://" + url

                config  = get_config()
                api_key = config.get("anthropic_api_key", "")

                career_url = ""
                ats_type   = "generic"

                with st.status(f"🤖 Finding {name}'s career page...", expanded=True) as status_box:
                    st.write(f"📡 Fetching homepage: {url}")
                    result     = ai_find_career_url(url, name, api_key)
                    career_url = result.get("career_url", "")
                    ats_type   = result.get("ats_type", "generic")
                    confidence = result.get("confidence", "low")
                    page_name  = result.get("page_name", "")
                    reasoning  = result.get("reasoning", "")
                    method     = result.get("method", "keyword")

                    if career_url:
                        st.write(f"✅ Found: **{page_name or 'Career page'}** → {career_url}")
                        st.write(f"🏷 ATS: {ats_type.upper()} · Confidence: {confidence}")
                        if reasoning:
                            st.write(f"💡 {reasoning}")
                        status_box.update(label=f"✅ Career page found!", state="complete")
                    else:
                        st.write("⚠️ Could not find career page — you can add it manually later.")
                        status_box.update(label="⚠️ Career page not found", state="error")

                # Save regardless
                add_company(name, url, career_url, ats_type, status_input, notes_input)
                add_log("info", f"Added: {name} → {career_url or 'no career URL'}", "companies")
                st.success(f"✅ **{name}** added to your target companies!")

                # Clear inputs via session state
                st.session_state["add_url_input"]  = ""
                st.session_state["add_name_input"] = ""
                st.rerun()

    # ── Tab 2: Manage Companies ───────────────────────────────────────────
    with tab2:
        companies = get_companies()
        if not companies:
            st.info("No companies added yet. Use the 'Add Company' tab to get started.")
        else:
            active = len([c for c in companies if c.get("status") == "active"])
            st.markdown(f"**{len(companies)} companies** · {active} active · {len(companies)-active} paused")

            search = st.text_input("🔍 Search", placeholder="Filter by name...", key="manage_search")
            filtered = [c for c in companies if search.lower() in c.get("name","").lower()] if search else companies

            for company in filtered:
                career_set = "✅" if company.get("career_url") else "⚠️"
                with st.expander(
                    f"{'🟢' if company.get('status')=='active' else '⏸'} **{company['name']}** "
                    f"· {company.get('ats_type','?').upper()} "
                    f"· {career_set} Career URL "
                    f"· {company.get('jobs_found',0)} jobs"
                ):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        new_name   = st.text_input("Name",       value=company.get("name",""),       key=f"name_{company['id']}")
                        new_url    = st.text_input("Website",    value=company.get("url",""),        key=f"url_{company['id']}")
                        new_career = st.text_input("Career URL", value=company.get("career_url",""), key=f"career_{company['id']}")
                        new_notes  = st.text_area("Notes",       value=company.get("notes",""),      key=f"notes_{company['id']}", height=60)
                    with col2:
                        ats_opts  = ["greenhouse","lever","workday","ashby","smartrecruiters","jobvite","generic"]
                        cur_ats   = company.get("ats_type","generic")
                        cur_ats   = cur_ats if cur_ats in ats_opts else "generic"
                        new_ats   = st.selectbox("ATS", ats_opts, index=ats_opts.index(cur_ats), key=f"ats_{company['id']}")
                        new_status= st.selectbox("Status", ["active","paused"],
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

                    if st.button("🤖 Re-detect Career Page with AI", key=f"redetect_{company['id']}"):
                        config  = get_config()
                        api_key = config.get("anthropic_api_key", "")
                        with st.status("🤖 AI searching...", expanded=True) as s:
                            result = ai_find_career_url(company.get("url",""), company["name"], api_key)
                            if result.get("career_url"):
                                st.write(f"✅ {result['career_url']}")
                                if result.get("reasoning"): st.write(f"💡 {result['reasoning']}")
                                s.update(label="✅ Found!", state="complete")
                                update_company(company["id"],
                                               career_url=result["career_url"],
                                               ats_type=result.get("ats_type","generic"))
                                st.rerun()
                            else:
                                s.update(label="⚠️ Not found", state="error")
                                st.warning("Could not find career page. Enter it manually above.")

    # ── Tab 3: Find Company URL ───────────────────────────────────────────
    with tab3:
        st.subheader("🔍 Find Company Website by Name")
        st.write("Don't know a company's URL? Enter the name and we'll try to find it.")

        search_name = st.text_input("Company Name", placeholder="e.g. Parloa, Figma, Notion", key="company_search_input")

        if st.button("🔍 Search", type="primary", key="search_btn") and search_name:
            from utils.scraper import search_company_url
            with st.spinner(f"Searching for {search_name}..."):
                raw = search_company_url(search_name)
            seen, unique = set(), []
            for c in raw:
                norm = c["url"].rstrip("/")
                if norm not in seen:
                    seen.add(norm)
                    unique.append(c)
            st.session_state["search_candidates"] = unique
            st.session_state["search_name"] = search_name

        if st.session_state.get("search_candidates"):
            unique = st.session_state["search_candidates"]
            sname  = st.session_state.get("search_name", "")
            st.success(f"Found {len(unique)} candidate(s):")
            for i, c in enumerate(unique):
                col1, col2, col3 = st.columns([3, 1, 1])
                curl = c["url"]
                col1.write(f"🌐 {curl}")
                col2.markdown(f'<a href="{curl}" target="_blank">Open ↗</a>', unsafe_allow_html=True)
                if col3.button("✅ Use This", key=f"cbtn_{i}_{abs(hash(curl))%99999}"):
                    st.session_state["prefill_url"]  = c["url"]
                    st.session_state["prefill_name"] = sname.strip().title()
                    st.session_state["search_candidates"] = []
                    st.rerun()
