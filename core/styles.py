"""
Kayfa brand CSS — same palette as the attrition dashboard (app.py) so
every Kayfa-built Streamlit tool looks like one family of products.
"""
import streamlit as st

KAYFA_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

:root {
    --blue-900: #0A2463; --blue-700: #1447A6; --blue-500: #2563EB;
    --blue-400: #3B82F6; --blue-100: #DBEAFE; --blue-50: #EFF6FF;
    --accent: #F59E0B; --white: #FFFFFF; --gray-50: #F8FAFC;
    --gray-100: #F1F5F9; --gray-200: #E2E8F0; --gray-600: #475569;
    --red-500: #EF4444; --green-500:#22C55E;
}

html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: var(--white);
    color: #1E293B;
    font-family: 'DM Sans', sans-serif;
}

[data-testid="stSidebar"] { background: linear-gradient(180deg, var(--blue-900) 0%, var(--blue-700) 100%) !important; border-right: none !important; }
[data-testid="stSidebar"] * { color: var(--white) !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.2) !important; }

.main.block-container { padding: 1.6rem 2.2rem 3rem; max-width: 1100px; background: var(--white); }

.page-header { background: linear-gradient(135deg, var(--blue-900) 0%, var(--blue-500) 100%); border-radius: 16px; padding: 1.8rem 2.2rem; margin-bottom: 1.6rem; color: white; position: relative; overflow: hidden; }
.page-header::after { content: ''; position: absolute; top: -60px; right: -60px; width: 220px; height: 220px; background: rgba(255,255,255,.06); border-radius: 50%; }
.page-header h1 { font-family:'Plus Jakarta Sans',sans-serif; font-size:1.7rem; font-weight:800; margin:0; }
.page-header p { font-size:.92rem; opacity:.88; margin:.3rem 0 0; }

.section-card { background: var(--white); border: 1px solid var(--gray-200); border-radius: 14px; padding: 1.4rem 1.6rem; box-shadow: 0 1px 6px rgba(0,0,0,.05); margin-bottom: 1.2rem; }
.section-title { font-family:'Plus Jakarta Sans',sans-serif; font-size:1.0rem; font-weight:700; color:var(--blue-900); margin-bottom:.8rem; padding-bottom:.5rem; border-bottom: 2px solid var(--blue-100); }

.badge { display:inline-block; padding:.18rem .65rem; border-radius:999px; font-size:.75rem; font-weight:700; margin:0 .2rem; }
.badge-blue { background:var(--blue-100); color:var(--blue-700); }
.badge-red { background:#FEE2E2; color:#B91C1C; }
.badge-green { background:#DCFCE7; color:#15803D; }
.badge-amber { background:#FEF3C7; color:#92400E; }

.divider { height:1px; background:var(--gray-200); margin:1.2rem 0; border:none; }

/* ── Quick prompt buttons ───────────────────────── */
div[data-testid="stButton"] > button {
    border-radius: 12px;
    border: 1px solid var(--blue-100);
    background: var(--blue-50);
    color: var(--blue-700);
    font-weight: 600;
    font-size: .85rem;
    padding: .55rem .8rem;
    white-space: normal;
    height: auto;
}
div[data-testid="stButton"] > button:hover {
    background: var(--blue-100);
    border-color: var(--blue-500);
    color: var(--blue-900);
}

/* ── Chat bubbles: RTL/LTR aware ────────────────── */
.chat-rtl { direction: rtl; text-align: right; }
.chat-ltr { direction: ltr; text-align: left; }

/* ── CRM ticket cards ───────────────────────────── */
.ticket-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:.9rem; }
.ticket-id { font-family:'Plus Jakarta Sans',sans-serif; font-weight:800; color:var(--blue-900); font-size:.95rem; letter-spacing:.02em; }
.ticket-grid { direction: rtl; }
.ticket-row { display:flex; padding:.55rem 0; border-bottom:1px solid var(--gray-100); font-size:.88rem; }
.ticket-row:last-child { border-bottom:none; }
.ticket-label { width:170px; min-width:170px; color:var(--gray-600); font-weight:700; flex-shrink:0; }
.ticket-value { color:#1E293B; line-height:1.55; }
.ticket-summary { background: var(--blue-50); border-right: 4px solid var(--blue-500); border-radius: 10px 0 0 10px; padding: .8rem 1rem; margin-top: .6rem; font-size:.86rem; line-height:1.6; }
.ticket-next { background: #FFFBEB; border-right: 4px solid var(--accent); border-radius: 10px 0 0 10px; padding: .8rem 1rem; margin-top: .6rem; font-size:.86rem; line-height:1.6; }
.ticket-meta { color: var(--gray-600); font-size:.78rem; margin-top:.8rem; text-align:left; direction:ltr; }
</style>
"""


def inject_global_css():
    st.markdown(KAYFA_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class="page-header">
            <h1>{title}</h1>
            {f"<p>{subtitle}</p>" if subtitle else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )
