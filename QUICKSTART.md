# Quick Start Guide

## Installation Steps

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   streamlit run app.py
   ```

3. **Configure in the UI:**
   - Enter your Qdrant URL and API key
   - Enter your OpenAI API key
   - Select your preferred voice

4. **Upload a PDF and start asking questions!**

## Project Structure Summary

- `app.py` - Main application entry point
- `config/` - Application settings and constants
- `services/` - Business logic (vector store, PDF processing, query processing)
- `agents/` - AI agent configuration
- `utils/` - Helper functions (session state, UI components)

The old `voice_Rag.py` file is kept for reference but the new modular structure is in use.
