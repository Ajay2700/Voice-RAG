"""UI components for Streamlit application."""

import streamlit as st
from config.settings import AVAILABLE_VOICES, DEFAULT_VOICE


def setup_sidebar() -> None:
    """Configure sidebar with API settings and voice options."""
    import os

    with st.sidebar:
        st.title("🔑 Control Panel")
        st.caption("Configure providers and voice preferences.")
        st.markdown("---")

        # Try to load from environment variables if not set
        default_qdrant_url = st.session_state.qdrant_url or os.getenv("QDRANT_URL", "")
        default_qdrant_key = st.session_state.qdrant_api_key or os.getenv("QDRANT_API_KEY", "")
        default_openai_key = st.session_state.openai_api_key or os.getenv("OPENAI_API_KEY", "")

        st.session_state.qdrant_url = st.text_input(
            "Qdrant URL",
            value=default_qdrant_url,
            type="default",
            help="Enter your Qdrant cloud URL (e.g., https://xxx.qdrant.io)"
        ).strip()
        st.session_state.qdrant_api_key = st.text_input(
            "Qdrant API Key",
            value=default_qdrant_key,
            type="password",
            help="Enter your Qdrant API key"
        ).strip()
        st.session_state.openai_api_key = st.text_input(
            "OpenAI API Key",
            value=default_openai_key,
            type="password",
            help="Enter your OpenAI API key"
        ).strip()

        st.markdown("---")
        st.markdown("### 🎤 Voice Settings")

        current_index = AVAILABLE_VOICES.index(
            st.session_state.selected_voice
        ) if st.session_state.selected_voice in AVAILABLE_VOICES else AVAILABLE_VOICES.index(DEFAULT_VOICE)

        st.session_state.selected_voice = st.selectbox(
            "Select Voice",
            options=AVAILABLE_VOICES,
            index=current_index,
            help="Choose the voice for the audio response"
        )

        st.markdown("---")
        st.caption("Tip: Save credentials in `.env` for faster startup.")
