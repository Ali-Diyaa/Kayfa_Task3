"""
PAGE 1 — Chat with the Kayfa AI Sales Agent.
Modern light-mode chat interface.
"""
import asyncio
import html
import base64
from pathlib import Path
import streamlit as st

from core.agent import handle_user_message
from core.chat_memory import append_messages, build_history_string, clear_history, load_history
from core.intent import is_arabic_text

# --- Load Kayfa logo as base64 (fixes the path showing) ---
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "kayfa_small.png"
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

def _render_message(role: str, content: str):
    is_user = role == "user"
    is_arabic = is_arabic_text(content)
    safe_content = html.escape(content).replace("\n", "<br>")

    if is_user:
        bg = "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)"
        color = "white"
        align = "flex-end"
        radius = "20px 20px 4px 20px"
        shadow = "0 4px 12px rgba(37,99,235,0.25)"
        avatar_html = "🧑"
        avatar_bg = "rgba(255,255,255,0.2)"
        avatar_border = "rgba(255,255,255,0.3)"
    else:
        bg = "#ffffff"
        color = "#0f172a"
        align = "flex-start"
        radius = "20px 20px 20px 4px"
        shadow = "0 2px 8px rgba(0,0,0,0.06)"
        # USE BASE64 IMAGE, NOT PATH
        if LOGO_B64:
            avatar_html = f'<img src="data:image/png;base64,{LOGO_B64}" style="width:24px;height:24px;object-fit:contain;">'
        else:
            avatar_html = "🤖"
        avatar_bg = "#e0e7ff"
        avatar_border = "#c7d2fe"

    direction = "rtl" if is_arabic else "ltr"
    text_align = "right" if is_arabic else "left"
    flex_dir = "row-reverse" if is_user else "row"
    border = "none" if is_user else "1px solid #e2e8f0"

    html_block = f"""
    <div style="display:flex; justify-content:{align}; margin:16px 0; font-family:'Cairo',system-ui,-apple-system,sans-serif;">
        <div style="display:flex; gap:12px; max-width:75%; align-items:flex-end; flex-direction:{flex_dir};">
            <div style="width:36px; height:36px; border-radius:50%; background:{avatar_bg}; display:flex; align-items:center; justify-content:center; flex-shrink:0; border:2px solid {avatar_border}; overflow:hidden;">
                {avatar_html}
            </div>
            <div style="background:{bg}; color:{color}; padding:14px 18px; border-radius:{radius}; box-shadow:{shadow}; direction:{direction}; text-align:{text_align}; line-height:1.6; font-size:15px; border:{border};">
                {safe_content}
            </div>
        </div>
    </div>
    """
    st.markdown(html_block, unsafe_allow_html=True)

def _run_turn(user_text: str):
    username = st.session_state.username
    history_str = build_history_string(st.session_state.messages, max_turns=6)
    st.session_state.messages.append({"role": "user", "content": user_text})
    append_messages(username, [{"role": "user", "content": user_text}])
    with st.spinner(""):
        reply = asyncio.run(handle_user_message(user_text, history_str))
    st.session_state.messages.append({"role": "assistant", "content": reply})
    append_messages(username, [{"role": "assistant", "content": reply}])

def show():
    username = st.session_state.username
    if "messages" not in st.session_state:
        st.session_state.messages = load_history(username)

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#f8fafc 0%,#ffffff 100%); border:1px solid #e2e8f0; border-radius:24px; padding:28px; margin-bottom:24px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
        <div style="display:flex; align-items:center; gap:16px;">
            <div style="width:56px; height:56px; border-radius:16px; background:linear-gradient(135deg,#2563eb,#1d4ed8); display:flex; align-items:center; justify-content:center; box-shadow:0 8px 16px rgba(37,99,235,0.25); font-size:28px;">💬</div>
            <div>
                <h1 style="margin:0; font-size:28px; font-weight:800; color:#0f172a; letter-spacing:-0.5px;">Kayfa AI Sales Agent</h1>
                <p style="margin:4px 0 0; color:#64748b; font-size:15px;">Welcome <b style="color:#2563eb;">{username}</b> — ask about courses, diplomas, prices, or register your interest.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.divider()
        if st.button("🗑️ New Chat", use_container_width=True):
            clear_history(username)
            st.session_state.messages = []
            st.rerun()

    if not st.session_state.messages:
        st.markdown("<h3 style='color:#0f172a; font-weight:700; margin:0 0 16px; font-family:Cairo,sans-serif;'>Try asking about:</h3>", unsafe_allow_html=True)
        cols = st.columns(2)
        for i, (icon, prompt) in enumerate(QUICK_PROMPTS):
            with cols[i % 2]:
                if st.button(f"{icon} {prompt}", key=f"q_{i}", use_container_width=True):
                    st.session_state.pending_prompt = prompt
                    st.rerun()
        st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

    for msg in st.session_state.messages:
        _render_message(msg["role"], msg["content"])

    if st.session_state.get("pending_prompt"):
        prompt = st.session_state.pop("pending_prompt")
        _render_message("user", prompt)
        _run_turn(prompt)
        st.rerun()

    user_text = st.chat_input("Type your question here...")
    if user_text:
        st.session_state.pending_prompt = user_text
        st.rerun()