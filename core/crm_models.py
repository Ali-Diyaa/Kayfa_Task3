"""
CRM ticket schema + persistence. Lifted directly from the sales_agent
notebook (Cell 17-18) and adapted to use core.db's shared collections
instead of a module-level pymongo client.
"""
import re
from datetime import datetime
from typing import List, Optional

import pymongo
from pydantic import BaseModel, Field

from .db import get_collections


# ── Phone validation (Egypt / KSA / UAE / Syria) ───────────────────────────
def validate_phone_number(phone: str) -> tuple[bool, str]:
    """Validates international phone numbers for Egypt, KSA, UAE, Syria.
    Returns (is_valid, cleaned_number)."""
    clean = re.sub(r"[\s\-\(\)]", "", phone or "")

    patterns = {
        "egypt": r"^(\+20|0020|0)?1[0-2,5]\d{8}$",
        "ksa": r"^(\+966|00966|0)?5\d{8}$",
        "uae": r"^(\+971|00971|0)?5\d{8}$",
        "syria": r"^(\+963|00963|0)?9\d{8}$",
    }

    for country, pattern in patterns.items():
        if re.match(pattern, clean):
            if clean.startswith("0"):
                clean = "+20" + clean[1:] if country == "egypt" else clean
            elif not clean.startswith("+"):
                clean = "+" + clean
            return True, clean

    if re.match(r"^\+\d{9,15}$", clean):
        return True, clean

    return False, phone


# ── Schema ──────────────────────────────────────────────────────────────────
class CRMTicket(BaseModel):
    """Structured CRM ticket written in Arabic, stored in MongoDB.

    Every field carries a Field(description=...) so the LLM that fills
    this schema knows exactly what to put in each slot. Technical terms
    (SOC, Power BI, Python, ...) stay in English even inside Arabic text.
    """

    name: str = Field(description="Full name of the prospect in Arabic or Latin script.")
    phone: str = Field(description="Phone or WhatsApp number with country code, e.g. '+20 1XX XXX XXXX — واتساب'.")
    email: str = Field(description="Email address; 'غير محدد' if not provided.")
    city: str = Field(description="City and country, e.g. 'القاهرة، مصر'.")
    language: str = Field(description="Preferred conversation language: 'العربية' or 'English'.")
    dialect: str = Field(description="Arabic dialect if applicable: 'اللهجة المصرية', 'اللهجة السعودية', 'اللهجة السورية', or 'فصحى'.")
    preferred_contact: str = Field(description="Best contact channel: 'واتساب', 'اتصال', 'بريد إلكتروني'.")
    best_time: str = Field(description="Best time to contact, e.g. 'مساءً بعد الساعة 6'.")
    products_of_interest: List[str] = Field(description="Specific Kayfa courses, tracks, or diplomas the prospect asked about, in their original English names.")
    goal: str = Field(description="The prospect's career or learning goal, in Arabic.")
    current_level: str = Field(description="Current skill level: 'مبتدئ', 'متوسط', 'متقدم'.")
    prerequisites_discussed: str = Field(description="Any prerequisites mentioned or clarified during the conversation, in Arabic.")
    lead_temperature: str = Field(description="Lead temperature: 'ساخن' (hot), 'دافئ' (warm), or 'بارد' (cold).")
    buying_signals: List[str] = Field(description="List of buying signals observed, in Arabic (e.g. 'سأل عن طرق الدفع').")
    budget_sensitivity: str = Field(description="Budget concern level: 'عالي', 'متوسط', 'منخفض', with a short Arabic note.")
    objections: List[str] = Field(description="List of objections raised by the prospect, in Arabic.")
    conversation_summary: str = Field(description="Concise Arabic summary of the entire conversation, keeping course names in English.")
    next_action: str = Field(description="Recommended next action for the sales rep, in Arabic.")


def save_lead_to_mongodb(ticket: CRMTicket, username: Optional[str] = None) -> str:
    """Persist a CRM ticket to MongoDB and return a human-readable ID like 'LEAD-2026-0042'."""
    cols = get_collections()

    counter = cols["counters"].find_one_and_update(
        {"_id": "ticket_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=pymongo.ReturnDocument.AFTER,
    )
    year = datetime.utcnow().year
    ticket_id = f"LEAD-{year}-{counter['seq']:04d}"

    ticket_dict = ticket.model_dump()
    ticket_dict["ticket_id"] = ticket_id
    ticket_dict["timestamp"] = datetime.utcnow()
    ticket_dict["created_by_username"] = username  # which logged-in visitor produced this lead

    cols["tickets"].insert_one(ticket_dict)
    return ticket_id


def list_tickets(limit: int = 200) -> List[dict]:
    cols = get_collections()
    return list(cols["tickets"].find().sort("timestamp", -1).limit(limit))
