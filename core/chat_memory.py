"""
Per-user conversation memory. One document per username in the
`conversations` collection — this is what lets a visitor log out, come
back tomorrow, and find their chat exactly where they left it.
"""
from datetime import datetime
from typing import List

from .db import get_collections


def load_history(username: str) -> List[dict]:
    cols = get_collections()
    doc = cols["conversations"].find_one({"username": username})
    if not doc:
        return []
    return doc.get("messages", [])


def append_messages(username: str, new_messages: List[dict]):
    """new_messages: list of {"role": "user"|"assistant", "content": str}"""
    cols = get_collections()
    now = datetime.utcnow()
    for m in new_messages:
        m.setdefault("timestamp", now)

    cols["conversations"].update_one(
        {"username": username},
        {
            "$push": {"messages": {"$each": new_messages}},
            "$set": {"updated_at": now},
            "$setOnInsert": {"username": username, "created_at": now},
        },
        upsert=True,
    )


def clear_history(username: str):
    cols = get_collections()
    cols["conversations"].update_one(
        {"username": username},
        {"$set": {"messages": [], "updated_at": datetime.utcnow()}},
        upsert=True,
    )


def build_history_string(messages: List[dict], max_turns: int = 6) -> str:
    """Turns the last N exchanges into a short transcript the agent can
    read as conversational memory/context."""
    if not messages:
        return ""
    recent = messages[-(max_turns * 2):]
    lines = []
    for m in recent:
        speaker = "User" if m["role"] == "user" else "Agent"
        lines.append(f"{speaker}: {m['content']}")
    return "\n".join(lines)
