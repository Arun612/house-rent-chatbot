from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
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
from rag_chain import ask, ask_stream
from metadata_extractor import extract_metadata
from database import Base, engine, SessionLocal, Document

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

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)

# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    """Init DB tables and Pinecone index in a background thread."""
    Base.metadata.create_all(bind=engine)
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
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # ── Duplicate guard ───────────────────────────────────────────────────────
    with SessionLocal() as db:
        existing = db.query(Document).filter(Document.filename == file.filename).first()
        if existing:
            return {**existing.to_dict(), "already_existed": True}

    contents = await file.read()
    parsed = parse_pdf(contents, file.filename)

    if not parsed["pages"]:
        raise HTTPException(
            status_code=422,
            detail="No readable text found in this PDF. It may be scanned/image-based.",
        )

    chunks: list[dict] = []
    for page in parsed["pages"]:
        for text in _splitter.split_text(page["text"]):
            if text.strip():
                chunks.append({"text": text.strip(), "page_num": page["page_num"]})

    if not chunks:
        raise HTTPException(status_code=422, detail="Could not extract any usable text chunks.")

    # ── Extract Metadata ──────────────────────────────────────────────────────
    full_text = "\n".join(page["text"] for page in parsed["pages"])
    metadata = extract_metadata(full_text)

    chunk_count = upsert_chunks(chunks, parsed["doc_id"], file.filename)

    with SessionLocal() as db:
        new_doc = Document(
            doc_id=parsed["doc_id"],
            filename=file.filename,
            page_count=parsed["page_count"],
            chunk_count=chunk_count,
            metadata_json=json.dumps(metadata)
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)
        return new_doc.to_dict()


# ── Documents ─────────────────────────────────────────────────────────────────
@app.get("/documents", tags=["Documents"])
def list_documents():
    with SessionLocal() as db:
        docs = db.query(Document).order_by(Document.created_at.desc()).all()
        return [doc.to_dict() for doc in docs]


@app.delete("/documents/{doc_id}", tags=["Documents"])
def remove_document(doc_id: str):
    with SessionLocal() as db:
        doc = db.query(Document).filter(Document.doc_id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")
        
        # Pinecone delete
        delete_doc_vectors(doc_id)
        
        # Cascading deletes will handle sessions and messages
        db.delete(doc)
        db.commit()

    return {"message": "Document and all its vectors deleted successfully."}


@app.delete("/purge/{doc_id}", tags=["Documents"])
def force_purge_doc_id(doc_id: str):
    delete_doc_vectors(doc_id)
    with SessionLocal() as db:
        doc = db.query(Document).filter(Document.doc_id == doc_id).first()
        if doc:
            db.delete(doc)
            db.commit()
    return {"message": f"Purged all Pinecone vectors for doc_id='{doc_id}'."}


@app.delete("/reset", tags=["System"])
def factory_reset():
    delete_all_vectors()
    with SessionLocal() as db:
        db.query(Document).delete()
        db.commit()
    return {"message": "Factory reset complete. All documents, vectors, and chat histories have been deleted."}


# ── Sessions ──────────────────────────────────────────────────────────────────
@app.post("/sessions", tags=["Sessions"])
def new_session(req: SessionRequest):
    with SessionLocal() as db:
        doc = db.query(Document).filter(Document.doc_id == req.doc_id).first()
        if not doc:
            raise HTTPException(
                status_code=404,
                detail="Document not found. Please upload it first.",
            )
        session_id = create_session(req.doc_id, doc.filename)
        return {
            "session_id": session_id,
            "doc_id": req.doc_id,
            "filename": doc.filename,
        }


@app.get("/sessions", tags=["Sessions"])
def all_sessions():
    return list_sessions()


@app.get("/sessions/{session_id}/history", tags=["Sessions"])
def session_history(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@app.delete("/sessions/{session_id}", tags=["Sessions"])
def remove_session_route(session_id: str):
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    delete_session(session_id)
    return {"message": "Session deleted."}


# ── Chat ──────────────────────────────────────────────────────────────────────
@app.post("/chat", tags=["Chat"])
async def chat(req: ChatRequest):
    """
    Send a question to the RAG chain and stream the response.
    """
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    with SessionLocal() as db:
        doc = db.query(Document).filter(Document.doc_id == session["doc_id"]).first()
        if not doc:
            raise HTTPException(
                status_code=400, 
                detail="The document for this conversation has been deleted. Please upload it again to start a new chat."
            )

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    history = get_history(req.session_id)
    add_message(req.session_id, "human", req.question.strip())

    async def generate():
        async for item in ask_stream(
            question=req.question.strip(),
            doc_id=session["doc_id"],
            history_messages=history,
        ):
            if "full_answer" in item:
                add_message(req.session_id, "ai", item["full_answer"])
                formatted_sources = [
                    {
                        "content": doc.get("snippet", ""),
                        "page": doc.get("page", "?"),
                    }
                    for doc in item["sources"]
                ]
                yield f"data: {json.dumps({'sources': formatted_sources})}\n\n"
            else:
                yield f"data: {json.dumps({'chunk': item['chunk']})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ── Frontend (serve static files) ─────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(os.path.join(_FRONTEND_DIR, "index.html"))

app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")
