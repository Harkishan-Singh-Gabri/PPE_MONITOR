import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd
import streamlit as st
from db.crud import get_violations

def show():
    st.markdown('<div class="page-title">⚠️ Violations</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Full violation log with filters</div>',
                unsafe_allow_html=True)

    violations = get_violations(limit=500)

    if not violations:
        st.markdown("""
        <div class="section-card" style="text-align:center; padding:3rem;">
            <div style="font-size:2.5rem; margin-bottom:0.5rem;">✅</div>
            <div style="color:#94a3b8; font-size:0.95rem;">
                No violations logged yet.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    df = pd.DataFrame([{
        "Worker ID": v.worker_id,
        "Violation": v.violation_type,
        "Severity": v.severity,
        "Zone": v.zone,
        "Confidence": f"{v.confidence:.0%}" if v.confidence else "N/A",
        "Timestamp": v.timestamp.strftime("%Y-%m-%d %H:%M:%S") if v.timestamp else "",
        "Snapshot": v.snapshot_path or "",
    } for v in violations])

    # filters
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns(3)

    with fc1:
        sev_filter = st.multiselect(
            "Severity",
            ["CRITICAL", "HIGH", "MEDIUM"],
            default=["CRITICAL", "HIGH"]
        )
    with fc2:
        workers = ["All"] + sorted(df["Worker ID"].unique().tolist())
        wid_filter = st.selectbox("Worker", workers)
    with fc3:
        vtypes = ["All"] + sorted(df["Violation"].unique().tolist())
        vtype_filter = st.selectbox("Violation Type", vtypes)

    st.markdown('</div>', unsafe_allow_html=True)

    # apply filters
    filtered = df.copy()
    if sev_filter:
        filtered = filtered[filtered["Severity"].isin(sev_filter)]
    if wid_filter != "All":
        filtered = filtered[filtered["Worker ID"] == wid_filter]
    if vtype_filter != "All":
        filtered = filtered[filtered["Violation"] == vtype_filter]

    # summary
    st.markdown(f"""
    <div style="font-size:0.85rem; color:#64748b; margin-bottom:0.5rem;">
        Showing <strong>{len(filtered)}</strong> of <strong>{len(df)}</strong> violations
    </div>
    """, unsafe_allow_html=True)

    # table
    st.markdown('<div class="section-card">', unsafe_allow_html=True)

    def severity_color(val):
        colors = {
            "CRITICAL": "background-color:#fef2f2; color:#dc2626; font-weight:600",
            "HIGH": "background-color:#fff7ed; color:#ea580c; font-weight:600",
            "MEDIUM": "background-color:#fffbeb; color:#d97706; font-weight:600",
        }
        return colors.get(val, "")

    display_df = filtered.drop(columns=["Snapshot"]).sort_values(
        "Timestamp", ascending=False
    ).head(100)

    styled = display_df.style.applymap(
        severity_color, subset=["Severity"]
    ).set_properties(**{
        "font-size": "0.85rem",
    })

    st.dataframe(styled, width="stretch", height=450)
    st.markdown('</div>', unsafe_allow_html=True)

    # export
    csv = filtered.to_csv(index=False)
    st.download_button(
        label= "⬇️ Export CSV",
        data = csv,
        file_name = "violations_export.csv",
        mime = "text/csv",
    )