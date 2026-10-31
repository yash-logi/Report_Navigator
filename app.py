import streamlit as st
import tempfile
import os
import hashlib
from backend.rag_pipeline import index_pdf, ask_question
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Report Navigator",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- DEMO DATA --------------------
DEMO_REPORT = "India Statistical Overview 2025.pdf"
DEMO_EVIDENCE = [
    {"page": 12, "type": "TEXT", "title": "Population overview",
     "content": "The report provides an overview of population trends, demographic composition and changes across states. This is sample interface content, not extracted report evidence."},
    {"page": 28, "type": "TABLE", "title": "State-wise indicators",
     "content": "State | Indicator A | Indicator B\nState A | 72.4 | 18.2\nState B | 68.1 | 21.7\nState C | 75.6 | 16.9"},
    {"page": 41, "type": "TEXT", "title": "Employment trends",
     "content": "This sample passage demonstrates how a report paragraph and its page reference will appear in the Evidence Explorer."},
]
DEMO_QUESTIONS = [
    "What are the main findings of this report?",
    "Which pages contain important statistics?",
    "What tables are included in the report?",
    "Summarize the employment section."
]

# -------------------- STATE --------------------
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_name" not in st.session_state:
    st.session_state.uploaded_name = ""
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = True

# -------------------- STYLE --------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: Inter, sans-serif; }
.stApp { background: #080D19; color: #E8EEF9; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: #0D1424; border-right: 1px solid #202B40; }
[data-testid="stSidebar"] > div:first-child { padding-top: 24px; }
.main .block-container { max-width: 1280px; padding-top: 2rem; padding-bottom: 3rem; }
.brand { font-size: 23px; font-weight: 800; letter-spacing: -1px; color: #F8FAFC; }
.brand span { color: #60A5FA; }
.tagline { color: #8291AA; font-size: 10px; letter-spacing: 1.7px; margin-top: 5px; }
.hero { background: linear-gradient(120deg,#12213D,#17294B 58%,#28214D); border: 1px solid #30446B; border-radius: 22px; padding: 34px; margin: 10px 0 26px; }
.hero-label { color: #93C5FD; font-size: 11px; font-weight: 800; letter-spacing: 2px; }
.hero-title { color: white; font-size: clamp(28px,4vw,40px); line-height: 1.15; font-weight: 800; letter-spacing: -1.5px; margin: 12px 0; }
.hero-desc { color: #B8C6DF; font-size: 14px; line-height: 1.8; max-width: 720px; }
.section-title { font-size: 19px; font-weight: 750; color: #F1F5F9; margin: 24px 0 14px; }
.panel { background: #111B2E; border: 1px solid #263650; border-radius: 16px; padding: 20px; min-height: 130px; }
.panel-kicker { color: #93C5FD; font-size: 10px; font-weight: 800; letter-spacing: 1.3px; }
.panel-title { color: #F1F5F9; font-size: 16px; font-weight: 750; margin: 10px 0 7px; }
.panel-copy { color: #91A0B8; font-size: 12px; line-height: 1.7; }
.metric { background: #111B2E; border: 1px solid #263650; border-radius: 14px; padding: 15px 17px; }
.metric-label { color: #91A0B8; font-size: 11px; font-weight: 600; }
.metric-value { color: #F8FAFC; font-size: 27px; font-weight: 800; margin-top: 7px; }
.source { background: #111B2E; border: 1px solid #30405A; border-radius: 14px; padding: 17px; margin: 10px 0; }
.source-meta { color: #93C5FD; font-size: 10px; font-weight: 800; letter-spacing: 1px; }
.source-text { color: #CFD9E9; font-size: 13px; line-height: 1.7; margin-top: 10px; }
div.stButton > button { border-radius: 10px; min-height: 42px; font-weight: 650; border: 1px solid #30405A; }
div.stButton > button:hover { border-color: #60A5FA; color: #93C5FD; }
.stTextInput input, .stTextArea textarea { background: #111B2E !important; color: #F8FAFC !important; border: 1px solid #30405A !important; border-radius: 10px !important; }
[data-testid="stChatMessage"] { background: #111B2E; border: 1px solid #263650; border-radius: 14px; }
.stSelectbox [data-baseweb="select"] > div { background: #111B2E; }
hr { border-color: #263650; }
.small-muted { color: #8291AA; font-size: 11px; }
</style>
""", unsafe_allow_html=True)

def go(page):
    st.session_state.page = page
    st.rerun()

def hero(kicker, title, desc):
    st.markdown(f"""
    <div class="hero">
      <div class="hero-label">{kicker}</div>
      <div class="hero-title">{title}</div>
      <div class="hero-desc">{desc}</div>
    </div>""", unsafe_allow_html=True)

def panel(icon, title, desc, kicker="WORKSPACE"):
    st.markdown(f"""
    <div class="panel">
      <div class="panel-kicker">{kicker}</div>
      <div class="panel-title">{icon} &nbsp; {title}</div>
      <div class="panel-copy">{desc}</div>
    </div>""", unsafe_allow_html=True)

# -------------------- SIDEBAR --------------------
with st.sidebar:
    st.markdown('<div class="brand">REPORT<span> NAVIGATOR</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline">EVIDENCE INTELLIGENCE WORKSPACE</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**WORKSPACE**")
    pages = ["Dashboard", "Ask Report", "Evidence Explorer", "Table Intelligence", "Report X-Ray"]
    selected = st.radio("Navigation", pages, index=pages.index(st.session_state.page), label_visibility="collapsed")
    if selected != st.session_state.page:
        st.session_state.page = selected
        st.rerun()

    st.markdown("---")
    st.markdown("**DOCUMENT CENTER**")
    uploaded = st.file_uploader("Upload a government report", type=["pdf"], help="Frontend preview only. This version does not read PDF contents.")
    if uploaded:
        st.session_state.uploaded_name = uploaded.name
        st.success("PDF selected")
        st.caption(f"{uploaded.name} · {uploaded.size/1024:.1f} KB")
    elif st.session_state.uploaded_name:
        st.caption(f"Selected: {st.session_state.uploaded_name}")

    st.markdown("---")
    st.markdown("**SYSTEM MODE**")
    st.markdown("""
    <div class="panel" style="min-height:0;padding:14px">
      <div class="panel-kicker">● FRONTEND PREVIEW</div>
      <div class="panel-title" style="font-size:14px">Interface demo</div>
      <div class="panel-copy">No external AI API · No backend connected</div>
    </div>""", unsafe_allow_html=True)
    st.markdown("<div class='small-muted'>REPORT NAVIGATOR · LOCAL UI</div>", unsafe_allow_html=True)

# -------------------- TOP BAR --------------------
left, right = st.columns([4,1])
with left:
    st.markdown("<div class='small-muted'>WORKSPACE / DOCUMENT INTELLIGENCE</div><div style='font-size:21px;font-weight:750;margin-top:5px'>Your research workspace</div>", unsafe_allow_html=True)
with right:
    st.markdown("<div style='text-align:right;padding-top:12px;color:#FBBF24;font-size:11px;font-weight:700'>● DEMO MODE</div>", unsafe_allow_html=True)

page = st.session_state.page

# -------------------- DASHBOARD --------------------
if page == "Dashboard":
    hero("YOUR INTELLIGENT RESEARCH WORKSPACE", "Turn hundreds of pages<br>into clear answers.",
         "A focused workspace for exploring government statistics, finding important evidence, reviewing tables and understanding long reports.")
    st.markdown("<div class='section-title'>Report overview</div>", unsafe_allow_html=True)
    if st.session_state.uploaded_name:
        report_name = st.session_state.uploaded_name
        status = "PDF selected · Not yet analyzed"
    else:
        report_name = "No report uploaded"
        status = "Upload a PDF from the sidebar to get started"
    cols = st.columns(4)
    for col, label, value in zip(cols, ["Pages analyzed","Text sections","Tables detected","Evidence chunks"], ["—","—","—","—"]):
        with col:
            st.markdown(f"<div class='metric'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Current document</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='source'><div class='source-meta'>DOCUMENT STATUS</div><div class='panel-title'>📄 {report_name}</div><div class='panel-copy'>{status}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'>Explore your report</div>", unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1:
        panel("💬","Ask your report","A conversational interface for asking questions and reviewing answers with page references.")
        if st.button("Open AI Assistant", use_container_width=True): go("Ask Report")
    with c2:
        panel("🧾","Evidence Explorer","Browse report passages, page references and supporting evidence.")
        if st.button("Explore Evidence", use_container_width=True): go("Evidence Explorer")
    with c3:
        panel("📊","Table Intelligence","Review extracted numerical tables and compare statistics.")
        if st.button("Explore Tables", use_container_width=True): go("Table Intelligence")
    st.markdown("<div class='section-title'>Suggested questions</div>", unsafe_allow_html=True)
    qcols = st.columns(2)
    for i, q in enumerate(DEMO_QUESTIONS):
        with qcols[i%2]:
            if st.button("↗  "+q, key=f"suggest_{i}", use_container_width=True):
                st.session_state.pending_question = q
                go("Ask Report")

# -------------------- ASK REPORT --------------------
elif page == "Ask Report":
    hero("AI RESEARCH ASSISTANT", "Ask. Discover. Verify.", "A clean chat workspace designed for questions about your uploaded government report.")
    if not st.session_state.uploaded_name:
        st.info("Upload a PDF from the sidebar to attach a report to this workspace. You can still try the demo chat below.")
    else:
        st.caption(f"Selected document: **{st.session_state.uploaded_name}**")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    pending = st.session_state.pop("pending_question", None)
    prompt = st.chat_input("Ask something about your report...")
    question = pending or prompt
    if question:
        st.session_state.messages.append({"role":"user","content":question})
        with st.chat_message("user"):
            st.markdown(question)
        demo_answer = ("This is a frontend demonstration. Your question has been displayed, but no report analysis has been performed because this version has no backend or connected language model. "
                       "When a backend is added, this area can show an evidence-based answer with page citations.")
        st.session_state.messages.append({"role":"assistant","content":demo_answer})
        with st.chat_message("assistant"):
            st.markdown(demo_answer)
            st.info("Demo response · No AI model was called")
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

# -------------------- EVIDENCE EXPLORER --------------------
elif page == "Evidence Explorer":
    hero("SOURCE TRANSPARENCY", "Every insight needs evidence.", "Explore how extracted report passages and page references will be presented.")
    st.info("The passages below are sample content for the frontend preview, not content extracted from your uploaded PDF.")
    selected_page = st.selectbox("Filter by report page", ["All pages", 12, 28, 41])
    for item in DEMO_EVIDENCE:
        if selected_page == "All pages" or item["page"] == selected_page:
            st.markdown(f"""<div class="source"><div class="source-meta">PAGE {item['page']} · {item['type']}</div><div class="panel-title">{item['title']}</div><div class="source-text">{item['content']}</div></div>""", unsafe_allow_html=True)

# -------------------- TABLE INTELLIGENCE --------------------
elif page == "Table Intelligence":
    hero("NUMERICAL RESEARCH", "Numbers tell stories.", "A dedicated space for browsing tables, spotting patterns and comparing report statistics.")
    st.info("Sample table shown for interface preview only. Uploaded PDF tables are not extracted in this frontend-only version.")
    st.markdown("<div class='section-title'>Table preview · Page 28</div>", unsafe_allow_html=True)
    df = pd.DataFrame({
        "State": ["State A","State B","State C","State D"],
        "Indicator A": [72.4,68.1,75.6,70.2],
        "Indicator B": [18.2,21.7,16.9,19.4]
    })
    st.dataframe(df, use_container_width=True, hide_index=True)
    a,b = st.columns(2)
    with a: st.metric("Tables available in demo", "1")
    with b: st.metric("Source page", "28")
    st.bar_chart(df.set_index("State"))

# -------------------- REPORT X-RAY --------------------
elif page == "Report X-Ray":
    hero("DOCUMENT ANALYTICS", "See inside your report.", "A visual overview of document structure, extracted information and page-level coverage.")
    st.info("Charts use sample values to demonstrate the layout. They are not calculated from your PDF.")
    c1,c2,c3 = st.columns(3)
    for col,label,val in zip([c1,c2,c3],["Total pages","Text sections","Tables"],["120","86","14"]):
        with col:
            st.markdown(f"<div class='metric'><div class='metric-label'>{label}</div><div class='metric-value'>{val}</div></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Content distribution · Demo</div>", unsafe_allow_html=True)
    chart = pd.DataFrame({"Content type":["Text sections","Tables","Figures"],"Count":[86,14,20]})
    st.bar_chart(chart.set_index("Content type"))
    st.markdown("<div class='section-title'>Page-wise coverage · Demo</div>", unsafe_allow_html=True)
    coverage = pd.DataFrame({"Page":[1,10,20,30,40,50],"Text sections":[2,4,3,5,2,4],"Tables":[0,1,0,2,1,0]})
    st.dataframe(coverage, use_container_width=True, hide_index=True)

# -------------------- FOOTER --------------------
st.markdown("---")
st.markdown("<div style='text-align:center;color:#64748B;font-size:10px;padding:12px;letter-spacing:1px'>REPORT NAVIGATOR · FRONTEND PREVIEW<br><br>STREAMLIT · PYTHON · NO BACKEND CONNECTED</div>", unsafe_allow_html=True)
