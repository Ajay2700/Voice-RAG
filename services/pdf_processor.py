"""PDF processing service with dual-granularity chunking."""

from typing import List
import tempfile
from datetime import datetime
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP


def process_pdf(file) -> List[Document]:
    """Process a PDF into two layers of chunks for high-recall retrieval.

    Layer 1 – **full-page chunks**: one document per PDF page so that
    header blocks (name, contact info, job title) are never split.

    Layer 2 – **fine-grained chunks**: smaller overlapping windows for
    precise fact matching (skills, dates, specific paragraphs).

    Both layers are returned together and stored in the same collection;
    the retriever scores whichever granularity best matches the query.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file.getvalue())
            loader = PyPDFLoader(tmp_file.name)
            pages = loader.load()

            base_meta = {
                "source_type": "pdf",
                "file_name": file.name,
                "timestamp": datetime.now().isoformat(),
            }

            # --- Layer 1: full-page documents ---
            full_page_docs: List[Document] = []
            for page in pages:
                text = page.page_content.strip()
                if not text:
                    continue
                meta = {
                    **base_meta,
                    **page.metadata,
                    "chunk_type": "full_page",
                }
                full_page_docs.append(Document(page_content=text, metadata=meta))

            # --- Layer 2: fine-grained chunks ---
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
            fine_chunks = splitter.split_documents(pages)
            for chunk in fine_chunks:
                chunk.metadata.update(base_meta)
                chunk.metadata["chunk_type"] = "fine"

            return full_page_docs + fine_chunks
    except Exception as e:
        raise Exception(f"PDF processing error: {str(e)}")
