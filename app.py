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


def main() -> None:
    """Main application function."""
    st.set_page_config(
        page_title="Voice RAG Agent",
        page_icon="🎙️",
        layout="wide"
    )
    
    init_session_state()
    setup_sidebar()
    
    st.title("🎙️ Voice RAG Agent")
    st.info(
        "Get voice-powered answers to your documentation questions by configuring your API keys "
        "and uploading PDF documents. Then, simply ask questions to receive both text and voice responses!"
    )
    
    # Check if credentials are provided
    credentials_provided = (
        st.session_state.qdrant_url and 
        st.session_state.qdrant_api_key and 
        st.session_state.openai_api_key
    )
    
    if not credentials_provided:
        st.warning("⚠️ Please provide all API credentials in the sidebar before uploading documents.")
        st.info("Required credentials:\n- Qdrant URL\n- Qdrant API Key\n- OpenAI API Key")
    
    # File upload section
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], disabled=not credentials_provided)
    
    if uploaded_file:
        file_name = uploaded_file.name
        if file_name not in st.session_state.processed_documents:
            # Validate credentials before processing
            if not credentials_provided:
                st.error("❌ Please provide all API credentials in the sidebar before processing documents.")
            else:
                with st.spinner('Processing PDF...'):
                    try:
                        # Setup Qdrant if not already done
                        if not st.session_state.client:
                            client, embedding_model = setup_qdrant(
                                st.session_state.qdrant_url,
                                st.session_state.qdrant_api_key
                            )
                            st.session_state.client = client
                            st.session_state.embedding_model = embedding_model
                        
                        # Process and store document
                        documents = process_pdf(uploaded_file)
                        if documents:
                            store_embeddings(
                                st.session_state.client,
                                st.session_state.embedding_model,
                                documents,
                                COLLECTION_NAME
                            )
                            st.session_state.processed_documents.append(file_name)
                            st.success(f"✅ Added PDF: {file_name}")
                            st.session_state.setup_complete = True
                    except ValueError as e:
                        st.error(f"❌ Configuration Error: {str(e)}")
                        st.info("💡 Please check that you've entered valid Qdrant URL and API key in the sidebar.")
                    except Exception as e:
                        st.error(f"❌ Error processing document: {str(e)}")
    
    # Display processed documents
    if st.session_state.processed_documents:
        st.sidebar.header("📚 Processed Documents")
        for doc in st.session_state.processed_documents:
            st.sidebar.text(f"📄 {doc}")
    
    # Query interface
    query = st.text_input(
        "What would you like to know about the documentation?",
        placeholder="e.g., How do I authenticate API requests?",
        disabled=not st.session_state.setup_complete
    )
    
    if query and st.session_state.setup_complete:
        with st.status("Processing your query...", expanded=True) as status:
            try:
                # Setup agents if not already done
                if not st.session_state.processor_agent or not st.session_state.tts_agent:
                    processor_agent, tts_agent = setup_agents(st.session_state.openai_api_key)
                    st.session_state.processor_agent = processor_agent
                    st.session_state.tts_agent = tts_agent
                
                st.info("🔄 Step 1: Generating query embedding and searching documents...")
                st.info("🔄 Step 2: Preparing context from search results...")
                st.info("🔄 Step 3: Generating text response...")
                st.info("🔄 Step 4: Generating voice instructions...")
                st.info("🔄 Step 5: Generating and playing audio...")
                
                result = asyncio.run(process_query(
                    query,
                    st.session_state.client,
                    st.session_state.embedding_model,
                    st.session_state.processor_agent,
                    st.session_state.tts_agent,
                    st.session_state.openai_api_key,
                    st.session_state.selected_voice,
                    COLLECTION_NAME
                ))
                
                if result["status"] == "success":
                    status.update(label="✅ Query processed!", state="complete")
                    
                    st.markdown("### Response:")
                    st.write(result["text_response"])
                    
                    if "audio_path" in result:
                        st.markdown(f"### 🔊 Audio Response (Voice: {st.session_state.selected_voice})")
                        st.audio(result["audio_path"], format="audio/mp3", start_time=0)
                        
                        with open(result["audio_path"], "rb") as audio_file:
                            audio_bytes = audio_file.read()
                            st.download_button(
                                label="📥 Download Audio Response",
                                data=audio_bytes,
                                file_name=f"voice_response_{st.session_state.selected_voice}.mp3",
                                mime="audio/mp3"
                            )
                    
                    st.markdown("### Sources:")
                    for source in result["sources"]:
                        st.markdown(f"- {source}")
                else:
                    status.update(label="❌ Error processing query", state="error")
                    st.error(f"Error: {result.get('error', 'Unknown error occurred')}")
            
            except Exception as e:
                status.update(label="❌ Error processing query", state="error")
                st.error(f"Error processing query: {str(e)}")
    
    elif not st.session_state.setup_complete:
        st.info("👈 Please configure the system and upload documents first!")


if __name__ == "__main__":
    main()
