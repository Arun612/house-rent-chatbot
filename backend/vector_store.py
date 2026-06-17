# vector_store.py
"""
Uses Pinecone SDK directly — no langchain-pinecone dependency required.
Exposes a LangChain-compatible BaseRetriever so rag_chain.py needs no changes.
"""
import time
from typing import List

from pinecone import Pinecone, ServerlessSpec
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from pydantic import ConfigDict

from config import (
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    EMBEDDING_DIMENSION,
    TOP_K,
)
from embedder import get_embeddings

# ── Singletons ────────────────────────────────────────────────────────────────
_pc: Pinecone | None = None
_index = None


def _get_pc() -> Pinecone:
    global _pc
    if _pc is None:
        _pc = Pinecone(api_key=PINECONE_API_KEY)
    return _pc


def get_index():
    """Create the Pinecone index if it doesn't exist, then return it."""
    global _index
    if _index is not None:
        return _index

    pc = _get_pc()
    existing = [idx.name for idx in pc.list_indexes()]

    if PINECONE_INDEX_NAME not in existing:
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        while not pc.describe_index(PINECONE_INDEX_NAME).status["ready"]:
            time.sleep(1)

    _index = pc.Index(PINECONE_INDEX_NAME)
    return _index


# ── Upsert ────────────────────────────────────────────────────────────────────
def upsert_chunks(chunks: list[dict], doc_id: str, filename: str) -> int:
    """Embed chunks locally and upsert to Pinecone in batches of 100."""
    if not chunks:
        return 0

    embedder = get_embeddings()
    texts = [c["text"] for c in chunks]
    vectors = embedder.embed_documents(texts)

    records = [
        {
            "id": f"{doc_id}::chunk_{i}",
            "values": vec,
            "metadata": {
                "text": chunk["text"],
                "source": filename,
                "page": chunk.get("page_num", 0),
                "doc_id": doc_id,
            },
        }
        for i, (chunk, vec) in enumerate(zip(chunks, vectors))
    ]

    index = get_index()
    for i in range(0, len(records), 100):          # Pinecone batch limit
        index.upsert(vectors=records[i : i + 100])

    return len(records)


# ── Custom LangChain Retriever ────────────────────────────────────────────────
class PineconeRetriever(BaseRetriever):
    """LangChain-compatible retriever backed by direct Pinecone SDK calls."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    doc_id: str
    top_k: int = TOP_K

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun = None,
    ) -> List[Document]:
        embedder = get_embeddings()
        query_vec = embedder.embed_query(query)
        index = get_index()

        results = index.query(
            vector=query_vec,
            top_k=self.top_k,
            filter={"doc_id": {"$eq": self.doc_id}},
            include_metadata=True,
        )

        # Pinecone SDK returns an object with .matches attribute (not a dict)
        matches = results.matches if hasattr(results, "matches") else results.get("matches", [])
        docs = []
        for match in matches:
            # match is a ScoredVector object — use attribute access, not dict
            if hasattr(match, "metadata"):
                meta = match.metadata or {}
            else:
                meta = match.get("metadata", {})

            # meta itself is a dict in the Pinecone response
            docs.append(
                Document(
                    page_content=meta.get("text", ""),
                    metadata={
                        "source": meta.get("source", ""),
                        "page": meta.get("page", 0),
                        "doc_id": meta.get("doc_id", ""),
                    },
                )
            )
        return docs


def get_retriever(doc_id: str, top_k: int = TOP_K) -> PineconeRetriever:
    return PineconeRetriever(doc_id=doc_id, top_k=top_k)


def delete_doc_vectors(doc_id: str) -> None:
    get_index().delete(filter={"doc_id": {"$eq": doc_id}})


def delete_all_vectors() -> None:
    """Hard wipe of all vectors in the entire index."""
    try:
        get_index().delete(delete_all=True)
    except Exception as e:
        print(f"Warning during hard reset: {e}")
