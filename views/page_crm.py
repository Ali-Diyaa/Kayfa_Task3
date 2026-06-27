import streamlit as st
from datetime import datetime
import streamlit.components.v1 as components
import plotly.graph_objects as go
from collections import Counter

from core.crm_models import list_tickets
from core.styles import page_header

# ═══════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════

TEMP_CONFIG = {
    "ساخن": {"en": "Hot",  "emoji": "🔥", "color": "#ef4444"},
    "دافئ": {"en": "Warm", "emoji": "🌤", "color": "#f59e0b"},
    "بارد": {"en": "Cold", "emoji": "❄", "color": "#3b82f6"},
}

_DARK_BG       = "#0B1220"
_PLOT_BG       = "#111827"
_GRID_CLR      = "#1f2937"
_TEXT_MUTED    = "#9ca3af"
_TEXT_WHITE     = "#ffffff"
_ACCENT_BLUE   = "#2563eb"
_ACCENT_INDIGO = "#6366f1"

_BASE_LAYOUT = dict(
    paper_bgcolor=_DARK_BG,
    plot_bgcolor=_PLOT_BG,
    font=dict(family="Inter, system-ui, sans-serif", color=_TEXT_MUTED, size=12),
    margin=dict(l=50, r=24, t=48, b=50),
)

_CHART_CFG = dict(displayModeBar=False, responsive=True)


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _fmt(value):
    if isinstance(value, list):
        return "، ".join(value) if value else "—"
    return value if value else "—"


# ═══════════════════════════════════════════════════════════════════
# Ticket Card
# ═══════════════════════════════════════════════════════════════════

def _ticket_card_html(t: dict) -> str:
    ticket_id = t.get("ticket_id", "—")
    name      = t.get("name", "No name")
    phone     = _fmt(t.get("phone"))
    city      = _fmt(t.get("city"))
    language  = f"{t.get('language','—')} — {t.get('dialect','—')}"
    products  = _fmt(t.get("products_of_interest"))
    goal      = _fmt(t.get("goal"))
    level     = _fmt(t.get("current_level"))
    signals   = _fmt(t.get("buying_signals"))
    objections = _fmt(t.get("objections"))
    summary   = t.get("conversation_summary", "—")
    next_action = t.get("next_action", "—")

    ts = t.get("timestamp")
    ts_str = ts.strftime("%Y-%m-%d · %H:%M") if isinstance(ts, datetime) else "—"
    temp = t.get("lead_temperature", "بارد")
    cfg  = TEMP_CONFIG.get(temp, TEMP_CONFIG["بارد"])

    initials = "".join([p[0] for p in name.split()[:2]]) if name != "No name" else "؟"
    phone_clean = "".join(filter(str.isdigit, phone))

    return f"""
    <div dir="rtl" style="font-family:'Cairo', system-ui, sans-serif; margin-bottom:24px;">
        <div style="border-radius:20px; background:{_DARK_BG}; border:1px solid #1e293b; overflow:hidden;">
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
                        <div style="color:{_TEXT_MUTED}; font-size:11px; margin-bottom:4px;">اللغة</div>
                        <div style="color:white; font-size:14px;">{language}</div>
                    </div>
                    <div style="background:#111827; padding:12px; border-radius:12px; border:1px solid #1f2937;">
                        <div style="color:{_TEXT_MUTED}; font-size:11px; margin-bottom:4px;">المنتجات</div>
                        <div style="color:white; font-size:14px;">{products}</div>
                    </div>
                    <div style="background:#111827; padding:12px; border-radius:12px; border:1px solid #1f2937;">
                        <div style="color:{_TEXT_MUTED}; font-size:11px; margin-bottom:4px;">الهدف</div>
                        <div style="color:white; font-size:14px;">{goal}</div>
                    </div>
                    <div style="background:#111827; padding:12px; border-radius:12px; border:1px solid #1f2937;">
                        <div style="color:{_TEXT_MUTED}; font-size:11px; margin-bottom:4px;">إشارات الشراء</div>
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


# ═══════════════════════════════════════════════════════════════════
# Dashboard — Stat Cards
# ═══════════════════════════════════════════════════════════════════

def _stat_cards_html(total, hot, warm, cold):
    hot_pct  = f"{hot / total * 100:.0f}%" if total else "0%"
    warm_pct = f"{warm / total * 100:.0f}%" if total else "0%"
    cold_pct = f"{cold / total * 100:.0f}%" if total else "0%"

    return f"""
    <style>
        .crm-stat-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            margin-bottom: 32px;
        }}
        @media (max-width: 900px) {{
            .crm-stat-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
        @media (max-width: 480px) {{
            .crm-stat-grid {{ grid-template-columns: 1fr; }}
        }}
        .crm-stat-card {{
            background: {_DARK_BG};
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 22px 24px;
            transition: transform 0.25s cubic-bezier(.16,1,.3,1),
                        box-shadow 0.25s cubic-bezier(.16,1,.3,1);
            cursor: default;
        }}
        .crm-stat-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 12px 32px rgba(0,0,0,0.35);
        }}
        .crm-stat-label  {{ color: {_TEXT_MUTED}; font-size: 12px; margin-bottom: 10px; font-weight: 500; }}
        .crm-stat-value  {{ font-size: 34px; font-weight: 800; line-height: 1; }}
        .crm-stat-pct    {{ font-size: 12px; margin-top: 8px; font-weight: 600; opacity: 0.75; }}
    </style>

    <div style="font-family:'Inter',system-ui,sans-serif; direction:ltr; text-align:left;">
        <div class="crm-stat-grid">
            <div class="crm-stat-card" style="border-left:3px solid {_ACCENT_BLUE};">
                <div class="crm-stat-label">📋 Total Leads</div>
                <div class="crm-stat-value" style="color:{_TEXT_WHITE};">{total}</div>
                <div class="crm-stat-pct" style="color:{_ACCENT_BLUE};">All tickets</div>
            </div>
            <div class="crm-stat-card" style="border-left:3px solid #ef4444;">
                <div class="crm-stat-label">🔥 Hot Leads</div>
                <div class="crm-stat-value" style="color:#ef4444;">{hot}</div>
                <div class="crm-stat-pct" style="color:#ef4444;">{hot_pct} of total</div>
            </div>
            <div class="crm-stat-card" style="border-left:3px solid #f59e0b;">
                <div class="crm-stat-label">🌤 Warm Leads</div>
                <div class="crm-stat-value" style="color:#f59e0b;">{warm}</div>
                <div class="crm-stat-pct" style="color:#f59e0b;">{warm_pct} of total</div>
            </div>
            <div class="crm-stat-card" style="border-left:3px solid #3b82f6;">
                <div class="crm-stat-label">❄ Cold Leads</div>
                <div class="crm-stat-value" style="color:#3b82f6;">{cold}</div>
                <div class="crm-stat-pct" style="color:#3b82f6;">{cold_pct} of total</div>
            </div>
        </div>
    </div>
    """


# ═══════════════════════════════════════════════════════════════════
# Dashboard — Charts
# ═══════════════════════════════════════════════════════════════════

def _chart_temperature(tickets):
    counts = Counter(t.get("lead_temperature", "بارد") for t in tickets)
    labels, values, colors = [], [], []
    for name, cfg in TEMP_CONFIG.items():
        labels.append(f"{cfg['emoji']}  {cfg['en']}")
        values.append(counts.get(name, 0))
        colors.append(cfg["color"])

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.62,
        marker_colors=colors,
        textinfo="label+percent",
        textfont_size=13, textfont_color="white",
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
    ))
    fig.add_annotation(
        text=f"<b style='font-size:28px'>{len(tickets)}</b>"
             f"<br><span style='font-size:11px;color:{_TEXT_MUTED}'>Total</span>",
        x=0.5, y=0.5, showarrow=False, font_color=_TEXT_WHITE,
    )
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text="Lead Temperature Distribution",
                   font=dict(size=15, color=_TEXT_WHITE)),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        height=340, showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)


def _chart_products(tickets):
    all_prods = []
    for t in tickets:
        p = t.get("products_of_interest", [])
        if isinstance(p, list):
            all_prods.extend(p)
        elif p:
            all_prods.append(str(p))

    if not all_prods:
        st.caption("No product data available yet.")
        return

    items = Counter(all_prods).most_common(8)
    labels = [i[0] for i in items]
    values = [i[1] for i in items]
    n = len(values)

    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker_color=[
            f"rgba(99,102,241,{0.4 + 0.6 * i / max(n - 1, 1)})"
            for i in range(n)
        ],
        marker_cornerradius=6,
        text=values, textposition="outside",
        textfont=dict(color=_TEXT_WHITE, size=12),
        hovertemplate="<b>%{y}</b><br>Count: %{x}<extra></extra>",
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text="Most Requested Products",
                   font=dict(size=15, color=_TEXT_WHITE)),
        xaxis=dict(gridcolor=_GRID_CLR, zerolinecolor=_GRID_CLR),
        yaxis=dict(autorange="reversed", gridcolor="rgba(0,0,0,0)",
                    tickfont=dict(size=12)),
        height=340, showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)


def _chart_cities(tickets):
    cities = [t.get("city", "Unknown") for t in tickets if t.get("city")]
    if not cities:
        st.caption("No city data available yet.")
        return

    items = Counter(cities).most_common(8)
    labels = [i[0] for i in items]
    values = [i[1] for i in items]
    n = len(values)

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=[
            f"rgba(37,99,235,{0.4 + 0.6 * i / max(n - 1, 1)})"
            for i in range(n)
        ],
        marker_cornerradius=6,
        text=values, textposition="outside",
        textfont=dict(color=_TEXT_WHITE, size=12),
        hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>",
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text="Geographic Distribution",
                   font=dict(size=15, color=_TEXT_WHITE)),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", tickangle=-30,
                    tickfont=dict(size=11)),
        yaxis=dict(gridcolor=_GRID_CLR, zerolinecolor=_GRID_CLR),
        height=340, showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)


def _chart_timeline(tickets):
    date_counts = Counter()
    for t in tickets:
        ts = t.get("timestamp")
        if isinstance(ts, datetime):
            date_counts[ts.strftime("%Y-%m-%d")] += 1

    if not date_counts:
        st.caption("No date data available yet.")
        return

    sorted_dates = sorted(date_counts.keys())
    values = [date_counts[d] for d in sorted_dates]

    fig = go.Figure(go.Scatter(
        x=sorted_dates, y=values,
        mode="lines+markers+text",
        fill="tozeroy",
        fillcolor="rgba(37,99,235,0.10)",
        line=dict(color=_ACCENT_BLUE, width=2.5, shape="spline"),
        marker=dict(size=8, color=_ACCENT_BLUE,
                    line=dict(width=2, color=_DARK_BG)),
        text=values, textposition="top center",
        textfont=dict(color=_TEXT_WHITE, size=11),
        hovertemplate="<b>%{x}</b><br>Tickets: %{y}<extra></extra>",
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text="Ticket Volume Over Time",
                   font=dict(size=15, color=_TEXT_WHITE)),
        xaxis=dict(gridcolor=_GRID_CLR, zerolinecolor=_GRID_CLR,
                    tickfont=dict(size=11)),
        yaxis=dict(gridcolor=_GRID_CLR, zerolinecolor=_GRID_CLR),
        height=340, showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)


def _chart_goals(tickets):
    goals = [t.get("goal") for t in tickets if t.get("goal")]
    if not goals:
        st.caption("No goal data available yet.")
        return

    items = Counter(goals).most_common(6)
    labels = [i[0] for i in items]
    values = [i[1] for i in items]
    n = len(values)

    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker_color=[
            f"rgba(245,158,11,{0.4 + 0.6 * i / max(n - 1, 1)})"
            for i in range(n)
        ],
        marker_cornerradius=6,
        text=values, textposition="outside",
        textfont=dict(color=_TEXT_WHITE, size=12),
        hovertemplate="<b>%{y}</b><br>Count: %{x}<extra></extra>",
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text="Lead Goals",
                   font=dict(size=15, color=_TEXT_WHITE)),
        xaxis=dict(gridcolor=_GRID_CLR, zerolinecolor=_GRID_CLR),
        yaxis=dict(autorange="reversed", gridcolor="rgba(0,0,0,0)",
                    tickfont=dict(size=12)),
        height=340, showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)


def _chart_languages(tickets):
    langs = []
    for t in tickets:
        lang = t.get("language")
        dialect = t.get("dialect")
        if lang:
            label = f"{lang}" + (f" — {dialect}" if dialect else "")
            langs.append(label)

    if not langs:
        st.caption("No language data available yet.")
        return

    items = Counter(langs).most_common(6)
    labels = [i[0] for i in items]
    values = [i[1] for i in items]

    pie_colors = [
        "#6366f1", "#8b5cf6", "#a78bfa",
        "#2563eb", "#3b82f6", "#60a5fa",
    ]

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.5,
        marker_colors=pie_colors[:len(values)],
        textinfo="label+percent",
        textfont_size=12, textfont_color="white",
        hovertemplate="<b>%{label}</b><br>Count: %{value}<extra></extra>",
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text="Language & Dialect Breakdown",
                   font=dict(size=15, color=_TEXT_WHITE)),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        height=340, showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)


# ═══════════════════════════════════════════════════════════════════
# Dashboard — Assemble
# ═══════════════════════════════════════════════════════════════════

def _render_dashboard(tickets):
    if not tickets:
        return

    total = len(tickets)
    hot  = sum(1 for t in tickets if t.get("lead_temperature") == "ساخن")
    warm = sum(1 for t in tickets if t.get("lead_temperature") == "دافئ")
    cold = sum(1 for t in tickets if t.get("lead_temperature") == "بارد")

    st.markdown(f"""
    <div style="font-family:'Inter',system-ui,sans-serif; margin-bottom:22px;
         display:flex; align-items:center; gap:12px; direction:ltr; text-align:left;">
        <span style="font-size:19px; font-weight:800; color:{_TEXT_WHITE};
              background:linear-gradient(135deg,{_ACCENT_BLUE},{_ACCENT_INDIGO});
              -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
            📊 Analytics Dashboard
        </span>
        <span style="font-size:13px; color:{_TEXT_MUTED};">— Overview of all captured leads</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(_stat_cards_html(total, hot, warm, cold), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        _chart_temperature(tickets)
    with c2:
        _chart_products(tickets)

    c3, c4 = st.columns(2)
    with c3:
        _chart_cities(tickets)
    with c4:
        _chart_timeline(tickets)

    c5, c6 = st.columns(2)
    with c5:
        _chart_goals(tickets)
    with c6:
        _chart_languages(tickets)

    st.markdown(
        '<div style="height:1px; background:linear-gradient(90deg,rgba(0,0,0,0),#1e293b 20%,#1e293b 80%,rgba(0,0,0,0)); '
        'margin:40px 0 8px;"></div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════
# Page
# ═══════════════════════════════════════════════════════════════════

def show():
    if st.session_state.get("role") != "admin":
        st.error("This page is available for the sales team (admin) only.")
        return

    page_header("🎯 CRM — Leads",
                "Every ticket here was captured automatically from a chatbot conversation.")

    tickets = list_tickets()

    _render_dashboard(tickets)

    if not tickets:
        st.info("No tickets yet. They will appear here once the chatbot captures a lead.")
        return

    c1, c2 = st.columns([1, 2])
    with c1:
        temp_filter = st.selectbox("Filter by temperature",
                                   ["All", "ساخن", "دافئ", "بارد"])
    with c2:
        search = st.text_input("Search by name / phone / ticket ID", "")

    filtered = tickets
    if temp_filter != "All":
        filtered = [t for t in filtered
                    if t.get("lead_temperature") == temp_filter]
    if search.strip():
        s = search.strip().lower()
        filtered = [
            t for t in filtered
            if s in str(t.get("name", "")).lower()
            or s in str(t.get("phone", "")).lower()
            or s in str(t.get("ticket_id", "")).lower()
        ]

    st.caption(f"Showing {len(filtered)} of {len(tickets)} tickets")
    st.divider()

    for t in filtered:
        components.html(_ticket_card_html(t), height=600, scrolling=False)