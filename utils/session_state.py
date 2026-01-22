"""Session state management utilities."""

import streamlit as st
from config.settings import DEFAULT_VOICE


def init_session_state() -> None:
    """Initialize Streamlit session state with default values."""
    defaults = {
        "initialized": False,
        "qdrant_url": "",
        "qdrant_api_key": "",
        "openai_api_key": "",
        "setup_complete": False,
        "client": None,
        "embedding_model": None,
        "processor_agent": None,
        "tts_agent": None,
        "selected_voice": DEFAULT_VOICE,
        "processed_documents": []
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
