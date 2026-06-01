import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from db.crud import get_violations, get_alerts, get_compliance_rate
from genai.chatbot import ask


def _metric_card(label, value, delta=None, delta_up=True, icon=""):
    delta_html = ""
    if delta:
        cls = "delta-up" if delta_up else "delta-down"
        arrow = "↑" if delta_up else "↓"
        delta_html = f'<div class="delta {cls}">{arrow} {delta} vs last 7 days</div>'

    st.markdown(f"""
    <div class="metric-card">
        <div class="label">{icon} {label}</div>
        <div class="value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def _violations_over_time_chart(violations):
    if not violations:
        return go.Figure()

    df = pd.DataFrame([{
        "timestamp": v.timestamp,
        "severity":  v.severity,
    } for v in violations])

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"]      = df["timestamp"].dt.floor("h")
    timeline        = df.groupby("hour").size().reset_index(name="count")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x    = timeline["hour"],
        y    = timeline["count"],
        mode = "lines+markers",
        line = dict(color="#6366f1", width=2.5, shape="spline"),
        fill = "tozeroy",
        fillcolor = "rgba(99,102,241,0.08)",
        marker = dict(size=5, color="#6366f1"),
        name = "Violations"
    ))

    fig.update_layout(
        paper_bgcolor = "white",
        plot_bgcolor  = "white",
        margin        = dict(l=10, r=10, t=10, b=10),
        height        = 200,
        showlegend    = False,
        xaxis = dict(
            showgrid     = False,
            tickfont     = dict(size=10, color="#94a3b8"),
            tickformat   = "%b %d",
            showline     = False,
        ),
        yaxis = dict(
            showgrid    = True,
            gridcolor   = "#f1f5f9",
            tickfont    = dict(size=10, color="#94a3b8"),
            showline    = False,
            zeroline    = False,
        ),
    )
    return fig


def _top_violations(violations):
    if not violations:
        st.markdown('<div style="color:#94a3b8; font-size:0.85rem;">No data yet.</div>',
                    unsafe_allow_html=True)
        return

    from collections import Counter
    counts = Counter(v.violation_type for v in violations)
    icons  = {
        "NO-Hardhat":     "⛑️",
        "NO-Safety Vest": "🦺",
        "NO-Gloves":      "🧤",
        "NO-Goggles":     "🥽",
        "NO-Mask":        "😷",
        "Fall-Detected":  "🚨",
        "posture_HIGH":   "⚠️",
    }

    for vtype, count in counts.most_common(5):
        icon = icons.get(vtype, "📌")
        st.markdown(f"""
        <div class="viol-row">
            <span>{icon} {vtype}</span>
            <span class="viol-count">{count}</span>
        </div>
        """, unsafe_allow_html=True)


def _recent_alerts(alerts):
    if not alerts:
        st.markdown('<div style="color:#94a3b8; font-size:0.85rem;">No alerts yet.</div>',
                    unsafe_allow_html=True)
        return

    for a in alerts[:6]:
        sev  = a.severity.upper()
        cls  = f"badge-{sev.lower()}"
        time_str = a.timestamp.strftime("%H:%M") if a.timestamp else ""
        st.markdown(f"""
        <div class="alert-row">
            <span class="badge {cls}">{sev}</span>
            <span class="alert-msg">{a.message}</span>
            <span class="alert-time">{time_str}</span>
        </div>
        """, unsafe_allow_html=True)


def show():
    # ── Header ────────────────────────────────────────────────────────────────
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"

    st.markdown(f"""
    <div class="page-title">{greeting}, Safety Admin! 👋</div>
    <div class="page-subtitle">Here's what's happening with safety today — {datetime.now().strftime("%B %d, %Y")}</div>
    """, unsafe_allow_html=True)

    # ── Fetch Data ────────────────────────────────────────────────────────────
    violations = get_violations(limit=500)
    alerts     = get_alerts(limit=100)
    compliance = get_compliance_rate()

    total    = len(violations)
    critical = sum(1 for v in violations if v.severity == "CRITICAL")
    high     = sum(1 for v in violations if v.severity == "HIGH")

    # ── Metric Cards + Chatbot (side by side) ────────────────────────────────
    left_col, chat_col = st.columns([3, 1.2])

    with left_col:
        # metric cards
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            _metric_card("Total Violations", f"{total:,}", "12.5%", True,  "🛡️")
        with c2:
            _metric_card("Critical",         f"{critical:,}", "8.3%", True,  "🚨")
        with c3:
            _metric_card("High Severity",    f"{high:,}", "5.6%", True,  "⚠️")
        with c4:
            _metric_card("Compliance Rate",  f"{compliance}%", "4.7%", False, "✅")

        st.markdown("<br>", unsafe_allow_html=True)

        # violations over time + top violations
        chart_col, top_col = st.columns([1.6, 1])

        with chart_col:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Violations Over Time</div>',
                        unsafe_allow_html=True)
            fig = _violations_over_time_chart(violations)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

        with top_col:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown("""
            <div style="display:flex; justify-content:space-between; align-items:center;
                        margin-bottom:1rem;">
                <div class="section-title" style="margin:0;">Top Violations</div>
            </div>
            """, unsafe_allow_html=True)
            _top_violations(violations)
            st.markdown('</div>', unsafe_allow_html=True)

        # recent alerts
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🔔 Recent Alerts</div>', unsafe_allow_html=True)
        _recent_alerts(alerts)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Embedded Chatbot ──────────────────────────────────────────────────────
    with chat_col:
        st.markdown("""
        <div class="section-card" style="height: calc(100% - 1rem);">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.3rem;">
                <span style="font-size:1.2rem;">🤖</span>
                <span style="font-weight:700; color:#0f172a; font-size:0.95rem;">Safety Chatbot</span>
                <span style="margin-left:auto; font-size:0.72rem; color:#22c55e; font-weight:600;">
                    ● Online
                </span>
            </div>
            <div style="font-size:0.78rem; color:#94a3b8; margin-bottom:0.8rem;">
                Ask me anything about safety data.
            </div>
        """, unsafe_allow_html=True)

        if "home_chat" not in st.session_state:
            st.session_state.home_chat = []

        # chat history display
        chat_container = st.container()
        with chat_container:
            if not st.session_state.home_chat:
                st.markdown("""
                <div class="chat-bot">
                    Hi! I'm SafeBot 🤖<br>
                    Ask me about violations, compliance, or worker safety.
                </div>
                """, unsafe_allow_html=True)

            for msg in st.session_state.home_chat[-6:]:
                if msg["role"] == "user":
                    st.markdown(f'<div class="chat-user">{msg["content"]}</div>',
                                unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-bot">{msg["content"]}</div>',
                                unsafe_allow_html=True)

        # quick prompts
        st.markdown("<div style='margin-top:0.5rem;'>", unsafe_allow_html=True)
        prompts = [
            "Most common violations?",
            "Compliance trend today",
            "Any falls detected?",
        ]
        for p in prompts:
            if st.button(p, key=f"prompt_{p}", width="stretch"):
                with st.spinner(""):
                    answer = ask(p, st.session_state.home_chat)
                st.session_state.home_chat.append({"role": "user",      "content": p})
                st.session_state.home_chat.append({"role": "assistant", "content": answer})
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # chat input
        q = st.chat_input("Ask a question...", key="home_chat_input")
        if q:
            with st.spinner(""):
                answer = ask(q, st.session_state.home_chat)
            st.session_state.home_chat.append({"role": "user",      "content": q})
            st.session_state.home_chat.append({"role": "assistant", "content": answer})
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)