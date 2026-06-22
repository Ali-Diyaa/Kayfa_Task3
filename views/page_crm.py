"""
PAGE 2 — CRM Tickets (admin-only).

Every lead the agent captured in MongoDB shows up here as a collapsible
card — click to expand and see the full picture: contact info, intent,
buying signals, objections, AI-written conversation summary, and the
recommended next action for the rep.

Access control: app.py only adds this page to navigation when
st.session_state.role == "admin". This module itself re-checks the role
too, so it's safe even if someone messes with navigation state.
"""
import streamlit as st
from datetime import datetime

from core.crm_models import list_tickets
from core.styles import page_header

TEMP_CONFIG = {
    "ساخن": {"en": "Hot", "emoji": "🔥", "color": "#ef4444", "bg": "rgba(239,68,68,0.15)"},
    "دافئ": {"en": "Warm", "emoji": "🌤️", "color": "#f59e0b", "bg": "rgba(245,158,11,0.15)"},
    "بارد": {"en": "Cold", "emoji": "❄️", "color": "#3b82f6", "bg": "rgba(59,130,246,0.15)"},
}

def _fmt(value):
    if isinstance(value, list):
        return "، ".join(value) if value else "—"
    return value if value else "—"

def _ticket_card_html(t: dict) -> str:
    ticket_id = t.get("ticket_id", "—")
    name = t.get("name", "No name")
    phone = _fmt(t.get("phone"))
    city = _fmt(t.get("city"))
    language = f"{t.get('language','—')} — {t.get('dialect','—')}"
    products = _fmt(t.get("products_of_interest"))
    goal = _fmt(t.get("goal"))
    level = _fmt(t.get("current_level"))
    signals = _fmt(t.get("buying_signals"))
    objections = _fmt(t.get("objections"))
    summary = t.get("conversation_summary", "—")
    next_action = t.get("next_action", "—")

    ts = t.get("timestamp")
    ts_str = ts.strftime("%Y-%m-%d · %H:%M") if isinstance(ts, datetime) else "—"

    temp = t.get("lead_temperature", "")
    cfg = TEMP_CONFIG.get(temp, TEMP_CONFIG["بارد"])
    temp_en = cfg["en"]
    emoji = cfg["emoji"]
    color = cfg["color"]
    bg = cfg["bg"]

    # Get initials for avatar
    initials = "".join([p[0] for p in name.split()[:2]]) if name!= "No name" else "؟"
    phone_clean = "".join(filter(str.isdigit, phone))

    return f"""
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
    <div dir="rtl" style="font-family:'Cairo',sans-serif; margin-bottom:24px;">
        <div style="position:relative; overflow:hidden; border-radius:24px; background:linear-gradient(180deg,#0B1220 0%,#0a0f1c 100%); border:1px solid rgba(255,255,255,0.08); box-shadow:0 20px 40px rgba(0,0,0,0.4);">
            <!-- Header -->
            <div style="background:linear-gradient(90deg,#2563eb 0%,#1d4ed8 100%); padding:24px 28px 80px; position:relative;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <div style="color:rgba(255,255,255,0.7); font-size:11px; margin-bottom:4px;">رقم التذكرة</div>
                        <div style="color:white; font-weight:700; font-size:18px; letter-spacing:0.5px;">{ticket_id}</div>
                    </div>
                    <div style="display:flex; flex-direction:column; align-items:flex-end; gap:8px;">
                        <div style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; border-radius:999px; background:{color}; color:white; font-size:12px; font-weight:700; box-shadow:0 4px 12px {bg};">
                            <span>{emoji}</span><span>{temp or '—'}</span>
                        </div>
                        <span style="padding:4px 10px; border-radius:999px; background:rgba(255,255,255,0.15); color:rgba(255,255,255,0.9); font-size:11px; border:1px solid rgba(255,255,255,0.2);">عميل محتمل</span>
                    </div>
                </div>

                <div style="margin-top:24px; display:flex; align-items:center; gap:16px;">
                    <div style="position:relative;">
                        <div style="width:72px; height:72px; border-radius:16px; background:rgba(255,255,255,0.15); backdrop-filter:blur(10px); border:2px solid rgba(255,255,255,0.3); display:flex; align-items:center; justify-content:center; box-shadow:0 8px 24px rgba(0,0,0,0.2);">
                            <span style="color:white; font-weight:800; font-size:24px;">{initials}</span>
                        </div>
                        <div style="position:absolute; bottom:-4px; left:-4px; width:20px; height:20px; background:#22c55e; border-radius:50%; border:3px solid #1d4ed8;"></div>
                    </div>
                    <div style="flex:1;">
                        <h2 style="color:white; font-weight:800; font-size:26px; margin:0 0 6px 0; line-height:1.2;">{name}</h2>
                        <div style="display:flex; align-items:center; gap:8px; color:rgba(255,255,255,0.85); font-size:14px;">
                            <span>📍 {city}</span>
                            <span style="width:4px; height:4px; background:rgba(255,255,255,0.4); border-radius:50%;"></span>
                            <span style="color:rgba(255,255,255,0.7); font-size:12px;">{level}</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Content -->
            <div style="padding:0 28px 28px; margin-top:-40px; position:relative;">
                <!-- Action Buttons -->
                <div style="display:flex; gap:8px; margin-bottom:20px; flex-wrap:wrap;">
                    <a href="https://wa.me/{phone_clean}" target="_blank" style="display:inline-flex; align-items:center; gap:8px; padding:10px 16px; background:#25D366; color:white; border-radius:12px; font-weight:600; font-size:14px; text-decoration:none; box-shadow:0 4px 12px rgba(37,211,102,0.3);">
                        💬 واتساب
                    </a>
                    <div style="padding:10px 16px; background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.9); border-radius:12px; font-size:14px; border:1px solid rgba(255,255,255,0.1); font-family:monospace; direction:ltr;">
                        {phone}
                    </div>
                </div>

                <!-- Fields Grid -->
                <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px;">
                    {''.join([f'''
                    <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:16px; padding:16px; transition:all 0.2s;">
                        <div style="display:flex; gap:12px; align-items:flex-start;">
                            <div style="width:40px; height:40px; border-radius:12px; background:{item[2]}; display:flex; align-items:center; justify-content:center; flex-shrink:0; font-size:18px;">{item[3]}</div>
                            <div style="flex:1; min-width:0;">
                                <div style="color:#94a3b8; font-size:11px; margin-bottom:4px; font-weight:500;">{item[0]}</div>
                                <div style="color:white; font-weight:600; font-size:14px; line-height:1.4;">{item[1]}</div>
                            </div>
                        </div>
                    ''' for item in [
                        ("اللغة", language, "rgba(37,99,235,0.15)", "🌐"),
                        ("المدينة", city, "rgba(139,92,246,0.15)", "📍"),
                        ("المنتجات", products, "rgba(37,99,235,0.2)", "🎓"),
                        ("الهدف", goal, "rgba(16,185,129,0.15)", "🎯"),
                        ("المستوى", level, "rgba(245,158,11,0.15)", "📊"),
                        ("إشارات الشراء", signals, "rgba(34,197,94,0.15)", "📈"),
                        ("الاعتراضات", objections, "rgba(249,115,22,0.15)", "⚠️"),
                    ]])}
                </div>

                <!-- Summary & Next -->
                <div style="display:grid; grid-template-columns:2fr 1fr; gap:16px; margin-top:20px;">
                    <div style="background:#111b2f; border:1px solid rgba(255,255,255,0.08); border-radius:16px; padding:20px;">
                        <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
                            <div style="width:28px; height:28px; border-radius:8px; background:rgba(255,255,255,0.1); display:flex; align-items:center; justify-content:center;">📝</div>
                            <h3 style="color:white; font-weight:700; margin:0; font-size:15px;">ملخص المحادثة</h3>
                        </div>
                        <p style="color:#cbd5e1; line-height:1.7; margin:0; font-size:14px;">{summary}</p>
                    </div>

                    <div style="background:linear-gradient(180deg,rgba(37,99,235,0.2) 0%,rgba(30,64,175,0.2) 100%); border:1px solid rgba(37,99,235,0.3); border-radius:16px; padding:20px;">
                        <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
                            <div style="width:28px; height:28px; border-radius:8px; background:#2563eb; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 12px rgba(37,99,235,0.3);">✓</div>
                            <h3 style="color:white; font-weight:700; margin:0; font-size:15px;">الإجراء التالي</h3>
                        </div>
                        <p style="color:rgba(255,255,255,0.9); line-height:1.6; margin:0 0 12px 0; font-size:13px; font-weight:500;">{next_action}</p>
                        <div style="display:flex; align-items:center; gap:6px; color:#93c5fd; font-size:11px;">
                            <div style="width:6px; height:6px; background:#60a5fa; border-radius:50%; animation:pulse 2s infinite;"></div>
                            أولوية عالية
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:20px; padding-top:16px; border-top:1px solid rgba(255,255,255,0.05); color:#64748b; font-size:12px;">
                    <span>🕒 آخر تحديث: {ts_str}</span>
                    <span style="display:flex; align-items:center; gap:6px;"><span style="width:6px; height:6px; background:#22c55e; border-radius:50%;"></span>نشط</span>
                </div>
            </div>
        </div>
    <style>@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.5}}}}</style>
    """

def show():
    if st.session_state.get("role")!= "admin":
        st.error("This page is available for the sales team (admin) only.")
        return

    page_header(
        "🎯 CRM — Leads",
        "Every ticket here was captured automatically from a chatbot conversation."
    )

    tickets = list_tickets()
    if not tickets:
        st.info("No tickets yet. They will appear here once the chatbot captures a lead.")
        return

    # ── Filters ─────────────────────────────────────────────────────────
    c1, c2 = st.columns([1, 2])
    with c1:
        temp_filter = st.selectbox(
            "Filter by temperature",
            ["All", "ساخن", "دافئ", "بارد"]
        )
    with c2:
        search = st.text_input("Search by name / phone / ticket ID", "")

    filtered = tickets
    if temp_filter!= "All":
        filtered = [t for t in filtered if t.get("lead_temperature") == temp_filter]
    if search.strip():
        s = search.strip().lower()
        filtered = [
            t for t in filtered
            if s in str(t.get("name", "")).lower()
            or s in str(t.get("phone", "")).lower()
            or s in str(t.get("ticket_id", "")).lower()
        ]

    st.caption(f"Showing {len(filtered)} of {len(tickets)} tickets")
    st.markdown("<div style='height:1px; background:rgba(255,255,255,0.1); margin:16px 0;'></div>", unsafe_allow_html=True)

    for t in filtered:
        # Render the beautiful card
        st.markdown(_ticket_card_html(t), unsafe_allow_html=True)