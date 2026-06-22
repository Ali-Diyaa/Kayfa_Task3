import os
import json
import re
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from typing import List, Optional, Any
import pickle
from pathlib import Path
from pydantic_ai.messages import (
    ModelMessage, ModelRequest, ModelResponse,
    UserPromptPart, TextPart
)

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
from .chat_memory import load_history, append_messages, build_history_string

load_dotenv()
GROQ_MODEL = "groq:openai/gpt-oss-120b"

def load_json_data(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FAISS_INDEX_PATH = DATA_DIR / "faiss_index.bin"
_FAISS_META_PATH = DATA_DIR / "faiss_metadata.pkl"
_JSON_DIR = DATA_DIR / "json"
ROADMAPS = load_json_data(str(_JSON_DIR / "kayfa_roadmaps.json"))

class RAGDeps(BaseModel):
    """Context passed to every tool call"""
    intent: str = "just_browsing"
    user_language: str = "ar"

class Answer(BaseModel):
    answer: str

def clean_for_user(text: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\(المصدر:[^)]+\)', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def get_pricing_database():
    """قاعدة بيانات الأسعار كاملة - من الـ PDFs"""
    return {
        "tracks": {
            "data science": {
                "name": "Data Science", "price": 250, "videos": 736, "hours": "75:31", "courses": 12,
                "ar": ["داتا ساينس", "علوم البيانات", "علوم بيانات", "data science"]
            },
            "security operations center": {
                "name": "Security Operations Center (SOC)", "price": 250, "videos": 401, "hours": "44:52", "courses": 9,
                "ar": ["سوك", "الأمن السيبراني", "مركز العمليات الأمنية", "soc", "security operations"]
            },
            "web development": {
                "name": "Web Development", "price": 200, "videos": 468, "hours": "45:45", "courses": 9,
                "ar": ["تطوير ويب", "ويب ديفيلوبمنت", "فول ستاك", "web", "fullstack"]
            },
            "data analysis": {
                "name": "Data Analysis", "price": 180, "videos": 404, "hours": "38:54", "courses": 8,
                "ar": ["داتا اناليسيس", "تحليل بيانات", "تحليل البيانات", "data analysis"]
            },
            "frontend track": {
                "name": "Frontend Track", "price": 100, "videos": 313, "hours": "28:12", "courses": 6,
                "ar": ["فرونت اند", "واجهات", "frontend", "front end"]
            },
            "backend track": {
                "name": "Backend Track", "price": 100, "videos": 244, "hours": "23:34", "courses": 6,
                "ar": ["باك اند", "backend", "back end"]
            },
            "artificial intelligence fundamentals": {
                "name": "Artificial Intelligence Fundamentals", "price": 65, "videos": 105, "hours": "8:44", "courses": 3,
                "ar": ["ذكاء اصطناعي", "ai", "أساسيات الذكاء الاصطناعي", "artificial intelligence"]
            },
            "fundamentals of graphics and motion": {
                "name": "Fundamentals of Graphics and Motion", "price": 65, "videos": 68, "hours": "6:14", "courses": 2,
                "ar": ["جرافيك", "موشن", "تصميم", "graphics", "motion"]
            },
            "video editing track": {
                "name": "Video Editing Track", "price": 45, "videos": 23, "hours": "6:08", "courses": 1,
                "ar": ["مونتاج", "فيديو ايديتنج", "video editing"]
            },
            "crash courses": {
                "name": "Crash Courses", "price": 25, "videos": 35, "hours": "2:07", "courses": 3,
                "ar": ["كورسات سريعة", "كراش كورس", "crash"]
            }
        },
        "courses": {
            "business statistics": {"name": "Business Statistics", "price": 65, "hours": "12:38", "instructor": "Prof. Mostafa Elhosseini"},
            "ms sql server programming": {"name": "MS SQL Server Programming", "price": 35, "hours": "10:03", "instructor": "Hagar Ibrahiem"},
            "data visualization by power bi": {"name": "Data Visualization by Power Bi", "price": 30, "hours": "6:13", "instructor": "Eman Raslan"},
            "network and security fundamentals": {"name": "Network and Security Fundamentals", "price": 30, "hours": "4:48", "instructor": "Ahmed Shalaby"},
            "html": {"name": "HTML", "price": 30, "hours": "5:12", "instructor": "Mohamed Ali"},
            "fundamentals of graphic design": {"name": "Fundamentals of Graphic Design", "price": 30, "hours": "2:35", "instructor": "Heba Hashem Abdeen"},
            "microsoft windows active directory": {"name": "Microsoft Windows Active Directory", "price": 35, "hours": "6:21", "instructor": "Abdelbaky Shehata"},
            "linux fundamentals": {"name": "Linux Fundamentals", "price": 40, "hours": "5:19", "instructor": "Yehia kandeel"},
            "splunk siem case studies": {"name": "Splunk SIEM Case Studies", "price": 50, "hours": "2:36", "instructor": "Motasem Hamdan"},
            "how ai & chat gpt work": {"name": "How AI & Chat GPT Work", "price": 20, "hours": "2:01", "instructor": "Mohammad Thabet"},
            "introduction to javascript": {"name": "Introduction to JavaScript", "price": 20, "hours": "2:35", "instructor": "Mohamed Ali"},
            "introduction to typescript": {"name": "Introduction to TypeScript", "price": 20, "hours": "2:33", "instructor": "Ahmed Saber"},
            "introduction to marketing": {"name": "Introduction to Marketing", "price": 15, "hours": "0:57", "instructor": "Walid Saed"},
            "career planning": {"name": "Career Planning", "price": 15, "hours": "0:18", "instructor": "Mariam Elgaby"}
        },
        "free": [
            "SOC Tips", "Programming Tips", "AI Tips", "Data Science Tips",
            "General Courses Tips", "Free Sessions", "Introduction to Data Science",
            "Live Session - All About Data Science", "HTML Tips",
            "QRadar Professional Pathway TIPS", "Network and Security Fundamentals Tips"
        ]
    }

def find_pricing(query: str) -> dict:
    db = get_pricing_database()
    
    q = query.lower().strip()
    q = re.sub(r'(مسار|دبلومة|دورة|كورس| track| course| diploma|ال|بالـ)', '', q).strip()
    
    # Tracks
    for key, track in db["tracks"].items():
        if q in key or any(q in ar.lower() or ar.lower() in q for ar in track["ar"]):
            return {"found": True, "type": "track", **track}

    # Courses
    for key, course in db["courses"].items():
        if q in key:
            return {"found": True, "type": "course", **course}

    # Free
    for item in db["free"]:
        if any(w in item.lower() for w in q.split() if len(w) > 3):
            return {"found": True, "type": "free", "name": item, "price": 0}

    return {"found": False}



BASE_SYSTEM_PROMPT = """
You are Kayfa AI Sales Agent for Kayfa, an IAO-accredited Arabic edtech platform by Kayfa Digital Solutions.
=== TOOL FALLBACK (CRITICAL) ===
- If a structured tool (get_roadmap_details_tool, get_courses_by_track, etc.) returns 
  NOT_FOUND or empty, ALWAYS try search_knowledge_base as a fallback BEFORE telling 
  the user the item doesn't exist.
- The knowledge base contains more content (diplomas like Fullstack, PenTest) than the 
  JSON catalogs. Vector search is your safety net.
- If BOTH structured and semantic search return nothing, then say you don't have it 
  and offer to connect with sales.
- NEVER say "we don't have X" without first calling search_knowledge_base.

=== GROUNDING (NON-NEGOTIABLE) ===
1. Answer ONLY from tool outputs: search_knowledge_base, get_courses_by_track, get_courses_by_keyword, get_roadmap_details_tool, list_all_diplomas_tool, get_exact_pricing.
2. Never invent course names, prices, durations, dates, instructors, or policies.
3. If tools return NO_RESULTS, say you do not have that information and offer to connect the user with sales.
4. Do not use pre-trained knowledge about Kayfa.

=== LANGUAGE ===
5. Detect the user's language and reply in the same language.
6. If Arabic, mirror the user's dialect (Egyptian, Saudi, Levantine) when possible; otherwise use Modern Standard Arabic.
7. Keep all technical terms in English (SOC, Splunk, QRadar, Python, Power BI, etc.).

=== SALES BEHAVIOR & TOOL CALLING ===
8. Be concise, helpful, and honest. No hype.
9. Recommend relevant diplomas or tracks when they match the user's goal.
10. When the user provides name AND phone/WhatsApp, call capture_lead immediately with a complete CRMTicket.
11. PRICING CONTEXT RULE: If the user asks "how much", "بكام", or "سعرها" referring to a track/course mentioned in the previous messages, EXTRACT the exact name from context and call get_exact_pricing. DO NOT ask the user to clarify.

=== OUTPUT FORMAT FOR USER ===
12. Use plain text only. No markdown bold (**), no italics, no headings with #.
13. Use bullet points starting with • 
14. Avoid large tables. If a table is necessary, use max 2 columns and simple pipes.
15. Do NOT write inline citations like (المصدر: ...) or (Source: ...). 
16. At the very end, add ONE source line only if you used tools: 
    Source: filename1, filename2
17. Remove emojis and decorative symbols.
"""

kayfa_agent = Agent(
    model=GROQ_MODEL,
    deps_type=RAGDeps,
    system_prompt=BASE_SYSTEM_PROMPT,
    model_settings={"temperature": 0.2},
    retries=2,
)

# ─── TOOL 1: Vector Search ───
@kayfa_agent.tool_plain
def search_knowledge_base(query: str, top_k: int = 4) -> str:
    """
    Search Kayfa's documentation (diplomas, policies, course details) using semantic search.
    Use this for ANY question about content, curriculum, instructors, accreditation, policies.
    Returns relevant text chunks with sources.
    """
    results = perform_vector_search(query, top_k=top_k)
    if not results:
        return "NO_RESULTS_FOUND"
    return build_context_from_results(results)

@kayfa_agent.tool_plain
def unified_search(query: str) -> str:
    """
    ALWAYS try this tool first for ANY product question.
    Searches both structured JSON catalogs AND markdown knowledge base.
    Returns combined results.
    """
    results = []
    
    # 1. Structured search in ROADMAPS
    for rm in ROADMAPS:
        haystack = (rm["name"] + " " + rm.get("summary", "")).lower()
        if any(word in haystack for word in query.lower().split() if len(word) > 3):
            results.append({
                "type": "roadmap_or_diploma",
                "name": rm["name"],
                "id": rm["id"],
                "duration": rm.get("duration"),
                "link": rm.get("link")
            })
    
    # 2. Vector search in MD files
    vector_results = perform_vector_search(query, top_k=4)
    for r in vector_results:
        results.append({
            "type": "document_chunk",
            "source": r["meta"]["source"],
            "text": r["text"][:500]
        })
    
    return json.dumps(results, ensure_ascii=False, indent=2) if results else "NO_RESULTS"

# ─── TOOL 2: Structured Course Search ───
@kayfa_agent.tool_plain
def get_courses_by_track(track: str, level: str = None) -> str:
    """
    Get courses filtered by track name (e.g., 'SOC', 'Data Science', 'AI').
    Use when user asks 'what courses in X track' or 'ماذا يوجد في مسار'.
    """
    results = search_courses_by_track(track, level)
    return json.dumps(results, ensure_ascii=False, indent=2) if results else "NO_COURSES_FOUND"

@kayfa_agent.tool_plain
def get_courses_by_keyword(keyword: str) -> str:
    """Search courses by keyword in name or summary."""
    results = search_courses_by_keyword(keyword)
    return json.dumps(results, ensure_ascii=False, indent=2) if results else "NO_COURSES_FOUND"

# ─── TOOL 3: Roadmap Details ───
@kayfa_agent.tool_plain
def get_roadmap_details_tool(roadmap_name: str) -> str:
    """
    Get full diploma/roadmap details including duration, skills, tools, and course list.
    Use for 'tell me about SOC diploma', 'تفاصيل دبلومة'.
    """
    details = get_roadmap_details(roadmap_name)
    return json.dumps(details, ensure_ascii=False, indent=2) if details else "ROADMAP_NOT_FOUND"

@kayfa_agent.tool_plain
def list_all_diplomas_tool() -> str:
    """List all available diplomas with duration and course count."""
    diplomas = list_all_diplomas()
    return json.dumps(diplomas, ensure_ascii=False, indent=2)

@kayfa_agent.tool
async def capture_lead(ctx: RunContext[RAGDeps], ticket: CRMTicket) -> str:
    """Save a qualified lead as a CRM ticket in MongoDB. Validates phone before saving."""
    
    
    if not ticket.name or ticket.name.strip() == "":
        return "MISSING_FIELD: Name is required to create a lead."
    
    ticket_id = save_lead_to_mongodb(ticket)
    
    return f"LEAD_SAVED:{ticket_id}"

@kayfa_agent.tool_plain
def get_exact_pricing(item_name: str) -> str:
    """
    Get EXACT pricing for any diploma, track, or course.
    ALWAYS use this when user asks about price, cost, 'بكام', 'سعر', 'how much'.
    If the user asks about a price using a pronoun (e.g., 'سعرها', 'how much is it'), 
    extract the exact English name from the previous conversation (e.g., "Data Science") 
    and pass it here as item_name.
    """
    result = find_pricing(item_name)

    if not result["found"]:
        db = get_pricing_database()
        prices = {v["name"]: f"${v['price']}" for v in db["tracks"].values()}
        return json.dumps({"found": False, "available_tracks": prices}, ensure_ascii=False)

    if result["type"] == "free":
        return json.dumps({"name": result["name"], "price": "مجاناً", "price_usd": 0}, ensure_ascii=False)

    return json.dumps({
        "name": result["name"],
        "price": f"${result['price']}",
        "price_usd": result["price"],
        "type": result["type"],
        "videos": result.get("videos"),
        "hours": result.get("hours"),
        "courses": result.get("courses")
    }, ensure_ascii=False)

def _history_to_model_messages(messages: List[dict]) -> List[ModelMessage]:
    result: List[ModelMessage] = []
    for m in messages:
        if m["role"] == "user":
            result.append(ModelRequest(parts=[UserPromptPart(content=m["content"])]))
        elif m["role"] == "assistant":
            result.append(ModelResponse(parts=[TextPart(content=m["content"])]))
    return result


async def ask_kayfa(question: str, username: str | None = None) -> str:
    deps = RAGDeps(
        intent=detect_intent(question),
        user_language="ar" if re.search('[\u0600-\u06FF]', question) else "en"
    )

    history = load_history(username) if username else []
    
    history_messages = _history_to_model_messages(history[-8:])

    result = await kayfa_agent.run(
        question, 
        deps=deps, 
        message_history=history_messages  
    )
    
    answer = clean_for_user(result.output)

    if username:
        append_messages(username, [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ])
    return answer
async def handle_user_message(user_message: str, username: str | None = None) -> str:
    return await ask_kayfa(user_message, username=username)