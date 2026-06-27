"""
Lightweight heuristics that steer the sales agent: what does the user
want (intent), how are they talking (dialect), and which sales playbook
should the system prompt switch to.
"""
import re


def detect_intent(user_message: str) -> str:
    """
    Rule-based intent classifier. Uses re.search() throughout to avoid
    the substring false-positive bug (e.g. 'كم' inside 'عندكم').
    Priority order: ready_to_enroll → comparing → hesitant → price_sensitive → browsing
    """
    msg = user_message.lower()

    # ── 1. READY TO ENROLL (most specific — check first) ──────────────────
    # Phone number present
    if re.search(r'\+?\d[\d\s\-]{8,}\d', msg):
        return "ready_to_enroll"

    if re.search(
        r'(واتس|واتساب|هاتف|تلفون|موبايل|رقمي|ايميلي|@)',
        msg
    ):
        return "ready_to_enroll"

    if re.search(
        r'\b(ready|enroll|register|sign\s?up|subscribe)\b',
        msg
    ):
        return "ready_to_enroll"

    if re.search(
        r'(اسمي|اسمى|سجلني|سجل|اشتراك|اشترك|انضم|ابدأ دلوقتي|عايز ابدأ)',
        msg
    ):
        return "ready_to_enroll"

    # ── 2. COMPARING OPTIONS ───────────────────────────────────────────────
    if re.search(r'\b(vs\.?|compare|difference|better|which)\b', msg):
        return "comparing_options"

    if re.search(
        r'(الأفضل|افضل|الفرق|فرق بين|مقارنة|ولا|أو بين|ايهما|أيهما)',
        msg
    ):
        return "comparing_options"

    # ── 3. HESITANT ────────────────────────────────────────────────────────
    if re.search(r'\b(refund|difficult|hard|not\s?sure|guarantee|risk)\b', msg):
        return "hesitant"

    if re.search(
        r'(استرجاع|ضمان|صعب|متردد|خايف|قلق|مضمون|هينفع|هيفيد|مش واثق)',
        msg
    ):
        return "hesitant"

    # ── 4. PRICE SENSITIVE ─────────────────────────────────────────────────
    # NOTE: Never use bare "كم" — it's a substring of عندكم / يمكن / etc.
    # Use anchored patterns only.
    if re.search(r'\b(price|cost|how\s?much|fee|payment|installment|cheap)\b', msg):
        return "price_sensitive"

    if re.search(
        r'(بكام|بكم\b|سعره|سعرها|سعر\s|تكلفة|كلفة|ادفع|تقسيط|الثمن|الرسوم)',
        msg
    ):
        return "price_sensitive"

    # ── 5. DEFAULT ─────────────────────────────────────────────────────────
    return "just_browsing"


def detect_dialect(text: str) -> str:
    """
    Heuristic dialect detector. Uses re.search() without \\b because Arabic
    word boundaries are unreliable across regex engines.
    Checks most-specific dialects first; falls back to MSA then English.
    """

    # ── Egyptian (largest user base; check before Gulf/Levantine) ──────────
    # Core particles: ايه/وايه (what), ده/دي (this), علشان, دلوقتي, بكام, فين, ليه …
    if re.search(
        r'(عايز|عاوز|إيه|ايه|وايه|علشان|خلاص|ده\b|دي\b|دول|'
        r'دلوقتي|امتى|فين\b|مين\b|ليه\b|إزيك|ازيك|ازاي|بكام|'
        r'قبل ما|اهو\b|مش\b|زيك|زيه|كده|يعني إيه)',
        text
    ):
        return "العربية — اللهجة المصرية"

    # ── Saudi / Gulf ────────────────────────────────────────────────────────
    if re.search(
        r'(ابغى|ابغي|أبغى|وش\b|يبه|ياخي|الحين|زين\b|عندي وقت|'
        r'شلون|هذا الشي|ودي|ما ودي)',
        text
    ):
        return "العربية — اللهجة السعودية / الخليجية"

    # ── Levantine (Syrian / Lebanese) ──────────────────────────────────────
    if re.search(
        r'(شو\b|بدي|كيفك|هلق|مشان|شقد|هون\b|ليش\b|عم\b|رح\b|'
        r'هيك|منيح|سيدي|يا زلمة)',
        text
    ):
        return "العربية — اللهجة الشامية"

    # ── Arabic but no dialect marker → MSA ─────────────────────────────────
    if re.search(r'[\u0600-\u06FF]', text):
        return "العربية — فصحى"

    return "English"


def is_arabic_text(text: str) -> bool:
    return bool(re.search(r'[\u0600-\u06FF]', text or ""))


def get_intent_strategy(intent: str) -> str:
    """
    Returns ONLY the intent-specific strategy block.
    This is appended to BASE_PROMPT by the system_prompt decorator —
    never rebuild the base here, to avoid doubling the token count.
    """
    strategies = {
        "just_browsing": (
            "═══ SALES STRATEGY: EXPLORER ═══\n"
            "The user is just browsing — be warm and curious.\n"
            "• Recommend free content or beginner courses to build trust.\n"
            "• Ask one soft discovery question about their goal or background.\n"
            "• Do NOT push for enrollment or pricing yet."
        ),
        "comparing_options": (
            "═══ SALES STRATEGY: COMPARISON ═══\n"
            "The user is weighing options — be concrete and data-driven.\n"
            "• Pull duration, price, tools, and career outcome FROM TOOL RESULTS only.\n"
            "• Present a clear side-by-side view using bullet points.\n"
            "• Recommend the higher-value option only if it genuinely fits their goal."
        ),
        "price_sensitive": (
            "═══ SALES STRATEGY: BUDGET-AWARE ═══\n"
            "The user is cost-conscious — lead with value, not price.\n"
            "• Mention free content or low-cost individual courses ($15–$65) first.\n"
            "• Highlight ROI and career outcomes from the retrieved diploma content.\n"
            "• Mention installments ONLY if explicitly stated in the retrieved context."
        ),
        "hesitant": (
            "═══ SALES STRATEGY: TRUST-BUILDER ═══\n"
            "The user has doubts — address objections directly.\n"
            "• Use trust signals (IAO accreditation, 15,000+ learners, instructors)\n"
            "  ONLY if they appear in the retrieved context.\n"
            "• Invite them to ask any concern — never rush to close."
        ),
        "ready_to_enroll": (
            "═══ SALES STRATEGY: HOT LEAD — CLOSE ═══\n"
            "The user is ready — pivot immediately to lead capture.\n"
            "• Confirm or collect: name, phone/WhatsApp, email, city, goal.\n"
            "• Once you have name + phone, call capture_lead immediately.\n"
            "• Answer any remaining product question WHILE collecting details."
        ),
    }

    return strategies.get(intent, strategies["just_browsing"])


