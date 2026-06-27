"""
PAGE — Sequential vs Parallel Performance Comparison for Admin.
All visuals in a single self-contained iframe — no clipping.
"""
import asyncio
import sys
import html as html_lib
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime

from core.db import safe_get_collections
from core.styles import page_header

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

BENCHMARK_PROMPTS = [
    "عندكم كورسات بيثون؟",
    "كام سعر دبلومة الـ SOC وايه محتوياتها؟",
    "ايه الفرق بين مسار الداتا ساينس والداتا اناليسيس من حيث المحتوى والمهارات؟",
    "فين ألاقي تفاصيل دبلومة الـ AI ومستوى الدخول بتاعتها؟",
    "عايز اسجل دلوقتي، اسمي أحمد محمود، رقمي +201012345678، من القاهرة، عايز أعرف سعر دبلومة الـ Fullstack قبل ما أبدأ",
]


def _load_pairs():
    cols = safe_get_collections()
    if cols is None:
        return []
    pairs = []
    for i in range(1, 6):
        sl = cols["usage_logs"].find_one({"chat_id": f"baseline_seq_{i}"})
        pl = cols["usage_logs"].find_one({"chat_id": f"optimized_{i}"})
        pairs.append({
            "prompt": (sl or pl or {}).get("user_prompt", BENCHMARK_PROMPTS[i - 1]),
            "seq_cost": sl.get("total_cost", 0) if sl else None,
            "par_cost": pl.get("total_cost", 0) if pl else None,
            "seq_tokens": sl.get("llm_tokens_in", 0) if sl else None,
            "par_tokens": pl.get("llm_tokens_in", 0) if pl else None,
            "seq_time": sl.get("latency_ms", 0) if sl else None,
            "par_time": pl.get("latency_ms", 0) if pl else None,
            "seq_tools": sl.get("tool_calls_count", 0) if sl else None,
            "par_tools": pl.get("tool_calls_count", 0) if pl else None,
            "has_seq": sl is not None,
            "has_par": pl is not None,
        })
    return pairs


async def _run_bench():
    from core.agent import (
        kayfa_agent, RAGDeps, extract_trace_steps,
        calculate_cost, GROQ_MODEL, detect_intent, detect_dialect,
        create_sequential_agent,
    )
    cols = safe_get_collections()
    if cols is None:
        return {"errors": ["Database unreachable"]}
    sa = create_sequential_agent()
    res = {"errors": []}
    for i, prompt in enumerate(BENCHMARK_PROMPTS):
        intent = detect_intent(prompt)
        dialect = detect_dialect(prompt)
        deps = RAGDeps(intent=intent, user_language="ar", dialect=dialect)
        for mode, agent, prefix in [("seq", sa, "baseline_seq"), ("par", kayfa_agent, "optimized")]:
            try:
                import time as _t
                t0 = _t.perf_counter()
                r = await agent.run(prompt, deps=deps)
                lat = (_t.perf_counter() - t0) * 1000
                u = r.usage
                cost = calculate_cost(GROQ_MODEL, u.input_tokens, u.output_tokens)
                trace = extract_trace_steps(r)
                tools = sum(1 for s in trace if any(p["type"] == "tool_call" for p in s.get("parts", [])))
                cols["usage_logs"].insert_one({
                    "chat_id": f"{prefix}_{i+1}", "user_id": "benchmark_user",
                    "timestamp": datetime.utcnow(), "user_prompt": prompt, "final_output": r.output,
                    "llm_model": GROQ_MODEL, "llm_tokens_in": u.input_tokens, "llm_tokens_out": u.output_tokens,
                    "llm_cost": cost, "emb_model": "FAISS/BGE-M3 (Local)", "emb_cost": 0.0,
                    "total_cost": cost, "tool_calls_count": tools, "latency_ms": lat,
                    "trace": trace, "intent": intent, "dialect": dialect,
                })
            except Exception as e:
                res["errors"].append(f"{'Sequential' if mode == 'seq' else 'Parallel'} Test {i+1}: {str(e)}")
    return res


# ════════════════════════════════════════════════════════════════
# Build the ENTIRE visual page as one HTML string
# ════════════════════════════════════════════════════════════════
def _build_results_html(complete: list) -> str:
    tsc = sum(p["seq_cost"] for p in complete)
    tpc = sum(p["par_cost"] for p in complete)
    tstm = sum(p["seq_time"] for p in complete)
    tptm = sum(p["par_time"] for p in complete)
    tst = sum(p["seq_tokens"] for p in complete)
    tpt = sum(p["par_tokens"] for p in complete)
    cs = tsc - tpc
    pct_c = (cs / tsc * 100) if tsc > 0 else 0
    ts = tstm - tptm
    pct_t = (ts / tstm * 100) if tstm > 0 else 0
    tk = tst - tpt
    pct_k = (tk / tst * 100) if tst > 0 else 0
    avg_s = tsc / len(complete)
    avg_p = tpc / len(complete)
    bar = min(max(pct_c, 0), 100)

    # ── Hero Cards ──
    def _hero(icon, value, label, sub, ck):
        t = {"green": ("linear-gradient(160deg,#14432a,#0a2e1a)", "#4ade80", "rgba(74,222,128,0.15)"),
             "amber": ("linear-gradient(160deg,#452c0a,#2d1d06)", "#fbbf24", "rgba(251,191,36,0.15)"),
             "blue":  ("linear-gradient(160deg,#1e3a5f,#0f2440)", "#60a5fa", "rgba(96,165,250,0.15)"),
             "pink":  ("linear-gradient(160deg,#4a1942,#2d0f2a)", "#fb7185", "rgba(251,113,133,0.15)")
             }.get(ck, ("linear-gradient(160deg,#1e3a5f,#0f2440)", "#60a5fa", "rgba(96,165,250,0.15)"))
        bg, ac, gl = t
        return f'''<div style="background:{bg};border:1px solid rgba(255,255,255,0.06);border-radius:20px;padding:28px 20px 24px;text-align:center;position:relative;overflow:hidden;">
<div style="position:absolute;top:-20px;right:-20px;width:90px;height:90px;background:radial-gradient(circle,{gl} 0%,transparent 70%);border-radius:50%;"></div>
<div style="width:48px;height:48px;margin:0 auto 14px;border-radius:14px;background:{gl};border:1px solid {ac}22;display:flex;align-items:center;justify-content:center;font-size:22px;">{icon}</div>
<div style="font-size:28px;font-weight:800;color:#f1f5f9;letter-spacing:-1px;margin-bottom:6px;">{value}</div>
<div style="font-size:11px;font-weight:700;color:{ac}99;text-transform:uppercase;letter-spacing:1.5px;">{label}</div>
<div style="font-size:11px;color:#64748b;margin-top:4px;">{sub}</div>
<div style="position:absolute;bottom:0;left:20%;right:20%;height:2px;background:linear-gradient(90deg,transparent,{ac}66,transparent);"></div></div>'''

    # ── Table ──
    rows = ""
    for i, p in enumerate(complete):
        pr = html_lib.escape(p.get("prompt", "—"))
        if len(pr) > 80: pr = pr[:77] + "…"
        sc, pc = p["seq_cost"], p["par_cost"]
        st_, pt_ = p["seq_tokens"], p["par_tokens"]
        stm, ptm = p["seq_time"], p["par_time"]
        stl, ptl = p["seq_tools"], p["par_tools"]

        def _c(a, b):
            return "color:#4ade80;font-weight:700;" if a - b > 0 else ("color:#f87171;font-weight:700;" if a - b < 0 else "color:#64748b;")
        def _fc(v): return f"${v:.6f}" if isinstance(v, (int, float)) else "N/A"
        def _fi(v): return f"{v:,}" if isinstance(v, (int, float)) else "N/A"
        def _fd(v): return f"{v:,.0f}" if isinstance(v, (int, float)) else "N/A"

        bg = "#0c1322" if i % 2 == 0 else "#0f172a"
        rows += f'''<tr style="background:{bg};">
<td style="text-align:center;font-weight:700;color:#f1f5f9;padding:14px 8px;border-bottom:1px solid rgba(30,41,59,.5);font-size:13px;">{i+1}</td>
<td style="direction:rtl;max-width:220px;font-size:11px;color:#94a3b8;padding:14px 10px;border-bottom:1px solid rgba(30,41,59,.5);line-height:1.6;">{pr}</td>
<td style="padding:14px 8px;border-bottom:1px solid rgba(30,41,59,.5);font-size:11px;color:#fca5a5;font-family:'JetBrains Mono',monospace;">{_fc(sc)}</td>
<td style="padding:14px 8px;border-bottom:1px solid rgba(30,41,59,.5);font-size:11px;color:#86efac;font-family:'JetBrains Mono',monospace;">{_fc(pc)}</td>
<td style="text-align:center;padding:14px 8px;border-bottom:1px solid rgba(30,41,59,.5);font-size:11px;font-family:'JetBrains Mono',monospace;{_c(sc,pc)}">{_fc(sc-pc)}</td>
<td style="padding:14px 8px;border-bottom:1px solid rgba(30,41,59,.5);font-size:11px;color:#cbd5e1;font-family:'JetBrains Mono',monospace;">{_fi(st_)}</td>
<td style="padding:14px 8px;border-bottom:1px solid rgba(30,41,59,.5);font-size:11px;color:#cbd5e1;font-family:'JetBrains Mono',monospace;">{_fi(pt_)}</td>
<td style="text-align:center;padding:14px 8px;border-bottom:1px solid rgba(30,41,59,.5);font-size:11px;font-family:'JetBrains Mono',monospace;{_c(st_,pt_)}">{_fi(st_-pt_)}</td>
<td style="padding:14px 8px;border-bottom:1px solid rgba(30,41,59,.5);font-size:11px;color:#fca5a5;font-family:'JetBrains Mono',monospace;">{_fd(stm)}ms</td>
<td style="padding:14px 8px;border-bottom:1px solid rgba(30,41,59,.5);font-size:11px;color:#86efac;font-family:'JetBrains Mono',monospace;">{_fd(ptm)}ms</td>
<td style="text-align:center;padding:14px 8px;border-bottom:1px solid rgba(30,41,59,.5);font-size:11px;font-family:'JetBrains Mono',monospace;{_c(stm,ptm)}">{_fd(stm-ptm)}ms</td>
<td style="text-align:center;padding:14px 8px;border-bottom:1px solid rgba(30,41,59,.5);font-size:12px;color:#cbd5e1;">{_fi(stl)}</td>
<td style="text-align:center;padding:14px 8px;border-bottom:1px solid rgba(30,41,59,.5);font-size:12px;color:#cbd5e1;">{_fi(ptl)}</td>
<td style="text-align:center;padding:14px 8px;border-bottom:1px solid rgba(30,41,59,.5);font-size:12px;font-family:'JetBrains Mono',monospace;{_c(stl,ptl)}">{_fi(stl-ptl)}</td></tr>'''

    # ── Enhancement cards ──
    def _ec(icon, title, desc, accent):
        return f'''<div style="background:#111827;border:1px solid #1f2937;border-radius:14px;padding:20px;">
<div style="width:44px;height:44px;border-radius:12px;background:{accent}15;border:1px solid {accent}22;display:flex;align-items:center;justify-content:center;font-size:20px;margin-bottom:12px;">{icon}</div>
<div style="font-size:14px;font-weight:700;color:{accent};margin-bottom:6px;">{title}</div>
<div style="font-size:12px;color:#94a3b8;line-height:1.7;">{desc}</div></div>'''

    # ── Assemble everything into ONE page ──
    return f'''
    <!-- HERO CARDS -->
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:32px;">
        {_hero("💰", f"${cs:.6f}", "Total Cost Saved", f"{pct_c:.1f}% reduction", "green")}
        {_hero("⚡", f"{ts:,.0f}ms", "Total Time Saved", f"{pct_t:.1f}% faster", "amber")}
        {_hero("🔢", f"{tk:,}", "Tokens Saved", f"{pct_k:.1f}% reduction", "blue")}
        {_hero("📉", f"${avg_s:.6f} → ${avg_p:.6f}", "Avg Cost / Test", f"${avg_s-avg_p:.6f} saved", "pink")}
    </div>

    <!-- GRAND TOTAL -->
    <div style="background:linear-gradient(135deg,#0f172a,#1e293b);border:2px solid #22c55e;border-radius:24px;padding:40px;text-align:center;position:relative;overflow:hidden;margin-bottom:32px;">
        <div style="position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:radial-gradient(circle,rgba(34,197,94,.06) 0%,transparent 70%);"></div>
        <div style="position:relative;">
            <div style="font-size:13px;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">💰 Total Cost Savings</div>
            <div style="font-size:52px;font-weight:800;color:#4ade80;letter-spacing:-2px;margin:8px 0;">${cs:.6f}</div>
            <div style="font-size:18px;color:#f1f5f9;margin-bottom:8px;">
                <span style="color:#fca5a5;">🔴 Sequential: ${tsc:.6f}</span>
                <span style="color:#64748b;margin:0 12px;">→</span>
                <span style="color:#86efac;">🟢 Parallel: ${tpc:.6f}</span>
            </div>
            <div style="font-size:13px;color:#64748b;margin-bottom:20px;">{pct_c:.1f}% reduction in LLM cost</div>
            <div style="width:100%;max-width:500px;margin:0 auto;height:10px;background:#1e293b;border-radius:99px;overflow:hidden;">
                <div style="height:100%;width:{bar}%;background:linear-gradient(90deg,#22c55e,#10b981);border-radius:99px;"></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:28px;">
                <div style="background:rgba(255,255,255,.03);border:1px solid #1e293b;border-radius:16px;padding:22px;">
                    <div style="font-size:28px;margin-bottom:6px;">⚡</div>
                    <div style="font-size:26px;font-weight:800;color:#fbbf24;letter-spacing:-1px;">{ts:,.0f}ms</div>
                    <div style="font-size:12px;color:#94a3b8;margin-top:6px;">Time Saved</div>
                    <div style="font-size:11px;color:#4ade80;font-weight:600;margin-top:2px;">{pct_t:.1f}% faster</div>
                    <div style="font-size:10px;color:#64748b;margin-top:4px;font-family:'JetBrains Mono',monospace;">{tstm:,.0f}ms → {tptm:,.0f}ms</div>
                </div>
                <div style="background:rgba(255,255,255,.03);border:1px solid #1e293b;border-radius:16px;padding:22px;">
                    <div style="font-size:28px;margin-bottom:6px;">🔢</div>
                    <div style="font-size:26px;font-weight:800;color:#a5b4fc;letter-spacing:-1px;">{tk:,}</div>
                    <div style="font-size:12px;color:#94a3b8;margin-top:6px;">Tokens Saved</div>
                    <div style="font-size:11px;color:#4ade80;font-weight:600;margin-top:2px;">{pct_k:.1f}% reduction</div>
                    <div style="font-size:10px;color:#64748b;margin-top:4px;font-family:'JetBrains Mono',monospace;">{tst:,} → {tpt:,}</div>
                </div>
            </div>
        </div>
    </div>

    <!-- TABLE -->
    <div style="background:#0B1220;border:1px solid #1e293b;border-radius:20px;overflow:hidden;margin-bottom:32px;">
        <div style="padding:20px 24px;border-bottom:1px solid #1e293b;font-size:16px;font-weight:700;color:#f1f5f9;">📊 Detailed Test-by-Test Comparison</div>
        <div style="overflow-x:auto;">
            <table style="width:100%;border-collapse:collapse;min-width:1100px;">
                <thead><tr style="background:#0f172a;">
                    <th style="padding:12px 8px;text-align:center;font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #1e293b;">#</th>
                    <th style="padding:12px 10px;text-align:right;font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #1e293b;">Prompt</th>
                    <th style="padding:12px 8px;text-align:center;font-size:10px;font-weight:700;color:#fca5a5;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #1e293b;">🔴 Seq $</th>
                    <th style="padding:12px 8px;text-align:center;font-size:10px;font-weight:700;color:#86efac;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #1e293b;">🟢 Par $</th>
                    <th style="padding:12px 8px;text-align:center;font-size:10px;font-weight:700;color:#4ade80;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #1e293b;">Δ Cost</th>
                    <th style="padding:12px 8px;text-align:center;font-size:10px;font-weight:700;color:#fca5a5;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #1e293b;">🔴 Seq Tok</th>
                    <th style="padding:12px 8px;text-align:center;font-size:10px;font-weight:700;color:#86efac;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #1e293b;">🟢 Par Tok</th>
                    <th style="padding:12px 8px;text-align:center;font-size:10px;font-weight:700;color:#4ade80;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #1e293b;">Δ Tok</th>
                    <th style="padding:12px 8px;text-align:center;font-size:10px;font-weight:700;color:#fca5a5;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #1e293b;">🔴 Seq ms</th>
                    <th style="padding:12px 8px;text-align:center;font-size:10px;font-weight:700;color:#86efac;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #1e293b;">🟢 Par ms</th>
                    <th style="padding:12px 8px;text-align:center;font-size:10px;font-weight:700;color:#4ade80;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #1e293b;">Δ ms</th>
                    <th style="padding:12px 8px;text-align:center;font-size:10px;font-weight:700;color:#cbd5e1;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #1e293b;">🔴 Tools</th>
                    <th style="padding:12px 8px;text-align:center;font-size:10px;font-weight:700;color:#cbd5e1;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #1e293b;">🟢 Tools</th>
                    <th style="padding:12px 8px;text-align:center;font-size:10px;font-weight:700;color:#4ade80;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #1e293b;">Δ Tools</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>

    <!-- ENHANCEMENT LEGEND -->
    <div style="background:#0B1220;border:1px solid #1e293b;border-radius:20px;padding:28px;">
        <div style="font-size:16px;font-weight:700;color:#f1f5f9;margin-bottom:20px;">🧩 Enhancements Applied in Parallel Mode</div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;">
            {_ec("⚡", "Parallel Tool Calling", "Independent tools called in the same LLM turn instead of chained sequentially. Reduces round-trips and repeated context.", "#fbbf24")}
            {_ec("📝", "Smaller Docstrings", "Tool descriptions trimmed to essentials. Less token overhead per tool call in the system prompt.", "#a5b4fc")}
            {_ec("🧠", "LRU Cache + Indexes", "Courses & roadmaps pre-indexed in memory at startup. O(1) lookups instead of scanning JSON arrays.", "#4ade80")}
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px;">
            {_ec("🎯", "Dynamic Intent Strategy", "System prompt adapts per-user-intent (browsing, comparing, price-sensitive, hesitant, ready-to-enroll).", "#c4b5fd")}
            {_ec("🗣", "Dialect Detection", "Egyptian, Saudi, Levantine, or MSA detected via regex — injected as a short dialect rule.", "#93c5fd")}
        </div>
    </div>'''


def _build_prompts_html() -> str:
    cards = ""
    for i, p in enumerate(BENCHMARK_PROMPTS):
        cards += f'''<div style="background:#111827;border:1px solid #1f2937;border-radius:12px;padding:14px 18px;direction:rtl;display:flex;align-items:flex-start;gap:12px;">
<span style="flex-shrink:0;width:26px;height:26px;border-radius:8px;background:linear-gradient(135deg,#6366f1,#4f46e5);color:white;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;">{i+1}</span>
<span style="color:#e2e8f0;font-size:13px;line-height:1.7;">{html_lib.escape(p)}</span></div>'''
    return f'''<div style="font-size:13px;color:#94a3b8;margin-bottom:14px;">The following 5 prompts will be tested with <b style="color:#fca5a5;">sequential</b> (one tool at a time) and <b style="color:#86efac;">parallel</b> (all independent tools at once) tool calling:</div>
<div style="display:flex;flex-direction:column;gap:8px;">{cards}</div>'''


def show():
    if st.session_state.get("role") != "admin":
        st.error("This page is available for admins only.")
        return

    page_header("⚡ Performance Benchmark", "Sequential vs Parallel Tool Calling — Before & After Optimization")

    pairs = _load_pairs()
    has_seq = any(p["has_seq"] for p in pairs)
    has_par = any(p["has_par"] for p in pairs)

    # ── Prompts preview (small, self-contained) ──
    components.html(
        f'''<!DOCTYPE html><html><head>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box;font-family:'Cairo','Inter',system-ui,sans-serif;}}body{{background:#060a13;color:#e2e8f0;padding:0;}}</style>
</head><body><div style="padding:0;">{_build_prompts_html()}</div></body></html>''',
        height=340, scrolling=False
    )

    # ── Status (native Streamlit) ──
    if has_seq and has_par:
        st.success("✅ Benchmark complete — both sequential and parallel results available")
    elif has_seq:
        st.warning("⚠️ Only sequential results found — run again for parallel")
    elif has_par:
        st.warning("⚠️ Only parallel results found — run again for sequential")

    # ── Run button (native Streamlit) ──
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("🚀 Run Benchmark", type="primary", use_container_width=True, key="run_bench_btn"):
            st.session_state["bench_running"] = True
            st.session_state["bench_errors"] = []
    with c2:
        st.markdown('<div style="padding-top:8px;font-size:12px;color:#64748b;">Runs 5 prompts × 2 agents = 10 LLM calls. Takes ~1-2 minutes.</div>', unsafe_allow_html=True)

    if st.session_state.get("bench_running"):
        with st.spinner("Running benchmarks..."):
            try:
                br = asyncio.run(_run_bench())
                st.session_state["bench_running"] = False
                if br["errors"]:
                    st.session_state["bench_errors"] = br["errors"]
                st.rerun()
            except Exception as e:
                st.session_state["bench_running"] = False
                st.error(f"Benchmark failed: {e}")
                st.rerun()

    for err in st.session_state.get("bench_errors", []):
        st.error(f"❌ {err}")

    # ── Results ──
    pairs = _load_pairs()
    complete = [p for p in pairs if p["has_seq"] and p["has_par"]]

    if not complete:
        st.markdown("""
        <div style="text-align:center;padding:80px 20px;">
            <div style="font-size:72px;margin-bottom:20px;">🔬</div>
            <div style="font-size:22px;font-weight:800;color:#0f172a;margin-bottom:10px;">No Benchmark Results Yet</div>
            <div style="font-size:14px;color:#64748b;line-height:1.8;">Click "🚀 Run Benchmark" above to test all 5 prompts.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── ALL results in ONE single iframe ──
    results_body = _build_results_html(complete)
    components.html(
        f'''<!DOCTYPE html><html><head>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box;font-family:'Cairo','Inter',system-ui,sans-serif;}}
body{{background:#060a13;color:#e2e8f0;padding:24px;}}
div[style*="overflow-x:auto"]::-webkit-scrollbar{{height:6px;width:6px;}}
div[style*="overflow-x:auto"]::-webkit-scrollbar-thumb{{background:#334155;border-radius:99px;}}
</style>
</head><body>{results_body}</body></html>''',
        height=2200, scrolling=True
    )