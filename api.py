"""
FastAPI server exposing the Kayfa AI Sales Agent via a /chat endpoint.

The agent itself is NOT modified. This file only imports and calls
`handle_user_message` from `core/agent.py` — exactly the same function
the Streamlit `page_chat.py` calls. All the logic (intent detection,
dialect detection, dynamic system prompt assembly, tools, phone
validation, lead capture, usage logging, chat memory) stays untouched.

Run:
    uvicorn api:app --reload --port 8000
"""
from __future__ import annotations

import threading
from contextlib import asynccontextmanager

# ─────────────────────────────────────────────────────────────────────
# 1. Streamlit script-context bootstrap (must run BEFORE importing core.*)
#    core/db.py and core/knowledge_base.py use @st.cache_resource to
#    memoize the Mongo client, FAISS index, and embedding model. In a
#    pure FastAPI process there's no Streamlit script run, so we install
#    a lightweight dummy ScriptRunContext on the main thread. This keeps
#    @st.cache_resource behaving like a plain memoizer.
# ─────────────────────────────────────────────────────────────────────
try:
    from streamlit.runtime.scriptrunner import script_run_context
    _dummy_ctx = script_run_context.ScriptRunContext()
    script_run_context.add_script_run_context(threading.current_thread(), _dummy_ctx)
except Exception as _e:  # pragma: no cover
    print(f"[warn] could not bootstrap Streamlit context: {_e}")


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# NOTE: imported AS-IS — no monkey patching, no re-implementation.
from core.agent import handle_user_message
from core.chat_memory import create_chat
from core.db import ensure_indexes


# 2. Pydantic schemas

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's question / message")
    chat_id: str | None = Field(
        default=None,
        description="Existing chat session id. If omitted and `username` is "
                    "supplied, a new chat session is created (mirrors page_chat.py).",
    )
    user_id: str | None = Field(
        default=None,
        description="Identifier used in usage_logs. Falls back to `username`.",
    )
    username: str | None = Field(
        default=None,
        description="Kayfa username. Required to create a new chat session "
                    "when `chat_id` is not provided.",
    )


class ChatResponse(BaseModel):
    reply: str
    chat_id: str | None


# 3. App lifecycle — same DB index setup the Streamlit app does at startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ensure_indexes()
    except Exception as e:
        print(f"[warn] ensure_indexes failed: {e}")
    yield


app = FastAPI(
    title="Kayfa AI Sales Agent",
    version="1.0.0",
    description="FastAPI wrapper that drives the Kayfa sales agent exactly "
                "as defined in core/agent.py — same tools, same dynamic "
                "system prompt, same logging, same memory.",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────────────
# 4. Endpoints
# ─────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """
    Send a message to the Kayfa AI sales agent.

    Internally calls `handle_user_message` from `core.agent`, which:
      • clears the per-request tool dedup cache
      • detects intent and dialect
      • builds the dynamic system prompt
        (BASE_PROMPT → intent strategy → dialect rule → parallel-tool rule)
      • loads the last 20 turns of history from MongoDB (if chat_id given)
      • runs the pydantic-ai Agent with ALL tools defined in agent.py
        (search_knowledge_base, get_courses_by_track, get_courses_by_keyword,
         get_roadmap_details_tool, list_all_diplomas_tool, capture_lead,
         get_exact_pricing)
      • logs usage + trace to the `usage_logs` collection
      • appends the user/assistant turn to chat memory

    Nothing in the agent's logic, tools, prompts, or logging is modified.
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="`message` must not be empty")

    chat_id = req.chat_id
    user_id = req.user_id or req.username

    if not chat_id and req.username:
        chat_id = create_chat(req.username, first_message=req.message)

    try:
        reply = await handle_user_message(
            user_message=req.message,
            chat_id=chat_id,
            user_id=user_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")

    return ChatResponse(reply=reply, chat_id=chat_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)