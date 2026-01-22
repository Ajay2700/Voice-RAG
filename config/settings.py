"""Application settings and constants."""

COLLECTION_NAME = "voice-rag-agent"

# Available voices for TTS
AVAILABLE_VOICES = [
    "alloy", "ash", "ballad", "coral", "echo", "fable", 
    "onyx", "nova", "sage", "shimmer", "verse"
]

# Default voice
DEFAULT_VOICE = "coral"

# Text splitter settings
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Vector search settings
SEARCH_LIMIT = 3
