import streamlit as st
from core.auth import login_user, register_user
from core.db import ensure_indexes
from views import page_chat, page_crm

st.set_page_config(
    page_title="Kayfa AI Sales Agent",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- FIX WHITE-ON-WHITE ---
def inject_global_css():
    st.markdown("""
    <style>
    /* FORCE LIGHT MODE - no dark ever */
    :root { color-scheme: light only!important; }
    html, body, [data-testid="stAppViewContainer"] {
        background: #ffffff!important;
        color: #0f172a!important;
    }

    /* Sidebar - always light */
    [data-testid="stSidebar"] {
        background: #f8fafc!important;
        border-right: 1px solid #e2e8f0!important;
    }
    [data-testid="stSidebar"] * { color: #0f172a!important; }

    /* Main content */
   .main.block-container { padding-top: 2rem; max-width: 900px; }

    /* Chat bubbles - modern */
    [data-testid="stChatMessage"] {
        background: transparent!important;
        padding: 0.5rem 0!important;
    }
    /* User bubble */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) > div > div {
        background: #2563eb!important;
        color: white!important;
        border-radius: 18px 18px 4px 18px!important;
        padding: 12px 16px!important;
        margin-left: auto!important;
        max-width: 75%!important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05)!important;
    }
    /* Assistant bubble */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) > div > div,
    [data-testid="stChatMessage"]:has(img) > div > div {
        background: #f1f5f9!important;
        color: #0f172a!important;
        border-radius: 18px 18px 18px 4px!important;
        padding: 12px 16px!important;
        max-width: 75%!important;
        border: 1px solid #e2e8f0!important;
    }

    /* Chat input - force white */
    [data-testid="stChatInput"] {
        background: white!important;
        border-top: 1px solid #e2e8f0!important;
    }
    [data-testid="stChatInput"] textarea {
        background: white!important;
        color: #0f172a!important;
        border: 1px solid #cbd5e1!important;
    }

    /* RTL support */
   .chat-rtl { direction: rtl; text-align: right; font-family: 'Cairo', sans-serif; }
   .chat-ltr { direction: ltr; text-align: left; }

    /* Hide deploy button */
    [data-testid="stDeployButton"] { display: none!important; }
    </style>
    """, unsafe_allow_html=True)
inject_global_css()

try:
    ensure_indexes()
except Exception as e:
    st.error(f"Failed to connect to database.\n\n{e}")
    st.stop()

def _login_screen():
    col_logo, col_form, col_pad = st.columns([1, 2, 1])
    with col_form:
        # --- LOGO ON LOGIN ---
        try:
            st.image("assets/kayfa_logo.png", width=180)
        except:
            st.markdown("<h1 style='text-align:center'>🏢 Kayfa</h1>", unsafe_allow_html=True)
        
        st.markdown(
            """<div style="text-align:center; margin-bottom:20px;">
                <p>Sales Agent Console — Please login to continue</p>
            </div>""",
            unsafe_allow_html=True,
        )

        tab_login, tab_register = st.tabs(["Login", "Create Account"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                # --- MANUAL ADMIN OVERRIDE (for testing) ---
                if username.strip().lower() == "admin" and password == "admin123":
                    st.session_state.authenticated = True
                    st.session_state.username = "admin"
                    st.session_state.role = "admin"
                    st.rerun()

                # --- Normal MongoDB login ---
                user, err = login_user(username, password)
                if err:
                    st.error(err)
                else:
                    st.session_state.authenticated = True
                    st.session_state.username = user["username"]
                    st.session_state.role = user.get("role", "user")
                    st.rerun()

        with tab_register:
            with st.form("register_form"):
                new_username = st.text_input("Username", key="reg_user")
                new_password = st.text_input("Password", type="password", key="reg_pass")
                confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
                reg_submitted = st.form_submit_button("Create Account", use_container_width=True)
            if reg_submitted:
                ok, msg = register_user(new_username, new_password, confirm_password)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

def _sidebar_branding():
    with st.sidebar:
        try:
            st.image("assets/kayfa_logo.png", use_container_width=True)
        except:
            st.markdown("### 🏢 Kayfa")
        st.caption("Sales Agent Console")
        st.divider()
        st.markdown(f"👤 **{st.session_state.username}**  \n`{st.session_state.role}`")
        if st.button("🚪 Logout", use_container_width=True):
            for key in ("authenticated", "username", "role", "messages"):
                st.session_state.pop(key, None)
            st.rerun()

def main():
    if not st.session_state.get("authenticated"):
        _login_screen()
        return

    _sidebar_branding()

    if st.session_state.role == "admin":
        pages = [
            st.Page(page_chat.show, title="Chat", icon="💬", url_path="chat"),
            st.Page(page_crm.show, title="CRM Leads", icon="🎯", url_path="crm"),
        ]
    else:
        pages = [st.Page(page_chat.show, title="Chat", icon="💬", url_path="chat")]

    pg = st.navigation(pages, position="sidebar")
    pg.run()

if __name__ == "__main__":
    main()