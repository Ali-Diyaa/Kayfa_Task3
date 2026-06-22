import os
import json
import re
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from.crm_models import CRMTicket, save_lead_to_mongodb, validate_phone_number
from.intent import detect_dialect, detect_intent
from.knowledge_base import (
    perform_vector_search,
    search_courses_by_track,
    search_courses_by_keyword,
    get_roadmap_details,
    list_all_diplomas,
    build_context_from_results,
    get_price
)

load_dotenv()
GROQ_MODEL = "groq:openai/gpt-oss-120b"

class RAGDeps(BaseModel):
    intent: str = "general_inquiry"
    user_language: str = "ar"

class Answer(BaseModel):
    answer: str

def clean_for_user(text: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\(المصدر:[^)]+\)', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

BASE_SYSTEM_PROMPT = """
You are Kayfa AI Sales Agent.

RULES:
1. Use tools for all Kayfa questions
2. Respond in user's language
3. Use bullet points with •
4. No markdown bold
5. Keep technical terms in English
"""

kayfa_agent = Agent(
    model=GROQ_MODEL,
    deps_type=RAGDeps,
    output_type=Answer,
    system_prompt=BASE_SYSTEM_PROMPT,
    model_settings={"temperature": 0.2},
    retries=3
)

@kayfa_agent.tool_plain
def search_knowledge_base(query: str, top_k: int = 4) -> str:
    results = perform_vector_search(query, top_k=top_k)
    if not results:
        return "NO_RESULTS_FOUND"
    return build_context_from_results(results)

@kayfa_agent.tool_plain
def get_courses_by_track(track: str, level: str = None) -> str:
    results = search_courses_by_track(track, level)
    return json.dumps(results, ensure_ascii=False) if results else "NO_COURSES_FOUND"

@kayfa_agent.tool_plain
def get_courses_by_keyword(keyword: str) -> str:
    results = search_courses_by_keyword(keyword)
    return json.dumps(results, ensure_ascii=False) if results else "NO_COURSES_FOUND"

@kayfa_agent.tool_plain
def get_roadmap_details_tool(roadmap_name: str) -> str:
    details = get_roadmap_details(roadmap_name)
    return json.dumps(details, ensure_ascii=False) if details else "ROADMAP_NOT_FOUND"

@kayfa_agent.tool_plain
def list_all_diplomas_tool() -> str:
    diplomas = list_all_diplomas()
    return json.dumps(diplomas, ensure_ascii=False)

@kayfa_agent.tool
async def capture_lead(ctx: RunContext[RAGDeps], ticket: CRMTicket) -> str:
    is_valid, cleaned_phone = validate_phone_number(ticket.phone)
    if not is_valid:
        return "PHONE_VALIDATION_FAILED"
    ticket.phone = cleaned_phone
    ticket_id = save_lead_to_mongodb(ticket)
    return f"LEAD_SAVED:{ticket_id}"

async def ask_kayfa(question: str) -> str:
    deps = RAGDeps(
        intent=detect_intent(question),
        user_language="ar" if re.search('[\u0600-\u06FF]', question) else "en"
    )
    result = await kayfa_agent.run(question, deps=deps)
    return clean_for_user(result.output.answer)

async def handle_user_message(user_message: str, history: str = "") -> str:
    return await ask_kayfa(user_message)