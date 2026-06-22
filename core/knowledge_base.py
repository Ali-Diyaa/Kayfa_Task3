import os
import json
import pickle
from pathlib import Path
from typing import List, Optional, Any
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Paths
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FAISS_INDEX_PATH = DATA_DIR / "faiss_index.bin"
_FAISS_META_PATH = DATA_DIR / "faiss_metadata.pkl"
_JSON_DIR = DATA_DIR / "json"

# Load data
def load_json_data(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

COURSES = load_json_data(str(_JSON_DIR / "kayfa_courses.json"))
ROADMAPS = load_json_data(str(_JSON_DIR / "kayfa_roadmaps.json"))

# Embedding model
_EMBED_MODEL_NAME = "BAAI/bge-m3"
_embedder = SentenceTransformer(_EMBED_MODEL_NAME)

# FAISS
faiss_index = None
faiss_metadata: List[dict] = []

def load_faiss_index():
    """Load the FAISS index and metadata from disk"""
    global faiss_index, faiss_metadata
    if _FAISS_INDEX_PATH.exists() and _FAISS_META_PATH.exists():
        faiss_index = faiss.read_index(str(_FAISS_INDEX_PATH))
        with open(_FAISS_META_PATH, "rb") as f:
            faiss_metadata = pickle.load(f)
        print(f"✓ Loaded FAISS index with {faiss_index.ntotal} vectors.")
    else:
        faiss_index = None
        faiss_metadata = []
        print("⚠️ No FAISS index found.")

def perform_vector_search(query: str, top_k: int = 3, source_filter: Optional[str] = None) -> List[dict]:
    global faiss_index, faiss_metadata

    if faiss_index is None:
        load_faiss_index()
        if faiss_index is None or faiss_index.ntotal == 0:
            print("⚠ FAISS index is empty - run ingest_md_files_faiss first")
            return []

    try:
        q_emb = _embedder.encode([query], normalize_embeddings=True).astype('float32')
        k_to_retrieve = top_k * 5 if source_filter else top_k

        distances, indices = faiss_index.search(q_emb, k_to_retrieve)

        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx == -1 or idx >= len(faiss_metadata):
                continue
            meta = faiss_metadata[idx]

            if source_filter:
                if source_filter in ["courses_json", "roadmaps_json"]:
                    if meta['source']!= source_filter:
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

# Load on import
load_faiss_index()