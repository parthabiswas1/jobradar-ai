import streamlit as st

st.set_page_config(
    page_title="AI Job Hunter",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.25rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #6b7280;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .status-badge-green {
        background: #d1fae5;
        color: #065f46;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .status-badge-yellow {
        background: #fef3c7;
        color: #92400e;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .status-badge-red {
        background: #fee2e2;
        color: #991b1b;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    div[data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
with st.sidebar:
    st.markdown("## 🎯 AI Job Hunter")
    st.markdown("---")
    
    pages = {
        "🏠 Dashboard": "dashboard",
        "🏢 Target Companies": "companies",
        "🔍 Job Filters": "filters",
        "📋 Matched Jobs": "matched_jobs",
        "🤖 AI Rankings": "ai_rankings",
        "📧 Email Digest": "email_digest",
        "📊 Logs & Status": "logs",
    }
    
    if "current_page" not in st.session_state:
        st.session_state.current_page = "dashboard"
    
    for label, key in pages.items():
        if st.button(label, key=f"nav_{key}", use_container_width=True,
                     type="primary" if st.session_state.current_page == key else "secondary"):
            st.session_state.current_page = key
            st.rerun()
    
    st.markdown("---")
    st.markdown("### ⚡ Quick Actions")
    if st.button("🔄 Run Scan Now", use_container_width=True):
        st.session_state.run_scan = True
        st.rerun()
    if st.button("📤 Send Digest Now", use_container_width=True):
        st.session_state.send_digest = True
        st.rerun()

# Route to pages
page = st.session_state.current_page

if page == "dashboard":
    from pages import dashboard
    dashboard.show()
elif page == "companies":
    from pages import companies
    companies.show()
elif page == "filters":
    from pages import filters
    filters.show()
elif page == "matched_jobs":
    from pages import matched_jobs
    matched_jobs.show()
elif page == "ai_rankings":
    from pages import ai_rankings
    ai_rankings.show()
elif page == "email_digest":
    from pages import email_digest
    email_digest.show()
elif page == "logs":
    from pages import logs
    logs.show()
