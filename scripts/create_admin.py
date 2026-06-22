"""
Create (or promote) an admin user directly in MongoDB.
Run: python scripts/create_admin.py
"""
import getpass
import os
import sys
from datetime import datetime
from pathlib import Path

import bcrypt
import pymongo
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def main():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    client = pymongo.MongoClient(uri)
    users = client["kayfa_crm"]["users"]

    username = input("Admin username: ").strip().lower()
    if not username:
        print("✗ Username can't be empty.")
        return

    existing = users.find_one({"username": username})

    if existing:
        print(f"User '{username}' already exists with role '{existing.get('role')}'.")
        change_pw = input("Reset password too? [y/N]: ").strip().lower() == "y"
        update = {"$set": {"role": "admin"}}
        if change_pw:
            password = getpass.getpass("New password: ")
            update["$set"]["password_hash"] = hash_pw(password)
        users.update_one({"username": username}, update)
        print(f"✓ '{username}' is now an admin.")
    else:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("✗ Passwords don't match.")
            return
        if len(password) < 6:
            print("✗ Password must be at least 6 characters.")
            return
            
        users.insert_one({
            "username": username,
            "password_hash": hash_pw(password),  # ← NOW HASHED
            "role": "admin",
            "created_at": datetime.utcnow(),
        })
        print(f"✓ Admin user '{username}' created.")

if __name__ == "__main__":
    main()