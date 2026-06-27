"""
Multi-chat memory system. Each user can have multiple chat sessions,
just like ChatGPT. One MongoDB document per chat session.
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from .db import get_collections


def _generate_chat_id() -> str:
    return f"chat_{uuid.uuid4().hex[:12]}"


def _auto_title(first_message: str) -> str:
    msg = (first_message or "").strip()
    if len(msg) <= 45:
        return msg
    return msg[:42] + "..."


# ── Migration from old single-doc format ────────────────────────────
def migrate_old_format(username: str):
    """Convert old single-doc-per-user to new multi-chat format (runs once)."""
    cols = get_collections()
    old_doc = cols["conversations"].find_one({
        "username": username,
        "chat_id": {"$exists": False}
    })
    if not old_doc:
        return

    messages = old_doc.get("messages", [])
    if not messages:
        cols["conversations"].delete_one({"_id": old_doc["_id"]})
        return

    chat_id = _generate_chat_id()
    title = _auto_title(messages[0].get("content", ""))

    cols["conversations"].insert_one({
        "chat_id": chat_id,
        "username": username,
        "title": title,
        "messages": messages,
        "created_at": old_doc.get("created_at", datetime.utcnow()),
        "updated_at": old_doc.get("updated_at", datetime.utcnow()),
    })
    cols["conversations"].delete_one({"_id": old_doc["_id"]})


# ── CRUD Operations ─────────────────────────────────────────────────
def list_user_chats(username: str) -> List[dict]:
    """List all chat sessions for a user, sorted by most recent."""
    migrate_old_format(username)
    cols = get_collections()
    docs = cols["conversations"].find(
        {"username": username},
        {"chat_id": 1, "title": 1, "updated_at": 1, "_id": 0}
    ).sort("updated_at", -1)
    return list(docs)


def create_chat(username: str, first_message: str = None) -> str:
    """Create a new chat session and return its chat_id."""
    cols = get_collections()
    now = datetime.utcnow()
    chat_id = _generate_chat_id()
    title = _auto_title(first_message) if first_message else "New Chat"

    cols["conversations"].insert_one({
        "chat_id": chat_id,
        "username": username,
        "title": title,
        "messages": [],
        "created_at": now,
        "updated_at": now,
    })
    return chat_id


def load_history(chat_id: str) -> List[dict]:
    """Load messages for a specific chat session."""
    cols = get_collections()
    doc = cols["conversations"].find_one({"chat_id": chat_id})
    if not doc:
        return []
    return doc.get("messages", [])


def append_messages(chat_id: str, new_messages: List[dict]):
    """Append messages to a specific chat session."""
    cols = get_collections()
    now = datetime.utcnow()
    for m in new_messages:
        m.setdefault("timestamp", now)

    cols["conversations"].update_one(
        {"chat_id": chat_id},
        {
            "$push": {"messages": {"$each": new_messages}},
            "$set": {"updated_at": now},
        }
    )


def update_chat_title(chat_id: str, new_title: str):
    """Rename a chat session."""
    cols = get_collections()
    cols["conversations"].update_one(
        {"chat_id": chat_id},
        {"$set": {"title": new_title.strip()[:80], "updated_at": datetime.utcnow()}}
    )


def delete_chat(chat_id: str):
    """Delete a chat session entirely."""
    cols = get_collections()
    cols["conversations"].delete_one({"chat_id": chat_id})


def clear_history(chat_id: str):
    """Clear all messages in a chat (keep the chat document)."""
    cols = get_collections()
    cols["conversations"].update_one(
        {"chat_id": chat_id},
        {"$set": {"messages": [], "updated_at": datetime.utcnow()}}
    )


def set_chat_title_from_message(chat_id: str, first_message: str):
    """Set title from first message only if still default."""
    cols = get_collections()
    doc = cols["conversations"].find_one({"chat_id": chat_id})
    if doc and doc.get("title") in ("New Chat", "محادثة جديدة", ""):
        cols["conversations"].update_one(
            {"chat_id": chat_id},
            {"$set": {"title": _auto_title(first_message)}}
        )


def build_history_string(messages: List[dict], max_turns: int = 6) -> str:
    """Turn the last N exchanges into a short transcript."""
    if not messages:
        return ""
    recent = messages[-(max_turns * 2):]
    lines = []
    for m in recent:
        speaker = "User" if m["role"] == "user" else "Agent"
        lines.append(f"{speaker}: {m['content']}")
    return "\n".join(lines)


# ── Date Grouping (for sidebar display) ─────────────────────────────
def group_chats_by_date(chats: List[dict]) -> Dict[str, List[dict]]:
    """Group chats into Today / Yesterday / Previous 7 Days / Older."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_ago = today_start - timedelta(days=7)

    groups = {
        "Today": [],
        "Yesterday": [],
        "Previous 7 Days": [],
        "Older": [],
    }

    for chat in chats:
        updated = chat.get("updated_at", now)
        if updated and updated >= today_start:
            groups["Today"].append(chat)
        elif updated and updated >= yesterday_start:
            groups["Yesterday"].append(chat)
        elif updated and updated >= week_ago:
            groups["Previous 7 Days"].append(chat)
        else:
            groups["Older"].append(chat)

    return {k: v for k, v in groups.items() if v}