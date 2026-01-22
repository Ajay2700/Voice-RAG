"""PDF processing service."""

from typing import List
import tempfile
from datetime import datetime
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP


def process_pdf(file) -> List:
    """Process PDF file and split into chunks with metadata.
    
    Args:
        file: Uploaded file object (Streamlit file uploader)
        
    Returns:
        List of document chunks with metadata
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(file.getvalue())
            loader = PyPDFLoader(tmp_file.name)
            documents = loader.load()
            
            # Add source metadata
            for doc in documents:
                doc.metadata.update({
                    "source_type": "pdf",
                    "file_name": file.name,
                    "timestamp": datetime.now().isoformat()
                })
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP
            )
            return text_splitter.split_documents(documents)
    except Exception as e:
        raise Exception(f"PDF processing error: {str(e)}")
