"""Application settings and constants."""

COLLECTION_NAME = "voice-rag-agent"

AVAILABLE_VOICES = [
    "alloy", "ash", "ballad", "coral", "echo", "fable",
    "onyx", "nova", "sage", "shimmer", "verse"
]

DEFAULT_VOICE = "coral"

# Smaller chunks preserve fine-grained facts (names, dates, skills).
# Full-page chunks are also stored separately by the PDF processor
# so header sections are never lost across chunk boundaries.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# Retrieve more candidates; score threshold filters weak matches.
SEARCH_LIMIT = 8
SCORE_THRESHOLD = 0.35
