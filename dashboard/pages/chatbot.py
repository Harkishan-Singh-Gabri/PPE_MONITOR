import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import streamlit as st
from genai.chatbot import ask


SUGGESTED = [
    "How many violations happened today?",
    "Which worker had the most violations?",
    "Were there any falls detected?",
    "What is today's compliance rate?",
    "Show me the most common violation types",
    "Which zone had the most incidents?",
]


def show():
    st.markdown('<div class="page-title">🤖 Safety Chatbot</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Ask anything about violations, workers, and safety data</div>',
        unsafe_allow_html=True
    )

    main_col, help_col = st.columns([2, 1])

    with help_col:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">💡 Suggested Questions</div>',
                    unsafe_allow_html=True)

        for q in SUGGESTED:
            if st.button(q, width="stretch", key=f"sugg_{q}"):
                if "chat_history" not in st.session_state:
                    st.session_state.chat_history = []
                with st.spinner("Querying..."):
                    answer = ask(q, st.session_state.chat_history)
                st.session_state.chat_history.append({"role": "user",      "content": q})
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # how it works
        st.markdown("""
        <div class="section-card">
            <div class="section-title">🔧 How It Works</div>
            <div style="font-size:0.82rem; color:#64748b; line-height:1.8;">
                1. You type a question<br>
                2. Groq converts it to SQL<br>
                3. Query runs on your DB<br>
                4. Groq summarizes the result<br><br>
                <strong style="color:#334155;">Your data never leaves your system.</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with main_col:
        st.markdown('<div class="section-card" style="min-height:500px;">', unsafe_allow_html=True)

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # chat display
        if not st.session_state.chat_history:
            st.markdown("""
            <div style="text-align:center; padding:3rem 0; color:#94a3b8;">
                <div style="font-size:2.5rem; margin-bottom:0.5rem;">🤖</div>
                <div style="font-size:0.95rem; font-weight:500; color:#64748b;">
                    Hi! I'm SafeBot
                </div>
                <div style="font-size:0.85rem; margin-top:0.3rem;">
                    Ask me anything about your safety data.
                </div>
            </div>
            """, unsafe_allow_html=True)

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"],
                                 avatar="🧑‍💼" if msg["role"] == "user" else "🤖"):
                st.write(msg["content"])

        st.markdown('</div>', unsafe_allow_html=True)

        # input + clear
        icol1, icol2 = st.columns([5, 1])
        with icol1:
            question = st.chat_input("Ask a safety question...")
        with icol2:
            if st.button("🗑 Clear", width="stretch"):
                st.session_state.chat_history = []
                st.rerun()

        if question:
            with st.spinner("Querying safety database..."):
                answer = ask(question, st.session_state.chat_history)
            st.session_state.chat_history.append({"role": "user",      "content": question})
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            st.rerun()