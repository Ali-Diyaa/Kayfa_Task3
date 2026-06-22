# Kayfa AI Sales Agent — Console

Two-page Streamlit app for the Kayfa sales chatbot:

1. **الشات بوت (Chat)** — visitors talk to the AI sales agent. Bilingual
   (Arabic dialects + English), grounded answers, lead capture, and
   per-user memory stored in MongoDB.
2. **CRM Leads** — admins only. Every captured lead shows up as a
   collapsible card with full details, in Arabic/RTL.

Login is required for both. Roles (`user` / `admin`) live in MongoDB,
not in the app — there is no "become admin" button anywhere in the UI
on purpose (see *Creating an admin* below).

---

## 1. Install

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure

```bash
cp .env.example .env
```

Fill in `.env`:
- `GROQ_API_KEY` — your Groq key (the agent runs on `groq:openai/gpt-oss-120b`).
- `MONGODB_URI` — local Mongo (`mongodb://localhost:27017`) or an Atlas
  connection string.

## 3. Drop in your brand assets & knowledge base

- `assets/kayfa_logo.png` — your logo. It's used in the sidebar AND as
  the chatbot's avatar next to its replies.
- `data/json/kayfa_courses.json`, `data/json/kayfa_roadmaps.json` —
  copy these from your existing notebook setup.
- `data/text/*.md` — your diploma pitches, FAQs, policies, etc.
- `data/data_summary.md` — replace the placeholder with your real map
  of the knowledge base.

## 4. Build the semantic search index (one-time, run again after content changes)

```bash
python scripts/build_index.py
```

This embeds everything in `data/text/*.md` + the courses JSON into
`data/faiss_index.bin` / `data/faiss_metadata.pkl`. The app only reads
this file at runtime — it never rebuilds it on a page load.

## 5. Create your first admin

```bash
python scripts/create_admin.py
```

Prompts for a username/password and writes `role: "admin"` straight
into MongoDB. Regular visitors who sign up through the app's "حساب
جديد" tab always get `role: "user"` and never see the CRM page.

## 6. Run

```bash
streamlit run app.py
```

---

## How the pieces fit together

```
app.py                  → auth gate + role-based navigation (st.navigation)
core/
  db.py                 → shared MongoDB client/collections
  auth.py                → bcrypt hashing, login/register
  crm_models.py          → CRMTicket schema, phone validation, save/list tickets
  intent.py              → intent detection, Arabic dialect detection, RTL check
  knowledge_base.py      → course/roadmap catalog + FAISS semantic search
  chat_memory.py         → per-user chat history (Mongo `conversations` collection)
  agent.py                → the pydantic-ai Agent, its tools, and the orchestrator
  styles.py               → shared Kayfa-brand CSS
views/
  page_chat.py            → Page 1 UI (quick prompts, RTL/LTR bubbles, logo avatar)
  page_crm.py              → Page 2 UI (admin-only, ticket dropdown cards)
scripts/
  build_index.py          → offline FAISS index builder
  create_admin.py         → the only way to grant the "admin" role
```

## MongoDB collections (db: `kayfa_crm`)

| Collection      | Purpose                                                        |
|-----------------|------------------------------------------------------------------|
| `users`         | `{username, password_hash, role, created_at}`                  |
| `conversations` | `{username, messages: [...], updated_at}` — chat memory          |
| `tickets`       | Captured leads (the `CRMTicket` fields + `ticket_id`, `timestamp`) |
| `counters`      | Auto-increment sequence used to generate `LEAD-2026-0042` style IDs |

## Notes / things you'll likely want to tweak

- **Pricing** in `core/knowledge_base.py::get_price` is hardcoded from
  the notebook — keep it in sync with your real price sheet, or swap
  it for a lookup against your courses JSON.
- **Memory fix vs. the notebook**: the original `handle_user_message`
  accepted a `conversation_history` argument but never used it. This
  version actually feeds the last few turns to the agent
  (`core/chat_memory.build_history_string`), so the chatbot has real
  short-term memory of the conversation, on top of the long-term
  history stored in Mongo per user.
- **Deploying**: Streamlit Community Cloud, or any VM/container — just
  make sure `GROQ_API_KEY` and `MONGODB_URI` are set as environment
  secrets, and that `data/faiss_index.bin` + `data/faiss_metadata.pkl`
  are built and shipped with the deployment (run `build_index.py`
  during your build step, not on every cold start).
