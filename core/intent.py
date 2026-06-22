"""
Lightweight heuristics that steer the sales agent: what does the user
want (intent), how are they talking (dialect), and which sales playbook
should the system prompt switch to. Lifted verbatim from the notebook.
"""
import re

def detect_intent(user_message: str) -> str:
    """Detects user intent using simple keywords (no LLM call -> cheap & fast)."""
    msg = (user_message or "").lower()

    if re.search(r"(\+?\d{10,}|@|\bواتس|رقمي)", msg):
        return "ready_to_enroll"

    if any(k in msg for k in ["ready", "enroll", "register", "sign up", "سجل", "تسجيل", "ابدأ", "اشتراك", "رقم", "هاتف", "واتساب", "ايميل"]):
        return "ready_to_enroll"

    if any(k in msg for k in ["price", "cost", "how much", "سعر", "تكلفة", "كم", "ادفع", "تقسيط"]):
        return "price_sensitive"

    if any(k in msg for k in ["refund", "difficult", "hard", "not sure", "استرجاع", "صعب", "متردد", "خايف", "قلق"]):
        return "hesitant"

    if any(k in msg for k in ["vs", "or", "compare", "difference", "better", "افضل", "فرق", "مقارنة", "ولا"]):
        return "comparing_options"

    return "just_browsing"

def detect_dialect(text: str) -> str:
    """Heuristic dialect detector for Arabic text."""
    text = text or ""

    if re.search(r"\b(عايز|عاوز|كده|ازيك|إزيك|ايه|إيه|علشان|عشانك|خلاص|ده|دي)\b", text):
        return "العربية — اللهجة المصرية"
    if re.search(r"\b(ابغى|ابغي|أبغى|وش|وشو|كيف الحال|عشان|يبه|ياخي|الحين)\b", text):
        return "العربية — اللهجة السعودية"
    if re.search(r"\b(شو|بدي|كيفك|هلق|مشان|شقد|لسا|هون|ليش)\b", text):
        return "العربية — اللهجة السورية"
    if re.search(r"[\u0600-\u06FF]", text):
        return "العربية — فصحى"
    return "English"

def is_arabic_text(text: str) -> bool:
    """Used by the UI to set dir='rtl' on chat bubbles."""
    return bool(re.search(r"[\u0600-\u06FF]", text or ""))

def get_dynamic_sales_prompt(intent: str) -> str:
    """Builds the sales-strategy prompt segment that adapts to detected intent - ENGLISH ONLY."""
    base_prompt = (
        "You are the Kayfa AI Sales Agent.\n"
        "Kayfa is an IAO-accredited Arabic educational platform by Kayfa Digital Solutions.\n\n"
        "=== GROUNDING RULES (NON-NEGOTIABLE) ===\n"
        "1. Answer ONLY from the RETRIEVED CONTEXT or tool outputs provided to you.\n"
        "2. NEVER invent course names, prices, durations, dates, or policies.\n"
        "3. If the context does not contain the answer, say you don't have the information\n"
        " and offer to connect them with the sales team in the user's language.\n"
        "4. Do NOT use your pre-trained knowledge about Kayfa — use ONLY the context.\n"
        "5. Always cite the source filename once at the end, not inline.\n\n"
        "=== LANGUAGE RULES ===\n"
        "6. Detect the user's language and reply in the same language.\n"
        "7. Keep technical terms (SOC, Power BI, Python, Splunk, SQL, etc.) in English.\n"
        "8. If Arabic, match the user's dialect when possible.\n\n"
        "=== SALES RULES ===\n"
        "9. Be persuasive but honest. Never claim a feature that isn't in the context.\n"
        "10. Guide warm leads toward tracks and diplomas when it fits their goal.\n"
        "11. When the user shows buying signals or shares contact info, collect:\n"
        " name, phone/WhatsApp, email, city, goal — then call capture_lead.\n"
    )

    intent_prompts = {
        "just_browsing": (
            "STRATEGY: The user is just browsing. Be warm and helpful.\n"
            "Recommend free content or beginner courses to build trust.\n"
            "Do NOT push for enrollment yet."
        ),
        "comparing_options": (
            "STRATEGY: The user is comparing options.\n"
            "Highlight concrete differences between tracks and diplomas\n"
            "(duration, price, tools, career outcome) FROM THE CONTEXT.\n"
            "Guide toward the higher-value diploma if it genuinely fits."
        ),
        "price_sensitive": (
            "STRATEGY: The user is price-sensitive.\n"
            "Mention free content, affordable individual courses ($15-$65),\n"
            "and installment options ONLY if mentioned in context.\n"
            "Emphasize ROI and career outcomes from the diploma pitches."
        ),
        "hesitant": (
            "STRATEGY: The user is hesitant.\n"
            "Address objections using the objection-handling sections\n"
            "in the diploma markdown. Use trust signals (IAO accreditation,\n"
            "instructors, 15,000+ learners) ONLY from the context."
        ),
        "ready_to_enroll": (
            "STRATEGY: HOT LEAD — ready to enroll.\n"
            "Pivot to collecting details: name, phone/WhatsApp, email,\n"
            "city, goal. Then call capture_lead with a full ticket."
        ),
    }

    return base_prompt + "\n" + intent_prompts.get(intent, intent_prompts["just_browsing"])