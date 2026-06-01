import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from db.crud import get_violations, get_alerts, get_compliance_rate


def show():
    st.markdown('<div class="page-title">📊 Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Safety performance insights and trends</div>',
                unsafe_allow_html=True)

    violations = get_violations(limit=500)
    compliance = get_compliance_rate()

    total    = len(violations)
    critical = sum(1 for v in violations if v.severity == "CRITICAL")
    high     = sum(1 for v in violations if v.severity == "HIGH")

    # metric cards
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("Total Violations", f"{total:,}",    "🛡️"),
        ("Critical",         f"{critical:,}", "🚨"),
        ("High Severity",    f"{high:,}",     "⚠️"),
        ("Compliance Rate",  f"{compliance}%","✅"),
    ]
    for col, (label, value, icon) in zip([c1,c2,c3,c4], cards):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">{icon} {label}</div>
                <div class="value">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not violations:
        st.markdown("""
        <div class="section-card" style="text-align:center; padding:3rem;">
            <div style="font-size:2.5rem; margin-bottom:0.5rem;">📭</div>
            <div style="color:#94a3b8; font-size:0.95rem;">
                No violations logged yet. Start the live feed to begin monitoring.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    df = pd.DataFrame([{
        "violation_type": v.violation_type,
        "severity":       v.severity,
        "worker_id":      v.worker_id,
        "timestamp":      v.timestamp,
    } for v in violations])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # row 1 — timeline + by type
    col1, col2 = st.columns([1.6, 1])

    with col1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Violations Over Time</div>',
                    unsafe_allow_html=True)
        df["hour"] = df["timestamp"].dt.floor("h")
        timeline   = df.groupby(["hour","severity"]).size().reset_index(name="count")
        fig = px.line(
            timeline, x="hour", y="count", color="severity",
            color_discrete_map={"CRITICAL": "#ef4444", "HIGH": "#f97316"},
            markers=True
        )
        fig.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=0,r=0,t=0,b=0), height=220,
            legend=dict(orientation="h", y=-0.2, font=dict(size=11)),
            xaxis=dict(showgrid=False, tickfont=dict(size=10,color="#94a3b8"),
                       tickformat="%b %d %H:%M", showline=False),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9",
                       tickfont=dict(size=10,color="#94a3b8"), showline=False, zeroline=False),
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">By Violation Type</div>',
                    unsafe_allow_html=True)
        type_counts         = df["violation_type"].value_counts().reset_index()
        type_counts.columns = ["Violation", "Count"]
        fig2 = px.bar(
            type_counts.head(6), x="Count", y="Violation",
            orientation="h",
            color="Count",
            color_continuous_scale=[[0,"#fef3c7"],[0.5,"#f97316"],[1,"#ef4444"]],
        )
        fig2.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=0,r=0,t=0,b=0), height=220,
            showlegend=False, coloraxis_showscale=False,
            xaxis=dict(showgrid=True, gridcolor="#f1f5f9",
                       tickfont=dict(size=10,color="#94a3b8"), showline=False),
            yaxis=dict(showgrid=False, tickfont=dict(size=10,color="#334155"),
                       showline=False),
        )
        st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    # row 2 — by worker + severity donut
    col3, col4 = st.columns(2)

    with col3:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Violations by Worker</div>',
                    unsafe_allow_html=True)
        worker_counts         = df["worker_id"].value_counts().reset_index()
        worker_counts.columns = ["Worker", "Count"]
        fig3 = px.bar(
            worker_counts.head(10), x="Worker", y="Count",
            color="Count",
            color_continuous_scale=[[0,"#e0e7ff"],[1,"#6366f1"]],
        )
        fig3.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=0,r=0,t=0,b=0), height=220,
            showlegend=False, coloraxis_showscale=False,
            xaxis=dict(showgrid=False, tickfont=dict(size=10,color="#94a3b8")),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9",
                       tickfont=dict(size=10,color="#94a3b8"), zeroline=False),
        )
        st.plotly_chart(fig3, width="stretch", config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Severity Distribution</div>',
                    unsafe_allow_html=True)
        sev_counts = df["severity"].value_counts().reset_index()
        sev_counts.columns = ["Severity", "Count"]
        fig4 = px.pie(
            sev_counts, names="Severity", values="Count",
            hole=0.55,
            color="Severity",
            color_discrete_map={"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#f59e0b"},
        )
        fig4.update_layout(
            paper_bgcolor="white",
            margin=dict(l=0,r=0,t=0,b=0), height=220,
            legend=dict(orientation="h", y=-0.15, font=dict(size=11)),
            showlegend=True,
        )
        fig4.update_traces(textinfo="percent+label", textfont_size=11)
        st.plotly_chart(fig4, width="stretch", config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)