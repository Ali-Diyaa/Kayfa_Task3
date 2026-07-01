System Architecture:
┌─────────────────────────────────────────────────────────────────────────┐
│                        STREAMLIT APP (app.py)                          │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │  Auth Layer   │  │ Model Pre-   │  │       Page Router            │  │
│  │ signup/login  │→ │ loader screen│→ │ (role-based navigation)      │  │
│  │ user | admin  │  │ BGE-M3+FAISS│  │                              │  │
│  └──────┬───────┘  └──────────────┘  └────────┬─────────────────────┘  │
│         │                                     │                        │
│         ▼                                     ▼                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     VIEWS (role-protected)                       │   │
│  │                                                                  │   │
│  │  👤 USER                              🛡️ ADMIN                  │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  │   │
│  │  │ 💬 Chat    │  │ 🎯 CRM     │  │ 📊 Cost    │  │ 🔍 Agent │  │   │
│  │  │ Agent UI   │  │ Leads Page │  │ Analytics  │  │ Traces   │  │   │
│  │  │ (RTL/MLTR) │  │ (Arabic    │  │ (Plotly)   │  │ Replay   │  │   │
│  │  │            │  │  tickets)  │  │            │  │ Steps    │  │   │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └────┬─────┘  │   │
│  │        │               │               │               │         │   │
│  └────────┼───────────────┼───────────────┼───────────────┼─────────┘   │
│           │               │               │               │             │
│           ▼               ▼               ▼               ▼             │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    CORE ENGINE (agent.py)                        │   │
│  │                                                                  │   │
│  │  User Message                                                    │   │
│  │       │                                                          │   │
│  │       ▼                                                          │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │   │
│  │  │ Intent       │    │ Dialect      │    │ Dynamic System   │   │   │
│  │  │ Detection    │───→│ Detection    │───→│ Prompt Builder   │   │   │
│  │  │ (5 intents)  │    │ (4 dialects) │    │ BASE + strategy  │   │   │
│  │  └──────────────┘    └──────────────┘    │ + dialect rule   │   │   │
│  │                                           └────────┬─────────┘   │   │
│  │                                                    │              │   │
│  │                                                    ▼              │   │
│  │  ┌──────────────────────────────────────────────────────────┐    │   │
│  │  │              PYDANTIC-AI AGENT (Groq LLM)               │    │   │
│  │  │                                                          │    │   │
│  │  │  ┌─────────┐ ┌──────────────┐ ┌──────────────────────┐  │    │   │
│  │  │  │search_  │ │get_courses_  │ │get_roadmap_details_  │  │    │   │
│  │  │  │knowledge│ │by_track/     │ │tool / list_all_      │  │    │   │
│  │  │  │_base    │ │by_keyword    │ │diplomas_tool         │  │    │   │
│  │  │  └────┬────┘ └──────┬───────┘ └──────────┬───────────┘  │    │   │
│  │  │       │             │                     │              │    │   │
│  │  │       ▼             ▼                     ▼              │    │   │
│  │  │  ┌─────────────────────────────────────────────────┐     │    │   │
│  │  │  │         PARALLEL TOOL EXECUTION                 │     │    │   │
│  │  │  │  Independent calls batched in ONE turn          │     │    │   │
│  │  │  │  (context billed once instead of many)          │     │    │   │
│  │  │  └─────────────────────┬───────────────────────────┘     │    │   │
│  │  │                        │                                 │    │   │
│  │  │  ┌─────────────┐ ┌────────────────┐                     │    │   │
│  │  │  │get_exact_   │ │capture_lead    │                     │    │   │
│  │  │  │pricing      │ │(→ CRM ticket)  │                     │    │   │
│  │  │  └─────────────┘ └────────────────┘                     │    │   │
│  │  └──────────────────────────┬───────────────────────────────┘    │   │
│  │                             │                                    │   │
│  │                             ▼                                    │   │
│  │  ┌──────────────────────────────────────────────────────────┐    │   │
│  │  │           USAGE LOGGING (per model call)                 │    │   │
│  │  │                                                          │    │   │
│  │  │  • LLM tokens in/out + cost (Groq pricing)              │    │   │
│  │  │  • Embedding cost (BGE-M3 local = $0)                   │    │   │
│  │  │  • Trace steps: think → tool_call → tool_result         │    │   │
│  │  │  • Intent, dialect, latency, tool count                  │    │   │
│  │  │  • Stamped with chat_id + user_id                        │    │   │
│  │  └──────────────────────────┬───────────────────────────────┘    │   │
│  │                             │                                    │   │
│  └─────────────────────────────┼────────────────────────────────────┘   │
│                                │                                        │
│                                ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      MONGODB (Atlas)                             │   │
│  │                                                                  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐ │   │
│  │  │  users   │ │ tickets  │ │conversat-│ │ usage_   │ │count-│ │   │
│  │  │          │ │ (CRM)    │ │  ions    │ │  logs    │ │ ers  │ │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────┘ │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘

Agent Flow — Single Message Lifecycle:
User sends: "سعر دبلومة الـ SOC كام؟ وهل تنفع لحد مبتدئ زيي؟"
                          │
                          ▼
                ┌─────────────────────┐
                │   detect_intent()   │────→ "price_sensitive"
                │   detect_dialect()  │────→ "العربية — اللهجة المصرية"
                └─────────┬───────────┘
                          │
                          ▼
                ┌─────────────────────┐
                │  Build RAGDeps:     │
                │  intent, language,  │
                │  dialect            │
                └─────────┬───────────┘
                          │
                          ▼
                ┌─────────────────────────────┐
                │  Dynamic System Prompt:     │
                │  BASE_PROMPT                │
                │  + BUDGET-AWARE strategy    │
                │  + Egyptian dialect rule    │
                │  + Parallel calling rule    │
                └─────────┬───────────────────┘
                          │
                          ▼
                ┌─────────────────────┐
                │ Load chat history   │
                │ (last 20 messages)  │
                └─────────┬───────────┘
                          │
                          ▼
            ┌───────────────────────────────┐
            │    PYDANTIC-AI AGENT RUN      │
            │                               │
            │  Turn 1: LLM decides tools    │
            │  ┌──────────────────────────┐ │
            │  │ PARALLEL TOOL CALLS:     │ │
            │  │ • get_exact_pricing      │ │
            │  │   ("SOC")               │ │
            │  │ • get_roadmap_details_   │ │
            │  │   tool("SOC diploma")   │ │
            │  └──────────┬───────────────┘ │
            │             │                 │
            │             ▼                 │
            │  Turn 2: LLM receives results │
            │  + generates final answer      │
            └──────────────┬────────────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  extract_trace()    │──→ [think, tool_call,
                │                     │     tool_result, final]
                └─────────┬───────────┘
                          │
                          ▼
                ┌─────────────────────┐
                │  Calculate cost:    │
                │  input_tokens ×     │
                │    $0.15/1M         │
                │  output_tokens ×    │
                │    $0.60/1M         │
                │  emb_cost = $0      │
                │  (local BGE-M3)     │
                └─────────┬───────────┘
                          │
                          ▼
                ┌─────────────────────┐
                │  Write to MongoDB:  │
                │  • usage_logs       │
                │    (tokens, cost,   │
                │     trace, intent)  │
                │  • conversations    │
                │    (chat history)   │
                └─────────┬───────────┘
                          │
                          ▼
                ┌─────────────────────┐
                │  clean_for_user()   │
                │  Strip markdown,    │
                │  append sources     │
                └─────────┬───────────┘
                          │
                          ▼
            "دبلومة الـ SOC مناسبة تمامًا للمبتدئين،
             ومدّتها ٥ شهور لايف. سعرها $250.
             المصدر: kayfa_soc_diploma.md,
                     kayfa_paid_educational_tracks.md"


Benchmark:
┌──────────────────┬──────────────────┐
│  Sequential      │  Optimized       │
│  (one tool/turn) │  (parallel)      │
├──────────────────┼──────────────────┤
│  3 model turns   │  2 model turns   │
│  12,400 tokens   │  8,400 tokens    │
│  $0.00389        │  $0.00238        │
│  8.2s latency    │  3.1s latency    │
└──────────────────┴──────────────────┘
│  Savings: ~39% cost, ~62% latency   │


Installation:
# Clone the repository
git clone https://github.com/<your-username>/kayfa-ai-sales-agent.git
cd kayfa-ai-sales-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt


Environment Setup:
MONGODB_URI=mongodb+srv://<user>:<pass>@cluster.mongodb.net/
GROQ_API_KEY=gsk_...