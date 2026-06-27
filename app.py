import streamlit as st
from core.auth import login_user, register_user
from core.db import ensure_indexes
from views import page_chat, page_crm, page_cost_tracking, page_agent_steps, page_comparison

st.set_page_config(
    page_title="Kayfa AI Sales Agent",
    page_icon="💬",
    layout="wide",
)

# ─── Global Styles ──────────────────────────────────────────────────
def inject_global_css(is_authenticated: bool):
    if not is_authenticated:
        st.markdown("""
        <style>
            .stApp { background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%) !important; }

            .main .block-container {
                max-width: 450px !important;
                margin-left: auto !important;
                margin-right: auto !important;
                padding-top: 20px !important;
                padding-bottom: 5vh !important;
            }

            .top-logo-container {
                text-align: center;
                margin-bottom: 30px;
                animation: fadeInDown 0.8s ease-out;
            }
            .top-logo-container img {
                width: 140px;
                filter: drop-shadow(0 10px 15px rgba(99, 102, 241, 0.15));
                transition: transform 0.3s ease;
            }
            .top-logo-container img:hover { transform: scale(1.05); }

            @keyframes fadeInDown {
                from { opacity: 0; transform: translateY(-20px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .login-card {
                background: #ffffff;
                border-radius: 24px;
                padding: 40px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.8);
                animation: fadeInUp 0.8s ease-out 0.2s both;
            }
            @keyframes fadeInUp {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .login-card [data-testid="stForm"] {
                border: none; background: transparent;
                padding: 0; box-shadow: none;
            }
            .login-card [data-testid="stVerticalBlock"] > div:has([data-testid="stTextInput"]) {
                margin-bottom: 20px;
            }
            .login-card label p {
                font-size: 13px; font-weight: 600; color: #475569;
                margin-bottom: 6px; font-family: 'Inter', sans-serif;
            }
            .login-card input {
                border: 1.5px solid #e2e8f0 !important;
                border-radius: 12px !important;
                padding: 12px 16px !important;
                background: #f8fafc !important;
                color: #0f172a !important;
                font-size: 15px !important;
                transition: all 0.2s ease !important;
            }
            .login-card input:focus {
                border-color: #6366f1 !important;
                box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1) !important;
                background: #ffffff !important;
            }
            .login-card [data-testid="stFormSubmitButton"] button {
                width: 100%; background: #6366f1; color: white; border: none;
                border-radius: 12px; padding: 14px; font-weight: 700; font-size: 15px;
                margin-top: 8px; transition: all 0.2s ease;
                box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
            }
            .login-card [data-testid="stFormSubmitButton"] button:hover {
                background: #4f46e5; transform: translateY(-1px);
                box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35);
            }
            .login-card [data-testid="stAlert"] {
                padding: 12px 16px; border-radius: 12px;
                border: none; font-size: 14px; margin-bottom: 16px;
            }

            .login-title {
                text-align: center; font-size: 24px; font-weight: 800;
                color: #0f172a; margin: 0 0 8px 0; font-family: 'Inter', sans-serif;
            }
            .login-subtitle {
                text-align: center; font-size: 14px; color: #94a3b8;
                margin: 0 0 32px 0; font-family: 'Inter', sans-serif;
            }

            div[data-testid="stVerticalBlock"]:has(button:contains("Login")) > div > div {
                background: #f1f5f9 !important; border-radius: 12px !important;
                padding: 4px !important; display: flex !important; gap: 4px !important;
                margin-bottom: 30px !important; border: none !important;
            }
            div[data-testid="stVerticalBlock"]:has(button:contains("Login")) button {
                border-radius: 10px !important; border: none !important;
                font-weight: 600 !important; transition: all 0.2s ease !important;
                background: transparent !important; color: #64748b !important;
            }
            div[data-testid="stVerticalBlock"]:has(button:contains("Login")) div[data-testid="stVerticalBlockBorderWrapper"]:first-child button {
                background: """ + ('#ffffff' if st.session_state.get("auth_tab") == "login" else 'transparent') + """ !important;
                color: """ + ('#4f46e5' if st.session_state.get("auth_tab") == "login" else '#64748b') + """ !important;
                box-shadow: """ + ('0 2px 8px rgba(0,0,0,0.05)' if st.session_state.get("auth_tab") == "login" else 'none') + """ !important;
            }
            div[data-testid="stVerticalBlock"]:has(button:contains("Create")) div[data-testid="stVerticalBlockBorderWrapper"]:last-child button {
                background: """ + ('#ffffff' if st.session_state.get("auth_tab") == "register" else 'transparent') + """ !important;
                color: """ + ('#4f46e5' if st.session_state.get("auth_tab") == "register" else '#64748b') + """ !important;
                box-shadow: """ + ('0 2px 8px rgba(0,0,0,0.05)' if st.session_state.get("auth_tab") == "register" else 'none') + """ !important;
            }

            .login-footer {
                text-align: center; margin-top: 24px; padding-top: 20px;
                border-top: 1px solid #f1f5f9; font-size: 12px;
                color: #cbd5e1; font-family: 'Inter', sans-serif;
            }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        :root { color-scheme: light only!important; }
        html, body, [data-testid="stAppViewContainer"] {
            background: #f1f5f9!important; color: #0f172a!important;
        }
        [data-testid="stSidebar"] {
            background: #f8fafc!important; border-right: 1px solid #e2e8f0!important;
        }
        [data-testid="stSidebar"] * { color: #0f172a!important; }
        .main.block-container { padding-top: 2rem; max-width: 1200px; }
        [data-testid="stChatMessage"] { background: transparent!important; padding: 0.5rem 0!important; }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) > div > div {
            background: #2563eb!important; color: white!important; border-radius: 18px 18px 4px 18px!important;
            padding: 12px 16px!important; margin-left: auto!important; max-width: 75%!important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) > div > div,
        [data-testid="stChatMessage"]:has(img) > div > div {
            background: #f1f5f9!important; color: #0f172a!important; border-radius: 18px 18px 18px 4px!important;
            padding: 12px 16px!important; max-width: 75%!important; border: 1px solid #e2e8f0!important;
        }
        [data-testid="stDeployButton"] { display: none!important; }
        </style>
        """, unsafe_allow_html=True)


# ─── Login Screen ───────────────────────────────────────────────────
def _login_screen():
    if "auth_tab" not in st.session_state:
        st.session_state.auth_tab = "login"

    with st.container():
        try:
            st.image("assets/kayfa_logo.png", width=140)
        except:
            st.markdown("<h1 style='text-align:center;font-size:4rem;margin-bottom:0;'>🏢</h1>", unsafe_allow_html=True)

        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("""
            <h1 class="login-title">Welcome Back</h1>
            <p class="login-subtitle">Sign in to your Kayfa AI Console</p>
        """, unsafe_allow_html=True)

        tab_cols = st.columns([1, 1], gap="small")
        with tab_cols[0]:
            if st.button("Login", key="tab_login", use_container_width=True):
                st.session_state.auth_tab = "login"
                st.rerun()
        with tab_cols[1]:
            if st.button("Create Account", key="tab_register", use_container_width=True):
                st.session_state.auth_tab = "register"
                st.rerun()

        if st.session_state.auth_tab == "login":
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Sign In", use_container_width=True)
            if submitted:
                if username.strip().lower() == "admin" and password == "admin123":
                    st.session_state.authenticated = True
                    st.session_state.username = "admin"
                    st.session_state.role = "admin"
                    st.rerun()
                user, err = login_user(username, password)
                if err:
                    st.error(err)
                else:
                    st.session_state.authenticated = True
                    st.session_state.username = user["username"]
                    st.session_state.role = user.get("role", "user")
                    st.rerun()
        else:
            with st.form("register_form", clear_on_submit=True):
                new_username = st.text_input("Username", placeholder="Choose a username", key="reg_user")
                new_password = st.text_input("Password", type="password", placeholder="Create a password", key="reg_pass")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password", key="reg_confirm")
                reg_submitted = st.form_submit_button("Create Account", use_container_width=True)
            if reg_submitted:
                ok, msg = register_user(new_username, new_password, confirm_password)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

        st.markdown('<div class="login-footer">© 2024 Kayfa Digital Solutions. All rights reserved.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ─── Main ───────────────────────────────────────────────────────────
def main():
    is_auth = st.session_state.get("authenticated", False)
    inject_global_css(is_authenticated=is_auth)

    try:
        ensure_indexes()
    except Exception as e:
        st.error(f"Failed to connect to database.\n\n{e}")
        st.stop()

    if not is_auth:
        _login_screen()
        return

    is_admin = st.session_state.role == "admin"

    # ── 1. Initialize current page if not set ──
    if "current_page" not in st.session_state:
        # Admins land on CRM, regular users land on Chat
        st.session_state.current_page = "crm" if is_admin else "chat"

    # ── 2. Build Custom Sidebar (Branding + Navigation) ──
    with st.sidebar:
        try:
            st.image("assets/kayfa_logo.png", use_container_width=True)
        except:
            st.markdown("### 🏢 Kayfa")
        st.caption("Sales Agent Console")
        st.divider()

        # Navigation — Chat is only for non-admin users
        nav_items = [
            ("💬 Chat", "chat", False, not is_admin),   # hidden for admin
            ("🎯 CRM Leads", "crm", True, True),
            ("📊 Cost Analytics", "cost_tracking", True, True),
            ("🔍 Agent Traces", "agent_steps", True, True),
            ("⚡ Benchmark", "comparison", True, True),
        ]

        for label, page_key, admin_only, visible in nav_items:
            if not visible:
                continue
            if admin_only and not is_admin:
                continue
            is_active = st.session_state.current_page == page_key
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, use_container_width=True, type=btn_type, key=f"nav_{page_key}"):
                st.session_state.current_page = page_key
                st.rerun()

        st.divider()
        st.markdown(f"👤 **{st.session_state.username}**  \n`{st.session_state.role}`")
        if st.button("🚪 Logout", use_container_width=True):
            for key in [
                "authenticated", "username", "role", "messages",
                "active_chat_id", "edit_mode", "pending_prompt",
                "auth_tab", "current_page", "bench_running", "bench_errors"
            ]:
                st.session_state.pop(key, None)
            st.rerun()

    # ── 3. Route to the active page ──
    page_map = {
        "chat": page_chat,
        "crm": page_crm,
        "cost_tracking": page_cost_tracking,
        "agent_steps": page_agent_steps,
        "comparison": page_comparison,
    }

    target_page = st.session_state.current_page

    # Safety: if admin somehow has "chat" as current_page, redirect to CRM
    if is_admin and target_page == "chat":
        st.session_state.current_page = "crm"
        st.rerun()

    # CRM and analytics pages are admin-only
    admin_pages = {"crm", "cost_tracking", "agent_steps", "comparison"}
    if target_page in admin_pages and not is_admin:
        st.error("This page is available for admins only.")
        return

    page_module = page_map.get(target_page, page_chat)
    page_module.show()


if __name__ == "__main__":
    main()