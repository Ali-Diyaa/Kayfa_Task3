"""
Run this ONCE (and again whenever your markdown knowledge base changes):

    python scripts/build_index.py

It reads every .md file in data/text/ plus data/json/kayfa_courses.json,
embeds them with the multilingual model, and writes
data/faiss_index.bin + data/faiss_metadata.pkl — which the Streamlit
app loads at runtime (core/knowledge_base.py::load_faiss_index).

This is intentionally NOT run inside the Streamlit app itself: building
the index touches every document and re-embeds everything, which is far
too slow to do on a page load.
"""
import json
import pickle
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data"
TEXT_DIR = DATA_DIR / "text"
COURSES_PATH = DATA_DIR / "json" / "kayfa_courses.json"


def clean_markdown(text: str) -> str:
    text = re.sub(r"[📊🛠️💼🏆🔐]", "", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_arabic_labels(content: str, source: str) -> list:
    labels = []
    if "soc" in source.lower():
        labels = ["الأمن السيبراني", "سوك", "تحليل أمني", "مركز العمليات الأمنية"]
    elif "data science" in source.lower():
        labels = ["علوم البيانات", "داتا ساينس", "تحليل بيانات", "تعلم آلة"]
    elif "ai" in source.lower():
        labels = ["ذكاء اصطناعي", "ai", "شات جي بي تي"]
    return labels


def main():
    from sentence_transformers import SentenceTransformer
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    import faiss

    if not TEXT_DIR.exists() or not any(TEXT_DIR.glob("*.md")):
        print(f"⚠ No .md files found in {TEXT_DIR}. Drop your knowledge-base markdown there first.")

    if not COURSES_PATH.exists():
        print(f"⚠ {COURSES_PATH} not found — courses won't be embedded.")
        courses = []
    else:
        with open(COURSES_PATH, "r", encoding="utf-8") as f:
            courses = json.load(f)

    print("Loading embedding model (first run downloads it, can take a minute)...")
    embedder = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", "؟ ", "! ", "، ", " ", ""],
        keep_separator=True,
        is_separator_regex=False,
    )

    metadata = []
    embeddings = []

    md_files = sorted(TEXT_DIR.glob("*.md")) if TEXT_DIR.exists() else []
    for file_path in md_files:
        content = clean_markdown(file_path.read_text(encoding="utf-8"))
        chunks = text_splitter.split_text(content)
        arabic_labels = extract_arabic_labels(content, file_path.stem)

        for i, chunk in enumerate(chunks):
            enriched_text = f"{' '.join(arabic_labels)} {chunk}" if arabic_labels else chunk
            emb = embedder.encode(enriched_text, normalize_embeddings=True)
            metadata.append(
                {
                    "id": f"{file_path.stem}_{i}",
                    "text": chunk,
                    "enriched": enriched_text,
                    "source": file_path.stem,
                    "arabic_labels": arabic_labels,
                    "chunk_id": i,
                }
            )
            embeddings.append(emb)

    for course in courses:
        text = f"{course['name']}: {course.get('summary','')} Level: {course.get('level','')} Duration: {course.get('duration','')}"
        enriched = f"دورة كورس {text}"
        emb = embedder.encode(enriched, normalize_embeddings=True)
        metadata.append(
            {
                "id": course["id"],
                "text": text,
                "source": "courses_json",
                "arabic_labels": [course["name"]],
                "chunk_id": 0,
            }
        )
        embeddings.append(emb)

    if not embeddings:
        print("✗ Nothing to embed — add markdown files / courses JSON first. Aborting.")
        return

    emb_matrix = np.array(embeddings).astype("float32")
    index = faiss.IndexFlatIP(emb_matrix.shape[1])
    index.add(emb_matrix)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(DATA_DIR / "faiss_index.bin"))
    with open(DATA_DIR / "faiss_metadata.pkl", "wb") as f:
        pickle.dump(metadata, f)

    print(f"✓ {len(md_files)} MD files + {len(courses)} courses → {index.ntotal} vectors saved to data/")


if __name__ == "__main__":
    main()
