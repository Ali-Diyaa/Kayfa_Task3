import streamlit as st
from datetime import datetime
import streamlit.components.v1 as components

from core.crm_models import list_tickets
from core.styles import page_header

TEMP_CONFIG = {
    "ساخن": {"en": "Hot", "emoji": "🔥", "color": "#ef4444"},
    "دافئ": {"en": "Warm", "emoji": "🌤", "color": "#f59e0b"},
    "بارد": {"en": "Cold", "emoji": "❄", "color": "#3b82f6"},
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
    temp = t.get("lead_temperature", "بارد")
    cfg = TEMP_CONFIG.get(temp, TEMP_CONFIG["بارد"])

    initials = "".join([p[0] for p in name.split()[:2]]) if name!= "No name" else "؟"
    phone_clean = "".join(filter(str.isdigit, phone))

    html = f"""
    <div dir="rtl" style="font-family:'Cairo', system-ui, sans-serif; margin-bottom:24px;">
        <div style="border-radius:20px; background:#0B1220; border:1px solid #1e293b; overflow:hidden;">
            <div style="background:linear-gradient(90deg,#2563eb,#1d4ed8); padding:24px; color:white;">
                <div style="display:flex; justify-content:space-between; align-items:start;">
                    <div>
                        <div style="opacity:0.7; font-size:12px;">رقم التذكرة</div>
                        <div style="font-weight:700; font-size:18px;">{ticket_id}</div>
                    </div>
                    <div style="background:{cfg['color']}; padding:6px 12px; border-radius:20px; font-size:12px; font-weight:700;">
                        {cfg['emoji']} {temp}
                    </div>
                </div>
                <div style="margin-top:20px; display:flex; align-items:center; gap:14px;">
                    <div style="width:60px; height:60px; border-radius:14px; background:rgba(255,255,255,0.15); display:flex; align-items:center; justify-content:center; font-weight:800; font-size:22px; border:2px solid rgba(255,255,255,0.3);">
                        {initials}
                    </div>
                    <div>
                        <h2 style="margin:0 0 4px 0; font-size:22px;">{name}</h2>
                        <div style="opacity:0.85; font-size:14px;">📍 {city} • {level}</div>
                    </div>
                </div>
            </div>

            <div style="padding:20px;">
                <div style="display:flex; gap:8px; margin-bottom:16px;">
                    <a href="https://wa.me/{phone_clean}" target="_blank" style="background:#25D366; color:white; padding:8px 14px; border-radius:10px; text-decoration:none; font-size:14px; font-weight:600;">💬 واتساب</a>
                    <div style="background:#1e293b; color:#e2e8f0; padding:8px 14px; border-radius:10px; font-family:monospace; direction:ltr; font-size:14px;">{phone}</div>
                </div>

                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:16px;">
                    <div style="background:#111827; padding:12px; border-radius:12px; border:1px solid #1f2937;">
                        <div style="color:#9ca3af; font-size:11px; margin-bottom:4px;">اللغة</div>
                        <div style="color:white; font-size:14px;">{language}</div>
                    </div>
                    <div style="background:#111827; padding:12px; border-radius:12px; border:1px solid #1f2937;">
                        <div style="color:#9ca3af; font-size:11px; margin-bottom:4px;">المنتجات</div>
                        <div style="color:white; font-size:14px;">{products}</div>
                    </div>
                    <div style="background:#111827; padding:12px; border-radius:12px; border:1px solid #1f2937;">
                        <div style="color:#9ca3af; font-size:11px; margin-bottom:4px;">الهدف</div>
                        <div style="color:white; font-size:14px;">{goal}</div>
                    </div>
                    <div style="background:#111827; padding:12px; border-radius:12px; border:1px solid #1f2937;">
                        <div style="color:#9ca3af; font-size:11px; margin-bottom:4px;">إشارات الشراء</div>
                        <div style="color:white; font-size:14px;">{signals}</div>
                    </div>
                </div>

                <div style="background:#111b2f; padding:16px; border-radius:12px; border:1px solid #1e3a8a; margin-bottom:12px;">
                    <div style="color:#60a5fa; font-weight:700; margin-bottom:8px; font-size:14px;">📝 ملخص المحادثة</div>
                    <div style="color:#cbd5e1; line-height:1.6; font-size:14px;">{summary}</div>
                </div>

                <div style="background:rgba(37,99,235,0.1); padding:16px; border-radius:12px; border:1px solid rgba(37,99,235,0.3);">
                    <div style="color:#93c5fd; font-weight:700; margin-bottom:8px; font-size:14px;">✓ الإجراء التالي</div>
                    <div style="color:#e0e7ff; font-size:14px;">{next_action}</div>
                </div>

                <div style="margin-top:12px; padding-top:12px; border-top:1px solid #1f2937; color:#6b7280; font-size:12px; display:flex; justify-content:space-between;">
                    <span>🕒 {ts_str}</span>
                    <span>● نشط</span>
                </div>
            </div>
        </div>
    </div>
    """
    return html

def show():
    if st.session_state.get("role")!= "admin":
        st.error("This page is available for the sales team (admin) only.")
        return

    page_header("🎯 CRM — Leads", "Every ticket here was captured automatically from a chatbot conversation.")

    tickets = list_tickets()
    if not tickets:
        st.info("No tickets yet. They will appear here once the chatbot captures a lead.")
        return

    c1, c2 = st.columns([1, 2])
    with c1:
        temp_filter = st.selectbox("Filter by temperature", ["All", "ساخن", "دافئ", "بارد"])
    with c2:
        search = st.text_input("Search by name / phone / ticket ID", "")

    filtered = tickets
    if temp_filter!= "All":
        filtered = [t for t in filtered if t.get("lead_temperature") == temp_filter]
    if search.strip():
        s = search.strip().lower()
        filtered = [t for t in filtered if s in str(t.get("name", "")).lower() or s in str(t.get("phone", "")).lower() or s in str(t.get("ticket_id", "")).lower()]

    st.caption(f"Showing {len(filtered)} of {len(tickets)} tickets")
    st.divider()

    for t in filtered:
        components.html(_ticket_card_html(t), height=600, scrolling=False)