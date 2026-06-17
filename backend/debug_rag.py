"""
debug_rag.py — Run this to test if Pinecone RAG is working correctly.
Usage: python debug_rag.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from config import PINECONE_API_KEY, PINECONE_INDEX_NAME, GROQ_API_KEY, GROQ_LLM_MODEL
from embedder import get_embeddings
from pinecone import Pinecone

def check_pinecone():
    print("\n=== Pinecone Check ===")
    pc = Pinecone(api_key=PINECONE_API_KEY)
    indexes = [idx.name for idx in pc.list_indexes()]
    print(f"Available indexes: {indexes}")
    
    if PINECONE_INDEX_NAME not in indexes:
        print(f"❌ Index '{PINECONE_INDEX_NAME}' NOT found!")
        return False
    
    idx = pc.Index(PINECONE_INDEX_NAME)
    stats = idx.describe_index_stats()
    print(f"✅ Index found: {PINECONE_INDEX_NAME}")
    print(f"   Total vectors: {stats.total_vector_count}")
    print(f"   Namespaces: {stats.namespaces}")
    return True

def check_embedder():
    print("\n=== Embedder Check ===")
    try:
        emb = get_embeddings()
        test_vec = emb.embed_query("test")
        print(f"✅ Embedder working. Dimension: {len(test_vec)}")
        return True
    except Exception as e:
        print(f"❌ Embedder error: {e}")
        return False

def test_query(doc_id: str, query: str):
    print(f"\n=== RAG Query Test ===")
    print(f"Query: '{query}'")
    print(f"Doc ID filter: '{doc_id}'")
    
    from pinecone import Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    idx = pc.Index(PINECONE_INDEX_NAME)
    
    emb = get_embeddings()
    query_vec = emb.embed_query(query)
    
    # Test WITH filter
    results_filtered = idx.query(
        vector=query_vec,
        top_k=8,
        filter={"doc_id": {"$eq": doc_id}},
        include_metadata=True,
    )
    print(f"\nResults with doc_id filter ({len(results_filtered.matches)} matches):")
    for i, m in enumerate(results_filtered.matches):
        print(f"  [{i+1}] score={m.score:.4f} | page={m.metadata.get('page','?')} | text={m.metadata.get('text','')[:100]}...")

    # Test WITHOUT filter (to see if ANY vectors exist)
    results_all = idx.query(
        vector=query_vec,
        top_k=3,
        include_metadata=True,
    )
    print(f"\nResults WITHOUT filter ({len(results_all.matches)} matches):")
    for i, m in enumerate(results_all.matches):
        print(f"  [{i+1}] score={m.score:.4f} | doc_id={m.metadata.get('doc_id','?')} | text={m.metadata.get('text','')[:80]}...")

if __name__ == "__main__":
    print("🔍 RentChat RAG Debugger")
    print("=" * 40)
    
    ok_pc = check_pinecone()
    ok_emb = check_embedder()
    
    if ok_pc and ok_emb:
        # List all doc_ids in Pinecone
        pc = Pinecone(api_key=PINECONE_API_KEY)
        idx = pc.Index(PINECONE_INDEX_NAME)
        
        # Fetch sample vectors to see what doc_ids exist
        emb = get_embeddings()
        sample_vec = emb.embed_query("rent")
        results = idx.query(vector=sample_vec, top_k=10, include_metadata=True)
        
        doc_ids = set()
        for m in results.matches:
            doc_ids.add(m.metadata.get("doc_id", "unknown"))
        
        print(f"\n=== Doc IDs in Pinecone ===")
        for did in doc_ids:
            print(f"  - {did}")
        
        if doc_ids:
            first_doc_id = list(doc_ids)[0]
            print(f"\nTesting query on doc_id: {first_doc_id}")
            test_query(first_doc_id, "What is the monthly rent?")
        else:
            print("\n⚠️  No vectors found in Pinecone! Please upload a PDF first.")
    
    print("\n✅ Debug complete.")
