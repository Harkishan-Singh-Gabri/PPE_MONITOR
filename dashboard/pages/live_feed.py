import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import cv2
import yaml
import tempfile
import streamlit as st
from api.pipeline import PPEPipeline


def show():
    st.markdown('<div class="page-title">📹 Live Detection</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Real-time PPE and posture monitoring</div>',
                unsafe_allow_html=True)

    # source selection
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    source_type = st.radio(
        "Video Source",
        ["📁 Upload Video", "🎥 Webcam"],
        horizontal=True
    )

    src = None
    if source_type == "📁 Upload Video":
        uploaded = st.file_uploader(
            "Upload video file",
            type=["mp4", "avi", "mov", "mkv"],
            label_visibility="collapsed"
        )
        if uploaded:
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tfile.write(uploaded.read())
            tfile.flush()
            src = tfile.name
            st.success(f"✅ Loaded: {uploaded.name}")
    else:
        src = 0
        st.info("Using webcam")

    st.markdown('</div>', unsafe_allow_html=True)

    # layout
    feed_col, panel_col = st.columns([3, 1])

    with panel_col:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">⚡ Pipeline Metrics</div>',
                    unsafe_allow_html=True)
        fps_box        = st.empty()
        latency_box    = st.empty()
        workers_box    = st.empty()
        violations_box = st.empty()
        falls_box      = st.empty()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🚨 Live Alerts</div>',
                    unsafe_allow_html=True)
        alert_box = st.empty()
        st.markdown('</div>', unsafe_allow_html=True)

    with feed_col:
        frame_box = st.empty()

        bcol1, bcol2 = st.columns(2)
        start = bcol1.button("▶ Start",  type="primary",
                             width="stretch", disabled=(src is None))
        stop  = bcol2.button("⏹ Stop",   width="stretch")

    if "running" not in st.session_state:
        st.session_state.running = False
    if "alert_log" not in st.session_state:
        st.session_state.alert_log = []

    if stop:
        st.session_state.running = False
        st.rerun()

    if start and src is not None:
        st.session_state.running   = True
        st.session_state.alert_log = []

        cfg_path = Path("config/settings.yaml")
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f)
        cfg["camera"]["source"] = src
        with open(cfg_path, "w") as f:
            yaml.dump(cfg, f)

        pipeline = PPEPipeline()

        while st.session_state.running:
            frame = pipeline.stream.read_frame()
            if frame is None:
                st.warning("Stream ended.")
                st.session_state.running = False
                break

            frame, alerts, metrics = pipeline.process_frame(frame)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_box.image(rgb, channels="RGB", use_container_width="stretch")

            fps_box.metric("FPS",                metrics["fps"])
            latency_box.metric("Latency",         f"{metrics['latency_ms']}ms")
            workers_box.metric("Active Workers",  metrics["active_workers"])
            violations_box.metric("Violations",   metrics["violations_today"])
            falls_box.metric("Falls Detected",    metrics["falls_detected"])

            for a in alerts:
                st.session_state.alert_log.insert(0, a)
            st.session_state.alert_log = st.session_state.alert_log[:10]

            with alert_box.container():
                for a in st.session_state.alert_log:
                    sev = a["severity"]
                    if sev == "CRITICAL":
                        st.error(f"🚨 {a['message']}")
                    elif sev == "HIGH":
                        st.warning(f"⚠️ {a['message']}")
                    else:
                        st.info(f"ℹ️ {a['message']}")

        pipeline.stream.release()