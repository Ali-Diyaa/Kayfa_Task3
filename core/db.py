"""
MongoDB connection layer.

Single shared client (cached so Streamlit doesn't reopen a connection
on every rerun). Everything else in the app talks to Mongo through
get_collections() so there's one source of truth for collection names.
"""
import os
import streamlit as st
import pymongo
from dotenv import load_dotenv

load_dotenv()

DB_NAME = "kayfa_crm"


@st.cache_resource(show_spinner=False)
def get_mongo_client() -> pymongo.MongoClient:
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    client = pymongo.MongoClient(
        uri,
        serverSelectionTimeoutMS=30000,   # 30s — Atlas needs more time than localhost
        connectTimeoutMS=30000,           # 30s for initial TCP connection
        socketTimeoutMS=None,             # No socket timeout — let operations finish
        retryWrites=True,                 # Atlas requires this
        retryReads=True,                  # Auto-retry on read failures
        maxPoolSize=10,                   # Connection pool size
        minPoolSize=2,                    # Keep 2 connections warm (prevents cold-start lag)
    )
    # Verify the connection actually works
    client.admin.command("ping")
    return client


def get_db():
    return get_mongo_client()[DB_NAME]


def get_collections() -> dict:
    db = get_db()
    return {
        "users": db["users"],
        "tickets": db["tickets"],
        "counters": db["counters"],
        "conversations": db["conversations"],
        "usage_logs": db["usage_logs"],
    }


def ensure_indexes():
    """Call once on app startup."""
    cols = get_collections()
    cols["users"].create_index("username", unique=True)
    cols["tickets"].create_index("ticket_id", unique=True)
    cols["tickets"].create_index("timestamp")

    try:
        cols["conversations"].drop_index("username_1")
    except Exception:
        pass

    cols["conversations"].create_index("chat_id", unique=True)
    cols["conversations"].create_index(
        [("username", 1), ("updated_at", -1)]
    )

    # ── Usage Logs indexes ──
    cols["usage_logs"].create_index("chat_id")
    cols["usage_logs"].create_index("user_id")
    cols["usage_logs"].create_index([("timestamp", -1)])
    cols["usage_logs"].create_index([("user_id", 1), ("timestamp", -1)])


def safe_get_collections() -> dict | None:
    """
    Try to get collections with retry on connection failure.
    Returns None if the database is unreachable — pages should
    handle this gracefully instead of crashing.
    """
    try:
        cols = get_collections()
        # Quick liveness check
        cols["users"].find_one(limit=1)
        return cols
    except pymongo.errors.ConnectionFailure:
        # Force-clear the cached client so next call creates a fresh one
        get_mongo_client.clear()
        try:
            cols = get_collections()
            cols["users"].find_one(limit=1)
            return cols
        except Exception:
            return None
    except Exception:
        return None