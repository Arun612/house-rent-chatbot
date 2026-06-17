from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from langchain_text_splitters import RecursiveCharacterTextSplitter
import json
import os

from config import CHUNK_SIZE, CHUNK_OVERLAP
from pdf_parser import parse_pdf
from vector_store import upsert_chunks, delete_doc_vectors, get_index, delete_all_vectors
from session_store import (
    create_session,
    get_session,
    add_message,
    get_history,
    delete_session,
    list_sessions,
    delete_all_sessions,
)
from rag_chain import ask

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="House Rent PDF Chatbot API",
    version="1.0.0",
    description="Upload rental PDFs and chat with them using Groq + Pinecone + LangChain.",
)

# ── Paths ─────────────────────────────────────────────────────────────────────
_BACKEND_DIR  = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.join(_BACKEND_DIR, "..", "frontend")
_FRONTEND_DIR = os.path.normpath(_FRONTEND_DIR)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Document Registry (persisted to disk so it survives restarts) ─────────────
_DOCS_FILE = os.path.join(os.path.dirname(__file__), "documents.json")
_documents: dict[str, dict] = {}

def _load_documents():
    global _documents
    if os.path.exists(_DOCS_FILE):
        try:
            with open(_DOCS_FILE, "r", encoding="utf-8") as f:
                _documents = json.load(f)
        except (json.JSONDecodeError, IOError):
            _documents = {}

def _save_documents():
    try:
        with open(_DOCS_FILE, "w", encoding="utf-8") as f:
            json.dump(_documents, f, indent=2, ensure_ascii=False)
    except IOError:
        pass

# Load documents on import
_load_documents()

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    """Init Pinecone index in a background thread — never blocks the event loop."""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, get_index)



# ── Request models ────────────────────────────────────────────────────────────
class SessionRequest(BaseModel):
    doc_id: str


class ChatRequest(BaseModel):
    session_id: str
    question: str


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "house-rent-chatbot"}


# ── Upload ────────────────────────────────────────────────────────────────────
@app.post("/upload", tags=["Documents"])
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF, parse it with PyMuPDF, chunk it, embed via sentence-transformers,
    and upsert all vectors to Pinecone.

    If the same filename was already uploaded, returns the existing document
    instead of creating a duplicate — preventing double-indexing in Pinecone.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # ── Duplicate guard ───────────────────────────────────────────────────────
    # If a document with this exact filename is already indexed, return it.
    # This is safer than MD5 hash, because sometimes the same PDF has slightly
    # different metadata bytes if downloaded twice.
    existing = next(
        (doc for doc in _documents.values() if doc["filename"] == file.filename),
        None,
    )
    if existing:
        return {**existing, "already_existed": True}

    contents = await file.read()
    parsed = parse_pdf(contents, file.filename)

    if not parsed["pages"]:
        raise HTTPException(
            status_code=422,
            detail="No readable text found in this PDF. It may be scanned/image-based.",
        )

    # Chunk every page
    chunks: list[dict] = []
    for page in parsed["pages"]:
        for text in _splitter.split_text(page["text"]):
            if text.strip():
                chunks.append({"text": text.strip(), "page_num": page["page_num"]})

    if not chunks:
        raise HTTPException(status_code=422, detail="Could not extract any usable text chunks.")

    chunk_count = upsert_chunks(chunks, parsed["doc_id"], file.filename)

    doc_info = {
        "doc_id": parsed["doc_id"],

        "filename": file.filename,
        "page_count": parsed["page_count"],
        "chunk_count": chunk_count,
    }
    _documents[parsed["doc_id"]] = doc_info
    _save_documents()          # ← persist so it survives restarts
    return doc_info


# ── Documents ─────────────────────────────────────────────────────────────────
@app.get("/documents", tags=["Documents"])
def list_documents():
    return list(_documents.values())


@app.delete("/documents/{doc_id}", tags=["Documents"])
def remove_document(doc_id: str):
    if doc_id not in _documents:
        raise HTTPException(status_code=404, detail="Document not found.")
    delete_doc_vectors(doc_id)
    del _documents[doc_id]
    _save_documents()          # ← persist deletion

    # Cascading delete: Remove all chat sessions tied to this document
    sessions = list_sessions()
    for s in sessions:
        if s["doc_id"] == doc_id:
            delete_session(s["session_id"])

    return {"message": "Document and all its vectors deleted successfully."}


@app.delete("/purge/{doc_id}", tags=["Documents"])
def force_purge_doc_id(doc_id: str):
    """
    Force-delete ALL Pinecone vectors for a doc_id even if it's not in documents.json.
    Use this to clean up orphan/legacy doc_ids that were created before persistence was added.
    """
    delete_doc_vectors(doc_id)
    # Also remove from registry if it happens to be there
    if doc_id in _documents:
        del _documents[doc_id]
        _save_documents()
    return {"message": f"Purged all Pinecone vectors for doc_id='{doc_id}'."}


@app.delete("/reset", tags=["System"])
def factory_reset():
    """
    DANGER: Wipes EVERYTHING.
    Deletes all vectors in Pinecone, clears documents.json, and clears sessions.json.
    """
    global _documents
    
    # 1. Hard wipe ALL vectors from Pinecone
    delete_all_vectors()
    
    # 2. Clear documents registry
    _documents.clear()
    _save_documents()
    
    # 3. Clear all chat sessions
    delete_all_sessions()
    
    return {"message": "Factory reset complete. All documents, vectors, and chat histories have been deleted."}


# ── Sessions ──────────────────────────────────────────────────────────────────
@app.post("/sessions", tags=["Sessions"])
def new_session(req: SessionRequest):
    """Create a new conversation session scoped to an uploaded document."""
    if req.doc_id not in _documents:
        raise HTTPException(
            status_code=404,
            detail="Document not found. Please upload it first.",
        )
    doc = _documents[req.doc_id]
    session_id = create_session(req.doc_id, doc["filename"])
    return {
        "session_id": session_id,
        "doc_id": req.doc_id,
        "filename": doc["filename"],
    }


@app.get("/sessions", tags=["Sessions"])
def all_sessions():
    return list_sessions()


@app.get("/sessions/{session_id}/history", tags=["Sessions"])
def session_history(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {
        "session_id": session_id,
        "doc_id": session["doc_id"],
        "filename": session["filename"],
        "created_at": session["created_at"],
        "messages": session["messages"],
    }


@app.delete("/sessions/{session_id}", tags=["Sessions"])
def remove_session(session_id: str):
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    delete_session(session_id)
    return {"message": "Session deleted."}


# ── Chat ──────────────────────────────────────────────────────────────────────
@app.post("/chat", tags=["Chat"])
async def chat(req: ChatRequest):
    """
    Send a question to the RAG chain.
    The session's full conversation history is injected into the chain so
    follow-up questions (e.g. "What about the deposit?") work correctly.
    """
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if session["doc_id"] not in _documents:
        raise HTTPException(
            status_code=400, 
            detail="The document for this conversation has been deleted. Please upload it again to start a new chat."
        )

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    history = get_history(req.session_id)

    result = ask(
        question=req.question.strip(),
        doc_id=session["doc_id"],
        history_messages=history,
    )

    # Persist both turns to the session
    add_message(req.session_id, "human", req.question.strip())
    add_message(req.session_id, "ai", result["answer"])

    formatted_sources = [
        {
            "content": doc.get("snippet", ""),
            "page": doc.get("page", "?"),
        }
        for doc in result["sources"]
    ]

    return {
        "answer": result["answer"],
        "sources": formatted_sources,
        "session_id": req.session_id,
        "turn": (len(history) // 2) + 1,
    }


# ── Frontend (serve static files) ─────────────────────────────────────────────
# Root → serve index.html
@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(os.path.join(_FRONTEND_DIR, "index.html"))

# Mount all other frontend assets (style.css, app.js, etc.)
# Must come LAST so API routes take priority
app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")
