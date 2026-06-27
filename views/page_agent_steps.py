"""
PAGE — Agent Trace Viewer for Admin.
Step-by-step execution traces matching notebook print_trace detail level.
"""
import json
import re
import html as html_lib
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from core.intent import detect_intent, detect_dialect

from core.db import safe_get_collections
from core.styles import page_header


def _safe_json(obj, max_len: int = 500) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False, indent=2)
        if len(s) > max_len:
            s = s[:max_len] + "\n… [truncated]"
        return s
    except Exception:
        return str(obj)[:max_len]


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _build_md_table(match):
    """Converts a regex-matched markdown table block into HTML table."""
    md_text = match.group(0)
    rows = [r.strip() for r in md_text.strip().split('\n') if r.strip()]
    if len(rows) < 2:
        return md_text

    html = '<div style="overflow-x:auto;margin:10px 0;border-radius:8px;border:1px solid #334155;"><table style="width:100%;border-collapse:collapse;font-size:13px;font-family:\'Cairo\',sans-serif;">'
    
    # Header
    headers = [h.strip() for h in rows[0].split('|') if h.strip()]
    html += '<thead><tr>' + ''.join(f'<th style="border:1px solid #334155;padding:8px 12px;background:#1e293b;color:#f1f5f9;text-align:right;font-weight:700;">{h}</th>' for h in headers) + '</tr></thead>'
    
    # Body
    html += '<tbody>'
    for row in rows[1:]:
        if re.match(r'^[\s\-\|:]+$', row):  # Skip separator row |---|---|
            continue
        cols = [c.strip() for c in row.split('|') if c.strip()]
        html += '<tr>' + ''.join(f'<td style="border:1px solid #334155;padding:8px 12px;color:#cbd5e1;text-align:right;">{c}</td>' for c in cols) + '</tr>'
    html += '</tbody></table></div>'
    return html


def _format_agent_text(content: str) -> str:
    """Formats agent text by converting markdown tables, bold, and breaks to clean HTML."""
    # 1. Escape HTML for safety
    safe = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # 2. Convert literal &lt;br&gt; and \n to proper HTML breaks
    safe = safe.replace("&lt;br&gt;", "<br>")
    safe = safe.replace("\n", "<br>")
    
    # 3. Convert Bold markdown **text** to <strong>text</strong>
    safe = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:#f8fafc;font-weight:700;">\1</strong>', safe)
    
    # 4. Convert Markdown Tables to HTML Tables
    # Match blocks starting and ending with | that may contain <br>
    safe = re.sub(
        r'(?:<br>)?\|.*?\|(?:<br>\|.*?\|)+(?:<br>)?',
        lambda m: _build_md_table(m).replace("<br>", "\n"),
        safe
    )
    
    # 5. Clean up excessive <br> tags around tables
    safe = re.sub(r'(<table)', r'<br><table', safe)
    safe = re.sub(r'(</div>)<br>', r'\1', safe)
    
    # 6. Bullet points styling
    safe = safe.replace("• ", '<span style="color:#6366f1;font-weight:700;margin-left:5px;">•</span> ')
    
    return safe


def _render_trace_steps(trace: list) -> str:
    """
    Render each ModelResponse as a numbered step.
    Each step shows: tool calls + args → tool result → text/thought — all in ONE card.
    """
    if not trace:
        return '<div style="text-align:center;padding:32px;color:#64748b;">No trace data available.</div>'

    nodes = []

    for i, step in enumerate(trace):
        parts = step.get("parts", [])
        tool_result = step.get("tool_result")

        tool_calls = [p for p in parts if p.get("type") == "tool_call"]
        text_parts = [p for p in parts if p.get("type") == "text"]

        step_num = i + 1
        is_last = (i == len(trace) - 1)
        is_answer = is_last and len(text_parts) > 0 and len(tool_calls) == 0
        is_parallel = len(tool_calls) > 1

        # ── Determine step styling ──
        if is_answer:
            dot_bg = "linear-gradient(135deg,#6366f1,#4f46e5)"
            dot_emoji = "💬"
            title_bg = "rgba(99,102,241,0.08)"
            title_color = "#a5b4fc"
            title_border = "rgba(99,102,241,0.15)"
            step_label = f"⚡ Step {step_num} — Parallel Tools + Final Answer" if is_parallel else f"💬 Step {step_num} — Final Answer"
        elif is_parallel:
            dot_bg = "linear-gradient(135deg,#ec4899,#db2777)"
            dot_emoji = "⚡"
            title_bg = "rgba(236,72,153,0.08)"
            title_color = "#f9a8d4"
            title_border = "rgba(236,72,153,0.15)"
            step_label = f"⚡ Step {step_num} — {len(tool_calls)} Tools Called in Parallel"
        elif tool_calls:
            dot_bg = "linear-gradient(135deg,#f59e0b,#d97706)"
            dot_emoji = "🔧"
            title_bg = "rgba(245,158,11,0.08)"
            title_color = "#fbbf24"
            title_border = "rgba(245,158,11,0.15)"
            step_label = f"🔧 Step {step_num} — Tool Call"
        else:
            dot_bg = "linear-gradient(135deg,#8b5cf6,#7c3aed)"
            dot_emoji = "🧠"
            title_bg = "rgba(139,92,246,0.08)"
            title_color = "#c4b5fd"
            title_border = "rgba(139,92,246,0.15)"
            step_label = f"🧠 Step {step_num} — Reasoning"

        # ── Build inner content ──
        inner_parts = []

        # Tool calls with args
        for tc in tool_calls:
            name = html_lib.escape(tc.get("tool_name", "?"))
            args = _esc(_safe_json(tc.get("args", {}), 400))

            if is_parallel:
                inner_parts.append(f'''
                <div style="background:#0a0f1a;border:1px solid #1a2235;border-radius:10px;overflow:hidden;margin-bottom:8px;">
                    <div style="padding:8px 12px;background:rgba(236,72,153,0.06);border-bottom:1px solid rgba(236,72,153,0.12);font-size:11px;font-weight:700;color:#f9a8d4;display:flex;align-items:center;gap:6px;">
                        <span style="width:18px;height:18px;border-radius:5px;background:rgba(236,72,153,0.2);display:inline-flex;align-items:center;justify-content:center;font-size:9px;">⚡</span>
                        {name}
                    </div>
                    <div style="padding:10px 12px;font-family:'JetBrains Mono',monospace;font-size:11px;color:#94a3b8;white-space:pre-wrap;word-break:break-word;line-height:1.6;max-height:120px;overflow-y:auto;">
                        {args}
                    </div>
                </div>''')
            else:
                inner_parts.append(f'''
                <div style="margin-bottom:10px;">
                    <div style="font-size:11px;font-weight:700;color:#fbbf24;margin-bottom:6px;display:flex;align-items:center;gap:6px;">
                        <span style="width:18px;height:18px;border-radius:5px;background:rgba(245,158,11,0.2);display:inline-flex;align-items:center;justify-content:center;font-size:9px;">🔧</span>
                        Tool Called: {name}
                    </div>
                    <div style="background:#0a0f1a;border:1px solid #1a2235;border-radius:8px;padding:10px 12px;font-family:'JetBrains Mono',monospace;font-size:11px;color:#94a3b8;white-space:pre-wrap;word-break:break-word;line-height:1.6;max-height:150px;overflow-y:auto;">
                        {args}
                    </div>
                </div>''')

        # Tool result
        if tool_result is not None:
            res = _esc(_safe_json(tool_result, 500))
            inner_parts.append(f'''
            <div style="margin-bottom:10px;">
                <div style="font-size:11px;font-weight:700;color:#4ade80;margin-bottom:6px;display:flex;align-items:center;gap:6px;">
                    <span style="width:18px;height:18px;border-radius:5px;background:rgba(34,197,94,0.2);display:inline-flex;align-items:center;justify-content:center;font-size:9px;">📦</span>
                    Tool Result
                </div>
                <div style="background:#0a0f1a;border:1px solid #1a2235;border-radius:8px;padding:10px 12px;font-family:'JetBrains Mono',monospace;font-size:11px;color:#94a3b8;white-space:pre-wrap;word-break:break-word;line-height:1.6;max-height:200px;overflow-y:auto;">
                    {res}
                </div>
            </div>''')

        # Text / thought parts
        for tp in text_parts:
            content = tp.get("content", "").strip()
            if not content:
                continue

            if is_answer:
                safe = _format_agent_text(content)
                inner_parts.append(f'''
                <div style="color:#e2e8f0;font-size:14px;line-height:2;direction:rtl;font-family:'Cairo','Inter',sans-serif;">
                    {safe}
                </div>''')
            else:
                # Reasoning text: formatted with a subtle background to separate paragraphs
                safe = _format_agent_text(content)
                inner_parts.append(f'''
                <div style="color:#c4b5fd;font-size:12px;line-height:1.8;font-style:italic;background:rgba(139,92,246,0.05);padding:12px;border-radius:8px;border-right:3px solid #8b5cf6;margin-bottom:10px;">
                    {safe}
                </div>''')

        inner = ''.join(inner_parts)

        nodes.append(f'''
        <div style="position:relative;margin-bottom:28px;">
            <div style="position:absolute;left:-40px;top:8px;width:36px;height:36px;border-radius:50%;background:{dot_bg};display:flex;align-items:center;justify-content:center;font-size:14px;box-shadow:0 0 0 4px #0B1220;z-index:1;">{dot_emoji}</div>
            <div style="background:#111827;border:1px solid #1f2937;border-radius:14px;overflow:hidden;">
                <div style="padding:10px 16px;background:{title_bg};border-bottom:1px solid {title_border};font-size:12px;font-weight:700;color:{title_color};">
                    {step_label}
                </div>
                <div style="padding:16px 18px;">
                    {inner}
                </div>
            </div>
        </div>''')

    timeline = ''.join(nodes)
    return f'''
    <div style="position:relative;padding-left:44px;">
        <div style="position:absolute;left:17px;top:0;bottom:0;width:2px;background:linear-gradient(180deg,#6366f1 0%,#334155 60%,transparent 100%);border-radius:2px;"></div>
        {timeline}
    </div>'''


def _build_full_html(logs: list) -> str:
    cards = ""
    for log in logs:
        prompt = log.get("user_prompt", "—")
        if len(prompt) > 160:
            prompt = prompt[:157] + "…"
        ts = log.get("timestamp")
        ts_str = ts.strftime("%Y-%m-%d · %H:%M:%S") if isinstance(ts, datetime) else "—"
        trace = log.get("trace", [])
        intent = log.get("intent", "—")
        dialect = log.get("dialect", "—")
        total_steps = len(trace)
        tool_count = log.get("tool_calls_count", 0)

        badges = (
            f'<span style="display:inline-flex;align-items:center;gap:4px;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:600;background:rgba(34,197,94,0.12);color:#4ade80;">💰 ${log.get("total_cost",0):.6f}</span>'
            f'<span style="display:inline-flex;align-items:center;gap:4px;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:600;background:rgba(245,158,11,0.12);color:#fbbf24;">⚡ {log.get("latency_ms",0):.0f}ms</span>'
            f'<span style="display:inline-flex;align-items:center;gap:4px;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:600;background:rgba(99,102,241,0.12);color:#a5b4fc;">🔢 {log.get("llm_tokens_in",0):,}in / {log.get("llm_tokens_out",0):,}out</span>'
            f'<span style="display:inline-flex;align-items:center;gap:4px;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:600;background:rgba(236,72,153,0.12);color:#f9a8d4;">🛠 {tool_count} tools</span>'
            f'<span style="display:inline-flex;align-items:center;gap:4px;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:600;background:rgba(139,92,246,0.12);color:#c4b5fd;">🎯 {html_lib.escape(str(intent))}</span>'
            f'<span style="display:inline-flex;align-items:center;gap:4px;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:600;background:rgba(59,130,246,0.12);color:#93c5fd;">🗣️ {html_lib.escape(str(dialect))}</span>'
            f'<span style="display:inline-flex;align-items:center;gap:4px;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:600;background:rgba(255,255,255,0.05);color:#64748b;">🕒 {ts_str}</span>'
        )

        trace_html = _render_trace_steps(trace)
        safe_prompt = html_lib.escape(prompt)

        cards += f'''
        <div style="
            background: #0B1220;
            border: 1px solid #1e293b;
            border-radius: 20px;
            overflow: hidden;
            margin-bottom: 32px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.2);
        ">
            <div style="
                background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                padding: 22px 26px;
                border-bottom: 1px solid #1e293b;
            ">
                <div style="color:#e2e8f0;font-size:15px;line-height:1.8;direction:rtl;margin-bottom:14px;font-family:'Cairo','Inter',sans-serif;">
                    💬 {safe_prompt}
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:7px;">{badges}</div>
            </div>
            <div style="padding:28px 28px 24px;">
                {trace_html}
            </div>
        </div>'''

    return f'''<!DOCTYPE html>
<html>
<head>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; font-family:'Cairo','Inter',system-ui,sans-serif; }}
        body {{ background:#060a13; padding:20px 24px; color:#e2e8f0; }}
        div[style*="overflow-y:auto"]::-webkit-scrollbar {{ width:4px; }}
        div[style*="overflow-y:auto"]::-webkit-scrollbar-thumb {{ background:#334155; border-radius:99px; }}
        div[style*="overflow-y:auto"]::-webkit-scrollbar-track {{ background:transparent; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
    </style>
</head>
<body>{cards}</body>
</html>'''


def show():
    if st.session_state.get("role") != "admin":
        st.error("This page is available for admins only.")
        return

    page_header("🔍 Agent Trace Viewer", "See exactly how the agent thinks and acts — step by step")

    cols_db = safe_get_collections()
    if cols_db is None:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
            <div style="font-size:64px;margin-bottom:16px;">🔌</div>
            <div style="font-size:20px;font-weight:700;color:#f1f5f9;margin-bottom:8px;">Database Unreachable</div>
            <div style="font-size:14px;color:#94a3b8;">Could not connect to MongoDB.</div>
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
            <div style="font-size:64px;margin-bottom:16px;">🔍</div>
            <div style="font-size:20px;font-weight:700;color:#f1f5f9;margin-bottom:8px;">No Trace Data Yet</div>
            <div style="font-size:14px;color:#94a3b8;">Traces will appear here as users interact with the agent.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Filters ──
    f1, f2, f3 = st.columns([1, 1, 1])
    with f1:
        users = sorted(set(l.get("user_id", "anonymous") for l in all_logs))
        sel_user = st.selectbox("User", ["All"] + users, key="trace_user")
    with f2:
        intents = sorted(set(l.get("intent", "") for l in all_logs if l.get("intent")))
        sel_intent = st.selectbox("Intent", ["All"] + intents, key="trace_intent")
    with f3:
        search_q = st.text_input("Search prompt...", key="trace_search")

    filtered = all_logs
    if sel_user != "All":
        filtered = [l for l in filtered if l.get("user_id") == sel_user]
    if sel_intent != "All":
        filtered = [l for l in filtered if l.get("intent") == sel_intent]
    if search_q.strip():
        sq = search_q.strip().lower()
        filtered = [l for l in filtered if sq in l.get("user_prompt", "").lower()]

    st.caption(f"Showing {len(filtered)} traces")
    show_count = st.slider("Traces to show", 1, len(filtered), min(10, len(filtered)), key="trace_count")

    full_html = _build_full_html(filtered[:show_count])
    est_height = min(len(filtered[:show_count]) * 650, 8000)
    components.html(full_html, height=est_height, scrolling=True)