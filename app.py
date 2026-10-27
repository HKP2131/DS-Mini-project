from __future__ import annotations

import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

from config import MAX_PAGES, SEED_URLS, TOP_K
from src.crawler import crawl
from src.pipeline import Retriever, prepare_chunks, save_collection

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
PAGES_FILE = DATA_DIR / "pages.json"
GEMINI_MODEL = "gemini-2.5-flash"

st.set_page_config(page_title="CivilRAG | Civil Engineering Study Bot", page_icon="🏗️", layout="wide")


def load_pages() -> list[dict]:
    if not PAGES_FILE.exists():
        return []
    try:
        value = json.loads(PAGES_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def get_gemini_key() -> str:
    """Read the key from Streamlit Cloud Secrets or an environment variable."""
    try:
        secret = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        secret = ""
    return str(secret or os.getenv("GEMINI_API_KEY", "")).strip()


def generate_grounded_answer(question: str, passages: list[dict], api_key: str) -> str:
    """Use Gemini only with retrieved excerpts; never send a question without context."""
    context = "\n\n".join(
        f"Source title: {item['title']}\nSource URL: {item['url']}\nPassage: {item['text']}"
        for item in passages
    )
    prompt = (
        "You are CivilRAG, an educational assistant for civil engineering students. "
        "Answer the user's question using only the source passages supplied below. "
        "Do not use outside knowledge and do not invent facts, values, equations, or citations. "
        "If the passages do not answer the question, say the collected Wikibooks pages do not provide enough information. "
        "Explain clearly and concisely. Do not reproduce long passages verbatim.\n\n"
        f"SOURCE PASSAGES:\n{context}\n\nQUESTION: {question}"
    )
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    response = requests.post(
        endpoint,
        params={"key": api_key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 700},
        },
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    candidates = payload.get("candidates", [])
    if not candidates:
        raise RuntimeError("The model returned no answer. Try again or use the retrieved passages.")
    parts = candidates[0].get("content", {}).get("parts", [])
    answer = "\n".join(part.get("text", "") for part in parts if part.get("text"))
    if not answer.strip():
        raise RuntimeError("The model returned an empty answer.")
    return answer.strip()


st.title("🏗️ CivilRAG")
st.caption(
    "A Civil Engineering study bot based on permitted Wikibooks article pages. "
    "Retrieved passages and source links are shown so you can check the evidence."
)

pages = load_pages()

# A fresh Streamlit Cloud deployment has no generated dataset. On first startup,
# check robots.txt and run a small, polite crawl. Do not bypass the rules if no
# suitable pages are available.
if not PAGES_FILE.exists() and not st.session_state.get("startup_crawl_attempted", False):
    st.session_state.startup_crawl_attempted = True
    with st.spinner("Checking Wikibooks robots.txt and collecting permitted article pages…"):
        pages, _ = crawl(SEED_URLS, MAX_PAGES, DATA_DIR)
        save_collection(pages, prepare_chunks(pages), DATA_DIR)
    st.rerun()

if not pages:
    st.error("No article text is available. The crawl may have found no permitted or usable pages.")
    log_path = DATA_DIR / "crawl_log.txt"
    with st.expander("View crawl log"):
        st.code(log_path.read_text(encoding="utf-8") if log_path.exists() else "No crawl log available.")
    st.markdown(
        "[Wikibooks Civil Engineering](https://en.wikibooks.org/wiki/Subject:Civil_engineering) · "
        "[robots.txt](https://en.wikibooks.org/robots.txt)"
    )
    st.stop()

chunks = prepare_chunks(pages)
retriever = Retriever(chunks)
api_key = get_gemini_key()

with st.sidebar:
    st.header("Collection overview")
    st.metric("Pages collected", len(pages))
    st.metric("Text chunks", len(chunks))
    st.metric("Words collected", sum(int(page.get("word_count", 0)) for page in pages))
    st.markdown("**Web mining pipeline**")
    st.write("1. robots.txt-aware collection")
    st.write("2. HTML text extraction")
    st.write("3. Cleaning and chunking")
    st.write("4. TF-IDF retrieval")
    st.write("5. Grounded answer + source links" if api_key else "5. Evidence passages + source links")
    st.caption("Gemini answer generation: enabled" if api_key else "Gemini key not set — evidence-retrieval mode")

st.subheader("Ask a Civil Engineering question")
question = st.text_input("Your question", placeholder="e.g., Explain soil mechanics")
top_k = st.slider("Number of source passages", min_value=1, max_value=6, value=TOP_K)

if st.button("Find answer", type="primary") and question.strip():
    results = retriever.search(question, top_k=top_k)
    if not results:
        st.info("No strong text match was found. Try a different question or keyword.")
    else:
        if api_key:
            try:
                answer = generate_grounded_answer(question, results, api_key)
                st.markdown("### Answer")
                st.write(answer)
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else "unknown"
                st.warning(
                    f"Gemini request failed (HTTP {status}). Check the API key and model quota. "
                    "Retrieved evidence is shown below."
                )
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                st.warning(f"Could not generate a response. Retrieved evidence is shown below. Details: {exc}")
        else:
            st.markdown("### Relevant information")
            st.info(
                "Gemini is not configured, so CivilRAG is showing the top retrieved passages. "
                "Add GEMINI_API_KEY in Streamlit Cloud → App settings → Secrets to enable generated answers."
            )
        st.markdown("### Sources used")
        for number, item in enumerate(results, start=1):
            st.markdown(f"**Passage {number}: {item['title']}** · similarity {item['score']:.3f}")
            with st.expander("View retrieved text"):
                st.write(item["text"])
            st.markdown(f"[Open original Wikibooks source]({item['url']})")

st.subheader("Collected pages")
summary = pd.DataFrame(
    [
        {
            "Title": page.get("title", ""),
            "Words": int(page.get("word_count", 0)),
            "Characters": int(page.get("characters", 0)),
            "Source": page.get("url", ""),
        }
        for page in pages
    ]
)
st.dataframe(summary, use_container_width=True, hide_index=True)

st.subheader("Collection visualisation")
fig, ax = plt.subplots()
ax.bar(summary["Title"].astype(str), summary["Words"])
ax.set_ylabel("Words collected")
ax.set_xlabel("Article")
ax.set_title("Words collected per Wikibooks page")
ax.tick_params(axis="x", labelrotation=35)
fig.tight_layout()
st.pyplot(fig)
plt.close(fig)

with st.expander("Ethical crawling log"):
    log_path = DATA_DIR / "crawl_log.txt"
    st.code(log_path.read_text(encoding="utf-8") if log_path.exists() else "No crawl log found.")
