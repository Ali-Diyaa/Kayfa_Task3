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
_EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
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

def perform_vector_search(query: str, top_k: int = 4) -> List[dict]:
    """Search using FAISS"""
    if faiss_index is None or faiss_index.ntotal == 0:
        return []

    query_emb = _embedder.encode(query, normalize_embeddings=True).astype('float32')
    scores, indices = faiss_index.search(np.array([query_emb]), top_k)

    results = []
    for idx, score in zip(indices[0], scores[0]):
        if idx < len(faiss_metadata):
            meta = faiss_metadata[idx]
            results.append({
                "text": meta["text"],
                "meta": {"source": meta["source"], "score": float(score)}
            })
    return results

def build_context_from_results(results: List[dict]) -> str:
    """Build context string from search results"""
    contexts = []
    for r in results:
        source = r["meta"]["source"]
        text = r["text"][:500]
        contexts.append(f"[SOURCE: {source}]\n{text}")
    return "\n\n".join(contexts)

def search_courses_by_track(track: str, level: Optional[str] = None) -> List[dict]:
    results = []
    for course in COURSES:
        if track.lower() in str(course.get("track", [])).lower():
            if level is None or course.get("level") == level:
                results.append(course)
    return results

def search_courses_by_keyword(keyword: str) -> List[dict]:
    results = []
    for course in COURSES:
        if keyword.lower() in course["name"].lower() or keyword.lower() in course["summary"].lower():
            results.append(course)
    return results

def get_roadmap_details(roadmap_name: str) -> Optional[dict]:
    for roadmap in ROADMAPS:
        if roadmap_name.lower() in roadmap["name"].lower():
            return roadmap
    return None

def list_all_diplomas() -> List[dict]:
    return [{"name": r["name"], "duration": r.get("duration"), "courses": len(r.get("courses", []))} for r in ROADMAPS]

def get_price(product_name: str) -> Optional[str]:
    for course in COURSES:
        if product_name.lower() in course["name"].lower():
            return course.get("price", "Contact for pricing")
    return None

# Load on import
load_faiss_index()