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
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=8000)
    # Fail fast with a clear error instead of hanging the app.
    client.admin.command("ping")
    return client


def get_db():
    return get_mongo_client()[DB_NAME]


def get_collections() -> dict:
    db = get_db()
    return {
        "users": db["users"],                  # {username, password_hash, role, created_at}
        "tickets": db["tickets"],               # CRM leads captured by the agent
        "counters": db["counters"],             # auto-increment ticket_id sequence
        "conversations": db["conversations"],   # per-user chat history / memory
    }


def ensure_indexes():
    """Call once (e.g. on app startup) to make lookups fast and usernames unique."""
    cols = get_collections()
    cols["users"].create_index("username", unique=True)
    cols["tickets"].create_index("ticket_id", unique=True)
    cols["tickets"].create_index("timestamp")
    cols["conversations"].create_index("username", unique=True)
