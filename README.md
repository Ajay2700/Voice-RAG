# 🎙️ Voice RAG Agent

A sophisticated Retrieval-Augmented Generation (RAG) application that provides voice-powered answers to questions about your documentation. Upload PDF documents, ask questions, and receive both text and audio responses powered by OpenAI's GPT-4o and TTS models.

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Technologies Used](#technologies-used)
- [Troubleshooting](#troubleshooting)

## ✨ Features

- **PDF Document Processing**: Upload and process PDF documents with automatic text chunking
- **Vector Search**: Semantic search using Qdrant vector database and FastEmbed embeddings
- **Intelligent Responses**: GPT-4o powered responses based on your documentation
- **Voice Output**: Natural text-to-speech responses with multiple voice options
- **Streaming Audio**: Real-time audio playback using OpenAI's streaming TTS API
- **Audio Download**: Download audio responses as MP3 files
- **Source Citation**: See which documents were used to answer your questions

## 🏗️ Architecture

The application follows a modular architecture:

```
Voice RAG Agent
├── Config Layer: Application settings and constants
├── Services Layer: Business logic (vector store, PDF processing, query processing)
├── Agents Layer: AI agent setup and configuration
├── Utils Layer: Session state and UI components
└── App Layer: Streamlit user interface
```

### Workflow

1. **Document Upload**: PDF files are processed and split into chunks
2. **Embedding Generation**: Document chunks are embedded using FastEmbed
3. **Vector Storage**: Embeddings are stored in Qdrant vector database
4. **Query Processing**: User queries are embedded and matched against stored documents
5. **Context Retrieval**: Relevant document chunks are retrieved
6. **Response Generation**: GPT-4o generates answers based on retrieved context
7. **Voice Synthesis**: Text responses are converted to speech using OpenAI TTS
8. **Audio Playback**: Audio is streamed and made available for download


<img width="1900" height="717" alt="image" src="https://github.com/user-attachments/assets/df79f706-6ccd-41fa-a2dc-171913d637c1" />



## 📦 Prerequisites

- Python 3.8 or higher
- Qdrant account and API credentials
- OpenAI API key with access to:
  - GPT-4o model
  - GPT-4o-mini-tts model
- Internet connection for API calls

## 🚀 Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd 14_Voice_RAG
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables (optional):**
   Create a `.env` file in the project root:
   ```env
   QDRANT_URL=your_qdrant_url
   QDRANT_API_KEY=your_qdrant_api_key
   OPENAI_API_KEY=your_openai_api_key
   ```

## ⚙️ Configuration

### API Keys

You can configure API keys in two ways:

1. **Environment Variables**: Create a `.env` file (see Installation)
2. **Streamlit UI**: Enter keys in the sidebar when running the app

### Voice Selection

Choose from 11 available voices:
- `alloy`, `ash`, `ballad`, `coral`, `echo`, `fable`, `onyx`, `nova`, `sage`, `shimmer`, `verse`

Default voice: `coral`

## 📖 Usage

1. **Start the application:**
   ```bash
   streamlit run app.py
   ```

2. **Configure API keys:**
   - Enter your Qdrant URL and API key in the sidebar
   - Enter your OpenAI API key in the sidebar
   - Select your preferred voice

3. **Upload documents:**
   - Click "Upload PDF" and select a PDF file
   - Wait for processing to complete
   - The document will be added to your knowledge base

4. **Ask questions:**
   - Type your question in the text input
   - The system will:
     - Search for relevant document sections
     - Generate a text response
     - Create and play an audio response
     - Show source citations

5. **Download audio:**
   - After receiving a response, click "Download Audio Response" to save the MP3 file

## 📁 Project Structure

```
14_Voice_RAG/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── .env                        # Environment variables (create this)
│
├── config/                     # Configuration module
│   ├── __init__.py
│   └── settings.py            # Application settings and constants
│
├── services/                   # Business logic services
│   ├── __init__.py
│   ├── vector_store.py        # Qdrant operations and embeddings
│   ├── pdf_processor.py       # PDF processing and chunking
│   └── query_processor.py    # Query processing and TTS generation
│
├── agent_config/               # AI agent configuration
│   ├── __init__.py
│   └── agent_setup.py         # Agent initialization and configuration
│
└── utils/                      # Utility functions
    ├── __init__.py
    ├── session_state.py       # Streamlit session state management
    └── ui_components.py       # UI component functions
```

## 🛠️ Technologies Used

- **Streamlit**: Web application framework
- **Qdrant**: Vector database for embeddings
- **FastEmbed**: Fast text embeddings
- **LangChain**: Document processing and text splitting
- **OpenAI**: GPT-4o for text generation and TTS for voice synthesis
- **OpenAI Agents**: Agent framework for orchestration
- **Python-dotenv**: Environment variable management

## 🔧 Troubleshooting

### Common Issues

1. **"Qdrant credentials not provided"**
   - Ensure you've entered Qdrant URL and API key in the sidebar
   - Check that credentials are correct

2. **"No relevant documents found"**
   - Make sure you've uploaded at least one PDF document
   - Try rephrasing your question
   - Check that documents were processed successfully

3. **Audio playback issues**
   - Ensure your OpenAI API key has access to TTS models
   - Check your internet connection
   - Verify audio drivers are working on your system

4. **Import errors**
   - Make sure all dependencies are installed: `pip install -r requirements.txt`
   - Verify you're using the correct Python version (3.8+)
   - Check that you're in the project directory

5. **PDF processing errors**
   - Ensure the PDF file is not corrupted
   - Check that the PDF contains extractable text (not just images)
   - Verify file size is reasonable

### Performance Tips

- **Document Size**: Large PDFs may take longer to process. Consider splitting very large documents.
- **Chunk Size**: Adjust `CHUNK_SIZE` and `CHUNK_OVERLAP` in `config/settings.py` for different document types.
- **Search Limit**: Modify `SEARCH_LIMIT` in `config/settings.py` to retrieve more or fewer context documents.


