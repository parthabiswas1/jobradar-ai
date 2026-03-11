import streamlit as st

st.set_page_config(
    page_title="JobRadar AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #0b0f1a !important;
    font-family: 'DM Sans', sans-serif;
}
#MainMenu, footer, header { visibility: hidden; }
div[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="collapsedControl"] { display: none; }

[data-testid="stSidebar"] {
    background: #070a12 !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }

.sidebar-logo {
    padding: 28px 22px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    margin-bottom: 6px;
}
.sidebar-logo h1 {
    font-family: 'Syne', sans-serif;
    font-size: 19px; font-weight: 800;
    color: #fff; margin: 0 0 3px;
    letter-spacing: -0.3px;
}
.sidebar-logo p { font-size: 10px; color: rgba(255,255,255,0.28); margin:0; text-transform:uppercase; letter-spacing:1.4px; }

.nav-label { font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:1.6px; color:rgba(255,255,255,0.22); padding:14px 22px 5px; }

[data-testid="stSidebar"] .stButton > button {
    background: transparent !important; border: none !important;
    color: rgba(255,255,255,0.45) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important; font-weight: 400 !important;
    text-align: left !important; padding: 9px 22px !important;
    width: 100% !important; border-radius: 0 !important;
    transition: all 0.15s !important; border-left: 2px solid transparent !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.04) !important; color: #fff !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: rgba(99,102,241,0.12) !important;
    color: #a5b4fc !important; font-weight: 600 !important;
    border-left: 2px solid #6366f1 !important;
}

.sdivider { height:1px; background:rgba(255,255,255,0.05); margin:10px 22px; }

[data-testid="stMainBlockContainer"] { padding: 32px 36px !important; }

/* page header */
.ph { margin-bottom: 26px; }
.ph h1 { font-family:'Syne',sans-serif; font-size:26px; font-weight:800; color:#fff; margin:0 0 5px; letter-spacing:-0.4px; }
.ph p  { font-size:13px; color:rgba(255,255,255,0.35); margin:0; }

/* metric card override */
[data-testid="stMetric"] {
    background: #131929 !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 14px !important;
    padding: 18px 20px !important;
}
[data-testid="stMetricLabel"]  { font-size:10px !important; color:rgba(255,255,255,0.32) !important; text-transform:uppercase; letter-spacing:0.9px; }
[data-testid="stMetricValue"]  { font-family:'Syne',sans-serif !important; font-size:30px !important; font-weight:700 !important; color:#fff !important; }
[data-testid="stMetricDelta"]  { color:#34d399 !important; font-size:11px !important; }

/* tabs */
[data-baseweb="tab-list"] { background:transparent !important; border-bottom:1px solid rgba(255,255,255,0.07) !important; gap:0; }
[data-baseweb="tab"] { background:transparent !important; color:rgba(255,255,255,0.38) !important; font-family:'DM Sans',sans-serif !important; font-size:13px !important; padding:9px 18px !important; border-bottom:2px solid transparent !important; }
[aria-selected="true"] { color:#a5b4fc !important; border-bottom:2px solid #6366f1 !important; }

/* inputs */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input { background:#0b0f1a !important; border:1px solid rgba(255,255,255,0.09) !important; border-radius:10px !important; color:#fff !important; font-family:'DM Sans',sans-serif !important; }
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus { border-color:rgba(99,102,241,0.5) !important; box-shadow:0 0 0 3px rgba(99,102,241,0.1) !important; }
label { color:rgba(255,255,255,0.55) !important; font-size:12.5px !important; }

/* selectbox */
[data-testid="stSelectbox"] > div > div { background:#0b0f1a !important; border:1px solid rgba(255,255,255,0.09) !important; border-radius:10px !important; color:#fff !important; }

/* buttons */
.stButton > button { font-family:'DM Sans',sans-serif !important; border-radius:10px !important; font-weight:500 !important; transition:all 0.15s !important; font-size:13px !important; }
.stButton > button[kind="primary"] { background:linear-gradient(135deg,#6366f1,#8b5cf6) !important; border:none !important; color:#fff !important; box-shadow:0 4px 14px rgba(99,102,241,0.3) !important; }
.stButton > button[kind="primary"]:hover { transform:translateY(-1px) !important; box-shadow:0 6px 20px rgba(99,102,241,0.4) !important; }
.stButton > button[kind="secondary"] { background:rgba(255,255,255,0.04) !important; border:1px solid rgba(255,255,255,0.09) !important; color:rgba(255,255,255,0.65) !important; }
.stButton > button[kind="secondary"]:hover { background:rgba(255,255,255,0.08) !important; color:#fff !important; }

/* form submit */
[data-testid="stFormSubmitButton"] > button { background:linear-gradient(135deg,#6366f1,#8b5cf6) !important; border:none !important; color:#fff !important; border-radius:10px !important; font-weight:600 !important; }

/* expanders */
[data-testid="stExpander"] { background:#131929 !important; border:1px solid rgba(255,255,255,0.07) !important; border-radius:12px !important; margin-bottom:8px !important; }
[data-testid="stExpander"] summary { color:rgba(255,255,255,0.72) !important; font-family:'DM Sans',sans-serif !important; font-size:13.5px !important; }

/* alerts */
[data-testid="stAlert"] { border-radius:10px !important; }

/* progress */
[data-testid="stProgressBar"] > div { background:rgba(255,255,255,0.06) !important; border-radius:99px; }
[data-testid="stProgressBar"] > div > div { background:linear-gradient(90deg,#6366f1,#8b5cf6) !important; border-radius:99px; }

/* multiselect */
[data-testid="stMultiSelect"] > div { background:#0b0f1a !important; border:1px solid rgba(255,255,255,0.09) !important; border-radius:10px !important; }
span[data-baseweb="tag"] { background:rgba(99,102,241,0.2) !important; color:#a5b4fc !important; }

/* checkbox */
[data-testid="stCheckbox"] label { color:rgba(255,255,255,0.65) !important; }

/* scrollbar */
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:rgba(255,255,255,0.1); border-radius:3px; }

/* dataframe */
[data-testid="stDataFrame"] { border:1px solid rgba(255,255,255,0.07) !important; border-radius:12px !important; overflow:hidden !important; }

hr { border-color:rgba(255,255,255,0.06) !important; }
[data-testid="stCaptionContainer"] { color:rgba(255,255,255,0.3) !important; }

/* info card */
.info-card {
    background:#131929; border:1px solid rgba(255,255,255,0.07);
    border-radius:14px; padding:22px 24px; margin-bottom:14px;
}
.info-card h3 { font-family:'Syne',sans-serif; font-size:13px; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:1.1px; margin:0 0 14px; }

/* status dots */
.dot-green { width:8px; height:8px; border-radius:50%; background:#34d399; display:inline-block; margin-right:6px; }
.dot-red   { width:8px; height:8px; border-radius:50%; background:#f87171; display:inline-block; margin-right:6px; }
.dot-yellow{ width:8px; height:8px; border-radius:50%; background:#fbbf24; display:inline-block; margin-right:6px; }

/* pill */
.pill { display:inline-block; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
.pill-indigo { background:rgba(99,102,241,0.15); color:#a5b4fc; }
.pill-green  { background:rgba(52,211,153,0.12); color:#34d399; }
.pill-yellow { background:rgba(251,191,36,0.12);  color:#fbbf24; }
.pill-red    { background:rgba(248,113,113,0.12); color:#f87171; }
.pill-gray   { background:rgba(255,255,255,0.06); color:rgba(255,255,255,0.4); }

/* score badge */
.score-hi { font-family:'Syne',sans-serif; font-weight:800; color:#34d399; font-size:20px; }
.score-md { font-family:'Syne',sans-serif; font-weight:800; color:#fbbf24; font-size:20px; }
.score-lo { font-family:'Syne',sans-serif; font-weight:800; color:#f87171; font-size:20px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <h1>⚡ JobRadar AI</h1>
        <p>Intelligent Job Hunter</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="nav-label">Menu</div>', unsafe_allow_html=True)

    pages = {
        "🏠  Dashboard":        "dashboard",
        "🏢  Target Companies": "companies",
        "🔍  Job Filters":      "filters",
        "📋  Matched Jobs":     "matched_jobs",
        "🤖  AI Rankings":      "ai_rankings",
        "📧  Email Digest":     "email_digest",
        "📊  Logs & Status":    "logs",
    }

    if "current_page" not in st.session_state:
        st.session_state.current_page = "dashboard"

    for label, key in pages.items():
        is_active = st.session_state.current_page == key
        if st.button(label, key=f"nav_{key}", use_container_width=True,
                     type="primary" if is_active else "secondary"):
            st.session_state.current_page = key
            st.rerun()

    st.markdown('<div class="sdivider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="nav-label">Quick Actions</div>', unsafe_allow_html=True)

    if st.button("⚡  Run Scan Now",    use_container_width=True, type="secondary"):
        st.session_state.run_scan = True; st.rerun()
    if st.button("📤  Send Digest Now", use_container_width=True, type="secondary"):
        st.session_state.send_digest = True; st.rerun()

# ── Router ────────────────────────────────────────────────────────────────────
page = st.session_state.current_page
if   page == "dashboard":    from pages import dashboard;    dashboard.show()
elif page == "companies":    from pages import companies;    companies.show()
elif page == "filters":      from pages import filters;      filters.show()
elif page == "matched_jobs": from pages import matched_jobs; matched_jobs.show()
elif page == "ai_rankings":  from pages import ai_rankings;  ai_rankings.show()
elif page == "email_digest": from pages import email_digest; email_digest.show()
elif page == "logs":         from pages import logs;         logs.show()
