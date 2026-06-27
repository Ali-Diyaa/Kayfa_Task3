"""
Knowledge base — FAISS vector search + structured course/roadmap lookups.
Embedding model and FAISS index are cached via st.cache_resource
so they load ONCE per process, not on every Streamlit rerun.
"""
import os
import json
import pickle
import streamlit as st
from pathlib import Path
from typing import List, Optional, Any
import faiss
import numpy as np

# Paths
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FAISS_INDEX_PATH = DATA_DIR / "faiss_index.bin"
_FAISS_META_PATH = DATA_DIR / "faiss_metadata.pkl"
_JSON_DIR = DATA_DIR / "json"


# ── JSON Data (fast, no caching needed) ────────────────────────────
def load_json_data(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

COURSES = load_json_data(str(_JSON_DIR / "kayfa_courses.json"))
ROADMAPS = load_json_data(str(_JSON_DIR / "kayfa_roadmaps.json"))


# ════════════════════════════════════════════════════════════════
# CACHED: Embedding Model — loads ONCE per Streamlit process
# Without this, 391MB of weights reload on every rerun
# ════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def get_embedder():
    """Load the sentence-transformer model once and cache it."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("BAAI/bge-m3")
    print("✅ Embedding model loaded & cached")
    return model


# ════════════════════════════════════════════════════════════════
# CACHED: FAISS Index + Metadata — loads ONCE per Streamlit process
# Without this, 160 vectors re-deserialize from disk on every rerun
# ════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def get_faiss_data():
    """
    Load FAISS index and metadata into memory, cached for the
    lifetime of the Streamlit process.
    Returns (index, metadata_list) or (None, []).
    """
    if not _FAISS_INDEX_PATH.exists() or not _FAISS_META_PATH.exists():
        print("⚠️ No FAISS index found — run the ingestion script first.")
        return None, []

    index = faiss.read_index(str(_FAISS_INDEX_PATH))
    with open(_FAISS_META_PATH, "rb") as f:
        metadata = pickle.load(f)

    print(f"✅ FAISS index loaded & cached ({index.ntotal} vectors)")
    return index, metadata


# ════════════════════════════════════════════════════════════════
# Vector Search — uses cached embedder + cached FAISS
# ════════════════════════════════════════════════════════════════
def perform_vector_search(query: str, top_k: int = 3,
                          source_filter: Optional[str] = None) -> List[dict]:
    faiss_index, faiss_metadata = get_faiss_data()

    if faiss_index is None or faiss_index.ntotal == 0:
        return []

    try:
        embedder = get_embedder()
        q_emb = embedder.encode([query], normalize_embeddings=True).astype('float32')
        k_to_retrieve = top_k * 5 if source_filter else top_k

        distances, indices = faiss_index.search(q_emb, k_to_retrieve)

        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx == -1 or idx >= len(faiss_metadata):
                continue
            meta = faiss_metadata[idx]

            if source_filter:
                if source_filter in ["courses_json", "roadmaps_json"]:
                    if meta['source'] != source_filter:
                        continue
                elif source_filter not in meta['source']:
                    continue

            results.append({
                "text": meta["text"],
                "meta": {
                    "source": meta["source"],
                    "chunk_id": meta.get("chunk_id", 0),
                    "score": float(dist),
                    "type": meta.get("type", "unknown")
                }
            })
            if len(results) >= top_k:
                break

        return results
    except Exception as e:
        print(f"Vector search error: {e}")
        import traceback
        traceback.print_exc()
        return []


def build_context_from_results(results: List[dict]) -> str:
    if not results:
        return "NO_RESULTS"

    parts = []
    for r in results:
        source = r["meta"].get("source", "unknown")
        score = r["meta"].get("score", 0)
        parts.append(f"[SOURCE: {source} | {score:.3f}]\n{r['text']}")

    return "\n\n---\n\n".join(parts)


# ════════════════════════════════════════════════════════════════
# Structured Lookups (in-memory JSON, no caching needed)
# ════════════════════════════════════════════════════════════════
def search_courses_by_track(track: str, level: Optional[str] = None) -> List[dict]:
    results = []
    track_lower = track.lower()
    for course in COURSES:
        course_tracks = [t.lower() for t in course.get("track", [])]
        if any(track_lower in ct or ct in track_lower for ct in course_tracks):
            if level is None or course.get("level", "").lower() == level.lower():
                results.append({
                    "id": course["id"],
                    "name": course["name"],
                    "level": course.get("level", "غير محدد"),
                    "duration": course.get("duration", "غير محدد"),
                    "link": course.get("link", "")
                })
    return results


def search_courses_by_keyword(keyword: str) -> List[dict]:
    kw = keyword.lower()
    results = []
    for c in COURSES:
        haystack = (c.get("name", "") + " " + c.get("summary", "")).lower()
        if kw in haystack:
            results.append({
                "id": c["id"],
                "name": c["name"],
                "level": c.get("level", "غير محدد"),
                "duration": c.get("duration", "غير محدد"),
                "link": c.get("link", "")
            })
    return results


def get_roadmap_details(roadmap_name: str) -> Optional[dict]:
    name_lower = roadmap_name.lower()
    for rm in ROADMAPS:
        if name_lower in rm["name"].lower() or name_lower in rm["id"].lower():
            course_details = []
            for cid in rm.get("courses_list", []):
                c = next((x for x in COURSES if x["id"] == cid), None)
                if c:
                    course_details.append({
                        "name": c["name"],
                        "level": c.get("level", "غير محدد")
                    })
            return {
                "name": rm["name"],
                "summary": rm.get("summary", ""),
                "duration": rm.get("duration", "غير محدد"),
                "skills": rm.get("skills", []),
                "tools": rm.get("tools", []),
                "courses": course_details,
                "link": rm.get("link", "")
            }
    return None


def list_all_diplomas() -> List[dict]:
    return [
        {
            "name": d["name"],
            "id": d["id"],
            "duration": d.get("duration", "غير محدد"),
            "courses_count": d.get("courses_count", len(d.get("courses_list", []))),
            "link": d.get("link", "")
        }
        for d in ROADMAPS
        if "diploma" in d["id"].lower() or "bootcamp" in d["id"].lower()
        or "diploma" in d["name"].lower()
    ]


def get_price(product_name: str) -> Optional[str]:
    for course in COURSES:
        if product_name.lower() in course["name"].lower():
            return course.get("price", "Contact for pricing")
    return None