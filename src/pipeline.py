from __future__ import annotations

import re
import json
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import CHUNK_WORDS, CHUNK_OVERLAP_WORDS, TOP_K

TOKEN_RE = re.compile(r"(?u)\b[a-zA-Z][a-zA-Z0-9'-]*\b")
MIN_RETRIEVAL_SCORE = 0.055


def _tokens(text: str) -> list[str]:
    """Return lower-case query terms, ignoring common stop words."""
    return [
        token.lower().strip("'-")
        for token in TOKEN_RE.findall(text or "")
        if len(token.strip("'-")) > 1
        and token.lower().strip("'-") not in ENGLISH_STOP_WORDS
    ]


def chunk_text(
    text: str,
    chunk_words: int = CHUNK_WORDS,
    overlap: int = CHUNK_OVERLAP_WORDS,
) -> list[str]:
    """Split long source text into overlapping, readable chunks."""
    words = re.findall(r"\S+", text or "")
    if not words:
        return []
    chunk_words = max(25, int(chunk_words))
    overlap = min(max(0, int(overlap)), chunk_words - 1)
    step = chunk_words - overlap
    chunks = []
    for start in range(0, len(words), step):
        part = words[start : start + chunk_words]
        if len(part) < 25 and chunks:
            break
        chunks.append(" ".join(part))
        if start + chunk_words >= len(words):
            break
    return chunks


def prepare_chunks(pages: list[dict]) -> pd.DataFrame:
    """Convert page records into a standard table of overlapping text chunks."""
    rows = []
    for page in pages:
        source_text = str(page.get("text", "") or "")
        for index, chunk in enumerate(chunk_text(source_text)):
            rows.append(
                {
                    "title": str(page.get("title", "Untitled")),
                    "url": str(page.get("url", "")),
                    "chunk_id": index,
                    "text": chunk,
                    "word_count": len(chunk.split()),
                }
            )
    return pd.DataFrame(
        rows, columns=["title", "url", "chunk_id", "text", "word_count"]
    )


class Retriever:
    """Hybrid lexical retrieval with relevance gating and source diversity.

    Word n-grams capture matching concepts, character n-grams help with variants
    and minor spelling differences, and token overlap helps short natural-language
    questions. The returned score is a ranking score, not a probability.
    """

    def __init__(self, chunks: pd.DataFrame):
        self.chunks = chunks.copy().reset_index(drop=True)
        self.word_vectorizer = None
        self.char_vectorizer = None
        self.word_matrix = None
        self.char_matrix = None
        self.doc_tokens: list[set[str]] = []
        self.title_tokens: list[set[str]] = []

        if self.chunks.empty:
            return

        documents = self.chunks["text"].fillna("").astype(str).tolist()
        titles = self.chunks["title"].fillna("").astype(str).tolist()
        self.doc_tokens = [set(_tokens(text)) for text in documents]
        self.title_tokens = [set(_tokens(title)) for title in titles]

        try:
            self.word_vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                sublinear_tf=True,
                max_features=30000,
            )
            self.word_matrix = self.word_vectorizer.fit_transform(documents)
        except ValueError:
            self.word_matrix = None

        try:
            self.char_vectorizer = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                sublinear_tf=True,
                max_features=40000,
            )
            self.char_matrix = self.char_vectorizer.fit_transform(documents)
        except ValueError:
            self.char_matrix = None

    def search(self, question: str, top_k: int = TOP_K) -> list[dict]:
        question = (question or "").strip()
        if not question or self.chunks.empty:
            return []

        query_terms = set(_tokens(question))
        if not query_terms:
            return []

        word_scores = [0.0] * len(self.chunks)
        char_scores = [0.0] * len(self.chunks)

        try:
            if self.word_matrix is not None and self.word_vectorizer is not None:
                query_vector = self.word_vectorizer.transform([question])
                word_scores = cosine_similarity(query_vector, self.word_matrix).ravel().tolist()
        except ValueError:
            pass

        try:
            if self.char_matrix is not None and self.char_vectorizer is not None:
                query_vector = self.char_vectorizer.transform([question])
                char_scores = cosine_similarity(query_vector, self.char_matrix).ravel().tolist()
        except ValueError:
            pass

        ranked = []
        for index, row in self.chunks.iterrows():
            present = query_terms.intersection(self.doc_tokens[index])
            coverage = len(present) / max(1, len(query_terms))
            title_coverage = len(query_terms.intersection(self.title_tokens[index])) / max(1, len(query_terms))

            # Combined ranking score; deliberately not described as a probability.
            score = (
                0.64 * float(word_scores[index])
                + 0.23 * float(char_scores[index])
                + 0.11 * coverage
                + 0.02 * title_coverage
            )
            if score < MIN_RETRIEVAL_SCORE or not present:
                continue

            ranked.append(
                {
                    "title": str(row.get("title", "Untitled")),
                    "url": str(row.get("url", "")),
                    "text": str(row.get("text", "")),
                    "score": min(1.0, score),
                    "matched_terms": sorted(present),
                    "chunk_id": int(row.get("chunk_id", 0)),
                }
            )

        ranked.sort(key=lambda result: result["score"], reverse=True)

        # Keep results useful: limit repeated overlapping chunks from the same page
        # and skip passages that are near-duplicates of an already selected chunk.
        results = []
        per_url: dict[str, int] = {}
        for result in ranked:
            url = result["url"]
            if per_url.get(url, 0) >= 2:
                continue
            words = set(_tokens(result["text"]))
            near_duplicate = False
            for prior in results:
                prior_words = set(_tokens(prior["text"]))
                union = words | prior_words
                if union and len(words & prior_words) / len(union) >= 0.72:
                    near_duplicate = True
                    break
            if near_duplicate:
                continue
            results.append(result)
            per_url[url] = per_url.get(url, 0) + 1
            if len(results) >= max(1, min(int(top_k), 10)):
                break
        return results


def extractive_summary(question: str, passages: list[dict], max_sentences: int = 4) -> list[dict]:
    """Select source sentences relevant to the question without generating facts."""
    candidates = []
    seen = set()
    for source_index, passage in enumerate(passages, start=1):
        raw_text = str(passage.get("text", "") or "")
        # Page extraction retains heading/paragraph boundaries, so handle newlines
        # as boundaries too before sentence ranking.
        for block in raw_text.splitlines():
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", block.strip()):
                sentence = " ".join(sentence.split())
                normal = re.sub(r"\W+", " ", sentence.lower()).strip()
                if len(sentence) < 35 or normal in seen:
                    continue
                seen.add(normal)
                candidates.append(
                    {
                        "sentence": sentence,
                        "source_index": source_index,
                        "title": passage.get("title", ""),
                        "url": passage.get("url", ""),
                    }
                )

    if not candidates:
        return []

    query_terms = set(_tokens(question))
    sentence_texts = [item["sentence"] for item in candidates]
    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        matrix = vectorizer.fit_transform([question] + sentence_texts)
        similarities = cosine_similarity(matrix[0:1], matrix[1:]).ravel()
    except ValueError:
        similarities = [0.0] * len(candidates)

    ranked = []
    for index, item in enumerate(candidates):
        sentence_tokens = set(_tokens(item["sentence"]))
        coverage = len(query_terms.intersection(sentence_tokens)) / max(1, len(query_terms))
        score = 0.78 * float(similarities[index]) + 0.22 * coverage
        if score > 0:
            ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)

    output = []
    for _, item in ranked:
        if item["sentence"] not in [prior["sentence"] for prior in output]:
            output.append(item)
        if len(output) >= max(1, min(int(max_sentences), 6)):
            break

    # If useful source evidence exists but the sentence-level scorer is very sparse,
    # return up to two short source sentences as a conservative fallback.
    if not output:
        output = candidates[: min(2, max_sentences)]
    return output


def save_collection(
    pages: list[dict], chunks: pd.DataFrame, data_dir: Path
) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    metadata = [
        {key: value for key, value in page.items() if key != "text"}
        for page in pages
    ]
    pd.DataFrame(
        metadata,
        columns=["url", "title", "collected_at", "characters", "word_count"],
    ).to_csv(data_dir / "crawl_results.csv", index=False)
    (data_dir / "pages.json").write_text(
        json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    chunks.to_csv(data_dir / "chunks.csv", index=False)
