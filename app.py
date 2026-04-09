"""Main Streamlit application for Voice RAG Agent."""

import asyncio
import streamlit as st
from dotenv import load_dotenv

from utils.session_state import init_session_state
from utils.ui_components import setup_sidebar
from services.vector_store import setup_qdrant, store_embeddings
from services.pdf_processor import process_pdf
from services.query_processor import process_query
from agent_config.agent_setup import setup_agents
from config.settings import COLLECTION_NAME

load_dotenv()


def looks_like_openai_key(api_key: str) -> bool:
    key = (api_key or "").strip()
    return key.startswith("sk-") and len(key) >= 20


def render_query_error(error_message: str) -> None:
    message = (error_message or "").lower()

    if "invalid_api_key" in message or "incorrect api key" in message:
        st.error("Invalid OpenAI API key. Please update it in the sidebar and retry.")
        return

    if "insufficient_quota" in message or "quota" in message:
        st.error("OpenAI quota limit reached. Please check billing/usage and try again.")
        return

    if "no relevant documents found" in message:
        st.warning("No relevant document chunks were found. Try uploading more docs or rephrasing.")
        return

    st.error(f"Error: {error_message}")


def apply_custom_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: radial-gradient(circle at top right, #1f2a44 0%, #0f1117 45%);
        }
        .hero-card {
            padding: 1.2rem 1.3rem;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 16px;
            background: linear-gradient(120deg, rgba(79, 70, 229, 0.35), rgba(15, 23, 42, 0.65));
            margin-bottom: 1rem;
        }
        .hero-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.3rem;
        }
        .hero-subtitle {
            opacity: 0.9;
            margin-bottom: 0;
        }
        .stat-card {
            padding: 0.75rem 0.9rem;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            background: rgba(255, 255, 255, 0.03);
            min-height: 84px;
        }
        .stat-label {
            font-size: 0.8rem;
            opacity: 0.8;
        }
        .stat-value {
            font-size: 1.15rem;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="Voice RAG Agent",
        page_icon="🎙️",
        layout="wide",
    )

    apply_custom_theme()
    init_session_state()
    setup_sidebar()

    credentials_provided = (
        st.session_state.qdrant_url
        and st.session_state.qdrant_api_key
        and st.session_state.openai_api_key
    )

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">🎙️ Voice RAG Agent</div>
            <p class="hero-subtitle">
                Ask questions over your PDFs and get grounded responses in both text and natural voice.
                Connect your APIs, upload docs, and start chatting with your knowledge base.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="stat-card"><div class="stat-label">Setup Status</div>'
            f'<div class="stat-value">{"Ready" if st.session_state.setup_complete else "Waiting"}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="stat-card"><div class="stat-label">Documents Indexed</div>'
            f'<div class="stat-value">{len(st.session_state.processed_documents)}</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="stat-card"><div class="stat-label">Selected Voice</div>'
            f'<div class="stat-value">{st.session_state.selected_voice}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    if not credentials_provided:
        st.warning("Please provide all API credentials in the sidebar before uploading documents.")
        st.info("Required credentials:\n- Qdrant URL\n- Qdrant API Key\n- OpenAI API Key")

    # ── Upload section ──────────────────────────────────────────────
    st.markdown("### 1) Upload Knowledge Base")
    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        disabled=not credentials_provided,
        help="Upload one PDF at a time to index it into Qdrant.",
    )

    if uploaded_file:
        file_name = uploaded_file.name
        if file_name not in st.session_state.processed_documents:
            if not credentials_provided:
                st.error("Please provide all API credentials in the sidebar first.")
            else:
                with st.spinner("Processing PDF (extracting, chunking, embedding)..."):
                    try:
                        if not st.session_state.client:
                            client, embedding_model = setup_qdrant(
                                st.session_state.qdrant_url,
                                st.session_state.qdrant_api_key,
                                st.session_state.openai_api_key,
                            )
                            st.session_state.client = client
                            st.session_state.embedding_model = embedding_model

                        documents = process_pdf(uploaded_file)
                        if documents:
                            store_embeddings(
                                st.session_state.client,
                                st.session_state.embedding_model,
                                documents,
                                COLLECTION_NAME,
                            )
                            st.session_state.processed_documents.append(file_name)
                            st.success(f"Indexed **{file_name}** ({len(documents)} chunks)")
                            st.session_state.setup_complete = True
                    except ValueError as e:
                        st.error(f"Configuration Error: {e}")
                        st.info("Check Qdrant credentials and OpenAI API key.")
                    except Exception as e:
                        st.error(f"Error processing document: {e}")

    if st.session_state.processed_documents:
        st.sidebar.header("📚 Processed Documents")
        for doc in st.session_state.processed_documents:
            st.sidebar.text(f"📄 {doc}")

    # ── Query section ───────────────────────────────────────────────
    st.markdown("### 2) Ask Questions")
    query = st.text_input(
        "What would you like to know about your documents?",
        placeholder="e.g., What is the candidate's name? What skills do they have?",
        disabled=not st.session_state.setup_complete,
    )

    selected_scope = "All documents"
    if st.session_state.processed_documents:
        scope_options = ["All documents"] + list(reversed(st.session_state.processed_documents))
        selected_scope = st.selectbox(
            "Search scope",
            options=scope_options,
            index=1 if len(scope_options) > 1 else 0,
            help="Choose a specific resume/PDF for higher accuracy.",
            disabled=not st.session_state.setup_complete,
        )

    if query and st.session_state.setup_complete:
        if not looks_like_openai_key(st.session_state.openai_api_key):
            st.error("Please enter a valid OpenAI API key in the sidebar before querying.")
            st.stop()

        with st.status("Processing your query...", expanded=True) as status:
            try:
                if not st.session_state.processor_agent:
                    st.session_state.processor_agent = setup_agents(
                        st.session_state.openai_api_key
                    )

                st.write("Searching document index...")

                result = asyncio.run(
                    process_query(
                        query,
                        st.session_state.client,
                        st.session_state.embedding_model,
                        st.session_state.processor_agent,
                        st.session_state.openai_api_key,
                        st.session_state.selected_voice,
                        None if selected_scope == "All documents" else selected_scope,
                        COLLECTION_NAME,
                    )
                )

                if result["status"] == "success":
                    chunks_used = result.get("chunks_used", "?")
                    status.update(
                        label=f"Done — used {chunks_used} context chunks",
                        state="complete",
                    )

                    response_tab, audio_tab, sources_tab = st.tabs(
                        ["🧠 Response", "🔊 Audio", "📚 Sources"]
                    )

                    with response_tab:
                        st.markdown("### Answer")
                        st.write(result["text_response"])

                    if "audio_path" in result:
                        with audio_tab:
                            st.markdown(
                                f"### Audio Response (Voice: `{st.session_state.selected_voice}`)"
                            )
                            st.audio(result["audio_path"], format="audio/mp3", start_time=0)
                            with open(result["audio_path"], "rb") as af:
                                st.download_button(
                                    label="📥 Download Audio Response",
                                    data=af.read(),
                                    file_name=f"voice_response_{st.session_state.selected_voice}.mp3",
                                    mime="audio/mp3",
                                )
                    else:
                        with audio_tab:
                            st.info("No audio was generated for this response.")

                    with sources_tab:
                        st.markdown("### Retrieved Sources")
                        for source in result["sources"]:
                            st.markdown(f"- {source}")
                else:
                    status.update(label="Error processing query", state="error")
                    render_query_error(result.get("error", "Unknown error"))

            except Exception as e:
                status.update(label="Error processing query", state="error")
                render_query_error(str(e))

    elif not st.session_state.setup_complete:
        st.info("👈 Please configure the system and upload documents first!")


if __name__ == "__main__":
    main()
