# session_store.py
"""
In-memory session store with JSON persistence.
Sessions survive server restarts via sessions.json.
"""
import uuid
import json
import os
from datetime import datetime

_SESSIONS_FILE = os.path.join(os.path.dirname(__file__), "sessions.json")
_sessions: dict[str, dict] = {}


# ── Persistence helpers ────────────────────────────────────────────────────────

def _load() -> None:
    global _sessions
    if os.path.exists(_SESSIONS_FILE):
        try:
            with open(_SESSIONS_FILE, "r", encoding="utf-8") as f:
                _sessions = json.load(f)
        except (json.JSONDecodeError, IOError):
            _sessions = {}


def _save() -> None:
    try:
        with open(_SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(_sessions, f, indent=2, ensure_ascii=False)
    except IOError:
        pass


_load()  # Load on import


# ── Public API ────────────────────────────────────────────────────────────────

def create_session(doc_id: str, filename: str) -> str:
    """Create a new chat session and return its session_id."""
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    _sessions[session_id] = {
        "doc_id": doc_id,
        "filename": filename,
        "created_at": datetime.now().isoformat(),
        "messages": [],          # [{"role": "human"|"ai", "content": str, "timestamp": str}]
    }
    _save()
    return session_id


def get_session(session_id: str) -> dict | None:
    return _sessions.get(session_id)


def add_message(session_id: str, role: str, content: str) -> None:
    """Append a message to the session history."""
    if session_id not in _sessions:
        return
    _sessions[session_id]["messages"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    })
    _save()


def get_history(session_id: str) -> list[dict]:
    return _sessions.get(session_id, {}).get("messages", [])


def delete_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
    _save()


def delete_all_sessions() -> None:
    """Clear all sessions from memory and disk."""
    global _sessions
    _sessions = {}
    _save()


def list_sessions() -> list[dict]:
    return [
        {
            "session_id": sid,
            "doc_id": data["doc_id"],
            "filename": data["filename"],
            "created_at": data["created_at"],
            "message_count": len(data["messages"]),
        }
        for sid, data in _sessions.items()
    ]
