"""
Authentication.
Roles live in MongoDB (users.role: "admin" | "user")
"""
from datetime import datetime
import re
import bcrypt
from .db import get_collections

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def register_user(username: str, password: str, confirm: str):
    username = (username or "").strip().lower()
    if not username or not password:
        return False, "Please enter username and password."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if password != confirm:
        return False, "Passwords do not match."

    cols = get_collections()
    if cols["users"].find_one({"username": username}):
        return False, "Username already exists. Try another."

    cols["users"].insert_one({
        "username": username,
        "password_hash": hash_password(password),
        "role": "user",
        "created_at": datetime.utcnow(),
    })
    return True, "Account created successfully! Please login."

def login_user(username: str, password: str):
    username = (username or "").strip()
    cols = get_collections()
    # --- FIX: case-insensitive search for admin ---
    user = cols["users"].find_one({
        "username": {"$regex": f"^{re.escape(username)}$", "$options": "i"}
    })
    if not user:
        return None, "Username not found."
    if not verify_password(password, user.get("password_hash", "")):
        return None, "Incorrect password."
    return user, None