import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="SafeGuard — PPE Monitor",
    page_icon="SG",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
[data-testid="stSidebarNav"] { display: none; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    border-right: 1px solid #334155;
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] .stRadio label {
    color: #94a3b8 !important;
    font-size: 0.9rem;
    padding: 0.4rem 0;
}

.main { background: #f8fafc; }
.main .block-container {
    background: #f8fafc;
    padding: 1.5rem 2rem;
    max-width: 100%;
}

.metric-card {
    background: white;
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    border: 1px solid #f1f5f9;
}
.metric-card .label {
    font-size: 0.78rem; color: #94a3b8; font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.3rem;
}
.metric-card .value { font-size: 2rem; font-weight: 700; color: #0f172a; line-height: 1.1; }
.metric-card .delta { font-size: 0.78rem; margin-top: 0.3rem; font-weight: 500; }
.delta-up   { color: #ef4444; }
.delta-down { color: #22c55e; }

.section-card {
    background: white;
    border-radius: 16px;
    padding: 1.4rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    border: 1px solid #f1f5f9;
    margin-bottom: 1rem;
}
.section-title { font-size: 1rem; font-weight: 600; color: #0f172a; margin-bottom: 1rem; }

.badge {
    display: inline-block; padding: 0.2rem 0.55rem;
    border-radius: 6px; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.05em;
}
.badge-critical { background:#fef2f2; color:#dc2626; border:1px solid #fecaca; }
.badge-high     { background:#fff7ed; color:#ea580c; border:1px solid #fed7aa; }
.badge-medium   { background:#fffbeb; color:#d97706; border:1px solid #fde68a; }

.alert-row {
    display:flex; align-items:center; gap:0.75rem;
    padding:0.7rem 0; border-bottom:1px solid #f1f5f9;
}
.alert-row:last-child { border-bottom:none; }
.alert-msg  { font-size:0.85rem; color:#334155; flex:1; }
.alert-time { font-size:0.75rem; color:#94a3b8; font-family:'DM Mono',monospace; }

.viol-row {
    display:flex; align-items:center; justify-content:space-between;
    padding:0.6rem 0; border-bottom:1px solid #f1f5f9;
    font-size:0.875rem; color:#334155;
}
.viol-row:last-child { border-bottom:none; }
.viol-count { font-weight:700; color:#0f172a; font-family:'DM Mono',monospace; }

.page-title    { font-size:1.6rem; font-weight:700; color:#0f172a; margin-bottom:0.2rem; }
.page-subtitle { font-size:0.9rem; color:#64748b; margin-bottom:1.2rem; }

.chat-user {
    background:#6366f1; color:white; padding:0.6rem 0.9rem;
    border-radius:12px 12px 2px 12px; font-size:0.85rem;
    margin:0.4rem 0; max-width:85%; margin-left:auto;
}
.chat-bot {
    background:#f1f5f9; color:#334155; padding:0.6rem 0.9rem;
    border-radius:12px 12px 12px 2px; font-size:0.85rem;
    margin:0.4rem 0; max-width:90%;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0.5rem 1.5rem;">
        <div style="margin-bottom:0.3rem;">
            <span style="font-size:1.4rem; font-weight:800; color:#f8fafc;
                         letter-spacing:-0.03em;">
                Safe<span style="color:#6366f1;">Guard</span>
            </span>
        </div>
        <div style="font-size:0.72rem; color:#64748b; padding-left:0.1rem;
                    letter-spacing:0.08em; text-transform:uppercase;">
            AI Workplace Safety Monitor
        </div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        ["🏠 Dashboard",
         "📹 Live Detection",
         "📊 Analytics",
         "⚠️ Violations",
         "🤖 Chatbot"],
        label_visibility="collapsed"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="padding:0.8rem;background:rgba(255,255,255,0.05);
                border-radius:10px;border:1px solid #334155;">
        <div style="font-size:0.7rem;color:#64748b;margin-bottom:0.5rem;font-weight:600;">
            SYSTEM STATUS
        </div>
        <div style="font-size:0.8rem;color:#22c55e;font-weight:500;">
            <span style="display:inline-block;width:7px;height:7px;background:#22c55e;
                         border-radius:50%;margin-right:6px;box-shadow:0 0 6px #22c55e;"></span>
            All systems operational
        </div>
    </div>
    <br><br>
    <div style="font-size:0.7rem;color:#475569;text-align:center;line-height:1.8;">
        YOLOv8 · ByteTrack · Groq LLaMA<br>
        <span style="color:#334155;">v1.0.0</span>
    </div>
    """, unsafe_allow_html=True)

if "🏠" in page:
    from dashboard.pages.home import show
    show()
elif "📹" in page:
    from dashboard.pages.live_feed import show
    show()
elif "📊" in page:
    from dashboard.pages.analytics import show
    show()
elif "⚠️" in page:
    from dashboard.pages.violations import show
    show()
elif "🤖" in page:
    from dashboard.pages.chatbot import show
    show()