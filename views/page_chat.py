"""
PAGE 1 — Chat with the Kayfa AI Sales Agent.
Multi-chat sidebar (ChatGPT-style) + modern light-mode chat interface.
"""
import asyncio
import html
import base64
import sys
from pathlib import Path
import streamlit as st

from core.agent import handle_user_message
from core.chat_memory import (
    list_user_chats, create_chat, load_history,
    delete_chat, update_chat_title, set_chat_title_from_message,
    group_chats_by_date,
)
from core.intent import is_arabic_text

# ── Fix Windows asyncio issue ──
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# --- Logo ---
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "kayfa_logo.png"
def _get_logo_base64():
    if LOGO_PATH.exists():
        return base64.b64encode(LOGO_PATH.read_bytes()).decode()
    return None

LOGO_B64 = _get_logo_base64()

QUICK_PROMPTS = [
    ("🛡️", "عايز اعرف الفرق بين دبلومة SOC والتراك المسجل"),
    ("💰", "كام سعر مسار تحليل البيانات؟"),
    ("🎓", "إيه هي الدبلومات الحية المتاحة عندكم؟"),
    ("🚀", "عايز اسجل دلوقتي، إزاي أبدأ؟"),
]

import re

def _has_arabic(text: str) -> bool:
    return bool(re.search(r'[\u0600-\u06FF]', text or ""))


def _render_content_with_tables(content: str) -> str:
    lines = content.split('\n')
    html_parts = []
    in_table = False
    table_rows = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('|') and stripped.endswith('|') and len(stripped) > 2:
            if not in_table:
                in_table = True
                table_rows = []

            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            is_separator = all(re.match(r'^[-:]+$', c) for c in cells)

            if not is_separator:
                table_rows.append(cells)
        else:
            if in_table:
                html_parts.append(_build_html_table(table_rows))
                in_table = False
                table_rows = []

            if stripped:
                safe_line = html.escape(stripped)
                safe_line = re.sub(
                    r'&lt;(https?://[^&]+)&gt;',
                    r'<a href="\1" target="_blank" style="color:#6366f1;text-decoration:none;font-weight:500;">\1</a>',
                    safe_line
                )
                safe_line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', safe_line)
                html_parts.append(f'<p style="margin:4px 0;line-height:1.85;">{safe_line}</p>')

    if in_table:
        html_parts.append(_build_html_table(table_rows))

    return '\n'.join(html_parts)


def _build_html_table(rows: list) -> str:
    if not rows:
        return ''

    table_html = '''<div style="overflow-x:auto;margin:14px 0 10px;border-radius:12px;border:1px solid #e2e8f0;">
    <table style="width:100%;border-collapse:collapse;font-size:13px;min-width:500px;">'''

    for i, row in enumerate(rows):
        is_header = (i == 0)
        tag = 'th' if is_header else 'td'
        bg = '#f1f5f9' if is_header else ('#ffffff' if i % 2 == 1 else '#f8fafc')
        fw = '700' if is_header else '400'
        color = '#334155' if is_header else '#475569'
        bdr = 'border-bottom:2px solid #cbd5e1' if is_header else 'border-bottom:1px solid #f1f5f9'

        table_html += f'<tr style="background:{bg};{bdr}">'
        for cell in row:
            safe_cell = html.escape(cell)
            safe_cell = re.sub(
                r'&lt;(https?://[^&]+)&gt;',
                r'<a href="\1" target="_blank" style="color:#6366f1;text-decoration:none;font-weight:600;white-space:nowrap;">Open ↗</a>',
                safe_cell
            )
            safe_cell = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', safe_cell)
            align = 'right' if _has_arabic(cell) else 'left'

            table_html += f'<{tag} style="padding:11px 16px;color:{color};font-weight:{fw};text-align:{align};vertical-align:top;white-space:normal;word-break:break-word;">{safe_cell}</{tag}>'
        table_html += '</tr>'

    table_html += '</table></div>'
    return table_html


# ─── Styles ─────────────────────────────────────────────────────────
def _inject_styles():
    watermark_css = ""
    if LOGO_B64:
        watermark_css = f"""
        .chat-watermark {{
            position: fixed;
            top: 50%;
            left: calc(50% + 150px);
            transform: translate(-50%, -50%);
            width: 480px;
            height: 480px;
            opacity: 0.03;
            pointer-events: none;
            z-index: 0;
            background-image: url('data:image/png;base64,{LOGO_B64}');
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
            filter: blur(1px);
        }}
        @media (max-width: 768px) {{
            .chat-watermark {{
                left: 50%;
                width: 280px;
                height: 280px;
            }}
        }}
        """

    st.markdown(f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">

    <style>
        .stApp {{ background: #f1f5f9 !important; }}
        .main .block-container {{
            position: relative;
            z-index: 1;
        }}

        {watermark_css}

        ::-webkit-scrollbar {{ width: 5px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 999px; }}

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {{
            background: #f8fafc !important;
            border-left: 1px solid #e2e8f0 !important;
        }}
        [data-testid="stSidebar"] * {{ font-family: 'Cairo','Inter',sans-serif !important; }}

        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {{
            background: #6366f1 !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            padding: 12px 16px !important;
            transition: all 0.2s !important;
        }}
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {{
            background: #4f46e5 !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(99,102,241,0.3);
        }}

        .chat-item-btn {{
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 10px !important;
            padding: 10px 12px !important;
            font-size: 13px !important;
            font-weight: 400 !important;
            color: #64748b !important;
            text-align: left !important;
            transition: all 0.15s !important;
            width: 100%;
            margin-bottom: 2px !important;
            line-height: 1.4 !important;
        }}
        .chat-item-btn:hover {{
            background: rgba(99,102,241,0.06) !important;
            color: #334155 !important;
            border-color: rgba(99,102,241,0.1) !important;
        }}
        .chat-item-btn.active-chat {{
            background: rgba(99,102,241,0.1) !important;
            color: #4338ca !important;
            font-weight: 600 !important;
            border-color: rgba(99,102,241,0.2) !important;
        }}

        .chat-group-label {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #94a3b8;
            padding: 16px 12px 6px;
        }}

        /* ── Chat Input ── */
        .stChatInputContainer {{
            background: transparent !important;
            border-top: none !important;
            padding: 0 15% 24px 15% !important;
        }}
        .stChatInputContainer > div {{
            background: #ffffff !important;
            border-radius: 28px !important;
            border: 1.5px solid #e2e8f0 !important;
            box-shadow: 0 8px 30px rgba(0,0,0,0.06) !important;
            padding: 6px 6px 6px 4px !important;
            display: flex !important;
            align-items: center !important;
            transition: border-color 0.2s, box-shadow 0.2s !important;
        }}
        .stChatInputContainer > div:focus-within {{
            border-color: #a5b4fc !important;
            box-shadow: 0 8px 30px rgba(99,102,241,0.12) !important;
        }}
        .stChatInputContainer > div > div {{
            border: none !important;
            box-shadow: none !important;
        }}
        .stChatInputContainer textarea {{
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
            border-radius: 24px !important;
            padding: 12px 16px !important;
            font-size: 15px !important;
            font-family: 'Cairo','Inter',sans-serif !important;
            min-height: 24px !important;
            resize: none !important;
        }}
        .stChatInputContainer textarea:focus {{
            box-shadow: none !important;
            outline: none !important;
        }}
        .stChatInputContainer button[data-testid="stBaseButton-secondary"] {{
            background: #6366f1 !important;
            color: white !important;
            border-radius: 50% !important;
            width: 40px !important;
            height: 40px !important;
            padding: 0 !important;
            margin: 0 4px 0 8px !important;
            border: none !important;
            flex-shrink: 0 !important;
        }}
        .stChatInputContainer button[data-testid="stBaseButton-secondary"]:hover {{
            background: #4f46e5 !important;
            transform: scale(1.05);
        }}

        /* ── Message Bubbles ── */
        @keyframes msgFadeIn {{
            from {{ opacity: 0; transform: translateY(12px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}
        .msg-animate {{ animation: msgFadeIn 0.35s cubic-bezier(0.16,1,0.3,1) both; }}

        @keyframes typingBounce {{
            0%, 60%, 100% {{ transform: translateY(0); }}
            30% {{ transform: translateY(-6px); }}
        }}
        .typing-dot {{
            display: inline-block; width: 7px; height: 7px;
            border-radius: 50%; background: #6366f1; margin: 0 2px;
        }}
        .typing-dot:nth-child(1) {{ animation: typingBounce 1.2s 0s infinite; }}
        .typing-dot:nth-child(2) {{ animation: typingBounce 1.2s 0.15s infinite; }}
        .typing-dot:nth-child(3) {{ animation: typingBounce 1.2s 0.3s infinite; }}

        /* ── Quick Prompt Cards — clean, no overlap ── */
        .quick-prompts-section {{
            padding: 0 10% 32px;
            max-width: 800px;
            margin: 0 auto;
        }}
        .quick-prompts-section [data-testid="stHorizontalBlock"] {{
            gap: 14px !important;
        }}

        /* Target only the quick-prompt buttons (not sidebar, not input) */
        .quick-prompts-section button[data-testid="stBaseButton-secondary"] {{
            background: #ffffff !important;
            border: 1.5px solid #e8ecf4 !important;
            border-radius: 18px !important;
            padding: 22px 24px 20px !important;
            text-align: right !important;
            direction: rtl !important;
            font-size: 14.5px !important;
            color: #1e293b !important;
            font-weight: 500 !important;
            line-height: 1.75 !important;
            height: auto !important;
            min-height: 100px !important;
            white-space: normal !important;
            word-break: break-word !important;
            transition: all 0.3s cubic-bezier(0.16,1,0.3,1) !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04), 0 4px 16px rgba(0,0,0,0.02) !important;
            position: relative !important;
            overflow: hidden !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: flex-start !important;
            gap: 0 !important;
        }}
        .quick-prompts-section button[data-testid="stBaseButton-secondary"]:hover {{
            border-color: #a5b4fc !important;
            transform: translateY(-3px) !important;
            box-shadow: 0 12px 32px rgba(99,102,241,0.12), 0 2px 8px rgba(99,102,241,0.06) !important;
            background: #ffffff !important;
            color: #0f172a !important;
        }}
        .quick-prompts-section button[data-testid="stBaseButton-secondary"]:active {{
            transform: translateY(-1px) !important;
        }}

        /* Colored top accent strip per card */
        .quick-prompts-section button[data-testid="stBaseButton-secondary"]::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            border-radius: 18px 18px 0 0;
            opacity: 0;
            transition: opacity 0.3s;
        }}
        .quick-prompts-section button[data-testid="stBaseButton-secondary"]:hover::before {{
            opacity: 1;
        }}

        /* Per-card accent colors via nth-child */
        .quick-prompts-section [data-testid="stHorizontalBlock"] > div:nth-child(1) button::before {{
            background: linear-gradient(90deg, #8b5cf6, #a78bfa);
        }}
        .quick-prompts-section [data-testid="stHorizontalBlock"] > div:nth-child(2) button::before {{
            background: linear-gradient(90deg, #22c55e, #4ade80);
        }}
        .quick-prompts-section [data-testid="stHorizontalBlock"] > div:nth-child(3) button::before {{
            background: linear-gradient(90deg, #f59e0b, #fbbf24);
        }}
        .quick-prompts-section [data-testid="stHorizontalBlock"] > div:nth-child(4) button::before {{
            background: linear-gradient(90deg, #6366f1, #818cf8);
        }}

        .empty-sidebar-hint {{
            text-align: center; padding: 24px 12px; color: #cbd5e1; font-size: 12px;
        }}
    </style>
    """, unsafe_allow_html=True)


# ─── Render message bubble ──────────────────────────────────────────
def _render_message(role: str, content: str, animate: bool = False):
    is_user = role == "user"
    is_arabic = is_arabic_text(content)

    if is_user:
        safe_content = html.escape(content).replace("\n", "<br>")
    else:
        safe_content = _render_content_with_tables(content)

    anim_class = "msg-animate" if animate else ""
    direction = "rtl" if is_arabic else "ltr"
    text_align = "right" if is_arabic else "left"

    if is_user:
        html_block = f"""
        <div class="{anim_class}" style="display:flex;justify-content:flex-end;margin:6px 0;padding:0 8px;font-family:'Cairo','Inter',sans-serif;">
            <div style="display:flex;gap:10px;align-items:flex-end;flex-direction:row-reverse;max-width:70%;">
                <div style="width:38px;height:38px;border-radius:14px;background:linear-gradient(135deg,#6366f1,#4f46e5);display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:0 4px 12px rgba(99,102,241,0.3);">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                </div>
                <div style="background:linear-gradient(135deg,#6366f1 0%,#4f46e5 100%);color:#fff;padding:14px 20px;border-radius:20px 20px 4px 20px;box-shadow:0 4px 16px rgba(99,102,241,0.25);direction:{direction};text-align:{text_align};line-height:1.75;font-size:15px;font-weight:500;">
                    {safe_content}
                </div>
            </div>
        </div>"""
    else:
        if LOGO_B64:
            avatar = f'<img src="data:image/png;base64,{LOGO_B64}" style="width:28px;height:28px;object-fit:contain;">'
        else:
            avatar = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2"><path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"/><path d="M16 14H8a4 4 0 0 0-4 4v2h16v-2a4 4 0 0 0-4-4z"/></svg>'

        html_block = f"""
        <div class="{anim_class}" style="display:flex;justify-content:flex-start;margin:6px 0;padding:0 8px;font-family:'Cairo','Inter',sans-serif;">
            <div style="display:flex;gap:10px;align-items:flex-start;max-width:75%;">
                <div style="width:38px;height:38px;border-radius:14px;background:#fff;display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:0 2px 8px rgba(0,0,0,0.06),0 0 0 1.5px #e0e7ff;margin-top:2px;">
                    {avatar}
                </div>
                <div style="background:#fff;color:#1e293b;padding:16px 22px;border-radius:4px 20px 20px 20px;box-shadow:0 2px 12px rgba(0,0,0,0.05),0 0 0 1px rgba(0,0,0,0.04);direction:{direction};text-align:{text_align};line-height:1.85;font-size:15px;position:relative;">
                    {safe_content}
                    <div style="position:absolute;bottom:6px;left:14px;display:flex;gap:3px;opacity:0.25;">
                        <span style="width:4px;height:4px;border-radius:50%;background:#6366f1;"></span>
                        <span style="width:4px;height:4px;border-radius:50%;background:#818cf8;"></span>
                        <span style="width:4px;height:4px;border-radius:50%;background:#a5b4fc;"></span>
                    </div>
                </div>
            </div>
        </div>"""
    st.markdown(html_block, unsafe_allow_html=True)


def _render_typing():
    if LOGO_B64:
        avatar = f'<img src="data:image/png;base64,{LOGO_B64}" style="width:28px;height:28px;object-fit:contain;">'
    else:
        avatar = '🤖'
    st.markdown(f"""
    <div style="display:flex;justify-content:flex-start;margin:6px 0;padding:0 8px;font-family:'Cairo','Inter',sans-serif;">
        <div style="display:flex;gap:10px;align-items:flex-start;">
            <div style="width:38px;height:38px;border-radius:14px;background:#fff;display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:0 2px 8px rgba(0,0,0,0.06),0 0 0 1.5px #e0e7ff;">
                {avatar}
            </div>
            <div style="background:#fff;padding:18px 24px;border-radius:4px 20px 20px 20px;box-shadow:0 2px 12px rgba(0,0,0,0.05),0 0 0 1px rgba(0,0,0,0.04);display:flex;align-items:center;gap:2px;">
                <span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)


# ─── Sidebar ────────────────────────────────────────────────────────
def _render_sidebar(username: str):
    active_chat_id = st.session_state.get("active_chat_id")
    edit_mode = st.session_state.get("edit_mode", False)
    chats = list_user_chats(username)
    grouped = group_chats_by_date(chats)

    with st.sidebar:
        if st.button(
            "+  New Chat",
            key="new_chat_btn",
            use_container_width=True,
            type="secondary",
        ):
            new_id = create_chat(username)
            st.session_state.active_chat_id = new_id
            st.session_state.messages = []
            st.session_state.edit_mode = False
            st.rerun()

        st.divider()

        top_row = st.columns([1, 1])
        with top_row[0]:
            edit_label = "✅  Done" if edit_mode else "✏️  Edit"
            btn_type = "primary" if edit_mode else "secondary"
            if st.button(edit_label, key="edit_toggle", use_container_width=True, type=btn_type):
                st.session_state.edit_mode = not edit_mode
                st.rerun()
        with top_row[1]:
            st.markdown(
                f'<div style="text-align:right;font-size:11px;color:#94a3b8;padding-top:8px;">{len(chats)} chat{"s" if len(chats)!=1 else ""}</div>',
                unsafe_allow_html=True
            )

        if not grouped:
            st.markdown(
                '<div class="empty-sidebar-hint">No chats yet.<br>Click "New Chat" to start.</div>',
                unsafe_allow_html=True
            )
        else:
            for group_label, group_chats in grouped.items():
                st.markdown(f'<div class="chat-group-label">{group_label}</div>', unsafe_allow_html=True)

                for chat in group_chats:
                    cid = chat["chat_id"]
                    title = chat.get("title", "Untitled")
                    is_active = (cid == active_chat_id)

                    if edit_mode:
                        col_t, col_d = st.columns([6, 1])
                        with col_t:
                            if st.button(
                                f"{'● ' if is_active else '○ '}{title}",
                                key=f"sel_{cid}",
                                use_container_width=True,
                            ):
                                st.session_state.active_chat_id = cid
                                st.session_state.messages = load_history(cid)
                                st.session_state.edit_mode = False
                                st.rerun()
                        with col_d:
                            if st.button("✕", key=f"del_{cid}"):
                                delete_chat(cid)
                                if st.session_state.get("active_chat_id") == cid:
                                    remaining = list_user_chats(username)
                                    if remaining:
                                        st.session_state.active_chat_id = remaining[0]["chat_id"]
                                        st.session_state.messages = load_history(remaining[0]["chat_id"])
                                    else:
                                        st.session_state.active_chat_id = None
                                        st.session_state.messages = []
                                st.rerun()
                    else:
                        if st.button(
                            f"{'● ' if is_active else '○ '}{title}",
                            key=f"sel_{cid}",
                            use_container_width=True,
                        ):
                            st.session_state.active_chat_id = cid
                            st.session_state.messages = load_history(cid)
                            st.rerun()

        st.markdown("""
        <div style="margin-top:24px;padding:16px;background:linear-gradient(135deg,#eef2ff,#e0e7ff);border-radius:14px;border:1px solid #c7d2fe;">
            <div style="font-size:12px;font-weight:700;color:#4338ca;margin-bottom:4px;">💡 Tip</div>
            <div style="font-size:11px;color:#6366f1;line-height:1.6;">
                Click "✏️ Edit" to delete chats.<br>Each chat has its own memory.
            </div>
        </div>
        """, unsafe_allow_html=True)


# ─── Top Bar ────────────────────────────────────────────────────────
def _render_top_bar(username: str):
    if LOGO_B64:
        logo_html = f'<img src="data:image/png;base64,{LOGO_B64}" style="height:40px;object-fit:contain;">'
    else:
        logo_html = '<span style="font-size:26px;font-weight:800;color:#6366f1;letter-spacing:-1px;">Kayfa</span>'

    active_id = st.session_state.get("active_chat_id")
    chat_title = "New Chat"
    if active_id:
        chats = list_user_chats(username)
        for c in chats:
            if c["chat_id"] == active_id:
                chat_title = c.get("title", "New Chat")
                break

    st.markdown(f"""
    <div style="
        background:#fff;border-bottom:1px solid #e2e8f0;
        padding:14px 32px;display:flex;align-items:center;justify-content:space-between;
        position:sticky;top:0;z-index:100;backdrop-filter:blur(12px);
        background:rgba(255,255,255,0.92);
    ">
        <div style="display:flex;align-items:center;gap:14px;">
            {logo_html}
            <div style="width:1px;height:26px;background:#e2e8f0;"></div>
            <div>
                <div style="font-size:14px;font-weight:700;color:#0f172a;font-family:'Inter','Cairo',sans-serif;letter-spacing:-0.3px;">
                    {html.escape(chat_title)}
                </div>
                <div style="display:flex;align-items:center;gap:6px;margin-top:1px;">
                    <span style="width:7px;height:7px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 3px rgba(34,197,94,0.15);display:inline-block;"></span>
                    <span style="font-size:11px;color:#94a3b8;font-family:'Inter',sans-serif;">Online</span>
                </div>
            </div>
        </div>
        <div style="font-size:13px;color:#94a3b8;font-family:'Cairo','Inter',sans-serif;">
            Welcome, <b style="color:#6366f1;">{html.escape(username)}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Empty State ────────────────────────────────────────────────────
def _render_empty_state():
    st.markdown("""
    <div style="text-align:center;padding:48px 20px 36px;">
        <div style="width:76px;height:76px;border-radius:22px;background:linear-gradient(135deg,#eef2ff,#e0e7ff);display:inline-flex;align-items:center;justify-content:center;margin-bottom:22px;box-shadow:0 8px 28px rgba(99,102,241,0.12);">
            <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        </div>
        <h2 style="margin:0 0 8px;font-size:24px;font-weight:800;color:#0f172a;font-family:'Cairo','Inter',sans-serif;">إزاي أقدر أساعدك النهارده؟</h2>
        <p style="margin:0;font-size:14px;color:#94a3b8;font-family:'Cairo','Inter',sans-serif;">اختار سؤال من الأسفل أو اكتب سؤالك</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Clean card buttons: wrap in a scoped div, then just use st.button ──
    st.markdown('<div class="quick-prompts-section">', unsafe_allow_html=True)

    # Row 1: cards 0 & 1
    c1, c2 = st.columns(2)
    with c1:
        if st.button(f"{QUICK_PROMPTS[0][0]}  {QUICK_PROMPTS[0][1]}", key="quick_0", use_container_width=True):
            st.session_state.pending_prompt = QUICK_PROMPTS[0][1]
            st.rerun()
    with c2:
        if st.button(f"{QUICK_PROMPTS[1][0]}  {QUICK_PROMPTS[1][1]}", key="quick_1", use_container_width=True):
            st.session_state.pending_prompt = QUICK_PROMPTS[1][1]
            st.rerun()

    # Row 2: cards 2 & 3
    c3, c4 = st.columns(2)
    with c3:
        if st.button(f"{QUICK_PROMPTS[2][0]}  {QUICK_PROMPTS[2][1]}", key="quick_2", use_container_width=True):
            st.session_state.pending_prompt = QUICK_PROMPTS[2][1]
            st.rerun()
    with c4:
        if st.button(f"{QUICK_PROMPTS[3][0]}  {QUICK_PROMPTS[3][1]}", key="quick_3", use_container_width=True):
            st.session_state.pending_prompt = QUICK_PROMPTS[3][1]
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ─── Main Page ──────────────────────────────────────────────────────
def show():
    _inject_styles()

    username = st.session_state.username
    active_chat_id = st.session_state.get("active_chat_id")

    if "messages" not in st.session_state:
        if active_chat_id:
            st.session_state.messages = load_history(active_chat_id)
        else:
            st.session_state.messages = []
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False

    if not active_chat_id:
        chats = list_user_chats(username)
        if chats:
            st.session_state.active_chat_id = chats[0]["chat_id"]
            st.session_state.messages = load_history(chats[0]["chat_id"])
            active_chat_id = chats[0]["chat_id"]
            st.rerun()

    _render_sidebar(username)
    _render_top_bar(username)

    # ── Watermark ──
    if LOGO_B64:
        st.markdown('<div class="chat-watermark"></div>', unsafe_allow_html=True)

    chat_container = st.container()
    with chat_container:
        if not st.session_state.messages:
            _render_empty_state()
        else:
            for idx, msg in enumerate(st.session_state.messages):
                is_last = (idx == len(st.session_state.messages) - 1)
                _render_message(msg["role"], msg["content"], animate=is_last)

    if st.session_state.get("pending_prompt"):
        prompt = st.session_state.pop("pending_prompt")
        current_chat_id = st.session_state.get("active_chat_id")

        if not current_chat_id:
            current_chat_id = create_chat(username, first_message=prompt)
            st.session_state.active_chat_id = current_chat_id
            st.session_state.messages = []

        set_chat_title_from_message(current_chat_id, prompt)

        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            _render_message("user", prompt, animate=True)
            _render_typing()

        try:
            reply = asyncio.run(
                handle_user_message(
                    prompt,
                    chat_id=current_chat_id,
                    user_id=st.session_state.username,
                )
            )
        except Exception as e:
            reply = "عذراً، حدث خطأ تقني. حاول تاني."
            print(f"Agent error: {e}")

        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

    user_text = st.chat_input(
        "اسأل عن الكورسات، الدبلومات، الأسعار…",
        key="chat_input_main"
    )
    if user_text:
        st.session_state.pending_prompt = user_text
        st.rerun()