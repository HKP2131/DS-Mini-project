from __future__ import annotations
import re
import json
from pathlib import Path
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config import CHUNK_WORDS, CHUNK_OVERLAP_WORDS, TOP_K

def chunk_text(text: str, chunk_words: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP_WORDS) -> list[str]:
    words = re.findall(r"\S+", text)
    if not words:
        return []
    chunks = []
    step = max(1, chunk_words - overlap)
    for start in range(0, len(words), step):
        part = words[start:start + chunk_words]
        if len(part) < 25 and chunks:
            break
        chunks.append(" ".join(part))
        if start + chunk_words >= len(words):
            break
    return chunks

def prepare_chunks(pages: list[dict]) -> pd.DataFrame:
    rows = []
    for page in pages:
        for index, chunk in enumerate(chunk_text(page.get("text", ""))):
            rows.append({
                "title": page.get("title", "Untitled"),
                "url": page.get("url", ""),
                "chunk_id": index,
                "text": chunk,
                "word_count": len(chunk.split()),
            })
    return pd.DataFrame(rows, columns=["title", "url", "chunk_id", "text", "word_count"])

class Retriever:
    """TF-IDF-based retrieval; answers are evidence passages with source links."""
    def __init__(self, chunks: pd.DataFrame):
        self.chunks = chunks.copy()
        self.vectorizer = None
        self.matrix = None
        if not self.chunks.empty:
            self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=25000)
            self.matrix = self.vectorizer.fit_transform(self.chunks["text"].astype(str))

    def search(self, question: str, top_k: int = TOP_K) -> list[dict]:
        if self.matrix is None or not question.strip():
            return []
        query = self.vectorizer.transform([question])
        scores = cosine_similarity(query, self.matrix).ravel()
        matches = []
        for index in scores.argsort()[::-1][:top_k]:
            score = float(scores[index])
            if score <= 0:
                continue
            row = self.chunks.iloc[int(index)]
            matches.append({
                "title": row["title"], "url": row["url"], "text": row["text"],
                "score": score, "chunk_id": int(row["chunk_id"])
            })
        return matches

def save_collection(pages: list[dict], chunks: pd.DataFrame, data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    metadata = [{key: value for key, value in page.items() if key != "text"} for page in pages]
    pd.DataFrame(metadata, columns=["url", "title", "collected_at", "characters", "word_count"]).to_csv(
        data_dir / "crawl_results.csv", index=False
    )
    (data_dir / "pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")
    chunks.to_csv(data_dir / "chunks.csv", index=False)
