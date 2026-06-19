import uuid
from datetime import datetime
from database import SessionLocal, ChatSession, ChatMessage

def create_session(doc_id: str, filename: str) -> str:
    """Create a new chat session and return its session_id."""
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        new_session = ChatSession(
            session_id=session_id,
            doc_id=doc_id,
            filename=filename
        )
        db.add(new_session)
        db.commit()
    return session_id

def get_session(session_id: str) -> dict | None:
    with SessionLocal() as db:
        sess = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if not sess:
            return None
        return {
            "session_id": sess.session_id,
            "doc_id": sess.doc_id,
            "filename": sess.filename,
            "created_at": sess.created_at.isoformat() if sess.created_at else None,
            "messages": get_history(session_id)
        }

def add_message(session_id: str, role: str, content: str) -> None:
    """Append a message to the session history."""
    with SessionLocal() as db:
        new_msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content
        )
        db.add(new_msg)
        db.commit()

def get_history(session_id: str) -> list[dict]:
    with SessionLocal() as db:
        messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.id).all()
        return [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None
            }
            for m in messages
        ]

def delete_session(session_id: str) -> None:
    with SessionLocal() as db:
        sess = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if sess:
            db.delete(sess)
            db.commit()

def delete_all_sessions() -> None:
    """Clear all sessions from the database."""
    with SessionLocal() as db:
        db.query(ChatSession).delete()
        db.commit()

def list_sessions() -> list[dict]:
    with SessionLocal() as db:
        sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
        result = []
        for sess in sessions:
            msg_count = db.query(ChatMessage).filter(ChatMessage.session_id == sess.session_id).count()
            result.append({
                "session_id": sess.session_id,
                "doc_id": sess.doc_id,
                "filename": sess.filename,
                "created_at": sess.created_at.isoformat() if sess.created_at else None,
                "message_count": msg_count,
            })
        return result
