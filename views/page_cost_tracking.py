"""
PAGE — Cost Analytics Dashboard for Admin.
Shows cost per message, per conversation, per user with rich visuals.
"""
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from collections import defaultdict
from core.intent import detect_intent, detect_dialect
import html as html_lib
from core.db import get_collections, safe_get_collections
from core.styles import page_header

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


# ── Shared admin CSS ──────────────────────────────────────────────
def _inject_css():
    st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        .cost-dashboard * { font-family: 'Cairo','Inter',system-ui,sans-serif !important; }
        .msg-log-card {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 20px 24px;
            margin-bottom: 12px;
            transition: border-color 0.2s;
        }
        .msg-log-card:hover { border-color: #334155; }
        .msg-prompt {
            color: #e2e8f0;
            font-size: 14px;
            line-height: 1.7;
            margin-bottom: 12px;
            direction: rtl;
        }
        .msg-badges { display: flex; flex-wrap: wrap; gap: 8px; }
        .badge {
            display: inline-flex; align-items: center; gap: 4px;
            padding: 4px 12px; border-radius: 20px;
            font-size: 11px; font-weight: 600;
        }
        .badge-cost { background: rgba(34,197,94,0.15); color: #4ade80; }
        .badge-tokens { background: rgba(99,102,241,0.15); color: #a5b4fc; }
        .badge-time { background: rgba(245,158,11,0.15); color: #fbbf24; }
        .badge-intent { background: rgba(139,92,246,0.15); color: #c4b5fd; }
        .badge-dialect { background: rgba(59,130,246,0.15); color: #93c5fd; }
        .badge-tools { background: rgba(236,72,153,0.15); color: #f9a8d4; }
        .badge-user { background: rgba(255,255,255,0.08); color: #cbd5e1; }
        .badge-ts { background: rgba(255,255,255,0.05); color: #64748b; }

        .conv-section {
            background: #0B1220;
            border: 1px solid #1e293b;
            border-radius: 20px;
            padding: 24px;
            margin-bottom: 24px;
        }
        .conv-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid #1e293b;
        }
        .conv-title { font-size: 16px; font-weight: 700; color: #f1f5f9; }
        .conv-total { font-size: 14px; font-weight: 700; color: #4ade80; }

        .user-summary-card {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 12px;
            display: flex; align-items: center; gap: 16px;
        }
        .user-avatar {
            width: 48px; height: 48px; border-radius: 14px;
            background: linear-gradient(135deg, #6366f1, #4f46e5);
            display: flex; align-items: center; justify-content: center;
            font-weight: 800; font-size: 18px; color: white; flex-shrink: 0;
        }
        .user-info { flex: 1; }
        .user-name { font-size: 15px; font-weight: 700; color: #f1f5f9; }
        .user-stats { font-size: 12px; color: #94a3b8; margin-top: 2px; }
        .user-cost { font-size: 18px; font-weight: 800; color: #4ade80; }

        /* ── Expander (Conversation Dropdown) ── */
        [data-testid="stExpander"] {
            border: 1px solid #1e293b !important;
            border-radius: 14px !important;
            background: #111827 !important;
            margin-bottom: 8px !important;
            transition: all 0.2s ease !important;
            overflow: hidden;
            color: #f1f5f9 !important;
        }
        [data-testid="stExpander"]:hover {
            border-color: #334155 !important;
            background: #1a2236 !important;
            box-shadow: 0 4px 16px rgba(0,0,0,0.15) !important;
        }
        [data-testid="stExpander"] svg {
            color: #6366f1 !important;
            transition: transform 0.25s ease !important;
        }
        [data-testid="stExpander"]:hover svg {
            transform: scale(1.2) !important;
            color: #818cf8 !important;
        }
        [data-testid="stExpander"] > div[data-testid="stVerticalBlock"] > div > div {
            background: transparent !important;
            border: none !important;
            padding: 14px 20px !important;
            cursor: pointer !important;
        }
        [data-testid="stExpander"][data-expanded="true"] {
            border-color: rgba(99,102,241,0.2) !important;
            border-bottom-left-radius: 0 !important;
            border-bottom-right-radius: 0 !important;
            background: #0f172a !important;
        }
        [data-testid="stExpander"][data-expanded="true"] > div[data-testid="stVerticalBlock"] > div > div {
            border-bottom: 1px solid rgba(99,102,241,0.1) !important;
            padding-bottom: 16px !important;
        }
    </style>
    """, unsafe_allow_html=True)
def _stat_card_html(icon: str, value: str, label: str, color: str) -> str:
    color_map = {
        "blue":   {"from": "#1e3a5f", "to": "#0f2440", "accent": "#60a5fa", "glow": "rgba(96,165,250,0.15)"},
        "green":  {"from": "#14432a", "to": "#0a2e1a", "accent": "#4ade80", "glow": "rgba(74,222,128,0.15)"},
        "amber":  {"from": "#452c0a", "to": "#2d1d06", "accent": "#fbbf24", "glow": "rgba(251,191,36,0.15)"},
        "purple": {"from": "#2e1065", "to": "#1a0a3e", "accent": "#a78bfa", "glow": "rgba(167,139,250,0.15)"},
    }
    c = color_map.get(color, color_map["blue"])

    return f'''
    <div style="
        background: linear-gradient(160deg, {c['from']} 0%, {c['to']} 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 20px;
        padding: 28px 20px 24px;
        text-align: center;
        position: relative;
        overflow: hidden;
        transition: all 0.35s cubic-bezier(0.16,1,0.3,1);
        cursor: default;
    " onmouseover="this.style.transform='translateY(-4px)';this.style.borderColor='{c['accent']}33';this.style.boxShadow='0 12px 40px {c['glow']}'"
       onmouseout="this.style.transform='translateY(0)';this.style.borderColor='rgba(255,255,255,0.06)';this.style.boxShadow='none'">

        <!-- Decorative circle -->
        <div style="
            position: absolute; top: -20px; right: -20px;
            width: 90px; height: 90px;
            background: radial-gradient(circle, {c['glow']} 0%, transparent 70%);
            border-radius: 50%;
            pointer-events: none;
        "></div>
        <div style="
            position: absolute; bottom: -15px; left: -15px;
            width: 60px; height: 60px;
            background: radial-gradient(circle, {c['glow']} 0%, transparent 70%);
            border-radius: 50%;
            pointer-events: none;
        "></div>

        <!-- Icon -->
        <div style="
            width: 48px; height: 48px;
            margin: 0 auto 14px;
            border-radius: 14px;
            background: {c['glow']};
            border: 1px solid {c['accent']}22;
            display: flex; align-items: center; justify-content: center;
            font-size: 22px;
            position: relative;
        ">{icon}</div>

        <!-- Value -->
        <div style="
            font-size: 30px;
            font-weight: 800;
            color: #f1f5f9;
            letter-spacing: -1px;
            margin-bottom: 6px;
            position: relative;
            font-family: 'Inter','Cairo',system-ui,sans-serif;
        ">{value}</div>

        <!-- Label -->
        <div style="
            font-size: 11px;
            font-weight: 700;
            color: {c['accent']}99;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            position: relative;
            font-family: 'Inter','Cairo',system-ui,sans-serif;
        ">{label}</div>

        <!-- Bottom accent line -->
        <div style="
            position: absolute;
            bottom: 0; left: 20%; right: 20%;
            height: 2px;
            background: linear-gradient(90deg, transparent, {c['accent']}66, transparent);
            border-radius: 0 0 20px 20px;
        "></div>
    </div>'''


def _badge_html(icon: str, text: str, cls: str) -> str:
    return f'<span class="badge {cls}">{icon} {text}</span>'


def _msg_card_html(log: dict) -> str:
    prompt = log.get("user_prompt", "—")
    if len(prompt) > 120:
        prompt = prompt[:117] + "..."
    ts = log.get("timestamp")
    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if isinstance(ts, datetime) else "—"

    badges = (
        _badge_html("💰", f"${log.get('total_cost', 0):.6f}", "badge-cost")
        + _badge_html("🔢", f"{log.get('llm_tokens_in', 0)}in / {log.get('llm_tokens_out', 0)}out", "badge-tokens")
        + _badge_html("⚡", f"{log.get('latency_ms', 0):.0f}ms", "badge-time")
        + _badge_html("🛠", f"{log.get('tool_calls_count', 0)} tools", "badge-tools")
        + _badge_html("🎯", log.get("intent", "—"), "badge-intent")
        + _badge_html("🗣", log.get("dialect", "—")[:20], "badge-dialect")
        + _badge_html("👤", log.get("user_id", "—"), "badge-user")
        + _badge_html("🕒", ts_str, "badge-ts")
    )

    return f'''
    <div class="msg-log-card">
        <div class="msg-prompt">💬 {prompt}</div>
        <div class="msg-badges">{badges}</div>
    </div>'''


# ── Plotly chart theme ───────────────────────────────────────────
_PLOTLY_LAYOUT = go.Layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Cairo, Inter, sans-serif", color="#94a3b8", size=12),
    margin=dict(l=40, r=30, t=40, b=40),
    xaxis=dict(
        gridcolor="rgba(51,65,85,0.3)",
        zerolinecolor="rgba(51,65,85,0.5)",
        tickfont=dict(size=11),
    ),
    yaxis=dict(
        gridcolor="rgba(51,65,85,0.3)",
        zerolinecolor="rgba(51,65,85,0.5)",
        tickfont=dict(size=11),
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        font=dict(size=11, color="#94a3b8"),
    ),
    hoverlabel=dict(
        bgcolor="#1e293b",
        bordercolor="#334155",
        font=dict(size=12, color="#e2e8f0", family="Cairo, Inter, sans-serif"),
    ),
)


def _build_charts(all_logs: list) -> None:
    """Build and render all Plotly charts from the logs data."""
    if not all_logs:
        return

    # ── Prepare DataFrame ──
    rows = []
    for log in all_logs:
        ts = log.get("timestamp")
        rows.append({
            "timestamp": ts if isinstance(ts, datetime) else datetime.min,
            "time_str": ts.strftime("%H:%M\n%m-%d") if isinstance(ts, datetime) else "—",
            "cost": log.get("total_cost", 0),
            "tokens_in": log.get("llm_tokens_in", 0),
            "tokens_out": log.get("llm_tokens_out", 0),
            "tokens_total": log.get("llm_tokens_in", 0) + log.get("llm_tokens_out", 0),
            "latency_ms": log.get("latency_ms", 0),
            "tool_calls": log.get("tool_calls_count", 0),
            "intent": log.get("intent", "unknown"),
            "dialect": log.get("dialect", "unknown"),
            "user_id": log.get("user_id", "anonymous"),
        })
    df = pd.DataFrame(rows)
    df = df.sort_values("timestamp").reset_index(drop=True)

    # ── Color palette ──
    C = {
        "green": "#4ade80",
        "blue": "#60a5fa",
        "amber": "#fbbf24",
        "purple": "#a78bfa",
        "pink": "#fb7185",
        "red": "#f87171",
        "cyan": "#22d3ee",
        "indigo": "#818cf8",
    }

    st.markdown('<div style="height:40px;"></div>', unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════
    # CHART 1 & 2: Cost Over Time + Token Breakdown (side by side)
    # ════════════════════════════════════════════════════════════
    ch1, ch2 = st.columns(2)
    with ch1:
        st.markdown("**💰 Cost Per Message Over Time**")
        fig1 = go.Figure(layout=_PLOTLY_LAYOUT)
        fig1.add_trace(go.Scatter(
            x=df["time_str"],
            y=df["cost"],
            mode="lines+markers",
            line=dict(color=C["green"], width=2, shape="spline"),
            marker=dict(size=8, color=C["green"], line=dict(width=1, color="#060a13")),
            name="Cost ($)",
            hovertemplate="<b>%{x}</b><br>Cost: $%{y:.6f}<extra></extra>",
        ))
        fig1.add_trace(go.Bar(
            x=df["time_str"],
            y=df["cost"],
            marker_color=df["cost"].apply(
                lambda v: C["green"] if v < df["cost"].median() else C["amber"]
            ),
            opacity=0.3,
            name="Cost Bar",
            showlegend=False,
            hovertemplate="<b>%{x}</b><br>Cost: $%{y:.6f}<extra></extra>",
        ))
        fig1.update_yaxes(title_text="Cost ($)", title_font=dict(size=12, color="#94a3b8"))
        fig1.update_xaxes(title_text="", tickangle=-45)
        st.plotly_chart(fig1, use_container_width=True, height=300)

    with ch2:
        st.markdown("**🔢 Token Usage: Input vs Output**")
        fig2 = go.Figure(layout=_PLOTLY_LAYOUT)
        fig2.add_trace(go.Bar(
            x=df["time_str"],
            y=df["tokens_in"],
            name="Tokens In",
            marker_color=C["blue"],
            hovertemplate="<b>%{x}</b><br>Input: %{y:,}<extra></extra>",
        ))
        fig2.add_trace(go.Bar(
            x=df["time_str"],
            y=df["tokens_out"],
            name="Tokens Out",
            marker_color=C["purple"],
            hovertemplate="<b>%{x}</b><br>Output: %{y:,}<extra></extra>",
        ))
        fig2.update_layout(barmode="group")
        fig2.update_yaxes(title_text="Tokens", title_font=dict(size=12, color="#94a3b8"))
        fig2.update_xaxes(title_text="", tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True, height=300)

    # ════════════════════════════════════════════════════════════
    # CHART 3 & 4: Cost by Intent + Tool Call Distribution
    # ════════════════════════════════════════════════════════════
    ch3, ch4 = st.columns(2)
    with ch3:
        st.markdown("**🎯 Average Cost by Intent**")
        intent_df = df.groupby("intent").agg(
            avg_cost=("cost", "mean"),
            total_msgs=("cost", "count"),
            avg_tokens=("tokens_total", "mean"),
        ).reset_index().sort_values("avg_cost", ascending=True)

        intent_colors = {
            "just_browsing": C["blue"],
            "comparing_options": C["amber"],
            "price_sensitive": C["pink"],
            "hesitant": C["purple"],
            "ready_to_enroll": C["green"],
            "unknown": "#64748b",
        }
        bar_colors = [intent_colors.get(i, "#64748b") for i in intent_df["intent"]]

        fig3 = go.Figure(layout=_PLOTLY_LAYOUT)
        fig3.add_trace(go.Bar(
            y=intent_df["intent"],
            x=intent_df["avg_cost"],
            orientation="h",
            marker_color=bar_colors,
            textposition="outside",
            text=intent_df["avg_cost"].apply(lambda v: f"${v:.6f}"),
            textfont=dict(size=11, color="#e2e8f0"),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Avg Cost: $%{x:.6f}<br>"
                "Messages: %{customdata[0]}<extra></extra>"
            ),
            customdata=intent_df[["total_msgs"]],
        ))
        fig3.update_xaxes(
            title_text="Average Cost ($)",
            title_font=dict(size=12, color="#94a3b8"),
            ticksuffix=" $",
        )
        fig3.update_yaxes(title_text="")
        fig3.update_layout(height=max(200, len(intent_df) * 45), margin=dict(l=120))
        st.plotly_chart(fig3, use_container_width=True)

    with ch4:
        st.markdown("**🛠 Tool Call Distribution**")
        tool_counts = df["tool_calls"].value_counts().sort_index()
        tool_labels = {0: "0 (No Tools)", 1: "1 Tool", 2: "2 Tools", 3: "3+ Tools"}
        tool_colors_map = {0: C["blue"], 1: C["green"], 2: C["amber"], 3: C["pink"]}

        fig4 = go.Figure(layout=_PLOTLY_LAYOUT)
        fig4.add_trace(go.Pie(
            labels=[tool_labels.get(k, f"{k} Tools") for k in tool_counts.index],
            values=tool_counts.values,
            marker_colors=[tool_colors_map.get(k, "#64748b") for k in tool_counts.index],
            hole=0.55,
            textinfo="label+percent",
            textfont=dict(size=12, color="#1e293b"),
            textposition="outside",
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}<extra></extra>",
        ))
        fig4.update_layout(
            height=300,
            margin=dict(t=30, b=30, l=30, r=30),
            showlegend=False,
            annotations=[dict(font=dict(size=14, color="#94a3b8"), text="Tool Calls", showarrow=False, x=0.5, y=1.02)],
        )
        st.plotly_chart(fig4, use_container_width=True)

    # ════════════════════════════════════════════════════════════
    # CHART 5: Latency vs Cost Scatter
    # ════════════════════════════════════════════════════════════
    st.markdown("**⚡ Latency vs Cost — Per Message**")
    fig5 = go.Figure(layout=_PLOTLY_LAYOUT)
    fig5.add_trace(go.Scatter(
        x=df["latency_ms"],
        y=df["cost"],
        mode="markers",
        marker=dict(
            size=df["tokens_total"] / 500 + 6,
            color=df["tool_calls"],
            colorscale=[[0, C["blue"]], [0.5, C["amber"]], [1, C["red"]]],
            colorbar=dict(
                title="Tool Calls",
                tickfont=dict(size=11, color="#94a3b8"),
            ),
            line=dict(width=0),
            opacity=0.85,
        ),
        text=df["time_str"],
        textposition="top center",
        textfont=dict(size=9, color="#64748b"),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Latency: %{x:,.0f} ms<br>"
            "Cost: $%{y:.6f}<br>"
            "Tokens: %{customdata[0]:,}<br>"
            "Tools: %{marker.color:.0f}<extra></extra>"
        ),
        customdata=df[["tokens_total"]],
        name="Messages",
    ))

    # Add quadrant reference lines
    med_lat = df["latency_ms"].median()
    med_cost = df["cost"].median()
    fig5.add_hline(y=med_cost, line_dash="dash", line_color="rgba(74,222,128,0.3)", annotation_text=f"Median Cost: ${med_cost:.6f}")
    fig5.add_vline(x=med_lat, line_dash="dash", line_color="rgba(96,165,250,0.3)", annotation_text=f"Median Latency: {med_lat:,.0f}ms")

    fig5.update_xaxes(title_text="Latency (ms)", title_font=dict(size=12, color="#94a3b8"))
    fig5.update_yaxes(title_text="Cost ($)", title_font=dict(size=12, color="#94a3b8"), ticksuffix=" $")
    fig5.update_layout(height=380)
    st.plotly_chart(fig5, use_container_width=True)


# ── Main Page ─────────────────────────────────────────────────────
def show():
    if st.session_state.get("role") != "admin":
        st.error("This page is available for admins only.")
        return

    _inject_css()
    page_header("📊 Cost Analytics", "Track every token, every dollar, every millisecond")

    cols_db = safe_get_collections()
    if cols_db is None:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
            <div style="font-size:64px;margin-bottom:16px;">🔌</div>
            <div style="font-size:20px;font-weight:700;color:#f1f5f9;margin-bottom:8px;">Database Unreachable</div>
            <div style="font-size:14px;color:#94a3b8;">Could not connect to MongoDB. Check your connection and try again.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    all_logs = list(cols_db["usage_logs"].find(
        {"chat_id": {"$not": {"$regex": "^(baseline_seq|optimized)_"}}}
    ).sort("timestamp", -1))

    # Backfill missing intent/dialect from stored prompts
    for log in all_logs:
        if not log.get("intent") or log["intent"] == "—":
            log["intent"] = detect_intent(log.get("user_prompt", ""))
        if not log.get("dialect") or log["dialect"] == "—":
            log["dialect"] = detect_dialect(log.get("user_prompt", ""))

    if not all_logs:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
            <div style="font-size:64px;margin-bottom:16px;">📭</div>
            <div style="font-size:20px;font-weight:700;color:#f1f5f9;margin-bottom:8px;">No Usage Data Yet</div>
            <div style="font-size:14px;color:#94a3b8;">Cost data will appear here as users interact with the agent.</div>
        </div>
        """, unsafe_allow_allow_html=True)
        return

    # ── Aggregate stats ──
    total_msgs = len(all_logs)
    total_cost = sum(l.get("total_cost", 0) for l in all_logs)
    total_tokens_in = sum(l.get("llm_tokens_in", 0) for l in all_logs)
    total_tokens_out = sum(l.get("llm_tokens_out", 0) for l in all_logs)
    total_tokens = total_tokens_in + total_tokens_out
    avg_cost = total_cost / total_msgs if total_msgs > 0 else 0
    total_time = sum(l.get("latency_ms", 0) for l in all_logs)

    # Unique users
    unique_users = set(l.get("user_id", "anonymous") for l in all_logs)

    # ── Summary Cards ──
    cards_html = f'''<div style="
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 16px;
        margin-bottom: 36px;
        font-family: 'Cairo','Inter',system-ui,sans-serif;
    ">
        {_stat_card_html("💬", f"{total_msgs:,}", "Total Messages", "blue")}
        {_stat_card_html("💰", f"${total_cost:.4f}", "Total Cost", "green")}
        {_stat_card_html("📉", f"${avg_cost:.6f}", "Avg Cost / Msg", "amber")}
        {_stat_card_html("🔢", f"{total_tokens:,}", "Total Tokens", "purple")}
        {_stat_card_html("👥", f"{len(unique_users)}", "Unique Users", "blue")}
    </div>'''
    components.html(cards_html, height=210, scrolling=False)

    # ── View Toggle ──
    tab1, tab2, tab3, tab4 = st.tabs(["📋 All Messages", "📁 By Conversation", "👥 By User", "📈 Analytics"])

    # ════════════════════════════════════════════════════════════════
    # TAB 1: All Messages
    # ════════════════════════════════════════════════════════════════
    with tab1:
        f_col1, f_col2 = st.columns([1, 2])
        with f_col1:
            users = sorted(unique_users)
            selected_user = st.selectbox("Filter by user", ["All"] + users, key="cost_user_filter")
        with f_col2:
            search_q = st.text_input("Search prompt...", key="cost_search")

        filtered = all_logs
        if selected_user != "All":
            filtered = [l for l in filtered if l.get("user_id") == selected_user]
        if search_q.strip():
            sq = search_q.strip().lower()
            filtered = [l for l in filtered if sq in l.get("user_prompt", "").lower()]

        st.caption(f"Showing {len(filtered)} of {len(all_logs)} messages")
        st.markdown('<div class="cost-dashboard">', unsafe_allow_html=True)
        for log in filtered:
            st.markdown(_msg_card_html(log), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # TAB 2: By Conversation
    # ════════════════════════════════════════════════════════════════
        # ════════════════════════════════════════════════════════════════
    # TAB 2: By Conversation (Collapsible)
    # ════════════════════════════════════════════════════════════════
    with tab2:
        by_chat = defaultdict(list)
        for log in all_logs:
            by_chat[log.get("chat_id", "unknown")].append(log)

        sorted_chats = sorted(
            by_chat.items(),
            key=lambda x: max(l.get("timestamp", datetime.min) for l in x[1]),
            reverse=True
        )

        for chat_id, logs in sorted_chats:
            chat_cost = sum(l.get("total_cost", 0) for l in logs)
            chat_msgs = len(logs)
            chat_tokens = sum(l.get("llm_tokens_in", 0) + l.get("llm_tokens_out", 0) for l in logs)
            latest = max(l.get("timestamp", datetime.min) for l in logs)
            latest_str = latest.strftime("%Y-%m-%d · %H:%M") if isinstance(latest, datetime) else "—"
            user = logs[0].get("user_id", "—")
            initial = user[0].upper() if user else "?"

            # Use Streamlit expander for native collapsible dropdown
            label = f"📁 {chat_id}"
            with st.expander(label, expanded=False):
                # Header card inside the expander
                st.markdown(f'''
                <div style="
                    background:linear-gradient(135deg,#1e293b,#0f172a);
                    border:1px solid #1e293b;
                    border-radius:16px;
                    padding:18px 22px;
                    margin-bottom:16px;
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    flex-wrap:wrap;
                    gap:12px;
                ">
                    <div>
                        <div style="font-size:15px;font-weight:700;color:#f1f5f9;font-family:'Cairo','Inter',sans-serif;">{html_lib.escape(label)}</div>
                        <div style="font-size:12px;color:#64748b;margin-top:4px;font-family:'Cairo','Inter',sans-serif;">
                            👤 {html_lib.escape(user)} · 🕒 {latest_str} · 💬 {chat_msgs} msgs · 🔢 {chat_tokens:,} tokens
                        </div>
                    </div>
                    <div style="
                        background:rgba(34,197,94,0.12);
                        border:1px solid rgba(34,197,94,0.25);
                        border-radius:12px;
                        padding:8px 16px;
                        font-size:16px;
                        font-weight:800;
                        color:#4ade80;
                        font-family:'JetBrains Mono','Cairo',monospace;
                        white-space:nowrap;
                    ">${chat_cost:.6f}</div>
                </div>
                ''', unsafe_allow_html=True)

                # Message cards inside the expander
                st.markdown('<div class="cost-dashboard">', unsafe_allow_html=True)
                for log in logs:
                    st.markdown(_msg_card_html(log), unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # TAB 3: By User
    # ════════════════════════════════════════════════════════════════
    with tab3:
        by_user = defaultdict(list)
        for log in all_logs:
            by_user[log.get("user_id", "anonymous")].append(log)

        sorted_users = sorted(
            by_user.items(),
            key=lambda x: sum(l.get("total_cost", 0) for l in x[1]),
            reverse=True
        )

        st.markdown('<div class="cost-dashboard">', unsafe_allow_html=True)
        for user_id, logs in sorted_users:
            u_cost = sum(l.get("total_cost", 0) for l in logs)
            u_msgs = len(logs)
            u_tokens = sum(l.get("llm_tokens_in", 0) + l.get("llm_tokens_out", 0) for l in logs)
            u_time = sum(l.get("latency_ms", 0) for l in logs)
            u_avg = u_cost / u_msgs if u_msgs > 0 else 0
            initial = user_id[0].upper() if user_id else "?"

            html = f'''
            <div class="user-summary-card">
                <div class="user-avatar">{initial}</div>
                <div class="user-info">
                    <div class="user-name">{user_id}</div>
                    <div class="user-stats">💬 {u_msgs} messages · 🔢 {u_tokens:,} tokens · ⚡ {u_time/1000:.1f}s total · Avg ${u_avg:.6f}/msg</div>
                </div>
                <div class="user-cost">${u_cost:.4f}</div>
            </div>'''
            st.markdown(html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # TAB 4: Analytics (Plotly Charts)
    # ════════════════════════════════════════════════════════════════
    with tab4:
        _build_charts(all_logs)