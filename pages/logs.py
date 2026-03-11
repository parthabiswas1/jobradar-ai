import streamlit as st
from datetime import datetime
from utils.db import get_logs, clear_logs, get_companies, get_jobs, get_config


def show():
    st.markdown('<div class="main-header">📊 Logs & System Status</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Monitor scans, filters, and system activity</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📝 Activity Logs", "📈 System Stats"])

    with tab1:
        logs = get_logs()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            level_filter = st.multiselect("Level", ["info", "warning", "error"],
                                          default=["info", "warning", "error"])
        with col2:
            source_filter = st.multiselect("Source",
                                           sorted(set(l.get("source", "system") for l in logs)))
        with col3:
            limit = st.selectbox("Show", [50, 100, 200, 500], index=0)
        with col4:
            st.write("")
            st.write("")
            if st.button("🗑 Clear Logs", type="secondary"):
                clear_logs()
                st.rerun()

        filtered_logs = logs
        if level_filter:
            filtered_logs = [l for l in filtered_logs if l.get("level") in level_filter]
        if source_filter:
            filtered_logs = [l for l in filtered_logs if l.get("source") in source_filter]
        
        filtered_logs = filtered_logs[:limit]

        if not filtered_logs:
            st.info("No logs yet. Run a scan to generate activity logs.")
        else:
            st.write(f"Showing {len(filtered_logs)} log entries")
            
            # Build log table
            log_data = []
            for log in filtered_logs:
                level = log.get("level", "info")
                icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(level, "⚪")
                ts = log.get("timestamp", "")[:19].replace("T", " ")
                log_data.append({
                    "": icon,
                    "Time": ts,
                    "Level": level.upper(),
                    "Source": log.get("source", ""),
                    "Message": log.get("message", ""),
                })
            
            import pandas as pd
            df = pd.DataFrame(log_data)
            
            # Color code by level
            def style_level(val):
                if val == "ERROR":
                    return "background-color: #fee2e2; color: #991b1b"
                elif val == "WARNING":
                    return "background-color: #fef3c7; color: #92400e"
                return ""
            
            styled = df.style.applymap(style_level, subset=["Level"])
            st.dataframe(styled, use_container_width=True, hide_index=True)

            # Error summary
            errors = [l for l in filtered_logs if l.get("level") == "error"]
            if errors:
                with st.expander(f"🔴 {len(errors)} Errors"):
                    for e in errors[:10]:
                        st.error(f"{e.get('timestamp','')[:16]} [{e.get('source','')}] {e.get('message','')}")

    with tab2:
        st.subheader("📈 System Statistics")
        
        companies = get_companies()
        jobs = get_jobs()
        config = get_config()
        logs = get_logs()
        
        # Company scan status
        st.write("### 🏢 Company Scan Status")
        if not companies:
            st.info("No companies added yet.")
        else:
            comp_data = []
            for c in companies:
                comp_jobs = [j for j in jobs if j.get("company") == c["name"]]
                passed = [j for j in comp_jobs if j.get("filter_passed")]
                ranked = [j for j in comp_jobs if j.get("ai_score") is not None]
                avg_score = (sum(j.get("ai_score", 0) for j in ranked) / len(ranked)) if ranked else 0
                
                comp_data.append({
                    "Company": c["name"],
                    "Status": c.get("status", "").upper(),
                    "ATS": c.get("ats_type", "?"),
                    "Total Jobs": len(comp_jobs),
                    "Passed Filter": len(passed),
                    "AI Ranked": len(ranked),
                    "Avg AI Score": f"{avg_score:.0f}" if avg_score else "—",
                    "Last Scanned": (c.get("last_scanned") or "Never")[:16].replace("T", " "),
                    "Career URL": c.get("career_url", "")[:60] + "..." if len(c.get("career_url","")) > 60 else c.get("career_url",""),
                })
            
            import pandas as pd
            st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)
        
        st.write("### 📊 Job Pipeline")
        total = len(jobs)
        passed_count = len([j for j in jobs if j.get("filter_passed")])
        ranked_count = len([j for j in jobs if j.get("ai_score") is not None])
        strong_count = len([j for j in jobs if (j.get("ai_score") or 0) >= 75])
        applied_count = len([j for j in jobs if j.get("status") == "applied"])
        
        pipeline = [
            ("Scraped", total, "#3b82f6"),
            ("Filter Passed", passed_count, "#8b5cf6"),
            ("AI Ranked", ranked_count, "#f59e0b"),
            ("Strong Matches (75+)", strong_count, "#10b981"),
            ("Applied", applied_count, "#ef4444"),
        ]
        
        cols = st.columns(len(pipeline))
        for col, (label, count, color) in zip(cols, pipeline):
            col.metric(label, count)
        
        # Pipeline funnel visualization
        if total > 0:
            import pandas as pd
            import altair as alt
            
            funnel_data = pd.DataFrame({
                "Stage": [p[0] for p in pipeline],
                "Count": [p[1] for p in pipeline],
            })
            
            chart = alt.Chart(funnel_data).mark_bar().encode(
                x=alt.X("Count:Q", title="Jobs"),
                y=alt.Y("Stage:N", sort=None, title=""),
                color=alt.Color("Stage:N", legend=None),
                tooltip=["Stage", "Count"]
            ).properties(title="Job Pipeline Funnel", height=200)
            
            st.altair_chart(chart, use_container_width=True)
        
        st.write("### ⚙️ Configuration Status")
        config_status = [
            ("Anthropic API Key", "✅ Set" if config.get("anthropic_api_key") else "❌ Missing"),
            ("Email To", config.get("email_to") or "❌ Not set"),
            ("SMTP Configured", "✅ Yes" if config.get("smtp_password") else "❌ No"),
            ("Digest Enabled", "✅ Yes" if config.get("digest_enabled") else "⏸ No"),
            ("Scan Enabled", "✅ Yes" if config.get("scan_enabled") else "⏸ No"),
            ("Scan Interval", f"{config.get('scan_interval_hours', 6)} hours"),
            ("Digest Times", ", ".join(config.get("digest_times", []))),
            ("Min AI Score", str(config.get("min_ai_score", 60))),
        ]
        
        import pandas as pd
        st.dataframe(pd.DataFrame(config_status, columns=["Setting", "Value"]),
                     use_container_width=True, hide_index=True)
