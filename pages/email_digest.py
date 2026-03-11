import streamlit as st
from utils.db import get_config, save_config, get_jobs, add_log
from utils.mailer import send_digest, build_digest_html


def show():
    st.markdown('<div class="main-header">📧 Email Digest & Configuration</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Configure email notifications and API keys</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📧 Email Setup", "⚙️ System Config", "👁 Preview Digest"])

    config = get_config()

    with tab1:
        st.subheader("📬 Email Configuration")
        st.info("💡 For Gmail: enable 2FA and create an **App Password** at myaccount.google.com/apppasswords")
        
        with st.form("email_form"):
            col1, col2 = st.columns(2)
            with col1:
                email_to = st.text_input("📥 Send Digest To", value=config.get("email_to", ""),
                                         placeholder="you@gmail.com")
                smtp_host = st.text_input("SMTP Host", value=config.get("smtp_host", "smtp.gmail.com"))
                smtp_port = st.number_input("SMTP Port", value=int(config.get("smtp_port", 587)), step=1)
            with col2:
                email_from = st.text_input("📤 Send From (leave blank = same as To)",
                                           value=config.get("email_from", ""),
                                           placeholder="you@gmail.com")
                smtp_password = st.text_input("🔑 SMTP Password / App Password",
                                              value=config.get("smtp_password", ""),
                                              type="password",
                                              placeholder="Gmail App Password")
            
            st.markdown("---")
            st.subheader("⏰ Digest Schedule")
            digest_enabled = st.checkbox("Enable Automatic Digest", value=config.get("digest_enabled", True))
            
            col1, col2 = st.columns(2)
            with col1:
                time1 = st.time_input("Morning digest time",
                                      value=_parse_time(config.get("digest_times", ["08:00", "18:00"])[0]))
            with col2:
                time2 = st.time_input("Evening digest time",
                                      value=_parse_time(config.get("digest_times", ["08:00", "18:00"])[-1]))
            
            min_ai_score = st.slider("Minimum AI Score for Digest", 0, 100,
                                     value=config.get("min_ai_score", 60), step=5)
            
            if st.form_submit_button("💾 Save Email Config", type="primary"):
                config.update({
                    "email_to": email_to,
                    "email_from": email_from,
                    "smtp_host": smtp_host,
                    "smtp_port": smtp_port,
                    "smtp_password": smtp_password,
                    "digest_enabled": digest_enabled,
                    "digest_times": [str(time1)[:5], str(time2)[:5]],
                    "min_ai_score": min_ai_score,
                })
                save_config(config)
                st.success("✅ Email configuration saved!")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Send Test Digest Now", type="primary", use_container_width=True):
                with st.spinner("Sending..."):
                    success = send_digest()
                if success:
                    st.success("✅ Digest sent! Check your inbox.")
                else:
                    st.error("❌ Failed to send. Check your email config and logs.")
        with col2:
            n_qualify = len([j for j in get_jobs()
                            if j.get("filter_passed") and
                            j.get("ai_score", 0) >= config.get("min_ai_score", 60)])
            st.metric("Jobs in next digest", n_qualify)

    with tab2:
        st.subheader("🔑 API Keys")
        
        with st.form("api_form"):
            anthropic_key = st.text_input(
                "Anthropic API Key",
                value=config.get("anthropic_api_key", ""),
                type="password",
                placeholder="sk-ant-...",
                help="Get your API key at console.anthropic.com"
            )
            st.caption("Required for AI job ranking. Get a free key at console.anthropic.com")
            
            st.markdown("---")
            st.subheader("🔄 Scan Settings")
            col1, col2 = st.columns(2)
            with col1:
                scan_enabled = st.checkbox("Enable Automatic Scanning",
                                           value=config.get("scan_enabled", True))
            with col2:
                scan_interval = st.selectbox(
                    "Scan Frequency",
                    [1, 2, 4, 6, 12, 24],
                    index=[1, 2, 4, 6, 12, 24].index(config.get("scan_interval_hours", 6)),
                    format_func=lambda x: f"Every {x} hour{'s' if x > 1 else ''}"
                )
            
            if st.form_submit_button("💾 Save Config", type="primary"):
                config.update({
                    "anthropic_api_key": anthropic_key,
                    "scan_enabled": scan_enabled,
                    "scan_interval_hours": scan_interval,
                })
                save_config(config)
                st.success("✅ Configuration saved!")
        
        st.markdown("---")
        st.subheader("📋 Setup Checklist")
        checks = [
            ("Anthropic API Key", bool(config.get("anthropic_api_key")), "console.anthropic.com"),
            ("Email configured", bool(config.get("email_to") and config.get("smtp_password")), "Check Email Setup tab"),
            ("Companies added", True, "Go to Target Companies page"),
            ("Filters set", True, "Go to Job Filters page"),
        ]
        for name, done, tip in checks:
            icon = "✅" if done else "❌"
            st.write(f"{icon} **{name}** {'— done!' if done else f'— {tip}'}")

    with tab3:
        st.subheader("👁 Email Preview")
        jobs = get_jobs()
        digest_jobs = [j for j in jobs if j.get("filter_passed") and
                       j.get("ai_score", 0) >= config.get("min_ai_score", 60)]
        
        if not digest_jobs:
            st.info("No qualifying jobs to preview. Run a scan and AI ranking first.")
        else:
            st.write(f"**Preview with {len(digest_jobs)} jobs (score ≥ {config.get('min_ai_score', 60)})**")
            html = build_digest_html(digest_jobs)
            st.components.v1.html(html, height=600, scrolling=True)


def _parse_time(t: str):
    import datetime
    try:
        h, m = t.split(":")
        return datetime.time(int(h), int(m))
    except Exception:
        return datetime.time(8, 0)
