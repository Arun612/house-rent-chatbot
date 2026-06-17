import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "house-rent-chatbot")
GROQ_LLM_MODEL: str = os.getenv("GROQ_LLM_MODEL", "llama-3.1-8b-instant")

# Embeddings — uses local sentence-transformers (no API key required)
# Pinecone index MUST be created with dimension=384
EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION: int = 384

# Chunking
CHUNK_SIZE: int = 1000
CHUNK_OVERLAP: int = 150

# Retrieval
TOP_K: int = 8
