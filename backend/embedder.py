# embedder.py
from langchain_huggingface import HuggingFaceEmbeddings
from config import EMBEDDING_MODEL

_embeddings: HuggingFaceEmbeddings | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Lazily initialise and return the singleton embedding model.
    Uses all-MiniLM-L6-v2 (384-dim) running locally — no API key required.
    """
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings
